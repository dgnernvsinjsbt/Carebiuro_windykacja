#!/usr/bin/env python3
"""
Analyze the Dec 6, 2025 MOODENG pump in detail
Check if the baseline strategy captured it properly
"""

import pandas as pd
import numpy as np

def main():
    # Load data
    df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/moodeng_30d_bingx.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Focus on Dec 6 pump period
    dec6 = df[(df['timestamp'] >= '2025-12-06 20:00:00') &
              (df['timestamp'] <= '2025-12-06 22:00:00')]

    print("="*80)
    print("MOODENG DEC 6 PUMP ANALYSIS")
    print("="*80)
    print(f"\nPump window: Dec 6, 20:00-22:00 UTC")
    print(f"Total candles: {len(dec6)}")

    if len(dec6) == 0:
        print("No data found in this window")
        return

    print(f"\nPrice action:")
    print(f"  Start: ${dec6.iloc[0]['close']:.5f}")
    print(f"  Peak:  ${dec6['high'].max():.5f}")
    print(f"  End:   ${dec6.iloc[-1]['close']:.5f}")
    print(f"  Gain:  {((dec6['high'].max() / dec6.iloc[0]['close']) - 1) * 100:.1f}%")

    # Show the 5 extreme candles
    print(f"\nExtreme candles (body >20%):")
    dec6['body_pct'] = abs(dec6['close'] - dec6['open']) / dec6['open'] * 100
    extreme = dec6[dec6['body_pct'] > 20].copy()

    if len(extreme) > 0:
        print(extreme[['timestamp', 'open', 'high', 'low', 'close', 'body_pct', 'volume']].to_string())

    # Calculate indicators for the whole dataset
    df['body'] = df['close'] - df['open']
    df['is_bullish'] = df['close'] > df['open']
    df['body_pct'] = abs(df['body']) / df['open'] * 100

    df['tr'] = np.maximum(
        df['high'] - df['low'],
        np.maximum(
            abs(df['high'] - df['close'].shift(1)),
            abs(df['low'] - df['close'].shift(1))
        )
    )
    df['atr'] = df['tr'].rolling(14).mean()

    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))

    df['sma_20'] = df['close'].rolling(20).mean()

    # Run baseline strategy and find trades during pump
    trades = []
    in_position = False
    entry_price = entry_idx = stop_loss = take_profit = 0

    for i in range(200, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i-1]

        if not in_position:
            rsi_cross = prev['rsi'] < 55 and row['rsi'] >= 55
            bullish_body = row['is_bullish'] and row['body_pct'] > 0.5
            above_sma = row['close'] > row['sma_20']

            if rsi_cross and bullish_body and above_sma:
                in_position = True
                entry_price = row['close']
                entry_idx = i
                entry_atr = row['atr']
                stop_loss = entry_price - (entry_atr * 1.0)
                take_profit = entry_price + (entry_atr * 4.0)
        else:
            bars_held = i - entry_idx

            if row['low'] <= stop_loss:
                pnl = (stop_loss - entry_price) / entry_price * 100
                trades.append({
                    'entry_time': df.iloc[entry_idx]['timestamp'],
                    'exit_time': row['timestamp'],
                    'entry_price': entry_price,
                    'exit_price': stop_loss,
                    'pnl_pct': pnl,
                    'result': 'SL',
                    'bars': bars_held
                })
                in_position = False
            elif row['high'] >= take_profit:
                pnl = (take_profit - entry_price) / entry_price * 100
                trades.append({
                    'entry_time': df.iloc[entry_idx]['timestamp'],
                    'exit_time': row['timestamp'],
                    'entry_price': entry_price,
                    'exit_price': take_profit,
                    'pnl_pct': pnl,
                    'result': 'TP',
                    'bars': bars_held
                })
                in_position = False
            elif bars_held >= 60:
                exit_price = row['close']
                pnl = (exit_price - entry_price) / entry_price * 100
                trades.append({
                    'entry_time': df.iloc[entry_idx]['timestamp'],
                    'exit_time': row['timestamp'],
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl_pct': pnl,
                    'result': 'TIME',
                    'bars': bars_held
                })
                in_position = False

    # Find trades during Dec 6 pump
    df_trades = pd.DataFrame(trades)
    if len(df_trades) > 0:
        df_trades['entry_time'] = pd.to_datetime(df_trades['entry_time'])
        df_trades['exit_time'] = pd.to_datetime(df_trades['exit_time'])

        pump_trades = df_trades[
            (df_trades['entry_time'] >= '2025-12-06 20:00:00') &
            (df_trades['entry_time'] <= '2025-12-06 23:00:00')
        ]

        print(f"\n\nTRADES DURING DEC 6 PUMP:")
        print(f"Total trades in 20:00-23:00 window: {len(pump_trades)}")

        if len(pump_trades) > 0:
            print(f"\nTrade details:")
            print(pump_trades[['entry_time', 'exit_time', 'entry_price', 'exit_price', 'pnl_pct', 'result', 'bars']].to_string())
            print(f"\nTotal PNL from pump trades: {pump_trades['pnl_pct'].sum():.2f}%")
        else:
            print("No trades captured during pump window")

        # Overall strategy stats
        print(f"\n\nOVERALL STRATEGY STATS:")
        print(f"Total trades: {len(df_trades)}")
        print(f"Total PNL: {df_trades['pnl_pct'].sum():.2f}%")
        print(f"Pump contribution: {(pump_trades['pnl_pct'].sum() / df_trades['pnl_pct'].sum() * 100) if len(pump_trades) > 0 else 0:.1f}%")

        # Best single trade
        best_trade = df_trades.nlargest(1, 'pnl_pct').iloc[0]
        print(f"\nBest single trade:")
        print(f"  Entry: {best_trade['entry_time']}")
        print(f"  Exit: {best_trade['exit_time']}")
        print(f"  PNL: {best_trade['pnl_pct']:.2f}%")
        print(f"  Result: {best_trade['result']}")
        print(f"  Contribution to total: {(best_trade['pnl_pct'] / df_trades['pnl_pct'].sum() * 100):.1f}%")

if __name__ == "__main__":
    main()
