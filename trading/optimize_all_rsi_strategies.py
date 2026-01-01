"""
Optimize All RSI Strategies - WITH CORRECTED RSI

Re-optimize all 9 coins with fixed Wilder's RSI calculation
"""

import pandas as pd
import numpy as np
from itertools import product
import sys
from pathlib import Path
from glob import glob

sys.path.insert(0, str(Path(__file__).parent / 'bingx-trading-bot'))
from data.indicators import rsi, atr


def backtest(df_1h, rsi_low, rsi_high, limit_offset_pct, stop_atr_mult, tp_atr_mult, max_wait_bars=5, fees=0.001):
    """Run backtest with given parameters"""
    capital = 100.0
    position = None
    pending_order = None
    trades = []
    equity_curve = [capital]

    for i in range(1, len(df_1h)):
        bar = df_1h.iloc[i]
        prev_bar = df_1h.iloc[i-1]

        if pd.isna(bar['rsi']) or pd.isna(bar['atr']):
            equity_curve.append(equity_curve[-1])
            continue

        # Check pending limit order
        if pending_order is not None:
            bars_waiting = i - pending_order['signal_bar']

            filled = False
            if pending_order['side'] == 'LONG':
                if bar['low'] <= pending_order['limit_price']:
                    filled = True
            else:
                if bar['high'] >= pending_order['limit_price']:
                    filled = True

            if filled:
                position = {
                    'side': pending_order['side'],
                    'entry_bar': i,
                    'entry_price': pending_order['limit_price'],
                    'stop_loss': pending_order['stop_loss'],
                    'take_profit': pending_order['take_profit'],
                    'size': capital * 0.10
                }
                pending_order = None
            elif bars_waiting >= max_wait_bars:
                pending_order = None

        # Check existing position
        if position is not None:
            exit_price = None
            exit_reason = None

            # Stop loss
            if position['side'] == 'LONG':
                if bar['low'] <= position['stop_loss']:
                    exit_price = position['stop_loss']
                    exit_reason = 'SL'
            else:
                if bar['high'] >= position['stop_loss']:
                    exit_price = position['stop_loss']
                    exit_reason = 'SL'

            # Take profit
            if exit_price is None:
                if position['side'] == 'LONG':
                    if bar['high'] >= position['take_profit']:
                        exit_price = position['take_profit']
                        exit_reason = 'TP'
                else:
                    if bar['low'] <= position['take_profit']:
                        exit_price = position['take_profit']
                        exit_reason = 'TP'

            # RSI exit
            if exit_price is None:
                if position['side'] == 'LONG':
                    if bar['rsi'] < rsi_high and prev_bar['rsi'] >= rsi_high:
                        exit_price = bar['close']
                        exit_reason = 'RSI'
                else:
                    if bar['rsi'] > rsi_low and prev_bar['rsi'] <= rsi_low:
                        exit_price = bar['close']
                        exit_reason = 'RSI'

            if exit_price is not None:
                if position['side'] == 'LONG':
                    pnl_pct = (exit_price - position['entry_price']) / position['entry_price']
                else:
                    pnl_pct = (position['entry_price'] - exit_price) / position['entry_price']

                pnl_pct -= (fees * 2)
                pnl = position['size'] * pnl_pct
                capital += pnl

                trades.append({'pnl': pnl, 'pnl_pct': pnl_pct * 100, 'exit_reason': exit_reason})
                position = None

        # Generate signals
        if position is None and pending_order is None:
            if bar['rsi'] > rsi_low and prev_bar['rsi'] <= rsi_low:
                signal_price = bar['close']
                limit_price = signal_price * (1 - limit_offset_pct / 100)
                stop_loss = limit_price - (stop_atr_mult * bar['atr'])
                take_profit = limit_price + (tp_atr_mult * bar['atr'])

                pending_order = {
                    'side': 'LONG',
                    'signal_bar': i,
                    'limit_price': limit_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit
                }

            elif bar['rsi'] < rsi_high and prev_bar['rsi'] >= rsi_high:
                signal_price = bar['close']
                limit_price = signal_price * (1 + limit_offset_pct / 100)
                stop_loss = limit_price + (stop_atr_mult * bar['atr'])
                take_profit = limit_price - (tp_atr_mult * bar['atr'])

                pending_order = {
                    'side': 'SHORT',
                    'signal_bar': i,
                    'limit_price': limit_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit
                }

        equity_curve.append(capital)

    # Calculate stats
    if len(trades) == 0:
        return None

    trades_df = pd.DataFrame(trades)
    total_return = ((capital - 100) / 100) * 100
    winning_trades = trades_df[trades_df['pnl'] > 0]
    win_rate = (len(winning_trades) / len(trades_df)) * 100

    # Drawdown
    equity_series = pd.Series(equity_curve)
    running_max = equity_series.expanding().max()
    drawdown = ((equity_series - running_max) / running_max) * 100
    max_drawdown = drawdown.min()

    return_dd_ratio = abs(total_return / max_drawdown) if max_drawdown != 0 else 0

    return {
        'rsi_low': rsi_low,
        'rsi_high': rsi_high,
        'limit_offset_pct': limit_offset_pct,
        'stop_atr_mult': stop_atr_mult,
        'tp_atr_mult': tp_atr_mult,
        'trades': len(trades_df),
        'return_pct': total_return,
        'max_dd_pct': max_drawdown,
        'return_dd_ratio': return_dd_ratio,
        'win_rate': win_rate
    }


