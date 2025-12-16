#!/usr/bin/env python3
"""
Weekly Performance Audit Script

Compares live trading results against backtest expectations.
Flags underperforming strategies for review.

Usage:
    python audit_performance.py                    # Audit last 7 days
    python audit_performance.py --days 14         # Audit last 14 days
    python audit_performance.py --since 2025-12-01  # Audit since date
"""

import pandas as pd
import numpy as np
import sqlite3
import argparse
from datetime import datetime, timedelta
from pathlib import Path
import json

# Backtest expectations per strategy (from our backtests)
BACKTEST_EXPECTATIONS = {
    'multi_timeframe_long': {
        'win_rate': 0.35,
        'avg_win_pct': 3.5,
        'avg_loss_pct': -1.2,
        'return_per_trade': 0.69,  # Expected avg return per trade
        'max_consecutive_losses': 5,
        'trades_per_week': 3,
        'min_acceptable_win_rate': 0.25,  # Alert threshold
        'max_acceptable_loss_streak': 7,
    },
    'trend_distance_short': {
        'win_rate': 0.38,
        'avg_win_pct': 4.2,
        'avg_loss_pct': -1.0,
        'return_per_trade': 0.98,
        'max_consecutive_losses': 4,
        'trades_per_week': 4,
        'min_acceptable_win_rate': 0.28,
        'max_acceptable_loss_streak': 6,
    },
    'moodeng_rsi_momentum': {
        'win_rate': 0.31,
        'avg_win_pct': 1.13,
        'avg_loss_pct': -0.31,
        'return_per_trade': 0.28,
        'max_consecutive_losses': 8,
        'trades_per_week': 30,
        'min_acceptable_win_rate': 0.22,
        'max_acceptable_loss_streak': 12,
    },
    'doge_volume_zones': {
        'win_rate': 0.52,
        'avg_win_pct': 0.8,
        'avg_loss_pct': -0.6,
        'return_per_trade': 0.33,
        'max_consecutive_losses': 4,
        'trades_per_week': 6,
        'min_acceptable_win_rate': 0.40,
        'max_acceptable_loss_streak': 6,
    },
    'pepe_volume_zones': {
        'win_rate': 0.667,
        'avg_win_pct': 0.6,
        'avg_loss_pct': -0.4,
        'return_per_trade': 0.27,
        'max_consecutive_losses': 3,
        'trades_per_week': 4,
        'min_acceptable_win_rate': 0.50,
        'max_acceptable_loss_streak': 5,
    },
    'trump_volume_zones': {
        'win_rate': 0.619,
        'avg_win_pct': 1.9,
        'avg_loss_pct': -0.6,
        'return_per_trade': 0.80,
        'max_consecutive_losses': 2,
        'trades_per_week': 5,
        'min_acceptable_win_rate': 0.45,
        'max_acceptable_loss_streak': 4,
    },
    'uni_volume_zones': {
        'win_rate': 0.451,
        'avg_win_pct': 1.2,
        'avg_loss_pct': -0.5,
        'return_per_trade': 0.32,
        'max_consecutive_losses': 5,
        'trades_per_week': 15,
        'min_acceptable_win_rate': 0.35,
        'max_acceptable_loss_streak': 8,
    },
}

# Alert thresholds
ALERT_THRESHOLDS = {
    'win_rate_deviation': 0.15,      # Alert if win rate is 15% below expected
    'avg_return_deviation': 0.30,    # Alert if avg return is 30% below expected
    'loss_streak_multiplier': 1.5,   # Alert if loss streak is 1.5x expected max
    'min_trades_for_significance': 10,  # Need at least 10 trades to judge
}


def load_live_trades(db_path: str, since: datetime) -> pd.DataFrame:
    """Load live trades from SQLite database"""
    conn = sqlite3.connect(db_path)

    query = """
    SELECT
        id,
        strategy,
        symbol,
        direction,
        entry_price,
        exit_price,
        entry_time,
        exit_time,
        pnl_pct,
        pnl_usdt,
        exit_reason,
        status
    FROM trades
    WHERE exit_time >= ?
    AND status = 'CLOSED'
    ORDER BY exit_time
    """

    df = pd.read_sql_query(query, conn, params=[since.isoformat()])
    conn.close()

    if len(df) > 0:
        df['entry_time'] = pd.to_datetime(df['entry_time'])
        df['exit_time'] = pd.to_datetime(df['exit_time'])
        df['is_winner'] = df['pnl_pct'] > 0

    return df


