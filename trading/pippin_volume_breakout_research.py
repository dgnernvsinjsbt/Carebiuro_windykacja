#!/usr/bin/env python3
"""
PIPPIN Volume Breakout / ATR Expansion / Pump Chasing Research
Broad exploration of different approaches (not hundreds of variations)
"""

import pandas as pd
import numpy as np
from datetime import datetime

print("=" * 80)
print("PIPPIN VOLUME BREAKOUT RESEARCH")
print("=" * 80)

# Load data
df = pd.read_csv('pippin_7d_bingx.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print(f"\nData: {len(df)} candles ({df['timestamp'].iloc[0]} to {df['timestamp'].iloc[-1]})")
print(f"Duration: {(df['timestamp'].iloc[-1] - df['timestamp'].iloc[0]).days} days")

# Calculate indicators
print("\nCalculating indicators...")
df['tr'] = df[['high', 'low', 'close']].apply(
    lambda row: max(row['high'] - row['low'],
                    abs(row['high'] - row['close']),
                    abs(row['low'] - row['close'])), axis=1
)
df['atr_14'] = df['tr'].rolling(window=14).mean()
df['atr_avg_20'] = df['atr_14'].rolling(window=20).mean()
df['atr_ratio'] = df['atr_14'] / df['atr_avg_20']

df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
df['sma_50'] = df['close'].rolling(window=50).mean()

df['vol_ma_30'] = df['volume'].rolling(window=30).mean()
df['vol_ratio'] = df['volume'] / df['vol_ma_30']

df['body_pct'] = abs(df['close'] - df['open']) / df['open'] * 100
df['is_green'] = (df['close'] > df['open']).astype(int)

# Session filter (US session 14:00-21:00 UTC)
df['hour'] = df['timestamp'].dt.hour
df['is_us_session'] = ((df['hour'] >= 14) & (df['hour'] < 21)).astype(int)

# Recent high/low for breakout detection
df['high_20'] = df['high'].rolling(window=20).max()
df['low_20'] = df['low'].rolling(window=20).min()

df = df.dropna().reset_index(drop=True)

print(f"After indicators: {len(df)} candles")

# ============================================================================
# STRATEGY 1: TIGHT VOLUME BREAKOUT (Tight Filters - Outlier Hunter)
# ============================================================================
def test_tight_volume_breakout(df):
    """
    Volume >4x (not 3x) + Body >1% + ATR expansion + US session
    Target: Catch explosive moves with tight filters
    """
    print("\n" + "=" * 80)
    print("STRATEGY 1: TIGHT VOLUME BREAKOUT (Outlier Hunter)")
    print("=" * 80)

    trades = []
    for i in range(50, len(df)):
        row = df.iloc[i]

        # ENTRY FILTERS (ALL must be true)
        if row['vol_ratio'] < 4.0:  # Volume >4x (tighter than 3x)
            continue
        if row['body_pct'] < 1.0:  # Body >1% (significant move)
            continue
        if row['atr_ratio'] < 1.2:  # ATR expansion (volatility)
            continue
        if row['is_us_session'] == 0:  # US session only
            continue

        # Direction from candle
        if row['is_green']:
            direction = 'LONG'
            entry_price = row['close']
        else:
            direction = 'SHORT'
            entry_price = row['close']

        # Exits
        atr = row['atr_14']
        if direction == 'LONG':
            stop_loss = entry_price - (1.0 * atr)
            take_profit = entry_price + (3.0 * atr)  # 3:1 R:R
        else:
            stop_loss = entry_price + (1.0 * atr)
            take_profit = entry_price - (3.0 * atr)

        # Simulate trade
        exit_price = None
        exit_reason = None
        for j in range(1, 61):  # Max 60 bars (1 hour)
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
            'vol_ratio': row['vol_ratio'],
            'body_pct': row['body_pct'],
            'atr_ratio': row['atr_ratio']
        })

    if len(trades) == 0:
        print("⚠️  No trades generated (filters too tight)")
        return None

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
    print(f"  Trades: {len(tdf)}")
    print(f"  Return: {total_return:+.2f}%")
    print(f"  Max DD: {max_dd:.2f}%")
    print(f"  Return/DD: {return_dd:.2f}x")
    print(f"  Win Rate: {win_rate:.1f}%")
    print(f"  Avg Win: {avg_win:+.2f}%")
    print(f"  Avg Loss: {avg_loss:.2f}%")
    print(f"\nExit Breakdown:")
    print(f"  {tdf['exit_reason'].value_counts().to_dict()}")

    return {
        'name': 'Tight Volume Breakout',
        'trades': len(tdf),
        'return': total_return,
        'max_dd': max_dd,
        'return_dd': return_dd,
        'win_rate': win_rate
    }

