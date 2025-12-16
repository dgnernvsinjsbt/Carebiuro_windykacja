"""
Test RSI Mean Reversion Strategy on S&P 500 and NASDAQ 100
"""
import pandas as pd
import numpy as np
import sys
sys.path.insert(0, '/workspaces/Carebiuro_windykacja')
from portfolio_simulation_FIXED import backtest_coin_FIXED

print('='*100)
print('📊 S&P 500 & NASDAQ 100 RSI MEAN REVERSION BACKTEST')
print('='*100)
print()

# Test configs (same as crypto portfolio)
test_configs = [
    # (rsi_low, rsi_high, limit_offset, sl_mult, tp_mult, name)
    (25, 70, 1.5, 1.0, 1.5, 'Like CRV'),
    (27, 65, 1.5, 1.5, 2.0, 'Like MELANIA'),
    (27, 65, 1.5, 1.0, 1.0, 'Like PEPE'),
    (27, 65, 2.0, 1.5, 1.5, 'Like MOODENG'),
    (30, 65, 1.5, 2.0, 1.0, 'Like AIXBT'),
    (30, 65, 1.0, 1.0, 0.5, 'Like TRUMPSOL'),
]

indices = {
    'SPY': 'S&P 500',
    'QQQ': 'NASDAQ 100'
}

all_results = []

for ticker, name in indices.items():
    print(f'\n{"="*100}')
    print(f'📈 {name} ({ticker})')
    print(f'{"="*100}\n')

    # Load data
    df = pd.read_csv(f'trading/{ticker.lower()}_1h_90d.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    print(f'Data: {len(df)} candles ({df["timestamp"].min()} to {df["timestamp"].max()})')
    print()

    results = []

    for rsi_low, rsi_high, limit_offset, sl_mult, tp_mult, config_name in test_configs:
        trades = backtest_coin_FIXED(
            df, f'{ticker}',
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
            'ticker': ticker,
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
            'final_equity': final_equity
        })

    # Sort by R/R ratio
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('rr_ratio', ascending=False)

    print(f'{"Config":<15} {"RSI":<8} {"Trades":<8} {"Return":<10} {"Max DD":<10} {"R/R":<8} {"Win%":<8} {"Final $"}')
    print('-'*100)

    for _, row in results_df.iterrows():
        print(f'{row["config"]:<15} {row["rsi"]:<8} {row["trades"]:<8} '
              f'{row["return"]:>8.2f}% {row["max_dd"]:>8.2f}% '
              f'{row["rr_ratio"]:>6.2f}x {row["win_rate"]:>6.1f}% '
              f'${row["final_equity"]:>8.2f}')

    all_results.append(results_df)

    # Show best config
    if len(results_df) > 0:
        best = results_df.iloc[0]
        print()
        print(f'🏆 BEST: {best["config"]} → {best["rr_ratio"]:.2f}x R/R, +{best["return"]:.2f}%, {best["trades"]} trades')

# Final comparison
print()
print('='*100)
print('📊 INDICES vs CRYPTO PORTFOLIO COMPARISON')
print('='*100)
print()

if all_results:
    spy_best = all_results[0].iloc[0] if len(all_results) > 0 else None
    qqq_best = all_results[1].iloc[0] if len(all_results) > 1 else None

    portfolio_avg_rr = (22.03 + 21.36 + 20.20 + 13.28 + 12.38 + 10.66 + 9.53 + 8.38 + 7.13) / 9

    print(f'{"Asset":<20} {"Best R/R":<12} {"Return":<12} {"Max DD":<12} {"Trades"}')
    print('-'*100)
    print(f'{"Crypto Portfolio Avg":<20} {portfolio_avg_rr:<12.2f}x {"N/A":<12} {"N/A":<12} {"~24/coin"}')
    print(f'{"CRV (Best)":<20} {"22.03x":<12} {"+39.92%":<12} {"-1.83%":<12} {"17"}')
    print(f'{"PEPE (Worst)":<20} {"7.13x":<12} {"+50.99%":<12} {"-2.33%":<12} {"33"}')
    print()

    if spy_best is not None:
        print(f'{"S&P 500 (SPY)":<20} {spy_best["rr_ratio"]:<12.2f}x '
              f'{spy_best["return"]:>+6.2f}%{" ":<5} '
              f'{spy_best["max_dd"]:>6.2f}%{" ":<5} '
              f'{spy_best["trades"]}')

    if qqq_best is not None:
        print(f'{"NASDAQ 100 (QQQ)":<20} {qqq_best["rr_ratio"]:<12.2f}x '
              f'{qqq_best["return"]:>+6.2f}%{" ":<5} '
              f'{qqq_best["max_dd"]:>6.2f}%{" ":<5} '
              f'{qqq_best["trades"]}')

    print()
    print('='*100)
    print('💡 VERDICT')
    print('='*100)
    print()

    if spy_best is not None and spy_best["rr_ratio"] > 7.13:
        print(f'✅ SPY ({spy_best["rr_ratio"]:.2f}x) BEATS crypto portfolio worst (PEPE 7.13x)')
    elif spy_best is not None:
        print(f'❌ SPY ({spy_best["rr_ratio"]:.2f}x) underperforms PEPE (7.13x)')

    if qqq_best is not None and qqq_best["rr_ratio"] > 7.13:
        print(f'✅ QQQ ({qqq_best["rr_ratio"]:.2f}x) BEATS crypto portfolio worst (PEPE 7.13x)')
    elif qqq_best is not None:
        print(f'❌ QQQ ({qqq_best["rr_ratio"]:.2f}x) underperforms PEPE (7.13x)')

    print()
    print('NOTE: Traditional indices trade 6.5h/day (9:30-16:00 ET) vs crypto 24/7')
    print('      Fewer trading hours = fewer signals expected')
