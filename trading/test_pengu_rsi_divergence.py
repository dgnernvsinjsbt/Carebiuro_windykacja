#!/usr/bin/env python3
"""
PENGU - RSI Divergence Strategy
Hunt for Nov 7 setup: 3 higher highs with lower RSI highs, then collapse
Nov-Dec 2025
"""
import pandas as pd
import numpy as np

print("="*90)
print("PENGU - RSI DIVERGENCE STRATEGY (Nov-Dec 2025)")
print("="*90)

# Load PENGU data
df = pd.read_csv('penguusdt_6months_bingx_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# Filter to Nov-Dec 2025
df = df[(df['timestamp'] >= '2025-11-01') & (df['timestamp'] < '2026-01-01')].reset_index(drop=True)

print(f"\n📊 Data: {df['timestamp'].min()} to {df['timestamp'].max()}")
print(f"   Candles: {len(df)}")
print(f"   Period: {(df['timestamp'].max() - df['timestamp'].min()).days} days")

# Calculate RSI
delta = df['close'].diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)
avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
rs = avg_gain / avg_loss
df['rsi'] = 100 - (100 / (1 + rs))

# Strategy parameters
rsi_arm_threshold = 80
min_divergences = 3
lookback_hours = 6
lookback_bars = lookback_hours * 4  # 6 hours = 24 bars on 15m
tp_pct = 8.0
risk_pct = 5.0

print(f"\n📋 Strategy Parameters:")
print(f"   ARM: RSI >{rsi_arm_threshold}")
print(f"   Min Divergences: {min_divergences}")
print(f"   Lookback Window: {lookback_hours} hours ({lookback_bars} bars)")
print(f"   Entry: First red candle after {min_divergences} divergences")
print(f"   Stop Loss: Highest high from divergence sequence")
print(f"   Take Profit: {tp_pct}%")
print(f"   Track: Trades that hit +2% before SL")

# Track divergences
def find_divergences(df, current_idx, lookback_bars):
    """
    Find bearish divergences: higher highs in price, lower highs in RSI
    Returns list of divergence points
    """
    start_idx = max(0, current_idx - lookback_bars)
    window = df.iloc[start_idx:current_idx+1].copy()

    if len(window) < 3:
        return []

    # Find local highs in price (peaks)
    price_highs = []
    for i in range(1, len(window) - 1):
        if window.iloc[i]['high'] > window.iloc[i-1]['high'] and window.iloc[i]['high'] > window.iloc[i+1]['high']:
            price_highs.append({
                'idx': start_idx + i,
                'price': window.iloc[i]['high'],
                'rsi': window.iloc[i]['rsi'],
                'time': window.iloc[i]['timestamp']
            })

    # Also consider the current bar if it's higher than previous
    if window.iloc[-1]['high'] > window.iloc[-2]['high']:
        price_highs.append({
            'idx': current_idx,
            'price': window.iloc[-1]['high'],
            'rsi': window.iloc[-1]['rsi'],
            'time': window.iloc[-1]['timestamp']
        })

    if len(price_highs) < 2:
        return []

    # Find divergences: higher price high but lower RSI high
    divergences = []
    for i in range(1, len(price_highs)):
        prev = price_highs[i-1]
        curr = price_highs[i]

        # Bearish divergence: price higher, RSI lower
        if curr['price'] > prev['price'] and curr['rsi'] < prev['rsi']:
            divergences.append({
                'idx': curr['idx'],
                'price_high': curr['price'],
                'rsi_high': curr['rsi'],
                'prev_price': prev['price'],
                'prev_rsi': prev['rsi'],
                'time': curr['time']
            })

    return divergences

# Backtest
equity = 100.0
trades = []
signals = []

in_position = False
entry_price = None
sl_price = None
tp_price = None
entry_idx = None

