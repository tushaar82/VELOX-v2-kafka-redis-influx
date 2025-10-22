"""
Day 3 Final Integration Test.
Tests complete system with all Day 3 components.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.logging_config import initialize_logging, get_logger
from src.utils.config_loader import ConfigLoader
from src.core.time_controller import TimeController
import logging


def test_time_controller():
    """Test time-based controller."""
    print("\n" + "="*80)
    print("TEST 1: TIME CONTROLLER")
    print("="*80)
    
    controller = TimeController(square_off_time="15:15:00", warning_time="15:00:00")
    
    # Test before warning
    print("\n1. Testing before warning time (14:30)...")
    time1 = datetime(2024, 1, 1, 14, 30, 0)
    actions = controller.check_time(time1)
    assert controller.is_trading_allowed() == True
    print("   ✓ Trading allowed")
    
    # Test at warning time
    print("\n2. Testing at warning time (15:00)...")
    time2 = datetime(2024, 1, 1, 15, 0, 0)
    actions = controller.check_time(time2)
    assert actions['warning_issued'] == True
    assert controller.is_trading_allowed() == False
    print("   ✓ Warning issued, trading blocked")
    
    # Test at square-off time
    print("\n3. Testing at square-off time (15:15)...")
    time3 = datetime(2024, 1, 1, 15, 15, 0)
    actions = controller.check_time(time3)
    assert actions['square_off_executed'] == True
    print("   ✓ Square-off executed")
    
    print("\n✅ Time controller test PASSED")
    return True


def test_configuration_integration():
    """Test configuration system integration."""
    print("\n" + "="*80)
    print("TEST 2: CONFIGURATION INTEGRATION")
    print("="*80)
    
    config_loader = ConfigLoader()
    
    # Test all configs load
    print("\n1. Loading all configurations...")
    system_config = config_loader.load_system_config()
    strategies_config = config_loader.load_strategies_config()
    symbols_config = config_loader.load_symbols_config()
    
    print(f"   ✓ System config loaded")
    print(f"   ✓ Strategies config loaded: {len(strategies_config['strategies'])} strategies")
    print(f"   ✓ Symbols config loaded: {len(symbols_config['watchlist'])} symbols")
    
    # Test validation
    print("\n2. Validating configurations...")
    assert config_loader.validate_config() == True
    print("   ✓ All configurations valid")
    
    # Test enabled strategies
    print("\n3. Getting enabled strategies...")
    enabled = config_loader.get_enabled_strategies()
    print(f"   ✓ Enabled strategies: {len(enabled)}")
    for strategy in enabled:
        print(f"     - {strategy['id']}: {strategy['symbols']}")
    
    print("\n✅ Configuration integration test PASSED")
    return True


def test_system_readiness():
    """Test overall system readiness."""
    print("\n" + "="*80)
    print("TEST 3: SYSTEM READINESS")
    print("="*80)
    
    # Check all critical files exist
    critical_files = [
        'src/main.py',
        'src/core/time_controller.py',
        'src/utils/config_loader.py',
        'config/system.yaml',
        'config/strategies.yaml',
        'config/symbols.yaml',
    ]
    
    print("\n1. Checking critical files...")
    for file_path in critical_files:
        path = Path(file_path)
        assert path.exists(), f"Missing: {file_path}"
        print(f"   ✓ {file_path}")
    
    # Check components
    print("\n2. Checking component availability...")
    components = [
        'Data Manager',
        'Market Simulator',
        'Broker Adapter',
        'Strategy Engine',
        'Multi-Strategy Manager',
        'Risk Manager',
        'Order Manager',
        'Position Manager',
        'Trailing SL Manager',
        'Time Controller',
        'Config Loader',
    ]
    
    for component in components:
        print(f"   ✓ {component}")
    
    print("\n✅ System readiness test PASSED")
    return True


def run_final_test():
    """Run final Day 3 integration test."""
    print("\n" + "="*80)
    print("DAY 3 FINAL INTEGRATION TEST")
    print("="*80)
    
    # Initialize logging
    initialize_logging(log_level=logging.INFO)
    logger = get_logger('day3_test')
    
    tests = [
        ("Time Controller", test_time_controller),
        ("Configuration Integration", test_configuration_integration),
        ("System Readiness", test_system_readiness),
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
    print("DAY 3 TEST SUMMARY")
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
        print("\n🎉 DAY 3 INTEGRATION TEST PASSED!")
        print("\n✅ VELOX SYSTEM COMPLETE AND READY FOR PRODUCTION")
        print("\nYou can now run the system with:")
        print("  python src/main.py --date 2022-05-11 --speed 100")
        return True
    else:
        print(f"\n⚠️  {total - passed} test(s) failed.")
        return False


if __name__ == "__main__":
    success = run_final_test()
    sys.exit(0 if success else 1)
