"""
Emergency Exit Manager - Exits all positions when loss limit is breached
Monitors daily P&L and automatically closes all positions on breach
"""
import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, date
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DailyPnL:
    """Daily P&L tracking"""
    date: str
    realized_pnl: float
    unrealized_pnl: float
    total_pnl: float
    trades_closed: int
    max_drawdown: float


class EmergencyExitManager:
    """
    Emergency exit manager for loss limit breach

    Features:
    - Monitors daily P&L in real-time
    - Triggers emergency exit when loss limit breached
    - Closes all open positions immediately
    - Prevents new positions until next trading day
    - Comprehensive logging and alerts
    """

    def __init__(self,
                 max_daily_loss: float,
                 max_daily_loss_pct: Optional[float] = None,
                 initial_capital: float = 100000.0):
        """
        Initialize emergency exit manager

        Args:
            max_daily_loss: Maximum daily loss in absolute amount
            max_daily_loss_pct: Maximum daily loss in percentage (optional)
            initial_capital: Initial trading capital
        """
        self.max_daily_loss = abs(max_daily_loss)  # Ensure positive
        self.max_daily_loss_pct = max_daily_loss_pct
        self.initial_capital = initial_capital

        # State
        self.emergency_exit_triggered = False
        self.trading_disabled = False
        self.emergency_exit_time: Optional[datetime] = None

        # P&L tracking
        self.daily_pnl: Dict[str, DailyPnL] = {}
        self.current_date = date.today().isoformat()

        # Callbacks
        self.on_emergency_exit_callback: Optional[Callable] = None
        self.on_position_close_callback: Optional[Callable] = None

        # Initialize today's P&L
        self._initialize_daily_pnl()

        logger.info(f"Emergency Exit Manager initialized: max_loss={self.max_daily_loss}, "
                   f"max_loss_pct={self.max_daily_loss_pct}")

    def _initialize_daily_pnl(self):
        """Initialize P&L tracking for current day"""
        today = date.today().isoformat()

        if today not in self.daily_pnl:
            self.daily_pnl[today] = DailyPnL(
                date=today,
                realized_pnl=0.0,
                unrealized_pnl=0.0,
                total_pnl=0.0,
                trades_closed=0,
                max_drawdown=0.0
            )
            logger.info(f"Initialized P&L tracking for {today}")

    def update_pnl(self, realized_pnl: float, unrealized_pnl: float) -> bool:
        """
        Update daily P&L and check for breach

        Args:
            realized_pnl: Realized P&L from closed trades
            unrealized_pnl: Unrealized P&L from open positions

        Returns:
            True if emergency exit triggered
        """
        # Check if we need to reset for new day
        today = date.today().isoformat()
        if today != self.current_date:
            self._reset_for_new_day(today)

        # Update P&L
        daily_pnl = self.daily_pnl[today]
        daily_pnl.realized_pnl = realized_pnl
        daily_pnl.unrealized_pnl = unrealized_pnl
        daily_pnl.total_pnl = realized_pnl + unrealized_pnl

        # Update max drawdown
        if daily_pnl.total_pnl < daily_pnl.max_drawdown:
            daily_pnl.max_drawdown = daily_pnl.total_pnl

        # Check for breach
        breach_triggered = self._check_loss_breach(daily_pnl)

        if breach_triggered and not self.emergency_exit_triggered:
            self._trigger_emergency_exit(daily_pnl)
            return True

        return False

    def _check_loss_breach(self, daily_pnl: DailyPnL) -> bool:
        """
        Check if loss limit is breached

        Args:
            daily_pnl: Daily P&L data

        Returns:
            True if breach detected
        """
        # Already triggered
        if self.emergency_exit_triggered:
            return False

        # Check absolute loss
        if daily_pnl.total_pnl <= -self.max_daily_loss:
            logger.warning(f"Daily loss limit breached: {daily_pnl.total_pnl:.2f} <= -{self.max_daily_loss:.2f}")
            return True

        # Check percentage loss (if configured)
        if self.max_daily_loss_pct:
            loss_pct = (abs(daily_pnl.total_pnl) / self.initial_capital) * 100
            if loss_pct >= self.max_daily_loss_pct:
                logger.warning(f"Daily loss % limit breached: {loss_pct:.2f}% >= {self.max_daily_loss_pct:.2f}%")
                return True

        return False

    def _trigger_emergency_exit(self, daily_pnl: DailyPnL):
        """
        Trigger emergency exit

        Args:
            daily_pnl: Daily P&L data
        """
        self.emergency_exit_triggered = True
        self.trading_disabled = True
        self.emergency_exit_time = datetime.now()

        logger.critical(
            f"🚨 EMERGENCY EXIT TRIGGERED 🚨\n"
            f"Date: {daily_pnl.date}\n"
            f"Total P&L: {daily_pnl.total_pnl:.2f}\n"
            f"Max Daily Loss: {self.max_daily_loss:.2f}\n"
            f"Realized P&L: {daily_pnl.realized_pnl:.2f}\n"
            f"Unrealized P&L: {daily_pnl.unrealized_pnl:.2f}\n"
            f"Trigger Time: {self.emergency_exit_time}"
        )

        # Execute callback if registered
        if self.on_emergency_exit_callback:
            try:
                self.on_emergency_exit_callback(daily_pnl)
            except Exception as e:
                logger.error(f"Error executing emergency exit callback: {e}")

    def close_all_positions(self, positions: List[Dict[str, Any]]) -> List[str]:
        """
        Close all open positions (emergency exit)

        Args:
            positions: List of open positions

        Returns:
            List of closed position IDs
        """
        if not positions:
            logger.info("No positions to close")
            return []

        closed_positions = []

        logger.warning(f"Closing {len(positions)} positions (EMERGENCY EXIT)")

        for position in positions:
            try:
                position_id = f"{position.get('strategy_id', 'unknown')}:{position.get('symbol', 'unknown')}"

                # Execute close callback
                if self.on_position_close_callback:
                    self.on_position_close_callback(position, "EMERGENCY_EXIT_LOSS_LIMIT")

                closed_positions.append(position_id)
                logger.info(f"Closed position: {position_id}")

            except Exception as e:
                logger.error(f"Error closing position {position}: {e}")

        logger.warning(f"Emergency exit completed: closed {len(closed_positions)} positions")

        return closed_positions

    def can_trade(self) -> tuple[bool, str]:
        """
        Check if trading is allowed

        Returns:
            (can_trade, reason) - Boolean and reason message
        """
        if self.trading_disabled:
            return False, f"Trading disabled due to emergency exit at {self.emergency_exit_time}"

        if self.emergency_exit_triggered:
            return False, "Emergency exit triggered - trading disabled for today"

        return True, "OK"

    def can_open_new_position(self, estimated_loss: float = 0.0) -> tuple[bool, str]:
        """
        Check if new position can be opened

        Args:
            estimated_loss: Estimated potential loss for the position

        Returns:
            (can_open, reason) - Boolean and reason message
        """
        # Check if trading is disabled
        can_trade, reason = self.can_trade()
        if not can_trade:
            return False, reason

        # Check if position would push us over limit
        today = date.today().isoformat()
        daily_pnl = self.daily_pnl.get(today)

        if daily_pnl:
            potential_pnl = daily_pnl.total_pnl - abs(estimated_loss)

            if potential_pnl <= -self.max_daily_loss:
                return False, f"Position would breach loss limit: current={daily_pnl.total_pnl:.2f}, potential={potential_pnl:.2f}"

        return True, "OK"

    def record_trade_close(self, pnl: float):
        """
        Record a closed trade

        Args:
            pnl: Trade P&L
        """
        today = date.today().isoformat()

        if today in self.daily_pnl:
            self.daily_pnl[today].trades_closed += 1
            logger.debug(f"Recorded trade close: pnl={pnl:.2f}, total_trades={self.daily_pnl[today].trades_closed}")

    def _reset_for_new_day(self, new_date: str):
        """
        Reset for new trading day

        Args:
            new_date: New date string
        """
        logger.info(f"Resetting emergency exit manager for new day: {new_date}")

        # Reset state
        self.current_date = new_date
        self.emergency_exit_triggered = False
        self.trading_disabled = False
        self.emergency_exit_time = None

        # Initialize new daily P&L
        self._initialize_daily_pnl()

    def get_daily_summary(self) -> Dict[str, Any]:
        """
        Get daily summary

        Returns:
            Summary dictionary
        """
        today = date.today().isoformat()
        daily_pnl = self.daily_pnl.get(today)

        if not daily_pnl:
            return {
                'date': today,
                'no_data': True
            }

        loss_pct = (abs(daily_pnl.total_pnl) / self.initial_capital) * 100 if self.initial_capital > 0 else 0
        remaining_loss_buffer = self.max_daily_loss - abs(daily_pnl.total_pnl)

        return {
            'date': daily_pnl.date,
            'realized_pnl': daily_pnl.realized_pnl,
            'unrealized_pnl': daily_pnl.unrealized_pnl,
            'total_pnl': daily_pnl.total_pnl,
            'max_drawdown': daily_pnl.max_drawdown,
            'trades_closed': daily_pnl.trades_closed,
            'loss_pct': loss_pct,
            'max_daily_loss': self.max_daily_loss,
            'max_daily_loss_pct': self.max_daily_loss_pct,
            'remaining_loss_buffer': remaining_loss_buffer,
            'emergency_exit_triggered': self.emergency_exit_triggered,
            'trading_disabled': self.trading_disabled,
            'emergency_exit_time': self.emergency_exit_time.isoformat() if self.emergency_exit_time else None
        }

    def set_emergency_exit_callback(self, callback: Callable):
        """Set callback to execute on emergency exit"""
        self.on_emergency_exit_callback = callback
        logger.info("Emergency exit callback registered")

    def set_position_close_callback(self, callback: Callable):
        """Set callback to execute when closing positions"""
        self.on_position_close_callback = callback
        logger.info("Position close callback registered")

    def get_risk_status(self) -> Dict[str, Any]:
        """
        Get current risk status

        Returns:
            Risk status dictionary
        """
        today = date.today().isoformat()
        daily_pnl = self.daily_pnl.get(today)

        if not daily_pnl:
            return {'status': 'unknown', 'message': 'No P&L data'}

        loss_pct = (abs(daily_pnl.total_pnl) / self.initial_capital) * 100
        buffer_pct = ((self.max_daily_loss - abs(daily_pnl.total_pnl)) / self.max_daily_loss) * 100

        # Determine risk level
        if self.emergency_exit_triggered:
            status = 'EMERGENCY_EXIT'
            color = 'red'
        elif buffer_pct < 10:
            status = 'CRITICAL'
            color = 'red'
        elif buffer_pct < 25:
            status = 'HIGH'
            color = 'orange'
        elif buffer_pct < 50:
            status = 'MODERATE'
            color = 'yellow'
        else:
            status = 'SAFE'
            color = 'green'

        return {
            'status': status,
            'color': color,
            'total_pnl': daily_pnl.total_pnl,
            'loss_pct': loss_pct,
            'buffer_pct': buffer_pct,
            'max_daily_loss': self.max_daily_loss,
            'trading_disabled': self.trading_disabled
        }
