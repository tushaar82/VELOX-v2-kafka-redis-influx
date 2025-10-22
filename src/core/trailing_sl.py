"""
Trailing Stop-Loss Engine.
Supports 4 types: fixed_pct, ATR, MA, time_decay.
"""

from enum import Enum
from typing import Dict, Optional
from datetime import datetime

from ..utils.logging_config import get_logger


class TrailingStopLossType(Enum):
    """Types of trailing stop-loss."""
    FIXED_PCT = "FIXED_PCT"  # Fixed percentage, doesn't trail
    ATR = "ATR"  # ATR-based trailing
    MA = "MA"  # Moving average based
    TIME_DECAY = "TIME_DECAY"  # Tightens over time


class TrailingStopLoss:
    """Trailing stop-loss calculator."""
    
    def __init__(self, sl_type: TrailingStopLossType, entry_price: float,
                 config: Dict, entry_timestamp: Optional[datetime] = None):
        """
        Initialize trailing stop-loss.
        
        Args:
            sl_type: Type of stop-loss
            entry_price: Entry price
            config: Configuration dictionary:
                - FIXED_PCT: {'pct': 0.02}  # 2%
                - ATR: {'atr_value': 2.0, 'atr_multiplier': 2.0}
                - MA: {'ma_value': 95.0, 'buffer_pct': 0.01}
                - TIME_DECAY: {'initial_sl_pct': 0.02, 'final_sl_pct': 0.005, 'decay_minutes': 60}
            entry_timestamp: Entry timestamp (for TIME_DECAY)
        """
        self.sl_type = sl_type
        self.entry_price = entry_price
        self.config = config
        self.entry_timestamp = entry_timestamp or datetime.now()
        
        self.highest_price = entry_price
        self.current_sl = self._calculate_initial_sl()
        
        self.logger = get_logger('trailing_sl')
        
        self.logger.debug(
            f"TrailingSL initialized: type={sl_type.value}, entry={entry_price:.2f}, "
            f"initial_sl={self.current_sl:.2f}"
        )
    
    def _calculate_initial_sl(self) -> float:
        """Calculate initial stop-loss based on type."""
        if self.sl_type == TrailingStopLossType.FIXED_PCT:
            pct = self.config.get('pct', 0.02)
            return self.entry_price * (1 - pct)
        
        elif self.sl_type == TrailingStopLossType.ATR:
            atr_value = self.config.get('atr_value', 2.0)
            atr_multiplier = self.config.get('atr_multiplier', 2.0)
            return self.entry_price - (atr_value * atr_multiplier)
        
        elif self.sl_type == TrailingStopLossType.MA:
            ma_value = self.config.get('ma_value', self.entry_price * 0.95)
            buffer_pct = self.config.get('buffer_pct', 0.01)
            return ma_value * (1 - buffer_pct)
        
        elif self.sl_type == TrailingStopLossType.TIME_DECAY:
            initial_sl_pct = self.config.get('initial_sl_pct', 0.02)
            return self.entry_price * (1 - initial_sl_pct)
        
        return self.entry_price * 0.98  # Default 2%
    
    def update(self, current_price: float, highest_price: float,
               atr_value: Optional[float] = None,
               ma_value: Optional[float] = None,
               current_timestamp: Optional[datetime] = None):
        """
        Update stop-loss based on current market conditions.
        
        Args:
            current_price: Current price
            highest_price: Highest price since entry
            atr_value: Current ATR value (for ATR type)
            ma_value: Current MA value (for MA type)
            current_timestamp: Current timestamp (for TIME_DECAY type)
        """
        # Update highest price
        if highest_price > self.highest_price:
            self.highest_price = highest_price
        
        # Calculate new SL based on type
        new_sl = self._calculate_new_sl(
            current_price, atr_value, ma_value, current_timestamp
        )
        
        # SL can only move up (tighten), never down
        if new_sl > self.current_sl:
            old_sl = self.current_sl
            self.current_sl = new_sl
            
            self.logger.debug(
                f"TrailingSL updated: {old_sl:.2f} -> {new_sl:.2f} "
                f"(price={current_price:.2f}, highest={self.highest_price:.2f})"
            )
    
    def _calculate_new_sl(self, current_price: float,
                         atr_value: Optional[float],
                         ma_value: Optional[float],
                         current_timestamp: Optional[datetime]) -> float:
        """Calculate new stop-loss value."""
        if self.sl_type == TrailingStopLossType.FIXED_PCT:
            # Fixed SL doesn't trail
            return self.current_sl
        
        elif self.sl_type == TrailingStopLossType.ATR:
            if atr_value is None:
                atr_value = self.config.get('atr_value', 2.0)
            
            atr_multiplier = self.config.get('atr_multiplier', 2.0)
            # SL trails based on highest price
            return self.highest_price - (atr_value * atr_multiplier)
        
        elif self.sl_type == TrailingStopLossType.MA:
            if ma_value is None:
                return self.current_sl
            
            buffer_pct = self.config.get('buffer_pct', 0.01)
            return ma_value * (1 - buffer_pct)
        
        elif self.sl_type == TrailingStopLossType.TIME_DECAY:
            if current_timestamp is None:
                current_timestamp = datetime.now()
            
            # Calculate time elapsed
            elapsed = (current_timestamp - self.entry_timestamp).total_seconds() / 60  # minutes
            decay_minutes = self.config.get('decay_minutes', 60)
            
            # Calculate current SL percentage (decays from initial to final)
            initial_sl_pct = self.config.get('initial_sl_pct', 0.02)
            final_sl_pct = self.config.get('final_sl_pct', 0.005)
            
            # Linear decay
            progress = min(1.0, elapsed / decay_minutes)
            current_sl_pct = initial_sl_pct - ((initial_sl_pct - final_sl_pct) * progress)
            
            # Apply to highest price
            return self.highest_price * (1 - current_sl_pct)
        
        return self.current_sl
    
    def is_hit(self, current_price: float) -> bool:
        """
        Check if stop-loss is hit.
        
        Args:
            current_price: Current price
            
        Returns:
            True if SL is hit
        """
        return current_price <= self.current_sl
    
    def get_info(self) -> Dict:
        """
        Get stop-loss information.
        
        Returns:
            Dictionary with SL details
        """
        return {
            'type': self.sl_type.value,
            'entry_price': self.entry_price,
            'current_sl': self.current_sl,
            'highest_price': self.highest_price,
            'distance_pct': ((self.highest_price - self.current_sl) / self.highest_price) * 100
        }


