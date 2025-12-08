#!/usr/bin/env python3
"""
BB3 Combined Strategy - LONG + SHORT both filtered to BEAR trend only
Based on findings:
- LONG in BEAR: +6.57% ($666) - counter-trend bounce from -3 STD
- SHORT in BEAR: +2.15% ($213) - with-trend rejection from +3 STD
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

# 1H trend filter (best performing)
df_1h = df.set_index('timestamp').resample('1h').agg({
    'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'
}).dropna()
df_1h['ema_50_1h'] = df_1h['close'].ewm(span=50, adjust=False).mean()
df_1h['trend_1h'] = np.where(df_1h['close'] > df_1h['ema_50_1h'], 'BULL', 'BEAR')

df['timestamp_1h'] = df['timestamp'].dt.floor('1h')
df = df.merge(df_1h[['trend_1h']], left_on='timestamp_1h', right_index=True, how='left')

df = df.dropna().reset_index(drop=True)

# Signals
df['long_signal'] = df['close'] < df['bb_lower_3']
df['short_signal'] = df['close'] > df['bb_upper_3']

# FEES
MAKER_FEE = 0.0002   # 0.02%
TAKER_FEE = 0.0005   # 0.05%
LIMIT_OFFSET = 0.00035
STARTING_BALANCE = 10000

def run_combined_backtest(df, name="", long_filter='BEAR', short_filter='BEAR'):
    """Run combined LONG+SHORT backtest"""
    trades = []
    in_position = False
    position_type = None

    for i in range(len(df)):
        row = df.iloc[i]
        trend = row['trend_1h']

        if not in_position:
            # LONG signal in specified trend
            if row['long_signal'] and trend == long_filter:
                in_position = True
                position_type = 'LONG'
                entry_price = row['close']
                entry_time = row['timestamp']
                atr = row['atr']
                stop_loss = entry_price - (atr * 2)
                take_profit = entry_price + (atr * 4)

            # SHORT signal in specified trend
            elif row['short_signal'] and trend == short_filter:
                in_position = True
                position_type = 'SHORT'
                entry_price = row['close']
                entry_time = row['timestamp']
                atr = row['atr']
                stop_loss = entry_price + (atr * 2)
                take_profit = entry_price - (atr * 4)
        else:
            high, low = row['high'], row['low']

            if position_type == 'LONG':
                if low <= stop_loss:
                    trades.append({
                        'entry_time': entry_time, 'exit_time': row['timestamp'],
                        'type': 'LONG', 'entry': entry_price,
                        'stop': stop_loss, 'target': take_profit, 'result': 'STOP'
                    })
                    in_position = False
                elif high >= take_profit:
                    trades.append({
                        'entry_time': entry_time, 'exit_time': row['timestamp'],
                        'type': 'LONG', 'entry': entry_price,
                        'stop': stop_loss, 'target': take_profit, 'result': 'TP'
                    })
                    in_position = False

            elif position_type == 'SHORT':
                if high >= stop_loss:
                    trades.append({
                        'entry_time': entry_time, 'exit_time': row['timestamp'],
                        'type': 'SHORT', 'entry': entry_price,
                        'stop': stop_loss, 'target': take_profit, 'result': 'STOP'
                    })
                    in_position = False
                elif low <= take_profit:
                    trades.append({
                        'entry_time': entry_time, 'exit_time': row['timestamp'],
                        'type': 'SHORT', 'entry': entry_price,
                        'stop': stop_loss, 'target': take_profit, 'result': 'TP'
                    })
                    in_position = False

    if not trades:
        return None

    trades_df = pd.DataFrame(trades)
    eth_idx = df.set_index('timestamp')

    # Get price extremes during trade
    def get_extremes(row):
        try:
            mask = (eth_idx.index >= row['entry_time']) & (eth_idx.index <= row['exit_time'])
            d = eth_idx.loc[mask]
            return pd.Series({'max_p': d['high'].max(), 'min_p': d['low'].min()})
        except:
            return pd.Series({'max_p': row['entry'], 'min_p': row['entry']})

    ext = trades_df.apply(get_extremes, axis=1)
    trades_df['max_price'] = ext['max_p']
    trades_df['min_price'] = ext['min_p']

    # Simulate with limit orders
    balance = STARTING_BALANCE
    results = []

    for _, row in trades_df.iterrows():
        signal = row['entry']

        if row['type'] == 'LONG':
            limit_price = signal * (1 - LIMIT_OFFSET)  # BELOW for longs
            filled = row['min_price'] <= limit_price
            if filled:
                entry = limit_price
                exit_price = row['target'] if row['result'] == 'TP' else row['stop']
                gross = (exit_price - entry) / entry * 100
        else:  # SHORT
            limit_price = signal * (1 + LIMIT_OFFSET)  # ABOVE for shorts
            filled = row['max_price'] >= limit_price
            if filled:
                entry = limit_price
                exit_price = row['target'] if row['result'] == 'TP' else row['stop']
                gross = (entry - exit_price) / entry * 100

        if filled:
            fee = (MAKER_FEE + TAKER_FEE) * 100
            net = gross - fee
            pnl = balance * (net / 100)
            balance += pnl
            results.append({
                'type': row['type'], 'filled': True, 'result': row['result'],
                'gross': gross, 'net': net, 'balance': balance, 'win': gross > 0
            })
        else:
            results.append({
                'type': row['type'], 'filled': False, 'result': 'SKIP',
                'gross': 0, 'net': 0, 'balance': balance, 'win': False
            })

    res_df = pd.DataFrame(results)
    filled = res_df[res_df['filled']]

    if len(filled) == 0:
        return None

    # Max drawdown
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
        'win_rate': filled['win'].sum() / len(filled) * 100,
        'net': filled['net'].sum(),
        'max_dd': dd.min(),
        'profit': balance - STARTING_BALANCE,
        'trades_df': trades_df,
        'results_df': res_df
    }

print("\n" + "=" * 110)
print("BB3 COMBINED STRATEGY - COMPARING CONFIGURATIONS")
print("=" * 110)

results = []

# Individual baselines
r = run_combined_backtest(df, name="LONG only (no filter)", long_filter='BEAR', short_filter='NONE')
# Hack: run with both filters as the trend they want
# Actually let me do this properly

# Re-run baselines separately
def run_single_direction(df, direction, trend_filter=None, name=""):
    trades = []
    in_position = False

    for i in range(len(df)):
        row = df.iloc[i]
        trend = row['trend_1h'] if trend_filter else None

        if not in_position:
            take_trade = False
            if direction == 'LONG' and row['long_signal']:
                if trend_filter is None or trend == trend_filter:
                    take_trade = True
                    position_type = 'LONG'
            elif direction == 'SHORT' and row['short_signal']:
                if trend_filter is None or trend == trend_filter:
                    take_trade = True
                    position_type = 'SHORT'

            if take_trade:
                in_position = True
                entry_price = row['close']
                entry_time = row['timestamp']
                atr = row['atr']
                if position_type == 'LONG':
                    stop_loss = entry_price - (atr * 2)
                    take_profit = entry_price + (atr * 4)
                else:
                    stop_loss = entry_price + (atr * 2)
                    take_profit = entry_price - (atr * 4)
        else:
            high, low = row['high'], row['low']

            if position_type == 'LONG':
                if low <= stop_loss:
                    trades.append({'entry_time': entry_time, 'exit_time': row['timestamp'],
                        'type': 'LONG', 'entry': entry_price, 'stop': stop_loss, 'target': take_profit, 'result': 'STOP'})
                    in_position = False
                elif high >= take_profit:
                    trades.append({'entry_time': entry_time, 'exit_time': row['timestamp'],
                        'type': 'LONG', 'entry': entry_price, 'stop': stop_loss, 'target': take_profit, 'result': 'TP'})
                    in_position = False
            else:
                if high >= stop_loss:
                    trades.append({'entry_time': entry_time, 'exit_time': row['timestamp'],
                        'type': 'SHORT', 'entry': entry_price, 'stop': stop_loss, 'target': take_profit, 'result': 'STOP'})
                    in_position = False
                elif low <= take_profit:
                    trades.append({'entry_time': entry_time, 'exit_time': row['timestamp'],
                        'type': 'SHORT', 'entry': entry_price, 'stop': stop_loss, 'target': take_profit, 'result': 'TP'})
                    in_position = False

    if not trades:
        return None

    trades_df = pd.DataFrame(trades)
    eth_idx = df.set_index('timestamp')

    def get_extremes(row):
        try:
            mask = (eth_idx.index >= row['entry_time']) & (eth_idx.index <= row['exit_time'])
            d = eth_idx.loc[mask]
            return pd.Series({'max_p': d['high'].max(), 'min_p': d['low'].min()})
        except:
            return pd.Series({'max_p': row['entry'], 'min_p': row['entry']})

    ext = trades_df.apply(get_extremes, axis=1)
    trades_df['max_price'] = ext['max_p']
    trades_df['min_price'] = ext['min_p']

    balance = STARTING_BALANCE
    results_list = []

    for _, row in trades_df.iterrows():
        signal = row['entry']

        if row['type'] == 'LONG':
            limit_price = signal * (1 - LIMIT_OFFSET)
            filled = row['min_price'] <= limit_price
            if filled:
                entry = limit_price
                exit_price = row['target'] if row['result'] == 'TP' else row['stop']
                gross = (exit_price - entry) / entry * 100
        else:
            limit_price = signal * (1 + LIMIT_OFFSET)
            filled = row['max_price'] >= limit_price
            if filled:
                entry = limit_price
                exit_price = row['target'] if row['result'] == 'TP' else row['stop']
                gross = (entry - exit_price) / entry * 100

        if filled:
            fee = (MAKER_FEE + TAKER_FEE) * 100
            net = gross - fee
            pnl = balance * (net / 100)
            balance += pnl
            results_list.append({'type': row['type'], 'filled': True, 'result': row['result'],
                'gross': gross, 'net': net, 'balance': balance, 'win': gross > 0})
        else:
            results_list.append({'type': row['type'], 'filled': False, 'result': 'SKIP',
                'gross': 0, 'net': 0, 'balance': balance, 'win': False})

    res_df = pd.DataFrame(results_list)
    filled = res_df[res_df['filled']]
    if len(filled) == 0:
        return None

    bal = np.array([STARTING_BALANCE] + list(res_df['balance']))
    peak = np.maximum.accumulate(bal)
    dd = (bal - peak) / peak * 100

    longs = filled[filled['type'] == 'LONG']
    shorts = filled[filled['type'] == 'SHORT']

    return {
        'name': name, 'filled': len(filled),
        'longs': len(longs), 'shorts': len(shorts),
        'long_wins': int(longs['win'].sum()) if len(longs) > 0 else 0,
        'short_wins': int(shorts['win'].sum()) if len(shorts) > 0 else 0,
        'wins': int(filled['win'].sum()),
        'losses': int(len(filled) - filled['win'].sum()),
        'win_rate': filled['win'].sum() / len(filled) * 100,
        'net': filled['net'].sum(),
        'max_dd': dd.min(),
        'profit': balance - STARTING_BALANCE,
        'trades_df': trades_df,
        'results_df': res_df
    }

results = []

# Baselines
r = run_single_direction(df, 'LONG', trend_filter=None, name="LONG only (no filter)")
if r: results.append(r)

r = run_single_direction(df, 'SHORT', trend_filter=None, name="SHORT only (no filter)")
if r: results.append(r)

# Best individual filtered
r = run_single_direction(df, 'LONG', trend_filter='BEAR', name="LONG in BEAR only")
if r: results.append(r)

r = run_single_direction(df, 'SHORT', trend_filter='BEAR', name="SHORT in BEAR only")
if r: results.append(r)

# Combined: BOTH in BEAR
r = run_combined_backtest(df, name="LONG+SHORT both in BEAR", long_filter='BEAR', short_filter='BEAR')
if r: results.append(r)

# Also test: LONG in BEAR + SHORT in BULL (opposite trends)
# Need to modify function for this
def run_combined_different_filters(df, name=""):
    trades = []
    in_position = False
    position_type = None

    for i in range(len(df)):
        row = df.iloc[i]
        trend = row['trend_1h']

        if not in_position:
            # LONG in BEAR
            if row['long_signal'] and trend == 'BEAR':
                in_position = True
                position_type = 'LONG'
                entry_price = row['close']
                entry_time = row['timestamp']
                atr = row['atr']
                stop_loss = entry_price - (atr * 2)
                take_profit = entry_price + (atr * 4)

            # SHORT in BULL (counter-trend for shorts? let's test)
            elif row['short_signal'] and trend == 'BULL':
                in_position = True
                position_type = 'SHORT'
                entry_price = row['close']
                entry_time = row['timestamp']
                atr = row['atr']
                stop_loss = entry_price + (atr * 2)
                take_profit = entry_price - (atr * 4)
        else:
            high, low = row['high'], row['low']

            if position_type == 'LONG':
                if low <= stop_loss:
                    trades.append({'entry_time': entry_time, 'exit_time': row['timestamp'],
                        'type': 'LONG', 'entry': entry_price, 'stop': stop_loss, 'target': take_profit, 'result': 'STOP'})
                    in_position = False
                elif high >= take_profit:
                    trades.append({'entry_time': entry_time, 'exit_time': row['timestamp'],
                        'type': 'LONG', 'entry': entry_price, 'stop': stop_loss, 'target': take_profit, 'result': 'TP'})
                    in_position = False

            elif position_type == 'SHORT':
                if high >= stop_loss:
                    trades.append({'entry_time': entry_time, 'exit_time': row['timestamp'],
                        'type': 'SHORT', 'entry': entry_price, 'stop': stop_loss, 'target': take_profit, 'result': 'STOP'})
                    in_position = False
                elif low <= take_profit:
                    trades.append({'entry_time': entry_time, 'exit_time': row['timestamp'],
                        'type': 'SHORT', 'entry': entry_price, 'stop': stop_loss, 'target': take_profit, 'result': 'TP'})
                    in_position = False

    if not trades:
        return None

    # Same processing as before...
    trades_df = pd.DataFrame(trades)
    eth_idx = df.set_index('timestamp')

    def get_extremes(row):
        try:
            mask = (eth_idx.index >= row['entry_time']) & (eth_idx.index <= row['exit_time'])
            d = eth_idx.loc[mask]
            return pd.Series({'max_p': d['high'].max(), 'min_p': d['low'].min()})
        except:
            return pd.Series({'max_p': row['entry'], 'min_p': row['entry']})

    ext = trades_df.apply(get_extremes, axis=1)
    trades_df['max_price'] = ext['max_p']
    trades_df['min_price'] = ext['min_p']

    balance = STARTING_BALANCE
    results_list = []

    for _, row in trades_df.iterrows():
        signal = row['entry']

        if row['type'] == 'LONG':
            limit_price = signal * (1 - LIMIT_OFFSET)
            filled = row['min_price'] <= limit_price
            if filled:
                entry = limit_price
                exit_price = row['target'] if row['result'] == 'TP' else row['stop']
                gross = (exit_price - entry) / entry * 100
        else:
            limit_price = signal * (1 + LIMIT_OFFSET)
            filled = row['max_price'] >= limit_price
            if filled:
                entry = limit_price
                exit_price = row['target'] if row['result'] == 'TP' else row['stop']
                gross = (entry - exit_price) / entry * 100

        if filled:
            fee = (MAKER_FEE + TAKER_FEE) * 100
            net = gross - fee
            pnl = balance * (net / 100)
            balance += pnl
            results_list.append({'type': row['type'], 'filled': True, 'result': row['result'],
                'gross': gross, 'net': net, 'balance': balance, 'win': gross > 0})
        else:
            results_list.append({'type': row['type'], 'filled': False, 'result': 'SKIP',
                'gross': 0, 'net': 0, 'balance': balance, 'win': False})

    res_df = pd.DataFrame(results_list)
    filled = res_df[res_df['filled']]
    if len(filled) == 0:
        return None

    bal = np.array([STARTING_BALANCE] + list(res_df['balance']))
    peak = np.maximum.accumulate(bal)
    dd = (bal - peak) / peak * 100

    longs = filled[filled['type'] == 'LONG']
    shorts = filled[filled['type'] == 'SHORT']

    return {
        'name': name, 'filled': len(filled),
        'longs': len(longs), 'shorts': len(shorts),
        'long_wins': int(longs['win'].sum()) if len(longs) > 0 else 0,
        'short_wins': int(shorts['win'].sum()) if len(shorts) > 0 else 0,
        'wins': int(filled['win'].sum()),
        'losses': int(len(filled) - filled['win'].sum()),
        'win_rate': filled['win'].sum() / len(filled) * 100,
        'net': filled['net'].sum(),
        'max_dd': dd.min(),
        'profit': balance - STARTING_BALANCE,
        'trades_df': trades_df,
        'results_df': res_df
    }

r = run_combined_different_filters(df, name="LONG(BEAR)+SHORT(BULL)")
if r: results.append(r)

# Print comparison
print(f"\n{'Strategy':<30} {'Filled':<8} {'L/S':<10} {'LW/SW':<10} {'Win%':<8} {'NET':<10} {'MaxDD':<10} {'Profit':<12}")
print("-" * 110)

for r in results:
    ls = f"{r['longs']}/{r['shorts']}"
    lw_sw = f"{r['long_wins']}/{r['short_wins']}"
    print(f"{r['name']:<30} {r['filled']:<8} {ls:<10} {lw_sw:<10} {r['win_rate']:.1f}%    {r['net']:>+.2f}%   {r['max_dd']:.2f}%    ${r['profit']:>+,.0f}")

print("\n" + "=" * 110)
best = max(results, key=lambda x: x['profit'])
print(f"BEST COMBINED STRATEGY: {best['name']}")
print(f"  Trades: {best['filled']} ({best['longs']}L / {best['shorts']}S)")
print(f"  Win rate: {best['win_rate']:.1f}% ({best['wins']}/{best['losses']})")
print(f"  Net return: {best['net']:.2f}%")
print(f"  Max DD: {best['max_dd']:.2f}%")
print(f"  Profit: ${best['profit']:+,.0f}")
print("=" * 110)

# Save best strategy trades
if best['shorts'] > 0:
    print(f"\nSaving {best['name']} trades to CSV...")
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
            'net_pnl_pct': r['net'],
            'winner': 'WIN' if r['win'] else ('LOSS' if r['filled'] else 'SKIP'),
            'running_balance': r['balance']
        })

    pd.DataFrame(output).to_csv('/workspaces/Carebiuro_windykacja/trading/results/bb3_combined_bear_strategy.csv', index=False)
    print("Saved: bb3_combined_bear_strategy.csv")
