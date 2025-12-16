"""
Smart RSI parameter optimization for S&P 500 Futures (ES)
Test multiple RSI bands to find what works for lower volatility
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
print('📊 S&P 500 FUTURES (ES) - INTELLIGENT RSI PARAMETER SWEEP')
print('='*100)
print()
print(f'Data: {len(df)} candles ({df["timestamp"].min()} to {df["timestamp"].max()})')
print(f'Period: 90 days, ~23h/day trading (like crypto!)')
print()

# Test multiple RSI parameter combinations
# Start with crypto params, then widen the bands for lower volatility
test_configs = [
    # (rsi_low, rsi_high, limit_offset, sl_mult, tp_mult, name)

    # Crypto parameters (baseline)
    (25, 70, 1.5, 1.0, 1.5, 'Crypto Tight (25/70)'),
    (27, 65, 1.5, 1.5, 2.0, 'Crypto Medium (27/65)'),
    (30, 65, 1.0, 1.0, 0.5, 'Crypto Wide (30/65)'),

    # Wider bands for lower volatility indices
    (30, 60, 1.0, 1.0, 1.5, 'Futures Narrow (30/60)'),
    (30, 60, 0.5, 1.5, 2.0, 'Futures Tight Limit (30/60)'),
    (35, 60, 1.0, 1.0, 1.5, 'Futures Medium (35/60)'),
    (35, 60, 0.5, 1.5, 2.0, 'Futures Med Tight (35/60)'),
    (40, 60, 1.0, 1.0, 1.0, 'Futures Wide (40/60)'),
    (40, 60, 0.5, 1.0, 1.5, 'Futures Wide Tight (40/60)'),

    # Very wide bands
    (35, 65, 1.0, 1.0, 1.5, 'Wide Band (35/65)'),
    (40, 65, 0.5, 1.0, 1.0, 'Very Wide (40/65)'),
]

results = []

for rsi_low, rsi_high, limit_offset, sl_mult, tp_mult, name in test_configs:
    trades = backtest_coin_FIXED(
        df, 'ES',
        rsi_low=rsi_low,
        rsi_high=rsi_high,
        limit_offset_pct=limit_offset,
        stop_atr_mult=sl_mult,
        tp_atr_mult=tp_mult
    )

    if len(trades) == 0:
        results.append({
            'config': name,
            'rsi': f'{rsi_low}/{rsi_high}',
            'limit': limit_offset,
            'trades': 0,
            'return': 0,
            'max_dd': 0,
            'rr_ratio': 0,
            'win_rate': 0,
            'final_equity': 1000
        })
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

    results.append({
        'config': name,
        'rsi': f'{rsi_low}/{rsi_high}',
        'limit': limit_offset,
        'sl': sl_mult,
        'tp': tp_mult,
        'trades': len(trades),
        'return': total_return,
        'max_dd': max_dd,
        'rr_ratio': rr_ratio,
        'win_rate': win_rate,
        'final_equity': final_equity
    })

# Sort by R/R ratio
results_df = pd.DataFrame(results)
results_df = results_df.sort_values('rr_ratio', ascending=False)

print('='*100)
print('📊 ES FUTURES BACKTEST RESULTS (90 days, sorted by R/R ratio)')
print('='*100)
print()

print(f'{"Config":<25} {"RSI":<10} {"Limit":<8} {"Trades":<8} {"Return":<10} {"Max DD":<10} {"R/R":<8} {"Win%"}')
print('-'*100)

for _, row in results_df.iterrows():
    print(f'{row["config"]:<25} {row["rsi"]:<10} {row["limit"]:<8.1f} {row["trades"]:<8} '
          f'{row["return"]:>8.2f}% {row["max_dd"]:>8.2f}% '
          f'{row["rr_ratio"]:>6.2f}x {row["win_rate"]:>6.1f}%')

print()
print('='*100)
print('🏆 BEST CONFIG FOR ES FUTURES')
print('='*100)
print()

if len(results_df[results_df['trades'] > 0]) > 0:
    best = results_df[results_df['trades'] > 0].iloc[0]
    print(f'Config: {best["config"]}')
    print(f'RSI: {best["rsi"]}')
    print(f'Limit Offset: {best["limit"]}%')
    print(f'Stop Loss: {best["sl"]}x ATR')
    print(f'Take Profit: {best["tp"]}x ATR')
    print()
    print(f'Return: +{best["return"]:.2f}%')
    print(f'Max DD: {best["max_dd"]:.2f}%')
    print(f'R/R Ratio: {best["rr_ratio"]:.2f}x')
    print(f'Win Rate: {best["win_rate"]:.1f}%')
    print(f'Trades: {best["trades"]}')
    print()

    # Compare with crypto portfolio
    portfolio_avg_rr = (22.03 + 21.36 + 20.20 + 13.28 + 12.38 + 10.66 + 9.53 + 8.38 + 7.13) / 9
    print('='*100)
    print('📊 COMPARISON WITH CRYPTO PORTFOLIO')
    print('='*100)
    print()
    print(f'ES Futures Best: {best["rr_ratio"]:.2f}x R/R, +{best["return"]:.2f}%, {best["trades"]} trades')
    print(f'Crypto Portfolio Avg: {portfolio_avg_rr:.2f}x R/R')
    print(f'Crypto Best (CRV): 22.03x R/R')
    print(f'Crypto Worst (PEPE): 7.13x R/R')
    print()

    if best["rr_ratio"] > 7.13:
        print(f'✅ ES ({best["rr_ratio"]:.2f}x) BEATS PEPE (7.13x) - WORTH CONSIDERING!')
    else:
        print(f'❌ ES ({best["rr_ratio"]:.2f}x) underperforms PEPE (7.13x)')

    # Show trade distribution
    print()
    print('='*100)
    print('📈 BEST CONFIG DETAILS')
    print('='*100)
    print()

    best_trades = backtest_coin_FIXED(
        df, 'ES',
        rsi_low=int(best['rsi'].split('/')[0]),
        rsi_high=int(best['rsi'].split('/')[1]),
        limit_offset_pct=best['limit'],
        stop_atr_mult=best['sl'],
        tp_atr_mult=best['tp']
    )

    best_trades.to_csv('trading/results/es_futures_best.csv', index=False)
    print(f'💾 Saved best config trades to: trading/results/es_futures_best.csv')

    # Show sample trades
    print()
    print('Sample trades:')
    print(best_trades[['entry_time', 'exit_time', 'side', 'pnl_pct', 'exit_reason']].head(10).to_string(index=False))

else:
    print('❌ No valid configurations generated any trades!')
    print('Try even wider RSI bands or different parameters.')
