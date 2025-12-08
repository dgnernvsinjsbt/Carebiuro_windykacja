#!/usr/bin/env python3
"""
BB3 Strategy with Trend Filter - V2
"""
import pandas as pd
import numpy as np

print("Loading data...")
df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/eth_usdt_1m_lbank.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# BB3 indicators
df['bb_mid'] = df['close'].rolling(20).mean()
df['bb_std'] = df['close'].rolling(20).std()
df['bb_upper_3'] = df['bb_mid'] + 3 * df['bb_std']
df['bb_lower_3'] = df['bb_mid'] - 3 * df['bb_std']
df['atr'] = (df['high'] - df['low']).rolling(14).mean()

# Trend filters
df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()
df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()

# 1H trend
df_1h = df.set_index('timestamp').resample('1h').agg({
    'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'
}).dropna()
df_1h['ema_50_1h'] = df_1h['close'].ewm(span=50, adjust=False).mean()
df_1h['trend_1h'] = np.where(df_1h['close'] > df_1h['ema_50_1h'], 'BULL', 'BEAR')

df['timestamp_1h'] = df['timestamp'].dt.floor('1h')
df = df.merge(df_1h[['trend_1h']], left_on='timestamp_1h', right_index=True, how='left')

df['trend_ema200'] = np.where(df['close'] > df['ema_200'], 'BULL', 'BEAR')
df['trend_ema_cross'] = np.where(df['ema_50'] > df['ema_200'], 'BULL', 'BEAR')

df = df.dropna().reset_index(drop=True)

df['long_signal'] = df['close'] < df['bb_lower_3']
df['short_signal'] = df['close'] > df['bb_upper_3']

MAKER_FEE = 0.0002
TAKER_FEE = 0.0005
LIMIT_OFFSET = 0.00035
STARTING_BALANCE = 10000

def run_backtest(df, allow_long=True, allow_short=True, trend_filter=None, name=""):
    trades = []
    in_position = False
    position_type = None

    for i in range(len(df)):
        row = df.iloc[i]
        trend = row[trend_filter] if trend_filter else None

        if not in_position:
            # LONG
            if allow_long and row['long_signal']:
                if trend_filter is None or trend == 'BULL':
                    in_position = True
                    position_type = 'LONG'
                    entry_price = row['close']
                    entry_time = row['timestamp']
                    atr = row['atr']
                    stop_loss = entry_price - (atr * 2)
                    take_profit = entry_price + (atr * 4)

            # SHORT
            if not in_position and allow_short and row['short_signal']:
                if trend_filter is None or trend == 'BEAR':
                    in_position = True
                    position_type = 'SHORT'
                    entry_price = row['close']
                    entry_time = row['timestamp']
                    atr = row['atr']
                    stop_loss = entry_price + (atr * 2)
                    take_profit = entry_price - (atr * 4)

        elif in_position:
            high, low = row['high'], row['low']

            if position_type == 'LONG':
                if low <= stop_loss:
                    trades.append({'entry_time': entry_time, 'exit_time': row['timestamp'],
                                   'type': 'LONG', 'entry': entry_price, 'stop': stop_loss,
                                   'target': take_profit, 'result': 'STOP'})
                    in_position = False
                elif high >= take_profit:
                    trades.append({'entry_time': entry_time, 'exit_time': row['timestamp'],
                                   'type': 'LONG', 'entry': entry_price, 'stop': stop_loss,
                                   'target': take_profit, 'result': 'TP'})
                    in_position = False

            elif position_type == 'SHORT':
                if high >= stop_loss:
                    trades.append({'entry_time': entry_time, 'exit_time': row['timestamp'],
                                   'type': 'SHORT', 'entry': entry_price, 'stop': stop_loss,
                                   'target': take_profit, 'result': 'STOP'})
                    in_position = False
                elif low <= take_profit:
                    trades.append({'entry_time': entry_time, 'exit_time': row['timestamp'],
                                   'type': 'SHORT', 'entry': entry_price, 'stop': stop_loss,
                                   'target': take_profit, 'result': 'TP'})
                    in_position = False

    if not trades:
        return None

    trades_df = pd.DataFrame(trades)
    eth_idx = df.set_index('timestamp')

    def get_extreme(row):
        try:
            mask = (eth_idx.index >= row['entry_time']) & (eth_idx.index <= row['exit_time'])
            d = eth_idx.loc[mask]
            return pd.Series({'max_p': d['high'].max(), 'min_p': d['low'].min()})
        except:
            return pd.Series({'max_p': row['entry'], 'min_p': row['entry']})

    ext = trades_df.apply(get_extreme, axis=1)
    trades_df['max_price'] = ext['max_p']
    trades_df['min_price'] = ext['min_p']

    balance = STARTING_BALANCE
    results = []

    for _, row in trades_df.iterrows():
        signal = row['entry']

        if row['type'] == 'LONG':
            limit = signal * (1 - LIMIT_OFFSET)
            filled = row['min_price'] <= limit
            if filled:
                entry = limit
                exit_p = row['target'] if row['result'] == 'TP' else row['stop']
                gross = (exit_p - entry) / entry * 100
        else:
            limit = signal * (1 + LIMIT_OFFSET)
            filled = row['max_price'] >= limit
            if filled:
                entry = limit
                exit_p = row['target'] if row['result'] == 'TP' else row['stop']
                gross = (entry - exit_p) / entry * 100

        if filled:
            fee = (MAKER_FEE + TAKER_FEE) * 100
            net = gross - fee
            pnl = balance * (net / 100)
            balance += pnl
            results.append({'type': row['type'], 'filled': True, 'result': row['result'],
                           'gross': gross, 'net': net, 'balance': balance, 'win': gross > 0})
        else:
            results.append({'type': row['type'], 'filled': False, 'result': 'SKIP',
                           'gross': 0, 'net': 0, 'balance': balance, 'win': False})

    res_df = pd.DataFrame(results)
    filled = res_df[res_df['filled']]

    bal = np.array([STARTING_BALANCE] + list(res_df['balance']))
    peak = np.maximum.accumulate(bal)
    dd = (bal - peak) / peak * 100

    longs = filled[filled['type'] == 'LONG']
    shorts = filled[filled['type'] == 'SHORT']

    return {
        'name': name,
        'filled': len(filled),
        'longs': len(longs),
        'shorts': len(shorts),
        'long_wins': int(longs['win'].sum()) if len(longs) > 0 else 0,
        'short_wins': int(shorts['win'].sum()) if len(shorts) > 0 else 0,
        'wins': int(filled['win'].sum()),
        'losses': int(len(filled) - filled['win'].sum()),
        'win_rate': filled['win'].sum() / len(filled) * 100 if len(filled) > 0 else 0,
        'net': filled['net'].sum(),
        'max_dd': dd.min(),
        'profit': balance - STARTING_BALANCE,
        'trades_df': trades_df,
        'results_df': res_df
    }

