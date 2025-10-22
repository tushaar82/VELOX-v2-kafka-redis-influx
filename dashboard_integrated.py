#!/usr/bin/env python3
"""
VELOX Dashboard with Kafka, InfluxDB, and Redis Integration.

Architecture:
- Kafka: Real-time event streaming (ticks, signals, trades)
- InfluxDB: Time-series storage (historical data, analytics)
- Redis: Fast caching (positions, indicators, latest ticks)
- Flask: Web dashboard
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

# Import database managers
from src.database.influx_manager import InfluxManager
from src.database.redis_manager import RedisManager
from src.utils.kafka_helper import KafkaProducerWrapper

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
    'last_update': None,
    'services': {
        'kafka': False,
        'influxdb': False,
        'redis': False
    }
}

app = Flask(__name__, template_folder='src/dashboard/templates')

# Global service instances
influx_manager = None
redis_manager = None
kafka_producer = None

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/api/status')
def get_status():
    with state_lock:
        state['last_update'] = datetime.now().isoformat()
        return jsonify(state.copy())

@app.route('/api/services')
def get_services_status():
    """Get status of external services."""
    services = {
        'kafka': kafka_producer is not None,
        'influxdb': influx_manager is not None and influx_manager.is_connected(),
        'redis': redis_manager is not None and redis_manager.is_connected()
    }
    return jsonify(services)

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

def initialize_services():
    """Initialize Kafka, InfluxDB, and Redis."""
    global influx_manager, redis_manager, kafka_producer
    
    add_log("Initializing external services...", "INFO")
    
    # Initialize InfluxDB
    try:
        influx_manager = InfluxManager(
            url='http://localhost:8086',
            token='velox-super-secret-token',
            org='velox',
            bucket='trading'
        )
        if influx_manager.is_connected():
            add_log("✅ InfluxDB connected", "INFO")
            update_state('services', {**state['services'], 'influxdb': True})
        else:
            add_log("⚠️  InfluxDB not available (optional)", "WARNING")
    except Exception as e:
        add_log(f"⚠️  InfluxDB initialization failed: {e}", "WARNING")
        influx_manager = None
    
    # Initialize Redis
    try:
        redis_manager = RedisManager(host='localhost', port=6379, db=0)
        if redis_manager.is_connected():
            add_log("✅ Redis connected", "INFO")
            update_state('services', {**state['services'], 'redis': True})
        else:
            add_log("⚠️  Redis not available (optional)", "WARNING")
    except Exception as e:
        add_log(f"⚠️  Redis initialization failed: {e}", "WARNING")
        redis_manager = None
    
    # Initialize Kafka
    try:
        kafka_producer = KafkaProducerWrapper(
            bootstrap_servers='localhost:9092',
            topic='velox-events'
        )
        add_log("✅ Kafka connected", "INFO")
        update_state('services', {**state['services'], 'kafka': True})
    except Exception as e:
        add_log(f"⚠️  Kafka not available (optional): {e}", "WARNING")
        kafka_producer = None
    
    # Summary
    connected = sum([
        influx_manager is not None and influx_manager.is_connected(),
        redis_manager is not None and redis_manager.is_connected(),
        kafka_producer is not None
    ])
    add_log(f"📊 Services: {connected}/3 connected", "INFO")

def run_simulation():
    """Run the simulation with integrated services."""
    print("Simulation thread starting...")
    time.sleep(3)  # Wait for Flask to start
    
    add_log("Initializing system...", "INFO")
    update_state('system_status', 'Initializing')
    
    # Initialize external services
    initialize_services()
    
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
        
        initialize_logging(log_level=logging.INFO)
        
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
        trailing_sl_manager = TrailingStopLossManager()
        
        # Load strategies
        add_log("Loading strategies from config/strategies.yaml...", "INFO")
        strategy_configs = load_strategies_config('./config/strategies.yaml')
        enabled_configs = get_enabled_strategies('./config/strategies.yaml')
        add_log(f"Found {len(enabled_configs)} enabled strategies", "INFO")
        
        # Get all symbols needed
        all_symbols = get_all_strategy_symbols('./config/strategies.yaml')
        add_log(f"Symbols required: {', '.join(all_symbols)}", "INFO")
        
        # Create strategy instances
        strategy_manager = MultiStrategyManager()
        strategy_list = []
        
        for config in enabled_configs:
            strategy = create_strategy_instance(config, all_symbols)
            if strategy:
                strategy_manager.add_strategy(strategy)
                strategy_list.append({
                    'id': config['id'],
                    'class': config['class'],
                    'symbols': config.get('symbols', []),
                    'enabled': True
                })
                add_log(f"✅ Loaded strategy: {config['id']} ({', '.join(config.get('symbols', []))})", "INFO")
                
                # Log strategy parameters
                params = config.get('params', {})
                if 'target_pct' in params:
                    target = params.get('target_pct', 0) * 100
                    sl = params.get('initial_sl_pct', 0) * 100
                    min_hold = params.get('min_hold_time_minutes', 0)
                    add_log(f"   Target: {target:.1f}%, SL: {sl:.1f}%, Min Hold: {min_hold}min", "INFO")
        
        strategy_manager.start()
        update_state('strategies', strategy_list)
        
        time_controller = TimeController()
        
        # Load data for all symbols from strategies
        date = '2024-03-15'  # Changed to more recent date with better volatility
        symbols = all_symbols
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
            add_log(f"Processing {symbol}: {len(symbol_data)} 1-min rows", "INFO")
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
                
                add_log(f"  {symbol}: Extended to {len(resampled)} 3-min candles (09:15-15:15)", "INFO")
                
                resampled['symbol'] = symbol
                resampled.reset_index(inplace=True)
                df_list.append(resampled)
        
        df = pd.concat(df_list, ignore_index=True)
        # IMPORTANT: Sort by timestamp so all symbols process together
        df = df.sort_values('timestamp').reset_index(drop=True)
        add_log(f"Resampled to {len(df)} 3-minute candles across {len(symbols)} symbols", "INFO")
        add_log(f"Time range (extended): {df['timestamp'].min()} to {df['timestamp'].max()} (target end 15:15)", "INFO")
        
        # Set initial prices for all symbols
        for symbol in symbols:
            symbol_data = df[df['symbol'] == symbol]
            if not symbol_data.empty:
                broker.update_market_price(symbol, symbol_data.iloc[0]['open'])
        
        add_log(f"Loaded {len(df)} candles for {len(symbols)} symbols", "INFO")
        
        # Create simulator
        simulator = MarketSimulator(data_manager, date, symbols, speed=100.0, ticks_per_candle=10)
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
            
            # === KAFKA: Stream tick data ===
            if kafka_producer:
                try:
                    kafka_producer.send({
                        'type': 'tick',
                        'symbol': tick['symbol'],
                        'price': tick['price'],
                        'timestamp': tick['timestamp'].isoformat(),
                        'volume': tick.get('volume', 0)
                    }, topic='velox-ticks')
                except Exception as e:
                    pass  # Silent fail for optional service
            
            # === REDIS: Cache latest tick ===
            if redis_manager:
                try:
                    redis_manager.set_latest_tick(tick['symbol'], tick)
                except Exception as e:
                    pass
            
            # === INFLUXDB: Store tick ===
            if influx_manager:
                try:
                    influx_manager.write_tick(tick['symbol'], tick, tick['timestamp'])
                except Exception as e:
                    pass
            
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
                    
                    # === KAFKA: Stream signal ===
                    if kafka_producer:
                        try:
                            kafka_producer.send({
                                'type': 'signal',
                                **signal,
                                'timestamp': datetime.now().isoformat()
                            }, topic='velox-signals')
                        except:
                            pass
                    
                    # === REDIS: Increment signal counter ===
                    if redis_manager:
                        try:
                            redis_manager.increment_signal_count(signal['strategy_id'], signal['action'])
                        except:
                            pass
                    
                    # Get current positions
                    strategy_positions = position_manager.get_positions()
                    all_positions = []
                    for strat_id, positions_dict in strategy_positions.items():
                        for symbol, pos in positions_dict.items():
                            all_positions.append(pos)
                    
                    # Validate signal
                    result = risk_manager.validate_signal(signal, strategy_positions, all_positions)
                    
                    if result.approved:
                        # Execute order
                        order = order_manager.execute_signal(signal)
                        if order and order['status'] == 'FILLED':
                            stats['orders'] += 1
                            add_log(f"✅ Order filled: {signal['action']} {signal['symbol']} @ {order['filled_price']:.2f}", "INFO")
                            
                            # === KAFKA: Stream trade ===
                            if kafka_producer:
                                try:
                                    kafka_producer.send({
                                        'type': 'trade',
                                        'action': signal['action'],
                                        'symbol': signal['symbol'],
                                        'price': order['filled_price'],
                                        'quantity': order['quantity'],
                                        'strategy_id': signal['strategy_id'],
                                        'timestamp': datetime.now().isoformat()
                                    }, topic='velox-trades')
                                except:
                                    pass
                            
                            # === INFLUXDB: Store trade ===
                            if influx_manager:
                                try:
                                    pnl = order.get('pnl', 0) if signal['action'] == 'SELL' else None
                                    influx_manager.write_trade(
                                        signal['strategy_id'],
                                        signal['symbol'],
                                        signal['action'],
                                        order['filled_price'],
                                        order['quantity'],
                                        pnl
                                    )
                                except:
                                    pass
                            
                            if signal['action'] == 'BUY':
                                # Get strategy-specific trailing SL config
                                strategy = strategy_manager.get_strategy(signal['strategy_id'])
                                
                                atr_multiplier = 2.5
                                for strat_config in strategy_configs:
                                    if strat_config['id'] == signal['strategy_id']:
                                        trailing_config = strat_config.get('trailing_sl', {})
                                        atr_multiplier = trailing_config.get('atr_multiplier', 2.5)
                                        break
                                
                                initial_atr = order['filled_price'] * 0.015
                                
                                # Setup trailing SL
                                trailing_sl_manager.add_stop_loss(
                                    strategy_id=signal['strategy_id'],
                                    symbol=signal['symbol'],
                                    sl_type=TrailingStopLossType.ATR,
                                    entry_price=order['filled_price'],
                                    config={
                                        'atr_value': initial_atr,
                                        'atr_multiplier': atr_multiplier
                                    },
                                    entry_timestamp=tick['timestamp']
                                )
                                # Fetch SL info for detailed logging
                                sl_info = trailing_sl_manager.get_stop_loss_info(signal['strategy_id'], signal['symbol'])
                                if sl_info:
                                    add_log(
                                        f"🛡️ Trailing SL activated for {signal['symbol']}:\n"
                                        f"   • Type: ATR ({atr_multiplier}x)\n"
                                        f"   • Entry: ${order['filled_price']:.2f}\n"
                                        f"   • Initial SL: ${sl_info['current_sl']:.2f}\n"
                                        f"   • Highest: ${sl_info['highest_price']:.2f}",
                                        "INFO"
                                    )
                                else:
                                    add_log(f"🛡️ Trailing SL activated for {signal['symbol']}: Initial SL @ ${order['filled_price'] - (atr_multiplier * initial_atr):.2f} ({atr_multiplier}x ATR)", "INFO")
                                
                                # Update strategy's internal position tracking to prevent duplicate entries
                                if strategy:
                                    strategy.add_position(
                                        symbol=signal['symbol'],
                                        entry_price=order['filled_price'],
                                        quantity=order['quantity'],
                                        timestamp=tick['timestamp']
                                    )
                                
                                # === REDIS: Cache position ===
                                if redis_manager:
                                    try:
                                        redis_manager.set_position(
                                            signal['strategy_id'],
                                            signal['symbol'],
                                            {
                                                'entry_price': order['filled_price'],
                                                'quantity': order['quantity'],
                                                'timestamp': tick['timestamp'].isoformat()
                                            }
                                        )
                                    except:
                                        pass
                            
                            elif signal['action'] == 'SELL':
                                # Close position
                                pos = position_manager.get_position(signal['strategy_id'], signal['symbol'])
                                if pos:
                                    pnl = (order['filled_price'] - pos['entry_price']) * pos['quantity']
                                    pnl_pct = ((order['filled_price'] - pos['entry_price']) / pos['entry_price']) * 100
                                    add_log(f"✅ SELL {signal['symbol']} @ ${order['filled_price']:.2f} | P&L: ${pnl:.2f} ({pnl_pct:+.2f}%)", "INFO")
                                    
                                    # === REDIS: Update strategy P&L ===
                                    if redis_manager:
                                        try:
                                            redis_manager.update_strategy_pnl(signal['strategy_id'], pnl)
                                            redis_manager.delete_position(signal['strategy_id'], signal['symbol'])
                                        except:
                                            pass
                                
                                position_manager.remove_position(signal['strategy_id'], signal['symbol'])
                                trailing_sl_manager.remove_stop_loss(signal['strategy_id'], signal['symbol'])
                                
                                # Update strategy's internal position tracking
                                strategy = strategy_manager.get_strategy(signal['strategy_id'])
                                if strategy:
                                    strategy.remove_position(signal['symbol'])
                    else:
                        add_log(f"⛔ Signal rejected: {result.reason}", "WARNING")
                
                # Clear all signals after processing to prevent duplicates
                strategy_manager.clear_all_signals()
            
            # Check trailing SL
            strategy_positions = position_manager.get_positions()
            for strat_id, positions_dict in strategy_positions.items():
                for symbol, pos in positions_dict.items():
                    current_price = broker.get_market_price(symbol)
                    
                    # Update trailing SL: compute highest price so far
                    sl_info_before = trailing_sl_manager.get_stop_loss_info(strat_id, symbol)
                    prev_highest = sl_info_before['highest_price'] if sl_info_before else current_price
                    highest_price = max(prev_highest, current_price)
                    trailing_sl_manager.update_stop_loss(
                        strat_id,
                        symbol,
                        current_price,
                        highest_price=highest_price
                    )
                    
                    # Check if SL hit
                    sl_hit = trailing_sl_manager.check_stop_loss(strat_id, symbol, current_price)
                    sl_info = trailing_sl_manager.get_stop_loss_info(strat_id, symbol)
                    
                    if sl_hit:
                        add_log(f"🛑 Trailing SL triggered for {symbol} @ ${current_price:.2f}", "WARNING")
                        
                        # Generate SELL signal
                        sell_signal = {
                            'strategy_id': strat_id,
                            'action': 'SELL',
                            'symbol': symbol,
                            'price': current_price,
                            'quantity': pos['quantity'],
                            'timestamp': tick['timestamp'],
                            'reason': f"Trailing SL hit @ {sl_info['current_sl']:.2f}"
                        }
                        
                        # Execute exit
                        order = order_manager.execute_signal(sell_signal)
                        if order and order['status'] == 'FILLED':
                            pnl = (current_price - pos['entry_price']) * pos['quantity']
                            pnl_pct = ((current_price - pos['entry_price']) / pos['entry_price']) * 100
                            add_log(f"✅ SELL {symbol} @ ${current_price:.2f} | P&L: ${pnl:.2f} ({pnl_pct:+.2f}%)", "INFO")
                            
                            position_manager.remove_position(strat_id, symbol)
                            trailing_sl_manager.remove_stop_loss(strat_id, symbol)
                            
                            # Update strategy's internal position tracking
                            strategy = strategy_manager.get_strategy(strat_id)
                            if strategy:
                                strategy.remove_position(symbol)
                    
                    # === INFLUXDB: Store position snapshot ===
                    if influx_manager:
                        try:
                            unrealized_pnl = (current_price - pos['entry_price']) * pos['quantity']
                            unrealized_pnl_pct = ((current_price - pos['entry_price']) / pos['entry_price']) * 100
                            influx_manager.write_position_snapshot(
                                strat_id, symbol, current_price, pos['quantity'],
                                unrealized_pnl, unrealized_pnl_pct, tick['timestamp']
                            )
                        except:
                            pass
                    
                    # === INFLUXDB: Store SL update ===
                    if influx_manager and sl_info:
                        try:
                            influx_manager.write_sl_update(
                                strat_id, symbol, f"{strat_id}_{symbol}",
                                sl_info['current_sl'], sl_info['highest_price'],
                                'ATR', tick['timestamp']
                            )
                        except:
                            pass
            
            # Update UI state every 100 ticks
            if stats['ticks'] % 100 == 0:
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
        
        # Close connections
        if kafka_producer:
            try:
                kafka_producer.flush()
                kafka_producer.close()
                add_log("Kafka connection closed", "INFO")
            except:
                pass
        
        if influx_manager:
            try:
                influx_manager.close()
                add_log("InfluxDB connection closed", "INFO")
            except:
                pass
        
        if redis_manager:
            try:
                redis_manager.close()
                add_log("Redis connection closed", "INFO")
            except:
                pass
        
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

# Start simulation in background thread
simulation_thread = threading.Thread(target=run_simulation, daemon=True)
simulation_thread.start()

if __name__ == '__main__':
    print("="*60)
    print("VELOX Trading System - Integrated Dashboard")
    print("="*60)
    print("Services: Kafka + InfluxDB + Redis")
    print("Dashboard: http://localhost:5000")
    print("="*60)
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
