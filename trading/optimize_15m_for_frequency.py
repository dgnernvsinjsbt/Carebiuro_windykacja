"""
Find filter combo that gives 60+ trades in 3 months with >50% win rate
Balance between selectivity and frequency
"""

import pandas as pd
import numpy as np

print("=" * 80)
print("OPTIMIZE FOR FREQUENCY (60+ trades target)")
print("=" * 80)

# Load the analysis data
df = pd.read_csv('melania_15m_crosses_analysis.csv')

print(f"\nTotal crosses: {len(df)}")
print(f"Base win rate: {(df['is_winner'].sum() / len(df)) * 100:.1f}%")

# Test various filter combinations
filter_configs = []

# RSI levels to test
rsi_levels_long = [20, 25, 30, 35]
rsi_levels_short = [65, 70, 75, 80]

# ATR thresholds
atr_thresholds = [1.5, 2.0, 2.5, 3.0, 3.5]

# Range96 thresholds
range96_thresholds = [10, 15, 20, 25]

# Test RSI level alone
print("\n" + "=" * 80)
print("RSI LEVEL ANALYSIS:")
print("=" * 80)

for level in sorted(df['rsi_level'].unique()):
    data = df[df['rsi_level'] == level]
    win_rate = (data['is_winner'].sum() / len(data)) * 100
    avg_profit = data['best_profit'].mean()

    print(f"\nRSI {level}:")
    print(f"  Signals: {len(data)}")
    print(f"  Win Rate: {win_rate:.1f}%")
    print(f"  Avg Profit: {avg_profit:.2f}%")

    if len(data) >= 60 and win_rate >= 50:
        print(f"  ✅ MEETS CRITERIA!")

# Test combinations
print("\n" + "=" * 80)
print("FILTER COMBINATIONS (Target: 60+ trades, >50% win rate):")
print("=" * 80)

results = []

# SHORT only with various filters
for rsi in rsi_levels_short:
    for atr in atr_thresholds:
        for range96 in range96_thresholds:
            mask = (df['rsi_level'] == rsi) & (df['atr_pct'] >= atr) & (df['range_96'] >= range96)
            filtered = df[mask]

            if len(filtered) > 0:
                win_rate = (filtered['is_winner'].sum() / len(filtered)) * 100
                avg_profit = filtered['best_profit'].mean()

                results.append({
                    'type': 'SHORT',
                    'rsi': rsi,
                    'atr_min': atr,
                    'range96_min': range96,
                    'signals': len(filtered),
                    'win_rate': win_rate,
                    'avg_profit': avg_profit,
                    'score': len(filtered) * (win_rate / 100) * avg_profit  # Quality * Frequency score
                })

# LONG only with various filters
for rsi in rsi_levels_long:
    for atr in atr_thresholds:
        for range96 in range96_thresholds:
            mask = (df['rsi_level'] == rsi) & (df['atr_pct'] >= atr) & (df['range_96'] >= range96)
            filtered = df[mask]

            if len(filtered) > 0:
                win_rate = (filtered['is_winner'].sum() / len(filtered)) * 100
                avg_profit = filtered['best_profit'].mean()

                results.append({
                    'type': 'LONG',
                    'rsi': rsi,
                    'atr_min': atr,
                    'range96_min': range96,
                    'signals': len(filtered),
                    'win_rate': win_rate,
                    'avg_profit': avg_profit,
                    'score': len(filtered) * (win_rate / 100) * avg_profit
                })

# Both LONG + SHORT with different filters for each
for long_rsi in rsi_levels_long:
    for short_rsi in rsi_levels_short:
        for atr in atr_thresholds:
            for range96 in range96_thresholds:
                long_mask = (df['rsi_level'] == long_rsi) & (df['atr_pct'] >= atr) & (df['range_96'] >= range96)
                short_mask = (df['rsi_level'] == short_rsi) & (df['atr_pct'] >= atr) & (df['range_96'] >= range96)
                combined_mask = long_mask | short_mask

                filtered = df[combined_mask]

                if len(filtered) > 0:
                    win_rate = (filtered['is_winner'].sum() / len(filtered)) * 100
                    avg_profit = filtered['best_profit'].mean()

                    results.append({
                        'type': f'BOTH L{long_rsi}/S{short_rsi}',
                        'rsi': f'{long_rsi}/{short_rsi}',
                        'atr_min': atr,
                        'range96_min': range96,
                        'signals': len(filtered),
                        'win_rate': win_rate,
                        'avg_profit': avg_profit,
                        'score': len(filtered) * (win_rate / 100) * avg_profit
                    })

