"""
Redis Position Tracker - Updates position data in Redis cache
Integrates with data manager to keep position state synchronized
"""
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import redis

logger = logging.getLogger(__name__)


class RedisPositionTracker:
    """Tracks positions in Redis cache for fast dashboard access"""

    def __init__(self, redis_client: Optional[redis.Redis] = None,
                 host: str = 'localhost', port: int = 6379):
        """Initialize position tracker"""

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
                logger.info("Redis position tracker connected")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                self.redis = None

    def update_position(self, strategy_id: str, symbol: str, position_data: Dict[str, Any]):
        """
        Update position in Redis

        Args:
            strategy_id: Strategy identifier
            symbol: Trading symbol
            position_data: Position data dict
        """
        if not self.redis:
            return

        try:
            key = f"position:{strategy_id}:{symbol}"

            # Add timestamp
            position_data['last_update'] = datetime.now().isoformat()

            # Store position data
            self.redis.set(key, json.dumps(position_data), ex=86400)  # 24h TTL

            logger.debug(f"Updated position {key}")
        except Exception as e:
            logger.error(f"Error updating position in Redis: {e}")

    def remove_position(self, strategy_id: str, symbol: str):
        """
        Remove position from Redis (when closed)

        Args:
            strategy_id: Strategy identifier
            symbol: Trading symbol
        """
        if not self.redis:
            return

        try:
            key = f"position:{strategy_id}:{symbol}"
            self.redis.delete(key)
            logger.debug(f"Removed position {key}")
        except Exception as e:
            logger.error(f"Error removing position from Redis: {e}")

    def get_position(self, strategy_id: str, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get position from Redis

        Args:
            strategy_id: Strategy identifier
            symbol: Trading symbol

        Returns:
            Position data dict or None
        """
        if not self.redis:
            return None

        try:
            key = f"position:{strategy_id}:{symbol}"
            data = self.redis.get(key)

            if data:
                return json.loads(data)
        except Exception as e:
            logger.error(f"Error getting position from Redis: {e}")

        return None

    def get_all_positions(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all positions from Redis

        Returns:
            Dict of position_key -> position_data
        """
        if not self.redis:
            return {}

        positions = {}

        try:
            for key in self.redis.scan_iter("position:*"):
                data = self.redis.get(key)
                if data:
                    positions[key] = json.loads(data)
        except Exception as e:
            logger.error(f"Error getting all positions from Redis: {e}")

        return positions

    def update_trailing_sl(self, trade_id: str, sl_data: Dict[str, Any]):
        """
        Update trailing stop-loss data

        Args:
            trade_id: Trade identifier
            sl_data: Stop-loss data dict
        """
        if not self.redis:
            return

        try:
            key = f"sl:{trade_id}"
            sl_data['last_update'] = datetime.now().isoformat()
            self.redis.set(key, json.dumps(sl_data), ex=86400)  # 24h TTL
            logger.debug(f"Updated trailing SL for {trade_id}")
        except Exception as e:
            logger.error(f"Error updating trailing SL in Redis: {e}")

    def close(self):
        """Close Redis connection"""
        if self.redis:
            self.redis.close()
            logger.info("Redis position tracker closed")
