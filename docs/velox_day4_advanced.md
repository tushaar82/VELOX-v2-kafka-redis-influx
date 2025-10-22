# VELOX DAY 4: ADVANCED ANALYTICS & MONITORING
## High-Performance Trade Analysis with Redis, InfluxDB & Grafana (12-14 hours)

---

## Architecture Overview

**Data Flow:**
```
Market Ticks → Redis (Hot Cache) → InfluxDB (Time-Series) → Grafana (Visualization)
             ↓
          SQLite (Trade Metadata)
             ↓
          Logging System (Structured Logs)
```

**Why This Stack:**
- **Redis**: In-memory cache for real-time data (sub-millisecond access)
- **InfluxDB**: Optimized for time-series data (100x faster than SQLite for metrics)
- **SQLite**: Trade metadata and relationships (ACID compliance)
- **Structured Logging**: JSON logs for ELK stack compatibility
- **Grafana**: Unified visualization layer

---

## MORNING SESSION (6 hours)

### Task 4.1: Advanced Data Storage Layer (2.5 hours)

#### Subtask 4.1.1: Redis Integration (1 hour)

**Purpose:** Ultra-fast real-time data access and caching

**Install & Configure:**

1. **Update `docker-compose.yml`** (10 mins)
```yaml
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes --maxmemory 2gb --maxmemory-policy allkeys-lru
    volumes:
      - redis-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3

volumes:
  redis-data:
```

2. **Create `src/database/redis_manager.py`** (50 mins)

```python
"""
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
from typing import Dict, Optional
from datetime import datetime, timedelta

class RedisManager:
    def __init__(self, host='localhost', port=6379):
        self.client = redis.Redis(
            host=host, 
            port=port, 
            decode_responses=True,
            socket_keepalive=True,
            socket_connect_timeout=5
        )
        self.pipeline = self.client.pipeline()
    
    # Position Management
    def set_position(self, strategy_id: str, symbol: str, position_data: dict, ttl: int = 86400):
        """Store position with 24-hour TTL"""
        key = f"position:{strategy_id}:{symbol}"
        self.client.setex(key, ttl, json.dumps(position_data))
    
    def get_position(self, strategy_id: str, symbol: str) -> Optional[dict]:
        """Retrieve position"""
        key = f"position:{strategy_id}:{symbol}"
        data = self.client.get(key)
        return json.loads(data) if data else None
    
    def get_all_positions(self) -> Dict[str, dict]:
        """Get all open positions"""
        positions = {}
        for key in self.client.scan_iter("position:*"):
            data = self.client.get(key)
            if data:
                positions[key] = json.loads(data)
        return positions
    
    def delete_position(self, strategy_id: str, symbol: str):
        """Remove closed position"""
        key = f"position:{strategy_id}:{symbol}"
        self.client.delete(key)
    
    # Real-time Indicators
    def set_indicators(self, symbol: str, indicators: dict, ttl: int = 300):
        """Cache indicator values (5-min TTL)"""
        key = f"indicators:{symbol}"
        self.client.setex(key, ttl, json.dumps(indicators))
    
    def get_indicators(self, symbol: str) -> Optional[dict]:
        key = f"indicators:{symbol}"
        data = self.client.get(key)
        return json.loads(data) if data else None
    
    # Latest Tick Data
    def set_latest_tick(self, symbol: str, tick_data: dict):
        """Store most recent tick"""
        key = f"tick:latest:{symbol}"
        self.client.setex(key, 60, json.dumps(tick_data))
    
    def get_latest_tick(self, symbol: str) -> Optional[dict]:
        key = f"tick:latest:{symbol}"
        data = self.client.get(key)
        return json.loads(data) if data else None
    
    # Trailing SL State
    def set_sl_state(self, trade_id: str, sl_data: dict):
        """Store trailing SL state"""
        key = f"sl:{trade_id}"
        self.client.set(key, json.dumps(sl_data))
    
    def get_sl_state(self, trade_id: str) -> Optional[dict]:
        key = f"sl:{trade_id}"
        data = self.client.get(key)
        return json.loads(data) if data else None
    
    # Strategy Statistics (with atomic operations)
    def increment_signal_count(self, strategy_id: str, action: str):
        """Atomic counter increment"""
        key = f"stats:strategy:{strategy_id}:signals:{action}"
        self.client.incr(key)
        self.client.expire(key, 86400)  # Reset daily
    
    def update_strategy_pnl(self, strategy_id: str, pnl: float):
        """Update strategy P&L"""
        key = f"stats:strategy:{strategy_id}:pnl"
        self.client.set(key, pnl)
    
    def get_strategy_stats(self, strategy_id: str) -> dict:
        """Get all strategy statistics"""
        pattern = f"stats:strategy:{strategy_id}:*"
        stats = {}
        for key in self.client.scan_iter(pattern):
            stats[key.split(':')[-1]] = self.client.get(key)
        return stats
    
    # Daily Aggregates
    def set_daily_stat(self, metric: str, value: float):
        key = f"stats:daily:{metric}"
        self.client.set(key, value)
        self.client.expire(key, 86400)
    
    def get_daily_stats(self) -> dict:
        stats = {}
        for key in self.client.scan_iter("stats:daily:*"):
            stats[key.split(':')[-1]] = float(self.client.get(key))
        return stats
    
    # Batch Operations (Performance)
    def batch_set_positions(self, positions: Dict[str, dict]):
        """Bulk position updates"""
        pipe = self.client.pipeline()
        for key, data in positions.items():
            pipe.setex(key, 86400, json.dumps(data))
        pipe.execute()
    
    def health_check(self) -> bool:
        """Check Redis connection"""
        try:
            return self.client.ping()
        except:
            return False
```

**Integration Points:**
- `PositionTracker`: Store/retrieve positions in Redis
- `IndicatorManager`: Cache calculated indicators
- `TrailingSLManager`: Store SL state in Redis
- Dashboard API: Read from Redis for sub-ms response

