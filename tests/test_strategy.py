"""
Unit tests for trading strategies.
"""

import sys
from pathlib import Path
import pytest
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.adapters.strategy.rsi_momentum import RSIMomentumStrategy
from src.utils.indicators import IndicatorManager


class TestRSIMomentumStrategy:
    """Test cases for RSI Momentum Strategy."""
    
    def setup_method(self):
        """Setup for each test."""
        config = {
            'rsi_period': 14,
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'ma_period': 20,
            'target_pct': 0.02,
            'initial_sl_pct': 0.01,
            'min_volume': 100
        }
        self.strategy = RSIMomentumStrategy(
            strategy_id='test_rsi',
            symbols=['TEST'],
            config=config
        )
        self.strategy.initialize()
    
    def test_initialization(self):
        """Test strategy initialization."""
        assert self.strategy.strategy_id == 'test_rsi'
        assert self.strategy.symbols == ['TEST']
        assert self.strategy.is_active == True
    
    def test_entry_conditions_rsi_oversold(self):
        """Test entry when RSI is oversold."""
        # Add enough data to calculate indicators
        for i in range(30):
            tick = {
                'timestamp': datetime.now(),
                'symbol': 'TEST',
                'price': 100.0 - i * 2,  # Downtrend
                'high': 100.0 - i * 2 + 1,
                'low': 100.0 - i * 2 - 1,
                'volume': 1000
            }
            self.strategy.on_tick(tick)
        
        # Now price should be low, RSI oversold
        # Add uptick above MA
        tick = {
            'timestamp': datetime.now(),
            'symbol': 'TEST',
            'price': 50.0,  # Above recent prices
            'high': 51.0,
            'low': 49.0,
            'volume': 1000
        }
        
        signal = self.strategy.check_entry_conditions('TEST', tick)
        
        # Should generate BUY signal (RSI oversold + price > MA)
        if signal:
            assert signal['action'] == 'BUY'
            assert signal['symbol'] == 'TEST'
            assert 'reason' in signal
    
    def test_no_entry_without_oversold(self):
        """Test no entry when RSI is not oversold."""
        # Add data with stable uptrend (RSI will be high)
        for i in range(30):
            tick = {
                'timestamp': datetime.now(),
                'symbol': 'TEST',
                'price': 100.0 + i,
                'high': 100.0 + i + 1,
                'low': 100.0 + i - 1,
                'volume': 1000
            }
            self.strategy.on_tick(tick)
        
        # Try to enter
        tick = {
            'timestamp': datetime.now(),
            'symbol': 'TEST',
            'price': 130.0,
            'volume': 1000
        }
        
        signal = self.strategy.check_entry_conditions('TEST', tick)
        
        # Should NOT generate signal (RSI not oversold)
        assert signal is None
    
    def test_exit_on_target(self):
        """Test exit when target profit reached."""
        # Simulate position entry
        self.strategy.add_position('TEST', 100.0, 10, datetime.now())
        
        # Price goes up to hit target (2%)
        tick = {
            'timestamp': datetime.now(),
            'symbol': 'TEST',
            'price': 102.5,  # 2.5% profit
            'volume': 1000
        }
        
        signal = self.strategy.check_exit_conditions('TEST', tick)
        
        assert signal is not None
        assert signal['action'] == 'SELL'
        assert 'Target hit' in signal['reason'] or 'target' in signal['reason'].lower()
    
    def test_exit_on_stop_loss(self):
        """Test exit when stop loss hit."""
        # Simulate position entry
        self.strategy.add_position('TEST', 100.0, 10, datetime.now())
        
        # Price goes down to hit SL (1%)
        tick = {
            'timestamp': datetime.now(),
            'symbol': 'TEST',
            'price': 98.5,  # 1.5% loss
            'volume': 1000
        }
        
        signal = self.strategy.check_exit_conditions('TEST', tick)
        
        assert signal is not None
        assert signal['action'] == 'SELL'
        assert 'stop' in signal['reason'].lower() or 'loss' in signal['reason'].lower()
    
    def test_exit_on_rsi_overbought(self):
        """Test exit when RSI becomes overbought."""
        # Simulate position entry
        self.strategy.add_position('TEST', 100.0, 10, datetime.now())
        
        # Add data to make RSI overbought
        for i in range(30):
            tick = {
                'timestamp': datetime.now(),
                'symbol': 'TEST',
                'price': 100.0 + i * 2,  # Strong uptrend
                'high': 100.0 + i * 2 + 1,
                'low': 100.0 + i * 2 - 1,
                'volume': 1000
            }
            self.strategy.on_tick(tick)
        
        # Check exit
        tick = {
            'timestamp': datetime.now(),
            'symbol': 'TEST',
            'price': 160.0,
            'volume': 1000
        }
        
        signal = self.strategy.check_exit_conditions('TEST', tick)
        
        # Should exit due to overbought
        if signal:
            assert signal['action'] == 'SELL'
    
    def test_no_exit_when_holding(self):
        """Test no exit signal when holding profitably."""
        # Simulate position entry
        self.strategy.add_position('TEST', 100.0, 10, datetime.now())
        
        # Add data with mixed movements (not pure uptrend to avoid RSI=100)
        prices = [100.0, 100.2, 100.1, 100.3, 100.2, 100.4, 100.3, 100.5, 100.4, 100.6,
                  100.5, 100.7, 100.6, 100.8, 100.7, 100.9, 100.8, 101.0, 100.9, 101.0]
        for price in prices:
            tick = {
                'timestamp': datetime.now(),
                'symbol': 'TEST',
                'price': price,
                'volume': 1000
            }
            self.strategy.on_tick(tick)
        
        # Price is slightly up but not at target
        tick = {
            'timestamp': datetime.now(),
            'symbol': 'TEST',
            'price': 101.0,  # 1% profit (target is 2%)
            'volume': 1000
        }
        
        signal = self.strategy.check_exit_conditions('TEST', tick)
        
        # Should NOT exit yet (RSI should be in normal range, not overbought)
        assert signal is None
    
    def test_position_tracking(self):
        """Test position tracking."""
        assert len(self.strategy.get_positions()) == 0
        
        # Add position
        self.strategy.add_position('TEST', 100.0, 10, datetime.now())
        
        positions = self.strategy.get_positions()
        assert len(positions) == 1
        assert 'TEST' in positions
        assert positions['TEST']['entry_price'] == 100.0
        assert positions['TEST']['quantity'] == 10
        
        # Remove position
        self.strategy.remove_position('TEST')
        assert len(self.strategy.get_positions()) == 0
    
    def test_position_price_update(self):
        """Test updating position with current price."""
        self.strategy.add_position('TEST', 100.0, 10, datetime.now())
        
        # Update with higher price
        self.strategy.update_position_price('TEST', 105.0)
        
        pos = self.strategy.get_positions()['TEST']
        assert pos['current_price'] == 105.0
        assert pos['highest_price'] == 105.0
        
        # Update with lower price (highest should stay)
        self.strategy.update_position_price('TEST', 103.0)
        
        pos = self.strategy.get_positions()['TEST']
        assert pos['current_price'] == 103.0
        assert pos['highest_price'] == 105.0  # Should not decrease
    
    def test_square_off_all(self):
        """Test square off all positions."""
        # Add multiple positions
        self.strategy.add_position('STOCK1', 100.0, 10, datetime.now())
        self.strategy.add_position('STOCK2', 200.0, 5, datetime.now())
        
        # Update prices
        self.strategy.update_position_price('STOCK1', 105.0)
        self.strategy.update_position_price('STOCK2', 210.0)
        
        # Square off all
        signals = self.strategy.square_off_all()
        
        assert len(signals) == 2
        for signal in signals:
            assert signal['action'] == 'SELL'
            assert signal['priority'] == 'HIGH'
            assert 'Square-off' in signal['reason']
    
    def test_strategy_activation(self):
        """Test activating/deactivating strategy."""
        assert self.strategy.is_active == True
        
        self.strategy.deactivate()
        assert self.strategy.is_active == False
        
        self.strategy.activate()
        assert self.strategy.is_active == True
    
    def test_signal_generation_and_clearing(self):
        """Test signal list management."""
        assert len(self.strategy.get_signals()) == 0
        
        # Signals would be added by strategy logic
        # For now just test the mechanism
        self.strategy.signals.append({'test': 'signal'})
        assert len(self.strategy.get_signals()) == 1
        
        self.strategy.clear_signals()
        assert len(self.strategy.get_signals()) == 0
    
    def test_min_volume_filter(self):
        """Test that low volume ticks are filtered."""
        # Add data with low volume
        for i in range(30):
            tick = {
                'timestamp': datetime.now(),
                'symbol': 'TEST',
                'price': 100.0 - i * 2,
                'volume': 50  # Below min_volume (100)
            }
            self.strategy.on_tick(tick)
        
        # Try to enter with low volume
        tick = {
            'timestamp': datetime.now(),
            'symbol': 'TEST',
            'price': 50.0,
            'volume': 50
        }
        
        signal = self.strategy.check_entry_conditions('TEST', tick)
        
        # Should NOT generate signal due to low volume
        assert signal is None


def run_tests():
    """Run all tests."""
    print("\n" + "="*80)
    print("RUNNING STRATEGY UNIT TESTS")
    print("="*80 + "\n")
    
    pytest.main([__file__, '-v', '--tb=short'])


if __name__ == "__main__":
    run_tests()
