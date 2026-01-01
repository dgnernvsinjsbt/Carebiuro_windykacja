"""
Fast vectorized backtest - processes entire dataset quickly
"""

import pandas as pd
import numpy as np
from pathlib import Path


def calculate_indicators(df):
    """Calculate all required indicators (vectorized)"""

    # ATR
    df['tr'] = np.maximum(
        df['high'] - df['low'],
        np.maximum(
            abs(df['high'] - df['close'].shift(1)),
            abs(df['low'] - df['close'].shift(1))
        )
    )
    df['atr'] = df['tr'].rolling(14).mean()

    # RSI
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = -delta.where(delta < 0, 0).rolling(14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))

    # SMAs
    df['sma_50'] = df['close'].rolling(50).mean()
    df['sma_200'] = df['close'].rolling(200).mean()

    # Trend
    df['uptrend'] = df['close'] > df['sma_50']
    df['downtrend'] = df['close'] < df['sma_50']

    # Candle patterns
    df['body'] = abs(df['close'] - df['open'])
    df['range'] = df['high'] - df['low']
    df['body_pct'] = (df['body'] / df['range'] * 100).fillna(0)

    df['is_bullish'] = df['close'] > df['open']
    df['is_bearish'] = df['close'] < df['open']

    df['lower_wick'] = np.where(
        df['is_bullish'],
        df['open'] - df['low'],
        df['close'] - df['low']
    )
    df['upper_wick'] = np.where(
        df['is_bullish'],
        df['high'] - df['close'],
        df['high'] - df['open']
    )

    # Volume
    df['vol_ratio'] = df['volume'] / df['volume'].rolling(20).mean()
    df['high_vol'] = df['vol_ratio'] > 2.0

    return df


def find_long_signals(df, df_5min, config):
    """Find all LONG entry signals with 5-min filter (vectorized)"""

    # Round timestamps to 5-min for merge
    df = df.copy()
    df['ts_5min'] = df['timestamp'].dt.floor('5T')
    df_5min_subset = df_5min[['timestamp', 'close', 'sma_50', 'rsi']].copy()
    df_5min_subset.columns = ['ts_5min', 'close_5m', 'sma_50_5m', 'rsi_5m']

    df_merged = df.merge(df_5min_subset, on='ts_5min', how='left')

    # 1-min explosive bullish pattern
    explosive_bullish = (
        df_merged['is_bullish'] &
        df_merged['uptrend'] &
        (df_merged['body_pct'] > config['body_threshold']) &
        (df_merged['vol_ratio'] > config['volume_multiplier']) &
        (df_merged['lower_wick'] < df_merged['body'] * config['wick_threshold']) &
        (df_merged['upper_wick'] < df_merged['body'] * config['wick_threshold']) &
        (df_merged['rsi'] > config['rsi_long_min']) &
        (df_merged['rsi'] < 75) &
        df_merged['high_vol']
    )

    # 5-min uptrend filter
    close_above_sma = df_merged['close_5m'] > df_merged['sma_50_5m']
    rsi_bullish = df_merged['rsi_5m'] > config['rsi_5min_min']
    distance = ((df_merged['close_5m'] - df_merged['sma_50_5m']) / df_merged['sma_50_5m']) * 100
    strong_distance = distance > config['distance_from_sma']

    filter_5min = close_above_sma & rsi_bullish & strong_distance

    return df_merged[explosive_bullish & filter_5min].copy()


def find_short_signals(df, config):
    """Find all SHORT entry signals (vectorized)"""

    # Trend distance short conditions
    below_50sma = df['close'] < df['sma_50']
    below_200sma = df['close'] < df['sma_200']

    distance = ((df['sma_50'] - df['close']) / df['sma_50']) * 100
    strong_distance = distance > config['distance_from_50sma']

    downtrend_filter = below_50sma & below_200sma & strong_distance

    explosive_bearish = (
        df['is_bearish'] &
        df['downtrend'] &
        (df['body_pct'] > config['body_threshold']) &
        (df['vol_ratio'] > config['volume_multiplier']) &
        (df['lower_wick'] < df['body'] * config['wick_threshold']) &
        (df['upper_wick'] < df['body'] * config['wick_threshold']) &
        (df['rsi'] > config['rsi_short_min']) &
        (df['rsi'] < config['rsi_short_max']) &
        df['high_vol']
    )

    return df[downtrend_filter & explosive_bearish].copy()


