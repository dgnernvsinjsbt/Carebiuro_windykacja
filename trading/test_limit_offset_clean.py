"""
Clean implementation of limit offset pattern strategy
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

def backtest(limit_offset_atr, tp_pct, sl_offset_atr, max_wait):
    trades = []
    equity = 100.0

    i = 50
    while i < len(df):
        row = df.iloc[i]

        # Detect pattern
        pattern = None
        if row['atr_pct'] > 5.0 and row['rsi'] > 70:
            pattern = 'VOL_SPIKE'
        elif row['body_pct'] > 3.0 and row['rsi'] > 70 and row['is_green']:
            pattern = 'PARABOLIC'
        elif row['price_change'] > 5.0 and row['is_green']:
            pattern = 'EXTREME_GREEN'

        if pattern:
            # Place limit order
            pattern_high = row['high']
            limit_price = pattern_high + (limit_offset_atr * row['atr'])
            sl_price = pattern_high + (sl_offset_atr * row['atr'])

            if sl_price <= limit_price:  # Sanity check
                i += 1
                continue

            # Wait for fill
            filled = False
            fill_idx = None
            for j in range(i+1, min(i+1+max_wait, len(df))):
                if df.iloc[j]['high'] >= limit_price:
                    filled = True
                    fill_idx = j
                    break

            if filled:
                # Trade management
                entry_price = limit_price
                tp_price = entry_price * (1 - tp_pct/100)

                for k in range(fill_idx+1, min(fill_idx+201, len(df))):
                    bar = df.iloc[k]

                    if bar['low'] <= tp_price:
                        # TP hit
                        pnl_pct = ((tp_price - entry_price) / entry_price) * 100
                        sl_risk_pct = ((sl_price - entry_price) / entry_price) * 100
                        pnl = equity * 0.05 * (abs(pnl_pct) / abs(sl_risk_pct))
                        equity += pnl

                        trades.append({
                            'pattern': pattern,
                            'entry_price': entry_price,
                            'exit_price': tp_price,
                            'pnl_pct': pnl_pct,
                            'equity': equity,
                            'result': 'TP',
                            'sl_risk': sl_risk_pct,
                        })

                        i = k + 1  # Skip ahead
                        break

                    elif bar['high'] >= sl_price:
                        # SL hit
                        pnl_pct = ((sl_price - entry_price) / entry_price) * 100
                        pnl = -equity * 0.05
                        equity += pnl

                        trades.append({
                            'pattern': pattern,
                            'entry_price': entry_price,
                            'exit_price': sl_price,
                            'pnl_pct': pnl_pct,
                            'equity': equity,
                            'result': 'SL',
                            'sl_risk': pnl_pct,
                        })

                        i = k + 1
                        break
                else:
                    # Timeout - close at market
                    i = min(fill_idx+201, len(df))
            else:
                # Order not filled
                i += max_wait
        else:
            i += 1

    return trades, equity

# Test configurations
configs = [
    (0.3, 8, 0.2, 20),
    (0.5, 8, 0.3, 20),
    (0.5, 10, 0.3, 20),
    (0.5, 12, 0.3, 20),
    (0.7, 10, 0.4, 20),
    (0.7, 12, 0.4, 20),
    (1.0, 12, 0.5, 20),
    (1.0, 15, 0.5, 20),
]

results = []

for offset, tp, sl_offset, wait in configs:
    trades, final_equity = backtest(offset, tp, sl_offset, wait)

    if len(trades) == 0:
        continue

    trades_df = pd.DataFrame(trades)
    winners = trades_df[trades_df['result'] == 'TP']
    win_rate = len(winners) / len(trades_df) * 100
    total_return = ((final_equity - 100) / 100) * 100

    # DD
    equity_curve = [100.0] + trades_df['equity'].tolist()
    max_dd = 0
    peak = 100
    for eq in equity_curve:
        if eq > peak:
            peak = eq
        dd = (eq - peak) / peak * 100
        if dd < max_dd:
            max_dd = dd

    results.append({
        'offset': offset,
        'tp': tp,
        'sl_off': sl_offset,
        'wait': wait,
        'trades': len(trades_df),
        'wr': win_rate,
        'return': total_return,
        'dd': max_dd,
        'r_dd': abs(total_return/max_dd) if max_dd != 0 else 0,
    })

results_df = pd.DataFrame(results).sort_values('r_dd', ascending=False)

print("=" * 100)
print("LIMIT OFFSET PATTERN STRATEGY")
print("=" * 100)
print(results_df.to_string(index=False))

if len(results_df) > 0:
    best = results_df.iloc[0]
    print(f"\n{'='*100}")
    print(f"BEST: Offset={best['offset']} TP={best['tp']}% SL={best['sl_off']}")
    print(f"Trades={best['trades']} WR={best['wr']:.1f}% Return={best['return']:+.1f}% DD={best['dd']:.1f}% R/DD={best['r_dd']:.2f}x")

    # Detailed run
    trades, _ = backtest(best['offset'], best['tp'], best['sl_off'], int(best['wait']))
    trades_df = pd.DataFrame(trades)

    print(f"\n{'='*100}")
    print("PATTERN BREAKDOWN")
    print(f"{'='*100}")
    for p in trades_df['pattern'].unique():
        pt = trades_df[trades_df['pattern'] == p]
        pw = len(pt[pt['result'] == 'TP'])
        print(f"{p:20s}: {len(pt)} trades, {pw/len(pt)*100:.1f}% WR")

    print(f"\n{'='*100}")
    print("SAMPLE TRADES")
    print(f"{'='*100}")
    print(trades_df[['pattern', 'entry_price', 'exit_price', 'sl_risk', 'pnl_pct', 'result']].head(40).to_string(index=False))

    trades_df.to_csv('trading/melania_limit_offset_final.csv', index=False)
    print(f"\nSaved to trading/melania_limit_offset_final.csv")
