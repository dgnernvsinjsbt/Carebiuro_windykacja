#!/usr/bin/env python3
"""
Analyze entry timing: Are we shorting pullbacks or falling knives?
"""

import pandas as pd
import numpy as np

def calculate_ema(prices: pd.Series, period: int) -> pd.Series:
    return prices.ewm(span=period, adjust=False).mean()

def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()

# Load PENGU data
df = pd.read_csv('/workspaces/Carebiuro_windykacja/pengu_15m_3months.csv')

# Calculate indicators
df['ema5'] = calculate_ema(df['close'], 5)
df['ema20'] = calculate_ema(df['close'], 20)

# Look back periods to understand context
for lookback in [1, 3, 5, 10, 20]:
    df[f'change_{lookback}b'] = (df['close'] - df['close'].shift(lookback)) / df['close'].shift(lookback) * 100

# Recent high/low
df['high_5'] = df['high'].rolling(5).max()
df['high_10'] = df['high'].rolling(10).max()
df['high_20'] = df['high'].rolling(20).max()

# Distance from recent highs
df['dist_from_5h'] = (df['close'] - df['high_5']) / df['high_5'] * 100
df['dist_from_10h'] = (df['close'] - df['high_10']) / df['high_10'] * 100
df['dist_from_20h'] = (df['close'] - df['high_20']) / df['high_20'] * 100

# Signal
df['signal'] = 0
df.loc[(df['ema5'] < df['ema20']) & (df['ema5'].shift(1) >= df['ema20'].shift(1)), 'signal'] = -1

# Backtest with best config
sl = 0.01
tp = 0.025
fee = 0.0001

trades = []
in_position = False

for i in range(50, len(df)):
    row = df.iloc[i]

    if not in_position:
        if row['signal'] == -1:
            entry_idx = i
            in_position = True
            entry_price = row['close']
            stop_loss = entry_price * (1 + sl)
            take_profit = entry_price * (1 - tp)
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
            net_pnl = pnl_pct - fee

            # Capture entry context
            entry_row = df.iloc[entry_idx]
            trades.append({
                'winner': net_pnl > 0,
                'pnl': net_pnl * 100,
                'change_1b': entry_row['change_1b'],
                'change_3b': entry_row['change_3b'],
                'change_5b': entry_row['change_5b'],
                'change_10b': entry_row['change_10b'],
                'change_20b': entry_row['change_20b'],
                'dist_from_5h': entry_row['dist_from_5h'],
                'dist_from_10h': entry_row['dist_from_10h'],
                'dist_from_20h': entry_row['dist_from_20h'],
            })

            in_position = False

trades_df = pd.DataFrame(trades)
winners = trades_df[trades_df['winner'] == True]
losers = trades_df[trades_df['winner'] == False]

print("=" * 80)
print("ENTRY TIMING ANALYSIS: Pullback vs Falling Knife")
print("=" * 80)

print("\n" + "=" * 80)
print("PRICE ACTION BEFORE ENTRY (negative = already falling)")
print("=" * 80)

print(f"\n{'Lookback Period':<20} {'All Trades':<15} {'Winners':<15} {'Losers':<15}")
print("-" * 80)

for period in [1, 3, 5, 10, 20]:
    col = f'change_{period}b'
    all_mean = trades_df[col].mean()
    win_mean = winners[col].mean()
    lose_mean = losers[col].mean()

    print(f"{period} bars before      {all_mean:>+12.2f}%   {win_mean:>+12.2f}%   {lose_mean:>+12.2f}%")

print("\n" + "=" * 80)
print("DISTANCE FROM RECENT HIGHS AT ENTRY")
print("=" * 80)

print(f"\n{'Period':<20} {'All Trades':<15} {'Winners':<15} {'Losers':<15}")
print("-" * 80)

for period in [5, 10, 20]:
    col = f'dist_from_{period}h'
    all_mean = trades_df[col].mean()
    win_mean = winners[col].mean()
    lose_mean = losers[col].mean()

    print(f"{period}-bar high       {all_mean:>+12.2f}%   {win_mean:>+12.2f}%   {lose_mean:>+12.2f}%")

print("\n" + "=" * 80)
print("INTERPRETATION")
print("=" * 80)

