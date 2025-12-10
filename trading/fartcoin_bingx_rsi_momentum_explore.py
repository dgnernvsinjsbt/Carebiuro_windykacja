#!/usr/bin/env python3
"""
FARTCOIN BingX - MOODENG RSI Momentum Strategy Exploration
Testing 30 configurations with ATR-based SL/TP
"""

import pandas as pd
import numpy as np
from itertools import product
import warnings
import sys
from datetime import datetime
warnings.filterwarnings('ignore')


def backtest_rsi_momentum(df, rsi_threshold, sl_atr_mult, tp_atr_mult, body_thresh=0.5, time_exit_bars=60):
    """
    Backtest RSI Momentum strategy (MOODENG-style)

    Entry:
    - RSI(14) crosses ABOVE threshold (previous < threshold, current >= threshold)
    - Bullish candle (body > body_thresh%)
    - Price ABOVE SMA(20)

    Exit:
    - SL: sl_atr_mult × ATR below entry
    - TP: tp_atr_mult × ATR above entry
    - Time: time_exit_bars if neither hit
    """
    trades = []

    for i in range(21, len(df) - 10):  # Need 20 bars for SMA20
        row = df.iloc[i]
        prev_row = df.iloc[i - 1]

        # Skip if missing data
        if pd.isna(row['atr']) or pd.isna(row['sma20']) or pd.isna(row['rsi']):
            continue

        # Entry conditions
        # 1. RSI crosses above threshold
        if not (prev_row['rsi'] < rsi_threshold and row['rsi'] >= rsi_threshold):
            continue

        # 2. Bullish candle with sufficient body
        if row['body_pct'] < body_thresh:
            continue

        # 3. Price above SMA(20)
        if row['close'] <= row['sma20']:
            continue

        # Enter LONG
        entry_price = row['close']
        entry_time = df.index[i]
        atr = row['atr']

        # Set SL/TP
        stop_loss = entry_price - (sl_atr_mult * atr)
        take_profit = entry_price + (tp_atr_mult * atr)

        # Simulate trade exit
        hit_sl = False
        hit_tp = False
        time_exit = False
        exit_price = entry_price
        exit_time = entry_time

        for j in range(i + 1, min(i + time_exit_bars + 1, len(df))):
            future_row = df.iloc[j]

            # Check SL/TP
            if future_row['low'] <= stop_loss:
                hit_sl = True
                exit_price = stop_loss
                exit_time = df.index[j]
                break
            if future_row['high'] >= take_profit:
                hit_tp = True
                exit_price = take_profit
                exit_time = df.index[j]
                break

        # Time exit if neither hit
        if not hit_sl and not hit_tp:
            time_exit = True
            exit_idx = min(i + time_exit_bars, len(df) - 1)
            exit_price = df.iloc[exit_idx]['close']
            exit_time = df.index[exit_idx]

        # Calculate P&L (LONG)
        pnl_pct = (exit_price - entry_price) / entry_price
        pnl_with_fees = pnl_pct - 0.001  # 0.1% fees

        trades.append({
            'pnl': pnl_with_fees,
            'hit_sl': hit_sl,
            'hit_tp': hit_tp,
            'time_exit': time_exit
        })

    if len(trades) == 0:
        return None

    # Calculate metrics
    trades_df = pd.DataFrame(trades)
    total_trades = len(trades_df)
    winners = trades_df[trades_df['pnl'] > 0]
    win_rate = len(winners) / total_trades * 100

    total_return = trades_df['pnl'].sum() * 100

    # Equity curve
    equity = (1 + trades_df['pnl']).cumprod()
    running_max = equity.cummax()
    drawdown = (equity - running_max) / running_max * 100
    max_drawdown = drawdown.min()

    rr_ratio = total_return / abs(max_drawdown) if max_drawdown != 0 else 0

    # Exit type breakdown
    tp_count = trades_df['hit_tp'].sum()
    sl_count = trades_df['hit_sl'].sum()
    time_count = trades_df['time_exit'].sum()

    return {
        'total_trades': total_trades,
        'win_rate': win_rate,
        'total_return': total_return,
        'max_drawdown': max_drawdown,
        'rr_ratio': rr_ratio,
        'rsi_threshold': rsi_threshold,
        'sl_atr_mult': sl_atr_mult,
        'tp_atr_mult': tp_atr_mult,
        'tp_count': tp_count,
        'sl_count': sl_count,
        'time_count': time_count,
        'tp_pct': tp_count / total_trades * 100,
        'sl_pct': sl_count / total_trades * 100,
        'time_pct': time_count / total_trades * 100
    }


