"""
Multi-Strategy Manager.
Orchestrates multiple trading strategies independently.
"""

from typing import Dict, List, Optional
from datetime import datetime

from ..adapters.strategy.base import StrategyAdapter
from ..utils.logging_config import get_logger


class MultiStrategyManager:
    """Manages multiple trading strategies."""
    
    def __init__(self):
        """Initialize multi-strategy manager."""
        self.strategies = {}  # strategy_id -> StrategyAdapter
        self.is_running = False
        self.logger = get_logger('multi_strategy_manager')
        
        self.logger.info("MultiStrategyManager initialized")
    
    def add_strategy(self, strategy: StrategyAdapter):
        """
        Add a strategy to the manager.
        
        Args:
            strategy: Strategy instance
        """
        strategy_id = strategy.strategy_id
        
        if strategy_id in self.strategies:
            self.logger.warning(f"Strategy {strategy_id} already exists, replacing")
        
        self.strategies[strategy_id] = strategy
        self.logger.info(
            f"Strategy added: {strategy_id}, symbols={strategy.symbols}, "
            f"active={strategy.is_active}"
        )
    
    def remove_strategy(self, strategy_id: str):
        """
        Remove a strategy.
        
        Args:
            strategy_id: Strategy identifier
        """
        if strategy_id in self.strategies:
            del self.strategies[strategy_id]
            self.logger.info(f"Strategy removed: {strategy_id}")
        else:
            self.logger.warning(f"Strategy {strategy_id} not found")
    
    def get_strategy(self, strategy_id: str) -> Optional[StrategyAdapter]:
        """
        Get a strategy by ID.
        
        Args:
            strategy_id: Strategy identifier
            
        Returns:
            Strategy instance or None
        """
        return self.strategies.get(strategy_id)
    
    def get_strategies(self) -> Dict[str, StrategyAdapter]:
        """
        Get all strategies.
        
        Returns:
            Dictionary of strategies {strategy_id: strategy}
        """
        return self.strategies.copy()
    
    def process_tick(self, tick_data: Dict):
        """
        Process a market tick through all strategies.
        
        Args:
            tick_data: Tick data dictionary
        """
        if not self.is_running:
            return
        
        symbol = tick_data.get('symbol')
        
        # Process tick through each strategy
        for strategy_id, strategy in self.strategies.items():
            # Only process if strategy is active and trades this symbol
            if strategy.is_active and symbol in strategy.symbols:
                try:
                    strategy.on_tick(tick_data)
                except Exception as e:
                    self.logger.error(
                        f"Error processing tick in strategy {strategy_id}: {e}",
                        exc_info=True
                    )
    
    def get_all_signals(self) -> List[Dict]:
        """
        Get signals from all strategies.
        
        Returns:
            List of all signals
        """
        all_signals = []
        
        for strategy in self.strategies.values():
            signals = strategy.get_signals()
            all_signals.extend(signals)
        
        return all_signals
    
    def clear_all_signals(self):
        """Clear signals from all strategies."""
        for strategy in self.strategies.values():
            strategy.clear_signals()
        
        self.logger.debug("All signals cleared")
    
    def get_all_positions(self) -> Dict[str, Dict]:
        """
        Get positions from all strategies.
        
        Returns:
            Dictionary {strategy_id: {symbol: position}}
        """
        all_positions = {}
        
        for strategy_id, strategy in self.strategies.items():
            positions = strategy.get_positions()
            if positions:
                all_positions[strategy_id] = positions
        
        return all_positions
    
    def activate_strategy(self, strategy_id: str):
        """
        Activate a strategy.
        
        Args:
            strategy_id: Strategy identifier
        """
        if strategy_id in self.strategies:
            self.strategies[strategy_id].activate()
            self.logger.info(f"Strategy activated: {strategy_id}")
        else:
            self.logger.warning(f"Strategy {strategy_id} not found")
    
    def deactivate_strategy(self, strategy_id: str):
        """
        Deactivate a strategy.
        
        Args:
            strategy_id: Strategy identifier
        """
        if strategy_id in self.strategies:
            self.strategies[strategy_id].deactivate()
            self.logger.info(f"Strategy deactivated: {strategy_id}")
        else:
            self.logger.warning(f"Strategy {strategy_id} not found")
    
    def square_off_all(self) -> List[Dict]:
        """
        Generate exit signals for all positions across all strategies.
        
        Returns:
            List of exit signals
        """
        all_exit_signals = []
        
        for strategy_id, strategy in self.strategies.items():
            exit_signals = strategy.square_off_all()
            all_exit_signals.extend(exit_signals)
            
            if exit_signals:
                self.logger.info(
                    f"Square-off signals generated for {strategy_id}: "
                    f"{len(exit_signals)} positions"
                )
        
        return all_exit_signals
    
    def get_status(self) -> Dict:
        """
        Get manager status.
        
        Returns:
            Status dictionary
        """
        strategy_statuses = []
        total_positions = 0
        num_active = 0
        
        for strategy_id, strategy in self.strategies.items():
            status = strategy.get_status()
            strategy_statuses.append(status)
            total_positions += status['num_positions']
            if status['is_active']:
                num_active += 1
        
        return {
            'is_running': self.is_running,
            'num_strategies': len(self.strategies),
            'num_active_strategies': num_active,
            'total_positions': total_positions,
            'strategies': strategy_statuses
        }
    
    def start(self):
        """Start the manager."""
        self.is_running = True
        self.logger.info("MultiStrategyManager started")
    
    def stop(self):
        """Stop the manager."""
        self.is_running = False
        self.logger.info("MultiStrategyManager stopped")


if __name__ == "__main__":
    # Test the manager
    from ..utils.logging_config import initialize_logging
    from ..adapters.strategy.rsi_momentum import RSIMomentumStrategy
    import logging
    
    initialize_logging(log_level=logging.INFO)
    
    print("\n=== Testing Multi-Strategy Manager ===\n")
    
    # Create manager
    manager = MultiStrategyManager()
    
    # Create strategies
    config1 = {
        'rsi_period': 14,
        'rsi_oversold': 30,
        'rsi_overbought': 70,
        'ma_period': 20
    }
    
    config2 = {
        'rsi_period': 14,
        'rsi_oversold': 25,
        'rsi_overbought': 75,
        'ma_period': 50
    }
    
    strategy1 = RSIMomentumStrategy('rsi_aggressive', ['STOCK1'], config1)
    strategy2 = RSIMomentumStrategy('rsi_conservative', ['STOCK2'], config2)
    
    strategy1.initialize()
    strategy2.initialize()
    
    # Add strategies
    manager.add_strategy(strategy1)
    manager.add_strategy(strategy2)
    
    print(f"Strategies: {list(manager.get_strategies().keys())}")
    
    # Start manager
    manager.start()
    
    # Process some ticks
    print("\nProcessing ticks...")
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
    
    # Get status
    status = manager.get_status()
    print(f"\nManager status:")
    print(f"  Running: {status['is_running']}")
    print(f"  Strategies: {status['num_strategies']}")
    print(f"  Active: {status['num_active_strategies']}")
    print(f"  Total positions: {status['total_positions']}")
    
    print("\n✓ Manager test complete")
