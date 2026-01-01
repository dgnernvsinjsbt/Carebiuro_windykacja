#!/usr/bin/env python3
"""
Simulate 9 separate $10 accounts with 100% position sizing per trade
Much higher risk, but also higher compounding
"""

import pandas as pd
import numpy as np

print("=" * 100)
print("SEPARATE ACCOUNTS SIMULATION - 100% POSITION SIZING")
print("=" * 100)
print("Setup: Each coin gets $10 starting capital, trades with 100% of equity")
print("Total starting capital: $90 (9 coins × $10)")
print()

# Load Sep 15 - Dec 7 trades
df_sep_dec = pd.read_csv('portfolio_trade_log_chronological.csv')
df_sep_dec['date'] = pd.to_datetime(df_sep_dec['date'])

# Load Dec 8-15 trades
df_dec_8_15 = pd.read_csv('dec8_15_all_trades.csv')
df_dec_8_15['entry_time'] = pd.to_datetime(df_dec_8_15['entry_time'])

# Combine all trades
df_sep_dec['symbol'] = df_sep_dec['coin'].apply(lambda x: x if 'USDT' in str(x) else f"{x}-USDT")

all_trades = []

# Add Sep-Dec 7 trades
for _, trade in df_sep_dec.iterrows():
    all_trades.append({
        'symbol': trade['symbol'],
        'date': trade['date'],
        'pnl_pct': trade['pnl_pct'],
        'exit_reason': trade['exit_reason'],
        'period': 'Sep-Dec7'
    })

# Add Dec 8-15 trades
for _, trade in df_dec_8_15.iterrows():
    all_trades.append({
        'symbol': trade['symbol'],
        'date': trade['entry_time'],
        'pnl_pct': trade['pnl_pct'],
        'exit_reason': trade['exit_reason'],
        'period': 'Dec8-15'
    })

# Convert to DataFrame
trades_df = pd.DataFrame(all_trades)
trades_df = trades_df.sort_values('date').reset_index(drop=True)

# Map symbol names
symbol_map = {
    'AIXBT-USDT': 'AIXBT-USDT', 'AIXBT': 'AIXBT-USDT',
    'MELANIA-USDT': 'MELANIA-USDT', 'MELANIA': 'MELANIA-USDT',
    'MOODENG-USDT': 'MOODENG-USDT', 'MOODENG': 'MOODENG-USDT',
    'PEPE-USDT': 'PEPE-USDT', 'PEPE': 'PEPE-USDT', '1000PEPE-USDT': 'PEPE-USDT',
    'DOGE-USDT': 'DOGE-USDT', 'DOGE': 'DOGE-USDT',
    'CRV-USDT': 'CRV-USDT', 'CRV': 'CRV-USDT',
    'TRUMPSOL-USDT': 'TRUMPSOL-USDT', 'TRUMPSOL': 'TRUMPSOL-USDT',
    'UNI-USDT': 'UNI-USDT', 'UNI': 'UNI-USDT',
    'XLM-USDT': 'XLM-USDT', 'XLM': 'XLM-USDT',
}

trades_df['symbol'] = trades_df['symbol'].map(symbol_map)

# Simulate each coin with $10 and 100% position sizing
results = []

print("\n" + "=" * 100)
print("DETAILED BREAKDOWN BY COIN:")
print("=" * 100)

