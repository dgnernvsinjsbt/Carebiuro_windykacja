"""
ETH/USDT - Two approaches:
1. Spot trading (long only, 0 fees)
2. Low-frequency strategies (stricter filters)
"""

import pandas as pd
import numpy as np

print("=" * 80)
print("ETH/USDT SPOT & LOW-FREQUENCY STRATEGIES")
print("=" * 80)

# Load data
df = pd.read_csv('./eth_usdt_1m_lbank.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print(f"Loaded {len(df):,} candles ({(df['timestamp'].max() - df['timestamp'].min()).days} days)")

# Calculate indicators
df['hour'] = df['timestamp'].dt.hour

# Bollinger Bands (wider for fewer signals)
for period in [20, 50]:
    df[f'bb_middle_{period}'] = df['close'].rolling(period).mean()
    df[f'bb_std_{period}'] = df['close'].rolling(period).std()
    df[f'bb_upper_{period}'] = df[f'bb_middle_{period}'] + (2.5 * df[f'bb_std_{period}'])
    df[f'bb_lower_{period}'] = df[f'bb_middle_{period}'] - (2.5 * df[f'bb_std_{period}'])

# RSI
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

df['rsi'] = calculate_rsi(df['close'])
df['rsi_slow'] = calculate_rsi(df['close'], 21)

# ATR
df['tr'] = np.maximum(df['high'] - df['low'],
                      np.maximum(abs(df['high'] - df['close'].shift(1)),
                                abs(df['low'] - df['close'].shift(1))))
df['atr'] = df['tr'].rolling(14).mean()

# Volume spike
df['vol_ma'] = df['volume'].rolling(50).mean()
df['vol_spike'] = df['volume'] > df['vol_ma'] * 2.0

# EMA trend
df['ema_20'] = df['close'].ewm(span=20).mean()
df['ema_50'] = df['close'].ewm(span=50).mean()
df['uptrend'] = df['ema_20'] > df['ema_50']

df = df.dropna()


def backtest_spot_long(df, strategy='bb_oversold', sl_pct=0.02, tp_pct=0.04):
    """
    Spot trading: Long only, NO fees, NO leverage
    """
    balance = 10000
    position = None
    trades = []
    equity = [balance]

    for i in range(100, len(df)):
        row = df.iloc[i]

        # Check exit if in position
        if position is not None:
            current_price = row['close']
            pnl_pct = (current_price - position['entry']) / position['entry']

            # Stop loss
            if current_price <= position['stop']:
                pnl = position['size'] * (position['stop'] - position['entry']) / position['entry']
                balance += pnl
                trades.append({'entry': position['entry'], 'exit': position['stop'],
                             'pnl': pnl, 'pnl_pct': pnl/position['size']*100, 'reason': 'stop'})
                position = None

            # Take profit
            elif current_price >= position['target']:
                pnl = position['size'] * (position['target'] - position['entry']) / position['entry']
                balance += pnl
                trades.append({'entry': position['entry'], 'exit': position['target'],
                             'pnl': pnl, 'pnl_pct': pnl/position['size']*100, 'reason': 'tp'})
                position = None

        # Entry signals (long only)
        if position is None:
            signal = False

            if strategy == 'bb_oversold':
                # BB oversold + RSI < 25
                signal = row['close'] < row['bb_lower_20'] and row['rsi'] < 25

            elif strategy == 'bb_oversold_strict':
                # Very strict: BB50 + RSI < 20 + volume spike
                signal = (row['close'] < row['bb_lower_50'] and
                         row['rsi'] < 20 and row['vol_spike'])

            elif strategy == 'trend_pullback':
                # Uptrend + RSI pullback
                signal = row['uptrend'] and row['rsi'] < 35 and row['close'] > row['ema_50']

            elif strategy == 'extreme_oversold':
                # Extreme conditions only
                signal = row['rsi'] < 15

            if signal:
                entry_price = row['close']
                size = balance * 0.5  # 50% of balance per trade

                position = {
                    'entry': entry_price,
                    'stop': entry_price * (1 - sl_pct),
                    'target': entry_price * (1 + tp_pct),
                    'size': size
                }

        equity.append(balance if position is None else balance + position['size'] *
                     (row['close'] - position['entry']) / position['entry'])

    if len(trades) < 3:
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


# ============ TEST SPOT STRATEGIES ============
print("\n" + "=" * 80)
print("PART 1: SPOT TRADING (Long Only, 0 Fees)")
print("=" * 80)

spot_results = []

strategies = ['bb_oversold', 'bb_oversold_strict', 'trend_pullback', 'extreme_oversold']
sl_tp_combos = [(0.01, 0.02), (0.015, 0.03), (0.02, 0.04), (0.02, 0.06), (0.03, 0.06)]

for strat in strategies:
    for sl, tp in sl_tp_combos:
        result = backtest_spot_long(df, strategy=strat, sl_pct=sl, tp_pct=tp)
        if result:
            spot_results.append({
                'strategy': strat,
                'sl_pct': sl * 100,
                'tp_pct': tp * 100,
                **result
            })

spot_df = pd.DataFrame(spot_results)
if len(spot_df) > 0:
    spot_df = spot_df.sort_values('profit_dd_ratio', ascending=False)

    print(f"\nTested {len(spot_df)} combinations")
    print("\nTOP 10 SPOT STRATEGIES:")

    for i, row in spot_df.head(10).iterrows():
        status = "TARGET MET" if row['profit_dd_ratio'] >= 4.0 else ""
        print(f"\n{row['strategy']} | SL:{row['sl_pct']:.1f}% TP:{row['tp_pct']:.1f}% {status}")
        print(f"   Return: {row['total_return']:.2f}% | DD: {row['max_drawdown']:.2f}% | P/DD: {row['profit_dd_ratio']:.2f}:1 | WR: {row['win_rate']:.1f}% | Trades: {row['total_trades']}")

    winners = spot_df[spot_df['profit_dd_ratio'] >= 4.0]
    if len(winners) > 0:
        print(f"\n*** FOUND {len(winners)} strategies meeting 4:1 target! ***")
else:
    print("No valid spot strategies found")


# ============ LOW FREQUENCY FUTURES ============
print("\n" + "=" * 80)
print("PART 2: LOW-FREQUENCY FUTURES (Strict Filters)")
print("=" * 80)

def backtest_lowfreq_futures(df, rsi_threshold=20, require_vol_spike=True,
                             leverage=5, sl_mult=2.0, tp_mult=4.0):
    """
    Futures with strict entry filters for fewer trades
    """
    balance = 10000
    position = None
    trades = []
    equity = [balance]

    FEE_PCT = 0.00045  # 0.045% per side

    for i in range(100, len(df)):
        row = df.iloc[i]

        if position is not None:
            current_price = row['close']

            if position['side'] == 'long':
                if current_price <= position['stop']:
                    pnl_pct = (position['stop'] - position['entry']) / position['entry']
                    pnl = pnl_pct * leverage * position['margin']
                    fees = position['margin'] * leverage * FEE_PCT * 2
                    pnl -= fees
                    balance += pnl
                    trades.append({'side': 'long', 'pnl': pnl, 'reason': 'stop'})
                    position = None
                elif current_price >= position['target']:
                    pnl_pct = (position['target'] - position['entry']) / position['entry']
                    pnl = pnl_pct * leverage * position['margin']
                    fees = position['margin'] * leverage * FEE_PCT * 2
                    pnl -= fees
                    balance += pnl
                    trades.append({'side': 'long', 'pnl': pnl, 'reason': 'tp'})
                    position = None

            else:  # short
                if current_price >= position['stop']:
                    pnl_pct = (position['entry'] - position['stop']) / position['entry']
                    pnl = pnl_pct * leverage * position['margin']
                    fees = position['margin'] * leverage * FEE_PCT * 2
                    pnl -= fees
                    balance += pnl
                    trades.append({'side': 'short', 'pnl': pnl, 'reason': 'stop'})
                    position = None
                elif current_price <= position['target']:
                    pnl_pct = (position['entry'] - position['target']) / position['entry']
                    pnl = pnl_pct * leverage * position['margin']
                    fees = position['margin'] * leverage * FEE_PCT * 2
                    pnl -= fees
                    balance += pnl
                    trades.append({'side': 'short', 'pnl': pnl, 'reason': 'tp'})
                    position = None

        # Strict entry: RSI extreme + volume spike
        if position is None:
            signal = None

            vol_ok = row['vol_spike'] if require_vol_spike else True

            if row['rsi'] < rsi_threshold and vol_ok:
                signal = 'long'
            elif row['rsi'] > (100 - rsi_threshold) and vol_ok:
                signal = 'short'

            if signal:
                entry_price = row['close']
                margin = balance * 0.02

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
                    'margin': margin
                }

        equity.append(balance)

    if len(trades) < 3:
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


