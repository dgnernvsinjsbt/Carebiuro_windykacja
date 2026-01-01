"""
Alternative overfitting test: Cross-coin validation

Instead of walk-forward in time, test if optimal parameters are:
1. Coin-specific (robust) vs time-specific (overfitted)
2. Consistent across different sub-periods

Test: Take MOODENG optimal params (30/65, 1%, 2x, 1x, 3h) and apply to:
- PEPE (should use different params: 25/70, 0.5%, 2x, 2x, 3h)
- DOGE (should use different params: 27/68, 1.5%, 2x, 1.5x, 4h)
- If MOODENG params work poorly on PEPE/DOGE → optimization found real coin differences
- If MOODENG params work equally well everywhere → overfitted to time period

Also test: Does the strategy work on different sub-periods of the same data?
"""

import pandas as pd
import numpy as np

print("=" * 80)
print("CROSS-VALIDATION TEST: Are parameters coin-specific or time-specific?")
print("=" * 80)

def calculate_indicators(df):
    delta = df['close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))

    df['tr'] = np.maximum(
        df['high'] - df['low'],
        np.maximum(
            abs(df['high'] - df['close'].shift(1)),
            abs(df['low'] - df['close'].shift(1))
        )
    )
    df['atr'] = df['tr'].rolling(14).mean()
    return df

def backtest_rsi(df, rsi_low, rsi_high, limit_pct, sl_mult, tp_mult, max_hold):
    trades = []
    equity = 100.0
    equity_curve = [equity]

    i = 14
    while i < len(df):
        row = df.iloc[i]
        if pd.isna(row['rsi']) or pd.isna(row['atr']):
            i += 1
            continue

        direction = None
        if row['rsi'] < rsi_low:
            direction = 'LONG'
        elif row['rsi'] > rsi_high:
            direction = 'SHORT'

        if direction is None:
            i += 1
            continue

        if direction == 'LONG':
            entry_price = row['close'] * (1 + limit_pct / 100)
            sl_price = entry_price - (row['atr'] * sl_mult)
            tp_price = entry_price + (row['atr'] * tp_mult)

            filled = False
            fill_idx = None
            for j in range(i + 1, min(i + 4, len(df))):
                if df.iloc[j]['low'] <= entry_price:
                    filled = True
                    fill_idx = j
                    break

            if not filled:
                i += 1
                continue

            exit_idx = None
            exit_price = None
            exit_type = 'TIME'

            for k in range(fill_idx + 1, min(fill_idx + max_hold + 1, len(df))):
                bar = df.iloc[k]
                if bar['low'] <= sl_price:
                    exit_idx, exit_price, exit_type = k, sl_price, 'SL'
                    break
                if bar['high'] >= tp_price:
                    exit_idx, exit_price, exit_type = k, tp_price, 'TP'
                    break

            if exit_idx is None:
                exit_idx = min(fill_idx + max_hold, len(df) - 1)
                exit_price = df.iloc[exit_idx]['close']

            pnl_pct = ((exit_price - entry_price) / entry_price) * 100 - 0.10
            equity += equity * (pnl_pct / 100)
            trades.append({'pnl_pct': pnl_pct, 'exit_type': exit_type, 'equity': equity})
            equity_curve.append(equity)
            i = exit_idx + 1

        elif direction == 'SHORT':
            entry_price = row['close'] * (1 - limit_pct / 100)
            sl_price = entry_price + (row['atr'] * sl_mult)
            tp_price = entry_price - (row['atr'] * tp_mult)

            filled = False
            fill_idx = None
            for j in range(i + 1, min(i + 4, len(df))):
                if df.iloc[j]['high'] >= entry_price:
                    filled = True
                    fill_idx = j
                    break

            if not filled:
                i += 1
                continue

            exit_idx = None
            exit_price = None
            exit_type = 'TIME'

            for k in range(fill_idx + 1, min(fill_idx + max_hold + 1, len(df))):
                bar = df.iloc[k]
                if bar['high'] >= sl_price:
                    exit_idx, exit_price, exit_type = k, sl_price, 'SL'
                    break
                if bar['low'] <= tp_price:
                    exit_idx, exit_price, exit_type = k, tp_price, 'TP'
                    break

            if exit_idx is None:
                exit_idx = min(fill_idx + max_hold, len(df) - 1)
                exit_price = df.iloc[exit_idx]['close']

            pnl_pct = ((entry_price - exit_price) / entry_price) * 100 - 0.10
            equity += equity * (pnl_pct / 100)
            trades.append({'pnl_pct': pnl_pct, 'exit_type': exit_type, 'equity': equity})
            equity_curve.append(equity)
            i = exit_idx + 1

        else:
            i += 1

    if len(trades) == 0:
        return None

    df_t = pd.DataFrame(trades)
    ret = ((equity_curve[-1] - 100) / 100) * 100
    eq = pd.Series(equity_curve)
    dd = ((eq - eq.expanding().max()) / eq.expanding().max() * 100).min()
    wr = (df_t['pnl_pct'] > 0).sum() / len(df_t) * 100
    slr = (df_t['exit_type'] == 'SL').sum() / len(df_t) * 100

    return {
        'return': ret,
        'max_dd': dd,
        'return_dd': ret / abs(dd) if dd != 0 else 0,
        'trades': len(df_t),
        'win_rate': wr,
        'sl_rate': slr
    }

# Test 1: MOODENG params on MOODENG coin (should work - optimized for it)
print("\n" + "=" * 80)
print("TEST 1: MOODENG optimal params (30/65) on MOODENG coin")
print("=" * 80)

df_moodeng = pd.read_csv('bingx-trading-bot/trading/moodeng_usdt_90d_1h.csv', parse_dates=['timestamp'])
df_moodeng = df_moodeng.sort_values('timestamp').reset_index(drop=True)
df_moodeng = df_moodeng[(df_moodeng['timestamp'] >= '2025-09-15') & (df_moodeng['timestamp'] < '2025-12-08')].reset_index(drop=True)
df_moodeng = calculate_indicators(df_moodeng)

print(f"Data: {len(df_moodeng)} bars (Sep 15 - Dec 7)")

result_moodeng_on_moodeng = backtest_rsi(df_moodeng, 30, 65, 1.0, 2.0, 1.0, 3)

if result_moodeng_on_moodeng:
    r = result_moodeng_on_moodeng
    print(f"Return: {r['return']:+.2f}% | DD: {r['max_dd']:.2f}% | R/DD: {r['return_dd']:.2f}x")
    print(f"Trades: {r['trades']} | Win: {r['win_rate']:.1f}% | SL: {r['sl_rate']:.1f}%")
    print("✅ Expected: +26.96% (baseline from optimization)")

# Test 2: MOODENG params on DIFFERENT coins (should work WORSE if not overfitted)
# Load other coin data and test
try:
    print("\n" + "=" * 80)
    print("TEST 2: MOODENG params (30/65) on PEPE coin (expects: 25/70 instead)")
    print("=" * 80)

    df_pepe = pd.read_csv('bingx-trading-bot/trading/pepe_usdt_90d_1h.csv', parse_dates=['timestamp'])
    df_pepe = df_pepe.sort_values('timestamp').reset_index(drop=True)
    df_pepe = df_pepe[(df_pepe['timestamp'] >= '2025-09-15') & (df_pepe['timestamp'] < '2025-12-08')].reset_index(drop=True)
    df_pepe = calculate_indicators(df_pepe)

    print(f"Data: {len(df_pepe)} bars (Sep 15 - Dec 7)")

    # Test with MOODENG params (wrong for PEPE)
    result_moodeng_on_pepe = backtest_rsi(df_pepe, 30, 65, 1.0, 2.0, 1.0, 3)

    # Test with PEPE's own optimal params
    result_pepe_on_pepe = backtest_rsi(df_pepe, 25, 70, 0.5, 2.0, 2.0, 3)

    if result_moodeng_on_pepe and result_pepe_on_pepe:
        print("\nWith MOODENG params (30/65, 1%, 2x, 1x):")
        r1 = result_moodeng_on_pepe
        print(f"  Return: {r1['return']:+.2f}% | DD: {r1['max_dd']:.2f}% | R/DD: {r1['return_dd']:.2f}x")
        print(f"  Trades: {r1['trades']} | Win: {r1['win_rate']:.1f}%")

        print("\nWith PEPE's optimal params (25/70, 0.5%, 2x, 2x):")
        r2 = result_pepe_on_pepe
        print(f"  Return: {r2['return']:+.2f}% | DD: {r2['max_dd']:.2f}% | R/DD: {r2['return_dd']:.2f}x")
        print(f"  Trades: {r2['trades']} | Win: {r2['win_rate']:.1f}%")

        print(f"\n📊 PEPE params vs MOODENG params:")
        print(f"  Return difference: {r2['return'] - r1['return']:+.2f}%")
        print(f"  R/DD improvement: {r2['return_dd'] - r1['return_dd']:+.2f}x")

        if r2['return_dd'] > r1['return_dd'] * 1.2:
            print("\n✅ PEPE-specific params are 20%+ better → Optimization found real coin differences")
        elif r2['return_dd'] < r1['return_dd'] * 0.8:
            print("\n⚠️  MOODENG params work BETTER on PEPE → Suggests time-specific overfitting")
        else:
            print("\n≈ Similar performance → Parameters are somewhat robust")

except FileNotFoundError:
    print("\n❌ PEPE data file not found")

# Test 3: Split MOODENG data into 3 periods and test consistency
print("\n" + "=" * 80)
print("TEST 3: MOODENG params on different sub-periods (consistency check)")
print("=" * 80)

# Split Sep 15 - Dec 7 into 3 periods
df_full = pd.read_csv('bingx-trading-bot/trading/moodeng_usdt_90d_1h.csv', parse_dates=['timestamp'])
df_full = df_full.sort_values('timestamp').reset_index(drop=True)
df_full = df_full[(df_full['timestamp'] >= '2025-09-15') & (df_full['timestamp'] < '2025-12-08')].reset_index(drop=True)
df_full = calculate_indicators(df_full)

total_bars = len(df_full)
third = total_bars // 3

df_period1 = df_full.iloc[:third].reset_index(drop=True)
df_period2 = df_full.iloc[third:2*third].reset_index(drop=True)
df_period3 = df_full.iloc[2*third:].reset_index(drop=True)

print(f"\nPeriod 1: {df_period1['timestamp'].min()} to {df_period1['timestamp'].max()} ({len(df_period1)} bars)")
r1 = backtest_rsi(df_period1, 30, 65, 1.0, 2.0, 1.0, 3)
if r1:
    print(f"  Return: {r1['return']:+.2f}% | DD: {r1['max_dd']:.2f}% | R/DD: {r1['return_dd']:.2f}x | Trades: {r1['trades']}")

print(f"\nPeriod 2: {df_period2['timestamp'].min()} to {df_period2['timestamp'].max()} ({len(df_period2)} bars)")
r2 = backtest_rsi(df_period2, 30, 65, 1.0, 2.0, 1.0, 3)
if r2:
    print(f"  Return: {r2['return']:+.2f}% | DD: {r2['max_dd']:.2f}% | R/DD: {r2['return_dd']:.2f}x | Trades: {r2['trades']}")

print(f"\nPeriod 3: {df_period3['timestamp'].min()} to {df_period3['timestamp'].max()} ({len(df_period3)} bars)")
r3 = backtest_rsi(df_period3, 30, 65, 1.0, 2.0, 1.0, 3)
if r3:
    print(f"  Return: {r3['return']:+.2f}% | DD: {r3['max_dd']:.2f}% | R/DD: {r3['return_dd']:.2f}x | Trades: {r3['trades']}")

if r1 and r2 and r3:
    returns = [r1['return'], r2['return'], r3['return']]
    rdd_ratios = [r1['return_dd'], r2['return_dd'], r3['return_dd']]

    print(f"\n📊 Consistency Analysis:")
    print(f"  Returns: {returns[0]:+.2f}%, {returns[1]:+.2f}%, {returns[2]:+.2f}%")
    print(f"  Std Dev: {np.std(returns):.2f}%")
    print(f"  R/DD Ratios: {rdd_ratios[0]:.2f}x, {rdd_ratios[1]:.2f}x, {rdd_ratios[2]:.2f}x")

    # Check if all periods are profitable
    all_profitable = all(r > 0 for r in returns)

    if all_profitable and np.std(returns) < 15:
        print("\n✅ CONSISTENT PERFORMANCE across all sub-periods")
        print("   - All 3 periods profitable")
        print("   - Low variance in returns")
        print("   → Strategy is robust, not overfitted to specific dates")
    elif all_profitable:
        print("\n⚠️  ALL PROFITABLE but HIGH VARIANCE")
        print("   - All periods make money but returns vary widely")
        print("   → Some overfitting possible but edge exists")
    else:
        print("\n❌ INCONSISTENT PERFORMANCE")
        print(f"   - Only {sum(1 for r in returns if r > 0)} out of 3 periods profitable")
        print("   → Suggests overfitting or parameter sensitivity")

print("\n" + "=" * 80)
print("FINAL VERDICT")
print("=" * 80)

print("\nIf coin-specific params are significantly better than generic params:")
print("  ✅ Optimization found real coin characteristics (NOT overfitted)")
print("\nIf performance is consistent across sub-periods:")
print("  ✅ Strategy works across different market conditions (NOT overfitted)")
print("\nIf both tests pass:")
print("  🚀 Safe to deploy - parameters are robust")
