"""
Test ALL 9 RSI strategies on July-August 2025 out-of-sample data
Using optimized parameters from Sep 15 - Dec 7 training period

This is the DEFINITIVE overfitting test:
- Training: Sep 15 - Dec 7, 2025
- Testing: July 1 - Aug 31, 2025 (BEFORE training period)

If strategies work on July-Aug → NOT overfitted, robust
If strategies fail on July-Aug → overfitted to Sep-Dec data
"""

import pandas as pd
import numpy as np

print("=" * 80)
print("WALK-FORWARD VALIDATION: Testing ALL strategies on July-Aug 2025")
print("Training Period: Sep 15 - Dec 7, 2025")
print("Test Period: July 1 - Aug 31, 2025 (OUT-OF-SAMPLE, BEFORE training)")
print("=" * 80)

# Load optimal configurations
configs = pd.read_csv('optimal_configs_90d.csv')

def calculate_indicators(df):
    """Calculate RSI and ATR indicators"""
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

def backtest_rsi_strategy(df, rsi_low, rsi_high, limit_pct, sl_mult, tp_mult, max_hold=3):
    """Backtest RSI mean reversion strategy"""
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

        # LONG
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
                exit_type = 'TIME'

            pnl_pct = ((exit_price - entry_price) / entry_price) * 100 - 0.10
            pnl_dollars = equity * (pnl_pct / 100)
            equity += pnl_dollars

            trades.append({'pnl_pct': pnl_pct, 'exit_type': exit_type, 'equity': equity})
            equity_curve.append(equity)
            i = exit_idx + 1

        # SHORT
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
                exit_type = 'TIME'

            pnl_pct = ((entry_price - exit_price) / entry_price) * 100 - 0.10
            pnl_dollars = equity * (pnl_pct / 100)
            equity += pnl_dollars

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
    tp_rate = (df_t['exit_type'] == 'TP').sum() / len(df_t) * 100
    sl_rate = (df_t['exit_type'] == 'SL').sum() / len(df_t) * 100

    return {
        'return': ret,
        'max_dd': dd,
        'return_dd': ret / abs(dd) if dd != 0 else 0,
        'trades': len(df_t),
        'win_rate': wr,
        'tp_rate': tp_rate,
        'sl_rate': sl_rate
    }

# Test each strategy
results = []

