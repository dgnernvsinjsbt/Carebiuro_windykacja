#!/usr/bin/env python3
"""
CLEAR SUMMARY: Full 3-month performance (Sep 15 - Dec 15)
"""

print("=" * 110)
print("FULL 3-MONTH RESULTS: Sep 15 - Dec 15, 2025 (91 days)")
print("=" * 110)
print("\nSetup: 9 separate accounts, $10 each, 100% position sizing per trade\n")

# Data from simulation
coins = [
    {'coin': 'MELANIA', 'sep_dec7': 123.76, 'dec8_15': 0.00, 'total': 123.76, 'max_dd': -2.86, 'trades': 10, 'win_rate': 80.0, 'final': 22.38},
    {'coin': 'CRV', 'sep_dec7': 27.95, 'dec8_15': 0.95, 'total': 29.16, 'max_dd': -1.70, 'trades': 14, 'win_rate': 85.7, 'final': 12.92},
    {'coin': 'XLM', 'sep_dec7': 33.78, 'dec8_15': 0.00, 'total': 33.78, 'max_dd': -2.06, 'trades': 16, 'win_rate': 81.2, 'final': 13.38},
    {'coin': 'DOGE', 'sep_dec7': 25.34, 'dec8_15': 6.05, 'total': 32.92, 'max_dd': -2.19, 'trades': 17, 'win_rate': 94.1, 'final': 13.29},
    {'coin': 'UNI', 'sep_dec7': 30.83, 'dec8_15': -0.67, 'total': 29.95, 'max_dd': -3.88, 'trades': 21, 'win_rate': 76.2, 'final': 12.99},
    {'coin': 'PEPE', 'sep_dec7': 32.82, 'dec8_15': -3.69, 'total': 27.92, 'max_dd': -9.41, 'trades': 26, 'win_rate': 73.1, 'final': 12.79},
    {'coin': 'TRUMPSOL', 'sep_dec7': 13.03, 'dec8_15': 0.67, 'total': 13.78, 'max_dd': -6.22, 'trades': 14, 'win_rate': 78.6, 'final': 11.38},
    {'coin': 'AIXBT', 'sep_dec7': 40.24, 'dec8_15': -9.94, 'total': 26.30, 'max_dd': -12.10, 'trades': 33, 'win_rate': 63.6, 'final': 12.63},
    {'coin': 'MOODENG', 'sep_dec7': 30.98, 'dec8_15': -3.31, 'total': 26.64, 'max_dd': -13.44, 'trades': 27, 'win_rate': 63.0, 'final': 12.66},
]

print("DETAILED BREAKDOWN:")
print("-" * 110)
print(f"{'Coin':<10} {'Sep-Dec 7':>12} {'Dec 8-15':>12} {'Total Return':>14} {'Max DD':>10} "
      f"{'R/DD':>8} {'Final $':>10} {'Trades':>8} {'Win%':>7}")
print("-" * 110)

for c in sorted(coins, key=lambda x: x['total'], reverse=True):
    ratio = c['total'] / abs(c['max_dd'])

    # Status based on Dec 8-15
    if c['dec8_15'] > 5:
        status = "🚀"
    elif c['dec8_15'] > 0:
        status = "✅"
    elif c['dec8_15'] == 0:
        status = "💤"
    elif c['dec8_15'] > -5:
        status = "⚠️"
    else:
        status = "❌"

    print(f"{c['coin']:<10} {c['sep_dec7']:>+11.2f}% {c['dec8_15']:>+11.2f}% {status} "
          f"{c['total']:>+13.2f}% {c['max_dd']:>9.2f}% {ratio:>7.1f}x "
          f"${c['final']:>9.2f} {c['trades']:>8} {c['win_rate']:>6.1f}%")

print("-" * 110)
print(f"{'TOTAL':<10} {'(Portfolio)':>12} {'':>12}    "
      f"{'+38.25%':>13} {'-5.98%':>10} {'6.4x':>8} ${'124.42':>9} {'168':>8} {'74.4%':>7}")

print("\n" + "=" * 110)
print("WHAT THIS SHOWS:")
print("=" * 110)

print("\n1. TIME PERIODS:")
print("   • Sep 15 - Dec 7:  83 days (main backtest period)")
print("   • Dec 8-15:        8 days (the rough week we analyzed)")
print("   • TOTAL:           91 days (~3 months)")

print("\n2. KEY FINDINGS:")

# Winners in both periods
both_positive = [c for c in coins if c['sep_dec7'] > 0 and c['dec8_15'] > 0]
print(f"\n   ✅ CONSISTENT WINNERS (positive in both periods):")
for c in sorted(both_positive, key=lambda x: x['total'], reverse=True):
    print(f"      • {c['coin']:10} Sep-Dec7: +{c['sep_dec7']:.2f}% | Dec8-15: +{c['dec8_15']:.2f}% | Total: +{c['total']:.2f}%")

# No trades in Dec 8-15
no_dec_trades = [c for c in coins if c['dec8_15'] == 0]
print(f"\n   💤 NO SIGNALS IN DEC 8-15 (no trades that week):")
for c in no_dec_trades:
    print(f"      • {c['coin']:10} Sep-Dec7: +{c['sep_dec7']:.2f}% | Dec8-15: No trades | Total: +{c['total']:.2f}%")

# Positive Sep-Dec but negative Dec 8-15
crashed = [c for c in coins if c['sep_dec7'] > 20 and c['dec8_15'] < -3]
print(f"\n   ❌ CRASHED IN DEC 8-15 (strong Sep-Dec7, but lost >3% in Dec 8-15):")
for c in sorted(crashed, key=lambda x: x['dec8_15']):
    before = 10 * (1 + c['sep_dec7']/100)
    after = c['final']
    print(f"      • {c['coin']:10} Sep-Dec7: +{c['sep_dec7']:.2f}% (${before:.2f}) → Dec8-15: {c['dec8_15']:.2f}% → Final: ${after:.2f}")

print("\n3. RISK-ADJUSTED RANKINGS:")
print("\n   🏆 TIER 1 (R/DD >15x): MELANIA, CRV, XLM, DOGE")
print("      → Safe to use 5-10x leverage")
print("\n   ✅ TIER 2 (R/DD 5-15x): UNI")
print("      → Can use 3-5x leverage carefully")
print("\n   ❌ TIER 3 (R/DD <3x): PEPE, TRUMPSOL, AIXBT, MOODENG")
print("      → AVOID with leverage (high drawdowns)")

print("\n4. BOTTOM LINE:")
print(f"\n   Starting Capital: $90.00 (9 coins × $10)")
print(f"   Final Capital:    $124.42")
print(f"   Total Profit:     $34.42 (+38.25%)")
print(f"   Max Drawdown:     -5.98%")
print(f"   Return/DD Ratio:  6.40x")
print(f"\n   Period: Sep 15 - Dec 15, 2025 (91 days)")
print(f"   This is ~3 months of ALL trading data")

print("\n" + "=" * 110)
print("LEGEND:")
print("=" * 110)
print("  🚀 = Big winner in Dec 8-15 (>5% gain)")
print("  ✅ = Positive in Dec 8-15 (0-5% gain)")
print("  💤 = No trades in Dec 8-15")
print("  ⚠️ = Small loss in Dec 8-15 (0 to -5%)")
print("  ❌ = Big loss in Dec 8-15 (<-5%)")
