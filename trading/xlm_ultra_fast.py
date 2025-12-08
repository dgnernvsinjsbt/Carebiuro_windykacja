"""
XLM/USDT Ultra-Fast Test
Minimal number of strategies, optimized for speed
"""

import pandas as pd
import numpy as np

print("Loading...")
df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/xlm_usdt_1m_lbank.csv')
print(f"Loaded {len(df):,} candles")

# Minimal indicators
df['tr'] = np.maximum(df['high'] - df['low'], np.maximum(abs(df['high'] - df['close'].shift(1)), abs(df['low'] - df['close'].shift(1))))
df['atr'] = df['tr'].rolling(14).mean()
df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
delta = df['close'].diff()
df['rsi'] = 100 - (100 / (1 + (delta.where(delta > 0, 0)).rolling(14).mean() / (-delta.where(delta < 0, 0)).rolling(14).mean()))

def fast_backtest(entries, sl_mult, tp_mult):
    """Ultra-fast backtest - sample trades instead of testing all"""
    equity = 1000
    peak = 1000
    max_dd = 0
    wins = 0
    total = 0

    # Sample every 5th entry to speed up
    entry_indices = np.where(entries)[0][::5]

    for idx in entry_indices[:500]:  # Cap at 500 trades max
        if idx < 250 or idx >= len(df) - 50:
            continue

        entry_price = df.iloc[idx]['close']
        sl = entry_price - sl_mult * df.iloc[idx]['atr']
        tp = entry_price + tp_mult * df.iloc[idx]['atr']

        # Check next 50 bars only
        for j in range(idx + 1, min(idx + 50, len(df))):
            if df.iloc[j]['low'] <= sl:
                pnl_pct = ((sl - entry_price) / entry_price) * 10 - 0.02
                equity += equity * pnl_pct
                total += 1
                break
            elif df.iloc[j]['high'] >= tp:
                pnl_pct = ((tp - entry_price) / entry_price) * 10 - 0.02
                equity += equity * pnl_pct
                wins += 1
                total += 1
                break

        if equity > peak:
            peak = equity
        dd = (peak - equity) / peak
        if dd > max_dd:
            max_dd = dd

    if total < 20:
        return None

    wr = wins / total * 100
    pnl = (equity - 1000) / 1000 * 100
    rr = (equity - 1000) / (max_dd * peak) if max_dd > 0 else 0

    return {'trades': total, 'wr': wr, 'pnl': pnl, 'dd': max_dd*100, 'rr': rr}

print("\nTesting strategies...\n")

# Strategy 1: EMA Pullback
print("1. EMA20 Pullback")
entries = ((df['low'] <= df['ema20']) & (df['close'] > df['ema20']) & (df['rsi'] > 40)).fillna(False)
for sl in [1.5, 2.0, 2.5]:
    for tp in [3.0, 4.0, 5.0]:
        r = fast_backtest(entries, sl, tp)
        if r:
            print(f"  SL:{sl} TP:{tp} -> {r['trades']} trades, {r['wr']:.1f}% WR, {r['pnl']:.1f}% PnL, R:R {r['rr']:.2f}")

# Strategy 2: RSI Oversold
print("\n2. RSI Oversold Bounce")
entries = ((df['rsi'] < 30) & (df['rsi'] > df['rsi'].shift(1)) & (df['close'] > df['open'])).fillna(False)
for sl in [1.5, 2.0, 2.5]:
    for tp in [3.0, 4.0, 5.0]:
        r = fast_backtest(entries, sl, tp)
        if r:
            print(f"  SL:{sl} TP:{tp} -> {r['trades']} trades, {r['wr']:.1f}% WR, {r['pnl']:.1f}% PnL, R:R {r['rr']:.2f}")

# Strategy 3: Combined
print("\n3. Conservative Combo")
entries = ((df['close'] > df['ema20']) & (df['low'] <= df['ema20']) & (df['rsi'] > 45) & (df['rsi'] < 60)).fillna(False)
for sl in [2.0, 2.5, 3.0]:
    for tp in [4.0, 5.0, 6.0]:
        r = fast_backtest(entries, sl, tp)
        if r:
            print(f"  SL:{sl} TP:{tp} -> {r['trades']} trades, {r['wr']:.1f}% WR, {r['pnl']:.1f}% PnL, R:R {r['rr']:.2f}")

print("\n✓ Test complete!")

# Save to file
with open('/workspaces/Carebiuro_windykacja/trading/results/xlm_ultra_fast_output.txt', 'w') as f:
    f.write("XLM/USDT Ultra-Fast Test Results\n")
    f.write("=" * 80 + "\n\n")
    f.write(f"Tested {len(df):,} candles\n")
    f.write("See console output for detailed results\n")