def optimize_coin(symbol, data_file):
    """Optimize a single coin"""
    print("\n" + "=" * 100)
    print(f"OPTIMIZING {symbol}")
    print("=" * 100)

    # Load data
    if data_file.endswith('.csv'):
        df = pd.read_csv(data_file)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)

        # Check if already 1h or needs resampling
        if len(df) > 3000:  # Likely 1-minute data
            print(f"Resampling {len(df)} 1m candles to 1h...")
            df = df.set_index('timestamp').resample('1h').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }).dropna().reset_index()

        df_1h = df
    else:
        print(f"❌ File not found: {data_file}")
        return None

    print(f"Data: {len(df_1h)} candles ({df_1h['timestamp'].min()} to {df_1h['timestamp'].max()})")

    # Calculate indicators
    print("Calculating indicators with CORRECTED RSI...")
    df_1h['rsi'] = rsi(df_1h['close'], 14)
    df_1h['atr'] = atr(df_1h['high'], df_1h['low'], df_1h['close'], 14)

    # Parameter grid
    rsi_low_values = [25, 27, 30]
    rsi_high_values = [65, 70, 75]
    limit_offset_values = [0.5, 1.0, 1.5, 2.0]
    stop_atr_values = [1.0, 1.5, 2.0]
    tp_atr_values = [1.0, 1.5, 2.0, 3.0]

    print(f"Testing {len(rsi_low_values) * len(rsi_high_values) * len(limit_offset_values) * len(stop_atr_values) * len(tp_atr_values)} combinations...")

    results = []
    total_combos = len(rsi_low_values) * len(rsi_high_values) * len(limit_offset_values) * len(stop_atr_values) * len(tp_atr_values)
    count = 0

    for rsi_low, rsi_high, limit_offset, stop_atr, tp_atr in product(
        rsi_low_values, rsi_high_values, limit_offset_values, stop_atr_values, tp_atr_values
    ):
        count += 1
        if count % 100 == 0:
            print(f"  Progress: {count}/{total_combos}...")

        result = backtest(df_1h, rsi_low, rsi_high, limit_offset, stop_atr, tp_atr)
        if result is not None:
            results.append(result)

    if len(results) == 0:
        print(f"❌ No valid results for {symbol}")
        return None

    # Convert to DataFrame and filter
    results_df = pd.DataFrame(results)
    results_df = results_df[results_df['trades'] >= 10]  # Min 10 trades

    if len(results_df) == 0:
        print(f"❌ No configs with min 10 trades for {symbol}")
        return None

    # Sort by Return/DD ratio
    results_df = results_df.sort_values('return_dd_ratio', ascending=False)

    print(f"\nCompleted: {len(results_df)} valid configs")

    # Show top 10
    print("\n" + "=" * 100)
    print(f"TOP 10 CONFIGS FOR {symbol}")
    print("=" * 100)
    print(f"{'Rank':<5} {'RSI':<10} {'Limit%':<8} {'SL_ATR':<8} {'TP_ATR':<8} {'Trades':<7} "
          f"{'Return%':<10} {'MaxDD%':<10} {'R/DD':<8} {'Win%':<7}")
    print("-" * 100)

    for idx, row in results_df.head(10).iterrows():
        rank = results_df.index.get_loc(idx) + 1
        print(f"{rank:<5} "
              f"{row['rsi_low']:.0f}/{row['rsi_high']:.0f}{'':<5} "
              f"{row['limit_offset_pct']:<8.1f} "
              f"{row['stop_atr_mult']:<8.1f} "
              f"{row['tp_atr_mult']:<8.1f} "
              f"{row['trades']:<7.0f} "
              f"{row['return_pct']:<10.2f} "
              f"{row['max_dd_pct']:<10.2f} "
              f"{row['return_dd_ratio']:<8.2f} "
              f"{row['win_rate']:<7.1f}")

    # Save results
    symbol_clean = symbol.replace('-', '_').replace('1000', '').lower()
    output_file = f'{symbol_clean}_optimization_corrected.csv'
    results_df.to_csv(output_file, index=False)
    print(f"\n✅ Saved: {output_file}")

    return results_df.iloc[0]


