"""Risk Manager - Validates and enforces risk limits"""
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import logging

class RiskManager:
    """Enforces risk management rules"""
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.max_portfolio_risk = config.get('max_portfolio_risk', 5.0)
        self.max_drawdown = config.get('max_drawdown', 10.0)
        self.cooldown_minutes = config.get('cooldown_after_loss', 60)
        self.max_consecutive_losses = config.get('max_consecutive_losses', 3)
        self.min_balance = config.get('min_account_balance', 100.0)
        
        self.consecutive_losses = 0
        self.last_loss_time: Optional[datetime] = None
        self.current_drawdown_pct = 0.0
        self.emergency_stop = False
        self.logger = logging.getLogger(__name__)

    def validate_trade(self, signal: Dict[str, Any], capital: float) -> tuple[bool, str]:
        """Validate if trade can be executed"""
        if self.emergency_stop:
            return False, "Emergency stop active"
        
        if capital < self.min_balance:
            return False, f"Insufficient balance: {capital} < {self.min_balance}"
        
        if self.current_drawdown_pct >= self.max_drawdown:
            self.emergency_stop = True
            return False, f"Max drawdown reached: {self.current_drawdown_pct:.2f}%"
        
        if self.consecutive_losses >= self.max_consecutive_losses:
            return False, f"Max consecutive losses reached: {self.consecutive_losses}"
        
        if self.last_loss_time and (datetime.utcnow() - self.last_loss_time).total_seconds() < self.cooldown_minutes * 60:
            return False, "In cooldown period after loss"
        
        return True, "OK"

    def record_trade_outcome(self, profit: float) -> None:
        """Record trade outcome for risk tracking"""
        if profit < 0:
            self.consecutive_losses += 1
            self.last_loss_time = datetime.utcnow()
        else:
            self.consecutive_losses = 0

    def update_drawdown(self, drawdown_pct: float) -> None:
        """Update current drawdown"""
        self.current_drawdown_pct = drawdown_pct
