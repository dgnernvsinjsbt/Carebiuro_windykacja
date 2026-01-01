#!/usr/bin/env python3
"""Test volatility context filters"""
import pandas as pd
import numpy as np

df = pd.read_csv('melania_6months_bingx.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
for col in ['open', 'high', 'low', 'close', 'volume']:
    df[col] = df[col].astype(float)

delta = df['close'].diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)
avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
rs = avg_gain / avg_loss
df['rsi'] = 100 - (100 / (1 + rs))

df['tr'] = np.maximum(df['high'] - df['low'], np.maximum(
    abs(df['high'] - df['close'].shift(1)),
    abs(df['low'] - df['close'].shift(1))
))
df['atr'] = df['tr'].rolling(14).mean()
df['avg_move_size'] = (abs(df['close'] - df['close'].shift(16)) / df['close'].shift(16) * 100).rolling(96).mean()

# Volatility context
df['atr_ma_20'] = df['atr'].rolling(20).mean()
df['atr_ratio'] = df['atr'] / df['atr_ma_20']

df['volume_ma_20'] = df['volume'].rolling(20).mean()
df['volume_ratio'] = df['volume'] / df['volume_ma_20']

def test(min_atr_ratio, min_vol_ratio):
    rsi_ob = 66
    limit_offset_atr = 0.1
    sl_atr = 1.2
    tp_atr = 3.0
    min_move = 0.8

    current_risk = 0.12
    equity = 100.0
    trades = []
    position = None
    pending_order = None

    for i in range(300, len(df)):
        row = df.iloc[i]

        if pd.isna(row['rsi']) or pd.isna(row['atr']) or pd.isna(row['avg_move_size']):
            continue
        if pd.isna(row['atr_ratio']) or pd.isna(row['volume_ratio']):
            continue

        if pending_order:
            if i - pending_order['signal_bar'] > 8:
                pending_order = None
            elif row['high'] >= pending_order['limit_price']:
                position = {
                    'entry': pending_order['limit_price'],
                    'sl_price': pending_order['sl_price'],
                    'tp_price': pending_order['tp_price'],
                    'size': pending_order['size'],
                    'entry_bar': i,
                    'signal_bar': pending_order['signal_bar']
                }
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

                signal_row = df.iloc[position['signal_bar']]
                trades.append({
                    'signal_time': signal_row['timestamp'],
                    'pnl_dollar': pnl_dollar
                })

                won = pnl_pct > 0
                current_risk = min(current_risk * 1.5, 0.30) if won else max(current_risk * 0.5, 0.02)
                position = None

        if not position and not pending_order and i > 0:
            prev_row = df.iloc[i-1]

            if pd.isna(prev_row['rsi']):
                continue

            # VOLATILITY FILTERS
            if row['atr_ratio'] < min_atr_ratio:
                continue
            if row['volume_ratio'] < min_vol_ratio:
                continue

            if prev_row['rsi'] > rsi_ob and row['rsi'] <= rsi_ob:
                if row['avg_move_size'] >= min_move:
                    signal_price = row['close']
                    atr = row['atr']

                    limit_price = signal_price + (atr * limit_offset_atr)
                    sl_price = limit_price + (atr * sl_atr)
                    tp_price = limit_price - (atr * tp_atr)

                    sl_dist = abs((sl_price - limit_price) / limit_price) * 100
                    size = (equity * current_risk) / (sl_dist / 100)

                    pending_order = {
                        'limit_price': limit_price,
                        'sl_price': sl_price,
                        'tp_price': tp_price,
                        'size': size,
                        'signal_bar': i
                    }

    if len(trades) < 15:
        return None

    trades_df = pd.DataFrame(trades)
    trades_df['signal_time'] = pd.to_datetime(trades_df['signal_time'])
    trades_df['month'] = trades_df['signal_time'].dt.to_period('M')

    monthly_pnl = {}
    for month in trades_df['month'].unique():
        monthly_pnl[str(month)] = trades_df[trades_df['month'] == month]['pnl_dollar'].sum()

    oct = monthly_pnl.get('2025-10', 0)
    nov = monthly_pnl.get('2025-11', 0)
    dec = monthly_pnl.get('2025-12', 0)

    total_return = ((equity - 100) / 100) * 100

    equity_curve = [100.0]
    running_equity = 100.0
    for pnl in trades_df['pnl_dollar']:
        running_equity += pnl
        equity_curve.append(running_equity)

    eq_series = pd.Series(equity_curve)
    running_max = eq_series.expanding().max()
    drawdown = (eq_series - running_max) / running_max * 100
    max_dd = drawdown.min()

    return_dd = total_return / abs(max_dd) if max_dd != 0 else 0

    return {
        'min_atr': min_atr_ratio,
        'min_vol': min_vol_ratio,
        'return': total_return,
        'max_dd': max_dd,
        'return_dd': return_dd,
        'trades': len(trades_df),
        'oct': oct,
        'nov': nov,
        'dec': dec,
        'oct_dec_ok': oct > 0 and nov > 0 and dec > 0
    }

print("VOLATILITY CONTEXT FILTERS")
print("=" * 80)

configs = [
    (0.0, 0.0),  # Baseline
    (1.0, 0.0),
    (1.1, 0.0),
    (1.2, 0.0),
    (0.0, 0.8),
    (0.0, 1.0),
    (0.0, 1.2),
    (1.1, 0.8),
    (1.1, 1.0),
]

results = []
for atr_r, vol_r in configs:
    r = test(atr_r, vol_r)
    if r:
        results.append(r)
        status = "✅" if r['oct_dec_ok'] else "❌"
        print(f"\nATR≥{atr_r}x Vol≥{vol_r}x {status}")
        print(f"  R/DD: {r['return_dd']:5.2f}x | Trades: {r['trades']:3d}")
        print(f"  Oct: ${r['oct']:+5.2f} | Nov: ${r['nov']:+5.2f} | Dec: ${r['dec']:+6.2f}")

valid = [r for r in results if r['oct_dec_ok']]
if valid:
    valid.sort(key=lambda x: x['return_dd'], reverse=True)
    best = valid[0]
    print("\n" + "=" * 80)
    print(f"BEST: ATR≥{best['min_atr']}x Vol≥{best['min_vol']}x")
    print(f"R/DD: {best['return_dd']:.2f}x | Trades: {best['trades']}")
    print(f"Oct: ${best['oct']:+.2f} | Nov: ${best['nov']:+.2f} | Dec: ${best['dec']:+.2f}")
