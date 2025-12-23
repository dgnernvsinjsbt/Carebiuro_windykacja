#!/usr/bin/env python3
"""
MOODENG - ZNAJDŹ NAJLEPSZY EDGE

Approach:
1. Sprawdź WSZYSTKIE możliwe setups
2. Znajdź który ma najlepszy win rate + avg profit
3. Optimize parametry dla tego setupu
4. Trade SELECTIVELY - tylko perfect conditions
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
df['ma_100'] = df['close'].rolling(window=100).mean()

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

df['forward_1h'] = df['close'].shift(-4).pct_change(fill_method=None) * 100
df['forward_4h'] = df['close'].shift(-16).pct_change(fill_method=None) * 100

df['month'] = df['timestamp'].dt.to_period('M')

print("="*140)
print("MOODENG - ZNAJDŹ NAJLEPSZY EDGE")
print("="*140)
print()

# ============================================
# PART 1: MONTHLY REGIME ANALYSIS
# ============================================
print("="*140)
print("PART 1: MONTHLY REGIME - Które miesiące są favorable?")
print("="*140)
print()

monthly_regimes = []

for month in df['month'].unique():
    df_month = df[df['month'] == month].copy()

    month_return = ((df_month.iloc[-1]['close'] - df_month.iloc[0]['close']) / df_month.iloc[0]['close']) * 100
    avg_atr = df_month['atr_pct'].mean()
    avg_move = df_month['return_1h'].abs().mean()

    # Classify regime
    if month_return > 5:
        regime = 'BULL'
    elif month_return < -10:
        regime = 'BEAR'
    else:
        regime = 'CHOP'

    if avg_atr > 1.1:
        vol_regime = 'HIGH_VOL'
    elif avg_atr < 0.9:
        vol_regime = 'LOW_VOL'
    else:
        vol_regime = 'MED_VOL'

    monthly_regimes.append({
        'month': str(month),
        'return': month_return,
        'regime': regime,
        'vol_regime': vol_regime,
        'avg_atr': avg_atr,
        'avg_move': avg_move
    })

regimes_df = pd.DataFrame(monthly_regimes)

print(f"{'Month':<10} | {'Return%':<9} | {'Regime':<10} | {'Vol Regime':<12} | {'Avg ATR%':<10}")
print("-"*140)

for idx, row in regimes_df.iterrows():
    print(f"{row['month']:<10} | {row['return']:>7.1f}% | {row['regime']:<10} | {row['vol_regime']:<12} | {row['avg_atr']:>8.3f}%")

print()

# ============================================
# PART 2: SCAN ALL POSSIBLE SETUPS
# ============================================
print("="*140)
print("PART 2: SCAN WSZYSTKIE MOŻLIWE SETUPS")
print("="*140)
print()

all_setups = []

# SETUP 1: UPTREND CONTINUATION
uptrends = df[(df['close'] > df['ma_20'] * 1.015) & (df['ma_20'] > df['ma_50'])].copy()
if len(uptrends) > 50:
    setup_name = "UPTREND_CONTINUATION"
    avg_fwd = uptrends['forward_4h'].mean()
    win_rate = (uptrends['forward_4h'] > 0).sum() / len(uptrends) * 100
    avg_win = uptrends[uptrends['forward_4h'] > 0]['forward_4h'].mean()
    avg_loss = uptrends[uptrends['forward_4h'] < 0]['forward_4h'].mean()

    all_setups.append({
        'setup': setup_name,
        'count': len(uptrends),
        'win_rate': win_rate,
        'avg_fwd': avg_fwd,
        'avg_win': avg_win if not pd.isna(avg_win) else 0,
        'avg_loss': avg_loss if not pd.isna(avg_loss) else 0,
        'expectancy': avg_fwd
    })

# SETUP 2: DOWNTREND CONTINUATION
downtrends = df[(df['close'] < df['ma_20'] * 0.985) & (df['ma_20'] < df['ma_50'])].copy()
if len(downtrends) > 50:
    setup_name = "DOWNTREND_CONTINUATION"
    avg_fwd = -downtrends['forward_4h'].mean()  # Negative for SHORT
    win_rate = (downtrends['forward_4h'] < 0).sum() / len(downtrends) * 100
    avg_win = -downtrends[downtrends['forward_4h'] < 0]['forward_4h'].mean()
    avg_loss = -downtrends[downtrends['forward_4h'] > 0]['forward_4h'].mean()

    all_setups.append({
        'setup': setup_name,
        'count': len(downtrends),
        'win_rate': win_rate,
        'avg_fwd': avg_fwd,
        'avg_win': avg_win if not pd.isna(avg_win) else 0,
        'avg_loss': avg_loss if not pd.isna(avg_loss) else 0,
        'expectancy': avg_fwd
    })

# SETUP 3: VOLATILITY EXPANSION + UPTREND
vol_expansion_up = df[(df['atr_pct'] > 1.2) & (df['close'] > df['ma_20'])].copy()
if len(vol_expansion_up) > 50:
    setup_name = "VOL_EXPANSION_UP"
    avg_fwd = vol_expansion_up['forward_4h'].mean()
    win_rate = (vol_expansion_up['forward_4h'] > 0).sum() / len(vol_expansion_up) * 100
    avg_win = vol_expansion_up[vol_expansion_up['forward_4h'] > 0]['forward_4h'].mean()
    avg_loss = vol_expansion_up[vol_expansion_up['forward_4h'] < 0]['forward_4h'].mean()

    all_setups.append({
        'setup': setup_name,
        'count': len(vol_expansion_up),
        'win_rate': win_rate,
        'avg_fwd': avg_fwd,
        'avg_win': avg_win if not pd.isna(avg_win) else 0,
        'avg_loss': avg_loss if not pd.isna(avg_loss) else 0,
        'expectancy': avg_fwd
    })

# SETUP 4: VOLATILITY EXPANSION + DOWNTREND
vol_expansion_down = df[(df['atr_pct'] > 1.2) & (df['close'] < df['ma_20'])].copy()
if len(vol_expansion_down) > 50:
    setup_name = "VOL_EXPANSION_DOWN"
    avg_fwd = -vol_expansion_down['forward_4h'].mean()
    win_rate = (vol_expansion_down['forward_4h'] < 0).sum() / len(vol_expansion_down) * 100
    avg_win = -vol_expansion_down[vol_expansion_down['forward_4h'] < 0]['forward_4h'].mean()
    avg_loss = -vol_expansion_down[vol_expansion_down['forward_4h'] > 0]['forward_4h'].mean()

    all_setups.append({
        'setup': setup_name,
        'count': len(vol_expansion_down),
        'win_rate': win_rate,
        'avg_fwd': avg_fwd,
        'avg_win': avg_win if not pd.isna(avg_win) else 0,
        'avg_loss': avg_loss if not pd.isna(avg_loss) else 0,
        'expectancy': avg_fwd
    })

# SETUP 5: OVERSOLD BOUNCE (RSI < 30)
oversold = df[(df['rsi'] < 30) & (df['close'] < df['ma_50'])].copy()
if len(oversold) > 30:
    setup_name = "OVERSOLD_BOUNCE"
    avg_fwd = oversold['forward_4h'].mean()
    win_rate = (oversold['forward_4h'] > 0).sum() / len(oversold) * 100
    avg_win = oversold[oversold['forward_4h'] > 0]['forward_4h'].mean()
    avg_loss = oversold[oversold['forward_4h'] < 0]['forward_4h'].mean()

    all_setups.append({
        'setup': setup_name,
        'count': len(oversold),
        'win_rate': win_rate,
        'avg_fwd': avg_fwd,
        'avg_win': avg_win if not pd.isna(avg_win) else 0,
        'avg_loss': avg_loss if not pd.isna(avg_loss) else 0,
        'expectancy': avg_fwd
    })

# SETUP 6: OVERBOUGHT FADE (RSI > 70)
overbought = df[(df['rsi'] > 70) & (df['close'] > df['ma_50'])].copy()
if len(overbought) > 30:
    setup_name = "OVERBOUGHT_FADE"
    avg_fwd = -overbought['forward_4h'].mean()
    win_rate = (overbought['forward_4h'] < 0).sum() / len(overbought) * 100
    avg_win = -overbought[overbought['forward_4h'] < 0]['forward_4h'].mean()
    avg_loss = -overbought[overbought['forward_4h'] > 0]['forward_4h'].mean()

    all_setups.append({
        'setup': setup_name,
        'count': len(overbought),
        'win_rate': win_rate,
        'avg_fwd': avg_fwd,
        'avg_win': avg_win if not pd.isna(avg_win) else 0,
        'avg_loss': avg_loss if not pd.isna(avg_loss) else 0,
        'expectancy': avg_fwd
    })

# SETUP 7: LOW VOL BREAKOUT
low_vol_breakout = df[df['atr_pct'] < 0.7].copy()
low_vol_breakout['local_high'] = low_vol_breakout['high'].rolling(window=20, center=False).max().shift(1)
low_vol_breakout = low_vol_breakout[low_vol_breakout['high'] > low_vol_breakout['local_high']].copy()

if len(low_vol_breakout) > 30:
    setup_name = "LOW_VOL_BREAKOUT"
    avg_fwd = low_vol_breakout['forward_4h'].mean()
    win_rate = (low_vol_breakout['forward_4h'] > 0).sum() / len(low_vol_breakout) * 100
    avg_win = low_vol_breakout[low_vol_breakout['forward_4h'] > 0]['forward_4h'].mean()
    avg_loss = low_vol_breakout[low_vol_breakout['forward_4h'] < 0]['forward_4h'].mean()

    all_setups.append({
        'setup': setup_name,
        'count': len(low_vol_breakout),
        'win_rate': win_rate,
        'avg_fwd': avg_fwd,
        'avg_win': avg_win if not pd.isna(avg_win) else 0,
        'avg_loss': avg_loss if not pd.isna(avg_loss) else 0,
        'expectancy': avg_fwd
    })

# SETUP 8: STRONG UPTREND + PULLBACK
strong_up = df[(df['close'] > df['ma_20'] * 1.03) & (df['ma_20'] > df['ma_50'])].copy()
strong_up['pullback'] = strong_up['close'] < strong_up['close'].shift(4)
strong_up_pullback = strong_up[strong_up['pullback']].copy()

if len(strong_up_pullback) > 30:
    setup_name = "UPTREND_PULLBACK"
    avg_fwd = strong_up_pullback['forward_4h'].mean()
    win_rate = (strong_up_pullback['forward_4h'] > 0).sum() / len(strong_up_pullback) * 100
    avg_win = strong_up_pullback[strong_up_pullback['forward_4h'] > 0]['forward_4h'].mean()
    avg_loss = strong_up_pullback[strong_up_pullback['forward_4h'] < 0]['forward_4h'].mean()

    all_setups.append({
        'setup': setup_name,
        'count': len(strong_up_pullback),
        'win_rate': win_rate,
        'avg_fwd': avg_fwd,
        'avg_win': avg_win if not pd.isna(avg_win) else 0,
        'avg_loss': avg_loss if not pd.isna(avg_loss) else 0,
        'expectancy': avg_fwd
    })

# SETUP 9: STRONG DOWNTREND + BOUNCE
strong_down = df[(df['close'] < df['ma_20'] * 0.97) & (df['ma_20'] < df['ma_50'])].copy()
strong_down['bounce'] = strong_down['close'] > strong_down['close'].shift(4)
strong_down_bounce = strong_down[strong_down['bounce']].copy()

if len(strong_down_bounce) > 30:
    setup_name = "DOWNTREND_BOUNCE_SHORT"
    avg_fwd = -strong_down_bounce['forward_4h'].mean()
    win_rate = (strong_down_bounce['forward_4h'] < 0).sum() / len(strong_down_bounce) * 100
    avg_win = -strong_down_bounce[strong_down_bounce['forward_4h'] < 0]['forward_4h'].mean()
    avg_loss = -strong_down_bounce[strong_down_bounce['forward_4h'] > 0]['forward_4h'].mean()

    all_setups.append({
        'setup': setup_name,
        'count': len(strong_down_bounce),
        'win_rate': win_rate,
        'avg_fwd': avg_fwd,
        'avg_win': avg_win if not pd.isna(avg_win) else 0,
        'avg_loss': avg_loss if not pd.isna(avg_loss) else 0,
        'expectancy': avg_fwd
    })

# Display results
setups_df = pd.DataFrame(all_setups)
setups_df = setups_df.sort_values('expectancy', ascending=False)

print(f"{'Setup':<25} | {'Count':<7} | {'WR%':<7} | {'Avg Fwd':<10} | {'Avg Win':<10} | {'Avg Loss':<10} | {'Expectancy':<10}")
print("-"*140)

for idx, row in setups_df.iterrows():
    quality = "🔥" if row['expectancy'] > 0.5 and row['win_rate'] > 55 else ("✅" if row['expectancy'] > 0.2 else "⚠️ ")
    print(f"{row['setup']:<25} | {row['count']:<7} | {row['win_rate']:>5.1f}% | {row['avg_fwd']:>8.2f}% | {row['avg_win']:>8.2f}% | {row['avg_loss']:>8.2f}% | {row['expectancy']:>8.2f}% {quality}")

print()

# ============================================
# PART 3: BEST SETUP OPTIMIZATION
# ============================================
print("="*140)
print("PART 3: OPTIMIZE NAJLEPSZY SETUP")
print("="*140)
print()

best_setup = setups_df.iloc[0]

print(f"🏆 BEST SETUP: {best_setup['setup']}")
print(f"   Expectancy: {best_setup['expectancy']:.2f}%")
print(f"   Win Rate: {best_setup['win_rate']:.1f}%")
print(f"   Count: {best_setup['count']}")
print()

print("Teraz optymalizujemy parametry dla tego setupu...")
print()

print("="*140)
print("💡 WNIOSKI:")
print("="*140)
print()

if best_setup['expectancy'] > 0.3:
    print(f"✅ ZNALEZIONO EDGE!")
    print(f"   Best setup: {best_setup['setup']}")
    print(f"   Expected profit per trade: {best_setup['expectancy']:.2f}%")
    print(f"   Win rate: {best_setup['win_rate']:.1f}%")
    print()
    print(f"   💰 Z 10 trades/month @ {best_setup['expectancy']:.2f}% avg:")
    print(f"      Monthly return: ~{best_setup['expectancy'] * 10 * 0.05:.1f}% (5% risk per trade)")
    print()
    print("   Następny krok: Optimize parameters i stwórz production strategy")
else:
    print(f"⚠️  Najlepszy setup ma słaby edge ({best_setup['expectancy']:.2f}%)")
    print(f"   MOODENG może być zbyt trudny do tradowania")
    print(f"   Rozważ inny coin")

print("="*140)
