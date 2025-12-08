#!/usr/bin/env python3
"""
BB3 SHORT Strategy with Trend Filter
Test if filtering shorts to BULL trend (counter-trend) makes them profitable
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
df['short_signal'] = df['close'] > df['bb_upper_3']

# FEES
MAKER_FEE = 0.0002   # 0.02%
TAKER_FEE = 0.0005   # 0.05%
LIMIT_OFFSET = 0.00035
STARTING_BALANCE = 10000

def run_short_backtest(df, trend_filter=None, filter_value=None, name=""):
    """Run SHORT backtest with optional trend filter"""
    trades = []
    in_position = False

    for i in range(len(df)):
        row = df.iloc[i]

        if not in_position:
            # Check for SHORT signal
            if row['short_signal']:
                # Apply trend filter if specified
                if trend_filter is None or row[trend_filter] == filter_value:
                    in_position = True
                    entry_price = row['close']
                    entry_time = row['timestamp']
                    atr = row['atr']
                    stop_loss = entry_price + (atr * 2)    # Above for shorts
                    take_profit = entry_price - (atr * 4)  # Below for shorts
        else:
            # Check exit conditions
            high, low = row['high'], row['low']

            # Stop loss hit (price went UP)
            if high >= stop_loss:
                trades.append({
                    'entry_time': entry_time,
                    'exit_time': row['timestamp'],
                    'entry': entry_price,
                    'stop': stop_loss,
                    'target': take_profit,
                    'result': 'STOP'
                })
                in_position = False
            # Take profit hit (price went DOWN)
            elif low <= take_profit:
                trades.append({
                    'entry_time': entry_time,
                    'exit_time': row['timestamp'],
                    'entry': entry_price,
                    'stop': stop_loss,
                    'target': take_profit,
                    'result': 'TP'
                })
                in_position = False

    if not trades:
        return None

    trades_df = pd.DataFrame(trades)
    eth_idx = df.set_index('timestamp')

    # Get max price during trade (for limit fill check on shorts)
    def get_max_price(row):
        try:
            mask = (eth_idx.index >= row['entry_time']) & (eth_idx.index <= row['exit_time'])
            return eth_idx.loc[mask]['high'].max()
        except:
            return row['entry']

    trades_df['max_price'] = trades_df.apply(get_max_price, axis=1)

    # Simulate with limit orders
    balance = STARTING_BALANCE
    results = []

    for _, row in trades_df.iterrows():
        signal = row['entry']
        limit_price = signal * (1 + LIMIT_OFFSET)  # ABOVE for shorts
        max_price = row['max_price']

        # For shorts, limit fills if price goes UP to our limit
        filled = max_price >= limit_price

        if filled:
            entry = limit_price
            exit_price = row['target'] if row['result'] == 'TP' else row['stop']
            # SHORT P/L: (entry - exit) / entry
            gross = (entry - exit_price) / entry * 100
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

    res_df = pd.DataFrame(results)
    filled = res_df[res_df['filled']]

    if len(filled) == 0:
        return None

    # Max drawdown
    bal = np.array([STARTING_BALANCE] + list(res_df['balance']))
    peak = np.maximum.accumulate(bal)
    dd = (bal - peak) / peak * 100

    return {
        'name': name,
        'total_signals': len(trades_df),
        'filled': len(filled),
        'wins': int(filled['win'].sum()),
        'losses': int(len(filled) - filled['win'].sum()),
        'win_rate': filled['win'].sum() / len(filled) * 100,
        'net': filled['net'].sum(),
        'max_dd': dd.min(),
        'profit': balance - STARTING_BALANCE,
        'trades_df': trades_df,
        'results_df': res_df
    }

print("\n" + "=" * 100)
print("BB3 SHORT STRATEGY - TREND FILTER TEST")
print("Hypothesis: Shorts work better in BULL trend (counter-trend mean reversion)")
print("=" * 100)

results = []

# 1. Baseline - no filter
r = run_short_backtest(df, trend_filter=None, name="SHORT No Filter (baseline)")
if r: results.append(r)

# 2. Test WITH TREND (shorts in BEAR) - should be worse
for name, col in [('EMA200 BEAR', 'trend_ema200'), ('EMA Cross BEAR', 'trend_ema_cross'), ('1H BEAR', 'trend_1h')]:
    r = run_short_backtest(df, trend_filter=col, filter_value='BEAR', name=f"SHORT in {name}")
    if r: results.append(r)

# 3. Test COUNTER TREND (shorts in BULL) - hypothesis: should be better
for name, col in [('EMA200 BULL', 'trend_ema200'), ('EMA Cross BULL', 'trend_ema_cross'), ('1H BULL', 'trend_1h')]:
    r = run_short_backtest(df, trend_filter=col, filter_value='BULL', name=f"SHORT in {name}")
    if r: results.append(r)

# Print results
print(f"\n{'Strategy':<30} {'Signals':<8} {'Filled':<8} {'W/L':<10} {'Win%':<8} {'NET':<10} {'MaxDD':<10} {'Profit':<10}")
print("-" * 100)

for r in results:
    wl = f"{r['wins']}/{r['losses']}"
    print(f"{r['name']:<30} {r['total_signals']:<8} {r['filled']:<8} {wl:<10} {r['win_rate']:.1f}%    {r['net']:>+.2f}%   {r['max_dd']:.2f}%    ${r['profit']:>+,.0f}")

print("\n" + "=" * 100)

# Analyze
profitable = [r for r in results if r['profit'] > 0]
if profitable:
    best = max(profitable, key=lambda x: x['profit'])
    print(f"PROFITABLE SHORTS FOUND!")
    print(f"Best: {best['name']} → {best['net']:.2f}% net, ${best['profit']:+,.0f}, {best['max_dd']:.2f}% max DD")
else:
    # Find least bad
    best = max(results, key=lambda x: x['profit'])
    print(f"NO PROFITABLE SHORT STRATEGY FOUND")
    print(f"Least bad: {best['name']} → {best['net']:.2f}% net, ${best['profit']:+,.0f}")

print("=" * 100)

# Also analyze WIN RATE by trend at signal time
print("\n--- DETAILED ANALYSIS: Short signal performance by trend ---")

# Get all short signals with trend info
short_signals = df[df['short_signal']].copy()
print(f"\nTotal short signals: {len(short_signals)}")
print(f"  In BULL (EMA200): {len(short_signals[short_signals['trend_ema200']=='BULL'])}")
print(f"  In BEAR (EMA200): {len(short_signals[short_signals['trend_ema200']=='BEAR'])}")
print(f"  In BULL (1H): {len(short_signals[short_signals['trend_1h']=='BULL'])}")
print(f"  In BEAR (1H): {len(short_signals[short_signals['trend_1h']=='BEAR'])}")
