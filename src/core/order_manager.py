"""
Order and Position Manager.
Handles order execution and position tracking.
"""

from typing import Dict, List, Optional
from datetime import datetime

from ..adapters.broker.base import BrokerAdapter, OrderAction, OrderType, OrderStatus
from ..utils.logging_config import get_logger
from ..utils.kafka_helper import KafkaProducerWrapper


class OrderManager:
    """Manages order execution and tracking."""
    
    def __init__(self, broker: BrokerAdapter, kafka_producer: Optional[KafkaProducerWrapper] = None,
                 data_manager=None):
        """
        Initialize order manager.
        
        Args:
            broker: Broker adapter
            kafka_producer: Optional Kafka producer for publishing events
            data_manager: Optional DataManager for database logging
        """
        self.broker = broker
        self.kafka_producer = kafka_producer
        self.data_manager = data_manager
        self.logger = get_logger('order_manager')
        
        self.pending_orders = {}  # order_id -> order_dict
        self.filled_orders = []
        
        self.logger.info("OrderManager initialized")
    
    def generate_trade_id(self, strategy_id: str, symbol: str, timestamp) -> str:
        """
        Generate unique trade ID.
        
        Args:
            strategy_id: Strategy identifier
            symbol: Symbol name
            timestamp: Trade timestamp
            
        Returns:
            Unique trade ID string
        """
        if isinstance(timestamp, datetime):
            ts_str = timestamp.strftime('%Y%m%d_%H%M%S_%f')
        else:
            ts_str = str(timestamp).replace(':', '').replace('-', '').replace(' ', '_')
        
        # Create unique ID
        trade_id = f"{strategy_id}_{symbol}_{ts_str[:15]}"
        
        return trade_id
    
    def execute_signal(self, signal: Dict) -> Optional[Dict]:
        """
        Execute a trading signal.
        
        Args:
            signal: Signal dictionary with keys:
                - strategy_id: Strategy identifier
                - action: BUY or SELL
                - symbol: Symbol
                - price: Price
                - quantity: Quantity
                - reason: Signal reason
                
        Returns:
            Order dictionary or None if execution failed
        """
        strategy_id = signal['strategy_id']
        action = signal['action']
        symbol = signal['symbol']
        price = signal.get('price')
        quantity = signal['quantity']
        timestamp = signal.get('timestamp', datetime.now())
        
        # Log signal to database before execution
        if self.data_manager:
            try:
                self.data_manager.log_signal(
                    signal_data=signal,
                    approved=True,
                    rejection_reason=None
                )
            except Exception as e:
                self.logger.error(f"Error logging signal: {e}")
        
        price_str = f"{price:.2f}" if price else "MARKET"
        self.logger.info(
            f"[ORDER_EXEC] Executing signal: {strategy_id}/{symbol} "
            f"{action} {quantity} @ {price_str}"
        )
        
        try:
            # Place order
            order_action = OrderAction.BUY if action == 'BUY' else OrderAction.SELL
            order = self.broker.place_order(
                symbol=symbol,
                action=order_action,
                quantity=quantity,
                order_type=OrderType.MARKET,
                price=price
            )
            
            # Add strategy context
            order['strategy_id'] = strategy_id
            order['signal_reason'] = signal.get('reason', '')
            
            # Track order
            if order['status'] == OrderStatus.FILLED.value:
                self.filled_orders.append(order)
                
                self.logger.info(
                    f"[ORDER_FILLED] {order['order_id']}: {symbol} {action} "
                    f"{quantity} @ {order['filled_price']:.2f}"
                )
                
                # Log trade to database
                if self.data_manager:
                    try:
                        if action == 'BUY':
                            # Generate trade ID for new position
                            trade_id = self.generate_trade_id(strategy_id, symbol, timestamp)
                            order['trade_id'] = trade_id
                            
                            # Log trade open
                            self.data_manager.log_trade_open(
                                trade_id=trade_id,
                                strategy_id=strategy_id,
                                symbol=symbol,
                                entry_price=order['filled_price'],
                                quantity=order['filled_quantity'],
                                timestamp=order.get('fill_timestamp', timestamp),
                                signal_conditions=signal.get('indicators', {})
                            )
                        elif action == 'SELL':
                            # For SELL, we would need to get trade_id from position
                            # This requires position manager integration
                            # For now, we'll log what we can
                            pass
                    except Exception as e:
                        self.logger.error(f"Error logging trade: {e}")
                
                # Publish to Kafka
                if self.kafka_producer:
                    self._publish_order_fill(order)
            
            else:
                self.pending_orders[order['order_id']] = order
                
                self.logger.warning(
                    f"[ORDER_PENDING] {order['order_id']}: {symbol} {action} "
                    f"{quantity} - Status: {order['status']}"
                )
            
            return order
            
        except Exception as e:
            self.logger.error(
                f"[ORDER_ERROR] Failed to execute signal for {symbol}: {e}",
                exc_info=True
            )
            return None
    
    def _publish_order_fill(self, order: Dict):
        """Publish order fill to Kafka."""
        try:
            fill_event = {
                'event_type': 'order_fill',
                'order_id': order['order_id'],
                'strategy_id': order['strategy_id'],
                'symbol': order['symbol'],
                'action': order['action'],
                'quantity': order['filled_quantity'],
                'price': order['filled_price'],
                'timestamp': order['fill_timestamp'].isoformat() if isinstance(order.get('fill_timestamp'), datetime) else str(order.get('fill_timestamp')),
                'reason': order.get('signal_reason', '')
            }
            
            self.kafka_producer.send(fill_event, topic='order_fills')
            
            self.logger.debug(f"[KAFKA] Published order fill: {order['order_id']}")
            
        except Exception as e:
            self.logger.error(f"[KAFKA_ERROR] Failed to publish order fill: {e}")
    
    def get_order_status(self, order_id: str) -> Optional[Dict]:
        """
        Get order status.
        
        Args:
            order_id: Order identifier
            
        Returns:
            Order dictionary or None
        """
        try:
            return self.broker.get_order_status(order_id)
        except Exception as e:
            self.logger.error(f"Error getting order status for {order_id}: {e}")
            return None
    
    def get_filled_orders(self) -> List[Dict]:
        """Get all filled orders."""
        return self.filled_orders.copy()
    
    def get_pending_orders(self) -> Dict:
        """Get all pending orders."""
        return self.pending_orders.copy()


