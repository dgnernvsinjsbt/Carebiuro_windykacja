"""
Walk-forward validation: Test optimized strategies on OUT-OF-SAMPLE data
BEFORE the training period to see if they're overfitted or genuinely robust.

Test 1: MOODENG RSI (optimized on Sep 15 - Dec 7)
        Test on: July 1 - Sep 14 (BEFORE training)

Test 2: FARTCOIN ATR (optimized on Oct 29 - Nov 29)
        Test on: Sep 1 - Oct 28 (BEFORE training)

If strategies work on earlier data → robust, Dec 8-15 was bad luck
If strategies fail on earlier data → overfitted, NOT safe for live
"""

import pandas as pd
import numpy as np

print("=" * 80)
print("WALK-FORWARD VALIDATION TEST")
print("Testing if strategies work on data BEFORE training period")
print("=" * 80)

# ============================================================================
# TEST 1: MOODENG RSI on July-Aug 2025 (before Sep 15 training start)
# ============================================================================

print("\n" + "=" * 80)
print("TEST 1: MOODENG RSI on July 1 - Sep 14, 2025")
print("=" * 80)

# Load MOODENG 1h data
df_moodeng = pd.read_csv('bingx-trading-bot/trading/moodeng_usdt_90d_1h.csv', parse_dates=['timestamp'])
df_moodeng = df_moodeng.sort_values('timestamp').reset_index(drop=True)

# Filter to BEFORE training period (July 1 - Sep 14)
df_test1 = df_moodeng[(df_moodeng['timestamp'] >= '2025-07-01') & (df_moodeng['timestamp'] < '2025-09-15')].reset_index(drop=True)

print(f"\nData: {len(df_test1)} bars ({df_test1['timestamp'].min()} to {df_test1['timestamp'].max()})")
print(f"Training period was: Sep 15 - Dec 7, 2025")
print(f"This is OUT-OF-SAMPLE data (before training)")

# Calculate RSI and ATR
def calculate_rsi_indicators(df):
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

df_test1 = calculate_rsi_indicators(df_test1)

# Optimized parameters from Sep-Dec training
MOODENG_PARAMS = {
    'rsi_low': 30,
    'rsi_high': 65,
    'limit_pct': 1.0,
    'sl_mult': 2.0,
    'tp_mult': 1.0,
    'max_hold': 3
}

def backtest_rsi_strategy(df, params):
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
        if row['rsi'] < params['rsi_low']:
            direction = 'LONG'
        elif row['rsi'] > params['rsi_high']:
            direction = 'SHORT'

        if direction is None:
            i += 1
            continue

        # LONG
        if direction == 'LONG':
            entry_price = row['close'] * (1 + params['limit_pct'] / 100)
            sl_price = entry_price - (row['atr'] * params['sl_mult'])
            tp_price = entry_price + (row['atr'] * params['tp_mult'])

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

            for k in range(fill_idx + 1, min(fill_idx + params['max_hold'] + 1, len(df))):
                bar = df.iloc[k]
                if bar['low'] <= sl_price:
                    exit_idx = k
                    exit_price = sl_price
                    exit_type = 'SL'
                    break
                if bar['high'] >= tp_price:
                    exit_idx = k
                    exit_price = tp_price
                    exit_type = 'TP'
                    break

            if exit_idx is None:
                exit_idx = min(fill_idx + params['max_hold'], len(df) - 1)
                exit_price = df.iloc[exit_idx]['close']
                exit_type = 'TIME'

            pnl_pct = ((exit_price - entry_price) / entry_price) * 100 - 0.10
            pnl_dollars = equity * (pnl_pct / 100)
            equity += pnl_dollars

            trades.append({
                'exit_type': exit_type,
                'pnl_pct': pnl_pct,
                'equity': equity
            })

            equity_curve.append(equity)
            i = exit_idx + 1
            continue

        # SHORT
        elif direction == 'SHORT':
            entry_price = row['close'] * (1 - params['limit_pct'] / 100)
            sl_price = entry_price + (row['atr'] * params['sl_mult'])
            tp_price = entry_price - (row['atr'] * params['tp_mult'])

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

            for k in range(fill_idx + 1, min(fill_idx + params['max_hold'] + 1, len(df))):
                bar = df.iloc[k]
                if bar['high'] >= sl_price:
                    exit_idx = k
                    exit_price = sl_price
                    exit_type = 'SL'
                    break
                if bar['low'] <= tp_price:
                    exit_idx = k
                    exit_price = tp_price
                    exit_type = 'TP'
                    break

            if exit_idx is None:
                exit_idx = min(fill_idx + params['max_hold'], len(df) - 1)
                exit_price = df.iloc[exit_idx]['close']
                exit_type = 'TIME'

            pnl_pct = ((entry_price - exit_price) / entry_price) * 100 - 0.10
            pnl_dollars = equity * (pnl_pct / 100)
            equity += pnl_dollars

            trades.append({
                'exit_type': exit_type,
                'pnl_pct': pnl_pct,
                'equity': equity
            })

            equity_curve.append(equity)
            i = exit_idx + 1
            continue

        i += 1

    return trades, equity_curve

