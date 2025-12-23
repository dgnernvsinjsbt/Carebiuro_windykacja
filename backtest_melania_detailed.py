#!/usr/bin/env python3
"""
MELANIA SHORT Reversal - Detailed Statistics
Get exact win rate, trade count, max DD, consecutive losses
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path('bingx-trading-bot').resolve()))

print("="*80)
print("MELANIA SHORT REVERSAL - DETAILED BACKTEST")
print("="*80)

# Load 6-month MELANIA data (same period as portfolio test)
df = pd.read_csv('trading/melania_6months_bingx.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print(f"\n📊 Data Loaded:")
print(f"   Period: {df['timestamp'].min()} to {df['timestamp'].max()}")
print(f"   Candles: {len(df)}")
print(f"   Days: {(df['timestamp'].max() - df['timestamp'].min()).days}")

# Calculate RSI (14-period Wilder's smoothing)
delta = df['close'].diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)
avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
rs = avg_gain / avg_loss
df['rsi'] = 100 - (100 / (1 + rs))

# Calculate ATR (14-period)
df['tr'] = np.maximum(
    df['high'] - df['low'],
    np.maximum(
        abs(df['high'] - df['close'].shift(1)),
        abs(df['low'] - df['close'].shift(1))
    )
)
df['atr'] = df['tr'].rolling(14).mean()

# MELANIA Parameters (from config.yaml)
RSI_TRIGGER = 72
LOOKBACK = 5
LIMIT_ATR_OFFSET = 0.8
TP_PCT = 10.0
MAX_WAIT_BARS = 20
MAX_SL_PCT = 10.0
RISK_PCT = 5.0

print(f"\n⚙️ MELANIA Strategy Parameters:")
print(f"   RSI Trigger: >{RSI_TRIGGER}")
print(f"   Lookback: {LOOKBACK} candles")
print(f"   Limit Offset: {LIMIT_ATR_OFFSET}x ATR")
print(f"   Take Profit: {TP_PCT}%")
print(f"   Max Wait: {MAX_WAIT_BARS} bars")
print(f"   Risk Per Trade: {RISK_PCT}%")

# Run backtest
equity = 100.0
trades = []
armed = False
signal_bar_idx = None
swing_low = None
limit_pending = False
limit_placed_bar = None
limit_price = None
sl_price = None
tp_price = None
position_size = None

consecutive_wins = 0
consecutive_losses = 0
max_consecutive_wins = 0
max_consecutive_losses = 0
current_streak = 0

for i in range(LOOKBACK + 14, len(df)):
    if limit_pending:
        # Check if limit filled
        if df.iloc[i]['low'] <= limit_price <= df.iloc[i]['high']:
            # Limit filled - enter trade
            entry_price = limit_price
            bars_waiting = i - limit_placed_bar

            # Find exit
            exit_idx = None
            exit_type = None

            for j in range(i+1, min(i+200, len(df))):
                if df.iloc[j]['low'] <= tp_price:
                    exit_idx = j
                    exit_type = 'TP'
                    break
                elif df.iloc[j]['high'] >= sl_price:
                    exit_idx = j
                    exit_type = 'SL'
                    break

            if exit_idx is None:
                exit_idx = min(i+200, len(df)-1)
                exit_type = 'TIME'

            # Calculate P&L
            if exit_type == 'TP':
                exit_price = tp_price
            elif exit_type == 'SL':
                exit_price = sl_price
            else:
                exit_price = df.iloc[exit_idx]['close']

            pnl_pct = ((entry_price - exit_price) / entry_price) * 100  # SHORT
            pnl_dollar = (pnl_pct / 100) * position_size
            equity += pnl_dollar

            # Track consecutive wins/losses
            if pnl_dollar > 0:
                consecutive_wins += 1
                consecutive_losses = 0
                max_consecutive_wins = max(max_consecutive_wins, consecutive_wins)
            else:
                consecutive_losses += 1
                consecutive_wins = 0
                max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)

            trades.append({
                'trade_num': len(trades) + 1,
                'signal_bar': signal_bar_idx,
                'armed_bar': signal_bar_idx,
                'limit_placed_bar': limit_placed_bar,
                'entry_bar': i,
                'exit_bar': exit_idx,
                'bars_waiting': bars_waiting,
                'signal_time': df.iloc[signal_bar_idx]['timestamp'],
                'entry_time': df.iloc[i]['timestamp'],
                'exit_time': df.iloc[exit_idx]['timestamp'],
                'rsi_at_signal': df.iloc[signal_bar_idx]['rsi'],
                'swing_low': swing_low,
                'limit_price': limit_price,
                'entry_price': entry_price,
                'sl_price': sl_price,
                'tp_price': tp_price,
                'exit_price': exit_price,
                'exit_type': exit_type,
                'position_size': position_size,
                'pnl_pct': pnl_pct,
                'pnl_dollar': pnl_dollar,
                'equity_before': equity - pnl_dollar,
                'equity_after': equity
            })

            # Reset state
            limit_pending = False
            armed = False
            signal_bar_idx = None
            swing_low = None
            continue

        # Check timeout
        bars_waiting = i - limit_placed_bar
        if bars_waiting > MAX_WAIT_BARS:
            limit_pending = False
            armed = False
            signal_bar_idx = None
            swing_low = None
            continue

    # Check for ARM signal
    if not armed and not limit_pending:
        if df.iloc[i]['rsi'] > RSI_TRIGGER:
            armed = True
            signal_bar_idx = i
            swing_low = df.iloc[i-LOOKBACK:i+1]['low'].min()
            continue

    # Check for support break
    if armed and not limit_pending:
        if df.iloc[i]['low'] < swing_low:
            limit_price = swing_low + (df.iloc[i]['atr'] * LIMIT_ATR_OFFSET)
            swing_high = df.iloc[signal_bar_idx:i+1]['high'].max()
            sl_price = swing_high
            tp_price = limit_price * (1 - TP_PCT / 100)

            sl_dist_pct = ((sl_price - limit_price) / limit_price) * 100

            if 0 < sl_dist_pct <= MAX_SL_PCT:
                position_size = (equity * (RISK_PCT / 100)) / (sl_dist_pct / 100)
                limit_pending = True
                limit_placed_bar = i
            else:
                armed = False
                signal_bar_idx = None
                swing_low = None

# Calculate statistics
df_trades = pd.DataFrame(trades)

if len(trades) > 0:
    total_return = ((equity - 100) / 100) * 100

    winners = df_trades[df_trades['pnl_dollar'] > 0]
    losers = df_trades[df_trades['pnl_dollar'] <= 0]

    win_rate = (len(winners) / len(trades)) * 100

    # Calculate max drawdown (CORRECTED METHOD)
    equity_curve = [100.0]
    for pnl in df_trades['pnl_dollar']:
        equity_curve.append(equity_curve[-1] + pnl)

    eq_series = pd.Series(equity_curve)
    running_max = eq_series.expanding().max()
    drawdown = (eq_series - running_max) / running_max * 100
    max_dd = drawdown.min()

    return_dd = total_return / abs(max_dd) if max_dd != 0 else 0

    print(f"\n{'='*80}")
    print("📊 MELANIA SHORT REVERSAL - DETAILED STATISTICS")
    print(f"{'='*80}")
    print(f"\n💰 Performance:")
    print(f"   Total Return: {total_return:+.2f}%")
    print(f"   Max Drawdown: {max_dd:.2f}%")
    print(f"   Return/DD Ratio: {return_dd:.2f}x")
    print(f"   Final Equity: ${equity:.2f}")

    print(f"\n📈 Trade Statistics:")
    print(f"   Total Trades: {len(trades)}")
    print(f"   Winners: {len(winners)} ({win_rate:.1f}%)")
    print(f"   Losers: {len(losers)} ({100-win_rate:.1f}%)")

    print(f"\n🔥 Streaks:")
    print(f"   Max Consecutive Wins: {max_consecutive_wins}")
    print(f"   Max Consecutive Losses: {max_consecutive_losses}")

    print(f"\n💵 P&L Breakdown:")
    print(f"   Avg Winner: {winners['pnl_pct'].mean():.2f}% (${winners['pnl_dollar'].mean():.2f})")
    print(f"   Avg Loser: {losers['pnl_pct'].mean():.2f}% (${losers['pnl_dollar'].mean():.2f})")
    print(f"   Best Trade: {df_trades['pnl_pct'].max():.2f}% (${df_trades['pnl_dollar'].max():.2f})")
    print(f"   Worst Trade: {df_trades['pnl_pct'].min():.2f}% (${df_trades['pnl_dollar'].min():.2f})")

    print(f"\n🎯 Exit Types:")
    print(f"   Take Profit: {len(df_trades[df_trades['exit_type']=='TP'])} ({len(df_trades[df_trades['exit_type']=='TP'])/len(trades)*100:.1f}%)")
    print(f"   Stop Loss: {len(df_trades[df_trades['exit_type']=='SL'])} ({len(df_trades[df_trades['exit_type']=='SL'])/len(trades)*100:.1f}%)")
    print(f"   Time Exit: {len(df_trades[df_trades['exit_type']=='TIME'])} ({len(df_trades[df_trades['exit_type']=='TIME'])/len(trades)*100:.1f}%)")

    print(f"\n⏱️ Trade Duration:")
    df_trades['duration_bars'] = df_trades['exit_bar'] - df_trades['entry_bar']
    print(f"   Avg Duration: {df_trades['duration_bars'].mean():.1f} bars ({df_trades['duration_bars'].mean()/4:.1f} hours)")
    print(f"   Min Duration: {df_trades['duration_bars'].min()} bars")
    print(f"   Max Duration: {df_trades['duration_bars'].max()} bars")

    # Monthly breakdown
    df_trades['month'] = pd.to_datetime(df_trades['entry_time']).dt.to_period('M')
    monthly = df_trades.groupby('month').agg({
        'pnl_dollar': ['sum', 'count'],
        'trade_num': 'count'
    })

    print(f"\n📅 Monthly Breakdown:")
    for month in monthly.index:
        month_trades = df_trades[df_trades['month'] == month]
        month_profit = month_trades['pnl_dollar'].sum()
        month_count = len(month_trades)
        month_win_rate = (len(month_trades[month_trades['pnl_dollar'] > 0]) / month_count * 100) if month_count > 0 else 0
        print(f"   {month}: {month_count} trades, ${month_profit:+.2f} ({month_win_rate:.1f}% win rate)")

    # Save trades
    df_trades.to_csv('melania_detailed_trades.csv', index=False)
    print(f"\n💾 Full trade log saved to: melania_detailed_trades.csv")

    print(f"\n{'='*80}")
    print("✅ MELANIA BACKTEST COMPLETE")
    print(f"{'='*80}")

else:
    print("\n❌ No trades generated")
