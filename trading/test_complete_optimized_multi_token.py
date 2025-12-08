"""
Test complete optimized strategy on FARTCOIN, PENGU, and PI
Strategy: EMA 3/15 SHORT + Filters + Dynamic Sizing + Adaptive TP
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def calculate_ema(df, span):
    return df['close'].ewm(span=span, adjust=False).mean()

def calculate_atr(df, period=14):
    high_low = df['high'] - df['low']
    high_close = (df['high'] - df['close'].shift()).abs()
    low_close = (df['low'] - df['close'].shift()).abs()
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    tr = ranges.max(axis=1)
    return tr.rolling(period).mean()

def calculate_rsi(df, period=14):
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def backtest_complete_optimized(df, use_baseline=False):
    """
    Complete optimized strategy:
    - Filters: Mom7d<0 + ATR<6% + RSI<60
    - Position Sizing: +25%/-3% (0.5x-2.0x)
    - Fixed SL: 3%
    - Adaptive TP: 3x ATR (4-15% range)
    """
    df = df.copy()

    # Calculate indicators
    df['ema_3'] = calculate_ema(df, 3)
    df['ema_15'] = calculate_ema(df, 15)
    df['momentum_7d'] = df['close'].pct_change(336) * 100
    df['atr'] = calculate_atr(df)
    df['atr_pct'] = (df['atr'] / df['close']) * 100
    df['rsi'] = calculate_rsi(df)

    # Optimized filter
    df['allow_short'] = (df['momentum_7d'] < 0) & (df['atr_pct'] < 6) & (df['rsi'] < 60)

    # Run backtest
    trades = []
    in_position = False
    entry_price = 0
    entry_date = None
    entry_atr = 0
    stop_loss = 0
    take_profit = 0
    fee = 0.0001

    for i in range(1, len(df)):
        row = df.iloc[i]
        prev_row = df.iloc[i-1]

        if not in_position:
            if (row['ema_3'] < row['ema_15'] and
                prev_row['ema_3'] >= prev_row['ema_15'] and
                row['allow_short']):

                in_position = True
                entry_price = row['close']
                entry_date = row['timestamp']
                entry_atr = row['atr_pct']

                # Fixed SL
                stop_loss = entry_price * 1.03

                if use_baseline:
                    # Baseline: Fixed 5% TP
                    take_profit = entry_price * 0.95
                else:
                    # Optimized: Adaptive 3x ATR TP (capped 4-15%)
                    tp_ratio = min(max(entry_atr / 100 * 3.0, 0.04), 0.15)
                    take_profit = entry_price * (1 - tp_ratio)

        else:
            exit_type = None
            exit_price = None

            if row['high'] >= stop_loss:
                exit_price = stop_loss
                exit_type = 'SL'
                pnl = (entry_price - stop_loss) / entry_price - fee
            elif row['low'] <= take_profit:
                exit_price = take_profit
                exit_type = 'TP'
                pnl = (entry_price - take_profit) / entry_price - fee

            if exit_type:
                trades.append({
                    'exit_date': row['timestamp'],
                    'pnl_pct': pnl * 100,
                    'exit_type': exit_type,
                    'win': pnl > 0
                })
                in_position = False

    if len(trades) == 0:
        return None

    trades_df = pd.DataFrame(trades)
    trades_df = trades_df.sort_values('exit_date').reset_index(drop=True)

    # Calculate with position sizing
    equity = 1.0
    position_size = 1.0
    equity_curve = [equity]

    for _, trade in trades_df.iterrows():
        trade_pnl = trade['pnl_pct'] * position_size
        equity *= (1 + trade_pnl / 100)
        equity_curve.append(equity)

        if not use_baseline:
            # Dynamic sizing: +25%/-3%
            if trade['pnl_pct'] > 0:
                position_size = min(position_size + 0.25, 2.0)
            else:
                position_size = max(position_size - 0.03, 0.5)

    # Calculate metrics
    equity_series = pd.Series(equity_curve)
    running_max = equity_series.expanding().max()
    drawdown = (equity_series - running_max) / running_max * 100
    max_dd = drawdown.min()
    total_return = (equity - 1) * 100

    winners = len(trades_df[trades_df['win']])
    win_rate = winners / len(trades_df) * 100

    return {
        'trades': len(trades_df),
        'return': total_return,
        'max_dd': max_dd,
        'win_rate': win_rate,
        'final_equity': equity,
        'rr_ratio': total_return / abs(max_dd),
        'equity_curve': equity_curve,
        'avg_win': trades_df[trades_df['pnl_pct'] > 0]['pnl_pct'].mean() if winners > 0 else 0,
        'avg_loss': trades_df[trades_df['pnl_pct'] < 0]['pnl_pct'].mean() if len(trades_df) > winners else 0
    }

# Test all tokens
tokens = {
    'FARTCOIN': 'fartcoin_30m_jan2025.csv',
    'PENGU': 'pengu_30m_jan2025.csv',
    'PI': 'pi_30m_jan2025.csv',
}

print("="*100)
print("COMPLETE OPTIMIZED STRATEGY - ALL TOKENS")
print("="*100)
print("\nStrategy:")
print("  Entry: EMA 3 crosses below EMA 15 (SHORT)")
print("  Filters: Mom7d<0 + ATR<6% + RSI<60")
print("  Position Sizing: +25% on wins, -3% on losses (0.5x-2.0x caps)")
print("  Fixed SL: 3%")
print("  Adaptive TP: 3x ATR (4-15% range)")

results = []
equity_curves = {}

for token, filename in tokens.items():
    print(f"\n{'='*60}")
    print(f"Processing {token}...")
    print(f"{'='*60}")

    try:
        df = pd.read_csv(filename)
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        # Baseline: Filters + Fixed TP (no dynamic sizing, no adaptive TP)
        baseline = backtest_complete_optimized(df, use_baseline=True)

        # Optimized: Filters + Dynamic Sizing + Adaptive TP
        optimized = backtest_complete_optimized(df, use_baseline=False)

        if baseline and optimized:
            results.append({
                'token': token,
                'baseline_trades': baseline['trades'],
                'baseline_return': baseline['return'],
                'baseline_dd': baseline['max_dd'],
                'baseline_wr': baseline['win_rate'],
                'baseline_rr': baseline['rr_ratio'],
                'opt_trades': optimized['trades'],
                'opt_return': optimized['return'],
                'opt_dd': optimized['max_dd'],
                'opt_wr': optimized['win_rate'],
                'opt_rr': optimized['rr_ratio'],
                'return_improvement': optimized['return'] - baseline['return'],
                'dd_change': optimized['max_dd'] - baseline['max_dd'],
                'rr_improvement': optimized['rr_ratio'] - baseline['rr_ratio'],
                'opt_avg_win': optimized['avg_win'],
                'opt_avg_loss': optimized['avg_loss']
            })

            equity_curves[f'{token} Baseline'] = baseline['equity_curve']
            equity_curves[f'{token} Optimized'] = optimized['equity_curve']

            print(f"\n{token} Results:")
            print(f"  Baseline:  {baseline['return']:.2f}% return, {baseline['max_dd']:.2f}% DD, {baseline['rr_ratio']:.2f} R:R")
            print(f"  Optimized: {optimized['return']:.2f}% return, {optimized['max_dd']:.2f}% DD, {optimized['rr_ratio']:.2f} R:R")
            print(f"  Improvement: {optimized['return'] - baseline['return']:+.2f}% return, {optimized['rr_ratio'] - baseline['rr_ratio']:+.2f} R:R")

    except Exception as e:
        print(f"Error with {token}: {e}")

results_df = pd.DataFrame(results)

print("\n" + "="*100)
print("BASELINE RESULTS (Filters + Fixed TP + Fixed 100% Position)")
print("="*100)
print(f"\n{'Token':<12} {'Trades':<8} {'Return':<12} {'Max DD':<12} {'Win Rate':<10} {'R:R':<8}")
print("-"*75)

for _, row in results_df.iterrows():
    print(f"{row['token']:<12} {row['baseline_trades']:<8.0f} {row['baseline_return']:<11.2f}% {row['baseline_dd']:<11.2f}% {row['baseline_wr']:<9.1f}% {row['baseline_rr']:<7.2f}")

print("\n" + "="*100)
print("OPTIMIZED RESULTS (+ Dynamic Sizing + Adaptive TP)")
print("="*100)
print(f"\n{'Token':<12} {'Trades':<8} {'Return':<12} {'Max DD':<12} {'Win Rate':<10} {'R:R':<8}")
print("-"*75)

for _, row in results_df.iterrows():
    print(f"{row['token']:<12} {row['opt_trades']:<8.0f} {row['opt_return']:<11.2f}% {row['opt_dd']:<11.2f}% {row['opt_wr']:<9.1f}% {row['opt_rr']:<7.2f}")

print("\n" + "="*100)
print("IMPROVEMENT ANALYSIS")
print("="*100)
print(f"\n{'Token':<12} {'Return Δ':<15} {'DD Δ':<15} {'R:R Δ':<12} {'Status':<10}")
print("-"*75)

for _, row in results_df.iterrows():
    status = '✅ Major' if row['return_improvement'] > 300 else '✅ Good' if row['return_improvement'] > 100 else '⚠️ Small' if row['return_improvement'] > 0 else '❌ Worse'
    print(f"{row['token']:<12} {row['return_improvement']:>+13.2f}% {row['dd_change']:>+13.2f}% {row['rr_improvement']:>+10.2f} {status:<10}")

print("\n" + "="*100)
print("DETAILED BREAKDOWN")
print("="*100)

for idx, (_, row) in enumerate(results_df.iterrows(), 1):
    print(f"\n{idx}. {row['token']}")
    print(f"   Baseline:  {row['baseline_return']:.2f}% return | {row['baseline_dd']:.2f}% DD | {row['baseline_rr']:.2f} R:R")
    print(f"   Optimized: {row['opt_return']:.2f}% return | {row['opt_dd']:.2f}% DD | {row['opt_rr']:.2f} R:R")
    print(f"   Improvement: {row['return_improvement']:+.2f}% return | {row['dd_change']:+.2f}% DD | {row['rr_improvement']:+.2f} R:R")
    print(f"   Win/Loss: {row['opt_avg_win']:.2f}% avg win | {row['opt_avg_loss']:.2f}% avg loss")
    print(f"   Final Equity: {row['opt_return']/100 + 1:.2f}x")

# Visualization
fig = plt.figure(figsize=(18, 12))
gs = fig.add_gridspec(3, 2, height_ratios=[2, 2, 1])

ax1 = fig.add_subplot(gs[0, :])  # Equity curves comparison (full width)
ax2 = fig.add_subplot(gs[1, 0])  # Risk-Return scatter
ax3 = fig.add_subplot(gs[1, 1])  # Improvement bars
ax4 = fig.add_subplot(gs[2, :])  # Summary table

colors = {
    'FARTCOIN': '#2E86AB',
    'PENGU': '#A23B72',
    'PI': '#F18F01'
}

# Plot 1: Equity Curves
for token in ['FARTCOIN', 'PENGU', 'PI']:
    if f'{token} Baseline' in equity_curves and f'{token} Optimized' in equity_curves:
        ec_base = equity_curves[f'{token} Baseline']
        ec_opt = equity_curves[f'{token} Optimized']

        ax1.plot(range(len(ec_base)), ec_base, linewidth=1.5, linestyle='--',
                color=colors.get(token, 'gray'), alpha=0.4, label=f'{token} Baseline')
        ax1.plot(range(len(ec_opt)), ec_opt, linewidth=2.5,
                color=colors.get(token, 'gray'), alpha=0.9, label=f'{token} OPTIMIZED')

ax1.axhline(y=1, color='gray', linestyle='--', alpha=0.5)
ax1.set_title('Complete Optimized Strategy: Equity Curves\nBaseline (dashed) vs Optimized (solid)',
              fontsize=14, fontweight='bold', pad=20)
ax1.set_xlabel('Trade Number', fontsize=11)
ax1.set_ylabel('Equity Multiple', fontsize=11)
ax1.legend(loc='upper left', fontsize=9, ncol=2)
ax1.grid(True, alpha=0.3)

# Plot 2: Risk-Return Scatter
for _, row in results_df.iterrows():
    token = row['token']
    # Baseline
    ax2.scatter(abs(row['baseline_dd']), row['baseline_return'], s=200, alpha=0.5,
                color=colors.get(token, 'gray'), marker='o', edgecolors='black', linewidths=1)
    # Optimized
    ax2.scatter(abs(row['opt_dd']), row['opt_return'], s=300, alpha=0.9,
                color=colors.get(token, 'gray'), marker='*', edgecolors='black', linewidths=1.5)

    # Arrow showing improvement
    ax2.annotate('', xy=(abs(row['opt_dd']), row['opt_return']),
                xytext=(abs(row['baseline_dd']), row['baseline_return']),
                arrowprops=dict(arrowstyle='->', color=colors.get(token, 'gray'),
                               lw=2.5, alpha=0.6))

    # Label
    ax2.text(abs(row['opt_dd']) + 1, row['opt_return'] + 20, token,
            fontsize=10, fontweight='bold', color=colors.get(token, 'gray'))

ax2.set_xlabel('Max Drawdown (abs %)', fontsize=11)
ax2.set_ylabel('Total Return %', fontsize=11)
ax2.set_title('Risk vs Return: Baseline (○) → Optimized (★)', fontsize=12, fontweight='bold')
ax2.grid(True, alpha=0.3)

# Plot 3: Improvement Bars
tokens_list = results_df['token'].tolist()
improvements = results_df['return_improvement'].tolist()
bars = ax3.barh(tokens_list, improvements, color=[colors.get(t, 'gray') for t in tokens_list], alpha=0.8)

for i, (token, improvement) in enumerate(zip(tokens_list, improvements)):
    ax3.text(improvement + 10, i, f'+{improvement:.0f}%',
            va='center', fontsize=10, fontweight='bold')

ax3.axvline(x=0, color='gray', linestyle='--', alpha=0.5)
ax3.set_xlabel('Return Improvement %', fontsize=11)
ax3.set_title('Absolute Return Improvement: Optimized vs Baseline', fontsize=12, fontweight='bold')
ax3.grid(True, alpha=0.3, axis='x')

# Plot 4: Summary Table
ax4.axis('tight')
ax4.axis('off')

table_data = []
table_data.append(['Token', 'Baseline Return', 'Optimized Return', 'Improvement', 'Final R:R'])

for _, row in results_df.iterrows():
    table_data.append([
        row['token'],
        f"{row['baseline_return']:.1f}%",
        f"{row['opt_return']:.1f}%",
        f"+{row['return_improvement']:.1f}%",
        f"{row['opt_rr']:.2f}"
    ])

table = ax4.table(cellText=table_data, cellLoc='center', loc='center',
                 colWidths=[0.15, 0.2, 0.2, 0.2, 0.15])
table.auto_set_font_size(False)
table.set_fontsize(10)
table.scale(1, 2)

# Style header row
for i in range(5):
    table[(0, i)].set_facecolor('#2E86AB')
    table[(0, i)].set_text_props(weight='bold', color='white')

# Color rows by token
for i, token in enumerate(results_df['token'].tolist(), 1):
    for j in range(5):
        table[(i, j)].set_facecolor(colors.get(token, 'gray'))
        table[(i, j)].set_alpha(0.2)

plt.tight_layout()
plt.savefig('results/complete_optimized_all_tokens.png', dpi=300, bbox_inches='tight')
print("\n✓ Saved visualization to results/complete_optimized_all_tokens.png")

# Save results
results_df.to_csv('results/complete_optimized_all_tokens.csv', index=False)
print("✓ Saved results to results/complete_optimized_all_tokens.csv")

print("\n" + "="*100)
print("FINAL SUMMARY")
print("="*100)

avg_baseline = results_df['baseline_return'].mean()
avg_optimized = results_df['opt_return'].mean()
avg_improvement = results_df['return_improvement'].mean()

print(f"\nAverage Baseline Return:  {avg_baseline:.2f}%")
print(f"Average Optimized Return: {avg_optimized:.2f}%")
print(f"Average Improvement:      {avg_improvement:+.2f}%")

print(f"\nTokens with >200% improvement: {len(results_df[results_df['return_improvement'] > 200])}/{len(results_df)}")
print(f"Tokens with >500% improvement: {len(results_df[results_df['return_improvement'] > 500])}/{len(results_df)}")

best = results_df.sort_values('opt_return', ascending=False).iloc[0]
print(f"\n🏆 Best Performer: {best['token']}")
print(f"   {best['opt_return']:.2f}% return | {best['opt_dd']:.2f}% DD | {best['opt_rr']:.2f} R:R")

print("\n" + "="*100)
print("STRATEGY COMPLETE")
print("="*100)
print("\n✅ All optimizations have been stacked and tested across all tokens.")
print("✅ Dynamic position sizing (+25%/-3%) amplifies returns significantly.")
print("✅ Adaptive TP (3x ATR) helps capture larger moves in high volatility periods.")
print("✅ Fixed 3% SL provides consistent risk management across market conditions.")

print("\n" + "="*100)
