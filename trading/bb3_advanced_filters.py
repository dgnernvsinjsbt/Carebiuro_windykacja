#!/usr/bin/env python3
"""
BB3 Advanced Filters Test
1. Session filters (Asian, EU, US)
2. Dynamic position sizing (streak-based)
3. ATR multiplier optimization
4. Volatility filter
5. Day of week filter
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

# ATR percentile for volatility filter
df['atr_pct'] = df['atr'].rolling(1440).apply(lambda x: pd.Series(x).rank(pct=True).iloc[-1], raw=False)

# 1H trend filter
df_1h = df.set_index('timestamp').resample('1h').agg({
    'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'
}).dropna()
df_1h['ema_50_1h'] = df_1h['close'].ewm(span=50, adjust=False).mean()
df_1h['trend_1h'] = np.where(df_1h['close'] > df_1h['ema_50_1h'], 'BULL', 'BEAR')

df['timestamp_1h'] = df['timestamp'].dt.floor('1h')
df = df.merge(df_1h[['trend_1h']], left_on='timestamp_1h', right_index=True, how='left')

# Session (UTC times)
df['hour'] = df['timestamp'].dt.hour
df['session'] = df['hour'].apply(lambda h:
    'ASIA' if 0 <= h < 8 else
    'EU' if 8 <= h < 14 else
    'US' if 14 <= h < 22 else 'ASIA')

# Day of week
df['dow'] = df['timestamp'].dt.dayofweek  # 0=Mon, 6=Sun

df = df.dropna().reset_index(drop=True)
df['long_signal'] = df['close'] < df['bb_lower_3']
df['short_signal'] = df['close'] > df['bb_upper_3']

# FEES
MAKER_FEE = 0.0002
TAKER_FEE = 0.0005
LIMIT_OFFSET = 0.00035
STARTING_BALANCE = 10000

def run_backtest(df, direction='LONG', trend_filter='BEAR',
                session_filter=None, dow_filter=None,
                atr_sl=2, atr_tp=4,
                vol_min=None, vol_max=None,
                sizing='fixed', base_size=1.0,
                name=""):
    """
    Advanced backtest with multiple filters

    sizing options:
    - 'fixed': always base_size
    - 'martingale': double after loss
    - 'anti_martingale': double after win
    - 'streak_reduce': reduce size after 2 losses
    - 'kelly': adjust based on recent win rate
    """
    trades = []
    in_position = False

    for i in range(len(df)):
        row = df.iloc[i]

        # Apply filters
        if trend_filter and row['trend_1h'] != trend_filter:
            continue
        if session_filter and row['session'] not in session_filter:
            continue
        if dow_filter and row['dow'] not in dow_filter:
            continue
        if vol_min and row['atr_pct'] < vol_min:
            continue
        if vol_max and row['atr_pct'] > vol_max:
            continue

        if not in_position:
            take_trade = False
            if direction == 'LONG' and row['long_signal']:
                take_trade = True
                position_type = 'LONG'
            elif direction == 'SHORT' and row['short_signal']:
                take_trade = True
                position_type = 'SHORT'

            if take_trade:
                in_position = True
                entry_price = row['close']
                entry_time = row['timestamp']
                atr = row['atr']
                entry_atr_pct = row['atr_pct']

                if position_type == 'LONG':
                    stop_loss = entry_price - (atr * atr_sl)
                    take_profit = entry_price + (atr * atr_tp)
                else:
                    stop_loss = entry_price + (atr * atr_sl)
                    take_profit = entry_price - (atr * atr_tp)

        elif in_position:
            high, low = row['high'], row['low']

            if position_type == 'LONG':
                if low <= stop_loss:
                    trades.append({
                        'entry_time': entry_time, 'exit_time': row['timestamp'],
                        'type': 'LONG', 'entry': entry_price, 'stop': stop_loss,
                        'target': take_profit, 'result': 'STOP', 'atr_pct': entry_atr_pct
                    })
                    in_position = False
                elif high >= take_profit:
                    trades.append({
                        'entry_time': entry_time, 'exit_time': row['timestamp'],
                        'type': 'LONG', 'entry': entry_price, 'stop': stop_loss,
                        'target': take_profit, 'result': 'TP', 'atr_pct': entry_atr_pct
                    })
                    in_position = False
            else:
                if high >= stop_loss:
                    trades.append({
                        'entry_time': entry_time, 'exit_time': row['timestamp'],
                        'type': 'SHORT', 'entry': entry_price, 'stop': stop_loss,
                        'target': take_profit, 'result': 'STOP', 'atr_pct': entry_atr_pct
                    })
                    in_position = False
                elif low <= take_profit:
                    trades.append({
                        'entry_time': entry_time, 'exit_time': row['timestamp'],
                        'type': 'SHORT', 'entry': entry_price, 'stop': stop_loss,
                        'target': take_profit, 'result': 'TP', 'atr_pct': entry_atr_pct
                    })
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
    streak = 0  # positive = wins, negative = losses
    recent_wins = []

    for idx, row in trades_df.iterrows():
        signal = row['entry']

        # Calculate position size
        if sizing == 'fixed':
            size = base_size
        elif sizing == 'martingale':
            size = base_size * (2 ** max(0, -streak))  # double after each loss
            size = min(size, 4.0)  # cap at 4x
        elif sizing == 'anti_martingale':
            size = base_size * (1 + 0.5 * max(0, streak))  # increase after wins
            size = min(size, 3.0)
        elif sizing == 'streak_reduce':
            if streak <= -2:
                size = base_size * 0.5  # halve after 2 losses
            elif streak >= 2:
                size = base_size * 1.5  # increase after 2 wins
            else:
                size = base_size
        elif sizing == 'kelly':
            if len(recent_wins) >= 10:
                wr = sum(recent_wins[-10:]) / 10
                # Simplified Kelly: size = win_rate - (1-win_rate)/2
                kelly = max(0.25, min(2.0, wr - (1-wr)/2))
                size = base_size * kelly
            else:
                size = base_size
        else:
            size = base_size

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
            # Apply position sizing to P/L
            pnl = balance * size * (net / 100)
            balance += pnl
            win = gross > 0

            # Update streak
            if win:
                streak = max(1, streak + 1)
            else:
                streak = min(-1, streak - 1)
            recent_wins.append(1 if win else 0)

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

    bal = np.array([STARTING_BALANCE] + list(res_df['balance']))
    peak = np.maximum.accumulate(bal)
    dd = (bal - peak) / peak * 100

    return {
        'name': name,
        'filled': len(filled),
        'wins': int(filled['win'].sum()),
        'losses': int(len(filled) - filled['win'].sum()),
        'win_rate': filled['win'].sum() / len(filled) * 100,
        'net': filled['net'].sum(),
        'max_dd': dd.min(),
        'profit': balance - STARTING_BALANCE,
        'avg_size': filled['size'].mean()
    }

# ============================================
# TEST 1: SESSION FILTERS
# ============================================
print("\n" + "=" * 100)
print("TEST 1: SESSION FILTERS (LONG in BEAR)")
print("=" * 100)

print(f"\n{'Session':<25} {'Trades':<8} {'W/L':<10} {'Win%':<8} {'NET':<10} {'MaxDD':<10} {'Profit':<10}")
print("-" * 85)

for session_name, session_list in [
    ('All Sessions', None),
    ('ASIA only (0-8 UTC)', ['ASIA']),
    ('EU only (8-14 UTC)', ['EU']),
    ('US only (14-22 UTC)', ['US']),
    ('ASIA+EU', ['ASIA', 'EU']),
    ('EU+US', ['EU', 'US']),
]:
    r = run_backtest(df, direction='LONG', trend_filter='BEAR', session_filter=session_list, name=session_name)
    if r and r['filled'] > 5:
        print(f"{r['name']:<25} {r['filled']:<8} {r['wins']}/{r['losses']:<6} {r['win_rate']:.1f}%    {r['net']:>+.2f}%   {r['max_dd']:.2f}%    ${r['profit']:>+,.0f}")

# ============================================
# TEST 2: ATR MULTIPLIER OPTIMIZATION
# ============================================
print("\n" + "=" * 100)
print("TEST 2: ATR MULTIPLIER OPTIMIZATION (LONG in BEAR)")
print("=" * 100)

print(f"\n{'SL/TP ATR':<25} {'Trades':<8} {'W/L':<10} {'Win%':<8} {'NET':<10} {'MaxDD':<10} {'Profit':<10}")
print("-" * 85)

for sl, tp in [(1.5, 3), (2, 3), (2, 4), (2, 5), (2.5, 4), (2.5, 5), (3, 6), (1.5, 4.5)]:
    r = run_backtest(df, direction='LONG', trend_filter='BEAR', atr_sl=sl, atr_tp=tp, name=f"SL {sl}x / TP {tp}x")
    if r and r['filled'] > 5:
        print(f"{r['name']:<25} {r['filled']:<8} {r['wins']}/{r['losses']:<6} {r['win_rate']:.1f}%    {r['net']:>+.2f}%   {r['max_dd']:.2f}%    ${r['profit']:>+,.0f}")

# ============================================
# TEST 3: POSITION SIZING STRATEGIES
# ============================================
print("\n" + "=" * 100)
print("TEST 3: POSITION SIZING STRATEGIES (LONG in BEAR)")
print("=" * 100)

print(f"\n{'Sizing Method':<25} {'Trades':<8} {'W/L':<10} {'Win%':<8} {'AvgSize':<8} {'MaxDD':<10} {'Profit':<10}")
print("-" * 85)

for sizing_name, sizing_method in [
    ('Fixed 1x', 'fixed'),
    ('Martingale (2x loss)', 'martingale'),
    ('Anti-Martingale (win+)', 'anti_martingale'),
    ('Streak Reduce', 'streak_reduce'),
    ('Kelly-inspired', 'kelly'),
]:
    r = run_backtest(df, direction='LONG', trend_filter='BEAR', sizing=sizing_method, name=sizing_name)
    if r:
        print(f"{r['name']:<25} {r['filled']:<8} {r['wins']}/{r['losses']:<6} {r['win_rate']:.1f}%    {r['avg_size']:.2f}x    {r['max_dd']:.2f}%    ${r['profit']:>+,.0f}")

# ============================================
# TEST 4: VOLATILITY FILTER
# ============================================
print("\n" + "=" * 100)
print("TEST 4: VOLATILITY FILTER (LONG in BEAR)")
print("=" * 100)

print(f"\n{'Volatility Range':<25} {'Trades':<8} {'W/L':<10} {'Win%':<8} {'NET':<10} {'MaxDD':<10} {'Profit':<10}")
print("-" * 85)

for vol_name, vol_min, vol_max in [
    ('All volatility', None, None),
    ('Low vol (0-33%)', None, 0.33),
    ('Mid vol (33-66%)', 0.33, 0.66),
    ('High vol (66-100%)', 0.66, None),
    ('Not extreme (10-90%)', 0.10, 0.90),
    ('Higher vol (50%+)', 0.50, None),
]:
    r = run_backtest(df, direction='LONG', trend_filter='BEAR', vol_min=vol_min, vol_max=vol_max, name=vol_name)
    if r and r['filled'] > 5:
        print(f"{r['name']:<25} {r['filled']:<8} {r['wins']}/{r['losses']:<6} {r['win_rate']:.1f}%    {r['net']:>+.2f}%   {r['max_dd']:.2f}%    ${r['profit']:>+,.0f}")

# ============================================
# TEST 5: DAY OF WEEK
# ============================================
print("\n" + "=" * 100)
print("TEST 5: DAY OF WEEK FILTER (LONG in BEAR)")
print("=" * 100)

print(f"\n{'Days':<25} {'Trades':<8} {'W/L':<10} {'Win%':<8} {'NET':<10} {'MaxDD':<10} {'Profit':<10}")
print("-" * 85)

for dow_name, dow_list in [
    ('All days', None),
    ('Weekdays (Mon-Fri)', [0,1,2,3,4]),
    ('Weekend (Sat-Sun)', [5,6]),
    ('Mon-Wed', [0,1,2]),
    ('Thu-Sat', [3,4,5]),
    ('Tue-Thu', [1,2,3]),
]:
    r = run_backtest(df, direction='LONG', trend_filter='BEAR', dow_filter=dow_list, name=dow_name)
    if r and r['filled'] > 5:
        print(f"{r['name']:<25} {r['filled']:<8} {r['wins']}/{r['losses']:<6} {r['win_rate']:.1f}%    {r['net']:>+.2f}%   {r['max_dd']:.2f}%    ${r['profit']:>+,.0f}")

# ============================================
# TEST 6: COMBINED BEST FILTERS
# ============================================
print("\n" + "=" * 100)
print("TEST 6: COMBINED OPTIMIZATIONS (LONG in BEAR)")
print("=" * 100)

print(f"\n{'Combination':<35} {'Trades':<8} {'W/L':<10} {'Win%':<8} {'MaxDD':<10} {'Profit':<12}")
print("-" * 95)

# Test combinations
combos = [
    {'name': 'Baseline (BEAR only)', 'session_filter': None, 'atr_sl': 2, 'atr_tp': 4, 'sizing': 'fixed', 'vol_min': None, 'vol_max': None},
    {'name': 'Best ATR (1.5/4.5)', 'session_filter': None, 'atr_sl': 1.5, 'atr_tp': 4.5, 'sizing': 'fixed', 'vol_min': None, 'vol_max': None},
    {'name': 'EU+US sessions', 'session_filter': ['EU', 'US'], 'atr_sl': 2, 'atr_tp': 4, 'sizing': 'fixed', 'vol_min': None, 'vol_max': None},
    {'name': 'Streak sizing', 'session_filter': None, 'atr_sl': 2, 'atr_tp': 4, 'sizing': 'streak_reduce', 'vol_min': None, 'vol_max': None},
    {'name': 'EU+US + Streak sizing', 'session_filter': ['EU', 'US'], 'atr_sl': 2, 'atr_tp': 4, 'sizing': 'streak_reduce', 'vol_min': None, 'vol_max': None},
    {'name': 'Best ATR + Streak', 'session_filter': None, 'atr_sl': 1.5, 'atr_tp': 4.5, 'sizing': 'streak_reduce', 'vol_min': None, 'vol_max': None},
    {'name': 'EU+US + Best ATR + Streak', 'session_filter': ['EU', 'US'], 'atr_sl': 1.5, 'atr_tp': 4.5, 'sizing': 'streak_reduce', 'vol_min': None, 'vol_max': None},
    {'name': 'High vol + Streak', 'session_filter': None, 'atr_sl': 2, 'atr_tp': 4, 'sizing': 'streak_reduce', 'vol_min': 0.5, 'vol_max': None},
]

best_combo = None
best_profit = 0

for c in combos:
    r = run_backtest(df, direction='LONG', trend_filter='BEAR',
                    session_filter=c['session_filter'],
                    atr_sl=c['atr_sl'], atr_tp=c['atr_tp'],
                    sizing=c['sizing'],
                    vol_min=c['vol_min'], vol_max=c['vol_max'],
                    name=c['name'])
    if r and r['filled'] > 5:
        print(f"{r['name']:<35} {r['filled']:<8} {r['wins']}/{r['losses']:<6} {r['win_rate']:.1f}%    {r['max_dd']:.2f}%    ${r['profit']:>+,.0f}")
        if r['profit'] > best_profit:
            best_profit = r['profit']
            best_combo = r

print("\n" + "=" * 100)
if best_combo:
    print(f"BEST COMBINATION: {best_combo['name']}")
    print(f"  Profit: ${best_combo['profit']:+,.0f} | Max DD: {best_combo['max_dd']:.2f}% | Win Rate: {best_combo['win_rate']:.1f}%")
print("=" * 100)

# ============================================
# SAME TESTS FOR SHORTS
# ============================================
print("\n\n" + "=" * 100)
print("SHORT STRATEGY OPTIMIZATIONS (SHORT in BEAR)")
print("=" * 100)

print(f"\n{'Optimization':<35} {'Trades':<8} {'W/L':<10} {'Win%':<8} {'MaxDD':<10} {'Profit':<12}")
print("-" * 95)

short_tests = [
    {'name': 'Baseline SHORT (BEAR)', 'session_filter': None, 'atr_sl': 2, 'atr_tp': 4, 'sizing': 'fixed'},
    {'name': 'SHORT EU+US', 'session_filter': ['EU', 'US'], 'atr_sl': 2, 'atr_tp': 4, 'sizing': 'fixed'},
    {'name': 'SHORT ATR 1.5/3', 'session_filter': None, 'atr_sl': 1.5, 'atr_tp': 3, 'sizing': 'fixed'},
    {'name': 'SHORT ATR 2/3', 'session_filter': None, 'atr_sl': 2, 'atr_tp': 3, 'sizing': 'fixed'},
    {'name': 'SHORT Streak sizing', 'session_filter': None, 'atr_sl': 2, 'atr_tp': 4, 'sizing': 'streak_reduce'},
    {'name': 'SHORT EU+US + Streak', 'session_filter': ['EU', 'US'], 'atr_sl': 2, 'atr_tp': 4, 'sizing': 'streak_reduce'},
]

for c in short_tests:
    r = run_backtest(df, direction='SHORT', trend_filter='BEAR',
                    session_filter=c['session_filter'],
                    atr_sl=c['atr_sl'], atr_tp=c['atr_tp'],
                    sizing=c['sizing'],
                    name=c['name'])
    if r and r['filled'] > 3:
        print(f"{r['name']:<35} {r['filled']:<8} {r['wins']}/{r['losses']:<6} {r['win_rate']:.1f}%    {r['max_dd']:.2f}%    ${r['profit']:>+,.0f}")
