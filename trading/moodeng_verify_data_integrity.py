#!/usr/bin/env python3
"""
MOODENG DATA INTEGRITY VERIFICATION
Runs 5 critical checks before optimization:
1. Data gaps detection
2. Duplicate timestamp detection
3. Outlier trades identification
4. Profit concentration analysis
5. Time consistency validation
"""

import pandas as pd
import numpy as np
from datetime import timedelta
import warnings
warnings.filterwarnings('ignore')

# Fee assumption: BingX Futures taker = 0.05% per side = 0.10% round trip
FEE_PER_TRADE = 0.10


def load_data():
    """Load MOODENG BingX data"""
    df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/moodeng_30d_bingx.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)
    return df


def check_data_gaps(df: pd.DataFrame) -> dict:
    """Check 1: Detect gaps in 1-minute data"""
    print("\n" + "="*80)
    print("CHECK 1: DATA GAPS DETECTION")
    print("="*80)

    gaps = []
    expected_diff = timedelta(minutes=1)

    for i in range(1, len(df)):
        actual_diff = df.iloc[i]['timestamp'] - df.iloc[i-1]['timestamp']
        if actual_diff > expected_diff:
            gaps.append({
                'index': i,
                'prev_time': df.iloc[i-1]['timestamp'],
                'curr_time': df.iloc[i]['timestamp'],
                'gap_minutes': int(actual_diff.total_seconds() / 60)
            })

    total_gap_minutes = sum(g['gap_minutes'] - 1 for g in gaps)

    print(f"Total candles: {len(df):,}")
    print(f"Date range: {df['timestamp'].iloc[0]} to {df['timestamp'].iloc[-1]}")
    print(f"Expected candles: {int((df['timestamp'].iloc[-1] - df['timestamp'].iloc[0]).total_seconds() / 60) + 1:,}")
    print(f"\nGaps found: {len(gaps)}")
    print(f"Total missing minutes: {total_gap_minutes:,}")

    if gaps:
        print(f"\nLargest gaps:")
        sorted_gaps = sorted(gaps, key=lambda x: x['gap_minutes'], reverse=True)[:10]
        for g in sorted_gaps:
            print(f"  {g['prev_time']} -> {g['curr_time']}: {g['gap_minutes']:,} minutes")

    result = {
        'pass': len(gaps) == 0,
        'gaps_count': len(gaps),
        'total_missing_minutes': total_gap_minutes,
        'largest_gap_minutes': max([g['gap_minutes'] for g in gaps]) if gaps else 0
    }

    if result['pass']:
        print("\n✅ PASS: No data gaps detected")
    else:
        if total_gap_minutes < 100:
            print(f"\n⚠️ WARNING: {total_gap_minutes} minutes missing (acceptable)")
        else:
            print(f"\n❌ FAIL: {total_gap_minutes} minutes missing (significant)")

    return result


def check_duplicates(df: pd.DataFrame) -> dict:
    """Check 2: Detect duplicate timestamps"""
    print("\n" + "="*80)
    print("CHECK 2: DUPLICATE TIMESTAMPS")
    print("="*80)

    duplicates = df[df.duplicated(subset=['timestamp'], keep=False)]

    print(f"Total candles: {len(df):,}")
    print(f"Duplicate timestamps: {len(duplicates)}")

    if len(duplicates) > 0:
        print("\nDuplicate examples:")
        print(duplicates[['timestamp', 'open', 'high', 'low', 'close', 'volume']].head(10))

    result = {
        'pass': len(duplicates) == 0,
        'duplicate_count': len(duplicates)
    }

    if result['pass']:
        print("\n✅ PASS: No duplicate timestamps")
    else:
        print(f"\n❌ FAIL: {len(duplicates)} duplicate timestamps found")

    return result