def calculate_live_metrics(trades: pd.DataFrame, strategy: str) -> dict:
    """Calculate performance metrics for a strategy's live trades"""
    strategy_trades = trades[trades['strategy'] == strategy]

    if len(strategy_trades) == 0:
        return None

    winners = strategy_trades[strategy_trades['is_winner']]
    losers = strategy_trades[~strategy_trades['is_winner']]

    # Calculate consecutive losses
    max_loss_streak = 0
    current_streak = 0
    for is_win in strategy_trades['is_winner']:
        if not is_win:
            current_streak += 1
            max_loss_streak = max(max_loss_streak, current_streak)
        else:
            current_streak = 0

    # Current loss streak (if still in one)
    current_loss_streak = 0
    for is_win in reversed(strategy_trades['is_winner'].tolist()):
        if not is_win:
            current_loss_streak += 1
        else:
            break

    return {
        'total_trades': len(strategy_trades),
        'winners': len(winners),
        'losers': len(losers),
        'win_rate': len(winners) / len(strategy_trades) if len(strategy_trades) > 0 else 0,
        'avg_win_pct': winners['pnl_pct'].mean() if len(winners) > 0 else 0,
        'avg_loss_pct': losers['pnl_pct'].mean() if len(losers) > 0 else 0,
        'total_return_pct': strategy_trades['pnl_pct'].sum(),
        'avg_return_per_trade': strategy_trades['pnl_pct'].mean(),
        'max_loss_streak': max_loss_streak,
        'current_loss_streak': current_loss_streak,
        'best_trade': strategy_trades['pnl_pct'].max(),
        'worst_trade': strategy_trades['pnl_pct'].min(),
        'total_pnl_usdt': strategy_trades['pnl_usdt'].sum(),
        'trades': strategy_trades.to_dict('records'),
    }


def compare_to_backtest(live_metrics: dict, expected: dict, strategy: str) -> dict:
    """Compare live metrics to backtest expectations and generate alerts"""
    alerts = []
    warnings = []
    status = 'OK'

    if live_metrics is None:
        return {
            'status': 'NO_DATA',
            'alerts': [],
            'warnings': ['No trades recorded for this strategy'],
            'metrics': None,
            'comparison': None,
        }

    n_trades = live_metrics['total_trades']

    # Check if we have enough trades for significance
    if n_trades < ALERT_THRESHOLDS['min_trades_for_significance']:
        warnings.append(f"Only {n_trades} trades - need {ALERT_THRESHOLDS['min_trades_for_significance']} for statistical significance")

    comparison = {}

    # Win rate comparison
    expected_wr = expected['win_rate']
    actual_wr = live_metrics['win_rate']
    wr_diff = actual_wr - expected_wr
    comparison['win_rate'] = {
        'expected': f"{expected_wr:.1%}",
        'actual': f"{actual_wr:.1%}",
        'diff': f"{wr_diff:+.1%}",
        'status': 'OK' if actual_wr >= expected['min_acceptable_win_rate'] else 'ALERT'
    }

    if actual_wr < expected['min_acceptable_win_rate']:
        alerts.append(f"Win rate {actual_wr:.1%} below minimum {expected['min_acceptable_win_rate']:.1%}")
        status = 'ALERT'
    elif wr_diff < -ALERT_THRESHOLDS['win_rate_deviation']:
        warnings.append(f"Win rate {wr_diff:+.1%} below expected")

    # Average return comparison
    expected_ret = expected['return_per_trade']
    actual_ret = live_metrics['avg_return_per_trade']
    ret_diff_pct = (actual_ret - expected_ret) / abs(expected_ret) if expected_ret != 0 else 0
    comparison['avg_return'] = {
        'expected': f"{expected_ret:.2f}%",
        'actual': f"{actual_ret:.2f}%",
        'diff': f"{ret_diff_pct:+.0%}",
        'status': 'OK' if ret_diff_pct >= -ALERT_THRESHOLDS['avg_return_deviation'] else 'WARNING'
    }

    if ret_diff_pct < -ALERT_THRESHOLDS['avg_return_deviation']:
        warnings.append(f"Avg return {ret_diff_pct:+.0%} below expected")
        if status == 'OK':
            status = 'WARNING'

    # Loss streak comparison
    max_expected_streak = expected['max_acceptable_loss_streak']
    actual_streak = live_metrics['max_loss_streak']
    comparison['loss_streak'] = {
        'expected_max': max_expected_streak,
        'actual_max': actual_streak,
        'current': live_metrics['current_loss_streak'],
        'status': 'OK' if actual_streak <= max_expected_streak else 'ALERT'
    }

    if actual_streak > max_expected_streak:
        alerts.append(f"Loss streak of {actual_streak} exceeds max expected {max_expected_streak}")
        status = 'ALERT'

    if live_metrics['current_loss_streak'] >= expected['max_consecutive_losses']:
        warnings.append(f"Currently in {live_metrics['current_loss_streak']}-trade loss streak")

    # Trade frequency comparison
    # (This would need to be calculated based on the time period)

    return {
        'status': status,
        'alerts': alerts,
        'warnings': warnings,
        'metrics': live_metrics,
        'comparison': comparison,
    }


