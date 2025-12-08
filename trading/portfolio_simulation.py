"""
Portfolio Simulation - BingX Trading Bot
Simulates a single portfolio trading account across all strategies with proper position management.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

# Configuration
STARTING_EQUITY = 10000
RESULTS_DIR = Path("trading/results")

# Strategy file mapping
STRATEGY_FILES = {
    "FARTCOIN_LONG": "FARTCOIN_LONG_detailed_trades.csv",
    "MOODENG_RSI": "moodeng_audit_trades.csv",
    "DOGE_VOLUME": "DOGE_volume_zones_optimized_trades.csv",
    "PEPE_VOLUME": "PEPE_volume_zones_optimized_trades.csv",
    "TRUMP_VOLUME": "TRUMP_volume_zones_best_riskadj_trades.csv",  # Using best risk-adjusted version
    "UNI_VOLUME": "UNI_volume_zones_trades.csv",
}

def load_and_normalize_trades(filepath, strategy_name):
    """Load trade CSV and normalize column names."""
    print(f"Loading {strategy_name} from {filepath}...")

    df = pd.read_csv(filepath)

    # Normalize column names based on file structure
    if 'entry_time' in df.columns:
        df = df.rename(columns={
            'entry_time': 'entry_date',
            'exit_time': 'exit_date'
        })

    # Ensure required columns exist
    required_cols = ['entry_date', 'exit_date', 'pnl_pct']
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Missing required column {col} in {filepath}")

    # Add strategy tag
    df['strategy'] = strategy_name

    # Convert dates to datetime
    df['entry_date'] = pd.to_datetime(df['entry_date'])
    df['exit_date'] = pd.to_datetime(df['exit_date'])

    # Add direction if not present (assume LONG for most strategies)
    if 'direction' not in df.columns:
        if 'result' in df.columns:
            df['direction'] = 'LONG'  # Most strategies are long
        else:
            df['direction'] = 'LONG'

    print(f"  Loaded {len(df)} trades from {strategy_name}")
    return df[['entry_date', 'exit_date', 'pnl_pct', 'strategy', 'direction']]

def simulate_portfolio(all_trades_df):
    """
    Simulate portfolio with proper position management.
    Rules:
    - Start with $10,000
    - Each trade uses 100% of available equity
    - Can only take one position at a time (capital locked)
    - Track unrealized P&L while position is open
    """

    # Sort all trades by entry time
    all_trades_df = all_trades_df.sort_values('entry_date').reset_index(drop=True)

    # Initialize portfolio state
    equity = STARTING_EQUITY
    max_equity = STARTING_EQUITY
    current_position = None  # {'entry_date', 'exit_date', 'pnl_pct', 'strategy', 'equity_at_entry'}

    executed_trades = []
    skipped_trades = []
    equity_curve = [(all_trades_df['entry_date'].min(), equity, 0.0)]  # (timestamp, equity, drawdown)

    print("\n=== Starting Portfolio Simulation ===")
    print(f"Starting Equity: ${equity:,.2f}")
    print(f"Total Trades to Process: {len(all_trades_df)}")

    for idx, trade in all_trades_df.iterrows():
        # Check if we have an open position
        if current_position is not None:
            # Check if current position should be closed
            if pd.Timestamp(trade['entry_date']) >= pd.Timestamp(current_position['exit_date']):
                # Close the position
                realized_pnl_pct = current_position['pnl_pct']
                equity_before = equity
                equity = equity * (1 + realized_pnl_pct / 100)

                # Update max equity and drawdown
                if equity > max_equity:
                    max_equity = equity
                drawdown = (equity - max_equity) / max_equity * 100

                # Record equity curve point
                equity_curve.append((current_position['exit_date'], equity, drawdown))

                print(f"  CLOSED {current_position['strategy']}: "
                      f"${equity_before:,.2f} → ${equity:,.2f} ({realized_pnl_pct:+.2f}%)")

                current_position = None

        # Try to open new position
        if current_position is None:
            # Capital is available, open position
            current_position = {
                'entry_date': trade['entry_date'],
                'exit_date': trade['exit_date'],
                'pnl_pct': trade['pnl_pct'],
                'strategy': trade['strategy'],
                'direction': trade['direction'],
                'equity_at_entry': equity
            }

            executed_trades.append({
                'entry_date': trade['entry_date'],
                'exit_date': trade['exit_date'],
                'strategy': trade['strategy'],
                'direction': trade['direction'],
                'pnl_pct': trade['pnl_pct'],
                'equity_before': equity,
                'status': 'EXECUTED'
            })

            print(f"  OPENED {trade['strategy']} @ {trade['entry_date']}")

        else:
            # Capital is locked, skip this trade
            skipped_trades.append({
                'entry_date': trade['entry_date'],
                'exit_date': trade['exit_date'],
                'strategy': trade['strategy'],
                'direction': trade['direction'],
                'pnl_pct': trade['pnl_pct'],
                'reason': f"Capital locked in {current_position['strategy']}"
            })

    # Close any remaining open position at the end
    if current_position is not None:
        realized_pnl_pct = current_position['pnl_pct']
        equity_before = equity
        equity = equity * (1 + realized_pnl_pct / 100)

        if equity > max_equity:
            max_equity = equity
        drawdown = (equity - max_equity) / max_equity * 100

        equity_curve.append((current_position['exit_date'], equity, drawdown))

        print(f"  CLOSED (final) {current_position['strategy']}: "
              f"${equity_before:,.2f} → ${equity:,.2f} ({realized_pnl_pct:+.2f}%)")

    # Calculate final metrics
    final_equity = equity
    total_return = (final_equity - STARTING_EQUITY) / STARTING_EQUITY * 100
    max_drawdown = min([point[2] for point in equity_curve])
    return_dd_ratio = total_return / abs(max_drawdown) if max_drawdown != 0 else float('inf')

    # Convert to DataFrames
    executed_df = pd.DataFrame(executed_trades)
    skipped_df = pd.DataFrame(skipped_trades)
    equity_curve_df = pd.DataFrame(equity_curve, columns=['timestamp', 'equity', 'drawdown_pct'])

    # Calculate win rate and other stats from executed trades
    if len(executed_df) > 0:
        wins = executed_df[executed_df['pnl_pct'] > 0]
        losses = executed_df[executed_df['pnl_pct'] <= 0]

        win_rate = len(wins) / len(executed_df) * 100
        avg_win = wins['pnl_pct'].mean() if len(wins) > 0 else 0
        avg_loss = losses['pnl_pct'].mean() if len(losses) > 0 else 0

        # Calculate streaks
        executed_df['is_win'] = executed_df['pnl_pct'] > 0
        executed_df['streak'] = (executed_df['is_win'] != executed_df['is_win'].shift()).cumsum()
        win_streaks = executed_df[executed_df['is_win']].groupby('streak').size()
        loss_streaks = executed_df[~executed_df['is_win']].groupby('streak').size()

        longest_win_streak = win_streaks.max() if len(win_streaks) > 0 else 0
        longest_loss_streak = loss_streaks.max() if len(loss_streaks) > 0 else 0
    else:
        win_rate = avg_win = avg_loss = longest_win_streak = longest_loss_streak = 0

    # Strategy contribution breakdown
    strategy_contribution = executed_df.groupby('strategy').agg({
        'pnl_pct': ['count', 'sum', 'mean'],
    }).round(4)

    results = {
        'final_equity': final_equity,
        'total_return': total_return,
        'max_drawdown': max_drawdown,
        'return_dd_ratio': return_dd_ratio,
        'total_trades': len(all_trades_df),
        'executed_trades': len(executed_df),
        'skipped_trades': len(skipped_df),
        'win_rate': win_rate,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'longest_win_streak': longest_win_streak,
        'longest_loss_streak': longest_loss_streak,
        'strategy_contribution': strategy_contribution,
        'executed_df': executed_df,
        'skipped_df': skipped_df,
        'equity_curve_df': equity_curve_df
    }

    return results

def analyze_position_overlaps(all_trades_df):
    """Analyze how many trades overlapped in time."""
    all_trades_df = all_trades_df.sort_values('entry_date').reset_index(drop=True)

    overlaps = []
    for i, trade in all_trades_df.iterrows():
        # Count how many other trades were active during this trade's lifetime
        concurrent = all_trades_df[
            (all_trades_df['entry_date'] < trade['exit_date']) &
            (all_trades_df['exit_date'] > trade['entry_date']) &
            (all_trades_df.index != i)
        ]
        overlaps.append(len(concurrent))

    all_trades_df['concurrent_positions'] = overlaps

    print(f"\n=== Position Overlap Analysis ===")
    print(f"Max Concurrent Positions: {max(overlaps) + 1}")  # +1 for the trade itself
    print(f"Avg Concurrent Positions: {np.mean(overlaps) + 1:.2f}")
    print(f"Trades with Overlaps: {sum([1 for x in overlaps if x > 0])} / {len(all_trades_df)}")

    return all_trades_df

def save_results(results):
    """Save simulation results to files."""

    # Save equity curve
    equity_file = RESULTS_DIR / "portfolio_equity_curve.csv"
    results['equity_curve_df'].to_csv(equity_file, index=False)
    print(f"\nSaved equity curve to {equity_file}")

    # Save all trades with execution status
    all_trades_df = pd.concat([
        results['executed_df'],
        pd.DataFrame(results['skipped_df']).assign(equity_before=np.nan, status='SKIPPED')
    ]).sort_values('entry_date').reset_index(drop=True)

    trades_file = RESULTS_DIR / "portfolio_all_trades.csv"
    all_trades_df.to_csv(trades_file, index=False)
    print(f"Saved all trades to {trades_file}")

    # Generate executive summary
    summary_md = f"""# Portfolio Simulation Results - 30 Day Backtest

