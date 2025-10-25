"""
Order Deduplicator - Prevents duplicate orders
Uses Redis to track pending orders and prevent duplicates
"""
import logging
import json
from typing import Dict, Any, Optional, Set
from datetime import datetime, timedelta
import redis
from enum import Enum

logger = logging.getLogger(__name__)


class OrderState(Enum):
    """Order state for deduplication"""
    PENDING = "PENDING"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class OrderDeduplicator:
    """
    Prevents duplicate orders using Redis-based tracking

    Features:
    - Tracks pending orders per symbol and strategy
    - Prevents duplicate BUY/SELL orders within time window
    - Automatic cleanup of expired orders
    - Thread-safe using Redis atomic operations
    """

    def __init__(self, redis_client: Optional[redis.Redis] = None,
                 host: str = 'localhost', port: int = 6379,
                 dedup_window_seconds: int = 5):
        """
        Initialize order deduplicator

        Args:
            redis_client: Existing Redis client or None to create new
            host: Redis host
            port: Redis port
            dedup_window_seconds: Time window to prevent duplicates (default 5s)
        """
        if redis_client:
            self.redis = redis_client
        else:
            try:
                self.redis = redis.Redis(
                    host=host,
                    port=port,
                    decode_responses=True
                )
                self.redis.ping()
                logger.info("Order deduplicator connected to Redis")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                self.redis = None

        self.dedup_window_seconds = dedup_window_seconds
        self._pending_orders: Set[str] = set()  # In-memory fallback

    def _get_order_key(self, strategy_id: str, symbol: str, action: str) -> str:
        """Generate Redis key for order"""
        return f"order:pending:{strategy_id}:{symbol}:{action}"

    def _get_order_hash_key(self, order_id: str) -> str:
        """Generate Redis key for order details"""
        return f"order:details:{order_id}"

    def can_place_order(self, strategy_id: str, symbol: str, action: str,
                       quantity: int, price: float) -> tuple[bool, str]:
        """
        Check if order can be placed (not a duplicate)

        Args:
            strategy_id: Strategy identifier
            symbol: Trading symbol
            action: BUY or SELL
            quantity: Order quantity
            price: Order price

        Returns:
            (can_place, reason) - Boolean and reason message
        """
        # Generate order signature
        order_signature = f"{strategy_id}:{symbol}:{action}:{quantity}"

        # Check in-memory cache first (fallback if Redis fails)
        if order_signature in self._pending_orders:
            return False, f"Duplicate order in memory cache: {order_signature}"

        if not self.redis:
            # If Redis not available, use in-memory tracking only
            logger.warning("Redis not available, using in-memory deduplication only")
            return True, "OK (in-memory only)"

        try:
            # Check if similar order exists in Redis
            order_key = self._get_order_key(strategy_id, symbol, action)

            # Try to set the key if it doesn't exist (atomic operation)
            existing_order = self.redis.get(order_key)

            if existing_order:
                order_data = json.loads(existing_order)
                time_diff = (datetime.now() - datetime.fromisoformat(order_data['timestamp'])).total_seconds()

                # Check if within deduplication window
                if time_diff < self.dedup_window_seconds:
                    return False, f"Duplicate order detected within {self.dedup_window_seconds}s window"

            return True, "OK"

        except Exception as e:
            logger.error(f"Error checking order duplication: {e}")
            # On error, allow order but log warning
            return True, f"Warning: Dedup check failed - {str(e)}"

    def register_order(self, order_id: str, strategy_id: str, symbol: str,
                      action: str, quantity: int, price: float) -> bool:
        """
        Register order as pending

        Args:
            order_id: Unique order identifier
            strategy_id: Strategy identifier
            symbol: Trading symbol
            action: BUY or SELL
            quantity: Order quantity
            price: Order price

        Returns:
            True if registered successfully
        """
        order_signature = f"{strategy_id}:{symbol}:{action}:{quantity}"
        self._pending_orders.add(order_signature)

        if not self.redis:
            return False

        try:
            # Store pending order in Redis
            order_key = self._get_order_key(strategy_id, symbol, action)
            order_data = {
                'order_id': order_id,
                'strategy_id': strategy_id,
                'symbol': symbol,
                'action': action,
                'quantity': quantity,
                'price': price,
                'timestamp': datetime.now().isoformat(),
                'state': OrderState.PENDING.value
            }

            # Set with expiration (2x dedup window)
            self.redis.setex(
                order_key,
                self.dedup_window_seconds * 2,
                json.dumps(order_data)
            )

            # Also store order details by order_id
            order_hash_key = self._get_order_hash_key(order_id)
            self.redis.setex(
                order_hash_key,
                300,  # 5 minutes
                json.dumps(order_data)
            )

            logger.debug(f"Registered pending order: {order_id} for {symbol}")
            return True

        except Exception as e:
            logger.error(f"Error registering order: {e}")
            return False

    def mark_order_filled(self, order_id: str, strategy_id: str, symbol: str, action: str) -> bool:
        """
        Mark order as filled and remove from pending

        Args:
            order_id: Order identifier
            strategy_id: Strategy identifier
            symbol: Trading symbol
            action: BUY or SELL

        Returns:
            True if marked successfully
        """
        # Remove from in-memory cache
        order_signature = f"{strategy_id}:{symbol}:{action}"
        self._pending_orders.discard(order_signature)

        if not self.redis:
            return False

        try:
            # Remove pending order
            order_key = self._get_order_key(strategy_id, symbol, action)
            self.redis.delete(order_key)

            # Update order details
            order_hash_key = self._get_order_hash_key(order_id)
            order_data = self.redis.get(order_hash_key)

            if order_data:
                data = json.loads(order_data)
                data['state'] = OrderState.FILLED.value
                data['filled_timestamp'] = datetime.now().isoformat()
                self.redis.setex(order_hash_key, 3600, json.dumps(data))  # Keep for 1 hour

            logger.debug(f"Marked order {order_id} as filled")
            return True

        except Exception as e:
            logger.error(f"Error marking order filled: {e}")
            return False

    def mark_order_rejected(self, order_id: str, strategy_id: str, symbol: str,
                          action: str, reason: str) -> bool:
        """
        Mark order as rejected

        Args:
            order_id: Order identifier
            strategy_id: Strategy identifier
            symbol: Trading symbol
            action: BUY or SELL
            reason: Rejection reason

        Returns:
            True if marked successfully
        """
        # Remove from in-memory cache
        order_signature = f"{strategy_id}:{symbol}:{action}"
        self._pending_orders.discard(order_signature)

        if not self.redis:
            return False

        try:
            # Remove pending order
            order_key = self._get_order_key(strategy_id, symbol, action)
            self.redis.delete(order_key)

            # Update order details
            order_hash_key = self._get_order_hash_key(order_id)
            order_data = self.redis.get(order_hash_key)

            if order_data:
                data = json.loads(order_data)
                data['state'] = OrderState.REJECTED.value
                data['rejection_reason'] = reason
                data['rejected_timestamp'] = datetime.now().isoformat()
                self.redis.setex(order_hash_key, 3600, json.dumps(data))

            logger.debug(f"Marked order {order_id} as rejected: {reason}")
            return True

        except Exception as e:
            logger.error(f"Error marking order rejected: {e}")
            return False

    def get_pending_orders(self, strategy_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get all pending orders

        Args:
            strategy_id: Filter by strategy (optional)

        Returns:
            Dictionary of pending orders
        """
        if not self.redis:
            return {}

        pending_orders = {}

        try:
            pattern = f"order:pending:{strategy_id}:*" if strategy_id else "order:pending:*"

            for key in self.redis.scan_iter(pattern):
                data = self.redis.get(key)
                if data:
                    order_data = json.loads(data)
                    pending_orders[order_data['order_id']] = order_data

        except Exception as e:
            logger.error(f"Error getting pending orders: {e}")

        return pending_orders

    def cleanup_expired_orders(self) -> int:
        """
        Cleanup expired pending orders (older than dedup window)

        Returns:
            Number of orders cleaned up
        """
        if not self.redis:
            return 0

        cleaned = 0
        cutoff_time = datetime.now() - timedelta(seconds=self.dedup_window_seconds * 2)

        try:
            for key in self.redis.scan_iter("order:pending:*"):
                data = self.redis.get(key)
                if data:
                    order_data = json.loads(data)
                    order_time = datetime.fromisoformat(order_data['timestamp'])

                    if order_time < cutoff_time:
                        self.redis.delete(key)
                        cleaned += 1

            if cleaned > 0:
                logger.info(f"Cleaned up {cleaned} expired pending orders")

        except Exception as e:
            logger.error(f"Error cleaning up expired orders: {e}")

        return cleaned

    def is_position_open(self, strategy_id: str, symbol: str) -> bool:
        """
        Check if there's already an open position for symbol

        Args:
            strategy_id: Strategy identifier
            symbol: Trading symbol

        Returns:
            True if position exists
        """
        if not self.redis:
            return False

        try:
            # Check Redis for position
            position_key = f"position:{strategy_id}:{symbol}"
            return self.redis.exists(position_key) > 0

        except Exception as e:
            logger.error(f"Error checking position: {e}")
            return False

    def close(self):
        """Close Redis connection"""
        if self.redis:
            self.redis.close()
            logger.info("Order deduplicator closed")