def check_outlier_trades(df: pd.DataFrame) -> dict:
    """Check 3: Detect outlier price movements that could be backtest artifacts"""
    print("\n" + "="*80)
    print("CHECK 3: OUTLIER TRADES DETECTION")
    print("="*80)

    # Calculate candle statistics
    df['body_pct'] = abs(df['close'] - df['open']) / df['open'] * 100
    df['range_pct'] = (df['high'] - df['low']) / df['low'] * 100
    df['wick_ratio'] = (df['high'] - df['low'] - abs(df['close'] - df['open'])) / abs(df['close'] - df['open'] + 0.0001)

    # Define outliers
    body_outliers = df[df['body_pct'] > 5.0]  # >5% single candle move
    range_outliers = df[df['range_pct'] > 10.0]  # >10% high-low range
    volume_outliers = df[df['volume'] > df['volume'].quantile(0.999)]  # Top 0.1% volume

    print(f"Total candles: {len(df):,}")
    print(f"\nBody >5%: {len(body_outliers)} candles")
    print(f"Range >10%: {len(range_outliers)} candles")
    print(f"Volume >99.9%: {len(volume_outliers)} candles")

    # Show worst offenders
    if len(body_outliers) > 0:
        print(f"\nLargest body moves:")
        worst = df.nlargest(5, 'body_pct')[['timestamp', 'open', 'close', 'body_pct', 'volume']]
        print(worst.to_string())

    # Check if outliers are clustered (sign of data issue)
    outlier_timestamps = pd.concat([body_outliers, range_outliers])['timestamp'].unique()

    result = {
        'pass': len(body_outliers) < 10,  # <10 extreme moves is acceptable
        'body_outliers': len(body_outliers),
        'range_outliers': len(range_outliers),
        'volume_outliers': len(volume_outliers),
        'max_body_pct': df['body_pct'].max(),
        'max_range_pct': df['range_pct'].max()
    }

    if result['pass']:
        print(f"\n✅ PASS: Outliers within acceptable range (<10 extreme moves)")
    else:
        print(f"\n⚠️ WARNING: {len(body_outliers)} extreme moves detected (review manually)")

    return result