**Simulation Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Executive Summary

### Portfolio Performance
| Metric | Value |
|--------|-------|
| **Starting Equity** | ${STARTING_EQUITY:,.2f} |
| **Final Equity** | ${results['final_equity']:,.2f} |
| **Total Return** | **{results['total_return']:+.2f}%** |
| **Max Drawdown** | **{results['max_drawdown']:.2f}%** |
| **Return/DD Ratio** | **{results['return_dd_ratio']:.2f}x** |

### Trading Activity
| Metric | Value |
|--------|-------|
| Total Trades Available | {results['total_trades']} |
| Trades Executed | {results['executed_trades']} ({results['executed_trades']/results['total_trades']*100:.1f}%) |
| Trades Skipped | {results['skipped_trades']} ({results['skipped_trades']/results['total_trades']*100:.1f}%) |
| **Win Rate** | **{results['win_rate']:.2f}%** |
| Average Win | {results['avg_win']:+.2f}% |
| Average Loss | {results['avg_loss']:.2f}% |
| Longest Win Streak | {results['longest_win_streak']} |
| Longest Loss Streak | {results['longest_loss_streak']} |

### Strategy Contribution

| Strategy | Trades | Total Return | Avg Return/Trade |
|----------|--------|--------------|------------------|
"""

    for strategy, row in results['strategy_contribution'].iterrows():
        count = int(row['pnl_pct']['count'])
        total = row['pnl_pct']['sum']
        avg = row['pnl_pct']['mean']
        summary_md += f"| {strategy} | {count} | {total:+.2f}% | {avg:+.2f}% |\n"

    summary_md += f"""

