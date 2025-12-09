"""
PIPPIN EMA Cross 10x TP - ULTRA AGGRESSIVE FILTERS
Goal: Keep the 24 TP winners, cut out the 136 SL losers!

Current: 184 trades, 23.9% WR, 73.9% SL rate
Target: <100 trades, >35% WR, <60% SL rate
"""

import pandas as pd
import numpy as np

# Load PIPPIN data
df = pd.read_csv('pippin_7d_bingx.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print(f"📊 PIPPIN Data: {len(df)} candles")
print(f"Total price change: {((df['close'].iloc[-1] / df['close'].iloc[0] - 1) * 100):.2f}%")
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
df['atr_expansion'] = df['atr'] > df['atr_avg']
df['atr_strong_expansion'] = df['atr'] > (df['atr_avg'] * 1.2)  # 20% above avg

# Calculate volume
df['volume_avg'] = df['volume'].rolling(window=20).mean()
df['volume_spike'] = df['volume'] > (df['volume_avg'] * 1.5)
df['volume_strong_spike'] = df['volume'] > (df['volume_avg'] * 2.0)  # 2x avg

# Calculate RSI
delta = df['close'].diff()
gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
rs = gain / loss
df['rsi'] = 100 - (100 / (1 + rs))

# Detect crossovers
df['ema_9_prev'] = df['ema_9'].shift(1)
df['ema_21_prev'] = df['ema_21'].shift(1)

df['cross_up'] = (df['ema_9'] > df['ema_21']) & (df['ema_9_prev'] <= df['ema_21_prev'])
df['cross_down'] = (df['ema_9'] < df['ema_21']) & (df['ema_9_prev'] >= df['ema_21_prev'])

# Consecutive candles (momentum confirmation)
df['consecutive_ups'] = 0
df['consecutive_downs'] = 0

for i in range(1, len(df)):
    if df.loc[i, 'close'] > df.loc[i, 'open']:  # Green
        df.loc[i, 'consecutive_ups'] = df.loc[i-1, 'consecutive_ups'] + 1
        df.loc[i, 'consecutive_downs'] = 0
    elif df.loc[i, 'close'] < df.loc[i, 'open']:  # Red
        df.loc[i, 'consecutive_downs'] = df.loc[i-1, 'consecutive_downs'] + 1
        df.loc[i, 'consecutive_ups'] = 0
    else:
        df.loc[i, 'consecutive_ups'] = 0
        df.loc[i, 'consecutive_downs'] = 0

# Candle body strength
df['body_pct'] = abs(df['close'] - df['open']) / df['open'] * 100

# Trend strength
df['strong_uptrend'] = (df['close'] > df['ema_50']) & (df['ema_9'] > df['ema_21']) & (df['ema_21'] > df['ema_50'])
df['strong_downtrend'] = (df['close'] < df['ema_50']) & (df['ema_9'] < df['ema_21']) & (df['ema_21'] < df['ema_50'])

# Distance from EMA50 (avoid overextended)
df['ema50_dist_pct'] = abs(df['close'] - df['ema_50']) / df['ema_50'] * 100
df['not_overextended'] = df['ema50_dist_pct'] < 5.0  # Within 5% of EMA50

print(f"✅ Total EMA crossovers: {df['cross_up'].sum() + df['cross_down'].sum()}")
print()

# ULTRA AGGRESSIVE FILTER CONFIGURATIONS
configs = [
    {
        'name': '3 Bars + Volume',
        'description': '3+ consecutive bars + volume spike',
        'sl_mult': 1.5,
        'tp_mult': 10.0,
        'long_filter': lambda row: row['consecutive_ups'] >= 3 and row['volume_spike'],
        'short_filter': lambda row: row['consecutive_downs'] >= 3 and row['volume_spike'],
    },
    {
        'name': '4 Bars Momentum',
        'description': '4+ consecutive bars (extreme momentum)',
        'sl_mult': 1.5,
        'tp_mult': 10.0,
        'long_filter': lambda row: row['consecutive_ups'] >= 4,
        'short_filter': lambda row: row['consecutive_downs'] >= 4,
    },
    {
        'name': 'ATR + Volume + Body',
        'description': 'ATR expansion + volume spike + strong body',
        'sl_mult': 1.5,
        'tp_mult': 10.0,
        'long_filter': lambda row: row['atr_expansion'] and row['volume_spike'] and row['body_pct'] > 0.5,
        'short_filter': lambda row: row['atr_expansion'] and row['volume_spike'] and row['body_pct'] > 0.5,
    },
    {
        'name': 'Strong Trend + Volume',
        'description': 'All EMAs aligned + volume spike',
        'sl_mult': 1.5,
        'tp_mult': 10.0,
        'long_filter': lambda row: row['strong_uptrend'] and row['volume_spike'],
        'short_filter': lambda row: row['strong_downtrend'] and row['volume_spike'],
    },
    {
        'name': 'Quad Filter',
        'description': 'ATR + Volume + Body + Trend aligned',
        'sl_mult': 1.5,
        'tp_mult': 10.0,
        'long_filter': lambda row: row['atr_expansion'] and row['volume_spike'] and row['body_pct'] > 0.5 and row['strong_uptrend'],
        'short_filter': lambda row: row['atr_expansion'] and row['volume_spike'] and row['body_pct'] > 0.5 and row['strong_downtrend'],
    },
    {
        'name': 'Strong ATR + Strong Vol',
        'description': 'ATR 1.2x avg + Volume 2x avg (extreme conditions)',
        'sl_mult': 1.5,
        'tp_mult': 10.0,
        'long_filter': lambda row: row['atr_strong_expansion'] and row['volume_strong_spike'],
        'short_filter': lambda row: row['atr_strong_expansion'] and row['volume_strong_spike'],
    },
    {
        'name': 'RSI Extreme + Volume',
        'description': 'RSI > 60 for LONG or < 40 for SHORT + volume',
        'sl_mult': 1.5,
        'tp_mult': 10.0,
        'long_filter': lambda row: row['rsi'] > 60 and row['volume_spike'],
        'short_filter': lambda row: row['rsi'] < 40 and row['volume_spike'],
    },
    {
        'name': '3 Bars + ATR + Volume',
        'description': 'Triple stack: momentum + volatility + volume',
        'sl_mult': 1.5,
        'tp_mult': 10.0,
        'long_filter': lambda row: row['consecutive_ups'] >= 3 and row['atr_expansion'] and row['volume_spike'],
        'short_filter': lambda row: row['consecutive_downs'] >= 3 and row['atr_expansion'] and row['volume_spike'],
    },
    {
        'name': 'Body + Not Overextended',
        'description': 'Strong body + within 5% of EMA50',
        'sl_mult': 1.5,
        'tp_mult': 10.0,
        'long_filter': lambda row: row['body_pct'] > 0.8 and row['not_overextended'],
        'short_filter': lambda row: row['body_pct'] > 0.8 and row['not_overextended'],
    },
    {
        'name': 'Mega Filter (All 5)',
        'description': '3+ bars + ATR + Volume + Body + Trend',
        'sl_mult': 1.5,
        'tp_mult': 10.0,
        'long_filter': lambda row: row['consecutive_ups'] >= 3 and row['atr_expansion'] and row['volume_spike'] and row['body_pct'] > 0.5 and row['strong_uptrend'],
        'short_filter': lambda row: row['consecutive_downs'] >= 3 and row['atr_expansion'] and row['volume_spike'] and row['body_pct'] > 0.5 and row['strong_downtrend'],
    },
    {
        'name': '2 Bars + Strong Vol',
        'description': '2+ consecutive + volume 2x avg',
        'sl_mult': 1.5,
        'tp_mult': 10.0,
        'long_filter': lambda row: row['consecutive_ups'] >= 2 and row['volume_strong_spike'],
        'short_filter': lambda row: row['consecutive_downs'] >= 2 and row['volume_strong_spike'],
    },
    {
        'name': 'Strong Body + Strong ATR',
        'description': 'Body > 1% + ATR 1.2x avg',
        'sl_mult': 1.5,
        'tp_mult': 10.0,
        'long_filter': lambda row: row['body_pct'] > 1.0 and row['atr_strong_expansion'],
        'short_filter': lambda row: row['body_pct'] > 1.0 and row['atr_strong_expansion'],
    },
]

# Backtest
MAX_HOLD_BARS = 120
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
            else:
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
        print(f"   ❌ No trades generated (filters too strict)\n")
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

    tp_rate = (tp_count / num_trades * 100) if num_trades > 0 else 0
    sl_rate = (sl_count / num_trades * 100) if num_trades > 0 else 0

    avg_winner = winners['pnl_pct'].mean() if len(winners) > 0 else 0
    avg_loser = losers['pnl_pct'].mean() if len(losers) > 0 else 0

    # Direction
    longs = trades_df[trades_df['direction'] == 'LONG']
    shorts = trades_df[trades_df['direction'] == 'SHORT']

    print(f"   Return: {total_return:+.2f}% | Max DD: {max_dd:.2f}% | R/DD: {return_dd:.2f}x")
    print(f"   Trades: {num_trades} ({len(longs)} LONG, {len(shorts)} SHORT)")
    print(f"   Win Rate: {win_rate:.1f}% | TP: {tp_rate:.1f}% | SL: {sl_rate:.1f}%")
    print(f"   Avg Winner: +{avg_winner:.2f}% | Avg Loser: {avg_loser:.2f}%")
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
        'longs': len(longs),
        'shorts': len(shorts),
    })