for idx, row in configs.iterrows():
    coin = row['coin']
    filename = f"trading/{coin.lower().replace('-', '_')}_july_aug_2025_1h.csv"

    print(f"\n{'=' * 80}")
    print(f"{coin}")
    print(f"{'=' * 80}")

    try:
        # Load July-Aug data
        df = pd.read_csv(filename, parse_dates=['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)
        df = calculate_indicators(df)

        print(f"Data: {len(df)} bars (July 1 - Aug 31, 2025)")

        # Get optimized parameters from training
        rsi_low = row['rsi_low']
        rsi_high = row['rsi_high']
        limit_pct = row['limit_offset']
        sl_mult = row['sl_mult']
        tp_mult = row['tp_mult']

        print(f"Params: RSI {rsi_low}/{rsi_high} | Limit {limit_pct}% | SL {sl_mult}x | TP {tp_mult}x")

        # Run backtest on July-Aug
        result = backtest_rsi_strategy(df, rsi_low, rsi_high, limit_pct, sl_mult, tp_mult, max_hold=3)

        if result is None:
            print(f"❌ NO TRADES on July-Aug")
            results.append({
                'coin': coin,
                'status': 'NO_TRADES',
                'jul_aug_return': 0,
                'training_return': row['return'],
                'jul_aug_rdd': 0,
                'training_rdd': row['rr_ratio']
            })
        else:
            # Training period performance
            train_return = row['return']
            train_rdd = row['rr_ratio']
            train_wr = row['win_rate']

            # July-Aug performance
            test_return = result['return']
            test_rdd = result['return_dd']
            test_wr = result['win_rate']

            print(f"\n📊 TRAINING (Sep 15 - Dec 7):")
            print(f"   Return: +{train_return:.2f}% | R/DD: {train_rdd:.2f}x | Win: {train_wr:.1f}%")

            print(f"\n📊 TEST (July 1 - Aug 31, OUT-OF-SAMPLE):")
            print(f"   Return: {test_return:+.2f}% | R/DD: {test_rdd:.2f}x | Win: {test_wr:.1f}%")
            print(f"   Trades: {result['trades']} | TP: {result['tp_rate']:.1f}% | SL: {result['sl_rate']:.1f}%")

            # Verdict for this coin
            if test_return > 0:
                print(f"\n✅ PROFITABLE on out-of-sample data!")
                status = 'PASS'
            else:
                print(f"\n❌ UNPROFITABLE on out-of-sample data")
                status = 'FAIL'

            results.append({
                'coin': coin,
                'status': status,
                'jul_aug_return': test_return,
                'jul_aug_rdd': test_rdd,
                'jul_aug_trades': result['trades'],
                'jul_aug_wr': test_wr,
                'training_return': train_return,
                'training_rdd': train_rdd,
                'training_wr': train_wr
            })

    except FileNotFoundError:
        print(f"❌ Data file not found: {filename}")
        results.append({
            'coin': coin,
            'status': 'NO_DATA',
            'jul_aug_return': 0,
            'training_return': row['return']
        })

# Summary
print("\n" + "=" * 80)
print("FINAL RESULTS SUMMARY")
print("=" * 80)

df_results = pd.DataFrame(results)

passed = df_results[df_results['status'] == 'PASS']
failed = df_results[df_results['status'] == 'FAIL']
no_trades = df_results[df_results['status'] == 'NO_TRADES']

print(f"\n✅ PASSED (profitable on July-Aug): {len(passed)}")
for idx, row in passed.iterrows():
    print(f"   {row['coin']}: {row['jul_aug_return']:+.2f}% ({row.get('jul_aug_trades', 0)} trades)")

print(f"\n❌ FAILED (unprofitable on July-Aug): {len(failed)}")
for idx, row in failed.iterrows():
    print(f"   {row['coin']}: {row['jul_aug_return']:+.2f}% ({row.get('jul_aug_trades', 0)} trades)")

print(f"\n⚠️  NO TRADES: {len(no_trades)}")
for idx, row in no_trades.iterrows():
    print(f"   {row['coin']}")

# Overall verdict
print("\n" + "=" * 80)
print("OVERFITTING VERDICT")
print("=" * 80)

total_testable = len(passed) + len(failed)
pass_rate = (len(passed) / total_testable * 100) if total_testable > 0 else 0

print(f"\nPass Rate: {len(passed)}/{total_testable} ({pass_rate:.1f}%)")

if pass_rate >= 70:
    print("\n✅ NOT OVERFITTED - Strategies are ROBUST")
    print("   70%+ of strategies profitable on out-of-sample data")
    print("   Parameters captured real market characteristics")
    print("\n🚀 SAFE TO DEPLOY LIVE")

elif pass_rate >= 50:
    print("\n⚠️  MIXED RESULTS - Some overfitting possible")
    print("   50-70% strategies worked on OOS data")
    print("   Consider deploying only the strategies that passed")
    print("\n🟡 DEPLOY WITH CAUTION - monitor closely")

elif pass_rate >= 30:
    print("\n❌ LIKELY OVERFITTED - Most strategies failed")
    print("   Only 30-50% worked on OOS data")
    print("   Parameters likely curve-fitted to training period")
    print("\n🚫 NOT RECOMMENDED for live - need re-optimization")

else:
    print("\n❌ SEVERELY OVERFITTED - Strategies are NOT robust")
    print("   <30% worked on out-of-sample data")
    print("   Training period performance was likely noise/luck")
    print("\n🚫 DO NOT DEPLOY - strategies are fundamentally flawed")

# Save results
df_results.to_csv('july_aug_validation_results.csv', index=False)
print(f"\n📁 Results saved to july_aug_validation_results.csv")

print("\n" + "=" * 80)
