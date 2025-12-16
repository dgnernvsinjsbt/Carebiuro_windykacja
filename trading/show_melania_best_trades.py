"""
Show actual trades for best MELANIA configuration on July-Aug 2025
Config: 30/65, 0.5%, 2.0x SL, 1.0x TP, 5h hold
"""

import pandas as pd
import numpy as np

print("=" * 80)
print("MELANIA-USDT: Best Config Trades on July-Aug 2025")
print("Config: RSI 30/65 | Limit 0.5% | SL 2.0x | TP 1.0x | Hold 5h")
print("=" * 80)

# Load data
df = pd.read_csv('trading/melania_usdt_july_aug_2025_1h.csv', parse_dates=['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# Calculate indicators
delta = df['close'].diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)
avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
rs = avg_gain / avg_loss
df['rsi'] = 100 - (100 / (1 + rs))

df['tr'] = np.maximum(
    df['high'] - df['low'],
    np.maximum(
        abs(df['high'] - df['close'].shift(1)),
        abs(df['low'] - df['close'].shift(1))
    )
)
df['atr'] = df['tr'].rolling(14).mean()

# Best parameters
RSI_LOW = 30
RSI_HIGH = 65
LIMIT_PCT = 0.5
SL_MULT = 2.0
TP_MULT = 1.0
MAX_HOLD = 5

trades = []
equity = 100.0
equity_curve = [equity]

i = 14
while i < len(df):
    row = df.iloc[i]

    if pd.isna(row['rsi']) or pd.isna(row['atr']):
        i += 1
        continue

    direction = None
    if row['rsi'] < RSI_LOW:
        direction = 'LONG'
    elif row['rsi'] > RSI_HIGH:
        direction = 'SHORT'

    if direction is None:
        i += 1
        continue

    if direction == 'LONG':
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
        exit_type = 'TIME'

        for k in range(fill_idx + 1, min(fill_idx + MAX_HOLD + 1, len(df))):
            bar = df.iloc[k]
            if bar['low'] <= sl_price:
                exit_idx, exit_price, exit_type = k, sl_price, 'SL'
                break
            if bar['high'] >= tp_price:
                exit_idx, exit_price, exit_type = k, tp_price, 'TP'
                break

        if exit_idx is None:
            exit_idx = min(fill_idx + MAX_HOLD, len(df) - 1)
            exit_price = df.iloc[exit_idx]['close']
            exit_type = 'TIME'

        pnl_pct = ((exit_price - entry_price) / entry_price) * 100 - 0.10
        equity += equity * (pnl_pct / 100)

        trades.append({
            'entry_time': df.iloc[fill_idx]['timestamp'],
            'exit_time': df.iloc[exit_idx]['timestamp'],
            'direction': 'LONG',
            'rsi_signal': row['rsi'],
            'signal_price': signal_price,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'exit_type': exit_type,
            'pnl_pct': pnl_pct,
            'equity': equity,
            'duration_hours': exit_idx - fill_idx
        })

        equity_curve.append(equity)
        i = exit_idx + 1

    elif direction == 'SHORT':
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
        exit_type = 'TIME'

        for k in range(fill_idx + 1, min(fill_idx + MAX_HOLD + 1, len(df))):
            bar = df.iloc[k]
            if bar['high'] >= sl_price:
                exit_idx, exit_price, exit_type = k, sl_price, 'SL'
                break
            if bar['low'] <= tp_price:
                exit_idx, exit_price, exit_type = k, tp_price, 'TP'
                break

        if exit_idx is None:
            exit_idx = min(fill_idx + MAX_HOLD, len(df) - 1)
            exit_price = df.iloc[exit_idx]['close']
            exit_type = 'TIME'

        pnl_pct = ((entry_price - exit_price) / entry_price) * 100 - 0.10
        equity += equity * (pnl_pct / 100)

        trades.append({
            'entry_time': df.iloc[fill_idx]['timestamp'],
            'exit_time': df.iloc[exit_idx]['timestamp'],
            'direction': 'SHORT',
            'rsi_signal': row['rsi'],
            'signal_price': signal_price,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'exit_type': exit_type,
            'pnl_pct': pnl_pct,
            'equity': equity,
            'duration_hours': exit_idx - fill_idx
        })

        equity_curve.append(equity)
        i = exit_idx + 1

    else:
        i += 1

# Print results
df_trades = pd.DataFrame(trades)

print(f"\nTotal Trades: {len(df_trades)}")
print(f"Final Equity: ${equity:.2f} (started with $100)")

# Statistics
winners = (df_trades['pnl_pct'] > 0).sum()
losers = (df_trades['pnl_pct'] < 0).sum()
win_rate = (winners / len(df_trades)) * 100

avg_winner = df_trades[df_trades['pnl_pct'] > 0]['pnl_pct'].mean()
avg_loser = df_trades[df_trades['pnl_pct'] < 0]['pnl_pct'].mean()

tp_count = (df_trades['exit_type'] == 'TP').sum()
sl_count = (df_trades['exit_type'] == 'SL').sum()
time_count = (df_trades['exit_type'] == 'TIME').sum()

print(f"\nWinners: {winners} ({win_rate:.1f}%)")
print(f"Losers: {losers} ({100-win_rate:.1f}%)")
print(f"Avg Winner: {avg_winner:+.2f}%")
print(f"Avg Loser: {avg_loser:+.2f}%")

print(f"\nExit Types:")
print(f"  TP: {tp_count} ({tp_count/len(df_trades)*100:.1f}%)")
print(f"  SL: {sl_count} ({sl_count/len(df_trades)*100:.1f}%)")
print(f"  TIME: {time_count} ({time_count/len(df_trades)*100:.1f}%)")

print(f"\nAvg Duration: {df_trades['duration_hours'].mean():.1f} hours")

# Equity curve stats
eq_series = pd.Series(equity_curve)
running_max = eq_series.expanding().max()
drawdown = (eq_series - running_max) / running_max * 100
max_dd = drawdown.min()

print(f"Max Drawdown: {max_dd:.2f}%")

# Show all trades
print("\n" + "=" * 80)
print("TRADE LOG:")
print("=" * 80)

for idx, trade in df_trades.iterrows():
    profit_emoji = "✅" if trade['pnl_pct'] > 0 else "❌"

    print(f"\n{profit_emoji} Trade #{idx+1} - {trade['direction']}")
    print(f"   Entry: {trade['entry_time'].strftime('%Y-%m-%d %H:%M')} | "
          f"RSI: {trade['rsi_signal']:.1f} | Price: ${trade['entry_price']:.6f}")
    print(f"   Exit:  {trade['exit_time'].strftime('%Y-%m-%d %H:%M')} | "
          f"Type: {trade['exit_type']} | Price: ${trade['exit_price']:.6f}")
    print(f"   P&L: {trade['pnl_pct']:+.2f}% | Duration: {trade['duration_hours']}h | "
          f"Equity: ${trade['equity']:.2f}")

# Show equity progression
print("\n" + "=" * 80)
print("EQUITY PROGRESSION:")
print("=" * 80)

milestones = [0, len(df_trades)//4, len(df_trades)//2, 3*len(df_trades)//4, len(df_trades)-1]
for i in milestones:
    if i < len(df_trades):
        print(f"After trade {i+1}: ${df_trades.iloc[i]['equity']:.2f}")

print("\n" + "=" * 80)
