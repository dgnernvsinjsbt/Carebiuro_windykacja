"""
PIPPIN Fresh Crosses - DEEP WINNER/LOSER Analysis
Analyze the ACTUAL 64 trades from Fresh Crosses strategy
Find what the 11 TP winners have vs 42 SL losers
Then test new filters based on those insights
"""

import pandas as pd
import numpy as np

df = pd.read_csv('pippin_7d_bingx.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print("="*90)
print("PIPPIN FRESH CROSSES - DEEP WINNER/LOSER ANALYSIS")
print("="*90)
print()

# Calculate ALL possible indicators
df['ema_9'] = df['close'].ewm(span=9, adjust=False).mean()
df['ema_21'] = df['close'].ewm(span=21, adjust=False).mean()
df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()

df['tr'] = np.maximum(
    df['high'] - df['low'],
    np.maximum(
        abs(df['high'] - df['close'].shift(1)),
        abs(df['low'] - df['close'].shift(1))
    )
)
df['atr'] = df['tr'].rolling(window=14).mean()
df['atr_avg'] = df['atr'].rolling(window=20).mean()

df['volume_avg'] = df['volume'].rolling(window=20).mean()

delta = df['close'].diff()
gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
rs = gain / loss
df['rsi'] = 100 - (100 / (1 + rs))

df['ema_9_prev'] = df['ema_9'].shift(1)
df['ema_21_prev'] = df['ema_21'].shift(1)

df['cross_up'] = (df['ema_9'] > df['ema_21']) & (df['ema_9_prev'] <= df['ema_21_prev'])
df['cross_down'] = (df['ema_9'] < df['ema_21']) & (df['ema_9_prev'] >= df['ema_21_prev'])

# Consecutive bars
df['consecutive_ups'] = 0
df['consecutive_downs'] = 0

for i in range(1, len(df)):
    if df.loc[i, 'close'] > df.loc[i, 'open']:
        df.loc[i, 'consecutive_ups'] = df.loc[i-1, 'consecutive_ups'] + 1
        df.loc[i, 'consecutive_downs'] = 0
    elif df.loc[i, 'close'] < df.loc[i, 'open']:
        df.loc[i, 'consecutive_downs'] = df.loc[i-1, 'consecutive_downs'] + 1
        df.loc[i, 'consecutive_ups'] = 0

# Additional features
df['hour'] = df['timestamp'].dt.hour
df['body_pct'] = abs(df['close'] - df['open']) / df['open'] * 100
df['volume_ratio'] = df['volume'] / df['volume_avg']
df['atr_ratio'] = df['atr'] / df['atr_avg']
df['ema50_dist_pct'] = ((df['close'] - df['ema_50']) / df['ema_50'] * 100).abs()

# Candle type
df['is_green'] = df['close'] > df['open']
df['is_red'] = df['close'] < df['open']
df['upper_wick'] = df['high'] - df[['close', 'open']].max(axis=1)
df['lower_wick'] = df[['close', 'open']].min(axis=1) - df['low']
df['upper_wick_pct'] = df['upper_wick'] / df['close'] * 100
df['lower_wick_pct'] = df['lower_wick'] / df['close'] * 100

# Trend state
df['uptrend'] = df['close'] > df['ema_50']
df['downtrend'] = df['close'] < df['ema_50']

# Run Fresh Crosses strategy to get the 64 trades
SL_MULT = 1.5
TP_MULT = 10.0
MAX_HOLD_BARS = 120
FEE_PCT = 0.10

trades = []
in_position = False
position = None

for i in range(50, len(df)):
    row = df.iloc[i]

    # Exit logic
    if in_position:
        bars_held = i - position['entry_idx']
        current_price = row['close']

        hit_sl = False
        hit_tp = False
        time_exit = False

        if position['direction'] == 'LONG':
            if current_price <= position['stop_loss']:
                hit_sl = True
                exit_price = position['stop_loss']
            elif current_price >= position['take_profit']:
                hit_tp = True
                exit_price = position['take_profit']
            elif bars_held >= MAX_HOLD_BARS:
                time_exit = True
                exit_price = current_price
        else:
            if current_price >= position['stop_loss']:
                hit_sl = True
                exit_price = position['stop_loss']
            elif current_price <= position['take_profit']:
                hit_tp = True
                exit_price = position['take_profit']
            elif bars_held >= MAX_HOLD_BARS:
                time_exit = True
                exit_price = current_price

        if hit_sl or hit_tp or time_exit:
            entry_row = df.iloc[position['entry_idx']]

            if position['direction'] == 'LONG':
                pnl_pct = ((exit_price / position['entry_price']) - 1) * 100
            else:
                pnl_pct = ((position['entry_price'] / exit_price) - 1) * 100

            pnl_pct -= FEE_PCT

            # Capture ALL entry features
            trades.append({
                'entry_time': position['entry_time'],
                'exit_reason': 'SL' if hit_sl else ('TP' if hit_tp else 'Time'),
                'direction': position['direction'],
                'pnl_pct': pnl_pct,
                # Entry features
                'hour': entry_row['hour'],
                'rsi': entry_row['rsi'],
                'body_pct': entry_row['body_pct'],
                'volume_ratio': entry_row['volume_ratio'],
                'atr_ratio': entry_row['atr_ratio'],
                'ema50_dist': entry_row['ema50_dist_pct'],
                'is_green': entry_row['is_green'],
                'is_red': entry_row['is_red'],
                'upper_wick_pct': entry_row['upper_wick_pct'],
                'lower_wick_pct': entry_row['lower_wick_pct'],
                'uptrend': entry_row['uptrend'],
            })

            in_position = False
            position = None

    # Entry logic - FRESH CROSSES ONLY
    if not in_position:
        if row['cross_up'] and row['consecutive_ups'] == 0:
            entry_price = row['close']
            atr = row['atr']

            position = {
                'entry_idx': i,
                'entry_time': row['timestamp'],
                'direction': 'LONG',
                'entry_price': entry_price,
                'stop_loss': entry_price - (SL_MULT * atr),
                'take_profit': entry_price + (TP_MULT * atr),
            }
            in_position = True

        elif row['cross_down'] and row['consecutive_downs'] == 0:
            entry_price = row['close']
            atr = row['atr']

            position = {
                'entry_idx': i,
                'entry_time': row['timestamp'],
                'direction': 'SHORT',
                'entry_price': entry_price,
                'stop_loss': entry_price + (SL_MULT * atr),
                'take_profit': entry_price - (TP_MULT * atr),
            }
            in_position = True

# Analyze trades
trades_df = pd.DataFrame(trades)

print(f"Total Fresh Cross Trades: {len(trades_df)}")
print()

tp_winners = trades_df[trades_df['exit_reason'] == 'TP']
sl_losers = trades_df[trades_df['exit_reason'] == 'SL']
time_exits = trades_df[trades_df['exit_reason'] == 'Time']

print(f"TP Winners: {len(tp_winners)} trades")
print(f"SL Losers: {len(sl_losers)} trades")
print(f"Time Exits: {len(time_exits)} trades")
print()

print("="*90)
print("DEEP FEATURE ANALYSIS: TP WINNERS vs SL LOSERS")
print("="*90)
print()

features = [
    ('hour', 'Hour'),
    ('rsi', 'RSI'),
    ('body_pct', 'Body %'),
    ('volume_ratio', 'Volume Ratio'),
    ('atr_ratio', 'ATR Ratio'),
    ('ema50_dist', 'EMA50 Distance %'),
    ('upper_wick_pct', 'Upper Wick %'),
    ('lower_wick_pct', 'Lower Wick %'),
]

discriminators = []

for feature, label in features:
    winner_avg = tp_winners[feature].mean()
    loser_avg = sl_losers[feature].mean()
    diff = winner_avg - loser_avg
    diff_pct = (diff / loser_avg * 100) if loser_avg != 0 else 0

    winner_median = tp_winners[feature].median()
    loser_median = sl_losers[feature].median()

    print(f"{label}:")
    print(f"  Winners: Avg={winner_avg:.2f}, Median={winner_median:.2f}")
    print(f"  Losers:  Avg={loser_avg:.2f}, Median={loser_median:.2f}")
    print(f"  Diff: {diff:+.2f} ({diff_pct:+.1f}%)")

    if abs(diff_pct) > 15:
        print(f"  🔥 SIGNIFICANT DIFFERENCE!")
    print()

    discriminators.append({
        'feature': feature,
        'label': label,
        'winner_avg': winner_avg,
        'loser_avg': loser_avg,
        'diff': diff,
        'diff_pct': diff_pct,
    })

# Boolean features
print("BOOLEAN FEATURES:")
print()

bool_features = [
    ('is_green', 'Green Candle'),
    ('is_red', 'Red Candle'),
    ('uptrend', 'Above EMA50'),
]

for feature, label in bool_features:
    winner_pct = (tp_winners[feature].sum() / len(tp_winners) * 100)
    loser_pct = (sl_losers[feature].sum() / len(sl_losers) * 100)
    diff = winner_pct - loser_pct

    print(f"{label}:")
    print(f"  Winners: {winner_pct:.1f}%")
    print(f"  Losers:  {loser_pct:.1f}%")
    print(f"  Diff: {diff:+.1f}pp")

    if abs(diff) > 15:
        print(f"  🔥 SIGNIFICANT DIFFERENCE!")
    print()

# Sort discriminators
disc_df = pd.DataFrame(discriminators)
disc_df['abs_diff_pct'] = disc_df['diff_pct'].abs()
disc_df = disc_df.sort_values('abs_diff_pct', ascending=False)

print("="*90)
print("TOP DISCRIMINATING FEATURES")
print("="*90)
print(disc_df[['label', 'winner_avg', 'loser_avg', 'diff', 'diff_pct']].to_string(index=False))
print()

# Save for inspection
trades_df.to_csv('results/pippin_fresh_crosses_64_trades.csv', index=False)

print("="*90)
print("🎯 ACTIONABLE FILTERS (Based on differences)")
print("="*90)
print()

# Find optimal thresholds
print("Testing threshold-based filters:")
print()

threshold_tests = []

# Test each numeric feature
for feature, label in features:
    # Try filtering on winner avg
    threshold = tp_winners[feature].median()

    # For features where winners are HIGHER
    if disc_df[disc_df['feature'] == feature]['diff'].iloc[0] > 0:
        filtered = trades_df[trades_df[feature] >= threshold]
        direction = '>='
    else:
        # For features where winners are LOWER
        filtered = trades_df[trades_df[feature] <= threshold]
        direction = '<='

    if len(filtered) > 0:
        tp_rate = (len(filtered[filtered['exit_reason'] == 'TP']) / len(filtered) * 100)
        threshold_tests.append({
            'feature': label,
            'threshold': threshold,
            'direction': direction,
            'trades_kept': len(filtered),
            'tp_rate': tp_rate,
        })

threshold_df = pd.DataFrame(threshold_tests).sort_values('tp_rate', ascending=False)

print("Best Thresholds (by TP rate improvement):")
print(threshold_df.to_string(index=False))
print()

print("="*90)
print("💾 Files saved:")
print("  - results/pippin_fresh_crosses_64_trades.csv")
print("="*90)