**Validation:**
```python
redis_mgr = RedisManager()
redis_mgr.set_position('rsi_agg', 'RELIANCE', {
    'entry_price': 2450.00,
    'quantity': 10,
    'entry_time': '2024-10-15 10:30:15'
})
pos = redis_mgr.get_position('rsi_agg', 'RELIANCE')
assert pos['entry_price'] == 2450.00
```

---

#### Subtask 4.1.2: InfluxDB Integration (1.5 hours)

**Purpose:** High-performance time-series storage

**Install & Configure:**

1. **Update `docker-compose.yml`** (10 mins)
```yaml
services:
  influxdb:
    image: influxdb:2.7-alpine
    ports:
      - "8086:8086"
    environment:
      - DOCKER_INFLUXDB_INIT_MODE=setup
      - DOCKER_INFLUXDB_INIT_USERNAME=admin
      - DOCKER_INFLUXDB_INIT_PASSWORD=veloxinflux123
      - DOCKER_INFLUXDB_INIT_ORG=velox
      - DOCKER_INFLUXDB_INIT_BUCKET=trading
      - DOCKER_INFLUXDB_INIT_ADMIN_TOKEN=velox-super-secret-token
    volumes:
      - influxdb-data:/var/lib/influxdb2
      - influxdb-config:/etc/influxdb2
    healthcheck:
      test: ["CMD", "influx", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3

volumes:
  influxdb-data:
  influxdb-config:
```

2. **Create `src/database/influx_manager.py`** (1 hour 20 mins)

```python
"""
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
"""

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS, ASYNCHRONOUS
from datetime import datetime
import logging

log = logging.getLogger(__name__)

class InfluxManager:
    def __init__(self, url='http://localhost:8086', token='velox-super-secret-token', 
                 org='velox', bucket='trading'):
        self.client = InfluxDBClient(url=url, token=token, org=org)
        self.write_api = self.client.write_api(write_options=ASYNCHRONOUS)
        self.query_api = self.client.query_api()
        self.bucket = bucket
        self.org = org
    
    # Write Operations
    def write_tick(self, symbol: str, tick_data: dict, timestamp: datetime = None):
        """Write tick data"""
        point = Point("ticks") \
            .tag("symbol", symbol) \
            .tag("source", tick_data.get('source', 'simulator')) \
            .field("open", float(tick_data['open'])) \
            .field("high", float(tick_data['high'])) \
            .field("low", float(tick_data['low'])) \
            .field("close", float(tick_data['close'])) \
            .field("volume", int(tick_data['volume'])) \
            .field("bid", float(tick_data.get('bid', tick_data['close']))) \
            .field("ask", float(tick_data.get('ask', tick_data['close']))) \
            .time(timestamp or datetime.utcnow(), WritePrecision.NS)
        
        self.write_api.write(bucket=self.bucket, record=point)
    
    def write_indicator(self, symbol: str, indicator_type: str, value: float, 
                       period: int = None, timestamp: datetime = None):
        """Write indicator value"""
        point = Point("indicators") \
            .tag("symbol", symbol) \
            .tag("indicator_type", indicator_type) \
            .field("value", float(value))
        
        if period:
            point.field("period", int(period))
        
        point.time(timestamp or datetime.utcnow(), WritePrecision.NS)
        self.write_api.write(bucket=self.bucket, record=point)
    
    def write_position_snapshot(self, strategy_id: str, symbol: str, 
                                price: float, quantity: int, 
                                unrealized_pnl: float, unrealized_pnl_pct: float,
                                timestamp: datetime = None):
        """Write position state snapshot"""
        point = Point("positions") \
            .tag("strategy_id", strategy_id) \
            .tag("symbol", symbol) \
            .field("price", float(price)) \
            .field("quantity", int(quantity)) \
            .field("unrealized_pnl", float(unrealized_pnl)) \
            .field("unrealized_pnl_pct", float(unrealized_pnl_pct)) \
            .time(timestamp or datetime.utcnow(), WritePrecision.NS)
        
        self.write_api.write(bucket=self.bucket, record=point)
    
    def write_sl_update(self, strategy_id: str, symbol: str, trade_id: str,
                       current_sl: float, highest_price: float, 
                       sl_type: str, timestamp: datetime = None):
        """Write trailing SL update"""
        point = Point("trailing_sl") \
            .tag("strategy_id", strategy_id) \
            .tag("symbol", symbol) \
            .tag("trade_id", trade_id) \
            .tag("sl_type", sl_type) \
            .field("current_sl", float(current_sl)) \
            .field("highest_price", float(highest_price)) \
            .time(timestamp or datetime.utcnow(), WritePrecision.NS)
        
        self.write_api.write(bucket=self.bucket, record=point)
    
    def write_trade(self, strategy_id: str, symbol: str, action: str,
                   price: float, quantity: int, pnl: float = None,
                   timestamp: datetime = None):
        """Write trade execution"""
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
    
    def write_strategy_metrics(self, strategy_id: str, metrics: dict,
                               timestamp: datetime = None):
        """Write strategy-level metrics"""
        point = Point("strategy_metrics") \
            .tag("strategy_id", strategy_id)
        
        for key, value in metrics.items():
            if isinstance(value, (int, float)):
                point.field(key, float(value))
        
        point.time(timestamp or datetime.utcnow(), WritePrecision.NS)
        self.write_api.write(bucket=self.bucket, record=point)
    
    # Batch Write (High Performance)
    def write_batch(self, points: list):
        """Batch write for performance"""
        self.write_api.write(bucket=self.bucket, record=points)
    
    # Query Operations
    def query_tick_range(self, symbol: str, start: str, end: str = None):
        """Query tick data for time range
        Args:
            start: ISO format or relative time like '-1h', '-1d'
            end: ISO format or 'now()'
        """
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
    
    def query_indicators(self, symbol: str, indicator_type: str, 
                        start: str = '-1h', end: str = 'now()'):
        """Query indicator values"""
        query = f'''
        from(bucket: "{self.bucket}")
          |> range(start: {start}, stop: {end})
          |> filter(fn: (r) => r["_measurement"] == "indicators")
          |> filter(fn: (r) => r["symbol"] == "{symbol}")
          |> filter(fn: (r) => r["indicator_type"] == "{indicator_type}")
        '''
        result = self.query_api.query(query=query)
        return self._parse_query_result(result)
    
    def query_position_history(self, strategy_id: str, symbol: str,
                               start: str = '-1h'):
        """Query position snapshots"""
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
    
    def query_sl_timeline(self, trade_id: str):
        """Query trailing SL updates for a trade"""
        query = f'''
        from(bucket: "{self.bucket}")
          |> range(start: -24h)
          |> filter(fn: (r) => r["_measurement"] == "trailing_sl")
          |> filter(fn: (r) => r["trade_id"] == "{trade_id}")
          |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
        '''
        result = self.query_api.query(query=query)
        return self._parse_query_result(result)
    
    def query_strategy_performance(self, strategy_id: str, start: str = '-24h'):
        """Query strategy metrics over time"""
        query = f'''
        from(bucket: "{self.bucket}")
          |> range(start: {start})
          |> filter(fn: (r) => r["_measurement"] == "strategy_metrics")
          |> filter(fn: (r) => r["strategy_id"] == "{strategy_id}")
          |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
        '''
        result = self.query_api.query(query=query)
        return self._parse_query_result(result)
    
    def _parse_query_result(self, result) -> list:
        """Parse Flux query result to list of dicts"""
        records = []
        for table in result:
            for record in table.records:
                records.append(record.values)
        return records
    
    def health_check(self) -> bool:
        """Check InfluxDB connection"""
        try:
            return self.client.ping()
        except:
            return False
    
    def close(self):
        """Close connections"""
        self.write_api.close()
        self.client.close()
```

