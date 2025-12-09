#!/usr/bin/env python3
"""
Analyze the best trade in detail: Dec 7 00:17-00:39 (+10.60%)
This single trade contributes 56.5% of total strategy profit
"""

import pandas as pd
import numpy as np

def main():
    # Load data
    df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/moodeng_30d_bingx.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Focus on best trade window
    best_trade_window = df[(df['timestamp'] >= '2025-12-07 00:00:00') &
                           (df['timestamp'] <= '2025-12-07 01:00:00')]

    print("="*80)
    print("BEST TRADE ANALYSIS: Dec 7, 00:17-00:39 (+10.60%)")
    print("="*80)

    if len(best_trade_window) == 0:
        print("No data found")
        return

    # Calculate indicators
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

    # Find the entry candle
    entry_candle = df[df['timestamp'] == '2025-12-07 00:17:00']
    if len(entry_candle) == 0:
        print("Entry candle not found")
        return

    entry_idx = entry_candle.index[0]
    entry_row = df.iloc[entry_idx]
    prev_row = df.iloc[entry_idx - 1]

    print(f"\nENTRY CONDITIONS (00:17:00):")
    print(f"  Price: ${entry_row['close']:.5f}")
    print(f"  RSI: {entry_row['rsi']:.2f} (prev: {prev_row['rsi']:.2f})")
    print(f"  RSI Cross: {prev_row['rsi'] < 55 and entry_row['rsi'] >= 55}")
    print(f"  Body: {entry_row['body_pct']:.2f}%")
    print(f"  Is Bullish: {entry_row['is_bullish']}")
    print(f"  Above SMA20: {entry_row['close'] > entry_row['sma_20']}")
    print(f"  ATR: ${entry_row['atr']:.5f} ({entry_row['atr']/entry_row['close']*100:.2f}%)")

    # Calculate entry signals
    entry_price = entry_row['close']
    entry_atr = entry_row['atr']
    stop_loss = entry_price - (entry_atr * 1.0)
    take_profit = entry_price + (entry_atr * 4.0)

    print(f"\nPOSITION PARAMETERS:")
    print(f"  Entry: ${entry_price:.5f}")
    print(f"  Stop Loss: ${stop_loss:.5f} (-{((entry_price-stop_loss)/entry_price*100):.2f}%)")
    print(f"  Take Profit: ${take_profit:.5f} (+{((take_profit-entry_price)/entry_price*100):.2f}%)")

    # Find exit
    exit_candle = df[df['timestamp'] == '2025-12-07 00:39:00']
    if len(exit_candle) > 0:
        exit_idx = exit_candle.index[0]
        exit_row = df.iloc[exit_idx]

        print(f"\nEXIT (00:39:00 - {exit_idx - entry_idx} bars later):")
        print(f"  Exit Price: ${exit_row['close']:.5f}")
        print(f"  High reached: ${exit_row['high']:.5f}")
        print(f"  TP Hit: {exit_row['high'] >= take_profit}")

        if exit_row['high'] >= take_profit:
            actual_pnl = (take_profit - entry_price) / entry_price * 100
            print(f"  Actual PNL: +{actual_pnl:.2f}% (TP HIT)")

    # Show price action during the trade
    print(f"\nPRICE ACTION DURING TRADE:")
    trade_candles = df[(df['timestamp'] >= '2025-12-07 00:17:00') &
                       (df['timestamp'] <= '2025-12-07 00:39:00')]

    print(trade_candles[['timestamp', 'open', 'high', 'low', 'close', 'body_pct', 'rsi']].to_string())

    # Context: what happened before
    print(f"\n\nCONTEXT (30 min before entry):")
    context = df[(df['timestamp'] >= '2025-12-06 23:47:00') &
                 (df['timestamp'] <= '2025-12-07 00:17:00')]

    print(f"Price range: ${context['low'].min():.5f} - ${context['high'].max():.5f}")
    print(f"Volatility (std): {context['close'].pct_change().std() * 100:.2f}%")
    print(f"Volume avg: {context['volume'].mean():.0f}")

    # Show last 10 candles before entry
    print(f"\nLast 10 candles before entry:")
    pre_entry = df.iloc[entry_idx-10:entry_idx][['timestamp', 'close', 'body_pct', 'rsi']]
    print(pre_entry.to_string())

    # Overall context: This trade's contribution
    print(f"\n\n{'='*80}")
    print("TRADE SIGNIFICANCE:")
    print(f"{'='*80}")
    print(f"This +10.60% trade represents 56.5% of the strategy's total 18.78% profit")
    print(f"Without this trade, strategy would return: {18.78 - 10.60:.2f}%")
    print(f"This is a classic 'outlier dependency' - strategy needs this trade to be profitable")

if __name__ == "__main__":
    main()
