"""
NQ Futures Walk-Forward Optimization
Weekly recalibration: Every Sunday optimize on last 30 days, trade next week
Simulates real-world adaptive trading
"""
import pandas as pd
import numpy as np
import sys
from datetime import timedelta
sys.path.insert(0, '/workspaces/Carebiuro_windykacja')
from portfolio_simulation_FIXED import backtest_coin_FIXED

# Load NQ futures data
df = pd.read_csv('trading/nq_futures_1h_90d.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print('='*100)
print('🔄 NQ FUTURES WALK-FORWARD OPTIMIZATION')
print('='*100)
print()
print('Strategy: Weekly recalibration based on last 30 days')
print('Process:')
print('  1. Every Sunday: Optimize on last 30 days of data')
print('  2. Find best RSI/limit/SL/TP parameters')
print('  3. Trade next week (Mon-Sun) with those parameters')
print('  4. Repeat for entire 90-day period')
print()
print(f'Data: {len(df)} candles, {df["timestamp"].min().date()} to {df["timestamp"].max().date()}')
print()

# Parameter grid for optimization
rsi_configs = [
    (25, 70), (30, 70), (30, 65), (35, 65), (40, 60)
]
limit_offsets = [0.1, 0.2, 0.3, 0.4, 0.5]
sl_mults = [0.5, 1.0, 1.5, 2.0]
tp_mults = [1.0, 1.5, 2.0, 3.0, 4.0]

# Track all weekly results
weekly_results = []
all_trades = []
optimization_history = []

# Start date: need 30 days of history first
start_date = df['timestamp'].min() + timedelta(days=30)
end_date = df['timestamp'].max()

current_date = start_date

week_num = 0

print('Starting walk-forward analysis...')
print()

while current_date < end_date:
    week_num += 1

    # Define optimization window (last 30 days)
    opt_start = current_date - timedelta(days=30)
    opt_end = current_date

    # Define trading window (next 7 days)
    trade_start = current_date
    trade_end = current_date + timedelta(days=7)

    # Get optimization data (30 days)
    opt_df = df[(df['timestamp'] >= opt_start) & (df['timestamp'] < opt_end)].copy()

    # Get trading data (next week)
    trade_df = df[(df['timestamp'] >= trade_start) & (df['timestamp'] < trade_end)].copy()

    if len(opt_df) < 100 or len(trade_df) == 0:
        # Not enough data, skip this week
        current_date += timedelta(days=7)
        continue

    print(f'Week {week_num}: {trade_start.date()} to {trade_end.date()}')
    print(f'  Optimization period: {opt_start.date()} to {opt_end.date()} ({len(opt_df)} candles)')

    # Run optimization on 30-day window
    best_rr = 0
    best_params = None

    for rsi_low, rsi_high in rsi_configs:
        for limit_offset in limit_offsets:
            for sl_mult in sl_mults:
                for tp_mult in tp_mults:
                    try:
                        trades = backtest_coin_FIXED(
                            opt_df, 'NQ',
                            rsi_low=rsi_low,
                            rsi_high=rsi_high,
                            limit_offset_pct=limit_offset,
                            stop_atr_mult=sl_mult,
                            tp_atr_mult=tp_mult
                        )

                        if len(trades) < 3:  # Need at least 3 trades
                            continue

                        # Calculate R/R ratio
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

                        if rr_ratio > best_rr:
                            best_rr = rr_ratio
                            best_params = {
                                'rsi_low': rsi_low,
                                'rsi_high': rsi_high,
                                'limit': limit_offset,
                                'sl': sl_mult,
                                'tp': tp_mult,
                                'opt_rr': rr_ratio,
                                'opt_trades': len(trades),
                                'opt_return': total_return
                            }
                    except:
                        continue

    if best_params is None:
        print(f'  ❌ No valid optimization found, skipping week')
        current_date += timedelta(days=7)
        continue

    print(f'  Best params: RSI {best_params["rsi_low"]}/{best_params["rsi_high"]}, '
          f'Limit {best_params["limit"]}%, SL {best_params["sl"]}x, TP {best_params["tp"]}x')
    print(f'  Optimization R/R: {best_params["opt_rr"]:.2f}x ({best_params["opt_trades"]} trades)')

    # Now trade the next week with these parameters
    week_trades = backtest_coin_FIXED(
        trade_df, 'NQ',
        rsi_low=best_params['rsi_low'],
        rsi_high=best_params['rsi_high'],
        limit_offset_pct=best_params['limit'],
        stop_atr_mult=best_params['sl'],
        tp_atr_mult=best_params['tp']
    )

    # Calculate week performance
    if len(week_trades) > 0:
        week_return = week_trades['pnl_pct'].sum()
        week_wins = len(week_trades[week_trades['pnl_pct'] > 0])
        week_losses = len(week_trades[week_trades['pnl_pct'] < 0])
        week_win_rate = week_wins / len(week_trades) * 100

        print(f'  Week result: {week_return:+.2f}% ({len(week_trades)} trades, {week_win_rate:.0f}% win rate)')

        weekly_results.append({
            'week': week_num,
            'start_date': trade_start,
            'end_date': trade_end,
            'rsi_low': best_params['rsi_low'],
            'rsi_high': best_params['rsi_high'],
            'limit': best_params['limit'],
            'sl': best_params['sl'],
            'tp': best_params['tp'],
            'trades': len(week_trades),
            'return': week_return,
            'wins': week_wins,
            'losses': week_losses,
            'win_rate': week_win_rate,
            'opt_rr': best_params['opt_rr']
        })

        # Add week number to trades
        week_trades['week'] = week_num
        all_trades.append(week_trades)
    else:
        print(f'  Week result: No trades generated')
        weekly_results.append({
            'week': week_num,
            'start_date': trade_start,
            'end_date': trade_end,
            'rsi_low': best_params['rsi_low'],
            'rsi_high': best_params['rsi_high'],
            'limit': best_params['limit'],
            'sl': best_params['sl'],
            'tp': best_params['tp'],
            'trades': 0,
            'return': 0,
            'wins': 0,
            'losses': 0,
            'win_rate': 0,
            'opt_rr': best_params['opt_rr']
        })

    print()

    # Move to next week
    current_date += timedelta(days=7)

print()
print('='*100)
print('📊 WALK-FORWARD RESULTS SUMMARY')
print('='*100)
print()

weekly_df = pd.DataFrame(weekly_results)

# Calculate overall performance
if len(all_trades) > 0:
    all_trades_df = pd.concat(all_trades, ignore_index=True)

    # Calculate cumulative equity
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

    total_trades = len(all_trades_df)
    total_wins = len(all_trades_df[all_trades_df['pnl_pct'] > 0])
    total_losses = len(all_trades_df[all_trades_df['pnl_pct'] < 0])
    overall_win_rate = total_wins / total_trades * 100

    print(f'WALK-FORWARD (Adaptive):')
    print(f'  Total Return: {total_return:+.2f}%')
    print(f'  Max Drawdown: {max_dd:.2f}%')
    print(f'  R/R Ratio: {rr_ratio:.2f}x')
    print(f'  Total Trades: {total_trades}')
    print(f'  Win Rate: {overall_win_rate:.1f}% ({total_wins}W / {total_losses}L)')
    print(f'  Final Equity: ${equity:.2f}')
    print()

    # Compare with static best params (from full optimization)
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
        print(f'✅ WALK-FORWARD WINS! ({rr_ratio:.2f}x vs 6.24x, +{improvement:.1f}%)')
        print(f'   → Adaptive parameters are BETTER than static')
        print(f'   → Use weekly recalibration for live trading')
    else:
        decline = ((6.24 - rr_ratio) / 6.24) * 100
        print(f'❌ STATIC WINS! (6.24x vs {rr_ratio:.2f}x, +{decline:.1f}%)')
        print(f'   → Adaptive parameters UNDERPERFORM static')
        print(f'   → Risk of overfitting to recent noise')
        print(f'   → Use static parameters (40/60, 0.3%, 2.0x SL, 4.0x TP)')

    print()
    print('='*100)
    print('📅 WEEK-BY-WEEK BREAKDOWN')
    print('='*100)
    print()

    print(f'{"Week":<6} {"Dates":<23} {"Params":<30} {"Trades":<8} {"Return":<10} {"Win%"}')
    print('-'*100)

    for _, row in weekly_df.iterrows():
        params = f"{row['rsi_low']}/{row['rsi_high']}, {row['limit']:.1f}%, {row['sl']:.1f}x/{row['tp']:.1f}x"
        date_range = f"{row['start_date'].strftime('%m/%d')}-{row['end_date'].strftime('%m/%d')}"

        print(f'{row["week"]:<6} {date_range:<23} {params:<30} '
              f'{row["trades"]:<8} {row["return"]:>8.2f}% {row["win_rate"]:>6.1f}%')

    print()
    print('='*100)
    print('📈 PARAMETER STABILITY')
    print('='*100)
    print()

    # Check how often parameters changed
    param_changes = 0
    for i in range(1, len(weekly_df)):
        prev = weekly_df.iloc[i-1]
        curr = weekly_df.iloc[i]

        if (prev['rsi_low'] != curr['rsi_low'] or
            prev['rsi_high'] != curr['rsi_high'] or
            prev['limit'] != curr['limit'] or
            prev['sl'] != curr['sl'] or
            prev['tp'] != curr['tp']):
            param_changes += 1

    stability = (1 - param_changes / (len(weekly_df) - 1)) * 100 if len(weekly_df) > 1 else 0

    print(f'Parameter changes: {param_changes}/{len(weekly_df)-1} weeks ({param_changes/(len(weekly_df)-1)*100:.1f}%)')
    print(f'Parameter stability: {stability:.1f}%')
    print()

    if stability < 30:
        print('⚠️  HIGH INSTABILITY - Parameters change almost every week')
        print('   → Market regime shifting rapidly OR overfitting to noise')
    elif stability < 60:
        print('📊 MODERATE STABILITY - Parameters adapt to market conditions')
        print('   → Good balance between adapting and staying consistent')
    else:
        print('✅ HIGH STABILITY - Parameters stay consistent')
        print('   → Market conditions stable, adaptive approach less critical')

    print()

    # Save results
    weekly_df.to_csv('trading/results/nq_walk_forward_weekly.csv', index=False)
    all_trades_df.to_csv('trading/results/nq_walk_forward_trades.csv', index=False)

    print('💾 Saved weekly results to: trading/results/nq_walk_forward_weekly.csv')
    print('💾 Saved all trades to: trading/results/nq_walk_forward_trades.csv')

    print()
    print('='*100)
    print('🎯 KEY INSIGHTS')
    print('='*100)
    print()
    print('Walk-forward optimization simulates REAL LIVE TRADING:')
    print('  ✅ Parameters adapt to recent market conditions')
    print('  ✅ Uses only past data (no look-ahead bias)')
    print('  ✅ Shows if strategy works out-of-sample')
    print()
    print('Risks:')
    print('  ⚠️  Overfitting to recent 30-day noise')
    print('  ⚠️  Parameters may whipsaw week-to-week')
    print('  ⚠️  Requires weekly reoptimization effort')
    print()

    if rr_ratio > 6.24:
        print('Recommendation: USE WALK-FORWARD for live trading')
        print('  → Set up weekly Sunday optimization routine')
        print('  → Run optimization on last 30 days')
        print('  → Update bot parameters for next week')
    else:
        print('Recommendation: USE STATIC PARAMS for live trading')
        print('  → RSI 40/60, Limit 0.3%, SL 2.0x, TP 4.0x')
        print('  → Simpler, no weekly maintenance')
        print('  → Better performance on historical data')

else:
    print('❌ No trades generated across any weeks!')
    print('Walk-forward optimization failed to find tradeable parameters.')
