"""XLM/USDT Final Test - Absolute Minimal"""
import pandas as pd
import numpy as np

# Load
df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/xlm_usdt_1m_lbank.csv')
df['atr'] = np.maximum(df['high'] - df['low'], np.maximum(abs(df['high'] - df['close'].shift(1)), abs(df['low'] - df['close'].shift(1)))).rolling(14).mean()
df['ema20'] = df['close'].ewm(20).mean()
delta = df['close'].diff()
df['rsi'] = 100 - (100 / (1 + (delta.where(delta > 0, 0)).rolling(14).mean() / (-delta.where(delta < 0, 0)).rolling(14).mean()))

# Single strategy test
entry_signal = ((df['low'] <= df['ema20']) & (df['close'] > df['ema20']) & (df['rsi'] > 40)).fillna(False).values

equity, peak, max_dd, wins, total = 1000, 1000, 0, 0, 0

for idx in np.where(entry_signal)[0][::10][:100]:  # Sample 100 trades
    if idx < 250 or idx >= len(df) - 30:
        continue
    entry = df.iloc[idx]['close']
    sl = entry - 2 * df.iloc[idx]['atr']
    tp = entry + 4 * df.iloc[idx]['atr']

    for j in range(idx + 1, min(idx + 30, len(df))):
        if df.iloc[j]['low'] <= sl:
            pnl_pct = ((sl - entry) / entry) * 10 - 0.02
            equity += equity * pnl_pct
            total += 1
            break
        elif df.iloc[j]['high'] >= tp:
            pnl_pct = ((tp - entry) / entry) * 10 - 0.02
            equity += equity * pnl_pct
            wins += 1
            total += 1
            break
    if equity > peak:
        peak = equity
    dd = (peak - equity) / peak
    if dd > max_dd:
        max_dd = dd

# Results
wr = wins / total * 100 if total > 0 else 0
pnl = (equity - 1000) / 1000 * 100
rr = (equity - 1000) / (max_dd * peak) if max_dd > 0 else 0

results = f"""
XLM/USDT TEST RESULTS
{"=" * 50}
Strategy: EMA20 Pullback
SL: 2x ATR | TP: 4x ATR

Trades: {total}
Win Rate: {wr:.1f}%
Total P&L: {pnl:.1f}%
Max DD: {max_dd*100:.1f}%
R:R Ratio: {rr:.2f}
Final Equity: ${equity:.2f}

{'✅ PASS' if rr >= 2.0 and wr >= 50.0 else '❌ FAIL'} (Target: R:R >= 2.0, WR >= 50%)
"""

print(results)

# Save
with open('/workspaces/Carebiuro_windykacja/trading/results/xlm_final_results.txt', 'w') as f:
    f.write(results)
