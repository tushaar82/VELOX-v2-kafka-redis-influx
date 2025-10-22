#!/usr/bin/env python3
"""
Quick test to verify trailing SL is working correctly.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.core.trailing_sl import TrailingStopLossManager, TrailingStopLossType
from datetime import datetime

print("\n" + "="*60)
print("Testing Trailing Stop Loss Manager")
print("="*60)

# Create manager
manager = TrailingStopLossManager()

# Test 1: Add a trailing SL
print("\n1. Adding trailing SL for ABB...")
entry_price = 916.72
initial_atr = entry_price * 0.02  # 2% = 18.33
atr_multiplier = 2.5

manager.add_stop_loss(
    strategy_id='rsi_aggressive',
    symbol='ABB',
    sl_type=TrailingStopLossType.ATR,
    entry_price=entry_price,
    config={'atr_value': initial_atr, 'atr_multiplier': atr_multiplier},
    entry_timestamp=datetime.now()
)

sl_info = manager.get_stop_loss_info('rsi_aggressive', 'ABB')
print(f"   Entry: ${entry_price:.2f}")
print(f"   Initial ATR: ${initial_atr:.2f}")
print(f"   Multiplier: {atr_multiplier}x")
print(f"   Initial SL: ${sl_info['current_sl']:.2f}")
print(f"   Distance: ${entry_price - sl_info['current_sl']:.2f} ({((entry_price - sl_info['current_sl'])/entry_price)*100:.2f}%)")

# Test 2: Update as price moves up
print("\n2. Price moves to $920.00...")
current_price = 920.00
highest_price = 920.00
atr_value = (highest_price - entry_price) * 0.5  # Dynamic ATR

manager.update_stop_loss(
    strategy_id='rsi_aggressive',
    symbol='ABB',
    current_price=current_price,
    highest_price=highest_price,
    atr_value=max(atr_value, initial_atr)
)

sl_info = manager.get_stop_loss_info('rsi_aggressive', 'ABB')
print(f"   Current: ${current_price:.2f}")
print(f"   Highest: ${highest_price:.2f}")
print(f"   ATR: ${atr_value:.2f}")
print(f"   Trailing SL: ${sl_info['current_sl']:.2f}")
print(f"   Distance: ${highest_price - sl_info['current_sl']:.2f} ({((highest_price - sl_info['current_sl'])/highest_price)*100:.2f}%)")

is_hit = manager.check_stop_loss('rsi_aggressive', 'ABB', current_price)
print(f"   SL Hit? {is_hit}")

# Test 3: Price moves higher
print("\n3. Price moves to $925.50...")
current_price = 925.50
highest_price = 925.50
atr_value = (highest_price - entry_price) * 0.5

manager.update_stop_loss(
    strategy_id='rsi_aggressive',
    symbol='ABB',
    current_price=current_price,
    highest_price=highest_price,
    atr_value=max(atr_value, initial_atr)
)

sl_info = manager.get_stop_loss_info('rsi_aggressive', 'ABB')
print(f"   Current: ${current_price:.2f}")
print(f"   Highest: ${highest_price:.2f}")
print(f"   ATR: ${atr_value:.2f}")
print(f"   Trailing SL: ${sl_info['current_sl']:.2f}")
print(f"   Distance: ${highest_price - sl_info['current_sl']:.2f} ({((highest_price - sl_info['current_sl'])/highest_price)*100:.2f}%)")

is_hit = manager.check_stop_loss('rsi_aggressive', 'ABB', current_price)
print(f"   SL Hit? {is_hit}")

# Test 4: Price retraces
print("\n4. Price retraces to $920.30...")
current_price = 920.30
# Highest stays at 925.50

manager.update_stop_loss(
    strategy_id='rsi_aggressive',
    symbol='ABB',
    current_price=current_price,
    highest_price=highest_price,  # Still 925.50
    atr_value=max(atr_value, initial_atr)
)

sl_info = manager.get_stop_loss_info('rsi_aggressive', 'ABB')
print(f"   Current: ${current_price:.2f}")
print(f"   Highest: ${highest_price:.2f}")
print(f"   Trailing SL: ${sl_info['current_sl']:.2f}")

is_hit = manager.check_stop_loss('rsi_aggressive', 'ABB', current_price)
print(f"   SL Hit? {is_hit}")

if is_hit:
    print(f"   ✅ TRAILING SL TRIGGERED! Exit @ ${current_price:.2f}")
    pnl = current_price - entry_price
    pnl_pct = (pnl / entry_price) * 100
    print(f"   P&L: ${pnl:.2f} ({pnl_pct:+.2f}%)")
else:
    print(f"   ❌ SL not hit yet")

print("\n" + "="*60)
print("✓ Test complete")
print("="*60 + "\n")
