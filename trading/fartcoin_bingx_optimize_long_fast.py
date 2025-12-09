#!/usr/bin/env python3
"""
FARTCOIN BingX LONG Strategy - FAST Optimization
Reduced to ~288 configs for speed
"""

import pandas as pd
import numpy as np
from itertools import product
import warnings
warnings.filterwarnings('ignore')


def backtest_long(df, df_5m, stop_atr, target_atr, body_thresh, vol_mult, rsi_5m_min, dist_5m_min):
    """Backtest LONG strategy with given parameters"""
    trades = []

    for i in range(len(df)):
        if i < 200:  # Need history for indicators
            continue

        row = df.iloc[i]
        timestamp = df.index[i]

        # Skip if missing data
        if pd.isna(row['atr']) or pd.isna(row['sma50']):
            continue

        # 1-min explosive candle check
        if row['body_pct'] < body_thresh:
            continue
        if row['volume_ratio'] < vol_mult:
            continue
        if row['wick_ratio'] > 0.4:  # Minimal wicks
            continue
        if not (45 <= row['rsi'] <= 75):
            continue

        # 5-min confirmation
        idx_5m = df_5m.index.searchsorted(timestamp, side='right') - 1
        if idx_5m < 0 or idx_5m >= len(df_5m):
            continue

        row_5m = df_5m.iloc[idx_5m]

        if pd.isna(row_5m['sma50']) or pd.isna(row_5m['rsi']):
            continue

        # 5-min uptrend check
        if row_5m['close'] <= row_5m['sma50']:
            continue
        if row_5m['rsi'] < rsi_5m_min:
            continue

        distance_5m = ((row_5m['close'] - row_5m['sma50']) / row_5m['sma50']) * 100
        if distance_5m < dist_5m_min:
            continue

        # Enter LONG
        entry_price = row['close']
        entry_time = timestamp
        atr = row['atr']

        # Set SL/TP
        stop_loss = entry_price - (stop_atr * atr)
        take_profit = entry_price + (target_atr * atr)

        # Simulate trade exit
        hit_sl = False
        hit_tp = False
        exit_price = entry_price
        exit_time = entry_time

        for j in range(i + 1, min(i + 500, len(df))):  # Max 500 bars
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

        # If neither hit, exit at current price
        if not hit_sl and not hit_tp:
            exit_price = df.iloc[min(i + 500, len(df) - 1)]['close']
            exit_time = df.index[min(i + 500, len(df) - 1)]

        # Calculate P&L (LONG)
        pnl_pct = (exit_price - entry_price) / entry_price
        pnl_with_fees = pnl_pct - 0.001  # 0.1% fees

        trades.append({
            'entry_time': entry_time,
            'exit_time': exit_time,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'pnl': pnl_with_fees,
            'hit_sl': hit_sl,
            'hit_tp': hit_tp
        })

    if len(trades) == 0:
        return None

    trades_df = pd.DataFrame(trades)

    # Calculate metrics
    total_trades = len(trades_df)
    winners = trades_df[trades_df['pnl'] > 0]
    win_rate = len(winners) / total_trades * 100 if total_trades > 0 else 0

    total_return = trades_df['pnl'].sum() * 100

    # Equity curve
    equity = (1 + trades_df['pnl']).cumprod()
    running_max = equity.cummax()
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
        'vol_mult': vol_mult,
        'rsi_5m_min': rsi_5m_min,
        'dist_5m_min': dist_5m_min
    }


def main():
    print("="*80)
    print("FARTCOIN LONG - FAST OPTIMIZATION (288 configs)")
    print("="*80)

    # Load 1-min data
    df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/fartcoin_30d_bingx.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)

    # Calculate 1-min indicators
    df['sma50'] = df['close'].rolling(50).mean()

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
    loss = -delta.where(delta < 0, 0).rolling(14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))

    # Body %
    df['body_pct'] = abs((df['close'] - df['open']) / df['open']) * 100

    # Wick ratio
    body = abs(df['close'] - df['open'])
    total_range = df['high'] - df['low']
    df['wick_ratio'] = (total_range - body) / total_range.replace(0, np.nan)

    # Volume ratio
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

    # RSI 5-min
    delta_5m = df_5m['close'].diff()
    gain_5m = delta_5m.where(delta_5m > 0, 0).rolling(14).mean()
    loss_5m = -delta_5m.where(delta_5m < 0, 0).rolling(14).mean()
    rs_5m = gain_5m / loss_5m
    df_5m['rsi'] = 100 - (100 / (1 + rs_5m))

    # Parameter grid (REDUCED)
    stop_values = [3.5, 4.0, 5.0, 6.0]  # 4 values
    target_values = [12, 15, 18]  # 3 values
    body_values = [0.8, 1.0, 1.2]  # 3 values
    vol_values = [2.5, 3.0]  # 2 values
    rsi_5m_values = [52, 55]  # 2 values
    dist_5m_values = [0.4, 0.5]  # 2 values
    # Total: 4 × 3 × 3 × 2 × 2 × 2 = 288 configs

    results = []
    total_configs = len(stop_values) * len(target_values) * len(body_values) * len(vol_values) * len(rsi_5m_values) * len(dist_5m_values)

    print(f"\nTesting {total_configs} configurations...")

    config_num = 0
    for stop, target, body, vol, rsi_5m, dist_5m in product(
        stop_values, target_values, body_values, vol_values, rsi_5m_values, dist_5m_values
    ):
        config_num += 1

        if config_num % 20 == 0:
            print(f"  Progress: {config_num}/{total_configs}")

        result = backtest_long(df, df_5m, stop, target, body, vol, rsi_5m, dist_5m)

        if result and result['total_trades'] >= 5:  # Min 5 trades
            results.append(result)

    if len(results) == 0:
        print("\n❌ No configurations produced ≥5 trades")
        return

    # Sort by R:R ratio
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('rr_ratio', ascending=False)

    # Save results
    output_path = '/workspaces/Carebiuro_windykacja/trading/results/fartcoin_bingx_long_optimization.csv'
    results_df.to_csv(output_path, index=False)

    # Print top 10
    print(f"\n{'='*80}")
    print("TOP 10 CONFIGURATIONS (by R:R ratio)")
    print("="*80)

    top10 = results_df.head(10)
    for idx, row in top10.iterrows():
        print(f"\n#{top10.index.get_loc(idx) + 1}")
        print(f"  Return: {row['total_return']:+.2f}% | DD: {row['max_drawdown']:.2f}% | R:R: {row['rr_ratio']:.2f}x")
        print(f"  Trades: {row['total_trades']:.0f} | WR: {row['win_rate']:.1f}%")
        print(f"  Stop: {row['stop_atr']:.1f}x | Target: {row['target_atr']:.1f}x | Body: {row['body_thresh']:.2f}% | Vol: {row['vol_mult']:.1f}x")
        print(f"  5m RSI: >{row['rsi_5m_min']:.0f} | 5m Dist: >{row['dist_5m_min']:.1f}%")

    print(f"\n✅ Results saved to {output_path}")
    print(f"✅ Found {len(results_df)} profitable configurations")


if __name__ == "__main__":
    main()
