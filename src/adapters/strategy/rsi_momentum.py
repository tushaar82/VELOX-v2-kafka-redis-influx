"""
RSI + MA Momentum Strategy.
Enters on RSI oversold + price above MA, exits on target/SL/overbought.
"""

from typing import Dict, Optional
from datetime import datetime, timedelta

from .base import StrategyAdapter
from ...utils.indicators import IndicatorManager
from ...utils.logging_config import get_logger


class RSIMomentumStrategy(StrategyAdapter):
    """RSI + Moving Average momentum strategy."""
    
    def __init__(self, strategy_id: str, symbols: list, config: Dict):
        """
        Initialize RSI Momentum strategy.
        
        Args:
            strategy_id: Unique strategy identifier
            symbols: List of symbols to trade
            config: Strategy configuration with keys:
                - rsi_period: RSI calculation period (default 14)
                - rsi_oversold: RSI oversold threshold (default 30)
                - rsi_overbought: RSI overbought threshold (default 70)
                - ma_period: Moving average period (default 20)
                - target_pct: Target profit percentage (default 0.02 = 2%)
                - initial_sl_pct: Initial stop loss percentage (default 0.01 = 1%)
                - min_volume: Minimum volume filter (default 100)
        """
        super().__init__(strategy_id, symbols, config)
        
        # Strategy parameters
        self.rsi_period = config.get('rsi_period', 14)
        self.rsi_oversold = config.get('rsi_oversold', 30)
        self.rsi_overbought = config.get('rsi_overbought', 70)
        self.ma_period = config.get('ma_period', 20)
        self.target_pct = config.get('target_pct', 0.02)
        self.initial_sl_pct = config.get('initial_sl_pct', 0.01)
        self.min_volume = config.get('min_volume', 100)
        
        # Realistic trading constraints
        self.min_hold_time_minutes = config.get('min_hold_time_minutes', 5)  # Minimum 5 minutes hold
        self.use_trailing_sl = config.get('use_trailing_sl', True)
        self.breakeven_trigger_pct = config.get('breakeven_trigger_pct', 0.005)  # Move to BE at 0.5% profit
        self.use_external_trailing_sl = config.get('use_external_trailing_sl', True)  # Use external trailing SL manager
        
        # Indicator manager
        self.indicator_manager = IndicatorManager()
        
        # Set warmup requirements
        self.warmup_candles_required = max(self.rsi_period, self.ma_period) + 10
        
        # Logger
        self.logger = get_logger('strategy', strategy_id)
        
        self.logger.info(
            f"RSIMomentumStrategy initialized: rsi_oversold={self.rsi_oversold}, "
            f"rsi_overbought={self.rsi_overbought}, ma_period={self.ma_period}, "
            f"target={self.target_pct*100}%, sl={self.initial_sl_pct*100}%, "
            f"min_hold={self.min_hold_time_minutes}min, "
            f"trailing_sl={'External' if self.use_external_trailing_sl else 'Internal'}, "
            f"warmup_candles={self.warmup_candles_required}"
        )
    
    def initialize(self) -> None:
        """Initialize strategy."""
        self.logger.info(f"Strategy {self.strategy_id} initialized for symbols: {self.symbols}")
    
    def on_tick(self, tick_data: Dict) -> None:
        """
        Process a market tick.
        
        Args:
            tick_data: Tick data dictionary
        """
        if not self.is_active:
            return
        
        symbol = tick_data['symbol']
        
        # Only process ticks for our symbols
        if symbol not in self.symbols:
            return
        
        # Update indicators with current forming candle
        if hasattr(self.indicator_manager, 'update_forming_candle'):
            self.indicator_manager.update_forming_candle(
                symbol=symbol,
                high=tick_data.get('high', tick_data.get('price')),
                low=tick_data.get('low', tick_data.get('price')),
                close=tick_data.get('close', tick_data.get('price')),
                volume=tick_data.get('volume', 0),
                timestamp=tick_data.get('timestamp')
            )
        else:
            # Fallback to process_tick
            self.indicator_manager.process_tick(tick_data)
        
        # Only generate signals if warmed up
        if not self.is_warmed_up:
            return
        
        # Update position price if we have one
        if symbol in self.positions:
            price = tick_data.get('price', tick_data.get('close'))
            self.update_position_price(symbol, price)
            
            # Check exit conditions
            exit_signal = self.check_exit_conditions(symbol, tick_data)
            if exit_signal:
                self.signals.append(exit_signal)
                self.logger.info(
                    f"[EXIT_SIGNAL] {symbol} @ {price:.2f}: {exit_signal['reason']}"
                )
        else:
            # Check entry conditions
            entry_signal = self.check_entry_conditions(symbol, tick_data)
            if entry_signal:
                self.signals.append(entry_signal)
                self.logger.info(
                    f"[ENTRY_SIGNAL] {symbol} @ {entry_signal['price']:.2f}: {entry_signal['reason']}"
                )
    
    def on_candle_close(self, candle_data: Dict, timeframe: str) -> None:
        """Process candle close event."""
        # Not used in this strategy (tick-based)
        pass
    
    def on_warmup_candle(self, candle_data: Dict, timeframe: str) -> None:
        """
        Process historical candle during warmup phase.
        
        Feed candles to indicator manager without generating signals.
        """
        symbol = candle_data.get('symbol')
        if symbol not in self.symbols:
            return
        
        # Add candle to indicator manager
        if hasattr(self.indicator_manager, 'add_candle'):
            self.indicator_manager.add_candle(
                symbol=symbol,
                open_price=candle_data['open'],
                high=candle_data['high'],
                low=candle_data['low'],
                close=candle_data['close'],
                volume=candle_data.get('volume', 0),
                timestamp=candle_data['timestamp']
            )
        else:
            # Fallback to process_tick for backward compatibility
            tick_data = {
                'symbol': symbol,
                'timestamp': candle_data['timestamp'],
                'price': candle_data['close'],
                'open': candle_data['open'],
                'high': candle_data['high'],
                'low': candle_data['low'],
                'close': candle_data['close'],
                'volume': candle_data.get('volume', 0)
            }
            self.indicator_manager.process_tick(tick_data)
    
    def on_candle_complete(self, candle_data: Dict, timeframe: str) -> None:
        """
        Process completed candle during live trading.
        
        Recalculate indicators when a candle closes.
        """
        if not self.is_warmed_up:
            return
        
        symbol = candle_data.get('symbol')
        if symbol not in self.symbols:
            return
        
        # Add closed candle to indicator manager
        if hasattr(self.indicator_manager, 'add_candle'):
            self.indicator_manager.add_candle(
                symbol=symbol,
                open_price=candle_data['open'],
                high=candle_data['high'],
                low=candle_data['low'],
                close=candle_data['close'],
                volume=candle_data.get('volume', 0),
                timestamp=candle_data['timestamp']
            )
        
        self.logger.debug(f"[{symbol}] Candle complete: O={candle_data['open']:.2f}, H={candle_data['high']:.2f}, "
                         f"L={candle_data['low']:.2f}, C={candle_data['close']:.2f}")
    
    def check_entry_conditions(self, symbol: str, tick_data: Dict) -> Optional[Dict]:
        """
        Check if entry conditions are met.
        
        Entry conditions:
        1. RSI < oversold threshold (30)
        2. Price > MA (momentum confirmation)
        3. Volume > minimum volume
        
        Args:
            symbol: Symbol to check
            tick_data: Current tick data
            
        Returns:
            Signal dictionary if conditions met, None otherwise
        """
        # Don't generate signal if not warmed up
        if not self.is_warmed_up:
            return None
        
        # Get indicators
        indicators = self.indicator_manager.get_indicators(
            symbol,
            rsi_period=self.rsi_period,
            ma_period=self.ma_period
        )
        
        # Need sufficient data
        if not indicators or indicators.get('rsi') is None or indicators.get('ma') is None:
            return None
        
        rsi = indicators['rsi']
        ma = indicators['ma']
        current_price = tick_data.get('price', tick_data.get('close'))
        volume = tick_data.get('volume', 0)
        
        # Log detailed check
        self.logger.debug(
            f"[SIGNAL_CHECK] {symbol} @ {current_price:.2f}\n"
            f"  ├─ RSI: {rsi:.2f} {'<' if rsi < self.rsi_oversold else '>='} "
            f"{self.rsi_oversold} (oversold) → {'PASS ✓' if rsi < self.rsi_oversold else 'FAIL ✗'}\n"
            f"  ├─ MA({self.ma_period}): {ma:.2f}\n"
            f"  ├─ Price > MA: {current_price:.2f} {'>' if current_price > ma else '<='} {ma:.2f} → "
            f"{'PASS ✓' if current_price > ma else 'FAIL ✗'}\n"
            f"  ├─ Volume: {volume} {'>' if volume > self.min_volume else '<='} {self.min_volume} → "
            f"{'PASS ✓' if volume > self.min_volume else 'FAIL ✗'}"
        )
        
        # Check conditions
        if rsi < self.rsi_oversold and current_price > ma and volume > self.min_volume:
            # Calculate quantity based on max position size (default $5000 per position)
            max_position_value = 5000  # Conservative position size
            quantity = int(max_position_value / current_price)
            quantity = max(1, quantity)  # At least 1 share
            
            signal = {
                'strategy_id': self.strategy_id,
                'action': 'BUY',
                'symbol': symbol,
                'price': current_price,
                'quantity': quantity,  # Dynamic quantity based on price
                'timestamp': tick_data.get('timestamp', datetime.now()),
                'reason': f"RSI={rsi:.2f} < {self.rsi_oversold} AND Price > MA({self.ma_period})",
                'indicators': {
                    'rsi': rsi,
                    'ma': ma,
                    'price': current_price,
                    'volume': volume
                }
            }
            
            self.logger.info(
                f"[SIGNAL_CHECK] {symbol} → DECISION: GENERATE BUY SIGNAL"
            )
            
            return signal
        
        return None
    
    def check_exit_conditions(self, symbol: str, tick_data: Dict) -> Optional[Dict]:
        """
        Check if exit conditions are met with realistic trading constraints.
        
        Exit conditions:
        1. Minimum hold time must pass (prevents instant exits)
        2. Hard stop loss hit (immediate exit)
        3. Target hit (after min hold time)
        4. RSI overbought (after min hold time)
        5. Trailing stop hit (after breakeven)
        
        Args:
            symbol: Symbol to check
            tick_data: Current tick data
            
        Returns:
            Signal dictionary if conditions met, None otherwise
        """
        # Don't generate signal if not warmed up
        if not self.is_warmed_up:
            return None
        
        if symbol not in self.positions:
            return None
        
        pos = self.positions[symbol]
        current_price = tick_data.get('price', tick_data.get('close'))
        entry_price = pos['entry_price']
        entry_time = pos.get('timestamp', datetime.now())
        current_time = tick_data.get('timestamp', datetime.now())
        
        # Calculate hold time
        hold_time = current_time - entry_time
        hold_minutes = hold_time.total_seconds() / 60
        
        # Calculate P&L
        pnl_pct = ((current_price - entry_price) / entry_price)
        
        # Get RSI
        indicators = self.indicator_manager.get_indicators(
            symbol,
            rsi_period=self.rsi_period
        )
        rsi = indicators.get('rsi') if indicators else None
        
        # Track highest price for position management
        if '_highest_price' not in pos:
            pos['_highest_price'] = current_price
        else:
            pos['_highest_price'] = max(pos['_highest_price'], current_price)
        
        highest_price = pos['_highest_price']
        max_pnl_pct = (highest_price - entry_price) / entry_price
        
        # Calculate stop loss price
        # If using external trailing SL, only use initial hard stop
        # Otherwise, implement internal trailing logic
        if self.use_external_trailing_sl:
            # Only check hard initial stop loss (external trailing SL handles the rest)
            sl_price = entry_price * (1 - self.initial_sl_pct)
        else:
            # Internal trailing stop logic
            sl_price = entry_price * (1 - self.initial_sl_pct)
            
            # If we've hit breakeven trigger, move SL to breakeven
            if max_pnl_pct >= self.breakeven_trigger_pct:
                sl_price = entry_price  # Breakeven
                if '_breakeven_set' not in pos:
                    pos['_breakeven_set'] = True
                    self.logger.info(f"[{symbol}] Stop loss moved to breakeven @ {sl_price:.2f}")
        
        # Log exit check
        rsi_str = f"{rsi:.2f}" if rsi is not None else "N/A"
        trailing_mode = "External" if self.use_external_trailing_sl else "Internal"
        self.logger.debug(
            f"[EXIT_CHECK] Position: {symbol}\n"
            f"  ├─ Entry: {entry_price:.2f}, Current: {current_price:.2f}, Highest: {highest_price:.2f}\n"
            f"  ├─ P&L: {pnl_pct*100:+.2f}% (Max: {max_pnl_pct*100:+.2f}%, Target: {self.target_pct*100}%)\n"
            f"  ├─ Hold time: {hold_minutes:.1f} min (min: {self.min_hold_time_minutes} min)\n"
            f"  ├─ RSI: {rsi_str} (overbought: {self.rsi_overbought})\n"
            f"  ├─ Hard Stop-loss: {sl_price:.2f} (Trailing: {trailing_mode})"
        )
        
        # Check exit conditions
        reason = None
        
        # IMMEDIATE EXIT: Hard stop loss hit (always exit, regardless of hold time)
        # Note: If using external trailing SL, this only catches hard initial stop
        # The external trailing SL manager handles trailing stops
        if current_price <= sl_price:
            if self.use_external_trailing_sl:
                reason = f"Hard stop-loss hit: {current_price:.2f} <= {sl_price:.2f} ({pnl_pct*100:.2f}%)"
            else:
                reason = f"Stop-loss hit: {current_price:.2f} <= {sl_price:.2f} ({pnl_pct*100:.2f}%)"
        
        # TIMED EXITS: Only after minimum hold time
        elif hold_minutes >= self.min_hold_time_minutes:
            # Target hit
            if pnl_pct >= self.target_pct:
                reason = f"Target hit: {pnl_pct*100:.2f}% >= {self.target_pct*100}% (held {hold_minutes:.1f}min)"
            
            # RSI overbought (only if profitable)
            elif rsi and rsi > self.rsi_overbought and pnl_pct > 0:
                reason = f"RSI overbought: {rsi:.2f} > {self.rsi_overbought} (P&L: {pnl_pct*100:+.2f}%)"
        
        else:
            self.logger.debug(
                f"[EXIT_CHECK] {symbol} → Holding (min time not met: {hold_minutes:.1f}/{self.min_hold_time_minutes} min)"
            )
        
        if reason:
            signal = {
                'strategy_id': self.strategy_id,
                'action': 'SELL',
                'symbol': symbol,
                'price': current_price,
                'quantity': pos['quantity'],
                'timestamp': tick_data.get('timestamp', datetime.now()),
                'reason': reason,
                'indicators': {
                    'rsi': rsi,
                    'pnl_pct': pnl_pct * 100,
                    'entry_price': entry_price,
                    'current_price': current_price,
                    'hold_minutes': hold_minutes
                }
            }
            
            self.logger.info(
                f"[EXIT_CHECK] {symbol} → DECISION: GENERATE SELL SIGNAL ({reason})"
            )
            
            return signal
        
        self.logger.debug(
            f"[EXIT_CHECK] {symbol} → DECISION: HOLD (no exit condition met)"
        )
        
        return None


