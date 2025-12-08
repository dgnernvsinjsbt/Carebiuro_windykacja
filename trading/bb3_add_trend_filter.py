#!/usr/bin/env python3
"""
Add trend filter to ORIGINAL BB3 trades (121 trades, +5.54% verified)
Test if we can improve by filtering out counter-trend trades
"""
import pandas as pd
import numpy as np

# Load original trades
trades = pd.read_csv('results/bb3_std_all_trades.csv')
trades['entry_time'] = pd.to_datetime(trades['entry_time'])
print(f"Original trades: {len(trades)}")

# Load 1-min data for trend calculation
df = pd.read_csv('eth_usdt_1m_lbank.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# Calculate trend indicators
df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()
df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()

# 1H trend
df_1h = df.set_index('timestamp').resample('1h').agg({
    'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'
}).dropna()
df_1h['ema_50_1h'] = df_1h['close'].ewm(span=50, adjust=False).mean()
df_1h['trend_1h'] = np.where(df_1h['close'] > df_1h['ema_50_1h'], 'BULL', 'BEAR')

# Map to 1m data
df['timestamp_1h'] = df['timestamp'].dt.floor('1h')
df = df.merge(df_1h[['trend_1h']], left_on='timestamp_1h', right_index=True, how='left')

df['trend_ema200'] = np.where(df['close'] > df['ema_200'], 'BULL', 'BEAR')
df['trend_ema_cross'] = np.where(df['ema_50'] > df['ema_200'], 'BULL', 'BEAR')
df = df.set_index('timestamp')

# Add trend at entry time to each trade
def get_trend(entry_time, trend_col):
    try:
        # Find nearest row
        idx = df.index.get_indexer([entry_time], method='nearest')[0]
        return df.iloc[idx][trend_col]
    except:
        return 'UNKNOWN'

trades['trend_ema200'] = trades['entry_time'].apply(lambda t: get_trend(t, 'trend_ema200'))
trades['trend_ema_cross'] = trades['entry_time'].apply(lambda t: get_trend(t, 'trend_ema_cross'))
trades['trend_1h'] = trades['entry_time'].apply(lambda t: get_trend(t, 'trend_1h'))

# Get min price during trade for limit order simulation
def get_min_price(entry_time, exit_time):
    try:
        mask = (df.index >= entry_time) & (df.index <= pd.to_datetime(exit_time))
        return df.loc[mask]['low'].min()
    except:
        return None

trades['exit_time'] = pd.to_datetime(trades['exit_time'])
trades['min_price'] = trades.apply(lambda r: get_min_price(r['entry_time'], r['exit_time']), axis=1)

# Constants
MAKER_FEE = 0.0002
TAKER_FEE = 0.0005
LIMIT_OFFSET = 0.00035
STARTING_BALANCE = 10000

def simulate_with_filter(trades, trend_col=None, filter_value='BULL'):
    """Simulate trades, optionally filtering by trend"""
    balance = STARTING_BALANCE
    results = []

    for _, row in trades.iterrows():
        # Apply filter (for LONG trades, we want BULL trend)
        if trend_col and row[trend_col] != filter_value:
            continue  # Skip this trade

        signal = row['entry']
        limit_price = signal * (1 - LIMIT_OFFSET)
        min_price = row['min_price'] if pd.notna(row['min_price']) else row['stop']

        filled = min_price <= limit_price

        if filled:
            entry = limit_price
            exit_price = row['target'] if row['result'] == 'TP' else row['stop']
            gross = (exit_price - entry) / entry * 100
            fee = (MAKER_FEE + TAKER_FEE) * 100
            net = gross - fee
            pnl = balance * (net / 100)
            balance += pnl
            results.append({
                'filled': True, 'result': row['result'],
                'gross': gross, 'net': net, 'balance': balance, 'win': gross > 0
            })
        else:
            results.append({
                'filled': False, 'result': 'SKIP',
                'gross': 0, 'net': 0, 'balance': balance, 'win': False
            })

    if not results:
        return None

    res_df = pd.DataFrame(results)
    filled = res_df[res_df['filled']]

    if len(filled) == 0:
        return None

    bal = np.array([STARTING_BALANCE] + list(res_df['balance']))
    peak = np.maximum.accumulate(bal)
    dd = (bal - peak) / peak * 100

    return {
        'filled': len(filled),
        'wins': int(filled['win'].sum()),
        'losses': int(len(filled) - filled['win'].sum()),
        'win_rate': filled['win'].sum() / len(filled) * 100,
        'net': filled['net'].sum(),
        'max_dd': dd.min(),
        'profit': balance - STARTING_BALANCE
    }

print("\n" + "=" * 90)
print("BB3 LONG STRATEGY - TREND FILTER TEST")
print("Using ORIGINAL 121 trades, testing trend filters")
print("=" * 90)

# Analyze trend distribution in trades
print(f"\nTrend distribution at entry:")
print(f"  EMA200:     BULL={len(trades[trades['trend_ema200']=='BULL'])}, BEAR={len(trades[trades['trend_ema200']=='BEAR'])}")
print(f"  EMA Cross:  BULL={len(trades[trades['trend_ema_cross']=='BULL'])}, BEAR={len(trades[trades['trend_ema_cross']=='BEAR'])}")
print(f"  1H Trend:   BULL={len(trades[trades['trend_1h']=='BULL'])}, BEAR={len(trades[trades['trend_1h']=='BEAR'])}")

# Analyze win rate by trend
print(f"\nWin rate by trend:")
for trend_col in ['trend_ema200', 'trend_ema_cross', 'trend_1h']:
    bull_trades = trades[trades[trend_col] == 'BULL']
    bear_trades = trades[trades[trend_col] == 'BEAR']
    bull_wr = (bull_trades['result'] == 'TP').sum() / len(bull_trades) * 100 if len(bull_trades) > 0 else 0
    bear_wr = (bear_trades['result'] == 'TP').sum() / len(bear_trades) * 100 if len(bear_trades) > 0 else 0
    print(f"  {trend_col:15}: BULL {bull_wr:.1f}% ({len(bull_trades)} trades), BEAR {bear_wr:.1f}% ({len(bear_trades)} trades)")

# Test different filters
print(f"\n{'Strategy':<30} {'Trades':<8} {'W/L':<10} {'Win%':<8} {'NET':<10} {'MaxDD':<10} {'Profit':<10}")
print("-" * 90)

# Baseline - no filter
r = simulate_with_filter(trades, trend_col=None)
print(f"{'No Filter (baseline)':<30} {r['filled']:<8} {r['wins']}/{r['losses']:<6} {r['win_rate']:.1f}%    {r['net']:>+.2f}%   {r['max_dd']:.2f}%    ${r['profit']:>+,.0f}")

# Test each trend filter (LONG = want BULL)
for name, col in [('EMA200 Filter', 'trend_ema200'), ('EMA Cross Filter', 'trend_ema_cross'), ('1H Trend Filter', 'trend_1h')]:
    r = simulate_with_filter(trades, trend_col=col, filter_value='BULL')
    if r:
        print(f"{name:<30} {r['filled']:<8} {r['wins']}/{r['losses']:<6} {r['win_rate']:.1f}%    {r['net']:>+.2f}%   {r['max_dd']:.2f}%    ${r['profit']:>+,.0f}")

# Test BEAR filter (counter-trend longs - should be worse)
print(f"\n--- Counter-trend test (LONG in BEAR - should be worse) ---")
for name, col in [('EMA200 (BEAR)', 'trend_ema200'), ('EMA Cross (BEAR)', 'trend_ema_cross'), ('1H Trend (BEAR)', 'trend_1h')]:
    r = simulate_with_filter(trades, trend_col=col, filter_value='BEAR')
    if r:
        print(f"{name:<30} {r['filled']:<8} {r['wins']}/{r['losses']:<6} {r['win_rate']:.1f}%    {r['net']:>+.2f}%   {r['max_dd']:.2f}%    ${r['profit']:>+,.0f}")

print("\n" + "=" * 90)
print("CONCLUSION")
print("=" * 90)
