"""
Multi-Pattern MELANIA Short Strategy
Combines the 3 best patterns found:
1. Volatility Spike (ATR > 5%, RSI > 70) - 100% win rate, 17% avg drop
2. Extreme Green Candle (>5% move) - 68.4% win rate
3. Parabolic Move (body > 3%, RSI > 70) - 66.7% win rate
"""
import pandas as pd
import numpy as np

df = pd.read_csv('trading/melania_3months_bingx.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

def calculate_rsi(prices, period=14):
    delta = prices.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(com=period-1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period-1, min_periods=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_atr(df, period=14):
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr

df['rsi'] = calculate_rsi(df['close'])
df['atr'] = calculate_atr(df)
df['atr_pct'] = (df['atr'] / df['close']) * 100
df['body'] = abs(df['close'] - df['open'])
df['body_pct'] = (df['body'] / df['open']) * 100
df['price_change'] = df['close'].pct_change() * 100
df['is_green'] = (df['close'] > df['open']).astype(int)

def backtest_multi_pattern(
    vol_spike_enabled=True,
    extreme_candle_enabled=True,
    parabolic_enabled=True,
    tp_pct=8.0,
    sl_pct=4.0,
    max_hold_hours=12
):
    """
    Backtest strategy with multiple pattern types.
    """
    trades = []
    equity = 100.0
    position = None

    for i in range(50, len(df)):
        row = df.iloc[i]

        # Manage open position
        if position is not None:
            entry_idx, entry_price, entry_type = position

            tp_price = entry_price * (1 - tp_pct/100)
            sl_price = entry_price * (1 + sl_pct/100)
            candles_held = i - entry_idx

            # TP hit
            if row['low'] <= tp_price:
                pnl_pct = ((tp_price - entry_price) / entry_price) * 100
                equity_risk = equity * 0.05
                pnl = equity_risk * (abs(pnl_pct) / sl_pct)
                equity += pnl

                trades.append({
                    'entry_idx': entry_idx,
                    'exit_idx': i,
                    'pattern': entry_type,
                    'entry_price': entry_price,
                    'exit_price': tp_price,
                    'pnl_pct': pnl_pct,
                    'pnl_usd': pnl,
                    'equity': equity,
                    'result': 'TP',
                    'candles_held': candles_held,
                })
                position = None
                continue

            # SL hit
            elif row['high'] >= sl_price:
                pnl_pct = ((sl_price - entry_price) / entry_price) * 100
                equity_risk = equity * 0.05
                pnl = -equity_risk
                equity += pnl

                trades.append({
                    'entry_idx': entry_idx,
                    'exit_idx': i,
                    'pattern': entry_type,
                    'entry_price': entry_price,
                    'exit_price': sl_price,
                    'pnl_pct': pnl_pct,
                    'pnl_usd': pnl,
                    'equity': equity,
                    'result': 'SL',
                    'candles_held': candles_held,
                })
                position = None
                continue

            # Timeout
            elif candles_held >= max_hold_hours * 4:  # 4 candles per hour
                exit_price = row['close']
                pnl_pct = ((exit_price - entry_price) / entry_price) * 100
                equity_risk = equity * 0.05
                pnl = equity_risk * (pnl_pct / sl_pct)
                equity += pnl

                trades.append({
                    'entry_idx': entry_idx,
                    'exit_idx': i,
                    'pattern': entry_type,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl_pct': pnl_pct,
                    'pnl_usd': pnl,
                    'equity': equity,
                    'result': 'TIMEOUT',
                    'candles_held': candles_held,
                })
                position = None
                continue

        # Look for entry signals (only if not in position)
        if position is None:
            # Pattern 1: Volatility Spike
            if vol_spike_enabled and row['atr_pct'] > 5.0 and row['rsi'] > 70:
                position = (i, row['close'], 'VOL_SPIKE')
                continue

            # Pattern 2: Extreme Green Candle
            if extreme_candle_enabled and row['price_change'] > 5.0 and row['is_green']:
                position = (i, row['close'], 'EXTREME_GREEN')
                continue

            # Pattern 3: Parabolic Move
            if parabolic_enabled and row['body_pct'] > 3.0 and row['rsi'] > 70 and row['is_green']:
                position = (i, row['close'], 'PARABOLIC')
                continue

    return trades, equity

# Test different configurations
configs = [
    # All patterns enabled
    {'name': 'All 3 Patterns', 'vol': True, 'ext': True, 'para': True, 'tp': 8, 'sl': 4, 'hold': 12},
    {'name': 'All - Tighter TP', 'vol': True, 'ext': True, 'para': True, 'tp': 6, 'sl': 4, 'hold': 12},
    {'name': 'All - Wider TP', 'vol': True, 'ext': True, 'para': True, 'tp': 10, 'sl': 4, 'hold': 12},
    {'name': 'All - Wider R:R', 'vol': True, 'ext': True, 'para': True, 'tp': 12, 'sl': 4, 'hold': 12},

    # Individual patterns
    {'name': 'Vol Spike Only', 'vol': True, 'ext': False, 'para': False, 'tp': 10, 'sl': 5, 'hold': 12},
    {'name': 'Extreme Green Only', 'vol': False, 'ext': True, 'para': False, 'tp': 6, 'sl': 4, 'hold': 8},
    {'name': 'Parabolic Only', 'vol': False, 'ext': False, 'para': True, 'tp': 8, 'sl': 4, 'hold': 12},

    # Best combo
    {'name': 'Vol + Extreme', 'vol': True, 'ext': True, 'para': False, 'tp': 8, 'sl': 4, 'hold': 12},
    {'name': 'Vol + Para', 'vol': True, 'ext': False, 'para': True, 'tp': 10, 'sl': 5, 'hold': 12},
]

results = []

for config in configs:
    trades, final_equity = backtest_multi_pattern(
        vol_spike_enabled=config['vol'],
        extreme_candle_enabled=config['ext'],
        parabolic_enabled=config['para'],
        tp_pct=config['tp'],
        sl_pct=config['sl'],
        max_hold_hours=config['hold']
    )

    if len(trades) == 0:
        continue

    trades_df = pd.DataFrame(trades)
    total_trades = len(trades_df)
    winners = trades_df[trades_df['result'] == 'TP']
    losers = trades_df[trades_df['result'] == 'SL']
    win_rate = len(winners) / total_trades * 100
    total_return = ((final_equity - 100) / 100) * 100

    # Calculate drawdown
    equity_curve = [100.0] + trades_df['equity'].tolist()
    max_dd = 0
    peak = equity_curve[0]
    for equity in equity_curve:
        if equity > peak:
            peak = equity
        dd = (equity - peak) / peak * 100
        if dd < max_dd:
            max_dd = dd

    results.append({
        'config': config['name'],
        'trades': total_trades,
        'win_rate': win_rate,
        'return': total_return,
        'max_dd': max_dd,
        'r_dd': abs(total_return / max_dd) if max_dd != 0 else 0,
        'final_equity': final_equity,
    })

results_df = pd.DataFrame(results).sort_values('r_dd', ascending=False)

print("=" * 120)
print("MULTI-PATTERN STRATEGY OPTIMIZATION")
print("=" * 120)
print(results_df.to_string(index=False))

# Best config
best = results_df.iloc[0]
print("\n" + "=" * 120)
print(f"BEST CONFIGURATION: {best['config']}")
print("=" * 120)
print(f"Total Trades: {best['trades']}")
print(f"Win Rate: {best['win_rate']:.1f}%")
print(f"Total Return: {best['return']:+.2f}%")
print(f"Max Drawdown: {best['max_dd']:.2f}%")
print(f"Return/DD: {best['r_dd']:.2f}x")
print(f"Final Equity: ${best['final_equity']:.2f}")

# Find best config params
best_config = [c for c in configs if c['name'] == best['config']][0]

# Run detailed backtest
trades, _ = backtest_multi_pattern(
    vol_spike_enabled=best_config['vol'],
    extreme_candle_enabled=best_config['ext'],
    parabolic_enabled=best_config['para'],
    tp_pct=best_config['tp'],
    sl_pct=best_config['sl'],
    max_hold_hours=best_config['hold']
)

trades_df = pd.DataFrame(trades)

print("\n" + "=" * 120)
print("PATTERN BREAKDOWN")
print("=" * 120)
for pattern in trades_df['pattern'].unique():
    pattern_trades = trades_df[trades_df['pattern'] == pattern]
    pattern_wins = len(pattern_trades[pattern_trades['result'] == 'TP'])
    pattern_wr = pattern_wins / len(pattern_trades) * 100
    print(f"{pattern:20s}: {len(pattern_trades):3d} trades, {pattern_wr:5.1f}% win rate")

print("\n" + "=" * 120)
print("TRADE LOG (first 20 trades)")
print("=" * 120)
print(trades_df[['pattern', 'entry_price', 'exit_price', 'pnl_pct', 'result', 'candles_held']].head(20).to_string(index=False))

trades_df.to_csv('trading/melania_multi_pattern_trades.csv', index=False)
print(f"\nFull trade log saved to: trading/melania_multi_pattern_trades.csv")
