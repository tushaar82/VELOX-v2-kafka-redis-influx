"""
Opening Range Breakout (ORB) Strategy.

This is one of the most popular and profitable intraday strategies in Indian markets.
It captures strong directional moves after the initial market consolidation.

Logic:
1. Define opening range: First 15-30 minutes of trading (9:15-9:45 AM)
2. Track high and low of this range
3. BUY when price breaks above range high with volume confirmation
4. SELL when price breaks below range low (or exit LONG position)
5. Exit at target (2-3x range) or stop loss (range low for LONG)

Key Success Factors:
- High volume on breakout (1.5x average)
- Clear range formation (not too tight)
- Strong directional move post-breakout
- Works best on volatile, liquid stocks
"""

from typing import Dict, Optional
from datetime import datetime, timedelta
import numpy as np

from .base import StrategyAdapter
from ...utils.indicators import IndicatorManager
from ...utils.logging_config import get_logger


class OpeningRangeBreakoutStrategy(StrategyAdapter):
    """
    Opening Range Breakout Strategy for Indian intraday trading.

    Best for: Trending days, volatile stocks, high liquidity
    Win Rate: ~55-65% with proper filters
    Risk/Reward: 1:2 to 1:3
    """

    def __init__(self, strategy_id: str, symbols: list, config: Dict):
        """Initialize Opening Range Breakout strategy."""
        super().__init__(strategy_id, symbols, config)

        # Strategy parameters
        self.orb_period_minutes = config.get('orb_period_minutes', 15)  # 15-minute opening range
        self.breakout_confirmation_pct = config.get('breakout_confirmation_pct', 0.1)  # 0.1% above high
        self.volume_multiplier = config.get('volume_multiplier', 1.5)  # 1.5x average volume
        self.risk_reward_ratio = config.get('risk_reward_ratio', 2.0)  # 1:2 R:R

        # Position sizing
        self.position_size_pct = config.get('position_size_pct', 0.1)  # 10% of capital
        self.max_position_size = config.get('max_position_size', 15000)

        # Range tracking per symbol
        self.opening_ranges = {}  # {symbol: {'high': float, 'low': float, 'confirmed': bool}}
        self.range_start_time = {}  # {symbol: datetime}
        self.session_high_low = {}  # Track session extremes
        self.volume_history = {}  # Track volume for confirmation

        # Indicator manager
        self.indicator_manager = IndicatorManager()

        # Set warmup requirements
        self.warmup_candles_required = 50

        # Logger
        self.logger = get_logger('strategy', strategy_id)

        self.logger.info(
            f"OpeningRangeBreakoutStrategy initialized: "
            f"ORB_period={self.orb_period_minutes}min, "
            f"Volume_mult={self.volume_multiplier}x, R:R={self.risk_reward_ratio}"
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

    def on_tick(self, tick_data: Dict) -> None:
        """Process a market tick."""
        symbol = tick_data.get('symbol')
        if symbol not in self.symbols:
            return

        timestamp = tick_data.get('timestamp', datetime.now())

        # Initialize range tracking
        if symbol not in self.range_start_time:
            self.range_start_time[symbol] = timestamp
            self.opening_ranges[symbol] = {
                'high': float('-inf'),
                'low': float('inf'),
                'confirmed': False,
                'avg_volume': 0
            }
            self.session_high_low[symbol] = {
                'high': float('-inf'),
                'low': float('inf')
            }
            self.volume_history[symbol] = []

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

        # Update session high/low
        price = tick_data.get('close', tick_data.get('price'))
        high = tick_data.get('high', price)
        low = tick_data.get('low', price)
        volume = tick_data.get('volume', 0)

        self.session_high_low[symbol]['high'] = max(
            self.session_high_low[symbol]['high'], high
        )
        self.session_high_low[symbol]['low'] = min(
            self.session_high_low[symbol]['low'], low
        )

        # Track volume
        if volume > 0:
            self.volume_history[symbol].append(volume)
            # Keep last 20 volume samples
            if len(self.volume_history[symbol]) > 20:
                self.volume_history[symbol].pop(0)

        # Calculate elapsed time
        elapsed_minutes = (timestamp - self.range_start_time[symbol]).total_seconds() / 60

        # Build opening range during first N minutes
        if elapsed_minutes <= self.orb_period_minutes:
            self.opening_ranges[symbol]['high'] = max(
                self.opening_ranges[symbol]['high'], high
            )
            self.opening_ranges[symbol]['low'] = min(
                self.opening_ranges[symbol]['low'], low
            )

        # Confirm range after ORB period
        elif not self.opening_ranges[symbol]['confirmed']:
            # Calculate average volume during range period
            if self.volume_history[symbol]:
                self.opening_ranges[symbol]['avg_volume'] = np.mean(self.volume_history[symbol])

            orb_high = self.opening_ranges[symbol]['high']
            orb_low = self.opening_ranges[symbol]['low']
            orb_range = orb_high - orb_low

            # Validate range (not too tight, not too wide)
            orb_range_pct = (orb_range / orb_low) * 100
            if 0.3 <= orb_range_pct <= 3.0:  # Range between 0.3% and 3%
                self.opening_ranges[symbol]['confirmed'] = True
                self.logger.info(
                    f"[{symbol}] Opening Range Confirmed\n"
                    f"  ├─ High: {orb_high:.2f}\n"
                    f"  ├─ Low: {orb_low:.2f}\n"
                    f"  ├─ Range: {orb_range:.2f} ({orb_range_pct:.2f}%)\n"
                    f"  └─ Avg Volume: {self.opening_ranges[symbol]['avg_volume']:.0f}"
                )
            else:
                self.logger.warning(
                    f"[{symbol}] ORB range invalid: {orb_range_pct:.2f}% "
                    f"(expected 0.3%-3.0%)"
                )

        # Only generate signals if warmed up and range is confirmed
        if not self.is_warmed_up or not self.opening_ranges[symbol]['confirmed']:
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

        LONG Entry: Price breaks above ORB high with volume confirmation
        """
        if not self.is_warmed_up:
            return None

        if symbol in self.positions:
            return None

        if not self.opening_ranges[symbol]['confirmed']:
            return None

        close = tick_data.get('close', tick_data.get('price'))
        volume = tick_data.get('volume', 0)

        orb_high = self.opening_ranges[symbol]['high']
        orb_low = self.opening_ranges[symbol]['low']
        orb_range = orb_high - orb_low
        avg_volume = self.opening_ranges[symbol]['avg_volume']

        # Breakout confirmation: price above high by small margin
        breakout_level = orb_high * (1 + self.breakout_confirmation_pct / 100)

        # Volume confirmation: current volume > threshold * average
        volume_confirmed = volume >= (avg_volume * self.volume_multiplier) if avg_volume > 0 else True

        # LONG ENTRY: Bullish breakout
        if close >= breakout_level and volume_confirmed:
            # Calculate stop loss and target
            stop_loss = orb_low
            target = close + (orb_range * self.risk_reward_ratio)

            self.logger.info(
                f"[{symbol}] BUY SIGNAL: ORB Breakout\n"
                f"  ├─ Price: {close:.2f}, ORB High: {orb_high:.2f}\n"
                f"  ├─ Breakout Level: {breakout_level:.2f}\n"
                f"  ├─ Volume: {volume:.0f} (Avg: {avg_volume:.0f}, Mult: {self.volume_multiplier}x)\n"
                f"  ├─ Stop Loss: {stop_loss:.2f}\n"
                f"  └─ Target: {target:.2f} (R:R = 1:{self.risk_reward_ratio})"
            )

            # Calculate quantity based on risk
            risk_per_share = close - stop_loss
            if risk_per_share <= 0:
                risk_per_share = close * 0.015  # Default 1.5% risk

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
                'reason': f"ORB breakout @ {close:.2f} (ORB: {orb_low:.2f}-{orb_high:.2f})",
                'metadata': {
                    'orb_high': orb_high,
                    'orb_low': orb_low,
                    'orb_range': orb_range,
                    'stop_loss': stop_loss,
                    'target': target,
                    'entry_type': 'breakout'
                }
            }

        return None

    def check_exit_conditions(self, symbol: str, tick_data: Dict) -> Optional[Dict]:
        """
        Check if exit conditions are met.

        EXIT: Target hit OR Stop loss hit OR Price breaks below ORB low
        """
        if not self.is_warmed_up:
            return None

        if symbol not in self.positions:
            return None

        pos = self.positions[symbol]
        close = tick_data.get('close', tick_data.get('price'))
        entry_price = pos['entry_price']

        metadata = pos.get('metadata', {})
        stop_loss = metadata.get('stop_loss', entry_price * 0.98)
        target = metadata.get('target', entry_price * 1.02)
        orb_low = metadata.get('orb_low', stop_loss)

        # Calculate P&L
        pnl_pct = ((close - entry_price) / entry_price) * 100

        reason = None

        # Exit 1: Target achieved
        if close >= target:
            reason = f"Target achieved: {close:.2f} >= {target:.2f} (P&L: {pnl_pct:+.2f}%)"

        # Exit 2: Stop Loss hit
        elif close <= stop_loss:
            reason = f"Stop Loss hit: {close:.2f} <= {stop_loss:.2f} (P&L: {pnl_pct:+.2f}%)"

        # Exit 3: Price breaks below ORB low (range breakdown)
        elif close < orb_low:
            reason = f"ORB range breakdown: {close:.2f} < {orb_low:.2f} (P&L: {pnl_pct:+.2f}%)"

        if reason:
            self.logger.info(
                f"[{symbol}] EXIT SIGNAL: {reason}\n"
                f"  ├─ Entry: {entry_price:.2f}, Exit: {close:.2f}\n"
                f"  └─ P&L: {pnl_pct:+.2f}%"
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
                'orb_period_minutes': self.orb_period_minutes,
                'volume_multiplier': self.volume_multiplier,
                'risk_reward_ratio': self.risk_reward_ratio
            },
            'opening_ranges': {
                symbol: {
                    'high': data['high'] if data['high'] != float('-inf') else None,
                    'low': data['low'] if data['low'] != float('inf') else None,
                    'confirmed': data['confirmed']
                }
                for symbol, data in self.opening_ranges.items()
            }
        })
        return status
