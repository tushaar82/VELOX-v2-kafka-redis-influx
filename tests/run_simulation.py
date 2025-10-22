"""
Run market simulation with Kafka integration.
"""

import sys
from pathlib import Path
import argparse

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.adapters.data.historical import HistoricalDataManager
from src.core.market_simulator import MarketSimulator
from src.utils.kafka_helper import KafkaProducerWrapper
from src.utils.logging_config import initialize_logging
import logging


def main():
    """Run market simulation."""
    parser = argparse.ArgumentParser(description='Run VELOX market simulation')
    parser.add_argument('--date', type=str, help='Date to simulate (YYYY-MM-DD)')
    parser.add_argument('--symbols', nargs='+', help='Symbols to simulate')
    parser.add_argument('--speed', type=float, default=10.0, help='Playback speed multiplier')
    parser.add_argument('--data-dir', type=str, default='./data', help='Data directory')
    parser.add_argument('--kafka', action='store_true', help='Enable Kafka publishing')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    args = parser.parse_args()
    
    # Initialize logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    initialize_logging(log_level=log_level)
    
    print("\n" + "="*80)
    print("VELOX MARKET SIMULATOR")
    print("="*80)
    
    # Initialize data manager
    print(f"\nLoading data from {args.data_dir}...")
    hdm = HistoricalDataManager(args.data_dir)
    stats = hdm.get_statistics()
    
    print(f"Available symbols: {len(stats['symbols'])}")
    print(f"Symbols: {', '.join(stats['symbols'][:10])}...")
    
    # Determine date and symbols
    if args.date:
        date = args.date
    else:
        # Use a date from the middle of available data
        symbol = stats['symbols'][0]
        dates = hdm.get_available_dates(symbol)
        date = dates[len(dates) // 2] if dates else None
    
    if not date:
        print("Error: No date available")
        return
    
    if args.symbols:
        symbols = args.symbols
    else:
        # Use first 5 symbols
        symbols = stats['symbols'][:5]
    
    print(f"\nSimulation parameters:")
    print(f"  Date: {date}")
    print(f"  Symbols: {', '.join(symbols)}")
    print(f"  Speed: {args.speed}x")
    print(f"  Kafka: {'Enabled' if args.kafka else 'Disabled'}")
    
    # Initialize Kafka producer if enabled
    kafka_producer = None
    if args.kafka:
        try:
            kafka_producer = KafkaProducerWrapper(topic='market.ticks')
            print("  Kafka producer: Connected")
        except Exception as e:
            print(f"  Kafka producer: Failed to connect - {e}")
            print("  Continuing without Kafka...")
    
    # Create simulator
    simulator = MarketSimulator(
        data_adapter=hdm,
        date=date,
        symbols=symbols,
        speed=args.speed,
        ticks_per_candle=10
    )
    
    # Load data
    print("\nLoading historical data...")
    if not simulator.load_data():
        print("Error: Failed to load data")
        return
    
    # Define callback
    tick_count = [0]
    last_print = [0]
    
    def tick_callback(tick):
        tick_count[0] += 1
        
        # Publish to Kafka if enabled
        if kafka_producer:
            kafka_producer.send({
                'timestamp': tick['timestamp'].isoformat(),
                'symbol': tick['symbol'],
                'price': tick['price'],
                'bid': tick['bid'],
                'ask': tick['ask'],
                'volume': tick['volume'],
                'open': tick['open'],
                'high': tick['high'],
                'low': tick['low'],
                'close': tick['close'],
                'source': 'simulator'
            })
        
        # Print progress
        if tick_count[0] - last_print[0] >= 500:
            print(f"  Ticks: {tick_count[0]}, Time: {tick['timestamp'].strftime('%H:%M:%S')}, "
                  f"Last: {tick['symbol']} @ {tick['price']}")
            last_print[0] = tick_count[0]
    
    # Run simulation
    print("\nStarting simulation...")
    print("Press Ctrl+C to pause\n")
    
    try:
        simulator.run_simulation(tick_callback)
    except KeyboardInterrupt:
        print("\n\nSimulation interrupted by user")
    
    # Cleanup
    if kafka_producer:
        kafka_producer.flush()
        kafka_producer.close()
    
    # Print summary
    status = simulator.get_status()
    print("\n" + "="*80)
    print("SIMULATION COMPLETE")
    print("="*80)
    print(f"Total ticks generated: {status['ticks_generated']}")
    print(f"Progress: {status['progress']:.1f}%")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
