"""
Strategy Factory for dynamic strategy loading.
"""

from typing import Dict, Optional
from .base import StrategyAdapter
from .rsi_momentum import RSIMomentumStrategy
from .supertrend import SupertrendStrategy
from .mtf_atr_strategy import MultiTimeframeATRStrategy
from .scalping_mtf_atr import ScalpingMTFATRStrategy
from .vwap_rsi_meanreversion import VWAPRSIMeanReversionStrategy
from .opening_range_breakout import OpeningRangeBreakoutStrategy
from .ema_macd_momentum import EMAMACDMomentumStrategy
from .supertrend_adx import SupertrendADXStrategy
from ...utils.logging_config import get_logger


# Strategy registry
STRATEGY_REGISTRY = {
    # Original strategies
    'RSIMomentumStrategy': RSIMomentumStrategy,
    'SupertrendStrategy': SupertrendStrategy,
    'MultiTimeframeATRStrategy': MultiTimeframeATRStrategy,
    'ScalpingMTFATRStrategy': ScalpingMTFATRStrategy,

    # New professional intraday strategies
    'VWAPRSIMeanReversionStrategy': VWAPRSIMeanReversionStrategy,
    'OpeningRangeBreakoutStrategy': OpeningRangeBreakoutStrategy,
    'EMAMACDMomentumStrategy': EMAMACDMomentumStrategy,
    'SupertrendADXStrategy': SupertrendADXStrategy,
}


class StrategyFactory:
    """Factory for creating strategy instances."""

    def __init__(self):
        """Initialize strategy factory."""
        self.logger = get_logger('strategy_factory')
        self.logger.info(f"Strategy factory initialized with {len(STRATEGY_REGISTRY)} strategies")

    def create_strategy(
        self,
        strategy_class: str,
        strategy_id: str,
        symbols: list,
        params: Dict
    ) -> Optional[StrategyAdapter]:
        """
        Create a strategy instance.

        Args:
            strategy_class: Class name of the strategy
            strategy_id: Unique strategy ID
            symbols: List of symbols to trade
            params: Strategy parameters

        Returns:
            Strategy instance or None if not found
        """
        if strategy_class not in STRATEGY_REGISTRY:
            self.logger.error(
                f"Unknown strategy class: {strategy_class}. "
                f"Available: {list(STRATEGY_REGISTRY.keys())}"
            )
            return None

        try:
            strategy_cls = STRATEGY_REGISTRY[strategy_class]
            strategy = strategy_cls(strategy_id, symbols, params)
            strategy.initialize()

            self.logger.info(
                f"Created strategy: {strategy_id} ({strategy_class}) "
                f"for {len(symbols)} symbols"
            )

            return strategy

        except Exception as e:
            self.logger.error(
                f"Failed to create strategy {strategy_id} ({strategy_class}): {e}",
                exc_info=True
            )
            return None

    def get_available_strategies(self) -> list:
        """
        Get list of available strategy classes.

        Returns:
            List of strategy class names
        """
        return list(STRATEGY_REGISTRY.keys())

    def register_strategy(self, name: str, strategy_class):
        """
        Register a new strategy class.

        Args:
            name: Strategy class name
            strategy_class: Strategy class
        """
        STRATEGY_REGISTRY[name] = strategy_class
        self.logger.info(f"Registered new strategy: {name}")


def register_strategy(name: str):
    """
    Decorator to register a strategy class.

    Usage:
        @register_strategy('MyStrategy')
        class MyStrategy(StrategyAdapter):
            pass
    """
    def decorator(cls):
        STRATEGY_REGISTRY[name] = cls
        return cls
    return decorator
