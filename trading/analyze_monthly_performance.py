"""
Month-by-month breakdown for best config:
25/68, 0.3% limit, 3.0x SL, 2.0x TP
"""

import pandas as pd
import numpy as np

print("=" * 80)
print("Monthly Performance: 25/68 | 0.3% | 3.0x SL | 2.0x TP")
print("=" * 80)

# Load combined dataset
df_july = pd.read_csv('trading/melania_usdt_july_aug_2025_1h.csv', parse_dates=['timestamp'])
df_sepdec = pd.read_csv('bingx-trading-bot/trading/melania_usdt_90d_1h.csv', parse_dates=['timestamp'])
df_sepdec = df_sepdec[(df_sepdec['timestamp'] >= '2025-09-15') & (df_sepdec['timestamp'] < '2025-12-08')]

df_july['timestamp'] = pd.to_datetime(df_july['timestamp']).dt.tz_localize(None)
df_sepdec['timestamp'] = pd.to_datetime(df_sepdec['timestamp']).dt.tz_localize(None)

df = pd.concat([df_july, df_sepdec]).sort_values('timestamp').reset_index(drop=True)

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

# Best config params
RSI_LOW = 25
RSI_HIGH = 68
LIMIT_PCT = 0.3
SL_MULT = 3.0
TP_MULT = 2.0

trades = []
equity = 100.0
equity_curve = []
equity_dates = []

i = 14
while i < len(df):
    row = df.iloc[i]
    prev_row = df.iloc[i-1] if i > 0 else None

    if pd.isna(row['rsi']) or pd.isna(row['atr']) or prev_row is None or pd.isna(prev_row['rsi']):
        i += 1
        continue

    # LONG: RSI crosses UP through rsi_low
    if prev_row['rsi'] < RSI_LOW and row['rsi'] >= RSI_LOW:
        signal_price = row['close']
        entry_price = signal_price * (1 + LIMIT_PCT / 100)
        sl_price = entry_price - (row['atr'] * SL_MULT)
        tp_price = entry_price + (row['atr'] * TP_MULT)

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
        exit_type = None

        for k in range(fill_idx + 1, len(df)):
            bar = df.iloc[k]
            prev_bar = df.iloc[k-1]

            if bar['low'] <= sl_price:
                exit_idx, exit_price, exit_type = k, sl_price, 'SL'
                break
            if bar['high'] >= tp_price:
                exit_idx, exit_price, exit_type = k, tp_price, 'TP'
                break
            if not pd.isna(bar['rsi']) and not pd.isna(prev_bar['rsi']):
                if prev_bar['rsi'] > RSI_HIGH and bar['rsi'] <= RSI_HIGH:
                    exit_idx, exit_price, exit_type = k, bar['close'], 'OPPOSITE'
                    break

        if exit_idx is None:
            i += 1
            continue

        pnl_pct = ((exit_price - entry_price) / entry_price) * 100 - 0.10
        equity_before = equity
        equity += equity * (pnl_pct / 100)

        trades.append({
            'entry_time': df.iloc[fill_idx]['timestamp'],
            'exit_time': df.iloc[exit_idx]['timestamp'],
            'direction': 'LONG',
            'exit_type': exit_type,
            'pnl_pct': pnl_pct,
            'pnl_dollars': equity - equity_before,
            'equity': equity,
            'month': df.iloc[exit_idx]['timestamp'].strftime('%Y-%m')
        })

        equity_curve.append(equity)
        equity_dates.append(df.iloc[exit_idx]['timestamp'])
        i = exit_idx + 1
        continue

    # SHORT: RSI crosses DOWN through rsi_high
    if prev_row['rsi'] > RSI_HIGH and row['rsi'] <= RSI_HIGH:
        signal_price = row['close']
        entry_price = signal_price * (1 - LIMIT_PCT / 100)
        sl_price = entry_price + (row['atr'] * SL_MULT)
        tp_price = entry_price - (row['atr'] * TP_MULT)

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
        exit_type = None

        for k in range(fill_idx + 1, len(df)):
            bar = df.iloc[k]
            prev_bar = df.iloc[k-1]

            if bar['high'] >= sl_price:
                exit_idx, exit_price, exit_type = k, sl_price, 'SL'
                break
            if bar['low'] <= tp_price:
                exit_idx, exit_price, exit_type = k, tp_price, 'TP'
                break
            if not pd.isna(bar['rsi']) and not pd.isna(prev_bar['rsi']):
                if prev_bar['rsi'] < RSI_LOW and bar['rsi'] >= RSI_LOW:
                    exit_idx, exit_price, exit_type = k, bar['close'], 'OPPOSITE'
                    break

        if exit_idx is None:
            i += 1
            continue

        pnl_pct = ((entry_price - exit_price) / entry_price) * 100 - 0.10
        equity_before = equity
        equity += equity * (pnl_pct / 100)

        trades.append({
            'entry_time': df.iloc[fill_idx]['timestamp'],
            'exit_time': df.iloc[exit_idx]['timestamp'],
            'direction': 'SHORT',
            'exit_type': exit_type,
            'pnl_pct': pnl_pct,
            'pnl_dollars': equity - equity_before,
            'equity': equity,
            'month': df.iloc[exit_idx]['timestamp'].strftime('%Y-%m')
        })

        equity_curve.append(equity)
        equity_dates.append(df.iloc[exit_idx]['timestamp'])
        i = exit_idx + 1
        continue

    i += 1

