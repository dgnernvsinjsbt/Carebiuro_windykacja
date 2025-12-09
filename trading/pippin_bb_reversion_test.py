#!/usr/bin/env python3
"""
PIPPIN Bollinger Band Mean Reversion - Strategic Feasibility Test

Pattern discovered: BB lower band touch → 60.1% mean reversion rate
Now testing 10 strategically chosen variants to validate tradability.

NOT a brute-force optimizer - these are carefully selected configurations
based on the pattern analysis findings.
"""

import pandas as pd
import numpy as np
from datetime import datetime

# Load PIPPIN data
df = pd.read_csv('pippin_7d_bingx.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print("=" * 80)
print("PIPPIN BB MEAN REVERSION - STRATEGIC FEASIBILITY TEST")
print("=" * 80)
print(f"Data: {len(df):,} candles from {df['timestamp'].min()} to {df['timestamp'].max()}")
print(f"Duration: {(df['timestamp'].max() - df['timestamp'].min()).days} days")
print()

# Add hour for session filtering
df['hour'] = df['timestamp'].dt.hour

# Calculate volume ratio
df['volume_ma_30'] = df['volume'].rolling(window=30).mean()
df['volume_ratio'] = df['volume'] / df['volume_ma_30']

def calculate_bollinger_bands(df, period, std_dev):
    """Calculate Bollinger Bands"""
    df[f'bb_ma_{period}'] = df['close'].rolling(window=period).mean()
    df[f'bb_std_{period}'] = df['close'].rolling(window=period).std()
    df[f'bb_upper_{period}_{std_dev}'] = df[f'bb_ma_{period}'] + (std_dev * df[f'bb_std_{period}'])
    df[f'bb_lower_{period}_{std_dev}'] = df[f'bb_ma_{period}'] - (std_dev * df[f'bb_std_{period}'])
    return df

def backtest_bb_reversion(df, config, config_name):
    """Backtest a BB mean reversion configuration"""

    bb_period = config['bb_period']
    bb_std = config['bb_std']
    entry_type = config['entry_type']  # 'touch', 'close_below', 'close_outside'
    sl_pct = config['sl_pct']
    tp_pct = config['tp_pct']
    max_hold = config['max_hold']
    session_filter = config['session_filter']  # None, 'us', 'europe', 'not_overnight'
    vol_filter = config['vol_filter']  # minimum volume ratio, None for no filter

    # Calculate BB
    df_test = df.copy()
    df_test = calculate_bollinger_bands(df_test, bb_period, bb_std)
    df_test = df_test.dropna().reset_index(drop=True)

    bb_lower = f'bb_lower_{bb_period}_{bb_std}'
    bb_upper = f'bb_upper_{bb_period}_{bb_std}'

    signals = []
    equity = 10000
    trades = []
    in_trade = False

    for i in range(1, len(df_test)):
        row = df_test.iloc[i]
        prev_row = df_test.iloc[i-1]

        # Skip if in trade
        if in_trade:
            continue

        # Session filter
        if session_filter == 'us' and not (14 <= row['hour'] < 21):
            continue
        elif session_filter == 'europe' and not (8 <= row['hour'] < 14):
            continue
        elif session_filter == 'not_overnight' and (21 <= row['hour'] or row['hour'] < 8):
            continue

        # Volume filter
        if vol_filter is not None and row['volume_ratio'] < vol_filter:
            continue

        # Entry conditions - LONG only (BB lower band)
        signal = False

        if entry_type == 'touch':
            # Price touches or goes below BB lower
            if row['low'] <= row[bb_lower]:
                signal = True
        elif entry_type == 'close_below':
            # Close below BB lower
            if row['close'] < row[bb_lower]:
                signal = True
        elif entry_type == 'close_outside':
            # Close outside AND previous close inside
            if row['close'] < row[bb_lower] and prev_row['close'] >= prev_row[bb_lower]:
                signal = True

        if not signal:
            continue

        # Enter trade
        entry_index = i
        entry_price = row['close']
        stop_loss = entry_price * (1 - sl_pct / 100)
        take_profit = entry_price * (1 + tp_pct / 100)
        in_trade = True

        # Simulate trade
        exit_price = None
        exit_reason = None
        exit_index = None

        for j in range(1, max_hold + 1):
            if entry_index + j >= len(df_test):
                break

            bar = df_test.iloc[entry_index + j]

            # Check SL
            if bar['low'] <= stop_loss:
                exit_price = stop_loss
                exit_reason = 'SL'
                exit_index = entry_index + j
                break

            # Check TP
            if bar['high'] >= take_profit:
                exit_price = take_profit
                exit_reason = 'TP'
                exit_index = entry_index + j
                break

        # Time exit
        if exit_price is None:
            exit_index = min(entry_index + max_hold, len(df_test) - 1)
            exit_price = df_test.iloc[exit_index]['close']
            exit_reason = 'TIME'

        # Calculate P&L with fees
        pnl_pct = ((exit_price - entry_price) / entry_price) - 0.001  # 0.1% fees
        equity *= (1 + pnl_pct)

        trades.append({
            'entry_time': row['timestamp'],
            'entry_price': entry_price,
            'exit_price': exit_price,
            'exit_reason': exit_reason,
            'pnl_pct': pnl_pct * 100,
            'bars_held': exit_index - entry_index,
            'equity': equity
        })

        in_trade = False

    if len(trades) == 0:
        return None

    # Calculate metrics
    tdf = pd.DataFrame(trades)
    total_return = (equity - 10000) / 10000 * 100

    eq = tdf['equity'].values
    running_max = np.maximum.accumulate(eq)
    drawdown = (eq - running_max) / running_max * 100
    max_dd = drawdown.min()

    return_dd_ratio = total_return / abs(max_dd) if max_dd != 0 else 0

    winners = tdf[tdf['pnl_pct'] > 0]
    win_rate = len(winners) / len(tdf) * 100

    avg_win = winners['pnl_pct'].mean() if len(winners) > 0 else 0
    losers = tdf[tdf['pnl_pct'] <= 0]
    avg_loss = losers['pnl_pct'].mean() if len(losers) > 0 else 0

    exit_counts = tdf['exit_reason'].value_counts()

    return {
        'config': config_name,
        'trades': len(tdf),
        'return': total_return,
        'max_dd': max_dd,
        'return_dd': return_dd_ratio,
        'win_rate': win_rate,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'tp_pct': exit_counts.get('TP', 0) / len(tdf) * 100,
        'sl_pct': exit_counts.get('SL', 0) / len(tdf) * 100,
        'time_pct': exit_counts.get('TIME', 0) / len(tdf) * 100,
        'avg_bars': tdf['bars_held'].mean(),
        'trades_df': tdf
    }

# Define 10 strategically chosen configurations
configs = [
    {
        'name': '1. BASELINE - Classic BB(20,2), 2:1 R:R',
        'config': {
            'bb_period': 20,
            'bb_std': 2.0,
            'entry_type': 'touch',
            'sl_pct': 0.5,
            'tp_pct': 1.0,
            'max_hold': 30,
            'session_filter': None,
            'vol_filter': None
        }
    },
    {
        'name': '2. CONSERVATIVE - BB(20,3), wider bands, 3:1 R:R',
        'config': {
            'bb_period': 20,
            'bb_std': 3.0,
            'entry_type': 'touch',
            'sl_pct': 0.5,
            'tp_pct': 1.5,
            'max_hold': 30,
            'session_filter': None,
            'vol_filter': None
        }
    },
    {
        'name': '3. AGGRESSIVE - BB(20,2), 1.5:1 R:R, quick exit',
        'config': {
            'bb_period': 20,
            'bb_std': 2.0,
            'entry_type': 'touch',
            'sl_pct': 0.6,
            'tp_pct': 0.9,
            'max_hold': 15,
            'session_filter': None,
            'vol_filter': None
        }
    },
    {
        'name': '4. US SESSION ONLY - BB(20,2), pattern finding',
        'config': {
            'bb_period': 20,
            'bb_std': 2.0,
            'entry_type': 'touch',
            'sl_pct': 0.5,
            'tp_pct': 1.0,
            'max_hold': 30,
            'session_filter': 'us',
            'vol_filter': None
        }
    },
    {
        'name': '5. VOLUME CONFIRMED - Volume > 1.2x avg',
        'config': {
            'bb_period': 20,
            'bb_std': 2.0,
            'entry_type': 'touch',
            'sl_pct': 0.5,
            'tp_pct': 1.0,
            'max_hold': 30,
            'session_filter': None,
            'vol_filter': 1.2
        }
    },
    {
        'name': '6. STRICT ENTRY - Close BELOW lower band',
        'config': {
            'bb_period': 20,
            'bb_std': 2.0,
            'entry_type': 'close_below',
            'sl_pct': 0.5,
            'tp_pct': 1.0,
            'max_hold': 30,
            'session_filter': None,
            'vol_filter': None
        }
    },
    {
        'name': '7. TIGHT STOPS - BB(20,2), 0.3% SL, 0.6% TP',
        'config': {
            'bb_period': 20,
            'bb_std': 2.0,
            'entry_type': 'touch',
            'sl_pct': 0.3,
            'tp_pct': 0.6,
            'max_hold': 20,
            'session_filter': None,
            'vol_filter': None
        }
    },
    {
        'name': '8. FAST BB - BB(10,2), quicker response',
        'config': {
            'bb_period': 10,
            'bb_std': 2.0,
            'entry_type': 'touch',
            'sl_pct': 0.5,
            'tp_pct': 1.0,
            'max_hold': 30,
            'session_filter': None,
            'vol_filter': None
        }
    },
    {
        'name': '9. SLOW BB - BB(50,2), smoother bands',
        'config': {
            'bb_period': 50,
            'bb_std': 2.0,
            'entry_type': 'touch',
            'sl_pct': 0.5,
            'tp_pct': 1.0,
            'max_hold': 30,
            'session_filter': None,
            'vol_filter': None
        }
    },
    {
        'name': '10. COMBO - US + Volume + Close below',
        'config': {
            'bb_period': 20,
            'bb_std': 2.0,
            'entry_type': 'close_below',
            'sl_pct': 0.5,
            'tp_pct': 1.0,
            'max_hold': 30,
            'session_filter': 'us',
            'vol_filter': 1.2
        }
    }
]

# Run all configurations
results = []

print("Testing 10 strategic BB mean reversion configurations...")
print()

for i, config_set in enumerate(configs, 1):
    print(f"[{i}/10] Testing: {config_set['name']}")

    result = backtest_bb_reversion(df, config_set['config'], config_set['name'])

    if result is None:
        print(f"  ❌ No trades generated\n")
        continue

    results.append(result)

    print(f"  Trades: {result['trades']}")
    print(f"  Return: {result['return']:+.2f}%")
    print(f"  Max DD: {result['max_dd']:.2f}%")
    print(f"  R/DD: {result['return_dd']:.2f}x")
    print(f"  Win Rate: {result['win_rate']:.1f}%")
    print(f"  Exits: TP {result['tp_pct']:.0f}%, SL {result['sl_pct']:.0f}%, TIME {result['time_pct']:.0f}%")
    print()

# Sort by Return/DD ratio
results_df = pd.DataFrame([{k: v for k, v in r.items() if k != 'trades_df'} for r in results])
results_df = results_df.sort_values('return_dd', ascending=False).reset_index(drop=True)

# Display results table
print("=" * 80)
print("RESULTS SUMMARY - Ranked by Return/DD Ratio")
print("=" * 80)
print()

print(f"{'Rank':<6} {'Config':<45} {'R/DD':<8} {'Return':<10} {'MaxDD':<10} {'WR':<8} {'Trades':<8}")
print("-" * 110)

for i, row in results_df.iterrows():
    rank = i + 1
    emoji = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"{rank}."

    print(f"{emoji:<6} {row['config'][:43]:<45} {row['return_dd']:>6.2f}x  "
          f"{row['return']:>+8.2f}%  {row['max_dd']:>8.2f}%  "
          f"{row['win_rate']:>6.1f}%  {row['trades']:>6.0f}")

print()
print("=" * 80)
print("KEY FINDINGS")
print("=" * 80)

# Best configuration
best = results_df.iloc[0]
print(f"\n🏆 BEST CONFIGURATION: {best['config']}")
print(f"   Return/DD: {best['return_dd']:.2f}x")
print(f"   Total Return: {best['return']:+.2f}%")
print(f"   Max Drawdown: {best['max_dd']:.2f}%")
print(f"   Win Rate: {best['win_rate']:.1f}%")
print(f"   Trades: {best['trades']:.0f}")
print(f"   Avg Trade Duration: {best['avg_bars']:.1f} bars")
print(f"   Exit Distribution: TP {best['tp_pct']:.0f}%, SL {best['sl_pct']:.0f}%, TIME {best['time_pct']:.0f}%")

# Profitability check
profitable_count = len(results_df[results_df['return'] > 0])
print(f"\n📊 Profitability: {profitable_count}/{len(results_df)} configurations profitable")

if profitable_count > 0:
    avg_return_profitable = results_df[results_df['return'] > 0]['return'].mean()
    avg_rdd_profitable = results_df[results_df['return'] > 0]['return_dd'].mean()
    print(f"   Avg Return (profitable): {avg_return_profitable:+.2f}%")
    print(f"   Avg R/DD (profitable): {avg_rdd_profitable:.2f}x")

# Win rate analysis
high_wr = results_df[results_df['win_rate'] >= 55]
print(f"\n🎯 High Win Rate (≥55%): {len(high_wr)} configurations")
if len(high_wr) > 0:
    print(f"   Best WR: {high_wr['win_rate'].max():.1f}% ({high_wr.loc[high_wr['win_rate'].idxmax(), 'config']})")

# Save detailed results
output_file = 'results/pippin_bb_reversion_test.csv'
results_df.to_csv(output_file, index=False)
print(f"\n💾 Results saved to: {output_file}")

# Save best configuration trades
if len(results) > 0:
    best_config = results[results_df.index[0]]
    trades_file = 'results/pippin_bb_best_trades.csv'
    best_config['trades_df'].to_csv(trades_file, index=False)
    print(f"💾 Best config trades saved to: {trades_file}")

print()
print("=" * 80)
print("VERDICT")
print("=" * 80)

if profitable_count == 0:
    print("\n❌ BB MEAN REVERSION FAILS ON PIPPIN")
    print("   All 10 configurations lost money")
    print("   Pattern from 7d analysis does not hold in live trading")
elif profitable_count < 3:
    print("\n⚠️ BB MEAN REVERSION MARGINAL ON PIPPIN")
    print(f"   Only {profitable_count}/10 configurations profitable")
    print("   Not robust enough for deployment")
elif best['return_dd'] < 3.0:
    print("\n⚠️ BB MEAN REVERSION WEAK ON PIPPIN")
    print(f"   Best R/DD: {best['return_dd']:.2f}x (target: >3.0x)")
    print("   Returns too low relative to risk")
else:
    print("\n✅ BB MEAN REVERSION VIABLE ON PIPPIN")
    print(f"   {profitable_count}/10 configurations profitable")
    print(f"   Best R/DD: {best['return_dd']:.2f}x")
    print(f"   Deploy with: {best['config']}")

print()
print("=" * 80)
