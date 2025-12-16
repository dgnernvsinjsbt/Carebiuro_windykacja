"""
Calculate TRUE peak-to-valley max drawdown across entire 7-month period
Track every equity point, find worst drawdown
"""
import pandas as pd
import numpy as np

def backtest_full_period():
    """Run full 7-month backtest and track equity curve"""

    months = [
        ('June', 'melania_june_2025_15m.csv'),
        ('July', 'melania_july_2025_15m.csv'),
        ('August', 'melania_august_2025_15m.csv'),
        ('September', 'melania_september_2025_15m.csv'),
        ('October', 'melania_october_2025_15m.csv'),
        ('November', 'melania_november_2025_15m.csv'),
        ('December', 'melania_december_2025_15m.csv'),
    ]

    all_equity_curve = [100.0]
    equity = 100.0
    position = None
    pending_order = None
    current_risk = 0.12
    max_risk = 0.30
    min_risk = 0.02
    total_trades = 0

    for month_name, filename in months:
        df = pd.read_csv(filename)
        df['timestamp'] = pd.to_datetime(df['timestamp'])

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

        for i in range(300, len(df)):
            row = df.iloc[i]

            if pd.isna(row['rsi']) or pd.isna(row['atr']) or pd.isna(row['ret_20']):
                continue
            if pd.isna(row['avg_move_size']):
                continue

            if pending_order:
                bars_waiting = i - pending_order['signal_bar']
                if bars_waiting > 8:
                    pending_order = None
                    continue

                if pending_order['direction'] == 'LONG':
                    if row['low'] <= pending_order['limit_price']:
                        position = {
                            'direction': 'LONG',
                            'entry': pending_order['limit_price'],
                            'sl_price': pending_order['sl_price'],
                            'tp_price': pending_order['tp_price'],
                            'size': pending_order['size']
                        }
                        pending_order = None
                else:
                    if row['high'] >= pending_order['limit_price']:
                        position = {
                            'direction': 'SHORT',
                            'entry': pending_order['limit_price'],
                            'sl_price': pending_order['sl_price'],
                            'tp_price': pending_order['tp_price'],
                            'size': pending_order['size']
                        }
                        pending_order = None

            if position:
                pnl_pct = None
                exit_type = None

                if position['direction'] == 'LONG':
                    if row['low'] <= position['sl_price']:
                        pnl_pct = ((position['sl_price'] - position['entry']) / position['entry']) * 100
                        exit_type = 'SL'
                    elif row['high'] >= position['tp_price']:
                        pnl_pct = ((position['tp_price'] - position['entry']) / position['entry']) * 100
                        exit_type = 'TP'
                else:
                    if row['high'] >= position['sl_price']:
                        pnl_pct = ((position['entry'] - position['sl_price']) / position['entry']) * 100
                        exit_type = 'SL'
                    elif row['low'] <= position['tp_price']:
                        pnl_pct = ((position['entry'] - position['tp_price']) / position['entry']) * 100
                        exit_type = 'TP'

                if pnl_pct is not None:
                    pnl_dollar = position['size'] * (pnl_pct / 100) - position['size'] * 0.001
                    equity += pnl_dollar
                    all_equity_curve.append(equity)
                    total_trades += 1

                    if pnl_pct > 0:
                        current_risk = min(current_risk * 1.5, max_risk)
                    else:
                        current_risk = max(current_risk * 0.5, min_risk)

                    position = None
                    continue

            if not position and not pending_order and i > 0:
                prev_row = df.iloc[i-1]

                if row['ret_20'] <= 0:
                    continue
                if pd.isna(prev_row['rsi']):
                    continue

                signal_price = row['close']
                atr = row['atr']

                if prev_row['rsi'] < 35 and row['rsi'] >= 35:
                    limit_price = signal_price - (atr * 0.1)
                    sl_price = limit_price - (atr * 1.2)
                    tp_price = limit_price + (atr * 3.0)
                    sl_dist = abs((limit_price - sl_price) / limit_price) * 100
                    size = (equity * current_risk) / (sl_dist / 100)

                    pending_order = {
                        'direction': 'LONG',
                        'limit_price': limit_price,
                        'sl_price': sl_price,
                        'tp_price': tp_price,
                        'size': size,
                        'signal_bar': i
                    }

                elif prev_row['rsi'] > 65 and row['rsi'] <= 65:
                    if row['avg_move_size'] < 0.8:
                        continue

                    limit_price = signal_price + (atr * 0.1)
                    sl_price = limit_price + (atr * 1.2)
                    tp_price = limit_price - (atr * 3.0)
                    sl_dist = abs((sl_price - limit_price) / limit_price) * 100
                    size = (equity * current_risk) / (sl_dist / 100)

                    pending_order = {
                        'direction': 'SHORT',
                        'limit_price': limit_price,
                        'sl_price': sl_price,
                        'tp_price': tp_price,
                        'size': size,
                        'signal_bar': i
                    }

    return all_equity_curve, total_trades

print('=' * 100)
print('TRUE PEAK-TO-VALLEY MAX DRAWDOWN CALCULATION')
print('Config: +50%/-50% | 2% Floor | 0.8% Filter')
print('=' * 100)

equity_curve, total_trades = backtest_full_period()

# Calculate TRUE max drawdown (peak to valley)
eq_series = pd.Series(equity_curve)
running_max = eq_series.expanding().max()
drawdown = (eq_series - running_max) / running_max * 100
max_dd = drawdown.min()
max_dd_idx = drawdown.idxmin()

# Find the peak before max DD
peak_equity = running_max.iloc[max_dd_idx]
valley_equity = eq_series.iloc[max_dd_idx]

# Final stats
final_equity = equity_curve[-1]
total_return = ((final_equity - 100) / 100) * 100
return_dd = total_return / abs(max_dd) if max_dd != 0 else 0

print(f"\nTotal Trades: {total_trades}")
print(f"Starting Equity: $100.00")
print(f"Final Equity: ${final_equity:,.2f}")
print(f"Total Return: +{total_return:.1f}%")
print(f"\n{'=' * 100}")
print('DRAWDOWN ANALYSIS')
print('=' * 100)
print(f"Peak Equity: ${peak_equity:,.2f} (at trade #{max_dd_idx})")
print(f"Valley Equity: ${valley_equity:,.2f}")
print(f"Peak-to-Valley Drop: ${peak_equity - valley_equity:,.2f}")
print(f"MAX DRAWDOWN: {max_dd:.2f}%")
print(f"\nReturn/DD Ratio: {return_dd:.2f}x")

print(f"\n{'=' * 100}")
print('VERIFICATION')
print('=' * 100)
print(f"This is the TRUE peak-to-valley max drawdown.")
print(f"Measured across {len(equity_curve):,} equity points (every trade exit).")
print(f"Peak = ${peak_equity:.2f} → Valley = ${valley_equity:.2f} = {max_dd:.2f}% drawdown")
print('=' * 100)
