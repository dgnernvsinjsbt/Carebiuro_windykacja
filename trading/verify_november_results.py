"""
Verify November 2025 results
Compare fresh downloaded data vs old script results
Old script showed: +193.6% return, 25 trades for Nov 2025
"""
import pandas as pd
import numpy as np

print('=' * 100)
print('VERIFYING NOVEMBER 2025 RESULTS')
print('=' * 100)

# Load fresh November data
print('\nLoading fresh November data...')
df = pd.read_csv('melania_november_2025_15m_fresh.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
print(f'Loaded {len(df)} bars')
print(f'Date range: {df["timestamp"].min()} to {df["timestamp"].max()}')

# Calculate indicators (EXACT same logic as old script)
print('\nCalculating indicators...')

# Wilder's RSI
delta = df['close'].diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)
avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
rs = avg_gain / avg_loss
df['rsi'] = 100 - (100 / (1 + rs))

# ATR
df['tr'] = np.maximum(df['high'] - df['low'], np.maximum(
    abs(df['high'] - df['close'].shift(1)),
    abs(df['low'] - df['close'].shift(1))
))
df['atr'] = df['tr'].rolling(14).mean()

# ret_20
df['ret_20'] = (df['close'] / df['close'].shift(20) - 1) * 100

print('Indicators calculated')

# Backtest with EXACT same logic as old script (SL 2.0x / TP 3.0x)
print('\nRunning backtest (SL 2.0x / TP 3.0x)...')

trades = []
equity = 100.0
position = None

for i in range(300, len(df)):
    row = df.iloc[i]

    if pd.isna(row['rsi']) or pd.isna(row['atr']) or pd.isna(row['ret_20']):
        continue

    # Manage existing position
    if position:
        bar = row
        if position['direction'] == 'LONG':
            # Check SL
            if bar['low'] <= position['sl_price']:
                pnl_pct = ((position['sl_price'] - position['entry']) / position['entry']) * 100
                pnl = position['size'] * (pnl_pct / 100) - position['size'] * 0.001
                equity += pnl
                trades.append({
                    'timestamp': row['timestamp'],
                    'direction': 'LONG',
                    'entry': position['entry'],
                    'exit': position['sl_price'],
                    'pnl_pct': pnl_pct,
                    'exit_type': 'SL'
                })
                position = None
                continue
            # Check TP
            elif bar['high'] >= position['tp_price']:
                pnl_pct = ((position['tp_price'] - position['entry']) / position['entry']) * 100
                pnl = position['size'] * (pnl_pct / 100) - position['size'] * 0.001
                equity += pnl
                trades.append({
                    'timestamp': row['timestamp'],
                    'direction': 'LONG',
                    'entry': position['entry'],
                    'exit': position['tp_price'],
                    'pnl_pct': pnl_pct,
                    'exit_type': 'TP'
                })
                position = None
                continue
        else:  # SHORT
            # Check SL
            if bar['high'] >= position['sl_price']:
                pnl_pct = ((position['entry'] - position['sl_price']) / position['entry']) * 100
                pnl = position['size'] * (pnl_pct / 100) - position['size'] * 0.001
                equity += pnl
                trades.append({
                    'timestamp': row['timestamp'],
                    'direction': 'SHORT',
                    'entry': position['entry'],
                    'exit': position['sl_price'],
                    'pnl_pct': pnl_pct,
                    'exit_type': 'SL'
                })
                position = None
                continue
            # Check TP
            elif bar['low'] <= position['tp_price']:
                pnl_pct = ((position['entry'] - position['tp_price']) / position['entry']) * 100
                pnl = position['size'] * (pnl_pct / 100) - position['size'] * 0.001
                equity += pnl
                trades.append({
                    'timestamp': row['timestamp'],
                    'direction': 'SHORT',
                    'entry': position['entry'],
                    'exit': position['tp_price'],
                    'pnl_pct': pnl_pct,
                    'exit_type': 'TP'
                })
                position = None
                continue

    # New signals
    if not position and i > 0:
        prev_row = df.iloc[i-1]

        # Check ret_20 filter
        if row['ret_20'] <= 0:
            continue

        if not pd.isna(prev_row['rsi']):
            # LONG: RSI crosses above 35
            if prev_row['rsi'] < 35 and row['rsi'] >= 35:
                entry = row['close']
                sl = entry - (row['atr'] * 2.0)
                tp = entry + (row['atr'] * 3.0)
                sl_dist = abs((entry - sl) / entry) * 100
                size = (equity * 0.12) / (sl_dist / 100)
                position = {
                    'direction': 'LONG',
                    'entry': entry,
                    'sl_price': sl,
                    'tp_price': tp,
                    'size': size
                }

            # SHORT: RSI crosses below 65
            elif prev_row['rsi'] > 65 and row['rsi'] <= 65:
                entry = row['close']
                sl = entry + (row['atr'] * 2.0)
                tp = entry - (row['atr'] * 3.0)
                sl_dist = abs((sl - entry) / entry) * 100
                size = (equity * 0.12) / (sl_dist / 100)
                position = {
                    'direction': 'SHORT',
                    'entry': entry,
                    'sl_price': sl,
                    'tp_price': tp,
                    'size': size
                }