if __name__ == "__main__":
    # Test the strategy
    from ...utils.logging_config import initialize_logging
    import logging
    
    initialize_logging(log_level=logging.INFO)
    
    print("\n=== Testing RSI Momentum Strategy ===\n")
    
    config = {
        'rsi_period': 14,
        'rsi_oversold': 30,
        'rsi_overbought': 70,
        'ma_period': 20,
        'target_pct': 0.02,
        'initial_sl_pct': 0.01
    }
    
    strategy = RSIMomentumStrategy('test_rsi', ['TEST'], config)
    strategy.initialize()
    
    print(f"Strategy: {strategy.strategy_id}")
    print(f"Symbols: {strategy.symbols}")
    print(f"Active: {strategy.is_active}")
    
    # Simulate some ticks
    print("\nSimulating downtrend (should make RSI oversold)...")
    for i in range(30):
        tick = {
            'timestamp': datetime.now(),
            'symbol': 'TEST',
            'price': 100.0 - i * 2,
            'high': 100.0 - i * 2 + 1,
            'low': 100.0 - i * 2 - 1,
            'volume': 1000
        }
        strategy.on_tick(tick)
    
    # Check for signals
    signals = strategy.get_signals()
    print(f"\nSignals generated: {len(signals)}")
    for signal in signals:
        print(f"  {signal['action']} {signal['symbol']} @ {signal['price']:.2f}: {signal['reason']}")
    
    print("\n✓ Strategy test complete")
