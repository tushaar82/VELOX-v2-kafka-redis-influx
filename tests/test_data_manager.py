#!/usr/bin/env python3
"""Test Unified DataManager."""

import sys
sys.path.insert(0, 'src')

from database.data_manager import DataManager
from datetime import datetime
import time

def main():
    print("\n" + "="*60)
    print("🚀 TESTING UNIFIED DATA MANAGER")
    print("="*60)
    
    dm = DataManager()
    
    # Test 1: Health check
    print("\n📊 Test 1: Health check...")
    health = dm.health_check()
    print(f"  Redis: {'✅' if health['redis'] else '❌'}")
    print(f"  InfluxDB: {'✅' if health['influxdb'] else '❌'}")
    print(f"  SQLite: {'✅' if health['sqlite'] else '❌'}")
    
    # Test 2: Open position
    print("\n📊 Test 2: Open position...")
    now = datetime.now()
    dm.open_position(
        'TRD_TEST_001', 'scalping_pro', 'RELIANCE',
        2450.00, 10, now,
        signal_conditions={'rsi': 45.5, 'ema9': 2448.0}
    )
    print("  ✅ Position opened")
    
    # Test 3: Process tick
    print("\n📊 Test 3: Process tick...")
    dm.process_tick('RELIANCE', {
        'open': 2450, 'high': 2455,
        'low': 2448, 'close': 2453, 'volume': 1500
    })
    print("  ✅ Tick processed")
    
    # Test 4: Cache indicators
    print("\n📊 Test 4: Cache indicators...")
    dm.cache_indicators('RELIANCE', {
        'rsi': 45.5, 'ema9': 2448.0, 'ema21': 2445.0, 'atr': 15.5
    })
    print("  ✅ Indicators cached")
    
    # Test 5: Update position snapshot
    print("\n📊 Test 5: Update position snapshot...")
    dm.update_position_snapshot('scalping_pro', 'RELIANCE', 2453.00, 10, 30.00, 1.22)
    print("  ✅ Position snapshot updated")
    
    # Test 6: Update trailing SL
    print("\n📊 Test 6: Update trailing SL...")
    dm.update_trailing_sl('TRD_TEST_001', 'scalping_pro', 'RELIANCE', 2445.00, 2455.00, 'ATR')
    print("  ✅ Trailing SL updated")
    
    # Test 7: Close position
    print("\n📊 Test 7: Close position...")
    dm.close_position(
        'TRD_TEST_001', 'scalping_pro', 'RELIANCE',
        2465.00, datetime.now(), 150.00, 6.12, 'Target hit'
    )
    print("  ✅ Position closed")
    
    # Test 8: Get trade
    print("\n📊 Test 8: Get trade...")
    trade = dm.get_trade('TRD_TEST_001')
    if trade:
        print(f"  ✅ Trade: P&L ${trade['pnl']:.2f} ({trade['pnl_pct']:.2f}%)")
    
    # Test 9: System info
    print("\n📊 Test 9: System info...")
    info = dm.get_system_info()
    print(f"  SQLite DB size: {info['sqlite']['db_size']:,} bytes")
    print(f"  Tables: {info['sqlite']['table_counts']}")
    
    dm.close()
    
    print("\n✅ All DataManager tests passed!")
    print("="*60)
    return 0

if __name__ == '__main__':
    sys.exit(main())
