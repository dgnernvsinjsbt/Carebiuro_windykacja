"""
Test RSI Mean Reversion Strategy on FARTCOIN
Compare with the 9-coin portfolio parameters
"""
import pandas as pd
import numpy as np
import sys
sys.path.insert(0, '/workspaces/Carebiuro_windykacja')
from portfolio_simulation_FIXED import backtest_coin_FIXED

# Load FARTCOIN data
df = pd.read_csv('bingx-trading-bot/trading/fartcoin_usdt_90d_1h.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

print('='*100)
print('🪙 FARTCOIN RSI MEAN REVERSION BACKTEST')
print('='*100)
print()
print(f'Data: {len(df)} candles ({df["timestamp"].min()} to {df["timestamp"].max()})')
print()

# Test different RSI parameters
test_configs = [
    # (rsi_low, rsi_high, limit_offset, sl_mult, tp_mult, name)
    (25, 70, 1.5, 1.0, 1.5, 'Like CRV (best)'),
    (27, 65, 1.5, 1.5, 2.0, 'Like MELANIA'),
    (27, 65, 1.5, 1.0, 1.0, 'Like PEPE'),
    (27, 65, 2.0, 1.5, 1.5, 'Like MOODENG'),
    (30, 65, 1.5, 2.0, 1.0, 'Like AIXBT'),
    (30, 65, 1.0, 1.0, 0.5, 'Like TRUMPSOL'),
]

results = []

for rsi_low, rsi_high, limit_offset, sl_mult, tp_mult, name in test_configs:
    trades = backtest_coin_FIXED(
        df, 'FARTCOIN-USDT',
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
print('📊 FARTCOIN RSI BACKTEST RESULTS (90 days)')
print('='*100)
print()

print(f'{"Config":<20} {"RSI":<8} {"Trades":<8} {"Return":<10} {"Max DD":<10} {"R/R":<8} {"Win%":<8} {"Final $"}')
print('-'*100)

for _, row in results_df.iterrows():
    print(f'{row["config"]:<20} {row["rsi"]:<8} {row["trades"]:<8} '
          f'{row["return"]:>8.2f}% {row["max_dd"]:>8.2f}% '
          f'{row["rr_ratio"]:>6.2f}x {row["win_rate"]:>6.1f}% '
          f'${row["final_equity"]:>8.2f}')

print()
print('='*100)
print('🏆 BEST CONFIG FOR FARTCOIN')
print('='*100)
print()

best = results_df.iloc[0]
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

# Compare with portfolio average
portfolio_avg_rr = (22.03 + 21.36 + 20.20 + 13.28 + 12.38 + 10.66 + 9.53 + 8.38 + 7.13) / 9
print('='*100)
print('📊 COMPARISON WITH 9-COIN PORTFOLIO')
print('='*100)
print()
print(f'FARTCOIN Best R/R: {best["rr_ratio"]:.2f}x')
print(f'Portfolio Average: {portfolio_avg_rr:.2f}x')
print(f'Portfolio Best (CRV): 22.03x')
print(f'Portfolio Worst (PEPE): 7.13x')
print()

if best["rr_ratio"] > 7.13:
    print(f'✅ FARTCOIN ({best["rr_ratio"]:.2f}x) beats PEPE (7.13x) - WORTH ADDING!')
else:
    print(f'❌ FARTCOIN ({best["rr_ratio"]:.2f}x) underperforms PEPE (7.13x) - skip it')
print()

# Save best config
best_config_trades = backtest_coin_FIXED(
    df, 'FARTCOIN-USDT',
    rsi_low=int(best['rsi'].split('/')[0]),
    rsi_high=int(best['rsi'].split('/')[1]),
    limit_offset_pct=best['limit'],
    stop_atr_mult=best['sl'],
    tp_atr_mult=best['tp']
)

best_config_trades.to_csv('trading/results/fartcoin_rsi_best.csv', index=False)
print(f'💾 Saved best config trades to: trading/results/fartcoin_rsi_best.csv')
