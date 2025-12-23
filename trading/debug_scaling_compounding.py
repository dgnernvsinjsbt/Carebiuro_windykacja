#!/usr/bin/env python3
"""
Debug: Skąd tak duży compounding?
Sprawdź trade-by-trade w September
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

# September only
df_sep = df[(df['timestamp'] >= '2025-09-01') & (df['timestamp'] < '2025-10-01')].copy().reset_index(drop=True)

print("="*140)
print("DEBUG: SEPTEMBER COMPOUNDING ANALYSIS")
print("="*140)
print()

lookback = 5
tp_pct = 4.0
scale_start = 50
scale_step = 5
max_scales = 10

equity = 100.0
peak_equity = 100.0
max_dd = 0.0
trades = []

# Wykryj swing points
swing_points = []

for i in range(lookback, len(df_sep) - lookback):
    is_swing_high = True
    for j in range(1, lookback + 1):
        if df_sep.iloc[i]['high'] <= df_sep.iloc[i-j]['high'] or df_sep.iloc[i]['high'] <= df_sep.iloc[i+j]['high']:
            is_swing_high = False
            break

    if is_swing_high:
        swing_points.append({'bar': i, 'price': df_sep.iloc[i]['high'], 'type': 'HIGH'})
        continue

    is_swing_low = True
    for j in range(1, lookback + 1):
        if df_sep.iloc[i]['low'] >= df_sep.iloc[i-j]['low'] or df_sep.iloc[i]['low'] >= df_sep.iloc[i+j]['low']:
            is_swing_low = False
            break

    if is_swing_low:
        swing_points.append({'bar': i, 'price': df_sep.iloc[i]['low'], 'type': 'LOW'})

# Trade
i = 0
while i < len(swing_points) - 2:
    p1 = swing_points[i]

    if p1['type'] != 'HIGH':
        i += 1
        continue

    j = i + 1
    while j < len(swing_points) and swing_points[j]['type'] != 'LOW':
        j += 1

    if j >= len(swing_points):
        break

    p2 = swing_points[j]

    k = j + 1
    while k < len(swing_points) and swing_points[k]['type'] != 'HIGH':
        k += 1

    if k >= len(swing_points):
        break

    p3 = swing_points[k]

    if p3['price'] < p1['price']:
        sl_price = p3['price']
        bar_low = p2['bar']
        bar_high = p3['bar']

        bounce_size = p3['price'] - p2['price']

        position_entries = []
        total_position_size = 0.0

        scale_levels = []
        for pct in range(scale_start, 100, scale_step):
            scale_price = p2['price'] + (bounce_size * pct / 100)
            scale_levels.append({'pct': pct, 'price': scale_price, 'filled': False})

        for m in range(bar_high + 1, min(bar_high + 100, len(df_sep))):
            row = df_sep.iloc[m]

            for level in scale_levels:
                if not level['filled'] and row['high'] >= level['price']:
                    entry_price = level['price']
                    sl_dist_pct = ((sl_price - entry_price) / entry_price) * 100

                    if sl_dist_pct > 0 and sl_dist_pct <= 10.0:
                        risk_per_entry = equity * 5.0 / max_scales / 100
                        entry_size = risk_per_entry / (sl_dist_pct / 100)

                        position_entries.append({
                            'bar': m,
                            'price': entry_price,
                            'size': entry_size
                        })

                        total_position_size += entry_size
                        level['filled'] = True

            if len(position_entries) > 0:
                avg_entry = sum([e['price'] * e['size'] for e in position_entries]) / total_position_size
                tp_price = avg_entry * (1 - tp_pct / 100)

                equity_before = equity

                if row['high'] >= sl_price:
                    sl_dist = ((sl_price - avg_entry) / avg_entry) * 100
                    pnl_pct = -sl_dist
                    pnl_dollar = total_position_size * (pnl_pct / 100)
                    equity += pnl_dollar

                    if equity > peak_equity:
                        peak_equity = equity
                    dd = ((peak_equity - equity) / peak_equity) * 100
                    if dd > max_dd:
                        max_dd = dd

                    trades.append({
                        'time': df_sep.iloc[m]['timestamp'],
                        'entries': len(position_entries),
                        'total_size': total_position_size,
                        'avg_entry': avg_entry,
                        'result': 'SL',
                        'pnl_dollar': pnl_dollar,
                        'pnl_pct': pnl_pct,
                        'equity_before': equity_before,
                        'equity_after': equity
                    })

                    break

                elif row['low'] <= tp_price:
                    tp_dist = ((avg_entry - tp_price) / avg_entry) * 100
                    pnl_pct = tp_dist
                    pnl_dollar = total_position_size * (pnl_pct / 100)
                    equity += pnl_dollar

                    if equity > peak_equity:
                        peak_equity = equity
                    dd = ((peak_equity - equity) / peak_equity) * 100
                    if dd > max_dd:
                        max_dd = dd

                    trades.append({
                        'time': df_sep.iloc[m]['timestamp'],
                        'entries': len(position_entries),
                        'total_size': total_position_size,
                        'avg_entry': avg_entry,
                        'result': 'TP',
                        'pnl_dollar': pnl_dollar,
                        'pnl_pct': pnl_pct,
                        'equity_before': equity_before,
                        'equity_after': equity
                    })

                    break

    i = k

# Analysis
trades_df = pd.DataFrame(trades)

print(f"Total Trades: {len(trades_df)}")
print(f"Starting Equity: $100.00")
print(f"Ending Equity: ${equity:.2f}")
print(f"Total Return: {((equity - 100) / 100) * 100:.1f}%")
print(f"Max Drawdown: {max_dd:.1f}%")
print()

print("="*140)
print("TOP 10 BIGGEST WINNERS")
print("="*140)
print(f"{'#':<4} | {'Date':<16} | {'Entries':<8} | {'Pos Size':<15} | {'P&L $':<15} | {'P&L %':<10} | {'Equity After':<15}")
print("-"*140)

top_winners = trades_df.nlargest(10, 'pnl_dollar')
for idx, t in top_winners.iterrows():
    contribution = (t['pnl_dollar'] / (equity - 100)) * 100
    print(f"{idx+1:<4} | {t['time'].strftime('%m-%d %H:%M'):<16} | {t['entries']:<8} | ${t['total_size']:>13,.2f} | ${t['pnl_dollar']:>13,.2f} | {t['pnl_pct']:>8.2f}% | ${t['equity_after']:>13,.2f} ({contribution:.1f}% profit)")

print()
print("="*140)
print("EQUITY CURVE MILESTONES")
print("="*140)

milestones = [200, 500, 1000, 5000, 10000, 50000, 100000]
for milestone in milestones:
    crossed = trades_df[trades_df['equity_after'] >= milestone]
    if len(crossed) > 0:
        first = crossed.iloc[0]
        print(f"  ${milestone:>6,}: Trade #{crossed.index[0]+1} on {first['time'].strftime('%m-%d %H:%M')}")

print()
print("="*140)
print("POZYCJA SIZE PROGRESSION")
print("="*140)
print(f"  First trade position: ${trades_df.iloc[0]['total_size']:,.2f}")
print(f"  Last trade position: ${trades_df.iloc[-1]['total_size']:,.2f}")
print(f"  Max position size: ${trades_df['total_size'].max():,.2f}")
print(f"  Growth: {(trades_df.iloc[-1]['total_size'] / trades_df.iloc[0]['total_size']):.0f}x")
print()

print("="*140)
print("KLUCZOWE PYTANIE: Czy to jest realistyczne?")
print("="*140)
print()
print(f"  🔴 Max DD tylko {max_dd:.1f}% przy +{((equity-100)/100)*100:.0f}% return?")
print(f"  🔴 Position size urósł {(trades_df.iloc[-1]['total_size'] / trades_df.iloc[0]['total_size']):.0f}x")
print(f"  🔴 Kilka trades z position size >${trades_df['total_size'].quantile(0.95):,.0f}")
print()
print("  To wygląda na:")
print("  1. Kilka BARDZO szczęśliwych trade'ów które trafiły TP z ogromnymi pozycjami")
print("  2. Extreme compounding effect")
print("  3. Możliwe błędy w position sizing (risk per entry * max_scales)")
print()
print("="*140)
