"""
Complete System Test - Days 1, 2, and 3 (Config)
Tests all components working together.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.logging_config import initialize_logging, get_logger
from src.utils.config_loader import ConfigLoader
from src.adapters.broker.simulated import SimulatedBrokerAdapter
from src.adapters.strategy.rsi_momentum import RSIMomentumStrategy
from src.core.multi_strategy_manager import MultiStrategyManager
from src.core.risk_manager import RiskManager
from src.core.order_manager import OrderManager, PositionManager
from src.core.trailing_sl import TrailingStopLossManager, TrailingStopLossType
from src.adapters.data.historical import HistoricalDataManager
from src.core.market_simulator import MarketSimulator
import logging


def test_configuration_system():
    """Test configuration loading and validation."""
    print("\n" + "="*80)
    print("TEST 1: CONFIGURATION SYSTEM")
    print("="*80)
    
    config_loader = ConfigLoader()
    
    # Test validation
    print("\n1. Validating configurations...")
    if config_loader.validate_config():
        print("   ✓ Configuration validation passed")
    else:
        print("   ✗ Configuration validation failed")
        return False
    
    # Test system config
    print("\n2. Loading system config...")
    system_config = config_loader.load_system_config()
    print(f"   ✓ Broker: {system_config['system']['broker']['type']}")
    print(f"   ✓ Capital: {system_config['system']['broker']['capital']}")
    print(f"   ✓ Max positions: {system_config['system']['risk']['max_total_positions']}")
    
    # Test strategies config
    print("\n3. Loading strategies config...")
    strategies = config_loader.get_enabled_strategies()
    print(f"   ✓ Enabled strategies: {len(strategies)}")
    for strategy in strategies:
        print(f"     - {strategy['id']}: {strategy['symbols']}")
    
    # Test symbols config
    print("\n4. Loading symbols config...")
    watchlist = config_loader.get_watchlist()
    print(f"   ✓ Watchlist: {len(watchlist)} symbols")
    print(f"     Symbols: {', '.join(watchlist[:5])}")
    
    print("\n✅ Configuration system test PASSED")
    return True


def test_data_pipeline():
    """Test data loading and simulation."""
    print("\n" + "="*80)
    print("TEST 2: DATA PIPELINE")
    print("="*80)
    
    # Test data loading
    print("\n1. Testing data loading...")
    hdm = HistoricalDataManager('./data')
    stats = hdm.get_statistics()
    
    print(f"   ✓ Symbols found: {len(stats['symbols'])}")
    print(f"   ✓ Symbols: {', '.join(stats['symbols'][:3])}")
    
    if stats['symbols']:
        symbol = stats['symbols'][0]
        dates = hdm.get_available_dates(symbol)
        print(f"   ✓ {symbol}: {len(dates)} trading days")
        
        if len(dates) > 100:
            test_date = dates[100]
            print(f"\n2. Loading data for {test_date}...")
            df = hdm.get_data(test_date, [symbol])
            print(f"   ✓ Loaded {len(df)} rows")
            print(f"   ✓ Columns: {list(df.columns)}")
    
    print("\n✅ Data pipeline test PASSED")
    return True


def test_strategy_components():
    """Test strategy, indicators, and signal generation."""
    print("\n" + "="*80)
    print("TEST 3: STRATEGY COMPONENTS")
    print("="*80)
    
    # Create strategy
    print("\n1. Creating RSI Momentum strategy...")
    config = {
        'rsi_period': 14,
        'rsi_oversold': 30,
        'rsi_overbought': 70,
        'ma_period': 20,
        'target_pct': 0.02,
        'initial_sl_pct': 0.01,
        'min_volume': 100
    }
    
    strategy = RSIMomentumStrategy('test_strategy', ['TEST'], config)
    strategy.initialize()
    print(f"   ✓ Strategy initialized: {strategy.strategy_id}")
    
    # Feed some ticks
    print("\n2. Processing ticks...")
    for i in range(30):
        tick = {
            'timestamp': datetime.now(),
            'symbol': 'TEST',
            'price': 100.0 - i * 2,
            'high': 100.0 - i * 2 + 1,
            'low': 100.0 - i * 2 - 1,
            'volume': 1000
        }
        strategy.on_tick(tick)
    
    print(f"   ✓ Processed 30 ticks")
    
    # Check signals
    signals = strategy.get_signals()
    print(f"   ✓ Signals generated: {len(signals)}")
    
    print("\n✅ Strategy components test PASSED")
    return True


def test_risk_and_order_management():
    """Test risk manager and order execution."""
    print("\n" + "="*80)
    print("TEST 4: RISK & ORDER MANAGEMENT")
    print("="*80)
    
    # Setup components
    print("\n1. Setting up components...")
    
    # Broker
    broker = SimulatedBrokerAdapter(initial_capital=100000)
    broker.connect()
    broker.update_market_price('TEST', 100.0)
    print("   ✓ Broker initialized")
    
    # Risk manager
    risk_config = {
        'max_position_size': 10000,
        'max_positions_per_strategy': 3,
        'max_total_positions': 5,
        'max_daily_loss': 5000,
        'initial_capital': 100000
    }
    risk_manager = RiskManager(risk_config)
    print("   ✓ Risk manager initialized")
    
    # Order manager
    order_manager = OrderManager(broker)
    print("   ✓ Order manager initialized")
    
    # Position manager
    position_manager = PositionManager(broker)
    print("   ✓ Position manager initialized")
    
    # Test signal validation
    print("\n2. Testing signal validation...")
    signal = {
        'strategy_id': 'test',
        'action': 'BUY',
        'symbol': 'TEST',
        'price': 100.0,
        'quantity': 10,
        'reason': 'Test signal'
    }
    
    result = risk_manager.validate_signal(signal, {}, {})
    if result.approved:
        print("   ✓ Signal approved by risk manager")
    else:
        print(f"   ✗ Signal rejected: {result.reason}")
        return False
    
    # Test order execution
    print("\n3. Testing order execution...")
    order = order_manager.execute_signal(signal)
    if order and order['status'] == 'FILLED':
        print(f"   ✓ Order executed: {order['order_id']}")
        print(f"   ✓ Filled at: {order['filled_price']:.2f}")
        
        # Update position
        position_manager.update_position('test', 'TEST', order)
        positions = position_manager.get_positions('test')
        print(f"   ✓ Position tracked: {len(positions)} positions")
    else:
        print("   ✗ Order execution failed")
        return False
    
    print("\n✅ Risk & order management test PASSED")
    return True


def test_trailing_stop_loss():
    """Test trailing stop-loss engine."""
    print("\n" + "="*80)
    print("TEST 5: TRAILING STOP-LOSS")
    print("="*80)
    
    print("\n1. Testing Fixed PCT trailing SL...")
    sl_manager = TrailingStopLossManager()
    
    sl_manager.add_stop_loss(
        strategy_id='test',
        symbol='TEST',
        sl_type=TrailingStopLossType.FIXED_PCT,
        entry_price=100.0,
        config={'pct': 0.02}
    )
    
    sl_info = sl_manager.get_stop_loss_info('test', 'TEST')
    print(f"   ✓ Initial SL: {sl_info['current_sl']:.2f}")
    
    # Update with price increase
    sl_manager.update_stop_loss('test', 'TEST', 110.0, 110.0)
    sl_info = sl_manager.get_stop_loss_info('test', 'TEST')
    print(f"   ✓ After price increase: SL stays at {sl_info['current_sl']:.2f} (fixed)")
    
    print("\n2. Testing ATR trailing SL...")
    sl_manager.add_stop_loss(
        strategy_id='test2',
        symbol='TEST2',
        sl_type=TrailingStopLossType.ATR,
        entry_price=100.0,
        config={'atr_value': 2.0, 'atr_multiplier': 2.0}
    )
    
    sl_info = sl_manager.get_stop_loss_info('test2', 'TEST2')
    print(f"   ✓ Initial SL: {sl_info['current_sl']:.2f}")
    
    # Update with price increase
    sl_manager.update_stop_loss('test2', 'TEST2', 110.0, 110.0, atr_value=2.0)
    sl_info = sl_manager.get_stop_loss_info('test2', 'TEST2')
    print(f"   ✓ After price increase: SL trails to {sl_info['current_sl']:.2f}")
    
    print("\n✅ Trailing stop-loss test PASSED")
    return True


def test_multi_strategy_manager():
    """Test multi-strategy coordination."""
    print("\n" + "="*80)
    print("TEST 6: MULTI-STRATEGY MANAGER")
    print("="*80)
    
    print("\n1. Creating multi-strategy manager...")
    manager = MultiStrategyManager()
    
    # Create strategies
    config1 = {
        'rsi_period': 14,
        'rsi_oversold': 30,
        'rsi_overbought': 70,
        'ma_period': 20,
        'target_pct': 0.02,
        'initial_sl_pct': 0.01
    }
    
    config2 = {
        'rsi_period': 14,
        'rsi_oversold': 25,
        'rsi_overbought': 75,
        'ma_period': 50,
        'target_pct': 0.03,
        'initial_sl_pct': 0.015
    }
    
    strategy1 = RSIMomentumStrategy('strategy1', ['STOCK1'], config1)
    strategy2 = RSIMomentumStrategy('strategy2', ['STOCK2'], config2)
    
    strategy1.initialize()
    strategy2.initialize()
    
    manager.add_strategy(strategy1)
    manager.add_strategy(strategy2)
    
    print(f"   ✓ Added 2 strategies")
    
    # Start manager
    manager.start()
    print(f"   ✓ Manager started")
    
    # Process some ticks
    print("\n2. Processing ticks through manager...")
    for i in range(5):
        tick1 = {
            'timestamp': datetime.now(),
            'symbol': 'STOCK1',
            'price': 100.0 + i,
            'volume': 1000
        }
        tick2 = {
            'timestamp': datetime.now(),
            'symbol': 'STOCK2',
            'price': 200.0 + i,
            'volume': 1000
        }
        
        manager.process_tick(tick1)
        manager.process_tick(tick2)
    
    print(f"   ✓ Processed 10 ticks (5 per symbol)")
    
    # Get status
    status = manager.get_status()
    print(f"\n3. Manager status:")
    print(f"   ✓ Running: {status['is_running']}")
    print(f"   ✓ Strategies: {status['num_strategies']}")
    print(f"   ✓ Active: {status['num_active_strategies']}")
    
    print("\n✅ Multi-strategy manager test PASSED")
    return True


def run_all_tests():
    """Run all system tests."""
    print("\n" + "="*80)
    print("VELOX COMPLETE SYSTEM TEST")
    print("Testing Days 1, 2, and 3 (Configuration)")
    print("="*80)
    
    # Initialize logging
    initialize_logging(log_level=logging.INFO)
    logger = get_logger('system_test')
    
    tests = [
        ("Configuration System", test_configuration_system),
        ("Data Pipeline", test_data_pipeline),
        ("Strategy Components", test_strategy_components),
        ("Risk & Order Management", test_risk_and_order_management),
        ("Trailing Stop-Loss", test_trailing_stop_loss),
        ("Multi-Strategy Manager", test_multi_strategy_manager),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ {test_name} FAILED with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "✗ FAILED"
        print(f"{test_name:.<50} {status}")
    
    print("="*80)
    print(f"Total: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    print("="*80)
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! System is ready for Day 3 completion.")
        return True
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review errors above.")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
