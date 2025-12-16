"""
Find PRECISE surgical filter - target ONLY the worst losers
MORE conservative filters that won't touch winners
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

    df['ret_4h'] = (df['close'] - df['close'].shift(16)) / df['close'].shift(16) * 100
    df['ret_4h_abs'] = abs(df['ret_4h'])
    df['avg_move_size'] = df['ret_4h_abs'].rolling(96).mean()

    df['signal'] = 0
    df.loc[(df['rsi'].shift(1) < 35) & (df['rsi'] >= 35), 'signal'] = 1
    df.loc[(df['rsi'].shift(1) > 65) & (df['rsi'] <= 65), 'signal'] = -1
    df['fwd_ret_12'] = (df['close'].shift(-12) - df['close']) / df['close'] * 100

    trades = []
    equity = 100.0
    position = None
    pending_order = None
    consecutive_losses = 0

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
                        'entry_move_size': row['avg_move_size'],
                        'consecutive_losses': consecutive_losses
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
                        'entry_move_size': row['avg_move_size'],
                        'consecutive_losses': consecutive_losses
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

                # Update consecutive losses
                if pnl_pct < 0:
                    consecutive_losses += 1
                else:
                    consecutive_losses = 0

                recent_signals = df.iloc[max(0, position['entry_bar']-384):position['entry_bar']]
                signal_rows = recent_signals[recent_signals['signal'] != 0]
                recent_signal_quality = signal_rows['fwd_ret_12'].mean() if len(signal_rows) >= 5 else np.nan

                trades.append({
                    'month': month_name,
                    'direction': position['direction'],
                    'pnl_pct': pnl_pct,
                    'pnl_dollar': pnl_dollar,
                    'exit': exit_type,
                    'entry_rsi': position['entry_rsi'],
                    'entry_atr': position['entry_atr'],
                    'entry_atr_pct': position['entry_atr'] / position['entry'] * 100,
                    'entry_move_size': position['entry_move_size'],
                    'signal_quality': recent_signal_quality,
                    'consecutive_losses': position['consecutive_losses'],
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
print('PRECISE SURGICAL FILTER: Remove ONLY worst 10-20 losers, keep ALL winners')
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

losers = df_all[df_all['pnl_dollar'] < 0].copy()
winners = df_all[df_all['pnl_dollar'] > 0].copy()

losers_sorted = losers.sort_values('pnl_dollar')
worst_20_losers = losers_sorted.head(20)

print(f"\nBaseline: {len(df_all)} trades, {len(winners)} winners, {len(losers)} losers")
print(f"Worst 20 losers: ${worst_20_losers['pnl_dollar'].sum():.2f} ({worst_20_losers['pnl_dollar'].sum()/losers['pnl_dollar'].sum()*100:.1f}% of losses)")

# Analyze worst losers more precisely
print('\n' + '=' * 140)
print('WORST 20 LOSERS - DETAILED CHARACTERISTICS')
print('=' * 140)
print(f"\n{'Metric':<25} {'Min':<10} {'Max':<10} {'Mean':<10} {'Median':<10}")
print('-' * 140)

metrics = [
    ('entry_rsi', 'Entry RSI'),
    ('entry_atr_pct', 'Entry ATR %'),
    ('entry_move_size', 'Move Size %'),
    ('signal_quality', 'Signal Quality'),
    ('consecutive_losses', 'Consec Losses'),
]

for col, label in metrics:
    print(f"{label:<25} {worst_20_losers[col].min():>9.2f} {worst_20_losers[col].max():>9.2f} "
          f"{worst_20_losers[col].mean():>9.2f} {worst_20_losers[col].median():>9.2f}")

# Direction breakdown
short_count = (worst_20_losers['direction'] == 'SHORT').sum()
print(f"\nDirection: {short_count}/20 SHORT ({short_count/20*100:.0f}%), {20-short_count}/20 LONG ({(20-short_count)/20*100:.0f}%)")

# More PRECISE filters - targeting extreme values only
filters = [
    # ULTRA CONSERVATIVE - target extremes only
    ('SHORT + ATR < 0.7% + Move < 0.9%',
     lambda t: (t['direction'] == 'SHORT') & (t['entry_atr_pct'] < 0.7) & (t['entry_move_size'] < 0.9)),

    ('SHORT + ATR < 0.75% + Move < 1.0%',
     lambda t: (t['direction'] == 'SHORT') & (t['entry_atr_pct'] < 0.75) & (t['entry_move_size'] < 1.0)),

    ('SHORT + ATR < 0.8% + Move < 1.1%',
     lambda t: (t['direction'] == 'SHORT') & (t['entry_atr_pct'] < 0.8) & (t['entry_move_size'] < 1.1)),

    # EXTREMELY LOW ATR ONLY
    ('SHORT + ATR < 0.65%',
     lambda t: (t['direction'] == 'SHORT') & (t['entry_atr_pct'] < 0.65)),

    ('SHORT + ATR < 0.7%',
     lambda t: (t['direction'] == 'SHORT') & (t['entry_atr_pct'] < 0.7)),

    # EXTREMELY LOW MOVE SIZE ONLY
    ('SHORT + Move < 0.8%',
     lambda t: (t['direction'] == 'SHORT') & (t['entry_move_size'] < 0.8)),

    ('SHORT + Move < 0.9%',
     lambda t: (t['direction'] == 'SHORT') & (t['entry_move_size'] < 0.9)),

    # TRIPLE CONDITION - very specific
    ('SHORT + ATR < 0.8% + Move < 1.0% + ConsecLoss >= 2',
     lambda t: (t['direction'] == 'SHORT') & (t['entry_atr_pct'] < 0.8) & (t['entry_move_size'] < 1.0) & (t['consecutive_losses'] >= 2)),

    # BAD SIGNAL QUALITY COMBOS
    ('SHORT + SigQual < -0.3% + Move < 1.2%',
     lambda t: (t['direction'] == 'SHORT') & (t['signal_quality'] < -0.3) & (t['entry_move_size'] < 1.2)),

    ('SHORT + SigQual < -0.2% + ATR < 0.9%',
     lambda t: (t['direction'] == 'SHORT') & (t['signal_quality'] < -0.2) & (t['entry_atr_pct'] < 0.9)),
]

print('\n' + '=' * 140)
print('PRECISE FILTER TEST RESULTS')
print('=' * 140)
print(f"\n{'Filter':<60} {'Worst':<8} {'Winners':<10} {'Losers':<10} {'Total':<8} {'Score':<8}\"")
print('-' * 140)

best_filters = []

for filter_name, filter_func in filters:
    # Apply filter - KEEP trades that DON'T match (i.e., filter OUT matches)
    try:
        filtered_df = df_all[~filter_func(df_all)]
        filtered_worst = worst_20_losers[~filter_func(worst_20_losers)]
        filtered_winners = winners[~filter_func(winners)]
        filtered_losers = losers[~filter_func(losers)]

        worst_removed = len(worst_20_losers) - len(filtered_worst)
        winners_kept = len(filtered_winners)
        winners_lost = len(winners) - winners_kept

        # Score: prioritize removing worst while keeping winners
        # Perfect score = remove all 20 worst, keep all 55 winners
        # NEW SCORING: heavily penalize losing winners
        score = (worst_removed / 20) * 100 - (winners_lost / len(winners)) * 100

        print(f"{filter_name:<60} {worst_removed:>2}/20   "
              f"{winners_kept:>3}/{len(winners):<3} {len(filtered_losers):>3}/{len(losers):<3} "
              f"{len(filtered_df):>3}/151  {score:>7.1f}")

        best_filters.append({
            'name': filter_name,
            'worst_removed': worst_removed,
            'winners_kept': winners_kept,
            'winners_lost': winners_lost,
            'total_trades': len(filtered_df),
            'score': score,
            'func': filter_func
        })
    except Exception as e:
        print(f"{filter_name:<60} ERROR: {e}")

# Show best filter details
best_filters.sort(key=lambda x: x['score'], reverse=True)
best = best_filters[0]

print('\n' + '=' * 140)
print(f'BEST FILTER: {best["name"]}')
print('=' * 140)

filtered_df = df_all[~best['func'](df_all)]
kept_trades = filtered_df.copy()

print(f"\nRemoves: {best['worst_removed']}/20 worst losers ({best['worst_removed']/20*100:.0f}%)")
print(f"Keeps: {best['winners_kept']}/{len(winners)} winners ({best['winners_kept']/len(winners)*100:.1f}%)")
print(f"Loses: {best['winners_lost']} winners ({best['winners_lost']/len(winners)*100:.1f}%)")
print(f"Total trades: {best['total_trades']}/151 ({best['total_trades']/151*100:.1f}%)")
print(f"Estimated return: ${kept_trades['pnl_dollar'].sum():.2f} ({(kept_trades['pnl_dollar'].sum()/100)*100:+.1f}%)")

print('\n' + '=' * 140)
print('TOP 5 FILTERS (Ranked by Score)')
print('=' * 140)

for i, f in enumerate(best_filters[:5], 1):
    print(f"\n{i}. {f['name']}")
    print(f"   Removes {f['worst_removed']}/20 worst ({f['worst_removed']/20*100:.0f}%) | "
          f"Keeps {f['winners_kept']}/{len(winners)} winners ({f['winners_kept']/len(winners)*100:.1f}%) | "
          f"Loses {f['winners_lost']} winners | Score: {f['score']:.1f}")

print('\n' + '=' * 140)