def check_profit_concentration(df: pd.DataFrame) -> dict:
    """Check 4: Run baseline strategy and check profit concentration"""
    print("\n" + "="*80)
    print("CHECK 4: PROFIT CONCENTRATION ANALYSIS")
    print("="*80)

    # Calculate indicators
    df['body'] = df['close'] - df['open']
    df['is_bullish'] = df['close'] > df['open']
    df['body_pct'] = abs(df['body']) / df['open'] * 100

    # ATR
    df['tr'] = np.maximum(
        df['high'] - df['low'],
        np.maximum(
            abs(df['high'] - df['close'].shift(1)),
            abs(df['low'] - df['close'].shift(1))
        )
    )
    df['atr'] = df['tr'].rolling(14).mean()

    # RSI
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))

    # SMA
    df['sma_20'] = df['close'].rolling(20).mean()

    # Run baseline strategy
    trades = []
    in_position = False
    entry_price = entry_idx = stop_loss = take_profit = 0

    for i in range(200, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i-1]

        if not in_position:
            # Entry: RSI crosses 55, bullish body >0.5%, price above SMA20
            rsi_cross = prev['rsi'] < 55 and row['rsi'] >= 55
            bullish_body = row['is_bullish'] and row['body_pct'] > 0.5
            above_sma = row['close'] > row['sma_20']

            if rsi_cross and bullish_body and above_sma:
                in_position = True
                entry_price = row['close']
                entry_idx = i
                entry_atr = row['atr']

                stop_loss = entry_price - (entry_atr * 1.0)  # 1.0x ATR SL
                take_profit = entry_price + (entry_atr * 4.0)  # 4.0x ATR TP
        else:
            # Check exits
            bars_held = i - entry_idx

            # SL
            if row['low'] <= stop_loss:
                pnl = (stop_loss - entry_price) / entry_price * 100
                trades.append({'entry_idx': entry_idx, 'exit_idx': i, 'pnl_pct': pnl, 'result': 'SL'})
                in_position = False
            # TP
            elif row['high'] >= take_profit:
                pnl = (take_profit - entry_price) / entry_price * 100
                trades.append({'entry_idx': entry_idx, 'exit_idx': i, 'pnl_pct': pnl, 'result': 'TP'})
                in_position = False
            # Time exit
            elif bars_held >= 60:
                exit_price = row['close']
                pnl = (exit_price - entry_price) / entry_price * 100
                trades.append({'entry_idx': entry_idx, 'exit_idx': i, 'pnl_pct': pnl, 'result': 'TIME'})
                in_position = False

    if not trades:
        print("❌ FAIL: No trades generated by baseline strategy")
        return {'pass': False, 'trades': 0}

    # Analyze concentration
    df_trades = pd.DataFrame(trades)
    df_trades = df_trades.sort_values('pnl_pct', ascending=False).reset_index(drop=True)

    total_pnl = df_trades['pnl_pct'].sum()
    top_20_pct_count = max(1, int(len(df_trades) * 0.2))
    top_20_pct_pnl = df_trades.head(top_20_pct_count)['pnl_pct'].sum()
    concentration = (top_20_pct_pnl / total_pnl * 100) if total_pnl > 0 else 0

    # Best single trade contribution
    best_trade_pnl = df_trades['pnl_pct'].max()
    best_trade_contrib = (best_trade_pnl / total_pnl * 100) if total_pnl > 0 else 0

    # Consecutive losses (max streak)
    df_trades['is_loss'] = df_trades['pnl_pct'] < 0
    loss_streaks = []
    current_streak = 0
    for is_loss in df_trades['is_loss']:
        if is_loss:
            current_streak += 1
        else:
            if current_streak > 0:
                loss_streaks.append(current_streak)
            current_streak = 0
    if current_streak > 0:
        loss_streaks.append(current_streak)

    max_loss_streak = max(loss_streaks) if loss_streaks else 0

    print(f"Total trades: {len(df_trades)}")
    print(f"Total PNL: {total_pnl:.2f}%")
    print(f"Top 20% trades: {top_20_pct_count}")
    print(f"Top 20% contribution: {concentration:.1f}%")
    print(f"Best trade contribution: {best_trade_contrib:.1f}%")
    print(f"Max consecutive losses: {max_loss_streak}")

    # Winners coefficient of variation (consistency)
    winners = df_trades[df_trades['pnl_pct'] > 0]
    if len(winners) > 1:
        cv = winners['pnl_pct'].std() / winners['pnl_pct'].mean()
        print(f"Winner CV (consistency): {cv:.2f}")
    else:
        cv = 0
        print("Winner CV: N/A (insufficient winners)")

    result = {
        'pass': concentration < 60 and best_trade_contrib < 30,  # Acceptable thresholds
        'trades': len(df_trades),
        'total_pnl': total_pnl,
        'top_20_concentration': concentration,
        'best_trade_contrib': best_trade_contrib,
        'max_loss_streak': max_loss_streak,
        'winner_cv': cv
    }

    if result['pass']:
        print(f"\n✅ PASS: Profit distribution acceptable (top 20% = {concentration:.1f}%)")
    else:
        if concentration >= 60:
            print(f"\n⚠️ WARNING: High profit concentration ({concentration:.1f}%) - outlier-dependent")
        if best_trade_contrib >= 30:
            print(f"\n⚠️ WARNING: Single trade contributes {best_trade_contrib:.1f}% of profit")

    return result


