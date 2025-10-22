#!/usr/bin/env python3
"""
Test script for SQLite Manager.
"""

import sys
sys.path.insert(0, 'src')

from database.sqlite_manager import SQLiteManager
from datetime import datetime, timedelta
import os

def test_sqlite():
    """Test SQLite Manager."""
    print("\n" + "="*60)
    print("💾 TESTING SQLITE MANAGER")
    print("="*60)
    
    # Use test database
    test_db = 'data/test_trades.db'
    if os.path.exists(test_db):
        os.remove(test_db)
    
    db = SQLiteManager(test_db)
    
    # Test 1: Insert trades
    print("\n📊 Test 1: Insert trades...")
    now = datetime.now()
    
    trades = [
        ('TRD001', 'scalping_pro', 'RELIANCE', 'BUY', now, 2450.00, 10),
        ('TRD002', 'scalping_pro', 'TCS', 'BUY', now + timedelta(minutes=5), 3500.00, 5),
        ('TRD003', 'rsi_aggressive', 'INFY', 'BUY', now + timedelta(minutes=10), 1450.00, 15),
    ]
    
    for trade in trades:
        if db.insert_trade(*trade):
            print(f"  ✅ Inserted {trade[0]}")
        else:
            print(f"  ❌ Failed {trade[0]}")
    
    # Test 2: Get open trades
    print("\n📊 Test 2: Get open trades...")
    open_trades = db.get_open_trades()
    print(f"  ✅ Found {len(open_trades)} open trades")
    for trade in open_trades:
        print(f"     - {trade['trade_id']}: {trade['symbol']} @ {trade['entry_price']}")
    
    # Test 3: Close a trade
    print("\n📊 Test 3: Close trade...")
    exit_time = now + timedelta(minutes=15)
    if db.update_trade_exit('TRD001', exit_time, 2465.00, 150.00, 6.12, 'Target hit'):
        print("  ✅ Trade TRD001 closed")
    
    # Test 4: Get closed trades
    print("\n📊 Test 4: Get closed trades...")
    closed_trades = db.get_closed_trades()
    print(f"  ✅ Found {len(closed_trades)} closed trades")
    for trade in closed_trades:
        print(f"     - {trade['trade_id']}: P&L ${trade['pnl']:.2f} ({trade['pnl_pct']:.2f}%)")
    
    # Test 5: Insert signal conditions
    print("\n📊 Test 5: Insert signal conditions...")
    conditions = {
        'ema9': 2448.0,
        'ema21': 2445.0,
        'rsi': 45.5,
        'macd_bullish': True,
        'volume_ok': True
    }
    db.insert_signal_conditions('TRD001', 'entry', conditions, now)
    print("  ✅ Signal conditions stored")
    
    # Test 6: Get signal conditions
    print("\n📊 Test 6: Get signal conditions...")
    retrieved_conditions = db.get_signal_conditions('TRD001', 'entry')
    if retrieved_conditions:
        print(f"  ✅ Retrieved conditions: RSI={retrieved_conditions['rsi']}")
    
    # Test 7: Close more trades for statistics
    print("\n📊 Test 7: Close more trades...")
    db.update_trade_exit('TRD002', exit_time, 3480.00, -100.00, -2.86, 'Stop loss')
    db.update_trade_exit('TRD003', exit_time, 1465.00, 225.00, 10.34, 'Target hit')
    print("  ✅ Additional trades closed")
    
    # Test 8: Strategy statistics
    print("\n📊 Test 8: Strategy statistics...")
    stats = db.get_strategy_stats('scalping_pro', days=30)
    if stats:
        print(f"  ✅ Strategy: scalping_pro")
        print(f"     Total Trades: {stats.get('total_trades', 0)}")
        print(f"     Winners: {stats.get('winners', 0)}")
        print(f"     Losers: {stats.get('losers', 0)}")
        print(f"     Win Rate: {stats.get('win_rate', 0):.2f}%")
        print(f"     Total P&L: ${stats.get('total_pnl', 0):.2f}")
        print(f"     Avg P&L: ${stats.get('avg_pnl', 0):.2f}")
        print(f"     Profit Factor: {stats.get('profit_factor', 0):.2f}")
    
    # Test 9: Symbol performance
    print("\n📊 Test 9: Symbol performance...")
    symbol_perf = db.get_symbol_performance('RELIANCE', days=30)
    if symbol_perf:
        print(f"  ✅ Symbol: RELIANCE")
        print(f"     Total Trades: {symbol_perf.get('total_trades', 0)}")
        print(f"     Total P&L: ${symbol_perf.get('total_pnl', 0):.2f}")
    
    # Test 10: Daily summary
    print("\n📊 Test 10: Daily summary...")
    today = datetime.now().strftime('%Y-%m-%d')
    daily = db.get_daily_summary(today)
    if daily:
        print(f"  ✅ Daily Summary ({today}):")
        print(f"     Total Trades: {daily.get('total_trades', 0)}")
        print(f"     Winners: {daily.get('winners', 0)}")
        print(f"     Total P&L: ${daily.get('total_pnl', 0):.2f}")
    
    # Test 11: Database info
    print("\n📊 Test 11: Database info...")
    size = db.get_database_size()
    counts = db.get_table_counts()
    print(f"  ✅ Database size: {size:,} bytes")
    print(f"  ✅ Table counts:")
    for table, count in counts.items():
        print(f"     - {table}: {count} rows")
    
    # Test 12: Get specific trade
    print("\n📊 Test 12: Get specific trade...")
    trade = db.get_trade('TRD001')
    if trade:
        print(f"  ✅ Trade TRD001:")
        print(f"     Entry: ${trade['entry_price']:.2f} @ {trade['entry_time']}")
        print(f"     Exit: ${trade['exit_price']:.2f} @ {trade['exit_time']}")
        print(f"     Duration: {trade['duration_seconds']}s")
        print(f"     P&L: ${trade['pnl']:.2f} ({trade['pnl_pct']:.2f}%)")
    
    # Cleanup
    db.close()
    print("\n✅ SQLite tests completed!")
    
    # Remove test database
    if os.path.exists(test_db):
        os.remove(test_db)
        print("✅ Test database cleaned up")
    
    return True


def main():
    """Run tests."""
    print("\n" + "="*60)
    print("🚀 VELOX SQLITE INTEGRATION TEST")
    print("="*60)
    
    success = test_sqlite()
    
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    print(f"SQLite: {'✅ PASSED' if success else '❌ FAILED'}")
    print("="*60)
    
    if success:
        print("\n🎉 All tests passed! SQLite integration is ready.")
        return 0
    else:
        print("\n⚠️  Tests failed. Check the output above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
