#!/usr/bin/env python3
"""
Analyze NASDAQ LONG trade dynamics:
- How long winners vs losers?
- Do we lose immediately or give back profits?
- Would trailing stop help?
- Should we use flat ATR stop instead of swing level?
"""
import pandas as pd
import numpy as np

print("="*90)
print("NASDAQ LONG REVERSAL - TRADE DYNAMICS ANALYSIS")
print("="*90)

# Load NASDAQ data
df = pd.read_csv('trading/nasdaq_3months_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# Calculate RSI
delta = df['close'].diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)
avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
rs = avg_gain / avg_loss
df['rsi'] = 100 - (100 / (1 + rs))

# Calculate ATR
df['tr'] = np.maximum(
    df['high'] - df['low'],
    np.maximum(
        abs(df['high'] - df['close'].shift(1)),
        abs(df['low'] - df['close'].shift(1))
    )
)
df['atr'] = df['tr'].rolling(14).mean()

def find_swing_high(df, idx, lookback):
    start = max(0, idx - lookback)
    return df.iloc[start:idx+1]['high'].max()

def find_swing_low(df, start_idx, end_idx):
    return df.iloc[start_idx:end_idx+1]['low'].min()

def analyze_trade_path(df, entry_idx, exit_idx, entry_price, sl_price, tp_price):
    """
    Analyze what happens during the trade
    Returns detailed path metrics
    """
    path = []
    max_profit_pct = 0
    max_profit_idx = entry_idx
    bars_to_max_profit = 0
    went_positive = False
    max_drawdown_pct = 0

    for j in range(entry_idx + 1, exit_idx + 1):
        bar = df.iloc[j]
        bars_elapsed = j - entry_idx

        # Calculate unrealized P&L based on current high/low
        high_pnl_pct = ((bar['high'] - entry_price) / entry_price) * 100
        low_pnl_pct = ((bar['low'] - entry_price) / entry_price) * 100

        # Track max profit
        if high_pnl_pct > max_profit_pct:
            max_profit_pct = high_pnl_pct
            max_profit_idx = j
            bars_to_max_profit = bars_elapsed

        # Track if we went positive
        if high_pnl_pct > 0:
            went_positive = True

        # Track max drawdown from entry
        if low_pnl_pct < max_drawdown_pct:
            max_drawdown_pct = low_pnl_pct

    total_bars = exit_idx - entry_idx

    return {
        'total_bars': total_bars,
        'max_profit_pct': max_profit_pct,
        'bars_to_max_profit': bars_to_max_profit,
        'went_positive': went_positive,
        'max_drawdown_pct': max_drawdown_pct,
        'gave_back_profit': max_profit_pct > 0  # Did we have profit at some point?
    }

# Run backtest with detailed tracking
rsi_trigger = 28
limit_offset = 0.20
tp_pct = 2.0
lookback = 5
max_wait = 20
max_sl_pct = 5.0

equity = 100.0
trades = []

armed = False
signal_idx = None
swing_high = None
limit_pending = False
limit_placed_idx = None
swing_low_for_sl = None

for i in range(lookback, len(df)):
    row = df.iloc[i]

    if pd.isna(row['rsi']) or pd.isna(row['atr']):
        continue

    # ARM
    if row['rsi'] < rsi_trigger:
        armed = True
        signal_idx = i
        swing_high = find_swing_high(df, i, lookback)
        limit_pending = False

    # Break
    if armed and swing_high is not None and not limit_pending:
        if row['high'] > swing_high:
            atr = row['atr']
            limit_price = swing_high - (atr * limit_offset)
            swing_low_for_sl = find_swing_low(df, signal_idx, i)
            limit_pending = True
            limit_placed_idx = i
            armed = False

    # Fill
    if limit_pending:
        if i - limit_placed_idx > max_wait:
            limit_pending = False
            continue

        if row['low'] <= limit_price:
            entry_price = limit_price
            entry_atr = row['atr']
            sl_price = swing_low_for_sl
            tp_price = entry_price * (1 + tp_pct / 100)

            sl_dist_pct = ((entry_price - sl_price) / entry_price) * 100

            # Flat ATR stop alternatives
            flat_atr_1x = entry_price - (entry_atr * 1.0)
            flat_atr_15x = entry_price - (entry_atr * 1.5)
            flat_atr_2x = entry_price - (entry_atr * 2.0)

            if sl_dist_pct <= 0 or sl_dist_pct > max_sl_pct:
                limit_pending = False
                continue

            size = (equity * 0.05) / (sl_dist_pct / 100)

            # Find exit
            hit_sl = False
            hit_tp = False
            exit_bar = None

            for j in range(i + 1, min(i + 500, len(df))):
                future_row = df.iloc[j]

                if future_row['low'] <= sl_price:
                    hit_sl = True
                    exit_bar = j
                    break
                elif future_row['high'] >= tp_price:
                    hit_tp = True
                    exit_bar = j
                    break

            if hit_sl:
                pnl_pct = -sl_dist_pct
                exit_reason = 'SL'
            elif hit_tp:
                pnl_pct = tp_pct
                exit_reason = 'TP'
            else:
                continue

            pnl_dollar = size * (pnl_pct / 100) - size * 0.001
            equity += pnl_dollar

            # Analyze trade path
            path_metrics = analyze_trade_path(df, i, exit_bar, entry_price, sl_price, tp_price)

            trades.append({
                'entry_idx': i,
                'exit_idx': exit_bar,
                'entry_price': entry_price,
                'sl_price': sl_price,
                'tp_price': tp_price,
                'entry_atr': entry_atr,
                'swing_sl_dist_pct': sl_dist_pct,
                'flat_atr_1x_dist_pct': ((entry_price - flat_atr_1x) / entry_price) * 100,
                'flat_atr_15x_dist_pct': ((entry_price - flat_atr_15x) / entry_price) * 100,
                'flat_atr_2x_dist_pct': ((entry_price - flat_atr_2x) / entry_price) * 100,
                'pnl_pct': pnl_pct,
                'pnl_dollar': pnl_dollar,
                'exit_reason': exit_reason,
                'total_bars': path_metrics['total_bars'],
                'max_profit_pct': path_metrics['max_profit_pct'],
                'bars_to_max_profit': path_metrics['bars_to_max_profit'],
                'went_positive': path_metrics['went_positive'],
                'max_drawdown_pct': path_metrics['max_drawdown_pct'],
                'gave_back_profit': path_metrics['gave_back_profit']
            })

            limit_pending = False