# ============================================================================
# STRATEGY 2: FADE PUMPS (Contrarian - Opposite of Pump Chasing)
# ============================================================================
def test_fade_pumps(df):
    """
    SHORT after big up moves (>1.5% body green) with volume
    Based on finding: "After >2% body candle" → -0.085% next bar (fades)
    """
    print("\n" + "=" * 80)
    print("STRATEGY 2: FADE PUMPS (Contrarian)")
    print("=" * 80)

    trades = []
    for i in range(50, len(df)):
        row = df.iloc[i]

        # ENTRY: Big green candle with volume
        if row['is_green'] == 0:
            continue
        if row['body_pct'] < 1.5:  # Large body
            continue
        if row['vol_ratio'] < 2.0:  # Volume confirmation
            continue
        if row['is_us_session'] == 0:  # US session only
            continue

        # FADE: SHORT after pump
        direction = 'SHORT'
        entry_price = row['close']

        # Exits (tight - mean reversion is fast)
        atr = row['atr_14']
        stop_loss = entry_price + (1.5 * atr)  # Stop above pump
        take_profit = entry_price - (2.0 * atr)  # Take profit below

        # Simulate trade
        exit_price = None
        exit_reason = None
        for j in range(1, 31):  # Max 30 bars (30 minutes - quick fade)
            if i + j >= len(df):
                break
            bar = df.iloc[i + j]

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
        pnl_pct = (entry_price - exit_price) / entry_price
        pnl_pct -= 0.001  # 0.1% fees

        trades.append({
            'timestamp': row['timestamp'],
            'direction': direction,
            'entry': entry_price,
            'exit': exit_price,
            'exit_reason': exit_reason,
            'pnl_pct': pnl_pct * 100,
            'body_pct': row['body_pct'],
            'vol_ratio': row['vol_ratio']
        })

    if len(trades) == 0:
        print("⚠️  No trades generated (filters too tight)")
        return None

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
    print(f"  Trades: {len(tdf)}")
    print(f"  Return: {total_return:+.2f}%")
    print(f"  Max DD: {max_dd:.2f}%")
    print(f"  Return/DD: {return_dd:.2f}x")
    print(f"  Win Rate: {win_rate:.1f}%")
    print(f"  Avg Win: {avg_win:+.2f}%")
    print(f"  Avg Loss: {avg_loss:.2f}%")
    print(f"\nExit Breakdown:")
    print(f"  {tdf['exit_reason'].value_counts().to_dict()}")

    return {
        'name': 'Fade Pumps',
        'trades': len(tdf),
        'return': total_return,
        'max_dd': max_dd,
        'return_dd': return_dd,
        'win_rate': win_rate
    }