def simulate_trades(df, signals, direction, stop_mult, target_mult):
    """Simulate trade execution - ONE POSITION AT A TIME"""

    trades = []
    in_position = False
    last_exit_idx = 0

    for idx, signal_row in signals.iterrows():
        # Skip if already in position or too soon after last exit
        if in_position or idx <= last_exit_idx:
            continue

        entry_price = signal_row['close']
        atr = signal_row['atr']

        if direction == 'LONG':
            stop_loss = entry_price - (stop_mult * atr)
            take_profit = entry_price + (target_mult * atr)

            # Find exit in future candles
            future = df.loc[idx+1:]  # Start from next candle

            # Check SL hit
            sl_hit = future[future['low'] <= stop_loss]
            tp_hit = future[future['high'] >= take_profit]

            if len(sl_hit) > 0 and len(tp_hit) > 0:
                # Both possible - which came first?
                if sl_hit.index[0] < tp_hit.index[0]:
                    exit_price = stop_loss
                    exit_type = 'SL'
                    exit_idx = sl_hit.index[0]
                else:
                    exit_price = take_profit
                    exit_type = 'TP'
                    exit_idx = tp_hit.index[0]
            elif len(sl_hit) > 0:
                exit_price = stop_loss
                exit_type = 'SL'
                exit_idx = sl_hit.index[0]
            elif len(tp_hit) > 0:
                exit_price = take_profit
                exit_type = 'TP'
                exit_idx = tp_hit.index[0]
            else:
                continue  # No exit found

            pnl_pct = ((exit_price - entry_price) / entry_price) * 100
            last_exit_idx = exit_idx

        else:  # SHORT
            stop_loss = entry_price + (stop_mult * atr)
            take_profit = entry_price - (target_mult * atr)

            future = df.loc[idx+1:]

            sl_hit = future[future['high'] >= stop_loss]
            tp_hit = future[future['low'] <= take_profit]

            if len(sl_hit) > 0 and len(tp_hit) > 0:
                if sl_hit.index[0] < tp_hit.index[0]:
                    exit_price = stop_loss
                    exit_type = 'SL'
                    exit_idx = sl_hit.index[0]
                else:
                    exit_price = take_profit
                    exit_type = 'TP'
                    exit_idx = tp_hit.index[0]
            elif len(sl_hit) > 0:
                exit_price = stop_loss
                exit_type = 'SL'
                exit_idx = sl_hit.index[0]
            elif len(tp_hit) > 0:
                exit_price = take_profit
                exit_type = 'TP'
                exit_idx = tp_hit.index[0]
            else:
                continue

            pnl_pct = ((entry_price - exit_price) / entry_price) * 100
            last_exit_idx = exit_idx

        trades.append({
            'entry_price': entry_price,
            'exit_price': exit_price,
            'exit_type': exit_type,
            'pnl_pct': pnl_pct
        })

    return pd.DataFrame(trades)


