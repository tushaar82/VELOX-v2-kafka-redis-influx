"""Strategy adapters."""

from .base import StrategyAdapter
from .rsi_momentum import RSIMomentumStrategy
from .mtf_atr_strategy import MultiTimeframeATRStrategy
from .scalping_mtf_atr import ScalpingMTFATRStrategy
from .supertrend import SupertrendStrategy

__all__ = ['RSIMomentumStrategy', 'MultiTimeframeATRStrategy', 'ScalpingMTFATRStrategy', 'SupertrendStrategy']
