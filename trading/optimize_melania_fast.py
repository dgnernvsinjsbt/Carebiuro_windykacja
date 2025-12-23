"""
Fast optimization focusing on key insights:
- High RSI tops (>75) have better drawdowns (-25% vs -13%)
- Early tops better than late tops
- One trade per week to avoid overtrading
"""
import pandas as pd
import numpy as np

# Load data
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

df['rsi'] = calculate_rsi(df['close'])
df['week'] = df['timestamp'].dt.isocalendar().week
df['year'] = df['timestamp'].dt.isocalendar().year
df['year_week'] = df['year'].astype(str) + '_W' + df['week'].astype(str)
df['wick_top'] = df['high'] - df[['open', 'close']].max(axis=1)
df['body'] = abs(df['close'] - df['open'])
df['wick_ratio'] = df['wick_top'] / (df['high'] - df['low'] + 0.0001)

def run_backtest(rsi_thresh, entry_break, tp_pct, sl_pct, small_wick_only=False):
    """
    Simple weekly strategy:
    - Track weekly high with RSI > threshold
    - Enter short on break below
    - One trade per week max
    """

    trades = []
    equity = 100.0

    traded_weeks = set()
    week_high = {}
    week_high_rsi = {}
    week_high_wick = {}

    for i in range(50, len(df)):
        row = df.iloc[i]
        current_week = row['year_week']

        # Initialize week tracking
        if current_week not in week_high:
            week_high[current_week] = 0
            week_high_rsi[current_week] = 0
            week_high_wick[current_week] = 0

        # Update week high if conditions met
        if row['high'] > week_high[current_week] and row['rsi'] > rsi_thresh:
            week_high[current_week] = row['high']
            week_high_rsi[current_week] = row['rsi']
            week_high_wick[current_week] = row['wick_ratio']

        # Skip if already traded this week
        if current_week in traded_weeks:
            continue

        # Check for entry
        if week_high[current_week] > 0:
            # Apply small wick filter if enabled
            if small_wick_only and week_high_wick[current_week] > 0.4:
                continue

            break_level = week_high[current_week] * (1 - entry_break/100)

            if row['low'] <= break_level:
                # Enter short
                entry_price = break_level
                tp_price = entry_price * (1 - tp_pct/100)
                sl_price = entry_price * (1 + sl_pct/100)

                # Simulate trade over next candles
                for j in range(i+1, min(i+300, len(df))):  # Max 75 hours
                    future_row = df.iloc[j]
                    future_week = future_row['year_week']

                    # TP hit
                    if future_row['low'] <= tp_price:
                        pnl_pct = ((tp_price - entry_price) / entry_price) * 100
                        equity_risk = equity * 0.05
                        pnl = equity_risk * (abs(pnl_pct) / sl_pct)
                        equity += pnl

                        trades.append({
                            'week': current_week,
                            'entry_rsi': week_high_rsi[current_week],
                            'pnl_pct': pnl_pct,
                            'equity': equity,
                            'result': 'WIN',
                        })
                        traded_weeks.add(current_week)
                        break

                    # SL hit
                    elif future_row['high'] >= sl_price:
                        pnl_pct = ((sl_price - entry_price) / entry_price) * 100
                        equity_risk = equity * 0.05
                        pnl = -equity_risk
                        equity += pnl

                        trades.append({
                            'week': current_week,
                            'entry_rsi': week_high_rsi[current_week],
                            'pnl_pct': pnl_pct,
                            'equity': equity,
                            'result': 'LOSS',
                        })
                        traded_weeks.add(current_week)
                        break

                    # Week change without hit - close at market
                    if future_week != current_week and j == min(i+300, len(df))-1:
                        exit_price = future_row['close']
                        pnl_pct = ((exit_price - entry_price) / entry_price) * 100
                        equity_risk = equity * 0.05
                        pnl = equity_risk * (pnl_pct / sl_pct)
                        equity += pnl

                        trades.append({
                            'week': current_week,
                            'entry_rsi': week_high_rsi[current_week],
                            'pnl_pct': pnl_pct,
                            'equity': equity,
                            'result': 'TIMEOUT',
                        })
                        traded_weeks.add(current_week)
                        break

    return trades, equity