def analyze_results(trades_df, strategy_name):
    """Analyze backtest results"""

    if len(trades_df) == 0:
        print(f"\n❌ {strategy_name}: No trades!")
        return None

    total_trades = len(trades_df)
    wins = trades_df[trades_df['pnl_pct'] > 0]
    losses = trades_df[trades_df['pnl_pct'] <= 0]

    num_wins = len(wins)
    num_losses = len(losses)
    win_rate = (num_wins / total_trades) * 100

    avg_win = wins['pnl_pct'].mean() if num_wins > 0 else 0
    avg_loss = losses['pnl_pct'].mean() if num_losses > 0 else 0

    total_return = trades_df['pnl_pct'].sum()

    # Drawdown
    cumulative = (1 + trades_df['pnl_pct'] / 100).cumprod()
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max * 100
    max_dd = drawdown.min()

    print(f"\n{'='*80}")
    print(f"{strategy_name}")
    print(f"{'='*80}")
    print(f"Total trades: {total_trades}")
    print(f"Wins: {num_wins} | Losses: {num_losses}")
    print(f"Win rate: {win_rate:.1f}%")
    print(f"Avg win: {avg_win:.2f}% | Avg loss: {avg_loss:.2f}%")
    print(f"Total return (1x): {total_return:.2f}%")
    print(f"Max DD (1x): {max_dd:.2f}%")

    if num_wins > 0 and num_losses > 0:
        rr = abs(avg_win / avg_loss)
        print(f"R:R ratio: 1:{rr:.2f}")

    # 10x leverage calculations
    leverage = 10
    fee_pct = 0.005  # BingX taker

    leveraged_win = avg_win * leverage
    leveraged_loss = avg_loss * leverage
    fee_per_trade = (fee_pct * 2) * leverage

    net_win = leveraged_win - fee_per_trade
    net_loss = leveraged_loss - fee_per_trade

    ev_per_trade = (win_rate/100 * net_win) + ((1-win_rate/100) * net_loss)
    total_expected = ev_per_trade * total_trades

    breakeven_wr = abs(net_loss) / (net_win + abs(net_loss)) * 100

    print(f"\n{'WITH 10x LEVERAGE + FEES:'}")
    print(f"Net win per trade: {net_win:+.2f}% | Net loss: {net_loss:+.2f}%")
    print(f"Expected per trade: {ev_per_trade:+.2f}%")
    print(f"Total expected ({total_trades} trades): {total_expected:+.2f}%")
    print(f"Break-even WR: {breakeven_wr:.1f}% (you: {win_rate:.1f}%)")
    print(f"Expected max DD (10x): {max_dd * 10:.2f}%")

    return {
        'total_trades': total_trades,
        'win_rate': win_rate,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'total_return': total_return,
        'max_dd': max_dd,
        'ev_per_trade': ev_per_trade,
        'total_expected': total_expected
    }


def main():
    print("="*80)
    print("FAST BACKTEST - FULL MONTH 1M DATA")
    print("="*80)

    # Load data
    data_path = Path(__file__).parent.parent / 'trading' / 'fartcoin_usdt_1m_lbank.csv'
    df = pd.read_csv(data_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.set_index(df.index)  # Use numeric index

    print(f"\nLoaded {len(df)} candles")
    print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")

    # Calculate indicators for 1-min
    print("\nCalculating 1-min indicators...")
    df = calculate_indicators(df)
    df = df.dropna()

    # Resample to 5-min for multi-timeframe filter
    print("Resampling to 5-min...")
    df_5min = df.set_index('timestamp').resample('5T').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).reset_index()
    df_5min = calculate_indicators(df_5min)
    df_5min = df_5min.dropna()

    # Load configs
    import yaml
    config_path = Path(__file__).parent / 'config.yaml'
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # LONG strategy
    print("\n" + "="*80)
    print("MULTI-TIMEFRAME LONG (with 5-min filter)")
    print("="*80)
    long_config = config['trading']['strategies']['multi_timeframe_long']
    long_signals = find_long_signals(df, df_5min, long_config)
    print(f"Found {len(long_signals)} potential signals")

    long_trades = simulate_trades(
        df, long_signals, 'LONG',
        long_config['stop_atr_mult'],
        long_config['target_atr_mult']
    )
    long_stats = analyze_results(long_trades, "MULTI-TIMEFRAME LONG")

    # SHORT strategy
    print("\n" + "="*80)
    print("TREND DISTANCE SHORT")
    print("="*80)
    short_config = config['trading']['strategies']['trend_distance_short']
    short_signals = find_short_signals(df, short_config)
    print(f"Found {len(short_signals)} potential signals")

    short_trades = simulate_trades(
        df, short_signals, 'SHORT',
        short_config['stop_atr_mult'],
        short_config['target_atr_mult']
    )
    short_stats = analyze_results(short_trades, "TREND DISTANCE SHORT")

    # Comparison
    if long_stats and short_stats:
        print("\n" + "="*80)
        print("FINAL VERDICT")
        print("="*80)

        winner = 'LONG' if long_stats['total_expected'] > short_stats['total_expected'] else 'SHORT'
        print(f"\n🏆 WINNER: {winner}")
        print(f"\nLong: {long_stats['total_expected']:+.2f}% expected")
        print(f"Short: {short_stats['total_expected']:+.2f}% expected")


if __name__ == "__main__":
    main()
