#!/usr/bin/env python3
"""
Generate visual analysis of FARTCOIN trading strategy:
1. Equity curve with trade markers
2. Price chart with entry/exit points
3. Trade distribution over time
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import json

# Load the best FARTCOIN configuration results
print("Loading data...")

# Load FARTCOIN price data
df_price = pd.read_csv('/workspaces/Carebiuro_windykacja/fartcoin_usdt_1m_lbank.csv')
df_price['timestamp'] = pd.to_datetime(df_price['timestamp'])

# Load optimization results to find the winning config
df_results = pd.read_csv('/workspaces/Carebiuro_windykacja/strategies/optimization-results-fartcoin.csv')
best_config = df_results.loc[df_results['rr_ratio'].idxmax()]

print(f"\nBest Config: {best_config['test_name']}")
print(f"R:R Ratio: {best_config['rr_ratio']:.2f}x")
print(f"Return: {best_config['total_return_pct']:.2f}%")
print(f"Trades: {int(best_config['total_trades'])}")

# Load the best configuration
with open('/workspaces/Carebiuro_windykacja/strategies/best-config-fartcoin.json', 'r') as f:
    best_config_params = json.load(f)

# Now we need to re-run the backtest to get individual trade details
# Import the backtest logic
import sys
sys.path.append('/workspaces/Carebiuro_windykacja/strategies')

print("\nRunning backtest to get trade details...")

# Simplified backtest to extract trade data
class TradeExtractor:
    def __init__(self, csv_path, config):
        self.df = pd.read_csv(csv_path)
        self.df['timestamp'] = pd.to_datetime(self.df['timestamp'])
        self.config = config
        self.trades = []
        self.calculate_indicators()

    def calculate_indicators(self):
        # Body and wicks
        self.df['body'] = abs(self.df['close'] - self.df['open'])
        self.df['body_pct'] = (self.df['body'] / self.df['open']) * 100
        self.df['upper_wick'] = self.df['high'] - self.df[['open', 'close']].max(axis=1)
        self.df['lower_wick'] = self.df[['open', 'close']].min(axis=1) - self.df['low']
        self.df['is_bullish'] = self.df['close'] > self.df['open']
        self.df['is_bearish'] = self.df['close'] < self.df['open']

        # Volume
        self.df['vol_ma'] = self.df['volume'].rolling(20).mean()
        self.df['vol_ratio'] = self.df['volume'] / self.df['vol_ma']

        # SMAs
        self.df['sma_50'] = self.df['close'].rolling(50).mean()
        self.df['sma_200'] = self.df['close'].rolling(200).mean()

        # Trends
        self.df['uptrend_50'] = self.df['close'] > self.df['sma_50']
        self.df['downtrend_50'] = self.df['close'] < self.df['sma_50']
        self.df['uptrend_200'] = self.df['close'] > self.df['sma_200']
        self.df['downtrend_200'] = self.df['close'] < self.df['sma_200']
        self.df['strong_uptrend'] = self.df['uptrend_50'] & self.df['uptrend_200']
        self.df['strong_downtrend'] = self.df['downtrend_50'] & self.df['downtrend_200']

        # Distance from SMA
        self.df['distance_from_50'] = abs((self.df['close'] - self.df['sma_50']) / self.df['sma_50']) * 100

        # RSI
        delta = self.df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        self.df['rsi'] = 100 - (100 / (1 + rs))

        # ATR
        high_low = self.df['high'] - self.df['low']
        high_close = abs(self.df['high'] - self.df['close'].shift())
        low_close = abs(self.df['low'] - self.df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        self.df['atr'] = tr.rolling(14).mean()

        # ATR percentile
        self.df['atr_percentile'] = self.df['atr'].rolling(100).apply(
            lambda x: (x.iloc[-1] > x).sum() / len(x) * 100 if len(x) > 0 else 50
        )
        self.df['high_vol'] = self.df['atr_percentile'] >= 50

    def detect_signal(self, idx):
        if idx < 200:
            return None

        row = self.df.loc[idx]
        cfg = self.config

        body = row['body']
        if body == 0:
            return None

        wick_ratio_lower = row['lower_wick'] / body
        wick_ratio_upper = row['upper_wick'] / body

        # Base checks
        body_ok = row['body_pct'] > cfg['body_threshold']
        volume_ok = row['vol_ratio'] > cfg['volume_multiplier']
        wicks_ok = wick_ratio_lower < cfg['wick_threshold'] and wick_ratio_upper < cfg['wick_threshold']
        vol_ok = row['high_vol'] if cfg.get('require_high_vol', True) else True

        if not (body_ok and volume_ok and wicks_ok and vol_ok):
            return None

        distance_ok = row['distance_from_50'] >= cfg['sma_distance_min']

        # Explosive Bearish Breakdown
        if row['is_bearish'] and row['strong_downtrend'] and distance_ok:
            if cfg['rsi_short_min'] < row['rsi'] < cfg['rsi_short_max']:
                return {
                    'direction': 'short',
                    'pattern': 'Explosive Bearish Breakdown',
                    'entry_price': row['close'],
                    'stop_loss': row['close'] + (cfg['stop_atr_mult'] * row['atr']),
                    'take_profit': row['close'] - (cfg.get('tp_atr_mult', cfg.get('tp_atr_high_vol', 15.0)) * row['atr']),
                    'timestamp': row['timestamp'],
                    'atr': row['atr']
                }

        # Explosive Bullish Breakout
        if cfg.get('trade_both_directions', True):
            if row['is_bullish'] and row['strong_uptrend'] and distance_ok:
                if cfg['rsi_long_min'] < row['rsi'] < cfg['rsi_long_max']:
                    return {
                        'direction': 'long',
                        'pattern': 'Explosive Bullish Breakout',
                        'entry_price': row['close'],
                        'stop_loss': row['close'] - (cfg['stop_atr_mult'] * row['atr']),
                        'take_profit': row['close'] + (cfg.get('tp_atr_mult', cfg.get('tp_atr_high_vol', 15.0)) * row['atr']),
                        'timestamp': row['timestamp'],
                        'atr': row['atr']
                    }

        return None

    def run(self):
        capital = 10000
        position = None

        for idx in range(200, len(self.df)):
            row = self.df.loc[idx]

            # Check exit
            if position:
                hours_held = (row['timestamp'] - position['entry_time']).total_seconds() / 3600

                exit_triggered = False
                exit_reason = None
                exit_price = None

                if position['direction'] == 'long':
                    if row['high'] >= position['take_profit']:
                        exit_price = position['take_profit']
                        exit_reason = 'TP'
                        exit_triggered = True
                    elif row['low'] <= position['stop_loss']:
                        exit_price = position['stop_loss']
                        exit_reason = 'SL'
                        exit_triggered = True
                    elif hours_held >= self.config.get('max_hold_hours', 24):
                        exit_price = row['close']
                        exit_reason = 'Time'
                        exit_triggered = True
                else:  # short
                    if row['low'] <= position['take_profit']:
                        exit_price = position['take_profit']
                        exit_reason = 'TP'
                        exit_triggered = True
                    elif row['high'] >= position['stop_loss']:
                        exit_price = position['stop_loss']
                        exit_reason = 'SL'
                        exit_triggered = True
                    elif hours_held >= self.config.get('max_hold_hours', 24):
                        exit_price = row['close']
                        exit_reason = 'Time'
                        exit_triggered = True

                if exit_triggered:
                    if position['direction'] == 'long':
                        pnl_pct = ((exit_price - position['entry_price']) / position['entry_price']) * 100
                    else:
                        pnl_pct = ((position['entry_price'] - exit_price) / position['entry_price']) * 100

                    position_size = capital * 0.02  # Simplified sizing
                    pnl_dollar = position_size * (pnl_pct / 100)
                    capital += pnl_dollar

                    self.trades.append({
                        'entry_time': position['entry_time'],
                        'exit_time': row['timestamp'],
                        'direction': position['direction'],
                        'pattern': position['pattern'],
                        'entry_price': position['entry_price'],
                        'exit_price': exit_price,
                        'exit_reason': exit_reason,
                        'pnl_pct': pnl_pct,
                        'pnl_dollar': pnl_dollar,
                        'capital': capital
                    })

                    position = None

            # Check entry
            if not position:
                signal = self.detect_signal(idx)
                if signal:
                    position = {
                        'direction': signal['direction'],
                        'pattern': signal['pattern'],
                        'entry_price': signal['entry_price'],
                        'entry_time': signal['timestamp'],
                        'stop_loss': signal['stop_loss'],
                        'take_profit': signal['take_profit']
                    }

        return pd.DataFrame(self.trades)

# Run extraction
extractor = TradeExtractor('/workspaces/Carebiuro_windykacja/fartcoin_usdt_1m_lbank.csv', best_config_params['config'])
df_trades = extractor.run()

print(f"\nExtracted {len(df_trades)} trades")

# Create visualizations
fig = plt.figure(figsize=(16, 12))
gs = fig.add_gridspec(3, 2, hspace=0.3, wspace=0.3)

# 1. Equity Curve with Trade Markers
ax1 = fig.add_subplot(gs[0, :])
df_trades['cumulative_return_pct'] = df_trades['pnl_pct'].cumsum()
df_trades['cumulative_capital'] = df_trades['capital']

ax1.plot(df_trades['exit_time'], df_trades['cumulative_return_pct'],
         linewidth=2, color='#2E86AB', label='Cumulative Return')
ax1.axhline(y=0, color='gray', linestyle='--', alpha=0.5)

# Mark winning and losing trades
wins = df_trades[df_trades['pnl_pct'] > 0]
losses = df_trades[df_trades['pnl_pct'] < 0]

ax1.scatter(wins['exit_time'], wins['cumulative_return_pct'],
           color='green', s=100, marker='^', alpha=0.7, label='Win', zorder=5)
ax1.scatter(losses['exit_time'], losses['cumulative_return_pct'],
           color='red', s=100, marker='v', alpha=0.7, label='Loss', zorder=5)

ax1.set_xlabel('Date', fontsize=12, fontweight='bold')
ax1.set_ylabel('Cumulative Return (%)', fontsize=12, fontweight='bold')
ax1.set_title('Equity Curve - FARTCOIN (Body 1.2% Config)', fontsize=14, fontweight='bold')
ax1.grid(True, alpha=0.3)
ax1.legend(loc='upper left', fontsize=10)
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))

# 2. Price Chart with Trade Markers (Daily candles for clarity)
ax2 = fig.add_subplot(gs[1, :])

# Resample to 4-hour candles for cleaner visualization
df_4h = df_price.set_index('timestamp').resample('4H').agg({
    'open': 'first',
    'high': 'max',
    'low': 'min',
    'close': 'last',
    'volume': 'sum'
}).dropna()

ax2.plot(df_4h.index, df_4h['close'], linewidth=1.5, color='#444', alpha=0.7, label='FARTCOIN Price')

# Mark entry points
for _, trade in df_trades.iterrows():
    if trade['direction'] == 'long':
        ax2.scatter(trade['entry_time'], trade['entry_price'],
                   color='green', s=150, marker='^', edgecolors='black', linewidth=1.5,
                   alpha=0.8, zorder=5)
    else:
        ax2.scatter(trade['entry_time'], trade['entry_price'],
                   color='red', s=150, marker='v', edgecolors='black', linewidth=1.5,
                   alpha=0.8, zorder=5)

# Add SMA lines for context
df_price_indexed = df_price.set_index('timestamp')
sma_50 = df_price_indexed['close'].rolling(50).mean().resample('4H').last()
sma_200 = df_price_indexed['close'].rolling(200).mean().resample('4H').last()

ax2.plot(sma_50.index, sma_50, linewidth=1, color='orange', alpha=0.5, label='50 SMA', linestyle='--')
ax2.plot(sma_200.index, sma_200, linewidth=1, color='purple', alpha=0.5, label='200 SMA', linestyle='--')

ax2.set_xlabel('Date', fontsize=12, fontweight='bold')
ax2.set_ylabel('Price (USDT)', fontsize=12, fontweight='bold')
ax2.set_title('FARTCOIN Price with Trade Entry Points (4H Chart)', fontsize=14, fontweight='bold')
ax2.grid(True, alpha=0.3)
ax2.legend(loc='upper left', fontsize=10)
ax2.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))

# Add legend for entry markers
from matplotlib.lines import Line2D
legend_elements = [
    Line2D([0], [0], marker='^', color='w', markerfacecolor='green',
           markersize=10, label='Long Entry', markeredgecolor='black', markeredgewidth=1),
    Line2D([0], [0], marker='v', color='w', markerfacecolor='red',
           markersize=10, label='Short Entry', markeredgecolor='black', markeredgewidth=1)
]
ax2.legend(handles=legend_elements, loc='upper right', fontsize=10)

# 3. Trade Distribution by Date
ax3 = fig.add_subplot(gs[2, 0])
df_trades['entry_date'] = pd.to_datetime(df_trades['entry_time']).dt.date
trade_counts = df_trades.groupby('entry_date').size()

ax3.bar(range(len(trade_counts)), trade_counts.values, color='#2E86AB', alpha=0.7)
ax3.set_xlabel('Trade Date', fontsize=12, fontweight='bold')
ax3.set_ylabel('Number of Trades', fontsize=12, fontweight='bold')
ax3.set_title('Trade Frequency Over Time', fontsize=14, fontweight='bold')
ax3.set_xticks(range(len(trade_counts)))
ax3.set_xticklabels([str(d) for d in trade_counts.index], rotation=45, ha='right', fontsize=8)
ax3.grid(True, alpha=0.3, axis='y')

# 4. Trade Performance Breakdown
ax4 = fig.add_subplot(gs[2, 1])

# P&L distribution
win_pnls = df_trades[df_trades['pnl_pct'] > 0]['pnl_pct']
loss_pnls = df_trades[df_trades['pnl_pct'] < 0]['pnl_pct']

positions = range(len(df_trades))
colors = ['green' if pnl > 0 else 'red' for pnl in df_trades['pnl_pct']]

ax4.bar(positions, df_trades['pnl_pct'], color=colors, alpha=0.7)
ax4.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
ax4.set_xlabel('Trade Number', fontsize=12, fontweight='bold')
ax4.set_ylabel('P&L (%)', fontsize=12, fontweight='bold')
ax4.set_title('Individual Trade Performance', fontsize=14, fontweight='bold')
ax4.grid(True, alpha=0.3, axis='y')

# Add statistics text
stats_text = f"""Stats:
Wins: {len(wins)} ({len(wins)/len(df_trades)*100:.1f}%)
Losses: {len(losses)} ({len(losses)/len(df_trades)*100:.1f}%)
Avg Win: {win_pnls.mean():.2f}%
Avg Loss: {loss_pnls.mean():.2f}%
R:R: {best_config['rr_ratio']:.2f}x"""

ax4.text(0.98, 0.97, stats_text, transform=ax4.transAxes,
         fontsize=9, verticalalignment='top', horizontalalignment='right',
         bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

plt.suptitle('FARTCOIN Trading Strategy - Visual Analysis',
             fontsize=16, fontweight='bold', y=0.995)

# Save figure
output_path = '/workspaces/Carebiuro_windykacja/strategies/FARTCOIN-VISUAL-ANALYSIS.png'
plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
print(f"\n✓ Saved visualization to: {output_path}")

# Also save trade details to CSV
trades_csv_path = '/workspaces/Carebiuro_windykacja/strategies/fartcoin-best-config-trades.csv'
df_trades.to_csv(trades_csv_path, index=False)
print(f"✓ Saved trade details to: {trades_csv_path}")

# Print summary
print("\n" + "="*80)
print("TRADE SUMMARY")
print("="*80)
print(f"\nTotal Trades: {len(df_trades)}")
print(f"Winners: {len(wins)} ({len(wins)/len(df_trades)*100:.1f}%)")
print(f"Losers: {len(losses)} ({len(losses)/len(df_trades)*100:.1f}%)")
print(f"\nAverage Win: {win_pnls.mean():.2f}%")
print(f"Average Loss: {loss_pnls.mean():.2f}%")
print(f"Largest Win: {win_pnls.max():.2f}%")
print(f"Largest Loss: {loss_pnls.min():.2f}%")
print(f"\nFinal Return: {df_trades['cumulative_return_pct'].iloc[-1]:.2f}%")
print(f"Final Capital: ${df_trades['capital'].iloc[-1]:,.2f}")
print(f"\nR:R Ratio: {best_config['rr_ratio']:.2f}x")
print(f"Max Drawdown: {best_config['max_drawdown']:.2f}%")

print("\n" + "="*80)
print("RECENT TRADES (Last 5)")
print("="*80)
print(df_trades[['entry_time', 'direction', 'entry_price', 'exit_price', 'exit_reason', 'pnl_pct']].tail(5).to_string(index=False))

print(f"\n✓ Analysis complete! Open the PNG file to view the charts.")
