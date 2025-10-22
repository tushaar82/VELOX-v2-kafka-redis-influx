"""
Unified Data Manager for VELOX Trading System.

Coordinates Redis (hot cache), InfluxDB (time-series), and SQLite (metadata).
Provides a single interface for all data operations.
"""

from .redis_manager import RedisManager
from .influx_manager import InfluxManager
from .sqlite_manager import SQLiteManager
from datetime import datetime
from typing import Dict, List, Optional
import logging

log = logging.getLogger(__name__)


class DataManager:
    """
    Unified interface for all data operations.
    
    Architecture:
    - Redis: Hot cache (positions, indicators, latest ticks)
    - InfluxDB: Time-series data (historical ticks, metrics)
    - SQLite: Trade metadata (relationships, conditions)
    
    Features:
    - Automatic data routing
    - Graceful degradation
    - Transaction coordination
    - Health monitoring
    """
    
    def __init__(self):
        """Initialize all database connections."""
        log.info("Initializing DataManager...")
        
        # Initialize managers
        self.redis = RedisManager()
        self.influx = InfluxManager()
        self.sqlite = SQLiteManager()
        
        # Check health
        redis_ok = self.redis.health_check()
        influx_ok = self.influx.health_check()
        
        log.info(
            f"✓ DataManager initialized: "
            f"Redis={'✓' if redis_ok else '✗'}, "
            f"InfluxDB={'✓' if influx_ok else '✗'}, "
            f"SQLite=✓"
        )
    
    # ==================== Position Operations ====================
    
    def open_position(self, trade_id: str, strategy_id: str, symbol: str,
                     entry_price: float, quantity: int, timestamp: datetime,
                     signal_conditions: dict = None):
        """
        Open new position across all systems.
        
        Args:
            trade_id: Unique trade identifier
            strategy_id: Strategy identifier
            symbol: Symbol name
            entry_price: Entry price
            quantity: Position quantity
            timestamp: Entry timestamp
            signal_conditions: Entry signal conditions
        """
        # SQLite: Store trade metadata
        self.sqlite.insert_trade(
            trade_id, strategy_id, symbol, 'BUY',
            timestamp, entry_price, quantity
        )
        
        # SQLite: Store signal conditions
        if signal_conditions:
            self.sqlite.insert_signal_conditions(
                trade_id, 'entry', signal_conditions, timestamp
            )
        
        # Redis: Cache position
        position_data = {
            'trade_id': trade_id,
            'strategy_id': strategy_id,
            'symbol': symbol,
            'entry_price': entry_price,
            'quantity': quantity,
            'entry_time': timestamp.isoformat()
        }
        self.redis.set_position(strategy_id, symbol, position_data)
        
        # InfluxDB: Write trade execution
        self.influx.write_trade(
            strategy_id, symbol, 'BUY',
            entry_price, quantity, timestamp=timestamp
        )
        
        log.info(f"✓ Position opened: {trade_id} ({strategy_id} {symbol} @ {entry_price})")
    
    def close_position(self, trade_id: str, strategy_id: str, symbol: str,
                      exit_price: float, exit_time: datetime,
                      pnl: float, pnl_pct: float, exit_reason: str):
        """
        Close position across all systems.
        
        Args:
            trade_id: Trade identifier
            strategy_id: Strategy identifier
            symbol: Symbol name
            exit_price: Exit price
            exit_time: Exit timestamp
            pnl: Profit/Loss amount
            pnl_pct: Profit/Loss percentage
            exit_reason: Reason for exit
        """
        # SQLite: Update trade with exit details
        self.sqlite.update_trade_exit(
            trade_id, exit_time, exit_price,
            pnl, pnl_pct, exit_reason
        )
        
        # Redis: Remove position from cache
        self.redis.delete_position(strategy_id, symbol)
        
        # InfluxDB: Write trade execution
        trade = self.sqlite.get_trade(trade_id)
        if trade:
            self.influx.write_trade(
                strategy_id, symbol, 'SELL',
                exit_price, trade['quantity'],
                pnl=pnl, timestamp=exit_time
            )
        
        log.info(f"✓ Position closed: {trade_id} (P&L: ${pnl:.2f}, {pnl_pct:.2f}%)")
    
    def update_position_snapshot(self, strategy_id: str, symbol: str,
                                 current_price: float, quantity: int,
                                 unrealized_pnl: float, unrealized_pnl_pct: float):
        """
        Update position snapshot (for monitoring).
        
        Args:
            strategy_id: Strategy identifier
            symbol: Symbol name
            current_price: Current price
            quantity: Position quantity
            unrealized_pnl: Unrealized P&L
            unrealized_pnl_pct: Unrealized P&L percentage
        """
        # InfluxDB: Write position snapshot
        self.influx.write_position_snapshot(
            strategy_id, symbol, current_price,
            quantity, unrealized_pnl, unrealized_pnl_pct
        )
    
    # ==================== Tick Data ====================
    
    def process_tick(self, symbol: str, tick_data: dict, timestamp: datetime = None):
        """
        Process incoming tick data.
        
        Args:
            symbol: Symbol name
            tick_data: Tick data dict
            timestamp: Tick timestamp
        """
        # Redis: Cache latest tick
        self.redis.set_latest_tick(symbol, tick_data)
        
        # InfluxDB: Store tick history
        self.influx.write_tick(symbol, tick_data, timestamp)
    
    def get_latest_tick(self, symbol: str) -> Optional[dict]:
        """Get latest tick from cache."""
        return self.redis.get_latest_tick(symbol)
    
    # ==================== Indicators ====================
    
    def cache_indicators(self, symbol: str, indicators: dict):
        """
        Cache calculated indicators.
        
        Args:
            symbol: Symbol name
            indicators: Dict of indicator values
        """
        # Redis: Cache for fast access
        self.redis.set_indicators(symbol, indicators)
        
        # InfluxDB: Store for history
        for indicator_type, value in indicators.items():
            if isinstance(value, (int, float)):
                self.influx.write_indicator(symbol, indicator_type, value)
    
    def get_indicators(self, symbol: str) -> Optional[dict]:
        """Get cached indicators."""
        return self.redis.get_indicators(symbol)
    
    # ==================== Strategy Statistics ====================
    
    def update_strategy_stats(self, strategy_id: str, metrics: dict):
        """
        Update strategy statistics.
        
        Args:
            strategy_id: Strategy identifier
            metrics: Dict of metrics
        """
        # Redis: Update counters
        if 'pnl' in metrics:
            self.redis.update_strategy_pnl(strategy_id, metrics['pnl'])
        
        # InfluxDB: Store metrics history
        self.influx.write_strategy_metrics(strategy_id, metrics)
    
    def get_strategy_stats(self, strategy_id: str, days: int = 30) -> dict:
        """
        Get strategy statistics.
        
        Args:
            strategy_id: Strategy identifier
            days: Number of days to analyze
            
        Returns:
            Statistics dict
        """
        # Get from SQLite (trade metadata)
        return self.sqlite.get_strategy_stats(strategy_id, days)
    
    # ==================== Trailing Stop Loss ====================
    
    def update_trailing_sl(self, trade_id: str, strategy_id: str, symbol: str,
                          current_sl: float, highest_price: float, sl_type: str):
        """
        Update trailing stop loss.
        
        Args:
            trade_id: Trade identifier
            strategy_id: Strategy identifier
            symbol: Symbol name
            current_sl: Current stop loss price
            highest_price: Highest price since entry
            sl_type: Type of stop loss
        """
        # Redis: Update SL state
        sl_data = {
            'current_sl': current_sl,
            'highest_price': highest_price,
            'sl_type': sl_type,
            'updated_at': datetime.now().isoformat()
        }
        self.redis.set_sl_state(trade_id, sl_data)
        
        # InfluxDB: Record SL update
        self.influx.write_sl_update(
            strategy_id, symbol, trade_id,
            current_sl, highest_price, sl_type
        )
    
    # ==================== Signal Logging (NEW - for trade verification) ====================

    def log_signal(self, strategy_id: str, symbol: str, action: str,
                  price: float, quantity: int, reason: str,
                  approved: bool, rejection_reason: str = None,
                  indicators: dict = None, timestamp: datetime = None):
        """
        Log trading signal (approved or rejected) for verification.

        Args:
            strategy_id: Strategy identifier
            symbol: Symbol name
            action: Signal action (BUY/SELL)
            price: Signal price
            quantity: Signal quantity
            reason: Signal generation reason
            approved: Whether signal was approved
            rejection_reason: Reason for rejection (if rejected)
            indicators: Dict of indicator values at signal time
            timestamp: Signal timestamp
        """
        status = 'approved' if approved else 'rejected'

        # InfluxDB: Write signal with all details
        self.influx.write_signal(
            strategy_id=strategy_id,
            symbol=symbol,
            action=action,
            price=price,
            quantity=quantity,
            reason=reason,
            status=status,
            rejection_reason=rejection_reason,
            indicators=indicators,
            timestamp=timestamp
        )

        log.debug(f"Signal logged: {strategy_id} {symbol} {action} @ {price} - {status}")

    def log_order_execution(self, strategy_id: str, symbol: str, action: str,
                           order_id: str, requested_price: float,
                           filled_price: float, timestamp: datetime = None):
        """
        Log order execution details for quality analysis.

        Args:
            strategy_id: Strategy identifier
            symbol: Symbol name
            action: Order action (BUY/SELL)
            order_id: Order identifier
            requested_price: Requested execution price
            filled_price: Actual filled price
            timestamp: Execution timestamp
        """
        # Calculate slippage
        slippage = abs(filled_price - requested_price)
        slippage_pct = slippage / requested_price if requested_price > 0 else 0

        # InfluxDB: Write execution details
        self.influx.write_order_execution(
            strategy_id=strategy_id,
            symbol=symbol,
            action=action,
            order_id=order_id,
            requested_price=requested_price,
            filled_price=filled_price,
            slippage=slippage,
            slippage_pct=slippage_pct,
            timestamp=timestamp
        )

        log.debug(f"Order execution logged: {order_id} - Slippage: {slippage_pct:.4%}")

    def log_trade_complete(self, trade_id: str, strategy_id: str, symbol: str,
                          entry_price: float, exit_price: float, quantity: int,
                          pnl: float, pnl_pct: float, duration_seconds: int,
                          exit_reason: str, entry_indicators: dict = None,
                          exit_indicators: dict = None, timestamp: datetime = None):
        """
        Log complete trade details for deep analysis.

        Args:
            trade_id: Trade identifier
            strategy_id: Strategy identifier
            symbol: Symbol name
            entry_price: Entry price
            exit_price: Exit price
            quantity: Trade quantity
            pnl: Profit/Loss
            pnl_pct: P&L percentage
            duration_seconds: Trade duration in seconds
            exit_reason: Reason for exit
            entry_indicators: Indicator values at entry
            exit_indicators: Indicator values at exit
            timestamp: Exit timestamp
        """
        # InfluxDB: Write comprehensive trade details
        self.influx.write_trade_details(
            strategy_id=strategy_id,
            symbol=symbol,
            trade_id=trade_id,
            action='EXIT',
            entry_price=entry_price,
            exit_price=exit_price,
            quantity=quantity,
            pnl=pnl,
            pnl_pct=pnl_pct,
            duration_seconds=duration_seconds,
            exit_reason=exit_reason,
            entry_indicators=entry_indicators,
            exit_indicators=exit_indicators,
            timestamp=timestamp
        )

        log.info(f"Trade complete logged: {trade_id} - P&L: ${pnl:.2f} ({pnl_pct:.2%})")

    # ==================== Queries ====================

    def get_open_positions(self, strategy_id: str = None) -> List[Dict]:
        """Get all open positions."""
        return self.sqlite.get_open_trades(strategy_id)
    
    def get_closed_trades(self, strategy_id: str = None, limit: int = 100) -> List[Dict]:
        """Get closed trades."""
        return self.sqlite.get_closed_trades(strategy_id, limit)
    
    def get_trade(self, trade_id: str) -> Optional[Dict]:
        """Get specific trade details."""
        return self.sqlite.get_trade(trade_id)
    
    def get_daily_summary(self, date: str = None) -> Dict:
        """Get daily trading summary."""
        return self.sqlite.get_daily_summary(date)
    
    # ==================== Health & Monitoring ====================
    
    def health_check(self) -> dict:
        """
        Check health of all systems.
        
        Returns:
            Health status dict
        """
        return {
            'redis': self.redis.health_check(),
            'influxdb': self.influx.health_check(),
            'sqlite': True,  # SQLite is always available
            'overall': 'healthy'
        }
    
    def get_system_info(self) -> dict:
        """
        Get system information.
        
        Returns:
            System info dict
        """
        return {
            'redis': self.redis.get_info() if self.redis.is_connected() else {},
            'influxdb': self.influx.get_bucket_info() if self.influx.is_connected() else {},
            'sqlite': {
                'db_size': self.sqlite.get_database_size(),
                'table_counts': self.sqlite.get_table_counts()
            }
        }
    
    # ==================== Signal Logging ====================
    
    def log_signal(self, signal_data: dict, approved: bool, rejection_reason: str = None):
        """
        Log all signals (approved and rejected).
        
        Args:
            signal_data: Signal dictionary
            approved: Whether signal was approved
            rejection_reason: Reason for rejection if not approved
        """
        try:
            # SQLite: Store signal metadata
            self.sqlite.insert_signal(
                signal_id=f"{signal_data['strategy_id']}_{signal_data['symbol']}_{signal_data['timestamp']}",
                strategy_id=signal_data['strategy_id'],
                symbol=signal_data['symbol'],
                action=signal_data['action'],
                price=signal_data['price'],
                quantity=signal_data['quantity'],
                timestamp=signal_data['timestamp'],
                approved=approved,
                rejection_reason=rejection_reason,
                indicators=signal_data.get('indicators', {})
            )
            
            # InfluxDB: Store for time-series analysis
            self.influx.write_signal(
                strategy_id=signal_data['strategy_id'],
                symbol=signal_data['symbol'],
                action=signal_data['action'],
                approved=approved,
                timestamp=signal_data['timestamp']
            )
        except Exception as e:
            log.error(f"Error logging signal: {e}", exc_info=True)
    
    def log_trade_open(self, trade_id: str, strategy_id: str, symbol: str,
                      entry_price: float, quantity: int, timestamp: datetime,
                      signal_conditions: dict = None):
        """
        Log trade opening (wrapper for open_position).
        
        Args:
            trade_id: Unique trade identifier
            strategy_id: Strategy identifier
            symbol: Symbol name
            entry_price: Entry price
            quantity: Quantity
            timestamp: Entry timestamp
            signal_conditions: Entry signal conditions
        """
        try:
            self.open_position(
                trade_id, strategy_id, symbol,
                entry_price, quantity, timestamp,
                signal_conditions
            )
        except Exception as e:
            log.error(f"Error logging trade open: {e}", exc_info=True)
    
    def log_trade_close(self, trade_id: str, exit_price: float, exit_time: datetime,
                       pnl: float, pnl_pct: float, exit_reason: str,
                       signal_conditions: dict = None):
        """
        Log trade closing.
        
        Args:
            trade_id: Trade identifier
            exit_price: Exit price
            exit_time: Exit timestamp
            pnl: Profit/Loss amount
            pnl_pct: Profit/Loss percentage
            exit_reason: Reason for exit
            signal_conditions: Exit signal conditions
        """
        try:
            # Get trade details
            trade = self.sqlite.get_trade(trade_id)
            if not trade:
                log.warning(f"Trade {trade_id} not found for closing")
                return
            
            # Close position
            self.close_position(
                trade_id, trade['strategy_id'], trade['symbol'],
                exit_price, exit_time, pnl, pnl_pct, exit_reason
            )
            
            # Store exit signal conditions
            if signal_conditions:
                self.sqlite.insert_signal_conditions(
                    trade_id, 'exit', signal_conditions, exit_time
                )
        except Exception as e:
            log.error(f"Error logging trade close: {e}", exc_info=True)
    
    def log_position_update(self, strategy_id: str, symbol: str, current_price: float,
                           quantity: int, unrealized_pnl: float, timestamp: datetime = None):
        """
        Log position snapshot for monitoring.
        
        Args:
            strategy_id: Strategy identifier
            symbol: Symbol name
            current_price: Current price
            quantity: Position quantity
            unrealized_pnl: Unrealized P&L
            timestamp: Snapshot timestamp
        """
        try:
            # Calculate entry price from position
            position = self.redis.get_position(strategy_id, symbol)
            if not position:
                return
            
            entry_price = position.get('entry_price', current_price)
            unrealized_pnl_pct = ((current_price - entry_price) / entry_price) * 100
            
            self.update_position_snapshot(
                strategy_id, symbol, current_price,
                quantity, unrealized_pnl, unrealized_pnl_pct
            )
        except Exception as e:
            log.error(f"Error logging position update: {e}", exc_info=True)
    
    def log_indicator_values(self, symbol: str, indicators: dict, timestamp: datetime = None):
        """
        Log indicator values for analysis.
        
        Args:
            symbol: Symbol name
            indicators: Dict of indicator values
            timestamp: Timestamp
        """
        try:
            self.cache_indicators(symbol, indicators)
        except Exception as e:
            log.error(f"Error logging indicator values: {e}", exc_info=True)
    
    def log_candle(self, symbol: str, timeframe: str, candle_data: dict, timestamp: datetime):
        """
        Log candle data.
        
        Args:
            symbol: Symbol name
            timeframe: Timeframe (e.g., '1min', '5min')
            candle_data: Candle data dict
            timestamp: Candle timestamp
        """
        try:
            # InfluxDB: Store candle data
            self.influx.write_candle(
                symbol=symbol,
                timeframe=timeframe,
                open_price=candle_data['open'],
                high=candle_data['high'],
                low=candle_data['low'],
                close=candle_data['close'],
                volume=candle_data['volume'],
                timestamp=timestamp
            )
        except Exception as e:
            log.error(f"Error logging candle: {e}", exc_info=True)
    
    # ==================== Batch Operations ====================
    
    def batch_log_ticks(self, ticks: List[dict]):
        """
        Batch log ticks for performance.
        
        Args:
            ticks: List of tick data dicts
        """
        try:
            for tick in ticks:
                self.process_tick(
                    tick['symbol'],
                    tick,
                    tick.get('timestamp')
                )
        except Exception as e:
            log.error(f"Error batch logging ticks: {e}", exc_info=True)
    
    def batch_log_indicators(self, indicators_list: List[dict]):
        """
        Batch log indicators for performance.
        
        Args:
            indicators_list: List of dicts with 'symbol' and 'indicators' keys
        """
        try:
            for item in indicators_list:
                self.log_indicator_values(
                    item['symbol'],
                    item['indicators'],
                    item.get('timestamp')
                )
        except Exception as e:
            log.error(f"Error batch logging indicators: {e}", exc_info=True)
    
    # ==================== Query Methods ====================
    
    def get_trade_history(self, strategy_id: str = None, limit: int = 100) -> List[Dict]:
        """
        Retrieve trade history.
        
        Args:
            strategy_id: Optional strategy filter
            limit: Maximum number of trades to return
            
        Returns:
            List of trade dicts
        """
        try:
            return self.get_closed_trades(strategy_id, limit)
        except Exception as e:
            log.error(f"Error getting trade history: {e}", exc_info=True)
            return []
    
    def get_performance_metrics(self, strategy_id: str, date_range: tuple = None) -> Dict:
        """
        Get performance analytics for a strategy.
        
        Args:
            strategy_id: Strategy identifier
            date_range: Optional (start_date, end_date) tuple
            
        Returns:
            Performance metrics dict
        """
        try:
            # Get basic stats from SQLite
            stats = self.get_strategy_stats(strategy_id, days=30)
            
            # Enhance with time-series data from InfluxDB if available
            if self.influx.is_connected():
                # Could add more detailed metrics here
                pass
            
            return stats
        except Exception as e:
            log.error(f"Error getting performance metrics: {e}", exc_info=True)
            return {}
    
    def close(self):
        """Close all connections."""
        self.redis.close()
        self.influx.close()
        self.sqlite.close()
        log.info("✓ DataManager closed")
