"""
Supertrend Strategy Implementation.
Simple trend-following strategy using Supertrend indicator.
"""

from typing import Dict, Optional
from datetime import datetime, timedelta
import numpy as np

from .base import StrategyAdapter
from ...utils.indicators import IndicatorManager
from ...utils.logging_config import get_logger


class SupertrendStrategy(StrategyAdapter):
    """
    Supertrend trend-following strategy.
    
    Entry:
    - BUY when price crosses above Supertrend line (trend turns bullish)
    - SELL when price crosses below Supertrend line (trend turns bearish)
    
    Parameters:
    - atr_period: ATR calculation period (default: 10)
    - atr_multiplier: ATR multiplier for bands (default: 3)
    - min_hold_time_minutes: Minimum hold time (default: 5)
    """
    
    def __init__(self, strategy_id: str, symbols: list, config: Dict):
        """Initialize Supertrend strategy."""
        super().__init__(strategy_id, symbols, config)
        
        # Strategy parameters
        self.atr_period = config.get('atr_period', 10)
        self.atr_multiplier = config.get('atr_multiplier', 3)
        self.min_hold_time_minutes = config.get('min_hold_time_minutes', 5)
        self.min_volume = config.get('min_volume', 100)
        
        # Position sizing
        self.position_size_pct = config.get('position_size_pct', 0.1)  # 10% of capital per trade
        # Align quantity sizing with RiskManager: use a max_position_size cap (default 11k)
        self.max_position_size = config.get('max_position_size', 11000)
        
        # Indicator manager
        self.indicator_manager = IndicatorManager()
        
        # Track previous Supertrend state
        self.prev_supertrend = {}  # {symbol: {'trend': 1/-1, 'value': float}}
        
        # Set warmup requirements
        self.warmup_candles_required = max(self.atr_period + 1, 50)
        
        # Logger
        self.logger = get_logger('strategy', strategy_id)
        
        self.logger.info(
            f"SupertrendStrategy initialized: atr_period={self.atr_period}, "
            f"atr_multiplier={self.atr_multiplier}, min_hold={self.min_hold_time_minutes}min, "
            f"warmup_candles={self.warmup_candles_required}"
        )
    
    def initialize(self) -> None:
        """Initialize strategy."""
        self.logger.info(f"Strategy {self.strategy_id} initialized for symbols: {self.symbols}")
    
    def on_candle_close(self, candle_data: Dict, timeframe: str) -> None:
        """
        Process candle close event.
        
        For Supertrend, we process on every tick, so this is optional.
        Can be used for additional logic if needed.
        """
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
        
        # Calculate Supertrend to build history (but don't generate signals)
        self.calculate_supertrend(symbol, candle_data['high'], candle_data['low'], candle_data['close'])
    
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
        
        # Recalculate Supertrend on candle close
        self.calculate_supertrend(symbol, candle_data['high'], candle_data['low'], candle_data['close'])
        
        self.logger.debug(f"[{symbol}] Candle complete: O={candle_data['open']:.2f}, H={candle_data['high']:.2f}, "
                         f"L={candle_data['low']:.2f}, C={candle_data['close']:.2f}")
    
    def calculate_supertrend(self, symbol: str, high: float, low: float, close: float) -> Dict:
        """
        Calculate Supertrend indicator.
        
        Returns:
            Dict with 'trend' (1=bullish, -1=bearish) and 'value' (Supertrend line)
        """
        # Get ATR
        indicators = self.indicator_manager.get_indicators(
            symbol,
            atr_period=self.atr_period
        )
        
        if not indicators or 'atr' not in indicators:
            return None
        
        atr = indicators['atr']
        
        # Check if ATR is valid
        if atr is None or atr == 0:
            return None
        
        # Calculate basic bands
        hl_avg = (high + low) / 2
        basic_upper = hl_avg + (self.atr_multiplier * atr)
        basic_lower = hl_avg - (self.atr_multiplier * atr)
        
        # Get previous Supertrend state
        prev = self.prev_supertrend.get(symbol)
        
        # Initialize on first calculation
        if prev is None:
            # Start with bullish assumption
            final_upper = basic_upper
            final_lower = basic_lower
            supertrend_value = basic_lower
            trend = 1 if close > basic_lower else -1
        else:
            # Apply band smoothing (bands can only move in favorable direction)
            # Upper band can only decrease or stay same
            final_upper = basic_upper if basic_upper < prev.get('upper', basic_upper) else prev.get('upper', basic_upper)
            # Lower band can only increase or stay same
            final_lower = basic_lower if basic_lower > prev.get('lower', basic_lower) else prev.get('lower', basic_lower)
            
            # Determine trend based on close vs previous Supertrend
            prev_trend = prev['trend']
            
            if prev_trend == 1:  # Was bullish
                # Stay bullish if close > lower band, else turn bearish
                if close <= final_lower:
                    trend = -1
                    supertrend_value = final_upper
                else:
                    trend = 1
                    supertrend_value = final_lower
            else:  # Was bearish
                # Stay bearish if close < upper band, else turn bullish
                if close >= final_upper:
                    trend = 1
                    supertrend_value = final_lower
                else:
                    trend = -1
                    supertrend_value = final_upper
        
        result = {
            'trend': trend,
            'value': supertrend_value,
            'atr': atr,
            'upper': final_upper if prev else basic_upper,
            'lower': final_lower if prev else basic_lower
        }
        
        # Store for next calculation
        self.prev_supertrend[symbol] = result
        
        # Log trend changes
        if prev and prev['trend'] != trend:
            self.logger.info(
                f"[{symbol}] 🔄 Supertrend TREND CHANGE: "
                f"{'Bearish→Bullish' if trend == 1 else 'Bullish→Bearish'} | "
                f"Close={close:.2f}, ST={supertrend_value:.2f}"
            )
        
        return result
    
    def on_tick(self, tick_data: Dict) -> None:
        """Process a market tick."""
        symbol = tick_data.get('symbol')
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
        
        # Check for entry signals
        if symbol not in self.positions:
            signal = self.check_entry_conditions(symbol, tick_data)
            if signal:
                self.signals.append(signal)
        else:
            # Check for exit signals
            signal = self.check_exit_conditions(symbol, tick_data)
            if signal:
                self.signals.append(signal)
    
    def check_entry_conditions(self, symbol: str, tick_data: Dict) -> Optional[Dict]:
        """
        Check if entry conditions are met.
        
        Entry: Price crosses above Supertrend (bullish trend)
        """
        # Don't generate signal if not warmed up
        if not self.is_warmed_up:
            return None
        
        # Don't generate signal if we already have a position
        if symbol in self.positions:
            return None
        close = tick_data.get('close', tick_data.get('price'))
        high = tick_data.get('high', close)
        low = tick_data.get('low', close)
        volume = tick_data.get('volume', 0)
        
        # Volume filter
        if volume < self.min_volume:
            return None
        
        # Get previous trend BEFORE calculating new one
        prev_trend = self.prev_supertrend.get(symbol, {}).get('trend')
        
        # Calculate Supertrend (this will update self.prev_supertrend)
        supertrend = self.calculate_supertrend(symbol, high, low, close)
        if not supertrend:
            return None
        
        # Need at least one previous calculation to detect crossover
        if prev_trend is None:
            return None
        
        # Entry signal: Trend changed from bearish to bullish
        if supertrend['trend'] == 1 and prev_trend == -1:
            # Price crossed above Supertrend
            self.logger.info(
                f"[{symbol}] BUY SIGNAL: Supertrend turned bullish\n"
                f"  ├─ Price: {close:.2f}\n"
                f"  ├─ Supertrend: {supertrend['value']:.2f}\n"
                f"  └─ ATR: {supertrend['atr']:.2f}"
            )
            
            # Calculate quantity strictly based on max_position_size limit
            # This avoids dependency on account capital inside the strategy
            quantity = int(self.max_position_size / close)
            
            # Minimum 1 share
            if quantity < 1:
                quantity = 1
            # Log planned quantity and position value
            planned_value = quantity * close
            self.logger.info(
                f"[{symbol}] Position sizing\n"
                f"  ├─ Max position size: {self.max_position_size}\n"
                f"  ├─ Computed quantity: {quantity}\n"
                f"  └─ Position value: {planned_value:.2f}"
            )
            
            return {
                'strategy_id': self.strategy_id,
                'action': 'BUY',
                'symbol': symbol,
                'price': close,
                'quantity': quantity,
                'timestamp': tick_data.get('timestamp'),
                'reason': f"Supertrend bullish crossover @ {close:.2f}"
            }
        
        return None
    
    def check_exit_conditions(self, symbol: str, tick_data: Dict) -> Optional[Dict]:
        """
        Check if exit conditions are met.
        
        Exit: Price crosses below Supertrend (bearish trend)
        """
        # Don't generate signal if not warmed up
        if not self.is_warmed_up:
            return None
        
        if symbol not in self.positions:
            return None
        
        pos = self.positions[symbol]
        close = tick_data.get('close', tick_data.get('price'))
        high = tick_data.get('high', close)
        low = tick_data.get('low', close)
        entry_price = pos['entry_price']
        entry_time = pos.get('timestamp', datetime.now())
        current_time = tick_data.get('timestamp', datetime.now())
        
        # Calculate hold time
        hold_time = current_time - entry_time
        hold_minutes = hold_time.total_seconds() / 60
        
        # Calculate P&L
        pnl_pct = ((close - entry_price) / entry_price) * 100
        
        # Get previous trend BEFORE calculating new one
        prev_trend = self.prev_supertrend.get(symbol, {}).get('trend')
        
        # Calculate Supertrend
        supertrend = self.calculate_supertrend(symbol, high, low, close)
        if not supertrend:
            return None
        
        # Need previous trend to detect crossover
        if prev_trend is None:
            return None
        
        self.logger.debug(
            f"[EXIT_CHECK] Position: {symbol}\n"
            f"  ├─ Entry: {entry_price:.2f}, Current: {close:.2f}\n"
            f"  ├─ P&L: {pnl_pct:+.2f}%\n"
            f"  ├─ Hold time: {hold_minutes:.1f} min (min: {self.min_hold_time_minutes} min)\n"
            f"  ├─ Supertrend: {supertrend['value']:.2f} (trend: {'Bullish' if supertrend['trend'] == 1 else 'Bearish'})"
        )
        
        reason = None
        
        # Exit signal: Trend changed from bullish to bearish (after min hold time)
        if hold_minutes >= self.min_hold_time_minutes:
            if supertrend['trend'] == -1 and prev_trend == 1:
                reason = f"Supertrend bearish crossover: {close:.2f} < {supertrend['value']:.2f} (P&L: {pnl_pct:+.2f}%)"
            else:
                self.logger.debug(
                    f"[{symbol}] No exit yet: trend={supertrend['trend']}, prev_trend={prev_trend}, "
                    f"hold={hold_minutes:.1f}min, pnl={pnl_pct:+.2f}%"
                )
        else:
            self.logger.debug(f"[{symbol}] Min hold not met: {hold_minutes:.1f} < {self.min_hold_time_minutes} min")
        
        if reason:
            self.logger.info(
                f"[{symbol}] SELL SIGNAL: {reason}\n"
                f"  ├─ Entry: {entry_price:.2f}, Exit: {close:.2f}\n"
                f"  ├─ P&L: {pnl_pct:+.2f}%\n"
                f"  └─ Hold time: {hold_minutes:.1f} min"
            )
            
            return {
                'strategy_id': self.strategy_id,
                'action': 'SELL',
                'symbol': symbol,
                'price': close,
                'quantity': pos['quantity'],
                'timestamp': current_time,
                'reason': reason
            }
        
        return None
    
    def get_status(self) -> Dict:
        """Get strategy status."""
        status = super().get_status()
        status.update({
            'parameters': {
                'atr_period': self.atr_period,
                'atr_multiplier': self.atr_multiplier,
                'min_hold_time': self.min_hold_time_minutes
            }
        })
        return status
