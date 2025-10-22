"""
Redis Manager for VELOX Trading System.

Redis Key Schema:
- position:{strategy_id}:{symbol} → JSON position data
- indicators:{symbol} → JSON indicator values
- signal:latest:{strategy_id} → Latest signal
- tick:latest:{symbol} → Latest tick data
- sl:{trade_id} → Trailing SL state
- stats:strategy:{strategy_id} → Strategy statistics
- stats:daily → Daily aggregate stats
"""

import redis
import json
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import logging

log = logging.getLogger(__name__)


class RedisManager:
    """
    Ultra-fast real-time data access and caching using Redis.
    
    Features:
    - Sub-millisecond data access
    - Automatic TTL for cache expiration
    - Atomic operations for counters
    - Batch operations for performance
    - Health monitoring
    """
    
    def __init__(self, host='localhost', port=6379, db=0):
        """
        Initialize Redis connection.
        
        Args:
            host: Redis server host
            port: Redis server port
            db: Redis database number (0-15)
        """
        try:
            self.client = redis.Redis(
                host=host,
                port=port,
                db=db,
                decode_responses=True,
                socket_keepalive=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            # Test connection
            self.client.ping()
            log.info(f"✓ Redis connected: {host}:{port}")
        except redis.ConnectionError as e:
            log.warning(f"⚠️  Redis connection failed: {e}. Running without Redis cache.")
            self.client = None
        except Exception as e:
            log.error(f"❌ Redis initialization error: {e}")
            self.client = None
    
    def is_connected(self) -> bool:
        """Check if Redis is connected."""
        return self.client is not None
    
    # ==================== Position Management ====================
    
    def set_position(self, strategy_id: str, symbol: str, position_data: dict, ttl: int = 86400):
        """
        Store position with TTL (default 24 hours).
        
        Args:
            strategy_id: Strategy identifier
            symbol: Symbol name
            position_data: Position details dict
            ttl: Time to live in seconds
        """
        if not self.is_connected():
            return False
        
        try:
            key = f"position:{strategy_id}:{symbol}"
            self.client.setex(key, ttl, json.dumps(position_data))
            return True
        except Exception as e:
            log.error(f"Redis set_position error: {e}")
            return False
    
    def get_position(self, strategy_id: str, symbol: str) -> Optional[dict]:
        """
        Retrieve position data.
        
        Args:
            strategy_id: Strategy identifier
            symbol: Symbol name
            
        Returns:
            Position dict or None
        """
        if not self.is_connected():
            return None
        
        try:
            key = f"position:{strategy_id}:{symbol}"
            data = self.client.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            log.error(f"Redis get_position error: {e}")
            return None
    
    def get_all_positions(self) -> Dict[str, dict]:
        """
        Get all open positions.
        
        Returns:
            Dict of {key: position_data}
        """
        if not self.is_connected():
            return {}
        
        try:
            positions = {}
            for key in self.client.scan_iter("position:*"):
                data = self.client.get(key)
                if data:
                    positions[key] = json.loads(data)
            return positions
        except Exception as e:
            log.error(f"Redis get_all_positions error: {e}")
            return {}
    
    def delete_position(self, strategy_id: str, symbol: str):
        """
        Remove closed position.
        
        Args:
            strategy_id: Strategy identifier
            symbol: Symbol name
        """
        if not self.is_connected():
            return False
        
        try:
            key = f"position:{strategy_id}:{symbol}"
            self.client.delete(key)
            return True
        except Exception as e:
            log.error(f"Redis delete_position error: {e}")
            return False
    
    # ==================== Real-time Indicators ====================
    
    def set_indicators(self, symbol: str, indicators: dict, ttl: int = 300):
        """
        Cache indicator values (default 5-min TTL).
        
        Args:
            symbol: Symbol name
            indicators: Indicator values dict
            ttl: Time to live in seconds
        """
        if not self.is_connected():
            return False
        
        try:
            key = f"indicators:{symbol}"
            self.client.setex(key, ttl, json.dumps(indicators))
            return True
        except Exception as e:
            log.error(f"Redis set_indicators error: {e}")
            return False
    
    def get_indicators(self, symbol: str) -> Optional[dict]:
        """
        Get cached indicator values.
        
        Args:
            symbol: Symbol name
            
        Returns:
            Indicators dict or None
        """
        if not self.is_connected():
            return None
        
        try:
            key = f"indicators:{symbol}"
            data = self.client.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            log.error(f"Redis get_indicators error: {e}")
            return None
    
    # ==================== Latest Tick Data ====================
    
    def set_latest_tick(self, symbol: str, tick_data: dict, ttl: int = 60):
        """
        Store most recent tick (1-min TTL).
        
        Args:
            symbol: Symbol name
            tick_data: Tick data dict
            ttl: Time to live in seconds
        """
        if not self.is_connected():
            return False
        
        try:
            key = f"tick:latest:{symbol}"
            # Convert datetime objects to ISO format strings
            serializable_data = {}
            for k, v in tick_data.items():
                if hasattr(v, 'isoformat'):  # datetime object
                    serializable_data[k] = v.isoformat()
                else:
                    serializable_data[k] = v
            self.client.setex(key, ttl, json.dumps(serializable_data))
            return True
        except Exception as e:
            log.error(f"Redis set_latest_tick error: {e}")
            return False
    
    def get_latest_tick(self, symbol: str) -> Optional[dict]:
        """
        Get most recent tick.
        
        Args:
            symbol: Symbol name
            
        Returns:
            Tick data dict or None
        """
        if not self.is_connected():
            return None
        
        try:
            key = f"tick:latest:{symbol}"
            data = self.client.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            log.error(f"Redis get_latest_tick error: {e}")
            return None
    
    # ==================== Trailing SL State ====================
    
    def set_sl_state(self, trade_id: str, sl_data: dict):
        """
        Store trailing SL state.
        
        Args:
            trade_id: Trade identifier
            sl_data: SL state dict
        """
        if not self.is_connected():
            return False
        
        try:
            key = f"sl:{trade_id}"
            self.client.set(key, json.dumps(sl_data))
            return True
        except Exception as e:
            log.error(f"Redis set_sl_state error: {e}")
            return False
    
    def get_sl_state(self, trade_id: str) -> Optional[dict]:
        """
        Get trailing SL state.
        
        Args:
            trade_id: Trade identifier
            
        Returns:
            SL state dict or None
        """
        if not self.is_connected():
            return None
        
        try:
            key = f"sl:{trade_id}"
            data = self.client.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            log.error(f"Redis get_sl_state error: {e}")
            return None
    
    # ==================== Strategy Statistics ====================
    
    def increment_signal_count(self, strategy_id: str, action: str):
        """
        Atomic counter increment for signals.
        
        Args:
            strategy_id: Strategy identifier
            action: Signal action (BUY/SELL)
        """
        if not self.is_connected():
            return False
        
        try:
            key = f"stats:strategy:{strategy_id}:signals:{action}"
            self.client.incr(key)
            self.client.expire(key, 86400)  # Reset daily
            return True
        except Exception as e:
            log.error(f"Redis increment_signal_count error: {e}")
            return False
    
    def update_strategy_pnl(self, strategy_id: str, pnl: float):
        """
        Update strategy P&L.
        
        Args:
            strategy_id: Strategy identifier
            pnl: Profit/Loss value
        """
        if not self.is_connected():
            return False
        
        try:
            key = f"stats:strategy:{strategy_id}:pnl"
            self.client.set(key, pnl)
            return True
        except Exception as e:
            log.error(f"Redis update_strategy_pnl error: {e}")
            return False
    
    def get_strategy_stats(self, strategy_id: str) -> dict:
        """
        Get all strategy statistics.
        
        Args:
            strategy_id: Strategy identifier
            
        Returns:
            Stats dict
        """
        if not self.is_connected():
            return {}
        
        try:
            pattern = f"stats:strategy:{strategy_id}:*"
            stats = {}
            for key in self.client.scan_iter(pattern):
                value = self.client.get(key)
                stat_name = key.split(':')[-1]
                stats[stat_name] = value
            return stats
        except Exception as e:
            log.error(f"Redis get_strategy_stats error: {e}")
            return {}
    
    # ==================== Daily Aggregates ====================
    
    def set_daily_stat(self, metric: str, value: float):
        """
        Set daily statistic.
        
        Args:
            metric: Metric name
            value: Metric value
        """
        if not self.is_connected():
            return False
        
        try:
            key = f"stats:daily:{metric}"
            self.client.set(key, value)
            self.client.expire(key, 86400)  # 24 hours
            return True
        except Exception as e:
            log.error(f"Redis set_daily_stat error: {e}")
            return False
    
    def get_daily_stats(self) -> dict:
        """
        Get all daily statistics.
        
        Returns:
            Daily stats dict
        """
        if not self.is_connected():
            return {}
        
        try:
            stats = {}
            for key in self.client.scan_iter("stats:daily:*"):
                value = self.client.get(key)
                metric_name = key.split(':')[-1]
                try:
                    stats[metric_name] = float(value)
                except (ValueError, TypeError):
                    stats[metric_name] = value
            return stats
        except Exception as e:
            log.error(f"Redis get_daily_stats error: {e}")
            return {}
    
    # ==================== Batch Operations ====================
    
    def batch_set_positions(self, positions: Dict[str, dict]):
        """
        Bulk position updates using pipeline.
        
        Args:
            positions: Dict of {key: position_data}
        """
        if not self.is_connected():
            return False
        
        try:
            pipe = self.client.pipeline()
            for key, data in positions.items():
                pipe.setex(key, 86400, json.dumps(data))
            pipe.execute()
            return True
        except Exception as e:
            log.error(f"Redis batch_set_positions error: {e}")
            return False
    
    # ==================== Health & Maintenance ====================
    
    def health_check(self) -> bool:
        """
        Check Redis connection health.
        
        Returns:
            True if connected and responsive
        """
        if not self.is_connected():
            return False
        
        try:
            return self.client.ping()
        except Exception as e:
            log.error(f"Redis health check failed: {e}")
            return False
    
    def get_info(self) -> dict:
        """
        Get Redis server info.
        
        Returns:
            Server info dict
        """
        if not self.is_connected():
            return {}
        
        try:
            info = self.client.info()
            return {
                'version': info.get('redis_version'),
                'uptime_seconds': info.get('uptime_in_seconds'),
                'connected_clients': info.get('connected_clients'),
                'used_memory_human': info.get('used_memory_human'),
                'total_commands_processed': info.get('total_commands_processed')
            }
        except Exception as e:
            log.error(f"Redis get_info error: {e}")
            return {}
    
    def clear_all(self):
        """
        Clear all keys (USE WITH CAUTION - for testing only).
        """
        if not self.is_connected():
            return False
        
        try:
            self.client.flushdb()
            log.warning("⚠️  Redis database cleared!")
            return True
        except Exception as e:
            log.error(f"Redis clear_all error: {e}")
            return False
    
    def close(self):
        """Close Redis connection."""
        if self.is_connected():
            try:
                self.client.close()
                log.info("Redis connection closed")
            except Exception as e:
                log.error(f"Redis close error: {e}")