for symbol in sorted(trades_df['symbol'].unique()):
    coin_trades = trades_df[trades_df['symbol'] == symbol].sort_values('date').reset_index(drop=True)

    capital = 10.0
    initial_capital = 10.0
    peak_capital = 10.0
    max_dd_pct = 0.0

    equity_curve = [capital]

    winners = 0
    losers = 0

    tp_count = 0
    sl_count = 0
    rsi_exit_count = 0

    # Track trades
    for idx, trade in coin_trades.iterrows():
        # 100% position sizing: entire capital at risk
        pnl_multiplier = 1 + (trade['pnl_pct'] / 100)
        capital = capital * pnl_multiplier

        equity_curve.append(capital)

        # Track peak and drawdown
        if capital > peak_capital:
            peak_capital = capital

        dd_pct = ((capital - peak_capital) / peak_capital) * 100
        if dd_pct < max_dd_pct:
            max_dd_pct = dd_pct

        # Win/loss counting
        if trade['pnl_pct'] > 0:
            winners += 1
        else:
            losers += 1

        # Exit reason counting
        if trade['exit_reason'] == 'TP':
            tp_count += 1
        elif trade['exit_reason'] == 'SL':
            sl_count += 1
        else:
            rsi_exit_count += 1

    final_capital = capital
    total_return = ((final_capital - initial_capital) / initial_capital) * 100
    win_rate = (winners / len(coin_trades)) * 100 if len(coin_trades) > 0 else 0

    # Period breakdown
    sep_dec_trades = coin_trades[coin_trades['period'] == 'Sep-Dec7']
    dec8_15_trades = coin_trades[coin_trades['period'] == 'Dec8-15']

    # Sep-Dec performance
    sep_capital = 10.0
    for _, trade in sep_dec_trades.iterrows():
        sep_capital *= (1 + trade['pnl_pct'] / 100)
    sep_return = ((sep_capital - 10.0) / 10.0) * 100

    # Dec 8-15 performance (starting from sep_capital)
    dec_capital = sep_capital
    for _, trade in dec8_15_trades.iterrows():
        dec_capital *= (1 + trade['pnl_pct'] / 100)
    dec_return = ((dec_capital - sep_capital) / sep_capital) * 100 if sep_capital > 0 else 0

    # Print detailed breakdown
    print(f"\n{'='*100}")
    print(f"COIN: {symbol}")
    print(f"{'='*100}")
    print(f"  Starting Capital:     ${initial_capital:.2f}")
    print(f"  Final Capital:        ${final_capital:.2f}")
    print(f"  Profit:               ${final_capital - initial_capital:+.2f}")
    print(f"  Total Return:         {total_return:+.2f}%")
    print(f"  Max Drawdown:         {max_dd_pct:.2f}%")
    print(f"  ")
    print(f"  Total Trades:         {len(coin_trades)}")
    print(f"  Winners:              {winners} ({win_rate:.1f}%)")
    print(f"  Losers:               {losers} ({100-win_rate:.1f}%)")
    print(f"  ")
    print(f"  Exit Reasons:")
    print(f"    Take Profit:        {tp_count} ({tp_count/len(coin_trades)*100:.1f}%)")
    print(f"    Stop Loss:          {sl_count} ({sl_count/len(coin_trades)*100:.1f}%)")
    print(f"    RSI Exit:           {rsi_exit_count} ({rsi_exit_count/len(coin_trades)*100:.1f}%)")
    print(f"  ")
    print(f"  Period Breakdown:")
    print(f"    Sep-Dec 7:          {len(sep_dec_trades)} trades, {sep_return:+.2f}% return (${10:.2f} → ${sep_capital:.2f})")
    print(f"    Dec 8-15:           {len(dec8_15_trades)} trades, {dec_return:+.2f}% return (${sep_capital:.2f} → ${dec_capital:.2f})")

    results.append({
        'symbol': symbol,
        'starting': initial_capital,
        'final': final_capital,
        'profit': final_capital - initial_capital,
        'return_pct': total_return,
        'max_dd_pct': max_dd_pct,
        'trades': len(coin_trades),
        'win_rate': win_rate,
        'tp_rate': (tp_count / len(coin_trades)) * 100,
        'sl_rate': (sl_count / len(coin_trades)) * 100,
        'sep_trades': len(sep_dec_trades),
        'dec_trades': len(dec8_15_trades),
        'sep_return': sep_return,
        'dec_return': dec_return
    })

results_df = pd.DataFrame(results).sort_values('profit', ascending=False)

# Summary table
print(f"\n{'='*100}")
print("SUMMARY TABLE (Ranked by Profit):")
print(f"{'='*100}")
print(f"{'Coin':<15} {'Final':>8} {'Profit':>9} {'Return%':>9} {'MaxDD%':>9} {'Trades':>7} {'Win%':>7} {'TP%':>6} {'SL%':>6}")
print("-" * 100)

for _, row in results_df.iterrows():
    print(f"{row['symbol']:<15} ${row['final']:>7.2f} ${row['profit']:>+8.2f} {row['return_pct']:>+8.2f}% "
          f"{row['max_dd_pct']:>+8.2f}% {row['trades']:>7} {row['win_rate']:>6.1f}% "
          f"{row['tp_rate']:>5.1f}% {row['sl_rate']:>5.1f}%")

# Totals
total_starting = results_df['starting'].sum()
total_final = results_df['final'].sum()
total_profit = results_df['profit'].sum()
total_return = ((total_final - total_starting) / total_starting) * 100