def generate_report(results: dict, period_start: datetime, period_end: datetime) -> str:
    """Generate markdown audit report"""

    lines = [
        "# Weekly Performance Audit Report",
        f"**Period:** {period_start.strftime('%Y-%m-%d')} to {period_end.strftime('%Y-%m-%d')}",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
    ]

    # Summary
    total_trades = sum(r['metrics']['total_trades'] for r in results.values() if r['metrics'])
    total_pnl = sum(r['metrics']['total_pnl_usdt'] for r in results.values() if r['metrics'])
    alerts_count = sum(len(r['alerts']) for r in results.values())
    warnings_count = sum(len(r['warnings']) for r in results.values())

    lines.extend([
        "## Summary",
        f"- **Total Trades:** {total_trades}",
        f"- **Total P&L:** ${total_pnl:,.2f}",
        f"- **Alerts:** {alerts_count}",
        f"- **Warnings:** {warnings_count}",
        "",
    ])

    # Status overview
    lines.append("## Strategy Status")
    lines.append("")
    lines.append("| Strategy | Status | Trades | Win Rate | Avg Return | P&L |")
    lines.append("|----------|--------|--------|----------|------------|-----|")

    for strategy, result in results.items():
        if result['metrics']:
            m = result['metrics']
            status_emoji = {'OK': '✅', 'WARNING': '⚠️', 'ALERT': '🚨', 'NO_DATA': '❓'}[result['status']]
            lines.append(
                f"| {strategy} | {status_emoji} {result['status']} | {m['total_trades']} | "
                f"{m['win_rate']:.1%} | {m['avg_return_per_trade']:.2f}% | ${m['total_pnl_usdt']:.2f} |"
            )
        else:
            lines.append(f"| {strategy} | ❓ NO_DATA | 0 | - | - | - |")

    lines.append("")

    # Alerts section
    if alerts_count > 0:
        lines.append("## 🚨 ALERTS (Action Required)")
        lines.append("")
        for strategy, result in results.items():
            if result['alerts']:
                lines.append(f"### {strategy}")
                for alert in result['alerts']:
                    lines.append(f"- {alert}")
                lines.append("")

    # Warnings section
    if warnings_count > 0:
        lines.append("## ⚠️ Warnings (Monitor)")
        lines.append("")
        for strategy, result in results.items():
            if result['warnings']:
                lines.append(f"### {strategy}")
                for warning in result['warnings']:
                    lines.append(f"- {warning}")
                lines.append("")

    # Detailed comparison
    lines.append("## Detailed Comparison vs Backtest")
    lines.append("")

    for strategy, result in results.items():
        if result['comparison']:
            lines.append(f"### {strategy}")
            lines.append("")
            lines.append("| Metric | Expected | Actual | Diff | Status |")
            lines.append("|--------|----------|--------|------|--------|")

            for metric, data in result['comparison'].items():
                if isinstance(data, dict):
                    status_emoji = {'OK': '✅', 'WARNING': '⚠️', 'ALERT': '🚨'}[data['status']]
                    lines.append(
                        f"| {metric} | {data['expected']} | {data['actual']} | "
                        f"{data['diff']} | {status_emoji} |"
                    )
            lines.append("")

    # Recommendations
    lines.append("## Recommendations")
    lines.append("")

    for strategy, result in results.items():
        if result['status'] == 'ALERT':
            lines.append(f"### {strategy} - REVIEW REQUIRED")
            lines.append("- Consider pausing this strategy")
            lines.append("- Check if market conditions have changed")
            lines.append("- Review recent losing trades for patterns")
            lines.append("- Compare signal quality vs backtest period")
            lines.append("")
        elif result['status'] == 'WARNING':
            lines.append(f"### {strategy} - MONITOR CLOSELY")
            lines.append("- Continue running but watch next 5-10 trades")
            lines.append("- If performance doesn't improve, reduce position size")
            lines.append("")

    # Action items
    lines.extend([
        "## Next Steps",
        "",
        "1. Review any ALERT strategies immediately",
        "2. For underperforming strategies, check:",
        "   - Volume patterns still valid?",
        "   - Session timing still optimal?",
        "   - Volatility regime changed?",
        "3. Consider running fresh optimization on 7-day data",
        "4. Schedule next audit: " + (period_end + timedelta(days=7)).strftime('%Y-%m-%d'),
        "",
    ])

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description='Weekly Performance Audit')
    parser.add_argument('--days', type=int, default=7, help='Number of days to audit')
    parser.add_argument('--since', type=str, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--db', type=str, default='./data/trades.db', help='Path to trades database')
    parser.add_argument('--output', type=str, default='./audit_report.md', help='Output report path')
    args = parser.parse_args()

    # Determine audit period
    if args.since:
        period_start = datetime.strptime(args.since, '%Y-%m-%d')
    else:
        period_start = datetime.now() - timedelta(days=args.days)

    period_end = datetime.now()

    print(f"🔍 Auditing performance from {period_start.strftime('%Y-%m-%d')} to {period_end.strftime('%Y-%m-%d')}")
    print()

    # Load live trades
    db_path = Path(args.db)
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        print("   Make sure the trading bot has logged trades to the database.")
        return

    trades = load_live_trades(str(db_path), period_start)
    print(f"📊 Loaded {len(trades)} trades from database")

    if len(trades) == 0:
        print("⚠️ No trades found in the specified period")
        return

    # Analyze each strategy
    results = {}
    for strategy, expected in BACKTEST_EXPECTATIONS.items():
        live_metrics = calculate_live_metrics(trades, strategy)
        results[strategy] = compare_to_backtest(live_metrics, expected, strategy)

    # Print summary to console
    print()
    print("=" * 60)
    print("AUDIT SUMMARY")
    print("=" * 60)

    for strategy, result in results.items():
        status_emoji = {'OK': '✅', 'WARNING': '⚠️', 'ALERT': '🚨', 'NO_DATA': '❓'}[result['status']]
        if result['metrics']:
            m = result['metrics']
            print(f"{status_emoji} {strategy}: {m['total_trades']} trades, "
                  f"{m['win_rate']:.1%} WR, ${m['total_pnl_usdt']:.2f} P&L")
        else:
            print(f"{status_emoji} {strategy}: No trades")

        for alert in result['alerts']:
            print(f"   🚨 {alert}")
        for warning in result['warnings']:
            print(f"   ⚠️ {warning}")

    print()

    # Generate and save report
    report = generate_report(results, period_start, period_end)

    output_path = Path(args.output)
    output_path.write_text(report)
    print(f"📝 Report saved to: {output_path}")

    # Also save as timestamped file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    archive_path = output_path.parent / f"audit_{timestamp}.md"
    archive_path.write_text(report)
    print(f"📁 Archived to: {archive_path}")

    # Return exit code based on alerts
    alert_count = sum(len(r['alerts']) for r in results.values())
    if alert_count > 0:
        print(f"\n⚠️ {alert_count} alerts require attention!")
        return 1

    print("\n✅ All strategies performing within expectations")
    return 0


if __name__ == '__main__':
    exit(main())