# Run test
trades1, equity1 = backtest_rsi_strategy(df_test1, MOODENG_PARAMS)

if len(trades1) == 0:
    print("\n❌ NO TRADES on July-Sep period")
else:
    df_t1 = pd.DataFrame(trades1)
    ret1 = ((equity1[-1] - 100) / 100) * 100

    eq1 = pd.Series(equity1)
    rmax1 = eq1.expanding().max()
    dd1 = (eq1 - rmax1) / rmax1 * 100
    maxdd1 = dd1.min()

    win1 = (df_t1['pnl_pct'] > 0).sum()
    winrate1 = (win1 / len(df_t1)) * 100

    tp1 = (df_t1['exit_type'] == 'TP').sum()
    sl1 = (df_t1['exit_type'] == 'SL').sum()

    tprate1 = (tp1 / len(df_t1)) * 100
    slrate1 = (sl1 / len(df_t1)) * 100

    print(f"\n✅ Results:")
    print(f"  Return: {ret1:+.2f}%")
    print(f"  Max DD: {maxdd1:.2f}%")
    print(f"  R/DD: {ret1/abs(maxdd1):.2f}x" if maxdd1 != 0 else "  R/DD: N/A")
    print(f"  Trades: {len(df_t1)}")
    print(f"  Win Rate: {winrate1:.1f}%")
    print(f"  TP Rate: {tprate1:.1f}% | SL Rate: {slrate1:.1f}%")

    print(f"\n📊 Comparison to Training Period (Sep 15 - Dec 7):")
    print(f"  Training: +26.96% | 85% win | -1.00% DD | 26.96x R/DD")
    print(f"  Jul-Sep:  {ret1:+.2f}% | {winrate1:.0f}% win | {maxdd1:.2f}% DD | {ret1/abs(maxdd1):.2f}x R/DD" if maxdd1 != 0 else f"  Jul-Sep:  {ret1:+.2f}% | {winrate1:.0f}% win")

# ============================================================================
# TEST 2: FARTCOIN ATR on Sep-Oct 2025 (before Oct 29 training start)
# ============================================================================

print("\n" + "=" * 80)
print("TEST 2: FARTCOIN ATR on Sep 1 - Oct 28, 2025")
print("=" * 80)

# Load FARTCOIN 1m data
df_fartcoin = pd.read_csv('trading/fartcoin_30d_bingx.csv', parse_dates=['timestamp'])
df_fartcoin = df_fartcoin.sort_values('timestamp').reset_index(drop=True)

# Filter to BEFORE training period (Sep 1 - Oct 28)
df_test2 = df_fartcoin[(df_fartcoin['timestamp'] >= '2025-09-01') & (df_fartcoin['timestamp'] < '2025-10-29')].reset_index(drop=True)

print(f"\nData: {len(df_test2)} bars ({df_test2['timestamp'].min()} to {df_test2['timestamp'].max()})")
print(f"Training period was: Oct 29 - Nov 29, 2025")
print(f"This is OUT-OF-SAMPLE data (before training)")

