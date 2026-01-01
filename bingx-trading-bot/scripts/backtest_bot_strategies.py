"""
Quick backtest of bot strategies on 1m FARTCOIN data
Gets exact win rate, avg win, avg loss for leverage calculations
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

# Add strategies directory to path
sys.path.insert(0, str(Path(__file__).parent))

from strategies.multi_timeframe_long import MultiTimeframeLongStrategy
from strategies.trend_distance_short import TrendDistanceShortStrategy


def calculate_indicators(df):
    """Calculate all required indicators"""

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

    # Trend detection
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


def run_backtest(strategy, df_1min, df_5min, strategy_name):
    """Run backtest for a strategy"""

    print(f"\n{'='*80}")
    print(f"BACKTESTING: {strategy_name}")
    print(f"{'='*80}")

    trades = []
    in_position = False
    entry_price = None
    stop_loss = None
    take_profit = None
    entry_idx = None

    # Iterate through candles
    for i in range(250, len(df_1min)):
        current_df = df_1min.iloc[:i+1].copy()

        if not in_position:
            # Get current 5-min data up to this point
            current_timestamp = df_1min.iloc[i]['timestamp']
            current_df_5min = df_5min[df_5min['timestamp'] <= current_timestamp].copy()

            # Check for signal with BOTH timeframes
            signal = strategy.analyze(current_df, current_df_5min)

            if signal:
                # Enter position
                in_position = True
                entry_price = signal['entry_price']
                stop_loss = signal['stop_loss']
                take_profit = signal['take_profit']
                entry_idx = i

        else:
            # Check if SL or TP hit
            current_candle = df_1min.iloc[i]

            # Check stop loss hit
            if signal['direction'] == 'LONG':
                if current_candle['low'] <= stop_loss:
                    # Stop loss hit
                    exit_price = stop_loss
                    pnl_pct = ((exit_price - entry_price) / entry_price) * 100

                    trades.append({
                        'entry_idx': entry_idx,
                        'exit_idx': i,
                        'direction': 'LONG',
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'exit_type': 'SL',
                        'pnl_pct': pnl_pct
                    })

                    in_position = False

                # Check take profit hit
                elif current_candle['high'] >= take_profit:
                    # Take profit hit
                    exit_price = take_profit
                    pnl_pct = ((exit_price - entry_price) / entry_price) * 100

                    trades.append({
                        'entry_idx': entry_idx,
                        'exit_idx': i,
                        'direction': 'LONG',
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'exit_type': 'TP',
                        'pnl_pct': pnl_pct
                    })

                    in_position = False

            elif signal['direction'] == 'SHORT':
                if current_candle['high'] >= stop_loss:
                    # Stop loss hit
                    exit_price = stop_loss
                    pnl_pct = ((entry_price - exit_price) / entry_price) * 100

                    trades.append({
                        'entry_idx': entry_idx,
                        'exit_idx': i,
                        'direction': 'SHORT',
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'exit_type': 'SL',
                        'pnl_pct': pnl_pct
                    })

                    in_position = False

                # Check take profit hit
                elif current_candle['low'] <= take_profit:
                    # Take profit hit
                    exit_price = take_profit
                    pnl_pct = ((entry_price - exit_price) / entry_price) * 100

                    trades.append({
                        'entry_idx': entry_idx,
                        'exit_idx': i,
                        'direction': 'SHORT',
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'exit_type': 'TP',
                        'pnl_pct': pnl_pct
                    })

                    in_position = False

    # Analyze trades
    if not trades:
        print("\n❌ No trades generated!")
        return None

    trades_df = pd.DataFrame(trades)

    # Calculate stats
    total_trades = len(trades_df)
    wins = trades_df[trades_df['pnl_pct'] > 0]
    losses = trades_df[trades_df['pnl_pct'] <= 0]

    num_wins = len(wins)
    num_losses = len(losses)
    win_rate = (num_wins / total_trades) * 100

    avg_win = wins['pnl_pct'].mean() if num_wins > 0 else 0
    avg_loss = losses['pnl_pct'].mean() if num_losses > 0 else 0

    total_return = trades_df['pnl_pct'].sum()

    # Calculate drawdown
    cumulative_returns = (1 + trades_df['pnl_pct'] / 100).cumprod()
    running_max = cumulative_returns.expanding().max()
    drawdown = (cumulative_returns - running_max) / running_max * 100
    max_drawdown = drawdown.min()

    # Print results
    print(f"\n📊 RESULTS:")
    print(f"   Total trades: {total_trades}")
    print(f"   Wins: {num_wins}")
    print(f"   Losses: {num_losses}")
    print(f"   Win rate: {win_rate:.1f}%")
    print(f"   Average win: {avg_win:.2f}%")
    print(f"   Average loss: {avg_loss:.2f}%")
    print(f"   Total return: {total_return:.2f}%")
    print(f"   Max drawdown: {max_drawdown:.2f}%")

    if num_wins > 0 and num_losses > 0:
        rr_ratio = abs(avg_win / avg_loss)
        print(f"   Actual R:R: 1:{rr_ratio:.2f}")

    return {
        'total_trades': total_trades,
        'num_wins': num_wins,
        'num_losses': num_losses,
        'win_rate': win_rate,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'total_return': total_return,
        'max_drawdown': max_drawdown,
        'trades_df': trades_df
    }


def calculate_10x_leverage_pnl(stats, strategy_name):
    """Calculate P&L with 10x leverage based on actual backtest stats"""

    print(f"\n{'='*80}")
    print(f"10x LEVERAGE P&L - {strategy_name}")
    print(f"{'='*80}")

    account = 100.0
    leverage = 10
    fee_pct = 0.005  # BingX taker fee

    # Actual stats from backtest
    win_rate = stats['win_rate'] / 100
    avg_win_pct = stats['avg_win']
    avg_loss_pct = stats['avg_loss']

    # With 10x leverage, each % becomes 10%
    leveraged_win_pct = avg_win_pct * leverage
    leveraged_loss_pct = avg_loss_pct * leverage

    # Calculate fee impact per trade
    # Fee = 0.005% on entry + 0.005% on exit = 0.01% per trade
    # At 10x leverage, position value is 10x, so fees are 10x too
    fee_per_trade_pct = (fee_pct * 2) * leverage  # 0.01% × 10 = 0.1%

    # Net P&L per trade
    net_win = leveraged_win_pct - fee_per_trade_pct
    net_loss = leveraged_loss_pct - fee_per_trade_pct

    # Expected value per trade
    ev_per_trade = (win_rate * net_win) + ((1 - win_rate) * net_loss)

    # Total expected return over all trades
    total_trades = stats['total_trades']
    total_expected = ev_per_trade * total_trades

    print(f"\n📈 ACTUAL BACKTEST STATS:")
    print(f"   Win rate: {win_rate*100:.1f}%")
    print(f"   Avg win (1x): {avg_win_pct:.2f}%")
    print(f"   Avg loss (1x): {avg_loss_pct:.2f}%")
    print(f"   Total trades: {total_trades}")

    print(f"\n⚡ WITH 10x LEVERAGE:")
    print(f"   Avg win (10x): {leveraged_win_pct:.2f}%")
    print(f"   Avg loss (10x): {leveraged_loss_pct:.2f}%")
    print(f"   Fee per trade: {fee_per_trade_pct:.2f}%")

    print(f"\n💰 NET P&L (after fees):")
    print(f"   Net win per trade: {net_win:+.2f}%")
    print(f"   Net loss per trade: {net_loss:+.2f}%")

    print(f"\n🎯 EXPECTED VALUE:")
    print(f"   Per trade: {ev_per_trade:+.2f}%")
    print(f"   After {total_trades} trades: {total_expected:+.2f}%")
    print(f"   On $100 account: ${account * (total_expected/100):+.2f}")

    # Break-even win rate
    # At break-even: win_rate × net_win + (1 - win_rate) × net_loss = 0
    # win_rate × net_win = -(1 - win_rate) × net_loss
    # win_rate × net_win = -net_loss + win_rate × net_loss
    # win_rate × (net_win - net_loss) = -net_loss
    # win_rate = -net_loss / (net_win - net_loss)
    breakeven_wr = abs(net_loss) / (net_win + abs(net_loss))

    print(f"\n🎲 BREAK-EVEN:")
    print(f"   Need win rate > {breakeven_wr*100:.1f}%")
    print(f"   Your win rate: {win_rate*100:.1f}%")
    print(f"   Profitable? {'✅ YES' if win_rate > breakeven_wr else '❌ NO'}")

    return {
        'ev_per_trade': ev_per_trade,
        'total_expected': total_expected,
        'net_win': net_win,
        'net_loss': net_loss,
        'breakeven_wr': breakeven_wr
    }


def main():
    print("="*80)
    print("BACKTESTING BOT STRATEGIES ON 1M FARTCOIN DATA (1 MONTH - Nov 5 to Dec 5)")
    print("="*80)

    # Load data
    print("\n📁 Loading FARTCOIN 1m data...")
    data_path = Path(__file__).parent.parent / 'trading' / 'fartcoin_usdt_1m_lbank.csv'
    df = pd.read_csv(data_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    print(f"   Loaded {len(df)} candles")
    print(f"   Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")

    # Calculate indicators
    print("\n📊 Calculating indicators...")
    df = calculate_indicators(df)

    # Resample to 5-min for multi-timeframe filter
    print("📊 Resampling to 5-min...")
    df_5min = df.set_index('timestamp').resample('5min').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).reset_index()
    df_5min = calculate_indicators(df_5min)

    # Load strategy configs from config.yaml
    import yaml
    config_path = Path(__file__).parent / 'config.yaml'
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # Strategy 1: Multi-Timeframe Long
    long_config = {
        'params': config['trading']['strategies']['multi_timeframe_long']
    }
    long_strategy = MultiTimeframeLongStrategy(long_config)
    long_stats = run_backtest(long_strategy, df, df_5min, 'Multi-Timeframe Long')

    # Strategy 2: Trend Distance Short
    short_config = {
        'params': config['trading']['strategies']['trend_distance_short']
    }
    short_strategy = TrendDistanceShortStrategy(short_config)
    short_stats = run_backtest(short_strategy, df, df_5min, 'Trend Distance Short')

    # Calculate 10x leverage P&L
    if long_stats:
        long_leverage = calculate_10x_leverage_pnl(long_stats, 'Multi-Timeframe Long')

    if short_stats:
        short_leverage = calculate_10x_leverage_pnl(short_stats, 'Trend Distance Short')

    # Final comparison
    if long_stats and short_stats:
        print("\n\n" + "="*80)
        print("FINAL COMPARISON")
        print("="*80)

        print(f"\n{'Metric':<40} {'Long':<20} {'Short':<20}")
        print("-"*80)
        print(f"{'Total trades':<40} {long_stats['total_trades']:<20} {short_stats['total_trades']:<20}")
        print(f"{'Win rate':<40} {f'{long_stats["win_rate"]:.1f}%':<20} {f'{short_stats["win_rate"]:.1f}%':<20}")
        print(f"{'Avg win (1x)':<40} {f'{long_stats["avg_win"]:.2f}%':<20} {f'{short_stats["avg_win"]:.2f}%':<20}")
        print(f"{'Avg loss (1x)':<40} {f'{long_stats["avg_loss"]:.2f}%':<20} {f'{short_stats["avg_loss"]:.2f}%':<20}")
        print(f"{'Total return (1x)':<40} {f'{long_stats["total_return"]:.2f}%':<20} {f'{short_stats["total_return"]:.2f}%':<20}")
        print(f"{'Max DD (1x)':<40} {f'{long_stats["max_drawdown"]:.2f}%':<20} {f'{short_stats["max_drawdown"]:.2f}%':<20}")

        print(f"\n{'WITH 10x LEVERAGE:':<40}")
        print(f"{'Expected per trade':<40} {f'{long_leverage["ev_per_trade"]:+.2f}%':<20} {f'{short_leverage["ev_per_trade"]:+.2f}%':<20}")
        print(f"{'Total expected return':<40} {f'{long_leverage["total_expected"]:+.2f}%':<20} {f'{short_leverage["total_expected"]:+.2f}%':<20}")

        winner = 'SHORT' if short_leverage['total_expected'] > long_leverage['total_expected'] else 'LONG'
        print(f"\n🏆 WINNER: {winner}")


if __name__ == "__main__":
    main()
