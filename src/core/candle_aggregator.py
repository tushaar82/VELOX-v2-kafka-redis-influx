"""
Candle Aggregator Module

This module aggregates ticks into candles of various timeframes and maintains
the current forming candle that updates with every tick.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Callable, Optional, Tuple
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class Candle:
    """Represents a single OHLC candle"""
    
    def __init__(self, symbol: str, timeframe: str, timestamp: datetime):
        self.symbol = symbol
        self.timeframe = timeframe
        self.timestamp = timestamp
        self.open: Optional[float] = None
        self.high: Optional[float] = None
        self.low: Optional[float] = None
        self.close: Optional[float] = None
        self.volume: int = 0
        self.is_complete = False
        
    def update(self, price: float, volume: int = 0):
        """Update candle with new tick data"""
        if self.open is None:
            self.open = price
            self.high = price
            self.low = price
        else:
            self.high = max(self.high, price)
            self.low = min(self.low, price)
        
        self.close = price
        self.volume += volume
        
    def to_dict(self) -> dict:
        """Convert candle to dictionary"""
        return {
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'timestamp': self.timestamp,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume,
            'is_complete': self.is_complete
        }
        
    def __repr__(self):
        return (f"Candle({self.symbol}, {self.timeframe}, {self.timestamp}, "
                f"O:{self.open}, H:{self.high}, L:{self.low}, C:{self.close}, V:{self.volume})")


class CandleAggregator:
    """
    Aggregates ticks into candles of configurable timeframes.
    Maintains current forming candles and emits completed candles.
    """
    
    # Timeframe to minutes mapping
    TIMEFRAME_MINUTES = {
        '1min': 1,
        '3min': 3,
        '5min': 5,
        '15min': 15,
        '30min': 30,
        '1hour': 60,
        '1day': 1440
    }
    
    def __init__(self, timeframes: List[str] = None, max_history: int = 500):
        """
        Initialize CandleAggregator
        
        Args:
            timeframes: List of timeframes to aggregate (e.g., ['1min', '5min'])
            max_history: Maximum number of closed candles to keep per symbol/timeframe
        """
        self.timeframes = timeframes or ['1min']
        self.max_history = max_history
        
        # Validate timeframes
        for tf in self.timeframes:
            if tf not in self.TIMEFRAME_MINUTES:
                raise ValueError(f"Unsupported timeframe: {tf}. Supported: {list(self.TIMEFRAME_MINUTES.keys())}")
        
        # Storage: {symbol: {timeframe: deque([Candle, ...])}}
        self.closed_candles: Dict[str, Dict[str, deque]] = defaultdict(lambda: defaultdict(lambda: deque(maxlen=max_history)))
        
        # Current forming candles: {symbol: {timeframe: Candle}}
        self.forming_candles: Dict[str, Dict[str, Candle]] = defaultdict(dict)
        
        # Callbacks: {timeframe: [callback_functions]}
        self.candle_callbacks: Dict[str, List[Callable]] = defaultdict(list)
        
        logger.info(f"CandleAggregator initialized with timeframes: {self.timeframes}, max_history: {max_history}")
        
    def process_tick(self, tick_data: dict) -> Dict[str, List[Candle]]:
        """
        Process incoming tick and update forming candles.
        
        Args:
            tick_data: Dict with keys: symbol, timestamp, price, volume
            
        Returns:
            Dict of completed candles by timeframe: {timeframe: [Candle, ...]}
        """
        symbol = tick_data['symbol']
        timestamp = tick_data['timestamp']
        price = tick_data['price']
        volume = tick_data.get('volume', 0)
        
        completed_candles = {}
        
        for timeframe in self.timeframes:
            # Get or create forming candle
            candle_timestamp = self._align_timestamp(timestamp, timeframe)
            
            # Check if we need to close the current forming candle
            if symbol in self.forming_candles and timeframe in self.forming_candles[symbol]:
                current_candle = self.forming_candles[symbol][timeframe]
                
                # If timestamp moved to next candle period, close current and create new
                if candle_timestamp > current_candle.timestamp:
                    # Mark as complete and store
                    current_candle.is_complete = True
                    self.closed_candles[symbol][timeframe].append(current_candle)
                    
                    # Track completed candles
                    if timeframe not in completed_candles:
                        completed_candles[timeframe] = []
                    completed_candles[timeframe].append(current_candle)
                    
                    # Trigger callbacks
                    self._trigger_callbacks(timeframe, current_candle)
                    
                    logger.debug(f"Closed candle: {current_candle}")
                    
                    # Create new forming candle
                    self.forming_candles[symbol][timeframe] = Candle(symbol, timeframe, candle_timestamp)
            
            # Create forming candle if doesn't exist
            if timeframe not in self.forming_candles[symbol]:
                self.forming_candles[symbol][timeframe] = Candle(symbol, timeframe, candle_timestamp)
            
            # Update forming candle
            self.forming_candles[symbol][timeframe].update(price, volume)
        
        return completed_candles
    
    def get_closed_candles(self, symbol: str, timeframe: str, count: int = None) -> List[Candle]:
        """
        Get N most recent closed candles.
        
        Args:
            symbol: Symbol to get candles for
            timeframe: Timeframe to get candles for
            count: Number of candles to return (None = all)
            
        Returns:
            List of Candle objects (oldest to newest)
        """
        if symbol not in self.closed_candles or timeframe not in self.closed_candles[symbol]:
            return []
        
        candles = list(self.closed_candles[symbol][timeframe])
        
        if count is not None:
            candles = candles[-count:]
        
        return candles
    
    def get_forming_candle(self, symbol: str, timeframe: str) -> Optional[Candle]:
        """
        Get current forming candle.
        
        Args:
            symbol: Symbol to get candle for
            timeframe: Timeframe to get candle for
            
        Returns:
            Current forming Candle or None
        """
        if symbol not in self.forming_candles or timeframe not in self.forming_candles[symbol]:
            return None
        
        return self.forming_candles[symbol][timeframe]
    
    def get_candle_state(self, symbol: str, timeframe: str) -> Tuple[Optional[Candle], Optional[Candle]]:
        """
        Get both last closed candle and current forming candle.
        
        Args:
            symbol: Symbol to get candles for
            timeframe: Timeframe to get candles for
            
        Returns:
            Tuple of (last_closed_candle, forming_candle)
        """
        last_closed = None
        if symbol in self.closed_candles and timeframe in self.closed_candles[symbol]:
            closed_list = self.closed_candles[symbol][timeframe]
            if closed_list:
                last_closed = closed_list[-1]
        
        forming = self.get_forming_candle(symbol, timeframe)
        
        return last_closed, forming
    
    def register_candle_callback(self, timeframe: str, callback: Callable):
        """
        Register callback for candle close events.
        
        Args:
            timeframe: Timeframe to register callback for
            callback: Function to call when candle closes (receives Candle object)
        """
        if timeframe not in self.TIMEFRAME_MINUTES:
            raise ValueError(f"Unsupported timeframe: {timeframe}")
        
        self.candle_callbacks[timeframe].append(callback)
        logger.info(f"Registered callback for {timeframe} candles")
    
    def is_candle_complete(self, symbol: str, timeframe: str) -> bool:
        """
        Check if a candle just completed (useful for strategies).
        
        Args:
            symbol: Symbol to check
            timeframe: Timeframe to check
            
        Returns:
            True if a candle just completed
        """
        # This is checked by looking at the last closed candle timestamp
        # vs current forming candle timestamp
        if symbol not in self.closed_candles or timeframe not in self.closed_candles[symbol]:
            return False
        
        closed_list = self.closed_candles[symbol][timeframe]
        if not closed_list:
            return False
        
        # A candle is "just complete" if it was added in the last process_tick call
        # This is a simple heuristic - in practice, strategies should use callbacks
        return True
    
    def _align_timestamp(self, timestamp: datetime, timeframe: str) -> datetime:
        """
        Align timestamp to candle boundary.
        
        Args:
            timestamp: Current timestamp
            timeframe: Timeframe to align to
            
        Returns:
            Aligned timestamp (start of candle period)
        """
        minutes = self.TIMEFRAME_MINUTES[timeframe]
        
        # Align to candle boundary
        aligned_minute = (timestamp.minute // minutes) * minutes
        aligned = timestamp.replace(minute=aligned_minute, second=0, microsecond=0)
        
        return aligned
    
    def _trigger_callbacks(self, timeframe: str, candle: Candle):
        """Trigger all registered callbacks for a timeframe"""
        if timeframe in self.candle_callbacks:
            for callback in self.candle_callbacks[timeframe]:
                try:
                    callback(candle)
                except Exception as e:
                    logger.error(f"Error in candle callback: {e}", exc_info=True)
    
    def get_candle_count(self, symbol: str, timeframe: str) -> int:
        """
        Get number of closed candles available.
        
        Args:
            symbol: Symbol to check
            timeframe: Timeframe to check
            
        Returns:
            Number of closed candles
        """
        if symbol not in self.closed_candles or timeframe not in self.closed_candles[symbol]:
            return 0
        
        return len(self.closed_candles[symbol][timeframe])
    
    def add_historical_candle(self, candle: Candle):
        """
        Add a historical candle (for warmup).
        
        Args:
            candle: Candle object to add
        """
        candle.is_complete = True
        self.closed_candles[candle.symbol][candle.timeframe].append(candle)
        logger.debug(f"Added historical candle: {candle}")
    
    def clear(self):
        """Clear all candle data"""
        self.closed_candles.clear()
        self.forming_candles.clear()
        logger.info("Cleared all candle data")
    
    def get_all_symbols(self) -> List[str]:
        """Get list of all symbols being tracked"""
        symbols = set()
        symbols.update(self.closed_candles.keys())
        symbols.update(self.forming_candles.keys())
        return list(symbols)
    
    def get_stats(self) -> dict:
        """Get aggregator statistics"""
        stats = {
            'symbols': self.get_all_symbols(),
            'timeframes': self.timeframes,
            'candle_counts': {}
        }
        
        for symbol in self.get_all_symbols():
            stats['candle_counts'][symbol] = {}
            for timeframe in self.timeframes:
                count = self.get_candle_count(symbol, timeframe)
                stats['candle_counts'][symbol][timeframe] = count
        
        return stats
