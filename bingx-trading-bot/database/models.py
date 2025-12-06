"""
Database Models

SQLAlchemy models for trade logging and performance tracking
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, Float, String, DateTime, Boolean, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import validates
import enum


Base = declarative_base()


class TradeStatus(enum.Enum):
    """Trade status enumeration"""
    PENDING = "PENDING"
    OPEN = "OPEN"
    CLOSING = "CLOSING"
    CLOSED = "CLOSED"


class ExitReason(enum.Enum):
    """Exit reason enumeration"""
    TAKE_PROFIT = "TP"
    STOP_LOSS = "SL"
    TRAILING_STOP = "TRAILING"
    PARTIAL_EXIT = "PARTIAL"
    TIME_STOP = "TIME"
    MANUAL = "MANUAL"
    EMERGENCY_STOP = "EMERGENCY"


class TradeSide(enum.Enum):
    """Trade side enumeration"""
    LONG = "LONG"
    SHORT = "SHORT"


class Trade(Base):
    """
    Trade log model

    Records all trade details including entry, exit, P&L, and metadata
    """
    __tablename__ = 'trades'

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Timestamps
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    entry_time = Column(DateTime, nullable=False, index=True)
    exit_time = Column(DateTime, nullable=True)

    # Trade identification
    strategy = Column(String(50), nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    side = Column(SQLEnum(TradeSide), nullable=False)

    # Entry details
    entry_price = Column(Float, nullable=False)
    quantity = Column(Float, nullable=False)
    entry_order_id = Column(String(100), nullable=True)

    # Exit details
    exit_price = Column(Float, nullable=True)
    exit_order_id = Column(String(100), nullable=True)

    # Risk management
    stop_loss = Column(Float, nullable=False)
    initial_stop = Column(Float, nullable=False)  # Track original stop for R calculation
    take_profit = Column(Float, nullable=False)

    # P&L
    pnl_usdt = Column(Float, nullable=True, default=0.0)
    pnl_percent = Column(Float, nullable=True, default=0.0)
    r_multiple = Column(Float, nullable=True, default=0.0)  # Risk/Reward multiple

    # Status
    status = Column(SQLEnum(TradeStatus), nullable=False, default=TradeStatus.PENDING, index=True)
    exit_reason = Column(SQLEnum(ExitReason), nullable=True)

    # Metadata
    capital_at_entry = Column(Float, nullable=True)
    risk_pct = Column(Float, nullable=True)
    pattern = Column(String(100), nullable=True)  # Pattern that triggered entry
    hours_held = Column(Float, nullable=True)

    # Partial exits
    partial_exits = Column(Boolean, default=False)
    remaining_quantity = Column(Float, nullable=True)

    # Notes
    notes = Column(String(500), nullable=True)

    @validates('side')
    def validate_side(self, key, value):
        """Validate trade side"""
        if isinstance(value, str):
            return TradeSide[value.upper()]
        return value

    @validates('status')
    def validate_status(self, key, value):
        """Validate trade status"""
        if isinstance(value, str):
            return TradeStatus[value.upper()]
        return value

    def calculate_pnl(self) -> None:
        """Calculate P&L metrics"""
        if self.exit_price is None or self.entry_price is None:
            return

        # Calculate P&L based on direction
        if self.side == TradeSide.LONG:
            pnl_per_unit = self.exit_price - self.entry_price
        else:  # SHORT
            pnl_per_unit = self.entry_price - self.exit_price

        # Calculate remaining quantity
        qty = self.remaining_quantity if self.remaining_quantity else self.quantity

        # Total P&L
        self.pnl_usdt = pnl_per_unit * qty
        self.pnl_percent = (pnl_per_unit / self.entry_price) * 100

        # R-multiple
        initial_risk = abs(self.entry_price - self.initial_stop)
        if initial_risk > 0:
            self.r_multiple = pnl_per_unit / initial_risk

    def update_exit(self, exit_price: float, exit_reason: ExitReason,
                    exit_time: Optional[datetime] = None) -> None:
        """Update trade with exit information"""
        self.exit_price = exit_price
        self.exit_reason = exit_reason
        self.exit_time = exit_time or datetime.utcnow()
        self.status = TradeStatus.CLOSED

        # Calculate hours held
        if self.entry_time:
            self.hours_held = (self.exit_time - self.entry_time).total_seconds() / 3600

        # Calculate P&L
        self.calculate_pnl()

    def __repr__(self) -> str:
        return (f"<Trade(id={self.id}, strategy='{self.strategy}', "
                f"symbol='{self.symbol}', side={self.side.value}, "
                f"status={self.status.value}, pnl={self.pnl_usdt:.2f if self.pnl_usdt else 0:.2f})>")


class PerformanceMetric(Base):
    """
    Daily performance metrics

    Aggregates trading performance by day for analysis
    """
    __tablename__ = 'performance_metrics'

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Date
    date = Column(DateTime, nullable=False, unique=True, index=True)

    # Trade statistics
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    breakeven_trades = Column(Integer, default=0)

    # P&L
    total_pnl = Column(Float, default=0.0)
    total_pnl_pct = Column(Float, default=0.0)
    gross_profit = Column(Float, default=0.0)
    gross_loss = Column(Float, default=0.0)

    # Risk metrics
    max_drawdown = Column(Float, default=0.0)
    max_drawdown_pct = Column(Float, default=0.0)
    peak_capital = Column(Float, nullable=True)

    # Performance ratios
    win_rate = Column(Float, default=0.0)
    profit_factor = Column(Float, default=0.0)
    sharpe_ratio = Column(Float, nullable=True)
    avg_win = Column(Float, default=0.0)
    avg_loss = Column(Float, default=0.0)
    avg_r_multiple = Column(Float, default=0.0)

    # Capital
    starting_capital = Column(Float, nullable=True)
    ending_capital = Column(Float, nullable=True)

    # Strategy breakdown (JSON could be better, but keeping simple)
    long_trades = Column(Integer, default=0)
    short_trades = Column(Integer, default=0)

    def calculate_metrics(self, trades: list) -> None:
        """Calculate metrics from list of trades"""
        if not trades:
            return

        # Count trades
        self.total_trades = len(trades)
        self.winning_trades = len([t for t in trades if t.pnl_usdt > 0])
        self.losing_trades = len([t for t in trades if t.pnl_usdt < 0])
        self.breakeven_trades = len([t for t in trades if t.pnl_usdt == 0])

        # Win rate
        self.win_rate = (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0

        # P&L
        self.total_pnl = sum(t.pnl_usdt for t in trades if t.pnl_usdt)
        self.gross_profit = sum(t.pnl_usdt for t in trades if t.pnl_usdt and t.pnl_usdt > 0)
        self.gross_loss = abs(sum(t.pnl_usdt for t in trades if t.pnl_usdt and t.pnl_usdt < 0))

        # Profit factor
        self.profit_factor = (self.gross_profit / self.gross_loss) if self.gross_loss > 0 else float('inf')

        # Average win/loss
        winning_pnls = [t.pnl_pct for t in trades if t.pnl_pct and t.pnl_pct > 0]
        losing_pnls = [t.pnl_pct for t in trades if t.pnl_pct and t.pnl_pct < 0]

        self.avg_win = sum(winning_pnls) / len(winning_pnls) if winning_pnls else 0
        self.avg_loss = sum(losing_pnls) / len(losing_pnls) if losing_pnls else 0

        # Average R-multiple
        r_multiples = [t.r_multiple for t in trades if t.r_multiple]
        self.avg_r_multiple = sum(r_multiples) / len(r_multiples) if r_multiples else 0

        # Strategy breakdown
        self.long_trades = len([t for t in trades if t.side == TradeSide.LONG])
        self.short_trades = len([t for t in trades if t.side == TradeSide.SHORT])

        # Capital
        if trades:
            self.starting_capital = trades[0].capital_at_entry
            # Ending capital = starting + total PnL
            self.ending_capital = self.starting_capital + self.total_pnl if self.starting_capital else None

            if self.starting_capital and self.ending_capital:
                self.total_pnl_pct = ((self.ending_capital - self.starting_capital) / self.starting_capital) * 100

    def __repr__(self) -> str:
        return (f"<PerformanceMetric(date={self.date.date()}, "
                f"trades={self.total_trades}, win_rate={self.win_rate:.1f}%, "
                f"pnl={self.total_pnl:.2f})>")


class SystemEvent(Base):
    """
    System events log

    Records important system events for debugging and auditing
    """
    __tablename__ = 'system_events'

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Timestamp
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Event details
    event_type = Column(String(50), nullable=False, index=True)  # START, STOP, ERROR, WARNING, etc.
    severity = Column(String(20), nullable=False)  # INFO, WARNING, ERROR, CRITICAL
    message = Column(String(500), nullable=False)
    details = Column(String(2000), nullable=True)  # JSON or text details

    # Context
    component = Column(String(50), nullable=True)  # data_feed, strategy, execution, etc.
    symbol = Column(String(20), nullable=True)

    def __repr__(self) -> str:
        return (f"<SystemEvent(timestamp={self.timestamp}, type='{self.event_type}', "
                f"severity='{self.severity}', message='{self.message[:50]}')>")


# Create all tables
def create_all_tables(engine):
    """Create all database tables"""
    Base.metadata.create_all(engine)


def drop_all_tables(engine):
    """Drop all database tables (use with caution!)"""
    Base.metadata.drop_all(engine)
