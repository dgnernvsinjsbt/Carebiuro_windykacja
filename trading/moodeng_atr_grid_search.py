#!/usr/bin/env python3
"""
MOODENG RSI Strategy - Comprehensive ATR-based SL/TP Grid Search
Test many combinations to find optimal risk:reward setup
"""

import pandas as pd
import numpy as np
from itertools import product
import warnings
warnings.filterwarnings('ignore')

FEE_PER_TRADE = 0.10  # BingX Futures: 0.05% x2


def load_data():
    """Load MOODENG BingX data"""
    df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/moodeng_30d_bingx.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)

    # ATR
    df['tr'] = np.maximum(
        df['high'] - df['low'],
        np.maximum(
            abs(df['high'] - df['close'].shift(1)),
            abs(df['low'] - df['close'].shift(1))
        )
    )
    df['atr'] = df['tr'].rolling(14).mean()

    # RSI
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))

    # SMA
    df['sma_20'] = df['close'].rolling(20).mean()

    # Basics
    df['body_pct'] = abs(df['close'] - df['open']) / df['open'] * 100
    df['is_bullish'] = df['close'] > df['open']

    return df


def backtest(df, sl_mult, tp_mult, rsi_entry=55, body_thresh=0.5, max_bars=60):
    """
    RSI Momentum Strategy with ATR-based SL/TP

    Entry:
    - RSI crosses above rsi_entry
    - Bullish candle with body > body_thresh%
    - Price above SMA(20)

    Exit:
    - SL: entry - (ATR * sl_mult)
    - TP: entry + (ATR * tp_mult)
    - Time: max_bars
    """
    trades = []
    in_position = False
    entry_price = entry_idx = stop_loss = take_profit = 0

    for i in range(200, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i-1]

        if not in_position:
            # Entry conditions
            rsi_cross = prev['rsi'] < rsi_entry and row['rsi'] >= rsi_entry
            bullish = row['is_bullish'] and row['body_pct'] > body_thresh
            above_sma = row['close'] > row['sma_20']

            if rsi_cross and bullish and above_sma:
                in_position = True
                entry_price = row['close']
                entry_idx = i
                entry_atr = row['atr']

                stop_loss = entry_price - (entry_atr * sl_mult)
                take_profit = entry_price + (entry_atr * tp_mult)
        else:
            # Exit conditions
            bars_held = i - entry_idx

            # Stop loss hit
            if row['low'] <= stop_loss:
                pnl = (stop_loss - entry_price) / entry_price * 100
                trades.append({
                    'entry_idx': entry_idx, 'exit_idx': i,
                    'entry_price': entry_price, 'exit_price': stop_loss,
                    'pnl_pct': pnl, 'result': 'SL', 'bars': bars_held
                })
                in_position = False
                continue

            # Take profit hit
            if row['high'] >= take_profit:
                pnl = (take_profit - entry_price) / entry_price * 100
                trades.append({
                    'entry_idx': entry_idx, 'exit_idx': i,
                    'entry_price': entry_price, 'exit_price': take_profit,
                    'pnl_pct': pnl, 'result': 'TP', 'bars': bars_held
                })
                in_position = False
                continue

            # Time exit
            if bars_held >= max_bars:
                exit_price = row['close']
                pnl = (exit_price - entry_price) / entry_price * 100
                trades.append({
                    'entry_idx': entry_idx, 'exit_idx': i,
                    'entry_price': entry_price, 'exit_price': exit_price,
                    'pnl_pct': pnl, 'result': 'TIME', 'bars': bars_held
                })
                in_position = False

    return trades


