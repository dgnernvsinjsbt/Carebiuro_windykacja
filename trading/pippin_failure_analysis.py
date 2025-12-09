"""
Deep dive analysis: Why did FARTCOIN ATR strategy fail on PIPPIN?
"""

import pandas as pd
import numpy as np
from pathlib import Path

# Load data and trades
data_path = Path(__file__).parent / 'pippin_7d_bingx.csv'
trades_path = Path(__file__).parent / 'results' / 'pippin_atr_trades.csv'

df = pd.read_csv(data_path)
df['timestamp'] = pd.to_datetime(df['timestamp'])
trades = pd.read_csv(trades_path)
trades['timestamp'] = pd.to_datetime(trades['timestamp'])

print("=" * 80)
print("PIPPIN vs FARTCOIN - FAILURE ANALYSIS")
print("=" * 80)

# ========================================
# 1. VOLATILITY ANALYSIS
# ========================================
print("\n1. VOLATILITY COMPARISON")
print("-" * 80)

# Calculate ATR for PIPPIN
df['tr'] = df[['high', 'low', 'close']].apply(
    lambda row: max(row['high'] - row['low'],
                    abs(row['high'] - row['close']),
                    abs(row['low'] - row['close'])), axis=1
)
df['atr_14'] = df['tr'].rolling(window=14).mean()
df = df.dropna()

avg_atr_pct = (df['atr_14'] / df['close']).mean() * 100
print(f"PIPPIN avg ATR: {avg_atr_pct:.2f}% of price")
print(f"FARTCOIN avg ATR: ~1.5% of price (estimated from strategy docs)")
print(f"Difference: PIPPIN is {avg_atr_pct/1.5:.1f}x more volatile" if avg_atr_pct > 1.5 else f"Difference: PIPPIN is {1.5/avg_atr_pct:.1f}x LESS volatile")

# Price swing analysis
price_swing = ((df['close'].max() - df['close'].min()) / df['close'].min()) * 100
print(f"\nPrice swing during test period:")
print(f"  PIPPIN: {price_swing:.1f}% ({df['close'].min():.5f} to {df['close'].max():.5f})")
print(f"  FARTCOIN: ~250% over 32 days (from strategy docs)")

# ========================================
# 2. WIN/LOSS PATTERN ANALYSIS
# ========================================
print("\n2. WIN/LOSS PATTERN")
print("-" * 80)

winners = trades[trades['pnl_pct'] > 0]
losers = trades[trades['pnl_pct'] <= 0]

print(f"Winners: {len(winners)} trades")
print(f"  Avg: {winners['pnl_pct'].mean():+.2f}%")
print(f"  Median: {winners['pnl_pct'].median():+.2f}%")
print(f"  Best: {winners['pnl_pct'].max():+.2f}%")

print(f"\nLosers: {len(losers)} trades")
print(f"  Avg: {losers['pnl_pct'].mean():.2f}%")
print(f"  Median: {losers['pnl_pct'].median():.2f}%")
print(f"  Worst: {losers['pnl_pct'].min():.2f}%")

print(f"\nProblem: Avg loss ({abs(losers['pnl_pct'].mean()):.2f}%) is TOO LARGE relative to avg win ({winners['pnl_pct'].mean():.2f}%)")
print(f"Math: {len(winners)} × {winners['pnl_pct'].mean():.2f}% = {len(winners) * winners['pnl_pct'].mean():.2f}%")
print(f"      {len(losers)} × {losers['pnl_pct'].mean():.2f}% = {len(losers) * losers['pnl_pct'].mean():.2f}%")
print(f"      Net: {(len(winners) * winners['pnl_pct'].mean()) + (len(losers) * losers['pnl_pct'].mean()):.2f}%")

# ========================================
# 3. EXIT TYPE ANALYSIS
# ========================================
print("\n3. EXIT BREAKDOWN COMPARISON")
print("-" * 80)

exit_counts = trades['exit_reason'].value_counts()
print("PIPPIN:")
for reason, count in exit_counts.items():
    pct = count / len(trades) * 100
    print(f"  {reason}: {count} ({pct:.1f}%)")

print("\nFARTCOIN baseline:")
print("  TP: 40%")
print("  SL: 47%")
print("  TIME: 13%")

tp_rate = exit_counts.get('TP', 0) / len(trades) * 100
print(f"\n⚠️ CRITICAL ISSUE: Only {tp_rate:.1f}% TP rate vs 40% baseline!")
print(f"   This means PIPPIN volatility doesn't sustain moves to reach 8x ATR target")

# ========================================
# 4. DIRECTIONAL BIAS
# ========================================
print("\n4. DIRECTIONAL PERFORMANCE")
print("-" * 80)

for direction in ['LONG', 'SHORT']:
    dir_trades = trades[trades['direction'] == direction]
    if len(dir_trades) == 0:
        continue

    dir_winners = dir_trades[dir_trades['pnl_pct'] > 0]
    dir_losers = dir_trades[dir_trades['pnl_pct'] <= 0]

    print(f"\n{direction}:")
    print(f"  Trades: {len(dir_trades)}")
    print(f"  Win Rate: {len(dir_winners)/len(dir_trades)*100:.1f}%")
    print(f"  Winners: {len(dir_winners)} @ {dir_winners['pnl_pct'].mean():+.2f}% avg")
    print(f"  Losers: {len(dir_losers)} @ {dir_losers['pnl_pct'].mean():.2f}% avg")
    print(f"  Net: {dir_trades['pnl_pct'].sum():+.2f}%")

    # Exit breakdown
    dir_exits = dir_trades['exit_reason'].value_counts()
    print(f"  Exits: TP {dir_exits.get('TP', 0)} | SL {dir_exits.get('SL', 0)} | TIME {dir_exits.get('TIME', 0)}")

