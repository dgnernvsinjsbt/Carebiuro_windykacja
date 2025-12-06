"""
Trade Logger

Handles persistent storage of trades and system events
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import create_engine, and_, or_, desc
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
import logging

from .models import (
    Base, Trade, PerformanceMetric, SystemEvent,
    TradeStatus, TradeSide, ExitReason, create_all_tables
)


class TradeLogger:
    """
    Trade logging and persistence

    Handles all database operations for trades and metrics
    """

    def __init__(self, database_url: str, echo: bool = False):
        """
        Initialize trade logger

        Args:
            database_url: SQLAlchemy database URL
            echo: Echo SQL queries to console
        """
        self.database_url = database_url
        self.engine = create_engine(database_url, echo=echo)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.logger = logging.getLogger(__name__)

        # Create tables if they don't exist
        self._initialize_database()

    def _initialize_database(self) -> None:
        """Create database tables"""
        try:
            create_all_tables(self.engine)
            self.logger.info("Database initialized successfully")
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to initialize database: {e}")
            raise

    def get_session(self) -> Session:
        """Get a new database session"""
        return self.SessionLocal()

    # ==================== TRADE OPERATIONS ====================

    def log_trade(self, trade_data: Dict[str, Any]) -> Optional[Trade]:
        """
        Log a new trade

        Args:
            trade_data: Dictionary with trade information

        Returns:
            Trade object or None if failed
        """
        session = self.get_session()
        try:
            trade = Trade(**trade_data)
            session.add(trade)
            session.commit()
            session.refresh(trade)

            self.logger.info(f"Trade logged: {trade.id} - {trade.strategy} {trade.side.value} {trade.symbol}")
            return trade

        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"Failed to log trade: {e}")
            return None
        finally:
            session.close()

    def update_trade(self, trade_id: int, updates: Dict[str, Any]) -> bool:
        """
        Update trade information

        Args:
            trade_id: Trade ID
            updates: Dictionary of fields to update

        Returns:
            True if successful
        """
        session = self.get_session()
        try:
            trade = session.query(Trade).filter(Trade.id == trade_id).first()

            if not trade:
                self.logger.warning(f"Trade {trade_id} not found")
                return False

            for key, value in updates.items():
                setattr(trade, key, value)

            session.commit()
            self.logger.debug(f"Trade {trade_id} updated")
            return True

        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"Failed to update trade {trade_id}: {e}")
            return False
        finally:
            session.close()

    def close_trade(self, trade_id: int, exit_price: float,
                    exit_reason: ExitReason, exit_time: Optional[datetime] = None) -> bool:
        """
        Close a trade and calculate P&L

        Args:
            trade_id: Trade ID
            exit_price: Exit price
            exit_reason: Reason for exit
            exit_time: Exit timestamp (default: now)

        Returns:
            True if successful
        """
        session = self.get_session()
        try:
            trade = session.query(Trade).filter(Trade.id == trade_id).first()

            if not trade:
                self.logger.warning(f"Trade {trade_id} not found")
                return False

            # Update exit information
            trade.update_exit(exit_price, exit_reason, exit_time)

            session.commit()
            self.logger.info(f"Trade {trade_id} closed: {exit_reason.value} | "
                           f"P&L: {trade.pnl_usdt:.2f} USDT ({trade.pnl_percent:.2f}%)")
            return True

        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"Failed to close trade {trade_id}: {e}")
            return False
        finally:
            session.close()

    def get_trade(self, trade_id: int) -> Optional[Trade]:
        """Get trade by ID"""
        session = self.get_session()
        try:
            trade = session.query(Trade).filter(Trade.id == trade_id).first()
            return trade
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to get trade {trade_id}: {e}")
            return None
        finally:
            session.close()

    def get_open_trades(self, symbol: Optional[str] = None,
                        strategy: Optional[str] = None) -> List[Trade]:
        """
        Get all open trades

        Args:
            symbol: Filter by symbol
            strategy: Filter by strategy

        Returns:
            List of open trades
        """
        session = self.get_session()
        try:
            query = session.query(Trade).filter(Trade.status == TradeStatus.OPEN)

            if symbol:
                query = query.filter(Trade.symbol == symbol)
            if strategy:
                query = query.filter(Trade.strategy == strategy)

            trades = query.all()
            return trades

        except SQLAlchemyError as e:
            self.logger.error(f"Failed to get open trades: {e}")
            return []
        finally:
            session.close()

    def get_trades_by_date(self, start_date: datetime,
                           end_date: Optional[datetime] = None) -> List[Trade]:
        """
        Get trades within date range

        Args:
            start_date: Start date
            end_date: End date (default: now)

        Returns:
            List of trades
        """
        session = self.get_session()
        try:
            query = session.query(Trade).filter(Trade.entry_time >= start_date)

            if end_date:
                query = query.filter(Trade.entry_time <= end_date)

            trades = query.order_by(Trade.entry_time).all()
            return trades

        except SQLAlchemyError as e:
            self.logger.error(f"Failed to get trades by date: {e}")
            return []
        finally:
            session.close()

    def get_recent_trades(self, limit: int = 10) -> List[Trade]:
        """Get most recent trades"""
        session = self.get_session()
        try:
            trades = session.query(Trade).order_by(desc(Trade.entry_time)).limit(limit).all()
            return trades
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to get recent trades: {e}")
            return []
        finally:
            session.close()

    # ==================== PERFORMANCE METRICS ====================

    def calculate_daily_metrics(self, date: datetime) -> Optional[PerformanceMetric]:
        """
        Calculate performance metrics for a specific day

        Args:
            date: Date to calculate metrics for

        Returns:
            PerformanceMetric object
        """
        # Get all closed trades for the day
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)

        trades = self.get_trades_by_date(start_of_day, end_of_day)
        closed_trades = [t for t in trades if t.status == TradeStatus.CLOSED]

        if not closed_trades:
            return None

        session = self.get_session()
        try:
            # Check if metrics already exist
            metric = session.query(PerformanceMetric).filter(
                PerformanceMetric.date == start_of_day
            ).first()

            if not metric:
                metric = PerformanceMetric(date=start_of_day)
                session.add(metric)

            # Calculate metrics
            metric.calculate_metrics(closed_trades)

            session.commit()
            session.refresh(metric)

            self.logger.info(f"Daily metrics calculated for {date.date()}: "
                           f"{metric.total_trades} trades, {metric.win_rate:.1f}% win rate")
            return metric

        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"Failed to calculate daily metrics: {e}")
            return None
        finally:
            session.close()

    def get_performance_summary(self, days: int = 30) -> Dict[str, Any]:
        """
        Get performance summary for last N days

        Args:
            days: Number of days to include

        Returns:
            Dictionary with summary statistics
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        trades = self.get_trades_by_date(start_date)
        closed_trades = [t for t in trades if t.status == TradeStatus.CLOSED]

        if not closed_trades:
            return {
                'total_trades': 0,
                'win_rate': 0.0,
                'total_pnl': 0.0,
                'profit_factor': 0.0
            }

        # Calculate summary
        total_trades = len(closed_trades)
        winning_trades = len([t for t in closed_trades if t.pnl_usdt > 0])
        losing_trades = len([t for t in closed_trades if t.pnl_usdt < 0])

        total_pnl = sum(t.pnl_usdt for t in closed_trades if t.pnl_usdt)
        gross_profit = sum(t.pnl_usdt for t in closed_trades if t.pnl_usdt and t.pnl_usdt > 0)
        gross_loss = abs(sum(t.pnl_usdt for t in closed_trades if t.pnl_usdt and t.pnl_usdt < 0))

        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float('inf')

        # Average R-multiple
        r_multiples = [t.r_multiple for t in closed_trades if t.r_multiple]
        avg_r = sum(r_multiples) / len(r_multiples) if r_multiples else 0

        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'gross_profit': gross_profit,
            'gross_loss': gross_loss,
            'profit_factor': profit_factor,
            'avg_r_multiple': avg_r
        }

    # ==================== SYSTEM EVENTS ====================

    def log_event(self, event_type: str, severity: str, message: str,
                  details: Optional[str] = None, component: Optional[str] = None,
                  symbol: Optional[str] = None) -> bool:
        """
        Log a system event

        Args:
            event_type: Type of event (START, STOP, ERROR, etc.)
            severity: Severity level (INFO, WARNING, ERROR, CRITICAL)
            message: Event message
            details: Additional details
            component: Component that generated the event
            symbol: Related symbol (if applicable)

        Returns:
            True if successful
        """
        session = self.get_session()
        try:
            event = SystemEvent(
                event_type=event_type,
                severity=severity,
                message=message,
                details=details,
                component=component,
                symbol=symbol
            )
            session.add(event)
            session.commit()

            self.logger.debug(f"Event logged: {event_type} - {message}")
            return True

        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"Failed to log event: {e}")
            return False
        finally:
            session.close()

    def get_recent_events(self, limit: int = 100,
                         severity: Optional[str] = None) -> List[SystemEvent]:
        """
        Get recent system events

        Args:
            limit: Maximum number of events
            severity: Filter by severity

        Returns:
            List of system events
        """
        session = self.get_session()
        try:
            query = session.query(SystemEvent).order_by(desc(SystemEvent.timestamp))

            if severity:
                query = query.filter(SystemEvent.severity == severity)

            events = query.limit(limit).all()
            return events

        except SQLAlchemyError as e:
            self.logger.error(f"Failed to get recent events: {e}")
            return []
        finally:
            session.close()

    # ==================== UTILITY ====================

    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        session = self.get_session()
        try:
            total_trades = session.query(Trade).count()
            open_trades = session.query(Trade).filter(Trade.status == TradeStatus.OPEN).count()
            closed_trades = session.query(Trade).filter(Trade.status == TradeStatus.CLOSED).count()
            total_events = session.query(SystemEvent).count()

            return {
                'total_trades': total_trades,
                'open_trades': open_trades,
                'closed_trades': closed_trades,
                'total_events': total_events
            }

        except SQLAlchemyError as e:
            self.logger.error(f"Failed to get statistics: {e}")
            return {}
        finally:
            session.close()

    def close(self) -> None:
        """Close database connection"""
        self.engine.dispose()
        self.logger.info("Database connection closed")
