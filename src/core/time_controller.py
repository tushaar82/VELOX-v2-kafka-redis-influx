"""
Time-Based Controller.
Manages time-based actions like auto square-off at 3:15 PM.
"""

from datetime import datetime, time
from typing import Optional, Callable

from ..utils.logging_config import get_logger


class TimeController:
    """Controls time-based actions during simulation."""
    
    def __init__(self, square_off_time: str = "15:15:00", warning_time: str = "15:00:00"):
        """
        Initialize time controller.
        
        Args:
            square_off_time: Time to square off all positions (HH:MM:SS)
            warning_time: Time to warn about upcoming square-off (HH:MM:SS)
        """
        self.square_off_time = self._parse_time(square_off_time)
        self.warning_time = self._parse_time(warning_time)
        
        self.warning_issued = False
        self.square_off_executed = False
        self.new_entries_blocked = False
        
        self.logger = get_logger('time_controller')
        
        self.logger.info(
            f"TimeController initialized: warning={warning_time}, "
            f"square_off={square_off_time}"
        )
    
    def _parse_time(self, time_str: str) -> time:
        """Parse time string to time object."""
        h, m, s = map(int, time_str.split(':'))
        return time(h, m, s)
    
    def check_time(self, current_time: datetime, 
                   on_warning: Optional[Callable] = None,
                   on_square_off: Optional[Callable] = None) -> dict:
        """
        Check current time and trigger actions.
        
        Args:
            current_time: Current simulation time
            on_warning: Callback for warning event
            on_square_off: Callback for square-off event
            
        Returns:
            Dictionary with actions taken
        """
        current_time_only = current_time.time()
        
        actions = {
            'warning_issued': False,
            'square_off_executed': False,
            'new_entries_blocked': False
        }
        
        # Check warning time
        if not self.warning_issued and current_time_only >= self.warning_time:
            self.warning_issued = True
            self.new_entries_blocked = True
            actions['warning_issued'] = True
            actions['new_entries_blocked'] = True
            
            self.logger.warning(
                f"⚠️  WARNING: {(self.square_off_time.hour * 60 + self.square_off_time.minute) - (current_time_only.hour * 60 + current_time_only.minute)} "
                f"minutes to square-off. New entries blocked."
            )
            
            if on_warning:
                on_warning()
        
        # Check square-off time
        if not self.square_off_executed and current_time_only >= self.square_off_time:
            self.square_off_executed = True
            actions['square_off_executed'] = True
            
            self.logger.warning(
                f"🔔 SQUARE-OFF TIME REACHED: {self.square_off_time}. "
                f"Closing all positions."
            )
            
            if on_square_off:
                on_square_off()
        
        return actions
    
    def is_trading_allowed(self) -> bool:
        """
        Check if new trades are allowed.
        
        Returns:
            True if trading allowed, False if blocked
        """
        return not self.new_entries_blocked
    
    def reset(self):
        """Reset controller for new day."""
        self.warning_issued = False
        self.square_off_executed = False
        self.new_entries_blocked = False
        self.logger.info("TimeController reset for new day")
    
    def get_status(self) -> dict:
        """
        Get controller status.
        
        Returns:
            Status dictionary
        """
        return {
            'warning_issued': self.warning_issued,
            'square_off_executed': self.square_off_executed,
            'new_entries_blocked': self.new_entries_blocked,
            'trading_allowed': self.is_trading_allowed()
        }


if __name__ == "__main__":
    # Test time controller
    from ..utils.logging_config import initialize_logging
    import logging
    
    initialize_logging(log_level=logging.INFO)
    
    print("\n=== Testing Time Controller ===\n")
    
    controller = TimeController(square_off_time="15:15:00", warning_time="15:00:00")
    
    # Test times
    test_times = [
        datetime(2024, 1, 1, 14, 30, 0),  # Before warning
        datetime(2024, 1, 1, 15, 0, 0),   # Warning time
        datetime(2024, 1, 1, 15, 10, 0),  # After warning
        datetime(2024, 1, 1, 15, 15, 0),  # Square-off time
        datetime(2024, 1, 1, 15, 20, 0),  # After square-off
    ]
    
    for test_time in test_times:
        print(f"\nTime: {test_time.strftime('%H:%M:%S')}")
        
        actions = controller.check_time(
            test_time,
            on_warning=lambda: print("  → Warning callback triggered"),
            on_square_off=lambda: print("  → Square-off callback triggered")
        )
        
        print(f"  Trading allowed: {controller.is_trading_allowed()}")
        print(f"  Actions: {actions}")
    
    print("\n✓ Time controller test complete")
