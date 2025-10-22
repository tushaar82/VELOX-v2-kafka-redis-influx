"""
Day 2 Integration Test.
End-to-end validation of strategy engine and risk management.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.adapters.broker.simulated import SimulatedBrokerAdapter
from src.adapters.strategy.rsi_momentum import RSIMomentumStrategy
from src.core.multi_strategy_manager import MultiStrategyManager
from src.core.risk_manager import RiskManager
from src.core.order_manager import OrderManager, PositionManager
from src.core.trailing_sl import TrailingStopLossManager, TrailingStopLossType
from src.utils.logging_config import initialize_logging, get_logger
import logging


def test_complete_signal_flow():
    """Test complete signal flow from strategy to execution."""
    print("\n" + "="*80)
    print("DAY 2 INTEGRATION TEST - Complete Signal Flow")
    print("="*80 + "\n")
    
    # Initialize logging
    initialize_logging(log_level=logging.INFO)
    logger = get_logger('integration_test')
    
    # 1. Setup components
    print("1. Setting up components...")
    
    # Broker
    broker = SimulatedBrokerAdapter(initial_capital=100000)
    broker.connect()
    print("   ✓ Broker initialized")
    
    # Risk Manager
    risk_config = {
        'max_position_size': 10000,
        'max_positions_per_strategy': 3,
        'max_total_positions': 5,
        'max_daily_loss': 5000,
        'initial_capital': 100000
    }
    risk_manager = RiskManager(risk_config)
    print("   ✓ Risk Manager initialized")
    
    # Order & Position Managers
    order_manager = OrderManager(broker)
    position_manager = PositionManager(broker)
    print("   ✓ Order & Position Managers initialized")
    
    # Trailing SL Manager
    sl_manager = TrailingStopLossManager()
    print("   ✓ Trailing SL Manager initialized")
    
    # Multi-Strategy Manager
    strategy_manager = MultiStrategyManager()
    print("   ✓ Multi-Strategy Manager initialized")
    
    # 2. Create strategies
    print("\n2. Creating strategies...")
    
    strategy1_config = {
        'rsi_period': 14,
        'rsi_oversold': 30,
        'rsi_overbought': 70,
        'ma_period': 20,
        'target_pct': 0.02,
        'initial_sl_pct': 0.01,
        'min_volume': 100
    }
    
    strategy1 = RSIMomentumStrategy('rsi_aggressive', ['STOCK1'], strategy1_config)
    strategy1.initialize()
    strategy_manager.add_strategy(strategy1)
    print("   ✓ Strategy 'rsi_aggressive' added")
    
    strategy2_config = {
        'rsi_period': 14,
        'rsi_oversold': 25,
        'rsi_overbought': 75,
        'ma_period': 50,
        'target_pct': 0.03,
        'initial_sl_pct': 0.015,
        'min_volume': 100
    }
    
    strategy2 = RSIMomentumStrategy('rsi_conservative', ['STOCK2'], strategy2_config)
    strategy2.initialize()
    strategy_manager.add_strategy(strategy2)
    print("   ✓ Strategy 'rsi_conservative' added")
    
    strategy_manager.start()
    
    # 3. Simulate market data to generate signals
    print("\n3. Simulating market data...")
    
    # Update broker prices
    broker.update_market_price('STOCK1', 100.0)
    broker.update_market_price('STOCK2', 200.0)
    
    # Generate downtrend for STOCK1 (to make RSI oversold)
    for i in range(30):
        tick = {
            'timestamp': datetime.now(),
            'symbol': 'STOCK1',
            'price': 100.0 - i * 2,
            'high': 100.0 - i * 2 + 1,
            'low': 100.0 - i * 2 - 1,
            'volume': 1000
        }
        strategy_manager.process_tick(tick)
        broker.update_market_price('STOCK1', tick['price'])
    
    print(f"   ✓ Processed 30 ticks for STOCK1")
    
    # Generate downtrend for STOCK2
    for i in range(30):
        tick = {
            'timestamp': datetime.now(),
            'symbol': 'STOCK2',
            'price': 200.0 - i * 3,
            'high': 200.0 - i * 3 + 1,
            'low': 200.0 - i * 3 - 1,
            'volume': 1000
        }
        strategy_manager.process_tick(tick)
        broker.update_market_price('STOCK2', tick['price'])
    
    print(f"   ✓ Processed 30 ticks for STOCK2")
    
    # 4. Check for signals
    print("\n4. Checking for signals...")
    signals = strategy_manager.get_all_signals()
    print(f"   Signals generated: {len(signals)}")
    
    for signal in signals:
        print(f"   - {signal['strategy_id']}/{signal['symbol']}: {signal['action']} @ {signal['price']:.2f}")
        print(f"     Reason: {signal['reason']}")
    
    # 5. Validate signals through risk manager
    print("\n5. Validating signals through risk manager...")
    
    approved_signals = []
    rejected_signals = []
    
    current_positions = strategy_manager.get_all_positions()
    
    for signal in signals:
        result = risk_manager.validate_signal(signal, current_positions, {})
        
        if result.approved:
            approved_signals.append(signal)
            print(f"   ✓ APPROVED: {signal['strategy_id']}/{signal['symbol']}")
        else:
            rejected_signals.append(signal)
            print(f"   ✗ REJECTED: {signal['strategy_id']}/{signal['symbol']} - {result.reason}")
    
    print(f"\n   Approved: {len(approved_signals)}, Rejected: {len(rejected_signals)}")
    
    # 6. Execute approved signals
    print("\n6. Executing approved signals...")
    
    for signal in approved_signals:
        order = order_manager.execute_signal(signal)
        
        if order and order['status'] == 'FILLED':
            # Update position
            position_manager.update_position(signal['strategy_id'], signal['symbol'], order)
            
            # Update strategy position
            strategy = strategy_manager.get_strategy(signal['strategy_id'])
            if strategy:
                strategy.add_position(
                    signal['symbol'],
                    order['filled_price'],
                    order['filled_quantity'],
                    order['fill_timestamp']
                )
            
            # Add trailing SL
            sl_manager.add_stop_loss(
                strategy_id=signal['strategy_id'],
                symbol=signal['symbol'],
                sl_type=TrailingStopLossType.FIXED_PCT,
                entry_price=order['filled_price'],
                config={'pct': 0.01}
            )
            
            print(f"   ✓ Executed: {signal['symbol']} @ {order['filled_price']:.2f}")
    
    # 7. Check positions
    print("\n7. Checking positions...")
    
    all_positions = position_manager.get_positions()
    total_positions = position_manager.get_all_positions_count()
    
    print(f"   Total positions: {total_positions}")
    
    for strategy_id, positions in all_positions.items():
        print(f"\n   Strategy: {strategy_id}")
        for symbol, pos in positions.items():
            print(f"     {symbol}: {pos['quantity']} @ {pos['average_price']:.2f}")
    
    # 8. Simulate price movement and check trailing SL
    print("\n8. Simulating price movement and trailing SL...")
    
    if total_positions > 0:
        # Simulate price going up
        for strategy_id, positions in all_positions.items():
            for symbol in positions.keys():
                current_price = broker.current_prices.get(symbol, 100.0)
                new_price = current_price * 1.01  # 1% up
                
                broker.update_market_price(symbol, new_price)
                sl_manager.update_stop_loss(strategy_id, symbol, new_price, new_price)
                
                sl_info = sl_manager.get_stop_loss_info(strategy_id, symbol)
                if sl_info:
                    print(f"   {strategy_id}/{symbol}: Price={new_price:.2f}, SL={sl_info['current_sl']:.2f}")
    
    # 9. Get final status
    print("\n9. Final status...")
    
    # Strategy manager status
    strategy_status = strategy_manager.get_status()
    print(f"\n   Strategy Manager:")
    print(f"     Running: {strategy_status['is_running']}")
    print(f"     Strategies: {strategy_status['num_strategies']}")
    print(f"     Active: {strategy_status['num_active_strategies']}")
    print(f"     Total positions: {strategy_status['total_positions']}")
    
    # Risk metrics
    risk_metrics = risk_manager.get_risk_metrics()
    print(f"\n   Risk Manager:")
    print(f"     Daily P&L: {risk_metrics['daily_pnl']:.2f}")
    print(f"     Daily trades: {risk_metrics['daily_trades']}")
    print(f"     Trading allowed: {risk_metrics['trading_allowed']}")
    
    # Broker account
    account = broker.get_account_info()
    print(f"\n   Broker Account:")
    print(f"     Capital: {account['capital']:.2f}")
    print(f"     Total value: {account['total_value']:.2f}")
    print(f"     P&L: {account['pnl']:.2f} ({account['pnl_pct']:.2f}%)")
    print(f"     Positions: {account['num_positions']}")
    
    # 10. Summary
    print("\n" + "="*80)
    print("INTEGRATION TEST SUMMARY")
    print("="*80)
    print(f"✓ Strategies created: 2")
    print(f"✓ Signals generated: {len(signals)}")
    print(f"✓ Signals approved: {len(approved_signals)}")
    print(f"✓ Orders executed: {len(order_manager.get_filled_orders())}")
    print(f"✓ Positions opened: {total_positions}")
    print(f"✓ Trailing SLs active: {len(sl_manager.get_all_stop_losses())}")
    print(f"✓ Risk checks passed: {len(approved_signals)}/{len(signals)}")
    print("="*80)
    
    print("\n🎉 Day 2 Integration Test PASSED!\n")
    
    return True


if __name__ == "__main__":
    try:
        test_complete_signal_flow()
    except Exception as e:
        print(f"\n✗ Integration test FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
