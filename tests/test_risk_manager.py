"""
Unit tests for Risk Manager.
"""

import sys
from pathlib import Path
import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.risk_manager import RiskManager, RiskCheckResult


class TestRiskManager:
    """Test cases for Risk Manager."""
    
    def setup_method(self):
        """Setup for each test."""
        config = {
            'max_position_size': 10000,  # Per position
            'max_positions_per_strategy': 3,
            'max_total_positions': 5,
            'max_daily_loss': 5000,
            'max_daily_loss_pct': 0.05,  # 5%
            'initial_capital': 100000
        }
        self.risk_manager = RiskManager(config)
    
    def test_initialization(self):
        """Test risk manager initialization."""
        assert self.risk_manager.max_position_size == 10000
        assert self.risk_manager.max_positions_per_strategy == 3
        assert self.risk_manager.max_total_positions == 5
        assert self.risk_manager.daily_pnl == 0
    
    def test_validate_signal_approved(self):
        """Test signal validation - approved."""
        signal = {
            'strategy_id': 'test',
            'action': 'BUY',
            'symbol': 'TEST',
            'price': 100.0,
            'quantity': 10
        }
        
        result = self.risk_manager.validate_signal(signal, {}, {})
        
        assert result.approved == True
        assert result.reason is None
    
    def test_validate_signal_position_size_exceeded(self):
        """Test signal validation - position size exceeded."""
        signal = {
            'strategy_id': 'test',
            'action': 'BUY',
            'symbol': 'TEST',
            'price': 100.0,
            'quantity': 200  # 200 * 100 = 20000 > 10000 limit
        }
        
        result = self.risk_manager.validate_signal(signal, {}, {})
        
        assert result.approved == False
        assert 'position size' in result.reason.lower()
    
    def test_validate_signal_max_positions_per_strategy(self):
        """Test signal validation - max positions per strategy."""
        # Simulate 3 existing positions for this strategy
        positions = {
            'test': {
                'STOCK1': {'quantity': 10},
                'STOCK2': {'quantity': 10},
                'STOCK3': {'quantity': 10}
            }
        }
        
        signal = {
            'strategy_id': 'test',
            'action': 'BUY',
            'symbol': 'STOCK4',
            'price': 100.0,
            'quantity': 10
        }
        
        result = self.risk_manager.validate_signal(signal, positions, {})
        
        assert result.approved == False
        assert 'max positions per strategy' in result.reason.lower()
    
    def test_validate_signal_max_total_positions(self):
        """Test signal validation - max total positions."""
        # Simulate 5 total positions across strategies
        positions = {
            'strategy1': {
                'STOCK1': {'quantity': 10},
                'STOCK2': {'quantity': 10}
            },
            'strategy2': {
                'STOCK3': {'quantity': 10},
                'STOCK4': {'quantity': 10},
                'STOCK5': {'quantity': 10}
            }
        }
        
        signal = {
            'strategy_id': 'strategy1',
            'action': 'BUY',
            'symbol': 'STOCK6',
            'price': 100.0,
            'quantity': 10
        }
        
        result = self.risk_manager.validate_signal(signal, positions, {})
        
        assert result.approved == False
        assert 'max total positions' in result.reason.lower()
    
    def test_validate_signal_daily_loss_limit(self):
        """Test signal validation - daily loss limit."""
        # Simulate daily loss
        self.risk_manager.daily_pnl = -6000  # Exceeds 5000 limit
        
        signal = {
            'strategy_id': 'test',
            'action': 'BUY',
            'symbol': 'TEST',
            'price': 100.0,
            'quantity': 10
        }
        
        result = self.risk_manager.validate_signal(signal, {}, {})
        
        assert result.approved == False
        assert 'daily loss limit' in result.reason.lower()
    
    def test_validate_signal_sell_always_approved(self):
        """Test that SELL signals are always approved."""
        # Even with daily loss limit exceeded
        self.risk_manager.daily_pnl = -6000
        
        signal = {
            'strategy_id': 'test',
            'action': 'SELL',
            'symbol': 'TEST',
            'price': 100.0,
            'quantity': 10
        }
        
        result = self.risk_manager.validate_signal(signal, {}, {})
        
        # SELL should be approved (exit positions)
        assert result.approved == True
    
    def test_update_daily_pnl(self):
        """Test updating daily P&L."""
        assert self.risk_manager.daily_pnl == 0
        
        self.risk_manager.update_daily_pnl(500)
        assert self.risk_manager.daily_pnl == 500
        
        self.risk_manager.update_daily_pnl(-200)
        assert self.risk_manager.daily_pnl == 300
    
    def test_reset_daily_stats(self):
        """Test resetting daily statistics."""
        self.risk_manager.daily_pnl = 1000
        self.risk_manager.daily_trades = 10
        
        self.risk_manager.reset_daily_stats()
        
        assert self.risk_manager.daily_pnl == 0
        assert self.risk_manager.daily_trades == 0
    
    def test_get_risk_metrics(self):
        """Test getting risk metrics."""
        self.risk_manager.daily_pnl = 1500
        self.risk_manager.daily_trades = 5
        
        metrics = self.risk_manager.get_risk_metrics()
        
        assert metrics['daily_pnl'] == 1500
        assert metrics['daily_trades'] == 5
        assert metrics['max_daily_loss'] == 5000
        # daily_loss_remaining = max_daily_loss + daily_pnl = 5000 + 1500 = 6500
        assert metrics['daily_loss_remaining'] == 6500
    
    def test_is_trading_allowed(self):
        """Test if trading is allowed."""
        assert self.risk_manager.is_trading_allowed() == True
        
        # Exceed daily loss
        self.risk_manager.daily_pnl = -6000
        assert self.risk_manager.is_trading_allowed() == False
        
        # Reset
        self.risk_manager.reset_daily_stats()
        assert self.risk_manager.is_trading_allowed() == True
    
    def test_calculate_position_size(self):
        """Test position size calculation."""
        # With current config, max is 10000
        size = self.risk_manager.calculate_max_position_size(100.0)
        
        # 10000 / 100 = 100 shares
        assert size == 100
    
    def test_validate_multiple_signals(self):
        """Test validating multiple signals."""
        signals = [
            {'strategy_id': 'test', 'action': 'BUY', 'symbol': 'S1', 'price': 100.0, 'quantity': 10},
            {'strategy_id': 'test', 'action': 'BUY', 'symbol': 'S2', 'price': 200.0, 'quantity': 5},
            {'strategy_id': 'test', 'action': 'SELL', 'symbol': 'S3', 'price': 150.0, 'quantity': 10}
        ]
        
        results = []
        for signal in signals:
            result = self.risk_manager.validate_signal(signal, {}, {})
            results.append(result)
        
        # All should be approved (within limits)
        assert all(r.approved for r in results)
    
    def test_position_value_calculation(self):
        """Test position value calculation."""
        signal = {
            'strategy_id': 'test',
            'action': 'BUY',
            'symbol': 'TEST',
            'price': 250.0,
            'quantity': 50
        }
        
        # Value = 250 * 50 = 12500 > 10000 limit
        result = self.risk_manager.validate_signal(signal, {}, {})
        
        assert result.approved == False


def run_tests():
    """Run all tests."""
    print("\n" + "="*80)
    print("RUNNING RISK MANAGER TESTS")
    print("="*80 + "\n")
    
    pytest.main([__file__, '-v', '--tb=short'])


if __name__ == "__main__":
    run_tests()
