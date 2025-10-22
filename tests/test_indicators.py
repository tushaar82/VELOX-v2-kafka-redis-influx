"""
Unit tests for technical indicators.
"""

import sys
from pathlib import Path
import pytest
import numpy as np

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.indicators import TechnicalIndicators, IndicatorManager


class TestTechnicalIndicators:
    """Test cases for TechnicalIndicators."""
    
    def setup_method(self):
        """Setup for each test."""
        self.ti = TechnicalIndicators('TEST')
    
    def test_initialization(self):
        """Test indicator initialization."""
        assert self.ti.symbol == 'TEST'
        assert self.ti.get_history_length() == 0
    
    def test_add_price(self):
        """Test adding prices."""
        self.ti.add_price(100.0)
        assert self.ti.get_history_length() == 1
        
        self.ti.add_price(101.0, high=102.0, low=100.5, volume=1000)
        assert self.ti.get_history_length() == 2
    
    def test_rsi_insufficient_data(self):
        """Test RSI with insufficient data."""
        for i in range(10):
            self.ti.add_price(100.0 + i)
        
        rsi = self.ti.calculate_rsi(period=14)
        assert rsi is None  # Not enough data
    
    def test_rsi_calculation(self):
        """Test RSI calculation with known values."""
        # Add prices that should give predictable RSI
        prices = [44, 44.34, 44.09, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84, 46.08,
                  45.89, 46.03, 45.61, 46.28, 46.28, 46.00, 46.03, 46.41, 46.22, 45.64]
        
        for price in prices:
            self.ti.add_price(price)
        
        rsi = self.ti.calculate_rsi(period=14)
        
        assert rsi is not None
        assert 0 <= rsi <= 100
        # RSI should be around 60-70 for this uptrend
        assert 50 < rsi < 80
    
    def test_rsi_bounds(self):
        """Test RSI stays within 0-100 bounds."""
        # Strong uptrend
        for i in range(20):
            self.ti.add_price(100.0 + i * 2)
        
        rsi = self.ti.calculate_rsi(period=14)
        assert 0 <= rsi <= 100
        assert rsi > 70  # Should be overbought
    
    def test_rsi_downtrend(self):
        """Test RSI in downtrend."""
        # Strong downtrend
        for i in range(20):
            self.ti.add_price(100.0 - i * 2)
        
        rsi = self.ti.calculate_rsi(period=14)
        assert 0 <= rsi <= 100
        assert rsi < 30  # Should be oversold
    
    def test_ma_insufficient_data(self):
        """Test MA with insufficient data."""
        for i in range(5):
            self.ti.add_price(100.0 + i)
        
        ma = self.ti.calculate_ma(period=10)
        assert ma is None
    
    def test_ma_calculation(self):
        """Test MA calculation."""
        prices = [10, 20, 30, 40, 50]
        for price in prices:
            self.ti.add_price(price)
        
        ma = self.ti.calculate_ma(period=5)
        assert ma == 30.0  # Average of 10,20,30,40,50
    
    def test_ma_moving_window(self):
        """Test MA with moving window."""
        prices = list(range(1, 11))  # 1 to 10
        for price in prices:
            self.ti.add_price(price)
        
        ma5 = self.ti.calculate_ma(period=5)
        assert ma5 == 8.0  # Average of last 5: (6+7+8+9+10)/5
    
    def test_atr_insufficient_data(self):
        """Test ATR with insufficient data."""
        for i in range(10):
            self.ti.add_price(100.0 + i)
        
        atr = self.ti.calculate_atr(period=14)
        assert atr is None
    
    def test_atr_calculation(self):
        """Test ATR calculation."""
        # Add prices with known ranges
        for i in range(20):
            high = 100.0 + i + 2.0
            low = 100.0 + i - 2.0
            close = 100.0 + i
            self.ti.add_price(close, high, low)
        
        atr = self.ti.calculate_atr(period=14)
        
        assert atr is not None
        assert atr > 0
        # With consistent 4-point range, ATR should be around 4
        assert 3.5 < atr < 4.5
    
    def test_atr_volatility(self):
        """Test ATR reflects volatility."""
        # Low volatility
        ti_low = TechnicalIndicators('LOW_VOL')
        for i in range(20):
            ti_low.add_price(100.0 + i * 0.1, 100.0 + i * 0.1 + 0.1, 100.0 + i * 0.1 - 0.1)
        
        # High volatility
        ti_high = TechnicalIndicators('HIGH_VOL')
        for i in range(20):
            ti_high.add_price(100.0 + i, 100.0 + i + 5.0, 100.0 + i - 5.0)
        
        atr_low = ti_low.calculate_atr(period=14)
        atr_high = ti_high.calculate_atr(period=14)
        
        assert atr_high > atr_low  # High volatility should have higher ATR
    
    def test_ema_calculation(self):
        """Test EMA calculation."""
        prices = list(range(1, 21))  # 1 to 20
        for price in prices:
            self.ti.add_price(price)
        
        ema = self.ti.calculate_ema(period=10)
        
        assert ema is not None
        # EMA should be close to recent prices in uptrend
        ma = self.ti.calculate_ma(period=10)
        # EMA gives more weight to recent prices, so should be >= MA in uptrend
        assert ema >= ma * 0.99  # Allow small tolerance
    
    def test_bollinger_bands(self):
        """Test Bollinger Bands calculation."""
        # Add prices with some volatility
        prices = [100, 102, 98, 101, 99, 103, 97, 102, 100, 101,
                  99, 103, 98, 102, 100, 104, 96, 103, 99, 102]
        
        for price in prices:
            self.ti.add_price(price)
        
        bb = self.ti.calculate_bollinger_bands(period=20, std_dev=2.0)
        
        assert bb is not None
        assert 'upper' in bb
        assert 'middle' in bb
        assert 'lower' in bb
        
        # Upper should be > middle > lower
        assert bb['upper'] > bb['middle'] > bb['lower']
        
        # Middle should be close to average
        assert abs(bb['middle'] - 100) < 5
    
    def test_get_all_indicators(self):
        """Test getting all indicators at once."""
        # Add enough data
        for i in range(30):
            self.ti.add_price(100.0 + i, 100.0 + i + 1, 100.0 + i - 1, 1000 + i * 10)
        
        indicators = self.ti.get_all()
        
        assert 'rsi' in indicators
        assert 'ma' in indicators
        assert 'ema' in indicators
        assert 'atr' in indicators
        assert 'current_price' in indicators
        assert 'volume' in indicators
        
        # All should have values
        assert indicators['rsi'] is not None
        assert indicators['ma'] is not None
        assert indicators['atr'] is not None
        assert indicators['current_price'] == 129.0  # Last price
    
    def test_cache_invalidation(self):
        """Test that cache is invalidated when new price added."""
        # Add prices with mixed movements to get RSI in middle range
        prices = [100, 102, 101, 103, 102, 104, 103, 105, 104, 106,
                  105, 104, 106, 105, 107, 106, 108, 107, 109, 108]
        for price in prices:
            self.ti.add_price(price)
        
        rsi1 = self.ti.calculate_rsi(period=14)
        
        # Add a downward price to change RSI
        self.ti.add_price(95.0)  # Big drop
        
        rsi2 = self.ti.calculate_rsi(period=14)
        
        # RSI should decrease due to drop
        assert rsi2 < rsi1  # Should decrease due to drop
        assert abs(rsi1 - rsi2) > 1.0  # At least 1 point difference
    
    def test_max_history_limit(self):
        """Test that history is limited to max_history."""
        ti = TechnicalIndicators('TEST', max_history=10)
        
        # Add more than max_history
        for i in range(20):
            ti.add_price(100.0 + i)
        
        # Should only keep last 10
        assert ti.get_history_length() == 10


