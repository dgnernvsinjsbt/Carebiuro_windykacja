"""
PIPPIN EMA Cross Strategy Test
Test 4 variants of EMA(9) x EMA(21) crossover strategy
Data: 7 days PIPPIN-USDT 1m from BingX Futures
"""

import pandas as pd
import numpy as np

# Load PIPPIN data
df = pd.read_csv('pippin_7d_bingx.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print(f"📊 PIPPIN Data: {len(df)} candles")
print(f"Period: {df['timestamp'].min()} to {df['timestamp'].max()}")
print(f"Price range: ${df['close'].min():.4f} - ${df['close'].max():.4f}")
print(f"Total price change: {((df['close'].iloc[-1] / df['close'].iloc[0] - 1) * 100):.2f}%")
print()

# Calculate EMAs
df['ema_9'] = df['close'].ewm(span=9, adjust=False).mean()
df['ema_21'] = df['close'].ewm(span=21, adjust=False).mean()
df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()

# Calculate ATR for stops/targets
df['tr'] = np.maximum(
    df['high'] - df['low'],
    np.maximum(
        abs(df['high'] - df['close'].shift(1)),
        abs(df['low'] - df['close'].shift(1))
    )
)
df['atr'] = df['tr'].rolling(window=14).mean()

# Calculate RSI
delta = df['close'].diff()
gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
rs = gain / loss
df['rsi'] = 100 - (100 / (1 + rs))

# Detect EMA crossovers
df['ema_9_prev'] = df['ema_9'].shift(1)
df['ema_21_prev'] = df['ema_21'].shift(1)

# LONG signal: EMA(9) crosses ABOVE EMA(21)
df['cross_up'] = (df['ema_9'] > df['ema_21']) & (df['ema_9_prev'] <= df['ema_21_prev'])

# SHORT signal: EMA(9) crosses BELOW EMA(21)
df['cross_down'] = (df['ema_9'] < df['ema_21']) & (df['ema_9_prev'] >= df['ema_21_prev'])

# Trend classification for filters
df['uptrend'] = df['close'] > df['ema_50']
df['downtrend'] = df['close'] < df['ema_50']

# ATR expansion filter
df['atr_avg'] = df['atr'].rolling(window=20).mean()
df['atr_expansion'] = df['atr'] > df['atr_avg']

print(f"✅ Total EMA crossovers detected: {df['cross_up'].sum() + df['cross_down'].sum()}")
print(f"   - Bullish crosses (9>21): {df['cross_up'].sum()}")
print(f"   - Bearish crosses (9<21): {df['cross_down'].sum()}")
print()

# Test Configurations
configs = [
    {
        'name': 'Pure Crosses',
        'description': 'No filters - every cross',
        'long_filter': lambda row: True,
        'short_filter': lambda row: True,
    },
    {
        'name': 'EMA50 Trend Filter',
        'description': 'LONG only above EMA50, SHORT only below',
        'long_filter': lambda row: row['uptrend'],
        'short_filter': lambda row: row['downtrend'],
    },
    {
        'name': 'RSI Filter (20-80)',
        'description': 'Avoid extreme RSI zones',
        'long_filter': lambda row: 20 < row['rsi'] < 80,
        'short_filter': lambda row: 20 < row['rsi'] < 80,
    },
    {
        'name': 'ATR Expansion Filter',
        'description': 'Only enter when ATR > 20-bar average',
        'long_filter': lambda row: row['atr_expansion'],
        'short_filter': lambda row: row['atr_expansion'],
    },
]

# Backtest parameters
SL_ATR_MULT = 1.5
TP_ATR_MULT = 3.0  # 2:1 R:R
MAX_HOLD_BARS = 60
FEE_PCT = 0.10  # 0.05% taker x2

results = []

for config in configs:
    print(f"🧪 Testing: {config['name']}")
    print(f"   {config['description']}")

    trades = []
    in_position = False
    position = None

    for i in range(50, len(df)):  # Start after EMAs warm up
        row = df.iloc[i]

        # Exit logic
        if in_position:
            bars_held = i - position['entry_idx']
            current_price = row['close']

            # Check exits
            hit_sl = False
            hit_tp = False
            time_exit = False

            if position['direction'] == 'LONG':
                if current_price <= position['stop_loss']:
                    hit_sl = True
                    exit_price = position['stop_loss']
                elif current_price >= position['take_profit']:
                    hit_tp = True
                    exit_price = position['take_profit']
                elif bars_held >= MAX_HOLD_BARS:
                    time_exit = True
                    exit_price = current_price
            else:  # SHORT
                if current_price >= position['stop_loss']:
                    hit_sl = True
                    exit_price = position['stop_loss']
                elif current_price <= position['take_profit']:
                    hit_tp = True
                    exit_price = position['take_profit']
                elif bars_held >= MAX_HOLD_BARS:
                    time_exit = True
                    exit_price = current_price

            if hit_sl or hit_tp or time_exit:
                # Calculate P&L
                if position['direction'] == 'LONG':
                    pnl_pct = ((exit_price / position['entry_price']) - 1) * 100
                else:  # SHORT
                    pnl_pct = ((position['entry_price'] / exit_price) - 1) * 100

                pnl_pct -= FEE_PCT  # Subtract fees

                trades.append({
                    'entry_time': position['entry_time'],
                    'exit_time': row['timestamp'],
                    'direction': position['direction'],
                    'entry_price': position['entry_price'],
                    'exit_price': exit_price,
                    'stop_loss': position['stop_loss'],
                    'take_profit': position['take_profit'],
                    'bars_held': bars_held,
                    'pnl_pct': pnl_pct,
                    'exit_reason': 'SL' if hit_sl else ('TP' if hit_tp else 'Time'),
                })

                in_position = False
                position = None

        # Entry logic
        if not in_position:
            # Check LONG entry
            if row['cross_up'] and config['long_filter'](row):
                entry_price = row['close']
                atr = row['atr']

                position = {
                    'entry_idx': i,
                    'entry_time': row['timestamp'],
                    'direction': 'LONG',
                    'entry_price': entry_price,
                    'stop_loss': entry_price - (SL_ATR_MULT * atr),
                    'take_profit': entry_price + (TP_ATR_MULT * atr),
                    'atr': atr,
                }
                in_position = True

            # Check SHORT entry
            elif row['cross_down'] and config['short_filter'](row):
                entry_price = row['close']
                atr = row['atr']

                position = {
                    'entry_idx': i,
                    'entry_time': row['timestamp'],
                    'direction': 'SHORT',
                    'entry_price': entry_price,
                    'stop_loss': entry_price + (SL_ATR_MULT * atr),
                    'take_profit': entry_price - (TP_ATR_MULT * atr),
                    'atr': atr,
                }
                in_position = True

    # Calculate metrics
    if len(trades) == 0:
        print(f"   ❌ No trades generated\n")
        continue

    trades_df = pd.DataFrame(trades)

    total_return = trades_df['pnl_pct'].sum()
    num_trades = len(trades_df)
    winners = trades_df[trades_df['pnl_pct'] > 0]
    losers = trades_df[trades_df['pnl_pct'] <= 0]
    win_rate = (len(winners) / num_trades * 100) if num_trades > 0 else 0

    # Calculate drawdown
    trades_df['cumulative_pnl'] = trades_df['pnl_pct'].cumsum()
    trades_df['running_max'] = trades_df['cumulative_pnl'].cumsum().expanding().max()
    trades_df['drawdown'] = trades_df['cumulative_pnl'] - trades_df['running_max']
    max_dd = trades_df['drawdown'].min()

    return_dd = total_return / abs(max_dd) if max_dd != 0 else 0

    # Exit reasons
    tp_count = len(trades_df[trades_df['exit_reason'] == 'TP'])
    sl_count = len(trades_df[trades_df['exit_reason'] == 'SL'])
    time_count = len(trades_df[trades_df['exit_reason'] == 'Time'])

    tp_rate = (tp_count / num_trades * 100) if num_trades > 0 else 0
    sl_rate = (sl_count / num_trades * 100) if num_trades > 0 else 0

    avg_winner = winners['pnl_pct'].mean() if len(winners) > 0 else 0
    avg_loser = losers['pnl_pct'].mean() if len(losers) > 0 else 0
    avg_bars = trades_df['bars_held'].mean()

    # Direction breakdown
    longs = trades_df[trades_df['direction'] == 'LONG']
    shorts = trades_df[trades_df['direction'] == 'SHORT']
    long_wr = (len(longs[longs['pnl_pct'] > 0]) / len(longs) * 100) if len(longs) > 0 else 0
    short_wr = (len(shorts[shorts['pnl_pct'] > 0]) / len(shorts) * 100) if len(shorts) > 0 else 0

    print(f"   Return: {total_return:+.2f}% | Max DD: {max_dd:.2f}% | R/DD: {return_dd:.2f}x")
    print(f"   Trades: {num_trades} ({len(longs)} LONG, {len(shorts)} SHORT)")
    print(f"   Win Rate: {win_rate:.1f}% | TP: {tp_rate:.1f}% | SL: {sl_rate:.1f}%")
    print(f"   Avg Winner: +{avg_winner:.2f}% | Avg Loser: {avg_loser:.2f}%")
    print(f"   Avg Hold: {avg_bars:.1f} bars ({avg_bars:.1f} min)")
    print(f"   LONG WR: {long_wr:.1f}% | SHORT WR: {short_wr:.1f}%")
    print()

    results.append({
        'config': config['name'],
        'return': total_return,
        'max_dd': max_dd,
        'return_dd': return_dd,
        'trades': num_trades,
        'win_rate': win_rate,
        'tp_rate': tp_rate,
        'sl_rate': sl_rate,
        'avg_winner': avg_winner,
        'avg_loser': avg_loser,
        'avg_bars': avg_bars,
        'longs': len(longs),
        'shorts': len(shorts),
        'long_wr': long_wr,
        'short_wr': short_wr,
    })

    # Save best config trades
    if config['name'] == 'Pure Crosses' or return_dd > 2.0:
        trades_df.to_csv(f'results/pippin_ema_{config["name"].lower().replace(" ", "_")}_trades.csv', index=False)

# Summary table
print("\n" + "="*80)
print("📊 PIPPIN EMA CROSS STRATEGY - SUMMARY RESULTS")
print("="*80)

results_df = pd.DataFrame(results)
results_df = results_df.sort_values('return_dd', ascending=False)
results_df.to_csv('results/pippin_ema_cross_summary.csv', index=False)

print("\nRanked by Return/DD Ratio:")
print(results_df[['config', 'return', 'max_dd', 'return_dd', 'win_rate', 'trades']].to_string(index=False))

print("\n" + "="*80)
print("🎯 BEST CONFIGURATION:")
best = results_df.iloc[0]
print(f"   {best['config']}")
print(f"   Return: {best['return']:+.2f}% | Max DD: {best['max_dd']:.2f}% | R/DD: {best['return_dd']:.2f}x")
print(f"   Trades: {int(best['trades'])} | Win Rate: {best['win_rate']:.1f}%")
print(f"   TP Rate: {best['tp_rate']:.1f}% | SL Rate: {best['sl_rate']:.1f}%")
print(f"   Avg Winner: +{best['avg_winner']:.2f}% | Avg Loser: {best['avg_loser']:.2f}%")
print(f"   LONG: {int(best['longs'])} trades ({best['long_wr']:.1f}% WR)")
print(f"   SHORT: {int(best['shorts'])} trades ({best['short_wr']:.1f}% WR)")
print("="*80)

# Compare to previous best (Pump Catcher)
print("\n📈 COMPARISON TO PREVIOUS BEST PIPPIN STRATEGY:")
print("   Pump Catcher Quick Scalp: +4.20% return, 0.17x R/DD, 318 trades")
print(f"   EMA Cross {best['config']}: {best['return']:+.2f}% return, {best['return_dd']:.2f}x R/DD, {int(best['trades'])} trades")
if best['return_dd'] > 0.17:
    improvement = ((best['return_dd'] / 0.17) - 1) * 100
    print(f"   🎉 IMPROVEMENT: {improvement:+.1f}% better R/DD!")
print()
