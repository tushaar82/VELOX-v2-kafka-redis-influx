"""
InfluxDB Manager for VELOX Trading System.

InfluxDB Schema:

Measurement: ticks
- tags: symbol, source
- fields: open, high, low, close, volume, bid, ask
- timestamp: nanosecond precision

Measurement: indicators
- tags: symbol, indicator_type
- fields: value, period
- timestamp: nanosecond precision

Measurement: positions
- tags: strategy_id, symbol
- fields: price, quantity, unrealized_pnl, unrealized_pnl_pct
- timestamp: nanosecond precision

Measurement: trailing_sl
- tags: strategy_id, symbol, trade_id
- fields: current_sl, highest_price, sl_type
- timestamp: nanosecond precision

Measurement: trades
- tags: strategy_id, symbol, action
- fields: price, quantity, pnl
- timestamp: nanosecond precision

Measurement: strategy_metrics
- tags: strategy_id
- fields: positions_count, signals_count, pnl, win_rate
- timestamp: nanosecond precision

Measurement: signals (NEW - for trade verification)
- tags: strategy_id, symbol, action, status (approved/rejected)
- fields: price, quantity, reason, rejection_reason, all indicator values
- timestamp: nanosecond precision

Measurement: order_execution (NEW - for execution quality)
- tags: strategy_id, symbol, action, order_id
- fields: requested_price, filled_price, slippage, slippage_pct, fill_time_ms
- timestamp: nanosecond precision

Measurement: trade_details (NEW - comprehensive trade info)
- tags: strategy_id, symbol, trade_id, action
- fields: entry_price, exit_price, quantity, pnl, pnl_pct, duration_seconds, exit_reason
- timestamp: nanosecond precision
"""

from datetime import datetime
import logging
from typing import Optional, List, Dict

log = logging.getLogger(__name__)

try:
    from influxdb_client import InfluxDBClient, Point, WritePrecision
    from influxdb_client.client.write_api import SYNCHRONOUS, ASYNCHRONOUS
    INFLUX_AVAILABLE = True
except ImportError:
    INFLUX_AVAILABLE = False
    log.warning("⚠️  influxdb-client not installed. Run: pip install influxdb-client")


