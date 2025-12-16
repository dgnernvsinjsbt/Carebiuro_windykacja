"""
Backtest każdego miesiąca osobno używając istniejących danych
Lipiec-Grudzień 2025, 15m timeframe
"""
import pandas as pd
import numpy as np

# Load existing data
print('Loading existing 15m data...')
df_all = pd.read_csv('trading/melania_15m_jan2025.csv')
df_all['timestamp'] = pd.to_datetime(df_all['timestamp'])
df_all = df_all.sort_values('timestamp').reset_index(drop=True)

print(f'Loaded {len(df_all)} bars from {df_all["timestamp"].min()} to {df_all["timestamp"].max()}')

def backtest_month(df, sl_mult, tp_mult):
    """Clean backtest - RSI 35/65 + ret_20 > 0"""

    # Calculate indicators (Wilder's RSI)
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

    trades, equity, position = [], 100.0, None

    for i in range(300, len(df)):
        row = df.iloc[i]
        if pd.isna(row['rsi']) or pd.isna(row['atr']) or pd.isna(row['ret_20']):
            continue

        # Manage position
        if position:
            if position['direction'] == 'LONG':
                if row['low'] <= position['sl_price']:
                    pnl_pct = ((position['sl_price'] - position['entry']) / position['entry']) * 100
                    pnl = position['size'] * (pnl_pct / 100) - position['size'] * 0.001
                    equity += pnl
                    trades.append({'pnl_pct': pnl_pct, 'exit': 'SL', 'direction': 'LONG'})
                    position = None
                    continue
                elif row['high'] >= position['tp_price']:
                    pnl_pct = ((position['tp_price'] - position['entry']) / position['entry']) * 100
                    pnl = position['size'] * (pnl_pct / 100) - position['size'] * 0.001
                    equity += pnl
                    trades.append({'pnl_pct': pnl_pct, 'exit': 'TP', 'direction': 'LONG'})
                    position = None
                    continue
            else:  # SHORT
                if row['high'] >= position['sl_price']:
                    pnl_pct = ((position['entry'] - position['sl_price']) / position['entry']) * 100
                    pnl = position['size'] * (pnl_pct / 100) - position['size'] * 0.001
                    equity += pnl
                    trades.append({'pnl_pct': pnl_pct, 'exit': 'SL', 'direction': 'SHORT'})
                    position = None
                    continue
                elif row['low'] <= position['tp_price']:
                    pnl_pct = ((position['entry'] - position['tp_price']) / position['entry']) * 100
                    pnl = position['size'] * (pnl_pct / 100) - position['size'] * 0.001
                    equity += pnl
                    trades.append({'pnl_pct': pnl_pct, 'exit': 'TP', 'direction': 'SHORT'})
                    position = None
                    continue

        # New signals
        if not position and i > 0:
            prev_row = df.iloc[i-1]
            if row['ret_20'] <= 0:
                continue
            if not pd.isna(prev_row['rsi']):
                # LONG: RSI crosses above 35
                if prev_row['rsi'] < 35 and row['rsi'] >= 35:
                    entry = row['close']
                    sl = entry - (row['atr'] * sl_mult)
                    tp = entry + (row['atr'] * tp_mult)
                    sl_dist = abs((entry - sl) / entry) * 100
                    size = (equity * 0.12) / (sl_dist / 100)
                    position = {'direction': 'LONG', 'entry': entry, 'sl_price': sl, 'tp_price': tp, 'size': size}
                # SHORT: RSI crosses below 65
                elif prev_row['rsi'] > 65 and row['rsi'] <= 65:
                    entry = row['close']
                    sl = entry + (row['atr'] * sl_mult)
                    tp = entry - (row['atr'] * tp_mult)
                    sl_dist = abs((sl - entry) / entry) * 100
                    size = (equity * 0.12) / (sl_dist / 100)
                    position = {'direction': 'SHORT', 'entry': entry, 'sl_price': sl, 'tp_price': tp, 'size': size}

    if not trades:
        return None

    df_t = pd.DataFrame(trades)
    ret = ((equity - 100) / 100) * 100

    # Calculate equity curve
    eq = [100.0]
    cum_eq = 100.0
    for pnl in df_t['pnl_pct']:
        cum_eq += (cum_eq * 0.12) * (pnl / 100) - (cum_eq * 0.12) * 0.001
        eq.append(cum_eq)

    eq_s = pd.Series(eq)
    max_dd = ((eq_s - eq_s.expanding().max()) / eq_s.expanding().max() * 100).min()
    win_rate = (df_t['pnl_pct'] > 0).sum() / len(df_t) * 100
    tp_rate = (df_t['exit'] == 'TP').sum() / len(df_t) * 100

    longs = df_t[df_t['direction'] == 'LONG']
    shorts = df_t[df_t['direction'] == 'SHORT']

    return {
        'trades': len(df_t),
        'win_rate': win_rate,
        'tp_rate': tp_rate,
        'return': ret,
        'max_dd': max_dd,
        'return_dd': ret / abs(max_dd) if max_dd != 0 else 0,
        'longs': len(longs),
        'shorts': len(shorts),
    }

