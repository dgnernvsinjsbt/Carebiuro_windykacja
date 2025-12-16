"""
OUT-OF-SAMPLE VALIDATION: Test ret_20 > 0% strategy on July-August 2025

Same exact strategy, different time period
If results are similar, strategy is robust (not overfit)
"""

import pandas as pd
import numpy as np
import ccxt
from datetime import datetime, timezone, timedelta
import time

print("=" * 80)
print("OUT-OF-SAMPLE VALIDATION: JULY-AUGUST 2025")
print("Testing ret_20 > 0% strategy on unseen data")
print("=" * 80)

# Download July-August data
exchange = ccxt.bingx({'enableRateLimit': True})

# July 1 - Aug 31, 2025
start_date = datetime(2025, 7, 1, tzinfo=timezone.utc)
end_date = datetime(2025, 8, 31, 23, 59, 59, tzinfo=timezone.utc)

start_ts = int(start_date.timestamp() * 1000)
end_ts = int(end_date.timestamp() * 1000)

print(f"\nDownloading MELANIA 15m data...")
print(f"Period: July 1 - Aug 31, 2025 ({(end_date - start_date).days} days)")

all_candles = []
current_ts = start_ts

while current_ts < end_ts:
    try:
        candles = exchange.fetch_ohlcv('MELANIA-USDT', timeframe='15m', since=current_ts, limit=1000)
        if not candles:
            break
        all_candles.extend(candles)
        current_ts = candles[-1][0] + (15 * 60 * 1000)
        time.sleep(0.5)
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(2)
        continue

df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True).dt.tz_localize(None)
df = df[(df['timestamp'] >= start_date.replace(tzinfo=None)) & (df['timestamp'] <= end_date.replace(tzinfo=None))]
df = df.sort_values('timestamp').reset_index(drop=True)

print(f"Downloaded {len(df)} bars")

# Calculate indicators (EXACT same as training period)
delta = df['close'].diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)
avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
rs = avg_gain / avg_loss
df['rsi'] = 100 - (100 / (1 + rs))

df['tr'] = np.maximum(df['high'] - df['low'], np.maximum(
    abs(df['high'] - df['close'].shift(1)),
    abs(df['low'] - df['close'].shift(1))
))
df['atr'] = df['tr'].rolling(14).mean()
df['ret_20'] = (df['close'] / df['close'].shift(20) - 1) * 100

print("Indicators calculated")

# Backtest with EXACT same parameters
print("\n" + "=" * 80)
print("BACKTESTING: RSI 35/65 + ret_20 > 0%")
print("Parameters: SL=2.0x ATR, TP=3.0x ATR, Risk=12%")
print("=" * 80)

trades = []
equity = 100.0
position = None