lowfreq_results = []

for rsi_th in [15, 18, 20, 22]:
    for vol_req in [True, False]:
        for lev in [3, 5, 10]:
            for sl, tp in [(1.5, 3.0), (2.0, 4.0), (2.0, 5.0), (2.5, 5.0)]:
                result = backtest_lowfreq_futures(df, rsi_threshold=rsi_th,
                                                  require_vol_spike=vol_req,
                                                  leverage=lev, sl_mult=sl, tp_mult=tp)
                if result:
                    lowfreq_results.append({
                        'rsi_th': rsi_th,
                        'vol_spike': vol_req,
                        'leverage': lev,
                        'sl': sl,
                        'tp': tp,
                        **result
                    })

lowfreq_df = pd.DataFrame(lowfreq_results)
if len(lowfreq_df) > 0:
    lowfreq_df = lowfreq_df.sort_values('profit_dd_ratio', ascending=False)

    print(f"\nTested {len(lowfreq_df)} combinations")
    print("\nTOP 10 LOW-FREQUENCY FUTURES:")

    for i, row in lowfreq_df.head(10).iterrows():
        status = "TARGET MET" if row['profit_dd_ratio'] >= 4.0 else ""
        vol = "Vol" if row['vol_spike'] else "NoVol"
        print(f"\nRSI<{row['rsi_th']} {vol} | {row['leverage']}x | SL:{row['sl']} TP:{row['tp']} {status}")
        print(f"   Return: {row['total_return']:.2f}% | DD: {row['max_drawdown']:.2f}% | P/DD: {row['profit_dd_ratio']:.2f}:1 | WR: {row['win_rate']:.1f}% | Trades: {row['total_trades']}")

    winners = lowfreq_df[lowfreq_df['profit_dd_ratio'] >= 4.0]
    if len(winners) > 0:
        print(f"\n*** FOUND {len(winners)} strategies meeting 4:1 target! ***")
else:
    print("No valid low-frequency strategies found")


# Save all results
print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

if len(spot_df) > 0:
    spot_winners = spot_df[spot_df['profit_dd_ratio'] >= 4.0]
    print(f"\nSpot (0 fees): {len(spot_winners)} strategies meet 4:1 target")
    if len(spot_winners) > 0:
        best = spot_winners.iloc[0]
        print(f"  Best: {best['strategy']} - {best['total_return']:.2f}% return, {best['profit_dd_ratio']:.2f}:1 ratio, {best['total_trades']} trades")

if len(lowfreq_df) > 0:
    lowfreq_winners = lowfreq_df[lowfreq_df['profit_dd_ratio'] >= 4.0]
    print(f"\nLow-freq futures (0.045% fees): {len(lowfreq_winners)} strategies meet 4:1 target")
    if len(lowfreq_winners) > 0:
        best = lowfreq_winners.iloc[0]
        print(f"  Best: RSI<{best['rsi_th']} {best['leverage']}x - {best['total_return']:.2f}% return, {best['profit_dd_ratio']:.2f}:1 ratio, {best['total_trades']} trades")