class TrailingStopLossManager:
    """Manages trailing stop-losses for multiple positions."""
    
    def __init__(self, data_manager=None):
        """
        Initialize manager.
        
        Args:
            data_manager: Optional DataManager for database logging
        """
        self.stop_losses = {}  # (strategy_id, symbol) -> TrailingStopLoss
        self.data_manager = data_manager
        self.logger = get_logger('trailing_sl_manager')
    
    def add_stop_loss(self, strategy_id: str, symbol: str,
                     sl_type: TrailingStopLossType, entry_price: float,
                     config: Dict, entry_timestamp: Optional[datetime] = None,
                     trade_id: Optional[str] = None):
        """
        Add a trailing stop-loss.
        
        Args:
            strategy_id: Strategy identifier
            symbol: Symbol
            sl_type: Type of stop-loss
            entry_price: Entry price
            config: Configuration
            entry_timestamp: Entry timestamp
            trade_id: Optional trade ID for database logging
        """
        key = (strategy_id, symbol)
        
        sl = TrailingStopLoss(sl_type, entry_price, config, entry_timestamp)
        self.stop_losses[key] = sl
        
        self.logger.info(
            f"TrailingSL added: {strategy_id}/{symbol}, type={sl_type.value}, "
            f"entry={entry_price:.2f}, sl={sl.current_sl:.2f}"
        )
        
        # Log SL setup to database
        if self.data_manager and trade_id:
            try:
                self.data_manager.update_trailing_sl(
                    trade_id=trade_id,
                    strategy_id=strategy_id,
                    symbol=symbol,
                    current_sl=sl.current_sl,
                    highest_price=entry_price,
                    sl_type=sl_type.value
                )
            except Exception as e:
                self.logger.error(f"Error logging SL setup: {e}")
    
    def update_stop_loss(self, strategy_id: str, symbol: str,
                        current_price: float, highest_price: float,
                        trade_id: Optional[str] = None,
                        **kwargs):
        """
        Update a stop-loss.
        
        Args:
            strategy_id: Strategy identifier
            symbol: Symbol
            current_price: Current price
            highest_price: Highest price
            trade_id: Optional trade ID for database logging
            **kwargs: Additional parameters (atr_value, ma_value, current_timestamp)
        """
        key = (strategy_id, symbol)
        
        if key in self.stop_losses:
            sl = self.stop_losses[key]
            prev_sl = sl.current_sl
            
            sl.update(current_price, highest_price, **kwargs)
            
            # Log SL update to database (only if SL moved significantly)
            if self.data_manager and trade_id and prev_sl > 0:
                sl_change_pct = abs((sl.current_sl - prev_sl) / prev_sl) * 100
                
                # Only log if SL moved more than 0.1%
                if sl_change_pct > 0.1:
                    try:
                        self.data_manager.update_trailing_sl(
                            trade_id=trade_id,
                            strategy_id=strategy_id,
                            symbol=symbol,
                            current_sl=sl.current_sl,
                            highest_price=sl.highest_price,
                            sl_type=sl.sl_type.value
                        )
                    except Exception as e:
                        self.logger.error(f"Error logging SL update: {e}")
    
    def check_stop_loss(self, strategy_id: str, symbol: str,
                       current_price: float) -> bool:
        """
        Check if stop-loss is hit.
        
        Args:
            strategy_id: Strategy identifier
            symbol: Symbol
            current_price: Current price
            
        Returns:
            True if SL is hit
        """
        key = (strategy_id, symbol)
        
        if key in self.stop_losses:
            is_hit = self.stop_losses[key].is_hit(current_price)
            
            if is_hit:
                sl_info = self.stop_losses[key].get_info()
                self.logger.info(
                    f"TrailingSL HIT: {strategy_id}/{symbol}, "
                    f"price={current_price:.2f}, sl={sl_info['current_sl']:.2f}"
                )
            
            return is_hit
        
        return False
    
    def remove_stop_loss(self, strategy_id: str, symbol: str):
        """
        Remove a stop-loss.
        
        Args:
            strategy_id: Strategy identifier
            symbol: Symbol
        """
        key = (strategy_id, symbol)
        
        if key in self.stop_losses:
            del self.stop_losses[key]
            self.logger.info(f"TrailingSL removed: {strategy_id}/{symbol}")
    
    def get_stop_loss_info(self, strategy_id: str, symbol: str) -> Optional[Dict]:
        """
        Get stop-loss information.
        
        Args:
            strategy_id: Strategy identifier
            symbol: Symbol
            
        Returns:
            SL info dictionary or None
        """
        key = (strategy_id, symbol)
        
        if key in self.stop_losses:
            return self.stop_losses[key].get_info()
        
        return None
    
    def get_all_stop_losses(self) -> Dict:
        """
        Get all stop-losses.
        
        Returns:
            Dictionary {(strategy_id, symbol): info}
        """
        return {
            key: sl.get_info()
            for key, sl in self.stop_losses.items()
        }


