#!/usr/bin/env python3
"""
Simple test to verify warmup is working.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.logging_config import initialize_logging, get_logger
from src.adapters.strategy.supertrend import SupertrendStrategy
from src.adapters.data.historical import HistoricalDataManager
from src.core.candle_aggregator import CandleAggregator
from src.core.warmup_manager import WarmupManager
from datetime import datetime
import logging

def main():
    """Test warmup."""
    initialize_logging(log_level=logging.INFO)
    logger = get_logger('warmup_test')
    
    logger.info("="*80)
    logger.info("WARMUP TEST")
    logger.info("="*80)
    
    # 1. Create strategy
    strategy = SupertrendStrategy('test_st', ['RELIANCE'], {
        'atr_period': 10,
        'atr_multiplier': 3.0,
        'target_pct': 0.02,
        'initial_sl_pct': 0.015
    })
    strategy.initialize()
    
    logger.info(f"Strategy created: is_warmed_up = {strategy.is_warmed_up}")
    logger.info(f"Warmup candles required: {strategy.warmup_candles_required}")
    
    # 2. Create candle aggregator
    aggregator = CandleAggregator(timeframes=['1min'], max_history=500)
    logger.info("Candle aggregator created")
    
    # 3. Create warmup manager
    warmup_mgr = WarmupManager(min_candles=200, auto_calculate=True)
    logger.info("Warmup manager created")
    
    # 4. Load historical data
    data_mgr = HistoricalDataManager('./data')
    date = datetime(2024, 1, 15)
    
    logger.info(f"Loading historical candles for {date.strftime('%Y-%m-%d')}...")
    historical_candles = warmup_mgr.load_historical_candles(
        data_manager=data_mgr,
        date=date,
        symbols=['RELIANCE'],
        count=200
    )
    
    if not historical_candles:
        logger.error("No historical candles loaded!")
        return False
    
    logger.info(f"Loaded {sum(len(v) for v in historical_candles.values())} candles")
    
    # 5. Warmup strategy
    logger.info("Warming up strategy...")
    success = warmup_mgr.warmup_strategies(
        strategies=[strategy],
        historical_candles=historical_candles,
        candle_aggregator=aggregator
    )
    
    logger.info(f"Warmup success: {success}")
    logger.info(f"Strategy is_warmed_up: {strategy.is_warmed_up}")
    
    # 6. Check status
    status = strategy.get_status()
    logger.info(f"Strategy status: {status}")
    
    if strategy.is_warmed_up:
        logger.info("✓ WARMUP SUCCESSFUL - Strategy ready for trading!")
        return True
    else:
        logger.error("✗ WARMUP FAILED - Strategy not ready")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
