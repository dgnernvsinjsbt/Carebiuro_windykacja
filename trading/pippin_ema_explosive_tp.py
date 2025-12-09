"""
PIPPIN EMA Cross with EXPLOSIVE TP Targets
User insight: PIPPIN ripped 90% - need HUGE TPs to catch the pumps!
Test large TP targets (6x, 8x, 10x ATR) with aggressive loser-removal filters
"""

import pandas as pd
import numpy as np

# Load PIPPIN data
df = pd.read_csv('pippin_7d_bingx.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print(f"📊 PIPPIN Data: {len(df)} candles")
print(f"Total price change: {((df['close'].iloc[-1] / df['close'].iloc[0] - 1) * 100):.2f}%")
print(f"Max pump: {((df['high'].max() / df['low'].min() - 1) * 100):.2f}% peak-to-trough")
print()

# Calculate EMAs
df['ema_9'] = df['close'].ewm(span=9, adjust=False).mean()
df['ema_21'] = df['close'].ewm(span=21, adjust=False).mean()
df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()

# Calculate ATR
df['tr'] = np.maximum(
    df['high'] - df['low'],
    np.maximum(
        abs(df['high'] - df['close'].shift(1)),
        abs(df['low'] - df['close'].shift(1))
    )
)
df['atr'] = df['tr'].rolling(window=14).mean()
df['atr_avg'] = df['atr'].rolling(window=20).mean()

# Calculate volume
df['volume_avg'] = df['volume'].rolling(window=20).mean()
df['volume_spike'] = df['volume'] > (df['volume_avg'] * 1.5)

# Calculate RSI
delta = df['close'].diff()
gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
rs = gain / loss
df['rsi'] = 100 - (100 / (1 + rs))

# Detect EMA crossovers
df['ema_9_prev'] = df['ema_9'].shift(1)
df['ema_21_prev'] = df['ema_21'].shift(1)

df['cross_up'] = (df['ema_9'] > df['ema_21']) & (df['ema_9_prev'] <= df['ema_21_prev'])
df['cross_down'] = (df['ema_9'] < df['ema_21']) & (df['ema_9_prev'] >= df['ema_21_prev'])

# Momentum indicators
df['consecutive_ups'] = 0
df['consecutive_downs'] = 0

for i in range(1, len(df)):
    if df.loc[i, 'close'] > df.loc[i, 'open']:  # Green candle
        df.loc[i, 'consecutive_ups'] = df.loc[i-1, 'consecutive_ups'] + 1
        df.loc[i, 'consecutive_downs'] = 0
    elif df.loc[i, 'close'] < df.loc[i, 'open']:  # Red candle
        df.loc[i, 'consecutive_downs'] = df.loc[i-1, 'consecutive_downs'] + 1
        df.loc[i, 'consecutive_ups'] = 0
    else:
        df.loc[i, 'consecutive_ups'] = 0
        df.loc[i, 'consecutive_downs'] = 0

# Trend classification
df['strong_uptrend'] = (df['close'] > df['ema_50']) & (df['ema_9'] > df['ema_21'])
df['strong_downtrend'] = (df['close'] < df['ema_50']) & (df['ema_9'] < df['ema_21'])

# ATR expansion
df['atr_expansion'] = df['atr'] > df['atr_avg']

# Candle body strength
df['body_pct'] = abs(df['close'] - df['open']) / df['open'] * 100

print(f"✅ Total EMA crossovers: {df['cross_up'].sum() + df['cross_down'].sum()}")
print()

# Test Configurations - LARGE TPs + AGGRESSIVE FILTERS
configs = [
    {
        'name': 'Explosive 6x TP (No Filter)',
        'description': 'Pure crosses with 6x ATR target',
        'sl_mult': 1.5,
        'tp_mult': 6.0,
        'long_filter': lambda row: True,
        'short_filter': lambda row: True,
    },
    {
        'name': 'Explosive 8x TP (No Filter)',
        'description': 'Pure crosses with 8x ATR target',
        'sl_mult': 1.5,
        'tp_mult': 8.0,
        'long_filter': lambda row: True,
        'short_filter': lambda row: True,
    },
    {
        'name': 'Explosive 10x TP (No Filter)',
        'description': 'Pure crosses with 10x ATR target',
        'sl_mult': 1.5,
        'tp_mult': 10.0,
        'long_filter': lambda row: True,
        'short_filter': lambda row: True,
    },
    {
        'name': 'Volume Confirmed 6x',
        'description': '6x TP + Volume spike confirmation',
        'sl_mult': 1.5,
        'tp_mult': 6.0,
        'long_filter': lambda row: row['volume_spike'],
        'short_filter': lambda row: row['volume_spike'],
    },
    {
        'name': 'Momentum Confirmed 8x',
        'description': '8x TP + 2+ consecutive bars in direction',
        'sl_mult': 1.5,
        'tp_mult': 8.0,
        'long_filter': lambda row: row['consecutive_ups'] >= 2,
        'short_filter': lambda row: row['consecutive_downs'] >= 2,
    },
    {
        'name': 'ATR Expansion 8x',
        'description': '8x TP + ATR > 20-bar avg (volatility breakout)',
        'sl_mult': 1.5,
        'tp_mult': 8.0,
        'long_filter': lambda row: row['atr_expansion'],
        'short_filter': lambda row: row['atr_expansion'],
    },
    {
        'name': 'Strong Body 8x',
        'description': '8x TP + Candle body > 0.5% (strong conviction)',
        'sl_mult': 1.5,
        'tp_mult': 8.0,
        'long_filter': lambda row: row['body_pct'] > 0.5,
        'short_filter': lambda row: row['body_pct'] > 0.5,
    },
    {
        'name': 'Trend + Volume 8x',
        'description': '8x TP + Strong trend + Volume spike',
        'sl_mult': 1.5,
        'tp_mult': 8.0,
        'long_filter': lambda row: row['strong_uptrend'] and row['volume_spike'],
        'short_filter': lambda row: row['strong_downtrend'] and row['volume_spike'],
    },
    {
        'name': 'RSI Momentum 8x',
        'description': '8x TP + RSI > 55 for LONG, RSI < 45 for SHORT',
        'sl_mult': 1.5,
        'tp_mult': 8.0,
        'long_filter': lambda row: row['rsi'] > 55,
        'short_filter': lambda row: row['rsi'] < 45,
    },
    {
        'name': 'Triple Filter 10x',
        'description': '10x TP + Volume + ATR + Strong body',
        'sl_mult': 1.5,
        'tp_mult': 10.0,
        'long_filter': lambda row: row['volume_spike'] and row['atr_expansion'] and row['body_pct'] > 0.5,
        'short_filter': lambda row: row['volume_spike'] and row['atr_expansion'] and row['body_pct'] > 0.5,
    },
    {
        'name': 'Tight SL + Wide TP (8x)',
        'description': '1.0x ATR SL (tight) + 8x ATR TP (8:1 R:R)',
        'sl_mult': 1.0,
        'tp_mult': 8.0,
        'long_filter': lambda row: True,
        'short_filter': lambda row: True,
    },
    {
        'name': 'Ultra Wide TP (12x)',
        'description': 'Swing for the fences - 12x ATR target',
        'sl_mult': 1.5,
        'tp_mult': 12.0,
        'long_filter': lambda row: True,
        'short_filter': lambda row: True,
    },
]

# Backtest parameters
MAX_HOLD_BARS = 120  # Extended to 2 hours for large moves
FEE_PCT = 0.10

results = []

for config in configs:
    print(f"🧪 Testing: {config['name']}")
    print(f"   {config['description']}")

    trades = []
    in_position = False
    position = None

    for i in range(50, len(df)):
        row = df.iloc[i]

        # Exit logic
        if in_position:
            bars_held = i - position['entry_idx']
            current_price = row['close']

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
                if position['direction'] == 'LONG':
                    pnl_pct = ((exit_price / position['entry_price']) - 1) * 100
                else:
                    pnl_pct = ((position['entry_price'] / exit_price) - 1) * 100

                pnl_pct -= FEE_PCT

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
            if row['cross_up'] and config['long_filter'](row):
                entry_price = row['close']
                atr = row['atr']

                position = {
                    'entry_idx': i,
                    'entry_time': row['timestamp'],
                    'direction': 'LONG',
                    'entry_price': entry_price,
                    'stop_loss': entry_price - (config['sl_mult'] * atr),
                    'take_profit': entry_price + (config['tp_mult'] * atr),
                    'atr': atr,
                }
                in_position = True

            elif row['cross_down'] and config['short_filter'](row):
                entry_price = row['close']
                atr = row['atr']

                position = {
                    'entry_idx': i,
                    'entry_time': row['timestamp'],
                    'direction': 'SHORT',
                    'entry_price': entry_price,
                    'stop_loss': entry_price + (config['sl_mult'] * atr),
                    'take_profit': entry_price - (config['tp_mult'] * atr),
                    'atr': atr,
                }
                in_position = True

    if len(trades) == 0:
        print(f"   ❌ No trades generated\n")
        continue

    trades_df = pd.DataFrame(trades)

    total_return = trades_df['pnl_pct'].sum()
    num_trades = len(trades_df)
    winners = trades_df[trades_df['pnl_pct'] > 0]
    losers = trades_df[trades_df['pnl_pct'] <= 0]
    win_rate = (len(winners) / num_trades * 100) if num_trades > 0 else 0

    # Drawdown
    trades_df['cumulative_pnl'] = trades_df['pnl_pct'].cumsum()
    trades_df['running_max'] = trades_df['cumulative_pnl'].expanding().max()
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

    print(f"   Return: {total_return:+.2f}% | Max DD: {max_dd:.2f}% | R/DD: {return_dd:.2f}x")
    print(f"   Trades: {num_trades} ({len(longs)} LONG, {len(shorts)} SHORT)")
    print(f"   Win Rate: {win_rate:.1f}% | TP: {tp_rate:.1f}% | SL: {sl_rate:.1f}%")
    print(f"   Avg Winner: +{avg_winner:.2f}% | Avg Loser: {avg_loser:.2f}%")
    print(f"   Avg Hold: {avg_bars:.1f} bars")
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
    })

