"""
Comprehensive NQ Futures Optimization
Test multiple RSI bands, limit offsets, and SL/TP multipliers
"""
import pandas as pd
import numpy as np
import sys
sys.path.insert(0, '/workspaces/Carebiuro_windykacja')
from portfolio_simulation_FIXED import backtest_coin_FIXED

# Load NQ futures data
df = pd.read_csv('trading/nq_futures_1h_90d.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

print('='*100)
print('🔧 NQ FUTURES COMPREHENSIVE OPTIMIZATION')
print('='*100)
print()
print(f'Data: {len(df)} candles, 90 days')
print(f'Period: {df["timestamp"].min()} to {df["timestamp"].max()}')
print()

# Parameter grid - test everything
rsi_configs = [
    (25, 70),  # Crypto tight
    (30, 70),  # Crypto medium
    (30, 65),  # Crypto wide
    (35, 65),  # Futures narrow
    (40, 60),  # Futures wide (ES best)
]

limit_offsets = [0.1, 0.2, 0.3, 0.4, 0.5]
sl_mults = [0.5, 1.0, 1.5, 2.0]
tp_mults = [1.0, 1.5, 2.0, 3.0, 4.0]  # Add 4.0x for asymmetric

total_combos = len(rsi_configs) * len(limit_offsets) * len(sl_mults) * len(tp_mults)

print('Testing:')
print(f'  RSI Bands: {len(rsi_configs)} configs')
print(f'  Limit Offsets: 0.1% to 0.5%')
print(f'  Stop Loss: 0.5x to 2.0x ATR')
print(f'  Take Profit: 1.0x to 4.0x ATR')
print()
print(f'Total combinations: {total_combos}')
print()

results = []
count = 0

for rsi_low, rsi_high in rsi_configs:
    for limit_offset in limit_offsets:
        for sl_mult in sl_mults:
            for tp_mult in tp_mults:
                count += 1
                if count % 20 == 0:
                    print(f'Progress: {count}/{total_combos}... ({count/total_combos*100:.1f}%)')

                trades = backtest_coin_FIXED(
                    df, 'NQ',
                    rsi_low=rsi_low,
                    rsi_high=rsi_high,
                    limit_offset_pct=limit_offset,
                    stop_atr_mult=sl_mult,
                    tp_atr_mult=tp_mult
                )

                if len(trades) == 0:
                    continue

                # Calculate metrics
                total_return = trades['pnl_pct'].sum()

                # Calculate max drawdown
                equity = 1000.0
                peak = 1000.0
                max_dd = 0.0

                for pnl_pct in trades['pnl_pct']:
                    equity += equity * (pnl_pct / 100)
                    if equity > peak:
                        peak = equity
                    dd = ((equity - peak) / peak) * 100
                    if dd < max_dd:
                        max_dd = dd

                final_equity = equity
                rr_ratio = abs(total_return / max_dd) if max_dd != 0 else 0
                win_rate = len(trades[trades['pnl_pct'] > 0]) / len(trades) * 100

                # Exit reason breakdown
                tp_exits = len(trades[trades['exit_reason'] == 'TP'])
                sl_exits = len(trades[trades['exit_reason'] == 'STOP'])
                rsi_exits = len(trades[trades['exit_reason'] == 'RSI'])

                results.append({
                    'rsi_low': rsi_low,
                    'rsi_high': rsi_high,
                    'limit': limit_offset,
                    'sl': sl_mult,
                    'tp': tp_mult,
                    'trades': len(trades),
                    'return': total_return,
                    'max_dd': max_dd,
                    'rr_ratio': rr_ratio,
                    'win_rate': win_rate,
                    'final_equity': final_equity,
                    'tp_pct': (tp_exits / len(trades) * 100) if len(trades) > 0 else 0,
                    'sl_pct': (sl_exits / len(trades) * 100) if len(trades) > 0 else 0,
                    'rsi_pct': (rsi_exits / len(trades) * 100) if len(trades) > 0 else 0,
                })

print()
print('='*100)
print('📊 TOP 30 CONFIGURATIONS (sorted by R/R ratio)')
print('='*100)
print()

results_df = pd.DataFrame(results)
results_df = results_df.sort_values('rr_ratio', ascending=False)

print(f'{"RSI":<10} {"Limit":<8} {"SL":<6} {"TP":<6} {"Trades":<8} {"Return":<10} {"Max DD":<10} '
      f'{"R/R":<8} {"Win%":<8} {"TP%":<6} {"SL%":<6} {"Final $"}')
print('-'*100)

for _, row in results_df.head(30).iterrows():
    print(f'{row["rsi_low"]}/{row["rsi_high"]:<6} {row["limit"]:<8.1f} {row["sl"]:<6.1f} '
          f'{row["tp"]:<6.1f} {row["trades"]:<8} '
          f'{row["return"]:>8.2f}% {row["max_dd"]:>8.2f}% '
          f'{row["rr_ratio"]:>6.2f}x {row["win_rate"]:>6.1f}% '
          f'{row["tp_pct"]:>5.1f}% {row["sl_pct"]:>5.1f}% '
          f'${row["final_equity"]:>8.2f}')

print()
print('='*100)
print('🏆 ABSOLUTE BEST CONFIGURATION')
print('='*100)
print()

best = results_df.iloc[0]
print(f'RSI: {best["rsi_low"]}/{best["rsi_high"]}')
print(f'Limit Offset: {best["limit"]}%')
print(f'Stop Loss: {best["sl"]}x ATR')
print(f'Take Profit: {best["tp"]}x ATR')
print()
print(f'Return: {best["return"]:+.2f}%')
print(f'Max DD: {best["max_dd"]:.2f}%')
print(f'R/R Ratio: {best["rr_ratio"]:.2f}x')
print(f'Win Rate: {best["win_rate"]:.1f}%')
print(f'Trades: {best["trades"]}')
print(f'Final Equity: ${best["final_equity"]:.2f}')
print()
print(f'Exit Breakdown:')
print(f'  Take Profit: {best["tp_pct"]:.1f}%')
print(f'  Stop Loss: {best["sl_pct"]:.1f}%')
print(f'  RSI Exit: {best["rsi_pct"]:.1f}%')
print()

# Compare with crypto and ES
print('='*100)
print('📊 NQ OPTIMIZED vs ES vs CRYPTO')
print('='*100)
print()

portfolio_avg_rr = (22.03 + 21.36 + 20.20 + 13.28 + 12.38 + 10.66 + 9.53 + 8.38 + 7.13) / 9

print(f'{"Asset":<25} {"R/R":<10} {"Return":<12} {"Max DD":<12} {"Trades"}')
print('-'*100)
print(f'{"NQ OPTIMIZED":<25} {best["rr_ratio"]:<10.2f}x {best["return"]:>+8.2f}% {" "*3} '
      f'{best["max_dd"]:>6.2f}% {" "*5} {best["trades"]}')
print(f'{"NQ Initial (3.27x)":<25} {"3.27x":<10} {"+4.80%":<12} {"-1.47%":<12} {"24"}')
print(f'{"ES Optimized (2.55x)":<25} {"2.55x":<10} {"+2.45%":<12} {"-0.96%":<12} {"20"}')
print()
print(f'{"Crypto Portfolio Avg":<25} {portfolio_avg_rr:<10.2f}x')
print(f'{"MOODENG (Best)":<25} {"26.96x":<10} {"+74.79":<12} {"-2.78%":<12} {"20"}')
print(f'{"PEPE (Worst)":<25} {"7.13x":<10} {"+21.72":<12} {"-3.04%":<12} {"12"}')
print()

print('='*100)
print('💡 VERDICT')
print('='*100)
print()

improvement = ((best["rr_ratio"] - 3.27) / 3.27) * 100
print(f'Improvement over initial NQ config: {improvement:+.1f}%')
print()

if best["rr_ratio"] > 7.13:
    print(f'✅ NQ OPTIMIZED ({best["rr_ratio"]:.2f}x) BEATS PEPE (7.13x)!')
    print(f'   → WORTH ADDING to crypto portfolio')
    print()
    print(f'   Portfolio would become: 9 crypto + NQ futures = 10 assets')
else:
    print(f'❌ NQ OPTIMIZED ({best["rr_ratio"]:.2f}x) still underperforms PEPE (7.13x)')
    print(f'   Gap: {7.13 - best["rr_ratio"]:.2f}x ({((7.13 - best["rr_ratio"]) / 7.13) * 100:.1f}% worse)')
    print()
    print(f'   → Stick with crypto-only portfolio')

print()

# Save results
results_df.to_csv('trading/results/nq_futures_optimization_full.csv', index=False)
print('💾 Saved full optimization results to: trading/results/nq_futures_optimization_full.csv')

# Save best config trades
best_trades = backtest_coin_FIXED(
    df, 'NQ',
    rsi_low=best['rsi_low'],
    rsi_high=best['rsi_high'],
    limit_offset_pct=best['limit'],
    stop_atr_mult=best['sl'],
    tp_atr_mult=best['tp']
)
best_trades.to_csv('trading/results/nq_futures_best_optimized.csv', index=False)
print('💾 Saved best config trades to: trading/results/nq_futures_best_optimized.csv')

print()
print('='*100)
print('📈 TOP 5 BY DIFFERENT METRICS')
print('='*100)
print()

# Top 5 by return
print('TOP 5 BY TOTAL RETURN:')
print(f'{"RSI":<10} {"Limit":<8} {"SL":<6} {"TP":<6} {"Return":<10} {"R/R":<8} {"Trades"}')
print('-'*80)
for _, row in results_df.nlargest(5, 'return').iterrows():
    print(f'{row["rsi_low"]}/{row["rsi_high"]:<6} {row["limit"]:<8.1f} {row["sl"]:<6.1f} '
          f'{row["tp"]:<6.1f} {row["return"]:>8.2f}% {row["rr_ratio"]:>6.2f}x {row["trades"]}')

print()
print('TOP 5 BY WIN RATE:')
print(f'{"RSI":<10} {"Limit":<8} {"SL":<6} {"TP":<6} {"Win%":<10} {"R/R":<8} {"Trades"}')
print('-'*80)
for _, row in results_df.nlargest(5, 'win_rate').iterrows():
    print(f'{row["rsi_low"]}/{row["rsi_high"]:<6} {row["limit"]:<8.1f} {row["sl"]:<6.1f} '
          f'{row["tp"]:<6.1f} {row["win_rate"]:>8.1f}% {row["rr_ratio"]:>6.2f}x {row["trades"]}')

print()
print('TOP 5 BY TRADE COUNT (most active):')
print(f'{"RSI":<10} {"Limit":<8} {"SL":<6} {"TP":<6} {"Trades":<10} {"R/R":<8} {"Return"}')
print('-'*80)
for _, row in results_df.nlargest(5, 'trades').iterrows():
    print(f'{row["rsi_low"]}/{row["rsi_high"]:<6} {row["limit"]:<8.1f} {row["sl"]:<6.1f} '
          f'{row["tp"]:<6.1f} {row["trades"]:<10} {row["rr_ratio"]:>6.2f}x {row["return"]:>+7.2f}%')

print()
