#!/usr/bin/env python3
"""
MOODENG - LOTTERY TICKET STRATEGY

Łap TYLKO ekstremalne moves (10%+) używając vol explosion as signal.

Idea:
- MOODENG ma kurtosis 387 = ekstremalne outliers
- 99th percentile move = 5.49% (1h)
- Są moves po 10-20%+ ale rzadkie
- Zamiast próbować tradować wszystko, łap TYLKO te big moves

Strategy:
- Small SL (1-2%)
- BIG TP (10-15%)
- Entry: Volatility explosion + momentum
- R:R = 5:1 do 10:1
- Win rate może być 20-30% ALE expectancy positive
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

period = 14
delta = df['close'].diff()
gain = delta.where(delta > 0, 0)
loss = -delta.where(delta < 0, 0)
avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
rs = avg_gain / avg_loss
df['rsi'] = 100 - (100 / (1 + rs))

df['return_1h'] = df['close'].pct_change(4) * 100
df['return_4h'] = df['close'].pct_change(16) * 100

df['month'] = df['timestamp'].dt.to_period('M')

print("="*140)
print("MOODENG - LOTTERY TICKET STRATEGY")
print("="*140)
print()

# ============================================
# PART 1: ANALYZE BIG MOVES
# ============================================
print("="*140)
print("PART 1: ANALYZE BIG MOVES - Kiedy się zdarzają?")
print("="*140)
print()

# Find all big moves
big_moves_10 = []
big_moves_15 = []
big_moves_20 = []

for i in range(20, len(df) - 40):
    # Look forward 4h (16 bars)
    future_high = df.iloc[i:i+40]['high'].max()
    future_low = df.iloc[i:i+40]['low'].min()

    current_price = df.iloc[i]['close']

    # Up move
    up_move = ((future_high - current_price) / current_price) * 100
    # Down move
    down_move = ((current_price - future_low) / current_price) * 100

    if up_move >= 10:
        big_moves_10.append({
            'bar': i,
            'direction': 'UP',
            'magnitude': up_move,
            'timestamp': df.iloc[i]['timestamp'],
            'atr_before': df.iloc[i]['atr_pct'],
            'rsi_before': df.iloc[i]['rsi'],
            'ma_dist': ((df.iloc[i]['close'] - df.iloc[i]['ma_20']) / df.iloc[i]['ma_20']) * 100,
            'return_1h_before': df.iloc[i]['return_1h']
        })

        if up_move >= 15:
            big_moves_15.append(big_moves_10[-1])
        if up_move >= 20:
            big_moves_20.append(big_moves_10[-1])

    if down_move >= 10:
        big_moves_10.append({
            'bar': i,
            'direction': 'DOWN',
            'magnitude': down_move,
            'timestamp': df.iloc[i]['timestamp'],
            'atr_before': df.iloc[i]['atr_pct'],
            'rsi_before': df.iloc[i]['rsi'],
            'ma_dist': ((df.iloc[i]['close'] - df.iloc[i]['ma_20']) / df.iloc[i]['ma_20']) * 100,
            'return_1h_before': df.iloc[i]['return_1h']
        })

        if down_move >= 15:
            big_moves_15.append(big_moves_10[-1])
        if down_move >= 20:
            big_moves_20.append(big_moves_10[-1])

print(f"Big moves found:")
print(f"  10%+ moves: {len(big_moves_10)} instances")
print(f"  15%+ moves: {len(big_moves_15)} instances")
print(f"  20%+ moves: {len(big_moves_20)} instances")
print()

if len(big_moves_10) > 0:
    moves_df = pd.DataFrame(big_moves_10)

    print(f"Characteristics BEFORE big move:")
    print(f"  Avg ATR: {moves_df['atr_before'].mean():.3f}% (overall: {df['atr_pct'].mean():.3f}%)")
    print(f"  Avg RSI: {moves_df['rsi_before'].mean():.1f}")
    print(f"  Avg 1h momentum: {moves_df['return_1h_before'].mean():.2f}%")
    print()

    # Check if high ATR predicts big moves
    high_atr_before = (moves_df['atr_before'] > 1.2).sum()
    print(f"  Vol explosion before (ATR > 1.2%): {high_atr_before}/{len(moves_df)} ({high_atr_before/len(moves_df)*100:.1f}%)")

    # Check momentum
    strong_momentum = (moves_df['return_1h_before'].abs() > 2).sum()
    print(f"  Strong momentum before (>2%): {strong_momentum}/{len(moves_df)} ({strong_momentum/len(moves_df)*100:.1f}%)")

    print()

# ============================================
# PART 2: PREDICTIVE SIGNALS
# ============================================
print("="*140)
print("PART 2: CO PREDICTS BIG MOVE?")
print("="*140)
print()

# Test different entry signals
signals_to_test = [
    {
        'name': 'VOL_EXPLOSION',
        'condition': df['atr_pct'] > 1.5,
        'description': 'ATR > 1.5%'
    },
    {
        'name': 'VOL_EXPANSION',
        'condition': df['atr_pct'] > df['atr_pct'].shift(4) * 1.3,
        'description': 'ATR increased 30% in last hour'
    },
    {
        'name': 'MOMENTUM_SPIKE',
        'condition': df['return_1h'].abs() > 3,
        'description': 'Absolute 1h move > 3%'
    },
    {
        'name': 'COMBO_VOL_MOMENTUM',
        'condition': (df['atr_pct'] > 1.2) & (df['return_1h'].abs() > 2),
        'description': 'ATR > 1.2% + momentum > 2%'
    }
]

for signal in signals_to_test:
    signal_bars = df[signal['condition']].copy()

    if len(signal_bars) < 50:
        continue

    # Check forward returns
    signal_bars.loc[:, 'forward_10h'] = df.loc[signal_bars.index, 'close'].shift(-40).pct_change(fill_method=None) * 100

    avg_move = signal_bars['forward_10h'].abs().mean()
    big_moves_caught = (signal_bars['forward_10h'].abs() > 10).sum()
    hit_rate = big_moves_caught / len(signal_bars) * 100

    print(f"Signal: {signal['name']}")
    print(f"  Description: {signal['description']}")
    print(f"  Frequency: {len(signal_bars)} instances")
    print(f"  Avg forward 10h move: {avg_move:.2f}%")
    print(f"  Big moves (>10%) caught: {big_moves_caught}/{len(signal_bars)} ({hit_rate:.1f}%)")

    if hit_rate > 15:
        print(f"  🔥 PROMISING SIGNAL!")
    elif hit_rate > 10:
        print(f"  ✅ DECENT")
    else:
        print(f"  ⚠️  WEAK")

    print()

# ============================================
# PART 3: LOTTERY TICKET STRATEGY
# ============================================
print("="*140)
print("PART 3: LOTTERY TICKET STRATEGY - Small SL, Big TP")
print("="*140)
print()

test_months = ['2025-06', '2025-07', '2025-08', '2025-09', '2025-10', '2025-11', '2025-12']

# Test different TP levels
tp_levels = [8, 10, 12, 15]
sl_pct = 2.0  # Fixed small SL

for tp_pct in tp_levels:
    print(f"Testing TP={tp_pct}%, SL={sl_pct}% (R:R = {tp_pct/sl_pct:.1f}:1)")
    print("-" * 80)

    monthly_results = []

    for month_str in test_months:
        df_month = df[df['month'] == month_str].copy().reset_index(drop=True)

        equity = 100.0
        peak_equity = 100.0
        max_dd = 0.0
        trades = []

        i = 20
        while i < len(df_month) - 40:
            row = df_month.iloc[i]

            # Skip if no indicators
            if pd.isna(row['atr_pct']) or pd.isna(row['rsi']):
                i += 1
                continue

            # ENTRY SIGNAL: Vol explosion + momentum
            vol_explosion = row['atr_pct'] > 1.2
            momentum = abs(row['return_1h']) > 2

            if vol_explosion and momentum:
                # Determine direction based on momentum
                if row['return_1h'] > 0:
                    # LONG
                    entry_price = row['close']
                    sl_price = entry_price * (1 - sl_pct / 100)
                    tp_price = entry_price * (1 + tp_pct / 100)
                    direction = 'LONG'
                else:
                    # SHORT
                    entry_price = row['close']
                    sl_price = entry_price * (1 + sl_pct / 100)
                    tp_price = entry_price * (1 - tp_pct / 100)
                    direction = 'SHORT'

                # Position size: risk 2% of equity
                position_size = (equity * 2.0) / sl_pct

                # Find exit
                hit_sl = False
                hit_tp = False

                for j in range(i + 1, min(i + 40, len(df_month))):
                    exit_row = df_month.iloc[j]

                    if direction == 'LONG':
                        if exit_row['low'] <= sl_price:
                            hit_sl = True
                            break
                        elif exit_row['high'] >= tp_price:
                            hit_tp = True
                            break
                    else:  # SHORT
                        if exit_row['high'] >= sl_price:
                            hit_sl = True
                            break
                        elif exit_row['low'] <= tp_price:
                            hit_tp = True
                            break

                if hit_sl or hit_tp:
                    if hit_tp:
                        pnl_pct = tp_pct
                    else:
                        pnl_pct = -sl_pct

                    pnl_dollar = position_size * (pnl_pct / 100)
                    equity += pnl_dollar

                    if equity > peak_equity:
                        peak_equity = equity
                    dd = ((peak_equity - equity) / peak_equity) * 100
                    if dd > max_dd:
                        max_dd = dd

                    trades.append({
                        'direction': direction,
                        'result': 'TP' if hit_tp else 'SL',
                        'pnl': pnl_dollar
                    })

                    # Skip ahead
                    i = j + 5
                    continue

            i += 1

        # Stats
        if len(trades) > 0:
            trades_df = pd.DataFrame(trades)
            total_return = ((equity - 100) / 100) * 100
            win_rate = (trades_df['result'] == 'TP').sum() / len(trades_df) * 100

            monthly_results.append({
                'month': month_str,
                'return': total_return,
                'max_dd': max_dd,
                'win_rate': win_rate,
                'trades': len(trades_df)
            })
        else:
            monthly_results.append({
                'month': month_str,
                'return': 0,
                'max_dd': 0,
                'win_rate': 0,
                'trades': 0
            })

    # Overall
    compounded = 100.0
    for m in monthly_results:
        compounded *= (1 + m['return'] / 100)

    total_return = ((compounded - 100) / 100) * 100
    overall_max_dd = max([m['max_dd'] for m in monthly_results] + [0.01])
    return_dd = total_return / overall_max_dd
    total_trades = sum([m['trades'] for m in monthly_results])
    avg_wr = np.mean([m['win_rate'] for m in monthly_results if m['trades'] > 0])

    print(f"  Total Return: {total_return:+.1f}%")
    print(f"  Max DD: {overall_max_dd:.1f}%")
    print(f"  R/DD: {return_dd:.2f}x")
    print(f"  Total Trades: {total_trades} ({total_trades/7:.1f}/month)")
    print(f"  Avg Win Rate: {avg_wr:.1f}%")

    # Calculate expectancy
    if total_trades > 0:
        expectancy = (avg_wr/100 * tp_pct) + ((100-avg_wr)/100 * -sl_pct)
        print(f"  Expectancy: {expectancy:.2f}% per trade")

        if return_dd > 5 and total_trades > 20:
            print(f"  🔥 STRONG STRATEGY!")
        elif return_dd > 2:
            print(f"  ✅ WORKS")
        else:
            print(f"  ⚠️  WEAK")

    print()

print("="*140)
