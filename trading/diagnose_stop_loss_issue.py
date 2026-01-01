#!/usr/bin/env python3
"""
If mean reversion was working (75% success), why did we hit stops 50% of the time?
Diagnose: Stop loss placement, limit order fills, entry timing
"""

import pandas as pd
import numpy as np

# Load Dec 8-15 trades
df = pd.read_csv('dec8_15_all_trades.csv')
df['entry_time'] = pd.to_datetime(df['entry_time'])
df['exit_time'] = pd.to_datetime(df['exit_time'])

# Load Sep-Dec 7 trades for comparison
df_old = pd.read_csv('portfolio_trade_log_chronological.csv')

print("=" * 80)
print("DIAGNOSIS: Why Did 50% of Trades Hit Stop Loss?")
print("=" * 80)

# 1. Stop Loss Distance Analysis
print("\n1. STOP LOSS PLACEMENT:")
print("-" * 40)

# Calculate stop distance as % from entry
df['stop_distance_pct'] = abs((df['stop_loss'] - df['entry_price']) / df['entry_price'] * 100)
df['tp_distance_pct'] = abs((df['take_profit'] - df['entry_price']) / df['entry_price'] * 100)

stop_loss_trades = df[df['exit_reason'] == 'SL']
take_profit_trades = df[df['exit_reason'] == 'TP']

print(f"  Avg Stop Distance: {df['stop_distance_pct'].mean():.2f}%")
print(f"  Avg TP Distance: {df['tp_distance_pct'].mean():.2f}%")
print(f"  Risk/Reward Ratio: {df['tp_distance_pct'].mean() / df['stop_distance_pct'].mean():.2f}x")

print(f"\n  SL Trades - Avg Stop Distance: {stop_loss_trades['stop_distance_pct'].mean():.2f}%")
print(f"  TP Trades - Avg TP Distance: {take_profit_trades['tp_distance_pct'].mean():.2f}%")

# 2. How close did we get to TP before hitting SL?
print("\n2. NEAR-MISSES (Trades that almost hit TP before SL):")
print("-" * 40)

# For now we can't easily calculate this without tick data
# But we can look at how far the SL trades were from TP when they got stopped

for idx, trade in stop_loss_trades.head(10).iterrows():
    pnl = trade['pnl_pct']
    stop_dist = trade['stop_distance_pct']
    tp_dist = trade['tp_distance_pct']

    # How far were we from TP when stopped?
    distance_to_tp = tp_dist + abs(pnl)  # If we lost 3%, and TP was 5% away, we were 8% from TP

    print(f"  {trade['symbol']:15} {trade['direction']:5} | Loss: {pnl:+.2f}% | "
          f"Stop: {stop_dist:.2f}% | TP: {tp_dist:.2f}% | Was {distance_to_tp:.2f}% from TP")

# 3. ATR-based stops - were they appropriate for Dec 8-15 volatility?
print("\n3. STOP SIZE vs VOLATILITY:")
print("-" * 40)

# Calculate how many ATRs each stop represented
# ATR is stored in the trades
df['stop_in_atrs'] = df['stop_distance_pct'] / (df['atr'] / df['entry_price'] * 100)
stop_loss_trades = df[df['exit_reason'] == 'SL'].copy()
take_profit_trades = df[df['exit_reason'] == 'TP'].copy()

print(f"  Avg Stop Size: {df['stop_in_atrs'].mean():.2f}x ATR")
print(f"  SL Trades - Stop Size: {stop_loss_trades['stop_in_atrs'].mean():.2f}x ATR")
print(f"  TP Trades - Stop Size: {take_profit_trades['stop_in_atrs'].mean():.2f}x ATR")

# Was Dec 8-15 more volatile than Sep-Dec 7?
print(f"\n  Dec 8-15 Avg ATR%: {(df['atr'] / df['entry_price'] * 100).mean():.2f}%")

# 4. Limit Order Fills - Are we entering at bad prices?
print("\n4. LIMIT ORDER ANALYSIS:")
print("-" * 40)

# Signal price vs entry price difference
df['limit_slippage_pct'] = ((df['entry_price'] - df['signal_price']) / df['signal_price'] * 100)

print(f"  Avg Limit Offset: {abs(df['limit_slippage_pct'].mean()):.2f}%")
print(f"  SL Trades - Limit Offset: {abs(stop_loss_trades['limit_slippage_pct'].mean()):.2f}%")
print(f"  TP Trades - Limit Offset: {abs(take_profit_trades['limit_slippage_pct'].mean()):.2f}%")

# Are losing trades getting worse fills?
if abs(stop_loss_trades['limit_slippage_pct'].mean()) > abs(take_profit_trades['limit_slippage_pct'].mean()):
    print("\n  ⚠️ PROBLEM: Losing trades are getting WORSE limit fills than winners!")
    print("  This suggests limit orders are catching falling knives / pumps")

