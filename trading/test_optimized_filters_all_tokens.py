"""
Test optimized filters (Mom7d<0 + ATR<6 + RSI<60) on all tokens
"""

import pandas as pd
import numpy as np

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

def backtest_with_filters(df, use_optimized_filters=False):
    """Backtest with original or optimized filters"""
    df = df.copy()

    # Calculate indicators
    df['ema_3'] = calculate_ema(df, 3)
    df['ema_15'] = calculate_ema(df, 15)
    df['momentum_7d'] = df['close'].pct_change(336) * 100
    df['momentum_14d'] = df['close'].pct_change(672) * 100

    if use_optimized_filters:
        df['atr'] = calculate_atr(df)
        df['atr_pct'] = (df['atr'] / df['close']) * 100
        df['rsi'] = calculate_rsi(df)
        # Optimized filter
        df['allow_short'] = (df['momentum_7d'] < 0) & (df['atr_pct'] < 6) & (df['rsi'] < 60)
    else:
        # Original filter
        df['allow_short'] = (df['momentum_7d'] < 5) & (df['momentum_14d'] < 10)

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
                    'entry_date': entry_date,
                    'exit_date': row['timestamp'],
                    'pnl_pct': pnl * 100,
                    'exit_type': exit_type
                })
                in_position = False

    # Calculate metrics
    if len(trades) == 0:
        return None

    trades_df = pd.DataFrame(trades)
    trades_df = trades_df.sort_values('entry_date').reset_index(drop=True)

    equity = 1.0
    equity_curve = [equity]

    for _, trade in trades_df.iterrows():
        equity *= (1 + trade['pnl_pct'] / 100)
        equity_curve.append(equity)

    equity_series = pd.Series(equity_curve)
    running_max = equity_series.expanding().max()
    drawdown = (equity_series - running_max) / running_max * 100
    max_dd = drawdown.min()

    winners = len(trades_df[trades_df['pnl_pct'] > 0])
    win_rate = winners / len(trades_df) * 100
    total_return = (equity - 1) * 100

    return {
        'trades': len(trades_df),
        'return': total_return,
        'max_dd': max_dd,
        'win_rate': win_rate,
        'final_equity': equity
    }

# Test all tokens
tokens = {
    'FARTCOIN': 'fartcoin_30m_jan2025.csv',
    'PENGU': 'pengu_30m_jan2025.csv',
    'PI': 'pi_30m_jan2025.csv',
    'MELANIA': 'melania_30m_jan2025.csv'
}

print("="*100)
print("OPTIMIZED FILTERS TEST - ALL TOKENS")
print("="*100)
print("\nFilters: Mom7d < 0% + ATR < 6% + RSI < 60")
print("Original: Mom7d < 5% + Mom14d < 10%")

results = []

for token, filename in tokens.items():
    try:
        df = pd.read_csv(filename)
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        # Original strategy
        original = backtest_with_filters(df, use_optimized_filters=False)

        # Optimized strategy
        optimized = backtest_with_filters(df, use_optimized_filters=True)

        if original and optimized:
            results.append({
                'token': token,
                'orig_trades': original['trades'],
                'orig_return': original['return'],
                'orig_dd': original['max_dd'],
                'orig_wr': original['win_rate'],
                'opt_trades': optimized['trades'],
                'opt_return': optimized['return'],
                'opt_dd': optimized['max_dd'],
                'opt_wr': optimized['win_rate'],
                'return_improvement': optimized['return'] - original['return'],
                'dd_improvement': optimized['max_dd'] - original['max_dd'],
                'trades_change': optimized['trades'] - original['trades']
            })

    except Exception as e:
        print(f"Error with {token}: {e}")

results_df = pd.DataFrame(results)

print("\n" + "="*100)
print("ORIGINAL STRATEGY RESULTS")
print("="*100)
print(f"\n{'TOKEN':<12} {'TRADES':<8} {'RETURN':<12} {'MAX DD':<12} {'WIN RATE':<10}")
print("-"*60)

for _, row in results_df.iterrows():
    print(f"{row['token']:<12} {row['orig_trades']:<8.0f} {row['orig_return']:<11.2f}% {row['orig_dd']:<11.2f}% {row['orig_wr']:<9.1f}%")

print("\n" + "="*100)
print("OPTIMIZED STRATEGY RESULTS")
print("="*100)
print(f"\n{'TOKEN':<12} {'TRADES':<8} {'RETURN':<12} {'MAX DD':<12} {'WIN RATE':<10}")
print("-"*60)

for _, row in results_df.iterrows():
    print(f"{row['token']:<12} {row['opt_trades']:<8.0f} {row['opt_return']:<11.2f}% {row['opt_dd']:<11.2f}% {row['opt_wr']:<9.1f}%")

print("\n" + "="*100)
print("IMPROVEMENT ANALYSIS")
print("="*100)
print(f"\n{'TOKEN':<12} {'RETURN Δ':<15} {'DD Δ':<15} {'TRADES Δ':<12} {'STATUS':<10}")
print("-"*70)

for _, row in results_df.iterrows():
    status = '✅' if row['return_improvement'] > 0 and row['dd_improvement'] > 0 else '⚠️' if row['return_improvement'] > 0 else '❌'
    print(f"{row['token']:<12} {row['return_improvement']:>+13.2f}% {row['dd_improvement']:>+13.2f}% {row['trades_change']:>+11.0f} {status:<10}")

print("\n" + "="*100)
print("SUMMARY")
print("="*100)

# Calculate averages
avg_return_orig = results_df['orig_return'].mean()
avg_return_opt = results_df['opt_return'].mean()
avg_dd_orig = results_df['orig_dd'].mean()
avg_dd_opt = results_df['opt_dd'].mean()

print(f"\nOriginal Strategy:")
print(f"  Average Return: {avg_return_orig:.2f}%")
print(f"  Average Max DD: {avg_dd_orig:.2f}%")

print(f"\nOptimized Strategy:")
print(f"  Average Return: {avg_return_opt:.2f}%")
print(f"  Average Max DD: {avg_dd_opt:.2f}%")

print(f"\nImprovement:")
print(f"  Return: {avg_return_opt - avg_return_orig:+.2f}%")
print(f"  Max DD: {avg_dd_opt - avg_dd_orig:+.2f}%")

tokens_improved = len(results_df[results_df['return_improvement'] > 0])
print(f"\nTokens with improved returns: {tokens_improved}/{len(results_df)}")

# Save results
results_df.to_csv('results/optimized_filters_all_tokens.csv', index=False)
print("\n✓ Saved results to results/optimized_filters_all_tokens.csv")
print("="*100)
