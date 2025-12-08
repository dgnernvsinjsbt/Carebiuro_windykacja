"""
ETH/USDT Session-Based Trading - OPTIMIZED
Better strategies with proper risk management and session filtering
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Load data
print("Loading ETH/USDT 1m data...")
df = pd.read_csv('./eth_usdt_1m_lbank.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print(f"Loaded {len(df):,} candles ({(df['timestamp'].max() - df['timestamp'].min()).days} days)")

# Calculate indicators
df['hour'] = df['timestamp'].dt.hour

# Multiple EMAs for better trend detection
df['ema8'] = df['close'].ewm(span=8, adjust=False).mean()
df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()

# Bollinger Bands
df['bb_middle'] = df['close'].rolling(20).mean()
df['bb_std'] = df['close'].rolling(20).std()
df['bb_upper'] = df['bb_middle'] + (2 * df['bb_std'])
df['bb_lower'] = df['bb_middle'] - (2 * df['bb_std'])

# RSI
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

df['rsi'] = calculate_rsi(df['close'])

# ATR for volatility
df['tr'] = np.maximum(df['high'] - df['low'],
                      np.maximum(abs(df['high'] - df['close'].shift(1)),
                                abs(df['low'] - df['close'].shift(1))))
df['atr'] = df['tr'].rolling(14).mean()

# Volume filter
df['vol_ma'] = df['volume'].rolling(20).mean()
df['high_volume'] = df['volume'] > df['vol_ma'] * 1.2

def backtest_optimized_strategy(df, strategy_name='bollinger_mean_reversion',
                                allowed_hours=None, leverage=5, max_trades_per_day=10):
    """
    Optimized strategies with better entry/exit logic
    """

    balance = 10000
    position = None
    trades = []
    equity = [balance]
    daily_trades = {}

    for i in range(250, len(df)):
        row = df.iloc[i]
        current_date = row['timestamp'].date()

        # Check daily trade limit
        if current_date not in daily_trades:
            daily_trades[current_date] = 0

        # Hour filter
        if allowed_hours is not None and row['hour'] not in allowed_hours:
            equity.append(balance if position is None else balance + position['unrealized_pnl'])
            continue

        # Update position
        if position is not None:
            current_price = row['close']

            if position['side'] == 'long':
                position['unrealized_pnl'] = (current_price - position['entry']) / position['entry'] * 100 * leverage * position['size']

                # Dynamic stop based on ATR
                atr_stop = position['entry'] - (row['atr'] * 1.5)
                position['stop'] = max(position['stop'], atr_stop)

                # Exit conditions
                if current_price <= position['stop']:
                    pnl = (position['stop'] - position['entry']) / position['entry'] * 100 * leverage * position['size']
                    balance += pnl
                    trades.append({
                        'entry_time': position['entry_time'],
                        'exit_time': row['timestamp'],
                        'side': position['side'],
                        'entry': position['entry'],
                        'exit': position['stop'],
                        'pnl': pnl,
                        'reason': 'stop_loss',
                        'duration_mins': (row['timestamp'] - position['entry_time']).total_seconds() / 60
                    })
                    position = None
                    equity.append(balance)
                    continue

                if current_price >= position['target']:
                    pnl = (position['target'] - position['entry']) / position['entry'] * 100 * leverage * position['size']
                    balance += pnl
                    trades.append({
                        'entry_time': position['entry_time'],
                        'exit_time': row['timestamp'],
                        'side': position['side'],
                        'entry': position['entry'],
                        'exit': position['target'],
                        'pnl': pnl,
                        'reason': 'take_profit',
                        'duration_mins': (row['timestamp'] - position['entry_time']).total_seconds() / 60
                    })
                    position = None
                    equity.append(balance)
                    continue

                # Time-based exit (prevent holding too long on 1m)
                duration_mins = (row['timestamp'] - position['entry_time']).total_seconds() / 60
                if duration_mins > 120:  # 2 hours max hold
                    pnl = (current_price - position['entry']) / position['entry'] * 100 * leverage * position['size']
                    balance += pnl
                    trades.append({
                        'entry_time': position['entry_time'],
                        'exit_time': row['timestamp'],
                        'side': position['side'],
                        'entry': position['entry'],
                        'exit': current_price,
                        'pnl': pnl,
                        'reason': 'time_exit',
                        'duration_mins': duration_mins
                    })
                    position = None
                    equity.append(balance)
                    continue

            else:  # short
                position['unrealized_pnl'] = (position['entry'] - current_price) / position['entry'] * 100 * leverage * position['size']

                atr_stop = position['entry'] + (row['atr'] * 1.5)
                position['stop'] = min(position['stop'], atr_stop)

                if current_price >= position['stop']:
                    pnl = (position['entry'] - position['stop']) / position['entry'] * 100 * leverage * position['size']
                    balance += pnl
                    trades.append({
                        'entry_time': position['entry_time'],
                        'exit_time': row['timestamp'],
                        'side': position['side'],
                        'entry': position['entry'],
                        'exit': position['stop'],
                        'pnl': pnl,
                        'reason': 'stop_loss',
                        'duration_mins': (row['timestamp'] - position['entry_time']).total_seconds() / 60
                    })
                    position = None
                    equity.append(balance)
                    continue

                if current_price <= position['target']:
                    pnl = (position['entry'] - position['target']) / position['entry'] * 100 * leverage * position['size']
                    balance += pnl
                    trades.append({
                        'entry_time': position['entry_time'],
                        'exit_time': row['timestamp'],
                        'side': position['side'],
                        'entry': position['entry'],
                        'exit': position['target'],
                        'pnl': pnl,
                        'reason': 'take_profit',
                        'duration_mins': (row['timestamp'] - position['entry_time']).total_seconds() / 60
                    })
                    position = None
                    equity.append(balance)
                    continue

                duration_mins = (row['timestamp'] - position['entry_time']).total_seconds() / 60
                if duration_mins > 120:
                    pnl = (position['entry'] - current_price) / position['entry'] * 100 * leverage * position['size']
                    balance += pnl
                    trades.append({
                        'entry_time': position['entry_time'],
                        'exit_time': row['timestamp'],
                        'side': position['side'],
                        'entry': position['entry'],
                        'exit': current_price,
                        'pnl': pnl,
                        'reason': 'time_exit',
                        'duration_mins': duration_mins
                    })
                    position = None
                    equity.append(balance)
                    continue

        # Generate signals
        if position is None and daily_trades[current_date] < max_trades_per_day:
            signal = None

            if strategy_name == 'bollinger_mean_reversion':
                # Buy at lower band, sell at upper band
                if row['close'] < row['bb_lower'] and row['rsi'] < 35:
                    signal = 'long'
                elif row['close'] > row['bb_upper'] and row['rsi'] > 65:
                    signal = 'short'

            elif strategy_name == 'ema_pullback':
                # Pullback to EMA8 in strong trend
                prev_row = df.iloc[i-1]
                if row['close'] > row['ema200'] and row['ema20'] > row['ema50']:
                    if prev_row['close'] < prev_row['ema8'] and row['close'] > row['ema8']:
                        if row['high_volume']:
                            signal = 'long'

                elif row['close'] < row['ema200'] and row['ema20'] < row['ema50']:
                    if prev_row['close'] > prev_row['ema8'] and row['close'] < row['ema8']:
                        if row['high_volume']:
                            signal = 'short'

            elif strategy_name == 'rsi_reversal':
                # Strong RSI reversal with volume
                if row['rsi'] < 25 and row['high_volume']:
                    signal = 'long'
                elif row['rsi'] > 75 and row['high_volume']:
                    signal = 'short'

            elif strategy_name == 'volatility_breakout':
                # Breakout with high volume
                prev_row = df.iloc[i-1]
                if row['close'] > row['bb_upper'] and row['close'] > row['ema20'] and row['high_volume']:
                    if row['rsi'] < 60:  # Not overbought yet
                        signal = 'long'
                elif row['close'] < row['bb_lower'] and row['close'] < row['ema20'] and row['high_volume']:
                    if row['rsi'] > 40:  # Not oversold yet
                        signal = 'short'

            if signal:
                entry_price = row['close']
                position_size = balance * 0.05  # 5% risk per trade

                if signal == 'long':
                    stop = entry_price - (row['atr'] * 1.5)
                    target = entry_price + (row['atr'] * 2.5)
                else:
                    stop = entry_price + (row['atr'] * 1.5)
                    target = entry_price - (row['atr'] * 2.5)

                position = {
                    'entry_time': row['timestamp'],
                    'side': signal,
                    'entry': entry_price,
                    'stop': stop,
                    'target': target,
                    'size': position_size,
                    'unrealized_pnl': 0
                }
                daily_trades[current_date] += 1

        equity.append(balance if position is None else balance + position['unrealized_pnl'])

    # Close final position
    if position is not None:
        final_price = df.iloc[-1]['close']
        if position['side'] == 'long':
            pnl = (final_price - position['entry']) / position['entry'] * 100 * leverage * position['size']
        else:
            pnl = (position['entry'] - final_price) / position['entry'] * 100 * leverage * position['size']

        balance += pnl
        trades.append({
            'entry_time': position['entry_time'],
            'exit_time': df.iloc[-1]['timestamp'],
            'side': position['side'],
            'entry': position['entry'],
            'exit': final_price,
            'pnl': pnl,
            'reason': 'final_close',
            'duration_mins': (df.iloc[-1]['timestamp'] - position['entry_time']).total_seconds() / 60
        })

    if len(trades) == 0:
        return None

    trades_df = pd.DataFrame(trades)

    total_return = (balance - 10000) / 10000 * 100
    wins = trades_df[trades_df['pnl'] > 0]
    losses = trades_df[trades_df['pnl'] <= 0]

    win_rate = len(wins) / len(trades_df) * 100
    avg_win = wins['pnl'].mean() if len(wins) > 0 else 0
    avg_loss = losses['pnl'].mean() if len(losses) > 0 else 0
    profit_factor = abs(wins['pnl'].sum() / losses['pnl'].sum()) if len(losses) > 0 and losses['pnl'].sum() != 0 else 0

    equity_series = pd.Series(equity)
    running_max = equity_series.expanding().max()
    drawdown = (equity_series - running_max) / running_max * 100
    max_drawdown = drawdown.min()

    profit_dd_ratio = abs(total_return / max_drawdown) if max_drawdown != 0 else 0

    return {
        'total_return': total_return,
        'max_drawdown': max_drawdown,
        'profit_dd_ratio': profit_dd_ratio,
        'win_rate': win_rate,
        'total_trades': len(trades_df),
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'profit_factor': profit_factor,
        'final_balance': balance,
        'avg_duration_mins': trades_df['duration_mins'].mean(),
        'trades': trades_df,
        'equity': equity
    }

# Define strategies and sessions
strategies = [
    'bollinger_mean_reversion',
    'ema_pullback',
    'rsi_reversal',
    'volatility_breakout'
]

sessions = {
    '24/7': None,
    'Asian (23-07)': list(range(23, 24)) + list(range(0, 7)),
    'European (07-15)': list(range(7, 15)),
    'US (13-21)': list(range(13, 21)),
    'Euro+US (07-21)': list(range(7, 21)),
    'Peak Hours (14-19)': list(range(14, 20)),
}

print("\n" + "="*80)
print("OPTIMIZED STRATEGY TESTING")
print("="*80)

all_results = []

for strategy in strategies:
    print(f"\n{strategy.upper()}")
    print("-" * 80)

    for session_name, hours in sessions.items():
        for leverage in [3, 5, 8]:
            result = backtest_optimized_strategy(
                df,
                strategy_name=strategy,
                allowed_hours=hours,
                leverage=leverage,
                max_trades_per_day=10
            )

            if result and result['total_trades'] > 20:  # Min trades filter
                all_results.append({
                    'strategy': strategy,
                    'session': session_name,
                    'leverage': leverage,
                    **{k: v for k, v in result.items() if k not in ['trades', 'equity']}
                })

                if result['profit_dd_ratio'] > 2.0:  # Only show good ones
                    print(f"  {session_name} @ {leverage}x: Return={result['total_return']:.1f}% DD={result['max_drawdown']:.1f}% P/DD={result['profit_dd_ratio']:.2f} WR={result['win_rate']:.1f}% Trades={result['total_trades']}")

# Create results dataframe
results_df = pd.DataFrame(all_results)

if len(results_df) > 0:
    # Sort by profit/DD ratio
    results_df = results_df.sort_values('profit_dd_ratio', ascending=False)

    # Find best overall
    best = results_df.iloc[0]

    print("\n" + "="*80)
    print("BEST STRATEGY FOUND")
    print("="*80)
    print(f"Strategy: {best['strategy']}")
    print(f"Session: {best['session']}")
    print(f"Leverage: {best['leverage']}x")
    print(f"Total Return: {best['total_return']:.2f}%")
    print(f"Max Drawdown: {best['max_drawdown']:.2f}%")
    print(f"Profit/DD Ratio: {best['profit_dd_ratio']:.2f}")
    print(f"Win Rate: {best['win_rate']:.1f}%")
    print(f"Total Trades: {best['total_trades']}")
    print(f"Profit Factor: {best['profit_factor']:.2f}")
    print(f"Avg Trade Duration: {best['avg_duration_mins']:.1f} minutes")

    # Save top 20
    results_df.head(20).to_csv('./results/eth_session_optimized_top20.csv', index=False)
    print("\nSaved: ./results/eth_session_optimized_top20.csv")

    # Get equity curve for best strategy
    best_result = backtest_optimized_strategy(
        df,
        strategy_name=best['strategy'],
        allowed_hours=sessions[best['session']],
        leverage=best['leverage'],
        max_trades_per_day=10
    )

    # Plot equity curve
    plt.figure(figsize=(14, 7))
    plt.plot(best_result['equity'], linewidth=1.5)
    plt.title(f"Best Strategy: {best['strategy']} - {best['session']} @ {best['leverage']}x\n" +
              f"Return: {best['total_return']:.1f}% | Max DD: {best['max_drawdown']:.1f}% | P/DD: {best['profit_dd_ratio']:.2f}",
              fontsize=12, fontweight='bold')
    plt.xlabel('Minutes')
    plt.ylabel('Balance ($)')
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig('./results/eth_session_best_equity.png', dpi=150)
    print("Saved: ./results/eth_session_best_equity.png")

    # Save best strategy trades
    best_result['trades'].to_csv('./results/eth_session_best_trades.csv', index=False)
    print("Saved: ./results/eth_session_best_trades.csv")
else:
    print("\nNo profitable strategies found!")

print("\nAnalysis complete!")