# Summary
print("\n" + "="*90)
print("📊 PIPPIN EMA CROSS 10x TP - ULTRA FILTERED - SUMMARY")
print("="*90)

results_df = pd.DataFrame(results)
results_df = results_df.sort_values('return_dd', ascending=False)
results_df.to_csv('results/pippin_ema_ultra_filtered_summary.csv', index=False)

print("\nRanked by Return/DD Ratio:")
print(results_df[['config', 'return', 'return_dd', 'win_rate', 'tp_rate', 'sl_rate', 'trades']].to_string(index=False))

print("\n" + "="*90)
if len(results_df) > 0:
    print("🎯 BEST ULTRA-FILTERED CONFIG:")
    best = results_df.iloc[0]
    print(f"   {best['config']}")
    print(f"   Return: {best['return']:+.2f}% | Max DD: {best['max_dd']:.2f}% | R/DD: {best['return_dd']:.2f}x")
    print(f"   Trades: {int(best['trades'])} (vs 184 unfiltered)")
    print(f"   Win Rate: {best['win_rate']:.1f}% (vs 23.9% unfiltered)")
    print(f"   TP Rate: {best['tp_rate']:.1f}% (vs 13.0% unfiltered)")
    print(f"   SL Rate: {best['sl_rate']:.1f}% (vs 73.9% unfiltered) ✅")
    print("="*90)

    print("\n📈 IMPROVEMENT OVER UNFILTERED:")
    print(f"   Trades reduced: 184 → {int(best['trades'])} ({((1 - best['trades']/184) * 100):.1f}% fewer)")
    print(f"   Win rate: 23.9% → {best['win_rate']:.1f}% ({best['win_rate'] - 23.9:+.1f}pp)")
    print(f"   SL rate: 73.9% → {best['sl_rate']:.1f}% ({best['sl_rate'] - 73.9:+.1f}pp)")
    print(f"   R/DD: 2.18x → {best['return_dd']:.2f}x ({best['return_dd'] - 2.18:+.2f}x)")

    if best['return_dd'] > 2.18:
        print(f"\n   🎉 FILTERS IMPROVED R/DD by {((best['return_dd'] / 2.18) - 1) * 100:+.1f}%!")

    if best['return_dd'] >= 3.0:
        print(f"\n   ✅ DEPLOYMENT READY! R/DD {best['return_dd']:.2f}x exceeds 3.0x threshold")
print()
