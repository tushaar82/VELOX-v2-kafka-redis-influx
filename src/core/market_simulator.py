"""
Market simulator with realistic intra-minute tick generation.
Replays historical OHLC data with simulated tick-level price movements.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Callable, Optional
import time
import signal

from ..adapters.data.base import DataAdapter
from ..utils.logging_config import get_logger


class MarketSimulator:
    """Simulates market data replay with realistic tick generation."""
    
    def __init__(self, data_adapter: DataAdapter, date: str, symbols: List[str], 
                 speed: float = 1.0, ticks_per_candle: int = 10):
        """
        Initialize market simulator.
        
        Args:
            data_adapter: Data adapter for loading historical data
            date: Date to simulate (YYYY-MM-DD)
            symbols: List of symbols to simulate
            speed: Playback speed multiplier (1.0=real-time, 100.0=100x faster)
            ticks_per_candle: Number of ticks to generate per 1-minute candle
        """
        self.data_adapter = data_adapter
        self.current_date = date
        self.symbols = symbols
        self.playback_speed = speed
        self.ticks_per_candle = ticks_per_candle
        
        self.logger = get_logger('simulator')
        
        # State
        self.data_buffer = None
        self.current_time = None
        self.is_running = False
        self.is_paused = False
        self.tick_count = 0
        self.start_time = None
        
        # Candle aggregator (optional)
        self.candle_aggregator = None
        
        # Setup signal handlers (only in main thread)
        try:
            signal.signal(signal.SIGINT, self._signal_handler)
        except ValueError:
            # Running in a thread, signal handlers not available
            self.logger.debug("Signal handlers not available (running in thread)")
        
        self.logger.info(
            f"MarketSimulator initialized: date={date}, symbols={symbols}, "
            f"speed={speed}x, ticks_per_candle={ticks_per_candle}"
        )
    
    def set_candle_aggregator(self, aggregator):
        """
        Set candle aggregator for tick-to-candle conversion.
        
        Args:
            aggregator: CandleAggregator instance
        """
        self.candle_aggregator = aggregator
        self.logger.info("Candle aggregator attached to simulator")
    
    def _signal_handler(self, signum, frame):
        """Handle Ctrl+C to pause instead of exit."""
        if self.is_running:
            self.pause()
            self.logger.info("Simulation paused (Ctrl+C). Call resume() to continue.")
    
    def load_data(self):
        """Load historical data for the simulation date."""
        self.logger.info(f"Loading data for {self.current_date}...")
        
        self.data_buffer = self.data_adapter.get_data(self.current_date, self.symbols)
        
        if self.data_buffer.empty:
            self.logger.error(f"No data available for {self.current_date}")
            return False
        
        # Sort by timestamp
        self.data_buffer = self.data_buffer.sort_values('timestamp')
        
        total_candles = len(self.data_buffer)
        total_ticks = total_candles * self.ticks_per_candle
        
        self.logger.info(
            f"Loaded {total_candles} candles, will generate {total_ticks} ticks"
        )
        
        return True
    
    def start(self):
        """Start the simulation."""
        self.is_running = True
        self.is_paused = False
        self.start_time = time.time()
        self.logger.info("Simulation started")
    
    def pause(self):
        """Pause the simulation."""
        self.is_paused = True
        self.logger.info("Simulation paused")
    
    def resume(self):
        """Resume the simulation."""
        self.is_paused = False
        self.logger.info("Simulation resumed")
    
    def stop(self):
        """Stop the simulation."""
        self.is_running = False
        elapsed = time.time() - self.start_time if self.start_time else 0
        self.logger.info(
            f"Simulation stopped. Generated {self.tick_count} ticks in {elapsed:.2f} seconds"
        )
    
    def set_speed(self, multiplier: float):
        """Update playback speed."""
        self.playback_speed = multiplier
        self.logger.info(f"Playback speed set to {multiplier}x")
    
    def jump_to_time(self, target_time: datetime):
        """Skip to a specific time in the simulation."""
        self.current_time = target_time
        self.logger.info(f"Jumped to {target_time}")
    
    def get_status(self) -> Dict:
        """Get current simulation status."""
        if self.data_buffer is None or self.data_buffer.empty:
            return {
                'status': 'not_loaded',
                'current_time': None,
                'progress': 0.0,
                'ticks_generated': self.tick_count
            }
        
        total_ticks = len(self.data_buffer) * self.ticks_per_candle
        progress = (self.tick_count / total_ticks * 100) if total_ticks > 0 else 0
        
        return {
            'status': 'running' if self.is_running else 'stopped',
            'paused': self.is_paused,
            'current_time': self.current_time,
            'progress': progress,
            'ticks_generated': self.tick_count,
            'ticks_remaining': total_ticks - self.tick_count
        }
    
    def generate_realistic_ticks(self, candle: Dict) -> List[Dict]:
        """
        Generate realistic tick sequence from OHLC candle.
        
        Args:
            candle: Dict with keys: timestamp, open, high, low, close, volume, symbol
            
        Returns:
            List of tick dictionaries
        """
        o, h, l, c = candle['open'], candle['high'], candle['low'], candle['close']
        volume = candle['volume']
        timestamp = candle['timestamp']
        symbol = candle['symbol']
        
        # Determine price path based on candle pattern
        price_path = self._determine_price_path(o, h, l, c)
        
        # Generate tick prices along the path
        tick_prices = self._interpolate_prices(price_path, self.ticks_per_candle, l, h)
        
        # Distribute volume across ticks
        tick_volumes = self._distribute_volume(volume, len(tick_prices))
        
        # Generate ticks
        ticks = []
        seconds_per_tick = 60.0 / self.ticks_per_candle
        
        for i, (price, vol) in enumerate(zip(tick_prices, tick_volumes)):
            tick_time = timestamp + timedelta(seconds=i * seconds_per_tick)
            
            # Calculate realistic bid/ask spread (0.1% typical for Indian stocks)
            spread_pct = 0.001  # 0.1% spread
            spread = price * spread_pct
            bid = price - spread / 2
            ask = price + spread / 2
            
            tick = {
                'timestamp': tick_time,
                'symbol': symbol,
                'price': round(price, 2),
                'bid': round(bid, 2),
                'ask': round(ask, 2),
                'volume': int(vol),
                'open': round(o, 2),
                'high': round(h, 2),
                'low': round(l, 2),
                'close': round(c, 2)
            }
            ticks.append(tick)
        
        return ticks
    
    def _determine_price_path(self, o: float, h: float, l: float, c: float) -> List[float]:
        """
        Determine realistic price path through OHLC points.
        Uses a more realistic path that doesn't always hit extremes.
        
        Args:
            o, h, l, c: Open, High, Low, Close prices
            
        Returns:
            List of key price points defining the path
        """
        # More realistic: price moves gradually from open to close
        # Only occasionally hitting the high/low extremes
        
        # 70% chance to use gradual path, 30% chance to hit extremes
        use_extremes = np.random.random() < 0.3
        
        if not use_extremes:
            # Gradual path: just interpolate from open to close with small variations
            return [o, c]
        
        # Original extreme-hitting logic for volatile candles
        if c > o:
            # Bullish candle: Open → High → Close (skip low unless very volatile)
            volatility = (h - l) / o
            if volatility > 0.02:  # 2% volatility
                return [o, l, h, c]
            else:
                return [o, h, c]
        elif c < o:
            # Bearish candle: Open → Low → Close (skip high unless very volatile)
            volatility = (h - l) / o
            if volatility > 0.02:
                return [o, h, l, c]
            else:
                return [o, l, c]
        else:
            # Doji: Open → High → Low → Close
            return [o, h, l, c]
    
    def _interpolate_prices(self, path: List[float], num_ticks: int, 
                           min_price: float, max_price: float) -> List[float]:
        """
        Interpolate prices along the path with realistic noise.
        Uses smoother interpolation to avoid hitting extremes too often.
        
        Args:
            path: Key price points
            num_ticks: Number of ticks to generate
            min_price: Minimum allowed price (low)
            max_price: Maximum allowed price (high)
            
        Returns:
            List of interpolated prices
        """
        # Interpolate linearly between path points
        path_indices = np.linspace(0, len(path) - 1, num_ticks)
        prices = np.interp(path_indices, range(len(path)), path)
        
        # Add realistic random walk noise (±0.05% per tick)
        # This creates more realistic price movement
        noise_pct = 0.0005
        noise = np.random.normal(0, noise_pct, num_ticks)
        prices = prices * (1 + noise)
        
        # Apply smoothing to avoid sharp jumps
        # Use exponential moving average for smoother transitions
        alpha = 0.3
        smoothed = [prices[0]]
        for i in range(1, len(prices)):
            smoothed.append(alpha * prices[i] + (1 - alpha) * smoothed[-1])
        prices = np.array(smoothed)
        
        # Ensure prices stay within realistic bounds (not exactly at extremes)
        # Leave 0.1% buffer from extremes to avoid triggering stops too easily
        buffer = (max_price - min_price) * 0.001
        prices = np.clip(prices, min_price + buffer, max_price - buffer)
        
        return prices.tolist()
    
    def _distribute_volume(self, total_volume: int, num_ticks: int) -> List[int]:
        """
        Distribute volume across ticks with realistic variation.
        
        Args:
            total_volume: Total volume for the candle
            num_ticks: Number of ticks
            
        Returns:
            List of volumes for each tick
        """
        if total_volume == 0:
            return [0] * num_ticks
        
        # Generate random weights
        weights = np.random.exponential(1.0, num_ticks)
        weights = weights / weights.sum()
        
        # Distribute volume
        volumes = (weights * total_volume).astype(int)
        
        # Adjust to match total exactly
        diff = total_volume - volumes.sum()
        if diff > 0:
            # Add remaining to random ticks
            indices = np.random.choice(num_ticks, diff, replace=True)
            for idx in indices:
                volumes[idx] += 1
        
        return volumes.tolist()
    
    def run_simulation(self, callback_fn: Optional[Callable] = None):
        """
        Run the main simulation loop.
        
        If candle_aggregator is set, ticks are first passed through the aggregator
        before being sent to the callback. This allows strategies to work with
        candle-based data instead of raw ticks.
        
        Args:
            callback_fn: Optional callback function called for each tick
                        Signature: callback_fn(tick_data: Dict)
        """
        if self.data_buffer is None or self.data_buffer.empty:
            self.logger.error("No data loaded. Call load_data() first.")
            return
        
        self.start()
        
        candle_count = 0
        last_log_tick = 0
        
        try:
            # Iterate through each candle
            for idx, row in self.data_buffer.iterrows():
                if not self.is_running:
                    break
                
                # Wait if paused
                while self.is_paused:
                    time.sleep(0.1)
                
                # Convert row to dict
                candle = row.to_dict()
                
                # Generate ticks for this candle
                ticks = self.generate_realistic_ticks(candle)
                
                # Process each tick
                for tick in ticks:
                    if not self.is_running:
                        break
                    
                    # Update current time
                    self.current_time = tick['timestamp']
                    
                    # Process through candle aggregator if available
                    if self.candle_aggregator:
                        completed_candles = self.candle_aggregator.process_tick(tick)
                        
                        # If candles completed, they will be handled by aggregator callbacks
                        # The callback_fn still receives ticks for backward compatibility
                    
                    # Call callback if provided
                    if callback_fn:
                        callback_fn(tick)
                    
                    # Increment counter
                    self.tick_count += 1
                    
                    # Sleep based on playback speed
                    # Real-time: 60 seconds / ticks_per_candle
                    # Adjusted: (60 / ticks_per_candle) / playback_speed
                    sleep_time = (60.0 / self.ticks_per_candle) / self.playback_speed
                    time.sleep(sleep_time)
                    
                    # Log progress every 1000 ticks
                    if self.tick_count - last_log_tick >= 1000:
                        self.logger.info(
                            f"Processed {self.tick_count} ticks, "
                            f"current time: {self.current_time.strftime('%H:%M:%S')}"
                        )
                        last_log_tick = self.tick_count
                
                candle_count += 1
                
                # Log every 100 candles
                if candle_count % 100 == 0:
                    self.logger.debug(f"Processed {candle_count} candles")
        
        except Exception as e:
            self.logger.error(f"Error in simulation: {e}", exc_info=True)
        
        finally:
            self.stop()


if __name__ == "__main__":
    # Test the simulator
    from ..adapters.data.historical import HistoricalDataManager
    from ..utils.logging_config import initialize_logging
    import logging
    
    initialize_logging(log_level=logging.INFO)
    
    # Initialize data manager
    hdm = HistoricalDataManager('./data')
    stats = hdm.get_statistics()
    
    if stats['symbols']:
        # Get a test date
        symbol = stats['symbols'][0]
        dates = hdm.get_available_dates(symbol)
        
        if len(dates) > 100:
            test_date = dates[100]
            test_symbols = [symbol]
            
            print(f"\n=== Testing Market Simulator ===")
            print(f"Date: {test_date}")
            print(f"Symbols: {test_symbols}")
            print(f"Speed: 100x")
            
            # Create simulator
            sim = MarketSimulator(hdm, test_date, test_symbols, speed=100.0)
            
            # Load data
            if sim.load_data():
                # Define callback
                tick_counter = [0]
                
                def tick_callback(tick):
                    tick_counter[0] += 1
                    if tick_counter[0] <= 5:
                        print(f"Tick {tick_counter[0]}: {tick['symbol']} @ {tick['price']} "
                              f"(bid={tick['bid']}, ask={tick['ask']}, vol={tick['volume']})")
                
                # Run simulation
                print("\nStarting simulation...")
                sim.run_simulation(tick_callback)
                
                # Print status
                status = sim.get_status()
                print(f"\n=== Simulation Complete ===")
                print(f"Total ticks generated: {status['ticks_generated']}")
                print(f"Progress: {status['progress']:.1f}%")
