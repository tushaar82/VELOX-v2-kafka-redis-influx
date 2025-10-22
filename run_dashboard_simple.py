#!/usr/bin/env python3
"""
Simple dashboard runner - starts simulation immediately.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from flask import Flask, render_template, jsonify
from datetime import datetime
import threading
import time
import logging

# Dashboard state
state = {
    'system_status': 'Starting',
    'is_running': False,
    'current_time': None,
    'strategies': [],
    'positions': [],
    'signals_today': 0,
    'orders_today': 0,
    'ticks_processed': 0,
    'account': {'capital': 100000, 'pnl': 0, 'pnl_pct': 0, 'total_value': 100000},
    'recent_logs': [],
    'last_update': None
}

app = Flask(__name__, template_folder='src/dashboard/templates')

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/api/status')
def get_status():
    state['last_update'] = datetime.now().isoformat()
    return jsonify(state)

def add_log(msg, level='INFO'):
    state['recent_logs'].insert(0, {
        'timestamp': datetime.now().strftime('%H:%M:%S'),
        'level': level,
        'message': msg
    })
    state['recent_logs'] = state['recent_logs'][:50]

def run_simulation():
    """Run the simulation."""
    time.sleep(3)  # Wait for dashboard to start
    
    add_log("Starting simulation...", "INFO")
    
    from src.utils.logging_config import initialize_logging, get_logger
    from src.adapters.broker.simulated import SimulatedBrokerAdapter
    from src.adapters.strategy.rsi_momentum import RSIMomentumStrategy
    from src.adapters.data.historical import HistoricalDataManager
    from src.core.market_simulator import MarketSimulator
    from src.core.multi_strategy_manager import MultiStrategyManager
    from src.core.time_controller import TimeController
    
    initialize_logging(log_level=logging.WARNING)  # Less verbose
    
    add_log("Loading data...", "INFO")
    data_manager = HistoricalDataManager('./data')
    add_log(f"Data loaded: {len(data_manager.get_statistics()['symbols'])} symbols", "INFO")
    
    broker = SimulatedBrokerAdapter(initial_capital=100000)
    broker.connect()
    add_log("Broker connected", "INFO")
    
    strategy_manager = MultiStrategyManager()
    strategy = RSIMomentumStrategy('test_strategy', ['ABB'], {
        'rsi_period': 14, 'rsi_oversold': 30, 'rsi_overbought': 70,
        'ma_period': 20, 'target_pct': 0.02, 'initial_sl_pct': 0.01, 'min_volume': 100
    })
    strategy.initialize()
    strategy_manager.add_strategy(strategy)
    strategy_manager.start()
    
    state['strategies'] = [{'id': 'test_strategy', 'symbols': ['ABB'], 'active': True}]
    add_log("Strategy loaded: test_strategy (ABB)", "INFO")
    
    time_controller = TimeController()
    
    # Load data
    date = '2020-09-15'
    df = data_manager.get_data(date, ['ABB'])
    if not df.empty:
        broker.update_market_price('ABB', df.iloc[0]['open'])
        add_log(f"Loaded {len(df)} candles for {date}", "INFO")
    
    # Create simulator
    simulator = MarketSimulator(data_manager, date, ['ABB'], speed=100.0, ticks_per_candle=10)
    simulator.load_data()
    
    state['system_status'] = 'Running'
    state['is_running'] = True
    add_log("Simulation started!", "INFO")
    
    stats = {'ticks': 0, 'last_update': 0}
    
    def process_tick(tick):
        stats['ticks'] += 1
        broker.update_market_price(tick['symbol'], tick['price'])
        
        actions = time_controller.check_time(tick['timestamp'])
        if actions['warning_issued']:
            add_log("⚠️ 15 minutes to square-off", "WARNING")
        if actions['square_off_executed']:
            add_log("🔔 Square-off time reached", "WARNING")
        
        strategy_manager.process_tick(tick)
        
        # Update dashboard every 100 ticks
        if stats['ticks'] - stats['last_update'] >= 100:
            stats['last_update'] = stats['ticks']
            account = broker.get_account_info()
            
            state['ticks_processed'] = stats['ticks']
            state['current_time'] = tick['timestamp'].strftime('%H:%M:%S')
            state['account'] = {
                'capital': account['capital'],
                'pnl': account['pnl'],
                'pnl_pct': account['pnl_pct'],
                'total_value': account['total_value']
            }
            
            if stats['ticks'] % 500 == 0:
                add_log(f"Processed {stats['ticks']} ticks @ {tick['timestamp'].strftime('%H:%M:%S')}", "INFO")
    
    try:
        simulator.run_simulation(callback_fn=process_tick)
        add_log("Simulation completed!", "INFO")
    except Exception as e:
        add_log(f"Error: {e}", "ERROR")
    finally:
        state['is_running'] = False
        state['system_status'] = 'Stopped'
        account = broker.get_account_info()
        state['account'] = {
            'capital': account['capital'],
            'pnl': account['pnl'],
            'pnl_pct': account['pnl_pct'],
            'total_value': account['total_value']
        }
        add_log(f"Final: {stats['ticks']} ticks processed", "INFO")

if __name__ == '__main__':
    print("\n" + "="*80)
    print("🚀 VELOX DASHBOARD")
    print("="*80)
    print("📊 Open: http://localhost:5000")
    print("="*80 + "\n")
    
    # Start simulation thread
    sim_thread = threading.Thread(target=run_simulation, daemon=True)
    sim_thread.start()
    
    # Run dashboard
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True, use_reloader=False)