class InfluxManager:
    """
    High-performance time-series storage using InfluxDB.
    
    Features:
    - Nanosecond precision timestamps
    - Asynchronous writes for performance
    - Efficient querying with Flux language
    - Automatic batching
    - Health monitoring
    """
    
    def __init__(self, url='http://localhost:8086', 
                 token='velox-super-secret-token',
                 org='velox', 
                 bucket='trading'):
        """
        Initialize InfluxDB connection.
        
        Args:
            url: InfluxDB server URL
            token: Authentication token
            org: Organization name
            bucket: Bucket name for data storage
        """
        self.url = url
        self.token = token
        self.org = org
        self.bucket = bucket
        self.client = None
        self.write_api = None
        self.query_api = None
        
        if not INFLUX_AVAILABLE:
            log.warning("InfluxDB client not available. Time-series data will not be stored.")
            return
        
        try:
            self.client = InfluxDBClient(url=url, token=token, org=org)
            self.write_api = self.client.write_api(write_options=ASYNCHRONOUS)
            self.query_api = self.client.query_api()
            
            # Test connection
            if self.health_check():
                log.info(f"✓ InfluxDB connected: {url}")
            else:
                log.warning(f"⚠️  InfluxDB connection failed: {url}")
                self.client = None
        except Exception as e:
            log.warning(f"⚠️  InfluxDB initialization failed: {e}. Running without time-series storage.")
            self.client = None
    
    def is_connected(self) -> bool:
        """Check if InfluxDB is connected."""
        return self.client is not None
    
    # ==================== Write Operations ====================
    
    def write_tick(self, symbol: str, tick_data: dict, timestamp: datetime = None):
        """
        Write tick data to InfluxDB.
        
        Args:
            symbol: Symbol name
            tick_data: Dict with open, high, low, close, volume
            timestamp: Timestamp (defaults to now)
        """
        if not self.is_connected():
            return False
        
        try:
            point = Point("ticks") \
                .tag("symbol", symbol) \
                .tag("source", tick_data.get('source', 'simulator')) \
                .field("open", float(tick_data.get('open', tick_data.get('close', 0)))) \
                .field("high", float(tick_data.get('high', tick_data.get('close', 0)))) \
                .field("low", float(tick_data.get('low', tick_data.get('close', 0)))) \
                .field("close", float(tick_data.get('close', 0))) \
                .field("volume", int(tick_data.get('volume', 0))) \
                .field("bid", float(tick_data.get('bid', tick_data.get('close', 0)))) \
                .field("ask", float(tick_data.get('ask', tick_data.get('close', 0)))) \
                .time(timestamp or datetime.utcnow(), WritePrecision.NS)
            
            self.write_api.write(bucket=self.bucket, record=point)
            return True
        except Exception as e:
            log.error(f"InfluxDB write_tick error: {e}")
            return False
    
    def write_indicator(self, symbol: str, indicator_type: str, value: float,
                       period: int = None, timestamp: datetime = None):
        """
        Write indicator value to InfluxDB.
        
        Args:
            symbol: Symbol name
            indicator_type: Type of indicator (RSI, EMA, etc.)
            value: Indicator value
            period: Period used for calculation
            timestamp: Timestamp (defaults to now)
        """
        if not self.is_connected():
            return False
        
        try:
            point = Point("indicators") \
                .tag("symbol", symbol) \
                .tag("indicator_type", indicator_type) \
                .field("value", float(value))
            
            if period:
                point.field("period", int(period))
            
            point.time(timestamp or datetime.utcnow(), WritePrecision.NS)
            self.write_api.write(bucket=self.bucket, record=point)
            return True
        except Exception as e:
            log.error(f"InfluxDB write_indicator error: {e}")
            return False
    
    def write_position_snapshot(self, strategy_id: str, symbol: str,
                                price: float, quantity: int,
                                unrealized_pnl: float, unrealized_pnl_pct: float,
                                timestamp: datetime = None):
        """
        Write position state snapshot to InfluxDB.
        
        Args:
            strategy_id: Strategy identifier
            symbol: Symbol name
            price: Current price
            quantity: Position quantity
            unrealized_pnl: Unrealized P&L
            unrealized_pnl_pct: Unrealized P&L percentage
            timestamp: Timestamp (defaults to now)
        """
        if not self.is_connected():
            return False
        
        try:
            point = Point("positions") \
                .tag("strategy_id", strategy_id) \
                .tag("symbol", symbol) \
                .field("price", float(price)) \
                .field("quantity", int(quantity)) \
                .field("unrealized_pnl", float(unrealized_pnl)) \
                .field("unrealized_pnl_pct", float(unrealized_pnl_pct)) \
                .time(timestamp or datetime.utcnow(), WritePrecision.NS)
            
            self.write_api.write(bucket=self.bucket, record=point)
            return True
        except Exception as e:
            log.error(f"InfluxDB write_position_snapshot error: {e}")
            return False
    
    def write_sl_update(self, strategy_id: str, symbol: str, trade_id: str,
                       current_sl: float, highest_price: float,
                       sl_type: str, timestamp: datetime = None):
        """
        Write trailing SL update to InfluxDB.
        
        Args:
            strategy_id: Strategy identifier
            symbol: Symbol name
            trade_id: Trade identifier
            current_sl: Current stop loss price
            highest_price: Highest price since entry
            sl_type: Type of stop loss
            timestamp: Timestamp (defaults to now)
        """
        if not self.is_connected():
            return False
        
        try:
            point = Point("trailing_sl") \
                .tag("strategy_id", strategy_id) \
                .tag("symbol", symbol) \
                .tag("trade_id", trade_id) \
                .tag("sl_type", sl_type) \
                .field("current_sl", float(current_sl)) \
                .field("highest_price", float(highest_price)) \
                .time(timestamp or datetime.utcnow(), WritePrecision.NS)
            
            self.write_api.write(bucket=self.bucket, record=point)
            return True
        except Exception as e:
            log.error(f"InfluxDB write_sl_update error: {e}")
            return False
    
    def write_trade(self, strategy_id: str, symbol: str, action: str,
                   price: float, quantity: int, pnl: float = None,
                   timestamp: datetime = None):
        """
        Write trade execution to InfluxDB.
        
        Args:
            strategy_id: Strategy identifier
            symbol: Symbol name
            action: Trade action (BUY/SELL)
            price: Execution price
            quantity: Trade quantity
            pnl: Profit/Loss (for exits)
            timestamp: Timestamp (defaults to now)
        """
        if not self.is_connected():
            return False
        
        try:
            point = Point("trades") \
                .tag("strategy_id", strategy_id) \
                .tag("symbol", symbol) \
                .tag("action", action) \
                .field("price", float(price)) \
                .field("quantity", int(quantity))
            
            if pnl is not None:
                point.field("pnl", float(pnl))
            
            point.time(timestamp or datetime.utcnow(), WritePrecision.NS)
            self.write_api.write(bucket=self.bucket, record=point)
            return True
        except Exception as e:
            log.error(f"InfluxDB write_trade error: {e}")
            return False
    
    def write_strategy_metrics(self, strategy_id: str, metrics: dict,
                               timestamp: datetime = None):
        """
        Write strategy-level metrics to InfluxDB.
        
        Args:
            strategy_id: Strategy identifier
            metrics: Dict of metric name -> value
            timestamp: Timestamp (defaults to now)
        """
        if not self.is_connected():
            return False
        
        try:
            point = Point("strategy_metrics") \
                .tag("strategy_id", strategy_id)
            
            for key, value in metrics.items():
                if isinstance(value, (int, float)):
                    point.field(key, float(value))
            
            point.time(timestamp or datetime.utcnow(), WritePrecision.NS)
            self.write_api.write(bucket=self.bucket, record=point)
            return True
        except Exception as e:
            log.error(f"InfluxDB write_strategy_metrics error: {e}")
            return False
    
    def write_batch(self, points: list):
        """
        Batch write for performance.

        Args:
            points: List of Point objects
        """
        if not self.is_connected():
            return False

        try:
            self.write_api.write(bucket=self.bucket, record=points)
            return True
        except Exception as e:
            log.error(f"InfluxDB write_batch error: {e}")
            return False

    def write_signal(self, strategy_id: str, symbol: str, action: str,
                    price: float, quantity: int, reason: str,
                    status: str, rejection_reason: str = None,
                    indicators: dict = None, timestamp: datetime = None):
        """
        Write signal (approved or rejected) to InfluxDB for trade verification.

        Args:
            strategy_id: Strategy identifier
            symbol: Symbol name
            action: Signal action (BUY/SELL)
            price: Signal price
            quantity: Signal quantity
            reason: Signal generation reason
            status: Signal status (approved/rejected)
            rejection_reason: Reason for rejection (if rejected)
            indicators: Dict of indicator values at signal time
            timestamp: Timestamp (defaults to now)
        """
        if not self.is_connected():
            return False

        try:
            point = Point("signals") \
                .tag("strategy_id", strategy_id) \
                .tag("symbol", symbol) \
                .tag("action", action) \
                .tag("status", status) \
                .field("price", float(price)) \
                .field("quantity", int(quantity)) \
                .field("reason", reason)

            if rejection_reason:
                point.field("rejection_reason", rejection_reason)

            # Add all indicator values as fields for detailed analysis
            if indicators:
                for key, value in indicators.items():
                    if isinstance(value, (int, float)):
                        point.field(f"ind_{key}", float(value))
                    elif isinstance(value, str):
                        point.field(f"ind_{key}", value)

            point.time(timestamp or datetime.utcnow(), WritePrecision.NS)
            self.write_api.write(bucket=self.bucket, record=point)
            return True
        except Exception as e:
            log.error(f"InfluxDB write_signal error: {e}")
            return False

    def write_order_execution(self, strategy_id: str, symbol: str, action: str,
                             order_id: str, requested_price: float,
                             filled_price: float, slippage: float,
                             slippage_pct: float, fill_time_ms: float = None,
                             timestamp: datetime = None):
        """
        Write order execution details for execution quality analysis.

        Args:
            strategy_id: Strategy identifier
            symbol: Symbol name
            action: Order action (BUY/SELL)
            order_id: Order identifier
            requested_price: Requested execution price
            filled_price: Actual filled price
            slippage: Absolute slippage
            slippage_pct: Slippage percentage
            fill_time_ms: Time to fill in milliseconds
            timestamp: Timestamp (defaults to now)
        """
        if not self.is_connected():
            return False

        try:
            point = Point("order_execution") \
                .tag("strategy_id", strategy_id) \
                .tag("symbol", symbol) \
                .tag("action", action) \
                .tag("order_id", order_id) \
                .field("requested_price", float(requested_price)) \
                .field("filled_price", float(filled_price)) \
                .field("slippage", float(slippage)) \
                .field("slippage_pct", float(slippage_pct))

            if fill_time_ms is not None:
                point.field("fill_time_ms", float(fill_time_ms))

            point.time(timestamp or datetime.utcnow(), WritePrecision.NS)
            self.write_api.write(bucket=self.bucket, record=point)
            return True
        except Exception as e:
            log.error(f"InfluxDB write_order_execution error: {e}")
            return False

    def write_trade_details(self, strategy_id: str, symbol: str, trade_id: str,
                           action: str, entry_price: float = None,
                           exit_price: float = None, quantity: int = None,
                           pnl: float = None, pnl_pct: float = None,
                           duration_seconds: int = None, exit_reason: str = None,
                           entry_indicators: dict = None, exit_indicators: dict = None,
                           timestamp: datetime = None):
        """
        Write comprehensive trade details for deep analysis.

        Args:
            strategy_id: Strategy identifier
            symbol: Symbol name
            trade_id: Trade identifier
            action: Trade action (ENTRY/EXIT)
            entry_price: Entry price
            exit_price: Exit price
            quantity: Trade quantity
            pnl: Profit/Loss
            pnl_pct: P&L percentage
            duration_seconds: Trade duration in seconds
            exit_reason: Reason for exit
            entry_indicators: Indicator values at entry
            exit_indicators: Indicator values at exit
            timestamp: Timestamp (defaults to now)
        """
        if not self.is_connected():
            return False

        try:
            point = Point("trade_details") \
                .tag("strategy_id", strategy_id) \
                .tag("symbol", symbol) \
                .tag("trade_id", trade_id) \
                .tag("action", action)

            if entry_price is not None:
                point.field("entry_price", float(entry_price))
            if exit_price is not None:
                point.field("exit_price", float(exit_price))
            if quantity is not None:
                point.field("quantity", int(quantity))
            if pnl is not None:
                point.field("pnl", float(pnl))
            if pnl_pct is not None:
                point.field("pnl_pct", float(pnl_pct))
            if duration_seconds is not None:
                point.field("duration_seconds", int(duration_seconds))
            if exit_reason:
                point.field("exit_reason", exit_reason)

            # Add entry indicators
            if entry_indicators:
                for key, value in entry_indicators.items():
                    if isinstance(value, (int, float)):
                        point.field(f"entry_{key}", float(value))

            # Add exit indicators
            if exit_indicators:
                for key, value in exit_indicators.items():
                    if isinstance(value, (int, float)):
                        point.field(f"exit_{key}", float(value))

            point.time(timestamp or datetime.utcnow(), WritePrecision.NS)
            self.write_api.write(bucket=self.bucket, record=point)
            return True
        except Exception as e:
            log.error(f"InfluxDB write_trade_details error: {e}")
            return False

    # ==================== Query Operations ====================
    
    def query_tick_range(self, symbol: str, start: str, end: str = None):
        """
        Query tick data for time range.
        
        Args:
            start: ISO format or relative time like '-1h', '-1d'
            end: ISO format or 'now()' (defaults to now)
            
        Returns:
            List of tick records
        """
        if not self.is_connected():
            return []
        
        try:
            end = end or 'now()'
            query = f'''
            from(bucket: "{self.bucket}")
              |> range(start: {start}, stop: {end})
              |> filter(fn: (r) => r["_measurement"] == "ticks")
              |> filter(fn: (r) => r["symbol"] == "{symbol}")
              |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
            '''
            result = self.query_api.query(query=query)
            return self._parse_query_result(result)
        except Exception as e:
            log.error(f"InfluxDB query_tick_range error: {e}")
            return []
    
    def query_indicators(self, symbol: str, indicator_type: str,
                        start: str = '-1h', end: str = 'now()'):
        """
        Query indicator values.
        
        Args:
            symbol: Symbol name
            indicator_type: Type of indicator
            start: Start time (relative or ISO)
            end: End time (relative or ISO)
            
        Returns:
            List of indicator records
        """
        if not self.is_connected():
            return []
        
        try:
            query = f'''
            from(bucket: "{self.bucket}")
              |> range(start: {start}, stop: {end})
              |> filter(fn: (r) => r["_measurement"] == "indicators")
              |> filter(fn: (r) => r["symbol"] == "{symbol}")
              |> filter(fn: (r) => r["indicator_type"] == "{indicator_type}")
            '''
            result = self.query_api.query(query=query)
            return self._parse_query_result(result)
        except Exception as e:
            log.error(f"InfluxDB query_indicators error: {e}")
            return []
    
    def query_position_history(self, strategy_id: str, symbol: str,
                               start: str = '-1h'):
        """
        Query position snapshots.
        
        Args:
            strategy_id: Strategy identifier
            symbol: Symbol name
            start: Start time (relative or ISO)
            
        Returns:
            List of position snapshot records
        """
        if not self.is_connected():
            return []
        
        try:
            query = f'''
            from(bucket: "{self.bucket}")
              |> range(start: {start})
              |> filter(fn: (r) => r["_measurement"] == "positions")
              |> filter(fn: (r) => r["strategy_id"] == "{strategy_id}")
              |> filter(fn: (r) => r["symbol"] == "{symbol}")
              |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
            '''
            result = self.query_api.query(query=query)
            return self._parse_query_result(result)
        except Exception as e:
            log.error(f"InfluxDB query_position_history error: {e}")
            return []
    
    def query_sl_timeline(self, trade_id: str):
        """
        Query trailing SL updates for a trade.
        
        Args:
            trade_id: Trade identifier
            
        Returns:
            List of SL update records
        """
        if not self.is_connected():
            return []
        
        try:
            query = f'''
            from(bucket: "{self.bucket}")
              |> range(start: -24h)
              |> filter(fn: (r) => r["_measurement"] == "trailing_sl")
              |> filter(fn: (r) => r["trade_id"] == "{trade_id}")
              |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
            '''
            result = self.query_api.query(query=query)
            return self._parse_query_result(result)
        except Exception as e:
            log.error(f"InfluxDB query_sl_timeline error: {e}")
            return []
    
    def query_strategy_performance(self, strategy_id: str, start: str = '-24h'):
        """
        Query strategy metrics over time.
        
        Args:
            strategy_id: Strategy identifier
            start: Start time (relative or ISO)
            
        Returns:
            List of strategy metric records
        """
        if not self.is_connected():
            return []
        
        try:
            query = f'''
            from(bucket: "{self.bucket}")
              |> range(start: {start})
              |> filter(fn: (r) => r["_measurement"] == "strategy_metrics")
              |> filter(fn: (r) => r["strategy_id"] == "{strategy_id}")
              |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
            '''
            result = self.query_api.query(query=query)
            return self._parse_query_result(result)
        except Exception as e:
            log.error(f"InfluxDB query_strategy_performance error: {e}")
            return []
    
    def query_trades_summary(self, strategy_id: str = None, start: str = '-24h'):
        """
        Query trade summary statistics.
        
        Args:
            strategy_id: Strategy identifier (optional)
            start: Start time (relative or ISO)
            
        Returns:
            List of trade records
        """
        if not self.is_connected():
            return []
        
        try:
            strategy_filter = f'|> filter(fn: (r) => r["strategy_id"] == "{strategy_id}")' if strategy_id else ''
            
            query = f'''
            from(bucket: "{self.bucket}")
              |> range(start: {start})
              |> filter(fn: (r) => r["_measurement"] == "trades")
              {strategy_filter}
              |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
            '''
            result = self.query_api.query(query=query)
            return self._parse_query_result(result)
        except Exception as e:
            log.error(f"InfluxDB query_trades_summary error: {e}")
            return []
    
    def _parse_query_result(self, result) -> list:
        """
        Parse Flux query result to list of dicts.
        
        Args:
            result: Query result object
            
        Returns:
            List of record dictionaries
        """
        records = []
        try:
            for table in result:
                for record in table.records:
                    records.append(record.values)
        except Exception as e:
            log.error(f"InfluxDB parse error: {e}")
        return records
    
    # ==================== Health & Maintenance ====================
    
    def health_check(self) -> bool:
        """
        Check InfluxDB connection health.
        
        Returns:
            True if connected and responsive
        """
        if not self.is_connected():
            return False
        
        try:
            return self.client.ping()
        except Exception as e:
            log.error(f"InfluxDB health check failed: {e}")
            return False
    
    def get_bucket_info(self) -> dict:
        """
        Get bucket information.
        
        Returns:
            Bucket info dict
        """
        if not self.is_connected():
            return {}
        
        try:
            buckets_api = self.client.buckets_api()
            bucket = buckets_api.find_bucket_by_name(self.bucket)
            if bucket:
                return {
                    'name': bucket.name,
                    'id': bucket.id,
                    'org_id': bucket.org_id,
                    'retention_rules': bucket.retention_rules
                }
        except Exception as e:
            log.error(f"InfluxDB get_bucket_info error: {e}")
        return {}
    
    def close(self):
        """Close InfluxDB connections."""
        if self.is_connected():
            try:
                if self.write_api:
                    self.write_api.close()
                if self.client:
                    self.client.close()
                log.info("InfluxDB connections closed")
            except Exception as e:
                log.error(f"InfluxDB close error: {e}")
