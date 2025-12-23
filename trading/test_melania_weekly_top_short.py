"""
MELANIA Weekly Top Short Strategy
Edge: 100% of weeks have significant drawdown from weekly top.
Average drawdown: -20.16%, median: -14.85%

Strategy:
- Each week starts fresh (Monday or first day)
- Wait for RSI > threshold at local high
- Short when price breaks below recent support
- Take profit at fixed % or trailing stop
- Reset for next week
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

# Strategy parameters
RSI_THRESHOLD = 70  # Arm when RSI > this
LOOKBACK = 8  # Look back N candles for recent high
ENTRY_BREAK_PCT = 0.5  # Enter when price breaks X% below recent high
TP_PCT = 8.0  # Take profit at 8% below entry
SL_PCT = 4.0  # Stop loss at 4% above entry
MAX_HOLD_CANDLES = 200  # Max hold time (50 hours)

def run_backtest(rsi_thresh, lookback, entry_break, tp_pct, sl_pct, max_hold):
    """Run backtest with given parameters."""

    trades = []
    equity = 100.0
    equity_curve = [equity]

    in_trade = False
    entry_price = 0
    entry_idx = 0
    entry_week = None
    highest_seen = 0
    armed = False
    armed_week = None

    for i in range(50, len(df)):
        row = df.iloc[i]
        current_week = row['year_week']

        # Reset at start of new week
        if current_week != armed_week:
            armed = False
            armed_week = None

        if in_trade:
            # Check exit conditions
            tp_price = entry_price * (1 - tp_pct/100)
            sl_price = entry_price * (1 + sl_pct/100)
            candles_held = i - entry_idx

            # Take profit
            if row['low'] <= tp_price:
                exit_price = tp_price
                pnl_pct = ((exit_price - entry_price) / entry_price) * 100
                position_size = equity * 0.05  # Risk 5% per trade
                pnl = position_size * (pnl_pct / sl_pct)  # Normalize by SL
                equity += pnl

                trades.append({
                    'week': entry_week,
                    'entry_idx': entry_idx,
                    'exit_idx': i,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl_pct': pnl_pct,
                    'pnl_usd': pnl,
                    'equity': equity,
                    'exit_reason': 'TP',
                    'candles_held': candles_held,
                })

                in_trade = False
                armed = False

            # Stop loss
            elif row['high'] >= sl_price:
                exit_price = sl_price
                pnl_pct = ((exit_price - entry_price) / entry_price) * 100
                position_size = equity * 0.05
                pnl = position_size * (pnl_pct / sl_pct)
                equity += pnl

                trades.append({
                    'week': entry_week,
                    'entry_idx': entry_idx,
                    'exit_idx': i,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl_pct': pnl_pct,
                    'pnl_usd': pnl,
                    'equity': equity,
                    'exit_reason': 'SL',
                    'candles_held': candles_held,
                })

                in_trade = False
                armed = False

            # Max hold timeout
            elif candles_held >= max_hold:
                exit_price = row['close']
                pnl_pct = ((exit_price - entry_price) / entry_price) * 100
                position_size = equity * 0.05
                pnl = position_size * (pnl_pct / sl_pct)
                equity += pnl

                trades.append({
                    'week': entry_week,
                    'entry_idx': entry_idx,
                    'exit_idx': i,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl_pct': pnl_pct,
                    'pnl_usd': pnl,
                    'equity': equity,
                    'exit_reason': 'TIMEOUT',
                    'candles_held': candles_held,
                })

                in_trade = False
                armed = False

        else:
            # Look for entry setup
            # Step 1: Arm when RSI > threshold at a local high
            if row['rsi'] > rsi_thresh and not armed:
                # Check if this is a local high
                recent_data = df.iloc[max(0, i-lookback):i+1]
                if len(recent_data) > 0 and row['high'] >= recent_data['high'].max() * 0.98:
                    armed = True
                    armed_week = current_week
                    highest_seen = row['high']

            # Step 2: Enter when price breaks below high
            if armed and current_week == armed_week:
                break_level = highest_seen * (1 - entry_break/100)

                if row['low'] <= break_level:
                    entry_price = break_level
                    entry_idx = i
                    entry_week = current_week
                    in_trade = True

        equity_curve.append(equity)

    return trades, equity_curve

# Run backtest
trades, equity_curve = run_backtest(
    RSI_THRESHOLD, LOOKBACK, ENTRY_BREAK_PCT, TP_PCT, SL_PCT, MAX_HOLD_CANDLES
)

# Analyze results
if len(trades) == 0:
    print("No trades generated!")
    exit()

trades_df = pd.DataFrame(trades)

print("=" * 100)
print(f"MELANIA WEEKLY TOP SHORT STRATEGY")
print("=" * 100)
print(f"RSI Threshold: {RSI_THRESHOLD}")
print(f"Lookback: {LOOKBACK} candles")
print(f"Entry Break: {ENTRY_BREAK_PCT}%")
print(f"Take Profit: {TP_PCT}%")
print(f"Stop Loss: {SL_PCT}%")
print(f"Max Hold: {MAX_HOLD_CANDLES} candles")
print("=" * 100)
print()

# Performance metrics
total_trades = len(trades_df)
winners = trades_df[trades_df['pnl_pct'] < 0]  # Negative PNL% = profit for shorts
losers = trades_df[trades_df['pnl_pct'] >= 0]
win_rate = len(winners) / total_trades * 100 if total_trades > 0 else 0

final_equity = equity_curve[-1]
total_return = ((final_equity - 100) / 100) * 100
max_equity = max(equity_curve)
max_dd = min([(equity_curve[i] - max(equity_curve[:i+1])) / max(equity_curve[:i+1]) * 100
              for i in range(1, len(equity_curve))])

print(f"Total Trades: {total_trades}")
print(f"Winners: {len(winners)} ({win_rate:.1f}%)")
print(f"Losers: {len(losers)}")
print()

print(f"Total Return: {total_return:+.2f}%")
print(f"Final Equity: ${final_equity:.2f}")
print(f"Max Drawdown: {max_dd:.2f}%")
print(f"Return/DD Ratio: {abs(total_return/max_dd):.2f}x" if max_dd != 0 else "N/A")
print()

if len(winners) > 0:
    print(f"Avg Winner: {winners['pnl_pct'].mean():.2f}%")
    print(f"Best Winner: {winners['pnl_pct'].min():.2f}%")
if len(losers) > 0:
    print(f"Avg Loser: {losers['pnl_pct'].mean():.2f}%")
    print(f"Worst Loser: {losers['pnl_pct'].max():.2f}%")
print()

# Exit reasons
print("Exit reasons:")
for reason in trades_df['exit_reason'].unique():
    count = (trades_df['exit_reason'] == reason).sum()
    print(f"  {reason}: {count} ({count/total_trades*100:.1f}%)")
print()

# Weekly breakdown
print("Trades by week:")
print(trades_df.groupby('week')['pnl_pct'].agg(['count', 'mean', 'sum']))
print()

print("=" * 100)
print("TRADE LOG")
print("=" * 100)
print(trades_df[['week', 'entry_price', 'exit_price', 'pnl_pct', 'exit_reason', 'candles_held']].to_string(index=False))

trades_df.to_csv('trading/melania_weekly_top_short_trades.csv', index=False)
print(f"\nSaved trades to: trading/melania_weekly_top_short_trades.csv")