def check_time_consistency(df: pd.DataFrame) -> dict:
    """Check 5: Verify timestamps are sequential and timezone-consistent"""
    print("\n" + "="*80)
    print("CHECK 5: TIME CONSISTENCY VALIDATION")
    print("="*80)

    # Check if timestamps are monotonically increasing
    is_sorted = df['timestamp'].is_monotonic_increasing

    # Check for backwards jumps
    backwards_jumps = 0
    for i in range(1, len(df)):
        if df.iloc[i]['timestamp'] < df.iloc[i-1]['timestamp']:
            backwards_jumps += 1

    # Check hour distribution (should have all 24 hours)
    df['hour'] = df['timestamp'].dt.hour
    hour_counts = df['hour'].value_counts().sort_index()
    missing_hours = set(range(24)) - set(hour_counts.index)

    print(f"Timestamps sorted: {is_sorted}")
    print(f"Backwards jumps: {backwards_jumps}")
    print(f"Unique hours present: {len(hour_counts)}/24")
    if missing_hours:
        print(f"Missing hours: {sorted(missing_hours)}")

    # Check day distribution (should have approximately uniform distribution)
    df['date'] = df['timestamp'].dt.date
    day_counts = df['date'].value_counts().sort_index()
    print(f"\nCandles per day:")
    print(f"  Min: {day_counts.min():,}")
    print(f"  Avg: {day_counts.mean():.0f}")
    print(f"  Max: {day_counts.max():,}")
    print(f"  Expected: ~1,440 (24 hours × 60 minutes)")

    result = {
        'pass': is_sorted and backwards_jumps == 0,
        'is_sorted': is_sorted,
        'backwards_jumps': backwards_jumps,
        'missing_hours': len(missing_hours),
        'min_candles_per_day': int(day_counts.min()),
        'max_candles_per_day': int(day_counts.max())
    }

    if result['pass']:
        print("\n✅ PASS: Time consistency verified")
    else:
        print(f"\n❌ FAIL: Time inconsistencies detected")

    return result


def main():
    print("="*80)
    print("MOODENG BINGX DATA INTEGRITY VERIFICATION")
    print("="*80)
    print("Running 5 critical checks before optimization...")

    df = load_data()

    results = {
        'data_gaps': check_data_gaps(df),
        'duplicates': check_duplicates(df),
        'outliers': check_outlier_trades(df),
        'concentration': check_profit_concentration(df),
        'time_consistency': check_time_consistency(df)
    }

    # Summary
    print("\n" + "="*80)
    print("VERIFICATION SUMMARY")
    print("="*80)

    all_passed = all(r['pass'] for r in results.values())

    for check_name, result in results.items():
        status = "✅ PASS" if result['pass'] else "❌ FAIL/WARNING"
        print(f"{check_name.upper():<20}: {status}")

    if all_passed:
        print("\n✅ ALL CHECKS PASSED - Data is clean and ready for optimization")
    else:
        print("\n⚠️ SOME CHECKS FAILED - Review warnings before proceeding")

    # Save detailed report
    report_lines = []
    report_lines.append("# MOODENG BINGX DATA VERIFICATION REPORT")
    report_lines.append(f"\n**Date**: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"**Data File**: trading/moodeng_30d_bingx.csv")
    report_lines.append(f"**Total Candles**: {len(df):,}")
    report_lines.append(f"**Date Range**: {df['timestamp'].iloc[0]} to {df['timestamp'].iloc[-1]}")
    report_lines.append(f"\n## Verification Results\n")

    for check_name, result in results.items():
        status = "PASS ✅" if result['pass'] else "FAIL/WARNING ⚠️"
        report_lines.append(f"### {check_name.upper().replace('_', ' ')}: {status}\n")
        for key, value in result.items():
            if key != 'pass':
                report_lines.append(f"- **{key}**: {value}")
        report_lines.append("")

    report_lines.append(f"\n## Conclusion\n")
    if all_passed:
        report_lines.append("All data integrity checks passed. The dataset is clean and ready for optimization.")
    else:
        report_lines.append("Some checks raised warnings. Review the detailed results above before proceeding with optimization.")

    report_path = '/workspaces/Carebiuro_windykacja/trading/results/MOODENG_VERIFICATION_REPORT.md'
    with open(report_path, 'w') as f:
        f.write('\n'.join(report_lines))

    print(f"\nDetailed report saved to: {report_path}")


if __name__ == "__main__":
    main()
