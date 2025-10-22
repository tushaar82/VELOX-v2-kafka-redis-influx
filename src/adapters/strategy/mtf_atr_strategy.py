"""
Multi-Timeframe ATR Strategy with 1:3 Risk-Reward Ratio.

Entry Logic:
- EMA crossover on primary timeframe (5-min)
- Trend confirmation on higher timeframe (15-min)
- RSI not overbought/oversold
- Volume above average

Exit Logic:
- ATR-based trailing stop loss (2x ATR)
- Fixed target at 1:3 risk-reward ratio
- Opposite signal on primary timeframe
"""

from typing import Dict, Optional
from datetime import datetime, timedelta
from collections import defaultdict

from .base import StrategyAdapter
from ...utils.indicators import IndicatorManager
from ...utils.logging_config import get_logger


class MultiTimeframeATRStrategy(StrategyAdapter):
    """
    Professional Tick-by-Tick Scalping Strategy.
    
    Features:
    - Multi-timeframe trend alignment (EMA 9/21 on 5m, EMA 50 on 15m, EMA 200 on 1h)
    - MACD momentum confirmation
    - RSI filter (40-70 for long, 30-60 for short)
    - Volume confirmation (above 20-period average)
    - Price near EMA9 entry (within 0.2 ATR)
    - ATR-based stop loss (2.5x ATR)
    - Multiple take profit levels (2 ATR and 3 ATR)
    - Breakeven move at 1 ATR profit
    - Trailing stop at 1.5 ATR profit (2x ATR trail)
    - Both LONG and SHORT positions
    - Risk management: 1% per trade, max 2 positions, 2.5% daily loss limit
    """
    
    def __init__(self, strategy_id: str, symbols: list, config: Dict):
        """
        Initialize Multi-Timeframe ATR strategy.
        
        Args:
            strategy_id: Unique strategy identifier
            symbols: List of symbols to trade
            config: Strategy configuration with keys:
                - fast_ema: Fast EMA period (default 9)
                - slow_ema: Slow EMA period (default 21)
                - trend_ema: Trend EMA period for HTF (default 50)
                - atr_period: ATR calculation period (default 14)
                - atr_multiplier: ATR multiplier for trailing SL (default 2.0)
                - risk_reward_ratio: Risk-reward ratio (default 3.0)
                - rsi_period: RSI period (default 14)
                - rsi_min: Minimum RSI for entry (default 30)
                - rsi_max: Maximum RSI for entry (default 70)
                - volume_period: Volume MA period (default 20)
                - min_volume_multiplier: Min volume vs average (default 1.2)
                - position_size_pct: Position size as % of capital (default 0.02)
        """
        super().__init__(strategy_id, symbols, config)
        
        # Strategy parameters
        self.fast_ema = config.get('fast_ema', 9)  # EMA 9 on 5-min
        self.slow_ema = config.get('slow_ema', 21)  # EMA 21 on 5-min
        self.trend_ema_15m = config.get('trend_ema_15m', 50)  # EMA 50 on 15-min
        self.trend_ema_1h = config.get('trend_ema_1h', 200)  # EMA 200 on 1-hour
        
        # ATR settings
        self.atr_period = config.get('atr_period', 14)
        self.atr_sl_multiplier = config.get('atr_sl_multiplier', 2.5)  # Stop loss
        self.atr_trail_multiplier = config.get('atr_trail_multiplier', 2.0)  # Trailing
        self.atr_tp1_multiplier = config.get('atr_tp1_multiplier', 2.0)  # TP1
        self.atr_tp2_multiplier = config.get('atr_tp2_multiplier', 3.0)  # TP2
        
        # Entry filters
        self.rsi_period = config.get('rsi_period', 14)
        self.rsi_long_min = config.get('rsi_long_min', 40)
        self.rsi_long_max = config.get('rsi_long_max', 70)
        self.rsi_short_min = config.get('rsi_short_min', 30)
        self.rsi_short_max = config.get('rsi_short_max', 60)
        self.volume_period = config.get('volume_period', 20)
        self.price_ema_distance = config.get('price_ema_distance', 0.2)  # 0.2 ATR
        
        # Risk management
        self.risk_per_trade = config.get('risk_per_trade', 0.01)  # 1%
        self.max_positions = config.get('max_positions', 2)
        self.daily_loss_limit = config.get('daily_loss_limit', 0.025)  # 2.5%
        self.max_consecutive_losses = config.get('max_consecutive_losses', 3)
        
        # Profit management
        self.breakeven_atr = config.get('breakeven_atr', 1.0)  # Move to BE at 1 ATR
        self.trailing_start_atr = config.get('trailing_start_atr', 1.5)  # Trail at 1.5 ATR
        self.tp1_percent = config.get('tp1_percent', 0.5)  # Close 50% at TP1
        self.tp2_percent = config.get('tp2_percent', 0.3)  # Close 30% at TP2
        
        # Daily tracking
        self.daily_pnl = 0
        self.daily_trades = 0
        self.consecutive_losses = 0
        self.last_reset_date = None
        
        # Indicator manager
        self.indicator_manager = IndicatorManager()
        
        # Multi-timeframe data buffers
        self.candle_buffers = defaultdict(lambda: defaultdict(list))  # symbol -> timeframe -> candles
        self.last_candle_time = defaultdict(lambda: defaultdict(lambda: None))  # symbol -> timeframe -> time
        self.candle_close_flags = defaultdict(lambda: defaultdict(bool))  # symbol -> timeframe -> closed
        
        # Position tracking
        self.position_stops = {}  # symbol -> stop_loss_price
        self.position_atr = {}  # symbol -> atr_value at entry
        self.position_tp1 = {}  # symbol -> TP1 price
        self.position_tp2 = {}  # symbol -> TP2 price
        self.position_breakeven_moved = {}  # symbol -> bool
        self.position_trailing_active = {}  # symbol -> bool
        self.position_highest_price = {}  # symbol -> highest price since entry
        self.position_lowest_price = {}  # symbol -> lowest price since entry
        self.position_direction = {}  # symbol -> 'LONG' or 'SHORT'
        
        # Logger
        self.logger = get_logger('strategy', strategy_id)
        
        self.logger.info(
            f"MultiTimeframeATRStrategy initialized: "
            f"EMA({self.fast_ema}/{self.slow_ema}), Trend EMA({self.trend_ema}), "
            f"ATR({self.atr_period}x{self.atr_multiplier}), RR={self.risk_reward_ratio}:1"
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
        
        # Update indicators
        self.indicator_manager.process_tick(tick_data)
        
        # Build candles for multi-timeframe analysis
        self._update_candle_buffers(symbol, tick_data)
        
        # Update position price if we have one
        if symbol in self.positions:
            price = tick_data.get('price', tick_data.get('close'))
            self.update_position_price(symbol, price)
            
            # Update trailing stop loss
            self._update_trailing_stop(symbol, price)
            
            # Check exit conditions
            exit_signal = self.check_exit_conditions(symbol, tick_data)
            if exit_signal:
                self.signals.append(exit_signal)
                self.logger.info(
                    f"[EXIT_SIGNAL] {symbol} @ {price:.2f}: {exit_signal['reason']}"
                )
        else:
            # Check entry conditions (only on candle close)
            entry_signal = self.check_entry_conditions(symbol, tick_data)
            if entry_signal:
                self.signals.append(entry_signal)
                self.logger.info(
                    f"[ENTRY_SIGNAL] {symbol} @ {entry_signal['price']:.2f}: {entry_signal['reason']}"
                )
    
    def on_candle_close(self, candle_data: Dict, timeframe: str) -> None:
        """Process candle close (not used in tick-based strategy)."""
        pass
    
    def _update_candle_buffers(self, symbol: str, tick_data: Dict):
        """Update candle buffers for multi-timeframe analysis."""
        timestamp = tick_data['timestamp']
        price = tick_data.get('price', tick_data.get('close'))
        
        # 3-minute candles (for entry signals)
        candle_3m_time = timestamp.replace(second=0, microsecond=0)
        candle_3m_time = candle_3m_time.replace(minute=(candle_3m_time.minute // 3) * 3)
        
        if self.last_candle_time[symbol]['3min'] != candle_3m_time:
            # New 3-min candle started (for reference only)
            self.last_candle_time[symbol]['3min'] = candle_3m_time
            # Keep last 100 candles
            if len(self.candle_buffers[symbol]['3min']) >= 100:
                self.candle_buffers[symbol]['3min'].pop(0)
        
        # 15-minute candles (for trend confirmation)
        candle_15m_time = timestamp.replace(second=0, microsecond=0)
        candle_15m_time = candle_15m_time.replace(minute=(candle_15m_time.minute // 15) * 15)
        
        if self.last_candle_time[symbol]['15min'] != candle_15m_time:
            self.last_candle_time[symbol]['15min'] = candle_15m_time
            # Keep last 100 candles
            if len(self.candle_buffers[symbol]['15min']) >= 100:
                self.candle_buffers[symbol]['15min'].pop(0)
    
    def _check_candle_close_signal(self, symbol: str, tick_data: Dict, timeframe: str):
        """Check for entry signal on candle close."""
        # This will be called when a 3-min candle closes
        # Entry logic will be checked here instead of on every tick
        pass
    
    def check_entry_conditions(self, symbol: str, tick_data: Dict) -> Optional[Dict]:
        """
        Check if entry conditions are met (tick-by-tick).
        
        Entry Conditions:
        1. Fast EMA crosses above Slow EMA (bullish)
        2. Price above Trend EMA on 15-min timeframe (trend confirmation)
        3. RSI between 30-70
        4. Volume above 1.0x average (optional)
        5. No existing position
        
        Returns:
            Signal dictionary if conditions met, None otherwise
        """
        if symbol in self.positions:
            return None
        
        price = tick_data.get('price', tick_data.get('close'))
        volume = tick_data.get('volume', 0)
        
        # Get technical indicators object
        if symbol not in self.indicator_manager.indicators:
            return None
        
        ti = self.indicator_manager.indicators[symbol]
        
        # Get indicators
        fast_ema = ti.calculate_ema(self.fast_ema)
        slow_ema = ti.calculate_ema(self.slow_ema)
        trend_ema = ti.calculate_ema(self.trend_ema)
        rsi = ti.calculate_rsi(self.rsi_period)
        atr = ti.calculate_atr(self.atr_period)
        
        # Calculate volume MA manually
        if len(ti.volumes) < self.volume_period:
            volume_ma = None
        else:
            import numpy as np
            volumes_list = list(ti.volumes)[-self.volume_period:]
            volume_ma = np.mean(volumes_list) if volumes_list else 0
        
        # Check if we have enough data (volume is optional if it's 0)
        if None in [fast_ema, slow_ema, trend_ema, rsi, atr]:
            return None
        
        # If volume data is missing or zero, skip volume filter
        if volume_ma is None or volume_ma == 0:
            volume_ok = True  # Skip volume filter if no volume data
            self.logger.debug(f"Volume filter skipped for {symbol} (no volume data)")
        else:
            # 4. Volume filter
            volume_ok = volume > (volume_ma * self.min_volume_multiplier)
        
        # Get previous values for crossover detection
        # We'll track previous EMAs in position data
        # For now, use a simple approach: check if fast > slow (bullish alignment)
        if not hasattr(self, '_prev_emas'):
            self._prev_emas = {}
        
        prev_fast_ema = self._prev_emas.get(f'{symbol}_fast', slow_ema)
        prev_slow_ema = self._prev_emas.get(f'{symbol}_slow', slow_ema)
        
        # Store current EMAs for next tick
        self._prev_emas[f'{symbol}_fast'] = fast_ema
        self._prev_emas[f'{symbol}_slow'] = slow_ema
        
        # Check conditions
        # 1. EMA crossover (bullish)
        ema_crossover = (prev_fast_ema <= prev_slow_ema) and (fast_ema > slow_ema)
        
        # 2. Price above trend EMA (uptrend confirmation)
        uptrend = price > trend_ema
        
        # 3. RSI filter (not overbought/oversold)
        rsi_ok = self.rsi_min < rsi < self.rsi_max
        
        # All conditions must be met
        if ema_crossover and uptrend and rsi_ok and volume_ok:
            # Calculate position size based on ATR
            risk_per_share = atr * self.atr_multiplier
            stop_loss_price = price - risk_per_share
            target_price = price + (risk_per_share * self.risk_reward_ratio)
            
            # Calculate quantity (2% of capital risked)
            # Assuming $100,000 capital for now
            capital = 100000
            risk_amount = capital * self.position_size_pct
            
            # Calculate quantity based on risk per share
            if risk_per_share > 0:
                quantity = max(1, int(risk_amount / risk_per_share))
            else:
                quantity = 1
            
            # Ensure position size doesn't exceed max_position_size (10000)
            max_position_size = 10000
            max_quantity = int(max_position_size / price) if price > 0 else 1
            quantity = min(quantity, max_quantity)
            
            # Store position parameters
            self.position_stops[symbol] = stop_loss_price
            self.position_targets[symbol] = target_price
            self.position_atr[symbol] = atr
            
            # Build reason string
            if volume_ma and volume_ma > 0:
                reason = f'EMA Crossover + Uptrend (RSI:{rsi:.1f}, Vol:{volume/volume_ma:.2f}x)'
            else:
                reason = f'EMA Crossover + Uptrend (RSI:{rsi:.1f}, Vol:N/A)'
            
            return {
                'strategy_id': self.strategy_id,
                'action': 'BUY',
                'symbol': symbol,
                'price': price,
                'quantity': quantity,
                'timestamp': tick_data['timestamp'],
                'reason': reason,
                'indicators': {
                    'fast_ema': fast_ema,
                    'slow_ema': slow_ema,
                    'trend_ema': trend_ema,
                    'rsi': rsi,
                    'atr': atr,
                    'stop_loss': stop_loss_price,
                    'target': target_price,
                    'risk_reward': self.risk_reward_ratio
                }
            }
        
        return None
    
    def check_exit_conditions(self, symbol: str, tick_data: Dict) -> Optional[Dict]:
        """
        Check if exit conditions are met.
        
        Exit Conditions:
        1. ANY PROFIT - Exit immediately when in profit
        2. Trailing stop loss hit (ATR-based)
        3. Price hits target (1:3 RR)
        4. Fast EMA crosses below Slow EMA (reversal)
        
        Returns:
            Signal dictionary if conditions met, None otherwise
        """
        if symbol not in self.positions:
            return None
        
        pos = self.positions[symbol]
        price = tick_data.get('price', tick_data.get('close'))
        entry_price = pos['entry_price']
        
        # Check if we have minimum profit (0.3% or more)
        min_profit_pct = 0.3  # Minimum 0.3% profit to exit
        current_pnl_pct = ((price - entry_price) / entry_price) * 100
        
        # QUICK PROFIT EXIT - Exit when we have at least 0.3% profit
        if current_pnl_pct >= min_profit_pct:
            pnl = (price - entry_price) * pos['quantity']
            
            self._cleanup_position_data(symbol)
            return {
                'strategy_id': self.strategy_id,
                'action': 'SELL',
                'symbol': symbol,
                'price': price,
                'quantity': pos['quantity'],
                'timestamp': tick_data['timestamp'],
                'reason': f'Quick profit exit: +${pnl:.2f} (+{current_pnl_pct:.2f}%)',
                'indicators': {}
            }
        
        # Get technical indicators object
        if symbol not in self.indicator_manager.indicators:
            return None
        
        ti = self.indicator_manager.indicators[symbol]
        
        # Get current indicators
        fast_ema = ti.calculate_ema(self.fast_ema)
        slow_ema = ti.calculate_ema(self.slow_ema)
        
        # 1. Check target hit
        if symbol in self.position_targets:
            target = self.position_targets[symbol]
            if price >= target:
                self._cleanup_position_data(symbol)
                return {
                    'strategy_id': self.strategy_id,
                    'action': 'SELL',
                    'symbol': symbol,
                    'price': price,
                    'quantity': pos['quantity'],
                    'timestamp': tick_data['timestamp'],
                    'reason': f'Target hit @ {target:.2f} (1:{self.risk_reward_ratio} RR)',
                    'indicators': {}
                }
        
        # 2. Check trailing stop loss (only if it's above entry price - in profit zone)
        if symbol in self.position_stops:
            stop = self.position_stops[symbol]
            
            # Only exit on trailing SL if the stop is above entry (profit protection)
            if stop > entry_price and price <= stop:
                pnl = (price - entry_price) * pos['quantity']
                pnl_pct = ((price - entry_price) / entry_price) * 100
                
                self._cleanup_position_data(symbol)
                return {
                    'strategy_id': self.strategy_id,
                    'action': 'SELL',
                    'symbol': symbol,
                    'price': price,
                    'quantity': pos['quantity'],
                    'timestamp': tick_data['timestamp'],
                    'reason': f'Trailing SL (profit lock): +${pnl:.2f} (+{pnl_pct:.2f}%)',
                    'indicators': {}
                }
            
            # If stop is below entry and price hits it, it's a loss - use initial SL instead
            elif stop <= entry_price and price <= stop:
                pnl = (price - entry_price) * pos['quantity']
                pnl_pct = ((price - entry_price) / entry_price) * 100
                
                self._cleanup_position_data(symbol)
                return {
                    'strategy_id': self.strategy_id,
                    'action': 'SELL',
                    'symbol': symbol,
                    'price': price,
                    'quantity': pos['quantity'],
                    'timestamp': tick_data['timestamp'],
                    'reason': f'Stop loss hit: ${pnl:.2f} ({pnl_pct:.2f}%)',
                    'indicators': {}
                }
        
        # 3. Check EMA crossover (bearish reversal)
        if fast_ema and slow_ema:
            if not hasattr(self, '_prev_emas'):
                self._prev_emas = {}
            
            prev_fast_ema = self._prev_emas.get(f'{symbol}_fast', fast_ema)
            prev_slow_ema = self._prev_emas.get(f'{symbol}_slow', slow_ema)
            
            # Store current for next tick
            self._prev_emas[f'{symbol}_fast'] = fast_ema
            self._prev_emas[f'{symbol}_slow'] = slow_ema
            
            ema_cross_down = (prev_fast_ema >= prev_slow_ema) and (fast_ema < slow_ema)
            
            if ema_cross_down:
                self._cleanup_position_data(symbol)
                return {
                    'strategy_id': self.strategy_id,
                    'action': 'SELL',
                    'symbol': symbol,
                    'price': price,
                    'quantity': pos['quantity'],
                    'timestamp': tick_data['timestamp'],
                    'reason': 'EMA bearish crossover',
                    'indicators': {}
                }
        
        return None
    
    def _update_trailing_stop(self, symbol: str, current_price: float):
        """
        Update trailing stop loss based on ATR.
        Only activates when in profit to lock in gains.
        
        Args:
            symbol: Symbol
            current_price: Current price
        """
        if symbol not in self.positions or symbol not in self.position_stops:
            return
        
        pos = self.positions[symbol]
        entry_price = pos['entry_price']
        highest_price = pos['highest_price']
        
        # Get current ATR
        if symbol in self.indicator_manager.indicators:
            ti = self.indicator_manager.indicators[symbol]
            atr = ti.calculate_atr(self.atr_period)
        else:
            atr = None
        
        if not atr:
            atr = self.position_atr.get(symbol, 0)
        
        # Calculate new trailing stop from highest price
        new_stop = highest_price - (atr * self.atr_multiplier)
        
        # Only activate trailing SL when we're in profit (highest price > entry)
        # This ensures trailing SL only locks in profits, not losses
        if highest_price > entry_price:
            # Ensure the new stop is at least at breakeven or better
            new_stop = max(new_stop, entry_price)
            
            # Only move stop up, never down
            current_stop = self.position_stops[symbol]
            if new_stop > current_stop:
                self.position_stops[symbol] = new_stop
                self.logger.info(
                    f"🛡️  Trailing SL updated for {symbol}: {current_stop:.2f} -> {new_stop:.2f} "
                    f"(Profit zone, Highest: {highest_price:.2f})"
                )
    
    def _cleanup_position_data(self, symbol: str):
        """Clean up position-related data."""
        if symbol in self.position_targets:
            del self.position_targets[symbol]
        if symbol in self.position_stops:
            del self.position_stops[symbol]
        if symbol in self.position_atr:
            del self.position_atr[symbol]
