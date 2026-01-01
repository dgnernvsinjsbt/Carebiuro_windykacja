"""
NQ Futures Monthly Optimization
Each month: Optimize on last 3 months, trade next month
Simulates real monthly recalibration for live trading
"""
import pandas as pd
import numpy as np
import sys
from datetime import datetime
sys.path.insert(0, '/workspaces/Carebiuro_windykacja')
from portfolio_simulation_FIXED import backtest_coin_FIXED

# Load 6-month NQ futures data
df = pd.read_csv('trading/nq_futures_1h_180d.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print('='*100)
print('📅 NQ FUTURES MONTHLY OPTIMIZATION')
print('='*100)
print()
print('Strategy: Each month, optimize on last 3 months, trade next month')
print()
print(f'Data: {len(df)} candles, {df["timestamp"].min().date()} to {df["timestamp"].max().date()}')
print()

# Reduced parameter grid (~30 combinations)
test_configs = [
    # (rsi_low, rsi_high, limit, sl, tp, name)
    # Best from full optimization
    (40, 60, 0.3, 2.0, 4.0, 'Static Best'),

    # RSI variations
    (35, 65, 0.3, 2.0, 4.0, 'Tighter RSI'),
    (40, 60, 0.3, 1.5, 4.0, 'Tighter SL'),
    (40, 60, 0.3, 2.0, 3.0, 'Tighter TP'),

    # Limit variations
    (40, 60, 0.2, 2.0, 4.0, 'Tighter Limit'),
    (40, 60, 0.4, 2.0, 4.0, 'Wider Limit'),

    # Asymmetric variations
    (40, 60, 0.3, 1.0, 4.0, 'Very Asymmetric (1x/4x)'),
    (40, 60, 0.3, 2.0, 2.0, 'Symmetric (2x/2x)'),

    # Conservative
    (40, 60, 0.3, 1.5, 3.0, 'Conservative'),
    (35, 65, 0.2, 1.5, 3.0, 'Conservative Tight'),

    # Aggressive
    (40, 60, 0.4, 2.0, 4.0, 'Aggressive'),
    (30, 70, 0.3, 2.0, 4.0, 'Crypto-like'),
]

# Define trading months
months = [
    {
        'name': 'September 2025',
        'opt_start': '2025-06-01',  # Jun-Jul-Aug
        'opt_end': '2025-09-01',
        'trade_start': '2025-09-01',  # Trade September
        'trade_end': '2025-10-01',
    },
    {
        'name': 'October 2025',
        'opt_start': '2025-07-01',  # Jul-Aug-Sep
        'opt_end': '2025-10-01',
        'trade_start': '2025-10-01',  # Trade October
        'trade_end': '2025-11-01',
    },
    {
        'name': 'November 2025',
        'opt_start': '2025-08-01',  # Aug-Sep-Oct
        'opt_end': '2025-11-01',
        'trade_start': '2025-11-01',  # Trade November
        'trade_end': '2025-12-01',
    },
    {
        'name': 'December 2025',
        'opt_start': '2025-09-01',  # Sep-Oct-Nov
        'opt_end': '2025-12-01',
        'trade_start': '2025-12-01',  # Trade December
        'trade_end': '2025-12-13',  # End of available data
    },
]

monthly_results = []
all_trades = []

for month_num, month in enumerate(months, 1):
    print('='*100)
    print(f'📊 MONTH {month_num}: {month["name"]}')
    print('='*100)
    print()

    # Get optimization data (3 months)
    opt_start = pd.to_datetime(month['opt_start']).tz_localize('UTC')
    opt_end = pd.to_datetime(month['opt_end']).tz_localize('UTC')
    opt_df = df[(df['timestamp'] >= opt_start) & (df['timestamp'] < opt_end)].copy()

    # Get trading data (1 month)
    trade_start = pd.to_datetime(month['trade_start']).tz_localize('UTC')
    trade_end = pd.to_datetime(month['trade_end']).tz_localize('UTC')
    trade_df = df[(df['timestamp'] >= trade_start) & (df['timestamp'] < trade_end)].copy()

    print(f'Optimization period: {opt_start.date()} to {opt_end.date()} ({len(opt_df)} candles)')
    print(f'Trading period: {trade_start.date()} to {trade_end.date()} ({len(trade_df)} candles)')
    print()

    if len(opt_df) < 100 or len(trade_df) < 50:
        print('❌ Insufficient data, skipping month')
        print()
        continue

    # Run optimization on 3-month window
    print(f'Testing {len(test_configs)} configurations...')
    print()

    best_rr = 0
    best_params = None
    best_config_name = None
    opt_results = []

    for rsi_low, rsi_high, limit, sl, tp, name in test_configs:
        try:
            trades = backtest_coin_FIXED(
                opt_df, 'NQ',
                rsi_low=rsi_low,
                rsi_high=rsi_high,
                limit_offset_pct=limit,
                stop_atr_mult=sl,
                tp_atr_mult=tp
            )

            if len(trades) < 3:
                continue

            # Calculate metrics
            total_return = trades['pnl_pct'].sum()

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

            if max_dd == 0:
                continue

            rr_ratio = abs(total_return / max_dd)
            win_rate = len(trades[trades['pnl_pct'] > 0]) / len(trades) * 100

            opt_results.append({
                'name': name,
                'rsi': f'{rsi_low}/{rsi_high}',
                'limit': limit,
                'sl': sl,
                'tp': tp,
                'trades': len(trades),
                'return': total_return,
                'max_dd': max_dd,
                'rr_ratio': rr_ratio,
                'win_rate': win_rate
            })

            if rr_ratio > best_rr:
                best_rr = rr_ratio
                best_params = (rsi_low, rsi_high, limit, sl, tp)
                best_config_name = name

        except:
            continue

    if not best_params:
        print('❌ No valid optimization found')
        print()
        continue

    # Show top 5 optimization results
    opt_df_results = pd.DataFrame(opt_results).sort_values('rr_ratio', ascending=False)

    print('Top 5 configurations (optimization period):')
    print(f'{"Config":<25} {"RSI":<10} {"Limit":<8} {"SL":<6} {"TP":<6} {"Trades":<8} {"R/R":<8} {"Return"}')
    print('-'*100)
    for _, row in opt_df_results.head(5).iterrows():
        print(f'{row["name"]:<25} {row["rsi"]:<10} {row["limit"]:<8.1f} {row["sl"]:<6.1f} '
              f'{row["tp"]:<6.1f} {row["trades"]:<8} {row["rr_ratio"]:<8.2f}x {row["return"]:>+7.2f}%')

    print()
    print(f'🏆 Selected: {best_config_name}')
    print(f'   RSI {best_params[0]}/{best_params[1]}, Limit {best_params[2]}%, SL {best_params[3]}x, TP {best_params[4]}x')
    print(f'   Optimization R/R: {best_rr:.2f}x')
    print()

    # Trade the month with optimized parameters
    print(f'Trading {month["name"]} with optimized parameters...')

    month_trades = backtest_coin_FIXED(
        trade_df, 'NQ',
        rsi_low=best_params[0],
        rsi_high=best_params[1],
        limit_offset_pct=best_params[2],
        stop_atr_mult=best_params[3],
        tp_atr_mult=best_params[4]
    )

    if len(month_trades) > 0:
        month_return = month_trades['pnl_pct'].sum()
        month_wins = len(month_trades[month_trades['pnl_pct'] > 0])
        month_losses = len(month_trades[month_trades['pnl_pct'] < 0])
        month_win_rate = month_wins / len(month_trades) * 100

        print(f'✅ Month result: {month_return:+.2f}% ({len(month_trades)} trades, {month_win_rate:.0f}% win rate)')

        monthly_results.append({
            'month': month['name'],
            'month_num': month_num,
            'config': best_config_name,
            'rsi_low': best_params[0],
            'rsi_high': best_params[1],
            'limit': best_params[2],
            'sl': best_params[3],
            'tp': best_params[4],
            'opt_rr': best_rr,
            'trades': len(month_trades),
            'wins': month_wins,
            'losses': month_losses,
            'win_rate': month_win_rate,
            'return': month_return,
        })

        month_trades['month'] = month['name']
        all_trades.append(month_trades)
    else:
        print(f'⚠️  Month result: No trades generated')
        monthly_results.append({
            'month': month['name'],
            'month_num': month_num,
            'config': best_config_name,
            'rsi_low': best_params[0],
            'rsi_high': best_params[1],
            'limit': best_params[2],
            'sl': best_params[3],
            'tp': best_params[4],
            'opt_rr': best_rr,
            'trades': 0,
            'wins': 0,
            'losses': 0,
            'win_rate': 0,
            'return': 0,
        })

    print()

# Calculate overall performance
print()
print('='*100)
print('📊 MONTHLY OPTIMIZATION RESULTS SUMMARY')
print('='*100)
print()

if all_trades:
    all_trades_df = pd.concat(all_trades, ignore_index=True)

    # Calculate cumulative performance
    equity = 1000.0
    peak = 1000.0
    max_dd = 0.0

    for pnl_pct in all_trades_df['pnl_pct']:
        equity += equity * (pnl_pct / 100)
        if equity > peak:
            peak = equity
        dd = ((equity - peak) / peak) * 100
        if dd < max_dd:
            max_dd = dd

    total_return = ((equity - 1000) / 1000) * 100
    rr_ratio = abs(total_return / max_dd) if max_dd != 0 else 0

    total_wins = len(all_trades_df[all_trades_df['pnl_pct'] > 0])
    total_losses = len(all_trades_df[all_trades_df['pnl_pct'] < 0])
    win_rate = total_wins / len(all_trades_df) * 100

    print('MONTHLY OPTIMIZATION (Adaptive):')
    print(f'  Total Return: {total_return:+.2f}%')
    print(f'  Max Drawdown: {max_dd:.2f}%')
    print(f'  R/R Ratio: {rr_ratio:.2f}x')
    print(f'  Total Trades: {len(all_trades_df)} ({total_wins}W / {total_losses}L)')
    print(f'  Win Rate: {win_rate:.1f}%')
    print(f'  Final Equity: ${equity:.2f}')
    print()

    print('STATIC BEST (40/60, 0.3%, 2.0x SL, 4.0x TP):')
    print(f'  Total Return: +13.31%')
    print(f'  Max Drawdown: -2.13%')
    print(f'  R/R Ratio: 6.24x')
    print(f'  Total Trades: 29')
    print(f'  Win Rate: 65.5%')
    print()

    print('='*100)
    print('💡 VERDICT')
    print('='*100)
    print()

    if rr_ratio > 6.24:
        improvement = ((rr_ratio - 6.24) / 6.24) * 100
        print(f'✅ MONTHLY OPTIMIZATION WINS! ({rr_ratio:.2f}x vs 6.24x, +{improvement:.1f}%)')
        print(f'   → Monthly recalibration is BETTER than static')
        print()
        print('🎯 RECOMMENDATION: Use monthly optimization for live trading')
        print('   → End of each month: Optimize on last 3 months')
        print('   → Trade next month with optimized parameters')
    else:
        decline = ((6.24 - rr_ratio) / 6.24) * 100
        print(f'❌ STATIC WINS! (6.24x vs {rr_ratio:.2f}x, +{decline:.1f}%)')
        print(f'   → Monthly recalibration UNDERPERFORMS static')
        print()
        print('🎯 RECOMMENDATION: Use static parameters')
        print('   RSI 40/60, Limit 0.3%, SL 2.0x, TP 4.0x')
        print('   → Simpler, no monthly maintenance, better performance')

    print()
    print('='*100)
    print('📅 MONTH-BY-MONTH BREAKDOWN')
    print('='*100)
    print()

    monthly_df = pd.DataFrame(monthly_results)

    print(f'{"Month":<20} {"Config":<25} {"Params":<25} {"Trades":<8} {"Return":<10} {"Win%"}')
    print('-'*100)

    for _, row in monthly_df.iterrows():
        params = f"{row['rsi_low']}/{row['rsi_high']}, {row['limit']:.1f}%, {row['sl']:.1f}x/{row['tp']:.1f}x"
        print(f'{row["month"]:<20} {row["config"]:<25} {params:<25} '
              f'{row["trades"]:<8} {row["return"]:>8.2f}% {row["win_rate"]:>6.1f}%')

    print()
    print('='*100)
    print('📈 PARAMETER STABILITY')
    print('='*100)
    print()

    # Check parameter changes
    param_changes = 0
    for i in range(1, len(monthly_df)):
        prev = monthly_df.iloc[i-1]
        curr = monthly_df.iloc[i]
        if (prev['rsi_low'] != curr['rsi_low'] or
            prev['rsi_high'] != curr['rsi_high'] or
            prev['limit'] != curr['limit'] or
            prev['sl'] != curr['sl'] or
            prev['tp'] != curr['tp']):
            param_changes += 1

    stability = (1 - param_changes / (len(monthly_df) - 1)) * 100 if len(monthly_df) > 1 else 0

    print(f'Parameter changes: {param_changes}/{len(monthly_df)-1} months ({param_changes/(len(monthly_df)-1)*100:.1f}%)')
    print(f'Parameter stability: {stability:.1f}%')
    print()

    if stability < 30:
        print('⚠️  HIGH INSTABILITY - Parameters change almost every month')
    elif stability < 60:
        print('📊 MODERATE STABILITY - Parameters adapt to market conditions')
    else:
        print('✅ HIGH STABILITY - Parameters stay consistent')

    # Save results
    monthly_df.to_csv('trading/results/nq_monthly_optimization.csv', index=False)
    all_trades_df.to_csv('trading/results/nq_monthly_trades.csv', index=False)

    print()
    print('💾 Saved monthly results to: trading/results/nq_monthly_optimization.csv')
    print('💾 Saved all trades to: trading/results/nq_monthly_trades.csv')

else:
    print('❌ No trades generated across any months!')
