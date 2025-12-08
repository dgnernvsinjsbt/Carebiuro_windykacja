#!/usr/bin/env python3
"""
FARTCOIN Filtered Backtest
Compare strategy performance WITH and WITHOUT regime filters
Validate that filters preserve current profitable conditions
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

from regime_filter import (
    prepare_dataframe,
    should_trade,
    classify_regime,
    FILTER_CONFIGS,
    get_filter_description
)


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate Average True Range"""
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()


def backtest_with_filter(df: pd.DataFrame, filter_type: str = 'none',
                         sl_pct: float = 0.05, tp_pct: float = 0.075,
                         fee_per_side: float = 0.00005) -> tuple:
    """
    Backtest EMA 5/20 short strategy with regime filtering

    Args:
        df: OHLC DataFrame
        filter_type: 'none', 'optimal', 'conservative', 'aggressive'
        sl_pct: Stop loss percentage (5% = 0.05)
        tp_pct: Take profit percentage (7.5% = 0.075)
        fee_per_side: Fee per side (0.005% = 0.00005)

    Returns:
        (trades_df, final_equity, filter_stats)
    """
    df = df.copy()

    # Prepare indicators
    df = prepare_dataframe(df)
    df['atr'] = calculate_atr(df, 14)
    df['atr_pct'] = df['atr'] / df['close'] * 100

    # Generate signals
    df['signal'] = 0
    df.loc[(df['ema5'] < df['ema20']) & (df['ema5'].shift(1) >= df['ema20'].shift(1)), 'signal'] = -1

    # Backtest
    trades = []
    equity = 1.0
    max_equity = 1.0

    in_position = False
    entry_idx = 0

    # Filter tracking
    signals_generated = 0
    signals_filtered = 0
    filter_active_bars = 0

    for i in range(200, len(df)):  # Start after indicators warm up
        row = df.iloc[i]

        # Track filter status
        if filter_type != 'none':
            trade_allowed = should_trade(df, i, filter_type)
            if not trade_allowed:
                filter_active_bars += 1

        if not in_position:
            if row['signal'] == -1:
                signals_generated += 1

                # Apply regime filter
                if filter_type != 'none' and not should_trade(df, i, filter_type):
                    signals_filtered += 1
                    continue  # Skip this trade

                # Enter short position
                regime = classify_regime(df, i)

                in_position = True
                entry_idx = i
                entry_price = row['close']
                entry_time = row['timestamp'] if 'timestamp' in row else None
                stop_loss = entry_price * (1 + sl_pct)
                take_profit = entry_price * (1 - tp_pct)

                # Store entry info
                entry_regime = regime
        else:
            exit_price = None
            exit_reason = None

            if row['high'] >= stop_loss:
                exit_price = stop_loss
                exit_reason = 'SL'
            elif row['low'] <= take_profit:
                exit_price = take_profit
                exit_reason = 'TP'

            if exit_price:
                pnl_pct = (entry_price - exit_price) / entry_price
                net_pnl = pnl_pct - (fee_per_side * 2)

                equity *= (1 + net_pnl)
                max_equity = max(max_equity, equity)
                dd = (max_equity - equity) / max_equity * 100

                trades.append({
                    'entry_time': entry_time,
                    'entry_idx': entry_idx,
                    'exit_idx': i,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl_pct': net_pnl * 100,
                    'winner': net_pnl > 0,
                    'exit_reason': exit_reason,
                    'equity': equity,
                    'drawdown': dd,
                    'bars_held': i - entry_idx,
                    # Regime info
                    'regime_type': entry_regime['type'],
                    'regime_favorable': entry_regime['short_favorable'],
                    'price_vs_ema50': entry_regime['price_vs_ema50'],
                    'price_vs_ema100': entry_regime['price_vs_ema100'],
                })

                in_position = False

    filter_stats = {
        'signals_generated': signals_generated,
        'signals_filtered': signals_filtered,
        'filter_rate': signals_filtered / signals_generated * 100 if signals_generated > 0 else 0,
        'filter_active_pct': filter_active_bars / (len(df) - 200) * 100,
    }

    return pd.DataFrame(trades), equity, filter_stats


