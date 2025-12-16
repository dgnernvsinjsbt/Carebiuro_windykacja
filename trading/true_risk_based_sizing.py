#!/usr/bin/env python3
"""
TRUE risk-based position sizing with dynamic SL distances per coin
Each trade gets position sized based on its ACTUAL stop loss distance
"""

import pandas as pd
import numpy as np

print("=" * 100)
print("TRUE RISK-BASED POSITION SIZING (Dynamic SL per Coin)")
print("=" * 100)

# Load trades
df_sep_dec = pd.read_csv('portfolio_trade_log_chronological.csv')
df_sep_dec['date'] = pd.to_datetime(df_sep_dec['date'])

df_dec_8_15 = pd.read_csv('dec8_15_all_trades.csv')
df_dec_8_15['entry_time'] = pd.to_datetime(df_dec_8_15['entry_time'])

# Calculate actual average SL distance per coin from Sep-Dec data
sl_trades = df_sep_dec[df_sep_dec['exit_reason'] == 'SL']
avg_sl_by_coin = {}

for coin in df_sep_dec['coin'].unique():
    coin_sl = sl_trades[sl_trades['coin'] == coin]
    if len(coin_sl) > 0:
        avg_sl_by_coin[coin] = abs(coin_sl['pnl_pct'].mean())
    else:
        # Use overall average if no SL data for this coin
        avg_sl_by_coin[coin] = 2.64  # Overall average

print("ACTUAL STOP LOSS DISTANCES BY COIN:")
print("-" * 100)
for coin, sl_dist in sorted(avg_sl_by_coin.items(), key=lambda x: x[1]):
    print(f"  {coin:15} SL Distance: {sl_dist:.2f}%")

# Map symbol names
symbol_map = {
    'AIXBT-USDT': 'AIXBT', 'AIXBT': 'AIXBT',
    'MELANIA-USDT': 'MELANIA', 'MELANIA': 'MELANIA',
    'MOODENG-USDT': 'MOODENG', 'MOODENG': 'MOODENG',
    'PEPE-USDT': 'PEPE', 'PEPE': 'PEPE', '1000PEPE-USDT': 'PEPE',
    'DOGE-USDT': 'DOGE', 'DOGE': 'DOGE',
    'CRV-USDT': 'CRV', 'CRV': 'CRV',
    'TRUMPSOL-USDT': 'TRUMPSOL', 'TRUMPSOL': 'TRUMPSOL',
    'UNI-USDT': 'UNI', 'UNI': 'UNI',
    'XLM-USDT': 'XLM', 'XLM': 'XLM',
}

# Combine all trades
df_sep_dec['symbol'] = df_sep_dec['coin']

all_trades = []

for _, trade in df_sep_dec.iterrows():
    all_trades.append({
        'symbol': trade['coin'],
        'date': trade['date'],
        'pnl_pct': trade['pnl_pct'],
        'exit_reason': trade['exit_reason'],
    })

for _, trade in df_dec_8_15.iterrows():
    # Map Dec 8-15 symbols to coin names
    coin_name = symbol_map.get(trade['symbol'], trade['symbol'])
    all_trades.append({
        'symbol': coin_name,
        'date': trade['entry_time'],
        'pnl_pct': trade['pnl_pct'],
        'exit_reason': trade['exit_reason'],
    })

trades_df = pd.DataFrame(all_trades)
trades_df = trades_df.sort_values('date').reset_index(drop=True)

# Test different risk percentages
risk_levels = [1.0, 2.0, 3.0, 4.0, 5.0, 10.0]

results = {}

for risk_pct in risk_levels:
    print(f"\n{'='*100}")
    print(f"SIMULATING: {risk_pct}% RISK PER TRADE (Dynamic Position Sizing)")
    print(f"{'='*100}")

    capital = 100.0
    initial_capital = 100.0
    peak_capital = 100.0
    max_dd_pct = 0.0

    liquidated = False
    liquidation_trade_num = None

    trade_log = []
    position_sizes = []

    for idx, trade in trades_df.iterrows():
        if liquidated:
            break

        # Get this coin's actual average SL distance
        coin = trade['symbol']
        sl_distance_pct = avg_sl_by_coin.get(coin, 2.64)

        # Calculate position size based on THIS trade's SL distance
        # Position size = (Risk% × Capital) / (SL_distance% × Leverage)
        leverage = 10.0
        position_size_pct = (risk_pct / (sl_distance_pct * leverage)) * 100
        position_size = capital * (position_size_pct / 100)

        position_sizes.append(position_size_pct)

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
        'avg_position_size_pct': np.mean(position_sizes),
        'min_position_size_pct': np.min(position_sizes),
        'max_position_size_pct': np.max(position_sizes),
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
        print(f"   Position Size: {np.min(position_sizes):.2f}% to {np.max(position_sizes):.2f}% (avg {np.mean(position_sizes):.2f}%)")

# Summary table
print("\n" + "=" * 100)
print("COMPARISON TABLE: TRUE RISK-BASED POSITION SIZING")
print("=" * 100)
print(f"\n{'Risk%':<8} {'Avg Pos%':<10} {'Pos Range':<20} {'Start':>10} {'Final':>12} {'Profit':>12} "
      f"{'Return%':>10} {'MaxDD%':>10} {'R/DD':>8} {'Status':<15}")
print("-" * 120)

for risk_pct in risk_levels:
    r = results[risk_pct]
    status = "💀 Liquidated" if r['liquidated'] else "✅ Survived"
    pos_range = f"{r['min_position_size_pct']:.1f}-{r['max_position_size_pct']:.1f}%"

    print(f"{risk_pct:<8.1f} {r['avg_position_size_pct']:<10.2f} {pos_range:<20} "
          f"${r['starting']:>9.2f} ${r['final']:>11.2f} ${r['profit']:>+11.2f} "
          f"{r['return_pct']:>+9.2f}% {r['max_dd_pct']:>+9.2f}% {r['return_dd_ratio']:>7.2f}x {status:<15}")

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

# Show liquidations
liquidated_list = [r for r in risk_levels if results[r]['liquidated']]
if liquidated_list:
    print(f"\n💀 LIQUIDATED:")
    for risk_pct in liquidated_list:
        r = results[risk_pct]
        print(f"   {risk_pct}% risk: Liquidated on trade #{r['liquidation_trade']}/{r['total_trades']}")
else:
    print(f"\n✅ NO LIQUIDATIONS! All risk levels survived.")

print(f"\n💡 WHY THIS IS DIFFERENT:")
print(f"   • Position sizes now VARY based on each coin's actual stop loss distance")
print(f"   • Tight stops (XLM: 1.66%) → LARGER positions (risk 4% with 1.66% SL = {4.0/(1.66*10)*100:.1f}% position)")
print(f"   • Wide stops (TRUMPSOL: 4.53%) → SMALLER positions (risk 4% with 4.53% SL = {4.0/(4.53*10)*100:.1f}% position)")
print(f"   • This means each trade risks EXACTLY the same % if SL hits")
print(f"   • But winning trades contribute differently based on their position size")

print(f"\n📊 EXAMPLE POSITION SIZES AT 4% RISK:")
for coin in sorted(avg_sl_by_coin.keys(), key=lambda x: avg_sl_by_coin[x]):
    sl = avg_sl_by_coin[coin]
    pos_size = (4.0 / (sl * 10)) * 100
    print(f"   • {coin:15} (SL {sl:.2f}%) → Position size: {pos_size:.2f}%")
