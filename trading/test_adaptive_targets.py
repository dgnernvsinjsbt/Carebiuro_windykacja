"""
Test adaptive TP/SL based on ATR and ATR filters
Goal: Improve on 747% FARTCOIN result with +25%/-3% sizing
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

def backtest_adaptive(df, strategy_type, **params):
    """
    strategy_type options:
    - 'baseline': Fixed 3% SL, 5% TP
    - 'adaptive_tp': Dynamic TP based on ATR
    - 'atr_filter': Only trade when ATR > threshold
    - 'adaptive_both': Dynamic TP + ATR filter
    """
    df = df.copy()

    # Calculate indicators
    df['ema_3'] = calculate_ema(df, 3)
    df['ema_15'] = calculate_ema(df, 15)
    df['momentum_7d'] = df['close'].pct_change(336) * 100
    df['atr'] = calculate_atr(df)
    df['atr_pct'] = (df['atr'] / df['close']) * 100
    df['rsi'] = calculate_rsi(df)

    # Base filter
    df['allow_short'] = (df['momentum_7d'] < 0) & (df['atr_pct'] < 6) & (df['rsi'] < 60)

    # Additional ATR filter if specified
    if strategy_type in ['atr_filter', 'adaptive_both']:
        atr_min = params.get('atr_min', 2.0)
        df['allow_short'] = df['allow_short'] & (df['atr_pct'] > atr_min)

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

                # Determine SL/TP based on strategy
                if strategy_type in ['adaptive_tp', 'adaptive_both']:
                    # Adaptive: Scale TP with ATR
                    atr_multiplier = params.get('atr_mult', 2.0)
                    min_tp = params.get('min_tp', 0.03)
                    max_tp = params.get('max_tp', 0.10)

                    # TP = ATR * multiplier, capped
                    tp_ratio = min(max(entry_atr / 100 * atr_multiplier, min_tp), max_tp)

                    # SL stays fixed or scales
                    if params.get('adaptive_sl', False):
                        sl_ratio = entry_atr / 100 * 1.5
                        stop_loss = entry_price * (1 + sl_ratio)
                    else:
                        stop_loss = entry_price * 1.03

                    take_profit = entry_price * (1 - tp_ratio)
                else:
                    # Fixed
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
                    'entry_atr': entry_atr,
                    'win': pnl > 0
                })
                in_position = False

    if len(trades) == 0:
        return None

    trades_df = pd.DataFrame(trades)
    trades_df = trades_df.sort_values('exit_date').reset_index(drop=True)

    # Apply +25%/-3% position sizing
    equity = 1.0
    position_size = 1.0
    min_cap = params.get('min_cap', 0.5)
    max_cap = params.get('max_cap', 2.0)
    win_adj = params.get('win_adj', 0.25)
    loss_adj = params.get('loss_adj', 0.03)

    for _, trade in trades_df.iterrows():
        trade_pnl = trade['pnl_pct'] * position_size
        equity *= (1 + trade_pnl / 100)

        if trade['pnl_pct'] > 0:
            position_size = min(position_size + win_adj, max_cap)
        else:
            position_size = max(position_size - loss_adj, min_cap)

    # Calculate metrics
    equity_temp = 1.0
    position_size = 1.0
    equity_curve = [equity_temp]

    for _, trade in trades_df.iterrows():
        trade_pnl = trade['pnl_pct'] * position_size
        equity_temp *= (1 + trade_pnl / 100)
        equity_curve.append(equity_temp)

        if trade['pnl_pct'] > 0:
            position_size = min(position_size + win_adj, max_cap)
        else:
            position_size = max(position_size - loss_adj, min_cap)

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
        'avg_win': trades_df[trades_df['pnl_pct'] > 0]['pnl_pct'].mean() if winners > 0 else 0,
        'avg_loss': trades_df[trades_df['pnl_pct'] < 0]['pnl_pct'].mean() if len(trades_df) > winners else 0
    }

# Load data
df = pd.read_csv('fartcoin_30m_jan2025.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

print("="*100)
print("ADAPTIVE TARGETS & ATR FILTERS TEST - FARTCOIN")
print("="*100)
print("\nBaseline: 747% return, -62% DD with +25%/-3% sizing")

strategies = [
    ('Baseline (Fixed 3%/5%)', 'baseline', {}),

    # ATR-based filters only
    ('ATR > 1.5%', 'atr_filter', {'atr_min': 1.5}),
    ('ATR > 2.0%', 'atr_filter', {'atr_min': 2.0}),
    ('ATR > 2.5%', 'atr_filter', {'atr_min': 2.5}),

    # Adaptive TP only
    ('Adaptive TP (2x ATR)', 'adaptive_tp', {'atr_mult': 2.0, 'min_tp': 0.03, 'max_tp': 0.10}),
    ('Adaptive TP (2.5x ATR)', 'adaptive_tp', {'atr_mult': 2.5, 'min_tp': 0.03, 'max_tp': 0.12}),
    ('Adaptive TP (3x ATR)', 'adaptive_tp', {'atr_mult': 3.0, 'min_tp': 0.04, 'max_tp': 0.15}),

    # Combination: Adaptive TP + ATR filter
    ('Adaptive TP + ATR>1.5', 'adaptive_both', {'atr_mult': 2.0, 'min_tp': 0.03, 'max_tp': 0.10, 'atr_min': 1.5}),
    ('Adaptive TP + ATR>2.0', 'adaptive_both', {'atr_mult': 2.5, 'min_tp': 0.03, 'max_tp': 0.12, 'atr_min': 2.0}),
    ('Adaptive TP + ATR>2.5', 'adaptive_both', {'atr_mult': 3.0, 'min_tp': 0.04, 'max_tp': 0.15, 'atr_min': 2.5}),

    # Adaptive SL+TP
    ('Adaptive Both (SL+TP)', 'adaptive_tp', {'atr_mult': 2.5, 'min_tp': 0.03, 'max_tp': 0.12, 'adaptive_sl': True}),
]

results = []

for name, strategy_type, params in strategies:
    print(f"\nTesting: {name}...")
    result = backtest_adaptive(df, strategy_type, **params)

    if result:
        results.append({
            'strategy': name,
            'trades': result['trades'],
            'return': result['return'],
            'max_dd': result['max_dd'],
            'win_rate': result['win_rate'],
            'rr_ratio': result['rr_ratio'],
            'avg_win': result['avg_win'],
            'avg_loss': result['avg_loss'],
            'return_vs_baseline': result['return'] - 746.54,
            'dd_vs_baseline': result['max_dd'] - (-61.69)
        })

results_df = pd.DataFrame(results)
results_df = results_df.sort_values('rr_ratio', ascending=False)

print("\n" + "="*100)
print("RESULTS BY RISK-REWARD RATIO")
print("="*100)
print(f"\n{'Strategy':<30} {'Trades':<8} {'Return':<12} {'Max DD':<12} {'R:R':<8} {'WR%':<8} {'Ret Δ':<12}")
print("-"*100)

for _, row in results_df.iterrows():
    print(f"{row['strategy']:<30} {row['trades']:<8.0f} {row['return']:<11.2f}% {row['max_dd']:<11.2f}% "
          f"{row['rr_ratio']:<7.2f} {row['win_rate']:<7.1f}% {row['return_vs_baseline']:>+11.2f}%")

print("\n" + "="*100)
print("TOP 3 RECOMMENDATIONS")
print("="*100)

for idx, (_, row) in enumerate(results_df.head(3).iterrows(), 1):
    print(f"\n#{idx}: {row['strategy']}")
    print(f"  Return: {row['return']:.2f}% ({row['return_vs_baseline']:+.2f}% vs baseline)")
    print(f"  Max DD: {row['max_dd']:.2f}% ({row['dd_vs_baseline']:+.2f}% vs baseline)")
    print(f"  R:R Ratio: {row['rr_ratio']:.2f}")
    print(f"  Trades: {row['trades']:.0f} | Win Rate: {row['win_rate']:.1f}%")
    print(f"  Avg Win: {row['avg_win']:.2f}% | Avg Loss: {row['avg_loss']:.2f}%")

# Save results
results_df.to_csv('results/adaptive_targets_results.csv', index=False)
print("\n✓ Saved results to results/adaptive_targets_results.csv")

print("\n" + "="*100)
print("VERDICT")
print("="*100)

best = results_df.iloc[0]
baseline = results_df[results_df['strategy'] == 'Baseline (Fixed 3%/5%)'].iloc[0]

if best['return'] > baseline['return'] + 50:
    print(f"\n✅ IMPROVEMENT FOUND!")
    print(f"   {best['strategy']} beats baseline by {best['return_vs_baseline']:+.2f}%")
    print(f"   New return: {best['return']:.2f}% (was {baseline['return']:.2f}%)")
else:
    print(f"\n⚠️  Baseline is still best or improvements are marginal")
    print(f"   Best alternative: {best['strategy']}")
    print(f"   Improvement: {best['return_vs_baseline']:+.2f}%")

print("="*100)
