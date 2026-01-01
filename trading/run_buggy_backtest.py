"""
Run the EXACT buggy backtest code to see the 2.77% drawdown
"""
import pandas as pd
import numpy as np

def calculate_rsi(prices, period=14):
    deltas = np.diff(prices)
    seed = deltas[:period+1]
    up = seed[seed >= 0].sum() / period
    down = -seed[seed < 0].sum() / period
    rs = up / down if down != 0 else 0
    rsi = np.zeros_like(prices)
    rsi[:period] = 100. - 100. / (1. + rs)

    for i in range(period, len(prices)):
        delta = deltas[i - 1]
        upval = delta if delta > 0 else 0
        downval = -delta if delta < 0 else 0
        up = (up * (period - 1) + upval) / period
        down = (down * (period - 1) + downval) / period
        rs = up / down if down != 0 else 0
        rsi[i] = 100. - 100. / (1. + rs)
    return rsi

def calculate_atr(df, period=14):
    high = df['high'].values
    low = df['low'].values
    close = df['close'].values
    tr = np.maximum(high - low, np.maximum(np.abs(high - np.roll(close, 1)), np.abs(low - np.roll(close, 1))))
    tr[0] = high[0] - low[0]
    atr = np.zeros_like(tr)
    atr[period-1] = np.mean(tr[:period])
    for i in range(period, len(tr)):
        atr[i] = (atr[i-1] * (period - 1) + tr[i]) / period
    return atr

def buggy_backtest(df, rsi_low=27, rsi_high=65, limit_offset_pct=1.0, max_hold_bars=3):
    """
    EXACT BUGGY CODE from backtest_all_10_strategies.py
    - No stop loss checking
    - No take profit checking
    - Only RSI and time exits
    """
    df = df.copy()
    df['rsi'] = calculate_rsi(df['close'].values, 14)
    df['atr'] = calculate_atr(df, 14)

    trades = []
    in_position = False
    entry_bar = None
    entry_price = None
    side = None

    for i in range(20, len(df)):
        current = df.iloc[i]
        prev = df.iloc[i-1]

        if pd.isna(current['rsi']) or pd.isna(current['atr']):
            continue

        # Exit logic (BUGGY - no stops!)
        if in_position:
            bars_held = i - entry_bar
            exit_reason = None
            exit_price = None

            # RSI exit
            if side == 'LONG' and current['rsi'] < rsi_high and prev['rsi'] >= rsi_high:
                exit_reason = 'RSI exit'
                exit_price = current['close']
            elif side == 'SHORT' and current['rsi'] > rsi_low and prev['rsi'] <= rsi_low:
                exit_reason = 'RSI exit'
                exit_price = current['close']

            # Time exit
            elif bars_held >= max_hold_bars:
                exit_reason = 'Time exit'
                exit_price = current['close']

            # ❌ NO STOP LOSS CHECK HERE!
            # ❌ NO TAKE PROFIT CHECK HERE!

            if exit_reason:
                pnl_pct = ((exit_price / entry_price) - 1) * 100 if side == 'LONG' else ((entry_price / exit_price) - 1) * 100

                trades.append({
                    'entry_bar': entry_bar,
                    'entry_time': df.iloc[entry_bar]['timestamp'],
                    'exit_bar': i,
                    'exit_time': current['timestamp'],
                    'side': side,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl_pct': pnl_pct,
                    'exit_reason': exit_reason,
                    'bars_held': bars_held
                })
                in_position = False

        # Entry logic
        if not in_position:
            # LONG signal
            if current['rsi'] > rsi_low and prev['rsi'] <= rsi_low:
                signal_price = current['close']
                limit_price = signal_price * (1 - limit_offset_pct / 100)

                # Check if limit fills in next 5 bars
                for j in range(i+1, min(i+6, len(df))):
                    if df.iloc[j]['low'] <= limit_price:
                        in_position = True
                        entry_bar = j
                        entry_price = limit_price
                        side = 'LONG'
                        break

            # SHORT signal
            elif current['rsi'] < rsi_high and prev['rsi'] >= rsi_high:
                signal_price = current['close']
                limit_price = signal_price * (1 + limit_offset_pct / 100)

                for j in range(i+1, min(i+6, len(df))):
                    if df.iloc[j]['high'] >= limit_price:
                        in_position = True
                        entry_bar = j
                        entry_price = limit_price
                        side = 'SHORT'
                        break

    return pd.DataFrame(trades)

# Load data
df = pd.read_csv('bingx-trading-bot/trading/crv_usdt_90d_1h.csv')
df['time'] = pd.to_datetime(df['timestamp'])

print('='*100)
print('🐛 BUGGY BACKTEST RESULTS (No stops, 3-hour time exit)')
print('='*100)
print()

trades = buggy_backtest(df, rsi_low=27, rsi_high=65, limit_offset_pct=1.0, max_hold_bars=3)
trades['cumulative'] = trades['pnl_pct'].cumsum()

# Calculate drawdown
trades['peak'] = trades['cumulative'].cummax()
trades['drawdown'] = trades['cumulative'] - trades['peak']

total_return = trades['cumulative'].iloc[-1]
max_dd = trades['drawdown'].min()
win_rate = (trades['pnl_pct'] > 0).sum() / len(trades) * 100

print(f'Total Trades: {len(trades)}')
print(f'Win Rate: {win_rate:.1f}%')
print(f'Total Return: +{total_return:.2f}%')
print(f'Max Drawdown: {max_dd:.2f}%')
print(f'Return/DD Ratio: {abs(total_return / max_dd):.2f}x')
print()

# Exit reason breakdown
print('Exit Reason Breakdown:')
for reason, count in trades['exit_reason'].value_counts().items():
    pct = count / len(trades) * 100
    print(f'  {reason}: {count} ({pct:.1f}%)')
print()

# Find drawdown sequence
max_dd_idx = trades['drawdown'].idxmin()
peak_idx = trades.loc[:max_dd_idx, 'cumulative'].idxmax()

print('='*100)
print('📉 DRAWDOWN SEQUENCE (Peak to Trough)')
print('='*100)
print()
print(f'Peak: +{trades.loc[peak_idx, "cumulative"]:.2f}% (after trade #{peak_idx + 1})')
print(f'Trough: +{trades.loc[max_dd_idx, "cumulative"]:.2f}% (after trade #{max_dd_idx + 1})')
print(f'Drawdown: {max_dd:.2f}%')
print()

drawdown_trades = trades.loc[peak_idx:max_dd_idx]
print(f'{"#":<5} {"Time":<20} {"Side":<6} {"P&L":<10} {"Cumulative":<12} {"Exit Reason":<15}')
print('-'*100)

for idx, row in drawdown_trades.iterrows():
    print(f'{idx+1:<5} {row["entry_time"]:<20} {row["side"]:<6} {row["pnl_pct"]:>8.2f}% {row["cumulative"]:>10.2f}% {row["exit_reason"]:<15}')

# Save results
trades.to_csv('buggy_backtest_trades.csv', index=False)
print()
print('💾 Saved: buggy_backtest_trades.csv')
