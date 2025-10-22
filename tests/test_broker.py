"""
Unit tests for broker adapters.
"""

import sys
from pathlib import Path
import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.adapters.broker.simulated import SimulatedBrokerAdapter
from src.adapters.broker.base import OrderType, OrderAction, OrderStatus


class TestSimulatedBroker:
    """Test cases for SimulatedBrokerAdapter."""
    
    def setup_method(self):
        """Setup for each test."""
        self.broker = SimulatedBrokerAdapter(initial_capital=100000)
        self.broker.connect()
        self.broker.update_market_price('TEST', 100.0)
    
    def test_connection(self):
        """Test broker connection."""
        assert self.broker.is_connected() == True
        
        self.broker.disconnect()
        assert self.broker.is_connected() == False
        
        self.broker.connect()
        assert self.broker.is_connected() == True
    
    def test_market_buy_order(self):
        """Test placing a market buy order."""
        order = self.broker.place_order('TEST', OrderAction.BUY, 10, OrderType.MARKET)
        
        assert order['status'] == OrderStatus.FILLED.value
        assert order['symbol'] == 'TEST'
        assert order['action'] == 'BUY'
        assert order['quantity'] == 10
        assert order['filled_quantity'] == 10
        assert order['filled_price'] is not None
        assert order['filled_price'] >= 100.0  # Should have slippage
        assert order['filled_price'] <= 100.2  # Max 0.2% slippage
    
    def test_market_sell_order(self):
        """Test placing a market sell order."""
        # First buy
        self.broker.place_order('TEST', OrderAction.BUY, 10, OrderType.MARKET)
        
        # Then sell
        order = self.broker.place_order('TEST', OrderAction.SELL, 10, OrderType.MARKET)
        
        assert order['status'] == OrderStatus.FILLED.value
        assert order['action'] == 'SELL'
        assert order['filled_price'] is not None
        assert order['filled_price'] <= 100.0  # Should have negative slippage
    
    def test_insufficient_capital(self):
        """Test order rejection due to insufficient capital."""
        # Try to buy more than we can afford
        order = self.broker.place_order('TEST', OrderAction.BUY, 10000, OrderType.MARKET)
        
        assert order['status'] == OrderStatus.REJECTED.value
        assert order['filled_price'] is None
    
    def test_position_creation(self):
        """Test position creation after buy order."""
        self.broker.place_order('TEST', OrderAction.BUY, 10, OrderType.MARKET)
        
        pos = self.broker.get_position('TEST')
        
        assert pos is not None
        assert pos['symbol'] == 'TEST'
        assert pos['quantity'] == 10
        assert pos['average_price'] > 0
        assert pos['pnl'] == 0.0  # No price change yet
    
    def test_position_pnl_calculation(self):
        """Test P&L calculation."""
        # Buy at 100
        self.broker.place_order('TEST', OrderAction.BUY, 10, OrderType.MARKET)
        
        # Price goes up to 110
        self.broker.update_market_price('TEST', 110.0)
        
        pos = self.broker.get_position('TEST')
        
        assert pos['current_price'] == 110.0
        assert pos['pnl'] > 0  # Should be profitable
        assert pos['pnl_pct'] > 0
        
        # Approximate check (accounting for slippage)
        assert pos['pnl'] > 90  # Should be around 100 (10 shares * 10 profit)
        assert pos['pnl'] < 110
    
    def test_position_close(self):
        """Test closing a position."""
        # Buy
        self.broker.place_order('TEST', OrderAction.BUY, 10, OrderType.MARKET)
        assert self.broker.get_position('TEST') is not None
        
        # Sell all
        self.broker.place_order('TEST', OrderAction.SELL, 10, OrderType.MARKET)
        assert self.broker.get_position('TEST') is None
    
    def test_position_partial_close(self):
        """Test partially closing a position."""
        # Buy 10
        self.broker.place_order('TEST', OrderAction.BUY, 10, OrderType.MARKET)
        
        # Sell 5
        self.broker.place_order('TEST', OrderAction.SELL, 5, OrderType.MARKET)
        
        pos = self.broker.get_position('TEST')
        assert pos is not None
        assert pos['quantity'] == 5
    
    def test_position_increase(self):
        """Test increasing a position."""
        # Buy 10
        self.broker.place_order('TEST', OrderAction.BUY, 10, OrderType.MARKET)
        
        # Buy 5 more
        self.broker.place_order('TEST', OrderAction.BUY, 5, OrderType.MARKET)
        
        pos = self.broker.get_position('TEST')
        assert pos['quantity'] == 15
    
    def test_multiple_positions(self):
        """Test managing multiple positions."""
        self.broker.update_market_price('STOCK1', 100.0)
        self.broker.update_market_price('STOCK2', 200.0)
        
        self.broker.place_order('STOCK1', OrderAction.BUY, 10, OrderType.MARKET)
        self.broker.place_order('STOCK2', OrderAction.BUY, 5, OrderType.MARKET)
        
        positions = self.broker.get_positions()
        assert len(positions) == 2
        
        symbols = [pos['symbol'] for pos in positions]
        assert 'STOCK1' in symbols
        assert 'STOCK2' in symbols
    
    def test_account_info(self):
        """Test account information."""
        initial_account = self.broker.get_account_info()
        assert initial_account['capital'] == 100000
        assert initial_account['num_positions'] == 0
        
        # Place order
        self.broker.place_order('TEST', OrderAction.BUY, 10, OrderType.MARKET)
        
        account = self.broker.get_account_info()
        assert account['capital'] < 100000  # Capital reduced
        assert account['num_positions'] == 1
        assert account['used_margin'] > 0
    
    def test_order_history(self):
        """Test order history tracking."""
        self.broker.place_order('TEST', OrderAction.BUY, 10, OrderType.MARKET)
        self.broker.place_order('TEST', OrderAction.SELL, 5, OrderType.MARKET)
        
        history = self.broker.get_order_history()
        assert len(history) == 2
        assert history[0]['action'] == 'BUY'
        assert history[1]['action'] == 'SELL'
    
    def test_order_status_query(self):
        """Test querying order status."""
        order = self.broker.place_order('TEST', OrderAction.BUY, 10, OrderType.MARKET)
        order_id = order['order_id']
        
        status = self.broker.get_order_status(order_id)
        assert status['order_id'] == order_id
        assert status['status'] == OrderStatus.FILLED.value
    
    def test_reset(self):
        """Test broker reset."""
        # Place some orders
        self.broker.place_order('TEST', OrderAction.BUY, 10, OrderType.MARKET)
        assert len(self.broker.get_positions()) == 1
        
        # Reset
        self.broker.reset()
        
        assert self.broker.get_account_info()['capital'] == 100000
        assert len(self.broker.get_positions()) == 0
        assert len(self.broker.get_order_history()) == 0
    
    def test_price_update_without_position(self):
        """Test updating price for symbol without position."""
        self.broker.update_market_price('NEWSTOCK', 500.0)
        pos = self.broker.get_position('NEWSTOCK')
        assert pos is None
    
    def test_slippage_consistency(self):
        """Test that slippage is within expected range."""
        orders = []
        for i in range(10):
            order = self.broker.place_order('TEST', OrderAction.BUY, 1, OrderType.MARKET)
            orders.append(order)
        
        for order in orders:
            filled_price = order['filled_price']
            # Slippage should be between 0.05% and 0.1%
            assert filled_price >= 100.05
            assert filled_price <= 100.11


def run_tests():
    """Run all tests."""
    print("\n" + "="*80)
    print("RUNNING BROKER UNIT TESTS")
    print("="*80 + "\n")
    
    pytest.main([__file__, '-v', '--tb=short'])


if __name__ == "__main__":
    run_tests()
