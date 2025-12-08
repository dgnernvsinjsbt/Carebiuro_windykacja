"""
Test the +25%/-3% position sizing strategy on PENGU and PI
Using the same filters: Mom7d<0 + ATR<6 + RSI<60
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

def backtest_token(df, use_position_sizing=False, win_adj=0.25, loss_adj=0.03, min_cap=0.5, max_cap=2.0):
    """Backtest with or without position sizing"""
    df = df.copy()

    # Calculate indicators
    df['ema_3'] = calculate_ema(df, 3)
    df['ema_15'] = calculate_ema(df, 15)
    df['momentum_7d'] = df['close'].pct_change(336) * 100
    df['atr'] = calculate_atr(df)
    df['atr_pct'] = (df['atr'] / df['close']) * 100
    df['rsi'] = calculate_rsi(df)

    # Best filter
    df['allow_short'] = (df['momentum_7d'] < 0) & (df['atr_pct'] < 6) & (df['rsi'] < 60)

    # Run backtest
    trades = []
    in_position = False
    entry_price = 0
    entry_date = None
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
                stop_loss = entry_price * 1.03
                take_profit = entry_price * 0.95
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

    # Calculate equity with or without position sizing
    equity = 1.0
    equity_curve = [equity]
    position_size = 1.0

    for _, trade in trades_df.iterrows():
        # Apply position sizing
        trade_pnl = trade['pnl_pct'] * position_size
        equity *= (1 + trade_pnl / 100)
        equity_curve.append(equity)

        # Adjust position size for next trade
        if use_position_sizing:
            if trade['pnl_pct'] > 0:
                position_size = min(position_size + win_adj, max_cap)
            else:
                position_size = max(position_size - loss_adj, min_cap)

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
        'equity_curve': equity_curve
    }

# Test all tokens
tokens = {
    'FARTCOIN': 'fartcoin_30m_jan2025.csv',
    'PENGU': 'pengu_30m_jan2025.csv',
    'PI': 'pi_30m_jan2025.csv',
}

print("="*100)
print("TESTING +25%/-3% POSITION SIZING ON ALL TOKENS")
print("="*100)
print("\nStrategy: EMA 3/15 SHORT Crossover")
print("Filters: Mom7d<0 + ATR<6% + RSI<60")
print("Position Sizing: +25% on wins, -3% on losses (0.5x-2.0x caps)")

results = []
equity_curves = {}

for token, filename in tokens.items():
    print(f"\nProcessing {token}...")
    try:
        df = pd.read_csv(filename)
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        # Fixed 100% baseline
        fixed = backtest_token(df, use_position_sizing=False)

        # Dynamic sizing
        dynamic = backtest_token(df, use_position_sizing=True, win_adj=0.25, loss_adj=0.03)

        if fixed and dynamic:
            results.append({
                'token': token,
                'fixed_trades': fixed['trades'],
                'fixed_return': fixed['return'],
                'fixed_dd': fixed['max_dd'],
                'fixed_wr': fixed['win_rate'],
                'fixed_rr': fixed['rr_ratio'],
                'dynamic_trades': dynamic['trades'],
                'dynamic_return': dynamic['return'],
                'dynamic_dd': dynamic['max_dd'],
                'dynamic_wr': dynamic['win_rate'],
                'dynamic_rr': dynamic['rr_ratio'],
                'return_improvement': dynamic['return'] - fixed['return'],
                'dd_change': dynamic['max_dd'] - fixed['max_dd'],
                'rr_improvement': dynamic['rr_ratio'] - fixed['rr_ratio']
            })

            equity_curves[f'{token} Fixed'] = fixed['equity_curve']
            equity_curves[f'{token} Dynamic'] = dynamic['equity_curve']

    except Exception as e:
        print(f"Error with {token}: {e}")

results_df = pd.DataFrame(results)

print("\n" + "="*100)
print("FIXED 100% POSITION SIZE RESULTS")
print("="*100)
print(f"\n{'Token':<12} {'Trades':<8} {'Return':<12} {'Max DD':<12} {'Win Rate':<10} {'R:R':<8}")
print("-"*75)

for _, row in results_df.iterrows():
    print(f"{row['token']:<12} {row['fixed_trades']:<8.0f} {row['fixed_return']:<11.2f}% {row['fixed_dd']:<11.2f}% {row['fixed_wr']:<9.1f}% {row['fixed_rr']:<7.2f}")

print("\n" + "="*100)
print("DYNAMIC +25%/-3% POSITION SIZE RESULTS")
print("="*100)
print(f"\n{'Token':<12} {'Trades':<8} {'Return':<12} {'Max DD':<12} {'Win Rate':<10} {'R:R':<8}")
print("-"*75)

for _, row in results_df.iterrows():
    print(f"{row['token']:<12} {row['dynamic_trades']:<8.0f} {row['dynamic_return']:<11.2f}% {row['dynamic_dd']:<11.2f}% {row['dynamic_wr']:<9.1f}% {row['dynamic_rr']:<7.2f}")

print("\n" + "="*100)
print("IMPROVEMENT ANALYSIS")
print("="*100)
print(f"\n{'Token':<12} {'Return Δ':<15} {'DD Δ':<15} {'R:R Δ':<12} {'Status':<10}")
print("-"*75)

for _, row in results_df.iterrows():
    status = '✅' if row['return_improvement'] > 0 and row['rr_improvement'] > 0 else '⚠️' if row['return_improvement'] > 0 else '❌'
    print(f"{row['token']:<12} {row['return_improvement']:>+13.2f}% {row['dd_change']:>+13.2f}% {row['rr_improvement']:>+10.2f} {status:<10}")

print("\n" + "="*100)
print("SUMMARY")
print("="*100)

avg_return_fixed = results_df['fixed_return'].mean()
avg_return_dynamic = results_df['dynamic_return'].mean()
avg_rr_fixed = results_df['fixed_rr'].mean()
avg_rr_dynamic = results_df['dynamic_rr'].mean()

print(f"\nFixed 100% Position:")
print(f"  Average Return: {avg_return_fixed:.2f}%")
print(f"  Average R:R Ratio: {avg_rr_fixed:.2f}")

print(f"\nDynamic +25%/-3% Position:")
print(f"  Average Return: {avg_return_dynamic:.2f}%")
print(f"  Average R:R Ratio: {avg_rr_dynamic:.2f}")

print(f"\nImprovement:")
print(f"  Return: {avg_return_dynamic - avg_return_fixed:+.2f}%")
print(f"  R:R Ratio: {avg_rr_dynamic - avg_rr_fixed:+.2f}")

tokens_improved = len(results_df[results_df['return_improvement'] > 0])
print(f"\nTokens with improved returns: {tokens_improved}/{len(results_df)}")

# Visualize
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

colors = {'FARTCOIN': '#2E86AB', 'PENGU': '#A23B72', 'PI': '#F18F01'}

# Fixed vs Dynamic comparison
for _, row in results_df.iterrows():
    token = row['token']
    ax1.scatter(abs(row['fixed_dd']), row['fixed_return'], s=200, alpha=0.7,
                color=colors.get(token, 'gray'), marker='o', label=f"{token} Fixed")
    ax1.scatter(abs(row['dynamic_dd']), row['dynamic_return'], s=200, alpha=0.7,
                color=colors.get(token, 'gray'), marker='*', label=f"{token} Dynamic")

    # Draw arrow showing improvement
    ax1.annotate('', xy=(abs(row['dynamic_dd']), row['dynamic_return']),
                xytext=(abs(row['fixed_dd']), row['fixed_return']),
                arrowprops=dict(arrowstyle='->', color=colors.get(token, 'gray'),
                               lw=2, alpha=0.5))

ax1.set_xlabel('Max Drawdown (abs %)', fontsize=11)
ax1.set_ylabel('Total Return %', fontsize=11)
ax1.set_title('Fixed vs Dynamic Position Sizing\n(arrows show improvement)', fontsize=12, fontweight='bold')
ax1.legend(loc='best', fontsize=9)
ax1.grid(True, alpha=0.3)

# Equity curves comparison
for token in ['FARTCOIN', 'PENGU', 'PI']:
    if f'{token} Fixed' in equity_curves and f'{token} Dynamic' in equity_curves:
        ec_fixed = equity_curves[f'{token} Fixed']
        ec_dynamic = equity_curves[f'{token} Dynamic']

        # Normalize to trade numbers
        max_len = max(len(ec_fixed), len(ec_dynamic))

        ax2.plot(range(len(ec_fixed)), ec_fixed, linewidth=1.5, linestyle='--',
                color=colors.get(token, 'gray'), alpha=0.5, label=f'{token} Fixed')
        ax2.plot(range(len(ec_dynamic)), ec_dynamic, linewidth=2.5,
                color=colors.get(token, 'gray'), alpha=0.9, label=f'{token} +25%/-3%')

ax2.axhline(y=1, color='gray', linestyle='--', alpha=0.5)
ax2.set_xlabel('Trade Number', fontsize=11)
ax2.set_ylabel('Equity Multiple', fontsize=11)
ax2.set_title('Equity Curves: Fixed (dashed) vs Dynamic (solid)', fontsize=12, fontweight='bold')
ax2.legend(loc='upper left', fontsize=9)
ax2.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('results/multi_token_position_sizing.png', dpi=300, bbox_inches='tight')
print("\n✓ Saved visualization to results/multi_token_position_sizing.png")

# Save results
results_df.to_csv('results/multi_token_sizing_results.csv', index=False)
print("✓ Saved results to results/multi_token_sizing_results.csv")

print("\n" + "="*100)
