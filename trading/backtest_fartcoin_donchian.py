"""
Donchian Channel Breakout Backtest - FARTCOIN
Parameters from DonchianBreakout.py:
  'FARTCOIN/USDT:USDT': {'period': 15, 'tp_atr': 7.5, 'sl_atr': 2}
"""
import pandas as pd
import numpy as np

# Load FARTCOIN 1H data
df = pd.read_csv('trading/fartcoin_1h_jun_dec_2025.csv', parse_dates=['timestamp'])

# FARTCOIN specific parameters (from DonchianBreakout.py)
PERIOD = 15
TP_ATR = 7.5
SL_ATR = 2.0
RISK_PCT = 3.0
MAX_LEVERAGE = 5.0
FEE_PCT = 0.07

print("="*60)
print("FARTCOIN DONCHIAN BREAKOUT BACKTEST")
print("="*60)
print(f"Parameters: Period={PERIOD}, TP={TP_ATR}xATR, SL={SL_ATR}xATR")
print(f"Risk: {RISK_PCT}% per trade, Max Leverage: {MAX_LEVERAGE}x")

# Calculate indicators
df['atr'] = (df['high'] - df['low']).rolling(14).mean()
df['donchian_upper'] = df['high'].rolling(PERIOD).max().shift(1)
df['donchian_lower'] = df['low'].rolling(PERIOD).min().shift(1)

# Backtest
equity = 100.0
max_equity = 100.0
max_dd = 0
trades = []

i = max(PERIOD, 14) + 1
while i < len(df) - 100:
    row = df.iloc[i]
    atr = row['atr']
    
    if pd.isna(atr) or atr <= 0:
        i += 1
        continue
    
    # Check for signal
    signal_dir = None
    if row['close'] > row['donchian_upper'] and not pd.isna(row['donchian_upper']):
        signal_dir = 'LONG'
    elif row['close'] < row['donchian_lower'] and not pd.isna(row['donchian_lower']):
        signal_dir = 'SHORT'
    
    if signal_dir is None:
        i += 1
        continue
    
    entry_price = row['close']
    
    # Calculate TP/SL
    if signal_dir == 'LONG':
        tp_price = entry_price + TP_ATR * atr
        sl_price = entry_price - SL_ATR * atr
        sl_dist_pct = (entry_price - sl_price) / entry_price * 100
    else:
        tp_price = entry_price - TP_ATR * atr
        sl_price = entry_price + SL_ATR * atr
        sl_dist_pct = (sl_price - entry_price) / entry_price * 100
    
    # Position sizing
    leverage = min(RISK_PCT / sl_dist_pct, MAX_LEVERAGE) if sl_dist_pct > 0 else 1
    
    # Simulate trade
    outcome = None
    for j in range(i + 1, min(i + 200, len(df))):
        candle = df.iloc[j]
        
        if signal_dir == 'LONG':
            if candle['low'] <= sl_price:
                outcome = 'SL'
                exit_price = sl_price
                exit_bar = j
                break
            if candle['high'] >= tp_price:
                outcome = 'TP'
                exit_price = tp_price
                exit_bar = j
                break
        else:
            if candle['high'] >= sl_price:
                outcome = 'SL'
                exit_price = sl_price
                exit_bar = j
                break
            if candle['low'] <= tp_price:
                outcome = 'TP'
                exit_price = tp_price
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
    equity_change = leverage * pnl_pct / 100
    equity *= (1 + equity_change)
    
    # Track drawdown
    max_equity = max(max_equity, equity)
    dd = (max_equity - equity) / max_equity * 100
    max_dd = max(max_dd, dd)
    
    trades.append({
        'bar': i,
        'date': row['timestamp'],
        'direction': signal_dir,
        'entry': entry_price,
        'exit': exit_price,
        'tp': tp_price,
        'sl': sl_price,
        'outcome': outcome,
        'pnl_pct': pnl_pct,
        'leverage': leverage,
        'equity': equity,
        'dd': dd
    })
    
    i = exit_bar + 1

# Results
wins = sum(1 for t in trades if t['outcome'] == 'TP')
losses = sum(1 for t in trades if t['outcome'] == 'SL')
total_return = (equity / 100 - 1) * 100
rr_ratio = total_return / max_dd if max_dd > 0 else 0

print(f"\n{'='*60}")
print("RESULTS")
print("="*60)
print(f"Total Trades: {len(trades)} ({wins}W / {losses}L)")
print(f"Win Rate: {wins / len(trades) * 100:.1f}%" if len(trades) > 0 else "N/A")
print(f"Final Equity: ${equity:.2f}")
print(f"Total Return: {total_return:+.1f}%")
print(f"Max Drawdown: -{max_dd:.1f}%")
print(f"R:R Ratio: {rr_ratio:.2f}x")

# Monthly breakdown
df_trades = pd.DataFrame(trades)
if len(df_trades) > 0:
    df_trades['month'] = pd.to_datetime(df_trades['date']).dt.to_period('M')
    print(f"\n{'='*60}")
    print("MONTHLY BREAKDOWN")
    print("="*60)
    for month in df_trades['month'].unique():
        month_trades = df_trades[df_trades['month'] == month]
        month_wins = (month_trades['outcome'] == 'TP').sum()
        month_losses = (month_trades['outcome'] == 'SL').sum()
        month_pnl = month_trades['pnl_pct'].sum()
        print(f"{month}: {len(month_trades)} trades ({month_wins}W/{month_losses}L), PnL: {month_pnl:+.1f}%")

# Trade sample
print(f"\n{'='*60}")
print("SAMPLE TRADES (first 5)")
print("="*60)
for t in trades[:5]:
    print(f"{t['date'].strftime('%Y-%m-%d %H:%M')}: {t['direction']} @ ${t['entry']:.4f} → {t['outcome']} @ ${t['exit']:.4f} ({t['pnl_pct']:+.2f}%)")

# Average metrics
if len(trades) > 0:
    avg_win = np.mean([t['pnl_pct'] for t in trades if t['outcome'] == 'TP'])
    avg_loss = np.mean([t['pnl_pct'] for t in trades if t['outcome'] == 'SL'])
    print(f"\nAvg Win: {avg_win:+.2f}%, Avg Loss: {avg_loss:.2f}%")
    print(f"Win/Loss Ratio: {abs(avg_win/avg_loss):.2f}x")

