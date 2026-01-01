"""
Sprawdzenie oryginalnego backtesta - dlaczego wyniki się różnią?
"""
import pandas as pd
import numpy as np

# Load data
df = pd.read_csv('trading/doge_1h_jun_dec_2025.csv', parse_dates=['timestamp'])

print(f"Data range: {df['timestamp'].min()} to {df['timestamp'].max()}")
print(f"Total candles: {len(df)}")
print(f"Price range: ${df['low'].min():.4f} to ${df['high'].max():.4f}")

# Parameters - EXACTLY as in original
PERIOD = 15
TP_ATR = 4.0
SL_ATR = 4.0
RISK_PCT = 3.0
MAX_LEVERAGE = 5.0
FEE_PCT = 0.07

# Calculate indicators
df['atr'] = (df['high'] - df['low']).rolling(14).mean()
df['donchian_upper'] = df['high'].rolling(PERIOD).max().shift(1)
df['donchian_lower'] = df['low'].rolling(PERIOD).min().shift(1)

# Original backtest logic - market orders only
equity = 100.0
max_equity = 100.0
max_dd = 0
trades = []

i = PERIOD + 14
while i < len(df) - 50:
    row = df.iloc[i]
    atr = row['atr']
    
    signal_dir = None
    if row['close'] > row['donchian_upper']:
        signal_dir = 'LONG'
    elif row['close'] < row['donchian_lower']:
        signal_dir = 'SHORT'
    
    if signal_dir is None:
        i += 1
        continue
    
    entry_price = row['close']
    
    # TP/SL from entry price
    if signal_dir == 'LONG':
        tp = entry_price * (1 + TP_ATR * atr / entry_price)
        sl = entry_price * (1 - SL_ATR * atr / entry_price)
        sl_dist_pct = SL_ATR * atr / entry_price * 100
    else:
        tp = entry_price * (1 - TP_ATR * atr / entry_price)
        sl = entry_price * (1 + SL_ATR * atr / entry_price)
        sl_dist_pct = SL_ATR * atr / entry_price * 100
    
    leverage = min(RISK_PCT / sl_dist_pct, MAX_LEVERAGE)
    
    # Find exit
    outcome = None
    for j in range(i + 1, min(i + 200, len(df))):
        candle = df.iloc[j]
        
        if signal_dir == 'LONG':
            # Check SL first (more conservative)
            if candle['low'] <= sl:
                outcome = 'SL'
                exit_price = sl
                exit_bar = j
                break
            if candle['high'] >= tp:
                outcome = 'TP'
                exit_price = tp
                exit_bar = j
                break
        else:
            if candle['high'] >= sl:
                outcome = 'SL'
                exit_price = sl
                exit_bar = j
                break
            if candle['low'] <= tp:
                outcome = 'TP'
                exit_price = tp
                exit_bar = j
                break
    
    if outcome is None:
        i += 1
        continue
    
    # Calculate PnL
    if signal_dir == 'LONG':
        pnl_pct = (exit_price - entry_price) / entry_price * 100
    else:
        pnl_pct = (entry_price - exit_price) / entry_price * 100
    
    pnl_pct -= 2 * FEE_PCT  # fees
    
    # Update equity
    equity *= (1 + leverage * pnl_pct / 100)
    
    # Track DD
    max_equity = max(max_equity, equity)
    dd = (max_equity - equity) / max_equity * 100
    max_dd = max(max_dd, dd)
    
    trades.append({
        'bar': i,
        'direction': signal_dir,
        'entry': entry_price,
        'exit': exit_price,
        'outcome': outcome,
        'pnl_pct': pnl_pct,
        'leverage': leverage,
        'equity': equity
    })
    
    i = exit_bar + 1

wins = sum(1 for t in trades if t['outcome'] == 'TP')
losses = sum(1 for t in trades if t['outcome'] == 'SL')
total_return = (equity / 100 - 1) * 100
rr_ratio = total_return / max_dd if max_dd > 0 else 0

print(f"\n{'='*60}")
print(f"ORIGINAL BACKTEST RESULTS - MARKET ORDERS")
print(f"{'='*60}")
print(f"Trades: {len(trades)} ({wins}W / {losses}L)")
print(f"Win Rate: {wins / len(trades) * 100:.1f}%")
print(f"Final Equity: ${equity:.2f}")
print(f"Return: {total_return:+.1f}%")
print(f"Max DD: -{max_dd:.1f}%")
print(f"R:R Ratio: {rr_ratio:.2f}x")

# Debug - first 5 trades
print(f"\nFirst 5 trades:")
for t in trades[:5]:
    print(f"  Bar {t['bar']}: {t['direction']} @ ${t['entry']:.4f} → {t['outcome']} @ ${t['exit']:.4f}, PnL: {t['pnl_pct']:.2f}%")

# Check if there's an issue with data
print(f"\nATR range: {df['atr'].min():.4f} to {df['atr'].max():.4f}")
print(f"Average ATR: {df['atr'].mean():.4f}")
print(f"Average SL distance: {trades[0]['entry'] * SL_ATR * df['atr'].mean() / trades[0]['entry']:.4f}")

