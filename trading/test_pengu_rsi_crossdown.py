#!/usr/bin/env python3
"""
PENGU - RSI Cross Down Strategy
Trigger: RSI crosses from >72 to <72
Entry: Limit at 30% retracement to 5-bar high
Nov-Dec 2025 test
"""
import pandas as pd
import numpy as np

print("="*90)
print("PENGU - RSI CROSS DOWN STRATEGY (Nov-Dec 2025)")
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

# Parameters
rsi_trigger = 72
lookback = 5
retracement_pct = 30.0  # 30% of the way to highest high
tp_pct = 5.0  # Flat 5% take profit
max_wait_bars = 10
max_sl_pct = 10.0
risk_pct = 5.0

print(f"\n📋 Strategy Parameters:")
print(f"   RSI Trigger: {rsi_trigger}")
print(f"   Lookback: {lookback} candles")
print(f"   Retracement: {retracement_pct}% to highest high")
print(f"   Take Profit: {tp_pct}% (flat)")
print(f"   Max Wait: {max_wait_bars} bars")
print(f"   Max SL: {max_sl_pct}%")
print(f"   Risk per Trade: {risk_pct}%")

# Stats
stats = {
    'crossdowns': 0,
    'signals': 0,
    'skipped_pending': 0,
    'rejected_sl': 0,
    'limits_placed': 0,
    'limits_filled': 0,
    'limits_timeout': 0
}

# Backtest
equity = 100.0
trades = []
rejected_trades = []  # Track what we rejected

limit_pending = False
limit_placed_idx = None
limit_price = None
sl_price = None
tp_price = None
entry_price = None

# Track RSI for cross detection
prev_rsi = None

for i in range(lookback + 14, len(df)):
    row = df.iloc[i]

    if pd.isna(row['rsi']):
        prev_rsi = row['rsi']
        continue

    current_rsi = row['rsi']

    # Check for limit order status
    if limit_pending:
        bars_waiting = i - limit_placed_idx

        # Timeout
        if bars_waiting > max_wait_bars:
            stats['limits_timeout'] += 1
            limit_pending = False
            prev_rsi = current_rsi
            continue

        # Check fill
        if row['high'] >= limit_price:  # SHORT: fill if price reaches our limit
            # FILLED - now find exit
            stats['limits_filled'] += 1

            sl_dist_pct = ((sl_price - limit_price) / limit_price) * 100
            position_size = (equity * (risk_pct / 100)) / (sl_dist_pct / 100)

            # Find exit
            hit_sl = False
            hit_tp = False
            exit_idx = None

            for j in range(i + 1, min(i + 500, len(df))):
                future_row = df.iloc[j]

                # SHORT: SL if price goes UP
                if future_row['high'] >= sl_price:
                    hit_sl = True
                    exit_idx = j
                    break
                # SHORT: TP if price goes DOWN
                elif future_row['low'] <= tp_price:
                    hit_tp = True
                    exit_idx = j
                    break

            if hit_sl:
                pnl_pct = -sl_dist_pct
                exit_reason = 'SL'
            elif hit_tp:
                pnl_pct = tp_pct
                exit_reason = 'TP'
            else:
                limit_pending = False
                prev_rsi = current_rsi
                continue

            pnl_dollar = position_size * (pnl_pct / 100)
            equity += pnl_dollar

            trades.append({
                'signal_time': df.iloc[limit_placed_idx]['timestamp'],
                'entry_time': row['timestamp'],
                'exit_time': df.iloc[exit_idx]['timestamp'] if exit_idx else None,
                'signal_rsi': df.iloc[limit_placed_idx]['rsi'],
                'entry_price': limit_price,
                'sl_price': sl_price,
                'tp_price': tp_price,
                'sl_dist_pct': sl_dist_pct,
                'position_size': position_size,
                'pnl_pct': pnl_pct,
                'pnl_dollar': pnl_dollar,
                'exit_reason': exit_reason,
                'equity_after': equity,
                'rejected': False
            })

            limit_pending = False

    # Detect RSI cross down from >72 to <72
    if prev_rsi is not None:
        crossed_down = (prev_rsi > rsi_trigger and current_rsi <= rsi_trigger)

        if crossed_down:
            stats['crossdowns'] += 1

            # Skip if limit already pending
            if limit_pending:
                stats['skipped_pending'] += 1
                prev_rsi = current_rsi
                continue

            # Calculate signal
            stats['signals'] += 1

            # Find highest high in last 5 candles
            highest_high = df.iloc[i-lookback:i+1]['high'].max()
            current_close = row['close']

            # Calculate limit: 30% of the way from close to highest high
            distance = highest_high - current_close
            limit_price = current_close + (distance * (retracement_pct / 100))

            # Stop loss at highest high
            sl_price = highest_high

            # Take profit at 5% below entry
            tp_price = limit_price * (1 - tp_pct / 100)

            # Calculate SL distance
            sl_dist_pct = ((sl_price - limit_price) / limit_price) * 100

            # Check SL filter
            if sl_dist_pct > max_sl_pct or sl_dist_pct <= 0:
                stats['rejected_sl'] += 1

                # Track rejected trade for analysis
                rejected_trades.append({
                    'signal_time': row['timestamp'],
                    'signal_rsi': current_rsi,
                    'close': current_close,
                    'highest_high': highest_high,
                    'limit_price': limit_price,
                    'sl_price': sl_price,
                    'sl_dist_pct': sl_dist_pct,
                    'rejected': True
                })

                prev_rsi = current_rsi
                continue

            # Valid - place limit
            stats['limits_placed'] += 1
            limit_pending = True
            limit_placed_idx = i

    prev_rsi = current_rsi

