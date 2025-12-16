"""
Calculate drawdown PROPERLY:
1. Track equity after every single trade across all 7 months
2. Calculate running maximum at each point
3. Calculate drawdown from running max at each point
4. Max DD = worst drawdown value
"""
import pandas as pd
import numpy as np

def backtest_all_months():
    """Run complete backtest, return equity curve"""

    months = [
        'melania_june_2025_15m.csv',
        'melania_july_2025_15m.csv',
        'melania_august_2025_15m.csv',
        'melania_september_2025_15m.csv',
        'melania_october_2025_15m.csv',
        'melania_november_2025_15m.csv',
        'melania_december_2025_15m.csv',
    ]

    equity_curve = [100.0]
    equity = 100.0
    current_risk = 0.12
    min_risk = 0.02
    max_risk = 0.30

    for filename in months:
        df = pd.read_csv(filename)

        # Indicators
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

                if pending_order['direction'] == 'LONG' and row['low'] <= pending_order['limit_price']:
                    position = {
                        'direction': 'LONG',
                        'entry': pending_order['limit_price'],
                        'sl_price': pending_order['sl_price'],
                        'tp_price': pending_order['tp_price'],
                        'size': pending_order['size']
                    }
                    pending_order = None
                elif pending_order['direction'] == 'SHORT' and row['high'] >= pending_order['limit_price']:
                    position = {
                        'direction': 'SHORT',
                        'entry': pending_order['limit_price'],
                        'sl_price': pending_order['sl_price'],
                        'tp_price': pending_order['tp_price'],
                        'size': pending_order['size']
                    }
                    pending_order = None

            # Check exit
            if position:
                pnl_pct = None

                if position['direction'] == 'LONG':
                    if row['low'] <= position['sl_price']:
                        pnl_pct = ((position['sl_price'] - position['entry']) / position['entry']) * 100
                    elif row['high'] >= position['tp_price']:
                        pnl_pct = ((position['tp_price'] - position['entry']) / position['entry']) * 100
                else:
                    if row['high'] >= position['sl_price']:
                        pnl_pct = ((position['entry'] - position['sl_price']) / position['entry']) * 100
                    elif row['low'] <= position['tp_price']:
                        pnl_pct = ((position['entry'] - position['tp_price']) / position['entry']) * 100

                if pnl_pct is not None:
                    pnl_dollar = position['size'] * (pnl_pct / 100) - position['size'] * 0.001
                    equity += pnl_dollar
                    equity_curve.append(equity)

                    # Update risk
                    if pnl_pct > 0:
                        current_risk = min(current_risk * 1.5, max_risk)
                    else:
                        current_risk = max(current_risk * 0.5, min_risk)

                    position = None
                    continue

            # Generate signals
            if not position and not pending_order and i > 0:
                prev_row = df.iloc[i-1]

                if row['ret_20'] <= 0 or pd.isna(prev_row['rsi']):
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
                    if row['avg_move_size'] >= 0.8:
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

    return equity_curve

# Run backtest
equity_curve = backtest_all_months()

# Calculate drawdown properly
eq_series = pd.Series(equity_curve)
running_max = eq_series.expanding().max()
drawdown = (eq_series - running_max) / running_max * 100
max_dd = drawdown.min()
max_dd_idx = drawdown.idxmin()

# Find peak and valley
peak = running_max.iloc[max_dd_idx]
valley = eq_series.iloc[max_dd_idx]

# Stats
final_equity = equity_curve[-1]
total_return = ((final_equity - 100) / 100) * 100
return_dd = total_return / abs(max_dd)

print('=' * 100)
print('PROPER DRAWDOWN CALCULATION')
print('=' * 100)
print(f'Total equity points tracked: {len(equity_curve):,}')
print(f'Starting equity: $100.00')
print(f'Final equity: ${final_equity:,.2f}')
print(f'Total return: +{total_return:.1f}%')
print()
print('=' * 100)
print('DRAWDOWN ANALYSIS')
print('=' * 100)
print(f'Peak equity: ${peak:,.2f} (at trade #{max_dd_idx})')
print(f'Valley equity: ${valley:,.2f}')
print(f'Drop: ${peak - valley:,.2f}')
print()
print(f'🔴 MAX DRAWDOWN: {max_dd:.2f}%')
print(f'🏆 RETURN/DD RATIO: {return_dd:.2f}x')
print('=' * 100)
