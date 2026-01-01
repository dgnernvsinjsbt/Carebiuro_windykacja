"""
Test NASDAQ 100 Futures (NQ) on 1-hour timeframe
Using optimized ES parameters as baseline
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
print('📊 NASDAQ 100 FUTURES (NQ) - 1H TIMEFRAME TEST')
print('='*100)
print()
print(f'Data: {len(df)} candles, 90 days')
print(f'Period: {df["timestamp"].min()} to {df["timestamp"].max()}')
print()

# Test configurations - use ES-optimized params plus variations
test_configs = [
    # (rsi_low, rsi_high, limit_offset, sl_mult, tp_mult, name)

    # ES best params
    (40, 60, 0.3, 0.5, 3.0, 'ES Best (40/60, 0.3%, 0.5x SL, 3x TP)'),

    # Variations - NQ is more volatile than ES
    (40, 60, 0.3, 0.5, 2.0, 'Tighter TP (2x)'),
    (40, 60, 0.3, 1.0, 3.0, 'Wider SL (1.0x)'),
    (35, 65, 0.3, 0.5, 3.0, 'Tighter RSI (35/65)'),
    (30, 70, 0.3, 0.5, 3.0, 'Even Tighter (30/70)'),

    # Tighter limits for better fills
    (40, 60, 0.2, 0.5, 3.0, 'Tighter Limit (0.2%)'),
    (40, 60, 0.4, 0.5, 3.0, 'Wider Limit (0.4%)'),

    # Crypto baseline
    (25, 70, 1.5, 1.0, 1.5, 'Crypto Baseline'),
]

results = []

for rsi_low, rsi_high, limit_offset, sl_mult, tp_mult, config_name in test_configs:
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

    # Exit breakdown
    tp_exits = len(trades[trades['exit_reason'] == 'TP'])
    sl_exits = len(trades[trades['exit_reason'] == 'STOP'])
    rsi_exits = len(trades[trades['exit_reason'] == 'RSI'])

    results.append({
        'config': config_name,
        'rsi': f'{rsi_low}/{rsi_high}',
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

# Sort by R/R ratio
results_df = pd.DataFrame(results)
results_df = results_df.sort_values('rr_ratio', ascending=False)

print('='*100)
print('📊 NQ FUTURES BACKTEST RESULTS (sorted by R/R ratio)')
print('='*100)
print()

print(f'{"Config":<45} {"RSI":<8} {"Trades":<8} {"Return":<10} {"Max DD":<10} {"R/R":<8} {"Win%":<8} {"TP%":<6} {"SL%"}')
print('-'*100)

for _, row in results_df.iterrows():
    print(f'{row["config"]:<45} {row["rsi"]:<8} {row["trades"]:<8} '
          f'{row["return"]:>8.2f}% {row["max_dd"]:>8.2f}% '
          f'{row["rr_ratio"]:>6.2f}x {row["win_rate"]:>6.1f}% '
          f'{row["tp_pct"]:>5.1f}% {row["sl_pct"]:>5.1f}%')

print()
print('='*100)
print('🏆 BEST NQ CONFIG')
print('='*100)
print()

if len(results_df) > 0:
    best = results_df.iloc[0]
    print(f'Config: {best["config"]}')
    print(f'RSI: {best["rsi"]}')
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

    # Compare with ES and crypto
    print('='*100)
    print('📊 NQ vs ES vs CRYPTO')
    print('='*100)
    print()

    portfolio_avg_rr = (22.03 + 21.36 + 20.20 + 13.28 + 12.38 + 10.66 + 9.53 + 8.38 + 7.13) / 9

    print(f'{"Asset":<20} {"R/R Ratio":<12} {"Return":<12} {"Max DD":<12} {"Trades"}')
    print('-'*100)
    print(f'{"NQ (NASDAQ 100)":<20} {best["rr_ratio"]:<12.2f}x {best["return"]:>+8.2f}% {" "*3} {best["max_dd"]:>6.2f}% {" "*5} {best["trades"]}')
    print(f'{"ES (S&P 500)":<20} {"2.55x":<12} {"+2.45%":<12} {"-0.96%":<12} {"20"}')
    print()
    print(f'{"Crypto Portfolio Avg":<20} {portfolio_avg_rr:<12.2f}x {" "*12} {" "*12} {"~24/coin"}')
    print(f'{"MOODENG (Best)":<20} {"26.96x":<12} {"+74.79":<12} {"-2.78%":<12} {"20"}')
    print(f'{"PEPE (Worst)":<20} {"7.13x":<12} {"+21.72":<12} {"-3.04%":<12} {"12"}')
    print()

    print('='*100)
    print('💡 VERDICT')
    print('='*100)
    print()

    if best["rr_ratio"] > 7.13:
        print(f'✅ NQ ({best["rr_ratio"]:.2f}x) BEATS crypto worst (PEPE 7.13x)!')
        print(f'   → WORTH CONSIDERING for portfolio')
    else:
        print(f'❌ NQ ({best["rr_ratio"]:.2f}x) underperforms PEPE (7.13x)')
        print(f'   → Stick with crypto-only portfolio')
    print()

    if best["rr_ratio"] > 2.55:
        print(f'✅ NQ ({best["rr_ratio"]:.2f}x) BEATS ES (2.55x)')
        print(f'   → NQ is better than ES for RSI mean reversion')
    else:
        print(f'{"→ NQ similar to ES" if abs(best["rr_ratio"] - 2.55) < 0.5 else "❌ NQ worse than ES"}')
    print()

    # Save best config trades
    rsi_low, rsi_high = map(int, best['rsi'].split('/'))

    best_trades = backtest_coin_FIXED(
        df, 'NQ',
        rsi_low=rsi_low,
        rsi_high=rsi_high,
        limit_offset_pct=best['limit'],
        stop_atr_mult=best['sl'],
        tp_atr_mult=best['tp']
    )

    best_trades.to_csv('trading/results/nq_futures_best.csv', index=False)
    print('💾 Saved best config trades to: trading/results/nq_futures_best.csv')

else:
    print('❌ No valid configurations generated any trades!')

print()
print('='*100)
print('📈 NQ vs ES KEY DIFFERENCES')
print('='*100)
print()
print('NASDAQ 100 (NQ):')
print('  - Tech-heavy index (Apple, Microsoft, Amazon, etc.)')
print('  - Higher volatility than S&P 500')
print('  - More reactive to tech sector news')
print('  - Larger intraday swings → potentially better for mean reversion')
print()
print('S&P 500 (ES):')
print('  - Broader market (500 stocks)')
print('  - Lower volatility')
print('  - More stable, slower moves')
print('  - Best result: 2.55x R/R')
print()