**Integration Points:**
- `MarketSimulator`: Write all ticks to InfluxDB
- `IndicatorManager`: Write calculated indicators
- `PositionTracker`: Write position snapshots every tick
- `TrailingSLManager`: Write SL updates
- Grafana: Query InfluxDB for charts

**Validation:**
```python
influx = InfluxManager()
influx.write_tick('RELIANCE', {
    'open': 2450, 'high': 2455, 'low': 2448, 
    'close': 2453, 'volume': 1500, 'source': 'test'
})
# Wait 1 second for async write
data = influx.query_tick_range('RELIANCE', start='-5m')
assert len(data) > 0
```

---

#### Subtask 4.1.3: SQLite for Trade Metadata (30 mins)

**Purpose:** ACID-compliant storage for trade relationships

**Create `src/database/sqlite_manager.py`**

```python
"""
SQLite stores trade metadata and relationships.
Time-series data goes to InfluxDB.
This keeps SQLite fast and focused.
"""

import sqlite3
from datetime import datetime
from typing import Optional, List, Dict
import logging

log = logging.getLogger(__name__)

class SQLiteManager:
    def __init__(self, db_path='data/velox_trades.db'):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # Dict-like access
        self._create_schema()
    
    def _create_schema(self):
        """Create optimized schema"""
        cursor = self.conn.cursor()
        
        # Trades table (metadata only)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS trades (
            trade_id TEXT PRIMARY KEY,
            strategy_id TEXT NOT NULL,
            symbol TEXT NOT NULL,
            action TEXT NOT NULL,
            entry_time TIMESTAMP NOT NULL,
            entry_price REAL NOT NULL,
            exit_time TIMESTAMP,
            exit_price REAL,
            quantity INTEGER NOT NULL,
            pnl REAL,
            pnl_pct REAL,
            exit_reason TEXT,
            duration_seconds INTEGER,
            status TEXT DEFAULT 'open',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Indexes for fast queries
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_strategy_id ON trades(strategy_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_symbol ON trades(symbol)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_entry_time ON trades(entry_time)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_status ON trades(status)')
        
        # Signal conditions (compact storage)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS signal_conditions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trade_id TEXT NOT NULL,
            signal_type TEXT NOT NULL,
            conditions_json TEXT NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            FOREIGN KEY (trade_id) REFERENCES trades(trade_id)
        )
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_trade_conditions ON signal_conditions(trade_id)')
        
        self.conn.commit()
    
    def insert_trade(self, trade_id: str, strategy_id: str, symbol: str, 
                    action: str, entry_time: datetime, entry_price: float, 
                    quantity: int) -> bool:
        """Insert new trade"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
            INSERT INTO trades (trade_id, strategy_id, symbol, action, 
                              entry_time, entry_price, quantity, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'open')
            ''', (trade_id, strategy_id, symbol, action, entry_time, 
                 entry_price, quantity))
            self.conn.commit()
            log.info(f"Trade {trade_id} inserted: {strategy_id} {action} {symbol}")
            return True
        except Exception as e:
            log.error(f"Failed to insert trade: {e}")
            return False
    
    def update_trade_exit(self, trade_id: str, exit_time: datetime, 
                         exit_price: float, pnl: float, pnl_pct: float,
                         exit_reason: str) -> bool:
        """Update trade with exit details"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
            UPDATE trades 
            SET exit_time = ?,
                exit_price = ?,
                pnl = ?,
                pnl_pct = ?,
                exit_reason = ?,
                duration_seconds = CAST((julianday(?) - julianday(entry_time)) * 86400 AS INTEGER),
                status = 'closed',
                updated_at = CURRENT_TIMESTAMP
            WHERE trade_id = ?
            ''', (exit_time, exit_price, pnl, pnl_pct, exit_reason, exit_time, trade_id))
            self.conn.commit()
            log.info(f"Trade {trade_id} closed: P&L {pnl_pct:.2f}%")
            return True
        except Exception as e:
            log.error(f"Failed to update trade: {e}")
            return False
    
    def insert_signal_conditions(self, trade_id: str, signal_type: str, 
                                 conditions: dict, timestamp: datetime):
        """Store signal conditions as JSON"""
        import json
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
            INSERT INTO signal_conditions (trade_id, signal_type, conditions_json, timestamp)
            VALUES (?, ?, ?, ?)
            ''', (trade_id, signal_type, json.dumps(conditions), timestamp))
            self.conn.commit()
        except Exception as e:
            log.error(f"Failed to insert conditions: {e}")
    
    def get_trade(self, trade_id: str) -> Optional[Dict]:
        """Get trade details"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM trades WHERE trade_id = ?', (trade_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_trades_by_strategy(self, strategy_id: str, limit: int = 100) -> List[Dict]:
        """Get recent trades for strategy"""
        cursor = self.conn.cursor()
        cursor.execute('''
        SELECT * FROM trades 
        WHERE strategy_id = ? 
        ORDER BY entry_time DESC 
        LIMIT ?
        ''', (strategy_id, limit))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_open_trades(self, strategy_id: str = None) -> List[Dict]:
        """Get all open trades"""
        cursor = self.conn.cursor()
        if strategy_id:
            cursor.execute('''
            SELECT * FROM trades 
            WHERE status = 'open' AND strategy_id = ?
            ORDER BY entry_time DESC
            ''', (strategy_id,))
        else:
            cursor.execute('''
            SELECT * FROM trades 
            WHERE status = 'open'
            ORDER BY entry_time DESC
            ''')
        return [dict(row) for row in cursor.fetchall()]
    
    def get_signal_conditions(self, trade_id: str, signal_type: str) -> Optional[dict]:
        """Get entry or exit conditions"""
        import json
        cursor = self.conn.cursor()
        cursor.execute('''
        SELECT conditions_json FROM signal_conditions
        WHERE trade_id = ? AND signal_type = ?
        ''', (trade_id, signal_type))
        row = cursor.fetchone()
        return json.loads(row[0]) if row else None
    
    def get_strategy_stats(self, strategy_id: str, days: int = 30) -> Dict:
        """Get strategy statistics"""
        cursor = self.conn.cursor()
        cursor.execute('''
        SELECT 
            COUNT(*) as total_trades,
            SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winners,
            SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losers,
            SUM(pnl) as total_pnl,
            AVG(pnl) as avg_pnl,
            AVG(duration_seconds) as avg_duration_sec
        FROM trades
        WHERE strategy_id = ? 
          AND status = 'closed'
          AND entry_time >= datetime('now', '-' || ? || ' days')
        ''', (strategy_id, days))
        row = cursor.fetchone()
        return dict(row) if row else {}
    
    def close(self):
        """Close connection"""
        self.conn.close()
```