# 5. Direction Bias
print("\n5. DIRECTIONAL BIAS:")
print("-" * 40)

for direction in ['LONG', 'SHORT']:
    dir_trades = df[df['direction'] == direction]
    dir_sl = dir_trades[dir_trades['exit_reason'] == 'SL']

    sl_rate = (len(dir_sl) / len(dir_trades)) * 100
    avg_pnl = dir_trades['pnl_pct'].mean()

    print(f"  {direction:5}: {len(dir_trades):2} trades | SL Rate: {sl_rate:5.1f}% | Avg P&L: {avg_pnl:+.2f}%")

# 6. Comparison to Sep-Dec 7
print("\n6. COMPARISON TO SEP-DEC 7 PERIOD:")
print("-" * 40)

# We don't have full data for old period, but we can estimate
sep_dec_sl_rate = 20.3
dec_sl_rate = 50.0

print(f"  Sep-Dec 7 Stop Loss Rate: {sep_dec_sl_rate:.1f}%")
print(f"  Dec 8-15 Stop Loss Rate:  {dec_sl_rate:.1f}%")
print(f"  **INCREASE: {dec_sl_rate - sep_dec_sl_rate:+.1f} percentage points**")

# 7. Coin-specific stop loss patterns
print("\n7. STOP LOSS PATTERNS BY COIN:")
print("-" * 80)
print(f"{'Coin':<15} {'Trades':>7} {'SL Rate':>9} {'Avg Stop':>10} {'ATR%':>8} {'Comment':<30}")
print("-" * 80)

for symbol in sorted(df['symbol'].unique()):
    coin_trades = df[df['symbol'] == symbol]
    coin_sl = coin_trades[coin_trades['exit_reason'] == 'SL']

    sl_rate = (len(coin_sl) / len(coin_trades)) * 100
    avg_stop_dist = coin_trades['stop_distance_pct'].mean()
    avg_atr_pct = (coin_trades['atr'] / coin_trades['entry_price'] * 100).mean()

    comment = ""
    if sl_rate > 60:
        comment = "🔴 Very high SL rate"
    elif avg_stop_dist < avg_atr_pct * 1.2:
        comment = "⚠️ Stops might be too tight"

    print(f"{symbol:<15} {len(coin_trades):>7} {sl_rate:>8.1f}% {avg_stop_dist:>9.2f}% {avg_atr_pct:>7.2f}% {comment:<30}")

print("\n" + "=" * 80)
print("ROOT CAUSE ANALYSIS:")
print("=" * 80)

# Calculate key metrics
avg_stop_in_atrs = df['stop_in_atrs'].mean()
avg_tp_in_atrs = df['tp_distance_pct'].mean() / (df['atr'] / df['entry_price'] * 100).mean()

print(f"\n📊 KEY FINDINGS:")
print(f"  1. Stops are {avg_stop_in_atrs:.2f}x ATR on average")
print(f"  2. TPs are {avg_tp_in_atrs:.2f}x ATR on average")
print(f"  3. R:R ratio is {avg_tp_in_atrs / avg_stop_in_atrs:.2f}:1")

# Identify the issue
if avg_stop_in_atrs < 1.5:
    print("\n🔴 PRIMARY ISSUE: STOPS TOO TIGHT!")
    print("  - Stops are <1.5x ATR, getting hit by normal volatility")
    print("  - Need to widen stops to 2.0-2.5x ATR or use volatility filter")
elif (df['atr'] / df['entry_price'] * 100).mean() > 2.0:
    print("\n🔴 PRIMARY ISSUE: EXCESSIVE VOLATILITY!")
    print("  - Dec 8-15 had very high ATR (>2%)")
    print("  - Fixed stop multipliers get overwhelmed in high volatility")
    print("  - Need to avoid trading during high volatility or widen stops")
else:
    print("\n🔴 PRIMARY ISSUE: LIMIT ORDER TIMING!")
    print("  - Limit orders are filling at suboptimal prices")
    print("  - Catching falling knives (LONG) or shorting into pumps (SHORT)")
    print("  - Consider using market orders or tighter limit offsets")

print("\n💡 SOLUTIONS:")
print("  1. Add VOLATILITY FILTER: Don't trade when ATR% > 2.5%")
print("  2. WIDEN STOPS: Use 2.0-2.5x ATR instead of 1.0-1.5x ATR")
print("  3. ADD CONFIRMATION: Wait 1-2 bars after RSI cross to confirm reversal")
print("  4. REDUCE POSITION SIZE: Use 5% instead of 10% during high volatility")
print("  5. ADD TREND FILTER: Don't trade against strong 20-50 bar trends")