class PositionManager:
    """Manages positions across strategies."""
    
    def __init__(self, broker: BrokerAdapter, kafka_producer: Optional[KafkaProducerWrapper] = None):
        """
        Initialize position manager.
        
        Args:
            broker: Broker adapter
            kafka_producer: Optional Kafka producer
        """
        self.broker = broker
        self.kafka_producer = kafka_producer
        self.logger = get_logger('position_manager')
        
        # Track positions by strategy
        self.strategy_positions = {}  # strategy_id -> {symbol: position_info}
        
        self.logger.info("PositionManager initialized")
    
    def update_position(self, strategy_id: str, symbol: str, order: Dict):
        """
        Update position after order fill.
        
        Args:
            strategy_id: Strategy identifier
            symbol: Symbol
            order: Filled order dictionary
        """
        if strategy_id not in self.strategy_positions:
            self.strategy_positions[strategy_id] = {}
        
        action = order['action']
        quantity = order['filled_quantity']
        price = order['filled_price']
        
        if action == 'BUY':
            if symbol in self.strategy_positions[strategy_id]:
                # Add to existing position
                pos = self.strategy_positions[strategy_id][symbol]
                total_cost = (pos['average_price'] * pos['quantity']) + (price * quantity)
                pos['quantity'] += quantity
                pos['average_price'] = total_cost / pos['quantity']
                
                self.logger.info(
                    f"[POSITION_UPDATE] {strategy_id}/{symbol}: "
                    f"Increased to {pos['quantity']} @ {pos['average_price']:.2f}"
                )
            else:
                # New position
                self.strategy_positions[strategy_id][symbol] = {
                    'symbol': symbol,
                    'quantity': quantity,
                    'average_price': price,
                    'entry_timestamp': order.get('fill_timestamp', datetime.now())
                }
                
                self.logger.info(
                    f"[POSITION_OPEN] {strategy_id}/{symbol}: "
                    f"{quantity} @ {price:.2f}"
                )
        
        elif action == 'SELL':
            if symbol in self.strategy_positions[strategy_id]:
                pos = self.strategy_positions[strategy_id][symbol]
                
                if quantity >= pos['quantity']:
                    # Close position
                    pnl = (price - pos['average_price']) * pos['quantity']
                    
                    self.logger.info(
                        f"[POSITION_CLOSE] {strategy_id}/{symbol}: "
                        f"{pos['quantity']} @ {price:.2f}, P&L: {pnl:.2f}"
                    )
                    
                    del self.strategy_positions[strategy_id][symbol]
                else:
                    # Reduce position
                    pnl = (price - pos['average_price']) * quantity
                    pos['quantity'] -= quantity
                    
                    self.logger.info(
                        f"[POSITION_REDUCE] {strategy_id}/{symbol}: "
                        f"Reduced by {quantity}, remaining: {pos['quantity']}, P&L: {pnl:.2f}"
                    )
        
        # Publish position update
        if self.kafka_producer:
            self._publish_position_update(strategy_id, symbol)
    
    def _publish_position_update(self, strategy_id: str, symbol: str):
        """Publish position update to Kafka."""
        try:
            if strategy_id in self.strategy_positions and symbol in self.strategy_positions[strategy_id]:
                pos = self.strategy_positions[strategy_id][symbol]
                
                position_event = {
                    'event_type': 'position_update',
                    'strategy_id': strategy_id,
                    'symbol': symbol,
                    'quantity': pos['quantity'],
                    'average_price': pos['average_price'],
                    'timestamp': datetime.now().isoformat()
                }
                
                self.kafka_producer.send(position_event, topic='positions')
                
                self.logger.debug(f"[KAFKA] Published position update: {strategy_id}/{symbol}")
            
        except Exception as e:
            self.logger.error(f"[KAFKA_ERROR] Failed to publish position update: {e}")
    
    def get_positions(self, strategy_id: Optional[str] = None) -> Dict:
        """
        Get positions.
        
        Args:
            strategy_id: Optional strategy ID to filter
            
        Returns:
            Dictionary of positions
        """
        if strategy_id:
            return self.strategy_positions.get(strategy_id, {}).copy()
        return self.strategy_positions.copy()
    
    def get_all_positions_count(self) -> int:
        """Get total number of positions across all strategies."""
        return sum(len(positions) for positions in self.strategy_positions.values())