**Validation:**
```python
db = SQLiteManager()
db.insert_trade('TRD001', 'rsi_agg', 'RELIANCE', 'BUY', 
                datetime.now(), 2450.00, 10)
trade = db.get_trade('TRD001')
assert trade['status'] == 'open'
```

---

### Task 4.2: Structured Logging System (1 hour)

**Purpose:** JSON logs for analysis and ELK stack integration

#### Subtask 4.2.1: Advanced Logging Configuration (1 hour)

**Create `src/utils/logging_system.py`**

```python
"""
Multi-destination structured logging:
1. Console (human-readable colored output)
2. File (JSON format for parsing)
3. Optional: ELK stack, Loki, etc.
"""

import logging
import json
import sys
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import colorlog

class StructuredLogger:
    def __init__(self, name: str, log_dir: str = 'logs'):
        self.name = name
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup multiple log handlers"""
        # Clear existing handlers
        self.logger.handlers = []
        
        # 1. Console Handler (colored, human-readable)
        console_handler = colorlog.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_format = colorlog.ColoredFormatter(
            '%(log_color)s[%(asctime)s] [%(levelname)-8s] [%(name)-20s]%(reset)s %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S.%f'[:-3],
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'white',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'bold_red',
            }
        )
        console_handler.setFormatter(console_format)
        self.logger.addHandler(console_handler)
        
        # 2. JSON File Handler (structured, daily rotation)
        json_file = self.log_dir / f'{self.name}_json.log'
        json_handler = TimedRotatingFileHandler(
            json_file, when='midnight', interval=1, backupCount=30
        )
        json_handler.setLevel(logging.DEBUG)
        json_handler.setFormatter(JSONFormatter())
        self.logger.addHandler(json_handler)
        
        # 3. Standard File Handler (human-readable, size rotation)
        text_file = self.log_dir / f'{self.name}.log'
        text_handler = RotatingFileHandler(
            text_file, maxBytes=50*1024*1024, backupCount=10  # 50MB per file
        )
        text_handler.setLevel(logging.DEBUG)
        text_format = logging.Formatter(
            '[%(asctime)s] [%(levelname)-8s] [%(name)-20s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S.%f'[:-3]
        )
        text_handler.setFormatter(text_format)
        self.logger.addHandler(text_handler)
    
    def debug(self, message: str, **context):
        self.logger.debug(message, extra={'context': context})
    
    def info(self, message: str, **context):
        self.logger.info(message, extra={'context': context})
    
    def warning(self, message: str, **context):
        self.logger.warning(message, extra={'context': context})
    
    def error(self, message: str, **context):
        self.logger.error(message, extra={'context': context}, exc_info=True)
    
    def critical(self, message: str, **context):
        self.logger.critical(message, extra={'context': context}, exc_info=True)


class JSONFormatter(logging.Formatter):
    """Format logs as JSON for structured parsing"""
    
    def format(self, record):
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add context if available
        if hasattr(record, 'context'):
            log_data['context'] = record.context
        
        # Add exception info if available
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


# Factory function for easy logger creation
def get_logger(name: str) -> StructuredLogger:
    return StructuredLogger(name)


# Pre-configured loggers for components
simulato_log = get_logger('simulator')
strategy_log = get_logger('strategy')
risk_log = get_logger('risk')
order_log = get_logger('order')
position_log = get_logger('position')
database_log = get_logger('database')
```

