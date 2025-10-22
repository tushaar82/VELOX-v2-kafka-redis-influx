"""
Broker factory for creating broker adapters.
"""

from typing import Dict
from .base import BrokerAdapter
from .simulated import SimulatedBrokerAdapter
from ...utils.logging_config import get_logger


class BrokerFactory:
    """Factory for creating broker adapters."""
    
    _brokers = {
        'simulated': SimulatedBrokerAdapter,
        # Add more brokers here
        # 'zerodha': ZerodhaBrokerAdapter,
        # 'upstox': UpstoxBrokerAdapter,
    }
    
    @classmethod
    def create(cls, broker_type: str, config: Dict) -> BrokerAdapter:
        """
        Create a broker adapter.
        
        Args:
            broker_type: Type of broker ('simulated', 'zerodha', etc.)
            config: Configuration dictionary
            
        Returns:
            BrokerAdapter instance
            
        Raises:
            ValueError: If broker type not supported
        """
        logger = get_logger('broker_factory')
        
        if broker_type not in cls._brokers:
            raise ValueError(
                f"Unsupported broker type: {broker_type}. "
                f"Available: {list(cls._brokers.keys())}"
            )
        
        broker_class = cls._brokers[broker_type]
        broker = broker_class(**config)
        
        logger.info(f"Created broker: {broker_type}")
        
        return broker
    
    @classmethod
    def register_broker(cls, name: str, broker_class: type):
        """
        Register a new broker type.
        
        Args:
            name: Broker name
            broker_class: Broker class (must inherit from BrokerAdapter)
        """
        if not issubclass(broker_class, BrokerAdapter):
            raise TypeError(f"{broker_class} must inherit from BrokerAdapter")
        
        cls._brokers[name] = broker_class
    
    @classmethod
    def list_brokers(cls) -> list:
        """Get list of available broker types."""
        return list(cls._brokers.keys())


if __name__ == "__main__":
    # Test factory
    from ...utils.logging_config import initialize_logging
    import logging
    
    initialize_logging(log_level=logging.INFO)
    
    print("\n=== Testing Broker Factory ===\n")
    
    # List available brokers
    print(f"Available brokers: {BrokerFactory.list_brokers()}")
    
    # Create simulated broker
    broker = BrokerFactory.create('simulated', {'initial_capital': 50000})
    broker.connect()
    
    print(f"\nBroker created: {type(broker).__name__}")
    print(f"Connected: {broker.is_connected()}")
    
    account = broker.get_account_info()
    print(f"Capital: {account['capital']}")
    
    print("\n✓ Factory test complete")
