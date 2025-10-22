"""
Logging configuration for VELOX trading system.
Provides comprehensive logging with component-level loggers and colored console output.
"""

import logging
import os
from datetime import datetime
from pathlib import Path


class ColoredFormatter(logging.Formatter):
    """Custom formatter with color coding for console output."""
    
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[37m',      # White
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)


class VeloxLogger:
    """Centralized logging manager for VELOX system."""
    
    def __init__(self, log_dir='logs', log_level=logging.INFO):
        """
        Initialize logging system.
        
        Args:
            log_dir: Directory to store log files
            log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR)
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.log_level = log_level
        
        # Create log file with date
        log_filename = f"velox_{datetime.now().strftime('%Y%m%d')}.log"
        self.log_file = self.log_dir / log_filename
        
        # Setup root logger
        self._setup_root_logger()
        
        # Component loggers
        self.component_loggers = {}
    
    def _setup_root_logger(self):
        """Configure root logger with file and console handlers."""
        root_logger = logging.getLogger()
        root_logger.setLevel(self.log_level)
        
        # Remove existing handlers
        root_logger.handlers = []
        
        # File handler - detailed format with milliseconds
        file_formatter = logging.Formatter(
            '[%(asctime)s.%(msecs)03d] [%(levelname)s] [%(name)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler = logging.FileHandler(self.log_file)
        file_handler.setLevel(self.log_level)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
        
        # Console handler - colored output
        console_formatter = ColoredFormatter(
            '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler = logging.StreamHandler()
        console_handler.setLevel(self.log_level)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
    
    def get_logger(self, component_name, strategy_id=None):
        """
        Get or create a logger for a specific component.
        
        Args:
            component_name: Name of component (simulator, strategy, risk, order, position)
            strategy_id: Optional strategy identifier
            
        Returns:
            logging.Logger instance
        """
        logger_name = component_name
        if strategy_id:
            logger_name = f"{component_name}.{strategy_id}"
        
        if logger_name not in self.component_loggers:
            logger = logging.getLogger(logger_name)
            self.component_loggers[logger_name] = logger
        
        return self.component_loggers[logger_name]
    
    def set_level(self, level):
        """Change log level dynamically."""
        self.log_level = level
        logging.getLogger().setLevel(level)
        for handler in logging.getLogger().handlers:
            handler.setLevel(level)


# Global logger instance
_velox_logger = None


def initialize_logging(log_dir='logs', log_level=logging.INFO):
    """
    Initialize the global logging system.
    
    Args:
        log_dir: Directory for log files
        log_level: Minimum log level
        
    Returns:
        VeloxLogger instance
    """
    global _velox_logger
    _velox_logger = VeloxLogger(log_dir, log_level)
    return _velox_logger


def get_logger(component_name, strategy_id=None):
    """
    Get a logger for a component.
    
    Args:
        component_name: Component name
        strategy_id: Optional strategy ID
        
    Returns:
        logging.Logger instance
    """
    global _velox_logger
    if _velox_logger is None:
        _velox_logger = initialize_logging()
    return _velox_logger.get_logger(component_name, strategy_id)


if __name__ == "__main__":
    # Test logging system
    initialize_logging(log_level=logging.DEBUG)
    
    # Test different components
    sim_logger = get_logger('simulator')
    strategy_logger = get_logger('strategy', 'rsi_aggressive')
    risk_logger = get_logger('risk')
    order_logger = get_logger('order')
    position_logger = get_logger('position')
    
    # Test different log levels
    sim_logger.debug("Simulator initialized with 5 symbols")
    sim_logger.info("Starting simulation for 2020-09-15")
    strategy_logger.info("RSI=28.5 < 30 → BUY signal generated for RELIANCE @ 2450.50")
    risk_logger.warning("Strategy position limit reached: 3/3")
    order_logger.info("Order placed: BUY RELIANCE 10 @ 2450.50")
    position_logger.info("Position opened: RELIANCE entry=2450.50")
    risk_logger.error("Daily loss limit exceeded: -3.2%")
    
    print(f"\nLog file created at: {_velox_logger.log_file}")
