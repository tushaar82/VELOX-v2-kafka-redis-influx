"""
SQLite Manager for VELOX Trading System.

SQLite stores trade metadata and relationships.
Time-series data goes to InfluxDB.
This keeps SQLite fast and focused.

Schema:
- trades: Trade metadata (entry/exit, P&L, duration)
- signal_conditions: Entry/exit signal conditions (JSON)
"""

import sqlite3
from datetime import datetime
from typing import Optional, List, Dict
import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)


class SQLiteManager:
    """
    ACID-compliant storage for trade metadata and relationships.
    
    Features:
    - Trade lifecycle tracking
    - Signal conditions storage
    - Performance statistics
    - Fast indexed queries
    - Thread-safe operations
    """
    
    def __init__(self, db_path='data/velox_trades.db'):
        """
        Initialize SQLite database.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        
        # Create data directory if needed
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        try:
            self.conn = sqlite3.connect(db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row  # Dict-like access
            self._create_schema()
            log.info(f"✓ SQLite connected: {db_path}")
        except Exception as e:
            log.error(f"❌ SQLite initialization failed: {e}")
            raise
    
    def _create_schema(self):
        """Create optimized database schema."""
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
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_strategy_status ON trades(strategy_id, status)')
        
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
        log.info("✓ SQLite schema created/verified")
    
    # ==================== Trade Operations ====================
    
    def insert_trade(self, trade_id: str, strategy_id: str, symbol: str,
                    action: str, entry_time: datetime, entry_price: float,
                    quantity: int) -> bool:
        """
        Insert new trade.
        
        Args:
            trade_id: Unique trade identifier
            strategy_id: Strategy identifier
            symbol: Symbol name
            action: Trade action (BUY/SELL)
            entry_time: Entry timestamp
            entry_price: Entry price
            quantity: Trade quantity
            
        Returns:
            True if successful
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
            INSERT INTO trades (trade_id, strategy_id, symbol, action,
                              entry_time, entry_price, quantity, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'open')
            ''', (trade_id, strategy_id, symbol, action, entry_time,
                 entry_price, quantity))
            self.conn.commit()
            log.info(f"✓ Trade {trade_id} inserted: {strategy_id} {action} {symbol} @ {entry_price}")
            return True
        except Exception as e:
            log.error(f"Failed to insert trade {trade_id}: {e}")
            return False
    
    def update_trade_exit(self, trade_id: str, exit_time: datetime,
                         exit_price: float, pnl: float, pnl_pct: float,
                         exit_reason: str) -> bool:
        """
        Update trade with exit details.
        
        Args:
            trade_id: Trade identifier
            exit_time: Exit timestamp
            exit_price: Exit price
            pnl: Profit/Loss amount
            pnl_pct: Profit/Loss percentage
            exit_reason: Reason for exit
            
        Returns:
            True if successful
        """
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
            log.info(f"✓ Trade {trade_id} closed: P&L {pnl:.2f} ({pnl_pct:.2f}%)")
            return True
        except Exception as e:
            log.error(f"Failed to update trade {trade_id}: {e}")
            return False
    
    def get_trade(self, trade_id: str) -> Optional[Dict]:
        """
        Get trade details.
        
        Args:
            trade_id: Trade identifier
            
        Returns:
            Trade dict or None
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT * FROM trades WHERE trade_id = ?', (trade_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            log.error(f"Failed to get trade {trade_id}: {e}")
            return None
    
    def get_open_trades(self, strategy_id: str = None) -> List[Dict]:
        """
        Get all open trades.
        
        Args:
            strategy_id: Optional strategy filter
            
        Returns:
            List of trade dicts
        """
        try:
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
        except Exception as e:
            log.error(f"Failed to get open trades: {e}")
            return []
    
    def get_closed_trades(self, strategy_id: str = None, limit: int = 100) -> List[Dict]:
        """
        Get closed trades.
        
        Args:
            strategy_id: Optional strategy filter
            limit: Maximum number of trades to return
            
        Returns:
            List of trade dicts
        """
        try:
            cursor = self.conn.cursor()
            if strategy_id:
                cursor.execute('''
                SELECT * FROM trades
                WHERE status = 'closed' AND strategy_id = ?
                ORDER BY exit_time DESC
                LIMIT ?
                ''', (strategy_id, limit))
            else:
                cursor.execute('''
                SELECT * FROM trades
                WHERE status = 'closed'
                ORDER BY exit_time DESC
                LIMIT ?
                ''', (limit,))
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            log.error(f"Failed to get closed trades: {e}")
            return []
    
    def get_trades_by_strategy(self, strategy_id: str, limit: int = 100) -> List[Dict]:
        """
        Get recent trades for strategy.
        
        Args:
            strategy_id: Strategy identifier
            limit: Maximum number of trades
            
        Returns:
            List of trade dicts
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
            SELECT * FROM trades
            WHERE strategy_id = ?
            ORDER BY entry_time DESC
            LIMIT ?
            ''', (strategy_id, limit))
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            log.error(f"Failed to get trades for {strategy_id}: {e}")
            return []
    
    # ==================== Signal Conditions ====================
    
    def insert_signal_conditions(self, trade_id: str, signal_type: str,
                                 conditions: dict, timestamp: datetime):
        """
        Store signal conditions as JSON.
        
        Args:
            trade_id: Trade identifier
            signal_type: 'entry' or 'exit'
            conditions: Dict of conditions that triggered signal
            timestamp: Signal timestamp
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
            INSERT INTO signal_conditions (trade_id, signal_type, conditions_json, timestamp)
            VALUES (?, ?, ?, ?)
            ''', (trade_id, signal_type, json.dumps(conditions), timestamp))
            self.conn.commit()
            log.debug(f"✓ Signal conditions stored for {trade_id}")
        except Exception as e:
            log.error(f"Failed to insert signal conditions: {e}")
    
    def get_signal_conditions(self, trade_id: str, signal_type: str) -> Optional[dict]:
        """
        Get entry or exit conditions.
        
        Args:
            trade_id: Trade identifier
            signal_type: 'entry' or 'exit'
            
        Returns:
            Conditions dict or None
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
            SELECT conditions_json FROM signal_conditions
            WHERE trade_id = ? AND signal_type = ?
            ''', (trade_id, signal_type))
            row = cursor.fetchone()
            return json.loads(row[0]) if row else None
        except Exception as e:
            log.error(f"Failed to get signal conditions: {e}")
            return None
    
    # ==================== Statistics ====================
    
    def get_strategy_stats(self, strategy_id: str, days: int = 30) -> Dict:
        """
        Get strategy statistics.
        
        Args:
            strategy_id: Strategy identifier
            days: Number of days to analyze
            
        Returns:
            Statistics dict
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
            SELECT
                COUNT(*) as total_trades,
                SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winners,
                SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losers,
                SUM(CASE WHEN pnl = 0 THEN 1 ELSE 0 END) as breakeven,
                SUM(pnl) as total_pnl,
                AVG(pnl) as avg_pnl,
                MAX(pnl) as max_win,
                MIN(pnl) as max_loss,
                AVG(duration_seconds) as avg_duration_sec,
                AVG(CASE WHEN pnl > 0 THEN pnl END) as avg_win,
                AVG(CASE WHEN pnl < 0 THEN pnl END) as avg_loss
            FROM trades
            WHERE strategy_id = ?
              AND status = 'closed'
              AND entry_time >= datetime('now', '-' || ? || ' days')
            ''', (strategy_id, days))
            row = cursor.fetchone()
            
            if row:
                stats = dict(row)
                # Calculate win rate
                total = stats.get('total_trades', 0)
                winners = stats.get('winners', 0)
                stats['win_rate'] = (winners / total * 100) if total > 0 else 0
                
                # Calculate profit factor
                avg_win = stats.get('avg_win', 0) or 0
                avg_loss = abs(stats.get('avg_loss', 0) or 0)
                stats['profit_factor'] = (avg_win / avg_loss) if avg_loss > 0 else 0
                
                return stats
            return {}
        except Exception as e:
            log.error(f"Failed to get strategy stats: {e}")
            return {}
    
    def get_daily_summary(self, date: str = None) -> Dict:
        """
        Get daily trading summary.
        
        Args:
            date: Date in YYYY-MM-DD format (defaults to today)
            
        Returns:
            Daily summary dict
        """
        try:
            if not date:
                date = datetime.now().strftime('%Y-%m-%d')
            
            cursor = self.conn.cursor()
            cursor.execute('''
            SELECT
                COUNT(*) as total_trades,
                SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winners,
                SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losers,
                SUM(pnl) as total_pnl,
                AVG(pnl) as avg_pnl,
                MAX(pnl) as best_trade,
                MIN(pnl) as worst_trade
            FROM trades
            WHERE status = 'closed'
              AND DATE(entry_time) = ?
            ''', (date,))
            row = cursor.fetchone()
            return dict(row) if row else {}
        except Exception as e:
            log.error(f"Failed to get daily summary: {e}")
            return {}
    
    def get_symbol_performance(self, symbol: str, days: int = 30) -> Dict:
        """
        Get performance statistics for a symbol.
        
        Args:
            symbol: Symbol name
            days: Number of days to analyze
            
        Returns:
            Performance dict
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
            SELECT
                COUNT(*) as total_trades,
                SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winners,
                SUM(pnl) as total_pnl,
                AVG(pnl) as avg_pnl,
                AVG(duration_seconds) as avg_duration_sec
            FROM trades
            WHERE symbol = ?
              AND status = 'closed'
              AND entry_time >= datetime('now', '-' || ? || ' days')
            ''', (symbol, days))
            row = cursor.fetchone()
            return dict(row) if row else {}
        except Exception as e:
            log.error(f"Failed to get symbol performance: {e}")
            return {}
    
    # ==================== Maintenance ====================
    
    def vacuum(self):
        """Optimize database (reclaim space, rebuild indexes)."""
        try:
            self.conn.execute('VACUUM')
            log.info("✓ Database vacuumed")
        except Exception as e:
            log.error(f"Failed to vacuum database: {e}")
    
    def get_database_size(self) -> int:
        """
        Get database file size in bytes.
        
        Returns:
            Size in bytes
        """
        try:
            return Path(self.db_path).stat().st_size
        except Exception as e:
            log.error(f"Failed to get database size: {e}")
            return 0
    
    def get_table_counts(self) -> Dict[str, int]:
        """
        Get row counts for all tables.
        
        Returns:
            Dict of {table_name: row_count}
        """
        try:
            cursor = self.conn.cursor()
            counts = {}
            
            cursor.execute("SELECT COUNT(*) FROM trades")
            counts['trades'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM signal_conditions")
            counts['signal_conditions'] = cursor.fetchone()[0]
            
            return counts
        except Exception as e:
            log.error(f"Failed to get table counts: {e}")
            return {}
    
    def close(self):
        """Close database connection."""
        try:
            self.conn.close()
            log.info("SQLite connection closed")
        except Exception as e:
            log.error(f"Failed to close SQLite: {e}")