def main():
    print("="*80)
    print("FARTCOIN BingX - RSI MOMENTUM EXPLORATION (30 configs)")
    print("Strategy: MOODENG RSI adapted for FARTCOIN")
    print("="*80)
    print(f"Started: {datetime.now().strftime('%H:%M:%S')}\n")

    # Load data
    print("Loading data...")
    df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/fartcoin_30d_bingx.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)

    # Calculate indicators
    print("Calculating indicators...")

    # SMA(20)
    df['sma20'] = df['close'].rolling(20).mean()

    # ATR(14)
    df['tr'] = np.maximum(
        df['high'] - df['low'],
        np.maximum(
            abs(df['high'] - df['close'].shift(1)),
            abs(df['low'] - df['close'].shift(1))
        )
    )
    df['atr'] = df['tr'].rolling(14).mean()

    # RSI(14)
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = -delta.where(delta < 0, 0).rolling(14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))

    # Body %
    df['body_pct'] = abs((df['close'] - df['open']) / df['open']) * 100

    # Parameter grid (30 configs)
    rsi_values = [50, 52, 55, 57, 60]  # 5 values
    sl_values = [1.0, 1.5]  # 2 values
    tp_values = [3.0, 4.0, 5.0]  # 3 values
    # Total: 5 × 2 × 3 = 30 configs

    results = []
    total_configs = len(rsi_values) * len(sl_values) * len(tp_values)

    print(f"\nTesting {total_configs} configurations...")
    print("="*80)

    config_num = 0
    for rsi_thresh, sl_mult, tp_mult in product(rsi_values, sl_values, tp_values):
        config_num += 1

        print(f"[{config_num}/{total_configs}] RSI>{rsi_thresh} SL={sl_mult:.1f}x TP={tp_mult:.1f}x", end='')
        sys.stdout.flush()

        result = backtest_rsi_momentum(df, rsi_thresh, sl_mult, tp_mult)

        if result and result['total_trades'] >= 5:
            print(f" ✓ {result['total_trades']} trades, R:R={result['rr_ratio']:.2f}x, Return={result['total_return']:+.1f}%")
            results.append(result)
        else:
            trades = result['total_trades'] if result else 0
            print(f" ✗ Only {trades} trades")

    print("="*80)

    if len(results) == 0:
        print("\n❌ No configurations produced ≥5 trades")
        return

    # Sort by R:R ratio
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('rr_ratio', ascending=False)

    # Save
    output_path = '/workspaces/Carebiuro_windykacja/trading/results/fartcoin_bingx_rsi_momentum.csv'
    results_df.to_csv(output_path, index=False)

    # Print top configs
    print(f"\n{'='*80}")
    print("TOP 10 CONFIGURATIONS (by R:R ratio)")
    print("="*80)

    for idx, row in results_df.head(min(10, len(results_df))).iterrows():
        rank = results_df.index.get_loc(idx) + 1
        print(f"\n#{rank}")
        print(f"  Return: {row['total_return']:+.2f}% | DD: {row['max_drawdown']:.2f}% | R:R: {row['rr_ratio']:.2f}x")
        print(f"  Trades: {row['total_trades']:.0f} | WR: {row['win_rate']:.1f}%")
        print(f"  RSI > {row['rsi_threshold']:.0f} | SL: {row['sl_atr_mult']:.1f}x ATR | TP: {row['tp_atr_mult']:.1f}x ATR")
        print(f"  Exits: TP={row['tp_pct']:.0f}% SL={row['sl_pct']:.0f}% Time={row['time_pct']:.0f}%")

    # Summary stats
    print(f"\n{'='*80}")
    print("SUMMARY STATISTICS")
    print("="*80)
    profitable = results_df[results_df['total_return'] > 0]
    print(f"Profitable configs: {len(profitable)}/{len(results_df)} ({len(profitable)/len(results_df)*100:.0f}%)")

    if len(profitable) > 0:
        print(f"Best return: {results_df['total_return'].max():+.2f}%")
        print(f"Best R:R: {results_df['rr_ratio'].max():.2f}x")
        print(f"Avg trades (all): {results_df['total_trades'].mean():.0f}")
        print(f"Avg WR (profitable): {profitable['win_rate'].mean():.1f}%")

    print(f"\n{'='*80}")
    print(f"✅ Results saved to {output_path}")
    print(f"Completed: {datetime.now().strftime('%H:%M:%S')}")


if __name__ == "__main__":
    main()
