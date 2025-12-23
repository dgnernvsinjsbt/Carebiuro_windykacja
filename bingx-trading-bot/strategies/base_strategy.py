"""
Base Strategy Abstract Class

All trading strategies inherit from this base class
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from datetime import datetime
import pandas as pd
import logging


class BaseStrategy(ABC):
    """Abstract base class for trading strategies"""

    def __init__(self, name: str, config: Dict[str, Any], symbol: Optional[str] = None):
        self.name = name
        self.config = config
        self.enabled = config.get('enabled', True)
        self.symbol = symbol  # Trading symbol this strategy is for

        # Setup logger for this strategy
        self.logger = logging.getLogger(f"strategy.{name}")

        # Position sizing
        self.base_risk_pct = config.get('base_risk_pct', 1.0)
        self.max_risk_pct = config.get('max_risk_pct', 3.0)
        self.current_risk_pct = self.base_risk_pct
        self.win_streak = 0
        self.loss_streak = 0

        # Statistics
        self.signals_generated = 0
        self.trades_entered = 0

    @abstractmethod
    def analyze(self, df_1min: pd.DataFrame, df_5min: Optional[pd.DataFrame] = None) -> Optional[Dict[str, Any]]:
        """
        Analyze market data and generate signal

        Args:
            df_1min: 1-minute OHLCV DataFrame
            df_5min: 5-minute OHLCV DataFrame (optional)

        Returns:
            Signal dictionary or None:
            {
                'direction': 'LONG' or 'SHORT',
                'entry_price': float,
                'stop_loss': float,
                'take_profit': float,
                'pattern': str,
                'confidence': float (0-1)
            }
        """
        pass

    def calculate_position_size(self, entry_price: float, stop_price: float, capital: float) -> float:
        """Calculate position size based on risk"""
        risk_amount = capital * (self.current_risk_pct / 100)
        stop_distance = abs(entry_price - stop_price) / entry_price

        if stop_distance == 0:
            return 0

        position_size = risk_amount / stop_distance
        max_position = capital * 0.4
        return min(position_size, max_position)

    def update_risk_sizing(self, trade_won: bool) -> None:
        """Update risk sizing based on trade outcome"""
        if trade_won:
            self.win_streak += 1
            self.loss_streak = 0
            self.current_risk_pct = min(
                self.base_risk_pct + (self.win_streak * 0.5),
                self.max_risk_pct
            )
        else:
            self.loss_streak += 1
            self.win_streak = 0
            self.current_risk_pct = self.base_risk_pct

    def get_statistics(self) -> Dict[str, Any]:
        """Get strategy statistics"""
        return {
            'name': self.name,
            'enabled': self.enabled,
            'signals_generated': self.signals_generated,
            'trades_entered': self.trades_entered,
            'win_streak': self.win_streak,
            'loss_streak': self.loss_streak,
            'current_risk_pct': self.current_risk_pct
        }
