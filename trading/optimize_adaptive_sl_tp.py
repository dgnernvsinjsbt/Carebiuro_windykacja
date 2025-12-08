"""
Comprehensive test of adaptive SL and TP combinations
Goal: Find optimal SL/TP scaling with ATR
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

def backtest_adaptive_sl_tp(df, sl_mult, tp_mult, min_sl, max_sl, min_tp, max_tp):
    """Test adaptive SL and TP based on ATR"""
    df = df.copy()

    # Calculate indicators
    df['ema_3'] = calculate_ema(df, 3)
    df['ema_15'] = calculate_ema(df, 15)
    df['momentum_7d'] = df['close'].pct_change(336) * 100
    df['atr'] = calculate_atr(df)
    df['atr_pct'] = (df['atr'] / df['close']) * 100
    df['rsi'] = calculate_rsi(df)

    # Filters
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

                # Adaptive SL and TP
                sl_ratio = min(max(entry_atr / 100 * sl_mult, min_sl), max_sl)
                tp_ratio = min(max(entry_atr / 100 * tp_mult, min_tp), max_tp)

                stop_loss = entry_price * (1 + sl_ratio)
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

    # Apply +25%/-3% position sizing
    equity = 1.0
    position_size = 1.0

    for _, trade in trades_df.iterrows():
        trade_pnl = trade['pnl_pct'] * position_size
        equity *= (1 + trade_pnl / 100)

        if trade['pnl_pct'] > 0:
            position_size = min(position_size + 0.25, 2.0)
        else:
            position_size = max(position_size - 0.03, 0.5)

    # Calculate metrics
    equity_temp = 1.0
    position_size = 1.0
    equity_curve = [equity_temp]

    for _, trade in trades_df.iterrows():
        trade_pnl = trade['pnl_pct'] * position_size
        equity_temp *= (1 + trade_pnl / 100)
        equity_curve.append(equity_temp)

        if trade['pnl_pct'] > 0:
            position_size = min(position_size + 0.25, 2.0)
        else:
            position_size = max(position_size - 0.03, 0.5)

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
        'rr_ratio': total_return / abs(max_dd),
        'avg_win': trades_df[trades_df['pnl_pct'] > 0]['pnl_pct'].mean() if winners > 0 else 0,
        'avg_loss': trades_df[trades_df['pnl_pct'] < 0]['pnl_pct'].mean() if len(trades_df) > winners else 0
    }

# Load data
df = pd.read_csv('fartcoin_30m_jan2025.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

print("="*100)
print("ADAPTIVE SL + TP OPTIMIZATION - FARTCOIN")
print("="*100)
print("\nCurrent Best: 942% with Fixed SL (3%) + Adaptive TP (3x ATR)")

strategies = []

# Test grid of SL and TP multipliers
sl_multipliers = [1.0, 1.5, 2.0, 2.5]  # ATR multiplier for SL
tp_multipliers = [2.0, 2.5, 3.0, 3.5, 4.0]  # ATR multiplier for TP

print("\nTesting adaptive SL + TP combinations...")

for sl_mult in sl_multipliers:
    for tp_mult in tp_multipliers:
        # Set reasonable min/max bounds
        min_sl = 0.015 if sl_mult < 2.0 else 0.02  # 1.5-2% min
        max_sl = 0.05 if sl_mult < 2.0 else 0.06   # 5-6% max
        min_tp = 0.03  # 3% min
        max_tp = 0.15  # 15% max

        result = backtest_adaptive_sl_tp(df, sl_mult, tp_mult, min_sl, max_sl, min_tp, max_tp)

        if result:
            strategies.append({
                'sl_mult': sl_mult,
                'tp_mult': tp_mult,
                'strategy': f'SL={sl_mult}x TP={tp_mult}x ATR',
                **result
            })

# Add baseline for comparison
baseline = backtest_adaptive_sl_tp(df, sl_mult=0, tp_mult=3.0, min_sl=0.03, max_sl=0.03, min_tp=0.04, max_tp=0.15)
if baseline:
    strategies.append({
        'sl_mult': 0,
        'tp_mult': 3.0,
        'strategy': 'Baseline (SL=3% fixed, TP=3x ATR)',
        **baseline
    })

results_df = pd.DataFrame(strategies)
results_df = results_df.sort_values('rr_ratio', ascending=False)

print("\n" + "="*100)
print("TOP 15 STRATEGIES BY RISK-REWARD RATIO")
print("="*100)
print(f"\n{'Strategy':<35} {'Trades':<8} {'Return':<12} {'Max DD':<12} {'R:R':<8} {'WR%':<8}")
print("-"*100)

for _, row in results_df.head(15).iterrows():
    print(f"{row['strategy']:<35} {row['trades']:<8.0f} {row['return']:<11.2f}% {row['max_dd']:<11.2f}% "
          f"{row['rr_ratio']:<7.2f} {row['win_rate']:<7.1f}%")

print("\n" + "="*100)
print("BEST BY ABSOLUTE RETURN")
print("="*100)

best_return = results_df.sort_values('return', ascending=False).head(10)
print(f"\n{'Strategy':<35} {'Return':<12} {'Max DD':<12} {'R:R':<8}")
print("-"*85)

for _, row in best_return.iterrows():
    print(f"{row['strategy']:<35} {row['return']:<11.2f}% {row['max_dd']:<11.2f}% {row['rr_ratio']:<7.2f}")

print("\n" + "="*100)
print("BEST DRAWDOWN CONTROL (DD > -50%)")
print("="*100)

low_dd = results_df[results_df['max_dd'] > -50].sort_values('return', ascending=False).head(10)
print(f"\n{'Strategy':<35} {'Return':<12} {'Max DD':<12} {'R:R':<8}")
print("-"*85)

for _, row in low_dd.iterrows():
    print(f"{row['strategy']:<35} {row['return']:<11.2f}% {row['max_dd']:<11.2f}% {row['rr_ratio']:<7.2f}")

print("\n" + "="*100)
print("TOP 3 RECOMMENDATIONS")
print("="*100)

for idx, (_, row) in enumerate(results_df.head(3).iterrows(), 1):
    print(f"\n#{idx}: {row['strategy']}")
    print(f"  Return: {row['return']:.2f}%")
    print(f"  Max DD: {row['max_dd']:.2f}%")
    print(f"  R:R Ratio: {row['rr_ratio']:.2f}")
    print(f"  Trades: {row['trades']:.0f} | Win Rate: {row['win_rate']:.1f}%")
    print(f"  Avg Win: {row['avg_win']:.2f}% | Avg Loss: {row['avg_loss']:.2f}%")
    print(f"  SL Multiplier: {row['sl_mult']}x ATR")
    print(f"  TP Multiplier: {row['tp_mult']}x ATR")

# Save results
results_df.to_csv('results/adaptive_sl_tp_optimization.csv', index=False)
print("\n✓ Saved results to results/adaptive_sl_tp_optimization.csv")

print("\n" + "="*100)
print("FINAL VERDICT")
print("="*100)

best = results_df.iloc[0]
baseline_row = results_df[results_df['strategy'].str.contains('Baseline')].iloc[0]

print(f"\n🏆 BEST STRATEGY: {best['strategy']}")
print(f"   Return: {best['return']:.2f}%")
print(f"   Max DD: {best['max_dd']:.2f}%")
print(f"   R:R Ratio: {best['rr_ratio']:.2f}")

print(f"\nvs Baseline (Fixed SL=3%, Adaptive TP=3x):")
print(f"   Return: {best['return'] - baseline_row['return']:+.2f}%")
print(f"   Max DD: {best['max_dd'] - baseline_row['max_dd']:+.2f}%")
print(f"   R:R: {best['rr_ratio'] - baseline_row['rr_ratio']:+.2f}")

if best['return'] > baseline_row['return'] + 50:
    print(f"\n✅ SIGNIFICANT IMPROVEMENT with adaptive SL!")
else:
    print(f"\n⚠️  Marginal improvement - fixed SL might be sufficient")

print("="*100)