avg_1b = trades_df['change_1b'].mean()
avg_5b = trades_df['change_5b'].mean()
avg_20b = trades_df['change_20b'].mean()
dist_20h = trades_df['dist_from_20h'].mean()

print("\nOn average, when EMA crossover triggers:")

if avg_1b < 0:
    print(f"  • Price is DOWN {abs(avg_1b):.2f}% in last bar → Momentum already turning")
else:
    print(f"  • Price is UP {avg_1b:.2f}% in last bar → Late weakness signal")

if avg_5b < 0:
    print(f"  • Price is DOWN {abs(avg_5b):.2f}% in last 5 bars → Short-term downtrend")
else:
    print(f"  • Price is UP {avg_5b:.2f}% in last 5 bars → Pullback from rally")

if avg_20b < 0:
    print(f"  • Price is DOWN {abs(avg_20b):.2f}% in last 20 bars → Longer-term downtrend")
else:
    print(f"  • Price is UP {avg_20b:.2f}% in last 20 bars → Reversal from higher levels")

print(f"  • Entry is {abs(dist_20h):.2f}% below 20-bar high")

if dist_20h > -3:
    print("\n⚠️  WARNING: Entering very close to recent highs (near-top short)")
    print("    This is GOOD for shorts - catching early weakness")
elif dist_20h < -8:
    print("\n⚠️  WARNING: Entering far from recent highs (falling knife territory)")
    print("    Already dropped significantly before entry signal")
else:
    print("\n✅ HEALTHY: Entering at moderate distance from highs")
    print("    Good balance between confirmation and not chasing")

# Falling knife vs pullback classification
print("\n" + "=" * 80)
print("TRADE CLASSIFICATION")
print("=" * 80)

# Classify each trade
trades_df['type'] = 'Unknown'

# Pullback: price was up recently (5-20 bars), now turning
trades_df.loc[(trades_df['change_5b'] > 0) & (trades_df['change_1b'] < 0), 'type'] = 'Pullback from rally'

# Falling knife: already down 3+ bars and 5+ bars
trades_df.loc[(trades_df['change_3b'] < -1) & (trades_df['change_5b'] < -2), 'type'] = 'Falling knife'

# Reversal: up medium-term, down short-term
trades_df.loc[(trades_df['change_20b'] > 0) & (trades_df['change_5b'] < 0), 'type'] = 'Reversal from higher'

# Downtrend continuation: all periods negative
trades_df.loc[(trades_df['change_5b'] < 0) & (trades_df['change_10b'] < 0) & (trades_df['change_20b'] < 0), 'type'] = 'Downtrend continuation'

for trade_type in ['Pullback from rally', 'Reversal from higher', 'Downtrend continuation', 'Falling knife']:
    subset = trades_df[trades_df['type'] == trade_type]
    if len(subset) > 0:
        win_rate = subset['winner'].mean() * 100
        avg_pnl = subset['pnl'].mean()
        count = len(subset)
        pct = count / len(trades_df) * 100

        status = "✅" if win_rate > 40 else "⚠️" if win_rate > 35 else "❌"
        print(f"{status} {trade_type:<25} {count:>3} ({pct:>5.1f}%) | Win: {win_rate:>5.1f}% | Avg: {avg_pnl:>+6.2f}%")

print("\n" + "=" * 80)
print("CONCLUSION")
print("=" * 80)

pullback_pct = len(trades_df[trades_df['type'] == 'Pullback from rally']) / len(trades_df) * 100
knife_pct = len(trades_df[trades_df['type'] == 'Falling knife']) / len(trades_df) * 100

if pullback_pct > knife_pct:
    print(f"\n✅ Strategy is MOSTLY catching pullbacks ({pullback_pct:.1f}% of trades)")
    print("   This is healthier - entering on weakness from strength")
elif knife_pct > pullback_pct:
    print(f"\n⚠️  Strategy catches MANY falling knives ({knife_pct:.1f}% of trades)")
    print("   Risk: entering after momentum already shifted")
else:
    print(f"\n➡️  Mixed strategy - {pullback_pct:.1f}% pullbacks, {knife_pct:.1f}% falling knives")
    print("   Captures various market conditions")