#!/bin/bash

# Script to create Kafka topics for VELOX trading system

echo "Creating Kafka topics..."

# Wait for Kafka to be ready
sleep 5

# Get Kafka container ID
KAFKA_CONTAINER=$(docker ps -qf "name=kafka")

if [ -z "$KAFKA_CONTAINER" ]; then
    echo "Error: Kafka container not found"
    exit 1
fi

# Create topics
topics=("market.ticks" "signals" "orders" "order_fills" "positions")

for topic in "${topics[@]}"; do
    echo "Creating topic: $topic"
    docker exec $KAFKA_CONTAINER kafka-topics \
        --create --topic $topic \
        --bootstrap-server localhost:9092 \
        --partitions 1 \
        --replication-factor 1 \
        --if-not-exists
done

echo ""
echo "Listing all topics:"
docker exec $KAFKA_CONTAINER kafka-topics \
    --list --bootstrap-server localhost:9092

echo ""
echo "✓ Kafka topics created successfully"
