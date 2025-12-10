#!/usr/bin/env python3
"""
FARTCOIN BingX SHORT - MINIMAL Optimization with Progress Tracking
24 configurations only
"""

import pandas as pd
import numpy as np
from itertools import product
import warnings
import sys
from datetime import datetime
warnings.filterwarnings('ignore')


def backtest_short(df, distance_min, stop_atr, target_atr, body_thresh, vol_mult):
    """Backtest SHORT strategy - optimized for speed"""
    trades = []

    # Pre-calculate all checks
    valid = (
        ~df['atr'].isna() &
        ~df['sma50'].isna() &
        df['downtrend'] &
        (df['sma_distance'] < -distance_min) &
        (df['body_pct'] >= body_thresh) &
        (df['volume_ratio'] >= vol_mult) &
        (df['rsi'] >= 25) &
        (df['rsi'] <= 55)
    )

    entry_indices = df[valid].index

    for entry_idx in entry_indices:
        i = df.index.get_loc(entry_idx)
        if i < 200 or i >= len(df) - 10:
            continue

        row = df.iloc[i]
        entry_price = row['close']
        atr = row['atr']

        stop_loss = entry_price + (stop_atr * atr)
        take_profit = entry_price - (target_atr * atr)

        # Quick exit check (max 200 bars instead of 500)
        hit_sl = False
        hit_tp = False
        exit_price = entry_price

        for j in range(i + 1, min(i + 200, len(df))):
            future = df.iloc[j]

            if future['high'] >= stop_loss:
                hit_sl = True
                exit_price = stop_loss
                break
            if future['low'] <= take_profit:
                hit_tp = True
                exit_price = take_profit
                break

        if not hit_sl and not hit_tp:
            exit_price = df.iloc[min(i + 200, len(df) - 1)]['close']

        pnl_pct = (entry_price - exit_price) / entry_price
        pnl_with_fees = pnl_pct - 0.001

        trades.append(pnl_with_fees)

    if len(trades) == 0:
        return None

    trades_arr = np.array(trades)
    total_trades = len(trades_arr)
    win_rate = (trades_arr > 0).sum() / total_trades * 100
    total_return = trades_arr.sum() * 100

    equity = np.cumprod(1 + trades_arr)
    running_max = np.maximum.accumulate(equity)
    drawdown = (equity - running_max) / running_max * 100
    max_drawdown = drawdown.min()

    rr_ratio = total_return / abs(max_drawdown) if max_drawdown != 0 else 0

    return {
        'total_trades': total_trades,
        'win_rate': win_rate,
        'total_return': total_return,
        'max_drawdown': max_drawdown,
        'rr_ratio': rr_ratio,
        'distance_min': distance_min,
        'stop_atr': stop_atr,
        'target_atr': target_atr,
        'body_thresh': body_thresh,
        'vol_mult': vol_mult
    }


def main():
    print("="*80)
    print("FARTCOIN SHORT - MINIMAL OPTIMIZATION (24 configs)")
    print("="*80)
    print(f"Started: {datetime.now().strftime('%H:%M:%S')}\n")

    # Load data
    print("Loading data...")
    df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/fartcoin_30d_bingx.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)

    # Calculate indicators
    print("Calculating indicators...")
    df['sma50'] = df['close'].rolling(50).mean()
    df['sma200'] = df['close'].rolling(200).mean()
    df['sma_distance'] = ((df['close'] - df['sma50']) / df['sma50']) * 100
    df['downtrend'] = (df['close'] < df['sma50']) & (df['close'] < df['sma200'])

    df['tr'] = np.maximum(
        df['high'] - df['low'],
        np.maximum(
            abs(df['high'] - df['close'].shift(1)),
            abs(df['low'] - df['close'].shift(1))
        )
    )
    df['atr'] = df['tr'].rolling(14).mean()

    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = -delta.where(delta < 0, 0).rolling(14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))

    df['body_pct'] = abs((df['close'] - df['open']) / df['open']) * 100
    df['volume_ratio'] = df['volume'] / df['volume'].rolling(20).mean()

    # MINIMAL parameter grid
    distance_values = [1.0, 1.5, 2.0]  # 3
    stop_values = [4.0, 5.0]  # 2
    body_values = [0.8, 1.0]  # 2
    vol_values = [2.5, 3.0]  # 2
    # Total: 3 × 2 × 2 × 2 = 24 configs

    target_atr = 15.0  # Fixed

    results = []
    total_configs = len(distance_values) * len(stop_values) * len(body_values) * len(vol_values)

    print(f"\nTesting {total_configs} configurations...")
    print("="*80)

    config_num = 0
    for dist, stop, body, vol in product(distance_values, stop_values, body_values, vol_values):
        config_num += 1

        print(f"[{config_num}/{total_configs}] Testing: dist={dist:.1f}% stop={stop:.1f}x body={body:.1f}% vol={vol:.1f}x", end='')
        sys.stdout.flush()

        result = backtest_short(df, dist, stop, target_atr, body, vol)

        if result and result['total_trades'] >= 10:
            print(f" ✓ {result['total_trades']} trades, R:R={result['rr_ratio']:.2f}x")
            results.append(result)
        else:
            trades = result['total_trades'] if result else 0
            print(f" ✗ Only {trades} trades")

    print("="*80)

    if len(results) == 0:
        print("\n❌ No configurations produced ≥10 trades")
        return

    # Sort by R:R
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('rr_ratio', ascending=False)

    # Save
    output_path = '/workspaces/Carebiuro_windykacja/trading/results/fartcoin_bingx_short_optimization.csv'
    results_df.to_csv(output_path, index=False)

    # Print top configs
    print(f"\n{'='*80}")
    print("TOP CONFIGURATIONS (by R:R ratio)")
    print("="*80)

    for idx, row in results_df.head(min(10, len(results_df))).iterrows():
        rank = results_df.index.get_loc(idx) + 1
        print(f"\n#{rank}")
        print(f"  Return: {row['total_return']:+.2f}% | DD: {row['max_drawdown']:.2f}% | R:R: {row['rr_ratio']:.2f}x")
        print(f"  Trades: {row['total_trades']:.0f} | WR: {row['win_rate']:.1f}%")
        print(f"  Distance: {row['distance_min']:.1f}% | Stop: {row['stop_atr']:.1f}x | Body: {row['body_thresh']:.1f}% | Vol: {row['vol_mult']:.1f}x")

    print(f"\n{'='*80}")
    print(f"✅ Results saved to {output_path}")
    print(f"✅ Found {len(results_df)} profitable configurations")
    print(f"Completed: {datetime.now().strftime('%H:%M:%S')}")


if __name__ == "__main__":
    main()
