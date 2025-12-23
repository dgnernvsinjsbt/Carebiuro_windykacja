#!/usr/bin/env python3
"""
MOODENG MOMENTUM + VOL EXPANSION STRATEGY

Based on deep analysis:
1. MOODENG is MOMENTUM coin (moves continue, not revert)
2. Volatility CLUSTERS (+48% after spike)
3. Breakouts work (55.8% success)
4. Trade only during trends (not ranging)

STRATEGY:
- Entry: Volatility spike + trend confirmation + breakout
- Direction: WITH the trend (momentum)
- Exit: Trailing stop or opposite signal
"""
import pandas as pd
import numpy as np

df = pd.read_csv('moodeng_6months_bingx_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# Indicators
high_low = df['high'] - df['low']
high_close = abs(df['high'] - df['close'].shift())
low_close = abs(df['low'] - df['close'].shift())
tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
df['atr'] = tr.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
df['atr_pct'] = (df['atr'] / df['close']) * 100

df['ma_20'] = df['close'].rolling(window=20).mean()
df['ma_50'] = df['close'].rolling(window=50).mean()

df['return_4h'] = df['close'].pct_change(16) * 100

df['month'] = df['timestamp'].dt.to_period('M')

print("="*140)
print("MOODENG MOMENTUM + VOL EXPANSION STRATEGY")
print("="*140)
print()

test_months = ['2025-06', '2025-07', '2025-08', '2025-09', '2025-10', '2025-11', '2025-12']
results = []

# Parameters
vol_threshold = 1.18  # ATR spike threshold (75th percentile)
lookback_breakout = 20  # Breakout lookback
trend_threshold = 1.5  # % from MA20 to confirm trend

for month_str in test_months:
    df_month = df[df['month'] == month_str].copy().reset_index(drop=True)

    equity = 100.0
    peak_equity = 100.0
    max_dd = 0.0
    trades = []

    in_position = False
    position_type = None
    entry_price = 0
    position_size = 0
    entry_bar = 0

    i = lookback_breakout
    while i < len(df_month) - 4:
        row = df_month.iloc[i]

        # Skip if no indicators
        if pd.isna(row['ma_20']) or pd.isna(row['ma_50']) or pd.isna(row['atr_pct']):
            i += 1
            continue

        # Calculate trend
        dist_ma20 = ((row['close'] - row['ma_20']) / row['ma_20']) * 100

        # Determine market state
        if dist_ma20 > trend_threshold:
            trend = 'UP'
        elif dist_ma20 < -trend_threshold:
            trend = 'DOWN'
        else:
            trend = 'RANGING'

        # ENTRY LOGIC
        if not in_position and trend != 'RANGING':
            # Check for volatility spike
            vol_spike = row['atr_pct'] > vol_threshold

            if vol_spike:
                # Check for breakout
                recent_high = df_month.iloc[max(0, i-lookback_breakout):i]['high'].max()
                recent_low = df_month.iloc[max(0, i-lookback_breakout):i]['low'].min()

                # LONG on breakout above resistance in uptrend
                if trend == 'UP' and row['high'] >= recent_high:
                    entry_price = row['close']
                    sl_price = recent_low

                    sl_dist_pct = ((entry_price - sl_price) / entry_price) * 100

                    if sl_dist_pct > 0 and sl_dist_pct <= 10.0:
                        position_size = (equity * 5.0) / sl_dist_pct
                        position_type = 'LONG'
                        in_position = True
                        entry_bar = i

                # SHORT on breakout below support in downtrend
                elif trend == 'DOWN' and row['low'] <= recent_low:
                    entry_price = row['close']
                    sl_price = recent_high

                    sl_dist_pct = ((sl_price - entry_price) / entry_price) * 100

                    if sl_dist_pct > 0 and sl_dist_pct <= 10.0:
                        position_size = (equity * 5.0) / sl_dist_pct
                        position_type = 'SHORT'
                        in_position = True
                        entry_bar = i

        # EXIT LOGIC
        if in_position:
            # Recalculate current trend
            current_dist_ma20 = ((row['close'] - row['ma_20']) / row['ma_20']) * 100

            exit_signal = False
            exit_type = None

            if position_type == 'LONG':
                # SL
                if row['low'] <= sl_price:
                    exit_price = sl_price
                    exit_type = 'SL'
                    exit_signal = True

                # Trend reversal
                elif current_dist_ma20 < -trend_threshold:
                    exit_price = row['close']
                    exit_type = 'TREND_REVERSE'
                    exit_signal = True

                # Time-based exit (20 bars = 5 hours)
                elif i - entry_bar >= 20:
                    exit_price = row['close']
                    exit_type = 'TIME'
                    exit_signal = True

            elif position_type == 'SHORT':
                # SL
                if row['high'] >= sl_price:
                    exit_price = sl_price
                    exit_type = 'SL'
                    exit_signal = True

                # Trend reversal
                elif current_dist_ma20 > trend_threshold:
                    exit_price = row['close']
                    exit_type = 'TREND_REVERSE'
                    exit_signal = True

                # Time-based exit
                elif i - entry_bar >= 20:
                    exit_price = row['close']
                    exit_type = 'TIME'
                    exit_signal = True

            if exit_signal:
                if position_type == 'LONG':
                    pnl_pct = ((exit_price - entry_price) / entry_price) * 100
                else:
                    pnl_pct = ((entry_price - exit_price) / entry_price) * 100

                pnl_dollar = position_size * (pnl_pct / 100)
                equity += pnl_dollar

                if equity > peak_equity:
                    peak_equity = equity
                dd = ((peak_equity - equity) / peak_equity) * 100
                if dd > max_dd:
                    max_dd = dd

                trades.append({
                    'type': position_type,
                    'exit': exit_type,
                    'pnl': pnl_dollar,
                    'pnl_pct': pnl_pct
                })

                in_position = False
                position_type = None

        i += 1

    # Close any open position at month end
    if in_position:
        row = df_month.iloc[-1]
        exit_price = row['close']

        if position_type == 'LONG':
            pnl_pct = ((exit_price - entry_price) / entry_price) * 100
        else:
            pnl_pct = ((entry_price - exit_price) / entry_price) * 100

        pnl_dollar = position_size * (pnl_pct / 100)
        equity += pnl_dollar

        if equity > peak_equity:
            peak_equity = equity
        dd = ((peak_equity - equity) / peak_equity) * 100
        if dd > max_dd:
            max_dd = dd

        trades.append({
            'type': position_type,
            'exit': 'EOD',
            'pnl': pnl_dollar,
            'pnl_pct': pnl_pct
        })

    # Stats
    if len(trades) > 0:
        trades_df = pd.DataFrame(trades)
        total_return = ((equity - 100) / 100) * 100
        winners = trades_df[trades_df['pnl'] > 0]
        win_rate = (len(winners) / len(trades_df)) * 100

        long_trades = trades_df[trades_df['type'] == 'LONG']
        short_trades = trades_df[trades_df['type'] == 'SHORT']

        results.append({
            'month': month_str,
            'return': total_return,
            'max_dd': max_dd,
            'return_dd': total_return / max_dd if max_dd > 0 else 0,
            'win_rate': win_rate,
            'trades': len(trades_df),
            'longs': len(long_trades),
            'shorts': len(short_trades),
            'final_equity': equity
        })
    else:
        results.append({
            'month': month_str,
            'return': 0,
            'max_dd': 0,
            'return_dd': 0,
            'win_rate': 0,
            'trades': 0,
            'longs': 0,
            'shorts': 0,
            'final_equity': equity
        })

# Display
results_df = pd.DataFrame(results)

print(f"{'Month':<10} | {'Return':<10} | {'Max DD':<8} | {'R/DD':<7} | {'WR%':<6} | {'Trades':<7} | {'L':<4} | {'S':<4} | {'Final $':<12}")
print("-"*140)

for idx, row in results_df.iterrows():
    status = "✅" if row['return'] > 0 else "❌"
    print(f"{row['month']:<10} | {row['return']:>8.1f}% | {row['max_dd']:>6.1f}% | {row['return_dd']:>5.2f}x | {row['win_rate']:>4.1f}% | {row['trades']:<7} | {row['longs']:<4} | {row['shorts']:<4} | ${row['final_equity']:>10,.2f} {status}")

print()

# Overall
compounded = 100.0
for idx, row in results_df.iterrows():
    compounded *= (1 + row['return'] / 100)

total_return = ((compounded - 100) / 100) * 100
overall_max_dd = results_df['max_dd'].max()
overall_return_dd = total_return / overall_max_dd if overall_max_dd > 0 else 0
wins = len(results_df[results_df['return'] > 0])
total_trades = results_df['trades'].sum()

print("="*140)
print("PODSUMOWANIE (Jun-Dec 2025):")
print(f"  Compounded Return: {total_return:+.1f}%")
print(f"  Max Drawdown: {overall_max_dd:.1f}%")
print(f"  Return/DD Ratio: {overall_return_dd:.2f}x")
print(f"  Winning Months: {wins}/7")
print(f"  Total Trades: {total_trades}")
print(f"  Trades/month: {total_trades/7:.1f}")
print()

if overall_return_dd > 5 and total_trades > 20:
    print("✅ MOMENTUM STRATEGY DZIAŁA!")
    print(f"   R/DD: {overall_return_dd:.2f}x (target: >5x)")
    print(f"   Trades: {total_trades} (target: >20)")
elif total_return > 0:
    print("⚠️  MOMENTUM strategy ma positive return ale słaby edge:")
    print(f"   R/DD: {overall_return_dd:.2f}x (target: >5x)")
    print(f"   Może potrzebne są inne parametry?")
else:
    print("❌ MOMENTUM strategy nie działa na MOODENG")
    print(f"   Return: {total_return:.1f}%")
    print()
    print("   Możliwe przyczyny:")
    print("   1. Volatility clustering działa ale entries/exits słabe")
    print("   2. Trend detection nieprecyzyjny")
    print("   3. MOODENG zbyt choppy mimo momentum characteristics")

print("="*140)
