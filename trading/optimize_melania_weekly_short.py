"""
Optimize MELANIA Weekly Top Short Strategy
Test multiple parameter combinations to find the edge.
"""
import pandas as pd
import numpy as np
from itertools import product

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

def calculate_atr(df, period=14):
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr

df['rsi'] = calculate_rsi(df['close'])
df['atr'] = calculate_atr(df)
df['week'] = df['timestamp'].dt.isocalendar().week
df['year'] = df['timestamp'].dt.isocalendar().year
df['year_week'] = df['year'].astype(str) + '_W' + df['week'].astype(str)

def run_backtest(rsi_thresh, entry_break, tp_pct, sl_pct, one_trade_per_week=True):
    """Run backtest with given parameters."""

    trades = []
    equity = 100.0

    in_trade = False
    entry_price = 0
    entry_idx = 0
    entry_week = None
    highest_seen = 0
    highest_rsi = 0
    armed = False
    armed_week = None
    traded_weeks = set()

    for i in range(50, len(df)):
        row = df.iloc[i]
        current_week = row['year_week']

        # Reset at start of new week
        if current_week != armed_week:
            armed = False
            armed_week = None
            highest_seen = 0
            highest_rsi = 0

        if in_trade:
            # Check exit conditions
            tp_price = entry_price * (1 - tp_pct/100)
            sl_price = entry_price * (1 + sl_pct/100)

            # Take profit
            if row['low'] <= tp_price:
                exit_price = tp_price
                pnl_pct = ((exit_price - entry_price) / entry_price) * 100
                equity_risk = equity * 0.05
                pnl = equity_risk * (abs(pnl_pct) / sl_pct)

                equity += pnl
                trades.append({
                    'week': entry_week,
                    'pnl_pct': pnl_pct,
                    'pnl_usd': pnl,
                    'equity': equity,
                    'exit_reason': 'TP',
                })

                in_trade = False

            # Stop loss
            elif row['high'] >= sl_price:
                exit_price = sl_price
                pnl_pct = ((exit_price - entry_price) / entry_price) * 100
                equity_risk = equity * 0.05
                pnl = -equity_risk

                equity += pnl
                trades.append({
                    'week': entry_week,
                    'pnl_pct': pnl_pct,
                    'pnl_usd': pnl,
                    'equity': equity,
                    'exit_reason': 'SL',
                })

                in_trade = False

        else:
            # Skip if already traded this week
            if one_trade_per_week and current_week in traded_weeks:
                continue

            # Track highest point in current week
            if row['high'] > highest_seen:
                highest_seen = row['high']
                highest_rsi = row['rsi']

            # Arm when RSI > threshold
            if highest_rsi > rsi_thresh and not armed:
                armed = True
                armed_week = current_week

            # Enter when price breaks below high
            if armed and current_week == armed_week:
                break_level = highest_seen * (1 - entry_break/100)

                if row['low'] <= break_level:
                    # Additional filter: make sure we're not at the absolute bottom
                    # (avoid shorting into strong support)
                    recent_low = df.iloc[max(0, i-96):i]['low'].min()  # 24h low
                    if row['low'] > recent_low * 1.02:  # At least 2% above recent low

                        entry_price = break_level
                        entry_idx = i
                        entry_week = current_week
                        in_trade = True
                        traded_weeks.add(current_week)
                        armed = False

    return trades, equity

# Parameter grid
rsi_thresholds = [70, 75, 80, 85]
entry_breaks = [1.0, 1.5, 2.0, 3.0]
tp_pcts = [6.0, 8.0, 10.0, 12.0]
sl_pcts = [3.0, 4.0, 5.0, 6.0]
one_trade_options = [True, False]

results = []
total_combos = len(rsi_thresholds) * len(entry_breaks) * len(tp_pcts) * len(sl_pcts) * len(one_trade_options)
combo_count = 0

print(f"Testing {total_combos} parameter combinations...")

for rsi_thresh, entry_break, tp_pct, sl_pct, one_trade in product(
    rsi_thresholds, entry_breaks, tp_pcts, sl_pcts, one_trade_options
):
    combo_count += 1
    if combo_count % 50 == 0:
        print(f"Progress: {combo_count}/{total_combos}")

    # Skip unrealistic R:R ratios
    if tp_pct / sl_pct < 1.2:  # Need at least 1.2:1 R:R
        continue

    trades, final_equity = run_backtest(rsi_thresh, entry_break, tp_pct, sl_pct, one_trade)

    if len(trades) == 0:
        continue

    trades_df = pd.DataFrame(trades)
    total_trades = len(trades_df)
    winners = trades_df[trades_df['pnl_pct'] < 0]
    win_rate = len(winners) / total_trades * 100 if total_trades > 0 else 0
    total_return = ((final_equity - 100) / 100) * 100

    # Calculate equity curve for drawdown
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
        'one_trade_per_week': one_trade,
        'total_trades': total_trades,
        'win_rate': win_rate,
        'total_return': total_return,
        'final_equity': final_equity,
        'max_dd': max_dd,
        'return_dd_ratio': abs(total_return / max_dd) if max_dd != 0 else 0,
    })

results_df = pd.DataFrame(results)
results_df = results_df.sort_values('return_dd_ratio', ascending=False)

print("\n" + "=" * 120)
print("TOP 20 PARAMETER COMBINATIONS (by Return/DD ratio)")
print("=" * 120)
print(results_df.head(20).to_string(index=False))

print("\n" + "=" * 120)
print("TOP 10 BY TOTAL RETURN")
print("=" * 120)
print(results_df.nlargest(10, 'total_return')[
    ['rsi_thresh', 'entry_break', 'tp_pct', 'sl_pct', 'one_trade_per_week',
     'total_trades', 'win_rate', 'total_return', 'max_dd', 'return_dd_ratio']
].to_string(index=False))

print("\n" + "=" * 120)
print("TOP 10 BY WIN RATE")
print("=" * 120)
print(results_df.nlargest(10, 'win_rate')[
    ['rsi_thresh', 'entry_break', 'tp_pct', 'sl_pct', 'one_trade_per_week',
     'total_trades', 'win_rate', 'total_return', 'max_dd', 'return_dd_ratio']
].to_string(index=False))

results_df.to_csv('trading/melania_weekly_short_optimization.csv', index=False)
print(f"\nSaved full results to: trading/melania_weekly_short_optimization.csv")

# Show best overall
best = results_df.iloc[0]
print("\n" + "=" * 120)
print("BEST STRATEGY (highest Return/DD ratio)")
print("=" * 120)
print(f"RSI Threshold: {best['rsi_thresh']}")
print(f"Entry Break: {best['entry_break']}%")
print(f"Take Profit: {best['tp_pct']}%")
print(f"Stop Loss: {best['sl_pct']}%")
print(f"One Trade Per Week: {best['one_trade_per_week']}")
print(f"\nTotal Trades: {best['total_trades']}")
print(f"Win Rate: {best['win_rate']:.1f}%")
print(f"Total Return: {best['total_return']:+.2f}%")
print(f"Max Drawdown: {best['max_dd']:.2f}%")
print(f"Return/DD Ratio: {best['return_dd_ratio']:.2f}x")