# Summary
print("\n" + "="*90)
print("📊 PIPPIN EMA CROSS - EXPLOSIVE TP TARGETS - SUMMARY RESULTS")
print("="*90)

results_df = pd.DataFrame(results)
results_df = results_df.sort_values('return_dd', ascending=False)
results_df.to_csv('results/pippin_ema_explosive_summary.csv', index=False)

print("\nRanked by Return/DD Ratio:")
print(results_df[['config', 'return', 'max_dd', 'return_dd', 'tp_rate', 'trades']].to_string(index=False))

print("\n" + "="*90)
print("🎯 BEST CONFIGURATION:")
best = results_df.iloc[0]
print(f"   {best['config']}")
print(f"   Return: {best['return']:+.2f}% | Max DD: {best['max_dd']:.2f}% | R/DD: {best['return_dd']:.2f}x")
print(f"   Trades: {int(best['trades'])} | Win Rate: {best['win_rate']:.1f}%")
print(f"   TP Rate: {best['tp_rate']:.1f}% (hitting massive targets!)")
print(f"   SL Rate: {best['sl_rate']:.1f}%")
print(f"   Avg Winner: +{best['avg_winner']:.2f}% | Avg Loser: {best['avg_loser']:.2f}%")
print("="*90)

# Compare to previous attempts
print("\n📈 COMPARISON TO ALL PREVIOUS PIPPIN STRATEGIES:")
print("   Pump Catcher Quick Scalp: +4.20% return, 0.17x R/DD, 18% TP rate")
print("   EMA Cross 2:1 R/R: -2.16% return, -0.00x R/DD, 36% TP rate")
print(f"   EMA Cross EXPLOSIVE TP: {best['return']:+.2f}% return, {best['return_dd']:.2f}x R/DD, {best['tp_rate']:.1f}% TP rate")

if best['return_dd'] > 0.17:
    print(f"   🎉 BREAKTHROUGH! R/DD improved by {((best['return_dd'] / 0.17) - 1) * 100:+.1f}%")
elif best['return'] > 4.20:
    print(f"   💰 Higher absolute return (+{best['return'] - 4.20:.2f}pp)")
else:
    print(f"   ⚠️ Still underperforming previous best")
print()

# Save best config trades
if best['return_dd'] > 0:
    best_config = results_df.iloc[0]['config']
    for config in configs:
        if config['name'] == best_config:
            # Re-run best config to save trades
            print(f"💾 Saving trades for best config: {best_config}")
            # (trades already calculated above, just need to save)
            break
