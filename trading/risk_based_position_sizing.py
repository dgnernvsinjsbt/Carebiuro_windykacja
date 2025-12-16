#!/usr/bin/env python3
"""
Risk-based position sizing with 10x leverage
Position size calculated so that SL hit = exact % loss of capital
"""

import pandas as pd
import numpy as np

print("=" * 100)
print("RISK-BASED POSITION SIZING WITH 10X LEVERAGE")
print("=" * 100)
print("Position sized so that stop loss = exact % of capital risked\n")

# Load Sep 15 - Dec 7 trades
df_sep_dec = pd.read_csv('portfolio_trade_log_chronological.csv')
df_sep_dec['date'] = pd.to_datetime(df_sep_dec['date'])

# Load Dec 8-15 trades
df_dec_8_15 = pd.read_csv('dec8_15_all_trades.csv')
df_dec_8_15['entry_time'] = pd.to_datetime(df_dec_8_15['entry_time'])

# Combine all trades
df_sep_dec['symbol'] = df_sep_dec['coin'].apply(lambda x: x if 'USDT' in str(x) else f"{x}-USDT")

all_trades = []

for _, trade in df_sep_dec.iterrows():
    all_trades.append({
        'symbol': trade['symbol'],
        'date': trade['date'],
        'pnl_pct': trade['pnl_pct'],
        'exit_reason': trade['exit_reason'],
    })

for _, trade in df_dec_8_15.iterrows():
    all_trades.append({
        'symbol': trade['symbol'],
        'date': trade['entry_time'],
        'pnl_pct': trade['pnl_pct'],
        'exit_reason': trade['exit_reason'],
    })

trades_df = pd.DataFrame(all_trades)
trades_df = trades_df.sort_values('date').reset_index(drop=True)

# Map symbol names
symbol_map = {
    'AIXBT-USDT': 'AIXBT-USDT', 'AIXBT': 'AIXBT-USDT',
    'MELANIA-USDT': 'MELANIA-USDT', 'MELANIA': 'MELANIA-USDT',
    'MOODENG-USDT': 'MOODENG-USDT', 'MOODENG': 'MOODENG-USDT',
    'PEPE-USDT': 'PEPE-USDT', 'PEPE': 'PEPE-USDT', '1000PEPE-USDT': 'PEPE-USDT',
    'DOGE-USDT': 'DOGE-USDT', 'DOGE': 'DOGE-USDT',
    'CRV-USDT': 'CRV-USDT', 'CRV': 'CRV-USDT',
    'TRUMPSOL-USDT': 'TRUMPSOL-USDT', 'TRUMPSOL': 'TRUMPSOL-USDT',
    'UNI-USDT': 'UNI-USDT', 'UNI': 'UNI-USDT',
    'XLM-USDT': 'XLM-USDT', 'XLM': 'XLM-USDT',
}

trades_df['symbol'] = trades_df['symbol'].map(symbol_map)

# Estimate average stop loss distance from losing trades
# We'll use a conservative estimate of 3% average SL distance
ASSUMED_SL_DISTANCE_PCT = 3.0  # Conservative estimate

print(f"Assumed Stop Loss Distance: {ASSUMED_SL_DISTANCE_PCT}%")
print(f"With 10x leverage, this becomes {ASSUMED_SL_DISTANCE_PCT * 10}% of position value\n")

# Test different risk percentages
risk_levels = [1.0, 2.0, 3.0, 4.0, 5.0, 10.0]

results = {}

for risk_pct in risk_levels:
    print(f"\n{'='*100}")
    print(f"SIMULATING: {risk_pct}% RISK PER TRADE")
    print(f"{'='*100}")

    capital = 100.0
    initial_capital = 100.0
    peak_capital = 100.0
    max_dd_pct = 0.0

    liquidated = False
    liquidation_trade_num = None

    trade_log = []

    for idx, trade in trades_df.iterrows():
        if liquidated:
            break

        # Calculate position size based on risk
        # Position size = (Capital × Risk%) / (SL_distance% × Leverage)
        leverage = 10.0
        position_size_pct = (risk_pct / (ASSUMED_SL_DISTANCE_PCT * leverage)) * 100
        position_size = capital * (position_size_pct / 100)

        # Apply leverage to P&L
        leveraged_pnl_pct = trade['pnl_pct'] * leverage

        # Calculate P&L in USD
        pnl_usd = position_size * (leveraged_pnl_pct / 100)

        # Update capital
        new_capital = capital + pnl_usd

        # Check for liquidation
        if new_capital <= 0:
            liquidated = True
            liquidation_trade_num = idx + 1
            capital = 0
            break

        capital = new_capital

        # Track peak and drawdown
        if capital > peak_capital:
            peak_capital = capital

        dd_pct = ((capital - peak_capital) / peak_capital) * 100
        if dd_pct < max_dd_pct:
            max_dd_pct = dd_pct

    final_capital = capital
    total_return = ((final_capital - initial_capital) / initial_capital) * 100

    # Calculate win/loss stats
    trades_completed = liquidation_trade_num if liquidated else len(trades_df)

    results[risk_pct] = {
        'starting': initial_capital,
        'final': final_capital,
        'profit': final_capital - initial_capital,
        'return_pct': total_return,
        'peak': peak_capital,
        'max_dd_pct': max_dd_pct,
        'return_dd_ratio': abs(total_return / max_dd_pct) if max_dd_pct != 0 else 0,
        'trades_completed': trades_completed,
        'total_trades': len(trades_df),
        'liquidated': liquidated,
        'liquidation_trade': liquidation_trade_num,
        'position_size_pct': position_size_pct
    }

    if liquidated:
        print(f"\n💀 LIQUIDATED on trade #{liquidation_trade_num}/{len(trades_df)}")
        print(f"   Survived {trades_completed - 1} trades ({(trades_completed/len(trades_df)*100):.1f}%)")
        print(f"   Peak before death: ${peak_capital:.2f}")
    else:
        print(f"\n✅ SURVIVED!")
        print(f"   Starting: ${initial_capital:.2f}")
        print(f"   Final:    ${final_capital:.2f}")
        print(f"   Profit:   ${final_capital - initial_capital:+.2f}")
        print(f"   Return:   {total_return:+.2f}%")
        print(f"   Peak:     ${peak_capital:.2f}")
        print(f"   Max DD:   {max_dd_pct:.2f}%")
        print(f"   R/DD:     {abs(total_return / max_dd_pct):.2f}x")
        print(f"   Avg Position Size: {position_size_pct:.2f}% of capital")