i = 300
while i < len(df):
    row = df.iloc[i]

    if pd.isna(row['rsi']) or pd.isna(row['atr']) or pd.isna(row['ret_20']):
        i += 1
        continue

    # Manage position
    if position is not None:
        bar = row

        if position['direction'] == 'LONG':
            if bar['low'] <= position['sl_price']:
                pnl = position['size'] * ((position['sl_price'] - position['entry']) / position['entry'])
                pnl -= position['size'] * 0.001
                equity += pnl
                trades.append({
                    'entry_time': df.iloc[position['entry_idx']]['timestamp'],
                    'exit_time': bar['timestamp'],
                    'direction': 'LONG',
                    'pnl_pct': ((position['sl_price'] - position['entry']) / position['entry']) * 100,
                    'pnl_dollars': pnl,
                    'equity': equity,
                    'exit_type': 'SL',
                    'bars_held': i - position['entry_idx']
                })
                position = None
                i += 1
                continue

            if bar['high'] >= position['tp_price']:
                pnl = position['size'] * ((position['tp_price'] - position['entry']) / position['entry'])
                pnl -= position['size'] * 0.001
                equity += pnl
                trades.append({
                    'entry_time': df.iloc[position['entry_idx']]['timestamp'],
                    'exit_time': bar['timestamp'],
                    'direction': 'LONG',
                    'pnl_pct': ((position['tp_price'] - position['entry']) / position['entry']) * 100,
                    'pnl_dollars': pnl,
                    'equity': equity,
                    'exit_type': 'TP',
                    'bars_held': i - position['entry_idx']
                })
                position = None
                i += 1
                continue

        elif position['direction'] == 'SHORT':
            if bar['high'] >= position['sl_price']:
                pnl = position['size'] * ((position['entry'] - position['sl_price']) / position['entry'])
                pnl -= position['size'] * 0.001
                equity += pnl
                trades.append({
                    'entry_time': df.iloc[position['entry_idx']]['timestamp'],
                    'exit_time': bar['timestamp'],
                    'direction': 'SHORT',
                    'pnl_pct': ((position['entry'] - position['sl_price']) / position['entry']) * 100,
                    'pnl_dollars': pnl,
                    'equity': equity,
                    'exit_type': 'SL',
                    'bars_held': i - position['entry_idx']
                })
                position = None
                i += 1
                continue

            if bar['low'] <= position['tp_price']:
                pnl = position['size'] * ((position['entry'] - position['tp_price']) / position['entry'])
                pnl -= position['size'] * 0.001
                equity += pnl
                trades.append({
                    'entry_time': df.iloc[position['entry_idx']]['timestamp'],
                    'exit_time': bar['timestamp'],
                    'direction': 'SHORT',
                    'pnl_pct': ((position['entry'] - position['tp_price']) / position['entry']) * 100,
                    'pnl_dollars': pnl,
                    'equity': equity,
                    'exit_type': 'TP',
                    'bars_held': i - position['entry_idx']
                })
                position = None
                i += 1
                continue

    # New entries - EXACT same logic
    if position is None and i > 0:
        prev_row = df.iloc[i-1]

        # Filter: ret_20 > 0%
        if row['ret_20'] <= 0:
            i += 1
            continue

        if not pd.isna(prev_row['rsi']):
            # LONG signal
            if prev_row['rsi'] < 35 and row['rsi'] >= 35:
                entry_price = row['close']
                sl_price = entry_price - (row['atr'] * 2.0)
                tp_price = entry_price + (row['atr'] * 3.0)

                sl_distance_pct = abs((entry_price - sl_price) / entry_price) * 100
                risk_dollars = equity * 0.12
                size = risk_dollars / (sl_distance_pct / 100)

                position = {
                    'direction': 'LONG',
                    'entry': entry_price,
                    'sl_price': sl_price,
                    'tp_price': tp_price,
                    'size': size,
                    'entry_idx': i
                }

            # SHORT signal
            elif prev_row['rsi'] > 65 and row['rsi'] <= 65:
                entry_price = row['close']
                sl_price = entry_price + (row['atr'] * 2.0)
                tp_price = entry_price - (row['atr'] * 3.0)

                sl_distance_pct = abs((sl_price - entry_price) / entry_price) * 100
                risk_dollars = equity * 0.12
                size = risk_dollars / (sl_distance_pct / 100)

                position = {
                    'direction': 'SHORT',
                    'entry': entry_price,
                    'sl_price': sl_price,
                    'tp_price': tp_price,
                    'size': size,
                    'entry_idx': i
                }

    i += 1

if len(trades) == 0:
    print("\n❌ NO TRADES on July-August data!")
    print("Strategy may be overfit to Sep-Dec conditions")
    exit()

trades_df = pd.DataFrame(trades)

# Calculate metrics
total_return = ((equity - 100) / 100) * 100
equity_curve = [100.0] + trades_df['equity'].tolist()
eq = pd.Series(equity_curve)
running_max = eq.expanding().max()
drawdowns = ((eq - running_max) / running_max * 100)
max_dd = drawdowns.min()

winners = trades_df[trades_df['pnl_pct'] > 0]
losers = trades_df[trades_df['pnl_pct'] < 0]

print("\n" + "=" * 80)
print("JULY-AUGUST 2025 RESULTS:")
print("=" * 80)

print(f"\n📊 PERFORMANCE:")
print(f"  Starting Capital: $100.00")
print(f"  Final Equity:     ${equity:,.2f}")
print(f"  Total Return:     {total_return:+,.2f}%")
print(f"  Max Drawdown:     {max_dd:.2f}%")
print(f"  Return/DD Ratio:  {total_return/abs(max_dd):.2f}x")

print(f"\n📈 TRADES:")
print(f"  Total Trades:     {len(trades_df)}")
print(f"  Winners:          {len(winners)} ({len(winners)/len(trades_df)*100:.1f}%)")
print(f"  Losers:           {len(losers)} ({len(losers)/len(trades_df)*100:.1f}%)")
print(f"  TP Rate:          {(trades_df['exit_type'] == 'TP').sum()/len(trades_df)*100:.1f}%")

print(f"\n💰 PROFIT STATS:")
print(f"  Avg Trade:        {trades_df['pnl_pct'].mean():+.2f}%")
if len(winners) > 0:
    print(f"  Avg Winner:       {winners['pnl_pct'].mean():+.2f}%")
if len(losers) > 0:
    print(f"  Avg Loser:        {losers['pnl_pct'].mean():+.2f}%")

print(f"\n📊 DIRECTION:")
longs = trades_df[trades_df['direction'] == 'LONG']
shorts = trades_df[trades_df['direction'] == 'SHORT']
if len(longs) > 0:
    print(f"  LONG:  {len(longs)} trades ({(longs['pnl_pct'] > 0).sum()}/{len(longs)} wins = {(longs['pnl_pct'] > 0).sum()/len(longs)*100:.1f}%)")
