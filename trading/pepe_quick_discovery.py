#!/usr/bin/env python3
"""
PEPE/USDT Quick Strategy Discovery
Focus on most promising approaches based on meme coin characteristics
"""

import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Load data
print("Loading PEPE/USDT 1m data...")
df = pd.read_csv('pepe_usdt_1m_lbank.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print(f"Data: {len(df)} candles from {df['timestamp'].iloc[0]} to {df['timestamp'].iloc[-1]}")
print(f"Price range: ${df['close'].min():.8f} to ${df['close'].max():.8f}\n")

# Calculate core indicators
df['returns'] = df['close'].pct_change()

# Bollinger Bands
df['bb_mid'] = df['close'].rolling(20).mean()
df['bb_std'] = df['close'].rolling(20).std()
df['bb_upper'] = df['bb_mid'] + 2 * df['bb_std']
df['bb_lower'] = df['bb_mid'] - 2 * df['bb_std']

# EMAs
df['ema_9'] = df['close'].ewm(span=9).mean()
df['ema_20'] = df['close'].ewm(span=20).mean()
df['ema_50'] = df['close'].ewm(span=50).mean()

# RSI
delta = df['close'].diff()
gain = delta.where(delta > 0, 0).rolling(14).mean()
loss = -delta.where(delta < 0, 0).rolling(14).mean()
rs = gain / loss
df['rsi'] = 100 - (100 / (1 + rs))

# ATR
high_low = df['high'] - df['low']
high_close = abs(df['high'] - df['close'].shift())
low_close = abs(df['low'] - df['close'].shift())
tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
df['atr'] = tr.rolling(14).mean()

# Volume
df['vol_sma'] = df['volume'].rolling(20).mean()
df['vol_ratio'] = df['volume'] / df['vol_sma']

# Session
df['hour'] = df['timestamp'].dt.hour

df = df.dropna().reset_index(drop=True)
print(f"After indicators: {len(df)} candles\n")


def run_backtest(df, entry_signal, strategy_name, fee_pct=0.1,
                atr_sl_mult=2.0, atr_tp_mult=4.0):
    """Simple backtest with ATR stops"""

    trades = []
    position = None

    for i in range(len(df)):
        row = df.iloc[i]

        if position is None and entry_signal.iloc[i]:
            entry_price = row['close']
            stop_loss = entry_price - (row['atr'] * atr_sl_mult)
            take_profit = entry_price + (row['atr'] * atr_tp_mult)

            position = {
                'entry_time': row['timestamp'],
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'entry_idx': i
            }

        elif position is not None:
            if row['low'] <= position['stop_loss']:
                exit_price = position['stop_loss']
                exit_reason = 'SL'
            elif row['high'] >= position['take_profit']:
                exit_price = position['take_profit']
                exit_reason = 'TP'
            else:
                continue

            pnl_pct = ((exit_price / position['entry_price']) - 1) * 100
            pnl_net = pnl_pct - fee_pct

            trades.append({
                'entry_time': position['entry_time'],
                'exit_time': row['timestamp'],
                'entry_price': position['entry_price'],
                'exit_price': exit_price,
                'pnl_gross': pnl_pct,
                'pnl_net': pnl_net,
                'exit_reason': exit_reason,
                'duration_mins': i - position['entry_idx']
            })

            position = None

    if len(trades) == 0:
        return None

    trades_df = pd.DataFrame(trades)
    total_pnl = trades_df['pnl_net'].sum()
    win_trades = trades_df[trades_df['pnl_net'] > 0]
    loss_trades = trades_df[trades_df['pnl_net'] <= 0]

    win_rate = len(win_trades) / len(trades_df) * 100
    avg_win = win_trades['pnl_net'].mean() if len(win_trades) > 0 else 0
    avg_loss = loss_trades['pnl_net'].mean() if len(loss_trades) > 0 else 0

    cumulative = trades_df['pnl_net'].cumsum()
    running_max = cumulative.expanding().max()
    drawdown = cumulative - running_max
    max_dd = abs(drawdown.min()) if len(drawdown) > 0 else 0.01

    rr_ratio = total_pnl / max_dd if max_dd > 0 else 0

    return {
        'strategy': strategy_name,
        'total_trades': len(trades_df),
        'win_rate': win_rate,
        'total_pnl': total_pnl,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'max_dd': max_dd,
        'rr_ratio': rr_ratio,
        'avg_duration_mins': trades_df['duration_mins'].mean()
    }


results = []

print("=" * 80)
print("QUICK STRATEGY DISCOVERY - PEPE/USDT")
print("=" * 80)

# Test 1: BB Mean Reversion (baseline from other meme coins)
print("\n[1] BB Mean Reversion...")
entry = df['close'] < df['bb_lower']
for sl, tp in [(1.5, 3.0), (2.0, 4.0), (2.5, 5.0), (3.0, 6.0)]:
    r = run_backtest(df, entry, f"BB_MeanRev_ATR_{sl}x{tp}", atr_sl_mult=sl, atr_tp_mult=tp)
    if r and r['total_trades'] >= 30:
        results.append(r)
        print(f"  ATR {sl}x{tp}: {r['total_trades']} trades, WR={r['win_rate']:.1f}%, "
              f"PnL={r['total_pnl']:.2f}%, R:R={r['rr_ratio']:.2f}")

# Test 2: EMA Trend Following
print("\n[2] EMA Trend Following...")
entry = (df['ema_9'] > df['ema_20']) & (df['ema_9'].shift(1) <= df['ema_20'].shift(1))
for sl, tp in [(2.0, 4.0), (2.5, 5.0), (3.0, 6.0)]:
    r = run_backtest(df, entry, f"EMA9_20_ATR_{sl}x{tp}", atr_sl_mult=sl, atr_tp_mult=tp)
    if r and r['total_trades'] >= 30:
        results.append(r)
        print(f"  ATR {sl}x{tp}: {r['total_trades']} trades, WR={r['win_rate']:.1f}%, "
              f"PnL={r['total_pnl']:.2f}%, R:R={r['rr_ratio']:.2f}")

# Test 3: RSI Oversold
print("\n[3] RSI Oversold...")
for threshold in [20, 25, 30]:
    entry = df['rsi'] < threshold
    r = run_backtest(df, entry, f"RSI_OS{threshold}_ATR_2x4", atr_sl_mult=2.0, atr_tp_mult=4.0)
    if r and r['total_trades'] >= 30:
        results.append(r)
        print(f"  RSI<{threshold}: {r['total_trades']} trades, WR={r['win_rate']:.1f}%, "
              f"PnL={r['total_pnl']:.2f}%, R:R={r['rr_ratio']:.2f}")

# Test 4: Volume Surge + Momentum
print("\n[4] Volume Surge + Momentum...")
for vol_mult in [2.0, 3.0, 5.0]:
    entry = (df['vol_ratio'] > vol_mult) & (df['close'] > df['close'].shift(1))
    r = run_backtest(df, entry, f"VolSurge_{vol_mult}x_ATR_2x4", atr_sl_mult=2.0, atr_tp_mult=4.0)
    if r and r['total_trades'] >= 30:
        results.append(r)
        print(f"  Vol>{vol_mult}x: {r['total_trades']} trades, WR={r['win_rate']:.1f}%, "
              f"PnL={r['total_pnl']:.2f}%, R:R={r['rr_ratio']:.2f}")

# Test 5: EMA Pullback (trending + oversold RSI)
print("\n[5] EMA Pullback in Uptrend...")
entry = (df['close'] > df['ema_20']) & (df['rsi'] < 30)
for sl, tp in [(2.0, 4.0), (2.5, 5.0), (3.0, 6.0)]:
    r = run_backtest(df, entry, f"EMA_RSI_Pullback_ATR_{sl}x{tp}", atr_sl_mult=sl, atr_tp_mult=tp)
    if r and r['total_trades'] >= 30:
        results.append(r)
        print(f"  ATR {sl}x{tp}: {r['total_trades']} trades, WR={r['win_rate']:.1f}%, "
              f"PnL={r['total_pnl']:.2f}%, R:R={r['rr_ratio']:.2f}")

# Test 6: Session-based strategies
print("\n[6] Session-Based Strategies...")
for session_name, hours in [('Asian', (0, 8)), ('Euro', (8, 14)), ('US', (14, 22))]:
    session_mask = (df['hour'] >= hours[0]) & (df['hour'] < hours[1])

    # BB + Session
    entry = (df['close'] < df['bb_lower']) & session_mask
    r = run_backtest(df, entry, f"BB_MeanRev_{session_name}_ATR_2x4", atr_sl_mult=2.0, atr_tp_mult=4.0)
    if r and r['total_trades'] >= 30:
        results.append(r)
        print(f"  BB {session_name}: {r['total_trades']} trades, WR={r['win_rate']:.1f}%, "
              f"PnL={r['total_pnl']:.2f}%, R:R={r['rr_ratio']:.2f}")

    # EMA + Session
    entry = (df['ema_9'] > df['ema_20']) & (df['ema_9'].shift(1) <= df['ema_20'].shift(1)) & session_mask
    r = run_backtest(df, entry, f"EMA9_20_{session_name}_ATR_2x4", atr_sl_mult=2.0, atr_tp_mult=4.0)
    if r and r['total_trades'] >= 30:
        results.append(r)
        print(f"  EMA {session_name}: {r['total_trades']} trades, WR={r['win_rate']:.1f}%, "
              f"PnL={r['total_pnl']:.2f}%, R:R={r['rr_ratio']:.2f}")

# Test 7: Different fee structures (limit orders)
print("\n[7] Limit Order Strategies (0.07% fees)...")
entry = df['close'] < df['bb_lower']
for sl, tp in [(2.0, 4.0), (2.5, 5.0), (3.0, 6.0)]:
    r = run_backtest(df, entry, f"BB_Limit_ATR_{sl}x{tp}", fee_pct=0.07, atr_sl_mult=sl, atr_tp_mult=tp)
    if r and r['total_trades'] >= 30:
        results.append(r)
        print(f"  Limit ATR {sl}x{tp}: {r['total_trades']} trades, WR={r['win_rate']:.1f}%, "
              f"PnL={r['total_pnl']:.2f}%, R:R={r['rr_ratio']:.2f}")

# Compile results
if len(results) == 0:
    print("\nNo strategies met minimum requirements (30+ trades)")
else:
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('rr_ratio', ascending=False)

    results_df.to_csv('results/pepe_quick_results.csv', index=False)
    print(f"\n{'=' * 80}")
    print(f"TOTAL STRATEGIES TESTED: {len(results_df)}")
    print(f"Results saved to: results/pepe_quick_results.csv")
    print(f"{'=' * 80}")

    print("\nTOP 10 STRATEGIES BY R:R RATIO:")
    print("=" * 80)

    for idx, row in results_df.head(10).iterrows():
        print(f"\n{row['strategy']}")
        print(f"  Trades: {row['total_trades']} | Win Rate: {row['win_rate']:.1f}%")
        print(f"  Total PnL: {row['total_pnl']:.2f}% | Max DD: {row['max_dd']:.2f}%")
        print(f"  R:R Ratio: {row['rr_ratio']:.2f}")
        print(f"  Avg Win: {row['avg_win']:.2f}% | Avg Loss: {row['avg_loss']:.2f}%")

    profitable = results_df[results_df['rr_ratio'] >= 2.0]

    if len(profitable) > 0:
        print(f"\n{'=' * 80}")
        print(f"STRATEGIES WITH R:R >= 2.0: {len(profitable)}")
        print(f"{'=' * 80}")

        for idx, row in profitable.iterrows():
            print(f"  {row['strategy']}: R:R={row['rr_ratio']:.2f}, PnL={row['total_pnl']:.2f}%")

        # Best strategy details
        best = profitable.iloc[0]
        print(f"\n{'=' * 80}")
        print("BEST STRATEGY FOR PEPE/USDT:")
        print(f"{'=' * 80}")
        print(f"Strategy: {best['strategy']}")
        print(f"Total Trades: {best['total_trades']}")
        print(f"Win Rate: {best['win_rate']:.1f}%")
        print(f"Total PnL: {best['total_pnl']:.2f}%")
        print(f"Max Drawdown: {best['max_dd']:.2f}%")
        print(f"R:R Ratio: {best['rr_ratio']:.2f}")
        print(f"Avg Win: {best['avg_win']:.2f}% | Avg Loss: {best['avg_loss']:.2f}%")
        print(f"Avg Duration: {best['avg_duration_mins']:.0f} minutes")
    else:
        print(f"\n{'=' * 80}")
        print("NO STRATEGIES ACHIEVED R:R >= 2.0")
        print(f"Best R:R: {results_df.iloc[0]['rr_ratio']:.2f} ({results_df.iloc[0]['strategy']})")
        print(f"{'=' * 80}")

print("\nBacktest complete!")
