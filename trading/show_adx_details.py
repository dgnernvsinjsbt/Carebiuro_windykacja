"""Quick check of ADX filter performance"""
import pandas as pd
import numpy as np

def calculate_adx(df, period=14):
    df['high_diff'] = df['high'].diff()
    df['low_diff'] = -df['low'].diff()
    df['plus_dm'] = np.where((df['high_diff'] > df['low_diff']) & (df['high_diff'] > 0), df['high_diff'], 0)
    df['minus_dm'] = np.where((df['low_diff'] > df['high_diff']) & (df['low_diff'] > 0), df['low_diff'], 0)
    df['tr'] = np.maximum(df['high'] - df['low'], np.maximum(
        abs(df['high'] - df['close'].shift(1)), abs(df['low'] - df['close'].shift(1))))
    df['plus_di'] = 100 * (df['plus_dm'].ewm(alpha=1/period, adjust=False).mean() /
                            df['tr'].ewm(alpha=1/period, adjust=False).mean())
    df['minus_di'] = 100 * (df['minus_dm'].ewm(alpha=1/period, adjust=False).mean() /
                             df['tr'].ewm(alpha=1/period, adjust=False).mean())
    df['dx'] = 100 * abs(df['plus_di'] - df['minus_di']) / (df['plus_di'] + df['minus_di'])
    df['adx'] = df['dx'].ewm(alpha=1/period, adjust=False).mean()
    return df

print('ADX Analysis by Month')
print('='*80)

months = [
    ('June', 'melania_june_2025_15m.csv'),
    ('July', 'melania_july_2025_15m.csv'),
    ('August', 'melania_august_2025_15m.csv'),
    ('September', 'melania_september_2025_15m.csv'),
    ('October', 'melania_october_2025_15m.csv'),
    ('November', 'melania_november_2025_15m.csv'),
    ('December', 'melania_december_2025_15m.csv'),
]

for month_name, filename in months:
    df = pd.read_csv(filename)
    df = calculate_adx(df)

    avg_adx = df['adx'].mean()
    median_adx = df['adx'].median()
    pct_above_20 = (df['adx'] > 20).sum() / len(df) * 100
    pct_above_25 = (df['adx'] > 25).sum() / len(df) * 100
    pct_above_30 = (df['adx'] > 30).sum() / len(df) * 100

    print(f'{month_name:12} | Avg ADX: {avg_adx:5.1f} | >20: {pct_above_20:5.1f}% | '
          f'>25: {pct_above_25:5.1f}% | >30: {pct_above_30:5.1f}%')