if __name__ == "__main__":
    # Test order and position managers
    from ..utils.logging_config import initialize_logging
    from ..adapters.broker.simulated import SimulatedBrokerAdapter
    import logging
    
    initialize_logging(log_level=logging.INFO)
    
    print("\n=== Testing Order & Position Managers ===\n")
    
    # Create broker
    broker = SimulatedBrokerAdapter(initial_capital=100000)
    broker.connect()
    broker.update_market_price('TEST', 100.0)
    
    # Create managers
    order_mgr = OrderManager(broker)
    pos_mgr = PositionManager(broker)
    
    # Test order execution
    print("1. Executing BUY signal...")
    signal = {
        'strategy_id': 'test_strategy',
        'action': 'BUY',
        'symbol': 'TEST',
        'price': 100.0,
        'quantity': 10,
        'reason': 'Test entry'
    }
    
    order = order_mgr.execute_signal(signal)
    if order:
        print(f"   Order: {order['order_id']}, Status: {order['status']}")
        
        # Update position
        pos_mgr.update_position('test_strategy', 'TEST', order)
    
    # Check positions
    print("\n2. Checking positions...")
    positions = pos_mgr.get_positions('test_strategy')
    print(f"   Positions: {len(positions)}")
    for symbol, pos in positions.items():
        print(f"   {symbol}: {pos['quantity']} @ {pos['average_price']:.2f}")
    
    print("\n✓ Order & Position managers test complete")
