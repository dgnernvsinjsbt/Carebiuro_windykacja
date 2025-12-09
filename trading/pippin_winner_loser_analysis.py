"""
PIPPIN - Winner vs Loser Pattern Discovery
Analyze the 184 trades from unfiltered EMA Cross 10x TP strategy
Find what WINNERS have in common vs what LOSERS share
"""

import pandas as pd
import numpy as np

# Load PIPPIN data
df = pd.read_csv('pippin_7d_bingx.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# Calculate all indicators
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

# Calculate features
df['hour'] = df['timestamp'].dt.hour
df['body_pct'] = abs(df['close'] - df['open']) / df['open'] * 100
df['volume_ratio'] = df['volume'] / df['volume_avg']
df['atr_ratio'] = df['atr'] / df['atr_avg']
df['ema50_dist_pct'] = ((df['close'] - df['ema_50']) / df['ema_50'] * 100).abs()

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

print("="*90)
print("PIPPIN WINNER VS LOSER PATTERN DISCOVERY")
print("="*90)
print()

# Run unfiltered backtest to get trades
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

            # Capture entry conditions
            trades.append({
                'entry_time': position['entry_time'],
                'exit_time': row['timestamp'],
                'direction': position['direction'],
                'entry_price': position['entry_price'],
                'exit_price': exit_price,
                'pnl_pct': pnl_pct,
                'exit_reason': 'SL' if hit_sl else ('TP' if hit_tp else 'Time'),
                # Entry features
                'entry_hour': entry_row['hour'],
                'entry_rsi': entry_row['rsi'],
                'entry_body_pct': entry_row['body_pct'],
                'entry_volume_ratio': entry_row['volume_ratio'],
                'entry_atr_ratio': entry_row['atr_ratio'],
                'entry_ema50_dist': entry_row['ema50_dist_pct'],
                'entry_consecutive_ups': entry_row['consecutive_ups'],
                'entry_consecutive_downs': entry_row['consecutive_downs'],
            })

            in_position = False
            position = None

    # Entry logic
    if not in_position:
        if row['cross_up']:
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

        elif row['cross_down']:
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

print(f"Total Trades: {len(trades_df)}")
print()

# Split into winners and losers
tp_winners = trades_df[trades_df['exit_reason'] == 'TP']
sl_losers = trades_df[trades_df['exit_reason'] == 'SL']

print(f"TP Winners: {len(tp_winners)} trades")
print(f"SL Losers: {len(sl_losers)} trades")
print(f"Time Exits: {len(trades_df[trades_df['exit_reason'] == 'Time'])} trades")
print()

print("="*90)
print("FEATURE COMPARISON: TP WINNERS vs SL LOSERS")
print("="*90)
print()

features = [
    ('entry_hour', 'Entry Hour'),
    ('entry_rsi', 'Entry RSI'),
    ('entry_body_pct', 'Entry Body %'),
    ('entry_volume_ratio', 'Volume Ratio'),
    ('entry_atr_ratio', 'ATR Ratio'),
    ('entry_ema50_dist', 'EMA50 Distance %'),
    ('entry_consecutive_ups', 'Consecutive Ups'),
    ('entry_consecutive_downs', 'Consecutive Downs'),
]

winner_profiles = []
loser_profiles = []

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

    if abs(diff_pct) > 20:
        print(f"  🔥 SIGNIFICANT DIFFERENCE!")
    print()

    winner_profiles.append({
        'feature': feature,
        'label': label,
        'winner_avg': winner_avg,
        'loser_avg': loser_avg,
        'diff': diff,
        'diff_pct': diff_pct,
    })

# Find most discriminating features
profiles_df = pd.DataFrame(winner_profiles)
profiles_df['abs_diff_pct'] = profiles_df['diff_pct'].abs()
profiles_df = profiles_df.sort_values('abs_diff_pct', ascending=False)

print("="*90)
print("TOP DISCRIMINATING FEATURES (sorted by difference %)")
print("="*90)
print()
print(profiles_df[['label', 'winner_avg', 'loser_avg', 'diff', 'diff_pct']].to_string(index=False))
print()

# Direction breakdown
print("="*90)
print("DIRECTION ANALYSIS")
print("="*90)
print()
tp_longs = tp_winners[tp_winners['direction'] == 'LONG']
tp_shorts = tp_winners[tp_winners['direction'] == 'SHORT']
sl_longs = sl_losers[sl_losers['direction'] == 'LONG']
sl_shorts = sl_losers[sl_losers['direction'] == 'SHORT']

print(f"TP Winners - LONG: {len(tp_longs)} ({len(tp_longs)/len(tp_winners)*100:.1f}%)")
print(f"TP Winners - SHORT: {len(tp_shorts)} ({len(tp_shorts)/len(tp_winners)*100:.1f}%)")
print(f"SL Losers - LONG: {len(sl_longs)} ({len(sl_longs)/len(sl_losers)*100:.1f}%)")
print(f"SL Losers - SHORT: {len(sl_shorts)} ({len(sl_shorts)/len(sl_losers)*100:.1f}%)")
print()

# Time of day analysis
print("="*90)
print("HOUR OF DAY DISTRIBUTION")
print("="*90)
print()

winner_hours = tp_winners['entry_hour'].value_counts().sort_index()
loser_hours = sl_losers['entry_hour'].value_counts().sort_index()

print("Hour | TP Winners | SL Losers | TP % of Total")
print("-----|------------|-----------|---------------")
for hour in range(24):
    tp_count = winner_hours.get(hour, 0)
    sl_count = loser_hours.get(hour, 0)
    total = tp_count + sl_count
    tp_pct = (tp_count / total * 100) if total > 0 else 0
    print(f"{hour:2d}   | {tp_count:10d} | {sl_count:9d} | {tp_pct:6.1f}%")
print()

# Find best hours (where TP % is highest)
hourly_stats = []
for hour in range(24):
    tp_count = winner_hours.get(hour, 0)
    sl_count = loser_hours.get(hour, 0)
    total = tp_count + sl_count
    if total >= 3:  # At least 3 trades
        tp_pct = (tp_count / total * 100)
        hourly_stats.append({'hour': hour, 'tp_count': tp_count, 'total': total, 'tp_pct': tp_pct})

hourly_df = pd.DataFrame(hourly_stats).sort_values('tp_pct', ascending=False)

print("🔥 BEST HOURS (TP % > 20%):")
best_hours = hourly_df[hourly_df['tp_pct'] > 20]
if len(best_hours) > 0:
    for _, row in best_hours.iterrows():
        print(f"  Hour {int(row['hour']):2d}: {row['tp_pct']:.1f}% TP rate ({int(row['tp_count'])}/{int(row['total'])} trades)")
else:
    print("  None found (all hours < 20% TP rate)")
print()

# Volume/ATR threshold analysis
print("="*90)
print("THRESHOLD ANALYSIS")
print("="*90)
print()

# Find optimal thresholds
thresholds_to_test = [
    ('entry_volume_ratio', [1.2, 1.3, 1.5, 1.8, 2.0]),
    ('entry_atr_ratio', [1.05, 1.1, 1.15, 1.2, 1.3]),
    ('entry_body_pct', [0.3, 0.5, 0.8, 1.0, 1.5]),
]

for feature, thresholds in thresholds_to_test:
    label = [f for f, l in features if f == feature][0]
    print(f"\n{label} Thresholds:")
    print("Threshold | Total Trades | TP Count | TP Rate | Would Keep")
    print("----------|--------------|----------|---------|------------")

    for threshold in thresholds:
        filtered = trades_df[trades_df[feature] >= threshold]
        filtered_tp = filtered[filtered['exit_reason'] == 'TP']

        total = len(filtered)
        tp_count = len(filtered_tp)
        tp_rate = (tp_count / total * 100) if total > 0 else 0

        print(f"  >={threshold:.2f}  | {total:12d} | {tp_count:8d} | {tp_rate:6.1f}% | {total} trades")

print()

# Save analysis
trades_df.to_csv('results/pippin_ema_trades_with_features.csv', index=False)
profiles_df.to_csv('results/pippin_winner_loser_profiles.csv', index=False)

print("="*90)
print("💾 Files saved:")
print("  - results/pippin_ema_trades_with_features.csv")
print("  - results/pippin_winner_loser_profiles.csv")
print("="*90)
