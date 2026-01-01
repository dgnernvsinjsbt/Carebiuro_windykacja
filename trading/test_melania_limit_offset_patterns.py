"""
MELANIA Pattern-Based SHORT with Limit Offset Entry
Strategy:
1. Detect patterns (VOL_SPIKE, PARABOLIC, EXTREME_GREEN)
2. Place limit order ABOVE current price by X ATR (wait for pullback)
3. Only enter if price retraces = confirms reversal
4. Tight SL at pattern high, wider TP

Benefits:
- Better entry price (higher is better for shorts)
- Tighter stops (pattern high is reference)
- Filters false signals (no retrace = no trade)
- More room to TP
"""
import pandas as pd
import numpy as np

df = pd.read_csv('trading/melania_3months_bingx.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

def calculate_rsi(prices, period=14):
    delta = prices.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(com=period-1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period-1, min_periods=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_atr(df, period=14):
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr

df['rsi'] = calculate_rsi(df['close'])
df['atr'] = calculate_atr(df)
df['body'] = abs(df['close'] - df['open'])
df['body_pct'] = (df['body'] / df['open']) * 100
df['price_change'] = df['close'].pct_change() * 100
df['is_green'] = (df['close'] > df['open']).astype(int)
df['atr_pct'] = (df['atr'] / df['close']) * 100

def backtest_limit_offset(
    limit_offset_atr=0.5,
    tp_pct=10.0,
    sl_offset_atr=0.3,
    max_wait_bars=20,
    patterns_enabled={'vol': True, 'para': True, 'extreme': True}
):
    """
    Pattern-based short with limit offset entry.
    """
    trades = []
    equity = 100.0
    pending_order = None  # (idx, pattern_type, pattern_high, limit_price, sl_price, atr)

    for i in range(50, len(df)):
        row = df.iloc[i]

        # Check for pending order fill
        if pending_order is not None:
            order_idx, pattern_type, pattern_high, limit_price, sl_price, order_atr = pending_order
            bars_waited = i - order_idx

            # Check if limit filled (price touched limit)
            if row['high'] >= limit_price:
                # Filled! Enter short
                entry_price = limit_price
                tp_price = entry_price * (1 - tp_pct/100)

                # Now manage the trade
                for j in range(i+1, min(i+200, len(df))):
                    future = df.iloc[j]

                    # TP hit
                    if future['low'] <= tp_price:
                        pnl_pct = ((tp_price - entry_price) / entry_price) * 100
                        sl_risk_pct = ((sl_price - entry_price) / entry_price) * 100
                        equity_risk = equity * 0.05
                        pnl = equity_risk * (abs(pnl_pct) / abs(sl_risk_pct))
                        equity += pnl

                        trades.append({
                            'pattern': pattern_type,
                            'signal_idx': order_idx,
                            'entry_idx': i,
                            'exit_idx': j,
                            'pattern_high': pattern_high,
                            'entry_price': entry_price,
                            'exit_price': tp_price,
                            'sl_price': sl_price,
                            'pnl_pct': pnl_pct,
                            'pnl_usd': pnl,
                            'equity': equity,
                            'result': 'TP',
                            'bars_to_fill': i - order_idx,
                            'sl_risk_pct': sl_risk_pct,
                        })
                        pending_order = None
                        break

                    # SL hit
                    elif future['high'] >= sl_price:
                        pnl_pct = ((sl_price - entry_price) / entry_price) * 100
                        sl_risk_pct = ((sl_price - entry_price) / entry_price) * 100
                        equity_risk = equity * 0.05
                        pnl = -equity_risk
                        equity += pnl

                        trades.append({
                            'pattern': pattern_type,
                            'signal_idx': order_idx,
                            'entry_idx': i,
                            'exit_idx': j,
                            'pattern_high': pattern_high,
                            'entry_price': entry_price,
                            'exit_price': sl_price,
                            'sl_price': sl_price,
                            'pnl_pct': pnl_pct,
                            'pnl_usd': pnl,
                            'equity': equity,
                            'result': 'SL',
                            'bars_to_fill': i - order_idx,
                            'sl_risk_pct': sl_risk_pct,
                        })
                        pending_order = None
                        break

            # Check timeout (order not filled)
            elif bars_waited >= max_wait_bars:
                pending_order = None

        # Look for new pattern signals (only if no pending order)
        if pending_order is None:
            pattern_triggered = None
            pattern_high = None

            # Pattern 1: Volatility Spike
            if patterns_enabled.get('vol', True):
                if row['atr_pct'] > 5.0 and row['rsi'] > 70:
                    pattern_triggered = 'VOL_SPIKE'
                    pattern_high = row['high']

            # Pattern 2: Parabolic Move
            if pattern_triggered is None and patterns_enabled.get('para', True):
                if row['body_pct'] > 3.0 and row['rsi'] > 70 and row['is_green']:
                    pattern_triggered = 'PARABOLIC'
                    pattern_high = row['high']

            # Pattern 3: Extreme Green Candle
            if pattern_triggered is None and patterns_enabled.get('extreme', True):
                if row['price_change'] > 5.0 and row['is_green']:
                    pattern_triggered = 'EXTREME_GREEN'
                    pattern_high = row['high']

            # If pattern found, place limit order
            if pattern_triggered is not None:
                limit_price = pattern_high + (limit_offset_atr * row['atr'])
                sl_price = pattern_high + (sl_offset_atr * row['atr'])

                # Sanity check: SL should be above limit
                if sl_price > limit_price:
                    pending_order = (i, pattern_triggered, pattern_high, limit_price, sl_price, row['atr'])

    return trades, equity

# Test different offset configurations
configs = [
    # Offset ATR, TP%, SL Offset ATR, Max Wait
    {'offset': 0.3, 'tp': 8, 'sl_offset': 0.2, 'wait': 20},
    {'offset': 0.5, 'tp': 8, 'sl_offset': 0.3, 'wait': 20},
    {'offset': 0.5, 'tp': 10, 'sl_offset': 0.3, 'wait': 20},
    {'offset': 0.5, 'tp': 12, 'sl_offset': 0.3, 'wait': 20},
    {'offset': 0.7, 'tp': 10, 'sl_offset': 0.4, 'wait': 20},
    {'offset': 0.7, 'tp': 12, 'sl_offset': 0.4, 'wait': 20},
    {'offset': 1.0, 'tp': 12, 'sl_offset': 0.5, 'wait': 20},
    {'offset': 1.0, 'tp': 15, 'sl_offset': 0.5, 'wait': 20},

    # Longer wait times
    {'offset': 0.5, 'tp': 10, 'sl_offset': 0.3, 'wait': 40},
    {'offset': 0.7, 'tp': 12, 'sl_offset': 0.4, 'wait': 40},

    # Individual patterns
    {'offset': 0.5, 'tp': 10, 'sl_offset': 0.3, 'wait': 20, 'patterns': {'vol': True, 'para': False, 'extreme': False}},
    {'offset': 0.5, 'tp': 10, 'sl_offset': 0.3, 'wait': 20, 'patterns': {'vol': False, 'para': True, 'extreme': False}},
    {'offset': 0.5, 'tp': 10, 'sl_offset': 0.3, 'wait': 20, 'patterns': {'vol': False, 'para': False, 'extreme': True}},
]

results = []

for config in configs:
    patterns = config.get('patterns', {'vol': True, 'para': True, 'extreme': True})

    trades, final_equity = backtest_limit_offset(
        limit_offset_atr=config['offset'],
        tp_pct=config['tp'],
        sl_offset_atr=config['sl_offset'],
        max_wait_bars=config['wait'],
        patterns_enabled=patterns
    )

    if len(trades) == 0:
        continue

    trades_df = pd.DataFrame(trades)
    total_trades = len(trades_df)
    winners = trades_df[trades_df['result'] == 'TP']
    win_rate = len(winners) / total_trades * 100
    total_return = ((final_equity - 100) / 100) * 100

    # Drawdown
    equity_curve = [100.0] + trades_df['equity'].tolist()
    max_dd = 0
    peak = equity_curve[0]
    for equity in equity_curve:
        if equity > peak:
            peak = equity
        dd = (equity - peak) / peak * 100
        if dd < max_dd:
            max_dd = dd

    avg_sl_risk = trades_df['sl_risk_pct'].mean()
    avg_bars_to_fill = trades_df['bars_to_fill'].mean()

    results.append({
        'offset_atr': config['offset'],
        'tp_pct': config['tp'],
        'sl_offset': config['sl_offset'],
        'max_wait': config['wait'],
        'patterns': str(patterns),
        'trades': total_trades,
        'win_rate': win_rate,
        'return': total_return,
        'max_dd': max_dd,
        'r_dd': abs(total_return / max_dd) if max_dd != 0 else 0,
        'avg_sl_risk': avg_sl_risk,
        'avg_bars_fill': avg_bars_to_fill,
    })

print(f"\nTested {len(configs)} configurations, got {len(results)} with trades")

if len(results) == 0:
    print("ERROR: No trades generated in any configuration!")
    exit()

results_df = pd.DataFrame(results).sort_values('r_dd', ascending=False)

print("=" * 140)
print("LIMIT OFFSET PATTERN STRATEGY - OPTIMIZATION")
print("=" * 140)
print(results_df.to_string(index=False))

# Best result
if len(results_df) > 0:
    best = results_df.iloc[0]
    print("\n" + "=" * 140)
    print(f"BEST STRATEGY")
    print("=" * 140)
    print(f"Limit Offset: {best['offset_atr']} ATR")
    print(f"Take Profit: {best['tp_pct']}%")
    print(f"SL Offset: {best['sl_offset']} ATR")
    print(f"Max Wait: {best['max_wait']} bars")
    print(f"Patterns: {best['patterns']}")
    print(f"\nTotal Trades: {best['trades']}")
    print(f"Win Rate: {best['win_rate']:.1f}%")
    print(f"Total Return: {best['return']:+.2f}%")
    print(f"Max Drawdown: {best['max_dd']:.2f}%")
    print(f"Return/DD: {best['r_dd']:.2f}x")
    print(f"Avg SL Risk: {best['avg_sl_risk']:.2f}%")
    print(f"Avg Bars to Fill: {best['avg_bars_fill']:.1f}")

    # Run best config in detail
    best_patterns = eval(best['patterns'])
    trades, _ = backtest_limit_offset(
        limit_offset_atr=best['offset_atr'],
        tp_pct=best['tp_pct'],
        sl_offset_atr=best['sl_offset'],
        max_wait_bars=int(best['max_wait']),
        patterns_enabled=best_patterns
    )

    trades_df = pd.DataFrame(trades)

    print("\n" + "=" * 140)
    print("PATTERN BREAKDOWN")
    print("=" * 140)
    for pattern in trades_df['pattern'].unique():
        p_trades = trades_df[trades_df['pattern'] == pattern]
        p_wins = len(p_trades[p_trades['result'] == 'TP'])
        p_wr = p_wins / len(p_trades) * 100
        print(f"{pattern:20s}: {len(p_trades):3d} trades, {p_wr:5.1f}% WR")

    print("\n" + "=" * 140)
    print("SAMPLE TRADES")
    print("=" * 140)
    print(trades_df[['pattern', 'pattern_high', 'entry_price', 'exit_price', 'sl_risk_pct', 'pnl_pct', 'result']].head(30).to_string(index=False))

    trades_df.to_csv('trading/melania_limit_offset_pattern_trades.csv', index=False)
    print(f"\nSaved to: trading/melania_limit_offset_pattern_trades.csv")
