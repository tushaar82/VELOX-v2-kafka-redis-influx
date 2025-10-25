"""
Redis Publisher for real-time dashboard updates
Publishes position updates, trade closures, and price updates to Redis pub/sub
"""
import json
import logging
from typing import Dict, Any, Optional
import redis
from datetime import datetime

logger = logging.getLogger(__name__)


class RedisPubSubPublisher:
    """Publisher for real-time dashboard updates via Redis pub/sub"""

    def __init__(self, host: str = 'localhost', port: int = 6379):
        """Initialize Redis publisher"""
        try:
            self.redis_client = redis.Redis(
                host=host,
                port=port,
                decode_responses=True
            )
            self.redis_client.ping()
            logger.info("Redis publisher connected")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis_client = None

    def _publish(self, channel: str, data: Dict[str, Any]):
        """Publish message to Redis channel"""
        if not self.redis_client:
            return

        try:
            message = json.dumps(data)
            self.redis_client.publish(channel, message)
            logger.debug(f"Published to {channel}: {message[:100]}")
        except Exception as e:
            logger.error(f"Error publishing to {channel}: {e}")

    def publish_position_update(self, position_data: Dict[str, Any]):
        """
        Publish position update

        Args:
            position_data: Position information including:
                - strategy_id
                - symbol
                - quantity
                - entry_price
                - current_price
                - highest_price
                - unrealized_pnl
                - unrealized_pnl_pct
                - trailing_sl (optional)
        """
        data = {
            **position_data,
            'timestamp': datetime.now().isoformat()
        }
        self._publish('position_updates', data)

    def publish_trade_closed(self, trade_data: Dict[str, Any]):
        """
        Publish trade closure

        Args:
            trade_data: Trade information including:
                - trade_id
                - strategy_id
                - symbol
                - entry_price
                - exit_price
                - quantity
                - pnl
                - pnl_pct
                - exit_reason
                - duration_seconds
        """
        data = {
            **trade_data,
            'timestamp': datetime.now().isoformat()
        }
        self._publish('trade_closed', data)

    def publish_price_update(self, symbol: str, price: float, additional_data: Optional[Dict] = None):
        """
        Publish price update

        Args:
            symbol: Trading symbol
            price: Current price
            additional_data: Optional additional data (indicators, etc.)
        """
        data = {
            'symbol': symbol,
            'price': price,
            'timestamp': datetime.now().isoformat()
        }

        if additional_data:
            data.update(additional_data)

        self._publish('price_updates', data)

    def publish_trailing_sl_update(self, trade_id: str, symbol: str, current_sl: float,
                                   previous_sl: Optional[float] = None,
                                   current_price: Optional[float] = None):
        """
        Publish trailing stop-loss update

        Args:
            trade_id: Trade identifier
            symbol: Trading symbol
            current_sl: Current stop-loss price
            previous_sl: Previous stop-loss price
            current_price: Current market price
        """
        data = {
            'trade_id': trade_id,
            'symbol': symbol,
            'current_sl': current_sl,
            'previous_sl': previous_sl,
            'current_price': current_price,
            'timestamp': datetime.now().isoformat()
        }
        self._publish('trailing_sl_updates', data)

    def publish_system_alert(self, alert_type: str, message: str, severity: str = 'info'):
        """
        Publish system alert

        Args:
            alert_type: Type of alert (position_opened, order_rejected, etc.)
            message: Alert message
            severity: Alert severity (info, warning, error)
        """
        data = {
            'type': alert_type,
            'message': message,
            'severity': severity,
            'timestamp': datetime.now().isoformat()
        }
        self._publish('system_alerts', data)

    def close(self):
        """Close Redis connection"""
        if self.redis_client:
            self.redis_client.close()
            logger.info("Redis publisher closed")


# Global instance
_publisher_instance = None


def get_redis_publisher() -> RedisPubSubPublisher:
    """Get or create global Redis publisher instance"""
    global _publisher_instance

    if _publisher_instance is None:
        _publisher_instance = RedisPubSubPublisher()

    return _publisher_instance
