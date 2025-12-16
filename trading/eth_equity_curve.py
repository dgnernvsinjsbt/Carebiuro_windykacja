#!/usr/bin/env python3
"""
Generate equity curve for optimized ETH strategy
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

def calculate_atr(high, low, close, period=14):
    tr = pd.concat([
        high - low,
        abs(high - close.shift()),
        abs(low - close.shift())
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def calculate_ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# Load data
df = pd.read_csv('eth_usdt_60d_bingx.csv')
df.columns = df.columns.str.lower()
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# Calculate indicators
df['atr'] = calculate_atr(df['high'], df['low'], df['close'])
df['atr_ma'] = df['atr'].rolling(20).mean()
df['atr_ratio'] = df['atr'] / df['atr_ma']
df['ema20'] = calculate_ema(df['close'], 20)
df['distance'] = abs((df['close'] - df['ema20']) / df['ema20'] * 100)
df['bullish'] = df['close'] > df['open']

# Calculate daily RSI
df_daily = df.set_index('timestamp').resample('1D').agg({
    'open': 'first',
    'high': 'max',
    'low': 'min',
    'close': 'last',
    'volume': 'sum'
}).dropna()

df_daily['rsi_daily'] = calculate_rsi(df_daily['close'], 14)

df = df.set_index('timestamp')
df = df.join(df_daily[['rsi_daily']], how='left')
df = df.ffill()
df = df.reset_index()

# Final optimized params
params = {
    'atr_mult': 1.2,
    'ema_dist': 1.5,
    'tp_mult': 18,
    'sl_mult': 1.0,
    'limit_offset': 0.6
}

print("=" * 80)
print("ETH OPTIMIZED STRATEGY - EQUITY CURVE")
print("=" * 80)
print(f"\nConfig: ATR {params['atr_mult']}x, EMA {params['ema_dist']}%, TP {params['tp_mult']}x, SL {params['sl_mult']}x, Limit {params['limit_offset']}%")

# Generate signals
signals = []
for i in range(len(df)):
    row = df.iloc[i]
    
    if (row['atr_ratio'] > params['atr_mult'] and
        row['distance'] < params['ema_dist'] and
        row['bullish'] and
        not pd.isna(row['rsi_daily']) and
        row['rsi_daily'] > 50):
        signals.append(i)

print(f"\nSignals: {len(signals)}")

# Backtest
trades = []

for signal_idx in signals:
    if signal_idx >= len(df) - 1:
        continue
    
    signal_price = df['close'].iloc[signal_idx]
    signal_atr = df['atr'].iloc[signal_idx]
    
    if pd.isna(signal_atr) or signal_atr == 0:
        continue
    
    # Limit order
    limit_price = signal_price * (1 + params['limit_offset'] / 100)
    
    # Try to fill
    filled = False
    fill_idx = None
    
    for i in range(signal_idx + 1, min(signal_idx + 4, len(df))):
        if df['high'].iloc[i] >= limit_price:
            filled = True
            fill_idx = i
            break
    
    if not filled:
        continue
    
    # Trade filled
    entry_price = limit_price
    entry_time = df['timestamp'].iloc[fill_idx]
    entry_atr = df['atr'].iloc[fill_idx]
    
    sl_price = entry_price - (params['sl_mult'] * entry_atr)
    tp_price = entry_price + (params['tp_mult'] * entry_atr)
    
    # Find exit
    exit_idx = None
    exit_price = None
    exit_reason = None
    
    for i in range(fill_idx + 1, min(fill_idx + 200, len(df))):
        if df['low'].iloc[i] <= sl_price:
            exit_idx = i
            exit_price = sl_price
            exit_reason = 'SL'
            break
        if df['high'].iloc[i] >= tp_price:
            exit_idx = i
            exit_price = tp_price
            exit_reason = 'TP'
            break
    
    if exit_idx is None:
        exit_idx = min(fill_idx + 199, len(df) - 1)
        exit_price = df['close'].iloc[exit_idx]
        exit_reason = 'TIME'
    
    exit_time = df['timestamp'].iloc[exit_idx]
    pnl_pct = (exit_price - entry_price) / entry_price * 100 - 0.10
    
    trades.append({
        'entry_time': entry_time,
        'exit_time': exit_time,
        'entry_price': entry_price,
        'exit_price': exit_price,
        'pnl_pct': pnl_pct,
        'exit_reason': exit_reason
    })

print(f"Trades: {len(trades)}")

# Create equity curve
df_trades = pd.DataFrame(trades)
df_trades['cumulative'] = df_trades['pnl_pct'].cumsum()
df_trades['equity'] = 100 + df_trades['cumulative']
df_trades['peak'] = df_trades['equity'].cummax()
df_trades['drawdown'] = ((df_trades['equity'] - df_trades['peak']) / df_trades['peak'] * 100)

# Stats
total_return = df_trades['pnl_pct'].sum()
max_dd = df_trades['drawdown'].min()
rdd = total_return / abs(max_dd)
wr = (df_trades['pnl_pct'] > 0).mean() * 100
tp_rate = (df_trades['exit_reason'] == 'TP').sum() / len(df_trades) * 100

print(f"\nReturn: {total_return:+.2f}%")
print(f"Max DD: {max_dd:.2f}%")
print(f"R/DD: {rdd:.2f}x")
print(f"Win Rate: {wr:.1f}%")
print(f"TP Rate: {tp_rate:.1f}%")

# Save trades
df_trades.to_csv('results/eth_optimized_trades.csv', index=False)
print(f"\n✅ Trades saved to: results/eth_optimized_trades.csv")

# Create visualization
fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 10), gridspec_kw={'height_ratios': [3, 1, 1]})
fig.suptitle('ETH-USDT Optimized Strategy\nATR 1.2x | EMA 1.5% | TP 18x | SL 1.0x | 60 Days',
             fontsize=16, fontweight='bold')

# === SUBPLOT 1: Equity Curve ===
ax1.plot(df_trades['entry_time'], df_trades['equity'], linewidth=2, color='#1565C0', label='Equity')
ax1.fill_between(df_trades['entry_time'], 100, df_trades['equity'], alpha=0.3, color='#42A5F5')
ax1.axhline(y=100, color='gray', linestyle='--', alpha=0.5, label='Starting Capital')

# Mark wins and losses
wins = df_trades[df_trades['pnl_pct'] > 0]
losses = df_trades[df_trades['pnl_pct'] <= 0]

ax1.scatter(wins['entry_time'], wins['equity'], color='green', s=50, alpha=0.7, marker='^', label='Winner', zorder=5)
ax1.scatter(losses['entry_time'], losses['equity'], color='red', s=50, alpha=0.7, marker='v', label='Loser', zorder=5)

# Mark TP hits
tps = df_trades[df_trades['exit_reason'] == 'TP']
if len(tps) > 0:
    ax1.scatter(tps['entry_time'], tps['equity'], color='gold', s=100, alpha=0.9, marker='*', label='TP Hit', zorder=6)

ax1.set_ylabel('Equity ($)', fontsize=12, fontweight='bold')
ax1.grid(True, alpha=0.3)
ax1.legend(loc='upper left', fontsize=10)
ax1.set_ylim(95, df_trades['equity'].max() * 1.05)

# Add stats box
stats_text = f"""Trades: {len(df_trades)}
Win Rate: {wr:.1f}%
TP Rate: {tp_rate:.1f}%
SL Rate: {(df_trades['exit_reason'] == 'SL').sum() / len(df_trades) * 100:.1f}%
Return: {total_return:+.2f}%
Max DD: {max_dd:.2f}%
R/DD: {rdd:.2f}x"""

ax1.text(0.98, 0.05, stats_text, transform=ax1.transAxes,
         fontsize=10, verticalalignment='bottom', horizontalalignment='right',
         bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

# === SUBPLOT 2: Drawdown ===
ax2.fill_between(df_trades['entry_time'], 0, df_trades['drawdown'], color='red', alpha=0.3)
ax2.plot(df_trades['entry_time'], df_trades['drawdown'], color='darkred', linewidth=1.5)
ax2.axhline(y=0, color='gray', linestyle='-', alpha=0.5)
ax2.set_ylabel('Drawdown (%)', fontsize=12, fontweight='bold')
ax2.grid(True, alpha=0.3)
ax2.set_ylim(max_dd * 1.2, 1)

# Highlight max DD
max_dd_idx = df_trades['drawdown'].idxmin()
ax2.scatter(df_trades['entry_time'].iloc[max_dd_idx], df_trades['drawdown'].iloc[max_dd_idx],
           color='darkred', s=100, marker='o', zorder=5)
ax2.annotate(f'Max DD: {max_dd:.2f}%',
            xy=(df_trades['entry_time'].iloc[max_dd_idx], df_trades['drawdown'].iloc[max_dd_idx]),
            xytext=(20, -20), textcoords='offset points',
            bbox=dict(boxstyle='round', facecolor='red', alpha=0.7),
            arrowprops=dict(arrowstyle='->', color='darkred'))

# === SUBPLOT 3: Trade P&L ===
colors = ['green' if x > 0 else 'red' for x in df_trades['pnl_pct']]
bars = ax3.bar(df_trades['entry_time'], df_trades['pnl_pct'], color=colors, alpha=0.7, width=0.5)

# Highlight TP hits
for i, row in tps.iterrows():
    ax3.bar(row['entry_time'], row['pnl_pct'], color='gold', alpha=0.9, width=0.5)

ax3.axhline(y=0, color='gray', linestyle='-', alpha=0.5)
ax3.set_ylabel('Trade P&L (%)', fontsize=12, fontweight='bold')
ax3.set_xlabel('Date', fontsize=12, fontweight='bold')
ax3.grid(True, alpha=0.3, axis='y')

# Format x-axis
for ax in [ax1, ax2, ax3]:
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=7))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

plt.tight_layout()

# Save
output_path = 'results/eth_optimized_equity_curve.png'
plt.savefig(output_path, dpi=300, bbox_inches='tight')
print(f"✅ Equity curve saved to: {output_path}")

print("\n" + "=" * 80)