print('\n' + '=' * 120)
print('FRESH BACKTEST - KAŻDY MIESIĄC OSOBNO (LIPIEC-GRUDZIEŃ 2025)')
print('=' * 120)

months = [
    (7, 'Jul 2025'),
    (8, 'Aug 2025'),
    (9, 'Sep 2025'),
    (10, 'Oct 2025'),
    (11, 'Nov 2025'),
    (12, 'Dec 2025'),
]

results = []

for month_num, month_name in months:
    print(f'\n{month_name}:')
    print('-' * 120)

    # Extract month data
    month_df = df_all[(df_all['timestamp'].dt.month == month_num) &
                      (df_all['timestamp'].dt.year == 2025)].copy().reset_index(drop=True)

    print(f'  Bars: {len(month_df)} ({month_df["timestamp"].min()} to {month_df["timestamp"].max()})')

    if len(month_df) < 500:
        print(f'  ⚠️  Not enough data for this month')
        continue

    # Backtest both configs
    current = backtest_month(month_df.copy(), sl_mult=2.0, tp_mult=3.0)
    wide_sl = backtest_month(month_df.copy(), sl_mult=3.0, tp_mult=1.0)

    print(f'\n  CURRENT (SL 2.0x / TP 3.0x):')
    if current:
        print(f'    {current["trades"]:3d} trades ({current["longs"]}L/{current["shorts"]}S), '
              f'{current["win_rate"]:5.1f}% win, {current["tp_rate"]:5.1f}% TP, '
              f'{current["return"]:+8.1f}% return, {current["max_dd"]:+7.2f}% DD, '
              f'{current["return_dd"]:7.2f}x R/DD')
    else:
        print(f'    No trades')

    print(f'\n  WIDE SL (SL 3.0x / TP 1.0x):')
    if wide_sl:
        print(f'    {wide_sl["trades"]:3d} trades ({wide_sl["longs"]}L/{wide_sl["shorts"]}S), '
              f'{wide_sl["win_rate"]:5.1f}% win, {wide_sl["tp_rate"]:5.1f}% TP, '
              f'{wide_sl["return"]:+8.1f}% return, {wide_sl["max_dd"]:+7.2f}% DD, '
              f'{wide_sl["return_dd"]:7.2f}x R/DD')
    else:
        print(f'    No trades')

    results.append({
        'month': month_name,
        'bars': len(month_df),
        'current_trades': current['trades'] if current else 0,
        'current_win': current['win_rate'] if current else 0,
        'current_return': current['return'] if current else 0,
        'current_dd': current['max_dd'] if current else 0,
        'current_rdd': current['return_dd'] if current else 0,
        'wide_trades': wide_sl['trades'] if wide_sl else 0,
        'wide_win': wide_sl['win_rate'] if wide_sl else 0,
        'wide_return': wide_sl['return'] if wide_sl else 0,
        'wide_dd': wide_sl['max_dd'] if wide_sl else 0,
        'wide_rdd': wide_sl['return_dd'] if wide_sl else 0,
    })

print('\n' + '=' * 120)
print('SUMMARY TABLE')
print('=' * 120)

df_res = pd.DataFrame(results)

print(f'\n{"Month":<10} {"Bars":<6} │ CURRENT (2.0/3.0)                              │ WIDE SL (3.0/1.0)')
print(f'{"":10} {"":6} │ {"Trd":<5} {"Win%":<7} {"Return":<11} {"DD%":<9} {"R/DD":<8} │ {"Trd":<5} {"Win%":<7} {"Return":<11} {"DD%":<9} {"R/DD":<8}')
print('-' * 120)

for idx, row in df_res.iterrows():
    print(f'{row["month"]:<10} {row["bars"]:<6} │ '
          f'{row["current_trades"]:<5} {row["current_win"]:<6.1f}% {row["current_return"]:<+10.1f}% '
          f'{row["current_dd"]:<+8.2f}% {row["current_rdd"]:<7.2f}x │ '
          f'{row["wide_trades"]:<5} {row["wide_win"]:<6.1f}% {row["wide_return"]:<+10.1f}% '
          f'{row["wide_dd"]:<+8.2f}% {row["wide_rdd"]:<7.2f}x')

print('\n' + '=' * 120)
print('TOTALS:')
print('=' * 120)

print(f'\nCURRENT (SL 2.0x / TP 3.0x):')
print(f'  Total trades: {df_res["current_trades"].sum()}')
print(f'  Avg win rate: {df_res["current_win"].mean():.1f}%')
print(f'  Total return: {df_res["current_return"].sum():+.1f}%')

print(f'\nWIDE SL (SL 3.0x / TP 1.0x):')
print(f'  Total trades: {df_res["wide_trades"].sum()}')
print(f'  Avg win rate: {df_res["wide_win"].mean():.1f}%')
print(f'  Total return: {df_res["wide_return"].sum():+.1f}%')

print(f'\nWINNER: {"CURRENT" if df_res["current_return"].sum() > df_res["wide_return"].sum() else "WIDE SL"} '
      f'by {abs(df_res["current_return"].sum() - df_res["wide_return"].sum()):.1f}%')

df_res.to_csv('clean_monthly_results.csv', index=False)
print(f'\n💾 Saved: clean_monthly_results.csv')