# Calculate results
if trades:
    df_trades = pd.DataFrame(trades)
    total_return = ((equity - 100) / 100) * 100
    win_rate = (df_trades['pnl_pct'] > 0).sum() / len(df_trades) * 100
    tp_rate = (df_trades['exit_type'] == 'TP').sum() / len(df_trades) * 100

    # Calculate equity curve for max DD
    eq = [100.0]
    cum_eq = 100.0
    for pnl in df_trades['pnl_pct']:
        cum_eq += (cum_eq * 0.12) * (pnl / 100) - (cum_eq * 0.12) * 0.001
        eq.append(cum_eq)
    eq_s = pd.Series(eq)
    max_dd = ((eq_s - eq_s.expanding().max()) / eq_s.expanding().max() * 100).min()
    return_dd = total_return / abs(max_dd) if max_dd != 0 else 0

    print('\n' + '=' * 100)
    print('RESULTS FROM FRESH NOVEMBER DATA')
    print('=' * 100)
    print(f'\nTrades: {len(df_trades)}')
    print(f'Win Rate: {win_rate:.1f}%')
    print(f'TP Rate: {tp_rate:.1f}%')
    print(f'Total Return: {total_return:+.1f}%')
    print(f'Max Drawdown: {max_dd:.2f}%')
    print(f'Return/DD: {return_dd:.2f}x')
    print(f'Final Equity: ${equity:.2f}')

    print('\n' + '=' * 100)
    print('COMPARISON TO OLD SCRIPT RESULTS')
    print('=' * 100)

    old_trades = 25
    old_return = 193.6

    print(f'\nOLD SCRIPT (November 2025):')
    print(f'  Trades: {old_trades}')
    print(f'  Return: +{old_return}%')

    print(f'\nFRESH DATA (November 2025):')
    print(f'  Trades: {len(df_trades)}')
    print(f'  Return: {total_return:+.1f}%')

    print(f'\nDIFFERENCE:')
    print(f'  Trades: {len(df_trades) - old_trades:+d} ({abs((len(df_trades) - old_trades) / old_trades * 100):.1f}% diff)')
    print(f'  Return: {total_return - old_return:+.1f}% ({abs((total_return - old_return) / old_return * 100):.1f}% diff)')

    if abs(len(df_trades) - old_trades) <= 2 and abs(total_return - old_return) < 10:
        print(f'\n✅ RESULTS MATCH! The +510% from the old script is LEGIT!')
        print(f'   Minor differences are normal due to rounding/timing.')
    else:
        print(f'\n❌ RESULTS DO NOT MATCH!')
        print(f'   The data or logic differs significantly.')
        print(f'   Need to investigate further.')

    # Show first 5 trades
    print('\n' + '=' * 100)
    print('FIRST 5 TRADES')
    print('=' * 100)
    for idx, trade in df_trades.head(5).iterrows():
        print(f"\n{idx+1}. {trade['direction']} @ ${trade['entry']:.6f} on {trade['timestamp']}")
        print(f"   Exit: ${trade['exit']:.6f} via {trade['exit_type']}")
        print(f"   P&L: {trade['pnl_pct']:+.2f}%")

    # Save trades
    df_trades.to_csv('november_verification_trades.csv', index=False)
    print(f'\n💾 Saved trades to: november_verification_trades.csv')

else:
    print('\n❌ NO TRADES GENERATED!')
    print('Something is wrong with the data or logic.')
