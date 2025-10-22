"""
Base abstract class for trading strategies.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from datetime import datetime


class StrategyAdapter(ABC):
    """Abstract base class for trading strategies."""
    
    def __init__(self, strategy_id: str, symbols: List[str], config: Dict):
        """
        Initialize strategy.
        
        Args:
            strategy_id: Unique strategy identifier
            symbols: List of symbols to trade
            config: Strategy configuration
        """
        self.strategy_id = strategy_id
        self.symbols = symbols
        self.config = config
        self.positions = {}  # symbol -> position_info
        self.signals = []  # List of generated signals
        self.is_active = True
        self.is_warmed_up = False  # Warmup status flag
        self.warmup_candles_required = 200  # Default warmup period
    
    @abstractmethod
    def initialize(self) -> None:
        """
        Initialize strategy.
        Called once before strategy starts.
        """
        pass
    
    @abstractmethod
    def on_tick(self, tick_data: Dict) -> None:
        """
        Process a market tick.
        
        NOTE: Strategies should check self.is_warmed_up before generating signals.
        During warmup phase, only update indicators, do not generate trade signals.
        
        Args:
            tick_data: Tick dictionary with keys:
                - timestamp: Tick timestamp
                - symbol: Symbol name
                - price: Current price
                - bid: Bid price
                - ask: Ask price
                - volume: Volume
                - open, high, low, close: OHLC data
        """
        pass
    
    @abstractmethod
    def on_candle_close(self, candle_data: Dict, timeframe: str) -> None:
        """
        Process a candle close event.
        
        Args:
            candle_data: Candle dictionary
            timeframe: Timeframe (e.g., '1min', '5min', '1hour')
        """
        pass
    
    def on_warmup_candle(self, candle_data: Dict, timeframe: str) -> None:
        """
        Process a historical candle during warmup phase.
        
        This method is called during the warmup phase to feed historical candles
        to the strategy for indicator initialization. Strategies should update
        their indicators but NOT generate any trade signals during warmup.
        
        Default implementation does nothing. Subclasses should override to
        feed candles to their indicator managers.
        
        Args:
            candle_data: Candle dictionary with keys:
                - symbol: Symbol name
                - timestamp: Candle timestamp
                - open, high, low, close: OHLC prices
                - volume: Volume
            timeframe: Timeframe (e.g., '1min', '5min')
        """
        pass
    
    def on_candle_complete(self, candle_data: Dict, timeframe: str) -> None:
        """
        Process a completed candle during live trading.
        
        This method is called when a candle is fully formed and closed.
        Strategies should recalculate indicators based on the closed candle.
        This is in addition to on_candle_close() and provides a clear
        separation between candle completion and strategy logic.
        
        Default implementation calls on_candle_close() for backward compatibility.
        
        Args:
            candle_data: Candle dictionary
            timeframe: Timeframe (e.g., '1min', '5min')
        """
        self.on_candle_close(candle_data, timeframe)
    
    def get_required_timeframes(self) -> List[str]:
        """
        Get list of timeframes required by this strategy.
        
        Subclasses should override to specify which timeframes they need.
        This is used by the candle aggregator to know which candles to generate.
        
        Returns:
            List of timeframe strings (e.g., ['1min', '5min'])
        """
        return ['1min']  # Default to 1-minute candles
    
    def set_warmup_complete(self):
        """
        Mark strategy as warmed up and ready for trading.
        
        This method is called by the WarmupManager after feeding historical
        candles to the strategy. After this is called, the strategy can
        start generating trade signals.
        """
        self.is_warmed_up = True
    
    @abstractmethod
    def check_entry_conditions(self, symbol: str, tick_data: Dict) -> Optional[Dict]:
        """
        Check if entry conditions are met.
        
        Args:
            symbol: Symbol to check
            tick_data: Current tick data
            
        Returns:
            Signal dictionary if conditions met, None otherwise
            Signal format:
            {
                'strategy_id': str,
                'action': 'BUY' or 'SELL',
                'symbol': str,
                'price': float,
                'quantity': int,
                'timestamp': datetime,
                'reason': str,
                'indicators': dict
            }
        """
        pass
    
    @abstractmethod
    def check_exit_conditions(self, symbol: str, tick_data: Dict) -> Optional[Dict]:
        """
        Check if exit conditions are met.
        
        Args:
            symbol: Symbol to check
            tick_data: Current tick data
            
        Returns:
            Signal dictionary if conditions met, None otherwise
        """
        pass
    
    def get_signals(self) -> List[Dict]:
        """
        Get all generated signals.
        
        Returns:
            List of signal dictionaries
        """
        return self.signals.copy()
    
    def clear_signals(self):
        """Clear all signals."""
        self.signals = []
    
    def get_positions(self) -> Dict:
        """
        Get current positions.
        
        Returns:
            Dictionary of positions {symbol: position_info}
        """
        return self.positions.copy()
    
    def add_position(self, symbol: str, entry_price: float, quantity: int, timestamp: datetime):
        """
        Add a position.
        
        Args:
            symbol: Symbol
            entry_price: Entry price
            quantity: Quantity
            timestamp: Entry timestamp
        """
        self.positions[symbol] = {
            'symbol': symbol,
            'entry_price': entry_price,
            'quantity': quantity,
            'entry_timestamp': timestamp,
            'highest_price': entry_price,
            'current_price': entry_price
        }
    
    def remove_position(self, symbol: str):
        """
        Remove a position.
        
        Args:
            symbol: Symbol to remove
        """
        if symbol in self.positions:
            del self.positions[symbol]
    
    def update_position_price(self, symbol: str, price: float):
        """
        Update position with current price.
        
        Args:
            symbol: Symbol
            price: Current price
        """
        if symbol in self.positions:
            pos = self.positions[symbol]
            pos['current_price'] = price
            if price > pos['highest_price']:
                pos['highest_price'] = price
    
    def square_off_all(self) -> List[Dict]:
        """
        Generate exit signals for all open positions.
        
        Returns:
            List of exit signals
        """
        exit_signals = []
        
        for symbol, pos in self.positions.items():
            signal = {
                'strategy_id': self.strategy_id,
                'action': 'SELL',
                'symbol': symbol,
                'price': pos['current_price'],
                'quantity': pos['quantity'],
                'timestamp': datetime.now(),
                'reason': 'Square-off all positions',
                'indicators': {},
                'priority': 'HIGH'
            }
            exit_signals.append(signal)
        
        return exit_signals
    
    def activate(self):
        """Activate strategy."""
        self.is_active = True
    
    def deactivate(self):
        """Deactivate strategy."""
        self.is_active = False
    
    def get_status(self) -> Dict:
        """
        Get strategy status.
        
        Returns:
            Status dictionary
        """
        return {
            'strategy_id': self.strategy_id,
            'is_active': self.is_active,
            'is_warmed_up': self.is_warmed_up,
            'warmup_candles_required': self.warmup_candles_required,
            'symbols': self.symbols,
            'num_positions': len(self.positions),
            'num_signals': len(self.signals)
        }
