#!/usr/bin/env python3
import pandas as pd

df = pd.read_csv('fartcoin_6months_bingx_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# Filter Sept - Dec
df_filtered = df[df['timestamp'] >= '2025-09-01'].copy()

# Group by day
df_filtered['date'] = df_filtered['timestamp'].dt.date
daily = df_filtered.groupby('date').agg({
    'open': 'first',
    'close': 'last'
}).reset_index()

daily['color'] = daily.apply(lambda x: 'GREEN' if x['close'] > x['open'] else 'RED', axis=1)

# Count by month
daily['month'] = pd.to_datetime(daily['date']).dt.to_period('M')

print("="*80)
print("RED vs GREEN DAYS - FARTCOIN (Sept - Dec 2025)")
print("="*80)
print()

for month in sorted(daily['month'].unique()):
    month_data = daily[daily['month'] == month]
    green = (month_data['color'] == 'GREEN').sum()
    red = (month_data['color'] == 'RED').sum()
    ratio = green / red if red > 0 else float('inf')
    
    print(f"{str(month)}:")
    print(f"  Green Days: {green}")
    print(f"  Red Days: {red}")
    print(f"  Total: {len(month_data)}")
    print(f"  Green:Red Ratio: {ratio:.2f}")
    print()

# Overall
total_green = (daily['color'] == 'GREEN').sum()
total_red = (daily['color'] == 'RED').sum()
total_ratio = total_green / total_red if total_red > 0 else float('inf')

print("="*80)
print("OVERALL (Sept - Dec):")
print(f"  Green Days: {total_green}")
print(f"  Red Days: {total_red}")
print(f"  Total: {len(daily)}")
print(f"  Green:Red Ratio: {total_ratio:.2f}")
print("="*80)
