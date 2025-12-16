"""
NQ Futures Walk-Forward with Multiple Lookback Windows
Test 30-day, 60-day, and 90-day optimization windows
Find optimal lookback period for live trading
"""
import pandas as pd
import numpy as np
import sys
from datetime import timedelta
sys.path.insert(0, '/workspaces/Carebiuro_windykacja')
from portfolio_simulation_FIXED import backtest_coin_FIXED

# Load 6-month NQ futures data
df = pd.read_csv('trading/nq_futures_1h_180d.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print('='*100)
print('🔄 NQ FUTURES WALK-FORWARD - MULTI-LOOKBACK COMPARISON')
print('='*100)
print()
print('Testing 3 different optimization lookback windows:')
print('  📅 30 days (1 month)')
print('  📅 60 days (2 months)')
print('  📅 90 days (3 months)')
print()
print(f'Total data: {len(df)} candles, {df["timestamp"].min().date()} to {df["timestamp"].max().date()}')
print()

# Parameter grid for optimization
rsi_configs = [(25, 70), (30, 70), (30, 65), (35, 65), (40, 60)]
limit_offsets = [0.1, 0.2, 0.3, 0.4, 0.5]
sl_mults = [0.5, 1.0, 1.5, 2.0]
tp_mults = [1.0, 1.5, 2.0, 3.0, 4.0]

def run_walk_forward(lookback_days, lookback_name):
    """Run walk-forward optimization with specified lookback period"""

    print('='*100)
    print(f'📊 TESTING {lookback_name.upper()} LOOKBACK')
    print('='*100)
    print()

    # Start trading after we have enough lookback data
    # Use last 90 days for trading (consistent across all lookbacks)
    trading_start = df['timestamp'].max() - timedelta(days=90)

    weekly_results = []
    all_trades = []

    current_date = trading_start
    week_num = 0

    while current_date < df['timestamp'].max():
        week_num += 1

        # Define optimization window (lookback_days before current_date)
        opt_start = current_date - timedelta(days=lookback_days)
        opt_end = current_date

        # Define trading window (next 7 days)
        trade_start = current_date
        trade_end = current_date + timedelta(days=7)

        # Get optimization data
        opt_df = df[(df['timestamp'] >= opt_start) & (df['timestamp'] < opt_end)].copy()

        # Get trading data
        trade_df = df[(df['timestamp'] >= trade_start) & (df['timestamp'] < trade_end)].copy()

        if len(opt_df) < 100 or len(trade_df) == 0:
            current_date += timedelta(days=7)
            continue

        # Run optimization
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

                            if len(trades) < 3:
                                continue

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
                                }
                        except:
                            continue

        if best_params is None:
            current_date += timedelta(days=7)
            continue

        # Trade next week with optimized parameters
        week_trades = backtest_coin_FIXED(
            trade_df, 'NQ',
            rsi_low=best_params['rsi_low'],
            rsi_high=best_params['rsi_high'],
            limit_offset_pct=best_params['limit'],
            stop_atr_mult=best_params['sl'],
            tp_atr_mult=best_params['tp']
        )

        # Record results
        if len(week_trades) > 0:
            week_return = week_trades['pnl_pct'].sum()
            week_wins = len(week_trades[week_trades['pnl_pct'] > 0])
            week_losses = len(week_trades[week_trades['pnl_pct'] < 0])

            weekly_results.append({
                'week': week_num,
                'start_date': trade_start,
                'return': week_return,
                'trades': len(week_trades),
                'wins': week_wins,
                'losses': week_losses,
                **best_params
            })

            week_trades['week'] = week_num
            all_trades.append(week_trades)
        else:
            weekly_results.append({
                'week': week_num,
                'start_date': trade_start,
                'return': 0,
                'trades': 0,
                'wins': 0,
                'losses': 0,
                **best_params
            })

        current_date += timedelta(days=7)

    # Calculate overall performance
    if len(all_trades) > 0:
        all_trades_df = pd.concat(all_trades, ignore_index=True)

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

        # Calculate parameter stability
        weekly_df = pd.DataFrame(weekly_results)
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

        print(f'{lookback_name} Results:')
        print(f'  Total Return: {total_return:+.2f}%')
        print(f'  Max Drawdown: {max_dd:.2f}%')
        print(f'  R/R Ratio: {rr_ratio:.2f}x')
        print(f'  Trades: {len(all_trades_df)} ({total_wins}W / {total_losses}L)')
        print(f'  Win Rate: {win_rate:.1f}%')
        print(f'  Final Equity: ${equity:.2f}')
        print(f'  Parameter Stability: {stability:.1f}% ({param_changes}/{len(weekly_df)-1} changes)')
        print()

        return {
            'lookback': lookback_name,
            'lookback_days': lookback_days,
            'return': total_return,
            'max_dd': max_dd,
            'rr_ratio': rr_ratio,
            'trades': len(all_trades_df),
            'wins': total_wins,
            'losses': total_losses,
            'win_rate': win_rate,
            'final_equity': equity,
            'stability': stability,
            'param_changes': param_changes,
            'weeks': len(weekly_df)
        }
    else:
        print(f'{lookback_name} Results: No trades generated')
        print()
        return None

