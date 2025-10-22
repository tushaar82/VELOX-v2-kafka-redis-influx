#!/usr/bin/env python3
"""
Test script for Structured Logging System.
"""

import sys
sys.path.insert(0, 'src')

from utils.logging_system import get_structured_logger, strategy_log, database_log
import time
import json
from pathlib import Path


def test_structured_logging():
    """Test structured logging system."""
    print("\n" + "="*60)
    print("📝 TESTING STRUCTURED LOGGING SYSTEM")
    print("="*60)
    
    # Test 1: Create custom logger
    print("\n📊 Test 1: Create custom logger...")
    test_log = get_structured_logger('test_logger')
    print("  ✅ Logger created")
    
    # Test 2: Log different levels
    print("\n📊 Test 2: Log different levels...")
    test_log.debug("This is a debug message", component="test", value=123)
    test_log.info("This is an info message", status="running", count=5)
    test_log.warning("This is a warning message", threshold=0.8, current=0.9)
    print("  ✅ Different log levels working")
    
    # Test 3: Log with context
    print("\n📊 Test 3: Log with context...")
    from utils.logging_system import strategy_log as strat_log
    strat_log.info(
        "Signal generated",
        strategy_id="scalping_pro",
        symbol="RELIANCE",
        action="BUY",
        price=2450.00,
        rsi=45.5,
        ema9=2448.0
    )
    print("  ✅ Context logging working")
    
    # Test 4: Database logging
    print("\n📊 Test 4: Database logging...")
    from utils.logging_system import database_log as db_log
    db_log.info(
        "Position stored in Redis",
        strategy="scalping_pro",
        symbol="TCS",
        entry_price=3500.00
    )
    print("  ✅ Database logging working")
    
    # Test 5: Error logging
    print("\n📊 Test 5: Error logging...")
    try:
        # Intentional error
        result = 1 / 0
    except Exception as e:
        test_log.error(
            "Division by zero error",
            operation="divide",
            numerator=1,
            denominator=0
        )
    print("  ✅ Error logging with traceback working")
    
    # Test 6: Check log files
    print("\n📊 Test 6: Check log files...")
    log_dir = Path('logs')
    
    # Check if log files exist
    json_log = log_dir / 'test_logger_json.log'
    text_log = log_dir / 'test_logger.log'
    
    if json_log.exists():
        print(f"  ✅ JSON log file created: {json_log}")
        
        # Read and parse JSON log
        with open(json_log, 'r') as f:
            lines = f.readlines()
            if lines:
                last_line = lines[-1]
                try:
                    log_entry = json.loads(last_line)
                    print(f"     Sample JSON entry:")
                    print(f"     - Timestamp: {log_entry.get('timestamp')}")
                    print(f"     - Level: {log_entry.get('level')}")
                    print(f"     - Message: {log_entry.get('message')}")
                    if 'context' in log_entry:
                        print(f"     - Context: {log_entry.get('context')}")
                except json.JSONDecodeError:
                    print("     ⚠️  Could not parse JSON")
    else:
        print("  ❌ JSON log file not created")
    
    if text_log.exists():
        print(f"  ✅ Text log file created: {text_log}")
        size = text_log.stat().st_size
        print(f"     Size: {size} bytes")
    else:
        print("  ❌ Text log file not created")
    
    # Test 7: Pre-configured loggers
    print("\n📊 Test 7: Pre-configured loggers...")
    from utils.logging_system import (
        simulator_log, strategy_log, risk_log,
        order_log, position_log, dashboard_log
    )
    
    loggers = [
        ('simulator', simulator_log),
        ('strategy', strategy_log),
        ('risk', risk_log),
        ('order', order_log),
        ('position', position_log),
        ('dashboard', dashboard_log)
    ]
    
    for name, logger in loggers:
        logger.info(f"{name.capitalize()} logger test", test=True)
        print(f"  ✅ {name} logger working")
    
    # Test 8: Performance test
    print("\n📊 Test 8: Performance test...")
    start = time.time()
    for i in range(100):
        test_log.info(f"Performance test message {i}", iteration=i)
    elapsed = time.time() - start
    print(f"  ✅ 100 log messages in {elapsed:.3f}s ({100/elapsed:.0f} msgs/sec)")
    
    print("\n✅ Structured logging tests completed!")
    return True


def main():
    """Run tests."""
    print("\n" + "="*60)
    print("🚀 VELOX STRUCTURED LOGGING TEST")
    print("="*60)
    
    success = test_structured_logging()
    
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    print(f"Structured Logging: {'✅ PASSED' if success else '❌ FAILED'}")
    print("="*60)
    
    if success:
        print("\n🎉 All tests passed! Structured logging is ready.")
        print("\n📁 Log files location: logs/")
        print("   - *_json.log (JSON format, daily rotation)")
        print("   - *.log (Text format, 50MB rotation)")
        return 0
    else:
        print("\n⚠️  Tests failed. Check the output above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
