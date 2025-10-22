"""
Simulated broker adapter for testing and backtesting.
Maintains internal state and simulates order execution.
"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional
import random

from .base import BrokerAdapter, OrderType, OrderAction, OrderStatus
from ...utils.logging_config import get_logger


class SimulatedBrokerAdapter(BrokerAdapter):
    """Simulated broker for testing."""
    
    def __init__(self, initial_capital: float = 100000.0, slippage_pct: float = 0.001):
        """
        Initialize simulated broker.
        
        Args:
            initial_capital: Starting capital
            slippage_pct: Slippage percentage (0.001 = 0.1%)
        """
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.slippage_pct = slippage_pct
        
        self.logger = get_logger('broker.simulated')
        
        # State
        self.connected = False
        self.orders = {}  # order_id -> order_dict
        self.positions = {}  # symbol -> position_dict
        self.current_prices = {}  # symbol -> price
        self.order_history = []
        
        self.logger.info(f"SimulatedBroker initialized with capital={initial_capital}")
    
    def connect(self) -> bool:
        """Connect to simulated broker."""
        self.connected = True
        self.logger.info("Connected to simulated broker")
        return True
    
    def disconnect(self) -> None:
        """Disconnect from simulated broker."""
        self.connected = False
        self.logger.info("Disconnected from simulated broker")
    
    def is_connected(self) -> bool:
        """Check connection status."""
        return self.connected
    
    def update_market_price(self, symbol: str, price: float):
        """
        Update current market price for a symbol.
        
        Args:
            symbol: Symbol name
            price: Current price
        """
        self.current_prices[symbol] = price
        
        # Update position P&L
        if symbol in self.positions:
            pos = self.positions[symbol]
            pos['current_price'] = price
            pos['pnl'] = (price - pos['average_price']) * pos['quantity']
            pos['pnl_pct'] = ((price - pos['average_price']) / pos['average_price']) * 100
    
    def place_order(self, symbol: str, action: OrderAction, quantity: int,
                   order_type: OrderType, price: Optional[float] = None) -> Dict:
        """Place an order."""
        if not self.connected:
            raise RuntimeError("Not connected to broker")
        
        order_id = str(uuid.uuid4())[:8]
        
        order = {
            'order_id': order_id,
            'symbol': symbol,
            'action': action.value if isinstance(action, OrderAction) else action,
            'quantity': quantity,
            'order_type': order_type.value if isinstance(order_type, OrderType) else order_type,
            'limit_price': price,
            'status': OrderStatus.PENDING.value,
            'filled_price': None,
            'filled_quantity': 0,
            'timestamp': datetime.now(),
            'fill_timestamp': None
        }
        
        self.orders[order_id] = order
        
        # For market orders, execute immediately
        if order_type == OrderType.MARKET or order_type == 'MARKET':
            self._execute_market_order(order)
        
        self.logger.info(
            f"Order placed: {order_id} {action} {quantity} {symbol} @ "
            f"{order_type} {price if price else 'MARKET'}"
        )
        
        return order.copy()
    
    def _execute_market_order(self, order: Dict):
        """Execute a market order with simulated slippage."""
        symbol = order['symbol']
        
        if symbol not in self.current_prices:
            order['status'] = OrderStatus.REJECTED.value
            self.logger.error(f"Order {order['order_id']}: No price available for {symbol}")
            return
        
        base_price = self.current_prices[symbol]
        
        # Apply slippage
        if order['action'] == 'BUY':
            # Buy at slightly higher price
            slippage = random.uniform(0.0005, self.slippage_pct)
            filled_price = base_price * (1 + slippage)
        else:
            # Sell at slightly lower price
            slippage = random.uniform(0.0005, self.slippage_pct)
            filled_price = base_price * (1 - slippage)
        
        # Check if we have enough capital
        if order['action'] == 'BUY':
            required_capital = filled_price * order['quantity']
            if required_capital > self.capital:
                order['status'] = OrderStatus.REJECTED.value
                self.logger.error(
                    f"Order {order['order_id']}: Insufficient capital. "
                    f"Required: {required_capital}, Available: {self.capital}"
                )
                return
        
        # Fill the order
        order['status'] = OrderStatus.FILLED.value
        order['filled_price'] = round(filled_price, 2)
        order['filled_quantity'] = order['quantity']
        order['fill_timestamp'] = datetime.now()
        
        # Update position
        self._update_position(order)
        
        # Update capital
        if order['action'] == 'BUY':
            self.capital -= filled_price * order['quantity']
        else:
            self.capital += filled_price * order['quantity']
        
        self.order_history.append(order.copy())
        
        self.logger.info(
            f"Order filled: {order['order_id']} {order['action']} "
            f"{order['quantity']} {order['symbol']} @ {filled_price:.2f}"
        )
    
    def _update_position(self, order: Dict):
        """Update position after order fill."""
        symbol = order['symbol']
        action = order['action']
        quantity = order['filled_quantity']
        price = order['filled_price']
        
        if symbol not in self.positions:
            # New position
            if action == 'BUY':
                self.positions[symbol] = {
                    'symbol': symbol,
                    'quantity': quantity,
                    'average_price': price,
                    'current_price': price,
                    'pnl': 0.0,
                    'pnl_pct': 0.0,
                    'entry_timestamp': order['fill_timestamp']
                }
                self.logger.info(f"Position opened: {symbol} {quantity} @ {price:.2f}")
        else:
            # Existing position
            pos = self.positions[symbol]
            
            if action == 'BUY':
                # Add to position
                total_cost = (pos['average_price'] * pos['quantity']) + (price * quantity)
                pos['quantity'] += quantity
                pos['average_price'] = total_cost / pos['quantity']
                self.logger.info(f"Position increased: {symbol} +{quantity} @ {price:.2f}")
            else:
                # Reduce position
                if quantity >= pos['quantity']:
                    # Close position
                    pnl = (price - pos['average_price']) * pos['quantity']
                    self.logger.info(
                        f"Position closed: {symbol} {pos['quantity']} @ {price:.2f}, "
                        f"P&L: {pnl:.2f} ({pnl/pos['quantity']/pos['average_price']*100:.2f}%)"
                    )
                    del self.positions[symbol]
                else:
                    # Partial close
                    pnl = (price - pos['average_price']) * quantity
                    pos['quantity'] -= quantity
                    self.logger.info(
                        f"Position reduced: {symbol} -{quantity} @ {price:.2f}, "
                        f"P&L: {pnl:.2f}"
                    )
    
    def get_order_status(self, order_id: str) -> Dict:
        """Get order status."""
        if order_id not in self.orders:
            raise ValueError(f"Order {order_id} not found")
        return self.orders[order_id].copy()
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        if order_id not in self.orders:
            return False
        
        order = self.orders[order_id]
        if order['status'] in [OrderStatus.FILLED.value, OrderStatus.CANCELLED.value]:
            return False
        
        order['status'] = OrderStatus.CANCELLED.value
        self.logger.info(f"Order cancelled: {order_id}")
        return True
    
    def get_positions(self) -> List[Dict]:
        """Get all positions."""
        return [pos.copy() for pos in self.positions.values()]
    
    def get_position(self, symbol: str) -> Optional[Dict]:
        """Get position for a symbol."""
        if symbol in self.positions:
            return self.positions[symbol].copy()
        return None
    
    def get_account_info(self) -> Dict:
        """Get account information."""
        total_pnl = sum(pos['pnl'] for pos in self.positions.values())
        used_margin = sum(
            pos['average_price'] * pos['quantity'] 
            for pos in self.positions.values()
        )
        
        return {
            'capital': self.capital,
            'initial_capital': self.initial_capital,
            'available_margin': self.capital,
            'used_margin': used_margin,
            'total_value': self.capital + used_margin,
            'pnl': total_pnl,
            'pnl_pct': (total_pnl / self.initial_capital) * 100 if self.initial_capital > 0 else 0,
            'num_positions': len(self.positions)
        }
    
    def get_order_history(self) -> List[Dict]:
        """Get order history."""
        return self.order_history.copy()
    
    def reset(self):
        """Reset broker to initial state."""
        self.capital = self.initial_capital
        self.orders = {}
        self.positions = {}
        self.current_prices = {}
        self.order_history = []
        self.logger.info("Broker reset to initial state")


if __name__ == "__main__":
    # Test the simulated broker
    from ...utils.logging_config import initialize_logging
    import logging
    
    initialize_logging(log_level=logging.INFO)
    
    print("\n=== Testing Simulated Broker ===\n")
    
    # Create broker
    broker = SimulatedBrokerAdapter(initial_capital=100000)
    broker.connect()
    
    # Update market prices
    broker.update_market_price('RELIANCE', 2450.00)
    broker.update_market_price('TCS', 3200.00)
    
    # Place buy order
    print("1. Placing BUY order for RELIANCE...")
    order1 = broker.place_order('RELIANCE', OrderAction.BUY, 10, OrderType.MARKET)
    print(f"   Order: {order1['order_id']}, Status: {order1['status']}")
    print(f"   Filled at: {order1['filled_price']}")
    
    # Check position
    print("\n2. Checking position...")
    pos = broker.get_position('RELIANCE')
    print(f"   Position: {pos['quantity']} @ {pos['average_price']:.2f}")
    
    # Update price and check P&L
    print("\n3. Updating price to 2475...")
    broker.update_market_price('RELIANCE', 2475.00)
    pos = broker.get_position('RELIANCE')
    print(f"   P&L: {pos['pnl']:.2f} ({pos['pnl_pct']:.2f}%)")
    
    # Place sell order
    print("\n4. Placing SELL order...")
    order2 = broker.place_order('RELIANCE', OrderAction.SELL, 10, OrderType.MARKET)
    print(f"   Order: {order2['order_id']}, Status: {order2['status']}")
    
    # Check account
    print("\n5. Account info:")
    account = broker.get_account_info()
    for key, value in account.items():
        print(f"   {key}: {value}")
    
    print("\n✓ Broker test complete")
