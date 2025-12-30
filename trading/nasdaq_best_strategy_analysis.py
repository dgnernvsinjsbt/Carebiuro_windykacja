#!/usr/bin/env python3
"""
Deep analysis of best NASDAQ strategies
"""

import pandas as pd
import numpy as np

df = pd.read_csv('/home/user/Carebiuro_windykacja/trading/nasdaq_nq_futures_1h_2025.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Indicators
df['tr'] = np.maximum(df['high'] - df['low'],
                      np.maximum(abs(df['high'] - df['close'].shift(1)),
                                abs(df['low'] - df['close'].shift(1))))
df['atr'] = df['tr'].rolling(14).mean()

# ADX
df['up_move'] = df['high'] - df['high'].shift(1)
df['down_move'] = df['low'].shift(1) - df['low']
df['plus_dm'] = np.where((df['up_move'] > df['down_move']) & (df['up_move'] > 0), df['up_move'], 0)
df['minus_dm'] = np.where((df['down_move'] > df['up_move']) & (df['down_move'] > 0), df['down_move'], 0)
df['plus_di'] = 100 * (pd.Series(df['plus_dm']).ewm(span=14, adjust=False).mean() / df['atr'])
df['minus_di'] = 100 * (pd.Series(df['minus_dm']).ewm(span=14, adjust=False).mean() / df['atr'])
df['dx'] = 100 * abs(df['plus_di'] - df['minus_di']) / (df['plus_di'] + df['minus_di'])
df['adx'] = df['dx'].ewm(span=14, adjust=False).mean()

# EMAs
df['ema13'] = df['close'].ewm(span=13, adjust=False).mean()
df['ema34'] = df['close'].ewm(span=34, adjust=False).mean()
df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
df['ema55'] = df['close'].ewm(span=55, adjust=False).mean()

FEE_PCT = 0.01

def detailed_backtest(df, signals_long, signals_short, tp_atr, sl_atr, offset_atr=0.7, max_wait=20):
    trades = []
    equity = 100.0
    max_equity = 100.0
    max_dd = 0.0
    position = None
    pending = None

    for i in range(50, len(df)):
        row = df.iloc[i]

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
                position = {
                    'side': pending['side'], 'entry': entry,
                    'tp': pending['tp'], 'sl': pending['sl'],
                    'entry_bar': i, 'entry_time': row['timestamp']
                }
                pending = None
            elif bars >= max_wait:
                pending = None

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

                trades.append({
                    'entry_time': position['entry_time'],
                    'exit_time': row['timestamp'],
                    'side': position['side'],
                    'entry': position['entry'],
                    'exit': exit_price,
                    'pnl': pnl,
                    'win': win,
                    'bars': i - position['entry_bar'],
                    'equity': equity
                })
                position = None

        if position is None and pending is None:
            atr = row['atr']
            price = row['close']
            if signals_long.iloc[i]:
                pending = {
                    'side': 'LONG', 'bar': i,
                    'limit': price - offset_atr * atr,
                    'tp': price + tp_atr * atr,
                    'sl': price - sl_atr * atr
                }
            elif signals_short.iloc[i]:
                pending = {
                    'side': 'SHORT', 'bar': i,
                    'limit': price + offset_atr * atr,
                    'tp': price - tp_atr * atr,
                    'sl': price + sl_atr * atr
                }

    return pd.DataFrame(trades), equity - 100, max_dd


# ============================================================
# STRATEGY 1: ADX>30 + EMA 13/34 (Best R:R)
# ============================================================
print("=" * 80)
print("🏆 STRATEGY 1: ADX>30 + EMA 13/34 CROSSOVER")
print("=" * 80)

df['ema_cross_long'] = (df['ema13'] > df['ema34']) & (df['ema13'].shift(1) <= df['ema34'].shift(1))
df['ema_cross_short'] = (df['ema13'] < df['ema34']) & (df['ema13'].shift(1) >= df['ema34'].shift(1))
df['adx30_long'] = df['ema_cross_long'] & (df['adx'] > 30)
df['adx30_short'] = df['ema_cross_short'] & (df['adx'] > 30)

trades1, ret1, dd1 = detailed_backtest(df, df['adx30_long'], df['adx30_short'], tp_atr=15, sl_atr=5)

print(f"\nParams: TP 15 ATR, SL 5 ATR, Offset 0.7 ATR")
print(f"Return: {ret1:+.2f}%")
print(f"Max DD: {dd1:.2f}%")
print(f"R:R: {ret1/abs(dd1):.2f}x")
print(f"Trades: {len(trades1)}")
print(f"Win Rate: {trades1['win'].mean()*100:.1f}%")

if len(trades1) > 0:
    wins = trades1[trades1['win']]
    losses = trades1[~trades1['win']]
    print(f"\nAvg Winner: {wins['pnl'].mean():+.2f}%" if len(wins) > 0 else "")
    print(f"Avg Loser: {losses['pnl'].mean():.2f}%" if len(losses) > 0 else "")
    print(f"Avg Trade Duration: {trades1['bars'].mean():.1f} bars ({trades1['bars'].mean()/24:.1f} days)")

    trades1['month'] = pd.to_datetime(trades1['exit_time']).dt.to_period('M')
    print("\n📅 Monthly:")
    for m in sorted(trades1['month'].unique()):
        mt = trades1[trades1['month'] == m]
        status = "✅" if mt['pnl'].sum() > 0 else "❌"
        print(f"  {m}: {mt['pnl'].sum():+.2f}% ({len(mt)} trades) {status}")

    longs = trades1[trades1['side'] == 'LONG']
    shorts = trades1[trades1['side'] == 'SHORT']
    print(f"\n  LONG: {longs['pnl'].sum():+.2f}% ({len(longs)} trades, {longs['win'].mean()*100:.0f}% win)")
    print(f"  SHORT: {shorts['pnl'].sum():+.2f}% ({len(shorts)} trades, {shorts['win'].mean()*100:.0f}% win)")


# ============================================================
# STRATEGY 2: Pullback to EMA50 (Best Win Rate)
# ============================================================
print("\n" + "=" * 80)
print("🎯 STRATEGY 2: PULLBACK TO EMA50")
print("=" * 80)

df['uptrend'] = df['close'] > df['ema50']
df['pullback_long'] = (df['low'] <= df['ema50']) & df['uptrend'].shift(1) & (df['close'] > df['open'])
df['downtrend'] = df['close'] < df['ema50']
df['pullback_short'] = (df['high'] >= df['ema50']) & df['downtrend'].shift(1) & (df['close'] < df['open'])

trades2, ret2, dd2 = detailed_backtest(df, df['pullback_long'], df['pullback_short'], tp_atr=10, sl_atr=4)

print(f"\nParams: TP 10 ATR, SL 4 ATR, Offset 0.7 ATR")
print(f"Return: {ret2:+.2f}%")
print(f"Max DD: {dd2:.2f}%")
print(f"R:R: {ret2/abs(dd2):.2f}x")
print(f"Trades: {len(trades2)}")
print(f"Win Rate: {trades2['win'].mean()*100:.1f}%")

if len(trades2) > 0:
    wins = trades2[trades2['win']]
    losses = trades2[~trades2['win']]
    print(f"\nAvg Winner: {wins['pnl'].mean():+.2f}%" if len(wins) > 0 else "")
    print(f"Avg Loser: {losses['pnl'].mean():.2f}%" if len(losses) > 0 else "")

    trades2['month'] = pd.to_datetime(trades2['exit_time']).dt.to_period('M')
    print("\n📅 Monthly:")
    for m in sorted(trades2['month'].unique()):
        mt = trades2[trades2['month'] == m]
        status = "✅" if mt['pnl'].sum() > 0 else "❌"
        print(f"  {m}: {mt['pnl'].sum():+.2f}% ({len(mt)} trades) {status}")

    longs = trades2[trades2['side'] == 'LONG']
    shorts = trades2[trades2['side'] == 'SHORT']
    print(f"\n  LONG: {longs['pnl'].sum():+.2f}% ({len(longs)} trades, {longs['win'].mean()*100:.0f}% win)")
    print(f"  SHORT: {shorts['pnl'].sum():+.2f}% ({len(shorts)} trades, {shorts['win'].mean()*100:.0f}% win)")


# ============================================================
# STRATEGY 3: ADX>25 + EMA 21/55 (Highest Win Rate)
# ============================================================
print("\n" + "=" * 80)
print("📈 STRATEGY 3: ADX>25 + EMA 21/55 (HIGHEST WIN RATE)")
print("=" * 80)

df['ema_cross_long2'] = (df['ema21'] > df['ema55']) & (df['ema21'].shift(1) <= df['ema55'].shift(1))
df['ema_cross_short2'] = (df['ema21'] < df['ema55']) & (df['ema21'].shift(1) >= df['ema55'].shift(1))
df['adx25_long'] = df['ema_cross_long2'] & (df['adx'] > 25)
df['adx25_short'] = df['ema_cross_short2'] & (df['adx'] > 25)

trades3, ret3, dd3 = detailed_backtest(df, df['adx25_long'], df['adx25_short'], tp_atr=10, sl_atr=8)

print(f"\nParams: TP 10 ATR, SL 8 ATR, Offset 0.7 ATR")
print(f"Return: {ret3:+.2f}%")
print(f"Max DD: {dd3:.2f}%")
print(f"R:R: {ret3/abs(dd3):.2f}x")
print(f"Trades: {len(trades3)}")
print(f"Win Rate: {trades3['win'].mean()*100:.1f}%")

if len(trades3) > 0:
    wins = trades3[trades3['win']]
    losses = trades3[~trades3['win']]
    print(f"\nAvg Winner: {wins['pnl'].mean():+.2f}%" if len(wins) > 0 else "")
    print(f"Avg Loser: {losses['pnl'].mean():.2f}%" if len(losses) > 0 else "")

    trades3['month'] = pd.to_datetime(trades3['exit_time']).dt.to_period('M')
    print("\n📅 Monthly:")
    for m in sorted(trades3['month'].unique()):
        mt = trades3[trades3['month'] == m]
        status = "✅" if mt['pnl'].sum() > 0 else "❌"
        print(f"  {m}: {mt['pnl'].sum():+.2f}% ({len(mt)} trades) {status}")

    longs = trades3[trades3['side'] == 'LONG']
    shorts = trades3[trades3['side'] == 'SHORT']
    print(f"\n  LONG: {longs['pnl'].sum():+.2f}% ({len(longs)} trades, {longs['win'].mean()*100:.0f}% win)")
    print(f"  SHORT: {shorts['pnl'].sum():+.2f}% ({len(shorts)} trades, {shorts['win'].mean()*100:.0f}% win)")


# ============================================================
# COMPARISON
# ============================================================
print("\n" + "=" * 80)
print("COMPARISON: BEST NASDAQ vs FARTCOIN")
print("=" * 80)
print(f"{'Metric':<25} {'ADX30+EMA':>15} {'Pullback':>15} {'ADX25+EMA21':>15} {'FARTCOIN':>15}")
print("-" * 80)
print(f"{'Return':<25} {ret1:>+14.2f}% {ret2:>+14.2f}% {ret3:>+14.2f}% {'+2232%':>15}")
print(f"{'Max Drawdown':<25} {dd1:>14.2f}% {dd2:>14.2f}% {dd3:>14.2f}% {'-17.86%':>15}")
print(f"{'R:R Ratio':<25} {ret1/abs(dd1):>14.2f}x {ret2/abs(dd2):>14.2f}x {ret3/abs(dd3):>14.2f}x {'124.98x':>15}")
print(f"{'Win Rate':<25} {trades1['win'].mean()*100:>14.1f}% {trades2['win'].mean()*100:>14.1f}% {trades3['win'].mean()*100:>14.1f}% {'67.7%':>15}")
print(f"{'Trades':<25} {len(trades1):>15} {len(trades2):>15} {len(trades3):>15} {'31':>15}")
print("=" * 80)

print("\n💡 KEY INSIGHT:")
print("   NASDAQ needs ADX filter to avoid choppy markets.")
print("   Best R:R comes from ADX>30 + slow EMA crossover.")
print("   But NASDAQ still can't match FARTCOIN's 124x R:R.")
print("   Different asset = different edge profile.")