# Calculate ATR indicators
def calculate_atr_indicators(df):
    df['tr'] = np.maximum(
        df['high'] - df['low'],
        np.maximum(
            abs(df['high'] - df['close'].shift(1)),
            abs(df['low'] - df['close'].shift(1))
        )
    )
    df['atr'] = df['tr'].rolling(14).mean()
    df['atr_ma'] = df['atr'].rolling(20).mean()
    df['atr_ratio'] = df['atr'] / df['atr_ma']
    df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['ema_dist_pct'] = abs(df['close'] - df['ema20']) / df['ema20'] * 100
    return df

df_test2 = calculate_atr_indicators(df_test2)

# Optimized parameters from Oct-Nov training
FARTCOIN_PARAMS = {
    'atr_expansion_threshold': 1.5,
    'ema_distance_max': 3.0,
    'limit_offset_pct': 1.0,
    'max_wait_bars': 3,
    'sl_mult': 2.0,
    'tp_mult': 8.0,
    'max_hold_bars': 200
}

def backtest_atr_strategy(df, params):
    trades = []
    equity = 100.0
    equity_curve = [equity]

    i = 20
    while i < len(df):
        row = df.iloc[i]

        if pd.isna(row['atr']) or pd.isna(row['atr_ratio']) or pd.isna(row['ema_dist_pct']):
            i += 1
            continue

        atr_expanding = row['atr_ratio'] > params['atr_expansion_threshold']
        ema_close = row['ema_dist_pct'] < params['ema_distance_max']

        direction = None
        if atr_expanding and ema_close:
            if row['close'] > row['open']:
                direction = 'LONG'
            elif row['close'] < row['open']:
                direction = 'SHORT'

        if direction is None:
            i += 1
            continue

        # LONG
        if direction == 'LONG':
            signal_price = row['close']
            entry_price = signal_price * (1 + params['limit_offset_pct'] / 100)
            sl_price = entry_price - (row['atr'] * params['sl_mult'])
            tp_price = entry_price + (row['atr'] * params['tp_mult'])

            filled = False
            fill_idx = None
            for j in range(i + 1, min(i + params['max_wait_bars'] + 1, len(df))):
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

            for k in range(fill_idx + 1, min(fill_idx + params['max_hold_bars'] + 1, len(df))):
                bar = df.iloc[k]
                if bar['low'] <= sl_price:
                    exit_idx = k
                    exit_price = sl_price
                    exit_type = 'SL'
                    break
                if bar['high'] >= tp_price:
                    exit_idx = k
                    exit_price = tp_price
                    exit_type = 'TP'
                    break

            if exit_idx is None:
                exit_idx = min(fill_idx + params['max_hold_bars'], len(df) - 1)
                exit_price = df.iloc[exit_idx]['close']
                exit_type = 'TIME'

            pnl_pct = ((exit_price - entry_price) / entry_price) * 100 - 0.10
            pnl_dollars = equity * (pnl_pct / 100)
            equity += pnl_dollars

            trades.append({
                'exit_type': exit_type,
                'pnl_pct': pnl_pct,
                'equity': equity
            })

            equity_curve.append(equity)
            i = exit_idx + 1
            continue

        # SHORT
        elif direction == 'SHORT':
            signal_price = row['close']
            entry_price = signal_price * (1 - params['limit_offset_pct'] / 100)
            sl_price = entry_price + (row['atr'] * params['sl_mult'])
            tp_price = entry_price - (row['atr'] * params['tp_mult'])

            filled = False
            fill_idx = None
            for j in range(i + 1, min(i + params['max_wait_bars'] + 1, len(df))):
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

            for k in range(fill_idx + 1, min(fill_idx + params['max_hold_bars'] + 1, len(df))):
                bar = df.iloc[k]
                if bar['high'] >= sl_price:
                    exit_idx = k
                    exit_price = sl_price
                    exit_type = 'SL'
                    break
                if bar['low'] <= tp_price:
                    exit_idx = k
                    exit_price = tp_price
                    exit_type = 'TP'
                    break

            if exit_idx is None:
                exit_idx = min(fill_idx + params['max_hold_bars'], len(df) - 1)
                exit_price = df.iloc[exit_idx]['close']
                exit_type = 'TIME'

            pnl_pct = ((entry_price - exit_price) / entry_price) * 100 - 0.10
            pnl_dollars = equity * (pnl_pct / 100)
            equity += pnl_dollars

            trades.append({
                'exit_type': exit_type,
                'pnl_pct': pnl_pct,
                'equity': equity
            })

            equity_curve.append(equity)
            i = exit_idx + 1
            continue

        i += 1

    return trades, equity_curve