# ============================================================================
# STRATEGY 3: VOLUME BREAKOUT + PRICE BREAKOUT (Momentum Confirmation)
# ============================================================================
def test_volume_price_breakout(df):
    """
    Volume >3x + Price breaks 20-bar high/low + ATR expansion
    Combines volume and price momentum
    """
    print("\n" + "=" * 80)
    print("STRATEGY 3: VOLUME + PRICE BREAKOUT (Momentum Confirmation)")
    print("=" * 80)

    trades = []
    for i in range(50, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i-1]

        # ENTRY FILTERS
        if row['vol_ratio'] < 3.0:  # Volume spike
            continue
        if row['atr_ratio'] < 1.3:  # ATR expansion
            continue
        if row['is_us_session'] == 0:  # US session only
            continue

        # Price breakout detection
        if row['close'] > prev['high_20']:  # LONG: Break above 20-bar high
            direction = 'LONG'
            entry_price = row['close']
        elif row['close'] < prev['low_20']:  # SHORT: Break below 20-bar low
            direction = 'SHORT'
            entry_price = row['close']
        else:
            continue  # No breakout

        # Exits
        atr = row['atr_14']
        if direction == 'LONG':
            stop_loss = entry_price - (1.5 * atr)
            take_profit = entry_price + (3.0 * atr)  # 2:1 R:R
        else:
            stop_loss = entry_price + (1.5 * atr)
            take_profit = entry_price - (3.0 * atr)

        # Simulate trade
        exit_price = None
        exit_reason = None
        for j in range(1, 46):  # Max 45 bars
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
            'vol_ratio': row['vol_ratio'],
            'atr_ratio': row['atr_ratio']
        })

    if len(trades) == 0:
        print("⚠️  No trades generated (filters too tight)")
        return None

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
    print(f"  Trades: {len(tdf)}")
    print(f"  Return: {total_return:+.2f}%")
    print(f"  Max DD: {max_dd:.2f}%")
    print(f"  Return/DD: {return_dd:.2f}x")
    print(f"  Win Rate: {win_rate:.1f}%")
    print(f"  Avg Win: {avg_win:+.2f}%")
    print(f"  Avg Loss: {avg_loss:.2f}%")
    print(f"\nExit Breakdown:")
    print(f"  {tdf['exit_reason'].value_counts().to_dict()}")

    return {
        'name': 'Volume + Price Breakout',
        'trades': len(tdf),
        'return': total_return,
        'max_dd': max_dd,
        'return_dd': return_dd,
        'win_rate': win_rate
    }

# ============================================================================
# RUN ALL TESTS
# ============================================================================

results = []

# Test 1: Tight Volume Breakout
r1 = test_tight_volume_breakout(df)
if r1:
    results.append(r1)

# Test 2: Fade Pumps
r2 = test_fade_pumps(df)
if r2:
    results.append(r2)

# Test 3: Volume + Price Breakout
r3 = test_volume_price_breakout(df)
if r3:
    results.append(r3)

# ============================================================================
# SUMMARY
# ============================================================================

print("\n" + "=" * 80)
print("SUMMARY - VOLUME BREAKOUT RESEARCH")
print("=" * 80)

if len(results) == 0:
    print("\n⚠️  No strategies generated trades")
else:
    print(f"\nTested {len(results)} strategies:\n")

    # Sort by Return/DD
    results_sorted = sorted(results, key=lambda x: x['return_dd'], reverse=True)

    print("| Rank | Strategy | Trades | Return | Max DD | Return/DD | Win Rate |")
    print("|------|----------|--------|--------|--------|-----------|----------|")

    for idx, r in enumerate(results_sorted, 1):
        emoji = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else "  "
        print(f"| {emoji} {idx} | {r['name']:<25} | {r['trades']:>6} | {r['return']:>+6.2f}% | {r['max_dd']:>6.2f}% | {r['return_dd']:>9.2f}x | {r['win_rate']:>7.1f}% |")

    print("\n" + "=" * 80)

    # Best strategy analysis
    best = results_sorted[0]
    print(f"\n🏆 BEST STRATEGY: {best['name']}")
    print(f"   Return/DD: {best['return_dd']:.2f}x")
    print(f"   Return: {best['return']:+.2f}%")
    print(f"   Win Rate: {best['win_rate']:.1f}%")
    print(f"   Trades: {best['trades']}")

    if best['return_dd'] >= 3.0:
        print(f"\n   ✅ VIABLE - Return/DD > 3.0x")
        print(f"   Recommendation: Test on 30-day data for validation")
    elif best['return_dd'] >= 2.0:
        print(f"\n   ⚠️  MARGINAL - Return/DD 2-3x")
        print(f"   Recommendation: Optimize filters or abandon")
    else:
        print(f"\n   ❌ NOT VIABLE - Return/DD < 2.0x")
        print(f"   Recommendation: PIPPIN may not be suitable for volume breakout strategies")

print("\n" + "=" * 80)
print("Research complete!")
print("=" * 80)
