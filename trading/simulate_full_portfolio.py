#!/usr/bin/env python3
"""Simulate full portfolio: All 4 coins combined, chronologically sorted, $100 start"""
import pandas as pd
import numpy as np

def get_all_trades(csv_file, rsi_trigger, limit_atr_offset, tp_pct, coin_name):
    """Get all trades for a coin with timestamps"""
    df = pd.read_csv(csv_file)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)

    # Calculate RSI
    delta = df['close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))

    # Calculate ATR
    df['tr'] = np.maximum(df['high'] - df['low'], np.maximum(
        abs(df['high'] - df['close'].shift(1)),
        abs(df['low'] - df['close'].shift(1))
    ))
    df['atr'] = df['tr'].rolling(14).mean()

    lookback = 5
    max_wait_bars = 20
    trades = []
    armed = False
    signal_idx = None
    swing_low = None
    limit_pending = False
    limit_placed_idx = None
    swing_high_for_sl = None

    for i in range(lookback, len(df)):
        row = df.iloc[i]
        if pd.isna(row['rsi']) or pd.isna(row['atr']):
            continue

        if row['rsi'] > rsi_trigger:
            armed = True
            signal_idx = i
            swing_low = df.iloc[max(0, i-lookback):i+1]['low'].min()
            limit_pending = False

        if armed and swing_low is not None and not limit_pending:
            if row['low'] < swing_low:
                atr = row['atr']
                limit_price = swing_low + (atr * limit_atr_offset)
                swing_high_for_sl = df.iloc[signal_idx:i+1]['high'].max()
                limit_pending = True
                limit_placed_idx = i
                armed = False

        if limit_pending:
            if i - limit_placed_idx > max_wait_bars:
                limit_pending = False
                continue

            if row['high'] >= limit_price:
                entry_price = limit_price
                sl_price = swing_high_for_sl
                tp_price = entry_price * (1 - tp_pct / 100)
                sl_dist_pct = ((sl_price - entry_price) / entry_price) * 100

                if sl_dist_pct <= 0 or sl_dist_pct > 10:
                    limit_pending = False
                    continue

                hit_sl = False
                hit_tp = False

                for j in range(i + 1, min(i + 500, len(df))):
                    future_row = df.iloc[j]
                    if future_row['high'] >= sl_price:
                        hit_sl = True
                        exit_time = future_row['timestamp']
                        break
                    elif future_row['low'] <= tp_price:
                        hit_tp = True
                        exit_time = future_row['timestamp']
                        break

                if hit_sl:
                    pnl_pct = -sl_dist_pct
                elif hit_tp:
                    pnl_pct = tp_pct
                else:
                    continue

                trades.append({
                    'coin': coin_name,
                    'signal_time': df.iloc[signal_idx]['timestamp'],
                    'entry_time': row['timestamp'],
                    'exit_time': exit_time,
                    'sl_dist_pct': sl_dist_pct,
                    'pnl_pct': pnl_pct,
                    'result': 'WIN' if pnl_pct > 0 else 'LOSS'
                })
                limit_pending = False

    return trades

print("Getting all trades from each coin...")
print("  FARTCOIN (RSI>70, 1.0ATR, 10%TP)...")
fartcoin_trades = get_all_trades('fartcoin_6months_bingx_15m.csv', 70, 1.0, 10, 'FARTCOIN')

print("  MOODENG (RSI>70, 0.8ATR, 8%TP)...")
moodeng_trades = get_all_trades('moodeng_6months_bingx_15m.csv', 70, 0.8, 8, 'MOODENG')

print("  MELANIA (RSI>72, 0.8ATR, 10%TP)...")
melania_trades = get_all_trades('melania_6months_bingx.csv', 72, 0.8, 10, 'MELANIA')

print("  DOGE (RSI>72, 0.6ATR, 6%TP)...")
doge_trades = get_all_trades('doge_6months_bingx_15m.csv', 72, 0.6, 6, 'DOGE')

# Combine all trades
all_trades = fartcoin_trades + moodeng_trades + melania_trades + doge_trades
all_trades_df = pd.DataFrame(all_trades)
all_trades_df = all_trades_df.sort_values('signal_time').reset_index(drop=True)

print(f"\nTotal trades across all coins: {len(all_trades_df)}")
print(f"  FARTCOIN: {len(fartcoin_trades)}")
print(f"  MOODENG: {len(moodeng_trades)}")
print(f"  MELANIA: {len(melania_trades)}")
print(f"  DOGE: {len(doge_trades)}")

# Simulate portfolio with $100 start, 5% risk per trade, full compounding
equity = 100.0
equity_curve = [100.0]
all_trades_df['equity_before'] = 0.0
all_trades_df['position_size'] = 0.0
all_trades_df['pnl_dollar'] = 0.0
all_trades_df['equity_after'] = 0.0

for i in range(len(all_trades_df)):
    trade = all_trades_df.iloc[i]

    # Calculate position size based on 5% risk
    risk_amount = equity * 0.05
    sl_dist_pct = trade['sl_dist_pct']
    position_size = risk_amount / (sl_dist_pct / 100)

    # Calculate P&L in dollars
    pnl_pct = trade['pnl_pct']
    pnl_dollar = position_size * (pnl_pct / 100) - position_size * 0.001  # 0.1% fees

    # Update equity
    all_trades_df.loc[i, 'equity_before'] = equity
    all_trades_df.loc[i, 'position_size'] = position_size
    all_trades_df.loc[i, 'pnl_dollar'] = pnl_dollar
    equity += pnl_dollar
    all_trades_df.loc[i, 'equity_after'] = equity
    equity_curve.append(equity)

# Calculate metrics
final_equity = equity
total_return = ((final_equity - 100) / 100) * 100

# Max drawdown
equity_series = pd.Series(equity_curve)
running_max = equity_series.expanding().max()
drawdown = (equity_series - running_max) / running_max * 100
max_dd = drawdown.min()
max_dd_idx = drawdown.idxmin()
max_dd_date = all_trades_df.iloc[max_dd_idx-1]['signal_time'] if max_dd_idx > 0 else all_trades_df.iloc[0]['signal_time']

return_dd = total_return / abs(max_dd) if max_dd != 0 else 0

# Win rate
winners = all_trades_df[all_trades_df['pnl_dollar'] > 0]
win_rate = len(winners) / len(all_trades_df) * 100

# Monthly breakdown
all_trades_df['month'] = pd.to_datetime(all_trades_df['signal_time']).dt.to_period('M')
monthly_trades = all_trades_df.groupby('month').agg({
    'pnl_dollar': ['sum', 'count'],
    'coin': lambda x: list(x)
}).reset_index()
monthly_trades.columns = ['month', 'pnl', 'trades', 'coins']

# Profit by coin
coin_pnl = all_trades_df.groupby('coin')['pnl_dollar'].agg(['sum', 'count']).reset_index()
coin_pnl.columns = ['coin', 'total_pnl', 'trades']
coin_pnl = coin_pnl.sort_values('total_pnl', ascending=False)

# Best and worst trades
best_trade = all_trades_df.loc[all_trades_df['pnl_dollar'].idxmax()]
worst_trade = all_trades_df.loc[all_trades_df['pnl_dollar'].idxmin()]

# Print results
print("\n" + "="*100)
print("FULL PORTFOLIO SIMULATION - ALL 4 COINS COMBINED")
print("="*100)
print(f"Starting Capital: $100.00")
print(f"Risk Per Trade: 5% of current equity")
print(f"Compounding: YES (reinvest all profits)")
print(f"Fees: 0.1% round-trip per trade")
print(f"Date Range: {all_trades_df['signal_time'].min().date()} to {all_trades_df['signal_time'].max().date()}")

print(f"\n{'='*100}")
print("PERFORMANCE SUMMARY")
print(f"{'='*100}")
print(f"Final Equity: ${final_equity:,.2f}")
print(f"Total Return: {total_return:+,.2f}%")
print(f"Max Drawdown: {max_dd:.2f}% (on {max_dd_date.date()})")
print(f"Return/DD Ratio: {return_dd:.2f}x")
print(f"Total Trades: {len(all_trades_df)}")
print(f"Win Rate: {win_rate:.1f}% ({len(winners)} wins / {len(all_trades_df)-len(winners)} losses)")
print(f"Avg Trade: ${all_trades_df['pnl_dollar'].mean():+.2f}")
print(f"Best Trade: ${best_trade['pnl_dollar']:+.2f} ({best_trade['coin']} on {best_trade['signal_time'].date()})")
print(f"Worst Trade: ${worst_trade['pnl_dollar']:+.2f} ({worst_trade['coin']} on {worst_trade['signal_time'].date()})")

print(f"\n{'='*100}")
print("PROFIT CONTRIBUTION BY COIN")
print(f"{'='*100}")
for _, row in coin_pnl.iterrows():
    pct_of_total = (row['total_pnl'] / (final_equity - 100)) * 100
    print(f"{row['coin']:<12} ${row['total_pnl']:>10.2f} ({row['trades']:>3} trades) | {pct_of_total:>6.1f}% of total profit")

print(f"\n{'='*100}")
print("MONTHLY BREAKDOWN")
print(f"{'='*100}")
print(f"{'Month':<12} {'Trades':>7} {'P&L':>12} {'Cumulative':>12}")
print("-"*100)
cumulative = 100.0
for _, row in monthly_trades.iterrows():
    cumulative += row['pnl']
    status = "✓" if row['pnl'] > 0 else "✗"
    print(f"{str(row['month']):<12} {status} {row['trades']:>5} ${row['pnl']:>11.2f} ${cumulative:>11.2f}")

print(f"\n{'='*100}")
print("TOP 10 BEST TRADES")
print(f"{'='*100}")
top_trades = all_trades_df.nlargest(10, 'pnl_dollar')[['coin', 'signal_time', 'pnl_dollar', 'pnl_pct', 'equity_before', 'equity_after']]
for i, (_, trade) in enumerate(top_trades.iterrows(), 1):
    print(f"#{i:>2} {trade['coin']:<12} {trade['signal_time'].date()} | ${trade['pnl_dollar']:>8.2f} ({trade['pnl_pct']:>+5.1f}%) | Equity: ${trade['equity_before']:.2f} → ${trade['equity_after']:.2f}")

print(f"\n{'='*100}")
print("TOP 10 WORST TRADES")
print(f"{'='*100}")
worst_trades = all_trades_df.nsmallest(10, 'pnl_dollar')[['coin', 'signal_time', 'pnl_dollar', 'pnl_pct', 'equity_before', 'equity_after']]
for i, (_, trade) in enumerate(worst_trades.iterrows(), 1):
    print(f"#{i:>2} {trade['coin']:<12} {trade['signal_time'].date()} | ${trade['pnl_dollar']:>8.2f} ({trade['pnl_pct']:>+5.1f}%) | Equity: ${trade['equity_before']:.2f} → ${trade['equity_after']:.2f}")

# Save full trade log
all_trades_df.to_csv('full_portfolio_trade_log.csv', index=False)
print(f"\n✅ Full trade log saved to: full_portfolio_trade_log.csv")
print(f"✅ Total rows: {len(all_trades_df)}")