# Test parameter grid (reduced for speed)
params_to_test = [
    # RSI, Entry Break, TP, SL, Small Wick Filter
    (75, 2.0, 10.0, 5.0, False),
    (75, 2.0, 12.0, 5.0, False),
    (75, 2.5, 10.0, 5.0, False),
    (75, 3.0, 12.0, 5.0, False),
    (80, 2.0, 10.0, 5.0, False),
    (80, 2.5, 12.0, 5.0, False),
    (80, 3.0, 15.0, 5.0, False),
    (75, 2.0, 10.0, 5.0, True),  # With wick filter
    (80, 2.5, 12.0, 5.0, True),  # With wick filter
    (85, 3.0, 15.0, 6.0, False),
]

results = []

for rsi_thresh, entry_break, tp_pct, sl_pct, small_wick in params_to_test:
    trades, final_equity = run_backtest(rsi_thresh, entry_break, tp_pct, sl_pct, small_wick)

    if len(trades) == 0:
        continue

    trades_df = pd.DataFrame(trades)
    total_trades = len(trades_df)
    winners = trades_df[trades_df['pnl_pct'] < 0]
    win_rate = len(winners) / total_trades * 100
    total_return = ((final_equity - 100) / 100) * 100

    # Calculate drawdown
    equity_curve = [100.0] + trades_df['equity'].tolist()
    max_dd = 0
    peak = equity_curve[0]
    for equity in equity_curve:
        if equity > peak:
            peak = equity
        dd = (equity - peak) / peak * 100
        if dd < max_dd:
            max_dd = dd

    results.append({
        'rsi_thresh': rsi_thresh,
        'entry_break': entry_break,
        'tp_pct': tp_pct,
        'sl_pct': sl_pct,
        'wick_filter': small_wick,
        'trades': total_trades,
        'win_rate': win_rate,
        'return': total_return,
        'max_dd': max_dd,
        'r_dd': abs(total_return / max_dd) if max_dd != 0 else 0,
    })

results_df = pd.DataFrame(results).sort_values('r_dd', ascending=False)

print("=" * 100)
print("MELANIA WEEKLY TOP SHORT - OPTIMIZATION RESULTS")
print("=" * 100)
print(results_df.to_string(index=False))

# Test best parameters in detail
best = results_df.iloc[0]
print("\n" + "=" * 100)
print("BEST STRATEGY - DETAILED RESULTS")
print("=" * 100)
print(f"RSI Threshold: {best['rsi_thresh']}")
print(f"Entry Break: {best['entry_break']}%")
print(f"Take Profit: {best['tp_pct']}%")
print(f"Stop Loss: {best['sl_pct']}%")
print(f"Wick Filter: {best['wick_filter']}")
print(f"\nTrades: {best['trades']}")
print(f"Win Rate: {best['win_rate']:.1f}%")
print(f"Total Return: {best['return']:+.2f}%")
print(f"Max Drawdown: {best['max_dd']:.2f}%")
print(f"Return/DD: {best['r_dd']:.2f}x")

# Run best strategy again to get trade details
trades, _ = run_backtest(
    int(best['rsi_thresh']),
    best['entry_break'],
    best['tp_pct'],
    best['sl_pct'],
    best['wick_filter']
)

trades_df = pd.DataFrame(trades)
print("\n" + "=" * 100)
print("TRADE LOG")
print("=" * 100)
print(trades_df.to_string(index=False))

trades_df.to_csv('trading/melania_weekly_best_trades.csv', index=False)
print(f"\nSaved to: trading/melania_weekly_best_trades.csv")