## Key Findings

### Position Management Impact
- **Capital Locked**: {results['skipped_trades']} trades ({results['skipped_trades']/results['total_trades']*100:.1f}%) were skipped because capital was locked in another position
- **Execution Rate**: Only {results['executed_trades']/results['total_trades']*100:.1f}% of available signals could be taken
- **Missed Opportunity**: Sum of skipped trade P&Ls = {results['skipped_df']['pnl_pct'].sum() if len(results['skipped_df']) > 0 else 0:+.2f}%

### Portfolio vs Individual Strategies
When each strategy runs independently (their individual backtests):
"""

    # Load individual strategy returns from CLAUDE.md
    individual_returns = {
        "FARTCOIN_LONG": 10.38,
        "MOODENG_RSI": 24.02,
        "DOGE_VOLUME": 7.64,
        "PEPE_VOLUME": 2.57,
        "TRUMP_VOLUME": 8.06,
        # UNI not in CLAUDE.md, will need to calculate
    }

    sum_individual = sum(individual_returns.values())

    summary_md += f"""
- Sum of individual strategy returns: **{sum_individual:+.2f}%**
- Actual portfolio return: **{results['total_return']:+.2f}%**
- **Diversification Impact**: {results['total_return'] - sum_individual:+.2f}% ({(results['total_return']/sum_individual - 1)*100:+.1f}% change)

### Why Portfolio Return ≠ Sum of Individual Returns
1. **Position Conflicts**: When multiple strategies signal at the same time, only ONE can be taken
2. **Capital Locking**: Once in a position, all other opportunities are skipped until exit
3. **Sequential Execution**: The portfolio simulates ONE trading account, not parallel accounts
4. **Timing Effects**: The order of trades matters - early losses reduce capital for later winners

