"""Position Manager - Tracks and manages open positions"""
from typing import Dict, Optional, Any
from enum import Enum
import logging

class PositionStatus(Enum):
    PENDING = "PENDING"
    OPEN = "OPEN"
    CLOSING = "CLOSING"
    CLOSED = "CLOSED"

class Position:
    """Represents a trading position"""
    def __init__(self, position_id: int, strategy: str, symbol: str, side: str, entry_price: float,
                 quantity: float, stop_loss: float, take_profit: float):
        self.id = position_id
        self.strategy = strategy
        self.symbol = symbol
        self.side = side
        self.entry_price = entry_price
        self.quantity = quantity
        self.stop_loss = stop_loss
        self.initial_stop = stop_loss
        self.take_profit = take_profit
        self.status = PositionStatus.PENDING
        self.remaining_quantity = quantity
        self.partial_exits_taken = []

class PositionManager:
    """Manages all open positions"""
    def __init__(self, max_positions_per_strategy: Dict[str, int]):
        self.positions: Dict[int, Position] = {}
        self.max_positions = max_positions_per_strategy
        self.next_id = 1
        self.logger = logging.getLogger(__name__)

    def can_open_position(self, strategy: str) -> bool:
        """Check if strategy can open new position"""
        count = sum(1 for p in self.positions.values() 
                   if p.strategy == strategy and p.status == PositionStatus.OPEN)
        return count < self.max_positions.get(strategy, 1)

    def open_position(self, signal: Dict[str, Any], quantity: float) -> Position:
        """Open new position from signal"""
        position = Position(
            self.next_id, signal['strategy'], signal.get('symbol', 'UNKNOWN'),
            signal['direction'], signal['entry_price'], quantity,
            signal['stop_loss'], signal['take_profit']
        )
        self.positions[self.next_id] = position
        self.next_id += 1
        self.logger.info(f"Position opened: {position.id} - {position.strategy} {position.side}")
        return position

    def get_open_positions(self) -> List[Position]:
        """Get all open positions"""
        return [p for p in self.positions.values() if p.status == PositionStatus.OPEN]
