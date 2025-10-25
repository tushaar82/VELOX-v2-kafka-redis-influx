"""
Data Service Layer for Analytics Dashboard
Provides unified access to InfluxDB, Redis, and SQLite data
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from influxdb_client import InfluxDBClient
import redis
import sqlite3
from dataclasses import dataclass, asdict
import json

logger = logging.getLogger(__name__)


@dataclass
class Position:
    """Current position data"""
    strategy_id: str
    symbol: str
    quantity: int
    entry_price: float
    current_price: float
    highest_price: float
    entry_time: str
    unrealized_pnl: float
    unrealized_pnl_pct: float
    trailing_sl: Optional[float] = None
    trade_id: Optional[str] = None


@dataclass
class ClosedTrade:
    """Closed trade data"""
    trade_id: str
    strategy_id: str
    symbol: str
    entry_price: float
    exit_price: float
    quantity: int
    entry_time: str
    exit_time: str
    pnl: float
    pnl_pct: float
    exit_reason: str
    duration_minutes: int
    max_favorable_excursion: Optional[float] = None
    max_adverse_excursion: Optional[float] = None


@dataclass
class StrategyMetrics:
    """Strategy performance metrics"""
    strategy_id: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    max_consecutive_wins: int
    max_consecutive_losses: int
    avg_trade_duration_minutes: int


@dataclass
class PriceData:
    """Price and trailing SL data for charts"""
    timestamp: str
    symbol: str
    price: float
    trailing_sl: Optional[float] = None
    indicators: Optional[Dict[str, float]] = None


class DataService:
    """Unified data service for all dashboard queries"""

    def __init__(self,
                 influx_url: str = "http://localhost:8086",
                 influx_token: str = "my-token",
                 influx_org: str = "velox",
                 influx_bucket: str = "trading",
                 redis_host: str = "localhost",
                 redis_port: int = 6379,
                 sqlite_path: str = "data/velox.db"):
        """Initialize data service connections"""

        # InfluxDB client
        try:
            self.influx_client = InfluxDBClient(
                url=influx_url,
                token=influx_token,
                org=influx_org
            )
            self.query_api = self.influx_client.query_api()
            self.influx_bucket = influx_bucket
            self.influx_org = influx_org
            logger.info("InfluxDB connection established")
        except Exception as e:
            logger.error(f"Failed to connect to InfluxDB: {e}")
            self.influx_client = None
            self.query_api = None

        # Redis client
        try:
            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                decode_responses=True
            )
            self.redis_client.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis_client = None

        # SQLite connection
        self.sqlite_path = sqlite_path
        logger.info(f"SQLite path: {sqlite_path}")

    def _get_sqlite_connection(self):
        """Get SQLite connection"""
        return sqlite3.connect(self.sqlite_path)

    # ========== POSITIONS ==========

    def get_open_positions(self) -> List[Position]:
        """Get all currently open positions from Redis"""
        if not self.redis_client:
            return []

        positions = []
        try:
            # Scan for all position keys
            for key in self.redis_client.scan_iter("position:*"):
                try:
                    data = self.redis_client.get(key)
                    if data:
                        pos_data = json.loads(data)

                        # Get trailing SL if available
                        trade_id = pos_data.get('trade_id')
                        trailing_sl = None
                        if trade_id:
                            sl_data = self.redis_client.get(f"sl:{trade_id}")
                            if sl_data:
                                sl_info = json.loads(sl_data)
                                trailing_sl = sl_info.get('current_sl')

                        position = Position(
                            strategy_id=pos_data.get('strategy_id', ''),
                            symbol=pos_data.get('symbol', ''),
                            quantity=pos_data.get('quantity', 0),
                            entry_price=pos_data.get('entry_price', 0.0),
                            current_price=pos_data.get('current_price', 0.0),
                            highest_price=pos_data.get('highest_price', 0.0),
                            entry_time=pos_data.get('entry_time', ''),
                            unrealized_pnl=pos_data.get('unrealized_pnl', 0.0),
                            unrealized_pnl_pct=pos_data.get('unrealized_pnl_pct', 0.0),
                            trailing_sl=trailing_sl,
                            trade_id=trade_id
                        )
                        positions.append(position)
                except Exception as e:
                    logger.error(f"Error parsing position {key}: {e}")
                    continue
        except Exception as e:
            logger.error(f"Error getting open positions: {e}")

        return positions

    def get_position_by_symbol(self, symbol: str, strategy_id: Optional[str] = None) -> Optional[Position]:
        """Get position for a specific symbol"""
        positions = self.get_open_positions()

        for pos in positions:
            if pos.symbol == symbol:
                if strategy_id is None or pos.strategy_id == strategy_id:
                    return pos

        return None

    # ========== CLOSED TRADES ==========

    def get_closed_trades(self, limit: int = 100, strategy_id: Optional[str] = None) -> List[ClosedTrade]:
        """Get closed trades from SQLite"""
        try:
            conn = self._get_sqlite_connection()
            cursor = conn.cursor()

            query = """
                SELECT
                    trade_id, strategy_id, symbol, entry_price, exit_price,
                    quantity, entry_time, exit_time, pnl, pnl_pct, exit_reason,
                    duration_seconds, max_favorable_excursion, max_adverse_excursion
                FROM trades
                WHERE status = 'CLOSED'
            """

            params = []
            if strategy_id:
                query += " AND strategy_id = ?"
                params.append(strategy_id)

            query += " ORDER BY exit_time DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()

            trades = []
            for row in rows:
                trade = ClosedTrade(
                    trade_id=row[0],
                    strategy_id=row[1],
                    symbol=row[2],
                    entry_price=row[3],
                    exit_price=row[4],
                    quantity=row[5],
                    entry_time=row[6],
                    exit_time=row[7],
                    pnl=row[8],
                    pnl_pct=row[9],
                    exit_reason=row[10],
                    duration_minutes=int(row[11] / 60) if row[11] else 0,
                    max_favorable_excursion=row[12],
                    max_adverse_excursion=row[13]
                )
                trades.append(trade)

            return trades
        except Exception as e:
            logger.error(f"Error getting closed trades: {e}")
            return []

    # ========== STRATEGY METRICS ==========

    def get_strategy_metrics(self, strategy_id: str) -> Optional[StrategyMetrics]:
        """Calculate strategy performance metrics"""
        try:
            conn = self._get_sqlite_connection()
            cursor = conn.cursor()

            # Get basic stats
            cursor.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN pnl <= 0 THEN 1 ELSE 0 END) as losses,
                    SUM(pnl) as total_pnl,
                    AVG(CASE WHEN pnl > 0 THEN pnl END) as avg_win,
                    AVG(CASE WHEN pnl < 0 THEN ABS(pnl) END) as avg_loss,
                    AVG(duration_seconds) as avg_duration
                FROM trades
                WHERE strategy_id = ? AND status = 'CLOSED'
            """, (strategy_id,))

            row = cursor.fetchone()

            if not row or row[0] == 0:
                conn.close()
                return None

            total_trades = row[0]
            winning_trades = row[1] or 0
            losing_trades = row[2] or 0
            total_pnl = row[3] or 0.0
            avg_win = row[4] or 0.0
            avg_loss = row[5] or 0.0
            avg_duration = row[6] or 0

            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
            profit_factor = (avg_win * winning_trades) / (avg_loss * losing_trades) if losing_trades > 0 and avg_loss > 0 else 0.0

            # Calculate max consecutive wins/losses
            cursor.execute("""
                SELECT pnl FROM trades
                WHERE strategy_id = ? AND status = 'CLOSED'
                ORDER BY exit_time
            """, (strategy_id,))

            trades = cursor.fetchall()
            conn.close()

            max_consecutive_wins = 0
            max_consecutive_losses = 0
            current_wins = 0
            current_losses = 0

            for trade in trades:
                pnl = trade[0]
                if pnl > 0:
                    current_wins += 1
                    current_losses = 0
                    max_consecutive_wins = max(max_consecutive_wins, current_wins)
                else:
                    current_losses += 1
                    current_wins = 0
                    max_consecutive_losses = max(max_consecutive_losses, current_losses)

            return StrategyMetrics(
                strategy_id=strategy_id,
                total_trades=total_trades,
                winning_trades=winning_trades,
                losing_trades=losing_trades,
                win_rate=win_rate,
                total_pnl=total_pnl,
                avg_win=avg_win,
                avg_loss=avg_loss,
                profit_factor=profit_factor,
                max_consecutive_wins=max_consecutive_wins,
                max_consecutive_losses=max_consecutive_losses,
                avg_trade_duration_minutes=int(avg_duration / 60) if avg_duration else 0
            )
        except Exception as e:
            logger.error(f"Error calculating strategy metrics: {e}")
            return None

    def get_all_strategy_metrics(self) -> Dict[str, StrategyMetrics]:
        """Get metrics for all strategies"""
        try:
            conn = self._get_sqlite_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT DISTINCT strategy_id FROM trades WHERE status = 'CLOSED'
            """)

            strategies = [row[0] for row in cursor.fetchall()]
            conn.close()

            metrics = {}
            for strategy_id in strategies:
                strategy_metrics = self.get_strategy_metrics(strategy_id)
                if strategy_metrics:
                    metrics[strategy_id] = strategy_metrics

            return metrics
        except Exception as e:
            logger.error(f"Error getting all strategy metrics: {e}")
            return {}

    # ========== PRICE & INDICATOR DATA ==========

    def get_price_history(self, symbol: str, hours: int = 1) -> List[PriceData]:
        """Get price history from InfluxDB"""
        if not self.query_api:
            return []

        try:
            query = f'''
                from(bucket: "{self.influx_bucket}")
                |> range(start: -{hours}h)
                |> filter(fn: (r) => r._measurement == "ticks")
                |> filter(fn: (r) => r.symbol == "{symbol}")
                |> filter(fn: (r) => r._field == "price")
                |> sort(columns: ["_time"])
            '''

            result = self.query_api.query(query, org=self.influx_org)

            prices = []
            for table in result:
                for record in table.records:
                    price_data = PriceData(
                        timestamp=record.get_time().isoformat(),
                        symbol=symbol,
                        price=record.get_value()
                    )
                    prices.append(price_data)

            return prices
        except Exception as e:
            logger.error(f"Error getting price history for {symbol}: {e}")
            return []

    def get_trailing_sl_history(self, trade_id: str) -> List[Dict[str, Any]]:
        """Get trailing SL updates from InfluxDB"""
        if not self.query_api:
            return []

        try:
            query = f'''
                from(bucket: "{self.influx_bucket}")
                |> range(start: -24h)
                |> filter(fn: (r) => r._measurement == "trailing_sl")
                |> filter(fn: (r) => r.trade_id == "{trade_id}")
                |> sort(columns: ["_time"])
            '''

            result = self.query_api.query(query, org=self.influx_org)

            sl_updates = []
            for table in result:
                for record in table.records:
                    sl_updates.append({
                        'timestamp': record.get_time().isoformat(),
                        'field': record.get_field(),
                        'value': record.get_value()
                    })

            return sl_updates
        except Exception as e:
            logger.error(f"Error getting trailing SL history: {e}")
            return []

    def get_indicator_values(self, symbol: str, strategy_id: str) -> Dict[str, float]:
        """Get current indicator values from Redis"""
        if not self.redis_client:
            return {}

        try:
            key = f"indicators:{symbol}:{strategy_id}"
            data = self.redis_client.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.error(f"Error getting indicators for {symbol}: {e}")

        return {}

    # ========== SYSTEM STATUS ==========

    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status"""
        status = {
            'timestamp': datetime.now().isoformat(),
            'databases': {
                'redis': self.redis_client is not None,
                'influxdb': self.influx_client is not None,
                'sqlite': True  # Always true if we can connect
            },
            'open_positions_count': len(self.get_open_positions()),
            'total_pnl': 0.0
        }

        # Calculate total P&L from open positions
        positions = self.get_open_positions()
        status['total_pnl'] = sum(pos.unrealized_pnl for pos in positions)

        return status

    # ========== ORDER TRACKING ==========

    def get_unclosed_orders(self) -> List[Dict[str, Any]]:
        """Get orders that might not be properly closed"""
        try:
            conn = self._get_sqlite_connection()
            cursor = conn.cursor()

            # Find trades that have been open for too long (>24 hours)
            cursor.execute("""
                SELECT trade_id, strategy_id, symbol, entry_time, entry_price, quantity
                FROM trades
                WHERE status = 'OPEN'
                AND datetime(entry_time) < datetime('now', '-24 hours')
                ORDER BY entry_time DESC
            """)

            rows = cursor.fetchall()
            conn.close()

            unclosed = []
            for row in rows:
                unclosed.append({
                    'trade_id': row[0],
                    'strategy_id': row[1],
                    'symbol': row[2],
                    'entry_time': row[3],
                    'entry_price': row[4],
                    'quantity': row[5],
                    'duration_hours': (datetime.now() - datetime.fromisoformat(row[3])).total_seconds() / 3600
                })

            return unclosed
        except Exception as e:
            logger.error(f"Error getting unclosed orders: {e}")
            return []

    def close(self):
        """Close all connections"""
        if self.influx_client:
            self.influx_client.close()
        if self.redis_client:
            self.redis_client.close()
