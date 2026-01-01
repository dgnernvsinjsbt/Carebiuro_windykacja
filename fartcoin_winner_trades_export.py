#!/usr/bin/env python3
"""Export FARTCOIN winning config trades to CSV + equity curve"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

print("Loading data...")
df = pd.read_csv('trading/fartcoin_6months_bingx_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
for col in ['open', 'high', 'low', 'close', 'volume']:
    df[col] = df[col].astype(float)

# RSI calculation
delta = df['close'].diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)
avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
rs = avg_gain / avg_loss
df['rsi'] = 100 - (100 / (1 + rs))

# ATR calculation
df['tr'] = np.maximum(df['high'] - df['low'], np.maximum(
    abs(df['high'] - df['close'].shift(1)),
    abs(df['low'] - df['close'].shift(1))
))
df['atr'] = df['tr'].rolling(14).mean()

# Test winning config: RSI>70, 1.0 ATR offset, 10% TP
rsi_trigger = 70
limit_atr_offset = 1.0
tp_pct = 10
lookback = 5
max_wait_bars = 20
equity = 100.0
trades = []
armed = False
signal_idx = None
swing_low = None
limit_pending = False
limit_placed_idx = None
swing_high_for_sl = None

for i in range(lookback, len(df)):
    row = df.iloc[i]
    if pd.isna(row['rsi']) or pd.isna(row['atr']):
        continue

    if row['rsi'] > rsi_trigger:
        armed = True
        signal_idx = i
        swing_low = df.iloc[max(0, i-lookback):i+1]['low'].min()
        limit_pending = False

    if armed and swing_low is not None and not limit_pending:
        if row['low'] < swing_low:
            atr = row['atr']
            limit_price = swing_low + (atr * limit_atr_offset)
            swing_high_for_sl = df.iloc[signal_idx:i+1]['high'].max()
            limit_pending = True
            limit_placed_idx = i
            armed = False

    if limit_pending:
        if i - limit_placed_idx > max_wait_bars:
            limit_pending = False
            continue

        if row['high'] >= limit_price:
            entry_price = limit_price
            sl_price = swing_high_for_sl
            tp_price = entry_price * (1 - tp_pct / 100)
            sl_dist_pct = ((sl_price - entry_price) / entry_price) * 100

            if sl_dist_pct <= 0 or sl_dist_pct > 10:
                limit_pending = False
                continue

            size = (equity * 0.05) / (sl_dist_pct / 100)
            hit_sl = False
            hit_tp = False
            exit_idx = None

            for j in range(i + 1, min(i + 500, len(df))):
                future_row = df.iloc[j]
                if future_row['high'] >= sl_price:
                    hit_sl = True
                    exit_idx = j
                    break
                elif future_row['low'] <= tp_price:
                    hit_tp = True
                    exit_idx = j
                    break

            if hit_sl:
                pnl_pct = -sl_dist_pct
                exit_type = 'SL'
            elif hit_tp:
                pnl_pct = tp_pct
                exit_type = 'TP'
            else:
                continue

            pnl_dollar = size * (pnl_pct / 100) - size * 0.001
            equity += pnl_dollar

            trades.append({
                'trade_num': len(trades) + 1,
                'signal_time': df.iloc[signal_idx]['timestamp'],
                'entry_time': row['timestamp'],
                'exit_time': df.iloc[exit_idx]['timestamp'] if exit_idx else None,
                'rsi_at_signal': df.iloc[signal_idx]['rsi'],
                'swing_low': swing_low,
                'limit_price': limit_price,
                'entry_price': entry_price,
                'sl_price': sl_price,
                'tp_price': tp_price,
                'sl_dist_pct': sl_dist_pct,
                'size': size,
                'exit_type': exit_type,
                'pnl_pct': pnl_pct,
                'pnl_dollar': pnl_dollar,
                'equity_before': equity - pnl_dollar,
                'equity_after': equity
            })
            limit_pending = False

# Create DataFrame and save to CSV
trades_df = pd.DataFrame(trades)
trades_df.to_csv('fartcoin_winner_trades.csv', index=False, float_format='%.4f')

# Generate equity curve
equity_curve = [100.0]
for pnl in trades_df['pnl_dollar']:
    equity_curve.append(equity_curve[-1] + pnl)

# Calculate drawdown
eq_series = pd.Series(equity_curve)
running_max = eq_series.expanding().max()
drawdown = (eq_series - running_max) / running_max * 100

# Plot equity curve
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True)

# Equity curve
ax1.plot(equity_curve, linewidth=2, color='#2E86AB')
ax1.fill_between(range(len(equity_curve)), equity_curve, 100, alpha=0.2, color='#2E86AB')
ax1.axhline(y=100, color='gray', linestyle='--', alpha=0.5, label='Starting Capital')
ax1.set_ylabel('Equity ($)', fontsize=12, fontweight='bold')
ax1.set_title('FARTCOIN RSI>70, 1.0 ATR, 10% TP - Equity Curve', fontsize=14, fontweight='bold')
ax1.grid(True, alpha=0.3)
ax1.legend()

# Add stats box
stats_text = f'Total Return: +{((equity-100)/100)*100:.1f}%\nMax DD: {drawdown.min():.2f}%\nR/DD: {((equity-100)/100)*100/abs(drawdown.min()):.1f}x\nTrades: {len(trades_df)}\nWin Rate: {(len(trades_df[trades_df["pnl_dollar"]>0])/len(trades_df)*100):.1f}%'
ax1.text(0.02, 0.98, stats_text, transform=ax1.transAxes, fontsize=10,
         verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

# Drawdown
ax2.fill_between(range(len(drawdown)), drawdown, 0, alpha=0.3, color='red', where=(drawdown<0))
ax2.plot(drawdown, linewidth=2, color='darkred')
ax2.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
ax2.set_ylabel('Drawdown (%)', fontsize=12, fontweight='bold')
ax2.set_xlabel('Trade Number', fontsize=12, fontweight='bold')
ax2.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('fartcoin_winner_equity_curve.png', dpi=150, bbox_inches='tight')
print(f"\n✅ Saved equity curve to fartcoin_winner_equity_curve.png")

print(f"✅ Exported {len(trades_df)} trades to fartcoin_winner_trades.csv")
print(f"\nSummary:")
print(f"  Total Return: +{((equity-100)/100)*100:.2f}%")
print(f"  Final Equity: ${equity:.2f}")
print(f"  Win Rate: {(len(trades_df[trades_df['pnl_dollar']>0])/len(trades_df)*100):.1f}%")
print(f"  Avg Winner: ${trades_df[trades_df['pnl_dollar']>0]['pnl_dollar'].mean():.2f}")
print(f"  Avg Loser: ${trades_df[trades_df['pnl_dollar']<0]['pnl_dollar'].mean():.2f}")