def calculate_metrics(trades):
    """Calculate performance metrics"""
    if not trades:
        return {
            'trades': 0, 'net': 0, 'wr': 0, 'dd': 0, 'r_dd': 0,
            'avg_win': 0, 'avg_loss': 0, 'pf': 0, 'sl_count': 0, 'tp_count': 0
        }

    df = pd.DataFrame(trades)

    # Win/loss stats
    winners = df[df['pnl_pct'] > 0]
    losers = df[df['pnl_pct'] <= 0]

    win_rate = len(winners) / len(df) * 100 if len(df) > 0 else 0
    avg_win = winners['pnl_pct'].mean() if len(winners) > 0 else 0
    avg_loss = abs(losers['pnl_pct'].mean()) if len(losers) > 0 else 0

    gross_profit = winners['pnl_pct'].sum() if len(winners) > 0 else 0
    gross_loss = abs(losers['pnl_pct'].sum()) if len(losers) > 0 else 0
    pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')

    # Equity curve
    equity = [100]
    for pnl in df['pnl_pct']:
        equity.append(equity[-1] * (1 + pnl/100))

    # Max drawdown
    peak = equity[0]
    max_dd = 0
    for e in equity:
        if e > peak:
            peak = e
        dd = (peak - e) / peak * 100
        max_dd = max(max_dd, dd)

    # Returns
    gross_return = equity[-1] - 100
    fee_cost = len(df) * FEE_PER_TRADE
    net_return = gross_return - fee_cost

    # Return/DD ratio
    r_dd = net_return / max_dd if max_dd > 0 else 0

    # Exit breakdown
    sl_count = len(df[df['result'] == 'SL'])
    tp_count = len(df[df['result'] == 'TP'])

    return {
        'trades': len(df),
        'net': net_return,
        'wr': win_rate,
        'dd': max_dd,
        'r_dd': r_dd,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'pf': pf,
        'sl_count': sl_count,
        'tp_count': tp_count
    }


