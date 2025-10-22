#!/usr/bin/env python3
"""
Test dashboard functionality without Flask.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from datetime import datetime
import logging

print("\n" + "="*80)
print("TESTING DASHBOARD SIMULATION")
print("="*80 + "\n")

# Import components
from src.utils.logging_config import initialize_logging, get_logger
from src.adapters.broker.simulated import SimulatedBrokerAdapter
from src.adapters.strategy.rsi_momentum import RSIMomentumStrategy
from src.adapters.data.historical import HistoricalDataManager
from src.core.market_simulator import MarketSimulator
from src.core.multi_strategy_manager import MultiStrategyManager
from src.core.time_controller import TimeController

initialize_logging(log_level=logging.INFO)
logger = get_logger('test')

# Test 1: Load data
print("1. Loading data...")
data_manager = HistoricalDataManager('./data')
stats = data_manager.get_statistics()
print(f"   ✓ Loaded {len(stats['symbols'])} symbols")

# Test 2: Create broker
print("\n2. Creating broker...")
broker = SimulatedBrokerAdapter(initial_capital=100000)
broker.connect()
print("   ✓ Broker connected")

# Test 3: Create strategy
print("\n3. Creating strategy...")
strategy_manager = MultiStrategyManager()
strategy = RSIMomentumStrategy('test', ['ABB'], {
    'rsi_period': 14, 'rsi_oversold': 30, 'rsi_overbought': 70,
    'ma_period': 20, 'target_pct': 0.02, 'initial_sl_pct': 0.01, 'min_volume': 100
})
strategy.initialize()
strategy_manager.add_strategy(strategy)
strategy_manager.start()
print("   ✓ Strategy created")

# Test 4: Load simulation data
print("\n4. Loading simulation data...")
date = '2020-09-15'
df = data_manager.get_data(date, ['ABB'])
print(f"   ✓ Loaded {len(df)} candles")

broker.update_market_price('ABB', df.iloc[0]['open'])

# Test 5: Create simulator
print("\n5. Creating simulator...")
simulator = MarketSimulator(data_manager, date, ['ABB'], speed=1000.0, ticks_per_candle=10)
simulator.load_data()
print("   ✓ Simulator ready")

# Test 6: Run simulation with progress
print("\n6. Running simulation...")
time_controller = TimeController()

tick_count = 0
last_log = 0

def process_tick(tick):
    global tick_count, last_log
    tick_count += 1
    
    broker.update_market_price(tick['symbol'], tick['price'])
    time_controller.check_time(tick['timestamp'])
    strategy_manager.process_tick(tick)
    
    if tick_count - last_log >= 500:
        last_log = tick_count
        print(f"   Processed {tick_count} ticks @ {tick['timestamp'].strftime('%H:%M:%S')}")

try:
    simulator.run_simulation(callback_fn=process_tick)
    print(f"\n   ✓ Simulation complete: {tick_count} ticks processed")
except Exception as e:
    print(f"\n   ✗ Error: {e}")
    import traceback
    traceback.print_exc()

# Test 7: Check final state
print("\n7. Final state:")
account = broker.get_account_info()
print(f"   Capital: ${account['capital']:.2f}")
print(f"   P&L: ${account['pnl']:.2f} ({account['pnl_pct']:.2f}%)")
print(f"   Positions: {account['num_positions']}")

print("\n" + "="*80)
print("✅ TEST COMPLETE")
print("="*80 + "\n")
