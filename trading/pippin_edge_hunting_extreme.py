#!/usr/bin/env python3
"""
PIPPIN Edge Hunting - Life or Death Edition
If my life depended on finding an edge, I would:
1. Exploit hour-based statistical bias (18:00 long, 23:00 short)
2. Stack multiple weak edges (BB + hour + session + volume)
3. Ultra-short scalping (5-10 bar max hold)
4. Extreme outlier hunting (only trade after big moves)
5. Mean reversion on steroids (multiple confirmation)
"""

import pandas as pd
import numpy as np
from datetime import datetime

print("=" * 80)
print("PIPPIN EDGE HUNTING - EXTREME MODE")
print("If my life depended on it, how would I trade this?")
print("=" * 80)

# Load data
df = pd.read_csv('pippin_7d_bingx.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print(f"\nData: {len(df)} candles ({df['timestamp'].iloc[0]} to {df['timestamp'].iloc[-1]})")

# Calculate ALL indicators
print("\nCalculating indicators...")
df['tr'] = df[['high', 'low', 'close']].apply(
    lambda row: max(row['high'] - row['low'],
                    abs(row['high'] - row['close']),
                    abs(row['low'] - row['close'])), axis=1
)
df['atr_14'] = df['tr'].rolling(window=14).mean()

# Bollinger Bands
df['sma_20'] = df['close'].rolling(window=20).mean()
df['std_20'] = df['close'].rolling(window=20).std()
df['bb_upper'] = df['sma_20'] + 2 * df['std_20']
df['bb_lower'] = df['sma_20'] - 2 * df['std_20']

# RSI
delta = df['close'].diff()
gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
rs = gain / loss
df['rsi'] = 100 - (100 / (1 + rs))

# Volume
df['vol_ma_30'] = df['volume'].rolling(window=30).mean()
df['vol_ratio'] = df['volume'] / df['vol_ma_30']

# Consecutive patterns
df['is_green'] = (df['close'] > df['open']).astype(int)
df['is_red'] = (df['close'] < df['open']).astype(int)

# Count consecutive reds/greens
consecutive_reds = []
consecutive_greens = []
red_count = 0
green_count = 0

for i in range(len(df)):
    if df.iloc[i]['is_red']:
        red_count += 1
        green_count = 0
    elif df.iloc[i]['is_green']:
        green_count += 1
        red_count = 0
    else:
        red_count = 0
        green_count = 0

    consecutive_reds.append(red_count)
    consecutive_greens.append(green_count)

df['consecutive_reds'] = consecutive_reds
df['consecutive_greens'] = consecutive_greens

# Hour and session
df['hour'] = df['timestamp'].dt.hour
df['is_us_session'] = ((df['hour'] >= 14) & (df['hour'] < 21)).astype(int)

# Body size
df['body_pct'] = abs(df['close'] - df['open']) / df['open'] * 100

# Recent high/low
df['high_5'] = df['high'].rolling(window=5).max()
df['low_5'] = df['low'].rolling(window=5).min()

df = df.dropna().reset_index(drop=True)

print(f"After indicators: {len(df)} candles")

# ============================================================================
# STRATEGY 1: TIME-BASED STATISTICAL EDGE (Pure Hour Bias)
# ============================================================================
def test_hour_bias_strategy(df):
    """
    Exploit hour-based statistical bias:
    - 18:00 UTC: +0.102% avg (LONG)
    - 23:00 UTC: -0.037% avg (SHORT)

    Pure statistical play - no indicators needed
    """
    print("\n" + "=" * 80)
    print("STRATEGY 1: TIME-BASED STATISTICAL EDGE")
    print("=" * 80)
    print("Logic: Trade hour 18 LONG, hour 23 SHORT - pure statistics")

    trades = []

    for i in range(50, len(df)):
        row = df.iloc[i]

        # LONG at 18:00 UTC (best hour +0.102%)
        if row['hour'] == 18:
            direction = 'LONG'
            entry_price = row['close']
            atr = row['atr_14']
            stop_loss = entry_price - (0.5 * atr)  # Tight stop
            take_profit = entry_price + (1.0 * atr)  # 2:1 R:R
            max_hold = 10  # 10 bars = 10 minutes (scalp)

        # SHORT at 23:00 UTC (worst hour -0.037%)
        elif row['hour'] == 23:
            direction = 'SHORT'
            entry_price = row['close']
            atr = row['atr_14']
            stop_loss = entry_price + (0.5 * atr)
            take_profit = entry_price - (1.0 * atr)
            max_hold = 10
        else:
            continue

        # Simulate trade
        exit_price = None
        exit_reason = None
        for j in range(1, max_hold + 1):
            if i + j >= len(df):
                break
            bar = df.iloc[i + j]

            if direction == 'LONG':
                if bar['low'] <= stop_loss:
                    exit_price = stop_loss
                    exit_reason = 'SL'
                    break
                elif bar['high'] >= take_profit:
                    exit_price = take_profit
                    exit_reason = 'TP'
                    break
            else:  # SHORT
                if bar['high'] >= stop_loss:
                    exit_price = stop_loss
                    exit_reason = 'SL'
                    break
                elif bar['low'] <= take_profit:
                    exit_price = take_profit
                    exit_reason = 'TP'
                    break

        if exit_price is None:
            exit_price = df.iloc[i + j]['close']
            exit_reason = 'TIME'

        # Calculate P&L
        if direction == 'LONG':
            pnl_pct = (exit_price - entry_price) / entry_price
        else:
            pnl_pct = (entry_price - exit_price) / entry_price

        pnl_pct -= 0.001  # 0.1% fees

        trades.append({
            'timestamp': row['timestamp'],
            'hour': row['hour'],
            'direction': direction,
            'entry': entry_price,
            'exit': exit_price,
            'exit_reason': exit_reason,
            'pnl_pct': pnl_pct * 100
        })

    if len(trades) == 0:
        print("⚠️  No trades generated")
        return None

    return analyze_results(trades, "Time-Based Statistical Edge")

# ============================================================================
# STRATEGY 2: STACKED EDGES (Combine Multiple Weak Signals)
# ============================================================================
def test_stacked_edges(df):
    """
    Stack ALL weak edges:
    - BB lower touch (60.1% reversion)
    - Hour 18 (best hour)
    - US session (best session)
    - Volume confirmation
    - RSI < 35 (oversold)

    If ALL conditions align, edge compounds
    """
    print("\n" + "=" * 80)
    print("STRATEGY 2: STACKED EDGES (Compound Weak Signals)")
    print("=" * 80)
    print("Logic: BB lower + hour 18 + US session + volume + RSI")

    trades = []

    for i in range(50, len(df)):
        row = df.iloc[i]

        # LONG: Stack all bullish edges
        if (row['close'] <= row['bb_lower'] and  # BB lower touch
            row['hour'] == 18 and                # Best hour
            row['is_us_session'] == 1 and        # US session
            row['vol_ratio'] >= 1.2 and          # Volume confirmation
            row['rsi'] < 35):                    # Oversold

            direction = 'LONG'
            entry_price = row['close']
            atr = row['atr_14']
            stop_loss = entry_price - (0.4 * atr)  # Very tight
            take_profit = entry_price + (1.2 * atr)  # 3:1 R:R
            max_hold = 20

        else:
            continue

        # Simulate trade
        exit_price = None
        exit_reason = None
        for j in range(1, max_hold + 1):
            if i + j >= len(df):
                break
            bar = df.iloc[i + j]

            if bar['low'] <= stop_loss:
                exit_price = stop_loss
                exit_reason = 'SL'
                break
            elif bar['high'] >= take_profit:
                exit_price = take_profit
                exit_reason = 'TP'
                break

        if exit_price is None:
            exit_price = df.iloc[i + j]['close']
            exit_reason = 'TIME'

        # Calculate P&L
        pnl_pct = ((exit_price - entry_price) / entry_price) - 0.001

        trades.append({
            'timestamp': row['timestamp'],
            'direction': direction,
            'entry': entry_price,
            'exit': exit_price,
            'exit_reason': exit_reason,
            'pnl_pct': pnl_pct * 100,
            'rsi': row['rsi'],
            'vol_ratio': row['vol_ratio']
        })

    if len(trades) == 0:
        print("⚠️  No trades generated (filters too tight)")
        return None

    return analyze_results(trades, "Stacked Edges")

# ============================================================================
# STRATEGY 3: ULTRA-SHORT SCALP (5-Bar Max)
# ============================================================================
def test_ultra_short_scalp(df):
    """
    Extreme short-term mean reversion:
    - Enter after 3 consecutive reds OR BB lower
    - Exit after 5 bars MAX (chop decays fast)
    - Target: 0.3-0.5% gains (tiny but frequent)
    """
    print("\n" + "=" * 80)
    print("STRATEGY 3: ULTRA-SHORT SCALP (5-Bar Max)")
    print("=" * 80)
    print("Logic: Mean reversion + 5-bar forced exit")

    trades = []

    for i in range(50, len(df)):
        row = df.iloc[i]

        # LONG after exhaustion
        if (row['consecutive_reds'] >= 3 or row['close'] <= row['bb_lower']) and row['is_us_session'] == 1:
            direction = 'LONG'
            entry_price = row['close']
            atr = row['atr_14']
            stop_loss = entry_price - (0.3 * atr)  # Extremely tight
            take_profit = entry_price + (0.5 * atr)  # Small gain
            max_hold = 5  # FORCE EXIT after 5 bars

        # SHORT after exhaustion
        elif (row['consecutive_greens'] >= 3 or row['close'] >= row['bb_upper']) and row['is_us_session'] == 1:
            direction = 'SHORT'
            entry_price = row['close']
            atr = row['atr_14']
            stop_loss = entry_price + (0.3 * atr)
            take_profit = entry_price - (0.5 * atr)
            max_hold = 5
        else:
            continue

        # Simulate trade
        exit_price = None
        exit_reason = None
        for j in range(1, max_hold + 1):
            if i + j >= len(df):
                break
            bar = df.iloc[i + j]

            if direction == 'LONG':
                if bar['low'] <= stop_loss:
                    exit_price = stop_loss
                    exit_reason = 'SL'
                    break
                elif bar['high'] >= take_profit:
                    exit_price = take_profit
                    exit_reason = 'TP'
                    break
            else:  # SHORT
                if bar['high'] >= stop_loss:
                    exit_price = stop_loss
                    exit_reason = 'SL'
                    break
                elif bar['low'] <= take_profit:
                    exit_price = take_profit
                    exit_reason = 'TP'
                    break

        if exit_price is None:
            exit_price = df.iloc[i + j]['close']
            exit_reason = 'TIME'

        # Calculate P&L
        if direction == 'LONG':
            pnl_pct = (exit_price - entry_price) / entry_price
        else:
            pnl_pct = (entry_price - exit_price) / entry_price

        pnl_pct -= 0.001  # 0.1% fees

        trades.append({
            'timestamp': row['timestamp'],
            'direction': direction,
            'entry': entry_price,
            'exit': exit_price,
            'exit_reason': exit_reason,
            'pnl_pct': pnl_pct * 100
        })

    if len(trades) == 0:
        print("⚠️  No trades generated")
        return None

    return analyze_results(trades, "Ultra-Short Scalp")

# ============================================================================
# STRATEGY 4: EXTREME REVERSAL (After Big Moves Only)
# ============================================================================
def test_extreme_reversal(df):
    """
    Only trade after extreme moves:
    - After >2% up move: SHORT
    - After >2% down move: LONG
    - Pattern shows: after >2% body → -0.085% next bar (fade)
    - Tight stop, quick exit
    """
    print("\n" + "=" * 80)
    print("STRATEGY 4: EXTREME REVERSAL (After >2% Moves)")
    print("=" * 80)
    print("Logic: Fade big moves (pattern: -0.085% after >2% body)")

    trades = []

    for i in range(50, len(df)):
        row = df.iloc[i]

        # SHORT after big up move
        if row['body_pct'] >= 2.0 and row['is_green'] and row['is_us_session'] == 1:
            direction = 'SHORT'
            entry_price = row['close']
            atr = row['atr_14']
            stop_loss = entry_price + (1.0 * atr)
            take_profit = entry_price - (1.5 * atr)  # 1.5:1 R:R
            max_hold = 15

        # LONG after big down move
        elif row['body_pct'] >= 2.0 and row['is_red'] and row['is_us_session'] == 1:
            direction = 'LONG'
            entry_price = row['close']
            atr = row['atr_14']
            stop_loss = entry_price - (1.0 * atr)
            take_profit = entry_price + (1.5 * atr)
            max_hold = 15
        else:
            continue

        # Simulate trade
        exit_price = None
        exit_reason = None
        for j in range(1, max_hold + 1):
            if i + j >= len(df):
                break
            bar = df.iloc[i + j]

            if direction == 'LONG':
                if bar['low'] <= stop_loss:
                    exit_price = stop_loss
                    exit_reason = 'SL'
                    break
                elif bar['high'] >= take_profit:
                    exit_price = take_profit
                    exit_reason = 'TP'
                    break
            else:  # SHORT
                if bar['high'] >= stop_loss:
                    exit_price = stop_loss
                    exit_reason = 'SL'
                    break
                elif bar['low'] <= take_profit:
                    exit_price = take_profit
                    exit_reason = 'TP'
                    break

        if exit_price is None:
            exit_price = df.iloc[i + j]['close']
            exit_reason = 'TIME'

        # Calculate P&L
        if direction == 'LONG':
            pnl_pct = (exit_price - entry_price) / entry_price
        else:
            pnl_pct = (entry_price - exit_price) / entry_price

        pnl_pct -= 0.001  # 0.1% fees

        trades.append({
            'timestamp': row['timestamp'],
            'direction': direction,
            'entry': entry_price,
            'exit': exit_price,
            'exit_reason': exit_reason,
            'pnl_pct': pnl_pct * 100,
            'body_pct': row['body_pct']
        })

    if len(trades) == 0:
        print("⚠️  No trades generated")
        return None

    return analyze_results(trades, "Extreme Reversal")

# ============================================================================
# ANALYSIS HELPER
# ============================================================================
def analyze_results(trades, strategy_name):
    """Calculate performance metrics"""
    tdf = pd.DataFrame(trades)

    # Calculate metrics
    equity = 10000
    equity_curve = [equity]
    for pnl in tdf['pnl_pct']:
        equity *= (1 + pnl / 100)
        equity_curve.append(equity)

    total_return = (equity - 10000) / 100
    running_max = np.maximum.accumulate(equity_curve)
    drawdown = (np.array(equity_curve) - running_max) / running_max * 100
    max_dd = drawdown.min()
    return_dd = total_return / abs(max_dd) if max_dd != 0 else 0

    win_rate = (tdf['pnl_pct'] > 0).sum() / len(tdf) * 100
    avg_win = tdf[tdf['pnl_pct'] > 0]['pnl_pct'].mean() if (tdf['pnl_pct'] > 0).any() else 0
    avg_loss = tdf[tdf['pnl_pct'] <= 0]['pnl_pct'].mean() if (tdf['pnl_pct'] <= 0).any() else 0

    print(f"\nResults:")
    print(f"  Trades: {len(tdf)} ({len(tdf)/7:.1f}/day)")
    print(f"  Return: {total_return:+.2f}%")
    print(f"  Max DD: {max_dd:.2f}%")
    print(f"  Return/DD: {return_dd:.2f}x")
    print(f"  Win Rate: {win_rate:.1f}%")
    print(f"  Avg Win: {avg_win:+.2f}%")
    print(f"  Avg Loss: {avg_loss:.2f}%")
    print(f"  Exit breakdown: {tdf['exit_reason'].value_counts().to_dict()}")

    # Top 20% concentration
    tdf_sorted = tdf.sort_values('pnl_pct', ascending=False)
    top_20_pct_count = max(1, int(len(tdf) * 0.2))
    top_20_pct_pnl = tdf_sorted.head(top_20_pct_count)['pnl_pct'].sum()
    top_20_concentration = (top_20_pct_pnl / tdf['pnl_pct'].sum() * 100) if tdf['pnl_pct'].sum() != 0 else 0
    print(f"  Top 20% concentration: {top_20_concentration:.1f}%")

    return {
        'name': strategy_name,
        'trades': len(tdf),
        'trades_per_day': len(tdf) / 7,
        'return': total_return,
        'max_dd': max_dd,
        'return_dd': return_dd,
        'win_rate': win_rate,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'top20': top_20_concentration
    }

# ============================================================================
# RUN ALL STRATEGIES
# ============================================================================

results = []

# Test 1: Time-based
r1 = test_hour_bias_strategy(df)
if r1:
    results.append(r1)

# Test 2: Stacked edges
r2 = test_stacked_edges(df)
if r2:
    results.append(r2)

# Test 3: Ultra-short scalp
r3 = test_ultra_short_scalp(df)
if r3:
    results.append(r3)

# Test 4: Extreme reversal
r4 = test_extreme_reversal(df)
if r4:
    results.append(r4)

# ============================================================================
# SUMMARY
# ============================================================================

print("\n" + "=" * 80)
print("EXTREME EDGE HUNTING SUMMARY")
print("=" * 80)

if len(results) == 0:
    print("\n⚠️  No strategies generated trades")
else:
    # Sort by Return/DD
    results_sorted = sorted(results, key=lambda x: x['return_dd'], reverse=True)

    print(f"\nTested {len(results)} unconventional strategies:\n")
    print("| Rank | Strategy | Trades/Day | Return | Max DD | Return/DD | Win Rate |")
    print("|------|----------|-----------|--------|--------|-----------|----------|")

    for idx, r in enumerate(results_sorted, 1):
        emoji = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else "  "
        print(f"| {emoji} {idx} | {r['name']:<30} | {r['trades_per_day']:>9.1f} | {r['return']:>+6.2f}% | {r['max_dd']:>6.2f}% | {r['return_dd']:>9.2f}x | {r['win_rate']:>7.1f}% |")

    print("\n" + "=" * 80)

    # Best strategy
    best = results_sorted[0]
    print(f"\n🏆 BEST EDGE FOUND: {best['name']}")
    print(f"   Return/DD: {best['return_dd']:.2f}x")
    print(f"   Return: {best['return']:+.2f}%")
    print(f"   Win Rate: {best['win_rate']:.1f}%")
    print(f"   Trades: {best['trades']} ({best['trades_per_day']:.1f}/day)")
    print(f"   Top 20%: {best['top20']:.1f}%")

    if best['return_dd'] >= 3.0:
        print(f"\n   ✅ VIABLE EDGE FOUND!")
        print(f"   This approach has sufficient risk-adjusted returns")
        print(f"   Recommendation: Test on 30-day data immediately")
    elif best['return_dd'] >= 2.0:
        print(f"\n   ⚠️  MARGINAL EDGE")
        print(f"   Close to viability - may work with optimization")
    else:
        print(f"\n   ❌ Still not enough")
        print(f"   Even extreme approaches struggle on PIPPIN")

print("\n" + "=" * 80)
print("Analysis complete - these are the BEST possible edges I can find")
print("=" * 80)
