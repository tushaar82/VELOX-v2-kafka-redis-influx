"""
Configuration loader for VELOX system.
"""

import yaml
from pathlib import Path
from typing import Dict, List, Optional

from .logging_config import get_logger


class ConfigLoader:
    """Loads and validates configuration files."""
    
    def __init__(self, config_dir: str = 'config'):
        """
        Initialize config loader.
        
        Args:
            config_dir: Directory containing config files
        """
        self.config_dir = Path(config_dir)
        self.logger = get_logger('config_loader')
        
        self._system_config = None
        self._strategies_config = None
        self._symbols_config = None
    
    def load_system_config(self, reload: bool = False) -> Dict:
        """
        Load system configuration.
        
        Args:
            reload: Force reload from file
            
        Returns:
            System configuration dictionary
        """
        if self._system_config and not reload:
            return self._system_config
        
        config_file = self.config_dir / 'system.yaml'
        
        try:
            with open(config_file, 'r') as f:
                self._system_config = yaml.safe_load(f)
            
            self.logger.info(f"Loaded system config from {config_file}")
            return self._system_config
            
        except Exception as e:
            self.logger.error(f"Failed to load system config: {e}")
            raise
    
    def load_strategies_config(self, reload: bool = False) -> Dict:
        """
        Load strategies configuration.
        
        Args:
            reload: Force reload from file
            
        Returns:
            Strategies configuration dictionary
        """
        if self._strategies_config and not reload:
            return self._strategies_config
        
        config_file = self.config_dir / 'strategies.yaml'
        
        try:
            with open(config_file, 'r') as f:
                self._strategies_config = yaml.safe_load(f)
            
            enabled_count = sum(1 for s in self._strategies_config.get('strategies', []) if s.get('enabled', True))
            self.logger.info(f"Loaded {enabled_count} enabled strategies from {config_file}")
            return self._strategies_config
            
        except Exception as e:
            self.logger.error(f"Failed to load strategies config: {e}")
            raise
    
    def load_symbols_config(self, reload: bool = False) -> Dict:
        """
        Load symbols configuration.
        
        Args:
            reload: Force reload from file
            
        Returns:
            Symbols configuration dictionary
        """
        if self._symbols_config and not reload:
            return self._symbols_config
        
        config_file = self.config_dir / 'symbols.yaml'
        
        try:
            with open(config_file, 'r') as f:
                self._symbols_config = yaml.safe_load(f)
            
            watchlist_count = len(self._symbols_config.get('watchlist', []))
            self.logger.info(f"Loaded {watchlist_count} symbols from {config_file}")
            return self._symbols_config
            
        except Exception as e:
            self.logger.error(f"Failed to load symbols config: {e}")
            raise
    
    def get_watchlist(self) -> List[str]:
        """
        Get watchlist symbols.
        
        Returns:
            List of symbol names
        """
        symbols_config = self.load_symbols_config()
        watchlist = symbols_config.get('watchlist', [])
        
        return [s['symbol'] for s in watchlist if s.get('enabled', True)]
    
    def get_warmup_config(self) -> dict:
        """
        Get warmup configuration.
        
        Returns:
            Dict with warmup settings
        """
        system_config = self.load_system_config()
        return system_config.get('warmup', {
            'enabled': True,
            'min_candles': 200,
            'auto_calculate': True
        })
    
    def get_candle_aggregation_config(self) -> dict:
        """
        Get candle aggregation configuration.
        
        Returns:
            Dict with candle aggregation settings
        """
        system_config = self.load_system_config()
        return system_config.get('candle_aggregation', {
            'enabled': True,
            'default_timeframe': '1min',
            'supported_timeframes': ['1min', '3min', '5min', '15min'],
            'max_history': 500
        })
    
    def get_database_logging_config(self) -> dict:
        """
        Get database logging configuration.
        
        Returns:
            Dict with logging settings
        """
        system_config = self.load_system_config()
        return system_config.get('database_logging', {
            'log_all_signals': True,
            'log_all_ticks': False,
            'log_indicators': True,
            'log_candles': True,
            'position_snapshot_interval': 100,
            'indicator_snapshot_interval': 50,
            'batch_size': 50
        })
    
    def get_strategy_timeframes(self, strategy_id: str) -> list:
        """
        Get required timeframes for a strategy.
        
        Args:
            strategy_id: Strategy identifier
            
        Returns:
            List of timeframe strings
        """
        strategies_config = self.load_strategies_config()
        strategies = strategies_config.get('strategies', [])
        
        for strategy in strategies:
            if strategy.get('id') == strategy_id:
                return strategy.get('timeframes', ['1min'])
        
        return ['1min']  # Default
    
    def get_enabled_strategies(self) -> List[Dict]:
        """
        Get list of enabled strategies.
        
        Returns:
            List of strategy configuration dictionaries
        """
        config = self.load_strategies_config()
        return [s for s in config.get('strategies', []) if s.get('enabled', True)]
    
    def validate_config(self) -> bool:
        """
        Validate all configurations.
        
        Returns:
            True if all configs valid
        """
        try:
            # Load all configs
            system = self.load_system_config()
            strategies = self.load_strategies_config()
            symbols = self.load_symbols_config()
            
            # Validate system config
            assert 'broker' in system['system'], "Missing broker config"
            assert 'risk' in system['system'], "Missing risk config"
            assert 'kafka' in system['system'], "Missing kafka config"
            
            # Validate strategies config
            assert 'strategies' in strategies, "Missing strategies list"
            for strategy in strategies['strategies']:
                assert 'id' in strategy, "Strategy missing id"
                assert 'class' in strategy, "Strategy missing class"
                assert 'symbols' in strategy, "Strategy missing symbols"
                assert 'params' in strategy, "Strategy missing params"
            
            # Validate symbols config
            assert 'watchlist' in symbols, "Missing watchlist"
            assert len(symbols['watchlist']) > 0, "Watchlist is empty"
            
            self.logger.info("All configurations validated successfully")
            return True
            
        except AssertionError as e:
            self.logger.error(f"Config validation failed: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Config validation error: {e}")
            return False
    
    def reload_all(self):
        """Reload all configurations."""
        self.logger.info("Reloading all configurations...")
        self.load_system_config(reload=True)
        self.load_strategies_config(reload=True)
        self.load_symbols_config(reload=True)
        self.logger.info("All configurations reloaded")


