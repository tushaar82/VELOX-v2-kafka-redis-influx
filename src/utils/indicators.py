"""
Technical indicators for trading strategies.
Implements RSI, MA, ATR and other common indicators.
"""

import numpy as np
from collections import deque
from typing import Optional, Dict


class TechnicalIndicators:
    """Calculate technical indicators from price data."""
    
    def __init__(self, symbol: str, max_history: int = 200):
        """
        Initialize technical indicators.
        
        Args:
            symbol: Symbol name
            max_history: Maximum number of prices to keep in history
        """
        self.symbol = symbol
        self.max_history = max_history
        
        # Price history (closed candles)
        self.close_prices = deque(maxlen=max_history)
        self.high_prices = deque(maxlen=max_history)
        self.low_prices = deque(maxlen=max_history)
        self.open_prices = deque(maxlen=max_history)
        self.volumes = deque(maxlen=max_history)
        
        # Current forming candle
        self.forming_candle = None
        
        # Cached calculations
        self._rsi_cache = {}
        self._ma_cache = {}
        self._atr_cache = {}
    
    def add_price(self, close: float, high: Optional[float] = None, 
                  low: Optional[float] = None, volume: Optional[int] = None):
        """
        Add a new price to history.
        
        Args:
            close: Close price
            high: High price (defaults to close)
            low: Low price (defaults to close)
            volume: Volume (defaults to 0)
        """
        self.close_prices.append(close)
        self.high_prices.append(high if high is not None else close)
        self.low_prices.append(low if low is not None else close)
        self.open_prices.append(close)  # Default open to close if not specified
        self.volumes.append(volume if volume is not None else 0)
        
        # Invalidate caches
        self._rsi_cache = {}
        self._ma_cache = {}
        self._atr_cache = {}
    
    def add_candle(self, open_price: float, high: float, low: float, close: float, volume: int = 0):
        """
        Add a complete candle to history.
        
        Args:
            open_price: Open price
            high: High price
            low: Low price
            close: Close price
            volume: Volume
        """
        self.open_prices.append(open_price)
        self.high_prices.append(high)
        self.low_prices.append(low)
        self.close_prices.append(close)
        self.volumes.append(volume)
        
        # Invalidate caches
        self._rsi_cache = {}
        self._ma_cache = {}
        self._atr_cache = {}
    
    def update_forming_candle(self, high: float, low: float, close: float, volume: int = 0):
        """
        Update the current forming candle without adding to history.
        
        This allows real-time indicator updates based on the current forming candle.
        
        Args:
            high: Current high
            low: Current low
            close: Current close
            volume: Current volume
        """
        self.forming_candle = {
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        }
    
    def get_candle_count(self) -> int:
        """
        Get number of complete candles in history.
        
        Returns:
            Number of candles
        """
        return len(self.close_prices)
    
    def is_ready(self, indicator_type: str, period: int) -> bool:
        """
        Check if enough data exists for indicator calculation.
        
        Args:
            indicator_type: Type of indicator ('rsi', 'ma', 'atr')
            period: Period for the indicator
            
        Returns:
            True if enough data available
        """
        if indicator_type == 'rsi':
            return len(self.close_prices) >= period + 1
        elif indicator_type == 'ma':
            return len(self.close_prices) >= period
        elif indicator_type == 'atr':
            return len(self.close_prices) >= period + 1
        else:
            return len(self.close_prices) >= period
    
    def calculate_rsi(self, period: int = 14) -> Optional[float]:
        """
        Calculate RSI (Relative Strength Index).
        
        Args:
            period: RSI period (default 14)
            
        Returns:
            RSI value (0-100) or None if insufficient data
        """
        if len(self.close_prices) < period + 1:
            return None
        
        # Check cache
        cache_key = f"rsi_{period}"
        if cache_key in self._rsi_cache:
            return self._rsi_cache[cache_key]
        
        # Calculate price changes
        prices = np.array(list(self.close_prices))
        deltas = np.diff(prices)
        
        # Separate gains and losses
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        # Calculate average gain and loss
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        # Calculate RS and RSI
        if avg_loss == 0:
            rsi = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
        
        # Validate
        rsi = max(0.0, min(100.0, rsi))
        
        # Cache result
        self._rsi_cache[cache_key] = rsi
        
        return rsi
    
    def calculate_ma(self, period: int = 20) -> Optional[float]:
        """
        Calculate Simple Moving Average.
        
        Args:
            period: MA period (default 20)
            
        Returns:
            MA value or None if insufficient data
        """
        if len(self.close_prices) < period:
            return None
        
        # Check cache
        cache_key = f"ma_{period}"
        if cache_key in self._ma_cache:
            return self._ma_cache[cache_key]
        
        # Calculate MA
        prices = np.array(list(self.close_prices))
        ma = np.mean(prices[-period:])
        
        # Cache result
        self._ma_cache[cache_key] = ma
        
        return ma
    
    def calculate_ema(self, period: int = 20) -> Optional[float]:
        """
        Calculate Exponential Moving Average.
        
        Args:
            period: EMA period (default 20)
            
        Returns:
            EMA value or None if insufficient data
        """
        if len(self.close_prices) < period:
            return None
        
        prices = np.array(list(self.close_prices))
        
        # Calculate multiplier
        multiplier = 2 / (period + 1)
        
        # Start with SMA
        ema = np.mean(prices[:period])
        
        # Calculate EMA
        for price in prices[period:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return ema
    
    def calculate_atr(self, period: int = 14) -> Optional[float]:
        """
        Calculate ATR (Average True Range).
        
        Args:
            period: ATR period (default 14)
            
        Returns:
            ATR value or None if insufficient data
        """
        if len(self.close_prices) < period + 1:
            return None
        
        # Check cache
        cache_key = f"atr_{period}"
        if cache_key in self._atr_cache:
            return self._atr_cache[cache_key]
        
        highs = np.array(list(self.high_prices))
        lows = np.array(list(self.low_prices))
        closes = np.array(list(self.close_prices))
        
        # Calculate True Range
        tr_list = []
        for i in range(1, len(closes)):
            h_l = highs[i] - lows[i]
            h_pc = abs(highs[i] - closes[i-1])
            l_pc = abs(lows[i] - closes[i-1])
            tr = max(h_l, h_pc, l_pc)
            tr_list.append(tr)
        
        # Calculate ATR as average of last N true ranges
        atr = np.mean(tr_list[-period:])
        
        # Cache result
        self._atr_cache[cache_key] = atr
        
        return atr
    
    def calculate_bollinger_bands(self, period: int = 20, std_dev: float = 2.0) -> Optional[Dict]:
        """
        Calculate Bollinger Bands.
        
        Args:
            period: Period for MA calculation
            std_dev: Number of standard deviations
            
        Returns:
            Dictionary with 'upper', 'middle', 'lower' or None
        """
        if len(self.close_prices) < period:
            return None
        
        prices = np.array(list(self.close_prices))
        recent_prices = prices[-period:]
        
        middle = np.mean(recent_prices)
        std = np.std(recent_prices)
        
        upper = middle + (std_dev * std)
        lower = middle - (std_dev * std)
        
        return {
            'upper': upper,
            'middle': middle,
            'lower': lower,
            'std': std
        }
    
    def calculate_macd(self, fast: int = 12, slow: int = 26, signal: int = 9) -> Optional[Dict]:
        """
        Calculate MACD (Moving Average Convergence Divergence).
        
        Args:
            fast: Fast EMA period
            slow: Slow EMA period
            signal: Signal line period
            
        Returns:
            Dictionary with 'macd', 'signal', 'histogram' or None
        """
        if len(self.close_prices) < slow + signal:
            return None
        
        prices = np.array(list(self.close_prices))
        
        # Calculate EMAs
        def calc_ema(data, period):
            multiplier = 2 / (period + 1)
            ema = np.mean(data[:period])
            for price in data[period:]:
                ema = (price * multiplier) + (ema * (1 - multiplier))
            return ema
        
        fast_ema = calc_ema(prices, fast)
        slow_ema = calc_ema(prices, slow)
        
        macd_line = fast_ema - slow_ema
        
        # For simplicity, using SMA for signal line
        # In production, would use EMA of MACD line
        signal_line = macd_line  # Simplified
        
        histogram = macd_line - signal_line
        
        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }
    
    def get_all(self, rsi_period: int = 14, ma_period: int = 20, atr_period: int = 14) -> Dict:
        """
        Get all indicators based on closed candles only.
        
        Args:
            rsi_period: RSI period
            ma_period: MA period
            atr_period: ATR period
            
        Returns:
            Dictionary with all indicator values
        """
        return {
            'rsi': self.calculate_rsi(rsi_period),
            'ma': self.calculate_ma(ma_period),
            'ema': self.calculate_ema(ma_period),
            'atr': self.calculate_atr(atr_period),
            'current_price': self.close_prices[-1] if self.close_prices else None,
            'volume': self.volumes[-1] if self.volumes else None
        }
    
    def get_all_with_forming(self, rsi_period: int = 14, ma_period: int = 20, atr_period: int = 14) -> Dict:
        """
        Get all indicators including the current forming candle for real-time updates.
        
        This temporarily adds the forming candle to history, calculates indicators,
        then removes it to maintain data integrity.
        
        Args:
            rsi_period: RSI period
            ma_period: MA period
            atr_period: ATR period
            
        Returns:
            Dictionary with all indicator values including forming candle
        """
        if not self.forming_candle:
            return self.get_all(rsi_period, ma_period, atr_period)
        
        # Temporarily add forming candle
        forming = self.forming_candle
        self.close_prices.append(forming['close'])
        self.high_prices.append(forming['high'])
        self.low_prices.append(forming['low'])
        self.volumes.append(forming['volume'])
        
        # Calculate indicators
        indicators = self.get_all(rsi_period, ma_period, atr_period)
        
        # Remove forming candle
        self.close_prices.pop()
        self.high_prices.pop()
        self.low_prices.pop()
        self.volumes.pop()
        
        return indicators
    
    def get_history_length(self) -> int:
        """Get number of prices in history."""
        return len(self.close_prices)

    def calculate_vwap(self) -> Optional[float]:
        """
        Calculate VWAP (Volume Weighted Average Price).

        VWAP is calculated from the start of the trading session.
        For intraday strategies, this provides the average price weighted by volume.

        Returns:
            VWAP value or None if insufficient data
        """
        if len(self.close_prices) == 0 or len(self.volumes) == 0:
            return None

        # Calculate typical price (H+L+C)/3
        typical_prices = []
        for i in range(len(self.close_prices)):
            typical_price = (
                self.high_prices[i] +
                self.low_prices[i] +
                self.close_prices[i]
            ) / 3.0
            typical_prices.append(typical_price)

        typical_prices = np.array(typical_prices)
        volumes = np.array(list(self.volumes))

        # VWAP = sum(typical_price * volume) / sum(volume)
        if np.sum(volumes) == 0:
            return None

        vwap = np.sum(typical_prices * volumes) / np.sum(volumes)
        return vwap

    def calculate_adx(self, period: int = 14) -> Optional[Dict]:
        """
        Calculate ADX (Average Directional Index) and DMI.

        ADX measures trend strength (0-100):
        - < 20: Weak/no trend
        - 20-25: Possible trend
        - 25-50: Strong trend
        - 50-75: Very strong trend
        - > 75: Extremely strong trend

        Args:
            period: ADX period (default 14)

        Returns:
            Dictionary with 'adx', 'plus_di', 'minus_di' or None
        """
        if len(self.close_prices) < period * 2:
            return None

        highs = np.array(list(self.high_prices))
        lows = np.array(list(self.low_prices))
        closes = np.array(list(self.close_prices))

        # Calculate +DM and -DM
        plus_dm = []
        minus_dm = []

        for i in range(1, len(highs)):
            high_diff = highs[i] - highs[i-1]
            low_diff = lows[i-1] - lows[i]

            if high_diff > low_diff and high_diff > 0:
                plus_dm.append(high_diff)
            else:
                plus_dm.append(0)

            if low_diff > high_diff and low_diff > 0:
                minus_dm.append(low_diff)
            else:
                minus_dm.append(0)

        plus_dm = np.array(plus_dm)
        minus_dm = np.array(minus_dm)

        # Calculate True Range
        tr_list = []
        for i in range(1, len(closes)):
            h_l = highs[i] - lows[i]
            h_pc = abs(highs[i] - closes[i-1])
            l_pc = abs(lows[i] - closes[i-1])
            tr = max(h_l, h_pc, l_pc)
            tr_list.append(tr)

        tr = np.array(tr_list)

        # Calculate smoothed values
        def smooth(values, period):
            smoothed = []
            first = np.sum(values[:period])
            smoothed.append(first)
            for i in range(period, len(values)):
                smoothed.append(smoothed[-1] - smoothed[-1]/period + values[i])
            return np.array(smoothed)

        if len(tr) < period or len(plus_dm) < period:
            return None

        smoothed_tr = smooth(tr, period)
        smoothed_plus_dm = smooth(plus_dm, period)
        smoothed_minus_dm = smooth(minus_dm, period)

        # Calculate +DI and -DI
        with np.errstate(divide='ignore', invalid='ignore'):
            plus_di = 100 * smoothed_plus_dm / smoothed_tr
            minus_di = 100 * smoothed_minus_dm / smoothed_tr

            # Calculate DX
            di_sum = plus_di + minus_di
            di_diff = np.abs(plus_di - minus_di)
            dx = np.where(di_sum != 0, 100 * di_diff / di_sum, 0)

            # Calculate ADX (smoothed DX)
            if len(dx) < period:
                adx = np.mean(dx)
            else:
                adx = np.mean(dx[-period:])

        # Handle NaN/Inf values
        adx = float(adx) if not (np.isnan(adx) or np.isinf(adx)) else 0.0
        plus_di_val = float(plus_di[-1]) if len(plus_di) > 0 and not (np.isnan(plus_di[-1]) or np.isinf(plus_di[-1])) else 0.0
        minus_di_val = float(minus_di[-1]) if len(minus_di) > 0 and not (np.isnan(minus_di[-1]) or np.isinf(minus_di[-1])) else 0.0

        return {
            'adx': adx,
            'plus_di': plus_di_val,
            'minus_di': minus_di_val
        }

    def calculate_stochastic(self, k_period: int = 14, d_period: int = 3) -> Optional[Dict]:
        """
        Calculate Stochastic Oscillator (%K and %D).

        Stochastic oscillator compares current close to the recent range:
        - > 80: Overbought
        - < 20: Oversold

        Args:
            k_period: %K period (default 14)
            d_period: %D smoothing period (default 3)

        Returns:
            Dictionary with 'k' and 'd' or None
        """
        if len(self.close_prices) < k_period + d_period:
            return None

        closes = np.array(list(self.close_prices))
        highs = np.array(list(self.high_prices))
        lows = np.array(list(self.low_prices))

        # Calculate %K
        k_values = []
        for i in range(k_period - 1, len(closes)):
            period_high = np.max(highs[i-k_period+1:i+1])
            period_low = np.min(lows[i-k_period+1:i+1])

            if period_high == period_low:
                k = 50.0  # Neutral if no range
            else:
                k = 100 * (closes[i] - period_low) / (period_high - period_low)

            k_values.append(k)

        k_values = np.array(k_values)

        # Calculate %D (SMA of %K)
        if len(k_values) < d_period:
            d = np.mean(k_values)
        else:
            d = np.mean(k_values[-d_period:])

        return {
            'k': float(k_values[-1]),
            'd': float(d)
        }


