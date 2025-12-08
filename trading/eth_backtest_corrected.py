"""
ETH/USDT Corrected Backtest - VERIFIED formula
Find strategies with >4:1 profit/DD ratio
"""

import pandas as pd
import numpy as np

print("=" * 80)
print("ETH/USDT CORRECTED BACKTEST")
print("=" * 80)

# Load data
df = pd.read_csv('./eth_usdt_1m_lbank.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print(f"Loaded {len(df):,} candles ({(df['timestamp'].max() - df['timestamp'].min()).days} days)")
print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")

# Calculate indicators
df['hour'] = df['timestamp'].dt.hour

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

# ATR
df['tr'] = np.maximum(df['high'] - df['low'],
                      np.maximum(abs(df['high'] - df['close'].shift(1)),
                                abs(df['low'] - df['close'].shift(1))))
df['atr'] = df['tr'].rolling(14).mean()

# Volume
df['vol_ma'] = df['volume'].rolling(20).mean()
df['high_volume'] = df['volume'] > df['vol_ma'] * 1.2

df = df.dropna()

def backtest_corrected(df, allowed_hours=None, leverage=10,
                       sl_mult=1.5, tp_mult=2.5, risk_per_trade=0.02,
                       rsi_oversold=30, rsi_overbought=70):
    """
    Corrected backtest with proper PnL calculation
    """
    balance = 10000
    position = None
    trades = []
    equity = [balance]

    FEE_PCT = 0.00005  # 0.005% per side

    for i in range(250, len(df)):
        row = df.iloc[i]

        # Hour filter
        if allowed_hours is not None and row['hour'] not in allowed_hours:
            equity.append(balance if position is None else balance + position.get('unrealized_pnl', 0))
            continue

        # Update position
        if position is not None:
            current_price = row['close']

            if position['side'] == 'long':
                # Calculate unrealized PnL correctly
                price_pct_change = (current_price - position['entry']) / position['entry']
                position['unrealized_pnl'] = price_pct_change * leverage * position['margin']

                # Check stop loss
                if current_price <= position['stop']:
                    exit_price = position['stop']
                    pnl_pct = (exit_price - position['entry']) / position['entry']
                    pnl = pnl_pct * leverage * position['margin']

                    # Subtract fees
                    position_value = position['margin'] * leverage
                    fees = position_value * FEE_PCT * 2  # Entry + exit
                    pnl -= fees

                    balance += pnl
                    trades.append({
                        'entry_time': position['entry_time'],
                        'exit_time': row['timestamp'],
                        'side': 'long',
                        'entry': position['entry'],
                        'exit': exit_price,
                        'pnl': pnl,
                        'pnl_pct': pnl / position['margin'] * 100,
                        'reason': 'stop_loss'
                    })
                    position = None

                # Check take profit
                elif current_price >= position['target']:
                    exit_price = position['target']
                    pnl_pct = (exit_price - position['entry']) / position['entry']
                    pnl = pnl_pct * leverage * position['margin']

                    position_value = position['margin'] * leverage
                    fees = position_value * FEE_PCT * 2
                    pnl -= fees

                    balance += pnl
                    trades.append({
                        'entry_time': position['entry_time'],
                        'exit_time': row['timestamp'],
                        'side': 'long',
                        'entry': position['entry'],
                        'exit': exit_price,
                        'pnl': pnl,
                        'pnl_pct': pnl / position['margin'] * 100,
                        'reason': 'take_profit'
                    })
                    position = None

            else:  # short
                price_pct_change = (position['entry'] - current_price) / position['entry']
                position['unrealized_pnl'] = price_pct_change * leverage * position['margin']

                if current_price >= position['stop']:
                    exit_price = position['stop']
                    pnl_pct = (position['entry'] - exit_price) / position['entry']
                    pnl = pnl_pct * leverage * position['margin']

                    position_value = position['margin'] * leverage
                    fees = position_value * FEE_PCT * 2
                    pnl -= fees

                    balance += pnl
                    trades.append({
                        'entry_time': position['entry_time'],
                        'exit_time': row['timestamp'],
                        'side': 'short',
                        'entry': position['entry'],
                        'exit': exit_price,
                        'pnl': pnl,
                        'pnl_pct': pnl / position['margin'] * 100,
                        'reason': 'stop_loss'
                    })
                    position = None

                elif current_price <= position['target']:
                    exit_price = position['target']
                    pnl_pct = (position['entry'] - exit_price) / position['entry']
                    pnl = pnl_pct * leverage * position['margin']

                    position_value = position['margin'] * leverage
                    fees = position_value * FEE_PCT * 2
                    pnl -= fees

                    balance += pnl
                    trades.append({
                        'entry_time': position['entry_time'],
                        'exit_time': row['timestamp'],
                        'side': 'short',
                        'entry': position['entry'],
                        'exit': exit_price,
                        'pnl': pnl,
                        'pnl_pct': pnl / position['margin'] * 100,
                        'reason': 'take_profit'
                    })
                    position = None

        # Generate signals (Bollinger Mean Reversion)
        if position is None:
            signal = None

            if row['close'] < row['bb_lower'] and row['rsi'] < rsi_oversold:
                signal = 'long'
            elif row['close'] > row['bb_upper'] and row['rsi'] > rsi_overbought:
                signal = 'short'

            if signal:
                entry_price = row['close']
                margin = balance * risk_per_trade  # Amount we're risking

                if signal == 'long':
                    stop = entry_price - (row['atr'] * sl_mult)
                    target = entry_price + (row['atr'] * tp_mult)
                else:
                    stop = entry_price + (row['atr'] * sl_mult)
                    target = entry_price - (row['atr'] * tp_mult)

                position = {
                    'entry_time': row['timestamp'],
                    'side': signal,
                    'entry': entry_price,
                    'stop': stop,
                    'target': target,
                    'margin': margin,
                    'unrealized_pnl': 0
                }

        equity.append(balance if position is None else balance + position.get('unrealized_pnl', 0))

    if len(trades) < 5:
        return None

    trades_df = pd.DataFrame(trades)

    total_return = (balance - 10000) / 10000 * 100
    wins = trades_df[trades_df['pnl'] > 0]
    losses = trades_df[trades_df['pnl'] <= 0]

    win_rate = len(wins) / len(trades_df) * 100
    avg_win = wins['pnl'].mean() if len(wins) > 0 else 0
    avg_loss = losses['pnl'].mean() if len(losses) > 0 else 0

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
        'final_balance': balance,
        'trades': trades_df
    }


