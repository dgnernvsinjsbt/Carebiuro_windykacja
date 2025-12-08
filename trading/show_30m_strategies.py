import pandas as pd

# Read the comparison results
df = pd.read_csv('results/comparison_15m_vs_30m.csv')

# Filter for 30M timeframe
df_30m = df[df['Timeframe'] == '30M'].copy()

# Sort by P/L descending
df_30m = df_30m.sort_values('P/L (%)', ascending=False)

print("=" * 80)
print("STRATEGIE SHORTUJĄCE NA 30M - WSZYSTKIE TOKENY")
print("=" * 80)
print(f"\nKonfiguracja: EMA 3/15 crossover + momentum filters\n")

for _, row in df_30m.iterrows():
    token = row['Token']
    pl = row['P/L (%)']
    trades = row['Trades']
    win_rate = row['Win Rate (%)']
    max_dd = row['Max DD (%)']
    risk_reward = row['Risk:Reward']
    
    print(f"\n{token}:")
    print(f"  P/L:        {pl:>8.1f}%")
    print(f"  Trades:     {trades:>8.0f}")
    print(f"  Win Rate:   {win_rate:>8.1f}%")
    print(f"  Max DD:     {max_dd:>8.1f}%")
    print(f"  Risk:Reward:{risk_reward:>8.2f}")

print("\n" + "=" * 80)
print(f"ŚREDNIA WSZYSTKICH TOKENÓW:")
avg_pl = df_30m['P/L (%)'].mean()
avg_trades = df_30m['Trades'].mean()
avg_wr = df_30m['Win Rate (%)'].mean()
avg_dd = df_30m['Max DD (%)'].mean()
avg_rr = df_30m['Risk:Reward'].mean()

print(f"  P/L:        {avg_pl:>8.1f}%")
print(f"  Trades:     {avg_trades:>8.1f}")
print(f"  Win Rate:   {avg_wr:>8.1f}%")
print(f"  Max DD:     {avg_dd:>8.1f}%")
print(f"  Risk:Reward:{avg_rr:>8.2f}")
print("=" * 80)

