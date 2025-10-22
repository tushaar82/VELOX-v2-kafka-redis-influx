#!/usr/bin/env python3
"""
Standalone system test runner.
Tests the complete VELOX system without import issues.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))
sys.path.insert(0, str(Path(__file__).parent))

from datetime import datetime
import logging

# Now import from src
from src.utils.logging_config import initialize_logging, get_logger
from src.utils.config_loader import ConfigLoader
from src.adapters.broker.simulated import SimulatedBrokerAdapter
from src.adapters.strategy.rsi_momentum import RSIMomentumStrategy
from src.adapters.data.historical import HistoricalDataManager
from src.core.market_simulator import MarketSimulator
from src.core.multi_strategy_manager import MultiStrategyManager
from src.core.risk_manager import RiskManager
from src.core.order_manager import OrderManager, PositionManager
from src.core.trailing_sl import TrailingStopLossManager, TrailingStopLossType
from src.core.time_controller import TimeController


def run_quick_test(date='2020-09-15', speed=1000.0):
    """Run a quick system test."""
    
    # Initialize logging
    initialize_logging(log_level=logging.INFO)
    logger = get_logger('system_test')
    
    logger.info("="*80)
    logger.info("VELOX SYSTEM TEST - Quick Run")
    logger.info("="*80)
    
    # Load config
    logger.info("Loading configuration...")
    config_loader = ConfigLoader()
    system_config = config_loader.load_system_config()
    
    # Initialize components
    logger.info("Initializing components...")
    
    # Data manager
    data_manager = HistoricalDataManager('./data')
    logger.info(f"✓ Data manager: {len(data_manager.get_statistics()['symbols'])} symbols")
    
    # Broker
    broker = SimulatedBrokerAdapter(initial_capital=100000)
    broker.connect()
    logger.info("✓ Broker connected")
    
    # Risk manager
    risk_manager = RiskManager({
        'max_position_size': 10000,
        'max_positions_per_strategy': 3,
        'max_total_positions': 5,
        'max_daily_loss': 5000,
        'initial_capital': 100000
    })
    logger.info("✓ Risk manager initialized")
    
    # Order and position managers
    order_manager = OrderManager(broker)
    position_manager = PositionManager(broker)
    logger.info("✓ Order & position managers initialized")
    
    # Strategy manager
    strategy_manager = MultiStrategyManager()
    
    # Create test strategy
    strategy = RSIMomentumStrategy('test_strategy', ['ABB'], {
        'rsi_period': 14,
        'rsi_oversold': 30,
        'rsi_overbought': 70,
        'ma_period': 20,
        'target_pct': 0.02,
        'initial_sl_pct': 0.01,
        'min_volume': 100
    })
    strategy.initialize()
    strategy_manager.add_strategy(strategy)
    strategy_manager.start()
    logger.info("✓ Strategy manager with 1 strategy")
    
    # Time controller
    time_controller = TimeController()
    logger.info("✓ Time controller initialized")
    
    # Load data and run simulation
    logger.info(f"\nRunning simulation for {date} at {speed}x speed...")
    
    symbols = ['ABB']
    
    # Set initial price
    try:
        df = data_manager.get_data(date, symbols)
        if not df.empty:
            initial_price = df.iloc[0]['open']
            broker.update_market_price('ABB', initial_price)
            logger.info(f"Initial price: {initial_price:.2f}")
    except Exception as e:
        logger.error(f"Failed to load data: {e}")
        return False
    
    # Create simulator
    simulator = MarketSimulator(
        data_adapter=data_manager,
        date=date,
        symbols=symbols,
        speed=speed,
        ticks_per_candle=10
    )
    
    # Load data
    simulator.load_data()
    
    # Statistics
    stats = {
        'ticks': 0,
        'signals': 0,
        'orders': 0
    }
    
    # Process ticks
    def process_tick(tick):
        stats['ticks'] += 1
        broker.update_market_price(tick['symbol'], tick['price'])
        
        # Check time
        time_controller.check_time(tick['timestamp'])
        
        # Process through strategy
        strategy_manager.process_tick(tick)
        
        # Get signals
        signals = strategy_manager.get_all_signals()
        if signals:
            stats['signals'] += len(signals)
            for signal in signals:
                # Validate
                result = risk_manager.validate_signal(signal, {}, {})
                if result.approved:
                    # Execute
                    order = order_manager.execute_signal(signal)
                    if order and order['status'] == 'FILLED':
                        stats['orders'] += 1
            
            strategy_manager.clear_all_signals()
    
    # Run
    try:
        simulator.run_simulation(callback_fn=process_tick)
    except KeyboardInterrupt:
        logger.warning("Interrupted")
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return False
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("TEST SUMMARY")
    logger.info("="*80)
    logger.info(f"Ticks processed: {stats['ticks']}")
    logger.info(f"Signals generated: {stats['signals']}")
    logger.info(f"Orders executed: {stats['orders']}")
    
    account = broker.get_account_info()
    logger.info(f"\nAccount:")
    logger.info(f"  Capital: {account['capital']:.2f}")
    logger.info(f"  P&L: {account['pnl']:.2f} ({account['pnl_pct']:.2f}%)")
    logger.info(f"  Positions: {account['num_positions']}")
    logger.info("="*80)
    
    logger.info("\n✅ SYSTEM TEST COMPLETED SUCCESSFULLY!")
    return True


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='VELOX System Test')
    parser.add_argument('--date', type=str, default='2020-09-15', help='Date to test')
    parser.add_argument('--speed', type=float, default=1000.0, help='Speed multiplier')
    
    args = parser.parse_args()
    
    success = run_quick_test(date=args.date, speed=args.speed)
    sys.exit(0 if success else 1)
