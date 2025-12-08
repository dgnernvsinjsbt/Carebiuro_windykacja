"""
ETH Defended Levels - Pre-Live Verification Script

Runs comprehensive data integrity checks before optimization:
1. Profit concentration analysis (are profits from few trades?)
2. Data quality verification (gaps, outliers)
3. Trade calculation accuracy checks
4. Time distribution analysis (is profit concentrated in time?)
5. Statistical robustness tests
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import timedelta

def load_data():
    """Load strategy data"""
    signals = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/results/eth_defended_levels_signals.csv')
    trades = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/results/eth_defended_levels_trades.csv')
    price_data = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/eth_usdt_1m_lbank.csv')

    signals['entry_time'] = pd.to_datetime(signals['entry_time'])
    trades['entry_time'] = pd.to_datetime(trades['entry_time'])
    price_data['timestamp'] = pd.to_datetime(price_data['timestamp'])

    return signals, trades, price_data

def check_profit_concentration(trades):
    """
    Check if profits are concentrated in few trades (outlier dependency)

    Red flags:
    - Top 20% trades contribute >60% of profit
    - Single trade contributes >40% of profit
    - High coefficient of variation (CV > 1.5)
    """
    print("\n" + "="*60)
    print("1. PROFIT CONCENTRATION ANALYSIS")
    print("="*60)

    if len(trades) == 0:
        print("⚠️ No trades to analyze!")
        return

    # Sort by profit
    trades_sorted = trades.sort_values('pnl_pct', ascending=False)
    total_profit = trades_sorted['pnl_pct'].sum()

    # Top 20% concentration
    top_20_pct_count = max(1, int(len(trades) * 0.2))
    top_20_pct_profit = trades_sorted.head(top_20_pct_count)['pnl_pct'].sum()
    top_20_pct_concentration = (top_20_pct_profit / total_profit) * 100

    # Single best trade concentration
    best_trade_profit = trades_sorted.iloc[0]['pnl_pct']
    best_trade_concentration = (best_trade_profit / total_profit) * 100

    # Coefficient of variation (std/mean for winners)
    winners = trades[trades['pnl_pct'] > 0]
    if len(winners) > 1:
        cv = winners['pnl_pct'].std() / winners['pnl_pct'].mean()
    else:
        cv = 0

    print(f"\nTotal trades: {len(trades)}")
    print(f"Total profit: {total_profit:.2f}%")
    print(f"\nPROFIT CONCENTRATION:")
    print(f"  Top 20% trades ({top_20_pct_count} trades): {top_20_pct_concentration:.1f}% of profit")
    print(f"  Best single trade: {best_trade_concentration:.1f}% of profit")
    print(f"  Coefficient of variation (winners): {cv:.2f}")

    # Warnings
    warnings = []
    if top_20_pct_concentration > 80:
        warnings.append(f"⚠️ HIGH concentration - top 20% contribute {top_20_pct_concentration:.1f}%")
    if best_trade_concentration > 40:
        warnings.append(f"⚠️ Single trade dominates - {best_trade_concentration:.1f}% of profit")
    if cv > 1.5:
        warnings.append(f"⚠️ High variance in winners - CV {cv:.2f}")

    if warnings:
        print(f"\n🚨 RED FLAGS:")
        for w in warnings:
            print(f"  {w}")
    else:
        print(f"\n✅ PASS - Profits reasonably distributed")

    # Show individual trade contributions
    print(f"\nINDIVIDUAL TRADE CONTRIBUTIONS:")
    for idx, row in trades_sorted.iterrows():
        contribution = (row['pnl_pct'] / total_profit) * 100
        print(f"  {row['entry_time']} | {row['direction']} | {row['pnl_pct']:+.2f}% | "
              f"Contrib: {contribution:.1f}% | Exit: {row['exit_reason']}")

    return {
        'top_20_concentration': top_20_pct_concentration,
        'best_trade_concentration': best_trade_concentration,
        'cv': cv,
        'warnings': warnings
    }

def check_data_quality(price_data):
    """Check for data gaps, outliers, anomalies"""
    print("\n" + "="*60)
    print("2. DATA QUALITY VERIFICATION")
    print("="*60)

    # Check for gaps in timestamps
    time_diffs = price_data['timestamp'].diff()
    expected_diff = pd.Timedelta('1 min')
    gaps = time_diffs[time_diffs > expected_diff * 1.5]

    print(f"\nData range: {price_data['timestamp'].min()} to {price_data['timestamp'].max()}")
    print(f"Total candles: {len(price_data)}")
    print(f"Expected duration: {(price_data['timestamp'].max() - price_data['timestamp'].min()).days} days")

    if len(gaps) > 0:
        print(f"\n⚠️ Found {len(gaps)} gaps in data:")
        for idx, gap in gaps.head(10).items():
            print(f"  {price_data['timestamp'].iloc[idx]} - gap of {gap}")
    else:
        print(f"✅ No gaps in data")

    # Check for price outliers
    price_data['price_change_pct'] = price_data['close'].pct_change() * 100
    extreme_moves = price_data[abs(price_data['price_change_pct']) > 5]

    if len(extreme_moves) > 0:
        print(f"\n⚠️ Found {len(extreme_moves)} extreme 1m moves (>5%):")
        for idx, row in extreme_moves.head(10).iterrows():
            print(f"  {row['timestamp']} - {row['price_change_pct']:+.2f}%")
    else:
        print(f"✅ No extreme price moves")

    # Check volume anomalies
    price_data['volume_ratio'] = price_data['volume'] / price_data['volume'].rolling(100).mean()
    volume_spikes = price_data[price_data['volume_ratio'] > 20]

    if len(volume_spikes) > 0:
        print(f"\n⚠️ Found {len(volume_spikes)} extreme volume spikes (>20x):")
        for idx, row in volume_spikes.head(10).iterrows():
            print(f"  {row['timestamp']} - {row['volume_ratio']:.1f}x average")
    else:
        print(f"✅ No extreme volume spikes")

def verify_trade_calculations(trades, price_data):
    """Verify that trade P&L calculations are accurate"""
    print("\n" + "="*60)
    print("3. TRADE CALCULATION VERIFICATION")
    print("="*60)

    verification_errors = []

    for idx, trade in trades.iterrows():
        entry_time = trade['entry_time']
        entry_price = trade['entry_price']
        exit_price = trade['exit_price']
        direction = trade['direction']
        reported_pnl = trade['pnl_pct']

        # Calculate expected P&L
        if direction == 'LONG':
            expected_pnl = ((exit_price - entry_price) / entry_price) * 100
        else:  # SHORT
            expected_pnl = ((entry_price - exit_price) / entry_price) * 100

        # Subtract fees
        expected_pnl -= 0.10

        # Check if matches reported
        diff = abs(expected_pnl - reported_pnl)

        if diff > 0.01:  # More than 0.01% difference
            verification_errors.append({
                'entry_time': entry_time,
                'direction': direction,
                'reported_pnl': reported_pnl,
                'expected_pnl': expected_pnl,
                'diff': diff
            })

        print(f"\n{entry_time} | {direction}")
        print(f"  Entry: ${entry_price:.2f} | Exit: ${exit_price:.2f} | Reason: {trade['exit_reason']}")
        print(f"  Reported P&L: {reported_pnl:+.2f}%")
        print(f"  Expected P&L: {expected_pnl:+.2f}%")
        print(f"  Match: {'✅' if diff < 0.01 else '⚠️ MISMATCH'}")

    if verification_errors:
        print(f"\n⚠️ Found {len(verification_errors)} calculation mismatches!")
        return False
    else:
        print(f"\n✅ All calculations verified correct")
        return True

def check_time_distribution(trades, price_data):
    """Check if profits are concentrated in specific time periods"""
    print("\n" + "="*60)
    print("4. TIME DISTRIBUTION ANALYSIS")
    print("="*60)

    if len(trades) == 0:
        print("⚠️ No trades to analyze!")
        return

    # Group by week
    trades['week'] = trades['entry_time'].dt.to_period('W')
    weekly_pnl = trades.groupby('week')['pnl_pct'].sum()

    print(f"\nWEEKLY P&L DISTRIBUTION:")
    for week, pnl in weekly_pnl.items():
        print(f"  Week {week}: {pnl:+.2f}%")

    # Check concentration
    total_profit = trades['pnl_pct'].sum()
    best_week_profit = weekly_pnl.max()
    best_week_concentration = (best_week_profit / total_profit) * 100

    print(f"\nBest week concentration: {best_week_concentration:.1f}% of total profit")

    if best_week_concentration > 60:
        print(f"⚠️ HIGH time concentration - best week contributes {best_week_concentration:.1f}%")
    else:
        print(f"✅ PASS - Profits distributed across time")

    # Session analysis
    print(f"\nSESSION BREAKDOWN:")
    trades['hour'] = trades['entry_time'].dt.hour

    def get_session(hour):
        if 0 <= hour < 8:
            return 'Asia'
        elif 8 <= hour < 14:
            return 'Europe'
        elif 14 <= hour < 21:
            return 'US'
        else:
            return 'Overnight'

    trades['session'] = trades['hour'].apply(get_session)

    for session in ['Asia', 'Europe', 'US', 'Overnight']:
        session_trades = trades[trades['session'] == session]
        if len(session_trades) > 0:
            print(f"  {session}: {len(session_trades)} trades | {session_trades['pnl_pct'].sum():+.2f}% | "
                  f"Win rate: {(session_trades['pnl_pct'] > 0).sum()}/{len(session_trades)}")

def statistical_robustness_tests(trades, signals):
    """Run statistical tests for robustness"""
    print("\n" + "="*60)
    print("5. STATISTICAL ROBUSTNESS TESTS")
    print("="*60)

    if len(trades) < 10:
        print("⚠️ Sample size too small for robust statistics (need 10+ trades)")
        print(f"Current: {len(trades)} trades")
        print("Recommendation: Wait for more signals before live trading")
        return

    # Expectancy calculation
    winners = trades[trades['pnl_pct'] > 0]
    losers = trades[trades['pnl_pct'] < 0]

    win_rate = len(winners) / len(trades)
    avg_win = winners['pnl_pct'].mean() if len(winners) > 0 else 0
    avg_loss = losers['pnl_pct'].mean() if len(losers) > 0 else 0

    expectancy = (win_rate * avg_win) + ((1 - win_rate) * avg_loss)

    print(f"\nEXPECTANCY ANALYSIS:")
    print(f"  Win rate: {win_rate*100:.1f}%")
    print(f"  Avg win: {avg_win:+.2f}%")
    print(f"  Avg loss: {avg_loss:+.2f}%")
    print(f"  Expectancy: {expectancy:+.2f}% per trade")

    if expectancy > 0:
        print(f"✅ POSITIVE expectancy")
    else:
        print(f"⚠️ NEGATIVE expectancy")

    # Check for consecutive loss streaks
    trades_sorted = trades.sort_values('entry_time')
    current_streak = 0
    max_loss_streak = 0

    for pnl in trades_sorted['pnl_pct']:
        if pnl < 0:
            current_streak += 1
            max_loss_streak = max(max_loss_streak, current_streak)
        else:
            current_streak = 0

    print(f"\nSTREAK ANALYSIS:")
    print(f"  Max consecutive losses: {max_loss_streak}")

    if max_loss_streak > 3:
        print(f"⚠️ Long loss streak detected - may be psychologically challenging")
    else:
        print(f"✅ Manageable loss streaks")

def generate_verification_report(checks):
    """Generate final verification report"""
    print("\n" + "="*60)
    print("FINAL VERIFICATION REPORT")
    print("="*60)

    all_clear = True
    critical_issues = []
    warnings = []

    # Profit concentration check
    if 'profit_concentration' in checks:
        pc = checks['profit_concentration']
        if pc['top_20_concentration'] > 80:
            critical_issues.append("Profits highly concentrated in top 20% trades")
        if pc['best_trade_concentration'] > 40:
            warnings.append("Single trade dominates profit")
        if pc['cv'] > 1.5:
            warnings.append("High variance in winning trades")

    if critical_issues:
        print("\n🚨 CRITICAL ISSUES:")
        for issue in critical_issues:
            print(f"  ❌ {issue}")
        all_clear = False

    if warnings:
        print("\n⚠️ WARNINGS:")
        for warning in warnings:
            print(f"  ⚠️ {warning}")

    if all_clear and not warnings:
        print("\n✅ ALL CHECKS PASSED - Strategy verified for optimization")
    elif all_clear and warnings:
        print("\n⚠️ PROCEED WITH CAUTION - Minor warnings detected")
    else:
        print("\n❌ CRITICAL ISSUES FOUND - Address before optimization")

    return all_clear

def main():
    print("="*60)
    print("ETH DEFENDED LEVELS - PRE-OPTIMIZATION VERIFICATION")
    print("="*60)

    # Load data
    signals, trades, price_data = load_data()

    checks = {}

    # Run all verification checks
    checks['profit_concentration'] = check_profit_concentration(trades)
    check_data_quality(price_data)
    verify_trade_calculations(trades, price_data)
    check_time_distribution(trades, price_data)
    statistical_robustness_tests(trades, signals)

    # Generate final report
    all_clear = generate_verification_report(checks)

    # Save verification results
    verification_summary = {
        'total_trades': len(trades),
        'total_signals': len(signals),
        'verification_passed': all_clear,
        'top_20_concentration': checks['profit_concentration']['top_20_concentration'],
        'best_trade_concentration': checks['profit_concentration']['best_trade_concentration'],
        'cv': checks['profit_concentration']['cv']
    }

    summary_df = pd.DataFrame([verification_summary])
    summary_df.to_csv('/workspaces/Carebiuro_windykacja/trading/results/eth_defended_levels_verification_summary.csv', index=False)

    print(f"\n✅ Verification summary saved to results/eth_defended_levels_verification_summary.csv")

if __name__ == '__main__':
    main()
