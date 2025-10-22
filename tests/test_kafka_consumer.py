"""
Test Kafka consumer - consumes messages from market.ticks topic.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.kafka_helper import KafkaConsumerWrapper
from src.utils.logging_config import initialize_logging
import logging

def main():
    """Test Kafka consumer."""
    initialize_logging(log_level=logging.INFO)
    
    print("\n=== Kafka Consumer Test ===")
    print("Consuming from market.ticks topic...")
    print("Press Ctrl+C to stop\n")
    
    try:
        consumer = KafkaConsumerWrapper(
            topic='market.ticks',
            group_id='test-consumer',
            auto_offset_reset='earliest'
        )
        
        count = 0
        for message in consumer.consume():
            count += 1
            
            # Print first 20 messages in detail
            if count <= 20:
                print(f"\nMessage {count}:")
                print(f"  Symbol: {message.get('symbol')}")
                print(f"  Time: {message.get('timestamp')}")
                print(f"  Price: {message.get('price')}")
                print(f"  Bid: {message.get('bid')}, Ask: {message.get('ask')}")
                print(f"  Volume: {message.get('volume')}")
            elif count % 100 == 0:
                # Print summary every 100 messages
                print(f"Received {count} messages... (last: {message.get('symbol')} @ {message.get('price')})")
        
        consumer.close()
        
    except KeyboardInterrupt:
        print(f"\n\nStopped. Total messages received: {count}")
    except Exception as e:
        print(f"\nError: {e}")

if __name__ == "__main__":
    main()