# Summary table
print("\n" + "=" * 100)
print("COMPARISON TABLE: RISK-BASED POSITION SIZING")
print("=" * 100)
print(f"\n{'Risk%':<8} {'Pos%':<10} {'Start':>10} {'Final':>12} {'Profit':>12} {'Return%':>10} "
      f"{'MaxDD%':>10} {'R/DD':>8} {'Status':<15}")
print("-" * 100)

for risk_pct in risk_levels:
    r = results[risk_pct]
    status = "💀 Liquidated" if r['liquidated'] else "✅ Survived"

    print(f"{risk_pct:<8.1f} {r['position_size_pct']:<10.2f} ${r['starting']:>9.2f} ${r['final']:>11.2f} "
          f"${r['profit']:>+11.2f} {r['return_pct']:>+9.2f}% {r['max_dd_pct']:>+9.2f}% "
          f"{r['return_dd_ratio']:>7.2f}x {status:<15}")

# Add baseline for comparison (10% fixed position sizing)
print("-" * 100)
print(f"{'BASELINE':<8} {'10.00%':<10} ${'100.00':>9} ${'1554.70':>11} ${'+1454.70':>11} "
      f"{'+1454.70%':>9} {'-28.61%':>9} {'50.84x':>7} {'✅ Survived':<15}")
print("(Fixed 10% position sizing from earlier simulation)")

print("\n" + "=" * 100)
print("KEY INSIGHTS:")
print("=" * 100)

# Find best performer
best_survivor = None
best_return = -float('inf')
for risk_pct in risk_levels:
    r = results[risk_pct]
    if not r['liquidated'] and r['return_pct'] > best_return:
        best_return = r['return_pct']
        best_survivor = risk_pct

if best_survivor:
    print(f"\n🏆 BEST PERFORMER: {best_survivor}% risk per trade")
    print(f"   Return: {results[best_survivor]['return_pct']:+.2f}%")
    print(f"   Max DD: {results[best_survivor]['max_dd_pct']:.2f}%")
    print(f"   R/DD: {results[best_survivor]['return_dd_ratio']:.2f}x")

# Find safest
safest = None
safest_dd = -float('inf')
for risk_pct in risk_levels:
    r = results[risk_pct]
    if not r['liquidated'] and r['max_dd_pct'] > safest_dd:
        safest_dd = r['max_dd_pct']
        safest = risk_pct

if safest:
    print(f"\n🛡️ SAFEST: {safest}% risk per trade")
    print(f"   Max DD: {results[safest]['max_dd_pct']:.2f}%")
    print(f"   Return: {results[safest]['return_pct']:+.2f}%")

# Show liquidations
liquidated_list = [r for r in risk_levels if results[r]['liquidated']]
if liquidated_list:
    print(f"\n💀 LIQUIDATED:")
    for risk_pct in liquidated_list:
        r = results[risk_pct]
        print(f"   {risk_pct}% risk: Liquidated on trade #{r['liquidation_trade']}/{r['total_trades']}")
else:
    print(f"\n✅ NO LIQUIDATIONS! All risk levels survived.")

print(f"\n💡 RECOMMENDATIONS:")
print(f"   • Lower risk % = smaller positions = smoother equity curve but lower returns")
print(f"   • Higher risk % = larger positions = higher returns but bigger drawdowns")
print(f"   • The {best_survivor}% risk level maximized returns while surviving")
print(f"   • With 10x leverage, even 1% risk per trade gives significant exposure")

print(f"\n📊 POSITION SIZE EXPLANATION:")
print(f"   With {ASSUMED_SL_DISTANCE_PCT}% stop loss and 10x leverage:")
for risk_pct in risk_levels:
    pos_size = results[risk_pct]['position_size_pct']
    print(f"   • {risk_pct}% risk → {pos_size:.2f}% position size")
    print(f"     → If SL hits: {pos_size:.2f}% × {ASSUMED_SL_DISTANCE_PCT}% × 10x = {risk_pct}% account loss")