class IndicatorManager:
    """Manages indicators for multiple symbols."""
    
    def __init__(self):
        """Initialize indicator manager."""
        self.indicators = {}  # symbol -> TechnicalIndicators
    
    def process_tick(self, tick_data: Dict):
        """
        Process a tick and update indicators.
        
        Args:
            tick_data: Tick dictionary with symbol, price, high, low, volume
        """
        symbol = tick_data['symbol']
        
        if symbol not in self.indicators:
            self.indicators[symbol] = TechnicalIndicators(symbol)
        
        self.indicators[symbol].add_price(
            close=tick_data.get('price', tick_data.get('close')),
            high=tick_data.get('high'),
            low=tick_data.get('low'),
            volume=tick_data.get('volume')
        )
    
    def add_candle(self, symbol: str, open_price: float, high: float, low: float, 
                   close: float, volume: int = 0, timestamp=None):
        """
        Add a complete candle to indicator history.
        
        Args:
            symbol: Symbol name
            open_price: Open price
            high: High price
            low: Low price
            close: Close price
            volume: Volume
            timestamp: Optional timestamp (for logging)
        """
        if symbol not in self.indicators:
            self.indicators[symbol] = TechnicalIndicators(symbol)
        
        self.indicators[symbol].add_candle(open_price, high, low, close, volume)
    
    def update_forming_candle(self, symbol: str, high: float, low: float, 
                             close: float, volume: int = 0, timestamp=None):
        """
        Update the current forming candle for real-time indicator updates.
        
        Args:
            symbol: Symbol name
            high: Current high
            low: Current low
            close: Current close
            volume: Current volume
            timestamp: Optional timestamp (for logging)
        """
        if symbol not in self.indicators:
            self.indicators[symbol] = TechnicalIndicators(symbol)
        
        self.indicators[symbol].update_forming_candle(high, low, close, volume)
    
    def process_candle(self, candle_data: Dict):
        """
        Process a complete candle.
        
        Args:
            candle_data: Candle dictionary with symbol, open, high, low, close, volume
        """
        symbol = candle_data['symbol']
        self.add_candle(
            symbol=symbol,
            open_price=candle_data['open'],
            high=candle_data['high'],
            low=candle_data['low'],
            close=candle_data['close'],
            volume=candle_data.get('volume', 0),
            timestamp=candle_data.get('timestamp')
        )
    
    def get_indicators(self, symbol: str, **kwargs) -> Dict:
        """
        Get indicators for a symbol.
        
        Args:
            symbol: Symbol name
            **kwargs: Arguments for get_all()
            
        Returns:
            Dictionary of indicators
        """
        if symbol not in self.indicators:
            return {}
        
        return self.indicators[symbol].get_all(**kwargs)
    
    def has_symbol(self, symbol: str) -> bool:
        """Check if symbol has indicators."""
        return symbol in self.indicators
    
    def get_candle_count(self, symbol: str) -> int:
        """
        Get number of candles for a symbol.
        
        Args:
            symbol: Symbol name
            
        Returns:
            Number of candles or 0 if symbol not found
        """
        if symbol not in self.indicators:
            return 0
        return self.indicators[symbol].get_candle_count()
    
    def is_ready(self, symbol: str, indicator_type: str, period: int) -> bool:
        """
        Check if enough data exists for indicator calculation.
        
        Args:
            symbol: Symbol name
            indicator_type: Type of indicator ('rsi', 'ma', 'atr')
            period: Period for the indicator
            
        Returns:
            True if enough data available
        """
        if symbol not in self.indicators:
            return False
        return self.indicators[symbol].is_ready(indicator_type, period)


if __name__ == "__main__":
    # Test indicators
    print("\n=== Testing Technical Indicators ===\n")
    
    ti = TechnicalIndicators('TEST')
    
    # Add some test data
    test_prices = [50, 51, 52, 48, 47, 49, 51, 53, 52, 51, 50, 52, 54, 53, 55, 56, 54, 53, 52, 54]
    
    print(f"Adding {len(test_prices)} prices...")
    for price in test_prices:
        ti.add_price(price, price, price)
    
    # Calculate indicators
    print(f"\nHistory length: {ti.get_history_length()}")
    
    rsi = ti.calculate_rsi(period=14)
    print(f"RSI(14): {rsi:.2f}" if rsi else "RSI: Not enough data")
    
    ma = ti.calculate_ma(period=10)
    print(f"MA(10): {ma:.2f}" if ma else "MA: Not enough data")
    
    atr = ti.calculate_atr(period=10)
    print(f"ATR(10): {atr:.2f}" if atr else "ATR: Not enough data")
    
    # Get all indicators
    print("\nAll indicators:")
    all_ind = ti.get_all()
    for key, value in all_ind.items():
        if value is not None:
            print(f"  {key}: {value:.2f}")
    
    print("\n✓ Indicators test complete")
