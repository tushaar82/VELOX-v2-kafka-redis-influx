"""
Warmup Manager Module

This module handles loading historical candles and warming up strategies
before live trading begins.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


class WarmupManager:
    """
    Manages the warmup phase where historical candles are loaded and fed to
    strategies to initialize indicators without generating trade signals.
    """
    
    def __init__(self, min_candles: int = 200, auto_calculate: bool = True):
        """
        Initialize WarmupManager
        
        Args:
            min_candles: Minimum number of historical candles to load
            auto_calculate: Automatically calculate required warmup from strategies
        """
        self.min_candles = min_candles
        self.auto_calculate = auto_calculate
        self.warmup_complete = False
        self.warmup_progress = 0.0
        self.candles_loaded = 0
        self.candles_required = min_candles
        self.warmup_start_time = None
        self.warmup_end_time = None
        
        logger.info(f"WarmupManager initialized: min_candles={min_candles}, auto_calculate={auto_calculate}")
    
    def calculate_required_warmup(self, strategies: List) -> int:
        """
        Calculate required warmup period based on strategies.
        
        Args:
            strategies: List of strategy instances
            
        Returns:
            Number of candles required for warmup
        """
        if not self.auto_calculate:
            return self.min_candles
        
        max_required = self.min_candles
        
        for strategy in strategies:
            # Check if strategy has warmup_candles_required property
            if hasattr(strategy, 'warmup_candles_required'):
                required = strategy.warmup_candles_required
                max_required = max(max_required, required)
                logger.info(f"Strategy {strategy.strategy_id} requires {required} warmup candles")
        
        self.candles_required = max_required
        logger.info(f"Total warmup candles required: {max_required}")
        
        return max_required
    
    def load_historical_candles(self, data_manager, date: datetime, symbols: List[str], 
                                count: int = None, timeframe: str = '1min') -> Dict[str, List[dict]]:
        """
        Load historical candles from data manager.
        
        Args:
            data_manager: DataManager instance to load data from
            date: Target date for simulation
            symbols: List of symbols to load
            count: Number of candles to load (None = use calculated required)
            timeframe: Timeframe for candles
            
        Returns:
            Dict of {symbol: [candle_dicts]}
        """
        if count is None:
            count = self.candles_required
        
        logger.info(f"Loading {count} historical candles for {len(symbols)} symbols before {date}")
        
        historical_candles = defaultdict(list)
        
        # Calculate start date based on count and timeframe
        # Assuming 1min candles and 6.5 hour trading day (390 minutes)
        trading_minutes_per_day = 390
        days_needed = (count // trading_minutes_per_day) + 2  # Add buffer
        start_date = date - timedelta(days=days_needed)
        
        try:
            # Load data from data manager (CSV files)
            for symbol in symbols:
                try:
                    # Try to load from CSV or database
                    candles = self._load_symbol_data(data_manager, symbol, start_date, date, count)
                    
                    if candles:
                        historical_candles[symbol] = candles
                        logger.info(f"Loaded {len(candles)} candles for {symbol}")
                    else:
                        logger.warning(f"No historical data found for {symbol}")
                        
                except Exception as e:
                    logger.error(f"Error loading historical data for {symbol}: {e}", exc_info=True)
        
        except Exception as e:
            logger.error(f"Error loading historical candles: {e}", exc_info=True)
        
        return dict(historical_candles)
    
    def _load_symbol_data(self, data_manager, symbol: str, start_date: datetime, 
                         end_date: datetime, count: int) -> List[dict]:
        """
        Load data for a single symbol.
        
        Args:
            data_manager: DataManager instance
            symbol: Symbol to load
            start_date: Start date
            end_date: End date
            count: Number of candles needed
            
        Returns:
            List of candle dicts
        """
        candles = []
        
        # Try to load from historical data adapter if available
        if hasattr(data_manager, 'historical_adapter'):
            try:
                df = data_manager.historical_adapter.load_data(symbol, start_date, end_date)
                
                if df is not None and not df.empty:
                    # Convert DataFrame to candle dicts
                    for idx, row in df.iterrows():
                        candle = {
                            'symbol': symbol,
                            'timestamp': idx if isinstance(idx, datetime) else row.get('timestamp'),
                            'open': row.get('open', row.get('Open')),
                            'high': row.get('high', row.get('High')),
                            'low': row.get('low', row.get('Low')),
                            'close': row.get('close', row.get('Close')),
                            'volume': row.get('volume', row.get('Volume', 0))
                        }
                        candles.append(candle)
                    
                    # Take only the last 'count' candles
                    candles = candles[-count:]
                    
            except Exception as e:
                logger.error(f"Error loading from historical adapter: {e}")
        
        return candles
    
    def warmup_strategies(self, strategies: List, historical_candles: Dict[str, List[dict]], 
                         candle_aggregator=None) -> bool:
        """
        Feed historical candles to strategies in warmup mode.
        
        Args:
            strategies: List of strategy instances
            historical_candles: Dict of {symbol: [candle_dicts]}
            candle_aggregator: Optional CandleAggregator to populate
            
        Returns:
            True if warmup successful
        """
        self.warmup_start_time = datetime.now()
        logger.info("Starting strategy warmup...")
        
        try:
            # Organize candles by timestamp across all symbols
            all_candles = []
            for symbol, candles in historical_candles.items():
                for candle in candles:
                    all_candles.append(candle)
            
            # Sort by timestamp
            all_candles.sort(key=lambda x: x['timestamp'])
            
            total_candles = len(all_candles)
            logger.info(f"Warming up with {total_candles} total candles")
            
            # Feed candles to strategies
            for idx, candle in enumerate(all_candles):
                # Update progress
                self.candles_loaded = idx + 1
                self.warmup_progress = (self.candles_loaded / total_candles) * 100
                
                # Add to candle aggregator if provided
                if candle_aggregator:
                    from .candle_aggregator import Candle
                    agg_candle = Candle(
                        symbol=candle['symbol'],
                        timeframe='1min',
                        timestamp=candle['timestamp']
                    )
                    agg_candle.open = candle['open']
                    agg_candle.high = candle['high']
                    agg_candle.low = candle['low']
                    agg_candle.close = candle['close']
                    agg_candle.volume = candle['volume']
                    candle_aggregator.add_historical_candle(agg_candle)
                
                # Feed to strategies
                for strategy in strategies:
                    if hasattr(strategy, 'on_warmup_candle'):
                        try:
                            strategy.on_warmup_candle(candle, timeframe='1min')
                        except Exception as e:
                            logger.error(f"Error in strategy {strategy.strategy_id} warmup: {e}", exc_info=True)
                
                # Log progress periodically
                if idx % 100 == 0:
                    logger.info(f"Warmup progress: {self.warmup_progress:.1f}% ({self.candles_loaded}/{total_candles})")
            
            # Mark warmup complete
            self.mark_warmup_complete(strategies)
            
            self.warmup_end_time = datetime.now()
            duration = (self.warmup_end_time - self.warmup_start_time).total_seconds()
            logger.info(f"Warmup completed in {duration:.2f} seconds")
            
            return True
            
        except Exception as e:
            logger.error(f"Error during warmup: {e}", exc_info=True)
            return False
    
    def mark_warmup_complete(self, strategies: List = None):
        """
        Mark warmup as complete and enable trading.
        
        Args:
            strategies: Optional list of strategies to mark as warmed up
        """
        self.warmup_complete = True
        self.warmup_progress = 100.0
        
        if strategies:
            for strategy in strategies:
                if hasattr(strategy, 'set_warmup_complete'):
                    strategy.set_warmup_complete()
                    logger.info(f"Strategy {strategy.strategy_id} warmup complete")
        
        logger.info("Warmup phase complete - trading enabled")
    
    def is_warmup_complete(self) -> bool:
        """Check if warmup is complete"""
        return self.warmup_complete
    
    def get_warmup_status(self) -> dict:
        """
        Get current warmup status.
        
        Returns:
            Dict with warmup status information
        """
        status = {
            'is_complete': self.warmup_complete,
            'progress': self.warmup_progress,
            'candles_loaded': self.candles_loaded,
            'candles_required': self.candles_required,
            'start_time': self.warmup_start_time,
            'end_time': self.warmup_end_time
        }
        
        if self.warmup_start_time and not self.warmup_complete:
            elapsed = (datetime.now() - self.warmup_start_time).total_seconds()
            status['elapsed_seconds'] = elapsed
            
            if self.warmup_progress > 0:
                estimated_total = elapsed / (self.warmup_progress / 100)
                estimated_remaining = estimated_total - elapsed
                status['estimated_remaining_seconds'] = estimated_remaining
        
        return status
    
    def reset(self):
        """Reset warmup state"""
        self.warmup_complete = False
        self.warmup_progress = 0.0
        self.candles_loaded = 0
        self.warmup_start_time = None
        self.warmup_end_time = None
        logger.info("Warmup state reset")
