#!/usr/bin/env python3
"""
PIPPIN Extreme Reversal - Optimization
Found edge: Fade >2% moves = 1.79x R/DD
Now optimize to push above 3.0x threshold
"""

import pandas as pd
import numpy as np

print("=" * 80)
print("PIPPIN EXTREME REVERSAL - OPTIMIZATION")
print("Discovered: Fade >2% moves = +23.13% return, 1.79x R/DD")
print("Goal: Optimize to exceed 3.0x R/DD threshold")
print("=" * 80)

# Load data
df = pd.read_csv('pippin_7d_bingx.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# Calculate indicators
df['tr'] = df[['high', 'low', 'close']].apply(
    lambda row: max(row['high'] - row['low'],
                    abs(row['high'] - row['close']),
                    abs(row['low'] - row['close'])), axis=1
)
df['atr_14'] = df['tr'].rolling(window=14).mean()
df['vol_ma_30'] = df['volume'].rolling(window=30).mean()
df['vol_ratio'] = df['volume'] / df['vol_ma_30']
df['is_green'] = (df['close'] > df['open']).astype(int)
df['is_red'] = (df['close'] < df['open']).astype(int)
df['body_pct'] = abs(df['close'] - df['open']) / df['open'] * 100
df['hour'] = df['timestamp'].dt.hour
df['is_us_session'] = ((df['hour'] >= 14) & (df['hour'] < 21)).astype(int)

df = df.dropna().reset_index(drop=True)

# Test parameter variations
configs = []

# Baseline (from discovery)
configs.append({
    'name': 'Baseline (Discovered)',
    'body_threshold': 2.0,
    'sl_atr_mult': 1.0,
    'tp_atr_mult': 1.5,
    'max_hold': 15,
    'session': 'us',
    'volume_filter': None
})

# Optimize body threshold
for body_thresh in [1.5, 2.0, 2.5]:
    configs.append({
        'name': f'Body {body_thresh}%',
        'body_threshold': body_thresh,
        'sl_atr_mult': 1.0,
        'tp_atr_mult': 1.5,
        'max_hold': 15,
        'session': 'us',
        'volume_filter': None
    })

# Optimize SL/TP ratios
for sl_mult in [0.8, 1.0, 1.2]:
    for tp_mult in [1.5, 2.0, 2.5]:
        configs.append({
            'name': f'SL{sl_mult}/TP{tp_mult}',
            'body_threshold': 2.0,
            'sl_atr_mult': sl_mult,
            'tp_atr_mult': tp_mult,
            'max_hold': 15,
            'session': 'us',
            'volume_filter': None
        })

# Add volume filter
for vol_min in [1.5, 2.0, 2.5]:
    configs.append({
        'name': f'+ Vol >{vol_min}x',
        'body_threshold': 2.0,
        'sl_atr_mult': 1.0,
        'tp_atr_mult': 1.5,
        'max_hold': 15,
        'session': 'us',
        'volume_filter': vol_min
    })

# Optimize max hold
for hold in [10, 15, 20]:
    configs.append({
        'name': f'Hold {hold} bars',
        'body_threshold': 2.0,
        'sl_atr_mult': 1.0,
        'tp_atr_mult': 1.5,
        'max_hold': hold,
        'session': 'us',
        'volume_filter': None
    })

# Test all sessions
for sess in ['us', 'all']:
    configs.append({
        'name': f'Session: {sess}',
        'body_threshold': 2.0,
        'sl_atr_mult': 1.0,
        'tp_atr_mult': 1.5,
        'max_hold': 15,
        'session': sess,
        'volume_filter': None
    })

def test_config(df, config):
    """Test a configuration"""
    trades = []

    for i in range(50, len(df)):
        row = df.iloc[i]

        # Session filter
        if config['session'] == 'us' and row['is_us_session'] == 0:
            continue

        # Volume filter
        if config['volume_filter'] and row['vol_ratio'] < config['volume_filter']:
            continue

        # Entry conditions
        if row['body_pct'] >= config['body_threshold']:
            if row['is_green']:  # SHORT after pump
                direction = 'SHORT'
            elif row['is_red']:  # LONG after dump
                direction = 'LONG'
            else:
                continue
        else:
            continue

        entry_price = row['close']
        atr = row['atr_14']

        if direction == 'LONG':
            stop_loss = entry_price - (config['sl_atr_mult'] * atr)
            take_profit = entry_price + (config['tp_atr_mult'] * atr)
        else:  # SHORT
            stop_loss = entry_price + (config['sl_atr_mult'] * atr)
            take_profit = entry_price - (config['tp_atr_mult'] * atr)

        # Simulate trade
        exit_price = None
        exit_reason = None
        for j in range(1, config['max_hold'] + 1):
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

        trades.append({'pnl_pct': pnl_pct * 100, 'exit': exit_reason})

    if len(trades) == 0:
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

    return {
        'config': config['name'],
        'trades': len(tdf),
        'return': total_return,
        'max_dd': max_dd,
        'return_dd': return_dd,
        'win_rate': win_rate
    }

print(f"\nTesting {len(configs)} configurations...")

results = []
for config in configs:
    result = test_config(df, config)
    if result:
        results.append(result)

# Sort by Return/DD
results_sorted = sorted(results, key=lambda x: x['return_dd'], reverse=True)

print("\n" + "=" * 80)
print("TOP 10 CONFIGURATIONS")
print("=" * 80)
print("\n| Rank | Configuration | Trades | Return | Max DD | Return/DD | Win Rate |")
print("|------|---------------|--------|--------|--------|-----------|----------|")

for idx, r in enumerate(results_sorted[:10], 1):
    emoji = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else "  "
    print(f"| {emoji} {idx:2} | {r['config']:<22} | {r['trades']:>6} | {r['return']:>+6.2f}% | {r['max_dd']:>6.2f}% | {r['return_dd']:>9.2f}x | {r['win_rate']:>7.1f}% |")

print("\n" + "=" * 80)

best = results_sorted[0]
print(f"\n🏆 BEST CONFIGURATION: {best['config']}")
print(f"   Return/DD: {best['return_dd']:.2f}x")
print(f"   Return: {best['return']:+.2f}%")
print(f"   Max DD: {best['max_dd']:.2f}%")
print(f"   Win Rate: {best['win_rate']:.1f}%")
print(f"   Trades: {best['trades']} ({best['trades']/7:.1f}/day)")

if best['return_dd'] >= 3.0:
    print(f"\n   ✅ VIABLE! Exceeded 3.0x threshold")
    print(f"   This configuration is ready for 30-day validation")
elif best['return_dd'] >= 2.0:
    print(f"\n   ⚠️  CLOSE! {best['return_dd']:.2f}x approaching viability")
    print(f"   May work with further optimization or more data")
else:
    print(f"\n   ❌ Still below threshold")
    print(f"   PIPPIN remains extremely difficult to trade")

print("\n" + "=" * 80)
print("Optimization complete")
print("=" * 80)
