"""
Test combinations of filters on FARTCOIN 30M to maximize returns
"""

import pandas as pd
import numpy as np

# Load the trade analysis
trades_df = pd.read_csv('results/fartcoin_30m_trade_analysis.csv')

print("="*100)
print("TESTING COMBINED FILTERS - FARTCOIN 30M")
print("="*100)

original_return = trades_df['pnl_pct'].sum()
original_trades = len(trades_df)
original_winners = len(trades_df[trades_df['win']])
original_losers = len(trades_df[~trades_df['win']])

print(f"\nOriginal Strategy:")
print(f"  Trades: {original_trades}")
print(f"  Winners: {original_winners} ({original_winners/original_trades*100:.1f}%)")
print(f"  Losers: {original_losers} ({original_losers/original_trades*100:.1f}%)")
print(f"  Return: {original_return:.2f}%")

# Define filter combinations to test
filter_combos = [
    # Single best
    ('Mom7d < 0%', lambda df: df['entry_momentum_7d'] < 0),

    # Double combos with Mom7d < 0%
    ('Mom7d<0 + ATR<6%', lambda df: (df['entry_momentum_7d'] < 0) & (df['entry_atr_pct'] < 6)),
    ('Mom7d<0 + RSI<60', lambda df: (df['entry_momentum_7d'] < 0) & (df['entry_rsi'] < 60)),
    ('Mom7d<0 + Vol>0.8x', lambda df: (df['entry_momentum_7d'] < 0) & (df['entry_volume_ratio'] > 0.8)),
    ('Mom7d<0 + BelowEMA50', lambda df: (df['entry_momentum_7d'] < 0) & (~df['entry_above_ema50'])),

    # Triple combos
    ('Mom7d<0 + ATR<6 + RSI<60', lambda df: (df['entry_momentum_7d'] < 0) & (df['entry_atr_pct'] < 6) & (df['entry_rsi'] < 60)),
    ('Mom7d<0 + ATR<5 + Vol>0.8x', lambda df: (df['entry_momentum_7d'] < 0) & (df['entry_atr_pct'] < 5) & (df['entry_volume_ratio'] > 0.8)),
    ('Mom7d<0 + RSI<55 + BelowEMA50', lambda df: (df['entry_momentum_7d'] < 0) & (df['entry_rsi'] < 55) & (~df['entry_above_ema50'])),

    # Aggressive combos (more filters)
    ('Mom7d<0 + ATR<5 + RSI<55 + Vol>0.8x',
     lambda df: (df['entry_momentum_7d'] < 0) & (df['entry_atr_pct'] < 5) & (df['entry_rsi'] < 55) & (df['entry_volume_ratio'] > 0.8)),

    ('Mom7d<-5 + ATR<5 + RSI<50',
     lambda df: (df['entry_momentum_7d'] < -5) & (df['entry_atr_pct'] < 5) & (df['entry_rsi'] < 50)),

    # Volume-focused
    ('Vol>0.8x + ATR<5', lambda df: (df['entry_volume_ratio'] > 0.8) & (df['entry_atr_pct'] < 5)),
    ('Vol>1.0x + Mom7d<0', lambda df: (df['entry_volume_ratio'] > 1.0) & (df['entry_momentum_7d'] < 0)),

    # Momentum-focused
    ('Mom7d<-5 + Mom14d<0', lambda df: (df['entry_momentum_7d'] < -5) & (df['entry_momentum_14d'] < 0)),
    ('Mom7d<-10 + ATR<6', lambda df: (df['entry_momentum_7d'] < -10) & (df['entry_atr_pct'] < 6)),
]

results = []

for name, filter_func in filter_combos:
    filtered = trades_df[filter_func(trades_df)]

    if len(filtered) == 0:
        continue

    total_return = filtered['pnl_pct'].sum()
    winners = len(filtered[filtered['win']])
    losers = len(filtered[~filtered['win']])
    win_rate = winners / len(filtered) * 100

    # Calculate efficiency
    trades_removed = original_trades - len(filtered)
    losers_removed = original_losers - losers
    winners_kept_pct = winners / original_winners * 100
    losers_removed_pct = losers_removed / original_losers * 100

    # Calculate max drawdown (simple approximation)
    filtered['cumsum'] = filtered['pnl_pct'].cumsum()
    filtered['running_max'] = filtered['cumsum'].expanding().max()
    filtered['dd'] = filtered['cumsum'] - filtered['running_max']
    max_dd = filtered['dd'].min()

    results.append({
        'filter': name,
        'trades': len(filtered),
        'removed': trades_removed,
        'return': total_return,
        'return_improvement': total_return - original_return,
        'win_rate': win_rate,
        'winners': winners,
        'losers': losers,
        'winners_kept_pct': winners_kept_pct,
        'losers_removed': losers_removed,
        'losers_removed_pct': losers_removed_pct,
        'max_dd': max_dd,
    })

results_df = pd.DataFrame(results)
results_df = results_df.sort_values('return', ascending=False)

print("\n" + "="*100)
print("COMBINED FILTER RESULTS (sorted by return)")
print("="*100)
print(f"\n{'Filter':<35} {'Trades':<8} {'Return':<10} {'Improve':<9} {'WR%':<7} {'W.Kept%':<9} {'L.Rem%':<9}")
print("-"*100)

for _, row in results_df.iterrows():
    print(f"{row['filter']:<35} {row['trades']:<8.0f} {row['return']:<9.1f}% {row['return_improvement']:>+8.1f}% {row['win_rate']:<6.1f}% {row['winners_kept_pct']:<8.1f}% {row['losers_removed_pct']:<8.1f}%")

print("\n" + "="*100)
print("TOP 5 RECOMMENDATIONS")
print("="*100)

for idx, row in results_df.head(5).iterrows():
    print(f"\n#{idx+1}: {row['filter']}")
    print(f"  Return: {row['return']:.2f}% ({row['return_improvement']:+.2f}% vs original)")
    print(f"  Trades: {row['trades']:.0f}/{original_trades} ({row['trades']/original_trades*100:.1f}% kept)")
    print(f"  Win Rate: {row['win_rate']:.1f}% (original: {original_winners/original_trades*100:.1f}%)")
    print(f"  Winners kept: {row['winners']:.0f}/{original_winners} ({row['winners_kept_pct']:.1f}%)")
    print(f"  Losers removed: {row['losers_removed']:.0f}/{original_losers} ({row['losers_removed_pct']:.1f}%)")
    print(f"  Max DD: {row['max_dd']:.2f}%")

    # Calculate quality score
    quality = row['return_improvement'] + (row['losers_removed_pct'] / 10) - (100 - row['winners_kept_pct'])
    print(f"  Quality Score: {quality:.1f}")

# Save results
results_df.to_csv('results/fartcoin_30m_combined_filters.csv', index=False)

print("\n✓ Saved combined filter results")
print("="*100)