# Coin data files mapping
COINS = {
    'MOODENG-USDT': 'bingx-trading-bot/trading/moodeng_usdt_90d_1h.csv',
    '1000PEPE-USDT': 'trading/moodeng_usdt_60d_bingx.csv',  # Will search for PEPE file
    'DOGE-USDT': 'trading/moodeng_usdt_60d_bingx.csv',
    'AIXBT-USDT': 'trading/moodeng_usdt_60d_bingx.csv',
    'TRUMPSOL-USDT': 'trading/trumpsol_60d_bingx.csv',
    'MELANIA-USDT': 'trading/melania_usdt_1m_lbank.csv',
    'CRV-USDT': 'trading/moodeng_usdt_60d_bingx.csv',
    'UNI-USDT': 'trading/moodeng_usdt_60d_bingx.csv',
    'XLM-USDT': 'trading/moodeng_usdt_60d_bingx.csv',
}

# Find actual data files
print("=" * 100)
print("SEARCHING FOR DATA FILES...")
print("=" * 100)

data_files = {}
for symbol in COINS.keys():
    symbol_search = symbol.replace('-USDT', '').replace('-', '_').lower()

    # Search for files
    patterns = [
        f'trading/*{symbol_search}*90d*.csv',
        f'trading/*{symbol_search}*60d*.csv',
        f'bingx-trading-bot/trading/*{symbol_search}*90d*.csv',
        f'bingx-trading-bot/trading/*{symbol_search}*60d*.csv',
    ]

    found = None
    for pattern in patterns:
        files = glob(pattern)
        if files:
            found = files[0]
            break

    if found:
        data_files[symbol] = found
        print(f"✅ {symbol:<20} -> {found}")
    else:
        print(f"❌ {symbol:<20} -> NOT FOUND")

print("\n" + "=" * 100)
print("STARTING OPTIMIZATION FOR ALL COINS")
print("=" * 100)

all_results = []

for symbol, data_file in data_files.items():
    best = optimize_coin(symbol, data_file)
    if best is not None:
        best['symbol'] = symbol
        all_results.append(best)

# Summary
print("\n\n" + "=" * 100)
print("OPTIMIZATION COMPLETE - SUMMARY")
print("=" * 100)
print(f"{'Symbol':<20} {'RSI':<10} {'Limit%':<8} {'SL':<6} {'TP':<6} {'Trades':<7} "
      f"{'Return%':<10} {'MaxDD%':<10} {'R/DD':<8} {'Win%':<7}")
print("-" * 100)

for result in sorted(all_results, key=lambda x: x['return_dd_ratio'], reverse=True):
    print(f"{result['symbol']:<20} "
          f"{result['rsi_low']:.0f}/{result['rsi_high']:.0f}{'':<5} "
          f"{result['limit_offset_pct']:<8.1f} "
          f"{result['stop_atr_mult']:<6.1f} "
          f"{result['tp_atr_mult']:<6.1f} "
          f"{result['trades']:<7.0f} "
          f"{result['return_pct']:<10.2f} "
          f"{result['max_dd_pct']:<10.2f} "
          f"{result['return_dd_ratio']:<8.2f} "
          f"{result['win_rate']:<7.1f}")

# Save summary
summary_df = pd.DataFrame(all_results)
summary_df.to_csv('all_coins_optimization_corrected.csv', index=False)
print(f"\n✅ Summary saved: all_coins_optimization_corrected.csv")
print("=" * 100)
