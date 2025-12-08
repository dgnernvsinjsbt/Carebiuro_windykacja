"""
ETH/USDT Quick Backtest - Fewer parameters, verified formula
"""

import pandas as pd
import numpy as np

print("=" * 80)
print("ETH/USDT SPOT (Long Only, 0 Fees)")
print("=" * 80)

# Load data - first 7 days for quick test
df = pd.read_csv('./eth_usdt_1m_lbank.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# Use full dataset (all 30 days)
# df = df.head(10080)  # 7 days for quick test

print(f"Loaded {len(df):,} candles ({(df['timestamp'].max() - df['timestamp'].min()).days} days)")

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

df = df.dropna()

def backtest_corrected(df, allowed_hours=None, leverage=10,
                       sl_mult=1.5, tp_mult=2.5, risk_per_trade=0.02):
    """Corrected backtest with proper PnL calculation"""
    balance = 10000
    position = None
    trades = []
    equity = [balance]

    FEE_PCT = 0  # Spot trading - no fees

    for i in range(250, len(df)):
        row = df.iloc[i]

        if allowed_hours is not None and row['hour'] not in allowed_hours:
            equity.append(balance if position is None else balance + position.get('unrealized_pnl', 0))
            continue

        if position is not None:
            current_price = row['close']

            if position['side'] == 'long':
                price_pct_change = (current_price - position['entry']) / position['entry']
                position['unrealized_pnl'] = price_pct_change * leverage * position['margin']

                if current_price <= position['stop']:
                    exit_price = position['stop']
                    pnl_pct = (exit_price - position['entry']) / position['entry']
                    pnl = pnl_pct * leverage * position['margin']
                    position_value = position['margin'] * leverage
                    fees = position_value * FEE_PCT * 2
                    pnl -= fees
                    balance += pnl
                    trades.append({'side': 'long', 'entry': position['entry'], 'exit': exit_price, 'pnl': pnl, 'reason': 'stop_loss'})
                    position = None

                elif current_price >= position['target']:
                    exit_price = position['target']
                    pnl_pct = (exit_price - position['entry']) / position['entry']
                    pnl = pnl_pct * leverage * position['margin']
                    position_value = position['margin'] * leverage
                    fees = position_value * FEE_PCT * 2
                    pnl -= fees
                    balance += pnl
                    trades.append({'side': 'long', 'entry': position['entry'], 'exit': exit_price, 'pnl': pnl, 'reason': 'take_profit'})
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
                    trades.append({'side': 'short', 'entry': position['entry'], 'exit': exit_price, 'pnl': pnl, 'reason': 'stop_loss'})
                    position = None

                elif current_price <= position['target']:
                    exit_price = position['target']
                    pnl_pct = (position['entry'] - exit_price) / position['entry']
                    pnl = pnl_pct * leverage * position['margin']
                    position_value = position['margin'] * leverage
                    fees = position_value * FEE_PCT * 2
                    pnl -= fees
                    balance += pnl
                    trades.append({'side': 'short', 'entry': position['entry'], 'exit': exit_price, 'pnl': pnl, 'reason': 'take_profit'})
                    position = None

        # Generate signals (Bollinger Mean Reversion)
        if position is None:
            signal = None

            # Long only for spot trading
            if row['close'] < row['bb_lower'] and row['rsi'] < 30:
                signal = 'long'

            if signal:
                entry_price = row['close']
                margin = balance * risk_per_trade

                if signal == 'long':
                    stop = entry_price - (row['atr'] * sl_mult)
                    target = entry_price + (row['atr'] * tp_mult)
                else:
                    stop = entry_price + (row['atr'] * sl_mult)
                    target = entry_price - (row['atr'] * tp_mult)

                position = {
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
    win_rate = len(wins) / len(trades_df) * 100

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
        'final_balance': balance
    }


# Quick parameter search - only 48 combinations
print("\nTesting 48 parameter combinations...")

results = []
combo = 0

sessions = {
    'All Hours': None,
    'Euro (07-15)': list(range(7, 15)),
    'US (13-21)': list(range(13, 21)),
}

for session_name, hours in sessions.items():
    for leverage in [1]:  # Spot = 1x only
        for sl_tp in [(1.5, 3.0), (1.5, 4.0), (2.0, 4.0), (2.0, 5.0), (1.0, 2.0), (1.0, 3.0)]:
            combo += 1
            print(f"  {combo}/48...", end='\r', flush=True)

            result = backtest_corrected(
                df,
                allowed_hours=hours,
                leverage=leverage,
                sl_mult=sl_tp[0],
                tp_mult=sl_tp[1],
                risk_per_trade=0.02
            )

            if result and result['total_trades'] >= 10:
                results.append({
                    'session': session_name,
                    'leverage': leverage,
                    'sl_mult': sl_tp[0],
                    'tp_mult': sl_tp[1],
                    **result
                })

print(f"\nCompleted! Tested {len(results)} valid combinations")

# Sort by profit/DD ratio
results_df = pd.DataFrame(results)
results_df = results_df.sort_values('profit_dd_ratio', ascending=False)

print("\n" + "=" * 80)
print("TOP 10 STRATEGIES (by Profit/DD Ratio)")
print("=" * 80)

for i, row in results_df.head(10).iterrows():
    status = "TARGET MET" if row['profit_dd_ratio'] >= 4.0 else ""
    print(f"\n{row['session']} | {row['leverage']}x | SL:{row['sl_mult']} TP:{row['tp_mult']} {status}")
    print(f"   Return: {row['total_return']:.2f}% | DD: {row['max_drawdown']:.2f}% | P/DD: {row['profit_dd_ratio']:.2f}:1 | WR: {row['win_rate']:.1f}% | Trades: {row['total_trades']}")

# Check 4:1 target
winners = results_df[results_df['profit_dd_ratio'] >= 4.0]

print("\n" + "=" * 80)
if len(winners) > 0:
    print(f"FOUND {len(winners)} strategies meeting 4:1 target!")
    best = winners.iloc[0]
    print(f"\nBEST: {best['session']} | {best['leverage']}x leverage")
    print(f"  Return: {best['total_return']:.2f}%")
    print(f"  Max DD: {best['max_drawdown']:.2f}%")
    print(f"  Profit/DD: {best['profit_dd_ratio']:.2f}:1")
else:
    print("No strategies met 4:1 target")
    best = results_df.iloc[0]
    print(f"\nBest available: {best['profit_dd_ratio']:.2f}:1 ratio")
    print(f"  Return: {best['total_return']:.2f}%")
    print(f"  Max DD: {best['max_drawdown']:.2f}%")

results_df.to_csv('./results/eth_corrected_results.csv', index=False)
print("\nSaved: ./results/eth_corrected_results.csv")