results_df = pd.DataFrame(results)

# Filter for minimum criteria
viable = results_df[(results_df['signals'] >= 60) & (results_df['win_rate'] >= 50)]

if len(viable) == 0:
    print("\n⚠️  NO CONFIGS meet 60+ trades AND 50%+ win rate")
    print("\nRelaxing criteria to 40+ trades...")
    viable = results_df[(results_df['signals'] >= 40) & (results_df['win_rate'] >= 50)]

if len(viable) == 0:
    print("\n⚠️  NO CONFIGS meet 40+ trades AND 50%+ win rate")
    print("\nShowing best by score (frequency × win rate × profit)...")
    viable = results_df.nlargest(20, 'score')

viable = viable.sort_values('score', ascending=False)

print(f"\n{'Type':<20} | {'RSI':<10} | {'ATR%':<6} | {'R96%':<6} | {'Signals':<8} | {'Win%':<8} | {'Avg Profit':<12} | Score")
print("-" * 120)

for i, (idx, row) in enumerate(viable.head(20).iterrows(), 1):
    highlight = "🏆" if i == 1 else ""
    print(f"{row['type']:<20} | {str(row['rsi']):<10} | {row['atr_min']:>5.1f} | {row['range96_min']:>5.0f} | "
          f"{row['signals']:>7.0f} | {row['win_rate']:>6.1f}% | {row['avg_profit']:>10.2f}% | "
          f"{row['score']:>8.1f} {highlight}")

# Analyze best
best = viable.iloc[0]
print("\n" + "=" * 80)
print("🏆 BEST BALANCE:")
print("=" * 80)
print(f"\nType: {best['type']}")
print(f"RSI: {best['rsi']}")
print(f"ATR Min: {best['atr_min']:.1f}%")
print(f"Range96 Min: {best['range96_min']:.0f}%")
print(f"Signals: {best['signals']:.0f} ({best['signals']/3:.1f} per month)")
print(f"Win Rate: {best['win_rate']:.1f}%")
print(f"Avg Profit: {best['avg_profit']:.2f}%")

# Show the actual data for best config
if 'BOTH' in best['type']:
    parts = best['type'].split()
    rsi_info = parts[1]  # L25/S70
    long_rsi = int(rsi_info.split('/')[0][1:])
    short_rsi = int(rsi_info.split('/')[1][1:])

    long_mask = (df['rsi_level'] == long_rsi) & (df['atr_pct'] >= best['atr_min']) & (df['range_96'] >= best['range96_min'])
    short_mask = (df['rsi_level'] == short_rsi) & (df['atr_pct'] >= best['atr_min']) & (df['range_96'] >= best['range96_min'])
    best_data = df[long_mask | short_mask]

    print(f"\nLONG trades: {long_mask.sum()} ({(df[long_mask]['is_winner'].sum() / long_mask.sum() * 100):.1f}% win rate)")
    print(f"SHORT trades: {short_mask.sum()} ({(df[short_mask]['is_winner'].sum() / short_mask.sum() * 100):.1f}% win rate)")
else:
    mask = (df['rsi_level'] == best['rsi']) & (df['atr_pct'] >= best['atr_min']) & (df['range_96'] >= best['range96_min'])
    best_data = df[mask]

print(f"\nSL Hit Rate: {(best_data['hit_sl'].sum() / len(best_data)) * 100:.1f}%")
print(f"Max Best Profit: {best_data['best_profit'].max():.2f}%")
print(f"Max Worst DD: {best_data['worst_drawdown'].min():.2f}%")

# Show next best alternatives
print("\n" + "=" * 80)
print("TOP ALTERNATIVES:")
print("=" * 80)

for i, (idx, row) in enumerate(viable.iloc[1:6].iterrows(), 2):
    print(f"\n#{i}: {row['type']} - RSI {row['rsi']}, ATR>{row['atr_min']:.1f}%, Range96>{row['range96_min']:.0f}%")
    print(f"    Signals: {row['signals']:.0f} | Win%: {row['win_rate']:.1f}% | Avg Profit: {row['avg_profit']:.2f}%")

print("\n" + "=" * 80)