def main():
    print("=" * 80)
    print("MOODENG RSI STRATEGY - ATR-based SL/TP Grid Search")
    print("=" * 80)

    df = load_data()
    print(f"\nLoaded {len(df):,} candles")
    print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}\n")

    # Define grid search space
    sl_multiples = [0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0]
    tp_multiples = [2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 7.0, 8.0, 10.0]

    print(f"Testing {len(sl_multiples)} SL values × {len(tp_multiples)} TP values = {len(sl_multiples) * len(tp_multiples)} combinations\n")

    results = []

    for sl_mult in sl_multiples:
        for tp_mult in tp_multiples:
            # Skip if TP < SL (negative R:R)
            if tp_mult < sl_mult:
                continue

            trades = backtest(df, sl_mult=sl_mult, tp_mult=tp_mult)
            metrics = calculate_metrics(trades)

            results.append({
                'sl_mult': sl_mult,
                'tp_mult': tp_mult,
                'rr_ratio': tp_mult / sl_mult,
                **metrics
            })

    # Convert to DataFrame
    df_results = pd.DataFrame(results)

    # Sort by Return/DD ratio
    df_results = df_results.sort_values('r_dd', ascending=False)

    # Display top 20
    print("=" * 80)
    print("TOP 20 CONFIGURATIONS BY RETURN/DD RATIO")
    print("=" * 80)
    print(f"\n{'Rank':<5} {'SL':<6} {'TP':<6} {'R:R':<6} {'Trades':<7} {'NET':<9} {'WR':<6} {'DD':<8} {'R/DD':<7} {'SL/TP'}")
    print("-" * 80)

    for i, row in df_results.head(20).iterrows():
        print(f"{i+1:<5} {row['sl_mult']:<6.2f} {row['tp_mult']:<6.2f} {row['rr_ratio']:<6.1f} "
              f"{row['trades']:<7} {row['net']:>+8.2f}% {row['wr']:>5.1f}% "
              f"{row['dd']:>7.2f}% {row['r_dd']:>6.2f}x {row['sl_count']}/{row['tp_count']}")

    # Show best by different criteria
    print("\n" + "=" * 80)
    print("BEST BY DIFFERENT CRITERIA")
    print("=" * 80)

    best_rdd = df_results.iloc[0]
    best_net = df_results.nlargest(1, 'net').iloc[0]
    best_wr = df_results.nlargest(1, 'wr').iloc[0]
    best_dd = df_results.nsmallest(1, 'dd').iloc[0]

    print(f"\n1. BEST RETURN/DD RATIO: {best_rdd['r_dd']:.2f}x")
    print(f"   SL {best_rdd['sl_mult']:.2f}x / TP {best_rdd['tp_mult']:.2f}x (R:R {best_rdd['rr_ratio']:.1f}:1)")
    print(f"   NET: {best_rdd['net']:+.2f}%, DD: {best_rdd['dd']:.2f}%, WR: {best_rdd['wr']:.1f}%, Trades: {best_rdd['trades']}")

    print(f"\n2. HIGHEST NET RETURN: {best_net['net']:+.2f}%")
    print(f"   SL {best_net['sl_mult']:.2f}x / TP {best_net['tp_mult']:.2f}x (R:R {best_net['rr_ratio']:.1f}:1)")
    print(f"   R/DD: {best_net['r_dd']:.2f}x, DD: {best_net['dd']:.2f}%, WR: {best_net['wr']:.1f}%, Trades: {best_net['trades']}")

    print(f"\n3. HIGHEST WIN RATE: {best_wr['wr']:.1f}%")
    print(f"   SL {best_wr['sl_mult']:.2f}x / TP {best_wr['tp_mult']:.2f}x (R:R {best_wr['rr_ratio']:.1f}:1)")
    print(f"   NET: {best_wr['net']:+.2f}%, R/DD: {best_wr['r_dd']:.2f}x, DD: {best_wr['dd']:.2f}%, Trades: {best_wr['trades']}")

    print(f"\n4. LOWEST DRAWDOWN: {best_dd['dd']:.2f}%")
    print(f"   SL {best_dd['sl_mult']:.2f}x / TP {best_dd['tp_mult']:.2f}x (R:R {best_dd['rr_ratio']:.1f}:1)")
    print(f"   NET: {best_dd['net']:+.2f}%, R/DD: {best_dd['r_dd']:.2f}x, WR: {best_dd['wr']:.1f}%, Trades: {best_dd['trades']}")

    # Save full results
    output_file = '/workspaces/Carebiuro_windykacja/trading/results/moodeng_atr_grid_search.csv'
    df_results.to_csv(output_file, index=False)
    print(f"\n✅ Full results saved to: {output_file}")

    # Heat map of R/DD by SL/TP
    print("\n" + "=" * 80)
    print("RETURN/DD HEATMAP (rows=SL, cols=TP)")
    print("=" * 80)

    pivot = df_results.pivot_table(values='r_dd', index='sl_mult', columns='tp_mult', fill_value=0)
    print("\n" + pivot.to_string())

    # Analysis insights
    print("\n" + "=" * 80)
    print("KEY INSIGHTS")
    print("=" * 80)

    # Find sweet spot
    good_configs = df_results[(df_results['r_dd'] > 3.0) & (df_results['trades'] >= 50)]

    if len(good_configs) > 0:
        print(f"\n✅ Found {len(good_configs)} configs with R/DD > 3.0x and ≥50 trades:")
        for _, row in good_configs.head(5).iterrows():
            print(f"   • SL {row['sl_mult']:.2f}x / TP {row['tp_mult']:.2f}x → "
                  f"NET {row['net']:+.2f}%, R/DD {row['r_dd']:.2f}x, WR {row['wr']:.1f}%")
    else:
        print("\n⚠️  No configs achieved R/DD > 3.0x with ≥50 trades")
        print("    Best achievable R/DD on this data:")
        for _, row in df_results.head(3).iterrows():
            print(f"   • SL {row['sl_mult']:.2f}x / TP {row['tp_mult']:.2f}x → "
                  f"NET {row['net']:+.2f}%, R/DD {row['r_dd']:.2f}x, {row['trades']} trades")

    # Optimal R:R ratio
    avg_rdd_by_rr = df_results.groupby('rr_ratio').agg({
        'r_dd': 'mean',
        'net': 'mean',
        'wr': 'mean',
        'trades': 'mean'
    }).sort_values('r_dd', ascending=False)

    print(f"\n📊 Average R/DD by Risk:Reward Ratio (top 5):")
    for rr, row in avg_rdd_by_rr.head(5).iterrows():
        print(f"   {rr:.1f}:1 → Avg R/DD: {row['r_dd']:.2f}x, Avg NET: {row['net']:+.2f}%, Avg WR: {row['wr']:.1f}%")


if __name__ == "__main__":
    main()
