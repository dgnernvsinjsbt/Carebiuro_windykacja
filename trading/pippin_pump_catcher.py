#!/usr/bin/env python3
"""
PIPPIN Pump/Dump Catcher - Explosive Move Strategy

CONCEPT: Don't fade the moves, RIDE them!
- Entry on large directional candles (pumps/dumps)
- MASSIVE take profits (3-8%) to catch explosive moves
- Tight stops (0.5-1%) to cut losers fast
- Target: Catch 3-5 of the 26.6 daily extreme moves (>2%)

Why this might work on PIPPIN:
1. +76.8% move in 7 days = explosive potential
2. 26.6 extreme moves/day = plenty of opportunities
3. 160% price range = big moves DO happen
4. Mean reversion failed because moves too small → so catch big ones instead
"""

import pandas as pd
import numpy as np
from datetime import datetime

# Load PIPPIN data
df = pd.read_csv('pippin_7d_bingx.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print("=" * 80)
print("PIPPIN PUMP/DUMP CATCHER - EXPLOSIVE MOVE STRATEGY")
print("=" * 80)
print(f"Data: {len(df):,} candles from {df['timestamp'].min()} to {df['timestamp'].max()}")
print(f"Duration: {(df['timestamp'].max() - df['timestamp'].min()).days} days")
print()

# Calculate indicators
df['body_pct'] = ((df['close'] - df['open']) / df['open'] * 100).abs()
df['direction'] = np.where(df['close'] > df['open'], 'UP', 'DOWN')
df['volume_ma_20'] = df['volume'].rolling(window=20).mean()
df['volume_ratio'] = df['volume'] / df['volume_ma_20']

# ATR
df['tr'] = df[['high', 'low', 'close']].apply(
    lambda row: max(row['high'] - row['low'],
                    abs(row['high'] - row['close']),
                    abs(row['low'] - row['close'])), axis=1
)
df['atr_14'] = df['tr'].rolling(window=14).mean()
df['atr_avg_20'] = df['atr_14'].rolling(window=20).mean()

df = df.dropna().reset_index(drop=True)

# Add hour for session filtering
df['hour'] = df['timestamp'].dt.hour

def backtest_pump_catcher(df, config, config_name):
    """Backtest a pump/dump catching configuration"""

    entry_threshold = config['entry_threshold']  # Min body % to enter
    direction_filter = config['direction_filter']  # 'both', 'long', 'short'
    vol_filter = config['vol_filter']  # Min volume ratio, None = no filter
    atr_filter = config['atr_filter']  # Min ATR ratio, None = no filter
    sl_pct = config['sl_pct']
    tp_pct = config['tp_pct']
    max_hold = config['max_hold']
    consecutive_filter = config.get('consecutive_filter', None)  # Require N consecutive candles
    pullback_entry = config.get('pullback_entry', False)  # Wait for pullback

    df_test = df.copy()
    equity = 10000
    trades = []
    in_trade = False

    for i in range(1, len(df_test) - max_hold):
        row = df_test.iloc[i]

        # Skip if in trade
        if in_trade:
            continue

        # Check for large directional candle
        large_candle = row['body_pct'] >= entry_threshold

        if not large_candle:
            continue

        # Volume filter
        if vol_filter is not None and row['volume_ratio'] < vol_filter:
            continue

        # ATR filter (expansion)
        if atr_filter is not None and row['atr_14'] < atr_filter * row['atr_avg_20']:
            continue

        # Consecutive filter (momentum)
        if consecutive_filter is not None:
            # Check if previous N-1 candles also moved in same direction
            prev_candles = df_test.iloc[i-consecutive_filter+1:i+1]
            if row['direction'] == 'UP':
                if not all(prev_candles['close'] > prev_candles['open']):
                    continue
            else:
                if not all(prev_candles['close'] < prev_candles['open']):
                    continue

        # Direction filter
        if direction_filter == 'long' and row['direction'] != 'UP':
            continue
        elif direction_filter == 'short' and row['direction'] != 'DOWN':
            continue

        # Determine entry
        if pullback_entry:
            # Wait for 0.3% pullback in next 3 bars
            entry_found = False
            for j in range(1, 4):
                if i + j >= len(df_test):
                    break
                future_bar = df_test.iloc[i + j]

                if row['direction'] == 'UP':
                    # Wait for pullback (price goes down 0.3%)
                    if future_bar['low'] <= row['close'] * 0.997:
                        entry_price = row['close'] * 0.997
                        entry_index = i + j
                        entry_found = True
                        break
                else:
                    # Wait for bounce (price goes up 0.3%)
                    if future_bar['high'] >= row['close'] * 1.003:
                        entry_price = row['close'] * 1.003
                        entry_index = i + j
                        entry_found = True
                        break

            if not entry_found:
                continue
        else:
            # Immediate entry at next candle open
            entry_index = i + 1
            entry_price = df_test.iloc[entry_index]['open']

        # Set stops and targets
        if row['direction'] == 'UP':
            stop_loss = entry_price * (1 - sl_pct / 100)
            take_profit = entry_price * (1 + tp_pct / 100)
            trade_direction = 'LONG'
        else:
            stop_loss = entry_price * (1 + sl_pct / 100)
            take_profit = entry_price * (1 - tp_pct / 100)
            trade_direction = 'SHORT'

        in_trade = True

        # Simulate trade
        exit_price = None
        exit_reason = None
        exit_index = None

        for j in range(1, max_hold + 1):
            if entry_index + j >= len(df_test):
                break

            bar = df_test.iloc[entry_index + j]

            if trade_direction == 'LONG':
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
            else:  # SHORT
                # Check SL
                if bar['high'] >= stop_loss:
                    exit_price = stop_loss
                    exit_reason = 'SL'
                    exit_index = entry_index + j
                    break
                # Check TP
                if bar['low'] <= take_profit:
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
        if trade_direction == 'LONG':
            pnl_pct = ((exit_price - entry_price) / entry_price) - 0.001
        else:
            pnl_pct = ((entry_price - exit_price) / entry_price) - 0.001

        equity *= (1 + pnl_pct)

        trades.append({
            'entry_time': df_test.iloc[entry_index]['timestamp'],
            'direction': trade_direction,
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

# Define 10 strategic pump/dump catching configurations
configs = [
    {
        'name': '1. BASELINE - >2% candle, 5% TP, 0.8% SL',
        'config': {
            'entry_threshold': 2.0,
            'direction_filter': 'both',
            'vol_filter': None,
            'atr_filter': None,
            'sl_pct': 0.8,
            'tp_pct': 5.0,
            'max_hold': 60,
            'consecutive_filter': None,
            'pullback_entry': False
        }
    },
    {
        'name': '2. VOLUME CONFIRMED - >2% + Vol >2x, 6% TP',
        'config': {
            'entry_threshold': 2.0,
            'direction_filter': 'both',
            'vol_filter': 2.0,
            'atr_filter': None,
            'sl_pct': 0.8,
            'tp_pct': 6.0,
            'max_hold': 60,
            'consecutive_filter': None,
            'pullback_entry': False
        }
    },
    {
        'name': '3. MOMENTUM - 3 consecutive >1%, 4% TP',
        'config': {
            'entry_threshold': 1.0,
            'direction_filter': 'both',
            'vol_filter': None,
            'atr_filter': None,
            'sl_pct': 0.6,
            'tp_pct': 4.0,
            'max_hold': 45,
            'consecutive_filter': 3,
            'pullback_entry': False
        }
    },
    {
        'name': '4. ATR EXPANSION - >2% + ATR spike, 5% TP',
        'config': {
            'entry_threshold': 2.0,
            'direction_filter': 'both',
            'vol_filter': None,
            'atr_filter': 1.5,
            'sl_pct': 0.8,
            'tp_pct': 5.0,
            'max_hold': 60,
            'consecutive_filter': None,
            'pullback_entry': False
        }
    },
    {
        'name': '5. EXTREME - >3% candle, 8% TP (rare outliers)',
        'config': {
            'entry_threshold': 3.0,
            'direction_filter': 'both',
            'vol_filter': None,
            'atr_filter': None,
            'sl_pct': 1.0,
            'tp_pct': 8.0,
            'max_hold': 90,
            'consecutive_filter': None,
            'pullback_entry': False
        }
    },
    {
        'name': '6. QUICK SCALP - >1.5% candle, 3% TP, tight',
        'config': {
            'entry_threshold': 1.5,
            'direction_filter': 'both',
            'vol_filter': None,
            'atr_filter': None,
            'sl_pct': 0.5,
            'tp_pct': 3.0,
            'max_hold': 30,
            'consecutive_filter': None,
            'pullback_entry': False
        }
    },
    {
        'name': '7. PULLBACK ENTRY - >2%, wait 0.3% pullback, 5% TP',
        'config': {
            'entry_threshold': 2.0,
            'direction_filter': 'both',
            'vol_filter': None,
            'atr_filter': None,
            'sl_pct': 0.8,
            'tp_pct': 5.0,
            'max_hold': 60,
            'consecutive_filter': None,
            'pullback_entry': True
        }
    },
    {
        'name': '8. LONG ONLY - >2%, 5% TP (trend bias)',
        'config': {
            'entry_threshold': 2.0,
            'direction_filter': 'long',
            'vol_filter': None,
            'atr_filter': None,
            'sl_pct': 0.8,
            'tp_pct': 5.0,
            'max_hold': 60,
            'consecutive_filter': None,
            'pullback_entry': False
        }
    },
    {
        'name': '9. CONSERVATIVE - >2.5%, 4% TP, 1% SL',
        'config': {
            'entry_threshold': 2.5,
            'direction_filter': 'both',
            'vol_filter': None,
            'atr_filter': None,
            'sl_pct': 1.0,
            'tp_pct': 4.0,
            'max_hold': 60,
            'consecutive_filter': None,
            'pullback_entry': False
        }
    },
    {
        'name': '10. COMBO - >2% + Vol>2x + ATR>1.5x, 7% TP',
        'config': {
            'entry_threshold': 2.0,
            'direction_filter': 'both',
            'vol_filter': 2.0,
            'atr_filter': 1.5,
            'sl_pct': 0.8,
            'tp_pct': 7.0,
            'max_hold': 75,
            'consecutive_filter': None,
            'pullback_entry': False
        }
    }
]

# Run all configurations
results = []

print("Testing 10 pump/dump catching configurations...")
print()

for i, config_set in enumerate(configs, 1):
    print(f"[{i}/10] Testing: {config_set['name']}")

    result = backtest_pump_catcher(df, config_set['config'], config_set['name'])

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

print(f"{'Rank':<6} {'Config':<50} {'R/DD':<8} {'Return':<10} {'MaxDD':<10} {'WR':<8} {'Trades':<8}")
print("-" * 115)

for i, row in results_df.iterrows():
    rank = i + 1
    emoji = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"{rank}."

    print(f"{emoji:<6} {row['config'][:48]:<50} {row['return_dd']:>6.2f}x  "
          f"{row['return']:>+8.2f}%  {row['max_dd']:>8.2f}%  "
          f"{row['win_rate']:>6.1f}%  {row['trades']:>6.0f}")

print()
print("=" * 80)
print("KEY FINDINGS")
print("=" * 80)

# Best configuration
if len(results_df) > 0:
    best = results_df.iloc[0]
    print(f"\n🏆 BEST CONFIGURATION: {best['config']}")
    print(f"   Return/DD: {best['return_dd']:.2f}x")
    print(f"   Total Return: {best['return']:+.2f}%")
    print(f"   Max Drawdown: {best['max_dd']:.2f}%")
    print(f"   Win Rate: {best['win_rate']:.1f}%")
    print(f"   Trades: {best['trades']:.0f}")
    print(f"   Avg Trade Duration: {best['avg_bars']:.1f} bars ({best['avg_bars']/60:.1f} hours)")
    print(f"   Exit Distribution: TP {best['tp_pct']:.0f}%, SL {best['sl_pct']:.0f}%, TIME {best['time_pct']:.0f}%")

    # Profitability check
    profitable_count = len(results_df[results_df['return'] > 0])
    print(f"\n📊 Profitability: {profitable_count}/{len(results_df)} configurations profitable")

    if profitable_count > 0:
        avg_return_profitable = results_df[results_df['return'] > 0]['return'].mean()
        avg_rdd_profitable = results_df[results_df['return'] > 0]['return_dd'].mean()
        print(f"   Avg Return (profitable): {avg_return_profitable:+.2f}%")
        print(f"   Avg R/DD (profitable): {avg_rdd_profitable:.2f}x")

    # TP rate analysis
    high_tp = results_df[results_df['tp_pct'] >= 30]
    print(f"\n🎯 High TP Rate (≥30%): {len(high_tp)} configurations")
    if len(high_tp) > 0:
        print(f"   Best TP%: {high_tp['tp_pct'].max():.0f}% ({high_tp.loc[high_tp['tp_pct'].idxmax(), 'config']})")

    # Save results
    output_file = 'results/pippin_pump_catcher_test.csv'
    results_df.to_csv(output_file, index=False)
    print(f"\n💾 Results saved to: {output_file}")

    # Save best configuration trades
    best_config = results[results_df.index[0]]
    trades_file = 'results/pippin_pump_best_trades.csv'
    best_config['trades_df'].to_csv(trades_file, index=False)
    print(f"💾 Best config trades saved to: {trades_file}")

    print()
    print("=" * 80)
    print("VERDICT")
    print("=" * 80)

    if profitable_count == 0:
        print("\n❌ PUMP CATCHING FAILS ON PIPPIN")
        print("   All configurations lost money")
        print("   Even large TP targets don't help")
    elif profitable_count < 3:
        print("\n⚠️ PUMP CATCHING MARGINAL ON PIPPIN")
        print(f"   Only {profitable_count}/10 configurations profitable")
        print("   Not robust enough for deployment")
    elif best['return_dd'] < 3.0:
        print("\n⚠️ PUMP CATCHING WEAK ON PIPPIN")
        print(f"   Best R/DD: {best['return_dd']:.2f}x (target: >3.0x)")
        print("   Returns too low relative to risk")
    else:
        print("\n✅ PUMP CATCHING VIABLE ON PIPPIN!")
        print(f"   {profitable_count}/10 configurations profitable")
        print(f"   Best R/DD: {best['return_dd']:.2f}x")
        print(f"   Deploy with: {best['config']}")
        print(f"\n   KEY SUCCESS FACTORS:")
        print(f"   - Large TP ({best['tp_pct']:.0f}%) captures explosive moves")
        print(f"   - TP hit rate: {best['tp_pct']:.0f}% (targets ARE reached)")
        print(f"   - Avg win: {best['avg_win']:+.2f}% >> Avg loss: {best['avg_loss']:.2f}%")
else:
    print("\n❌ NO VALID CONFIGURATIONS")
    print("   All tests failed to generate trades")

print()
print("=" * 80)
