#!/usr/bin/env python3
"""
Quick test for Supertrend strategy instantiation.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from adapters.strategy.supertrend import SupertrendStrategy
from utils.logging_config import initialize_logging
import logging

initialize_logging(log_level=logging.INFO)

print("\n" + "="*60)
print("Testing Supertrend Strategy")
print("="*60)

# Test instantiation
try:
    strategy = SupertrendStrategy('test_supertrend', ['ABB', 'BATAINDIA'], {
        'atr_period': 10,
        'atr_multiplier': 3,
        'min_hold_time_minutes': 5,
        'min_volume': 50,
        'position_size_pct': 0.1
    })
    
    print("\n✅ SupertrendStrategy instantiated successfully!")
    print(f"   Strategy ID: {strategy.strategy_id}")
    print(f"   Symbols: {strategy.symbols}")
    print(f"   ATR Period: {strategy.atr_period}")
    print(f"   ATR Multiplier: {strategy.atr_multiplier}")
    print(f"   Min Hold Time: {strategy.min_hold_time_minutes} minutes")
    
    # Test initialize
    strategy.initialize()
    print("\n✅ Strategy initialized successfully!")
    
    # Test methods exist
    assert hasattr(strategy, 'on_tick'), "Missing on_tick method"
    assert hasattr(strategy, 'on_candle_close'), "Missing on_candle_close method"
    assert hasattr(strategy, 'check_entry_conditions'), "Missing check_entry_conditions method"
    assert hasattr(strategy, 'check_exit_conditions'), "Missing check_exit_conditions method"
    assert hasattr(strategy, 'calculate_supertrend'), "Missing calculate_supertrend method"
    
    print("\n✅ All required methods present!")
    
    print("\n" + "="*60)
    print("✓ Supertrend Strategy Test PASSED")
    print("="*60 + "\n")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
