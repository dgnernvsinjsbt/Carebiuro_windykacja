"""
Backtest all 10 RSI strategies and save trades to CSV

Runs backtests on all 10 coins with their optimized parameters
and saves individual trade files for later combined analysis.
"""

import pandas as pd
import numpy as np
from pathlib import Path


def calculate_indicators(df):
    """Calculate RSI and ATR indicators"""
    # RSI calculation
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))

    # ATR calculation
    df['h-l'] = df['high'] - df['low']
    df['h-pc'] = abs(df['high'] - df['close'].shift(1))
    df['l-pc'] = abs(df['low'] - df['close'].shift(1))
    df['tr'] = df[['h-l', 'h-pc', 'l-pc']].max(axis=1)
    df['atr'] = df['tr'].rolling(window=14).mean()
    df = df.drop(['h-l', 'h-pc', 'l-pc', 'tr'], axis=1)

    return df


def backtest_rsi_strategy(df, rsi_low, rsi_high, limit_offset_pct, max_hold_bars=3, stop_atr_mult=2.0):
    """Backtest RSI mean reversion strategy with limit orders"""

    trades = []
    in_position = False
    entry_bar = None
    entry_price = None
    signal_price = None
    side = None

    for i in range(1, len(df)):
        current = df.iloc[i]
        prev = df.iloc[i-1]

        if pd.isna(current['rsi']) or pd.isna(current['atr']):
            continue

        # Exit logic
        if in_position:
            bars_held = i - entry_bar
            exit_reason = None
            exit_price = None

            # RSI exit
            if side == 'LONG' and current['rsi'] < rsi_high and prev['rsi'] >= rsi_high:
                exit_reason = 'RSI exit'
                exit_price = current['close']
            elif side == 'SHORT' and current['rsi'] > rsi_low and prev['rsi'] <= rsi_low:
                exit_reason = 'RSI exit'
                exit_price = current['close']

            # Time exit
            elif bars_held >= max_hold_bars:
                exit_reason = 'Time exit'
                exit_price = current['close']

            if exit_reason:
                pnl_pct = ((exit_price / entry_price) - 1) * 100 if side == 'LONG' else ((entry_price / exit_price) - 1) * 100

                trades.append({
                    'entry_time': df.iloc[entry_bar]['timestamp'],
                    'exit_time': current['timestamp'],
                    'side': side,
                    'signal_price': signal_price,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'exit_reason': exit_reason,
                    'bars_held': bars_held,
                    'pnl_pct': pnl_pct,
                    'entry_rsi': df.iloc[entry_bar]['rsi'],
                    'exit_rsi': current['rsi']
                })

                in_position = False

        # Entry logic
        if not in_position:
            # LONG signal
            if current['rsi'] > rsi_low and prev['rsi'] <= rsi_low:
                signal_price = current['close']
                limit_price = signal_price * (1 - limit_offset_pct / 100)

                # Check if limit would fill in next bars
                filled = False
                for j in range(i+1, min(i+6, len(df))):  # Check next 5 bars
                    if df.iloc[j]['low'] <= limit_price:
                        filled = True
                        entry_bar = j
                        entry_price = limit_price
                        side = 'LONG'
                        in_position = True
                        break

            # SHORT signal
            elif current['rsi'] < rsi_high and prev['rsi'] >= rsi_high:
                signal_price = current['close']
                limit_price = signal_price * (1 + limit_offset_pct / 100)

                # Check if limit would fill in next bars
                filled = False
                for j in range(i+1, min(i+6, len(df))):  # Check next 5 bars
                    if df.iloc[j]['high'] >= limit_price:
                        filled = True
                        entry_bar = j
                        entry_price = limit_price
                        side = 'SHORT'
                        in_position = True
                        break

    return pd.DataFrame(trades)


