"""
Performance Metrics Tracking

Tracks and calculates real-time performance metrics
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import logging


@dataclass
class PositionMetrics:
    """Metrics for a single position"""
    entry_time: datetime
    entry_price: float
    current_price: float
    quantity: float
    side: str
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0
    r_multiple: float = 0.0
    hours_held: float = 0.0


@dataclass
class StrategyMetrics:
    """Metrics for a strategy"""
    name: str
    enabled: bool = True
    total_signals: int = 0
    trades_opened: int = 0
    trades_closed: int = 0
    wins: int = 0
    losses: int = 0
    breakeven: int = 0
    total_pnl: float = 0.0
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    avg_r_multiple: float = 0.0
    best_trade: float = 0.0
    worst_trade: float = 0.0
    current_streak: int = 0  # Positive = wins, negative = losses


class PerformanceTracker:
    """
    Real-time performance tracking

    Tracks portfolio performance, drawdown, and strategy metrics
    """

    def __init__(self, initial_capital: float):
        """
        Initialize performance tracker

        Args:
            initial_capital: Starting capital
        """
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.peak_capital = initial_capital

        # Equity curve
        self.equity_history: List[Dict[str, Any]] = []

        # Drawdown tracking
        self.current_drawdown = 0.0
        self.max_drawdown = 0.0
        self.max_drawdown_pct = 0.0

        # Trade statistics
        self.total_trades = 0
        self.open_positions: Dict[int, PositionMetrics] = {}

        # Strategy metrics
        self.strategy_metrics: Dict[str, StrategyMetrics] = {}

        # Daily statistics
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.daily_wins = 0
        self.daily_losses = 0
        self.last_reset_date = datetime.utcnow().date()

        # Session tracking
        self.session_start = datetime.utcnow()

        self.logger = logging.getLogger(__name__)

    def register_strategy(self, strategy_name: str) -> None:
        """Register a strategy for tracking"""
        if strategy_name not in self.strategy_metrics:
            self.strategy_metrics[strategy_name] = StrategyMetrics(name=strategy_name)
            self.logger.info(f"Strategy registered: {strategy_name}")

    def record_signal(self, strategy_name: str) -> None:
        """Record a trading signal"""
        if strategy_name in self.strategy_metrics:
            self.strategy_metrics[strategy_name].total_signals += 1

    def add_position(self, position_id: int, strategy: str, side: str,
                    entry_price: float, quantity: float,
                    entry_time: datetime) -> None:
        """
        Add an open position

        Args:
            position_id: Unique position ID
            strategy: Strategy name
            side: LONG or SHORT
            entry_price: Entry price
            quantity: Position size
            entry_time: Entry timestamp
        """
        self.open_positions[position_id] = PositionMetrics(
            entry_time=entry_time,
            entry_price=entry_price,
            current_price=entry_price,
            quantity=quantity,
            side=side
        )

        # Update strategy metrics
        if strategy in self.strategy_metrics:
            self.strategy_metrics[strategy].trades_opened += 1

        self.logger.debug(f"Position added: {position_id} ({strategy} {side})")

    def update_position(self, position_id: int, current_price: float) -> None:
        """
        Update position with current price

        Args:
            position_id: Position ID
            current_price: Current market price
        """
        if position_id not in self.open_positions:
            return

        pos = self.open_positions[position_id]
        pos.current_price = current_price

        # Calculate unrealized P&L
        if pos.side == 'LONG':
            pos.unrealized_pnl = (current_price - pos.entry_price) * pos.quantity
        else:  # SHORT
            pos.unrealized_pnl = (pos.entry_price - current_price) * pos.quantity

        pos.unrealized_pnl_pct = (pos.unrealized_pnl / (pos.entry_price * pos.quantity)) * 100

        # Calculate hours held
        pos.hours_held = (datetime.utcnow() - pos.entry_time).total_seconds() / 3600

    def close_position(self, position_id: int, strategy: str,
                      exit_price: float, pnl: float, r_multiple: float) -> None:
        """
        Close a position and update metrics

        Args:
            position_id: Position ID
            strategy: Strategy name
            exit_price: Exit price
            pnl: Realized P&L
            r_multiple: R-multiple achieved
        """
        # Remove from open positions
        if position_id in self.open_positions:
            del self.open_positions[position_id]

        # Update capital
        self.current_capital += pnl

        # Update peak and drawdown
        if self.current_capital > self.peak_capital:
            self.peak_capital = self.current_capital

        self.current_drawdown = self.peak_capital - self.current_capital
        self.current_drawdown_pct = (self.current_drawdown / self.peak_capital) * 100

        if self.current_drawdown > self.max_drawdown:
            self.max_drawdown = self.current_drawdown
            self.max_drawdown_pct = self.current_drawdown_pct

        # Update trade count
        self.total_trades += 1
        self.daily_trades += 1

        # Update strategy metrics
        if strategy in self.strategy_metrics:
            metrics = self.strategy_metrics[strategy]
            metrics.trades_closed += 1
            metrics.total_pnl += pnl

            if pnl > 0:
                metrics.wins += 1
                metrics.gross_profit += pnl
                metrics.current_streak = max(1, metrics.current_streak + 1)
                self.daily_wins += 1

                if pnl > metrics.best_trade:
                    metrics.best_trade = pnl

            elif pnl < 0:
                metrics.losses += 1
                metrics.gross_loss += abs(pnl)
                metrics.current_streak = min(-1, metrics.current_streak - 1)
                self.daily_losses += 1

                if pnl < metrics.worst_trade:
                    metrics.worst_trade = pnl

            else:
                metrics.breakeven += 1
                metrics.current_streak = 0

            # Recalculate derived metrics
            total_closed = metrics.trades_closed
            if total_closed > 0:
                metrics.win_rate = (metrics.wins / total_closed) * 100

            if metrics.gross_loss > 0:
                metrics.profit_factor = metrics.gross_profit / metrics.gross_loss
            else:
                metrics.profit_factor = float('inf') if metrics.gross_profit > 0 else 0

            # Average win/loss
            if metrics.wins > 0:
                metrics.avg_win = metrics.gross_profit / metrics.wins

            if metrics.losses > 0:
                metrics.avg_loss = metrics.gross_loss / metrics.losses

        # Update daily P&L
        self.daily_pnl += pnl

        # Record equity point
        self.record_equity_point()

        self.logger.info(f"Position closed: {position_id} ({strategy}) | "
                        f"PnL: {pnl:+.2f} USDT | Capital: {self.current_capital:.2f}")

    def record_equity_point(self) -> None:
        """Record current equity for equity curve"""
        self.equity_history.append({
            'timestamp': datetime.utcnow(),
            'capital': self.current_capital,
            'drawdown': self.current_drawdown,
            'drawdown_pct': self.current_drawdown_pct,
            'open_positions': len(self.open_positions)
        })

    def reset_daily_stats(self) -> None:
        """Reset daily statistics (called at start of new day)"""
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.daily_wins = 0
        self.daily_losses = 0
        self.last_reset_date = datetime.utcnow().date()
        self.logger.info("Daily statistics reset")

    def check_daily_reset(self) -> None:
        """Check if we need to reset daily stats"""
        current_date = datetime.utcnow().date()
        if current_date > self.last_reset_date:
            self.reset_daily_stats()

    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        # Calculate total unrealized P&L
        unrealized_pnl = sum(pos.unrealized_pnl for pos in self.open_positions.values())

        # Calculate total return
        total_return = self.current_capital - self.initial_capital
        total_return_pct = (total_return / self.initial_capital) * 100

        # Calculate session duration
        session_duration = datetime.utcnow() - self.session_start
        hours = session_duration.total_seconds() / 3600

        # Aggregate strategy metrics
        total_signals = sum(m.total_signals for m in self.strategy_metrics.values())

        # Daily win rate
        daily_win_rate = (self.daily_wins / self.daily_trades * 100) if self.daily_trades > 0 else 0

        return {
            'capital': {
                'initial': self.initial_capital,
                'current': self.current_capital,
                'peak': self.peak_capital,
                'total_return': total_return,
                'total_return_pct': total_return_pct,
                'unrealized_pnl': unrealized_pnl
            },
            'drawdown': {
                'current': self.current_drawdown,
                'current_pct': self.current_drawdown_pct,
                'max': self.max_drawdown,
                'max_pct': self.max_drawdown_pct
            },
            'trades': {
                'total': self.total_trades,
                'open_positions': len(self.open_positions)
            },
            'daily': {
                'pnl': self.daily_pnl,
                'trades': self.daily_trades,
                'wins': self.daily_wins,
                'losses': self.daily_losses,
                'win_rate': daily_win_rate
            },
            'session': {
                'start': self.session_start,
                'duration_hours': hours
            },
            'signals': {
                'total': total_signals
            }
        }

    def get_strategy_summary(self, strategy_name: str) -> Optional[Dict[str, Any]]:
        """Get summary for a specific strategy"""
        if strategy_name not in self.strategy_metrics:
            return None

        metrics = self.strategy_metrics[strategy_name]

        return {
            'name': metrics.name,
            'enabled': metrics.enabled,
            'signals': metrics.total_signals,
            'trades': {
                'opened': metrics.trades_opened,
                'closed': metrics.trades_closed,
                'wins': metrics.wins,
                'losses': metrics.losses,
                'breakeven': metrics.breakeven
            },
            'performance': {
                'total_pnl': metrics.total_pnl,
                'gross_profit': metrics.gross_profit,
                'gross_loss': metrics.gross_loss,
                'win_rate': metrics.win_rate,
                'profit_factor': metrics.profit_factor,
                'avg_win': metrics.avg_win,
                'avg_loss': metrics.avg_loss,
                'best_trade': metrics.best_trade,
                'worst_trade': metrics.worst_trade
            },
            'current_streak': metrics.current_streak
        }

    def print_dashboard(self) -> None:
        """Print performance dashboard to console"""
        summary = self.get_summary()

        print("\n" + "=" * 70)
        print("TRADING ENGINE STATUS")
        print("=" * 70)

        # Session info
        hours = summary['session']['duration_hours']
        print(f"\nUptime: {int(hours)}h {int((hours % 1) * 60)}m")

        # Capital
        cap = summary['capital']
        print(f"\nCapital:")
        print(f"  Current:       ${cap['current']:,.2f}")
        print(f"  Peak:          ${cap['peak']:,.2f}")
        print(f"  Total Return:  ${cap['total_return']:+,.2f} ({cap['total_return_pct']:+.2f}%)")
        print(f"  Unrealized:    ${cap['unrealized_pnl']:+,.2f}")

        # Drawdown
        dd = summary['drawdown']
        print(f"\nDrawdown:")
        print(f"  Current:  {dd['current_pct']:.2f}%")
        print(f"  Max:      {dd['max_pct']:.2f}%")

        # Open positions
        print(f"\nOpen Positions: {summary['trades']['open_positions']}")
        for pos_id, pos in self.open_positions.items():
            print(f"  - {pos.side} @ {pos.entry_price:.8f} | "
                  f"PnL: {pos.unrealized_pnl:+.2f} ({pos.unrealized_pnl_pct:+.2f}%) | "
                  f"{pos.r_multiple:+.2f}R | {pos.hours_held:.1f}h")

        # Daily stats
        daily = summary['daily']
        print(f"\nToday's Stats:")
        print(f"  Trades:    {daily['trades']} ({daily['wins']}W / {daily['losses']}L)")
        print(f"  Win Rate:  {daily['win_rate']:.1f}%")
        print(f"  P&L:       ${daily['pnl']:+,.2f}")

        # Strategy breakdown
        print(f"\nStrategies:")
        for name, metrics in self.strategy_metrics.items():
            if metrics.enabled:
                print(f"  {name}:")
                print(f"    Trades:        {metrics.trades_closed} ({metrics.wins}W / {metrics.losses}L)")
                print(f"    Win Rate:      {metrics.win_rate:.1f}%")
                print(f"    Profit Factor: {metrics.profit_factor:.2f}")
                print(f"    P&L:           ${metrics.total_pnl:+,.2f}")

        print("=" * 70 + "\n")
