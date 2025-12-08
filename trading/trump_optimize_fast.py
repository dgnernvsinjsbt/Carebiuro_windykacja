"""
TRUMP Strategy - Fast Optimization
Test key parameters quickly
"""

import pandas as pd
import numpy as np

# Load data
print("Loading data...")
data = pd.read_csv('trump_usdt_1m_mexc.csv')

# Calculate basic indicators
data['rsi'] = 0.0
delta = pd.Series(data['close']).diff()
gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
rs = gain / loss
data['rsi'] = 100 - (100 / (1 + rs))

# ATR
high_low = data['high'] - data['low']
high_close = abs(data['high'] - data['close'].shift())
low_close = abs(data['low'] - data['close'].shift())
ranges = pd.concat([high_low, high_close, low_close], axis=1)
true_range = ranges.max(axis=1)
data['atr'] = true_range.rolling(14).mean()
data['atr_pct'] = (data['atr'] / data['close']) * 100

data['timestamp'] = pd.to_datetime(data['timestamp'])
data['hour'] = data['timestamp'].dt.hour

print("="*80)
print("TRUMP FAST OPTIMIZATION")
print("="*80)

results = []

# ============================================================================
# Test 1: Different SL/TP Ratios
# ============================================================================
print("\n1. SL/TP RATIO TEST (RSI < 30, US Session)")
print("-"*80)

configs = [
    (1.0, 2.0),  # 1:2 R:R
    (1.5, 3.0),  # 1:2 R:R
    (2.0, 4.0),  # 1:2 R:R
    (2.0, 6.0),  # 1:3 R:R
    (3.0, 9.0),  # 1:3 R:R
]

for sl_mult, tp_mult in configs:
    capital = 10000
    trades = []

    for i in range(200, len(data), 5):  # Sample every 5th candle for speed
        row = data.iloc[i]

        if pd.isna(row['rsi']) or pd.isna(row['atr_pct']):
            continue

        # Entry: RSI < 30, US session
        if row['rsi'] < 30 and 14 <= row['hour'] < 21:
            entry = row['close']
            atr = row['atr_pct'] / 100

            sl = entry * (1 - sl_mult * atr)
            tp = entry * (1 + tp_mult * atr)

            # Look ahead max 30 candles
            for j in range(i+1, min(i+31, len(data))):
                future = data.iloc[j]

                if future['low'] <= sl:
                    pnl_pct = ((sl - entry) / entry) * 100 - 0.1  # fees
                    trades.append(pnl_pct)
                    break
                elif future['high'] >= tp:
                    pnl_pct = ((tp - entry) / entry) * 100 - 0.1  # fees
                    trades.append(pnl_pct)
                    break

    if len(trades) > 0:
        win_rate = (np.array(trades) > 0).sum() / len(trades) * 100
        total_return = np.sum(trades)
        avg_trade = np.mean(trades)

        print(f"SL {sl_mult}x / TP {tp_mult}x | Trades: {len(trades):>3} | WR: {win_rate:>5.1f}% | Ret: {total_return:>6.2f}% | Avg: {avg_trade:>6.3f}%")

        results.append({
            'config': f'SL{sl_mult}_TP{tp_mult}',
            'sl': sl_mult,
            'tp': tp_mult,
            'trades': len(trades),
            'win_rate': win_rate,
            'return': total_return
        })

# ============================================================================
# Test 2: Session Filters
# ============================================================================
print("\n\n2. SESSION FILTER TEST (RSI < 30, SL 2x / TP 4x)")
print("-"*80)

sessions = [
    ('Asia', 0, 8),
    ('Europe', 8, 14),
    ('US', 14, 21),
    ('Overnight', 21, 24),
    ('All Day', 0, 24)
]