def backtest_fartcoin_atr(df):
    """Backtest FARTCOIN ATR expansion strategy"""

    # Calculate EMA(20)
    df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()

    # Calculate ATR average
    df['atr_avg'] = df['atr'].rolling(window=20).mean()

    trades = []
    in_position = False
    entry_bar = None
    entry_price = None
    signal_price = None
    side = None
    target_price = None
    stop_price = None

    for i in range(1, len(df)):
        current = df.iloc[i]

        if pd.isna(current['atr']) or pd.isna(current['atr_avg']) or pd.isna(current['ema20']):
            continue

        # Exit logic
        if in_position:
            bars_held = i - entry_bar
            exit_reason = None
            exit_price = None

            # Take profit hit
            if side == 'LONG' and current['high'] >= target_price:
                exit_reason = 'Take profit'
                exit_price = target_price
            elif side == 'SHORT' and current['low'] <= target_price:
                exit_reason = 'Take profit'
                exit_price = target_price

            # Stop loss hit
            elif side == 'LONG' and current['low'] <= stop_price:
                exit_reason = 'Stop loss'
                exit_price = stop_price
            elif side == 'SHORT' and current['high'] >= stop_price:
                exit_reason = 'Stop loss'
                exit_price = stop_price

            # Time exit
            elif bars_held >= 4:
                exit_reason = 'Time exit'
                exit_price = current['close']

            if exit_reason:
                pnl_pct = ((exit_price / entry_price) - 1) * 100 if side == 'LONG' else ((entry_price / exit_price) - 1) * 100

                trades.append({
                    'entry_time': df.iloc[entry_bar]['timestamp'],
                    'exit_time': current['timestamp'],
                    'side': side,
                    'signal_price': signal_price,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'exit_reason': exit_reason,
                    'bars_held': bars_held,
                    'pnl_pct': pnl_pct,
                    'entry_atr': df.iloc[entry_bar]['atr'],
                    'exit_atr': current['atr']
                })

                in_position = False

        # Entry logic
        if not in_position:
            # ATR expansion check
            if current['atr'] > 1.5 * current['atr_avg']:
                # Check EMA distance
                ema_dist_pct = abs((current['close'] / current['ema20']) - 1) * 100

                if ema_dist_pct <= 3.0:
                    # LONG signal (bullish candle)
                    if current['close'] > current['open']:
                        signal_price = current['close']
                        limit_price = signal_price * 1.01  # 1% above

                        # Check if limit fills in next 3 bars
                        for j in range(i+1, min(i+4, len(df))):
                            if df.iloc[j]['high'] >= limit_price:
                                entry_bar = j
                                entry_price = limit_price
                                side = 'LONG'
                                target_price = entry_price + (8.0 * df.iloc[entry_bar]['atr'])
                                stop_price = entry_price - (2.0 * df.iloc[entry_bar]['atr'])
                                in_position = True
                                break

                    # SHORT signal (bearish candle)
                    elif current['close'] < current['open']:
                        signal_price = current['close']
                        limit_price = signal_price * 0.99  # 1% below

                        # Check if limit fills in next 3 bars
                        for j in range(i+1, min(i+4, len(df))):
                            if df.iloc[j]['low'] <= limit_price:
                                entry_bar = j
                                entry_price = limit_price
                                side = 'SHORT'
                                target_price = entry_price - (8.0 * df.iloc[entry_bar]['atr'])
                                stop_price = entry_price + (2.0 * df.iloc[entry_bar]['atr'])
                                in_position = True
                                break

    return pd.DataFrame(trades)