**Usage Example:**
```python
from src.utils.logging_system import strategy_log

strategy_log.info("Signal generated", 
                  strategy_id="rsi_agg",
                  symbol="RELIANCE",
                  action="BUY",
                  rsi=28.5,
                  price=2450.00)
```

**JSON Output:**
```json
{
  "timestamp": "2024-10-22T10:30:15.123Z",
  "level": "INFO",
  "logger": "strategy",
  "message": "Signal generated",
  "context": {
    "strategy_id": "rsi_agg",
    "symbol": "RELIANCE",
    "action": "BUY",
    "rsi": 28.5,
    "price": 2450.0
  }
}
```

---

### Task 4.3: Integration Layer (1.5 hours)

**Purpose:** Connect all data systems with existing components

#### Subtask 4.3.1: Create Unified Data Manager (1 hour)

**Create `src/database/data_manager.py`**

```python
"""
Unified interface for all data operations.
Handles Redis (hot), InfluxDB (time-series), SQLite (metadata).
"""

from .redis_manager import RedisManager
from .influx_manager import InfluxManager
from .sqlite_manager import SQLiteManager
from ..utils.logging_system import database_log as log
from datetime import datetime
from typing import Dict, List, Optional

class DataManager:
    def __init__(self):
        self.redis = RedisManager()
        self.influx = InfluxManager()
        self.sqlite = SQLiteManager()
        log.info("DataManager initialized", 
                 redis_status=self.redis.health_check(),
                 influx_status=self.influx.health_check())
    
    # Position Operations (Redis + InfluxDB)
    def open_position(self, trade_id: str, strategy_id: str, symbol: str,
                     entry_price: float, quantity: int, timestamp: datetime):
        """Open new position across all systems"""
        # SQLite: metadata
        self.sqlite.insert_trade(trade_id, strategy_id, symbol, 'BUY',
                                timestamp, entry_price, quantity)
        
        # Redis: hot cache
        position_data = {
            'trade_id': trade_id,
            'entry_price': entry_price,
            'quantity': quantity,
            'entry_time': timestamp.isoformat()
        }
        self.redis.set_position(strategy_id, symbol, position_data)
        
        # InfluxDB: time-series
        self.influx.write_trade(strategy_id, symbol, 'BUY', 
                               entry_price, quantity, timestamp=timestamp)
        
        log.info("Position opened", trade_id=trade_id, strategy_id=strategy_id,
                symbol=symbol, price=entry_price, qty=quantity)
    
    def update_position_snapshot(self, trade_id: str, strategy_id: str, 
                                symbol: str, current_price: float,
                                unrealized_pnl: float, unrealized_pnl_pct: float,
                                indicators: dict, timestamp: datetime):
        """Store position snapshot (called every tick)"""
        # Get position from Redis
        position = self.redis.get_position(strategy_id, symbol)
        if not position:
            return
        
        # InfluxDB: snapshot (efficient time-series storage)
        self.influx.write_position_snapshot(
            strategy_id, symbol, current_price, position.get('quantity', 0),
            unrealized_pnl, unrealized_pnl_pct, timestamp
        )
        
        # InfluxDB: indicators
        for indicator_name, value in indicators.items():
            if value is not None:
                self.influx.write_indicator(symbol, indicator_name, value, 
                                           timestamp=timestamp)
    
    def close_position(self, trade_id: str, strategy_id: str, symbol: str,
                      exit_price: float, pnl: float, pnl_pct: float,
                      exit_reason: str, timestamp: datetime):
        """Close position across all systems"""
        # Get position details
        position = self.redis.get_position(strategy_id, symbol)
        
        # SQLite: update with exit details
        self.sqlite.update_trade_exit(trade_id, timestamp, exit_price,
                                      pnl, pnl_pct, exit_reason)
        
        # Redis: remove from hot cache
        self.redis.delete_position(strategy_id, symbol)
        
        # InfluxDB: write exit trade
        quantity = position.get('quantity', 0) if position else 0
        self.influx.write_trade(strategy_id, symbol, 'SELL',
                               exit_price, quantity, pnl, timestamp)
        
        log.info("Position closed", trade_id=trade_id, strategy_id=strategy_id,
                symbol=symbol, pnl=pnl, pnl_pct=pnl_pct, reason=exit_reason)
    
    # Trailing SL Operations
    def update_trailing_sl(self, trade_id: str, strategy_id: str, symbol: str,
                          current_sl: float, highest_price: float, 
                          sl_type: str, timestamp: datetime):
        """Store trailing SL update"""
        # Redis: current state
        sl_data = {
            'current_sl': current_sl,
            'highest_price': highest_price,
            'sl_type': sl_type,
            'updated_at': timestamp.isoformat()
        }
        self.redis.set_sl_state(trade_id, sl_data)
        
        # InfluxDB: historical timeline
        self.influx.write_sl_update(strategy_id, symbol, trade_id,
                                    current_sl, highest_price, sl_type, timestamp)
    
    # Signal Conditions
    def store_signal_conditions(self, trade_id: str, signal_type: str,
                               conditions: dict, timestamp: datetime):
        """Store why signal was generated"""
        self.sqlite.insert_signal_conditions(trade_id, signal_type, 
                                            conditions, timestamp)
    
    # Market Data
    def store_tick(self, symbol: str, tick_data: dict, timestamp: datetime):
        """Store tick data"""
        # Redis: latest tick (cache)
        self.redis.set_latest_tick(symbol, tick_data)
        
        # InfluxDB: time-series
        self.influx.write_tick(symbol, tick_data, timestamp)
    
    # Query Operations
    def get_trade_details(self, trade_id: str) -> Dict:
        """Get complete trade details"""
        # Metadata from SQLite
        trade = self.sqlite.get_trade(trade_id)
        if not trade:
            return None
        
        # Entry conditions
        trade['entry_conditions'] = self.sqlite.get_signal_conditions(
            trade_id, 'entry'
        )
        
        # Exit conditions
        trade['exit_conditions'] = self.sqlite.get_signal_conditions(
            trade_id, 'exit'
        )
        
        # SL timeline from InfluxDB
        trade['sl_timeline'] = self.influx.query_sl_timeline(trade_id)
        
        # Position history from InfluxDB
        if trade.get('strategy_id') and trade.get('symbol'):
            trade['position_history'] = self.influx.query_position_history(
                trade['strategy_id'], trade['symbol'], 
                start=trade['entry_time']
            )
        
        return trade
    
    def get_open_positions(self) -> List[Dict]:
        """Get all open positions"""
        # Fast retrieval from Redis
        redis_positions = self.redis.get_all_positions()
        
        # Enrich with metadata from SQLite
        positions = []
        for key, pos_data in redis_positions.items():
            strategy_id = key.split(':')[1]
            symbol = key.split(':')[2]
            
            # Get trade metadata
            trades = self.sqlite.get_open_trades(strategy_id)
            trade = next((t for t in trades if t['symbol'] == symbol), None)
            
            if trade:
                positions.append({
                    **pos_data,
                    **trade
                })
        
        return positions
    
    def get_strategy_performance(self, strategy_id: str, 
                                 start: str = '-24h') -> Dict:
        """Get strategy performance metrics"""
        # Stats from SQLite
        stats = self.sqlite.get_strategy_stats(strategy_id, days=30)
        
        # Time-series metrics from InfluxDB
        metrics_history = self.influx.query_strategy_performance(
            strategy_id, start
        )
        
        # Current stats from Redis
        redis_stats = self.redis.get_strategy_stats(strategy_id)
        
        return {
            'stats': stats,
            'metrics_history': metrics_history,
            'current': redis_stats
        }
    
    def health_check(self) -> Dict:
        """Check all systems"""
        return {
            'redis': self.redis.health_check(),
            'influxdb': self.influx.health_check(),
            'sqlite': True  # Always available
        }
    
    def close(self):
        """Close all connections"""
        self.influx.close()
        self.sqlite.close()
```

