"""
Risk Manager - Enhanced with deduplication and emergency exit.
Validates signals and enforces risk limits.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass

from ..utils.logging_config import get_logger
from .order_deduplicator import OrderDeduplicator
from .emergency_exit_manager import EmergencyExitManager


@dataclass
class RiskCheckResult:
    """Result of risk check."""
    approved: bool
    reason: Optional[str] = None
    adjusted_quantity: Optional[int] = None


class RiskManager:
    """Manages risk and validates trading signals."""
    
    def __init__(self, config: Dict, data_manager=None, redis_client=None):
        """
        Initialize risk manager with enhanced safety features.

        Args:
            config: Risk configuration with keys:
                - max_position_size: Maximum value per position
                - max_positions_per_strategy: Max positions per strategy
                - max_total_positions: Max total positions across all strategies
                - max_daily_loss: Maximum daily loss in absolute value
                - max_daily_loss_pct: Maximum daily loss as percentage
                - initial_capital: Initial capital
                - fixed_lot_size: Fixed lot size per trade (optional)
                - enable_deduplication: Enable order deduplication (default True)
            data_manager: Optional DataManager for database logging
            redis_client: Optional Redis client for deduplication
        """
        self.max_position_size = config.get('max_position_size', 10000)
        self.max_positions_per_strategy = config.get('max_positions_per_strategy', 3)
        self.max_total_positions = config.get('max_total_positions', 5)
        self.max_daily_loss = config.get('max_daily_loss', 5000)
        self.max_daily_loss_pct = config.get('max_daily_loss_pct', 0.05)
        self.initial_capital = config.get('initial_capital', 100000)
        self.fixed_lot_size = config.get('fixed_lot_size', None)
        self.enable_deduplication = config.get('enable_deduplication', True)

        # Daily tracking
        self.daily_pnl = 0.0
        self.daily_trades = 0

        # Database manager
        self.data_manager = data_manager

        # Order deduplicator
        self.deduplicator = None
        if self.enable_deduplication:
            try:
                self.deduplicator = OrderDeduplicator(redis_client=redis_client)
                self.logger = get_logger('risk_manager')
                self.logger.info("Order deduplication ENABLED")
            except Exception as e:
                self.logger = get_logger('risk_manager')
                self.logger.warning(f"Failed to initialize deduplicator: {e}")
        else:
            self.logger = get_logger('risk_manager')
            self.logger.warning("Order deduplication DISABLED")

        # Emergency exit manager
        self.emergency_exit_manager = EmergencyExitManager(
            max_daily_loss=self.max_daily_loss,
            max_daily_loss_pct=self.max_daily_loss_pct,
            initial_capital=self.initial_capital
        )

        self.logger.info(
            f"RiskManager initialized: max_position_size={self.max_position_size}, "
            f"max_positions_per_strategy={self.max_positions_per_strategy}, "
            f"max_total_positions={self.max_total_positions}, "
            f"max_daily_loss={self.max_daily_loss}, "
            f"fixed_lot_size={self.fixed_lot_size}"
        )
    
    def validate_signal(self, signal: Dict, current_positions: Dict,
                       account_info: Dict) -> RiskCheckResult:
        """
        Validate a trading signal against risk limits with enhanced safety checks.

        Args:
            signal: Signal dictionary with keys:
                - strategy_id: Strategy identifier
                - action: BUY or SELL
                - symbol: Symbol
                - price: Price
                - quantity: Quantity
            current_positions: Current positions {strategy_id: {symbol: position}}
            account_info: Account information

        Returns:
            RiskCheckResult with approval status
        """
        strategy_id = signal['strategy_id']
        action = signal['action']
        symbol = signal['symbol']
        price = signal['price']
        quantity = signal['quantity']

        # Apply fixed lot size if configured
        if self.fixed_lot_size and action == 'BUY':
            original_quantity = quantity
            quantity = self.fixed_lot_size
            signal['quantity'] = quantity
            if original_quantity != quantity:
                self.logger.info(
                    f"[RISK_CHECK] {strategy_id}/{symbol}: Lot size adjusted "
                    f"{original_quantity} -> {quantity} (fixed lot size)"
                )
        
        # SELL signals are always approved (exiting positions)
        if action == 'SELL':
            self.logger.debug(f"[RISK_CHECK] {strategy_id}/{symbol}: SELL signal approved")

            # Log to database
            if self.data_manager:
                try:
                    self.data_manager.log_signal(
                        signal_data=signal,
                        approved=True,
                        rejection_reason=None
                    )
                except Exception as e:
                    self.logger.error(f"Error logging signal: {e}")

            return RiskCheckResult(approved=True, adjusted_quantity=quantity)

        # Check 0: Emergency exit status
        can_trade, emergency_reason = self.emergency_exit_manager.can_trade()
        if not can_trade:
            reason = f"Emergency exit triggered: {emergency_reason}"
            self.logger.critical(f"[RISK_CHECK] {strategy_id}/{symbol}: REJECTED - {reason}")

            if self.data_manager:
                try:
                    self.data_manager.log_signal(
                        signal_data=signal,
                        approved=False,
                        rejection_reason=reason
                    )
                except Exception as e:
                    self.logger.error(f"Error logging signal: {e}")

            return RiskCheckResult(approved=False, reason=reason)

        # Check 0.5: Order deduplication
        if self.deduplicator and action == 'BUY':
            # Check if position already exists
            if self.deduplicator.is_position_open(strategy_id, symbol):
                reason = f"Position already exists for {symbol}"
                self.logger.warning(f"[RISK_CHECK] {strategy_id}/{symbol}: REJECTED - {reason}")

                if self.data_manager:
                    try:
                        self.data_manager.log_signal(
                            signal_data=signal,
                            approved=False,
                            rejection_reason=reason
                        )
                    except Exception as e:
                        self.logger.error(f"Error logging signal: {e}")

                return RiskCheckResult(approved=False, reason=reason)

            # Check for duplicate order
            can_place, dedup_reason = self.deduplicator.can_place_order(
                strategy_id, symbol, action, quantity, price
            )

            if not can_place:
                reason = f"Duplicate order prevented: {dedup_reason}"
                self.logger.warning(f"[RISK_CHECK] {strategy_id}/{symbol}: REJECTED - {reason}")

                if self.data_manager:
                    try:
                        self.data_manager.log_signal(
                            signal_data=signal,
                            approved=False,
                            rejection_reason=reason
                        )
                    except Exception as e:
                        self.logger.error(f"Error logging signal: {e}")

                return RiskCheckResult(approved=False, reason=reason)
        
        # Check 1: Position size limit
        position_value = price * quantity
        if position_value > self.max_position_size:
            reason = (
                f"Position size {position_value:.2f} exceeds limit "
                f"{self.max_position_size:.2f}"
            )
            self.logger.warning(f"[RISK_CHECK] {strategy_id}/{symbol}: REJECTED - {reason}")
            
            # Log rejection to database
            if self.data_manager:
                try:
                    self.data_manager.log_signal(
                        signal_data=signal,
                        approved=False,
                        rejection_reason=reason
                    )
                except Exception as e:
                    self.logger.error(f"Error logging signal: {e}")
            
            return RiskCheckResult(approved=False, reason=reason)
        
        # Check 2: Max positions per strategy
        strategy_positions = current_positions.get(strategy_id, {})
        if symbol not in strategy_positions:  # New position
            if len(strategy_positions) >= self.max_positions_per_strategy:
                reason = (
                    f"Max positions per strategy ({self.max_positions_per_strategy}) "
                    f"reached for {strategy_id}"
                )
                self.logger.warning(f"[RISK_CHECK] {strategy_id}/{symbol}: REJECTED - {reason}")
                
                # Log rejection to database
                if self.data_manager:
                    try:
                        self.data_manager.log_signal(
                            signal_data=signal,
                            approved=False,
                            rejection_reason=reason
                        )
                    except Exception as e:
                        self.logger.error(f"Error logging signal: {e}")
                
                return RiskCheckResult(approved=False, reason=reason)
        
        # Check 3: Max total positions
        total_positions = sum(len(positions) for positions in current_positions.values())
        if symbol not in strategy_positions:  # New position
            if total_positions >= self.max_total_positions:
                reason = f"Max total positions ({self.max_total_positions}) reached"
                self.logger.warning(f"[RISK_CHECK] {strategy_id}/{symbol}: REJECTED - {reason}")
                
                # Log rejection to database
                if self.data_manager:
                    try:
                        self.data_manager.log_signal(
                            signal_data=signal,
                            approved=False,
                            rejection_reason=reason
                        )
                    except Exception as e:
                        self.logger.error(f"Error logging signal: {e}")
                
                return RiskCheckResult(approved=False, reason=reason)
        
        # Check 4: Daily loss limit
        if not self.is_trading_allowed():
            reason = (
                f"Daily loss limit exceeded: {self.daily_pnl:.2f} < "
                f"-{self.max_daily_loss:.2f}"
            )
            self.logger.warning(f"[RISK_CHECK] {strategy_id}/{symbol}: REJECTED - {reason}")
            
            # Log rejection to database
            if self.data_manager:
                try:
                    self.data_manager.log_signal(
                        signal_data=signal,
                        approved=False,
                        rejection_reason=reason
                    )
                except Exception as e:
                    self.logger.error(f"Error logging signal: {e}")
            
            return RiskCheckResult(approved=False, reason=reason)
        
        # All checks passed
        self.logger.debug(
            f"[RISK_CHECK] {strategy_id}/{symbol}: APPROVED "
            f"(value={position_value:.2f}, quantity={quantity}, positions={total_positions})"
        )

        # Log approval to database
        if self.data_manager:
            try:
                self.data_manager.log_signal(
                    signal_data=signal,
                    approved=True,
                    rejection_reason=None
                )
            except Exception as e:
                self.logger.error(f"Error logging signal: {e}")

        return RiskCheckResult(approved=True, adjusted_quantity=quantity)
    
    def update_daily_pnl(self, realized_pnl: float = 0.0, unrealized_pnl: float = 0.0,
                         trade_closed: bool = False):
        """
        Update daily P&L and check for emergency exit.

        Args:
            realized_pnl: Realized P&L from closed trades
            unrealized_pnl: Unrealized P&L from open positions
            trade_closed: Whether a trade was closed
        """
        if trade_closed:
            self.daily_pnl += realized_pnl
            self.daily_trades += 1
            self.emergency_exit_manager.record_trade_close(realized_pnl)

        # Update emergency exit manager
        total_pnl = self.daily_pnl + unrealized_pnl
        emergency_triggered = self.emergency_exit_manager.update_pnl(
            realized_pnl=self.daily_pnl,
            unrealized_pnl=unrealized_pnl
        )

        self.logger.debug(
            f"Daily P&L updated: realized={self.daily_pnl:.2f}, "
            f"unrealized={unrealized_pnl:.2f}, total={total_pnl:.2f} "
            f"(trades: {self.daily_trades})"
        )

        if emergency_triggered:
            self.logger.critical(
                f"🚨 EMERGENCY EXIT TRIGGERED - Daily loss limit breached! 🚨"
            )
        elif self.daily_pnl < -self.max_daily_loss:
            self.logger.warning(
                f"Daily loss limit exceeded: {self.daily_pnl:.2f} < -{self.max_daily_loss:.2f}"
            )
    
    def reset_daily_stats(self):
        """Reset daily statistics for new trading day."""
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.logger.info("Daily statistics reset")

    def register_order(self, order_id: str, strategy_id: str, symbol: str,
                      action: str, quantity: int, price: float) -> bool:
        """
        Register order with deduplicator

        Args:
            order_id: Unique order ID
            strategy_id: Strategy identifier
            symbol: Trading symbol
            action: BUY or SELL
            quantity: Order quantity
            price: Order price

        Returns:
            True if registered successfully
        """
        if self.deduplicator:
            return self.deduplicator.register_order(
                order_id, strategy_id, symbol, action, quantity, price
            )
        return True

    def mark_order_filled(self, order_id: str, strategy_id: str, symbol: str, action: str) -> bool:
        """
        Mark order as filled in deduplicator

        Args:
            order_id: Order identifier
            strategy_id: Strategy identifier
            symbol: Trading symbol
            action: BUY or SELL

        Returns:
            True if marked successfully
        """
        if self.deduplicator:
            return self.deduplicator.mark_order_filled(order_id, strategy_id, symbol, action)
        return True

    def mark_order_rejected(self, order_id: str, strategy_id: str, symbol: str,
                          action: str, reason: str) -> bool:
        """
        Mark order as rejected in deduplicator

        Args:
            order_id: Order identifier
            strategy_id: Strategy identifier
            symbol: Trading symbol
            action: BUY or SELL
            reason: Rejection reason

        Returns:
            True if marked successfully
        """
        if self.deduplicator:
            return self.deduplicator.mark_order_rejected(
                order_id, strategy_id, symbol, action, reason
            )
        return True

    def get_emergency_exit_manager(self) -> EmergencyExitManager:
        """Get emergency exit manager instance"""
        return self.emergency_exit_manager

    def cleanup_expired_orders(self) -> int:
        """
        Cleanup expired pending orders

        Returns:
            Number of cleaned up orders
        """
        if self.deduplicator:
            return self.deduplicator.cleanup_expired_orders()
        return 0
    
    def is_trading_allowed(self) -> bool:
        """
        Check if trading is allowed based on daily loss.
        
        Returns:
            True if trading is allowed
        """
        return self.daily_pnl > -self.max_daily_loss
    
    def calculate_max_position_size(self, price: float) -> int:
        """
        Calculate maximum position size in shares.
        
        Args:
            price: Current price
            
        Returns:
            Maximum number of shares
        """
        return int(self.max_position_size / price)
    
    def get_risk_metrics(self) -> Dict:
        """
        Get current risk metrics.
        
        Returns:
            Dictionary with risk metrics
        """
        daily_loss_remaining = self.max_daily_loss + self.daily_pnl
        
        return {
            'daily_pnl': self.daily_pnl,
            'daily_trades': self.daily_trades,
            'max_daily_loss': self.max_daily_loss,
            'daily_loss_remaining': daily_loss_remaining,
            'trading_allowed': self.is_trading_allowed(),
            'max_position_size': self.max_position_size,
            'max_positions_per_strategy': self.max_positions_per_strategy,
            'max_total_positions': self.max_total_positions
        }
    
    def get_daily_risk_metrics(self) -> Dict:
        """
        Get daily risk metrics from database.
        
        Returns:
            Dict with daily risk metrics
        """
        if self.data_manager:
            try:
                return self.data_manager.get_daily_summary()
            except Exception as e:
                self.logger.error(f"Error getting daily risk metrics: {e}")
        
        # Fallback to local metrics
        return {
            'daily_pnl': self.daily_pnl,
            'daily_trades': self.daily_trades,
            'trading_allowed': self.is_trading_allowed()
        }
    
    def get_rejection_statistics(self) -> Dict:
        """
        Get statistics on signal rejections.
        
        Returns:
            Dict with rejection stats by reason
        """
        # This would query the database for rejected signals
        # and aggregate by rejection reason
        if self.data_manager:
            try:
                # For now, return a placeholder
                # In a full implementation, this would query SQLite
                # for all rejected signals and group by rejection_reason
                return {
                    'total_rejections': 0,
                    'by_reason': {}
                }
            except Exception as e:
                self.logger.error(f"Error getting rejection stats: {e}")
        
        return {
            'total_rejections': 0,
            'by_reason': {}
        }


if __name__ == "__main__":
    # Test risk manager
    from ..utils.logging_config import initialize_logging
    import logging
    
    initialize_logging(log_level=logging.INFO)
    
    print("\n=== Testing Risk Manager ===\n")
    
    config = {
        'max_position_size': 10000,
        'max_positions_per_strategy': 3,
        'max_total_positions': 5,
        'max_daily_loss': 5000,
        'initial_capital': 100000
    }
    
    risk_manager = RiskManager(config)
    
    # Test signal validation
    print("1. Valid signal:")
    signal1 = {
        'strategy_id': 'test',
        'action': 'BUY',
        'symbol': 'TEST',
        'price': 100.0,
        'quantity': 10
    }
    result1 = risk_manager.validate_signal(signal1, {}, {})
    print(f"   Approved: {result1.approved}")
    
    # Test position size limit
    print("\n2. Position size exceeded:")
    signal2 = {
        'strategy_id': 'test',
        'action': 'BUY',
        'symbol': 'TEST',
        'price': 100.0,
        'quantity': 200  # 20000 > 10000 limit
    }
    result2 = risk_manager.validate_signal(signal2, {}, {})
    print(f"   Approved: {result2.approved}")
    print(f"   Reason: {result2.reason}")
    
    # Test daily loss limit
    print("\n3. Daily loss limit:")
    risk_manager.daily_pnl = -6000
    signal3 = {
        'strategy_id': 'test',
        'action': 'BUY',
        'symbol': 'TEST',
        'price': 100.0,
        'quantity': 10
    }
    result3 = risk_manager.validate_signal(signal3, {}, {})
    print(f"   Approved: {result3.approved}")
    print(f"   Reason: {result3.reason}")
    
    # Get metrics
    print("\n4. Risk metrics:")
    metrics = risk_manager.get_risk_metrics()
    for key, value in metrics.items():
        print(f"   {key}: {value}")
    
    print("\n✓ Risk manager test complete")