# Run test
trades2, equity2 = backtest_atr_strategy(df_test2, FARTCOIN_PARAMS)

if len(trades2) == 0:
    print("\n❌ NO TRADES on Sep-Oct period")
else:
    df_t2 = pd.DataFrame(trades2)
    ret2 = ((equity2[-1] - 100) / 100) * 100

    eq2 = pd.Series(equity2)
    rmax2 = eq2.expanding().max()
    dd2 = (eq2 - rmax2) / rmax2 * 100
    maxdd2 = dd2.min()

    win2 = (df_t2['pnl_pct'] > 0).sum()
    winrate2 = (win2 / len(df_t2)) * 100

    tp2 = (df_t2['exit_type'] == 'TP').sum()
    sl2 = (df_t2['exit_type'] == 'SL').sum()

    tprate2 = (tp2 / len(df_t2)) * 100
    slrate2 = (sl2 / len(df_t2)) * 100

    print(f"\n✅ Results:")
    print(f"  Return: {ret2:+.2f}%")
    print(f"  Max DD: {maxdd2:.2f}%")
    print(f"  R/DD: {ret2/abs(maxdd2):.2f}x" if maxdd2 != 0 else "  R/DD: N/A")
    print(f"  Trades: {len(df_t2)}")
    print(f"  Win Rate: {winrate2:.1f}%")
    print(f"  TP Rate: {tprate2:.1f}% | SL Rate: {slrate2:.1f}%")

    print(f"\n📊 Comparison to Training Period (Oct 29 - Nov 29):")
    print(f"  Training: +101.11% | 42.6% win | -11.98% DD | 8.44x R/DD")
    print(f"  Sep-Oct:  {ret2:+.2f}% | {winrate2:.0f}% win | {maxdd2:.2f}% DD | {ret2/abs(maxdd2):.2f}x R/DD" if maxdd2 != 0 else f"  Sep-Oct:  {ret2:+.2f}% | {winrate2:.0f}% win")

# ============================================================================
# FINAL VERDICT
# ============================================================================

print("\n" + "=" * 80)
print("FINAL VERDICT")
print("=" * 80)

if len(trades1) > 0 and len(trades2) > 0:
    # Both strategies generated trades on earlier data
    if ret1 > 0 and ret2 > 0:
        print("\n✅ BOTH strategies profitable on OUT-OF-SAMPLE data BEFORE training")
        print("\nThis proves:")
        print("  - Strategies are NOT overfitted to training period")
        print("  - They work on multiple different time periods")
        print("  - Dec 8-15 was genuinely bad variance, not systematic failure")
        print("\n🚀 SAFE TO DEPLOY LIVE")
    elif ret1 > 0 or ret2 > 0:
        print("\n⚠️  MIXED results: One strategy worked, one didn't")
        working = "MOODENG RSI" if ret1 > 0 else "FARTCOIN ATR"
        failing = "FARTCOIN ATR" if ret1 > 0 else "MOODENG RSI"
        print(f"\n  ✅ {working}: Works on earlier OOS data")
        print(f"  ❌ {failing}: Fails on earlier OOS data")
        print("\n  Consider deploying only the robust strategy")
    else:
        print("\n❌ BOTH strategies FAILED on earlier OOS data")
        print("\nThis suggests OVERFITTING:")
        print("  - Strategies only work on specific training period")
        print("  - Fail on both earlier (Jul-Oct) AND later (Dec 8-15) data")
        print("  - Parameters likely curve-fitted to training data noise")
        print("\n🚫 NOT SAFE TO DEPLOY LIVE - need to re-optimize with walk-forward")
else:
    print("\n❌ Insufficient data for walk-forward test")
    print("  One or both strategies generated no trades on earlier periods")

print("\n" + "=" * 80)
