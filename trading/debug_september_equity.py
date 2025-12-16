"""
Debug September equity curve
Show trade-by-trade equity progression and max DD calculation
"""
import pandas as pd
import numpy as np

print('=' * 100)
print('DEBUGGING SEPTEMBER EQUITY CURVE')
print('=' * 100)

# Load September data
df = pd.read_csv('melania_september_2025_15m_fresh.csv')
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

# Backtest with detailed equity tracking
trades = []
equity = 100.0
position = None
equity_curve = [100.0]

print(f'\nStarting equity: ${equity:.2f}')
print('\n' + '=' * 100)
print('TRADE-BY-TRADE BREAKDOWN')
print('=' * 100)
print(f"\n{'#':<4} {'Date':<12} {'Dir':<6} {'Entry':<10} {'Exit':<10} {'Type':<4} {'P&L%':<8} {'Equity':<10} {'Change':<8}")
print('-' * 100)

trade_num = 0

for i in range(300, len(df)):
    row = df.iloc[i]

    if pd.isna(row['rsi']) or pd.isna(row['atr']) or pd.isna(row['ret_20']):
        continue

    # Manage position
    if position:
        bar = row
        exit_taken = False

        if position['direction'] == 'LONG':
            if bar['low'] <= position['sl_price']:
                pnl_pct = ((position['sl_price'] - position['entry']) / position['entry']) * 100
                pnl_dollar = position['size'] * (pnl_pct / 100) - position['size'] * 0.001
                equity_before = equity
                equity += pnl_dollar
                equity_curve.append(equity)

                trade_num += 1
                trades.append({'pnl_pct': pnl_pct, 'exit': 'SL'})

                print(f"{trade_num:<4} {str(row['timestamp'])[:10]:<12} {'LONG':<6} "
                      f"${position['entry']:.6f} ${position['sl_price']:.6f} {'SL':<4} "
                      f"{pnl_pct:>+7.2f}% ${equity:>9.2f} {((equity/equity_before-1)*100):>+7.2f}%")

                position = None
                exit_taken = True

            elif bar['high'] >= position['tp_price']:
                pnl_pct = ((position['tp_price'] - position['entry']) / position['entry']) * 100
                pnl_dollar = position['size'] * (pnl_pct / 100) - position['size'] * 0.001
                equity_before = equity
                equity += pnl_dollar
                equity_curve.append(equity)

                trade_num += 1
                trades.append({'pnl_pct': pnl_pct, 'exit': 'TP'})

                print(f"{trade_num:<4} {str(row['timestamp'])[:10]:<12} {'LONG':<6} "
                      f"${position['entry']:.6f} ${position['tp_price']:.6f} {'TP':<4} "
                      f"{pnl_pct:>+7.2f}% ${equity:>9.2f} {((equity/equity_before-1)*100):>+7.2f}%")

                position = None
                exit_taken = True

        else:  # SHORT
            if bar['high'] >= position['sl_price']:
                pnl_pct = ((position['entry'] - position['sl_price']) / position['entry']) * 100
                pnl_dollar = position['size'] * (pnl_pct / 100) - position['size'] * 0.001
                equity_before = equity
                equity += pnl_dollar
                equity_curve.append(equity)

                trade_num += 1
                trades.append({'pnl_pct': pnl_pct, 'exit': 'SL'})

                print(f"{trade_num:<4} {str(row['timestamp'])[:10]:<12} {'SHORT':<6} "
                      f"${position['entry']:.6f} ${position['sl_price']:.6f} {'SL':<4} "
                      f"{pnl_pct:>+7.2f}% ${equity:>9.2f} {((equity/equity_before-1)*100):>+7.2f}%")

                position = None
                exit_taken = True

            elif bar['low'] <= position['tp_price']:
                pnl_pct = ((position['entry'] - position['tp_price']) / position['entry']) * 100
                pnl_dollar = position['size'] * (pnl_pct / 100) - position['size'] * 0.001
                equity_before = equity
                equity += pnl_dollar
                equity_curve.append(equity)

                trade_num += 1
                trades.append({'pnl_pct': pnl_pct, 'exit': 'TP'})

                print(f"{trade_num:<4} {str(row['timestamp'])[:10]:<12} {'SHORT':<6} "
                      f"${position['entry']:.6f} ${position['tp_price']:.6f} {'TP':<4} "
                      f"{pnl_pct:>+7.2f}% ${equity:>9.2f} {((equity/equity_before-1)*100):>+7.2f}%")

                position = None
                exit_taken = True

        if exit_taken:
            continue

    # New signals
    if not position and i > 0:
        prev_row = df.iloc[i-1]
        if row['ret_20'] <= 0:
            continue
        if not pd.isna(prev_row['rsi']):
            if prev_row['rsi'] < 35 and row['rsi'] >= 35:  # LONG
                entry = row['close']
                sl = entry - (row['atr'] * 2.0)
                tp = entry + (row['atr'] * 3.0)
                sl_dist = abs((entry - sl) / entry) * 100
                size = (equity * 0.12) / (sl_dist / 100)
                position = {'direction': 'LONG', 'entry': entry, 'sl_price': sl, 'tp_price': tp, 'size': size}
            elif prev_row['rsi'] > 65 and row['rsi'] <= 65:  # SHORT
                entry = row['close']
                sl = entry + (row['atr'] * 2.0)
                tp = entry - (row['atr'] * 3.0)
                sl_dist = abs((sl - entry) / entry) * 100
                size = (equity * 0.12) / (sl_dist / 100)
                position = {'direction': 'SHORT', 'entry': entry, 'sl_price': sl, 'tp_price': tp, 'size': size}

# Calculate final stats
print('\n' + '=' * 100)
print('SUMMARY')
print('=' * 100)

total_return = ((equity - 100) / 100) * 100
print(f'\nStarting equity: $100.00')
print(f'Ending equity: ${equity:.2f}')
print(f'Total return: {total_return:+.2f}%')
print(f'Total trades: {len(trades)}')

# Calculate CORRECT max drawdown
eq_series = pd.Series(equity_curve)
running_max = eq_series.expanding().max()
drawdown = (eq_series - running_max) / running_max * 100
max_dd = drawdown.min()

print(f'\n' + '=' * 100)
print('MAX DRAWDOWN CALCULATION')
print('=' * 100)
print(f'\nEquity curve has {len(equity_curve)} points (start + {len(trades)} trades)')
print(f'Highest equity reached: ${running_max.max():.2f}')
print(f'Lowest equity reached: ${eq_series.min():.2f}')
print(f'Max drawdown from peak: {max_dd:.2f}%')

# Show worst drawdown point
worst_idx = drawdown.idxmin()
print(f'\nWorst drawdown occurred at trade #{worst_idx}')
print(f'  Peak before: ${running_max.iloc[worst_idx]:.2f}')
print(f'  Equity at worst: ${eq_series.iloc[worst_idx]:.2f}')
print(f'  Drawdown: {drawdown.iloc[worst_idx]:.2f}%')

print('\n' + '=' * 100)
print('EQUITY CURVE (every trade)')
print('=' * 100)
for i, eq in enumerate(equity_curve):
    peak = running_max.iloc[i]
    dd = drawdown.iloc[i]
    marker = ' ⬇️ WORST DD' if i == worst_idx else ''
    print(f"Trade {i}: ${eq:>9.2f} (Peak: ${peak:>9.2f}, DD: {dd:>7.2f}%){marker}")