# Weighted average drawdown
weighted_dd = (results_df['max_dd_pct'] * results_df['starting']).sum() / total_starting

print("-" * 100)
print(f"{'TOTAL':<15} ${total_final:>7.2f} ${total_profit:>+8.2f} {total_return:>+8.2f}% {weighted_dd:>+8.2f}%")

print(f"\n{'='*100}")
print("PORTFOLIO STATISTICS:")
print(f"{'='*100}")

winners = results_df[results_df['profit'] > 0]
losers = results_df[results_df['profit'] <= 0]

print(f"\n  Starting Capital:     ${total_starting:.2f}")
print(f"  Final Capital:        ${total_final:.2f}")
print(f"  Total Profit:         ${total_profit:+.2f}")
print(f"  Total Return:         {total_return:+.2f}%")
print(f"  Weighted Max DD:      {weighted_dd:.2f}%")
print(f"  ")
print(f"  Winning Coins:        {len(winners)}/9 ({len(winners)/9*100:.1f}%)")
print(f"  Losing Coins:         {len(losers)}/9 ({len(losers)/9*100:.1f}%)")
print(f"  ")
print(f"  Best Performer:       {results_df.iloc[0]['symbol']} ({results_df.iloc[0]['return_pct']:+.2f}%)")
print(f"  Worst Performer:      {results_df.iloc[-1]['symbol']} ({results_df.iloc[-1]['return_pct']:+.2f}%)")
print(f"  ")
print(f"  Profit from Winners:  ${winners['profit'].sum():+.2f}")
print(f"  Loss from Losers:     ${losers['profit'].sum():+.2f}")

print(f"\n{'='*100}")
print("COMPARISON:")
print(f"{'='*100}")

# Compare to shared portfolio (from earlier)
shared_100_start = 100.0
shared_final = 133.65
shared_90_final = (shared_final / shared_100_start) * 90.0

print(f"\n{'Method':<30} {'Start':>10} {'Final':>10} {'Profit':>10} {'Return%':>10} {'Max DD%':>10}")
print("-" * 85)
print(f"{'Separate 100% Accounts':<30} ${total_starting:>9.2f} ${total_final:>9.2f} ${total_profit:>+9.2f} {total_return:>+9.2f}% {weighted_dd:>+9.2f}%")
print(f"{'Shared 10% Portfolio':<30} ${90.0:>9.2f} ${shared_90_final:>9.2f} ${shared_90_final-90:>+9.2f} {(shared_90_final-90)/90*100:>+9.2f}% {-3.23:>+9.2f}%")

diff_profit = total_final - shared_90_final

print(f"\n{'DIFFERENCE':<30} ${0:>9.2f} ${diff_profit:>9.2f} ${diff_profit:>+9.2f} {total_return - (shared_90_final-90)/90*100:>+9.2f}pp {weighted_dd - (-3.23):>+9.2f}pp")

print(f"\n{'='*100}")
print("ANALYSIS:")
print(f"{'='*100}")

if total_final > shared_90_final:
    print(f"\n  ✅ Separate 100% accounts OUTPERFORMED by ${diff_profit:.2f}")
    print(f"     → Aggressive position sizing + compounding beat diversification")
else:
    print(f"\n  ⚠️ Shared 10% portfolio performed BETTER by ${abs(diff_profit):.2f}")
    print(f"     → Conservative sizing + diversification beat aggressive compounding")

if abs(weighted_dd) < 3.23:
    print(f"  ✅ Separate accounts had LOWER drawdown ({weighted_dd:.2f}% vs -3.23%)")
else:
    print(f"  ❌ Separate accounts had HIGHER drawdown ({weighted_dd:.2f}% vs -3.23%)")

print(f"\n  💀 LEVERAGE WARNING:")
print(f"     Max Drawdown: {weighted_dd:.2f}%")
print(f"     With 5x leverage: {weighted_dd * 5:.2f}% (account loss)")
print(f"     With 10x leverage: {weighted_dd * 10:.2f}% (account loss)")

if abs(weighted_dd * 10) > 50:
    print(f"     ❌ UNSAFE for 10x leverage (would exceed -50% loss)")
elif abs(weighted_dd * 5) > 30:
    print(f"     ⚠️ RISKY for 5x leverage (would exceed -30% loss)")
else:
    print(f"     ✅ Safe for moderate leverage")
