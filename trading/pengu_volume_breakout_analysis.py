#!/usr/bin/env python3
"""
PENGU Volume Breakout Analysis

Hypothesis: During high-volume candles (top 2-5%), PENGU stops chopping
and gives clean directional moves (whale activity).

Strategy:
- Wait for volume spike (top X% of candles)
- Enter in direction of spike close (bullish = long, bearish = short)
- Stop below/above the spike candle
- Target 2x-3x the spike candle range

Compare to normal PENGU chop where nothing works.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Load PENGU data
print("Loading PENGU data...")
df = pd.read_csv('pengu_usdt_1m_lbank.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Calculate indicators
df['body'] = df['close'] - df['open']
df['body_pct'] = (df['close'] - df['open']) / df['open'] * 100
df['range'] = df['high'] - df['low']
df['range_pct'] = (df['high'] - df['low']) / df['low'] * 100
df['is_green'] = df['close'] > df['open']

# Forward returns (what happens AFTER the volume spike)
for i in [1, 3, 5, 10, 20]:
    df[f'fwd_{i}'] = df['close'].shift(-i) / df['close'] - 1

# Calculate ATR for stop/target sizing (needed for backtest)
df['atr'] = df['range'].rolling(14).mean()

print(f"Total candles: {len(df)}")
print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
print()

# Volume percentiles
volume_percentiles = df['volume'].quantile([0.90, 0.95, 0.98, 0.99]).to_dict()
print("Volume Percentiles:")
for pct, vol in volume_percentiles.items():
    print(f"  {pct*100:.0f}%: {vol:,.0f}")
print()

# Analyze different volume thresholds
thresholds = [
    ('Top 10%', df['volume'].quantile(0.90)),
    ('Top 5%', df['volume'].quantile(0.95)),
    ('Top 2%', df['volume'].quantile(0.98)),
    ('Top 1%', df['volume'].quantile(0.99)),
]

results = []

for name, threshold in thresholds:
    # Find volume spike candles
    spikes = df[df['volume'] >= threshold].copy()

    # Separate bullish and bearish spikes
    bullish_spikes = spikes[spikes['is_green'] == True]
    bearish_spikes = spikes[spikes['is_green'] == False]

    print("=" * 80)
    print(f"{name} Volume Spikes (threshold: {threshold:,.0f})")
    print("=" * 80)
    print(f"Total spikes: {len(spikes)}")
    print(f"  Bullish (green): {len(bullish_spikes)} ({len(bullish_spikes)/len(spikes)*100:.1f}%)")
    print(f"  Bearish (red): {len(bearish_spikes)} ({len(bearish_spikes)/len(spikes)*100:.1f}%)")
    print()

    # Analyze BULLISH spikes (would we go LONG?)
    if len(bullish_spikes) > 0:
        print("BULLISH SPIKES (Long entry signal):")
        print(f"  Avg body size: {bullish_spikes['body_pct'].mean():.3f}%")
        print(f"  Avg volume: {bullish_spikes['volume'].mean():,.0f}")
        print()
        print("  Forward returns after bullish spike:")
        for i in [1, 3, 5, 10, 20]:
            fwd_ret = bullish_spikes[f'fwd_{i}'].mean() * 100
            win_rate = (bullish_spikes[f'fwd_{i}'] > 0).mean() * 100
            print(f"    +{i} bars: {fwd_ret:+.3f}% (WR: {win_rate:.1f}%)")
        print()

    # Analyze BEARISH spikes (would we go SHORT?)
    if len(bearish_spikes) > 0:
        print("BEARISH SPIKES (Short entry signal):")
        print(f"  Avg body size: {bearish_spikes['body_pct'].mean():.3f}%")
        print(f"  Avg volume: {bearish_spikes['volume'].mean():,.0f}")
        print()
        print("  Forward returns after bearish spike (negative = profit for short):")
        for i in [1, 3, 5, 10, 20]:
            fwd_ret = bearish_spikes[f'fwd_{i}'].mean() * 100
            win_rate = (bearish_spikes[f'fwd_{i}'] < 0).mean() * 100  # Negative = short profit
            print(f"    +{i} bars: {fwd_ret:+.3f}% (WR: {win_rate:.1f}%)")
        print()

    # Combined strategy: Long on bullish spikes, Short on bearish spikes
    total_trades = len(spikes)
    long_profits = bullish_spikes['fwd_5'].sum() if len(bullish_spikes) > 0 else 0
    short_profits = -bearish_spikes['fwd_5'].sum() if len(bearish_spikes) > 0 else 0  # Negative fwd = short profit
    total_profit_pct = (long_profits + short_profits) * 100

    avg_fwd_5 = (long_profits + short_profits) / total_trades if total_trades > 0 else 0

    results.append({
        'threshold': name,
        'total_spikes': total_trades,
        'bullish_spikes': len(bullish_spikes),
        'bearish_spikes': len(bearish_spikes),
        'avg_fwd_5': avg_fwd_5 * 100,
        'total_profit_pct': total_profit_pct,
    })

    print(f"COMBINED STRATEGY (Long bullish spikes, Short bearish spikes):")
    print(f"  Total trades: {total_trades}")
    print(f"  Avg 5-bar return: {avg_fwd_5*100:+.3f}%")
    print(f"  Total profit (5-bar hold): {total_profit_pct:+.2f}%")
    print()

# Summary comparison
print("=" * 80)
print("VOLUME THRESHOLD COMPARISON")
print("=" * 80)
results_df = pd.DataFrame(results)
print(results_df.to_string(index=False))
print()

# Best threshold
best = results_df.loc[results_df['avg_fwd_5'].idxmax()]
print(f"✅ BEST THRESHOLD: {best['threshold']}")
print(f"   Avg forward return: {best['avg_fwd_5']:.3f}%")
print(f"   Total trades: {int(best['total_spikes'])}")
print()

# Backtest the best threshold with stops/targets
print("=" * 80)
print(f"BACKTESTING: {best['threshold']} Volume Breakout Strategy")
print("=" * 80)

threshold_val = dict(thresholds)[best['threshold']]
spikes = df[df['volume'] >= threshold_val].copy()

trades = []
for idx, spike in spikes.iterrows():
    if pd.isna(spike['atr']):
        continue

    entry_price = spike['close']
    spike_range = spike['range']
    atr = spike['atr']

    # Direction based on candle color
    if spike['is_green']:
        # LONG
        direction = 'LONG'
        stop_loss = entry_price - (1.0 * atr)  # 1x ATR stop
        take_profit = entry_price + (2.0 * atr)  # 2x ATR target

        # Check next 20 bars for SL/TP hit
        for i in range(1, 21):
            if idx + i >= len(df):
                break
            candle = df.iloc[idx + i]

            # Check SL first (conservative)
            if candle['low'] <= stop_loss:
                exit_price = stop_loss
                pnl = (exit_price / entry_price - 1) - 0.001  # 0.1% fees
                trades.append({
                    'direction': direction,
                    'entry': entry_price,
                    'exit': exit_price,
                    'pnl': pnl,
                    'bars': i,
                    'exit_reason': 'SL'
                })
                break

            # Check TP
            if candle['high'] >= take_profit:
                exit_price = take_profit
                pnl = (exit_price / entry_price - 1) - 0.001
                trades.append({
                    'direction': direction,
                    'entry': entry_price,
                    'exit': exit_price,
                    'pnl': pnl,
                    'bars': i,
                    'exit_reason': 'TP'
                })
                break
        else:
            # Neither hit in 20 bars - exit at market
            exit_price = df.iloc[idx + 20]['close'] if idx + 20 < len(df) else entry_price
            pnl = (exit_price / entry_price - 1) - 0.001
            trades.append({
                'direction': direction,
                'entry': entry_price,
                'exit': exit_price,
                'pnl': pnl,
                'bars': 20,
                'exit_reason': 'TIME'
            })

    else:
        # SHORT
        direction = 'SHORT'
        stop_loss = entry_price + (1.0 * atr)  # 1x ATR stop
        take_profit = entry_price - (2.0 * atr)  # 2x ATR target

        # Check next 20 bars for SL/TP hit
        for i in range(1, 21):
            if idx + i >= len(df):
                break
            candle = df.iloc[idx + i]

            # Check SL first (conservative)
            if candle['high'] >= stop_loss:
                exit_price = stop_loss
                pnl = (entry_price / exit_price - 1) - 0.001  # Short P&L
                trades.append({
                    'direction': direction,
                    'entry': entry_price,
                    'exit': exit_price,
                    'pnl': pnl,
                    'bars': i,
                    'exit_reason': 'SL'
                })
                break

            # Check TP
            if candle['low'] <= take_profit:
                exit_price = take_profit
                pnl = (entry_price / exit_price - 1) - 0.001
                trades.append({
                    'direction': direction,
                    'entry': entry_price,
                    'exit': exit_price,
                    'pnl': pnl,
                    'bars': i,
                    'exit_reason': 'TP'
                })
                break
        else:
            # Neither hit in 20 bars - exit at market
            exit_price = df.iloc[idx + 20]['close'] if idx + 20 < len(df) else entry_price
            pnl = (entry_price / exit_price - 1) - 0.001
            trades.append({
                'direction': direction,
                'entry': entry_price,
                'exit': exit_price,
                'pnl': pnl,
                'bars': 20,
                'exit_reason': 'TIME'
            })

# Backtest results
trades_df = pd.DataFrame(trades)

if len(trades_df) > 0:
    total_return = trades_df['pnl'].sum() * 100
    avg_trade = trades_df['pnl'].mean() * 100
    win_rate = (trades_df['pnl'] > 0).mean() * 100
    avg_winner = trades_df[trades_df['pnl'] > 0]['pnl'].mean() * 100 if (trades_df['pnl'] > 0).any() else 0
    avg_loser = trades_df[trades_df['pnl'] < 0]['pnl'].mean() * 100 if (trades_df['pnl'] < 0).any() else 0

    print(f"Total trades: {len(trades_df)}")
    print(f"Total return: {total_return:+.2f}%")
    print(f"Avg trade: {avg_trade:+.3f}%")
    print(f"Win rate: {win_rate:.1f}%")
    print(f"Avg winner: {avg_winner:+.3f}%")
    print(f"Avg loser: {avg_loser:+.3f}%")
    print()

    # Exit reason breakdown
    print("Exit reasons:")
    print(trades_df['exit_reason'].value_counts())
    print()

    # Direction breakdown
    print("By direction:")
    for direction in ['LONG', 'SHORT']:
        direction_trades = trades_df[trades_df['direction'] == direction]
        if len(direction_trades) > 0:
            direction_return = direction_trades['pnl'].sum() * 100
            direction_wr = (direction_trades['pnl'] > 0).mean() * 100
            print(f"  {direction}: {len(direction_trades)} trades, {direction_return:+.2f}%, WR: {direction_wr:.1f}%")
    print()

    # Save results
    trades_df.to_csv('results/PENGU_volume_breakout_trades.csv', index=False)
    print("✅ Trades saved to: results/PENGU_volume_breakout_trades.csv")
else:
    print("❌ No trades generated")

print()
print("=" * 80)
print("CONCLUSION")
print("=" * 80)
print("Compare this to the baseline PENGU strategies that all lost money.")
print("If volume breakouts show positive returns, this validates your hypothesis:")
print("  - PENGU is choppy 90%+ of the time (unprofitable)")
print("  - But during volume spikes, whales create directional moves (profitable)")
print("  - Strategy: Only trade during volume events, ignore the rest")
