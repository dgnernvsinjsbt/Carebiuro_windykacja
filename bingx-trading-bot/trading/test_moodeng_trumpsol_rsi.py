#!/usr/bin/env python3
"""
Test RSI swing strategy on MOODENG and TRUMPSOL (1h data)
"""

import pandas as pd
import numpy as np
from pathlib import Path

def add_indicators(df):
    """Add RSI and ATR indicators"""
    # RSI
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(window=14).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))

    # ATR
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['atr'] = tr.rolling(window=14).mean()

    return df

def backtest_rsi(df, symbol, rsi_low=30, rsi_high=65, stop_atr_mult=2.0,
                 limit_offset_pct=0.0, max_wait_bars=5, fees_pct=0.1):
    """
    Backtest RSI swing strategy

    limit_offset_pct: 0 = market orders, >0 = limit orders with offset
    """

    df = df.copy()
    df = add_indicators(df)
    df = df.dropna().reset_index(drop=True)

    capital = 100.0
    position = None
    trades = []
    equity_curve = [capital]

    # Pending limit orders
    pending_long = None
    pending_short = None

    for i in range(1, len(df)):
        prev_rsi = df.loc[i-1, 'rsi']
        curr_rsi = df.loc[i, 'rsi']
        curr_price = df.loc[i, 'close']
        curr_atr = df.loc[i, 'atr']
        curr_time = df.loc[i, 'timestamp']

        # Check pending limit orders
        if pending_long:
            # Check if limit filled
            if df.loc[i, 'low'] <= pending_long['limit_price']:
                # Filled!
                entry_price = pending_long['limit_price']
                stop_loss = entry_price - (stop_atr_mult * pending_long['atr'])

                position = {
                    'side': 'LONG',
                    'entry_bar': i,
                    'entry_price': entry_price,
                    'entry_time': curr_time,
                    'stop_loss': stop_loss,
                    'quantity': capital / entry_price,
                    'atr': pending_long['atr']
                }

                # Pay maker fee
                capital *= (1 - fees_pct / 100 / 2)  # Maker fee

                pending_long = None
            elif i - pending_long['signal_bar'] >= max_wait_bars:
                # Expired
                pending_long = None

        if pending_short:
            # Check if limit filled
            if df.loc[i, 'high'] >= pending_short['limit_price']:
                # Filled!
                entry_price = pending_short['limit_price']
                stop_loss = entry_price + (stop_atr_mult * pending_short['atr'])

                position = {
                    'side': 'SHORT',
                    'entry_bar': i,
                    'entry_price': entry_price,
                    'entry_time': curr_time,
                    'stop_loss': stop_loss,
                    'quantity': capital / entry_price,
                    'atr': pending_short['atr']
                }

                # Pay maker fee
                capital *= (1 - fees_pct / 100 / 2)  # Maker fee

                pending_short = None
            elif i - pending_short['signal_bar'] >= max_wait_bars:
                # Expired
                pending_short = None

        # Exit logic
        if position:
            exit_signal = False
            exit_price = curr_price
            exit_reason = None

            if position['side'] == 'LONG':
                # Stop loss
                if df.loc[i, 'low'] <= position['stop_loss']:
                    exit_signal = True
                    exit_price = position['stop_loss']
                    exit_reason = 'STOP_LOSS'
                # RSI exit
                elif curr_rsi < rsi_high and prev_rsi >= rsi_high:
                    exit_signal = True
                    exit_reason = 'RSI_EXIT'

            else:  # SHORT
                # Stop loss
                if df.loc[i, 'high'] >= position['stop_loss']:
                    exit_signal = True
                    exit_price = position['stop_loss']
                    exit_reason = 'STOP_LOSS'
                # RSI exit
                elif curr_rsi > rsi_low and prev_rsi <= rsi_low:
                    exit_signal = True
                    exit_reason = 'RSI_EXIT'

            if exit_signal:
                # Close position
                if position['side'] == 'LONG':
                    pnl_pct = ((exit_price - position['entry_price']) / position['entry_price']) * 100
                else:
                    pnl_pct = ((position['entry_price'] - exit_price) / position['entry_price']) * 100

                # Apply fees
                capital *= (1 + pnl_pct / 100)
                capital *= (1 - fees_pct / 100 / 2)  # Exit fee

                trades.append({
                    'entry_time': position['entry_time'],
                    'exit_time': curr_time,
                    'side': position['side'],
                    'entry_price': position['entry_price'],
                    'exit_price': exit_price,
                    'pnl_pct': pnl_pct,
                    'exit_reason': exit_reason,
                    'bars_held': i - position['entry_bar']
                })

                position = None

        # Entry logic (if no position and no pending orders)
        if not position and not pending_long and not pending_short:
            # LONG signal
            if curr_rsi > rsi_low and prev_rsi <= rsi_low:
                if limit_offset_pct > 0:
                    # Place limit order
                    limit_price = curr_price * (1 - limit_offset_pct / 100)
                    pending_long = {
                        'signal_bar': i,
                        'limit_price': limit_price,
                        'atr': curr_atr
                    }
                else:
                    # Market order
                    entry_price = curr_price
                    stop_loss = entry_price - (stop_atr_mult * curr_atr)

                    position = {
                        'side': 'LONG',
                        'entry_bar': i,
                        'entry_price': entry_price,
                        'entry_time': curr_time,
                        'stop_loss': stop_loss,
                        'quantity': capital / entry_price,
                        'atr': curr_atr
                    }

                    # Pay taker fee
                    capital *= (1 - fees_pct / 100)

            # SHORT signal
            elif curr_rsi < rsi_high and prev_rsi >= rsi_high:
                if limit_offset_pct > 0:
                    # Place limit order
                    limit_price = curr_price * (1 + limit_offset_pct / 100)
                    pending_short = {
                        'signal_bar': i,
                        'limit_price': limit_price,
                        'atr': curr_atr
                    }
                else:
                    # Market order
                    entry_price = curr_price
                    stop_loss = entry_price + (stop_atr_mult * curr_atr)

                    position = {
                        'side': 'SHORT',
                        'entry_bar': i,
                        'entry_price': entry_price,
                        'entry_time': curr_time,
                        'stop_loss': stop_loss,
                        'quantity': capital / entry_price,
                        'atr': curr_atr
                    }

                    # Pay taker fee
                    capital *= (1 - fees_pct / 100)

        equity_curve.append(capital)

    # Calculate metrics
    if not trades:
        return None

    trades_df = pd.DataFrame(trades)

    total_return = ((capital - 100) / 100) * 100
    wins = trades_df[trades_df['pnl_pct'] > 0]
    losses = trades_df[trades_df['pnl_pct'] <= 0]

    win_rate = len(wins) / len(trades_df) * 100 if len(trades_df) > 0 else 0

    # Max drawdown
    equity_series = pd.Series(equity_curve)
    running_max = equity_series.expanding().max()
    drawdown = ((equity_series - running_max) / running_max) * 100
    max_dd = drawdown.min()

    # Return/DD ratio
    if max_dd < 0:
        return_dd = total_return / abs(max_dd)
    else:
        return_dd = 0

    return {
        'symbol': symbol,
        'rsi_low': rsi_low,
        'rsi_high': rsi_high,
        'limit_offset_pct': limit_offset_pct,
        'total_return': total_return,
        'max_dd': max_dd,
        'return_dd': return_dd,
        'trades': len(trades_df),
        'win_rate': win_rate,
        'avg_pnl': trades_df['pnl_pct'].mean(),
        'avg_winner': wins['pnl_pct'].mean() if len(wins) > 0 else 0,
        'avg_loser': losses['pnl_pct'].mean() if len(losses) > 0 else 0,
    }

