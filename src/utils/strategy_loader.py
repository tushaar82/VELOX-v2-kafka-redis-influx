"""
Strategy configuration loader.
Loads strategy configurations from YAML file.
"""

import yaml
from pathlib import Path
from typing import List, Dict


def load_strategies_config(config_path: str = './config/strategies.yaml') -> List[Dict]:
    """
    Load strategy configurations from YAML file.
    
    Args:
        config_path: Path to strategies.yaml file
        
    Returns:
        List of strategy configuration dictionaries
    """
    config_file = Path(config_path)
    
    if not config_file.exists():
        raise FileNotFoundError(f"Strategy config file not found: {config_path}")
    
    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)
    
    if 'strategies' not in config:
        raise ValueError("Invalid strategy config: 'strategies' key not found")
    
    return config['strategies']


def get_enabled_strategies(config_path: str = './config/strategies.yaml') -> List[Dict]:
    """
    Get only enabled strategies from configuration.
    
    Args:
        config_path: Path to strategies.yaml file
        
    Returns:
        List of enabled strategy configurations
    """
    all_strategies = load_strategies_config(config_path)
    return [s for s in all_strategies if s.get('enabled', False)]


def get_all_strategy_symbols(config_path: str = './config/strategies.yaml') -> List[str]:
    """
    Get all unique symbols used across all enabled strategies.
    
    Args:
        config_path: Path to strategies.yaml file
        
    Returns:
        List of unique symbol names
    """
    strategies = get_enabled_strategies(config_path)
    symbols = set()
    
    for strategy in strategies:
        symbols.update(strategy.get('symbols', []))
    
    return sorted(list(symbols))


def create_strategy_instance(strategy_config: Dict, available_symbols: List[str]):
    """
    Create a strategy instance from configuration.
    
    Args:
        strategy_config: Strategy configuration dictionary
        available_symbols: List of symbols with available data
        
    Returns:
        Strategy instance or None if symbols not available
    """
    from ..adapters.strategy.rsi_momentum import RSIMomentumStrategy
    from ..adapters.strategy.mtf_atr_strategy import MultiTimeframeATRStrategy
    from ..adapters.strategy.scalping_mtf_atr import ScalpingMTFATRStrategy
    from ..adapters.strategy.supertrend import SupertrendStrategy
    
    strategy_classes = {
        'RSIMomentumStrategy': RSIMomentumStrategy,
        'MultiTimeframeATRStrategy': MultiTimeframeATRStrategy,
        'ScalpingMTFATRStrategy': ScalpingMTFATRStrategy,
        'SupertrendStrategy': SupertrendStrategy
    }
    
    strategy_id = strategy_config['id']
    class_name = strategy_config['class']
    config_symbols = strategy_config.get('symbols', [])
    params = strategy_config.get('params', {})
    
    # Filter symbols to only those with available data
    filtered_symbols = [s for s in config_symbols if s in available_symbols]
    
    if not filtered_symbols:
        return None
    
    # Get strategy class
    strategy_class = strategy_classes.get(class_name)
    if not strategy_class:
        raise ValueError(f"Unknown strategy class: {class_name}")
    
    # Create strategy instance
    strategy = strategy_class(strategy_id, filtered_symbols, params)
    
    return strategy