# Test different parameter combinations
print("\n" + "=" * 80)
print("TESTING PARAMETER COMBINATIONS")
print("=" * 80)

results = []
combo_count = 0
total_combos = 4 * 4 * 3 * 4 * 4  # 768

sessions = {
    'All Hours': None,
    'European (07-15)': list(range(7, 15)),
    'US (13-21)': list(range(13, 21)),
    'Euro+US (07-21)': list(range(7, 21)),
}

for session_name, hours in sessions.items():
    for leverage in [5, 10, 15, 20]:
        for sl_mult in [1.0, 1.5, 2.0]:
            for tp_mult in [2.0, 3.0, 4.0, 5.0]:
                for risk in [0.01, 0.02, 0.03, 0.05]:
                    combo_count += 1
                    if combo_count % 50 == 0:
                        print(f"Progress: {combo_count}/{total_combos} ({combo_count/total_combos*100:.1f}%)", flush=True)

                    result = backtest_corrected(
                        df,
                        allowed_hours=hours,
                        leverage=leverage,
                        sl_mult=sl_mult,
                        tp_mult=tp_mult,
                        risk_per_trade=risk
                    )

                    if result and result['total_trades'] >= 10:
                        results.append({
                            'session': session_name,
                            'leverage': leverage,
                            'sl_mult': sl_mult,
                            'tp_mult': tp_mult,
                            'risk_pct': risk * 100,
                            **{k: v for k, v in result.items() if k != 'trades'}
                        })

# Sort by profit/DD ratio
results_df = pd.DataFrame(results)
results_df = results_df.sort_values('profit_dd_ratio', ascending=False)

print(f"\nTested {len(results_df)} parameter combinations")

# Show top 20
print("\n" + "=" * 80)
print("TOP 20 STRATEGIES (by Profit/DD Ratio)")
print("=" * 80)

top20 = results_df.head(20)
for i, row in top20.iterrows():
    ratio_status = "✅" if row['profit_dd_ratio'] >= 4.0 else "❌"
    print(f"\n{ratio_status} Session: {row['session']} | Leverage: {row['leverage']}x | SL: {row['sl_mult']}x | TP: {row['tp_mult']}x | Risk: {row['risk_pct']:.1f}%")
    print(f"   Return: {row['total_return']:.2f}% | Max DD: {row['max_drawdown']:.2f}% | P/DD: {row['profit_dd_ratio']:.2f}:1 | WR: {row['win_rate']:.1f}% | Trades: {row['total_trades']}")

# Find strategies meeting the 4:1 target
winners = results_df[results_df['profit_dd_ratio'] >= 4.0]

print("\n" + "=" * 80)
print("STRATEGIES MEETING 4:1 TARGET")
print("=" * 80)

if len(winners) > 0:
    print(f"\n✅ Found {len(winners)} strategies with profit/DD >= 4.0!")

    best = winners.iloc[0]
    print(f"\n📌 BEST STRATEGY:")
    print(f"   Session: {best['session']}")
    print(f"   Leverage: {best['leverage']}x")
    print(f"   Stop Loss: {best['sl_mult']}x ATR")
    print(f"   Take Profit: {best['tp_mult']}x ATR")
    print(f"   Risk per trade: {best['risk_pct']:.1f}%")
    print(f"\n   Performance:")
    print(f"   Total Return: {best['total_return']:.2f}%")
    print(f"   Max Drawdown: {best['max_drawdown']:.2f}%")
    print(f"   Profit/DD Ratio: {best['profit_dd_ratio']:.2f}:1")
    print(f"   Win Rate: {best['win_rate']:.1f}%")
    print(f"   Total Trades: {best['total_trades']}")
    print(f"   Avg Win: ${best['avg_win']:.2f}")
    print(f"   Avg Loss: ${best['avg_loss']:.2f}")
else:
    print("\n❌ No strategies met the 4:1 target with these parameters")
    print("\nBest available:")
    best = results_df.iloc[0]
    print(f"   Return: {best['total_return']:.2f}%")
    print(f"   Max DD: {best['max_drawdown']:.2f}%")
    print(f"   Profit/DD: {best['profit_dd_ratio']:.2f}:1")

# Save results
results_df.to_csv('./results/eth_corrected_results.csv', index=False)
print("\nSaved: ./results/eth_corrected_results.csv")