if __name__ == "__main__":
    # Test trailing SL
    from ..utils.logging_config import initialize_logging
    import logging
    
    initialize_logging(log_level=logging.INFO)
    
    print("\n=== Testing Trailing Stop-Loss ===\n")
    
    # Test FIXED_PCT
    print("1. Fixed Percentage SL:")
    sl_fixed = TrailingStopLoss(
        TrailingStopLossType.FIXED_PCT,
        entry_price=100.0,
        config={'pct': 0.02}
    )
    print(f"   Entry: 100.0, SL: {sl_fixed.current_sl:.2f}")
    sl_fixed.update(110.0, 110.0)
    print(f"   After price -> 110: SL: {sl_fixed.current_sl:.2f} (no change)")
    
    # Test ATR
    print("\n2. ATR-based SL:")
    sl_atr = TrailingStopLoss(
        TrailingStopLossType.ATR,
        entry_price=100.0,
        config={'atr_value': 2.0, 'atr_multiplier': 2.0}
    )
    print(f"   Entry: 100.0, SL: {sl_atr.current_sl:.2f}")
    sl_atr.update(110.0, 110.0, atr_value=2.0)
    print(f"   After price -> 110: SL: {sl_atr.current_sl:.2f} (trails up)")
    
    # Test TIME_DECAY
    print("\n3. Time Decay SL:")
    entry_time = datetime.now()
    sl_decay = TrailingStopLoss(
        TrailingStopLossType.TIME_DECAY,
        entry_price=100.0,
        config={'initial_sl_pct': 0.02, 'final_sl_pct': 0.005, 'decay_minutes': 60},
        entry_timestamp=entry_time
    )
    print(f"   Entry: 100.0, Initial SL: {sl_decay.current_sl:.2f}")
    
    from datetime import timedelta
    future_time = entry_time + timedelta(minutes=30)
    sl_decay.update(110.0, 110.0, current_timestamp=future_time)
    print(f"   After 30 min, price -> 110: SL: {sl_decay.current_sl:.2f} (tightens)")
    
    print("\n✓ Trailing SL test complete")