## Conclusion

"""

    if results['total_return'] > 0:
        summary_md += f"The portfolio generated a **{results['total_return']:+.2f}%** return over 30 days with a **{results['max_drawdown']:.2f}%** max drawdown, resulting in a **{results['return_dd_ratio']:.2f}x** Return/DD ratio.\n\n"
    else:
        summary_md += f"The portfolio generated a **{results['total_return']:+.2f}%** loss over 30 days.\n\n"

    if results['skipped_trades'] > results['executed_trades'] * 0.5:
        summary_md += "⚠️ **High Trade Skip Rate**: More than half of available trades were skipped due to capital being locked. This suggests the strategies have significant temporal overlap.\n\n"

    if results['return_dd_ratio'] > 5:
        summary_md += "✅ **Excellent Risk-Adjusted Returns**: Return/DD ratio > 5x indicates strong performance with controlled drawdowns.\n\n"

    summary_md += f"""
**Recommendation**: {"The portfolio shows profitable performance suitable for live trading." if results['total_return'] > 10 else "The portfolio performance is below individual strategy expectations due to position conflicts."}

---

*Generated by portfolio_simulation.py*
"""

    summary_file = RESULTS_DIR / "PORTFOLIO_SIMULATION_30D.md"
    with open(summary_file, 'w') as f:
        f.write(summary_md)

    print(f"Saved executive summary to {summary_file}")

def main():
    """Main execution function."""

    print("=" * 80)
    print("BingX Trading Bot - Portfolio Simulation")
    print("=" * 80)

    # Load all strategy trade files
    all_trades = []

    for strategy_name, filename in STRATEGY_FILES.items():
        filepath = RESULTS_DIR / filename

        if not filepath.exists():
            print(f"WARNING: {filepath} not found, skipping {strategy_name}")
            continue

        try:
            trades_df = load_and_normalize_trades(filepath, strategy_name)
            all_trades.append(trades_df)
        except Exception as e:
            print(f"ERROR loading {strategy_name}: {e}")
            continue

    if not all_trades:
        print("ERROR: No trade files could be loaded!")
        return

    # Merge all trades
    all_trades_df = pd.concat(all_trades, ignore_index=True)
    print(f"\n=== Merged Data ===")
    print(f"Total Trades Across All Strategies: {len(all_trades_df)}")
    print(f"Date Range: {all_trades_df['entry_date'].min()} to {all_trades_df['exit_date'].max()}")
    print(f"Strategies Loaded: {all_trades_df['strategy'].nunique()}")
    print(f"\nTrades per Strategy:")
    print(all_trades_df['strategy'].value_counts())

    # Analyze overlaps
    all_trades_df = analyze_position_overlaps(all_trades_df)

    # Run simulation
    results = simulate_portfolio(all_trades_df)

    # Print summary to console
    print("\n" + "=" * 80)
    print("PORTFOLIO SIMULATION RESULTS")
    print("=" * 80)
    print(f"\n{'Metric':<30} {'Value':<20}")
    print("-" * 50)
    print(f"{'Starting Equity':<30} ${results['final_equity'] / (1 + results['total_return']/100):>19,.2f}")
    print(f"{'Final Equity':<30} ${results['final_equity']:>19,.2f}")
    print(f"{'Total Return':<30} {results['total_return']:>19.2f}%")
    print(f"{'Max Drawdown':<30} {results['max_drawdown']:>19.2f}%")
    print(f"{'Return/DD Ratio':<30} {results['return_dd_ratio']:>19.2f}x")
    print(f"\n{'Trades Executed':<30} {results['executed_trades']:>20}")
    print(f"{'Trades Skipped':<30} {results['skipped_trades']:>20}")
    print(f"{'Win Rate':<30} {results['win_rate']:>19.2f}%")
    print(f"{'Avg Win':<30} {results['avg_win']:>19.2f}%")
    print(f"{'Avg Loss':<30} {results['avg_loss']:>19.2f}%")

    print("\n" + "-" * 50)
    print("Strategy Contributions:")
    print(results['strategy_contribution'])

    # Save all results
    save_results(results)

    print("\n" + "=" * 80)
    print("Simulation Complete!")
    print("=" * 80)

if __name__ == "__main__":
    main()