def analyze_current_period(df: pd.DataFrame, trades_df: pd.DataFrame, weeks: int = 4):
    """
    Analyze performance in the most recent N weeks (current conditions)

    Args:
        df: Full OHLC DataFrame
        trades_df: Trades DataFrame with entry_time
        weeks: Number of recent weeks to analyze

    Returns:
        Dict with current period stats
    """
    if 'entry_time' not in trades_df.columns or trades_df['entry_time'].isna().all():
        return None

    trades_df['entry_date'] = pd.to_datetime(trades_df['entry_time'])
    last_date = trades_df['entry_date'].max()
    cutoff_date = last_date - pd.Timedelta(weeks=weeks)

    recent_trades = trades_df[trades_df['entry_date'] >= cutoff_date]

    if len(recent_trades) == 0:
        return None

    # Calculate equity for recent period
    equity = 1.0
    for _, t in recent_trades.iterrows():
        equity *= (1 + t['pnl_pct'] / 100)

    return {
        'trades': len(recent_trades),
        'win_rate': recent_trades['winner'].mean() * 100,
        'return': (equity - 1) * 100,
        'avg_pnl': recent_trades['pnl_pct'].mean(),
        'start_date': recent_trades['entry_date'].min().strftime('%Y-%m-%d'),
        'end_date': recent_trades['entry_date'].max().strftime('%Y-%m-%d'),
    }


