#!/usr/bin/env python3
"""
FARTCOIN BingX LONG - MINIMAL Optimization with Progress Tracking
24 configurations only
"""

import pandas as pd
import numpy as np
from itertools import product
import warnings
import sys
from datetime import datetime
warnings.filterwarnings('ignore')


def backtest_long(df, df_5m, stop_atr, target_atr, body_thresh, vol_mult):
    """Backtest LONG strategy - optimized for speed"""
    trades = []

    # Fixed 5-min thresholds for speed
    rsi_5m_min = 52
    dist_5m_min = 0.4

    for i in range(200, len(df) - 10):
        row = df.iloc[i]
        timestamp = df.index[i]

        # Quick checks
        if pd.isna(row['atr']) or pd.isna(row['sma50']):
            continue
        if row['body_pct'] < body_thresh:
            continue
        if row['volume_ratio'] < vol_mult:
            continue
        if row['wick_ratio'] > 0.4:
            continue
        if not (45 <= row['rsi'] <= 75):
            continue

        # 5-min check
        idx_5m = df_5m.index.searchsorted(timestamp, side='right') - 1
        if idx_5m < 0 or idx_5m >= len(df_5m):
            continue

        row_5m = df_5m.iloc[idx_5m]
        if pd.isna(row_5m['sma50']) or pd.isna(row_5m['rsi']):
            continue
        if row_5m['close'] <= row_5m['sma50']:
            continue
        if row_5m['rsi'] < rsi_5m_min:
            continue

        distance_5m = ((row_5m['close'] - row_5m['sma50']) / row_5m['sma50']) * 100
        if distance_5m < dist_5m_min:
            continue

        # Enter LONG
        entry_price = row['close']
        atr = row['atr']

        stop_loss = entry_price - (stop_atr * atr)
        take_profit = entry_price + (target_atr * atr)

        # Quick exit (max 200 bars)
        hit_sl = False
        hit_tp = False
        exit_price = entry_price

        for j in range(i + 1, min(i + 200, len(df))):
            future = df.iloc[j]

            if future['low'] <= stop_loss:
                hit_sl = True
                exit_price = stop_loss
                break
            if future['high'] >= take_profit:
                hit_tp = True
                exit_price = take_profit
                break

        if not hit_sl and not hit_tp:
            exit_price = df.iloc[min(i + 200, len(df) - 1)]['close']

        pnl_pct = (exit_price - entry_price) / entry_price
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
        'stop_atr': stop_atr,
        'target_atr': target_atr,
        'body_thresh': body_thresh,
        'vol_mult': vol_mult
    }


def main():
    print("="*80)
    print("FARTCOIN LONG - MINIMAL OPTIMIZATION (24 configs)")
    print("="*80)
    print(f"Started: {datetime.now().strftime('%H:%M:%S')}\n")

    # Load 1-min data
    print("Loading data...")
    df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/fartcoin_30d_bingx.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)

    # Calculate 1-min indicators
    print("Calculating 1-min indicators...")
    df['sma50'] = df['close'].rolling(50).mean()

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

    body = abs(df['close'] - df['open'])
    total_range = df['high'] - df['low']
    df['wick_ratio'] = (total_range - body) / total_range.replace(0, np.nan)

    df['volume_ratio'] = df['volume'] / df['volume'].rolling(20).mean()

    # Create 5-min data
    print("Resampling to 5-min...")
    df_5m = df.resample('5T').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()

    df_5m['sma50'] = df_5m['close'].rolling(50).mean()

    delta_5m = df_5m['close'].diff()
    gain_5m = delta_5m.where(delta_5m > 0, 0).rolling(14).mean()
    loss_5m = -delta_5m.where(delta_5m < 0, 0).rolling(14).mean()
    rs_5m = gain_5m / loss_5m
    df_5m['rsi'] = 100 - (100 / (1 + rs_5m))

    # MINIMAL parameter grid
    stop_values = [4.0, 5.0, 6.0]  # 3
    target_values = [12, 15]  # 2
    body_values = [0.8, 1.0]  # 2
    vol_values = [2.5, 3.0]  # 2
    # Total: 3 × 2 × 2 × 2 = 24 configs

    results = []
    total_configs = len(stop_values) * len(target_values) * len(body_values) * len(vol_values)

    print(f"\nTesting {total_configs} configurations...")
    print("="*80)

    config_num = 0
    for stop, target, body, vol in product(stop_values, target_values, body_values, vol_values):
        config_num += 1

        print(f"[{config_num}/{total_configs}] Testing: stop={stop:.1f}x target={target:.0f}x body={body:.1f}% vol={vol:.1f}x", end='')
        sys.stdout.flush()

        result = backtest_long(df, df_5m, stop, target, body, vol)

        if result and result['total_trades'] >= 5:
            print(f" ✓ {result['total_trades']} trades, R:R={result['rr_ratio']:.2f}x")
            results.append(result)
        else:
            trades = result['total_trades'] if result else 0
            print(f" ✗ Only {trades} trades")

    print("="*80)

    if len(results) == 0:
        print("\n❌ No configurations produced ≥5 trades")
        return

    # Sort by R:R
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('rr_ratio', ascending=False)

    # Save
    output_path = '/workspaces/Carebiuro_windykacja/trading/results/fartcoin_bingx_long_optimization.csv'
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
        print(f"  Stop: {row['stop_atr']:.1f}x | Target: {row['target_atr']:.0f}x | Body: {row['body_thresh']:.1f}% | Vol: {row['vol_mult']:.1f}x")

    print(f"\n{'='*80}")
    print(f"✅ Results saved to {output_path}")
    print(f"✅ Found {len(results_df)} profitable configurations")
    print(f"Completed: {datetime.now().strftime('%H:%M:%S')}")


if __name__ == "__main__":
    main()
