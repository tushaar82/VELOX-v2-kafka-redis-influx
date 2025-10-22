#!/usr/bin/env python3
"""
Working dashboard with proper threading.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from flask import Flask, render_template_string, render_template, jsonify
import threading
import time
import logging
import pandas as pd
from threading import Lock
from datetime import datetime

# Thread-safe state with lock
state_lock = Lock()
state = {
    'system_status': 'Initializing',
    'is_running': False,
    'current_time': '--:--:--',
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
    with state_lock:
        state['last_update'] = datetime.now().isoformat()
        return jsonify(state.copy())

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
        state['recent_logs'] = state['recent_logs'][:50]

def run_simulation():
    """Run the simulation."""
    print("Simulation thread starting...")
    time.sleep(3)  # Wait for Flask to start
    
    add_log("Initializing system...", "INFO")
    update_state('system_status', 'Initializing')
    
    try:
        from src.utils.logging_config import initialize_logging
        from src.utils.strategy_loader import load_strategies_config, get_enabled_strategies, create_strategy_instance, get_all_strategy_symbols
        from src.adapters.broker.simulated import SimulatedBrokerAdapter
        from src.adapters.strategy.rsi_momentum import RSIMomentumStrategy
        from src.adapters.data.historical import HistoricalDataManager
        from src.core.market_simulator import MarketSimulator
        from src.core.multi_strategy_manager import MultiStrategyManager
        from src.core.time_controller import TimeController
        from src.core.risk_manager import RiskManager
        from src.core.order_manager import OrderManager, PositionManager
        from src.core.trailing_sl import TrailingStopLossManager, TrailingStopLossType
        from src.core.warmup_manager import WarmupManager
        
        initialize_logging(log_level=logging.INFO)  # Changed to INFO to see trailing SL logs
        
        add_log("Loading data...", "INFO")
        data_manager = HistoricalDataManager('./data')
        add_log(f"Data loaded: {len(data_manager.get_statistics()['symbols'])} symbols", "INFO")
        
        broker = SimulatedBrokerAdapter(initial_capital=100000)
        broker.connect()
        add_log("Broker connected", "INFO")
        
        # Risk manager
        risk_manager = RiskManager({
            'max_position_size': 11000,  # Slightly higher to accommodate rounding
            'max_positions_per_strategy': 3,
            'max_total_positions': 5,
            'max_daily_loss': 5000,
            'initial_capital': 100000
        })
        add_log("Risk manager initialized", "INFO")
        
        # Order and position managers
        order_manager = OrderManager(broker)
        position_manager = PositionManager(broker)
        add_log("Order & position managers initialized", "INFO")
        
        # Trailing SL manager
        trailing_sl_manager = TrailingStopLossManager()
        add_log("Trailing SL manager initialized", "INFO")
        
        # Load strategies from YAML config
        add_log("Loading strategies from config/strategies.yaml...", "INFO")
        strategy_configs = get_enabled_strategies('./config/strategies.yaml')
        add_log(f"Found {len(strategy_configs)} enabled strategies", "INFO")
        
        strategy_manager = MultiStrategyManager()
        
        # Get all symbols needed by strategies
        all_symbols = get_all_strategy_symbols('./config/strategies.yaml')
        add_log(f"Symbols required: {', '.join(all_symbols)}", "INFO")
        
        # Create strategy instances from config
        strategy_list = []
        for config in strategy_configs:
            strategy_id = config['id']
            symbols = config.get('symbols', [])
            params = config.get('params', {})
            
            # Create strategy instance
            strategy = create_strategy_instance(config, all_symbols)
            if strategy:
                strategy.initialize()
                strategy_manager.add_strategy(strategy)
                strategy_list.append({
                    'id': strategy_id,
                    'symbols': symbols,
                    'active': True
                })
                add_log(f"✅ Loaded strategy: {strategy_id} ({', '.join(symbols)})", "INFO")
                
                # Log key parameters
                target = params.get('target_pct', 0) * 100
                sl = params.get('initial_sl_pct', 0) * 100
                min_hold = params.get('min_hold_time_minutes', 0)
                add_log(f"   Target: {target:.1f}%, SL: {sl:.1f}%, Min Hold: {min_hold}min", "INFO")
        
        strategy_manager.start()
        update_state('strategies', strategy_list)
        
        time_controller = TimeController()
        
        # Load data for all symbols from strategies
        date = '2020-09-15'
        symbols = all_symbols  # Use symbols from config
        add_log(f"Loading 3-minute candle data for {date}...", "INFO")
        
        # Load 1-minute data and resample to 3-minute
        df_1min = data_manager.get_data(date, symbols)
        if df_1min.empty:
            add_log("No data found!", "ERROR")
            return
        
        # Resample to 3-minute candles
        df_list = []
        for symbol in symbols:
            symbol_data = df_1min[df_1min['symbol'] == symbol].copy()
            if not symbol_data.empty:
                symbol_data.set_index('timestamp', inplace=True)
                
                # Resample to 3-minute OHLC
                resampled = symbol_data.resample('3T').agg({
                    'open': 'first',
                    'high': 'max',
                    'low': 'min',
                    'close': 'last',
                    'volume': 'sum'
                })

                # Ensure we run until 15:15 by creating a full 3-minute index and filling gaps
                market_open = pd.Timestamp(f"{date} 09:15:00")
                market_cutoff = pd.Timestamp(f"{date} 15:15:00")
                full_idx = pd.date_range(start=market_open, end=market_cutoff, freq='3T')

                # Align to full grid
                resampled = resampled.reindex(full_idx)
                # Ensure the index name is preserved for reset_index -> 'timestamp'
                resampled.index.name = 'timestamp'

                # Forward/backward fill close, then use close for O/H/L when missing; volume=0 for gaps
                resampled['close'] = resampled['close'].ffill().bfill()
                for col in ['open', 'high', 'low']:
                    resampled[col] = resampled[col].fillna(resampled['close'])
                resampled['volume'] = resampled['volume'].fillna(0)
                
                resampled['symbol'] = symbol
                resampled.reset_index(inplace=True)
                df_list.append(resampled)
        
        df = pd.concat(df_list, ignore_index=True)
        # IMPORTANT: Sort by timestamp so all symbols process together
        df = df.sort_values('timestamp').reset_index(drop=True)
        add_log(f"Resampled to {len(df)} 3-minute candles across {len(symbols)} symbols", "INFO")
        add_log(f"Time range (extended): {df['timestamp'].min()} to {df['timestamp'].max()} (target end 15:15)", "INFO")
        
        # Warmup strategies with historical candles
        add_log("Warming up strategies with historical data...", "INFO")
        warmup_manager = WarmupManager(min_candles=200, auto_calculate=True)
        
        # Calculate required warmup candles from strategies
        strategies_list = [s for s in strategy_manager.get_strategies().values()]
        required_candles = warmup_manager.calculate_required_warmup(strategies_list)
        add_log(f"Warmup requires {required_candles} candles per symbol", "INFO")
        
        # Load historical candles for warmup (use first N candles from the loaded data)
        warmup_candles = {}
        for symbol in all_symbols:
            symbol_data = df[df['symbol'] == symbol].head(required_candles)
            if not symbol_data.empty:
                candles = []
                for _, row in symbol_data.iterrows():
                    candles.append({
                        'symbol': symbol,
                        'timestamp': row['timestamp'],
                        'open': row['open'],
                        'high': row['high'],
                        'low': row['low'],
                        'close': row['close'],
                        'volume': row['volume']
                    })
                warmup_candles[symbol] = candles
                add_log(f"  Prepared {len(candles)} warmup candles for {symbol}", "INFO")
        
        # Warmup strategies
        warmup_success = warmup_manager.warmup_strategies(strategies_list, warmup_candles)
        if warmup_success:
            add_log(f"✅ Strategies warmed up successfully!", "INFO")
            # Verify warmup status
            for strategy in strategies_list:
                if hasattr(strategy, 'is_warmed_up'):
                    add_log(f"  {strategy.strategy_id}: warmed_up={strategy.is_warmed_up}", "INFO")
        else:
            add_log("⚠️ Warmup had issues, but continuing...", "WARNING")
        
        # Set initial prices for all symbols
        for symbol in symbols:
            symbol_data = df[df['symbol'] == symbol]
            if not symbol_data.empty:
                broker.update_market_price(symbol, symbol_data.iloc[0]['open'])
        
        add_log(f"Loaded {len(df)} candles for {len(symbols)} symbols", "INFO")
        
        # Create simulator for all symbols with realistic settings
        # Speed: 100x for faster simulation
        # Ticks: 10 per 3-minute candle (every 18 seconds) for more granular price action
        # Note: We'll manually set the resampled data
        simulator = MarketSimulator(data_manager, date, symbols, speed=100.0, ticks_per_candle=10)
        # Override with our 3-minute resampled data
        simulator.data_buffer = df
        simulator.logger.info(f"Using 3-minute candles: {len(df)} candles loaded")
        
        update_state('system_status', 'Running')
        update_state('is_running', True)
        add_log("✅ Simulation started!", "INFO")
        print("Simulation running...")
        
        stats = {'ticks': 0, 'last_update': 0, 'signals': 0, 'orders': 0}
        
        def process_tick(tick):
            stats['ticks'] += 1
            broker.update_market_price(tick['symbol'], tick['price'])
            
            actions = time_controller.check_time(tick['timestamp'])
            if actions['warning_issued']:
                add_log("⚠️ 15 minutes to square-off", "WARNING")
            if actions['square_off_executed']:
                add_log("🔔 Square-off time reached", "WARNING")
            
            strategy_manager.process_tick(tick)
            
            # Check for signals and execute trades
            signals = strategy_manager.get_all_signals()
            if signals:
                for signal in signals:
                    stats['signals'] += 1
                    add_log(f"📊 Signal: {signal['action']} {signal['symbol']} @ {signal['price']:.2f} (Strategy: {signal['strategy_id']})", "INFO")
                    
                    # Get current positions (returns dict of {strategy_id: {symbol: position}})
                    strategy_positions = position_manager.get_positions()
                    # Flatten to list for risk manager
                    all_positions = []
                    for strat_id, positions_dict in strategy_positions.items():
                        for symbol, pos in positions_dict.items():
                            all_positions.append(pos)
                    
                    # Validate signal through risk manager
                    result = risk_manager.validate_signal(signal, strategy_positions, all_positions)
                    
                    if result.approved:
                        # Execute order
                        order = order_manager.execute_signal(signal)
                        if order and order['status'] == 'FILLED':
                            stats['orders'] += 1
                            add_log(f"✅ Order filled: {signal['action']} {signal['symbol']} @ {order['filled_price']:.2f}", "INFO")
                            
                            if signal['action'] == 'BUY':
                                # Get strategy-specific trailing SL config from YAML
                                strategy = strategy_manager.get_strategy(signal['strategy_id'])
                                
                                # Find the strategy config to get trailing SL settings
                                atr_multiplier = 2.5  # default
                                for strat_config in strategy_configs:
                                    if strat_config['id'] == signal['strategy_id']:
                                        trailing_config = strat_config.get('trailing_sl', {})
                                        atr_multiplier = trailing_config.get('atr_multiplier', 2.5)
                                        break
                                
                                # Estimate initial ATR as a reasonable value
                                # For Indian stocks around 900-1000, ATR is typically 10-20 points
                                # Use 1.5% of price as ATR estimate
                                initial_atr = order['filled_price'] * 0.015
                                
                                # Setup trailing SL for new position
                                trailing_sl_manager.add_stop_loss(
                                    strategy_id=signal['strategy_id'],
                                    symbol=signal['symbol'],
                                    sl_type=TrailingStopLossType.ATR,
                                    entry_price=order['filled_price'],
                                    config={'atr_value': initial_atr, 'atr_multiplier': atr_multiplier, 'atr_period': 14},
                                    entry_timestamp=signal.get('timestamp')
                                )
                                
                                sl_info = trailing_sl_manager.get_stop_loss_info(signal['strategy_id'], signal['symbol'])
                                if sl_info:
                                    add_log(f"🛡️ Trailing SL activated for {signal['symbol']}: Initial SL @ ${sl_info['current_sl']:.2f} ({atr_multiplier}x ATR)", "INFO")
                                else:
                                    add_log(f"🛡️ Trailing SL activated for {signal['symbol']}", "INFO")
                                
                                # Update strategy position tracking
                                strategy = strategy_manager.get_strategy(signal['strategy_id'])
                                if strategy:
                                    strategy.add_position(
                                        symbol=signal['symbol'],
                                        entry_price=order['filled_price'],
                                        quantity=signal['quantity'],
                                        timestamp=signal.get('timestamp')
                                    )
                            
                            elif signal['action'] == 'SELL':
                                # Remove trailing SL
                                trailing_sl_manager.remove_stop_loss(signal['strategy_id'], signal['symbol'])
                                add_log(f"🔓 Position closed for {signal['symbol']}", "INFO")
                                
                                # Update strategy position tracking
                                strategy = strategy_manager.get_strategy(signal['strategy_id'])
                                if strategy:
                                    strategy.remove_position(signal['symbol'])
                    else:
                        add_log(f"❌ Signal rejected: {result.reason}", "WARNING")
                
                strategy_manager.clear_all_signals()
            
            # Update and check trailing stop losses
            strategy_positions = position_manager.get_positions()
            for strat_id, positions_dict in strategy_positions.items():
                for symbol, pos in positions_dict.items():
                    # Update trailing SL
                    current_price = tick['price'] if tick['symbol'] == symbol else broker.get_market_price(symbol)
                    
                    # Track highest price for trailing (use dict keys, not hasattr)
                    if '_highest_price' not in pos:
                        pos['_highest_price'] = current_price
                    else:
                        pos['_highest_price'] = max(pos.get('_highest_price', current_price), current_price)
                    
                    # Calculate dynamic ATR estimate based on price range
                    # ATR should be reasonable - typically 1-2% of price for intraday
                    price_range = pos['_highest_price'] - pos['entry_price']
                    # Use 1.5% of current price as baseline ATR
                    baseline_atr = pos['entry_price'] * 0.015
                    # If position has moved, use 30% of the range as ATR estimate
                    dynamic_atr = max(abs(price_range) * 0.3, baseline_atr) if abs(price_range) > baseline_atr else baseline_atr
                    atr_value = dynamic_atr
                    
                    trailing_sl_manager.update_stop_loss(
                        strategy_id=strat_id,
                        symbol=symbol,
                        current_price=current_price,
                        highest_price=pos['_highest_price'],
                        atr_value=atr_value
                    )
                    
                    # Get updated SL info and log changes
                    sl_info = trailing_sl_manager.get_stop_loss_info(strat_id, symbol)
                    if sl_info:
                        # Log every time SL moves up (not just when different from last)
                        last_sl = pos.get('_last_sl', 0)
                        current_sl = sl_info['current_sl']
                        
                        if current_sl > last_sl:
                            pos['_last_sl'] = current_sl
                            distance_pct = ((pos['_highest_price'] - current_sl) / pos['_highest_price']) * 100
                            add_log(f"📈 Trailing SL updated for {symbol}: ${current_sl:.2f} (distance: {distance_pct:.2f}%)", "INFO")
                        elif '_last_sl' not in pos:
                            pos['_last_sl'] = current_sl
                    
                    # CHECK IF TRAILING SL IS HIT
                    if sl_info and trailing_sl_manager.check_stop_loss(strat_id, symbol, current_price):
                        # Generate exit signal for trailing SL hit
                        exit_signal = {
                            'strategy_id': strat_id,
                            'action': 'SELL',
                            'symbol': symbol,
                            'price': current_price,
                            'quantity': pos['quantity'],
                            'timestamp': tick.get('timestamp'),
                            'reason': f"Trailing SL hit: {current_price:.2f} <= {sl_info['current_sl']:.2f}"
                        }
                        
                        add_log(f"🛑 Trailing SL triggered for {symbol} @ ${current_price:.2f} (SL: ${sl_info['current_sl']:.2f})", "WARNING")
                        
                        # Execute the exit
                        order = order_manager.execute_signal(exit_signal)
                        if order and order['status'] == 'FILLED':
                            stats['orders'] += 1
                            pnl = (current_price - pos['entry_price']) * pos['quantity']
                            pnl_pct = ((current_price - pos['entry_price']) / pos['entry_price']) * 100
                            add_log(f"✅ SELL {symbol} @ ${current_price:.2f} | P&L: ${pnl:.2f} ({pnl_pct:+.2f}%)", "INFO")
                            
                            # Remove trailing SL
                            trailing_sl_manager.remove_stop_loss(strat_id, symbol)
                            
                            # Update strategy position tracking
                            strategy = strategy_manager.get_strategy(strat_id)
                            if strategy:
                                strategy.remove_position(symbol)
            
            # Update dashboard every 50 ticks for more frequent updates
            if stats['ticks'] - stats['last_update'] >= 50:
                stats['last_update'] = stats['ticks']
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
                
                # Update positions with trailing SL info
                strategy_positions = position_manager.get_positions()
                positions_with_sl = []
                for strat_id, positions_dict in strategy_positions.items():
                    for symbol, pos in positions_dict.items():
                        sl_info = trailing_sl_manager.get_stop_loss_info(strat_id, symbol)
                        sl_value = sl_info['current_sl'] if sl_info else 'N/A'
                        positions_with_sl.append({
                            'symbol': symbol,
                            'quantity': pos['quantity'],
                            'entry_price': pos['entry_price'],
                            'current_price': broker.get_market_price(symbol),
                            'pnl': pos['pnl'],
                            'trailing_sl': sl_value
                        })
                update_state('positions', positions_with_sl)
                
                if stats['ticks'] % 500 == 0:
                    add_log(f"📊 Processed {stats['ticks']} ticks @ {tick['timestamp'].strftime('%H:%M:%S')}", "INFO")
                    print(f"Progress: {stats['ticks']} ticks")
        
        simulator.run_simulation(callback_fn=process_tick)
        
        add_log("✅ Simulation completed!", "INFO")
        print("Simulation complete!")
        
    except Exception as e:
        add_log(f"❌ Error: {e}", "ERROR")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        update_state('is_running', False)
        update_state('system_status', 'Stopped')
        
        try:
            account = broker.get_account_info()
            update_state('account', {
                'capital': account['capital'],
                'pnl': account['pnl'],
                'pnl_pct': account['pnl_pct'],
                'total_value': account['total_value']
            })
            add_log(f"Final: {stats['ticks']} ticks processed", "INFO")
        except:
            pass

if __name__ == '__main__':
    print("\n" + "="*80)
    print("🚀 VELOX DASHBOARD (Working Version)")
    print("="*80)
    print("📊 Dashboard: http://localhost:5000")
    print("📅 Date: 2020-09-15")
    print("⚡ Speed: 100x (realistic simulation)")
    print("📈 Strategies: 2 (rsi_aggressive with 5min hold, rsi_moderate with 10min hold)")
    print("📊 Symbols: ABB, BATAINDIA, ANGELONE")
    print("="*80)
    print("\nStarting dashboard server...")
    print("Open http://localhost:5000 in your browser\n")
    
    # Start simulation thread
    sim_thread = threading.Thread(target=run_simulation, daemon=True)
    sim_thread.start()
    
    # Run dashboard
    try:
        app.run(host='0.0.0.0', port=5000, debug=False, threaded=True, use_reloader=False)
    except KeyboardInterrupt:
        print("\n\nShutting down...")
