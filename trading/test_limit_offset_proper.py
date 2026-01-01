#!/usr/bin/env python3
"""
LIMIT OFFSET - PROPER TEST

Baseline: SL=3.5%, TP=10%, market entry at trigger
Test: Same config but with limit order placed 0.5x ATR above trigger
"""
import pandas as pd
import numpy as np

df = pd.read_csv('fartcoin_6months_bingx_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)
df_dec = df[df['timestamp'].dt.month == 12].copy().reset_index(drop=True)

# Calculate ATR
high_low = df_dec['high'] - df_dec['low']
high_close = abs(df_dec['high'] - df_dec['close'].shift())
low_close = abs(df_dec['low'] - df_dec['close'].shift())
tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
df_dec['atr'] = tr.ewm(alpha=1/14, min_periods=14, adjust=False).mean()

print("="*140)
print("LIMIT OFFSET STRATEGY - PROPER COMPARISON")
print("="*140)
print()

ENTRY_OFFSET_PCT = 2.0
SL_PCT = 3.5
TP_PCT = 10.0
INITIAL_EQUITY = 100.0
MAX_WAIT_BARS = 20

def run_test(use_limit_offset=False, limit_offset_atr=0.0):
    """Run backtest with optional limit offset"""
    equity = INITIAL_EQUITY
    peak_equity = INITIAL_EQUITY
    max_dd = 0.0
    trades = []

    current_day = None
    daily_high = 0
    in_position = False
    tp_hit_today = False
    position = None
    pending_limit = None

    for i in range(50, len(df_dec)):
        row = df_dec.iloc[i]
        day = row['timestamp'].date()

        # New day reset
        if day != current_day:
            current_day = day
            daily_high = row['high']
            tp_hit_today = False
            pending_limit = None

            if in_position:
                exit_price = row['open']
                pnl_pct = ((position['entry_price'] - exit_price) / position['entry_price']) * 100
                pnl_dollar = position['position_size'] * (pnl_pct / 100)
                equity += pnl_dollar
                trades.append({'result': 'DAY_CLOSE', 'pnl_dollar': pnl_dollar})
                in_position = False
                position = None

        # Update daily high
        if row['high'] > daily_high:
            daily_high = row['high']

        # Check pending limit order
        if use_limit_offset and pending_limit:
            # Check if expired
            if i - pending_limit['placed_bar'] > MAX_WAIT_BARS:
                pending_limit = None
            # Check if filled (price bounced up to limit)
            elif row['high'] >= pending_limit['limit_price']:
                # FILLED
                entry_price = pending_limit['limit_price']
                sl_price = entry_price * (1 + SL_PCT / 100)
                tp_price = entry_price * (1 - TP_PCT / 100)
                position_size = (equity * 5.0) / SL_PCT

                in_position = True
                position = {
                    'entry_price': entry_price,
                    'sl_price': sl_price,
                    'tp_price': tp_price,
                    'position_size': position_size
                }
                pending_limit = None

        # Check for signal
        if not in_position and not tp_hit_today and not pending_limit:
            trigger_price = daily_high * (1 - ENTRY_OFFSET_PCT / 100)

            # Check if price dropped to trigger (intra-candle)
            if row['low'] <= trigger_price:
                if use_limit_offset:
                    # Place limit order above trigger
                    limit_price = trigger_price + (limit_offset_atr * row['atr'])

                    # Check if immediately filled
                    if row['high'] >= limit_price:
                        # Fill immediately
                        entry_price = limit_price
                        sl_price = entry_price * (1 + SL_PCT / 100)
                        tp_price = entry_price * (1 - TP_PCT / 100)
                        position_size = (equity * 5.0) / SL_PCT

                        in_position = True
                        position = {
                            'entry_price': entry_price,
                            'sl_price': sl_price,
                            'tp_price': tp_price,
                            'position_size': position_size
                        }
                    else:
                        # Place pending limit
                        pending_limit = {
                            'limit_price': limit_price,
                            'placed_bar': i
                        }
                else:
                    # Market entry at trigger (baseline)
                    entry_price = trigger_price
                    sl_price = entry_price * (1 + SL_PCT / 100)
                    tp_price = entry_price * (1 - TP_PCT / 100)
                    position_size = (equity * 5.0) / SL_PCT

                    in_position = True
                    position = {
                        'entry_price': entry_price,
                        'sl_price': sl_price,
                        'tp_price': tp_price,
                        'position_size': position_size
                    }

        # Check exits
        if in_position:
            hit_sl = row['high'] >= position['sl_price']
            hit_tp = row['low'] <= position['tp_price']

            if hit_sl or hit_tp:
                exit_price = position['sl_price'] if hit_sl else position['tp_price']
                pnl_pct = ((position['entry_price'] - exit_price) / position['entry_price']) * 100
                pnl_dollar = position['position_size'] * (pnl_pct / 100)
                equity += pnl_dollar

                if equity > peak_equity:
                    peak_equity = equity
                dd = ((peak_equity - equity) / peak_equity) * 100
                if dd > max_dd:
                    max_dd = dd

                trades.append({
                    'result': 'TP' if hit_tp else 'SL',
                    'pnl_dollar': pnl_dollar
                })

                in_position = False
                position = None

                if hit_tp:
                    tp_hit_today = True

    # Calculate results
    if trades:
        trades_df = pd.DataFrame(trades)
        total_return = ((equity - INITIAL_EQUITY) / INITIAL_EQUITY) * 100
        win_rate = (trades_df['result'] == 'TP').sum() / len(trades_df) * 100
        return_dd = total_return / max_dd if max_dd > 0 else 0

        return {
            'return': total_return,
            'max_dd': max_dd,
            'return_dd': return_dd,
            'trades': len(trades_df),
            'win_rate': win_rate,
            'equity': equity
        }
    return None

# Test baseline (market entry)
print("Testing BASELINE (market entry at trigger)...")
baseline = run_test(use_limit_offset=False)

# Test limit offsets
print("Testing LIMIT OFFSETS...")
offsets = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
limit_results = []

for offset in offsets:
    result = run_test(use_limit_offset=True, limit_offset_atr=offset)
    if result:
        result['offset'] = offset
        limit_results.append(result)

print()
print("="*140)
print("RESULTS")
print("="*140)
print()

# Baseline
print(f"BASELINE (market entry):")
print(f"  Return: {baseline['return']:+.2f}%")
print(f"  Max DD: {baseline['max_dd']:.2f}%")
print(f"  R/DD: {baseline['return_dd']:.2f}x")
print(f"  Trades: {baseline['trades']}")
print(f"  Win Rate: {baseline['win_rate']:.1f}%")
print(f"  Final Equity: ${baseline['equity']:.2f}")
print()

# Limit offsets
print(f"LIMIT OFFSET RESULTS:")
print("-"*140)
print(f"{'Offset':<12} {'Return':<12} {'Max DD':<12} {'R/DD':<10} {'Trades':<10} {'WR %':<10} {'Final $':<12}")
print("-"*140)

for r in limit_results:
    status = "🔥" if r['return_dd'] > baseline['return_dd'] else ("✅" if r['return_dd'] > baseline['return_dd'] * 0.9 else "")
    print(f"{r['offset']:.1f}x ATR    {r['return']:>+10.2f}%  {r['max_dd']:>10.2f}%  {r['return_dd']:>8.2f}x  {r['trades']:<10.0f} {r['win_rate']:>8.1f}%  ${r['equity']:>10.2f}  {status}")

print()
print("="*140)
print()

# Find best
if limit_results:
    best = max(limit_results, key=lambda x: x['return_dd'])

    if best['return_dd'] > baseline['return_dd']:
        improvement = best['return_dd'] - baseline['return_dd']
        print(f"🔥 IMPROVEMENT FOUND!")
        print(f"  Best offset: {best['offset']:.1f}x ATR")
        print(f"  Return: {best['return']:+.2f}% (baseline: {baseline['return']:+.2f}%)")
        print(f"  Max DD: {best['max_dd']:.2f}% (baseline: {baseline['max_dd']:.2f}%)")
        print(f"  R/DD: {best['return_dd']:.2f}x (baseline: {baseline['return_dd']:.2f}x)")
        print(f"  Improvement: +{improvement:.2f}x R/DD")
    else:
        print(f"❌ NO IMPROVEMENT")
        print(f"  Best limit offset: {best['offset']:.1f}x ATR with R/DD {best['return_dd']:.2f}x")
        print(f"  Baseline still better: {baseline['return_dd']:.2f}x R/DD")

print()
print("="*140)