for i in range(lookback_bars + 14, len(df)):
    row = df.iloc[i]

    if pd.isna(row['rsi']):
        continue

    # Check if in position
    if in_position:
        # Check for exit
        if row['high'] >= sl_price:
            # Hit SL
            sl_dist_pct = ((sl_price - entry_price) / entry_price) * 100
            pnl_pct = -sl_dist_pct
            position_size = (equity * (risk_pct / 100)) / (sl_dist_pct / 100)
            pnl_dollar = position_size * (pnl_pct / 100)
            equity += pnl_dollar

            trades.append({
                'entry_time': df.iloc[entry_idx]['timestamp'],
                'exit_time': row['timestamp'],
                'entry_price': entry_price,
                'sl_price': sl_price,
                'tp_price': tp_price,
                'exit_price': sl_price,
                'sl_dist_pct': sl_dist_pct,
                'pnl_pct': pnl_pct,
                'pnl_dollar': pnl_dollar,
                'exit_reason': 'SL',
                'equity_after': equity,
                'reached_2pct': False  # Will check later
            })

            in_position = False

        elif row['low'] <= tp_price:
            # Hit TP
            sl_dist_pct = ((sl_price - entry_price) / entry_price) * 100
            pnl_pct = tp_pct
            position_size = (equity * (risk_pct / 100)) / (sl_dist_pct / 100)
            pnl_dollar = position_size * (pnl_pct / 100)
            equity += pnl_dollar

            trades.append({
                'entry_time': df.iloc[entry_idx]['timestamp'],
                'exit_time': row['timestamp'],
                'entry_price': entry_price,
                'sl_price': sl_price,
                'tp_price': tp_price,
                'exit_price': tp_price,
                'sl_dist_pct': sl_dist_pct,
                'pnl_pct': pnl_pct,
                'pnl_dollar': pnl_dollar,
                'exit_reason': 'TP',
                'equity_after': equity,
                'reached_2pct': True
            })

            in_position = False

    # Look for entry signals (only if not in position)
    if not in_position and row['rsi'] > rsi_arm_threshold:
        # Find divergences in lookback window
        divergences = find_divergences(df, i, lookback_bars)

        if len(divergences) >= min_divergences:
            # Check if current candle is red (close < open)
            is_red_candle = row['close'] < row['open']

            if is_red_candle:
                # ENTRY SIGNAL!
                # Find highest high from divergence sequence
                div_indices = [d['idx'] for d in divergences[-min_divergences:]]
                highest_high = df.iloc[div_indices]['high'].max()

                entry_price = row['close']
                sl_price = highest_high
                tp_price = entry_price * (1 - tp_pct / 100)  # SHORT
                sl_dist_pct = ((sl_price - entry_price) / entry_price) * 100

                # Only enter if SL makes sense (not too wide)
                if sl_dist_pct > 0 and sl_dist_pct <= 15:  # Max 15% SL
                    signals.append({
                        'time': row['timestamp'],
                        'rsi': row['rsi'],
                        'divergences': len(divergences),
                        'entry_price': entry_price,
                        'sl_price': sl_price,
                        'sl_dist_pct': sl_dist_pct,
                        'divergence_details': divergences[-min_divergences:]
                    })

                    in_position = True
                    entry_idx = i

# Check which SL trades reached 2% profit before reversing
for trade in trades:
    if trade['exit_reason'] == 'SL':
        # Find the trade in df
        entry_time = trade['entry_time']
        exit_time = trade['exit_time']
        entry_idx = df[df['timestamp'] == entry_time].index[0]
        exit_idx = df[df['timestamp'] == exit_time].index[0]

        # Check if price went 2% in our favor before hitting SL
        target_2pct = trade['entry_price'] * 0.98  # 2% down for SHORT

        for j in range(entry_idx + 1, exit_idx + 1):
            if df.iloc[j]['low'] <= target_2pct:
                trade['reached_2pct'] = True
                break

# Results
print(f"\n" + "="*90)
print("📊 RESULTS")
print("="*90)
print()

print(f"Signals Generated: {len(signals)}")
print(f"Trades Executed:   {len(trades)}")
print()

