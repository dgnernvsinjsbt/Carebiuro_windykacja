#!/usr/bin/env python3
"""
BB3 Final Optimized Strategy - Best parameters for LONG and SHORT
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

# 1H trend filter
df_1h = df.set_index('timestamp').resample('1h').agg({
    'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'
}).dropna()
df_1h['ema_50_1h'] = df_1h['close'].ewm(span=50, adjust=False).mean()
df_1h['trend_1h'] = np.where(df_1h['close'] > df_1h['ema_50_1h'], 'BULL', 'BEAR')

df['timestamp_1h'] = df['timestamp'].dt.floor('1h')
df = df.merge(df_1h[['trend_1h']], left_on='timestamp_1h', right_index=True, how='left')

df = df.dropna().reset_index(drop=True)
df['long_signal'] = df['close'] < df['bb_lower_3']
df['short_signal'] = df['close'] > df['bb_upper_3']

MAKER_FEE = 0.0002
TAKER_FEE = 0.0005
LIMIT_OFFSET = 0.00035
STARTING_BALANCE = 10000

def run_strategy(df, long_params=None, short_params=None, name=""):
    """
    Run combined strategy with separate params for LONG and SHORT
    params = {'atr_sl': x, 'atr_tp': y, 'sizing': 'method'}
    """
    trades = []
    in_position = False
    position_type = None

    for i in range(len(df)):
        row = df.iloc[i]
        trend = row['trend_1h']

        if not in_position:
            # LONG in BEAR
            if long_params and row['long_signal'] and trend == 'BEAR':
                in_position = True
                position_type = 'LONG'
                entry_price = row['close']
                entry_time = row['timestamp']
                atr = row['atr']
                stop_loss = entry_price - (atr * long_params['atr_sl'])
                take_profit = entry_price + (atr * long_params['atr_tp'])
                params = long_params

            # SHORT in BEAR
            elif short_params and row['short_signal'] and trend == 'BEAR':
                in_position = True
                position_type = 'SHORT'
                entry_price = row['close']
                entry_time = row['timestamp']
                atr = row['atr']
                stop_loss = entry_price + (atr * short_params['atr_sl'])
                take_profit = entry_price - (atr * short_params['atr_tp'])
                params = short_params

        elif in_position:
            high, low = row['high'], row['low']

            if position_type == 'LONG':
                if low <= stop_loss:
                    trades.append({'entry_time': entry_time, 'exit_time': row['timestamp'],
                        'type': 'LONG', 'entry': entry_price, 'stop': stop_loss,
                        'target': take_profit, 'result': 'STOP', 'params': params})
                    in_position = False
                elif high >= take_profit:
                    trades.append({'entry_time': entry_time, 'exit_time': row['timestamp'],
                        'type': 'LONG', 'entry': entry_price, 'stop': stop_loss,
                        'target': take_profit, 'result': 'TP', 'params': params})
                    in_position = False
            else:
                if high >= stop_loss:
                    trades.append({'entry_time': entry_time, 'exit_time': row['timestamp'],
                        'type': 'SHORT', 'entry': entry_price, 'stop': stop_loss,
                        'target': take_profit, 'result': 'STOP', 'params': params})
                    in_position = False
                elif low <= take_profit:
                    trades.append({'entry_time': entry_time, 'exit_time': row['timestamp'],
                        'type': 'SHORT', 'entry': entry_price, 'stop': stop_loss,
                        'target': take_profit, 'result': 'TP', 'params': params})
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

    # Simulate with position sizing
    balance = STARTING_BALANCE
    results = []
    streak = 0

    for _, row in trades_df.iterrows():
        signal = row['entry']
        sizing = row['params'].get('sizing', 'fixed')

        # Position sizing
        if sizing == 'fixed':
            size = 1.0
        elif sizing == 'streak_reduce':
            if streak <= -2:
                size = 0.5
            elif streak >= 2:
                size = 1.5
            else:
                size = 1.0
        else:
            size = 1.0

        # Check limit fill
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
            pnl = balance * size * (net / 100)
            balance += pnl
            win = gross > 0

            if win:
                streak = max(1, streak + 1)
            else:
                streak = min(-1, streak - 1)

            results.append({
                'type': row['type'], 'filled': True, 'result': row['result'],
                'gross': gross, 'net': net, 'size': size, 'pnl': pnl,
                'balance': balance, 'win': win
            })
        else:
            results.append({
                'type': row['type'], 'filled': False, 'result': 'SKIP',
                'gross': 0, 'net': 0, 'size': 0, 'pnl': 0,
                'balance': balance, 'win': False
            })

    res_df = pd.DataFrame(results)
    filled = res_df[res_df['filled']]

    if len(filled) == 0:
        return None

    # Calculate metrics
    bal = np.array([STARTING_BALANCE] + list(res_df['balance']))
    peak = np.maximum.accumulate(bal)
    dd = (bal - peak) / peak * 100

    longs = filled[filled['type'] == 'LONG']
    shorts = filled[filled['type'] == 'SHORT']

    profit = balance - STARTING_BALANCE
    max_dd = abs(dd.min())
    rr_ratio = profit / (max_dd * 100) if max_dd > 0 else 0  # profit per 1% DD

    return {
        'name': name,
        'trades': len(filled),
        'longs': len(longs),
        'shorts': len(shorts),
        'wins': int(filled['win'].sum()),
        'losses': int(len(filled) - filled['win'].sum()),
        'win_rate': filled['win'].sum() / len(filled) * 100,
        'net_pct': filled['net'].sum(),
        'max_dd': dd.min(),
        'profit': profit,
        'rr_ratio': rr_ratio,
        'profit_per_trade': profit / len(filled),
        'trades_df': trades_df,
        'results_df': res_df
    }

print("\n" + "=" * 120)
print("BB3 FINAL OPTIMIZED STRATEGIES - COMPARISON")
print("=" * 120)

strategies = []

# 1. Original LONG only (2/4 ATR)
r = run_strategy(df,
    long_params={'atr_sl': 2, 'atr_tp': 4, 'sizing': 'fixed'},
    short_params=None,
    name="1. LONG baseline (2/4)")
if r: strategies.append(r)

# 2. LONG optimized (3/6 ATR)
r = run_strategy(df,
    long_params={'atr_sl': 3, 'atr_tp': 6, 'sizing': 'fixed'},
    short_params=None,
    name="2. LONG optimized (3/6)")
if r: strategies.append(r)

# 3. SHORT baseline (2/4 ATR)
r = run_strategy(df,
    long_params=None,
    short_params={'atr_sl': 2, 'atr_tp': 4, 'sizing': 'fixed'},
    name="3. SHORT baseline (2/4)")
if r: strategies.append(r)

# 4. SHORT with streak sizing
r = run_strategy(df,
    long_params=None,
    short_params={'atr_sl': 2, 'atr_tp': 4, 'sizing': 'streak_reduce'},
    name="4. SHORT + streak sizing")
if r: strategies.append(r)

# 5. LONG + SHORT combined baseline
r = run_strategy(df,
    long_params={'atr_sl': 2, 'atr_tp': 4, 'sizing': 'fixed'},
    short_params={'atr_sl': 2, 'atr_tp': 4, 'sizing': 'fixed'},
    name="5. L+S combined baseline")
if r: strategies.append(r)

# 6. LONG (3/6) + SHORT (2/4 streak) - BEST COMBO
r = run_strategy(df,
    long_params={'atr_sl': 3, 'atr_tp': 6, 'sizing': 'fixed'},
    short_params={'atr_sl': 2, 'atr_tp': 4, 'sizing': 'streak_reduce'},
    name="6. BEST: L(3/6) + S(streak)")
if r: strategies.append(r)

# 7. Both with streak sizing
r = run_strategy(df,
    long_params={'atr_sl': 3, 'atr_tp': 6, 'sizing': 'streak_reduce'},
    short_params={'atr_sl': 2, 'atr_tp': 4, 'sizing': 'streak_reduce'},
    name="7. Both streak sizing")
if r: strategies.append(r)

# 8. Conservative: tighter stops
r = run_strategy(df,
    long_params={'atr_sl': 2.5, 'atr_tp': 5, 'sizing': 'fixed'},
    short_params={'atr_sl': 2, 'atr_tp': 4, 'sizing': 'streak_reduce'},
    name="8. L(2.5/5) + S(streak)")
if r: strategies.append(r)

# Print results
print(f"\n{'Strategy':<30} {'Trades':<8} {'L/S':<8} {'W/L':<10} {'Win%':<8} {'NET%':<10} {'MaxDD%':<10} {'Profit':<12} {'R:R':<8} {'$/Trade':<10}")
print("-" * 130)

for s in strategies:
    ls = f"{s['longs']}/{s['shorts']}"
    wl = f"{s['wins']}/{s['losses']}"
    print(f"{s['name']:<30} {s['trades']:<8} {ls:<8} {wl:<10} {s['win_rate']:.1f}%    {s['net_pct']:>+.2f}%   {s['max_dd']:.2f}%    ${s['profit']:>+,.0f}      {s['rr_ratio']:.2f}     ${s['profit_per_trade']:>+.1f}")

# Find best by different metrics
print("\n" + "=" * 120)
print("BEST BY METRIC:")
print("=" * 120)

best_profit = max(strategies, key=lambda x: x['profit'])
best_rr = max(strategies, key=lambda x: x['rr_ratio'])
best_wr = max(strategies, key=lambda x: x['win_rate'])
lowest_dd = max(strategies, key=lambda x: x['max_dd'])  # max because DD is negative

print(f"\n  HIGHEST PROFIT:     {best_profit['name']:<30} → ${best_profit['profit']:+,.0f}")
print(f"  BEST RISK:REWARD:   {best_rr['name']:<30} → {best_rr['rr_ratio']:.2f} (${best_rr['profit']:+,.0f} / {abs(best_rr['max_dd']):.2f}% DD)")
print(f"  HIGHEST WIN RATE:   {best_wr['name']:<30} → {best_wr['win_rate']:.1f}%")
print(f"  LOWEST DRAWDOWN:    {lowest_dd['name']:<30} → {lowest_dd['max_dd']:.2f}%")

# Final recommendation
print("\n" + "=" * 120)
print("FINAL RECOMMENDATION")
print("=" * 120)

best = best_profit  # or best_rr depending on preference
print(f"""
Strategy: {best['name']}

