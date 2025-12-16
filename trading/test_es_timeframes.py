"""
Test ES Futures across multiple timeframes: 15m, 30m, 1h
Hypothesis: Faster charts capture more intraday volatility
"""
import pandas as pd
import numpy as np
import sys
sys.path.insert(0, '/workspaces/Carebiuro_windykacja')
from portfolio_simulation_FIXED import backtest_coin_FIXED

print('='*100)
print('⏱️  ES FUTURES MULTI-TIMEFRAME COMPARISON')
print('='*100)
print()
print('Testing RSI mean reversion strategy on 15min, 30min, and 1h charts')
print('Hypothesis: Faster timeframes = more signals + better volatility capture')
print()

# Test configurations
# Start with best 1h params, plus some variations for faster timeframes
test_configs = [
    # (rsi_low, rsi_high, limit_offset, sl_mult, tp_mult, name)

    # Best from 1h optimization
    (40, 60, 0.3, 0.5, 3.0, '1h Best (40/60, 0.3%, 0.5x SL, 3x TP)'),

    # Tighter RSI for faster timeframes (more signals)
    (35, 65, 0.3, 0.5, 3.0, 'Tighter RSI (35/65)'),
    (30, 70, 0.3, 0.5, 3.0, 'Even Tighter (30/70)'),

    # Tighter stops for faster noise
    (40, 60, 0.3, 1.0, 3.0, 'Wider SL (1.0x)'),
    (40, 60, 0.3, 0.5, 2.0, 'Tighter TP (2x)'),

    # Crypto-like for comparison
    (25, 70, 0.5, 1.0, 1.5, 'Crypto Baseline'),
]

timeframes = {
    '15m': ('trading/es_futures_15m_60d.csv', 60),  # (file, days)
    '30m': ('trading/es_futures_30m_60d.csv', 60),
    '1h': ('trading/es_futures_1h_90d.csv', 90),
}

all_results = []

for tf_name, (filepath, days) in timeframes.items():
    print('='*100)
    print(f'📊 TIMEFRAME: {tf_name.upper()}')
    print('='*100)
    print()

    # Load data
    df = pd.read_csv(filepath)
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    print(f'Data: {len(df)} candles, {days} days ({len(df)/days:.0f} candles/day)')
    print(f'Period: {df["timestamp"].min()} to {df["timestamp"].max()}')
    print()

    results = []

    for rsi_low, rsi_high, limit_offset, sl_mult, tp_mult, config_name in test_configs:
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

        # Exit breakdown
        tp_exits = len(trades[trades['exit_reason'] == 'TP'])
        sl_exits = len(trades[trades['exit_reason'] == 'STOP'])

        # Trades per day
        trades_per_day = len(trades) / days

        results.append({
            'timeframe': tf_name,
            'config': config_name,
            'rsi': f'{rsi_low}/{rsi_high}',
            'limit': limit_offset,
            'sl': sl_mult,
            'tp': tp_mult,
            'trades': len(trades),
            'trades_per_day': trades_per_day,
            'return': total_return,
            'max_dd': max_dd,
            'rr_ratio': rr_ratio,
            'win_rate': win_rate,
            'final_equity': final_equity,
            'tp_pct': (tp_exits / len(trades) * 100) if len(trades) > 0 else 0,
            'sl_pct': (sl_exits / len(trades) * 100) if len(trades) > 0 else 0,
        })

    # Sort by R/R ratio
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('rr_ratio', ascending=False)

    print(f'{"Config":<45} {"RSI":<8} {"Trades":<8} {"T/Day":<8} {"Return":<10} {"Max DD":<10} {"R/R":<8} {"Win%"}')
    print('-'*100)

    for _, row in results_df.iterrows():
        print(f'{row["config"]:<45} {row["rsi"]:<8} {row["trades"]:<8} '
              f'{row["trades_per_day"]:<8.2f} '
              f'{row["return"]:>8.2f}% {row["max_dd"]:>8.2f}% '
              f'{row["rr_ratio"]:>6.2f}x {row["win_rate"]:>6.1f}%')

    print()

    # Show best config
    if len(results_df) > 0:
        best = results_df.iloc[0]
        print(f'🏆 BEST: {best["config"]}')
        print(f'   {best["rr_ratio"]:.2f}x R/R, {best["return"]:+.2f}%, {best["trades"]} trades ({best["trades_per_day"]:.2f}/day)')
        print(f'   TP: {best["tp_pct"]:.1f}%, SL: {best["sl_pct"]:.1f}%')
        print()

    all_results.append(results_df)