def compare_filters():
    """Compare all filter configurations"""

    print("=" * 80)
    print("FARTCOIN FILTERED BACKTEST COMPARISON")
    print("Strategy: EMA 5/20 Cross Down Short")
    print("Config: SL 5%, TP 7.5% (1.5:1 R:R), 0.01% fees")
    print("=" * 80)

    # Load data
    df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/fartcoin_bingx_15m.csv')

    print(f"\nData Range: {df['timestamp'].iloc[0]} to {df['timestamp'].iloc[-1]}")
    print(f"Total Bars: {len(df)}")
    print(f"Price Start: ${df['close'].iloc[200]:.4f}")
    print(f"Price End: ${df['close'].iloc[-1]:.4f}")
    print(f"Price Change: {(df['close'].iloc[-1] / df['close'].iloc[200] - 1) * 100:+.1f}%")

    # Test all filter configurations
    results = []

    print("\n" + "=" * 80)
    print("FILTER COMPARISON")
    print("=" * 80)

    for filter_type in ['none', 'optimal', 'conservative', 'aggressive']:
        trades_df, equity, filter_stats = backtest_with_filter(df, filter_type)

        if len(trades_df) > 0:
            total_return = (equity - 1) * 100
            win_rate = trades_df['winner'].mean() * 100
            max_dd = trades_df['drawdown'].max()
            risk_reward = total_return / max_dd if max_dd > 0 else 0

            # Recent period (last 4 weeks)
            recent = analyze_current_period(df, trades_df, weeks=4)

            results.append({
                'filter': filter_type,
                'name': FILTER_CONFIGS[filter_type]['name'],
                'trades': len(trades_df),
                'signals_filtered': filter_stats['signals_filtered'],
                'filter_rate': filter_stats['filter_rate'],
                'win_rate': win_rate,
                'return': total_return,
                'max_dd': max_dd,
                'risk_reward': risk_reward,
                'avg_trade': trades_df['pnl_pct'].mean(),
                'recent_return': recent['return'] if recent else None,
                'recent_trades': recent['trades'] if recent else None,
            })

    # Display results
    print(f"\n{'Filter Type':<20} {'Trades':<8} {'Filtered':<10} {'Win%':<8} {'Return':<12} {'MaxDD':<8} {'R:R':<8}")
    print("-" * 95)

    for r in results:
        filtered_str = f"{r['signals_filtered']} ({r['filter_rate']:.0f}%)" if r['filter_rate'] > 0 else "0"
        print(f"{r['name']:<20} {r['trades']:<8} {filtered_str:<10} {r['win_rate']:<7.1f}% "
              f"{r['return']:<+11.2f}% {r['max_dd']:<7.1f}% {r['risk_reward']:<7.2f}x")

    # Current period validation
    print("\n" + "=" * 80)
    print("CURRENT PERIOD VALIDATION (Last 4 Weeks)")
    print("=" * 80)
    print(f"\n{'Filter Type':<20} {'Trades':<8} {'Return':<12} {'Impact':<15}")
    print("-" * 60)

    baseline_recent = results[0]['recent_return']

    for r in results:
        if r['recent_return'] is not None:
            impact = r['recent_return'] - baseline_recent
            impact_str = f"{impact:+.1f}%" if baseline_recent else "N/A"

            status = "✅" if impact >= -10 else "⚠️" if impact >= -20 else "❌"
            print(f"{status} {r['name']:<18} {r['recent_trades']:<8} {r['recent_return']:<+11.2f}% {impact_str:<15}")

    # Detailed comparison
    print("\n" + "=" * 80)
    print("OPTIMAL FILTER ANALYSIS")
    print("=" * 80)

    baseline = results[0]
    optimal = next((r for r in results if r['filter'] == 'optimal'), None)

    if optimal:
        print(f"\nBaseline (No Filter):")
        print(f"  Trades: {baseline['trades']}")
        print(f"  Return: {baseline['return']:+.2f}%")
        print(f"  Max DD: {baseline['max_dd']:.2f}%")
        print(f"  Risk:Reward: {baseline['risk_reward']:.2f}x")

        print(f"\nOptimal Filter (Weak Uptrends Only):")
        print(f"  Trades: {optimal['trades']} (filtered {optimal['signals_filtered']} signals)")
        print(f"  Return: {optimal['return']:+.2f}%")
        print(f"  Max DD: {optimal['max_dd']:.2f}%")
        print(f"  Risk:Reward: {optimal['risk_reward']:.2f}x")

        print(f"\nImpact:")
        print(f"  Trades reduced: {baseline['trades'] - optimal['trades']} ({optimal['filter_rate']:.0f}%)")
        print(f"  Return change: {optimal['return'] - baseline['return']:+.2f}%")
        print(f"  DD change: {optimal['max_dd'] - baseline['max_dd']:+.2f}%")
        print(f"  R:R change: {optimal['risk_reward'] - baseline['risk_reward']:+.2f}x")

        # Fee savings
        baseline_fees = baseline['trades'] * 0.01  # 0.01% round-trip per trade
        optimal_fees = optimal['trades'] * 0.01
        fee_savings = baseline_fees - optimal_fees

        print(f"\nFee Savings:")
        print(f"  Baseline fees: {baseline_fees:.2f}%")
        print(f"  Optimal fees: {optimal_fees:.2f}%")
        print(f"  Savings: {fee_savings:.2f}%")

    # Leverage recommendations
    print("\n" + "=" * 80)
    print("LEVERAGE RECOMMENDATIONS")
    print("=" * 80)

    for r in results[:2]:  # Show baseline and optimal
        print(f"\n{r['name']}:")
        print(f"  Max DD: {r['max_dd']:.1f}%")
        print(f"  Safe leverage (2x DD buffer): {100 / (r['max_dd'] * 2):.1f}x")
        print(f"  Aggressive leverage (1.5x DD buffer): {100 / (r['max_dd'] * 1.5):.1f}x")

        leverages = [3, 5, 7, 10]
        print(f"  Returns at different leverage:")
        for lev in leverages:
            lev_return = r['return'] * lev
            lev_dd = r['max_dd'] * lev
            status = "✅" if lev_dd < 50 else "⚠️" if lev_dd < 80 else "❌"
            print(f"    {status} {lev}x: {lev_return:+.0f}% return, {lev_dd:.1f}% max DD")

    # Save detailed results
    print("\n" + "=" * 80)

    # Save all filter results
    for r in results:
        filter_type = r['filter']
        trades_df, _, _ = backtest_with_filter(df, filter_type)

        output_path = Path(f'/workspaces/Carebiuro_windykacja/trading/results/fartcoin_{filter_type}_filter.csv')
        trades_df.to_csv(output_path, index=False)
        print(f"{r['name']} results saved to: {output_path}")

    return pd.DataFrame(results)


if __name__ == '__main__':
    results_df = compare_filters()