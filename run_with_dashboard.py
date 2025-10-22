#!/usr/bin/env python3
"""
Run VELOX system with live dashboard.
"""

import sys
from pathlib import Path
import threading
import time

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from datetime import datetime
import logging

# Import components
from src.utils.logging_config import initialize_logging, get_logger
from src.utils.config_loader import ConfigLoader
from src.adapters.broker.simulated import SimulatedBrokerAdapter
from src.adapters.strategy.rsi_momentum import RSIMomentumStrategy
from src.adapters.data.historical import HistoricalDataManager
from src.core.market_simulator import MarketSimulator
from src.core.multi_strategy_manager import MultiStrategyManager
from src.core.risk_manager import RiskManager
from src.core.order_manager import OrderManager, PositionManager
from src.core.time_controller import TimeController

# Import dashboard
from src.dashboard.app import app, update_state, add_log


def run_simulation_with_dashboard(date='2020-09-15', speed=100.0):
    """Run simulation and update dashboard."""
    
    # Initialize logging
    initialize_logging(log_level=logging.INFO)
    logger = get_logger('dashboard_runner')
    
    logger.info("Initializing VELOX system with dashboard...")
    add_log("System initializing...", "INFO")
    
    # Load config
    config_loader = ConfigLoader()
    system_config = config_loader.load_system_config()
    
    # Initialize components
    data_manager = HistoricalDataManager('./data')
    add_log(f"Data manager loaded: {len(data_manager.get_statistics()['symbols'])} symbols", "INFO")
    
    broker = SimulatedBrokerAdapter(initial_capital=100000)
    broker.connect()
    add_log("Broker connected", "INFO")
    
    risk_manager = RiskManager({
        'max_position_size': 10000,
        'max_positions_per_strategy': 3,
        'max_total_positions': 5,
        'max_daily_loss': 5000,
        'initial_capital': 100000
    })
    add_log("Risk manager initialized", "INFO")
    
    order_manager = OrderManager(broker)
    position_manager = PositionManager(broker)
    
    strategy_manager = MultiStrategyManager()
    
    # Create strategy
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
    
    # Update dashboard with strategy info
    update_state('strategies', [{
        'id': 'test_strategy',
        'symbols': ['ABB'],
        'active': True
    }])
    add_log("Strategy loaded: test_strategy (ABB)", "INFO")
    
    time_controller = TimeController()
    
    # Update dashboard status
    update_state('system_status', 'Running')
    update_state('is_running', True)
    
    # Load data
    symbols = ['ABB']
    try:
        df = data_manager.get_data(date, symbols)
        if not df.empty:
            initial_price = df.iloc[0]['open']
            broker.update_market_price('ABB', initial_price)
            add_log(f"Loaded data for {date}, initial price: {initial_price:.2f}", "INFO")
    except Exception as e:
        logger.error(f"Failed to load data: {e}")
        add_log(f"Error loading data: {e}", "ERROR")
        return
    
    # Create simulator
    simulator = MarketSimulator(
        data_adapter=data_manager,
        date=date,
        symbols=symbols,
        speed=speed,
        ticks_per_candle=10
    )
    simulator.load_data()
    
    add_log(f"Starting simulation at {speed}x speed", "INFO")
    
    # Statistics
    stats = {
        'ticks': 0,
        'signals': 0,
        'orders': 0,
        'last_log_tick': 0
    }
    
    # Process ticks
    def process_tick(tick):
        stats['ticks'] += 1
        
        # Update broker price
        broker.update_market_price(tick['symbol'], tick['price'])
        
        # Check time
        actions = time_controller.check_time(tick['timestamp'])
        if actions['warning_issued']:
            add_log("⚠️ 15 minutes to square-off", "WARNING")
        if actions['square_off_executed']:
            add_log("🔔 Square-off time reached", "WARNING")
        
        # Process through strategy
        strategy_manager.process_tick(tick)
        
        # Get signals
        signals = strategy_manager.get_all_signals()
        if signals:
            stats['signals'] += len(signals)
            for signal in signals:
                add_log(f"Signal: {signal['action']} {signal['symbol']} @ {signal['price']:.2f}", "INFO")
                
                # Validate
                result = risk_manager.validate_signal(signal, {}, {})
                if result.approved:
                    # Execute
                    order = order_manager.execute_signal(signal)
                    if order and order['status'] == 'FILLED':
                        stats['orders'] += 1
                        add_log(f"Order filled: {signal['action']} {signal['symbol']}", "INFO")
            
            strategy_manager.clear_all_signals()
        
        # Update dashboard every 100 ticks
        if stats['ticks'] % 100 == 0 or stats['ticks'] - stats['last_log_tick'] >= 100:
            stats['last_log_tick'] = stats['ticks']
            
            account = broker.get_account_info()
            
            update_state('ticks_processed', stats['ticks'])
            update_state('signals_today', stats['signals'])
            update_state('orders_today', stats['orders'])
            update_state('current_time', tick['timestamp'].strftime('%H:%M:%S'))
            update_state('account', {
                'capital': account['capital'],
                'pnl': account['pnl'],
                'pnl_pct': account['pnl_pct'],
                'total_value': account['total_value']
            })
            
            if stats['ticks'] % 500 == 0:
                add_log(f"Processed {stats['ticks']} ticks, time: {tick['timestamp'].strftime('%H:%M:%S')}", "INFO")
    
    # Run simulation
    try:
        simulator.run_simulation(callback_fn=process_tick)
        add_log("Simulation completed", "INFO")
    except KeyboardInterrupt:
        add_log("Simulation interrupted", "WARNING")
    except Exception as e:
        logger.error(f"Simulation error: {e}", exc_info=True)
        add_log(f"Error: {e}", "ERROR")
    finally:
        update_state('is_running', False)
        update_state('system_status', 'Stopped')
        
        # Final update
        account = broker.get_account_info()
        update_state('account', {
            'capital': account['capital'],
            'pnl': account['pnl'],
            'pnl_pct': account['pnl_pct'],
            'total_value': account['total_value']
        })
        
        add_log(f"Final stats: {stats['ticks']} ticks, {stats['signals']} signals, {stats['orders']} orders", "INFO")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='VELOX with Dashboard')
    parser.add_argument('--date', type=str, default='2020-09-15', help='Date to simulate')
    parser.add_argument('--speed', type=float, default=100.0, help='Simulation speed')
    parser.add_argument('--port', type=int, default=5000, help='Dashboard port')
    
    args = parser.parse_args()
    
    print("\n" + "="*80)
    print("🚀 VELOX TRADING SYSTEM WITH DASHBOARD")
    print("="*80)
    print(f"📊 Dashboard: http://localhost:{args.port}")
    print(f"📅 Date: {args.date}")
    print(f"⚡ Speed: {args.speed}x")
    print("="*80 + "\n")
    print("Starting dashboard server...")
    print("Open http://localhost:5000 in your browser")
    print("Press Ctrl+C to stop\n")
    
    # Start simulation in a separate thread after a delay
    def delayed_start():
        time.sleep(2)  # Wait for dashboard to be ready
        run_simulation_with_dashboard(args.date, args.speed)
    
    sim_thread = threading.Thread(
        target=delayed_start,
        daemon=True
    )
    sim_thread.start()
    
    # Run dashboard (blocking)
    try:
        app.run(host='0.0.0.0', port=args.port, debug=False, use_reloader=False, threaded=True)
    except KeyboardInterrupt:
        print("\n\nShutting down...")


if __name__ == "__main__":
    main()
