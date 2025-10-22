"""
Kafka producer and consumer wrappers with JSON serialization.
"""

import json
from typing import Dict, Optional, Generator
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError

from .logging_config import get_logger


class KafkaProducerWrapper:
    """Wrapper for Kafka producer with JSON serialization."""
    
    def __init__(self, bootstrap_servers: str = 'localhost:9092', topic: str = None):
        """
        Initialize Kafka producer.
        
        Args:
            bootstrap_servers: Kafka broker address
            topic: Default topic to publish to
        """
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.logger = get_logger('kafka_producer')
        
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                acks='all',
                retries=3
            )
            self.logger.info(f"KafkaProducer connected to {bootstrap_servers}")
        except Exception as e:
            self.logger.error(f"Failed to connect to Kafka: {e}")
            raise
    
    def send(self, message: Dict, topic: Optional[str] = None, key: Optional[str] = None):
        """
        Send a message to Kafka.
        
        Args:
            message: Dictionary to send (will be JSON serialized)
            topic: Topic to send to (uses default if not specified)
            key: Optional message key
        """
        target_topic = topic or self.topic
        
        if not target_topic:
            self.logger.error("No topic specified")
            return
        
        try:
            future = self.producer.send(target_topic, value=message, key=key)
            # Don't wait for confirmation to maintain high throughput
            # future.get(timeout=10)  # Uncomment for synchronous sends
        except KafkaError as e:
            self.logger.error(f"Failed to send message to {target_topic}: {e}")
    
    def flush(self):
        """Ensure all messages are sent."""
        try:
            self.producer.flush()
            self.logger.debug("Producer flushed")
        except Exception as e:
            self.logger.error(f"Error flushing producer: {e}")
    
    def close(self):
        """Close the producer connection."""
        try:
            self.producer.close()
            self.logger.info("KafkaProducer closed")
        except Exception as e:
            self.logger.error(f"Error closing producer: {e}")


class KafkaConsumerWrapper:
    """Wrapper for Kafka consumer with JSON deserialization."""
    
    def __init__(self, bootstrap_servers: str = 'localhost:9092', 
                 topic: str = None, group_id: str = 'velox-consumer',
                 auto_offset_reset: str = 'earliest'):
        """
        Initialize Kafka consumer.
        
        Args:
            bootstrap_servers: Kafka broker address
            topic: Topic to consume from
            group_id: Consumer group ID
            auto_offset_reset: Where to start reading ('earliest' or 'latest')
        """
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.group_id = group_id
        self.logger = get_logger('kafka_consumer')
        
        try:
            self.consumer = KafkaConsumer(
                topic,
                bootstrap_servers=bootstrap_servers,
                group_id=group_id,
                auto_offset_reset=auto_offset_reset,
                enable_auto_commit=True,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                key_deserializer=lambda k: k.decode('utf-8') if k else None
            )
            self.logger.info(f"KafkaConsumer connected to {bootstrap_servers}, topic={topic}")
        except Exception as e:
            self.logger.error(f"Failed to connect to Kafka: {e}")
            raise
    
    def consume(self, timeout_ms: int = 1000) -> Generator[Dict, None, None]:
        """
        Consume messages from Kafka.
        
        Args:
            timeout_ms: Timeout for polling
            
        Yields:
            Deserialized message dictionaries
        """
        try:
            for message in self.consumer:
                yield message.value
        except KeyboardInterrupt:
            self.logger.info("Consumer interrupted")
        except Exception as e:
            self.logger.error(f"Error consuming messages: {e}")
    
    def consume_batch(self, max_records: int = 100, timeout_ms: int = 1000):
        """
        Consume a batch of messages.
        
        Args:
            max_records: Maximum number of records to fetch
            timeout_ms: Timeout for polling
            
        Returns:
            List of messages
        """
        messages = []
        try:
            records = self.consumer.poll(timeout_ms=timeout_ms, max_records=max_records)
            for topic_partition, msgs in records.items():
                for msg in msgs:
                    messages.append(msg.value)
        except Exception as e:
            self.logger.error(f"Error consuming batch: {e}")
        
        return messages
    
    def close(self):
        """Close the consumer connection."""
        try:
            self.consumer.close()
            self.logger.info("KafkaConsumer closed")
        except Exception as e:
            self.logger.error(f"Error closing consumer: {e}")


if __name__ == "__main__":
    # Test Kafka connectivity
    from .logging_config import initialize_logging
    import logging
    import time
    
    initialize_logging(log_level=logging.INFO)
    
    print("\n=== Testing Kafka Connection ===")
    
    # Test producer
    try:
        producer = KafkaProducerWrapper(topic='test.topic')
        
        # Send test messages
        for i in range(5):
            message = {
                'id': i,
                'timestamp': time.time(),
                'data': f'Test message {i}'
            }
            producer.send(message)
            print(f"Sent: {message}")
        
        producer.flush()
        producer.close()
        
        print("\n✓ Producer test passed")
        
    except Exception as e:
        print(f"\n✗ Producer test failed: {e}")
    
    # Test consumer
    try:
        print("\nTesting consumer (will read 5 messages)...")
        consumer = KafkaConsumerWrapper(topic='test.topic', group_id='test-group')
        
        count = 0
        for message in consumer.consume():
            print(f"Received: {message}")
            count += 1
            if count >= 5:
                break
        
        consumer.close()
        
        print("\n✓ Consumer test passed")
        
    except Exception as e:
        print(f"\n✗ Consumer test failed: {e}")