# Analyze by month
df_trades = pd.DataFrame(trades)

print(f"\nTotal Performance:")
print(f"  Starting Equity: $100")
print(f"  Final Equity: ${equity:.2f}")
print(f"  Total Return: +{((equity - 100) / 100) * 100:.2f}%")
print(f"  Total Trades: {len(df_trades)}")

print("\n" + "=" * 80)
print("MONTH-BY-MONTH BREAKDOWN:")
print("=" * 80)

months = df_trades.groupby('month')

start_equity = 100.0
for month, group in months:
    month_start_equity = start_equity
    month_end_equity = group.iloc[-1]['equity']
    month_return = ((month_end_equity - month_start_equity) / month_start_equity) * 100

    winners = (group['pnl_pct'] > 0).sum()
    losers = (group['pnl_pct'] < 0).sum()
    win_rate = (winners / len(group)) * 100

    # Calculate month drawdown
    month_equity_curve = [month_start_equity] + group['equity'].tolist()
    month_eq = pd.Series(month_equity_curve)
    running_max = month_eq.expanding().max()
    dd = ((month_eq - running_max) / running_max * 100).min()

    # Exit breakdown
    tp_count = (group['exit_type'] == 'TP').sum()
    sl_count = (group['exit_type'] == 'SL').sum()
    opp_count = (group['exit_type'] == 'OPPOSITE').sum()

    print(f"\n{month}:")
    print(f"  Equity: ${month_start_equity:.2f} → ${month_end_equity:.2f}")
    print(f"  Return: {month_return:+.2f}%")
    print(f"  Max DD: {dd:.2f}%")
    print(f"  Trades: {len(group)} ({winners}W / {losers}L)")
    print(f"  Win Rate: {win_rate:.1f}%")
    print(f"  Exits: {tp_count} TP | {sl_count} SL | {opp_count} OPP")

    # Show best and worst trades
    best_trade = group.loc[group['pnl_pct'].idxmax()]
    worst_trade = group.loc[group['pnl_pct'].idxmin()]

    print(f"  Best Trade: {best_trade['direction']} {best_trade['pnl_pct']:+.2f}% ({best_trade['exit_type']})")
    print(f"  Worst Trade: {worst_trade['direction']} {worst_trade['pnl_pct']:+.2f}% ({worst_trade['exit_type']})")

    start_equity = month_end_equity

print("\n" + "=" * 80)
print("SUMMARY:")
print("=" * 80)

monthly_returns = []
for month, group in months:
    month_start = equity_curve[0] if month == '2025-07' else df_trades[df_trades['month'] < month].iloc[-1]['equity'] if len(df_trades[df_trades['month'] < month]) > 0 else 100
    month_end = group.iloc[-1]['equity']
    monthly_returns.append(((month_end - month_start) / month_start) * 100)

print(f"\nConsistency Metrics:")
print(f"  Positive Months: {sum(1 for r in monthly_returns if r > 0)} out of {len(monthly_returns)}")
print(f"  Average Monthly Return: {np.mean(monthly_returns):+.2f}%")
print(f"  Std Dev of Monthly Returns: {np.std(monthly_returns):.2f}%")
print(f"  Best Month: {max(monthly_returns):+.2f}%")
print(f"  Worst Month: {min(monthly_returns):+.2f}%")

print("\n" + "=" * 80)