**Validation:**
```python
dm = DataManager()
health = dm.health_check()
assert all(health.values()), "All systems should be healthy"
```

---

#### Subtask 4.3.2: Update Core Components (30 mins)

**Update `src/core/position_tracker.py`:**
```python
from src.database.data_manager import DataManager
from src.utils.logging_system import position_log as log

class PositionTracker:
    def __init__(self):
        self.data_manager = DataManager()
    
    def on_fill(self, fill_data: dict):
        """Called when order fills"""
        trade_id = fill_data['trade_id']
        strategy_id = fill_data['strategy_id']
        symbol = fill_data['symbol']
        action = fill_data['action']
        price = fill_data['price']
        quantity = fill_data['quantity']
        timestamp = fill_data['timestamp']
        
        if action == 'BUY':
            self.data_manager.open_position(
                trade_id, strategy_id, symbol, price, quantity, timestamp
            )
        elif action == 'SELL':
            # Calculate P&L
            position = self.data_manager.redis.get_position(strategy_id, symbol)
            if position:
                entry_price = position['entry_price']
                pnl = (price - entry_price) * quantity
                pnl_pct = (price - entry_price) / entry_price * 100
                
                self.data_manager.close_position(
                    trade_id, strategy_id, symbol, price, pnl, pnl_pct,
                    fill_data.get('exit_reason', 'manual'), timestamp
                )
    
    def on_tick(self, tick_data: dict):
        """Update position snapshots"""
        symbol = tick_data['symbol']
        current_price = tick_data['close']
        timestamp = tick_data['timestamp']
        
        # Get all positions for this symbol
        positions = self.data_manager.get_open_positions()
        
        for position in positions:
            if position['symbol'] == symbol:
                # Calculate unrealized P&L
                entry_price = position['entry_price']
                quantity = position['quantity']
                unrealized_pnl = (current_price - entry_price) * quantity
                unrealized_pnl_pct = (current_price - entry_price) / entry_price * 100
                
                # Get indicators from Redis cache
                indicators = self.data_manager.redis.get_indicators(symbol) or {}
                
                # Store snapshot
                self.data_manager.update_position_snapshot(
                    position['trade_id'], position['strategy_id'], symbol,
                    current_price, unrealized_pnl, unrealized_pnl_pct,
                    indicators, timestamp
                )
```

**Update `src/core/trailing_sl_manager.py`:**
```python
from src.database.data_manager import DataManager

class TrailingSLManager:
    def __init__(self, strategy_id: str, config: dict):
        self.strategy_id = strategy_id
        self.config = config
        self.data_manager = DataManager()
    
    def update(self, trade_id: str, symbol: str, current_price: float, 
               timestamp: datetime):
        """Update trailing SL"""
        # Get current SL state from Redis
        sl_state = self.data_manager.redis.get_sl_state(trade_id)
        
        # Calculate new SL based on type
        new_sl = self._calculate_sl(current_price, sl_state)
        
        # Only update if SL moves up
        if new_sl > sl_state.get('current_sl', 0):
            self.data_manager.update_trailing_sl(
                trade_id, self.strategy_id, symbol, new_sl,
                sl_state.get('highest_price', current_price),
                self.config['type'], timestamp
            )
```

---

## AFTERNOON SESSION (6 hours)

### Task 4.4: Grafana Dashboard Suite (3 hours)

**Update `docker-compose.yml` with complete stack:**

