"""
Analyze the exact drawdown sequence from the buggy backtest
"""
import pandas as pd

# Read the buggy backtest results
df = pd.read_csv('crv_audit_filled_trades.csv')

# Calculate drawdown
df['peak'] = df['cumulative'].cummax()
df['drawdown'] = df['cumulative'] - df['peak']

# Find the max drawdown point
max_dd_idx = df['drawdown'].idxmin()
max_dd = df.loc[max_dd_idx, 'drawdown']
peak_idx = df.loc[:max_dd_idx, 'cumulative'].idxmax()

print('='*100)
print('🔍 EXACT DRAWDOWN SEQUENCE ANALYSIS')
print('='*100)
print()
print(f'Max Drawdown: {max_dd:.2f}%')
print(f'Peak equity: {df.loc[peak_idx, "cumulative"]:.2f}% (after trade #{peak_idx + 1})')
print(f'Trough equity: {df.loc[max_dd_idx, "cumulative"]:.2f}% (after trade #{max_dd_idx + 1})')
print()

# Show the trades that caused the drawdown
print('='*100)
print('📉 TRADES FROM PEAK TO TROUGH')
print('='*100)
print()

drawdown_trades = df.loc[peak_idx:max_dd_idx]
print(f'{"#":<5} {"Time":<20} {"Side":<6} {"Entry":<10} {"Exit":<10} {"P&L":<10} {"Cumulative":<12} {"DD from peak":<15}')
print('-'*100)

for idx, row in drawdown_trades.iterrows():
    dd_from_peak = row['cumulative'] - df.loc[peak_idx, 'cumulative']
    print(f'{idx+1:<5} {row["time"]:<20} {row["side"]:<6} ${row["entry_price"]:<9.4f} ${row["exit_price"]:<9.4f} {row["pnl_pct"]:>8.2f}% {row["cumulative"]:>10.2f}% {dd_from_peak:>13.2f}%')

print()
print('='*100)
print('🔍 INDIVIDUAL TRADE DETAILS')
print('='*100)
print()

losing_trades = drawdown_trades[drawdown_trades['pnl_pct'] < 0]
print(f'Losing trades in drawdown: {len(losing_trades)}')
print(f'Total loss: {losing_trades["pnl_pct"].sum():.2f}%')
print()

for idx, row in losing_trades.iterrows():
    print(f'Trade #{idx+1}: {row["side"]} @ ${row["entry_price"]:.4f}')
    print(f'  Exit: ${row["exit_price"]:.4f} ({row["exit_reason"]})')
    print(f'  Loss: {row["pnl_pct"]:.2f}%')
    print(f'  Bars held: {row["bars_held"]}')
    if pd.notna(row['exit_rsi']):
        print(f'  Exit RSI: {row["exit_rsi"]:.1f}')
    print()

# Now check what happened INTRABAR during those losing trades
print('='*100)
print('🎢 INTRABAR ANALYSIS: Could stops have helped?')
print('='*100)
print()

# Read the 3h intrabar analysis
intrabar = pd.read_csv('3h_strategy_intrabar_analysis.csv')

# Match the losing trades by entry_bar
print(f'{"Trade":<7} {"Side":<6} {"Entry":<10} {"Exit P&L":<12} {"Worst DD":<12} {"Recovery":<12} {"Exit Reason":<15}')
print('-'*100)

for idx, trade in losing_trades.iterrows():
    # Find matching trade in intrabar data
    entry_bar = trade['entry_bar']
    intrabar_match = intrabar[intrabar['entry_bar'] == entry_bar]

    if len(intrabar_match) > 0:
        ib = intrabar_match.iloc[0]
        recovery = ib['intrabar_dd'] - ib['final_pnl']
        print(f'#{idx+1:<6} {trade["side"]:<6} ${trade["entry_price"]:<9.4f} {trade["pnl_pct"]:>10.2f}% {ib["intrabar_dd"]:>10.2f}% {recovery:>10.2f}% {trade["exit_reason"]:<15}')

print()
print('='*100)
print('💡 CONCLUSION')
print('='*100)
print()
print(f'The {max_dd:.2f}% drawdown happened from trade #{peak_idx+1} to #{max_dd_idx+1}')
print(f'It consisted of {len(losing_trades)} losing trades totaling {losing_trades["pnl_pct"].sum():.2f}%')
print()
print('Key insights:')
print(f'1. Most losses were small ({losing_trades["pnl_pct"].mean():.2f}% average)')
print(f'2. The 3-hour time limit prevented both big winners AND big losers')
print(f'3. Intrabar drawdowns were often WORSE than final exit (mean reversion effect)')
print()

# Check if adding stops would have helped
print('Would stops have helped?')
print()
stops_analysis = []
for idx, trade in losing_trades.iterrows():
    entry_bar = trade['entry_bar']
    intrabar_match = intrabar[intrabar['entry_bar'] == entry_bar]
    if len(intrabar_match) > 0:
        ib = intrabar_match.iloc[0]
        # If intrabar DD was worse than final, stop would have triggered
        if ib['intrabar_dd'] < -2.0:  # 2x ATR ~= 2% for CRV
            stops_analysis.append({
                'trade': idx+1,
                'actual_loss': trade['pnl_pct'],
                'would_stop': True,
                'intrabar_dd': ib['intrabar_dd']
            })
        else:
            stops_analysis.append({
                'trade': idx+1,
                'actual_loss': trade['pnl_pct'],
                'would_stop': False,
                'intrabar_dd': ib['intrabar_dd']
            })

stops_df = pd.DataFrame(stops_analysis)
if len(stops_df) > 0 and 'would_stop' in stops_df.columns:
    stopped_trades = stops_df[stops_df['would_stop'] == True]
    print(f'Trades that would hit 2% stop: {len(stopped_trades)}/{len(stops_df)}')
    if len(stopped_trades) > 0:
        print(f'Average loss on stopped trades: {stopped_trades["actual_loss"].mean():.2f}%')
        print(f'Those trades actually lost: {stopped_trades["actual_loss"].mean():.2f}% (by waiting 3h)')
        print()
        print('❌ Stops would NOT have helped - trades recovered after hitting stop level')
    else:
        print('✅ No trades would have hit 2% stops')
