"""
Analyze position sizes: Fixed vs Risk-Based
"""
import pandas as pd

df_risk = pd.read_csv('portfolio_RISK_BASED.csv')

print('='*80)
print('🔍 POSITION SIZE ANALYSIS - Risk-Based 1%')
print('='*80)
print()

# Position size stats
print(f'Average Position Size: {df_risk["position_pct"].mean():.2f}%')
print(f'Median Position Size: {df_risk["position_pct"].median():.2f}%')
print(f'Min Position Size: {df_risk["position_pct"].min():.2f}%')
print(f'Max Position Size: {df_risk["position_pct"].max():.2f}% (CAPPED at 50%)')
print()

# Distribution
print('Position Size Distribution:')
print(f'  > 40%: {len(df_risk[df_risk["position_pct"] > 40])} trades ({len(df_risk[df_risk["position_pct"] > 40])/len(df_risk)*100:.1f}%)')
print(f'  30-40%: {len(df_risk[(df_risk["position_pct"] >= 30) & (df_risk["position_pct"] <= 40)])} trades')
print(f'  20-30%: {len(df_risk[(df_risk["position_pct"] >= 20) & (df_risk["position_pct"] < 30)])} trades')
print(f'  < 20%: {len(df_risk[df_risk["position_pct"] < 20])} trades')
print()

# How many hit the 50% cap?
capped = len(df_risk[df_risk["position_pct"] >= 49.9])
print(f'Trades that hit 50% cap: {capped} ({capped/len(df_risk)*100:.1f}%)')
print()

# Show the logic
print('='*80)
print('💡 WHY ARE POSITION SIZES SO LARGE?')
print('='*80)
print()
print('Risk-Based Formula: Position Size = (Equity × Risk%) / Stop Loss %')
print()
print('Example with $1000 equity, 1% risk:')
print('-'*80)
print(f'{"Stop Loss %":<15} {"Risk Amount":<15} {"Position Size":<20} {"Position %"}')
print('-'*80)

for sl in [0.5, 1.0, 1.5, 2.0, 3.0]:
    risk_amt = 1000 * 0.01
    pos_size = risk_amt / (sl / 100)
    pos_pct = (pos_size / 1000) * 100
    capped = min(pos_size, 500)
    capped_pct = (capped / 1000) * 100

    if pos_size > 500:
        print(f'{sl:.1f}%            ${risk_amt:<14.2f} ${pos_size:<18,.2f} {pos_pct:.1f}% → CAPPED at 50%')
    else:
        print(f'{sl:.1f}%            ${risk_amt:<14.2f} ${pos_size:<18,.2f} {pos_pct:.1f}%')

print()
print('='*80)
print('🎯 KEY INSIGHT')
print('='*80)
print()
print('Risk-Based 1% does NOT mean "use 1% of equity per trade"')
print('It means "risk losing 1% if stop loss hits"')
print()
print('With tight stops (1-1.5% ATR), position sizes become HUGE:')
print('  - 1.5% stop → 66% position size (capped at 50%)')
print('  - 1.0% stop → 100% position size (capped at 50%)')
print()
print('This INCREASES risk compared to fixed 10% sizing!')
print()

# Show actual examples from the trades
print('='*80)
print('📋 REAL EXAMPLES FROM BACKTEST')
print('='*80)
print()

# Sort by position size
df_sorted = df_risk.sort_values('position_pct', ascending=False)

print(f'{"Coin":<15} {"Stop %":<10} {"Position %":<12} {"Portfolio Impact":<15} {"PnL %"}')
print('-'*80)
for idx, row in df_sorted.head(10).iterrows():
    print(f'{row["coin"]:<15} {row["stop_loss_pct"]:<10.2f} {row["position_pct"]:<12.2f} {row["portfolio_impact"]:<15.2f} {row["pnl_pct"]:.2f}%')

print()
print('Notice: Tighter stops → Larger position sizes → Bigger portfolio swings!')
print()

# Compare to fixed 10%
print('='*80)
print('📊 FIXED 10% vs RISK-BASED 1% COMPARISON')
print('='*80)
print()
print(f'{"Metric":<25} {"Fixed 10%":<15} {"Risk-Based 1%"}')
print('-'*80)
print(f'{"Position Size":<25} {"Always 10%":<15} {"28-50% avg 37%"}')
print(f'{"Largest Loss (Trade)":<25} {"-3.6%":<15} {"-3.6%"}')
print(f'{"Largest Loss (Portfolio)":<25} {"-0.36%":<15} {"-1.03%"}')
print(f'{"Max Drawdown":<25} {"-1.69%":<15} {"-4.12%"}')
print(f'{"Final Return":<25} {"+35.19%":<15} {"+101.17%"}')
print()
print('Trade-off: 2.9x higher returns, but 2.4x larger drawdowns')
print('R/R improved from 20.78x → 24.58x (+18%)')
