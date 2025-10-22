"""
Advanced Structured Logging System for VELOX.

Multi-destination logging:
1. Console (colored, human-readable)
2. JSON File (structured, parseable)
3. Text File (human-readable, rotated)

Features:
- Colored console output
- JSON structured logs
- Automatic file rotation
- Context-aware logging
- ELK stack compatible
"""

import logging
import json
import sys
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler

try:
    import colorlog
    COLORLOG_AVAILABLE = True
except ImportError:
    COLORLOG_AVAILABLE = False


class JSONFormatter(logging.Formatter):
    """Format logs as JSON for structured parsing."""
    
    def format(self, record):
        """Format log record as JSON."""
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add context if available
        if hasattr(record, 'context'):
            log_data['context'] = record.context
        
        # Add exception info if available
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


class StructuredLogger:
    """
    Advanced logger with multiple output destinations.
    
    Features:
    - Colored console output
    - JSON structured logs (for parsing/ELK)
    - Rotated text logs (for human reading)
    - Context-aware logging
    """
    
    def __init__(self, name: str, log_dir: str = 'logs', level=logging.INFO):
        """
        Initialize structured logger.
        
        Args:
            name: Logger name
            log_dir: Directory for log files
            level: Logging level
        """
        self.name = name
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        self._setup_handlers(level)
    
    def _setup_handlers(self, level):
        """Setup multiple log handlers."""
        # Clear existing handlers
        self.logger.handlers = []
        
        # 1. Console Handler (colored, human-readable)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        
        if COLORLOG_AVAILABLE:
            console_format = colorlog.ColoredFormatter(
                '%(log_color)s[%(asctime)s] [%(levelname)-8s] [%(name)-20s]%(reset)s %(message)s',
                datefmt='%H:%M:%S',
                log_colors={
                    'DEBUG': 'cyan',
                    'INFO': 'white',
                    'WARNING': 'yellow',
                    'ERROR': 'red',
                    'CRITICAL': 'bold_red',
                }
            )
            console_handler.setFormatter(console_format)
        else:
            console_format = logging.Formatter(
                '[%(asctime)s] [%(levelname)-8s] [%(name)-20s] %(message)s',
                datefmt='%H:%M:%S'
            )
            console_handler.setFormatter(console_format)
        
        self.logger.addHandler(console_handler)
        
        # 2. JSON File Handler (structured, daily rotation)
        json_file = self.log_dir / f'{self.name}_json.log'
        json_handler = TimedRotatingFileHandler(
            json_file, when='midnight', interval=1, backupCount=30
        )
        json_handler.setLevel(logging.DEBUG)
        json_handler.setFormatter(JSONFormatter())
        self.logger.addHandler(json_handler)
        
        # 3. Text File Handler (human-readable, size rotation)
        text_file = self.log_dir / f'{self.name}.log'
        text_handler = RotatingFileHandler(
            text_file, maxBytes=50*1024*1024, backupCount=10  # 50MB per file
        )
        text_handler.setLevel(logging.DEBUG)
        text_format = logging.Formatter(
            '[%(asctime)s] [%(levelname)-8s] [%(name)-20s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        text_handler.setFormatter(text_format)
        self.logger.addHandler(text_handler)
    
    def debug(self, message: str, **context):
        """Log debug message with context."""
        self.logger.debug(message, extra={'context': context})
    
    def info(self, message: str, **context):
        """Log info message with context."""
        self.logger.info(message, extra={'context': context})
    
    def warning(self, message: str, **context):
        """Log warning message with context."""
        self.logger.warning(message, extra={'context': context})
    
    def error(self, message: str, **context):
        """Log error message with context."""
        self.logger.error(message, extra={'context': context}, exc_info=True)
    
    def critical(self, message: str, **context):
        """Log critical message with context."""
        self.logger.critical(message, extra={'context': context}, exc_info=True)


# Factory function for easy logger creation
def get_structured_logger(name: str, level=logging.INFO) -> StructuredLogger:
    """
    Create a structured logger.
    
    Args:
        name: Logger name
        level: Logging level
        
    Returns:
        StructuredLogger instance
    """
    return StructuredLogger(name, level=level)


# Pre-configured loggers for components
simulator_log = get_structured_logger('simulator')
strategy_log = get_structured_logger('strategy')
risk_log = get_structured_logger('risk')
order_log = get_structured_logger('order')
position_log = get_structured_logger('position')
database_log = get_structured_logger('database')
dashboard_log = get_structured_logger('dashboard')


# Convenience function for backward compatibility
def get_logger(name: str) -> logging.Logger:
    """
    Get a standard Python logger (for backward compatibility).
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)