# Test all three lookback periods
results = []

print('Starting walk-forward analysis with multiple lookback windows...')
print('This will take a few minutes...')
print()

for lookback_days, lookback_name in [(30, '30-day'), (60, '60-day'), (90, '90-day')]:
    result = run_walk_forward(lookback_days, lookback_name)
    if result:
        results.append(result)

# Compare all results
print()
print('='*100)
print('🏆 FINAL COMPARISON - WALK-FORWARD LOOKBACK WINDOWS')
print('='*100)
print()

if results:
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('rr_ratio', ascending=False)

    print(f'{"Lookback":<12} {"R/R":<10} {"Return":<12} {"Max DD":<12} {"Trades":<10} {"Win%":<10} {"Stability"}')
    print('-'*100)

    for _, row in results_df.iterrows():
        print(f'{row["lookback"]:<12} {row["rr_ratio"]:<10.2f}x {row["return"]:>+8.2f}% {" "*3} '
              f'{row["max_dd"]:>6.2f}% {" "*5} {row["trades"]:<10} '
              f'{row["win_rate"]:>6.1f}% {" "*3} {row["stability"]:>6.1f}%')

    print()
    print('STATIC BEST (40/60, 0.3%, 2.0x SL, 4.0x TP):')
    print(f'{"Static":<12} {"6.24x":<10} {"+13.31%":<12} {"-2.13%":<12} {"29":<10} {"65.5%":<10} {"100.0%"}')
    print()

    print('='*100)
    print('💡 VERDICT')
    print('='*100)
    print()

    best = results_df.iloc[0]

    if best['rr_ratio'] > 6.24:
        improvement = ((best['rr_ratio'] - 6.24) / 6.24) * 100
        print(f'✅ WALK-FORWARD WINS with {best["lookback"]} lookback!')
        print(f'   R/R: {best["rr_ratio"]:.2f}x vs 6.24x static (+{improvement:.1f}%)')
        print(f'   Return: {best["return"]:+.2f}%')
        print(f'   Parameter Stability: {best["stability"]:.1f}%')
        print()
        print(f'🎯 RECOMMENDATION: Use {best["lookback"]} walk-forward for live trading')
        print(f'   → Every Sunday: Optimize on last {best["lookback_days"]} days')
        print(f'   → Trade next week with optimized parameters')
    else:
        decline = ((6.24 - best['rr_ratio']) / 6.24) * 100
        print(f'❌ STATIC STILL WINS!')
        print(f'   Static: 6.24x R/R vs Best Walk-Forward ({best["lookback"]}): {best["rr_ratio"]:.2f}x')
        print(f'   Gap: {decline:.1f}%')
        print()
        print(f'📊 Best walk-forward was {best["lookback"]} with:')
        print(f'   R/R: {best["rr_ratio"]:.2f}x')
        print(f'   Return: {best["return"]:+.2f}%')
        print(f'   Stability: {best["stability"]:.1f}%')
        print()
        print('🎯 RECOMMENDATION: Use static parameters for live trading')
        print('   RSI 40/60, Limit 0.3%, SL 2.0x, TP 4.0x')
        print('   → Simpler, no weekly maintenance, better performance')

    print()
    print('='*100)
    print('📈 KEY INSIGHTS')
    print('='*100)
    print()

    print('Lookback Window Analysis:')
    for _, row in results_df.iterrows():
        print(f'  {row["lookback"]}:')
        if row['stability'] < 30:
            stability_label = 'HIGH INSTABILITY'
        elif row['stability'] < 60:
            stability_label = 'MODERATE STABILITY'
        else:
            stability_label = 'HIGH STABILITY'

        print(f'    - {stability_label} ({row["param_changes"]}/{row["weeks"]-1} param changes)')
        print(f'    - {row["rr_ratio"]:.2f}x R/R, {row["return"]:+.2f}% return')
        print(f'    - {row["trades"]} trades, {row["win_rate"]:.1f}% win rate')

    print()
    print('General Findings:')
    print('  • Longer lookback = more stable parameters')
    print('  • Shorter lookback = adapts faster to recent conditions')
    print('  • Trade-off: Stability vs Adaptability')

    # Save results
    results_df.to_csv('trading/results/nq_walk_forward_comparison.csv', index=False)
    print()
    print('💾 Saved comparison to: trading/results/nq_walk_forward_comparison.csv')

else:
    print('❌ No valid walk-forward results generated!')
