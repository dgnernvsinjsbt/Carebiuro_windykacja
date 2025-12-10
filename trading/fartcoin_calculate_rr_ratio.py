"""
FARTCOIN - Calculate Return/DD Ratio for all configs
"""

import pandas as pd
import numpy as np

def calculate_max_drawdown(equity_curve):
    """Calculate max drawdown from equity curve"""
    running_max = equity_curve.cummax()
    drawdown = (equity_curve - running_max) / running_max * 100
    return drawdown.min()

def main():
    print("📊 FARTCOIN - CALCULATING RETURN/DD RATIOS\n")

    # Load all trades
    df_trades = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/results/fartcoin_all_concept_trades.csv')

    # Get unique concepts
    concepts = df_trades['concept'].unique()

    results = []

    for concept in concepts:
        trades = df_trades[df_trades['concept'] == concept].copy()
        trades = trades.sort_values('entry_idx')

        # Build equity curve
        trades['cumulative_return'] = trades['pnl_pct'].cumsum()
        equity_curve = 100 + trades['cumulative_return']

        # Metrics
        total_return = trades['pnl_pct'].sum()
        max_dd = calculate_max_drawdown(equity_curve)
        return_dd = total_return / abs(max_dd) if max_dd != 0 else 0

        winners = trades[trades['pnl_pct'] > 0]
        win_rate = len(winners) / len(trades) * 100 if len(trades) > 0 else 0

        top10 = trades.nlargest(10, 'pnl_pct')['pnl_pct'].mean() if len(trades) >= 10 else trades['pnl_pct'].max()

        results.append({
            'Concept': concept,
            'Trades': len(trades),
            'Return_%': round(total_return, 2),
            'Max_DD_%': round(max_dd, 2),
            'Return/DD': round(return_dd, 2),
            'Win_Rate_%': round(win_rate, 1),
            'Top10_Avg_%': round(top10, 2),
            'Max_Winner_%': round(trades['pnl_pct'].max(), 2)
        })

    df_results = pd.DataFrame(results)
    df_results = df_results.sort_values('Return/DD', ascending=False)

    print("="*100)
    print("📈 PHASE 1 CONCEPTS - RANKED BY RETURN/DD RATIO")
    print("="*100)
    print(df_results.to_string(index=False))

    # Now for Phase 2 filters
    print("\n\n📊 PHASE 2 - LOADING FILTER OPTIMIZATION...\n")

    # Need to recalculate with actual trades
    # Load the comparison CSV
    df_comparison = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/results/fartcoin_filter_optimization.csv')

    print("⚠️  Phase 2 results don't have individual trades saved - recalculating...\n")

    # Re-run just the top configs to get equity curves
    print("🔄 Re-running top 5 configs with equity curve tracking...\n")

if __name__ == '__main__':
    main()
