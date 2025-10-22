"""
Professional Tick-by-Tick Scalping Strategy.
Multi-timeframe trend alignment with MACD, RSI, and volume confirmation.
"""

from typing import Dict, Optional, List
from datetime import datetime, timedelta
from collections import defaultdict

from .base import StrategyAdapter
from ...utils.indicators import IndicatorManager
from ...utils.logging_config import get_logger


class ScalpingMTFATRStrategy(StrategyAdapter):
    """
    Professional Tick-by-Tick Scalping Strategy.
    
    Entry Rules:
    LONG: Price > EMA21, EMA9 > EMA21, Price > EMA50(15m), Price > EMA200(1h),
          40 < RSI < 70, MACD bullish, Volume > Avg, Price near EMA9
    
    SHORT: Price < EMA21, EMA9 < EMA21, Price < EMA50(15m), Price < EMA200(1h),
           30 < RSI < 60, MACD bearish, Volume > Avg, Price near EMA9
    
    Exit Rules:
    - TP1: 2 ATR (close 50%)
    - TP2: 3 ATR (close 30%)
    - Breakeven: Move SL to entry at 1 ATR profit
    - Trailing: Start at 1.5 ATR profit, trail 2 ATR behind highest/lowest
    - Stop Loss: 2.5 ATR from entry
    
    Risk Management:
    - Max 2 positions
    - 1% risk per trade
    - 2.5% daily loss limit
    - Max 3 consecutive losses
    """
    
    def __init__(self, strategy_id: str, symbols: list, config: Dict):
        """Initialize Scalping MTF ATR strategy."""
        super().__init__(strategy_id, symbols, config)
        
        # EMA settings
        self.ema9 = config.get('ema9', 9)
        self.ema21 = config.get('ema21', 21)
        self.ema50_15m = config.get('ema50_15m', 50)
        self.ema200_1h = config.get('ema200_1h', 200)
        
        # ATR settings
        self.atr_period = config.get('atr_period', 14)
        self.atr_sl_mult = config.get('atr_sl_mult', 2.5)
        self.atr_tp1_mult = config.get('atr_tp1_mult', 2.0)
        self.atr_tp2_mult = config.get('atr_tp2_mult', 3.0)
        self.atr_trail_mult = config.get('atr_trail_mult', 2.0)
        
        # RSI settings
        self.rsi_period = config.get('rsi_period', 14)
        self.rsi_long_min = config.get('rsi_long_min', 40)
        self.rsi_long_max = config.get('rsi_long_max', 70)
        self.rsi_short_min = config.get('rsi_short_min', 30)
        self.rsi_short_max = config.get('rsi_short_max', 60)
        
        # Volume and entry
        self.volume_period = config.get('volume_period', 20)
        self.price_ema_dist = config.get('price_ema_dist', 0.2)  # 0.2 ATR
        
        # Risk management
        self.risk_per_trade = config.get('risk_per_trade', 0.01)
        self.max_positions = config.get('max_positions', 2)
        self.daily_loss_limit = config.get('daily_loss_limit', 0.025)
        self.max_consec_losses = config.get('max_consec_losses', 3)
        
        # Profit management
        self.breakeven_atr = config.get('breakeven_atr', 1.0)
        self.trailing_start_atr = config.get('trailing_start_atr', 1.5)
        self.tp1_pct = config.get('tp1_pct', 0.5)
        self.tp2_pct = config.get('tp2_pct', 0.3)
        
        # Indicators
        self.indicator_manager = IndicatorManager()
        
        # Position tracking
        self.position_direction = {}  # 'LONG' or 'SHORT'
        self.position_stops = {}
        self.position_tp1 = {}
        self.position_tp2 = {}
        self.position_atr = {}
        self.position_highest = {}
        self.position_lowest = {}
        self.breakeven_moved = {}
        self.trailing_active = {}
        
        # Daily tracking
        self.daily_pnl = 0
        self.daily_trades = 0
        self.consec_losses = 0
        self.last_reset_date = None
        
        # Logger
        self.logger = get_logger('strategy', strategy_id)
        self.logger.info(
            f"Scalping MTF ATR Strategy initialized: "
            f"EMA({self.ema9}/{self.ema21}/{self.ema50_15m}/{self.ema200_1h}), "
            f"Risk={self.risk_per_trade*100}%, Max Pos={self.max_positions}"
        )
    
    def initialize(self):
        """Initialize strategy."""
        self.logger.info(f"Strategy {self.strategy_id} initialized for symbols: {self.symbols}")
    
    def on_tick(self, tick_data: Dict):
        """Process each tick."""
        symbol = tick_data['symbol']
        
        # Update indicators
        self.indicator_manager.process_tick(tick_data)
        
        # Daily reset check
        self._check_daily_reset(tick_data['timestamp'])
        
        # Check if we can trade
        if not self._can_trade():
            return
        
        # Check entry conditions
        if symbol not in self.positions:
            entry_signal = self.check_entry_conditions(symbol, tick_data)
            if entry_signal:
                self.emit_signal(entry_signal)
        
        # Manage existing positions
        if symbol in self.positions:
            # Update highest/lowest
            self._update_price_extremes(symbol, tick_data)
            
            # Check exit conditions
            exit_signal = self.check_exit_conditions(symbol, tick_data)
            if exit_signal:
                self.emit_signal(exit_signal)
    
    def _check_daily_reset(self, timestamp):
        """Reset daily counters at start of day."""
        current_date = timestamp.date()
        
        if self.last_reset_date != current_date:
            self.daily_pnl = 0
            self.daily_trades = 0
            self.consec_losses = 0
            self.last_reset_date = current_date
            self.logger.info(f"📅 Daily reset: {current_date}")
    
    def _can_trade(self) -> bool:
        """Check if trading is allowed."""
        # Max positions check
        if len(self.positions) >= self.max_positions:
            return False
        
        # Daily loss limit check
        if self.daily_pnl <= -self.daily_loss_limit:
            return False
        
        # Consecutive losses check
        if self.consec_losses >= self.max_consec_losses:
            return False
        
        return True
    
    def check_entry_conditions(self, symbol: str, tick_data: Dict) -> Optional[Dict]:
        """
        Check for LONG or SHORT entry signals.
        Returns signal dict or None.
        """
        price = tick_data.get('price', tick_data.get('close'))
        volume = tick_data.get('volume', 0)
        
        # Get indicators
        if symbol not in self.indicator_manager.indicators:
            return None
        
        ti = self.indicator_manager.indicators[symbol]
        
        ema9 = ti.calculate_ema(self.ema9)
        ema21 = ti.calculate_ema(self.ema21)
        ema50 = ti.calculate_ema(self.ema50_15m)
        ema200 = ti.calculate_ema(self.ema200_1h)
        rsi = ti.calculate_rsi(self.rsi_period)
        atr = ti.calculate_atr(self.atr_period)
        macd_data = ti.calculate_macd()
        
        # Volume MA
        if len(ti.volumes) >= self.volume_period:
            import numpy as np
            volume_ma = np.mean(list(ti.volumes)[-self.volume_period:])
        else:
            volume_ma = 0
        
        # Check if we have all data
        if None in [ema9, ema21, ema50, ema200, rsi, atr] or not macd_data:
            return None
        
        macd_line = macd_data['macd']
        macd_signal = macd_data['signal']
        macd_hist = macd_data['histogram']
        
        # Check LONG signal
        long_signal = self._check_long_signal(
            price, ema9, ema21, ema50, ema200, rsi, 
            macd_line, macd_signal, macd_hist, volume, volume_ma, atr
        )
        
        if long_signal:
            return self._create_entry_signal(symbol, tick_data, 'LONG', atr)
        
        # Check SHORT signal
        short_signal = self._check_short_signal(
            price, ema9, ema21, ema50, ema200, rsi,
            macd_line, macd_signal, macd_hist, volume, volume_ma, atr
        )
        
        if short_signal:
            return self._create_entry_signal(symbol, tick_data, 'SHORT', atr)
        
        return None
    
    def _check_long_signal(self, price, ema9, ema21, ema50, ema200, rsi,
                           macd_line, macd_signal, macd_hist, volume, volume_ma, atr) -> bool:
        """Check if all LONG conditions are met."""
        return (
            # Trend aligned
            price > ema21 and
            ema9 > ema21 and
            price > ema50 and
            price > ema200 and
            
            # Momentum good
            self.rsi_long_min < rsi < self.rsi_long_max and
            macd_line > macd_signal and
            macd_hist > 0 and
            
            # Volume high
            (volume_ma == 0 or volume > volume_ma) and
            
            # Price near EMA9
            abs(price - ema9) < (atr * self.price_ema_dist) and
            price > ema9
        )
    
    def _check_short_signal(self, price, ema9, ema21, ema50, ema200, rsi,
                            macd_line, macd_signal, macd_hist, volume, volume_ma, atr) -> bool:
        """Check if all SHORT conditions are met."""
        return (
            # Trend aligned
            price < ema21 and
            ema9 < ema21 and
            price < ema50 and
            price < ema200 and
            
            # Momentum good
            self.rsi_short_min < rsi < self.rsi_short_max and
            macd_line < macd_signal and
            macd_hist < 0 and
            
            # Volume high
            (volume_ma == 0 or volume > volume_ma) and
            
            # Price near EMA9
            abs(price - ema9) < (atr * self.price_ema_dist) and
            price < ema9
        )
    
    def _create_entry_signal(self, symbol: str, tick_data: Dict, direction: str, atr: float) -> Dict:
        """Create entry signal with SL and TP levels."""
        price = tick_data.get('price', tick_data.get('close'))
        
        if direction == 'LONG':
            sl = price - (atr * self.atr_sl_mult)
            tp1 = price + (atr * self.atr_tp1_mult)
            tp2 = price + (atr * self.atr_tp2_mult)
        else:  # SHORT
            sl = price + (atr * self.atr_sl_mult)
            tp1 = price - (atr * self.atr_tp1_mult)
            tp2 = price - (atr * self.atr_tp2_mult)
        
        # Calculate position size (1% risk)
        capital = 100000  # TODO: Get from broker
        risk_amount = capital * self.risk_per_trade
        stop_distance = abs(price - sl)
        
        if stop_distance > 0:
            quantity = max(1, int(risk_amount / stop_distance))
        else:
            quantity = 1
        
        # Limit position size
        max_position_value = 10000
        max_qty = int(max_position_value / price) if price > 0 else 1
        quantity = min(quantity, max_qty)
        
        # Store position data
        self.position_direction[symbol] = direction
        self.position_stops[symbol] = sl
        self.position_tp1[symbol] = tp1
        self.position_tp2[symbol] = tp2
        self.position_atr[symbol] = atr
        self.position_highest[symbol] = price
        self.position_lowest[symbol] = price
        self.breakeven_moved[symbol] = False
        self.trailing_active[symbol] = False
        
        return {
            'strategy_id': self.strategy_id,
            'action': 'BUY' if direction == 'LONG' else 'SELL',
            'symbol': symbol,
            'price': price,
            'quantity': quantity,
            'timestamp': tick_data['timestamp'],
            'reason': f'{direction} Signal: EMA aligned, MACD bullish, RSI good',
            'indicators': {
                'direction': direction,
                'sl': sl,
                'tp1': tp1,
                'tp2': tp2,
                'atr': atr
            }
        }
    
    def _update_price_extremes(self, symbol: str, tick_data: Dict):
        """Update highest/lowest price since entry."""
        price = tick_data.get('price', tick_data.get('close'))
        
        if symbol in self.position_highest:
            self.position_highest[symbol] = max(self.position_highest[symbol], price)
        
        if symbol in self.position_lowest:
            self.position_lowest[symbol] = min(self.position_lowest[symbol], price)
    
    def check_exit_conditions(self, symbol: str, tick_data: Dict) -> Optional[Dict]:
        """Check exit conditions for open position."""
        if symbol not in self.positions:
            return None
        
        pos = self.positions[symbol]
        price = tick_data.get('price', tick_data.get('close'))
        entry_price = pos['entry_price']
        direction = self.position_direction.get(symbol, 'LONG')
        atr = self.position_atr.get(symbol, 0)
        
        # Calculate profit in ATR
        if direction == 'LONG':
            profit_atr = (price - entry_price) / atr if atr > 0 else 0
        else:  # SHORT
            profit_atr = (entry_price - price) / atr if atr > 0 else 0
        
        # 1. Check TP1
        if symbol in self.position_tp1:
            tp1 = self.position_tp1[symbol]
            if (direction == 'LONG' and price >= tp1) or (direction == 'SHORT' and price <= tp1):
                # Close 50% at TP1
                qty_to_close = max(1, int(pos['quantity'] * self.tp1_pct))
                return self._create_exit_signal(symbol, tick_data, qty_to_close, f'TP1 hit @ {tp1:.2f}')
        
        # 2. Check TP2
        if symbol in self.position_tp2:
            tp2 = self.position_tp2[symbol]
            if (direction == 'LONG' and price >= tp2) or (direction == 'SHORT' and price <= tp2):
                # Close 30% at TP2
                qty_to_close = max(1, int(pos['quantity'] * self.tp2_pct))
                return self._create_exit_signal(symbol, tick_data, qty_to_close, f'TP2 hit @ {tp2:.2f}')
        
        # 3. Move to breakeven at 1 ATR profit
        if not self.breakeven_moved.get(symbol, False) and profit_atr >= self.breakeven_atr:
            self.position_stops[symbol] = entry_price
            self.breakeven_moved[symbol] = True
            self.logger.info(f"🔒 Breakeven moved for {symbol} @ {entry_price:.2f}")
        
        # 4. Start trailing at 1.5 ATR profit
        if profit_atr >= self.trailing_start_atr:
            self._update_trailing_stop(symbol, price, direction, atr, entry_price)
        
        # 5. Check stop loss
        if symbol in self.position_stops:
            sl = self.position_stops[symbol]
            if (direction == 'LONG' and price <= sl) or (direction == 'SHORT' and price >= sl):
                return self._create_exit_signal(symbol, tick_data, pos['quantity'], f'Stop loss @ {sl:.2f}')
        
        return None
    
    def _update_trailing_stop(self, symbol: str, price: float, direction: str, atr: float, entry_price: float):
        """Update trailing stop based on highest/lowest price."""
        if direction == 'LONG':
            highest = self.position_highest.get(symbol, price)
            new_sl = highest - (atr * self.atr_trail_mult)
            new_sl = max(new_sl, entry_price)  # Never below entry
            
            current_sl = self.position_stops.get(symbol, 0)
            if new_sl > current_sl:
                self.position_stops[symbol] = new_sl
                if not self.trailing_active.get(symbol, False):
                    self.trailing_active[symbol] = True
                    self.logger.info(f"🎯 Trailing SL activated for {symbol} @ {new_sl:.2f}")
        
        else:  # SHORT
            lowest = self.position_lowest.get(symbol, price)
            new_sl = lowest + (atr * self.atr_trail_mult)
            new_sl = min(new_sl, entry_price)  # Never above entry
            
            current_sl = self.position_stops.get(symbol, 999999)
            if new_sl < current_sl:
                self.position_stops[symbol] = new_sl
                if not self.trailing_active.get(symbol, False):
                    self.trailing_active[symbol] = True
                    self.logger.info(f"🎯 Trailing SL activated for {symbol} @ {new_sl:.2f}")
    
    def _create_exit_signal(self, symbol: str, tick_data: Dict, quantity: int, reason: str) -> Dict:
        """Create exit signal."""
        price = tick_data.get('price', tick_data.get('close'))
        direction = self.position_direction.get(symbol, 'LONG')
        
        # Cleanup if closing full position
        if quantity >= self.positions[symbol]['quantity']:
            self._cleanup_position_data(symbol)
        
        return {
            'strategy_id': self.strategy_id,
            'action': 'SELL' if direction == 'LONG' else 'BUY',
            'symbol': symbol,
            'price': price,
            'quantity': quantity,
            'timestamp': tick_data['timestamp'],
            'reason': reason,
            'indicators': {}
        }
    
    def _cleanup_position_data(self, symbol: str):
        """Clean up position tracking data."""
        for d in [self.position_direction, self.position_stops, self.position_tp1, 
                  self.position_tp2, self.position_atr, self.position_highest,
                  self.position_lowest, self.breakeven_moved, self.trailing_active]:
            if symbol in d:
                del d[symbol]
    
    def on_candle_close(self, candle_data: Dict, timeframe: str) -> None:
        """Not used in tick-by-tick strategy."""
        pass