trades_df = pd.DataFrame(trades)

print(f"\n📊 Analyzed {len(trades_df)} trades")
print()

# Split winners vs losers
winners = trades_df[trades_df['exit_reason'] == 'TP']
losers = trades_df[trades_df['exit_reason'] == 'SL']

print("="*90)
print("⏱️  DURATION ANALYSIS")
print("="*90)
print()
print(f"{'Metric':<30} | {'Winners (TP)':<15} | {'Losers (SL)':<15}")
print("-" * 65)
print(f"{'Count':<30} | {len(winners):<15} | {len(losers):<15}")
print(f"{'Avg Bars':<30} | {winners['total_bars'].mean():<15.1f} | {losers['total_bars'].mean():<15.1f}")
print(f"{'Median Bars':<30} | {winners['total_bars'].median():<15.1f} | {losers['total_bars'].median():<15.1f}")
print(f"{'Min Bars':<30} | {winners['total_bars'].min():<15} | {losers['total_bars'].min():<15}")
print(f"{'Max Bars':<30} | {winners['total_bars'].max():<15} | {losers['total_bars'].max():<15}")

print("\n" + "="*90)
print("📈 PROFIT DYNAMICS - DO WE GIVE BACK PROFITS?")
print("="*90)
print()

# Losers that went positive
losers_went_positive = losers[losers['went_positive']]
print(f"Total Losers: {len(losers)}")
print(f"Losers that went POSITIVE before SL: {len(losers_went_positive)} ({len(losers_went_positive)/len(losers)*100:.1f}%)")
print()

if len(losers_went_positive) > 0:
    print(f"These {len(losers_went_positive)} trades GAVE BACK PROFIT:")
    print(f"  Avg max profit reached: {losers_went_positive['max_profit_pct'].mean():.2f}%")
    print(f"  Avg bars to max profit: {losers_went_positive['bars_to_max_profit'].mean():.1f}")
    print(f"  Then hit SL at: {losers_went_positive['swing_sl_dist_pct'].mean():.2f}% loss")
    print()
    print("  🔥 TRAILING STOP WOULD HELP HERE!")

# Losers that never went positive (immediate losses)
losers_immediate = losers[~losers['went_positive']]
print(f"\nLosers that NEVER went positive: {len(losers_immediate)} ({len(losers_immediate)/len(losers)*100:.1f}%)")
if len(losers_immediate) > 0:
    print(f"  Avg bars to SL: {losers_immediate['total_bars'].mean():.1f}")
    print(f"  Max drawdown: {losers_immediate['max_drawdown_pct'].mean():.2f}%")
    print()
    print("  ❌ These are bad entries - trailing stop won't help")

print("\n" + "="*90)
print("🎯 WINNERS - DO THEY MOVE FAST?")
print("="*90)
print()
print(f"Avg bars to TP: {winners['total_bars'].mean():.1f}")
print(f"Avg max profit (peak): {winners['max_profit_pct'].mean():.2f}%")
print(f"Avg bars to max profit: {winners['bars_to_max_profit'].mean():.1f}")
print()