┌─────────────────────────────────────────────────────────────┐
│  PERFORMANCE METRICS                                        │
├─────────────────────────────────────────────────────────────┤
│  Total Trades:      {best['trades']:<10} ({best['longs']} LONG / {best['shorts']} SHORT)       │
│  Win Rate:          {best['win_rate']:.1f}%        ({best['wins']} wins / {best['losses']} losses)        │
│  Net Return:        {best['net_pct']:+.2f}%                                       │
│  Max Drawdown:      {best['max_dd']:.2f}%                                       │
│  Profit:            ${best['profit']:+,.0f}                                        │
│  Risk:Reward:       {best['rr_ratio']:.2f}x       (${best['profit']:+,.0f} / ${abs(best['max_dd'])*100:.0f} risk)       │
│  Profit/Trade:      ${best['profit_per_trade']:+.2f}                                      │
└─────────────────────────────────────────────────────────────┘

TRADING RULES:
  • Filter: Only trade when 1H close < 1H EMA50 (BEAR trend)
  • LONG:  Entry at -3 STD BB, SL = 3x ATR, TP = 6x ATR
  • SHORT: Entry at +3 STD BB, SL = 2x ATR, TP = 4x ATR + streak sizing
  • Limit orders: 0.035% below signal (LONG) / above signal (SHORT)
  • Fees: 0.02% maker + 0.05% taker = 0.07% round-trip
""")

# Save best strategy trades
print("Saving best strategy trades to CSV...")
trades_df = best['trades_df']
res_df = best['results_df']

output = []
balance = STARTING_BALANCE
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
        'size': r['size'] if r['filled'] else 0,
        'gross_pnl_pct': r['gross'],
        'net_pnl_pct': r['net'],
        'pnl_dollar': r['pnl'],
        'winner': 'WIN' if r['win'] else ('LOSS' if r['filled'] else 'SKIP'),
        'running_balance': r['balance']
    })

pd.DataFrame(output).to_csv('/workspaces/Carebiuro_windykacja/trading/results/bb3_final_optimized.csv', index=False)
print("Saved: results/bb3_final_optimized.csv")
print("=" * 120)
