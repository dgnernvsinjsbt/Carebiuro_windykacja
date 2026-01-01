"""
Analyze the WORST losing trades
Find common characteristics to filter them out
"""
import pandas as pd
import numpy as np

def analyze_all_trades(df, month_name):
    """Collect detailed info on every trade"""

    delta = df['close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))

    df['tr'] = np.maximum(df['high'] - df['low'], np.maximum(
        abs(df['high'] - df['close'].shift(1)),
        abs(df['low'] - df['close'].shift(1))
    ))
    df['atr'] = df['tr'].rolling(14).mean()
    df['ret_20'] = (df['close'] / df['close'].shift(20) - 1) * 100

    # Additional metrics
    df['ret_4h'] = (df['close'] - df['close'].shift(16)) / df['close'].shift(16) * 100
    df['ret_4h_abs'] = abs(df['ret_4h'])
    df['avg_move_size'] = df['ret_4h_abs'].rolling(96).mean()

    # Recent signal quality
    df['signal'] = 0
    df.loc[(df['rsi'].shift(1) < 35) & (df['rsi'] >= 35), 'signal'] = 1
    df.loc[(df['rsi'].shift(1) > 65) & (df['rsi'] <= 65), 'signal'] = -1
    df['fwd_ret_12'] = (df['close'].shift(-12) - df['close']) / df['close'] * 100

    trades = []
    equity = 100.0
    position = None
    pending_order = None
    trade_number = 0

    for i in range(300, len(df)):
        row = df.iloc[i]

        if pd.isna(row['rsi']) or pd.isna(row['atr']) or pd.isna(row['ret_20']):
            continue

        if pending_order:
            bars_waiting = i - pending_order['signal_bar']
            if bars_waiting > 8:
                pending_order = None
                continue

            if pending_order['direction'] == 'LONG':
                if row['low'] <= pending_order['limit_price']:
                    position = {
                        'direction': 'LONG',
                        'entry': pending_order['limit_price'],
                        'entry_bar': i,
                        'sl_price': pending_order['sl_price'],
                        'tp_price': pending_order['tp_price'],
                        'size': pending_order['size'],
                        'entry_rsi': row['rsi'],
                        'entry_atr': row['atr'],
                        'entry_move_size': row['avg_move_size']
                    }
                    pending_order = None
            else:
                if row['high'] >= pending_order['limit_price']:
                    position = {
                        'direction': 'SHORT',
                        'entry': pending_order['limit_price'],
                        'entry_bar': i,
                        'sl_price': pending_order['sl_price'],
                        'tp_price': pending_order['tp_price'],
                        'size': pending_order['size'],
                        'entry_rsi': row['rsi'],
                        'entry_atr': row['atr'],
                        'entry_move_size': row['avg_move_size']
                    }
                    pending_order = None

        if position:
            pnl_pct = None
            exit_type = None

            if position['direction'] == 'LONG':
                if row['low'] <= position['sl_price']:
                    pnl_pct = ((position['sl_price'] - position['entry']) / position['entry']) * 100
                    exit_type = 'SL'
                elif row['high'] >= position['tp_price']:
                    pnl_pct = ((position['tp_price'] - position['entry']) / position['entry']) * 100
                    exit_type = 'TP'
            else:
                if row['high'] >= position['sl_price']:
                    pnl_pct = ((position['entry'] - position['sl_price']) / position['entry']) * 100
                    exit_type = 'SL'
                elif row['low'] <= position['tp_price']:
                    pnl_pct = ((position['entry'] - position['tp_price']) / position['entry']) * 100
                    exit_type = 'TP'

            if pnl_pct is not None:
                pnl_dollar = position['size'] * (pnl_pct / 100) - position['size'] * 0.001
                equity += pnl_dollar

                trade_number += 1

                # Calculate recent signal quality at entry
                recent_signals = df.iloc[max(0, position['entry_bar']-384):position['entry_bar']]
                signal_rows = recent_signals[recent_signals['signal'] != 0]
                recent_signal_quality = signal_rows['fwd_ret_12'].mean() if len(signal_rows) >= 5 else np.nan

                trades.append({
                    'month': month_name,
                    'trade_num': trade_number,
                    'direction': position['direction'],
                    'pnl_pct': pnl_pct,
                    'pnl_dollar': pnl_dollar,
                    'exit': exit_type,
                    'entry_rsi': position['entry_rsi'],
                    'entry_atr': position['entry_atr'],
                    'entry_atr_pct': position['entry_atr'] / position['entry'] * 100,
                    'entry_move_size': position['entry_move_size'],
                    'signal_quality': recent_signal_quality,
                    'winner': pnl_pct > 0
                })
                position = None
                continue

        if not position and not pending_order and i > 0:
            prev_row = df.iloc[i-1]

            if row['ret_20'] <= 0:
                continue
            if pd.isna(prev_row['rsi']):
                continue

            signal_price = row['close']
            atr = row['atr']

            if prev_row['rsi'] < 35 and row['rsi'] >= 35:
                limit_price = signal_price - (atr * 0.1)
                sl_price = limit_price - (atr * 1.2)
                tp_price = limit_price + (atr * 3.0)
                sl_dist = abs((limit_price - sl_price) / limit_price) * 100
                size = (equity * 0.12) / (sl_dist / 100)

                pending_order = {
                    'direction': 'LONG',
                    'limit_price': limit_price,
                    'sl_price': sl_price,
                    'tp_price': tp_price,
                    'size': size,
                    'signal_bar': i
                }

            elif prev_row['rsi'] > 65 and row['rsi'] <= 65:
                limit_price = signal_price + (atr * 0.1)
                sl_price = limit_price + (atr * 1.2)
                tp_price = limit_price - (atr * 3.0)
                sl_dist = abs((sl_price - limit_price) / limit_price) * 100
                size = (equity * 0.12) / (sl_dist / 100)

                pending_order = {
                    'direction': 'SHORT',
                    'limit_price': limit_price,
                    'sl_price': sl_price,
                    'tp_price': tp_price,
                    'size': size,
                    'signal_bar': i
                }

    return trades

print('=' * 140)
print('ANALYZING WORST LOSING TRADES')
print('=' * 140)

months = [
    ('June', 'melania_june_2025_15m.csv'),
    ('July', 'melania_july_2025_15m.csv'),
    ('August', 'melania_august_2025_15m.csv'),
    ('September', 'melania_september_2025_15m.csv'),
    ('October', 'melania_october_2025_15m.csv'),
    ('November', 'melania_november_2025_15m.csv'),
    ('December', 'melania_december_2025_15m.csv'),
]

all_trades = []

for month_name, filename in months:
    df = pd.read_csv(filename)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    trades = analyze_all_trades(df.copy(), month_name)
    all_trades.extend(trades)

df_all = pd.DataFrame(all_trades)

# Separate winners and losers
losers = df_all[df_all['pnl_dollar'] < 0].copy()
winners = df_all[df_all['pnl_dollar'] > 0].copy()

# Find worst 20% of losers
losers_sorted = losers.sort_values('pnl_dollar')
worst_20pct_count = int(len(losers) * 0.2)
worst_losers = losers_sorted.head(worst_20pct_count)
acceptable_losers = losers_sorted.tail(len(losers) - worst_20pct_count)

print(f"\nTotal trades: {len(df_all)}")
print(f"Winners: {len(winners)} (${winners['pnl_dollar'].sum():.2f})")
print(f"Losers: {len(losers)} (${losers['pnl_dollar'].sum():.2f})")
print(f"Worst 20% losers: {len(worst_losers)} (${worst_losers['pnl_dollar'].sum():.2f}) - {worst_losers['pnl_dollar'].sum()/losers['pnl_dollar'].sum()*100:.1f}% of total loss")

# Compare characteristics
print('\n' + '=' * 140)
print('WORST LOSERS vs ACCEPTABLE LOSERS vs WINNERS')
print('=' * 140)

metrics = [
    ('entry_rsi', 'Entry RSI'),
    ('entry_atr_pct', 'Entry ATR %'),
    ('entry_move_size', 'Avg Move Size %'),
    ('signal_quality', 'Signal Quality'),
]

print(f"\n{'Metric':<20} {'Worst Losers':<15} {'Accept Losers':<15} {'Winners':<15} {'Difference'}")
print('-' * 140)

for col, label in metrics:
    worst_avg = worst_losers[col].mean()
    accept_avg = acceptable_losers[col].mean()
    winner_avg = winners[col].mean()
    diff = worst_avg - winner_avg

    print(f"{label:<20} {worst_avg:>14.2f} {accept_avg:>14.2f} {winner_avg:>14.2f} {diff:>+14.2f}")

# Show distribution
print('\n' + '=' * 140)
print('WORST 20 TRADES DETAIL')
print('=' * 140)
print(f"\n{'Month':<12} {'#':<5} {'Dir':<6} {'P&L':<10} {'RSI':<8} {'ATR%':<8} {'Move%':<8} {'SigQual':<10}")
print('-' * 140)

for _, trade in worst_losers.head(20).iterrows():
    print(f"{trade['month']:<12} {trade['trade_num']:<5.0f} {trade['direction']:<6} "
          f"${trade['pnl_dollar']:>8.2f} {trade['entry_rsi']:>7.1f} {trade['entry_atr_pct']:>7.2f} "
          f"{trade['entry_move_size']:>7.2f} {trade['signal_quality']:>9.2f}")

# Test filters
print('\n' + '=' * 140)
print('POTENTIAL FILTERS TO AVOID WORST LOSERS')
print('=' * 140)

# Test signal quality filter
sq_threshold = -0.1
filtered_trades = df_all[df_all['signal_quality'] > sq_threshold]
filtered_worst = worst_losers[worst_losers['signal_quality'] > sq_threshold]

print(f"\n1. Signal Quality > {sq_threshold}%:")
print(f"   Filters out {len(worst_losers) - len(filtered_worst)}/{len(worst_losers)} worst losers ({(1 - len(filtered_worst)/len(worst_losers))*100:.1f}%)")
print(f"   Keeps {len(filtered_trades)}/{len(df_all)} total trades ({len(filtered_trades)/len(df_all)*100:.1f}%)")

# Test move size filter
move_threshold = 1.5
filtered_trades = df_all[df_all['entry_move_size'] > move_threshold]
filtered_worst = worst_losers[worst_losers['entry_move_size'] > move_threshold]

print(f"\n2. Move Size > {move_threshold}%:")
print(f"   Filters out {len(worst_losers) - len(filtered_worst)}/{len(worst_losers)} worst losers ({(1 - len(filtered_worst)/len(worst_losers))*100:.1f}%)")
print(f"   Keeps {len(filtered_trades)}/{len(df_all)} total trades ({len(filtered_trades)/len(df_all)*100:.1f}%)")

# Test combo
combo_trades = df_all[(df_all['signal_quality'] > sq_threshold) & (df_all['entry_move_size'] > move_threshold)]
combo_worst = worst_losers[(worst_losers['signal_quality'] > sq_threshold) & (worst_losers['entry_move_size'] > move_threshold)]

print(f"\n3. COMBO (Signal Quality > {sq_threshold}% AND Move Size > {move_threshold}%):")
print(f"   Filters out {len(worst_losers) - len(combo_worst)}/{len(worst_losers)} worst losers ({(1 - len(combo_worst)/len(worst_losers))*100:.1f}%)")
print(f"   Keeps {len(combo_trades)}/{len(df_all)} total trades ({len(combo_trades)/len(df_all)*100:.1f}%)")

# Calculate what return would be
combo_return = (combo_trades['pnl_dollar'].sum() / 100) * 100
print(f"   Estimated return: {combo_return:+.1f}% (vs +106.6% baseline)")

print('\n' + '=' * 140)
