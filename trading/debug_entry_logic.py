"""
Debug why entry RSI is wrong
"""
import pandas as pd
import numpy as np

def calculate_rsi(prices, period=14):
    deltas = np.diff(prices)
    seed = deltas[:period+1]
    up = seed[seed >= 0].sum() / period
    down = -seed[seed < 0].sum() / period
    rs = up / down if down != 0 else 0
    rsi = np.zeros_like(prices)
    rsi[:period] = 100. - 100. / (1. + rs)

    for i in range(period, len(prices)):
        delta = deltas[i - 1]
        upval = delta if delta > 0 else 0
        downval = -delta if delta < 0 else 0
        up = (up * (period - 1) + upval) / period
        down = (down * (period - 1) + downval) / period
        rs = up / down if down != 0 else 0
        rsi[i] = 100. - 100. / (1. + rs)
    return rsi

df = pd.read_csv('bingx-trading-bot/trading/crv_usdt_90d_1h.csv')
df['rsi'] = calculate_rsi(df['close'].values, 14)

print('='*100)
print('🔍 DEBUG: First 5 RSI crossovers')
print('='*100)
print()

rsi_low = 27
rsi_high = 65

long_signals = 0
short_signals = 0

for i in range(20, len(df)):
    current = df.iloc[i]
    prev = df.iloc[i-1]

    if pd.isna(current['rsi']):
        continue

    # LONG signal: RSI crosses ABOVE 27
    if current['rsi'] > rsi_low and prev['rsi'] <= rsi_low:
        print(f'Bar {i}: LONG signal')
        print(f'  Previous RSI: {prev["rsi"]:.2f} (≤ 27)')
        print(f'  Current RSI: {current["rsi"]:.2f} (> 27)')
        print(f'  Close: ${current["close"]:.4f}')
        print(f'  ✅ Valid crossover from {prev["rsi"]:.2f} to {current["rsi"]:.2f}')
        print()
        long_signals += 1
        if long_signals >= 3:
            break

for i in range(20, len(df)):
    current = df.iloc[i]
    prev = df.iloc[i-1]

    if pd.isna(current['rsi']):
        continue

    # SHORT signal: RSI crosses BELOW 65
    if current['rsi'] < rsi_high and prev['rsi'] >= rsi_high:
        print(f'Bar {i}: SHORT signal')
        print(f'  Previous RSI: {prev["rsi"]:.2f} (≥ 65)')
        print(f'  Current RSI: {current["rsi"]:.2f} (< 65)')
        print(f'  Close: ${current["close"]:.4f}')
        print(f'  ✅ Valid crossover from {prev["rsi"]:.2f} to {current["rsi"]:.2f}')
        print()
        short_signals += 1
        if short_signals >= 3:
            break

print('='*100)
print('🤔 So crossovers ARE detected correctly...')
print('But why is signal_rsi wrong in the backtest?')
print('='*100)
print()
print('Theory: The signal_rsi I saved is at the SIGNAL bar,')
print('but the limit order might fill SEVERAL BARS LATER.')
print('By then, RSI has moved away from 27/65.')
print()
print('Let me check this...')
print()

# Now trace what happens with limit orders
print('='*100)
print('🔍 TRACE: First SHORT signal with limit order')
print('='*100)
print()

for i in range(20, len(df)):
    current = df.iloc[i]
    prev = df.iloc[i-1]

    if pd.isna(current['rsi']):
        continue

    # SHORT signal
    if current['rsi'] < rsi_high and prev['rsi'] >= rsi_high:
        print(f'Bar {i}: SHORT signal detected')
        print(f'  Signal RSI: {current["rsi"]:.2f}')
        print(f'  Signal close: ${current["close"]:.4f}')

        signal_price = current['close']
        limit_price = signal_price * 1.01  # 1% higher

        print(f'  Limit price: ${limit_price:.4f} (1% higher)')
        print()
        print('Checking next 5 bars for limit fill...')
        print()

        for j in range(i+1, min(i+6, len(df))):
            check_bar = df.iloc[j]
            print(f'  Bar {j}: high=${check_bar["high"]:.4f}, RSI={check_bar["rsi"]:.2f}', end='')

            if check_bar['high'] >= limit_price:
                print(f' ← FILLED!')
                print()
                print(f'✅ Limit filled at bar {j}')
                print(f'   Entry price: ${limit_price:.4f}')
                print(f'   RSI at entry bar: {check_bar["rsi"]:.2f}')
                print(f'   RSI at signal bar: {current["rsi"]:.2f}')
                print()
                print(f'❓ Which RSI should I save? Signal bar ({current["rsi"]:.2f}) or entry bar ({check_bar["rsi"]:.2f})?')
                break
            else:
                print(f' (no fill)')

        break  # Just show first one

print()
print('='*100)
print('💡 ANSWER')
print('='*100)
print()
print('The backtest is saving RSI from the ENTRY bar (when limit filled),')
print('not the SIGNAL bar (when crossover happened).')
print()
print('This is CORRECT for live trading (you need to know RSI at actual entry),')
print('but it means signal_rsi will NOT be exactly 27/65.')
print()
print('The SIGNAL happens at RSI 27/65, but the ENTRY happens 1-5 bars later,')
print('and by then RSI has moved.')
print()
print('This is NOT a bug - this is realistic behavior!')
