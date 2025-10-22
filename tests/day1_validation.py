"""
Day 1 validation test - Verify complete data pipeline.
"""

import sys
from pathlib import Path
import subprocess
import time
import random

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.adapters.data.historical import HistoricalDataManager
from src.core.market_simulator import MarketSimulator
from src.utils.kafka_helper import KafkaProducerWrapper, KafkaConsumerWrapper
from src.utils.data_validator import DataValidator
from src.utils.logging_config import initialize_logging
import logging


def check_kafka_containers():
    """Check if Kafka containers are running."""
    print("\n1. Checking Kafka containers...")
    result = subprocess.run(['docker', 'ps'], capture_output=True, text=True)
    
    kafka_running = 'kafka' in result.stdout
    zookeeper_running = 'zookeeper' in result.stdout
    
    if kafka_running and zookeeper_running:
        print("   ✓ Kafka and Zookeeper containers are running")
        return True
    else:
        print("   ✗ Kafka containers not running")
        if not kafka_running:
            print("     - Kafka container missing")
        if not zookeeper_running:
            print("     - Zookeeper container missing")
        return False


def check_kafka_topics():
    """Check if required Kafka topics exist."""
    print("\n2. Checking Kafka topics...")
    
    required_topics = ['market.ticks', 'signals', 'orders', 'order_fills', 'positions']
    
    try:
        result = subprocess.run(
            ['docker', 'exec', 
             subprocess.run(['docker', 'ps', '-qf', 'name=kafka'], 
                          capture_output=True, text=True).stdout.strip(),
             'kafka-topics', '--list', '--bootstrap-server', 'localhost:9092'],
            capture_output=True, text=True, timeout=10
        )
        
        existing_topics = result.stdout.strip().split('\n')
        
        all_exist = True
        for topic in required_topics:
            if topic in existing_topics:
                print(f"   ✓ Topic '{topic}' exists")
            else:
                print(f"   ✗ Topic '{topic}' missing")
                all_exist = False
        
        return all_exist
        
    except Exception as e:
        print(f"   ✗ Error checking topics: {e}")
        return False