# Did winners peak higher than TP?
winners_peaked_higher = winners[winners['max_profit_pct'] > tp_pct]
print(f"Winners that peaked ABOVE TP: {len(winners_peaked_higher)} ({len(winners_peaked_higher)/len(winners)*100:.1f}%)")
if len(winners_peaked_higher) > 0:
    print(f"  Avg peak: {winners_peaked_higher['max_profit_pct'].mean():.2f}% (vs TP {tp_pct:.1f}%)")
    print(f"  Avg missed profit: {(winners_peaked_higher['max_profit_pct'] - tp_pct).mean():.2f}%")
    print()
    print("  🔥 TRAILING STOP could capture more profit here!")

print("\n" + "="*90)
print("🛑 STOP LOSS ANALYSIS - SWING vs FLAT ATR")
print("="*90)
print()

print(f"{'Stop Method':<25} | {'Avg Distance':<15} | {'vs Swing Level':<15}")
print("-" * 60)
print(f"{'Swing Low (current)':<25} | {trades_df['swing_sl_dist_pct'].mean():<15.2f}% | {'baseline':<15}")
print(f"{'Flat 1.0x ATR':<25} | {trades_df['flat_atr_1x_dist_pct'].mean():<15.2f}% | {(trades_df['flat_atr_1x_dist_pct'].mean() - trades_df['swing_sl_dist_pct'].mean()):+.2f}%")
print(f"{'Flat 1.5x ATR':<25} | {trades_df['flat_atr_15x_dist_pct'].mean():<15.2f}% | {(trades_df['flat_atr_15x_dist_pct'].mean() - trades_df['swing_sl_dist_pct'].mean()):+.2f}%")
print(f"{'Flat 2.0x ATR':<25} | {trades_df['flat_atr_2x_dist_pct'].mean():<15.2f}% | {(trades_df['flat_atr_2x_dist_pct'].mean() - trades_df['swing_sl_dist_pct'].mean()):+.2f}%")

print("\n" + "="*90)
print("💡 RECOMMENDATIONS")
print("="*90)
print()

gave_back_pct = (len(losers_went_positive) / len(losers) * 100) if len(losers) > 0 else 0
peaked_higher_pct = (len(winners_peaked_higher) / len(winners) * 100) if len(winners) > 0 else 0

print(f"1. TRAILING STOP POTENTIAL:")
print(f"   - {len(losers_went_positive)}/{len(losers)} losers ({gave_back_pct:.0f}%) went positive before SL")
print(f"   - {len(winners_peaked_higher)}/{len(winners)} winners ({peaked_higher_pct:.0f}%) peaked above TP")

if gave_back_pct > 30 or peaked_higher_pct > 50:
    print(f"   ✅ TRAILING STOP RECOMMENDED! High potential to:")
    if gave_back_pct > 30:
        print(f"      - Protect {gave_back_pct:.0f}% of losers that went positive")
    if peaked_higher_pct > 50:
        print(f"      - Capture extra profit from {peaked_higher_pct:.0f}% of winners")
else:
    print(f"   ⚠️  TRAILING STOP LIMITED BENEFIT")

print()
print(f"2. STOP LOSS METHOD:")
swing_avg = trades_df['swing_sl_dist_pct'].mean()
flat_1x_avg = trades_df['flat_atr_1x_dist_pct'].mean()
flat_15x_avg = trades_df['flat_atr_15x_dist_pct'].mean()
flat_2x_avg = trades_df['flat_atr_2x_dist_pct'].mean()

print(f"   Current swing level: {swing_avg:.2f}% avg distance")

if abs(flat_15x_avg - swing_avg) < 0.1:
    print(f"   ✅ Swing level ≈ 1.5x ATR ({flat_15x_avg:.2f}%) - current method is good")
elif flat_1x_avg < swing_avg < flat_15x_avg:
    print(f"   ✅ Swing level ({swing_avg:.2f}%) between 1.0-1.5x ATR - adaptive and good")
else:
    print(f"   Consider testing flat 1.5x ATR ({flat_15x_avg:.2f}%) for consistency")

print()
print(f"3. IMMEDIATE LOSSES:")
print(f"   - {len(losers_immediate)}/{len(losers)} losers ({len(losers_immediate)/len(losers)*100:.0f}%) never went positive")
print(f"   - These are BAD ENTRIES - no trailing stop can save them")
print(f"   - Avg time to SL: {losers_immediate['total_bars'].mean():.1f} bars")

if len(losers_immediate) / len(losers) > 0.5:
    print(f"   ⚠️  ENTRY QUALITY is the main issue, not exit method")

# Save detailed trades
trades_df.to_csv('nasdaq_trade_dynamics_detailed.csv', index=False)
print(f"\n💾 Detailed trades saved to: nasdaq_trade_dynamics_detailed.csv")
print("="*90)
