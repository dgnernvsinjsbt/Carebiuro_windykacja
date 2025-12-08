"""
XLM/USDT Simple Test - Single Best Strategy
Testing BB Mean Reversion which worked on other coins
"""

import pandas as pd
import numpy as np

# Load data
df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/xlm_usdt_1m_lbank.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
print(f"Loaded {len(df):,} candles")

# Calculate indicators
df['tr'] = np.maximum(
    df['high'] - df['low'],
    np.maximum(abs(df['high'] - df['close'].shift(1)), abs(df['low'] - df['close'].shift(1)))
)
df['atr'] = df['tr'].rolling(14).mean()

# BB
df['bb_mid'] = df['close'].rolling(20).mean()
df['bb_std'] = df['close'].rolling(20).std()
df['bb_lower'] = df['bb_mid'] - 2 * df['bb_std']

# RSI
delta = df['close'].diff()
gain = (delta.where(delta > 0, 0)).rolling(14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
rs = gain / loss
df['rsi'] = 100 - (100 / (1 + rs))

# Simple backtest
capital = 1000
equity = capital
peak = capital
max_dd = 0
trades = []
in_pos = False

for i in range(250, len(df)):
    row = df.iloc[i]

    # Update DD
    if equity > peak:
        peak = equity
    dd = (peak - equity) / peak
    if dd > max_dd:
        max_dd = dd

    # Exit
    if in_pos:
        if row['low'] <= sl:
            pnl = ((sl - entry) / entry) * 10 - 0.02  # 10x leverage, 2% fees
            equity += equity * pnl
            trades.append({'pnl': pnl, 'reason': 'SL'})
            in_pos = False
        elif row['high'] >= tp:
            pnl = ((tp - entry) / entry) * 10 - 0.02
            equity += equity * pnl
            trades.append({'pnl': pnl, 'reason': 'TP'})
            in_pos = False

    # Entry: EMA20 pullback (different strategy)
    if not in_pos:
        ema20 = df.iloc[i]['bb_mid']  # Use BB mid as EMA20 approximation
        if row['close'] > ema20 and row['low'] <= ema20 and row['rsi'] > 40:
            entry = row['close']
            sl = entry - 1.5 * row['atr']
            tp = entry + 3 * row['atr']
            in_pos = True

# Results
trades_df = pd.DataFrame(trades)
total = len(trades_df)
winners = len(trades_df[trades_df['pnl'] > 0])
win_rate = winners / total * 100 if total > 0 else 0
total_pnl = (equity - capital) / capital * 100
rr = (equity - capital) / (max_dd * peak) if max_dd > 0 else 0

print(f"\nEMA20 Pullback - 1.5x SL, 3x TP")
print(f"Trades: {total}")
print(f"Win Rate: {win_rate:.1f}%")
print(f"Total P&L: {total_pnl:.2f}%")
print(f"Max DD: {max_dd*100:.2f}%")
print(f"R:R Ratio: {rr:.2f}")
print(f"Final Equity: ${equity:.2f}")