print("\n" + "=" * 105)
print("BB3 STRATEGY - TREND FILTER COMPARISON (all with limit orders, 0.07% RT fees)")
print("=" * 105)

results = []

# 1. Long only (baseline)
r = run_backtest(df, allow_long=True, allow_short=False, trend_filter=None, name="Long Only")
if r: results.append(r)

# 2. Short only
r = run_backtest(df, allow_long=False, allow_short=True, trend_filter=None, name="Short Only")
if r: results.append(r)

# 3. Both no filter
r = run_backtest(df, allow_long=True, allow_short=True, trend_filter=None, name="Long+Short (no filter)")
if r: results.append(r)

# 4-6. With trend filters
for filt_name, filt_col in [('EMA200', 'trend_ema200'), ('EMA Cross', 'trend_ema_cross'), ('1H Trend', 'trend_1h')]:
    r = run_backtest(df, allow_long=True, allow_short=True, trend_filter=filt_col, name=f"L+S w/ {filt_name}")
    if r: results.append(r)

# Print
print(f"\n{'Strategy':<25} {'Trades':<8} {'L/S':<10} {'L-W':<6} {'S-W':<6} {'Win%':<8} {'NET':<10} {'MaxDD':<10} {'Profit':<10}")
print("-" * 105)

for r in results:
    ls = f"{r['longs']}/{r['shorts']}"
    print(f"{r['name']:<25} {r['filled']:<8} {ls:<10} {r['long_wins']:<6} {r['short_wins']:<6} {r['win_rate']:.1f}%    {r['net']:>+.2f}%   {r['max_dd']:.2f}%    ${r['profit']:>+,.0f}")

best = max(results, key=lambda x: x['profit'])
print(f"\n{'='*105}")
print(f"BEST: {best['name']} → {best['net']:.2f}% net, ${best['profit']:+,.0f} profit, {best['max_dd']:.2f}% max DD")
print(f"{'='*105}")

# Save best CSV
print(f"\nSaving {best['name']} to CSV...")
trades_df = best['trades_df']
res_df = best['results_df']

output = []
for i in range(len(trades_df)):
    trade = trades_df.iloc[i]
    r = res_df.iloc[i]

    output.append({
        'trade_num': i + 1,
        'entry_time': trade['entry_time'],
        'exit_time': trade['exit_time'],
        'type': trade['type'],
        'signal_price': trade['entry'],
        'stop': trade['stop'],
        'target': trade['target'],
        'filled': 'YES' if r['filled'] else 'NO',
        'result': r['result'] if r['filled'] else 'SKIP',
        'gross_pnl_pct': r['gross'],
        'entry_fee_pct': MAKER_FEE * 100 if r['filled'] else 0,
        'exit_fee_pct': TAKER_FEE * 100 if r['filled'] else 0,
        'profit_after_fees_pct': r['net'],
        'winner': 'WIN' if r['win'] else ('LOSS' if r['filled'] else 'SKIP'),
        'running_balance': r['balance']
    })

pd.DataFrame(output).to_csv('/workspaces/Carebiuro_windykacja/trading/results/bb3_best_strategy.csv', index=False)
print("Saved: bb3_best_strategy.csv")
