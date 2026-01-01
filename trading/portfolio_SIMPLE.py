"""
SIMPLE PORTFOLIO SIMULATION - Just process exits chronologically
No complex logic, just: exit → calculate P&L → update equity
"""
import pandas as pd
import numpy as np
import sys
sys.path.insert(0, '/workspaces/Carebiuro_windykacja')
from portfolio_simulation_FIXED import backtest_coin_FIXED, COINS

print('='*100)
print('💼 SIMPLE PORTFOLIO SIMULATION')
print('='*100)
print()

# Collect all trades from all coins
all_trades = []
for coin, config in COINS.items():
    df = pd.read_csv(config['file'])
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    trades = backtest_coin_FIXED(
        df, coin,
        rsi_low=config['rsi_low'],
        rsi_high=config['rsi_high'],
        limit_offset_pct=config['offset'],
        stop_atr_mult=config['sl'],
        tp_atr_mult=config['tp']
    )

    if len(trades) > 0:
        all_trades.append(trades)
        print(f'✅ {coin}: {len(trades)} trades')

# Combine all trades
combined = pd.concat(all_trades, ignore_index=True)
print()
print(f'Total trades: {len(combined)}')

# Sort by exit time (chronological)
combined = combined.sort_values('exit_time').reset_index(drop=True)

# Simple simulation: Process each exit chronologically
equity = 1000.0
results = []

for idx, trade in combined.iterrows():
    # 10% position size
    position_size = equity * 0.10

    # Calculate P&L
    dollar_pnl = position_size * (trade['pnl_pct'] / 100)

    # Update equity
    equity += dollar_pnl

    # Record
    results.append({
        'exit_time': trade['exit_time'],
        'coin': trade['coin'],
        'side': trade['side'],
        'pnl_pct': trade['pnl_pct'],
        'position_size': position_size,
        'dollar_pnl': dollar_pnl,
        'equity': equity,
        'exit_reason': trade['exit_reason']
    })

# Convert to dataframe
results_df = pd.DataFrame(results)

# Calculate drawdown
results_df['peak'] = results_df['equity'].cummax()
results_df['drawdown'] = results_df['equity'] - results_df['peak']
results_df['drawdown_pct'] = (results_df['drawdown'] / results_df['peak']) * 100

# Final stats
final_equity = results_df['equity'].iloc[-1]
total_return = ((final_equity - 1000) / 1000) * 100
max_dd = results_df['drawdown_pct'].min()
winners = len(results_df[results_df['pnl_pct'] > 0])
losers = len(results_df[results_df['pnl_pct'] < 0])

print()
print('='*100)
print('📊 FINAL RESULTS')
print('='*100)
print()
print(f'Starting: $1,000.00')
print(f'Final: ${final_equity:,.2f}')
print(f'Return: {total_return:+.2f}%')
print(f'Max DD: {max_dd:.2f}%')
print(f'Return/DD: {abs(total_return/max_dd):.2f}x')
print()
print(f'Trades: {len(results_df)}')
print(f'Winners: {winners} ({winners/len(results_df)*100:.1f}%)')
print(f'Losers: {losers} ({losers/len(results_df)*100:.1f}%)')
print()

# Per coin
print('PER COIN:')
print(f'{"Coin":<15} {"Trades":<8} {"Win%":<8} {"Total P&L"}')
print('-'*60)
for coin in sorted(COINS.keys()):
    coin_trades = results_df[results_df['coin'] == coin]
    if len(coin_trades) > 0:
        wins = len(coin_trades[coin_trades['pnl_pct'] > 0])
        win_pct = wins / len(coin_trades) * 100
        total_pnl = coin_trades['dollar_pnl'].sum()
        print(f'{coin:<15} {len(coin_trades):<8} {win_pct:<8.1f} ${total_pnl:+.2f}')

print()

# Find max DD point
max_dd_idx = results_df['drawdown_pct'].idxmin()
max_dd_trade = results_df.loc[max_dd_idx]
print('='*100)
print('MAX DRAWDOWN DETAILS')
print('='*100)
print(f'Date: {max_dd_trade["exit_time"]}')
print(f'Coin: {max_dd_trade["coin"]}')
print(f'Equity: ${max_dd_trade["equity"]:.2f}')
print(f'Peak: ${max_dd_trade["peak"]:.2f}')
print(f'DD: {max_dd_trade["drawdown_pct"]:.2f}%')
print()

# Show trades around max DD
print('TRADES AROUND MAX DD:')
for i in range(max(0, max_dd_idx-5), min(len(results_df), max_dd_idx+6)):
    t = results_df.loc[i]
    marker = ' ← MAX DD' if i == max_dd_idx else ''
    print(f'{t["exit_time"]} {t["coin"]:<15} {t["exit_reason"]:<5} {t["pnl_pct"]:>7.2f}% → ${t["equity"]:.2f} (DD: {t["drawdown_pct"]:.2f}%){marker}')

print()

# Save
results_df.to_csv('portfolio_SIMPLE.csv', index=False)
print('💾 Saved: portfolio_SIMPLE.csv')
