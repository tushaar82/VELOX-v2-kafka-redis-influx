"""
VELOX Main Orchestrator.
Ties all components together for complete system operation.
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime
import logging

# Add src to path if running as script
src_path = Path(__file__).parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from utils.logging_config import initialize_logging, get_logger
from utils.config_loader import ConfigLoader
from adapters.broker.simulated import SimulatedBrokerAdapter
from adapters.strategy.rsi_momentum import RSIMomentumStrategy
from adapters.data.historical import HistoricalDataManager
from core.market_simulator import MarketSimulator
from core.multi_strategy_manager import MultiStrategyManager
from core.risk_manager import RiskManager
from core.order_manager import OrderManager, PositionManager
from core.trailing_sl import TrailingStopLossManager, TrailingStopLossType
from core.time_controller import TimeController
from core.candle_aggregator import CandleAggregator
from core.warmup_manager import WarmupManager
from database.data_manager import DataManager


class VeloxSystem:
    """Main VELOX trading system orchestrator."""
    
    def __init__(self, config_dir: str = 'config', data_dir: str = 'data'):
        """
        Initialize VELOX system.
        
        Args:
            config_dir: Configuration directory
            data_dir: Data directory
        """
        self.logger = get_logger('velox_system')
        
        # Load configurations
        self.logger.info("Loading configurations...")
        self.config_loader = ConfigLoader(config_dir)
        
        if not self.config_loader.validate_config():
            raise ValueError("Configuration validation failed")
        
        self.system_config = self.config_loader.load_system_config()
        self.strategies_config = self.config_loader.load_strategies_config()
        
        # Initialize components
        self.logger.info("Initializing components...")
        
        # Data manager
        self.data_manager = HistoricalDataManager(data_dir)
        self.logger.info(f"Data manager initialized with {len(self.data_manager.get_statistics()['symbols'])} symbols")
        
        # Broker
        broker_config = self.system_config['system']['broker']
        self.broker = SimulatedBrokerAdapter(
            initial_capital=broker_config['capital'],
            slippage_pct=broker_config.get('slippage_pct', 0.001)
        )
        self.broker.connect()
        self.logger.info(f"Broker initialized: {broker_config['type']}, capital={broker_config['capital']}")
        
        # Database manager for comprehensive logging (initialize early)
        try:
            self.db_manager = DataManager()
            self.logger.info("Database manager initialized")
        except Exception as e:
            self.logger.warning(f"Database manager initialization failed: {e} - continuing without database")
            self.db_manager = None
        
        # Risk manager
        risk_config = self.system_config['system']['risk']
        risk_config['initial_capital'] = broker_config['capital']
        self.risk_manager = RiskManager(risk_config, data_manager=self.db_manager)
        self.logger.info("Risk manager initialized")
        
        # Order and position managers
        self.order_manager = OrderManager(self.broker, data_manager=self.db_manager)
        self.position_manager = PositionManager(self.broker)
        self.logger.info("Order and position managers initialized")
        
        # Trailing SL manager
        self.sl_manager = TrailingStopLossManager(data_manager=self.db_manager)
        self.logger.info("Trailing SL manager initialized")
        
        # Time controller
        self.time_controller = TimeController()
        self.logger.info("Time controller initialized")
        
        # Candle aggregator and warmup manager (initialized per simulation)
        self.candle_aggregator = None
        self.warmup_manager = None
        
        # Strategy manager
        self.strategy_manager = MultiStrategyManager()
        self._load_strategies()
        self.logger.info("Strategy manager initialized")
        
        self.logger.info("✓ VELOX system initialized successfully")
    
    def _load_strategies(self):
        """Load strategies from configuration."""
        enabled_strategies = self.config_loader.get_enabled_strategies()
        
        for strategy_config in enabled_strategies:
            strategy_id = strategy_config['id']
            strategy_class = strategy_config['class']
            symbols = strategy_config['symbols']
            params = strategy_config['params']
            
            # Currently only RSI Momentum is implemented
            if strategy_class == 'RSIMomentumStrategy':
                strategy = RSIMomentumStrategy(strategy_id, symbols, params)
                strategy.initialize()
                self.strategy_manager.add_strategy(strategy)
                self.logger.info(f"Loaded strategy: {strategy_id} for {symbols}")
            else:
                self.logger.warning(f"Unknown strategy class: {strategy_class}")
    
    def run_simulation(self, date: str, speed: float = 100.0):
        """
        Run simulation for a specific date.
        
        Args:
            date: Date to simulate (YYYY-MM-DD)
            speed: Simulation speed multiplier
        """
        self.logger.info("="*80)
        self.logger.info(f"STARTING SIMULATION: {date} at {speed}x speed")
        self.logger.info("="*80)
        
        # Get symbols from all strategies
        all_symbols = set()
        for strategy in self.strategy_manager.get_strategies().values():
            all_symbols.update(strategy.symbols)
        
        symbols = list(all_symbols)
        self.logger.info(f"Symbols to simulate: {symbols}")
        
        # ========== WARMUP & CANDLE AGGREGATION SETUP ==========
        
        # 1. Collect required timeframes from all strategies
        timeframes = set()
        strategies_list = list(self.strategy_manager.get_strategies().values())
        
        for strategy in strategies_list:
            if hasattr(strategy, 'get_required_timeframes'):
                timeframes.update(strategy.get_required_timeframes())
            else:
                timeframes.add('1min')  # Default
        
        self.logger.info(f"Required timeframes: {list(timeframes)}")
        
        # 2. Create CandleAggregator
        self.candle_aggregator = CandleAggregator(
            timeframes=list(timeframes),
            max_history=500
        )
        self.logger.info("Candle aggregator created")
        
        # 3. Register callbacks for candle completion
        for tf in timeframes:
            self.candle_aggregator.register_candle_callback(
                tf,
                lambda candle, tf=tf: self._on_candle_complete(candle)
            )
        
        # 4. Create WarmupManager
        self.warmup_manager = WarmupManager(
            min_candles=200,
            auto_calculate=True
        )
        self.logger.info("Warmup manager created")
        
        # 5. Calculate required warmup period
        required_candles = self.warmup_manager.calculate_required_warmup(strategies_list)
        self.logger.info(f"Warmup requires {required_candles} candles")
        
        # 6. Load historical candles for warmup
        self.logger.info("Loading historical candles for warmup...")
        try:
            date_obj = datetime.strptime(date, '%Y-%m-%d')
            historical_candles = self.warmup_manager.load_historical_candles(
                data_manager=self.data_manager,
                date=date_obj,
                symbols=symbols,
                count=required_candles
            )
            
            if not historical_candles:
                self.logger.warning("No historical data for warmup - manually enabling strategies")
                # Manually enable strategies if no historical data
                for strategy in strategies_list:
                    strategy.set_warmup_complete()
                self.logger.warning("Strategies enabled without warmup - may have inaccurate indicators initially")
            else:
                # 7. Warmup strategies
                self.logger.info(f"Warming up strategies with {sum(len(v) for v in historical_candles.values())} candles...")
                success = self.warmup_manager.warmup_strategies(
                    strategies=strategies_list,
                    historical_candles=historical_candles,
                    candle_aggregator=self.candle_aggregator
                )
                
                if success:
                    self.logger.info("✓ Warmup complete - strategies ready for trading")
                    warmup_status = self.warmup_manager.get_warmup_status()
                    self.logger.info(f"  Candles loaded: {warmup_status['candles_loaded']}/{warmup_status['candles_required']}")
                else:
                    self.logger.error("✗ Warmup failed - manually enabling strategies")
                    # Manually enable strategies if warmup failed
                    for strategy in strategies_list:
                        strategy.set_warmup_complete()
                    self.logger.warning("Strategies enabled without warmup - may have inaccurate indicators initially")
        
        except Exception as e:
            self.logger.error(f"Warmup error: {e}", exc_info=True)
            self.logger.warning("Continuing without warmup - manually enabling strategies")
            # Manually enable strategies if warmup failed
            for strategy in strategies_list:
                strategy.set_warmup_complete()
            self.logger.warning("Strategies enabled without warmup - may have inaccurate indicators initially")
        
        # ========== END WARMUP & CANDLE AGGREGATION SETUP ==========
        
        # Update broker prices for all symbols
        try:
            df = self.data_manager.get_data(date, symbols)
            if df.empty:
                self.logger.error(f"No data available for {date}")
                return
            
            # Set initial prices
            for symbol in symbols:
                symbol_data = df[df['symbol'] == symbol]
                if not symbol_data.empty:
                    initial_price = symbol_data.iloc[0]['open']
                    self.broker.update_market_price(symbol, initial_price)
                    self.logger.info(f"Initial price for {symbol}: {initial_price:.2f}")
        
        except Exception as e:
            self.logger.error(f"Failed to load data for {date}: {e}")
            return
        
        # Create simulator
        simulator = MarketSimulator(
            data_adapter=self.data_manager,
            date=date,
            symbols=symbols,
            speed=speed,
            ticks_per_candle=10
        )
        
        # Attach candle aggregator to simulator
        simulator.set_candle_aggregator(self.candle_aggregator)
        self.logger.info("Candle aggregator attached to simulator")
        
        # Start strategy manager
        self.strategy_manager.start()
        
        # Statistics
        stats = {
            'ticks_processed': 0,
            'signals_generated': 0,
            'signals_approved': 0,
            'orders_executed': 0,
            'positions_opened': 0,
            'positions_closed': 0
        }
        
        # Simulation callback
        def process_tick(tick_data):
            stats['ticks_processed'] += 1
            
            # Update broker price
            self.broker.update_market_price(tick_data['symbol'], tick_data['price'])
            
            # Periodic database logging
            if self.db_manager:
                # Log position snapshots every 100 ticks
                if stats['ticks_processed'] % 100 == 0:
                    for strategy in strategies_list:
                        for symbol, position in strategy.positions.items():
                            try:
                                current_price = tick_data.get('price', tick_data.get('close'))
                                entry_price = position.get('entry_price')
                                quantity = position.get('quantity')
                                
                                if entry_price and quantity:
                                    unrealized_pnl = (current_price - entry_price) * quantity
                                    
                                    self.db_manager.log_position_update(
                                        strategy_id=strategy.strategy_id,
                                        symbol=symbol,
                                        current_price=current_price,
                                        quantity=quantity,
                                        unrealized_pnl=unrealized_pnl,
                                        timestamp=tick_data.get('timestamp')
                                    )
                            except Exception as e:
                                pass  # Silent fail for logging
                
                # Log indicator values every 50 ticks
                if stats['ticks_processed'] % 50 == 0:
                    symbol = tick_data.get('symbol')
                    if symbol:
                        for strategy in strategies_list:
                            if hasattr(strategy, 'indicator_manager'):
                                try:
                                    indicators = strategy.indicator_manager.get_indicators(symbol)
                                    if indicators:
                                        self.db_manager.log_indicator_values(
                                            symbol=symbol,
                                            indicators=indicators,
                                            timestamp=tick_data.get('timestamp')
                                        )
                                except Exception as e:
                                    pass  # Silent fail for logging
            
            # Check time-based actions
            actions = self.time_controller.check_time(
                tick_data['timestamp'],
                on_warning=lambda: self.logger.warning("⚠️  15 minutes to square-off"),
                on_square_off=lambda: self._square_off_all(stats)
            )
            
            # Block new entries if needed
            if actions['new_entries_blocked']:
                return
            
            # Process tick through strategies
            self.strategy_manager.process_tick(tick_data)
            
            # Get and process signals
            signals = self.strategy_manager.get_all_signals()
            if signals:
                stats['signals_generated'] += len(signals)
                
                for signal in signals:
                    # Validate with risk manager
                    current_positions = self.strategy_manager.get_all_positions()
                    result = self.risk_manager.validate_signal(signal, current_positions, {})
                    
                    if result.approved:
                        stats['signals_approved'] += 1
                        
                        # Execute order
                        order = self.order_manager.execute_signal(signal)
                        
                        if order and order['status'] == 'FILLED':
                            stats['orders_executed'] += 1
                            
                            # Update position
                            self.position_manager.update_position(
                                signal['strategy_id'],
                                signal['symbol'],
                                order
                            )
                            
                            # Update strategy position
                            strategy = self.strategy_manager.get_strategy(signal['strategy_id'])
                            if strategy:
                                if signal['action'] == 'BUY':
                                    strategy.add_position(
                                        signal['symbol'],
                                        order['filled_price'],
                                        order['filled_quantity'],
                                        order['fill_timestamp']
                                    )
                                    stats['positions_opened'] += 1
                                    
                                    # Add trailing SL
                                    self.sl_manager.add_stop_loss(
                                        strategy_id=signal['strategy_id'],
                                        symbol=signal['symbol'],
                                        sl_type=TrailingStopLossType.FIXED_PCT,
                                        entry_price=order['filled_price'],
                                        config={'pct': 0.01}
                                    )
                                else:
                                    strategy.remove_position(signal['symbol'])
                                    stats['positions_closed'] += 1
                                    
                                    # Remove trailing SL
                                    self.sl_manager.remove_stop_loss(
                                        signal['strategy_id'],
                                        signal['symbol']
                                    )
                
                # Clear signals
                self.strategy_manager.clear_all_signals()
            
            # Update trailing SLs
            for strategy_id, positions in self.strategy_manager.get_all_positions().items():
                for symbol, pos in positions.items():
                    current_price = pos.get('current_price', pos['entry_price'])
                    highest_price = pos.get('highest_price', pos['entry_price'])
                    
                    self.sl_manager.update_stop_loss(
                        strategy_id,
                        symbol,
                        current_price,
                        highest_price
                    )
                    
                    # Check if SL hit
                    if self.sl_manager.check_stop_loss(strategy_id, symbol, current_price):
                        self.logger.warning(f"Trailing SL hit for {strategy_id}/{symbol}")
                        # Would generate exit signal here
        
        # Run simulation
        try:
            simulator.run_simulation(callback_fn=process_tick)
        except KeyboardInterrupt:
            self.logger.warning("Simulation interrupted by user")
        except Exception as e:
            self.logger.error(f"Simulation error: {e}", exc_info=True)
        
        # Final summary
        self._print_summary(stats)
    
    def _on_candle_complete(self, candle):
        """
        Called when a candle completes.
        
        Args:
            candle: Completed Candle object
        """
        try:
            candle_data = candle.to_dict()
            
            # Notify all strategies
            for strategy in self.strategy_manager.get_strategies().values():
                if hasattr(strategy, 'on_candle_complete'):
                    strategy.on_candle_complete(candle_data, candle.timeframe)
            
            # Log to database
            if self.db_manager:
                try:
                    self.db_manager.log_candle(
                        symbol=candle.symbol,
                        timeframe=candle.timeframe,
                        candle_data=candle_data,
                        timestamp=candle.timestamp
                    )
                except Exception as e:
                    pass  # Silent fail for logging
        
        except Exception as e:
            self.logger.error(f"Error in candle complete callback: {e}", exc_info=True)
    
    def _square_off_all(self, stats: dict):
        """Square off all positions."""
        self.logger.warning("🔔 SQUARE-OFF: Closing all positions")
        
        signals = self.strategy_manager.square_off_all()
        
        for signal in signals:
            order = self.order_manager.execute_signal(signal)
            if order and order['status'] == 'FILLED':
                self.position_manager.update_position(
                    signal['strategy_id'],
                    signal['symbol'],
                    order
                )
                stats['positions_closed'] += 1
    
    def _print_summary(self, stats: dict):
        """Print simulation summary."""
        self.logger.info("="*80)
        self.logger.info("SIMULATION SUMMARY")
        self.logger.info("="*80)
        
        self.logger.info(f"Ticks processed: {stats['ticks_processed']}")
        self.logger.info(f"Signals generated: {stats['signals_generated']}")
        self.logger.info(f"Signals approved: {stats['signals_approved']}")
        self.logger.info(f"Orders executed: {stats['orders_executed']}")
        self.logger.info(f"Positions opened: {stats['positions_opened']}")
        self.logger.info(f"Positions closed: {stats['positions_closed']}")
        
        # Account info
        account = self.broker.get_account_info()
        self.logger.info(f"\nAccount Summary:")
        self.logger.info(f"  Capital: {account['capital']:.2f}")
        self.logger.info(f"  Total value: {account['total_value']:.2f}")
        self.logger.info(f"  P&L: {account['pnl']:.2f} ({account['pnl_pct']:.2f}%)")
        self.logger.info(f"  Open positions: {account['num_positions']}")
        
        self.logger.info("="*80)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='VELOX Multi-Strategy Trading System')
    parser.add_argument('--date', type=str, required=True, help='Date to simulate (YYYY-MM-DD)')
    parser.add_argument('--speed', type=float, default=100.0, help='Simulation speed multiplier')
    parser.add_argument('--config', type=str, default='config', help='Configuration directory')
    parser.add_argument('--data', type=str, default='data', help='Data directory')
    parser.add_argument('--log-level', type=str, default='INFO', 
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging level')
    
    args = parser.parse_args()
    
    # Initialize logging
    log_level = getattr(logging, args.log_level)
    initialize_logging(log_level=log_level)
    
    logger = get_logger('main')
    
    try:
        # Create and run system
        logger.info("🚀 Starting VELOX Trading System")
        
        system = VeloxSystem(config_dir=args.config, data_dir=args.data)
        system.run_simulation(date=args.date, speed=args.speed)
        
        logger.info("✓ VELOX system completed successfully")
        
    except KeyboardInterrupt:
        logger.warning("System interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"System error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
