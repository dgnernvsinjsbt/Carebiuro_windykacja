"""
PEPE Strategy Filter Analysis
Analyze winning vs losing trades to find common patterns and test filters
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Load data
df = pd.read_csv('pepe_usdt_1m_lbank.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# Calculate indicators
df['sma20'] = df['close'].rolling(20).mean()
df['sma50'] = df['close'].rolling(50).mean()
df['sma200'] = df['close'].rolling(200).mean()

# ATR
high_low = df['high'] - df['low']
high_close = (df['high'] - df['close'].shift()).abs()
low_close = (df['low'] - df['close'].shift()).abs()
true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
df['atr'] = true_range.rolling(14).mean()

# RSI
delta = df['close'].diff()
gain = delta.where(delta > 0, 0).rolling(14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
rs = gain / loss
df['rsi'] = 100 - (100 / (1 + rs))

# Bollinger Bands
df['bb_middle'] = df['close'].rolling(20).mean()
bb_std = df['close'].rolling(20).std()
df['bb_upper'] = df['bb_middle'] + 2 * bb_std
df['bb_lower'] = df['bb_middle'] - 2 * bb_std
df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle'] * 100

# Volume
df['volume_sma20'] = df['volume'].rolling(20).mean()
df['volume_ratio'] = df['volume'] / df['volume_sma20']

# Hour of day
df['hour'] = df['timestamp'].dt.hour

# Higher timeframe trend (15-min approximation using 15-candle SMA)
df['sma15'] = df['close'].rolling(15).mean()
df['trend_15m'] = (df['close'] > df['sma15']).astype(int)

print("Loaded data with", len(df), "candles")
print("\nRunning original strategy to get all trades...")

# Original strategy from audit
class BacktestEngine:
    def __init__(self, df, fees=0.001):
        self.df = df.copy()
        self.fees = fees
        self.trades = []

    def run_market_orders(self):
        """Run strategy with MARKET orders only (0.10% fees)"""
        in_position = False
        entry_price = 0
        entry_idx = 0
        sl_price = 0
        tp_price = 0

        for i in range(200, len(self.df)):
            current = self.df.iloc[i]

            if in_position:
                # Check SL/TP (both could hit in same candle)
                sl_hit = current['low'] <= sl_price
                tp_hit = current['high'] >= tp_price

                if sl_hit and tp_hit:
                    # Both hit - assume SL hit first (conservative)
                    exit_price = sl_price
                    exit_reason = 'SL'
                elif sl_hit:
                    exit_price = sl_price
                    exit_reason = 'SL'
                elif tp_hit:
                    exit_price = tp_price
                    exit_reason = 'TP'
                else:
                    continue  # Still in position

                pnl = (exit_price / entry_price - 1) - self.fees
                self.trades.append({
                    'entry_idx': entry_idx,
                    'exit_idx': i,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl_gross': (exit_price / entry_price - 1),
                    'pnl_net': pnl,
                    'exit_reason': exit_reason,
                    'entry_rsi': self.df.iloc[entry_idx]['rsi'],
                    'entry_bb_dist': (self.df.iloc[entry_idx]['close'] - self.df.iloc[entry_idx]['bb_lower']) / self.df.iloc[entry_idx]['bb_lower'] * 100,
                    'entry_atr': self.df.iloc[entry_idx]['atr'],
                    'entry_bb_width': self.df.iloc[entry_idx]['bb_width'],
                    'entry_volume_ratio': self.df.iloc[entry_idx]['volume_ratio'],
                    'entry_hour': self.df.iloc[entry_idx]['hour'],
                    'entry_trend_15m': self.df.iloc[entry_idx]['trend_15m'],
                    'entry_distance_from_sma50': (self.df.iloc[entry_idx]['close'] - self.df.iloc[entry_idx]['sma50']) / self.df.iloc[entry_idx]['sma50'] * 100,
                    'hold_bars': i - entry_idx
                })
                in_position = False
            else:
                # Entry logic: RSI <= 40 AND close <= bb_lower
                if (current['rsi'] <= 40 and
                    current['close'] <= current['bb_lower'] and
                    not pd.isna(current['atr'])):
                    entry_price = current['close']
                    entry_idx = i
                    sl_price = entry_price - 1.5 * current['atr']
                    tp_price = entry_price + 2.0 * current['atr']
                    in_position = True

        return pd.DataFrame(self.trades)

# Run backtest
engine = BacktestEngine(df, fees=0.001)
trades_df = engine.run_market_orders()

print(f"\nTotal trades: {len(trades_df)}")

# Split winners vs losers
winners = trades_df[trades_df['pnl_net'] > 0].copy()
losers = trades_df[trades_df['pnl_net'] <= 0].copy()

print(f"Winners: {len(winners)} ({len(winners)/len(trades_df)*100:.1f}%)")
print(f"Losers: {len(losers)} ({len(losers)/len(trades_df)*100:.1f}%)")

print("\n" + "="*80)
print("COMPARING WINNERS vs LOSERS")
print("="*80)

# Function to compare distributions
def compare_feature(winners, losers, feature_name, bins=20):
    print(f"\n{feature_name}:")
    print(f"  Winners - Mean: {winners[feature_name].mean():.3f}, Median: {winners[feature_name].median():.3f}, Std: {winners[feature_name].std():.3f}")
    print(f"  Losers  - Mean: {losers[feature_name].mean():.3f}, Median: {losers[feature_name].median():.3f}, Std: {losers[feature_name].std():.3f}")
    print(f"  Difference: {winners[feature_name].mean() - losers[feature_name].mean():.3f}")

# Compare key features
compare_feature(winners, losers, 'entry_rsi')
compare_feature(winners, losers, 'entry_bb_dist')
compare_feature(winners, losers, 'entry_atr')
compare_feature(winners, losers, 'entry_bb_width')
compare_feature(winners, losers, 'entry_volume_ratio')
compare_feature(winners, losers, 'entry_distance_from_sma50')
compare_feature(winners, losers, 'hold_bars')

# Hour distribution
print("\n\nEntry Hour Distribution:")
print("Winners:")
print(winners['entry_hour'].value_counts().sort_index())
print("\nLosers:")
print(losers['entry_hour'].value_counts().sort_index())

# Trend filter
print("\n\n15-min Trend Filter:")
print(f"Winners - Uptrend: {(winners['entry_trend_15m']==1).sum()} ({(winners['entry_trend_15m']==1).sum()/len(winners)*100:.1f}%)")
print(f"Losers  - Uptrend: {(losers['entry_trend_15m']==1).sum()} ({(losers['entry_trend_15m']==1).sum()/len(losers)*100:.1f}%)")

# Exit reason
print("\n\nExit Reason:")
print("Winners:")
print(winners['exit_reason'].value_counts())
print("\nLosers:")
print(losers['exit_reason'].value_counts())

print("\n" + "="*80)
print("TESTING FILTERS")
print("="*80)

def test_filter(trades_df, filter_func, filter_name):
    """Test a filter and report results"""
    filtered = trades_df[filter_func(trades_df)].copy()

    if len(filtered) == 0:
        print(f"\n{filter_name}: NO TRADES PASSED FILTER")
        return

    total_pnl = filtered['pnl_net'].sum()
    win_rate = (filtered['pnl_net'] > 0).sum() / len(filtered) * 100

    # Calculate equity curve
    equity = 10000
    peak = equity
    max_dd = 0
    for pnl in filtered['pnl_net']:
        equity = equity * (1 + pnl)
        if equity > peak:
            peak = equity
        dd = (peak - equity) / peak * 100
        if dd > max_dd:
            max_dd = dd

    total_return = (equity / 10000 - 1) * 100

    print(f"\n{filter_name}:")
    print(f"  Trades: {len(filtered)} ({len(filtered)/len(trades_df)*100:.1f}% of original)")
    print(f"  Win Rate: {win_rate:.1f}%")
    print(f"  Total Return: {total_return:.2f}%")
    print(f"  Max DD: {max_dd:.2f}%")
    print(f"  Strategy R:R: {total_return/max_dd if max_dd > 0 else 0:.2f}")

    return {
        'filter': filter_name,
        'trades': len(filtered),
        'win_rate': win_rate,
        'return': total_return,
        'max_dd': max_dd,
        'strategy_rr': total_return/max_dd if max_dd > 0 else 0
    }

# Test various filters
filter_results = []

# Baseline (no filter)
result = test_filter(trades_df, lambda df: df.index == df.index, "BASELINE (No Filter)")
if result:
    filter_results.append(result)

# Filter 1: Higher timeframe trend (15m uptrend)
result = test_filter(trades_df, lambda df: df['entry_trend_15m'] == 1, "Filter 1: 15-min Uptrend")
if result:
    filter_results.append(result)

# Filter 2: Low volatility (BB width < median)
median_bb_width = trades_df['entry_bb_width'].median()
result = test_filter(trades_df, lambda df: df['entry_bb_width'] < median_bb_width, f"Filter 2: BB Width < {median_bb_width:.2f}%")
if result:
    filter_results.append(result)

# Filter 3: High volatility (BB width > median)
result = test_filter(trades_df, lambda df: df['entry_bb_width'] > median_bb_width, f"Filter 3: BB Width > {median_bb_width:.2f}%")
if result:
    filter_results.append(result)

# Filter 4: Deep oversold (RSI < 35)
result = test_filter(trades_df, lambda df: df['entry_rsi'] < 35, "Filter 4: Deep Oversold (RSI < 35)")
if result:
    filter_results.append(result)

# Filter 5: Volume confirmation (volume > 1.2x average)
result = test_filter(trades_df, lambda df: df['entry_volume_ratio'] > 1.2, "Filter 5: Volume > 1.2x Avg")
if result:
    filter_results.append(result)

# Filter 6: Close to SMA50 (distance < 5%)
result = test_filter(trades_df, lambda df: df['entry_distance_from_sma50'].abs() < 5, "Filter 6: Within 5% of SMA50")
if result:
    filter_results.append(result)

# Filter 7: Very close to BB lower (distance < 0.5%)
result = test_filter(trades_df, lambda df: df['entry_bb_dist'] < 0.5, "Filter 7: Very Close to BB Lower (<0.5%)")
if result:
    filter_results.append(result)

# Filter 8: Avoid certain hours (avoid low liquidity hours)
result = test_filter(trades_df, lambda df: ~df['entry_hour'].isin([0, 1, 2, 3, 4, 5, 6]), "Filter 8: Avoid Hours 0-6 (Low Liquidity)")
if result:
    filter_results.append(result)

# COMBINED FILTERS
# Best combo: Uptrend + Deep oversold + Volume
result = test_filter(trades_df,
    lambda df: (df['entry_trend_15m'] == 1) &
               (df['entry_rsi'] < 35) &
               (df['entry_volume_ratio'] > 1.2),
    "COMBO 1: Uptrend + RSI<35 + Volume>1.2x")
if result:
    filter_results.append(result)

# Combo 2: Low volatility + Very close to BB
result = test_filter(trades_df,
    lambda df: (df['entry_bb_width'] < median_bb_width) &
               (df['entry_bb_dist'] < 0.5),
    "COMBO 2: Low Volatility + Very Close BB")
if result:
    filter_results.append(result)

# Combo 3: Uptrend + Volume + Time filter
result = test_filter(trades_df,
    lambda df: (df['entry_trend_15m'] == 1) &
               (df['entry_volume_ratio'] > 1.2) &
               (~df['entry_hour'].isin([0, 1, 2, 3, 4, 5, 6])),
    "COMBO 3: Uptrend + Volume + Good Hours")
if result:
    filter_results.append(result)

# Summary table
print("\n" + "="*80)
print("FILTER SUMMARY (Ranked by Strategy R:R)")
print("="*80)

results_df = pd.DataFrame(filter_results)
results_df = results_df.sort_values('strategy_rr', ascending=False)
print(results_df.to_string(index=False))

# Save results
results_df.to_csv('results/PEPE_filter_test_results.csv', index=False)
trades_df.to_csv('results/PEPE_all_trades_with_features.csv', index=False)

print("\n\nResults saved to:")
print("- results/PEPE_filter_test_results.csv")
print("- results/PEPE_all_trades_with_features.csv")

# Visualize best filter
print("\n" + "="*80)
print("VISUALIZING BEST FILTER")
print("="*80)

best_filter = results_df.iloc[0]
print(f"\nBest filter: {best_filter['filter']}")
print(f"Strategy R:R: {best_filter['strategy_rr']:.2f}")

# Create visualization comparing baseline vs best filter
fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# Equity curves
ax = axes[0, 0]
equity_baseline = 10000
equity_curve_baseline = [equity_baseline]
for pnl in trades_df['pnl_net']:
    equity_baseline *= (1 + pnl)
    equity_curve_baseline.append(equity_baseline)

# Get best filter data
if "COMBO 1" in best_filter['filter']:
    filtered_trades = trades_df[(trades_df['entry_trend_15m'] == 1) &
                                (trades_df['entry_rsi'] < 35) &
                                (trades_df['entry_volume_ratio'] > 1.2)]
elif "Uptrend" in best_filter['filter'] and "COMBO" not in best_filter['filter']:
    filtered_trades = trades_df[trades_df['entry_trend_15m'] == 1]
else:
    filtered_trades = trades_df

equity_filtered = 10000
equity_curve_filtered = [equity_filtered]
for pnl in filtered_trades['pnl_net']:
    equity_filtered *= (1 + pnl)
    equity_curve_filtered.append(equity_filtered)

ax.plot(equity_curve_baseline, label='Baseline', alpha=0.7)
ax.plot(equity_curve_filtered, label=f'Best Filter ({best_filter["filter"]})', alpha=0.7)
ax.set_title('Equity Curve Comparison')
ax.set_xlabel('Trade Number')
ax.set_ylabel('Equity ($)')
ax.legend()
ax.grid(True, alpha=0.3)

# Win rate comparison
ax = axes[0, 1]
baseline_winrate = (trades_df['pnl_net'] > 0).sum() / len(trades_df) * 100
filtered_winrate = best_filter['win_rate']
ax.bar(['Baseline', 'Best Filter'], [baseline_winrate, filtered_winrate], alpha=0.7)
ax.set_title('Win Rate Comparison')
ax.set_ylabel('Win Rate (%)')
ax.grid(True, alpha=0.3)

# Trade count
ax = axes[1, 0]
ax.bar(['Baseline', 'Best Filter'], [len(trades_df), best_filter['trades']], alpha=0.7)
ax.set_title('Number of Trades')
ax.set_ylabel('Trades')
ax.grid(True, alpha=0.3)

# Strategy R:R
ax = axes[1, 1]
baseline_equity = 10000
baseline_peak = baseline_equity
baseline_max_dd = 0
for pnl in trades_df['pnl_net']:
    baseline_equity *= (1 + pnl)
    if baseline_equity > baseline_peak:
        baseline_peak = baseline_equity
    dd = (baseline_peak - baseline_equity) / baseline_peak * 100
    if dd > baseline_max_dd:
        baseline_max_dd = dd
baseline_return = (baseline_equity / 10000 - 1) * 100
baseline_rr = baseline_return / baseline_max_dd if baseline_max_dd > 0 else 0

ax.bar(['Baseline', 'Best Filter'], [baseline_rr, best_filter['strategy_rr']], alpha=0.7)
ax.set_title('Strategy R:R (Return / Max DD)')
ax.set_ylabel('R:R Ratio')
ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('results/PEPE_filter_comparison.png', dpi=150, bbox_inches='tight')
print("\nVisualization saved to: results/PEPE_filter_comparison.png")

print("\n✅ ANALYSIS COMPLETE")