if len(shorts) > 0:
    print(f"  SHORT: {len(shorts)} trades ({(shorts['pnl_pct'] > 0).sum()}/{len(shorts)} wins = {(shorts['pnl_pct'] > 0).sum()/len(shorts)*100:.1f}%)")

# Compare to Sep-Dec results
print("\n" + "=" * 80)
print("COMPARISON: July-Aug vs Sep-Dec")
print("=" * 80)

sep_dec_results = {
    'period': 'Sep-Dec (training)',
    'trades': 53,
    'win_rate': 64.2,
    'return': 1685.9,
    'max_dd': -41.32,
    'return_dd': 40.80,
    'tp_rate': 64.2
}

jul_aug_results = {
    'period': 'Jul-Aug (validation)',
    'trades': len(trades_df),
    'win_rate': len(winners)/len(trades_df)*100,
    'return': total_return,
    'max_dd': max_dd,
    'return_dd': total_return/abs(max_dd) if max_dd != 0 else 0,
    'tp_rate': (trades_df['exit_type'] == 'TP').sum()/len(trades_df)*100
}

print(f"\n| Metric | Jul-Aug (test) | Sep-Dec (train) | Difference |")
print("|--------|----------------|-----------------|------------|")
print(f"| Trades | {jul_aug_results['trades']:3.0f} | {sep_dec_results['trades']:3.0f} | {jul_aug_results['trades'] - sep_dec_results['trades']:+3.0f} |")
print(f"| Win Rate | {jul_aug_results['win_rate']:4.1f}% | {sep_dec_results['win_rate']:4.1f}% | {jul_aug_results['win_rate'] - sep_dec_results['win_rate']:+4.1f}% |")
print(f"| Return | {jul_aug_results['return']:+6.0f}% | {sep_dec_results['return']:+6.0f}% | {jul_aug_results['return'] - sep_dec_results['return']:+6.0f}% |")
print(f"| Max DD | {jul_aug_results['max_dd']:5.1f}% | {sep_dec_results['max_dd']:5.1f}% | {jul_aug_results['max_dd'] - sep_dec_results['max_dd']:+5.1f}% |")
print(f"| R/DD | {jul_aug_results['return_dd']:5.2f}x | {sep_dec_results['return_dd']:5.2f}x | {jul_aug_results['return_dd'] - sep_dec_results['return_dd']:+5.2f}x |")
print(f"| TP Rate | {jul_aug_results['tp_rate']:4.1f}% | {sep_dec_results['tp_rate']:4.1f}% | {jul_aug_results['tp_rate'] - sep_dec_results['tp_rate']:+4.1f}% |")

print("\n" + "=" * 80)
print("VALIDATION ASSESSMENT:")
print("=" * 80)

# Assessment criteria
trade_count_ok = jul_aug_results['trades'] >= 20  # At least 20 trades in 2 months
win_rate_ok = jul_aug_results['win_rate'] >= 50  # At least 50% win rate
return_dd_ok = jul_aug_results['return_dd'] >= 3  # At least 3x R/DD
performance_similar = abs(jul_aug_results['win_rate'] - sep_dec_results['win_rate']) < 20  # Within 20% win rate

print(f"\n✓ Trade count: {jul_aug_results['trades']} trades ({'✅ PASS' if trade_count_ok else '❌ FAIL - need 20+'})")
print(f"✓ Win rate: {jul_aug_results['win_rate']:.1f}% ({'✅ PASS' if win_rate_ok else '❌ FAIL - need 50%+'})")
print(f"✓ R/DD: {jul_aug_results['return_dd']:.2f}x ({'✅ PASS' if return_dd_ok else '❌ FAIL - need 3x+'})")
print(f"✓ Performance consistency: {abs(jul_aug_results['win_rate'] - sep_dec_results['win_rate']):.1f}% difference ({'✅ PASS' if performance_similar else '❌ FAIL - >20% difference'})")

if trade_count_ok and win_rate_ok and return_dd_ok and performance_similar:
    print(f"\n✅ VALIDATION PASSED!")
    print(f"   Strategy performs consistently on out-of-sample data")
    print(f"   NOT overfit to Sep-Dec period")
else:
    print(f"\n⚠️  VALIDATION CONCERNS:")
    if not trade_count_ok:
        print(f"   - Too few trades on Jul-Aug data")
    if not win_rate_ok:
        print(f"   - Win rate too low on Jul-Aug data")
    if not return_dd_ok:
        print(f"   - R/DD too low on Jul-Aug data")
    if not performance_similar:
        print(f"   - Performance too different between periods")
    print(f"\n   Strategy may be overfit to Sep-Dec conditions")

trades_df.to_csv('melania_jul_aug_validation_trades.csv', index=False)
print(f"\n💾 Saved Jul-Aug trades to: melania_jul_aug_validation_trades.csv")

print("\n" + "=" * 80)