```yaml
version: '3.8'

services:
  zookeeper:
    image: confluentinc/cp-zookeeper:latest
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
    ports:
      - "2181:2181"

  kafka:
    image: confluentinc/cp-kafka:latest
    depends_on:
      - zookeeper
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
    ports:
      - "9092:9092"

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes --maxmemory 2gb --maxmemory-policy allkeys-lru
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data

  influxdb:
    image: influxdb:2.7-alpine
    environment:
      - DOCKER_INFLUXDB_INIT_MODE=setup
      - DOCKER_INFLUXDB_INIT_USERNAME=admin
      - DOCKER_INFLUXDB_INIT_PASSWORD=veloxinflux123
      - DOCKER_INFLUXDB_INIT_ORG=velox
      - DOCKER_INFLUXDB_INIT_BUCKET=trading
      - DOCKER_INFLUXDB_INIT_ADMIN_TOKEN=velox-super-secret-token
    ports:
      - "8086:8086"
    volumes:
      - influxdb-data:/var/lib/influxdb2

  prometheus:
    image: prom/prometheus:latest
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.retention.time=30d'
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus:/etc/prometheus
      - prometheus-data:/prometheus

  grafana:
    image: grafana/grafana:latest
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=velox123
      - GF_INSTALL_PLUGINS=grafana-clock-panel
    ports:
      - "3000:3000"
    volumes:
      - grafana-data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning
      - ./grafana/dashboards:/var/lib/grafana/dashboards
      - ./data/velox_trades.db:/var/lib/grafana/velox_trades.db:ro
    depends_on:
      - prometheus
      - influxdb

volumes:
  redis-data:
  influxdb-data:
  prometheus-data:
  grafana-data:
```

#### Subtask 4.4.1: Configure Data Sources (30 mins)

**Create `grafana/provisioning/datasources/datasources.yml`:**
```yaml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: false
    
  - name: InfluxDB
    type: influxdb
    access: proxy
    url: http://influxdb:8086
    jsonData:
      version: Flux
      organization: velox
      defaultBucket: trading
      tlsSkipVerify: true
    secureJsonData:
      token: velox-super-secret-token
    editable: false
    
  - name: VeloxDB
    type: frser-sqlite-datasource
    access: proxy
    url: file:/var/lib/grafana/velox_trades.db
    editable: false
```

---

#### Subtask 4.4.2: Dashboard 1 - System Overview (1 hour)

**Create `grafana/dashboards/01-system-overview.json`**

Key Panels:
1. **System Health Row**
   - Kafka lag (Prometheus)
   - Redis memory usage
   - InfluxDB write rate
   - Tick processing rate

2. **Trading Activity Row**
   - Total open positions (gauge)
   - Daily P&L (big stat with color)
   - Signals generated today (counter)
   - Active strategies (stat)

3. **Performance Row**
   - Strategy P&L comparison (bar chart from InfluxDB)
   - Win rate by strategy (gauge per strategy)
   - Trade frequency (time series)

4. **Real-Time Positions**
   - Table showing open positions from Redis via API

Query examples:
```flux
// InfluxDB: Strategy P&L over time
from(bucket: "trading")
  |> range(start: -24h)
  |> filter(fn: (r) => r["_measurement"] == "strategy_metrics")
  |> filter(fn: (r) => r["_field"] == "pnl")
  |> group(columns: ["strategy_id"])
```

---

#### Subtask 4.4.3: Dashboard 2 - Trade Analysis (1 hour)

**Create `grafana/dashboards/02-trade-analysis.json`**

**Variables:**
- `$strategy`: Multi-select from SQLite
  ```sql
  SELECT DISTINCT strategy_id FROM trades ORDER BY strategy_id
  ```
- `$symbol`: Multi-select filtered by strategy
  ```sql
  SELECT DISTINCT symbol FROM trades 
  WHERE strategy_id IN ($strategy)
  ORDER BY symbol
  ```
- `$status`: open/closed/all

Key Panels:
1. **Trade Statistics**
   - Total trades (stat)
   - Win/Loss ratio (pie chart)
   - Average duration (stat)
   - Total P&L (stat with trend)

2. **Trade Timeline**
   ```sql
   SELECT 
     entry_time as time,
     symbol,
     pnl,
     CASE WHEN pnl > 0 THEN 'profit' ELSE 'loss' END as result
   FROM trades
   WHERE strategy_id IN ($strategy)
     AND symbol IN ($symbol)
     AND status LIKE $status
     AND $__timeFilter(entry_time)
   ORDER BY entry_time
   ```

3. **Cumulative P&L Chart**
   ```sql
   SELECT 
     entry_time as time,
     SUM(pnl) OVER (ORDER BY entry_time) as cumulative_pnl
   FROM trades
   WHERE strategy_id IN ($strategy)
     AND status = 'closed'
     AND $__timeFilter(entry_time)
   ```

4. **Trade List Table** (with row click → detail)
   ```sql
   SELECT 
     trade_id,
     strategy_id,
     symbol,
     entry_time,
     exit_time,
     pnl,
     pnl_pct,
     exit_reason,
     duration_seconds
   FROM trades
   WHERE strategy_id IN ($strategy)
     AND symbol IN ($symbol)
     AND status LIKE $status
     AND $__timeFilter(entry_time)
   ORDER BY entry_time DESC
   LIMIT 100
   ```

---

#### Subtask 4.4.4: Dashboard 3 - Trade Detail (30 mins)

**Create `grafana/dashboards/03-trade-detail.json`**

**Variable:**
- `$trade_id`: From URL parameter or dropdown

Key Panels:
1. **Trade Summary** (stat panels)
   ```sql
   SELECT * FROM trades WHERE trade_id = '$trade_id'
   ```