def main():
    symbols = [
        ('MOODENG', 'trading/moodeng_usdt_90d_1h.csv'),
        ('TRUMPSOL', 'trading/trumpsol_usdt_90d_1h.csv')
    ]

    print("="*80)
    print("RSI SWING STRATEGY TEST (1H CANDLES)")
    print("="*80)
    print("\nTesting RSI 30/65 baseline + limit order variants\n")

    all_results = []

    for symbol, filepath in symbols:
        print(f"\n{'='*80}")
        print(f"{symbol}")
        print(f"{'='*80}")

        df = pd.read_csv(filepath)
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        print(f"Data: {len(df)} candles ({df['timestamp'].min()} to {df['timestamp'].max()})")

        # Test configurations
        configs = [
            {'rsi_low': 30, 'rsi_high': 65, 'limit_offset_pct': 0.0, 'label': 'Market Orders'},
            {'rsi_low': 30, 'rsi_high': 65, 'limit_offset_pct': 0.5, 'label': 'Limit 0.5%'},
            {'rsi_low': 30, 'rsi_high': 65, 'limit_offset_pct': 1.0, 'label': 'Limit 1.0%'},
            {'rsi_low': 27, 'rsi_high': 65, 'limit_offset_pct': 0.5, 'label': 'RSI 27/65 + Limit 0.5%'},
        ]

        print(f"\n{'Config':<30} {'Return':<12} {'MaxDD':<12} {'R/DD':<10} {'Trades':<8} {'WinRate'}")
        print("-"*80)

        for config in configs:
            result = backtest_rsi(
                df,
                symbol,
                rsi_low=config['rsi_low'],
                rsi_high=config['rsi_high'],
                limit_offset_pct=config['limit_offset_pct']
            )

            if result:
                all_results.append(result)
                print(f"{config['label']:<30} {result['total_return']:>10.2f}%  {result['max_dd']:>10.2f}%  {result['return_dd']:>8.2f}x  {result['trades']:>6}   {result['win_rate']:>5.1f}%")

    # Summary
    print(f"\n\n{'='*80}")
    print("BEST CONFIGS BY RETURN/DD RATIO")
    print(f"{'='*80}")

    best_results = sorted(all_results, key=lambda x: x['return_dd'], reverse=True)[:10]

    print(f"\n{'Symbol':<12} {'RSI':<12} {'Limit':<10} {'R/DD':<10} {'Return':<12} {'MaxDD':<12} {'Trades'}")
    print("-"*80)

    for r in best_results:
        rsi_str = f"{int(r['rsi_low'])}/{int(r['rsi_high'])}"
        limit_str = f"{r['limit_offset_pct']:.1f}%"

        print(f"{r['symbol']:<12} {rsi_str:<12} {limit_str:<10} {r['return_dd']:>8.2f}x  {r['total_return']:>10.2f}%  {r['max_dd']:>10.2f}%  {r['trades']:>6}")

if __name__ == "__main__":
    main()