if len(trades) > 0:
    trades_df = pd.DataFrame(trades)
    total_return = ((equity - 100) / 100) * 100

    # Max DD
    equity_curve = [100.0]
    for pnl in trades_df['pnl_dollar']:
        equity_curve.append(equity_curve[-1] + pnl)

    eq_series = pd.Series(equity_curve)
    running_max = eq_series.expanding().max()
    drawdown = (eq_series - running_max) / running_max * 100
    max_dd = drawdown.min()

    return_dd = total_return / abs(max_dd) if max_dd != 0 else 0

    winners = trades_df[trades_df['pnl_dollar'] > 0]
    losers = trades_df[trades_df['pnl_dollar'] < 0]
    win_rate = (len(winners) / len(trades_df)) * 100

    tp_count = len(trades_df[trades_df['exit_reason'] == 'TP'])
    sl_count = len(trades_df[trades_df['exit_reason'] == 'SL'])

    reached_2pct = trades_df[trades_df['reached_2pct'] == True]

    print(f"📈 Performance:")
    print(f"   Total Return:     {total_return:+.1f}%")
    print(f"   Max Drawdown:     {max_dd:.2f}%")
    print(f"   Return/DD:        {return_dd:.2f}x")
    print(f"   Final Equity:     ${equity:.2f}")
    print()

    print(f"📊 Trade Statistics:")
    print(f"   Total Trades:     {len(trades_df)}")
    print(f"   Winners:          {len(winners)} ({win_rate:.1f}%)")
    print(f"   Losers:           {len(losers)} ({100-win_rate:.1f}%)")
    print(f"   TP Hits:          {tp_count}")
    print(f"   SL Hits:          {sl_count}")
    print(f"   Avg SL Distance:  {trades_df['sl_dist_pct'].mean():.2f}%")
    print()

    print(f"💡 2% Profit Analysis:")
    print(f"   Trades that reached +2% profit: {len(reached_2pct)} ({len(reached_2pct)/len(trades_df)*100:.1f}%)")
    print(f"   Of which hit SL eventually:     {len(reached_2pct[reached_2pct['exit_reason']=='SL'])}")
    print(f"   → Would have been winners with 2% TP!")
    print()

    # Show all trades
    print(f"📋 ALL TRADES:")
    print()
    print(f"{'Entry Time':>20} | {'Entry $':>10} | {'SL Dist':>8} | {'Exit':>4} | {'P&L %':>7} | {'2% Hit':>7}")
    print("-" * 80)

    for _, t in trades_df.iterrows():
        reached_2 = "✅" if t['reached_2pct'] else "❌"
        print(f"{str(t['entry_time'])[:19]:>20} | ${t['entry_price']:>9.6f} | {t['sl_dist_pct']:>7.2f}% | {t['exit_reason']:>4} | {t['pnl_pct']:>6.1f}% | {reached_2:>7}")

    # Save trades
    trades_df.to_csv('pengu_rsi_divergence_trades.csv', index=False)
    print(f"\n💾 Trades saved to: pengu_rsi_divergence_trades.csv")

    # Show signal details
    if len(signals) > 0:
        print(f"\n📡 SIGNAL DETAILS:")
        print()
        print(f"{'Signal Time':>20} | {'RSI':>6} | {'Divs':>5} | {'Entry $':>10} | {'SL $':>10} | {'SL Dist':>8}")
        print("-" * 75)

        for sig in signals[:10]:  # Show first 10
            print(f"{str(sig['time'])[:19]:>20} | {sig['rsi']:>6.2f} | {sig['divergences']:>5} | ${sig['entry_price']:>9.6f} | ${sig['sl_price']:>9.6f} | {sig['sl_dist_pct']:>7.2f}%")

        if len(signals) > 10:
            print(f"   ... and {len(signals) - 10} more signals")

else:
    print("❌ No trades generated!")

    if len(signals) > 0:
        print(f"\n📡 Found {len(signals)} signals but none resulted in trades")
        print("   (Possibly all had SL distance >15%)")

print("="*90)
