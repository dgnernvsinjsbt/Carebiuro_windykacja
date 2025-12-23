#!/usr/bin/env python3
"""
Debug why August failed (-65.6%) when market was down -13.3%
Compare Aug vs Oct/Nov characteristics
"""
import pandas as pd
import numpy as np

df = pd.read_csv('penguusdt_6months_bingx_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# ATR
high_low = df['high'] - df['low']
high_close = abs(df['high'] - df['close'].shift())
low_close = abs(df['low'] - df['close'].shift())
tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
df['atr'] = tr.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
df['atr_pct'] = (df['atr'] / df['close']) * 100

df['month'] = df['timestamp'].dt.to_period('M')

print("="*120)
print("DEBUGGING AUGUST FAILURE vs OCT/NOV SUCCESS")
print("="*120)
print()

# Analyze Aug, Oct, Nov
months_to_analyze = ['2025-08', '2025-10', '2025-11']

for month_str in months_to_analyze:
    df_month = df[df['month'] == month_str].copy().reset_index(drop=True)

    if len(df_month) == 0:
        continue

    print(f"{'='*120}")
    print(f"{month_str}")
    print(f"{'='*120}")

    # Market stats
    month_start = df_month.iloc[0]['close']
    month_end = df_month.iloc[-1]['close']
    market_return = ((month_end - month_start) / month_start) * 100
    avg_atr = df_month['atr_pct'].mean()

    print(f"\n📊 Market Characteristics:")
    print(f"   Market Return: {market_return:+.1f}%")
    print(f"   Avg ATR: {avg_atr:.2f}%")
    print(f"   Start Price: ${month_start:.6f}")
    print(f"   End Price: ${month_end:.6f}")

    # Backtest with detailed tracking
    threshold = -2.5
    lookback_bars = 32
    tp_pct = 5.0
    max_sl_pct = 3.0
    risk_pct = 5.0

    equity = 100.0
    trades = []

    for i in range(lookback_bars, len(df_month)):
        row = df_month.iloc[i]

        if pd.isna(row['atr']):
            continue

        high_8h = df_month.iloc[max(0, i-lookback_bars):i]['high'].max()
        dist_pct = ((row['close'] - high_8h) / high_8h) * 100

        if dist_pct > threshold:
            continue

        entry_price = row['close']
        sl_price = high_8h
        sl_dist_pct = ((sl_price - entry_price) / entry_price) * 100

        if sl_dist_pct <= 0 or sl_dist_pct > max_sl_pct:
            continue

        tp_price = entry_price * (1 - tp_pct / 100)
        position_size = (equity * (risk_pct / 100)) / (sl_dist_pct / 100)

        # Track distance to TP and SL
        max_favorable = 0
        hit_sl = False
        hit_tp = False
        bars_held = 0

        for j in range(i + 1, min(i + 100, len(df_month))):
            future_row = df_month.iloc[j]
            bars_held += 1

            # Track max favorable move
            current_profit_pct = ((entry_price - future_row['low']) / entry_price) * 100
            max_favorable = max(max_favorable, current_profit_pct)

            if future_row['high'] >= sl_price:
                hit_sl = True
                break
            elif future_row['low'] <= tp_price:
                hit_tp = True
                break

        if not (hit_sl or hit_tp):
            continue

        pnl_pct = tp_pct if hit_tp else -sl_dist_pct
        pnl_dollar = position_size * (pnl_pct / 100)
        equity += pnl_dollar

        trades.append({
            'pnl_pct': pnl_pct,
            'pnl_dollar': pnl_dollar,
            'hit_tp': hit_tp,
            'sl_dist_pct': sl_dist_pct,
            'max_favorable': max_favorable,
            'bars_held': bars_held,
            'reached_tp': max_favorable >= tp_pct
        })

    if len(trades) > 0:
        trades_df = pd.DataFrame(trades)
        total_return = ((equity - 100) / 100) * 100

        winners = trades_df[trades_df['pnl_dollar'] > 0]
        losers = trades_df[trades_df['pnl_dollar'] < 0]
        win_rate = (len(winners) / len(trades_df)) * 100

        # Analyze "almosts" - trades that reached TP but hit SL
        almost_winners = losers[losers['reached_tp'] == True]

        print(f"\n📈 Trading Results:")
        print(f"   Total Return: {total_return:+.1f}%")
        print(f"   Total Trades: {len(trades_df)}")
        print(f"   Winners: {len(winners)} ({win_rate:.1f}%)")
        print(f"   Losers: {len(losers)}")
        print(f"   Avg SL Distance: {trades_df['sl_dist_pct'].mean():.2f}%")
        print(f"   Avg Bars Held: {trades_df['bars_held'].mean():.1f}")

        print(f"\n💡 'Almost Winners' (reached TP then hit SL):")
        print(f"   Count: {len(almost_winners)}")
        print(f"   % of losers: {len(almost_winners)/len(losers)*100:.1f}%" if len(losers) > 0 else "   N/A")
        print(f"   Avg max favorable: {almost_winners['max_favorable'].mean():.2f}%" if len(almost_winners) > 0 else "   N/A")

        print(f"\n📊 Winner Stats:")
        if len(winners) > 0:
            print(f"   Avg bars held: {winners['bars_held'].mean():.1f}")
            print(f"   Avg max favorable: {winners['max_favorable'].mean():.2f}%")

        print(f"\n📊 Loser Stats:")
        if len(losers) > 0:
            print(f"   Avg bars held: {losers['bars_held'].mean():.1f}")
            print(f"   Avg max favorable: {losers['max_favorable'].mean():.2f}%")

    print()

print("="*120)
print("CONCLUSIONS")
print("="*120)
print()
print("Key questions to answer:")
print("1. Does Aug have more 'almost winners' (reached TP then bounced back)?")
print("2. Is Aug's avg max favorable move lower than Oct/Nov?")
print("3. Do Aug trades get stopped out faster (fewer bars held)?")
print()
print("If Aug has high 'almost winners', we need TIGHTER TP or WIDER SL.")
print("If Aug trades don't move favorably at all, entry timing is wrong.")
print("="*120)