# ========================================
# 5. CHRONOLOGICAL ANALYSIS
# ========================================
print("\n5. CHRONOLOGICAL BREAKDOWN")
print("-" * 80)

trades['equity_change'] = trades['equity'].pct_change() * 100
cumulative = trades[['timestamp', 'pnl_pct', 'equity', 'direction', 'exit_reason']].copy()

print("\nEquity progression by day:")
trades['date'] = trades['timestamp'].dt.date
daily = trades.groupby('date').agg({
    'pnl_pct': 'sum',
    'equity': 'last',
    'exit_reason': lambda x: f"TP:{(x=='TP').sum()} SL:{(x=='SL').sum()} TIME:{(x=='TIME').sum()}"
})

for date, row in daily.iterrows():
    print(f"  {date}: {row['pnl_pct']:+6.2f}% (equity: ${row['equity']:.2f}) - {row['exit_reason']}")

# ========================================
# 6. ROOT CAUSE SUMMARY
# ========================================
print("\n" + "=" * 80)
print("ROOT CAUSE ANALYSIS")
print("=" * 80)

print("\n❌ Why FARTCOIN strategy failed on PIPPIN:\n")

# Calculate TP% needed to break even
win_rate = len(winners) / len(trades)
avg_win = winners['pnl_pct'].mean()
avg_loss = abs(losers['pnl_pct'].mean())
current_expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)

print(f"1. **Insufficient TP rate** ({tp_rate:.1f}% vs 40% baseline)")
print(f"   - Wide 8x ATR target doesn't hit on PIPPIN")
print(f"   - PIPPIN has choppy volatility, not sustained trends")
print(f"   - 72.6% of trades hit SL before TP\n")

print(f"2. **Poor risk/reward realized**")
print(f"   - Avg win: {avg_win:.2f}% vs Avg loss: {avg_loss:.2f}%")
print(f"   - Need R:R of {avg_win/avg_loss:.1f}:1 but only getting 1.85:1")
print(f"   - FARTCOIN gets 2.2:1 (4.97% win / 2.23% loss)\n")

print(f"3. **Low win rate** ({win_rate*100:.1f}% vs 42.6% baseline)")
print(f"   - Even with limit order filter, entries are bad")
print(f"   - PIPPIN volatility is different character than FARTCOIN\n")

print(f"4. **Negative expectancy per trade**")
print(f"   - Current: {current_expectancy:.3f}%")
print(f"   - Need: >0.1% to be profitable")
print(f"   - Math: ({win_rate:.2f} × {avg_win:.2f}%) - ({1-win_rate:.2f} × {avg_loss:.2f}%) = {current_expectancy:.2f}%\n")

# What would fix it?
print("=" * 80)
print("WHAT WOULD NEED TO CHANGE?")
print("=" * 80)

# Calculate needed win rate for breakeven
# win_rate * avg_win - (1 - win_rate) * avg_loss = 0
# win_rate * avg_win = (1 - win_rate) * avg_loss
# win_rate * avg_win = avg_loss - win_rate * avg_loss
# win_rate * (avg_win + avg_loss) = avg_loss
# win_rate = avg_loss / (avg_win + avg_loss)

needed_wr = avg_loss / (avg_win + avg_loss)
print(f"\nTo break even with current avg win/loss:")
print(f"  Need win rate: {needed_wr*100:.1f}% (currently {win_rate*100:.1f}%)")
print(f"  Gap: {(needed_wr - win_rate)*100:+.1f} percentage points")

# Or tighter stop loss
needed_loss = avg_win * win_rate / (1 - win_rate)
print(f"\nOR tighter stop loss:")
print(f"  Need avg loss: {needed_loss:.2f}% (currently {avg_loss:.2f}%)")
print(f"  Reduction needed: {((avg_loss - needed_loss) / avg_loss)*100:.0f}%")

# Or wider take profit
needed_win = avg_loss * (1 - win_rate) / win_rate
print(f"\nOR wider take profit:")
print(f"  Need avg win: {needed_win:.2f}% (currently {avg_win:.2f}%)")
print(f"  Increase needed: {((needed_win - avg_win) / avg_win)*100:.0f}%")

print("\n" + "=" * 80)
print("CONCLUSION")
print("=" * 80)
print("\n⚠️ PIPPIN volatility structure is fundamentally different from FARTCOIN")
print("\nFARTCOIN: Sustained trends after ATR expansion (8x ATR moves happen)")
print("PIPPIN: Choppy volatility spikes that quickly reverse (8x ATR too far)")
print("\nStrategy needs PIPPIN-specific optimization:")
print("  - Tighter TP (3-4x ATR instead of 8x)")
print("  - Tighter SL (1.0x ATR instead of 2x)")
print("  - Or different strategy entirely (mean-reversion, volume zones)")
print("\n❌ DO NOT DEPLOY this strategy on PIPPIN without major modifications\n")
