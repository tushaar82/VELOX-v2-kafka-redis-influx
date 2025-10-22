"""
EMA Crossover with MACD Confirmation Strategy.

This momentum strategy combines two powerful trend indicators to capture
strong directional moves in the market. It works best on trending days
in Indian markets.

Entry Logic:
- BUY: 9 EMA crosses above 21 EMA AND MACD histogram > 0
- SELL: 9 EMA crosses below 21 EMA OR MACD turns negative

Exit Logic:
- Opposite crossover
- MACD histogram turns negative
- Trailing stop loss (ATR-based)
- Target: 2% profit or 1% stop loss

Key Success Factors:
- Clear trend direction
- MACD confirmation reduces false signals
- Works well mid-day (10:30 AM - 2:30 PM)
- Best on liquid, momentum stocks
"""

from typing import Dict, Optional
from datetime import datetime, timedelta
import numpy as np

from .base import StrategyAdapter
from ...utils.indicators import IndicatorManager
from ...utils.logging_config import get_logger


class EMAMACDMomentumStrategy(StrategyAdapter):
    """
    EMA Crossover + MACD Momentum Strategy for Indian markets.

    Best for: Trending days, momentum stocks, clear directional moves
    Win Rate: ~50-60% with proper filtering
    Risk/Reward: 1:2
    """

    def __init__(self, strategy_id: str, symbols: list, config: Dict):
        """Initialize EMA MACD Momentum strategy."""
        super().__init__(strategy_id, symbols, config)

        # EMA parameters
        self.fast_ema_period = config.get('fast_ema_period', 9)
        self.slow_ema_period = config.get('slow_ema_period', 21)

        # MACD parameters
        self.macd_fast = config.get('macd_fast', 12)
        self.macd_slow = config.get('macd_slow', 26)
        self.macd_signal = config.get('macd_signal', 9)

        # Exit parameters
        self.target_pct = config.get('target_pct', 2.0)  # 2% target
        self.stop_loss_pct = config.get('stop_loss_pct', 1.0)  # 1% SL
        self.trailing_sl_atr_mult = config.get('trailing_sl_atr_mult', 1.5)  # 1.5x ATR
        self.atr_period = config.get('atr_period', 14)

        # Volume and trend filters
        self.min_volume = config.get('min_volume', 100)
        self.min_ema_separation_pct = config.get('min_ema_separation_pct', 0.2)  # 0.2% separation

        # Position sizing
        self.position_size_pct = config.get('position_size_pct', 0.08)  # 8% of capital
        self.max_position_size = config.get('max_position_size', 12000)

        # Track previous EMA values for crossover detection
        self.prev_ema_fast = {}
        self.prev_ema_slow = {}
        self.prev_macd = {}

        # Indicator manager
        self.indicator_manager = IndicatorManager()

        # Set warmup requirements
        self.warmup_candles_required = max(self.slow_ema_period, self.macd_slow) + 10

        # Logger
        self.logger = get_logger('strategy', strategy_id)

        self.logger.info(
            f"EMAMACDMomentumStrategy initialized: "
            f"EMA={self.fast_ema_period}/{self.slow_ema_period}, "
            f"MACD={self.macd_fast}/{self.macd_slow}/{self.macd_signal}, "
            f"Target/SL={self.target_pct}%/{self.stop_loss_pct}%"
        )

    def initialize(self) -> None:
        """Initialize strategy."""
        self.logger.info(f"Strategy {self.strategy_id} initialized for symbols: {self.symbols}")

    def on_candle_close(self, candle_data: Dict, timeframe: str) -> None:
        """Process candle close event."""
        pass

    def on_warmup_candle(self, candle_data: Dict, timeframe: str) -> None:
        """Process historical candle during warmup phase."""
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

            # Update EMA and MACD history during warmup
            self._update_indicator_history(symbol)

    def on_candle_complete(self, candle_data: Dict, timeframe: str) -> None:
        """Process completed candle during live trading."""
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

            # Update indicator history
            self._update_indicator_history(symbol)

    def _update_indicator_history(self, symbol: str):
        """Update EMA and MACD history for crossover detection."""
        if symbol not in self.indicator_manager.indicators:
            return

        tech_indicators = self.indicator_manager.indicators[symbol]

        # Calculate current EMAs
        ema_fast = tech_indicators.calculate_ema(self.fast_ema_period)
        ema_slow = tech_indicators.calculate_ema(self.slow_ema_period)
        macd_data = tech_indicators.calculate_macd(
            self.macd_fast, self.macd_slow, self.macd_signal
        )

        # Store current values as previous for next iteration
        if ema_fast is not None:
            self.prev_ema_fast[symbol] = ema_fast
        if ema_slow is not None:
            self.prev_ema_slow[symbol] = ema_slow
        if macd_data is not None:
            self.prev_macd[symbol] = macd_data

    def on_tick(self, tick_data: Dict) -> None:
        """Process a market tick."""
        symbol = tick_data.get('symbol')
        if symbol not in self.symbols:
            return

        # Update forming candle
        if hasattr(self.indicator_manager, 'update_forming_candle'):
            self.indicator_manager.update_forming_candle(
                symbol=symbol,
                high=tick_data.get('high', tick_data.get('price')),
                low=tick_data.get('low', tick_data.get('price')),
                close=tick_data.get('close', tick_data.get('price')),
                volume=tick_data.get('volume', 0),
                timestamp=tick_data.get('timestamp')
            )

        # Only generate signals if warmed up
        if not self.is_warmed_up:
            return

        # Check for entry/exit signals
        if symbol not in self.positions:
            signal = self.check_entry_conditions(symbol, tick_data)
            if signal:
                self.signals.append(signal)
        else:
            signal = self.check_exit_conditions(symbol, tick_data)
            if signal:
                self.signals.append(signal)

    def check_entry_conditions(self, symbol: str, tick_data: Dict) -> Optional[Dict]:
        """
        Check if entry conditions are met.

        LONG Entry: 9 EMA crosses above 21 EMA AND MACD histogram > 0
        """
        if not self.is_warmed_up:
            return None

        if symbol in self.positions:
            return None

        close = tick_data.get('close', tick_data.get('price'))
        volume = tick_data.get('volume', 0)

        # Volume filter
        if volume < self.min_volume:
            return None

        # Get indicators
        if symbol not in self.indicator_manager.indicators:
            return None

        tech_indicators = self.indicator_manager.indicators[symbol]

        # Calculate current EMAs
        ema_fast = tech_indicators.calculate_ema(self.fast_ema_period)
        ema_slow = tech_indicators.calculate_ema(self.slow_ema_period)
        macd_data = tech_indicators.calculate_macd(
            self.macd_fast, self.macd_slow, self.macd_signal
        )
        atr = tech_indicators.calculate_atr(self.atr_period)

        if ema_fast is None or ema_slow is None or macd_data is None:
            return None

        # Get previous values
        prev_fast = self.prev_ema_fast.get(symbol)
        prev_slow = self.prev_ema_slow.get(symbol)
        prev_macd_hist = self.prev_macd.get(symbol, {}).get('histogram', None)

        if prev_fast is None or prev_slow is None or prev_macd_hist is None:
            return None

        macd_histogram = macd_data['histogram']

        # Calculate EMA separation
        ema_separation_pct = abs((ema_fast - ema_slow) / ema_slow) * 100

        # LONG ENTRY: Bullish EMA crossover + Positive MACD
        # Crossover: prev_fast <= prev_slow AND current_fast > current_slow
        bullish_crossover = (prev_fast <= prev_slow) and (ema_fast > ema_slow)
        macd_positive = macd_histogram > 0
        sufficient_separation = ema_separation_pct >= self.min_ema_separation_pct

        if bullish_crossover and macd_positive and sufficient_separation:
            # Calculate stop loss and target
            stop_loss = close * (1 - self.stop_loss_pct / 100)
            target = close * (1 + self.target_pct / 100)

            # ATR-based trailing SL (if available)
            if atr:
                trailing_sl = close - (atr * self.trailing_sl_atr_mult)
                stop_loss = max(stop_loss, trailing_sl)

            self.logger.info(
                f"[{symbol}] BUY SIGNAL: EMA Crossover + MACD Confirmation\n"
                f"  ├─ Price: {close:.2f}\n"
                f"  ├─ Fast EMA({self.fast_ema_period}): {ema_fast:.2f}\n"
                f"  ├─ Slow EMA({self.slow_ema_period}): {ema_slow:.2f}\n"
                f"  ├─ EMA Separation: {ema_separation_pct:.2f}%\n"
                f"  ├─ MACD Histogram: {macd_histogram:.4f} (Positive)\n"
                f"  ├─ Stop Loss: {stop_loss:.2f}\n"
                f"  └─ Target: {target:.2f}"
            )

            # Calculate quantity
            quantity = int(self.max_position_size / close)
            if quantity < 1:
                quantity = 1

            return {
                'strategy_id': self.strategy_id,
                'action': 'BUY',
                'symbol': symbol,
                'price': close,
                'quantity': quantity,
                'timestamp': tick_data.get('timestamp'),
                'reason': f"EMA crossover + MACD confirmation @ {close:.2f}",
                'metadata': {
                    'ema_fast': ema_fast,
                    'ema_slow': ema_slow,
                    'macd_histogram': macd_histogram,
                    'stop_loss': stop_loss,
                    'target': target,
                    'atr': atr
                }
            }

        return None

    def check_exit_conditions(self, symbol: str, tick_data: Dict) -> Optional[Dict]:
        """
        Check if exit conditions are met.

        EXIT: Target hit OR SL hit OR Bearish crossover OR MACD negative
        """
        if not self.is_warmed_up:
            return None

        if symbol not in self.positions:
            return None

        pos = self.positions[symbol]
        close = tick_data.get('close', tick_data.get('price'))
        entry_price = pos['entry_price']

        metadata = pos.get('metadata', {})
        stop_loss = metadata.get('stop_loss', entry_price * 0.99)
        target = metadata.get('target', entry_price * 1.02)
        atr = metadata.get('atr')

        # Calculate P&L
        pnl_pct = ((close - entry_price) / entry_price) * 100

        # Get current indicators
        if symbol not in self.indicator_manager.indicators:
            return None

        tech_indicators = self.indicator_manager.indicators[symbol]

        ema_fast = tech_indicators.calculate_ema(self.fast_ema_period)
        ema_slow = tech_indicators.calculate_ema(self.slow_ema_period)
        macd_data = tech_indicators.calculate_macd(
            self.macd_fast, self.macd_slow, self.macd_signal
        )

        if ema_fast is None or ema_slow is None or macd_data is None:
            return None

        # Get previous values
        prev_fast = self.prev_ema_fast.get(symbol)
        prev_slow = self.prev_ema_slow.get(symbol)

        macd_histogram = macd_data['histogram']

        reason = None

        # Exit 1: Target achieved
        if close >= target:
            reason = f"Target achieved: {close:.2f} >= {target:.2f} (P&L: {pnl_pct:+.2f}%)"

        # Exit 2: Stop Loss hit
        elif close <= stop_loss:
            reason = f"Stop Loss hit: {close:.2f} <= {stop_loss:.2f} (P&L: {pnl_pct:+.2f}%)"

        # Exit 3: Bearish EMA crossover
        elif prev_fast and prev_slow:
            bearish_crossover = (prev_fast >= prev_slow) and (ema_fast < ema_slow)
            if bearish_crossover:
                reason = f"Bearish EMA crossover (P&L: {pnl_pct:+.2f}%)"

        # Exit 4: MACD turns negative
        elif macd_histogram < 0:
            reason = f"MACD histogram negative: {macd_histogram:.4f} (P&L: {pnl_pct:+.2f}%)"

        # Update trailing stop loss if in profit
        elif atr and pnl_pct > 0.5:  # Update SL when 0.5%+ in profit
            new_trailing_sl = close - (atr * self.trailing_sl_atr_mult)
            if new_trailing_sl > stop_loss:
                # Update position metadata with new SL
                pos['metadata']['stop_loss'] = new_trailing_sl
                self.logger.debug(
                    f"[{symbol}] Trailing SL updated: {stop_loss:.2f} -> {new_trailing_sl:.2f}"
                )

        if reason:
            self.logger.info(
                f"[{symbol}] EXIT SIGNAL: {reason}\n"
                f"  ├─ Entry: {entry_price:.2f}, Exit: {close:.2f}\n"
                f"  ├─ Fast EMA: {ema_fast:.2f}, Slow EMA: {ema_slow:.2f}\n"
                f"  └─ MACD Histogram: {macd_histogram:.4f}"
            )

            return {
                'strategy_id': self.strategy_id,
                'action': 'SELL',
                'symbol': symbol,
                'price': close,
                'quantity': pos['quantity'],
                'timestamp': tick_data.get('timestamp'),
                'reason': reason
            }

        return None

    def get_status(self) -> Dict:
        """Get strategy status."""
        status = super().get_status()
        status.update({
            'parameters': {
                'fast_ema': self.fast_ema_period,
                'slow_ema': self.slow_ema_period,
                'macd': f"{self.macd_fast}/{self.macd_slow}/{self.macd_signal}",
                'target_pct': self.target_pct,
                'stop_loss_pct': self.stop_loss_pct
            }
        })
        return status
