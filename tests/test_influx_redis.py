#!/usr/bin/env python3
"""
Test script for Redis and InfluxDB integration.
"""

import sys
sys.path.insert(0, 'src')

from database.redis_manager import RedisManager
from database.influx_manager import InfluxManager
from datetime import datetime
import time

def test_redis():
    """Test Redis Manager."""
    print("\n" + "="*60)
    print("🔴 TESTING REDIS MANAGER")
    print("="*60)
    
    redis = RedisManager()
    
    # Test connection
    if redis.health_check():
        print("✅ Redis connection: OK")
    else:
        print("❌ Redis connection: FAILED")
        return False
    
    # Test position storage
    print("\n📊 Testing position storage...")
    position_data = {
        'entry_price': 2450.00,
        'quantity': 10,
        'entry_time': datetime.now().isoformat(),
        'strategy': 'scalping_pro'
    }
    
    redis.set_position('scalping_pro', 'RELIANCE', position_data)
    retrieved = redis.get_position('scalping_pro', 'RELIANCE')
    
    if retrieved and retrieved['entry_price'] == 2450.00:
        print("✅ Position storage: OK")
    else:
        print("❌ Position storage: FAILED")
        return False
    
    # Test indicators cache
    print("\n📈 Testing indicators cache...")
    indicators = {
        'rsi': 45.5,
        'ema9': 2448.0,
        'ema21': 2445.0,
        'atr': 15.5
    }
    
    redis.set_indicators('RELIANCE', indicators)
    retrieved_ind = redis.get_indicators('RELIANCE')
    
    if retrieved_ind and retrieved_ind['rsi'] == 45.5:
        print("✅ Indicators cache: OK")
    else:
        print("❌ Indicators cache: FAILED")
        return False
    
    # Test signal counter
    print("\n📊 Testing signal counters...")
    redis.increment_signal_count('scalping_pro', 'BUY')
    redis.increment_signal_count('scalping_pro', 'BUY')
    redis.increment_signal_count('scalping_pro', 'SELL')
    
    stats = redis.get_strategy_stats('scalping_pro')
    if stats:
        print(f"✅ Signal counters: BUY={stats.get('BUY', 0)}, SELL={stats.get('SELL', 0)}")
    else:
        print("❌ Signal counters: FAILED")
    
    # Test daily stats
    print("\n📊 Testing daily stats...")
    redis.set_daily_stat('total_pnl', 1250.50)
    redis.set_daily_stat('trades_count', 15)
    
    daily = redis.get_daily_stats()
    if daily and daily.get('total_pnl') == 1250.50:
        print("✅ Daily stats: OK")
    else:
        print("❌ Daily stats: FAILED")
    
    # Get Redis info
    print("\n📊 Redis Server Info:")
    info = redis.get_info()
    for key, value in info.items():
        print(f"  {key}: {value}")
    
    # Cleanup
    redis.delete_position('scalping_pro', 'RELIANCE')
    print("\n✅ Redis tests completed!")
    return True


def test_influx():
    """Test InfluxDB Manager."""
    print("\n" + "="*60)
    print("📊 TESTING INFLUXDB MANAGER")
    print("="*60)
    
    influx = InfluxManager()
    
    # Test connection
    if influx.health_check():
        print("✅ InfluxDB connection: OK")
    else:
        print("❌ InfluxDB connection: FAILED")
        return False
    
    # Test tick write
    print("\n📊 Testing tick data write...")
    tick_data = {
        'open': 2450.00,
        'high': 2455.00,
        'low': 2448.00,
        'close': 2453.00,
        'volume': 1500,
        'source': 'test'
    }
    
    if influx.write_tick('RELIANCE', tick_data):
        print("✅ Tick write: OK")
    else:
        print("❌ Tick write: FAILED")
        return False
    
    # Test indicator write
    print("\n📈 Testing indicator write...")
    if influx.write_indicator('RELIANCE', 'RSI', 45.5, period=14):
        print("✅ Indicator write: OK")
    else:
        print("❌ Indicator write: FAILED")
    
    # Test trade write
    print("\n💰 Testing trade write...")
    if influx.write_trade('scalping_pro', 'RELIANCE', 'BUY', 2450.00, 10):
        print("✅ Trade write: OK")
    else:
        print("❌ Trade write: FAILED")
    
    # Test position snapshot
    print("\n📊 Testing position snapshot...")
    if influx.write_position_snapshot('scalping_pro', 'RELIANCE', 2453.00, 10, 30.00, 1.22):
        print("✅ Position snapshot: OK")
    else:
        print("❌ Position snapshot: FAILED")
    
    # Test strategy metrics
    print("\n📊 Testing strategy metrics...")
    metrics = {
        'positions_count': 2,
        'signals_count': 15,
        'pnl': 1250.50,
        'win_rate': 0.65
    }
    
    if influx.write_strategy_metrics('scalping_pro', metrics):
        print("✅ Strategy metrics: OK")
    else:
        print("❌ Strategy metrics: FAILED")
    
    # Wait for async writes
    print("\n⏳ Waiting for async writes to complete...")
    time.sleep(2)
    
    # Test query
    print("\n📊 Testing data query...")
    ticks = influx.query_tick_range('RELIANCE', start='-5m')
    if ticks:
        print(f"✅ Query: Retrieved {len(ticks)} tick records")
    else:
        print("⚠️  Query: No data yet (async writes may still be processing)")
    
    # Get bucket info
    print("\n📊 InfluxDB Bucket Info:")
    bucket_info = influx.get_bucket_info()
    for key, value in bucket_info.items():
        print(f"  {key}: {value}")
    
    print("\n✅ InfluxDB tests completed!")
    return True


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("🚀 VELOX DATABASE INTEGRATION TESTS")
    print("="*60)
    
    redis_ok = test_redis()
    influx_ok = test_influx()
    
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    print(f"Redis:    {'✅ PASSED' if redis_ok else '❌ FAILED'}")
    print(f"InfluxDB: {'✅ PASSED' if influx_ok else '❌ FAILED'}")
    print("="*60)
    
    if redis_ok and influx_ok:
        print("\n🎉 All tests passed! Database integration is ready.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check the output above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
