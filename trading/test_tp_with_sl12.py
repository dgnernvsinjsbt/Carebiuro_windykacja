#!/usr/bin/env python3
"""Test TP values with original 1.2 ATR SL to keep Oct profitable"""
import pandas as pd
import numpy as np

df = pd.read_csv('melania_6months_bingx.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
for col in ['open', 'high', 'low', 'close', 'volume']:
    df[col] = df[col].astype(float)

# Calculate indicators
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
df['ret_20'] = (df['close'] / df['close'].shift(20) - 1) * 100
df['ret_4h'] = (df['close'] - df['close'].shift(16)) / df['close'].shift(16) * 100
df['ret_4h_abs'] = abs(df['ret_4h'])
df['avg_move_size'] = df['ret_4h_abs'].rolling(96).mean()

def backtest_tp(tp_atr):
    """Test TP with fixed SL 1.2"""
    # Fixed params
    rsi_ob = 65
    limit_offset_atr = 0.1
    sl_atr = 1.2  # KEEP ORIGINAL
    min_move = 0.8
    min_momentum = 0

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

        # Check pending order
        if pending_order:
            bars_waiting = i - pending_order['signal_bar']
            if bars_waiting > 8:
                pending_order = None
                continue

            if row['high'] >= pending_order['limit_price']:
                position = {
                    'entry': pending_order['limit_price'],
                    'sl_price': pending_order['sl_price'],
                    'tp_price': pending_order['tp_price'],
                    'size': pending_order['size'],
                    'entry_bar': i,
                    'signal_bar': pending_order['signal_bar']
                }
                pending_order = None

        # Check exit
        if position:
            pnl_pct = None
            exit_reason = None

            if row['high'] >= position['sl_price']:
                pnl_pct = ((position['entry'] - position['sl_price']) / position['entry']) * 100
                exit_reason = 'SL'
            elif row['low'] <= position['tp_price']:
                pnl_pct = ((position['entry'] - position['tp_price']) / position['entry']) * 100
                exit_reason = 'TP'

            if pnl_pct is not None:
                pnl_dollar = position['size'] * (pnl_pct / 100) - position['size'] * 0.001
                equity += pnl_dollar
                equity_curve.append(equity)

                signal_row = df.iloc[position['signal_bar']]

                trades.append({
                    'signal_time': signal_row['timestamp'],
                    'pnl_dollar': pnl_dollar,
                    'exit_reason': exit_reason
                })

                won = pnl_pct > 0
                current_risk = min(current_risk * 1.5, 0.30) if won else max(current_risk * 0.5, 0.02)
                position = None
                continue

        # Generate signals (SHORT only)
        if not position and not pending_order and i > 0:
            prev_row = df.iloc[i-1]

            if row['ret_20'] <= min_momentum or pd.isna(prev_row['rsi']):
                continue

            if prev_row['rsi'] > rsi_ob and row['rsi'] <= rsi_ob:
                if row['avg_move_size'] >= min_move:
                    signal_price = row['close']
                    atr = row['atr']

                    limit_price = signal_price + (atr * limit_offset_atr)
                    sl_price = limit_price + (atr * sl_atr)
                    tp_price = limit_price - (atr * tp_atr)  # VARIABLE

                    sl_dist = abs((sl_price - limit_price) / limit_price) * 100
                    size = (equity * current_risk) / (sl_dist / 100)

                    pending_order = {
                        'limit_price': limit_price,
                        'sl_price': sl_price,
                        'tp_price': tp_price,
                        'size': size,
                        'signal_bar': i
                    }

    if not trades:
        return None

    trades_df = pd.DataFrame(trades)
    trades_df['signal_time'] = pd.to_datetime(trades_df['signal_time'])
    trades_df['month'] = trades_df['signal_time'].dt.to_period('M')

    # Calculate monthly P&L
    monthly_pnl = {}
    for month in trades_df['month'].unique():
        month_pnl = trades_df[trades_df['month'] == month]['pnl_dollar'].sum()
        monthly_pnl[str(month)] = month_pnl

    total_return = ((equity - 100) / 100) * 100
    eq_series = pd.Series(equity_curve)
    running_max = eq_series.expanding().max()
    drawdown = (eq_series - running_max) / running_max * 100
    max_dd = drawdown.min()

    return_dd = total_return / abs(max_dd) if max_dd != 0 else 0

    winners = trades_df[trades_df['pnl_dollar'] > 0]
    win_rate = len(winners) / len(trades_df) * 100

    # Check Oct-Dec status
    oct_pnl = monthly_pnl.get('2025-10', 0)
    nov_pnl = monthly_pnl.get('2025-11', 0)
    dec_pnl = monthly_pnl.get('2025-12', 0)
    oct_dec_all_positive = (oct_pnl > 0) and (nov_pnl > 0) and (dec_pnl > 0)

    return {
        'tp_atr': tp_atr,
        'return': total_return,
        'max_dd': max_dd,
        'return_dd': return_dd,
        'trades': len(trades_df),
        'win_rate': win_rate,
        'oct_pnl': oct_pnl,
        'nov_pnl': nov_pnl,
        'dec_pnl': dec_pnl,
        'oct_dec_ok': oct_dec_all_positive
    }

print("=" * 80)
print("TESTING TAKE PROFIT with SL=1.2 ATR (keeps October profitable)")
print("=" * 80)

tp_values = [2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 6.0]

results = []
for tp in tp_values:
    result = backtest_tp(tp)
    if result:
        results.append(result)
        status = "✅" if result['oct_dec_ok'] else "❌"
        print(f"\nTP {tp:.1f} ATR {status}")
        print(f"  Return/DD: {result['return_dd']:5.2f}x | Return: {result['return']:+7.1f}% | DD: {result['max_dd']:6.2f}%")
        print(f"  Trades: {result['trades']:3d} | Win Rate: {result['win_rate']:5.1f}%")
        print(f"  Oct: ${result['oct_pnl']:+6.2f} | Nov: ${result['nov_pnl']:+6.2f} | Dec: ${result['dec_pnl']:+7.2f}")

# Find configs where Oct-Dec all positive
valid_configs = [r for r in results if r['oct_dec_ok']]

if valid_configs:
    print("\n" + "=" * 80)
    print("CONFIGS WHERE OCT-DEC ALL PROFITABLE")
    print("=" * 80)

    valid_configs.sort(key=lambda x: x['return_dd'], reverse=True)

    for r in valid_configs:
        print(f"\nTP {r['tp_atr']:.1f} ATR:")
        print(f"  Return/DD: {r['return_dd']:.2f}x")
        print(f"  Return: {r['return']:+.1f}%")
        print(f"  Max DD: {r['max_dd']:.2f}%")
        print(f"  Trades: {r['trades']}")
        print(f"  Oct: ${r['oct_pnl']:+.2f} | Nov: ${r['nov_pnl']:+.2f} | Dec: ${r['dec_pnl']:+.2f}")

    best = valid_configs[0]
    print("\n" + "=" * 80)
    print("🎉 BEST CONFIG WITH OCT-DEC ALL PROFITABLE!")
    print("=" * 80)
    print(f"\nParameters:")
    print(f"  RSI: 65")
    print(f"  Offset: 0.1 ATR")
    print(f"  Stop Loss: 1.2 ATR")
    print(f"  Take Profit: {best['tp_atr']:.1f} ATR")
    print(f"\nPerformance:")
    print(f"  Return/DD: {best['return_dd']:.2f}x")
    print(f"  Return: {best['return']:+.1f}%")
    print(f"  Max DD: {best['max_dd']:.2f}%")
    print(f"  Trades: {best['trades']}")
    print(f"\nOct-Dec:")
    print(f"  Oct: ${best['oct_pnl']:+.2f} ✅")
    print(f"  Nov: ${best['nov_pnl']:+.2f} ✅")
    print(f"  Dec: ${best['dec_pnl']:+.2f} ✅")
else:
    print("\n❌ No configs found where Oct-Dec are all profitable with SL 1.2")
    print("May need to add momentum or RSI filters")

print("\n" + "=" * 80)
