"""
Comprehensive ES Futures Optimization
Test limit offsets 0.1-0.5% and various SL/TP ATR multipliers
"""
import pandas as pd
import numpy as np
import sys
sys.path.insert(0, '/workspaces/Carebiuro_windykacja')
from portfolio_simulation_FIXED import backtest_coin_FIXED

# Load ES futures data
df = pd.read_csv('trading/es_futures_1h_90d.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

print('='*100)
print('🔧 ES FUTURES OPTIMIZATION - COMPREHENSIVE PARAMETER SWEEP')
print('='*100)
print()
print(f'Data: {len(df)} candles, 90 days, 23h/day trading')
print()
print('Testing:')
print('  - RSI: 40/60 (best signal generator from previous test)')
print('  - Limit Offsets: 0.1%, 0.2%, 0.3%, 0.4%, 0.5%')
print('  - Stop Loss: 0.5x, 1.0x, 1.5x, 2.0x ATR')
print('  - Take Profit: 1.0x, 1.5x, 2.0x, 3.0x ATR')
print()
print(f'Total combinations: {5 * 4 * 4} = 80')
print()

# Parameter grid
rsi_low, rsi_high = 40, 60  # Best from previous test
limit_offsets = [0.1, 0.2, 0.3, 0.4, 0.5]
sl_mults = [0.5, 1.0, 1.5, 2.0]
tp_mults = [1.0, 1.5, 2.0, 3.0]

results = []
total = len(limit_offsets) * len(sl_mults) * len(tp_mults)
count = 0

for limit_offset in limit_offsets:
    for sl_mult in sl_mults:
        for tp_mult in tp_mults:
            count += 1
            if count % 10 == 0:
                print(f'Progress: {count}/{total}...')

            trades = backtest_coin_FIXED(
                df, 'ES',
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

print('\n' + '='*100)
print('📊 TOP 20 CONFIGURATIONS (sorted by R/R ratio)')
print('='*100)
print()

results_df = pd.DataFrame(results)
results_df = results_df.sort_values('rr_ratio', ascending=False)

print(f'{"Limit":<8} {"SL":<6} {"TP":<6} {"Trades":<8} {"Return":<10} {"Max DD":<10} {"R/R":<8} {"Win%":<8} '
      f'{"TP%":<6} {"SL%":<6} {"RSI%"}')
print('-'*100)

for _, row in results_df.head(20).iterrows():
    print(f'{row["limit"]:<8.1f} {row["sl"]:<6.1f} {row["tp"]:<6.1f} {row["trades"]:<8} '
          f'{row["return"]:>8.2f}% {row["max_dd"]:>8.2f}% '
          f'{row["rr_ratio"]:>6.2f}x {row["win_rate"]:>6.1f}% '
          f'{row["tp_pct"]:>5.1f}% {row["sl_pct"]:>5.1f}% {row["rsi_pct"]:>5.1f}%')

print()
print('='*100)
print('🏆 BEST CONFIGURATION')
print('='*100)
print()

best = results_df.iloc[0]
print(f'RSI: {rsi_low}/{rsi_high}')
print(f'Limit Offset: {best["limit"]}%')
print(f'Stop Loss: {best["sl"]}x ATR')
print(f'Take Profit: {best["tp"]}x ATR')
print()
print(f'Return: {best["return"]:+.2f}%')
print(f'Max DD: {best["max_dd"]:.2f}%')
print(f'R/R Ratio: {best["rr_ratio"]:.2f}x')
print(f'Win Rate: {best["win_rate"]:.1f}%')
print(f'Trades: {best["trades"]}')
print()
print(f'Exit Breakdown:')
print(f'  Take Profit: {best["tp_pct"]:.1f}%')
print(f'  Stop Loss: {best["sl_pct"]:.1f}%')
print(f'  RSI Exit: {best["rsi_pct"]:.1f}%')
print()

# Compare with crypto
portfolio_avg_rr = (22.03 + 21.36 + 20.20 + 13.28 + 12.38 + 10.66 + 9.53 + 8.38 + 7.13) / 9
print('='*100)
print('📊 VS CRYPTO PORTFOLIO')
print('='*100)
print()
print(f'ES Futures Best: {best["rr_ratio"]:.2f}x R/R, {best["return"]:+.2f}%, {best["trades"]} trades')
print(f'Crypto Avg: {portfolio_avg_rr:.2f}x R/R')
print(f'Crypto Best (CRV): 22.03x R/R, +39.92%')
print(f'Crypto Worst (PEPE): 7.13x R/R, +50.99%')
print()

if best["rr_ratio"] > 7.13:
    print(f'✅ ES ({best["rr_ratio"]:.2f}x) beats PEPE (7.13x)!')
else:
    print(f'❌ ES ({best["rr_ratio"]:.2f}x) underperforms PEPE (7.13x)')

# Save results
results_df.to_csv('trading/results/es_futures_optimization.csv', index=False)
print()
print('💾 Saved full results to: trading/results/es_futures_optimization.csv')

# Save best config trades
best_trades = backtest_coin_FIXED(
    df, 'ES',
    rsi_low=rsi_low,
    rsi_high=rsi_high,
    limit_offset_pct=best['limit'],
    stop_atr_mult=best['sl'],
    tp_atr_mult=best['tp']
)
best_trades.to_csv('trading/results/es_futures_best_optimized.csv', index=False)
print('💾 Saved best config trades to: trading/results/es_futures_best_optimized.csv')