# Strategy configurations (ALL 10 COINS)
STRATEGIES = {
    'CRV-USDT': {'file': 'crv_usdt_90d_1h.csv', 'rsi_low': 27, 'rsi_high': 65, 'limit_offset': 1.0, 'type': 'rsi'},
    'MELANIA-USDT': {'file': 'melania_usdt_90d_1h.csv', 'rsi_low': 27, 'rsi_high': 65, 'limit_offset': 1.0, 'type': 'rsi'},
    'AIXBT-USDT': {'file': 'aixbt_usdt_90d_1h.csv', 'rsi_low': 27, 'rsi_high': 65, 'limit_offset': 1.0, 'type': 'rsi'},
    'TRUMPSOL-USDT': {'file': 'trumpsol_usdt_90d_1h.csv', 'rsi_low': 30, 'rsi_high': 65, 'limit_offset': 1.0, 'type': 'rsi'},
    'UNI-USDT': {'file': 'uni_usdt_90d_1h.csv', 'rsi_low': 30, 'rsi_high': 65, 'limit_offset': 1.0, 'type': 'rsi'},
    'XLM-USDT': {'file': 'xlm_usdt_90d_1h.csv', 'rsi_low': 30, 'rsi_high': 65, 'limit_offset': 0.5, 'type': 'rsi'},
    'MOODENG-USDT': {'file': 'moodeng_usdt_90d_1h.csv', 'rsi_low': 30, 'rsi_high': 65, 'limit_offset': 1.0, 'type': 'rsi'},
    'DOGE-USDT': {'file': 'doge_usdt_90d_1h.csv', 'rsi_low': 27, 'rsi_high': 65, 'limit_offset': 0.1, 'type': 'rsi'},
    'FARTCOIN-USDT': {'file': 'fartcoin_usdt_90d_1h.csv', 'type': 'atr'},
    '1000PEPE-USDT': {'file': '1000pepe_usdt_90d_1h.csv', 'rsi_low': 30, 'rsi_high': 65, 'limit_offset': 0.6, 'type': 'rsi'},
}


def main():
    """Run backtests for all 10 strategies"""

    print("\n" + "="*70)
    print("BACKTESTING ALL 10 STRATEGIES")
    print("="*70)

    output_dir = Path("trading/results")
    output_dir.mkdir(parents=True, exist_ok=True)

    all_trades = []

    for symbol, config in STRATEGIES.items():
        print(f"\n{'='*70}")
        print(f"Backtesting {symbol}")
        print(f"{'='*70}")

        # Load data
        data_file = Path("trading") / config['file']

        if not data_file.exists():
            print(f"❌ Data file not found: {data_file}")
            continue

        df = pd.read_csv(data_file)

        # Ensure timestamp column is datetime
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        else:
            df['timestamp'] = pd.to_datetime(df.index if 'time' not in df.columns else df['time'])

        # Calculate indicators
        df = calculate_indicators(df)

        # Run backtest
        if config['type'] == 'rsi':
            trades = backtest_rsi_strategy(
                df,
                rsi_low=config['rsi_low'],
                rsi_high=config['rsi_high'],
                limit_offset_pct=config['limit_offset']
            )
        else:  # FARTCOIN ATR
            trades = backtest_fartcoin_atr(df)

        if len(trades) > 0:
            trades['symbol'] = symbol

            # Save individual strategy trades
            output_file = output_dir / f"{symbol.replace('-', '_').lower()}_trades.csv"
            trades.to_csv(output_file, index=False)
            print(f"✅ Saved {len(trades)} trades to {output_file}")

            # Add to combined list
            all_trades.append(trades)

            # Print summary
            print(f"  Trades: {len(trades)}")
            print(f"  Win rate: {(trades['pnl_pct'] > 0).mean() * 100:.1f}%")
            print(f"  Avg PnL: {trades['pnl_pct'].mean():.2f}%")
        else:
            print(f"⚠️ No trades generated")

    # Combine all trades
    if all_trades:
        combined = pd.concat(all_trades, ignore_index=True)
        combined = combined.sort_values('entry_time').reset_index(drop=True)

        combined_file = output_dir / "all_10_strategies_trades.csv"
        combined.to_csv(combined_file, index=False)

        print("\n" + "="*70)
        print(f"✅ COMBINED: {len(combined)} trades saved to {combined_file}")
        print("="*70)
    else:
        print("\n❌ No trades generated for any strategy")


if __name__ == '__main__':
    main()
