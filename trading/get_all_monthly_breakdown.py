#!/usr/bin/env python3
"""Get monthly breakdown for best config of each coin"""
import pandas as pd
import numpy as np

def test_coin(csv_file, coin_name, rsi_trigger, limit_atr_offset, tp_pct):
    df = pd.read_csv(csv_file)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)

    delta = df['close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))

    df['tr'] = np.maximum(df['high'] - df['low'], np.maximum(
        abs(df['high'] - df['close'].shift(1)),
        abs(df['low'] - df['close'].shift(1))
    ))
    df['atr'] = df['tr'].rolling(14).mean()

    lookback = 5
    max_wait_bars = 20
    equity = 100.0
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

                size = (equity * 0.05) / (sl_dist_pct / 100)
                hit_sl = False
                hit_tp = False

                for j in range(i + 1, min(i + 500, len(df))):
                    future_row = df.iloc[j]
                    if future_row['high'] >= sl_price:
                        hit_sl = True
                        break
                    elif future_row['low'] <= tp_price:
                        hit_tp = True
                        break

                if hit_sl:
                    pnl_pct = -sl_dist_pct
                elif hit_tp:
                    pnl_pct = tp_pct
                else:
                    continue

                pnl_dollar = size * (pnl_pct / 100) - size * 0.001
                equity += pnl_dollar
                trades.append({'time': df.iloc[signal_idx]['timestamp'], 'pnl': pnl_dollar})
                limit_pending = False

    trades_df = pd.DataFrame(trades)
    trades_df['month'] = pd.to_datetime(trades_df['time']).dt.to_period('M')
    monthly_pnl = {}
    for month in trades_df['month'].unique():
        monthly_pnl[str(month)] = trades_df[trades_df['month'] == month]['pnl'].sum()

    return monthly_pnl, len(trades_df)

# Test each coin with best config
print("Running best configs for all 4 coins...\n")

fartcoin_monthly, fartcoin_trades = test_coin('fartcoin_6months_bingx_15m.csv', 'FARTCOIN', 70, 1.0, 10)
print(f"FARTCOIN: {fartcoin_trades} trades")

moodeng_monthly, moodeng_trades = test_coin('moodeng_6months_bingx_15m.csv', 'MOODENG', 70, 0.8, 8)
print(f"MOODENG: {moodeng_trades} trades")

melania_monthly, melania_trades = test_coin('melania_6months_bingx.csv', 'MELANIA', 72, 0.8, 10)
print(f"MELANIA: {melania_trades} trades")

doge_monthly, doge_trades = test_coin('doge_6months_bingx_15m.csv', 'DOGE', 72, 0.6, 6)
print(f"DOGE: {doge_trades} trades")

# Get all unique months
all_months = set()
for monthly in [fartcoin_monthly, moodeng_monthly, melania_monthly, doge_monthly]:
    all_months.update(monthly.keys())
all_months = sorted(all_months)

print("\n" + "="*100)
print("MONTHLY BREAKDOWN - ALL 4 COINS")
print("="*100)
print(f"{'Month':<12} {'FARTCOIN':>12} {'MOODENG':>12} {'MELANIA':>12} {'DOGE':>12} {'TOTAL':>12}")
print("-"*100)

totals = {'FARTCOIN': 0, 'MOODENG': 0, 'MELANIA': 0, 'DOGE': 0}
for month in all_months:
    fart = fartcoin_monthly.get(month, 0)
    mood = moodeng_monthly.get(month, 0)
    mel = melania_monthly.get(month, 0)
    dog = doge_monthly.get(month, 0)

    totals['FARTCOIN'] += fart
    totals['MOODENG'] += mood
    totals['MELANIA'] += mel
    totals['DOGE'] += dog

    total = fart + mood + mel + dog

    print(f"{month:<12} ${fart:>11.2f} ${mood:>11.2f} ${mel:>11.2f} ${dog:>11.2f} ${total:>11.2f}")

print("-"*100)
grand_total = sum(totals.values())
print(f"{'TOTAL':<12} ${totals['FARTCOIN']:>11.2f} ${totals['MOODENG']:>11.2f} ${totals['MELANIA']:>11.2f} ${totals['DOGE']:>11.2f} ${grand_total:>11.2f}")
print("="*100)

# Summary stats
print("\nSUMMARY:")
for coin, total in totals.items():
    monthly_vals = [fartcoin_monthly, moodeng_monthly, melania_monthly, doge_monthly]
    coin_idx = ['FARTCOIN', 'MOODENG', 'MELANIA', 'DOGE'].index(coin)
    profitable = sum(1 for v in monthly_vals[coin_idx].values() if v > 0)
    total_months = len(monthly_vals[coin_idx])
    print(f"  {coin}: ${total:+.2f} | {profitable}/{total_months} months profitable")