def test_data_loading():
    """Test loading data from multiple dates."""
    print("\n3. Testing data loading...")
    
    try:
        hdm = HistoricalDataManager('./data')
        stats = hdm.get_statistics()
        
        if not stats['symbols']:
            print("   ✗ No symbols found")
            return False
        
        print(f"   ✓ Found {len(stats['symbols'])} symbols")
        
        # Test loading 5 random dates
        symbol = stats['symbols'][0]
        dates = hdm.get_available_dates(symbol)
        
        if len(dates) < 5:
            print(f"   ✗ Insufficient dates: {len(dates)}")
            return False
        
        print(f"   ✓ Symbol '{symbol}' has {len(dates)} trading days")
        print(f"     Date range: {dates[0]} to {dates[-1]}")
        
        # Sample dates from different periods
        test_dates = [
            dates[0],  # First date
            dates[len(dates)//4],  # 25%
            dates[len(dates)//2],  # 50%
            dates[3*len(dates)//4],  # 75%
            dates[-1]  # Last date
        ]
        
        print(f"\n   Testing data load from 5 dates:")
        for date in test_dates:
            df = hdm.get_data(date, [symbol])
            if df.empty:
                print(f"     ✗ {date}: No data")
                return False
            else:
                print(f"     ✓ {date}: {len(df)} rows")
        
        return True
        
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False


def test_data_validation():
    """Test data validation."""
    print("\n4. Testing data validation...")
    
    try:
        hdm = HistoricalDataManager('./data')
        stats = hdm.get_statistics()
        
        if not stats['symbols']:
            print("   ✗ No symbols found")
            return False
        
        validator = DataValidator()
        symbol = stats['symbols'][0]
        dates = hdm.get_available_dates(symbol)
        
        # Validate 3 random dates
        test_dates = random.sample(dates, min(3, len(dates)))
        
        for date in test_dates:
            df = hdm.get_data(date, [symbol])
            result = validator.validate_day(df, date)
            
            if result['issues']:
                print(f"   ⚠ {date}: {len(result['issues'])} issues found")
            else:
                print(f"   ✓ {date}: Validation passed")
        
        # Generate report
        validator.generate_report()
        print("   ✓ Data quality report generated")
        
        return True
        
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False


def test_simulation():
    """Test running simulation."""
    print("\n5. Testing market simulation...")
    
    try:
        hdm = HistoricalDataManager('./data')
        stats = hdm.get_statistics()
        
        if not stats['symbols']:
            print("   ✗ No symbols found")
            return False
        
        # Use one symbol for quick test
        symbol = stats['symbols'][0]
        dates = hdm.get_available_dates(symbol)
        test_date = dates[len(dates)//2]
        
        print(f"   Simulating {test_date} with {symbol} at 100x speed...")
        
        simulator = MarketSimulator(
            data_adapter=hdm,
            date=test_date,
            symbols=[symbol],
            speed=100.0,
            ticks_per_candle=10
        )
        
        if not simulator.load_data():
            print("   ✗ Failed to load data")
            return False
        
        # Run simulation with callback
        tick_count = [0]
        
        def callback(tick):
            tick_count[0] += 1
        
        start_time = time.time()
        simulator.run_simulation(callback)
        elapsed = time.time() - start_time
        
        status = simulator.get_status()
        
        print(f"   ✓ Generated {status['ticks_generated']} ticks in {elapsed:.2f} seconds")
        
        return True
        
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False


def test_kafka_integration():
    """Test Kafka producer and consumer."""
    print("\n6. Testing Kafka integration...")
    
    try:
        # Test producer
        print("   Testing Kafka producer...")
        producer = KafkaProducerWrapper(topic='market.ticks')
        
        # Send test messages
        for i in range(10):
            producer.send({
                'timestamp': time.time(),
                'symbol': 'TEST',
                'price': 100.0 + i,
                'volume': 100,
                'source': 'test'
            })
        
        producer.flush()
        print("   ✓ Sent 10 test messages")
        
        # Wait a bit
        time.sleep(2)
        
        # Test consumer
        print("   Testing Kafka consumer...")
        consumer = KafkaConsumerWrapper(
            topic='market.ticks',
            group_id='test-validation',
            auto_offset_reset='earliest'
        )
        
        received = 0
        for message in consumer.consume():
            received += 1
            if received >= 10:
                break
        
        consumer.close()
        producer.close()
        
        print(f"   ✓ Received {received} messages")
        
        return received >= 10
        
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False


def check_logs():
    """Check if logs are being created."""
    print("\n7. Checking logs...")
    
    log_dir = Path('./logs')
    if not log_dir.exists():
        print("   ✗ Log directory not found")
        return False
    
    log_files = list(log_dir.glob('velox_*.log'))
    
    if not log_files:
        print("   ✗ No log files found")
        return False
    
    latest_log = max(log_files, key=lambda p: p.stat().st_mtime)
    
    # Read last 20 lines
    with open(latest_log, 'r') as f:
        lines = f.readlines()
        last_lines = lines[-20:] if len(lines) > 20 else lines
    
    print(f"   ✓ Log file found: {latest_log.name}")
    print(f"   ✓ Log has {len(lines)} entries")
    print("\n   Last 5 log entries:")
    for line in last_lines[-5:]:
        print(f"     {line.strip()}")
    
    return True


def main():
    """Run Day 1 validation."""
    initialize_logging(log_level=logging.INFO)
    
    print("\n" + "="*80)
    print("DAY 1 VALIDATION TEST")
    print("="*80)
    
    results = {
        'Kafka Containers': check_kafka_containers(),
        'Kafka Topics': check_kafka_topics(),
        'Data Loading': test_data_loading(),
        'Data Validation': test_data_validation(),
        'Market Simulation': test_simulation(),
        'Kafka Integration': test_kafka_integration(),
        'Logging': check_logs()
    }
    
    # Summary
    print("\n" + "="*80)
    print("VALIDATION SUMMARY")
    print("="*80)
    
    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{test_name:.<50} {status}")
    
    total = len(results)
    passed = sum(results.values())
    
    print("="*80)
    print(f"Total: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    print("="*80)
    
    if passed == total:
        print("\n🎉 All Day 1 validations passed! Ready for Day 2.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please fix before proceeding to Day 2.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
