#!/usr/bin/env python3
"""
VELOX Trading Dashboard - Production Ready
Complete trading system with proper P&L and position tracking.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from flask import Flask, render_template, jsonify
from datetime import datetime
import threading
import time
import logging
from threading import Lock

# Thread-safe state
state_lock = Lock()
state = {
    'system_status': 'Initializing',
    'is_running': False,
    'current_time': '--:--:--',
    'strategies': [],
    'positions': [],
    'closed_trades': [],
    'signals_today': 0,
    'orders_today': 0,
    'trades_closed': 0,
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
    with state_lock:
        state['last_update'] = datetime.now().isoformat()
        return jsonify(state.copy())

@app.route('/api/available_dates')
def get_available_dates():
    """Get list of available dates for simulation."""
    try:
        from src.adapters.data.historical import HistoricalDataManager
        data_manager = HistoricalDataManager('./data')
        stats = data_manager.get_statistics()
        
        # Get date ranges for all symbols
        dates = []
        for symbol, info in stats['symbols'].items():
            if 'date_range' in info:
                dates.append({
                    'symbol': symbol,
                    'start': info['date_range']['start'],
                    'end': info['date_range']['end']
                })
        
        return jsonify({'dates': dates})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/start_simulation', methods=['POST'])
def start_simulation():
    """Start a new simulation with selected date."""
    try:
        from flask import request
        data = request.get_json()
        date = data.get('date', '2020-09-15')
        
        # Start simulation in background
        import threading
        sim_thread = threading.Thread(
            target=run_simulation_date,
            args=(date,),
            daemon=True
        )
        sim_thread.start()
        
        return jsonify({'status': 'started', 'date': date})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def update_state(key, value):
    with state_lock:
        state[key] = value

def add_log(msg, level='INFO'):
    with state_lock:
        state['recent_logs'].insert(0, {
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'level': level,
            'message': msg
        })
        state['recent_logs'] = state['recent_logs'][:100]

def run_simulation_date(date='2020-09-15'):
    """Run simulation for a specific date."""
    run_simulation(date)

def run_simulation(date='2020-09-15'):
    """Run the complete trading simulation."""
    print("Simulation thread starting...")
    time.sleep(3)
    
    add_log("Initializing VELOX trading system...", "INFO")
    update_state('system_status', 'Initializing')
    
    try:
        from src.utils.logging_config import initialize_logging
        from src.utils.strategy_loader import get_enabled_strategies, get_all_strategy_symbols, create_strategy_instance
        from src.adapters.broker.simulated import SimulatedBrokerAdapter
        from src.adapters.data.historical import HistoricalDataManager
        from src.core.market_simulator import MarketSimulator
        from src.core.multi_strategy_manager import MultiStrategyManager
        from src.core.time_controller import TimeController
        from src.core.risk_manager import RiskManager
        from src.core.order_manager import OrderManager, PositionManager
        from src.core.trailing_sl import TrailingStopLossManager, TrailingStopLossType
        
        initialize_logging(log_level=logging.WARNING)
        
        # Initialize components
        add_log("Loading historical data...", "INFO")
        data_manager = HistoricalDataManager('./data')
        add_log(f"✓ Data loaded: {len(data_manager.get_statistics()['symbols'])} symbols", "INFO")
        
        broker = SimulatedBrokerAdapter(initial_capital=100000)
        broker.connect()
        add_log("✓ Broker connected: $100,000 capital", "INFO")
        
        risk_manager = RiskManager({
            'max_position_size': 10000,
            'max_positions_per_strategy': 3,
            'max_total_positions': 5,
            'max_daily_loss': 5000,
            'initial_capital': 100000
        })
        add_log("✓ Risk manager initialized", "INFO")
        
        order_manager = OrderManager(broker)
        position_manager = PositionManager(broker)
        trailing_sl_manager = TrailingStopLossManager()
        add_log("✓ Order, position & trailing SL managers ready", "INFO")
        
        # Load strategy configurations from YAML
        add_log("Loading strategy configurations...", "INFO")
        strategy_configs = get_enabled_strategies('./config/strategies.yaml')
        all_symbols = get_all_strategy_symbols('./config/strategies.yaml')
        
        add_log(f"Found {len(strategy_configs)} enabled strategies", "INFO")
        add_log(f"Required symbols: {', '.join(all_symbols)}", "INFO")
        
        # Load data for all required symbols
        add_log(f"Loading market data for {date}...", "INFO")
        print(f"Loading data for {date}...")
        df = data_manager.get_data(date, all_symbols)
        
        if df.empty:
            add_log("❌ No data found!", "ERROR")
            return
        
        # Filter symbols to only those with data
        available_symbols = df['symbol'].unique().tolist()
        if len(available_symbols) < len(all_symbols):
            missing = set(all_symbols) - set(available_symbols)
            add_log(f"⚠️  Symbols with no data: {missing}", "WARNING")
        
        symbols = available_symbols
        add_log(f"✓ Using symbols with data: {symbols}", "INFO")
        
        # Create strategies from YAML configuration
        strategy_manager = MultiStrategyManager()
        strategies_info = []
        
        for idx, strategy_config in enumerate(strategy_configs, 1):
            strategy_id = strategy_config['id']
            strategy_class = strategy_config['class']
            
            # Create strategy instance
            strategy = create_strategy_instance(strategy_config, available_symbols)
            
            if strategy:
                strategy.initialize()
                strategy_manager.add_strategy(strategy)
                
                # Get actual symbols used
                actual_symbols = [s for s in strategy_config.get('symbols', []) if s in available_symbols]
                strategies_info.append({
                    'id': strategy_id,
                    'symbols': actual_symbols,
                    'active': True
                })
                
                add_log(f"✓ Strategy {idx}: {strategy_id} ({', '.join(actual_symbols)}) - {strategy_class}", "INFO")
            else:
                add_log(f"⚠️  Strategy {idx}: {strategy_id} - No symbols available", "WARNING")
        
        if not strategies_info:
            add_log("❌ No strategies could be initialized!", "ERROR")
            return
        
        strategy_manager.start()
        update_state('strategies', strategies_info)
        
        time_controller = TimeController()
        
        # Set initial prices
        for symbol in symbols:
            symbol_data = df[df['symbol'] == symbol]
            if not symbol_data.empty:
                broker.update_market_price(symbol, symbol_data.iloc[0]['open'])
        
        add_log(f"✓ Loaded {len(df)} candles for {len(symbols)} symbols", "INFO")
        
        # Create simulator
        simulator = MarketSimulator(data_manager, date, symbols, speed=50.0, ticks_per_candle=10)
        simulator.load_data()
        
        update_state('system_status', 'Running')
        update_state('is_running', True)
        add_log("🚀 Simulation started! Trading live...", "INFO")
        print("✓ Simulation running...")
        
        # Statistics
        stats = {
            'ticks': 0,
            'last_update': 0,
            'signals': 0,
            'orders': 0,
            'trades_closed': 0,
            'position_highest': {}  # Track highest price per position
        }
        
        def process_tick(tick):
            stats['ticks'] += 1
            broker.update_market_price(tick['symbol'], tick['price'])
            
            # Time controller
            actions = time_controller.check_time(tick['timestamp'])
            if actions['warning_issued']:
                add_log("⚠️  WARNING: 15 minutes to market close!", "WARNING")
            if actions['square_off_executed']:
                add_log("🔔 MARKET CLOSED: Squaring off all positions", "WARNING")
            
            # Process tick through strategies
            strategy_manager.process_tick(tick)
            
            # Handle signals
            signals = strategy_manager.get_all_signals()
            if signals:
                for signal in signals:
                    stats['signals'] += 1
                    
                    # Get positions for risk check
                    strategy_positions = position_manager.get_positions()
                    all_positions = []
                    for strat_id, pos_dict in strategy_positions.items():
                        for sym, pos in pos_dict.items():
                            all_positions.append(pos)
                    
                    # Validate signal
                    result = risk_manager.validate_signal(signal, strategy_positions, all_positions)
                    
                    if result.approved:
                        # Execute order
                        order = order_manager.execute_signal(signal)
                        
                        if order and order['status'] == 'FILLED':
                            stats['orders'] += 1
                            
                            if signal['action'] == 'BUY':
                                add_log(f"✅ BUY {signal['symbol']} @ ${order['filled_price']:.2f} x{signal['quantity']}", "INFO")
                                
                                # Update PositionManager first
                                position_manager.update_position(
                                    strategy_id=signal['strategy_id'],
                                    symbol=signal['symbol'],
                                    order=order
                                )
                                
                                # Add trailing SL
                                trailing_sl_manager.add_stop_loss(
                                    strategy_id=signal['strategy_id'],
                                    symbol=signal['symbol'],
                                    sl_type=TrailingStopLossType.ATR,
                                    entry_price=order['filled_price'],
                                    config={'atr_multiplier': 2.0, 'atr_period': 14},
                                    entry_timestamp=signal.get('timestamp')
                                )
                                add_log(f"🛡️  Trailing SL activated for {signal['symbol']}", "INFO")
                                
                                # Update strategy position
                                strategy = strategy_manager.get_strategy(signal['strategy_id'])
                                if strategy:
                                    strategy.add_position(
                                        symbol=signal['symbol'],
                                        entry_price=order['filled_price'],
                                        quantity=signal['quantity'],
                                        timestamp=signal.get('timestamp')
                                    )
                                
                                # Track highest price
                                key = f"{signal['strategy_id']}_{signal['symbol']}"
                                stats['position_highest'][key] = order['filled_price']
                                
                                print(f"✓ Position opened: {signal['symbol']}")
                            
                            elif signal['action'] == 'SELL':
                                # Calculate P&L for this trade
                                strategy_pos = position_manager.get_positions().get(signal['strategy_id'], {})
                                pos = strategy_pos.get(signal['symbol'])
                                if pos:
                                    entry_price = pos.get('average_price', pos.get('entry_price', 0))
                                    pnl = (order['filled_price'] - entry_price) * signal['quantity']
                                    pnl_pct = ((order['filled_price'] - entry_price) / entry_price) * 100 if entry_price > 0 else 0
                                    
                                    add_log(f"✅ SELL {signal['symbol']} @ ${order['filled_price']:.2f} | P&L: ${pnl:+.2f} ({pnl_pct:+.2f}%)", "INFO")
                                    
                                    # Track closed trade with details
                                    closed_trade = {
                                        'timestamp': tick['timestamp'].strftime('%H:%M:%S'),
                                        'strategy': signal['strategy_id'],
                                        'symbol': signal['symbol'],
                                        'quantity': signal['quantity'],
                                        'entry_price': entry_price,
                                        'exit_price': order['filled_price'],
                                        'pnl': pnl,
                                        'pnl_pct': pnl_pct,
                                        'reason': signal.get('reason', 'Exit signal')
                                    }
                                    
                                    # Add to closed trades list (keep last 20)
                                    with state_lock:
                                        state['closed_trades'].insert(0, closed_trade)
                                        state['closed_trades'] = state['closed_trades'][:20]
                                    
                                    stats['trades_closed'] += 1
                                else:
                                    add_log(f"✅ SELL {signal['symbol']} @ ${order['filled_price']:.2f}", "INFO")
                                
                                # Update PositionManager
                                position_manager.update_position(
                                    strategy_id=signal['strategy_id'],
                                    symbol=signal['symbol'],
                                    order=order
                                )
                                
                                # Remove trailing SL
                                trailing_sl_manager.remove_stop_loss(signal['strategy_id'], signal['symbol'])
                                
                                # Update strategy position
                                strategy = strategy_manager.get_strategy(signal['strategy_id'])
                                if strategy:
                                    strategy.remove_position(signal['symbol'])
                                
                                # Remove from highest tracking
                                key = f"{signal['strategy_id']}_{signal['symbol']}"
                                if key in stats['position_highest']:
                                    del stats['position_highest'][key]
                                
                                print(f"✓ Position closed: {signal['symbol']}")
                    else:
                        add_log(f"❌ Signal rejected: {result.reason}", "WARNING")
                
                strategy_manager.clear_all_signals()
            
            # Update trailing SLs
            strategy_positions = position_manager.get_positions()
            for strat_id, pos_dict in strategy_positions.items():
                for symbol, pos in pos_dict.items():
                    current_price = tick['price'] if tick['symbol'] == symbol else broker.current_prices.get(symbol, 0)
                    
                    # Track highest price
                    key = f"{strat_id}_{symbol}"
                    if key not in stats['position_highest']:
                        stats['position_highest'][key] = current_price
                    else:
                        stats['position_highest'][key] = max(stats['position_highest'][key], current_price)
                    
                    # Update trailing SL
                    trailing_sl_manager.update_stop_loss(
                        strategy_id=strat_id,
                        symbol=symbol,
                        current_price=current_price,
                        highest_price=stats['position_highest'][key]
                    )
            
            # Update dashboard every 50 ticks
            if stats['ticks'] - stats['last_update'] >= 50:
                stats['last_update'] = stats['ticks']
                
                # Get account info
                account = broker.get_account_info()
                
                # Update state
                update_state('ticks_processed', stats['ticks'])
                update_state('signals_today', stats['signals'])
                update_state('orders_today', stats['orders'])
                update_state('trades_closed', stats['trades_closed'])
                update_state('current_time', tick['timestamp'].strftime('%H:%M:%S'))
                update_state('account', {
                    'capital': account['capital'],
                    'pnl': account['pnl'],
                    'pnl_pct': account['pnl_pct'],
                    'total_value': account['total_value']
                })
                
                # Update positions - get fresh data
                current_positions = position_manager.get_positions()
                positions_list = []
                
                # Debug: print what we got
                if stats['ticks'] % 100 == 0:
                    print(f"DEBUG: position_manager.get_positions() = {current_positions}")
                
                for strat_id, pos_dict in current_positions.items():
                    for symbol, pos in pos_dict.items():
                        try:
                            current_price = broker.current_prices.get(symbol, 0)
                            entry_price = pos.get('average_price', pos.get('entry_price', 0))
                            pnl = (current_price - entry_price) * pos['quantity']
                            pnl_pct = ((current_price - entry_price) / entry_price) * 100 if entry_price > 0 else 0
                            
                            sl_info = trailing_sl_manager.get_stop_loss_info(strat_id, symbol)
                            sl_value = sl_info['current_sl'] if sl_info else 'N/A'
                            
                            position_data = {
                                'strategy': strat_id,
                                'symbol': symbol,
                                'quantity': pos['quantity'],
                                'entry_price': entry_price,
                                'current_price': current_price,
                                'pnl': pnl,
                                'pnl_pct': pnl_pct,
                                'trailing_sl': sl_value
                            }
                            positions_list.append(position_data)
                            
                            if stats['ticks'] % 100 == 0:
                                print(f"  Position: {symbol} @ ${current_price:.2f}, Entry: ${entry_price:.2f}, P&L: ${pnl:+.2f}")
                        except Exception as e:
                            print(f"ERROR building position data for {symbol}: {e}")
                            import traceback
                            traceback.print_exc()
                
                update_state('positions', positions_list)
                
                # Debug log
                if stats['ticks'] % 100 == 0:
                    print(f"→ Sent {len(positions_list)} positions to dashboard")
                
                if stats['ticks'] % 500 == 0:
                    add_log(f"📊 Processed {stats['ticks']} ticks @ {tick['timestamp'].strftime('%H:%M:%S')}", "INFO")
                    print(f"Progress: {stats['ticks']} ticks, {stats['orders']} orders, {stats['trades_closed']} closed")
        
        # Run simulation
        add_log("🔄 Starting continuous trading...", "INFO")
        print("Starting continuous trading simulation...")
        print(f"Expected to process ~{len(df) * 10} ticks from {len(df)} candles")
        
        try:
            simulator.run_simulation(callback_fn=process_tick)
            add_log("✅ Trading day completed!", "INFO")
            print("✓ Trading day complete!")
        except KeyboardInterrupt:
            add_log("⚠️ System stopped by user", "WARNING")
            print("\n⚠️ System stopped by user")
        except Exception as e:
            add_log(f"❌ System error: {e}", "ERROR")
            print(f"❌ System error: {e}")
            import traceback
            traceback.print_exc()
            raise
        
    except Exception as e:
        add_log(f"❌ Error: {e}", "ERROR")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        update_state('is_running', False)
        update_state('system_status', 'Completed')
        
        try:
            account = broker.get_account_info()
            update_state('account', {
                'capital': account['capital'],
                'pnl': account['pnl'],
                'pnl_pct': account['pnl_pct'],
                'total_value': account['total_value']
            })
            add_log(f"📊 Final: {stats['ticks']} ticks, {stats['orders']} orders, {stats['trades_closed']} trades closed", "INFO")
            add_log(f"💰 Final P&L: ${account['pnl']:+.2f} ({account['pnl_pct']:+.2f}%)", "INFO")
            add_log("ℹ️ Trading day completed. Dashboard remains active for review.", "INFO")
            print("\n" + "="*80)
            print("📊 TRADING DAY SUMMARY")
            print("="*80)
            print(f"Ticks Processed: {stats['ticks']}")
            print(f"Orders Executed: {stats['orders']}")
            print(f"Trades Closed: {stats['trades_closed']}")
            print(f"Final P&L: ${account['pnl']:+.2f} ({account['pnl_pct']:+.2f}%)")
            print("="*80)
            print("✓ Dashboard still running at http://localhost:5000")
            print("✓ Press Ctrl+C to stop the dashboard")
            print("="*80 + "\n")
        except:
            pass

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='VELOX Trading Dashboard')
    parser.add_argument('--date', type=str, default='2020-09-15', help='Date to simulate (YYYY-MM-DD)')
    parser.add_argument('--port', type=int, default=5000, help='Dashboard port')
    args = parser.parse_args()
    
    print("\n" + "="*80)
    print("🚀 VELOX TRADING DASHBOARD - PRODUCTION VERSION")
    print("="*80)
    print(f"📊 Dashboard: http://localhost:{args.port}")
    print(f"📅 Simulation Date: {args.date}")
    print("⚡ Speed: 50x")
    print("📈 Strategies: 3 (rsi_aggressive, rsi_moderate, mtf_atr)")
    print("📊 Symbols: ABB, BATAINDIA, ANGELONE, AMBER, ADANIENT, BANKINDIA")
    print("="*80)
    print("\n💡 TIP: Run different dates with --date YYYY-MM-DD")
    print("   Example: python dashboard_final.py --date 2020-09-16")
    print("\n📅 Available date range: 2015-02-02 to 2025-07-25")
    print("="*80)
    print("\nStarting dashboard server...")
    print(f"Open http://localhost:{args.port} in your browser\n")
    
    # Start simulation thread with selected date
    sim_thread = threading.Thread(target=run_simulation, args=(args.date,), daemon=True)
    sim_thread.start()
    
    # Run dashboard
    try:
        app.run(host='0.0.0.0', port=args.port, debug=False, threaded=True, use_reloader=False)
    except KeyboardInterrupt:
        print("\n\nShutting down...")