# Results
print(f"\n" + "="*90)
print("📊 SIGNAL FLOW")
print("="*90)
print()
print(f"RSI Crossdowns (>72 → ≤72):  {stats['crossdowns']}")
print(f"  Skipped (limit pending):    {stats['skipped_pending']}")
print(f"  Valid signals:              {stats['signals']}")
print(f"    ❌ Rejected (SL >{max_sl_pct}%):  {stats['rejected_sl']}")
print(f"    ✅ Limits placed:           {stats['limits_placed']}")
print()
print(f"Limit Results:")
print(f"  ✅ Filled:                   {stats['limits_filled']} ({stats['limits_filled']/stats['limits_placed']*100 if stats['limits_placed'] > 0 else 0:.1f}%)")
print(f"  ⏱️  Timeout:                  {stats['limits_timeout']} ({stats['limits_timeout']/stats['limits_placed']*100 if stats['limits_placed'] > 0 else 0:.1f}%)")

# Backtest results
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

    print(f"\n" + "="*90)
    print("🏆 BACKTEST RESULTS (WITH SL FILTER)")
    print("="*90)
    print()
    print(f"Total Trades:     {len(trades_df)}")
    print(f"Win Rate:         {win_rate:.1f}% ({len(winners)}W / {len(losers)}L)")
    print(f"TP Hits:          {tp_count}")
    print(f"SL Hits:          {sl_count}")
    print()
    print(f"Total Return:     {total_return:+.1f}%")
    print(f"Max Drawdown:     {max_dd:.2f}%")
    print(f"Return/DD:        {return_dd:.2f}x")
    print(f"Final Equity:     ${equity:.2f}")
    print()
    print(f"Avg Winner:       {winners['pnl_pct'].mean():.2f}%")
    print(f"Avg Loser:        {losers['pnl_pct'].mean():.2f}%")
    print(f"Avg SL Distance:  {trades_df['sl_dist_pct'].mean():.2f}%")

    trades_df.to_csv('pengu_rsi_crossdown_trades.csv', index=False)
    print(f"\n💾 Trades saved to: pengu_rsi_crossdown_trades.csv")
else:
    print("\n❌ No trades generated!")

# Analyze rejected trades
if stats['rejected_sl'] > 0:
    rejected_df = pd.DataFrame(rejected_trades)

    print(f"\n" + "="*90)
    print(f"🔍 REJECTED TRADES ANALYSIS (SL >{max_sl_pct}%)")
    print("="*90)
    print()
    print(f"Total rejected: {len(rejected_df)}")
    print(f"Avg SL distance: {rejected_df['sl_dist_pct'].mean():.2f}%")
    print(f"Max SL distance: {rejected_df['sl_dist_pct'].max():.2f}%")
    print(f"Min SL distance: {rejected_df['sl_dist_pct'].min():.2f}%")

    print(f"\n💡 What if we took ALL rejected trades?")
    print("   (Simulating with same fill/exit logic but no SL filter)")

    # Quick sim of rejected trades
    rejected_equity = 100.0
    rejected_trade_results = []

    for _, rej in rejected_df.iterrows():
        # Find if this limit would have filled
        signal_idx = df[df['timestamp'] == rej['signal_time']].index[0]
        limit_price = rej['limit_price']
        sl_price = rej['sl_price']
        tp_price = limit_price * (1 - tp_pct / 100)
        sl_dist_pct = rej['sl_dist_pct']

        # Check fill within 10 bars
        filled = False
        for j in range(signal_idx + 1, min(signal_idx + max_wait_bars + 1, len(df))):
            if df.iloc[j]['high'] >= limit_price:
                filled = True
                fill_idx = j
                break

        if not filled:
            continue

        # Find exit
        hit_sl = False
        hit_tp = False

        for k in range(fill_idx + 1, min(fill_idx + 500, len(df))):
            if df.iloc[k]['high'] >= sl_price:
                hit_sl = True
                break
            elif df.iloc[k]['low'] <= tp_price:
                hit_tp = True
                break

        if hit_sl:
            pnl_pct = -sl_dist_pct
        elif hit_tp:
            pnl_pct = tp_pct
        else:
            continue

        position_size = (rejected_equity * (risk_pct / 100)) / (sl_dist_pct / 100)
        pnl_dollar = position_size * (pnl_pct / 100)
        rejected_equity += pnl_dollar
        rejected_trade_results.append(pnl_dollar)

    if len(rejected_trade_results) > 0:
        rejected_return = ((rejected_equity - 100) / 100) * 100
        print(f"   Rejected trades that would have filled: {len(rejected_trade_results)}")
        print(f"   Return from rejected trades: {rejected_return:+.1f}%")
        print(f"   Combined total return: {total_return + rejected_return:+.1f}%")
    else:
        print(f"   None of the rejected trades would have filled within timeout")

print("="*90)
