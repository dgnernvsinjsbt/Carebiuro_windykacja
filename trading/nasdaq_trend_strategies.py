#!/usr/bin/env python3
"""
Custom Trend Following Strategies for NASDAQ100 Futures
Testing multiple approaches to find what works for lower-vol assets
"""

import pandas as pd
import numpy as np

# Load data
df = pd.read_csv('/home/user/Carebiuro_windykacja/trading/nasdaq_nq_futures_1h_2025.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

print(f"Data: {len(df)} 1h candles, {df['timestamp'].min().date()} to {df['timestamp'].max().date()}")

# Pre-calculate common indicators
df['tr'] = np.maximum(df['high'] - df['low'],
                      np.maximum(abs(df['high'] - df['close'].shift(1)),
                                abs(df['low'] - df['close'].shift(1))))
df['atr'] = df['tr'].rolling(14).mean()

# ADX calculation
def calc_adx(df, period=14):
    df = df.copy()
    df['up_move'] = df['high'] - df['high'].shift(1)
    df['down_move'] = df['low'].shift(1) - df['low']

    df['plus_dm'] = np.where((df['up_move'] > df['down_move']) & (df['up_move'] > 0), df['up_move'], 0)
    df['minus_dm'] = np.where((df['down_move'] > df['up_move']) & (df['down_move'] > 0), df['down_move'], 0)

    df['plus_di'] = 100 * (df['plus_dm'].ewm(span=period, adjust=False).mean() / df['atr'])
    df['minus_di'] = 100 * (df['minus_dm'].ewm(span=period, adjust=False).mean() / df['atr'])

    df['dx'] = 100 * abs(df['plus_di'] - df['minus_di']) / (df['plus_di'] + df['minus_di'])
    df['adx'] = df['dx'].ewm(span=period, adjust=False).mean()

    return df

df = calc_adx(df)

# Donchian channels
df['donchian_high_20'] = df['high'].rolling(20).max()
df['donchian_low_20'] = df['low'].rolling(20).min()
df['donchian_high_50'] = df['high'].rolling(50).max()
df['donchian_low_50'] = df['low'].rolling(50).min()

# EMAs
for span in [8, 13, 21, 34, 50, 55, 100, 200]:
    df[f'ema{span}'] = df['close'].ewm(span=span, adjust=False).mean()

# ROC (Rate of Change)
df['roc_10'] = (df['close'] - df['close'].shift(10)) / df['close'].shift(10) * 100
df['roc_20'] = (df['close'] - df['close'].shift(20)) / df['close'].shift(20) * 100

# Volatility expansion
df['atr_sma'] = df['atr'].rolling(50).mean()
df['vol_expansion'] = df['atr'] > df['atr_sma'] * 1.2

FEE_PCT = 0.01

def backtest_strategy(df, signals_long, signals_short, tp_atr, sl_atr, max_wait=20, name="Strategy"):
    """Generic backtester"""
    equity = 100.0
    max_equity = 100.0
    max_dd = 0.0
    trades = []
    position = None
    pending = None

    for i in range(50, len(df)):
        row = df.iloc[i]

        # Check pending
        if pending is not None:
            bars = i - pending['bar']
            filled = False
            if pending['side'] == 'LONG' and row['low'] <= pending['limit']:
                filled = True
                entry = pending['limit']
            elif pending['side'] == 'SHORT' and row['high'] >= pending['limit']:
                filled = True
                entry = pending['limit']

            if filled:
                position = {'side': pending['side'], 'entry': entry, 'tp': pending['tp'], 'sl': pending['sl'], 'entry_bar': i}
                pending = None
            elif bars >= max_wait:
                pending = None

        # Check position
        if position is not None:
            exit_price = None
            win = False
            if position['side'] == 'LONG':
                if row['high'] >= position['tp']:
                    exit_price = position['tp']
                    win = True
                elif row['low'] <= position['sl']:
                    exit_price = position['sl']
            else:
                if row['low'] <= position['tp']:
                    exit_price = position['tp']
                    win = True
                elif row['high'] >= position['sl']:
                    exit_price = position['sl']

            if exit_price is not None:
                if position['side'] == 'LONG':
                    pnl = (exit_price - position['entry']) / position['entry'] * 100
                else:
                    pnl = (position['entry'] - exit_price) / position['entry'] * 100
                pnl -= FEE_PCT * 2
                equity *= (1 + pnl/100)
                max_equity = max(max_equity, equity)
                dd = (equity - max_equity) / max_equity * 100
                max_dd = min(max_dd, dd)
                trades.append({'pnl': pnl, 'win': win, 'bars': i - position['entry_bar']})
                position = None

        # New signals
        if position is None and pending is None:
            atr = row['atr']
            price = row['close']

            if signals_long.iloc[i]:
                pending = {
                    'side': 'LONG', 'bar': i,
                    'limit': price - 0.7 * atr,
                    'tp': price + tp_atr * atr,
                    'sl': price - sl_atr * atr
                }
            elif signals_short.iloc[i]:
                pending = {
                    'side': 'SHORT', 'bar': i,
                    'limit': price + 0.7 * atr,
                    'tp': price - tp_atr * atr,
                    'sl': price + sl_atr * atr
                }

    ret = equity - 100
    rr = ret / abs(max_dd) if max_dd != 0 else 0
    n_trades = len(trades)
    win_rate = sum(1 for t in trades if t['win']) / n_trades * 100 if n_trades > 0 else 0
    avg_bars = np.mean([t['bars'] for t in trades]) if trades else 0

    return ret, max_dd, rr, n_trades, win_rate, avg_bars


print("\n" + "=" * 90)
print("TESTING TREND FOLLOWING STRATEGIES FOR NASDAQ100")
print("=" * 90)

results = []

# ============================================================
# STRATEGY 1: DONCHIAN BREAKOUT (Turtle Trading)
# ============================================================
print("\n📊 STRATEGY 1: DONCHIAN BREAKOUT")
print("-" * 60)

for period in [20, 50]:
    df[f'donch_long_{period}'] = df['close'] > df[f'donchian_high_{period}'].shift(1)
    df[f'donch_short_{period}'] = df['close'] < df[f'donchian_low_{period}'].shift(1)

    for tp in [8, 10, 12]:
        for sl in [4, 5, 6]:
            ret, dd, rr, trades, wr, bars = backtest_strategy(
                df, df[f'donch_long_{period}'], df[f'donch_short_{period}'],
                tp, sl, max_wait=30, name=f"Donchian-{period}"
            )
            if trades >= 5:
                results.append({
                    'strategy': f'Donchian-{period}',
                    'params': f'TP{tp}/SL{sl}',
                    'return': ret, 'max_dd': dd, 'rr': rr,
                    'trades': trades, 'win_rate': wr, 'avg_bars': bars
                })

# ============================================================
# STRATEGY 2: ADX FILTERED EMA
# ============================================================
print("\n📊 STRATEGY 2: ADX FILTERED EMA (only trade when trending)")
print("-" * 60)

for adx_thresh in [20, 25, 30]:
    for ema_f, ema_s in [(13, 34), (21, 55), (8, 21)]:
        df['ema_cross_long'] = (df[f'ema{ema_f}'] > df[f'ema{ema_s}']) & (df[f'ema{ema_f}'].shift(1) <= df[f'ema{ema_s}'].shift(1))
        df['ema_cross_short'] = (df[f'ema{ema_f}'] < df[f'ema{ema_s}']) & (df[f'ema{ema_f}'].shift(1) >= df[f'ema{ema_s}'].shift(1))

        # Filter by ADX
        df['adx_long'] = df['ema_cross_long'] & (df['adx'] > adx_thresh)
        df['adx_short'] = df['ema_cross_short'] & (df['adx'] > adx_thresh)

        for tp in [10, 12, 15]:
            for sl in [5, 6, 8]:
                ret, dd, rr, trades, wr, bars = backtest_strategy(
                    df, df['adx_long'], df['adx_short'],
                    tp, sl, max_wait=30, name=f"ADX{adx_thresh}-EMA{ema_f}/{ema_s}"
                )
                if trades >= 5:
                    results.append({
                        'strategy': f'ADX>{adx_thresh} EMA{ema_f}/{ema_s}',
                        'params': f'TP{tp}/SL{sl}',
                        'return': ret, 'max_dd': dd, 'rr': rr,
                        'trades': trades, 'win_rate': wr, 'avg_bars': bars
                    })

# ============================================================
# STRATEGY 3: MOMENTUM BREAKOUT (ROC + Price Structure)
# ============================================================
print("\n📊 STRATEGY 3: MOMENTUM BREAKOUT")
print("-" * 60)

for roc_thresh in [2, 3, 5]:
    # Long: ROC positive AND price above EMA50 AND making higher high
    df['higher_high'] = df['high'] > df['high'].shift(1).rolling(5).max()
    df['lower_low'] = df['low'] < df['low'].shift(1).rolling(5).min()

    df['mom_long'] = (df['roc_20'] > roc_thresh) & (df['close'] > df['ema50']) & df['higher_high']
    df['mom_short'] = (df['roc_20'] < -roc_thresh) & (df['close'] < df['ema50']) & df['lower_low']

    for tp in [8, 10, 12]:
        for sl in [4, 5, 6]:
            ret, dd, rr, trades, wr, bars = backtest_strategy(
                df, df['mom_long'], df['mom_short'],
                tp, sl, max_wait=30, name=f"Momentum-ROC{roc_thresh}"
            )
            if trades >= 5:
                results.append({
                    'strategy': f'Momentum ROC>{roc_thresh}%',
                    'params': f'TP{tp}/SL{sl}',
                    'return': ret, 'max_dd': dd, 'rr': rr,
                    'trades': trades, 'win_rate': wr, 'avg_bars': bars
                })

# ============================================================
# STRATEGY 4: VOLATILITY EXPANSION + TREND
# ============================================================
print("\n📊 STRATEGY 4: VOLATILITY EXPANSION + TREND FILTER")
print("-" * 60)

# Trade when volatility expands AND price confirms trend direction
df['vol_long'] = df['vol_expansion'] & (df['close'] > df['ema21']) & (df['close'] > df['close'].shift(1))
df['vol_short'] = df['vol_expansion'] & (df['close'] < df['ema21']) & (df['close'] < df['close'].shift(1))

for tp in [8, 10, 12, 15]:
    for sl in [4, 5, 6, 8]:
        ret, dd, rr, trades, wr, bars = backtest_strategy(
            df, df['vol_long'], df['vol_short'],
            tp, sl, max_wait=30, name="VolExpansion"
        )
        if trades >= 5:
            results.append({
                'strategy': 'Vol Expansion + Trend',
                'params': f'TP{tp}/SL{sl}',
                'return': ret, 'max_dd': dd, 'rr': rr,
                'trades': trades, 'win_rate': wr, 'avg_bars': bars
            })

# ============================================================
# STRATEGY 5: TREND CONTINUATION (Pullback to EMA in trend)
# ============================================================
print("\n📊 STRATEGY 5: TREND CONTINUATION (Pullback Entry)")
print("-" * 60)

for ema in [21, 34, 50]:
    # Uptrend: Price above EMA, pulls back to touch EMA, bounces
    df['uptrend'] = df['close'] > df[f'ema{ema}']
    df['pullback_long'] = (df['low'] <= df[f'ema{ema}']) & df['uptrend'].shift(1) & (df['close'] > df['open'])

    df['downtrend'] = df['close'] < df[f'ema{ema}']
    df['pullback_short'] = (df['high'] >= df[f'ema{ema}']) & df['downtrend'].shift(1) & (df['close'] < df['open'])

    for tp in [6, 8, 10, 12]:
        for sl in [3, 4, 5, 6]:
            ret, dd, rr, trades, wr, bars = backtest_strategy(
                df, df['pullback_long'], df['pullback_short'],
                tp, sl, max_wait=20, name=f"Pullback-EMA{ema}"
            )
            if trades >= 10:  # Need more trades for pullback
                results.append({
                    'strategy': f'Pullback to EMA{ema}',
                    'params': f'TP{tp}/SL{sl}',
                    'return': ret, 'max_dd': dd, 'rr': rr,
                    'trades': trades, 'win_rate': wr, 'avg_bars': bars
                })

# ============================================================
# STRATEGY 6: BREAKOUT WITH VOLUME/MOMENTUM CONFIRMATION
# ============================================================
print("\n📊 STRATEGY 6: CONFIRMED BREAKOUT (Multi-filter)")
print("-" * 60)

# Breakout above 20-period high + ADX trending + momentum positive
df['confirmed_long'] = (
    (df['close'] > df['donchian_high_20'].shift(1)) &
    (df['adx'] > 20) &
    (df['roc_10'] > 0) &
    (df['close'] > df['ema50'])
)
df['confirmed_short'] = (
    (df['close'] < df['donchian_low_20'].shift(1)) &
    (df['adx'] > 20) &
    (df['roc_10'] < 0) &
    (df['close'] < df['ema50'])
)

for tp in [8, 10, 12, 15]:
    for sl in [4, 5, 6, 8]:
        ret, dd, rr, trades, wr, bars = backtest_strategy(
            df, df['confirmed_long'], df['confirmed_short'],
            tp, sl, max_wait=30, name="Confirmed Breakout"
        )
        if trades >= 5:
            results.append({
                'strategy': 'Confirmed Breakout',
                'params': f'TP{tp}/SL{sl}',
                'return': ret, 'max_dd': dd, 'rr': rr,
                'trades': trades, 'win_rate': wr, 'avg_bars': bars
            })

# ============================================================
# RESULTS
# ============================================================
print("\n" + "=" * 90)
print("TOP 20 RESULTS (sorted by R:R)")
print("=" * 90)

results_df = pd.DataFrame(results)
results_df = results_df.sort_values('rr', ascending=False)

print(f"{'Strategy':<30} {'Params':<12} {'Return':>10} {'MaxDD':>10} {'R:R':>8} {'Trades':>8} {'Win%':>8}")
print("-" * 90)

for _, r in results_df.head(20).iterrows():
    print(f"{r['strategy']:<30} {r['params']:<12} {r['return']:>+9.2f}% {r['max_dd']:>9.2f}% {r['rr']:>7.2f}x {r['trades']:>8.0f} {r['win_rate']:>7.1f}%")

print("-" * 90)
best = results_df.iloc[0]
print(f"\n🏆 BEST STRATEGY: {best['strategy']}")
print(f"   Params: {best['params']}")
print(f"   Return: {best['return']:+.2f}%")
print(f"   Max DD: {best['max_dd']:.2f}%")
print(f"   R:R: {best['rr']:.2f}x")
print(f"   Trades: {best['trades']:.0f}")
print(f"   Win Rate: {best['win_rate']:.1f}%")

# Show strategy comparison
print("\n" + "=" * 90)
print("STRATEGY TYPE COMPARISON (best of each)")
print("=" * 90)

strategy_types = results_df.groupby('strategy').apply(lambda x: x.loc[x['rr'].idxmax()]).reset_index(drop=True)
strategy_types = strategy_types.sort_values('rr', ascending=False)

print(f"{'Strategy':<30} {'Params':<12} {'Return':>10} {'R:R':>8} {'Trades':>8} {'Win%':>8}")
print("-" * 90)
for _, r in strategy_types.head(10).iterrows():
    print(f"{r['strategy']:<30} {r['params']:<12} {r['return']:>+9.2f}% {r['rr']:>7.2f}x {r['trades']:>8.0f} {r['win_rate']:>7.1f}%")