class TestIndicatorManager:
    """Test cases for IndicatorManager."""
    
    def setup_method(self):
        """Setup for each test."""
        self.manager = IndicatorManager()
    
    def test_initialization(self):
        """Test manager initialization."""
        assert not self.manager.has_symbol('TEST')
    
    def test_process_tick(self):
        """Test processing ticks."""
        tick = {
            'symbol': 'TEST',
            'price': 100.0,
            'high': 101.0,
            'low': 99.0,
            'volume': 1000
        }
        
        self.manager.process_tick(tick)
        
        assert self.manager.has_symbol('TEST')
    
    def test_multiple_symbols(self):
        """Test managing multiple symbols."""
        symbols = ['STOCK1', 'STOCK2', 'STOCK3']
        
        for symbol in symbols:
            tick = {'symbol': symbol, 'price': 100.0}
            self.manager.process_tick(tick)
        
        for symbol in symbols:
            assert self.manager.has_symbol(symbol)
    
    def test_get_indicators(self):
        """Test getting indicators for a symbol."""
        # Add data
        for i in range(30):
            tick = {
                'symbol': 'TEST',
                'price': 100.0 + i,
                'high': 100.0 + i + 1,
                'low': 100.0 + i - 1,
                'volume': 1000
            }
            self.manager.process_tick(tick)
        
        indicators = self.manager.get_indicators('TEST')
        
        assert 'rsi' in indicators
        assert 'ma' in indicators
        assert indicators['rsi'] is not None
    
    def test_get_indicators_nonexistent_symbol(self):
        """Test getting indicators for non-existent symbol."""
        indicators = self.manager.get_indicators('NONEXISTENT')
        assert indicators == {}


def run_tests():
    """Run all tests."""
    print("\n" + "="*80)
    print("RUNNING INDICATOR UNIT TESTS")
    print("="*80 + "\n")
    
    pytest.main([__file__, '-v', '--tb=short'])


if __name__ == "__main__":
    run_tests()
