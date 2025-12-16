#!/usr/bin/env python3
"""Quick test of promising configs for Oct-Dec profitability"""
import pandas as pd
import numpy as np

df = pd.read_csv('melania_6months_bingx.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
for col in ['open', 'high', 'low', 'close', 'volume']:
    df[col] = df[col].astype(float)

# Indicators
delta = df['close'].diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)
avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
rs = avg_gain / avg_loss
df['rsi'] = 100 - (100 / (1 + rs))
df['tr'] = np.maximum(df['high'] - df['low'], np.maximum(
    abs(df['high'] - df['close'].shift(1)), abs(df['low'] - df['close'].shift(1))
))
df['atr'] = df['tr'].rolling(14).mean()
df['ret_20'] = (df['close'] / df['close'].shift(20) - 1) * 100
df['ret_4h'] = (df['close'] - df['close'].shift(16)) / df['close'].shift(16) * 100
df['ret_4h_abs'] = abs(df['ret_4h'])
df['avg_move_size'] = df['ret_4h_abs'].rolling(96).mean()

def test_config(rsi_ob, sl_atr, tp_atr, min_move, min_mom, name):
    current_risk = 0.12
    equity = 100.0
    equity_curve = [equity]
    trades = []
    position = None
    pending_order = None

    for i in range(300, len(df)):
        row = df.iloc[i]
        if pd.isna(row['rsi']) or pd.isna(row['atr']) or pd.isna(row['ret_20']) or pd.isna(row['avg_move_size']):
            continue

        if pending_order:
            if i - pending_order['signal_bar'] > 8:
                pending_order = None
            elif row['high'] >= pending_order['limit_price']:
                position = {'entry': pending_order['limit_price'], 'sl_price': pending_order['sl_price'],
                           'tp_price': pending_order['tp_price'], 'size': pending_order['size'], 'entry_bar': i}
                pending_order = None

        if position:
            pnl_pct = None
            if row['high'] >= position['sl_price']:
                pnl_pct = ((position['entry'] - position['sl_price']) / position['entry']) * 100
            elif row['low'] <= position['tp_price']:
                pnl_pct = ((position['entry'] - position['tp_price']) / position['entry']) * 100

            if pnl_pct is not None:
                pnl_dollar = position['size'] * (pnl_pct / 100) - position['size'] * 0.001
                equity += pnl_dollar
                equity_curve.append(equity)
                trades.append({'pnl_dollar': pnl_dollar, 'entry_time': df.iloc[position['entry_bar']]['timestamp']})
                won = pnl_pct > 0
                current_risk = min(current_risk * 1.5, 0.30) if won else max(current_risk * 0.5, 0.02)
                position = None

        if not position and not pending_order and i > 0:
            prev_row = df.iloc[i-1]
            if row['ret_20'] <= min_mom or pd.isna(prev_row['rsi']):
                continue
            if prev_row['rsi'] > rsi_ob and row['rsi'] <= rsi_ob:
                if row['avg_move_size'] >= min_move:
                    signal_price = row['close']
                    atr = row['atr']
                    limit_price = signal_price + (atr * 0.1)
                    sl_price = limit_price + (atr * sl_atr)
                    tp_price = limit_price - (atr * tp_atr)
                    sl_dist = abs((sl_price - limit_price) / limit_price) * 100
                    size = (equity * current_risk) / (sl_dist / 100)
                    pending_order = {'limit_price': limit_price, 'sl_price': sl_price,
                                   'tp_price': tp_price, 'size': size, 'signal_bar': i}

    if not trades:
        return None

    trades_df = pd.DataFrame(trades)
    trades_df['month'] = pd.to_datetime(trades_df['entry_time']).dt.to_period('M')

    monthly_pnl = {}
    for month in trades_df['month'].unique():
        monthly_pnl[str(month)] = trades_df[trades_df['month'] == month]['pnl_dollar'].sum()

    total_return = ((equity - 100) / 100) * 100
    eq_series = pd.Series(equity_curve)
    running_max = eq_series.expanding().max()
    drawdown = (eq_series - running_max) / running_max * 100
    max_dd = drawdown.min()

    return {
        'name': name,
        'return': total_return,
        'max_dd': max_dd,
        'return_dd': total_return / abs(max_dd) if max_dd != 0 else 0,
        'trades': len(trades),
        'monthly': monthly_pnl
    }

# Test promising configs
configs = [
    # (rsi, sl_atr, tp_atr, min_move, min_mom, name)
    (65, 2.5, 4.0, 1.0, 1.5, "Wide stops, wider TP, strong momentum"),
    (65, 3.0, 5.0, 1.0, 1.5, "Very wide stops, let winners run"),
    (68, 2.5, 4.0, 1.2, 1.5, "Tight RSI, wide stops, strong filters"),
    (65, 2.5, 5.0, 0.8, 2.0, "Wide exits, very strong momentum"),
    (62, 2.5, 4.0, 1.0, 1.0, "Loose RSI, moderate momentum"),
    (65, 2.0, 4.0, 1.0, 1.5, "Balanced wide"),
    (65, 2.5, 6.0, 1.0, 1.5, "Very wide TP"),
]

results = []
for config in configs:
    result = test_config(*config)
    if result:
        results.append(result)

print("=" * 80)
print("TESTING CONFIGS FOR OCT-DEC PROFITABILITY")
print("=" * 80)

for r in results:
    oct = r['monthly'].get('2025-10', 0)
    nov = r['monthly'].get('2025-11', 0)
    dec = r['monthly'].get('2025-12', 0)

    oct_dec_all_profitable = oct > 0 and nov > 0 and dec > 0

    print(f"\n{r['name']}")
    print(f"  Return/DD: {r['return_dd']:.2f}x | Return: {r['return']:+.1f}% | DD: {r['max_dd']:.2f}% | Trades: {r['trades']}")
    print(f"  Oct: ${oct:+.2f} | Nov: ${nov:+.2f} | Dec: ${dec:+.2f} | Oct-Dec: {'✅ ALL PROFIT' if oct_dec_all_profitable else '❌'}")

# Find best with Oct-Dec all profitable
profitable_configs = [r for r in results if all(r['monthly'].get(f'2025-{m:02d}', 0) > 0 for m in [10,11,12])]

if profitable_configs:
    best = max(profitable_configs, key=lambda x: x['return_dd'])
    print("\n" + "=" * 80)
    print("BEST CONFIG (Oct-Dec all profitable)")
    print("=" * 80)
    print(f"\n{best['name']}")
    print(f"Return/DD: {best['return_dd']:.2f}x")
    print(f"Return: {best['return']:+.1f}%")
    print(f"Max DD: {best['max_dd']:.2f}%")
    print(f"Trades: {best['trades']}")
    print("\nMonthly:")
    for month, pnl in sorted(best['monthly'].items()):
        print(f"  {month}: ${pnl:+.2f}")
else:
    print("\n❌ None of the tested configs have Oct-Dec all profitable")
    print("Need even more aggressive parameters!")