if __name__ == "__main__":
    # Test config loader
    from .logging_config import initialize_logging
    import logging
    
    initialize_logging(log_level=logging.INFO)
    
    print("\n=== Testing Config Loader ===\n")
    
    loader = ConfigLoader()
    
    # Validate
    if loader.validate_config():
        print("✓ Configuration validation passed")
    
    # Load system config
    system = loader.load_system_config()
    print(f"\nSystem config:")
    print(f"  Broker: {system['system']['broker']['type']}")
    print(f"  Capital: {system['system']['broker']['capital']}")
    print(f"  Max positions: {system['system']['risk']['max_total_positions']}")
    
    # Load strategies
    strategies = loader.get_enabled_strategies()
    print(f"\nEnabled strategies: {len(strategies)}")
    for strategy in strategies:
        print(f"  - {strategy['id']}: {strategy['symbols']}")
    
    # Load watchlist
    watchlist = loader.get_watchlist()
    print(f"\nWatchlist: {watchlist}")
    
    # Test new config methods
    warmup_config = loader.get_warmup_config()
    print(f"\nWarmup config: {warmup_config}")
    
    candle_config = loader.get_candle_aggregation_config()
    print(f"Candle aggregation config: {candle_config}")
    
    db_logging_config = loader.get_database_logging_config()
    print(f"Database logging config: {db_logging_config}")
    
    print("\n✓ Config loader test complete")