for session_name, hour_start, hour_end in sessions:
    trades = []

    for i in range(200, len(data), 5):
        row = data.iloc[i]

        if pd.isna(row['rsi']) or pd.isna(row['atr_pct']):
            continue

        # Entry: RSI < 30, specific session
        if row['rsi'] < 30 and hour_start <= row['hour'] < hour_end:
            entry = row['close']
            atr = row['atr_pct'] / 100

            sl = entry * (1 - 2.0 * atr)
            tp = entry * (1 + 4.0 * atr)

            for j in range(i+1, min(i+31, len(data))):
                future = data.iloc[j]

                if future['low'] <= sl:
                    pnl_pct = ((sl - entry) / entry) * 100 - 0.1
                    trades.append(pnl_pct)
                    break
                elif future['high'] >= tp:
                    pnl_pct = ((tp - entry) / entry) * 100 - 0.1
                    trades.append(pnl_pct)
                    break

    if len(trades) > 0:
        win_rate = (np.array(trades) > 0).sum() / len(trades) * 100
        total_return = np.sum(trades)

        print(f"{session_name:12} | Trades: {len(trades):>3} | WR: {win_rate:>5.1f}% | Return: {total_return:>6.2f}%")

        results.append({
            'config': f'Session_{session_name}',
            'trades': len(trades),
            'win_rate': win_rate,
            'return': total_return
        })

# ============================================================================
# Test 3: RSI Threshold Variations
# ============================================================================
print("\n\n3. RSI THRESHOLD TEST (US Session, SL 2x / TP 4x)")
print("-"*80)

rsi_thresholds = [20, 25, 30, 35, 40]

for rsi_thresh in rsi_thresholds:
    trades = []

    for i in range(200, len(data), 5):
        row = data.iloc[i]

        if pd.isna(row['rsi']) or pd.isna(row['atr_pct']):
            continue

        if row['rsi'] < rsi_thresh and 14 <= row['hour'] < 21:
            entry = row['close']
            atr = row['atr_pct'] / 100

            sl = entry * (1 - 2.0 * atr)
            tp = entry * (1 + 4.0 * atr)

            for j in range(i+1, min(i+31, len(data))):
                future = data.iloc[j]

                if future['low'] <= sl:
                    pnl_pct = ((sl - entry) / entry) * 100 - 0.1
                    trades.append(pnl_pct)
                    break
                elif future['high'] >= tp:
                    pnl_pct = ((tp - entry) / entry) * 100 - 0.1
                    trades.append(pnl_pct)
                    break

    if len(trades) > 0:
        win_rate = (np.array(trades) > 0).sum() / len(trades) * 100
        total_return = np.sum(trades)

        print(f"RSI < {rsi_thresh:>2} | Trades: {len(trades):>3} | WR: {win_rate:>5.1f}% | Return: {total_return:>6.2f}%")

        results.append({
            'config': f'RSI<{rsi_thresh}',
            'rsi_threshold': rsi_thresh,
            'trades': len(trades),
            'win_rate': win_rate,
            'return': total_return
        })

# ============================================================================
# FINAL SUMMARY
# ============================================================================
print("\n\n" + "="*80)
print("OPTIMIZATION SUMMARY")
print("="*80)

if len(results) > 0:
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('return', ascending=False)

    print("\nTop 5 Configurations:")
    print("-"*80)
    print(f"{'Config':<20} {'Trades':<8} {'Win Rate':<10} {'Return':<10}")
    print("-"*80)

    for _, row in results_df.head(5).iterrows():
        print(f"{row['config']:<20} {row['trades']:<8.0f} {row['win_rate']:<10.1f} {row['return']:<10.2f}%")

    best = results_df.iloc[0]

    print(f"\n✓ Best Configuration: {best['config']}")
    print(f"  Return: {best['return']:.2f}%")
    print(f"  Win Rate: {best['win_rate']:.1f}%")
    print(f"  Trades: {best['trades']:.0f}")

    if best['return'] > 0:
        print("\n✅ TRUMP IS TRADEABLE with optimized parameters")
    else:
        print("\n❌ TRUMP REMAINS UNPROFITABLE - Consider skipping this token")

    # Save
    results_df.to_csv('results/TRUMP_optimization_comparison.csv', index=False)
    print("\nResults saved to: results/TRUMP_optimization_comparison.csv")
else:
    print("\n❌ No valid configurations found")

print("="*80)