2. **Price Chart with SL** (InfluxDB)
   ```flux
   from(bucket: "trading")
     |> range(start: -24h)
     |> filter(fn: (r) => r["_measurement"] == "positions")
     |> filter(fn: (r) => r["trade_id"] == "$trade_id")
     |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
   
   // Overlay with SL timeline
   from(bucket: "trading")
     |> range(start: -24h)
     |> filter(fn: (r) => r["_measurement"] == "trailing_sl")
     |> filter(fn: (r) => r["trade_id"] == "$trade_id")
   ```

3. **Indicator Timeline** (InfluxDB)
   ```flux
   from(bucket: "trading")
     |> range(start: -24h)
     |> filter(fn: (r) => r["_measurement"] == "indicators")
     |> filter(fn: (r) => r["symbol"] == "$symbol")
     |> filter(fn: (r) => r["indicator_type"] =~ /rsi|ma|atr/)
   ```

4. **SL Update Timeline** (table)
   ```flux
   from(bucket: "trading")
     |> range(start: -24h)
     |> filter(fn: (r) => r["_measurement"] == "trailing_sl")
     |> filter(fn: (r) => r["trade_id"] == "$trade_id")
     |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
   ```

5. **Entry Conditions** (table from SQLite)
   ```sql
   SELECT conditions_json 
   FROM signal_conditions
   WHERE trade_id = '$trade_id' AND signal_type = 'entry'
   ```

---

### Task 4.5: Enhanced Dashboard API (1.5 hours)

**Update `src/dashboard/app.py`:**

```python
from flask import Flask, jsonify, request
from flask_socketio import SocketIO, emit
from src.database.data_manager import DataManager
from src.utils.logging_system import get_logger
import json

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
data_manager = DataManager()
log = get_logger('dashboard')

# Real-time position updates
@socketio.on('connect')
def handle_connect():
    log.info("Client connected")
    emit('connection_status', {'status': 'connected'})

@socketio.on('subscribe_positions')
def handle_subscribe():
    """Send real-time position updates"""
    while True:
        positions = data_manager.get_open_positions()
        emit('positions_update', positions)
        socketio.sleep(1)

# REST API Endpoints
@app.route('/api/health')
def health():
    """System health check"""
    return jsonify(data_manager.health_check())

@app.route('/api/positions')
def get_positions():
    """Get all open positions"""
    positions = data_manager.get_open_positions()
    return jsonify(positions)

@app.route('/api/strategies')
def get_strategies():
    """Get strategy list with stats"""
    # Load from config
    from src.utils.config_loader import ConfigLoader
    config = ConfigLoader().load_strategies_config()
    
    strategies = []
    for strategy_config in config['strategies']:
        strategy_id = strategy_config['id']
        stats = data_manager.get_strategy_performance(strategy_id)
        strategies.append({
            'id': strategy_id,
            'config': strategy_config,
            'stats': stats
        })
    
    return jsonify(strategies)

@app.route('/api/trade/<trade_id>')
def get_trade_detail(trade_id):
    """Get complete trade details"""
    trade = data_manager.get_trade_details(trade_id)
    if not trade:
        return jsonify({'error': 'Trade not found'}), 404
    return jsonify(trade)

@app.route('/api/trade/<trade_id>/export')
def export_trade(trade_id):
    """Export trade data as CSV"""
    trade = data_manager.get_trade_details(trade_id)
    if not trade:
        return jsonify({'error': 'Trade not found'}), 404
    
    # Convert to CSV format
    import pandas as pd
    df = pd.DataFrame(trade['position_history'])
    csv_data = df.to_csv(index=False)
    
    from flask import Response
    return Response(
        csv_data,
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment;filename=trade_{trade_id}.csv'
        }
    )

@app.route('/api/indicators/<symbol>')
def get_indicators(symbol):
    """Get latest indicators for symbol"""
    indicators = data_manager.redis.get_indicators(symbol)
    return jsonify(indicators or {})

@app.route('/grafana/search', methods=['POST'])
def grafana_search():
    """Grafana Simple JSON datasource - search"""
    # Return available metrics
    return jsonify([
        'strategies',
        'symbols',
        'trades'
    ])

@app.route('/grafana/query', methods=['POST'])
def grafana_query():
    """Grafana Simple JSON datasource - query"""
    req = request.get_json()
    target = req['targets'][0]['target']
    
    if target == 'strategies':
        # Return strategy list
        strategies = data_manager.sqlite.conn.execute(
            'SELECT DISTINCT strategy_id FROM trades'
        ).fetchall()
        return jsonify([{'text': s[0], 'value': s[0]} for s in strategies])
    
    # Add more query handlers as needed
    return jsonify([])

if __name__ == '__main__':
    log.info("Starting dashboard on http://localhost:5000")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
```

---

### Task 4.6: Comprehensive Testing Suite (1.5 hours)

#### Subtask 4.6.1: Unit Tests (45 mins)

**Create `tests/test_database_layer.py`:**

```python
import pytest
from datetime import datetime, timedelta
from src.database.redis_manager import RedisManager
from src.database.influx_manager import InfluxManager
from src.database.sqlite_manager import SQLiteManager
from src.database.data_manager import DataManager

class TestRedisManager:
    @pytest.fixture
    def redis_mgr(self):
        return RedisManager()
    
    def test_position_crud(self, redis_mgr):
        """Test position create, read, delete"""
        position_data = {
            'trade_id': 'TEST001',
            'entry_price': 2450.00,
            'quantity': 10,
            'entry_time': datetime.now().isoformat()
        }
        
        # Create
        redis_mgr.set_position('test_strategy', 'TESTSTOCK', position_data)
        
        # Read
        retrieved = redis_mgr.get_position('test_strategy', 'TESTSTOCK')
        assert retrieved['trade_id'] == 'TEST001'
        assert retrieved['entry_price'] == 2450.00
        
        # Delete
        redis_mgr.delete_position('test_strategy', 'TESTSTOCK')
        assert redis_mgr.get_position('test_strategy', 'TESTSTOCK') is None
    