# Final comparison across timeframes
print()
print('='*100)
print('🏁 MULTI-TIMEFRAME COMPARISON - BEST CONFIGS')
print('='*100)
print()

print(f'{"Timeframe":<12} {"Best Config":<45} {"R/R":<10} {"Return":<12} {"Max DD":<12} {"Trades":<10} {"T/Day"}')
print('-'*100)

for i, (tf_name, _) in enumerate(timeframes.items()):
    if i < len(all_results) and len(all_results[i]) > 0:
        best = all_results[i].iloc[0]
        print(f'{tf_name:<12} {best["config"]:<45} '
              f'{best["rr_ratio"]:<10.2f}x '
              f'{best["return"]:>+8.2f}% {" "*3} '
              f'{best["max_dd"]:>8.2f}% {" "*3} '
              f'{best["trades"]:<10} '
              f'{best["trades_per_day"]:.2f}')

print()
print('='*100)
print('💡 VERDICT')
print('='*100)
print()

# Find absolute best across all timeframes
best_overall = None
best_rr = 0

for i, results_df in enumerate(all_results):
    if len(results_df) > 0:
        best = results_df.iloc[0]
        if best['rr_ratio'] > best_rr:
            best_rr = best['rr_ratio']
            best_overall = (list(timeframes.keys())[i], best)

if best_overall:
    tf_name, best = best_overall
    print(f'🥇 BEST OVERALL: {tf_name.upper()} timeframe')
    print(f'   Config: {best["config"]}')
    print(f'   R/R: {best["rr_ratio"]:.2f}x')
    print(f'   Return: {best["return"]:+.2f}%')
    print(f'   Max DD: {best["max_dd"]:.2f}%')
    print(f'   Trades: {best["trades"]} ({best["trades_per_day"]:.2f}/day)')
    print(f'   Win Rate: {best["win_rate"]:.1f}%')
    print()

    # Compare with crypto
    portfolio_avg_rr = (22.03 + 21.36 + 20.20 + 13.28 + 12.38 + 10.66 + 9.53 + 8.38 + 7.13) / 9
    print(f'   vs Crypto Portfolio Avg: {portfolio_avg_rr:.2f}x R/R')
    print(f'   vs Crypto Best (MOODENG): 26.96x R/R')
    print(f'   vs Crypto Worst (PEPE): 7.13x R/R')
    print()

    if best['rr_ratio'] > 7.13:
        print(f'   ✅ ES ({best["rr_ratio"]:.2f}x) BEATS crypto worst (PEPE 7.13x)!')
        print(f'   → WORTH ADDING to portfolio')
    else:
        print(f'   ❌ ES ({best["rr_ratio"]:.2f}x) underperforms PEPE (7.13x)')
        print(f'   → Stick with crypto-only portfolio')
    print()

# Save best overall trades
if best_overall:
    tf_name, best = best_overall
    filepath, days = timeframes[tf_name]

    df = pd.read_csv(filepath)
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    rsi_low, rsi_high = map(int, best['rsi'].split('/'))

    best_trades = backtest_coin_FIXED(
        df, 'ES',
        rsi_low=rsi_low,
        rsi_high=rsi_high,
        limit_offset_pct=best['limit'],
        stop_atr_mult=best['sl'],
        tp_atr_mult=best['tp']
    )

    output_file = f'trading/results/es_futures_best_{tf_name}.csv'
    best_trades.to_csv(output_file, index=False)
    print(f'💾 Saved best config trades to: {output_file}')

print()
print('='*100)
print('📈 KEY INSIGHTS')
print('='*100)
print()
print('1. Signal Frequency: Faster timeframes = more signals per day')
print('   - 15m: ~2.7x more signals than 1h (64 vs 24 candles/day)')
print('   - 30m: ~1.3x more signals than 1h (32 vs 24 candles/day)')
print()
print('2. Volatility Capture: Faster charts catch intraday moves')
print('   - 1h smooths out noise but misses quick reversals')
print('   - 15m/30m catch mean reversion moves within single 1h candles')
print()
print('3. Parameter Sensitivity: Faster timeframes may need tighter RSI')
print('   - 1h: RSI 40/60 optimal (wider bands for less frequent signals)')
print('   - 15m/30m: May benefit from 30/70 or 35/65 (more signals)')
print()
