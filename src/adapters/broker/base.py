"""
Base abstract class for broker adapters.
Defines the interface for order execution and position management.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from enum import Enum


class OrderType(Enum):
    """Order types."""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"
    STOP_LOSS_LIMIT = "STOP_LOSS_LIMIT"


class OrderAction(Enum):
    """Order actions."""
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(Enum):
    """Order status."""
    PENDING = "PENDING"
    OPEN = "OPEN"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class BrokerAdapter(ABC):
    """Abstract base class for broker adapters."""
    
    @abstractmethod
    def connect(self) -> bool:
        """
        Connect to the broker.
        
        Returns:
            True if connection successful, False otherwise
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from the broker."""
        pass
    
    @abstractmethod
    def place_order(self, symbol: str, action: OrderAction, quantity: int, 
                   order_type: OrderType, price: Optional[float] = None) -> Dict:
        """
        Place an order.
        
        Args:
            symbol: Symbol to trade
            action: BUY or SELL
            quantity: Number of shares
            order_type: Order type (MARKET, LIMIT, etc.)
            price: Limit price (required for LIMIT orders)
            
        Returns:
            Order dictionary with keys:
            - order_id: Unique order identifier
            - symbol: Symbol
            - action: BUY/SELL
            - quantity: Quantity
            - order_type: Order type
            - status: Order status
            - filled_price: Execution price (if filled)
            - filled_quantity: Filled quantity
            - timestamp: Order timestamp
        """
        pass
    
    @abstractmethod
    def get_order_status(self, order_id: str) -> Dict:
        """
        Get status of an order.
        
        Args:
            order_id: Order identifier
            
        Returns:
            Order status dictionary
        """
        pass
    
    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an order.
        
        Args:
            order_id: Order identifier
            
        Returns:
            True if cancellation successful
        """
        pass
    
    @abstractmethod
    def get_positions(self) -> List[Dict]:
        """
        Get all open positions.
        
        Returns:
            List of position dictionaries with keys:
            - symbol: Symbol
            - quantity: Position size (positive for long, negative for short)
            - average_price: Average entry price
            - current_price: Current market price
            - pnl: Unrealized P&L
            - pnl_pct: Unrealized P&L percentage
        """
        pass
    
    @abstractmethod
    def get_position(self, symbol: str) -> Optional[Dict]:
        """
        Get position for a specific symbol.
        
        Args:
            symbol: Symbol to query
            
        Returns:
            Position dictionary or None if no position
        """
        pass
    
    @abstractmethod
    def get_account_info(self) -> Dict:
        """
        Get account information.
        
        Returns:
            Account dictionary with keys:
            - capital: Total capital
            - available_margin: Available margin
            - used_margin: Used margin
            - pnl: Total P&L
        """
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """
        Check if connected to broker.
        
        Returns:
            True if connected
        """
        pass
