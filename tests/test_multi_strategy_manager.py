"""
Unit tests for Multi-Strategy Manager.
"""

import sys
from pathlib import Path
import pytest
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.multi_strategy_manager import MultiStrategyManager
from src.adapters.strategy.rsi_momentum import RSIMomentumStrategy


class TestMultiStrategyManager:
    """Test cases for MultiStrategyManager."""
    
    def setup_method(self):
        """Setup for each test."""
        self.manager = MultiStrategyManager()
    
    def test_initialization(self):
        """Test manager initialization."""
        assert len(self.manager.get_strategies()) == 0
        assert self.manager.is_running == False
    
    def test_add_strategy(self):
        """Test adding a strategy."""
        config = {
            'rsi_period': 14,
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'ma_period': 20,
            'target_pct': 0.02,
            'initial_sl_pct': 0.01
        }
        
        strategy = RSIMomentumStrategy('rsi_1', ['TEST'], config)
        self.manager.add_strategy(strategy)
        
        strategies = self.manager.get_strategies()
        assert len(strategies) == 1
        assert 'rsi_1' in strategies
    
    def test_add_multiple_strategies(self):
        """Test adding multiple strategies."""
        config1 = {'rsi_period': 14, 'rsi_oversold': 30, 'rsi_overbought': 70, 'ma_period': 20}
        config2 = {'rsi_period': 14, 'rsi_oversold': 25, 'rsi_overbought': 75, 'ma_period': 50}
        
        strategy1 = RSIMomentumStrategy('rsi_aggressive', ['STOCK1'], config1)
        strategy2 = RSIMomentumStrategy('rsi_conservative', ['STOCK2'], config2)
        
        self.manager.add_strategy(strategy1)
        self.manager.add_strategy(strategy2)
        
        strategies = self.manager.get_strategies()
        assert len(strategies) == 2
        assert 'rsi_aggressive' in strategies
        assert 'rsi_conservative' in strategies
    
    def test_remove_strategy(self):
        """Test removing a strategy."""
        config = {'rsi_period': 14}
        strategy = RSIMomentumStrategy('test', ['TEST'], config)
        
        self.manager.add_strategy(strategy)
        assert len(self.manager.get_strategies()) == 1
        
        self.manager.remove_strategy('test')
        assert len(self.manager.get_strategies()) == 0
    
    def test_get_strategy(self):
        """Test getting a specific strategy."""
        config = {'rsi_period': 14}
        strategy = RSIMomentumStrategy('test', ['TEST'], config)
        
        self.manager.add_strategy(strategy)
        
        retrieved = self.manager.get_strategy('test')
        assert retrieved is not None
        assert retrieved.strategy_id == 'test'
    
    def test_get_nonexistent_strategy(self):
        """Test getting non-existent strategy."""
        strategy = self.manager.get_strategy('nonexistent')
        assert strategy is None
    
    def test_process_tick_single_strategy(self):
        """Test processing tick with single strategy."""
        config = {'rsi_period': 14, 'rsi_oversold': 30, 'ma_period': 20, 'min_volume': 100}
        strategy = RSIMomentumStrategy('test', ['TEST'], config)
        strategy.initialize()
        
        self.manager.add_strategy(strategy)
        
        # Process some ticks
        for i in range(30):
            tick = {
                'timestamp': datetime.now(),
                'symbol': 'TEST',
                'price': 100.0 - i * 2,
                'high': 100.0 - i * 2 + 1,
                'low': 100.0 - i * 2 - 1,
                'volume': 1000
            }
            self.manager.process_tick(tick)
        
        # Should have processed ticks
        signals = self.manager.get_all_signals()
        # May or may not have signals depending on conditions
        assert isinstance(signals, list)
    
    def test_process_tick_multiple_strategies(self):
        """Test processing tick with multiple strategies."""
        config1 = {'rsi_period': 14, 'rsi_oversold': 30, 'ma_period': 20}
        config2 = {'rsi_period': 14, 'rsi_oversold': 25, 'ma_period': 50}
        
        strategy1 = RSIMomentumStrategy('rsi_1', ['TEST'], config1)
        strategy2 = RSIMomentumStrategy('rsi_2', ['TEST'], config2)
        
        strategy1.initialize()
        strategy2.initialize()
        
        self.manager.add_strategy(strategy1)
        self.manager.add_strategy(strategy2)
        
        tick = {
            'timestamp': datetime.now(),
            'symbol': 'TEST',
            'price': 100.0,
            'volume': 1000
        }
        
        self.manager.process_tick(tick)
        
        # Both strategies should have processed the tick
        # (even if they don't generate signals)
        assert True  # Just verify no errors
    
    def test_get_all_signals(self):
        """Test getting signals from all strategies."""
        config = {'rsi_period': 14}
        strategy1 = RSIMomentumStrategy('s1', ['TEST'], config)
        strategy2 = RSIMomentumStrategy('s2', ['TEST'], config)
        
        strategy1.initialize()
        strategy2.initialize()
        
        # Manually add signals for testing
        strategy1.signals.append({'strategy_id': 's1', 'action': 'BUY'})
        strategy2.signals.append({'strategy_id': 's2', 'action': 'SELL'})
        
        self.manager.add_strategy(strategy1)
        self.manager.add_strategy(strategy2)
        
        signals = self.manager.get_all_signals()
        
        assert len(signals) == 2
        assert any(s['strategy_id'] == 's1' for s in signals)
        assert any(s['strategy_id'] == 's2' for s in signals)
    
    def test_clear_all_signals(self):
        """Test clearing signals from all strategies."""
        config = {'rsi_period': 14}
        strategy = RSIMomentumStrategy('test', ['TEST'], config)
        strategy.initialize()
        
        strategy.signals.append({'test': 'signal'})
        self.manager.add_strategy(strategy)
        
        assert len(self.manager.get_all_signals()) == 1
        
        self.manager.clear_all_signals()
        
        assert len(self.manager.get_all_signals()) == 0
    
    def test_get_all_positions(self):
        """Test getting positions from all strategies."""
        config = {'rsi_period': 14}
        strategy1 = RSIMomentumStrategy('s1', ['TEST1'], config)
        strategy2 = RSIMomentumStrategy('s2', ['TEST2'], config)
        
        strategy1.initialize()
        strategy2.initialize()
        
        # Add positions
        strategy1.add_position('TEST1', 100.0, 10, datetime.now())
        strategy2.add_position('TEST2', 200.0, 5, datetime.now())
        
        self.manager.add_strategy(strategy1)
        self.manager.add_strategy(strategy2)
        
        positions = self.manager.get_all_positions()
        
        assert len(positions) == 2
        assert 's1' in positions
        assert 's2' in positions
        assert 'TEST1' in positions['s1']
        assert 'TEST2' in positions['s2']
    
    def test_activate_deactivate_strategy(self):
        """Test activating/deactivating a strategy."""
        config = {'rsi_period': 14}
        strategy = RSIMomentumStrategy('test', ['TEST'], config)
        strategy.initialize()
        
        self.manager.add_strategy(strategy)
        
        assert strategy.is_active == True
        
        self.manager.deactivate_strategy('test')
        assert strategy.is_active == False
        
        self.manager.activate_strategy('test')
        assert strategy.is_active == True
    
    def test_square_off_all_strategies(self):
        """Test square off all positions."""
        config = {'rsi_period': 14}
        strategy1 = RSIMomentumStrategy('s1', ['TEST1'], config)
        strategy2 = RSIMomentumStrategy('s2', ['TEST2'], config)
        
        strategy1.initialize()
        strategy2.initialize()
        
        # Add positions
        strategy1.add_position('TEST1', 100.0, 10, datetime.now())
        strategy1.update_position_price('TEST1', 105.0)
        
        strategy2.add_position('TEST2', 200.0, 5, datetime.now())
        strategy2.update_position_price('TEST2', 210.0)
        
        self.manager.add_strategy(strategy1)
        self.manager.add_strategy(strategy2)
        
        # Square off all
        signals = self.manager.square_off_all()
        
        assert len(signals) == 2
        for signal in signals:
            assert signal['action'] == 'SELL'
            assert signal['priority'] == 'HIGH'
    
    def test_get_status(self):
        """Test getting manager status."""
        config = {'rsi_period': 14}
        strategy1 = RSIMomentumStrategy('s1', ['TEST1'], config)
        strategy2 = RSIMomentumStrategy('s2', ['TEST2'], config)
        
        strategy1.initialize()
        strategy2.initialize()
        
        strategy1.add_position('TEST1', 100.0, 10, datetime.now())
        
        self.manager.add_strategy(strategy1)
        self.manager.add_strategy(strategy2)
        
        status = self.manager.get_status()
        
        assert status['num_strategies'] == 2
        assert status['num_active_strategies'] == 2
        assert status['total_positions'] == 1
        assert len(status['strategies']) == 2
    
    def test_start_stop(self):
        """Test starting and stopping manager."""
        assert self.manager.is_running == False
        
        self.manager.start()
        assert self.manager.is_running == True
        
        self.manager.stop()
        assert self.manager.is_running == False
    
    def test_inactive_strategy_no_processing(self):
        """Test that inactive strategies don't process ticks."""
        config = {'rsi_period': 14, 'rsi_oversold': 30, 'ma_period': 20}
        strategy = RSIMomentumStrategy('test', ['TEST'], config)
        strategy.initialize()
        strategy.deactivate()
        
        self.manager.add_strategy(strategy)
        
        # Process tick
        tick = {
            'timestamp': datetime.now(),
            'symbol': 'TEST',
            'price': 100.0,
            'volume': 1000
        }
        
        self.manager.process_tick(tick)
        
        # Should not generate signals (strategy is inactive)
        signals = self.manager.get_all_signals()
        assert len(signals) == 0


def run_tests():
    """Run all tests."""
    print("\n" + "="*80)
    print("RUNNING MULTI-STRATEGY MANAGER TESTS")
    print("="*80 + "\n")
    
    pytest.main([__file__, '-v', '--tb=short'])


if __name__ == "__main__":
    run_tests()
