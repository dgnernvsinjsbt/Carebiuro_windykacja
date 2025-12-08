"""
PEPE Master Strategy - BB Oversold Mean Reversion
Implementation based on pattern analysis from prompt 011

Strategy Type: Mean Reversion (Bollinger Band + RSI)
Direction: LONG Only
Timeframe: 1-minute
Expected Win Rate: 65-73%
Expected R:R: 2:1
"""

import pandas as pd
import numpy as np
from typing import Tuple, List
import matplotlib.pyplot as plt

class PEPEStrategy:
    """
    PEPE Mean Reversion Strategy

    Entry Rules (ALL must be true):
    1. Price touches Lower BB (20, 2.0)
    2. RSI(14) <= 30 (oversold)
    3. Candle body >= 0.2%
    4. Volume >= 1.0x average
    5. NOT in CHOPPY regime

    Exit Rules:
    - Stop Loss: 1.5x ATR below entry
    - Take Profit: 3.0x ATR above entry
    - R:R Ratio: 2:1
    - Time Exit: 60 candles (60 minutes)
    """

    def __init__(
        self,
        bb_period: int = 20,
        bb_std: float = 2.0,
        rsi_period: int = 14,
        rsi_threshold: float = 30.0,
        atr_period: int = 14,
        sl_atr_mult: float = 1.5,
        tp_atr_mult: float = 3.0,
        min_body_pct: float = 0.002,  # 0.2%
        vol_mult: float = 1.0,
        time_exit_candles: int = 60,
        fees_pct: float = 0.0007,  # 0.07% round-trip (limit maker + taker)
    ):
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.rsi_period = rsi_period
        self.rsi_threshold = rsi_threshold
        self.atr_period = atr_period
        self.sl_atr_mult = sl_atr_mult
        self.tp_atr_mult = tp_atr_mult
        self.min_body_pct = min_body_pct
        self.vol_mult = vol_mult
        self.time_exit_candles = time_exit_candles
        self.fees_pct = fees_pct

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate all required indicators"""
        df = df.copy()

        # Bollinger Bands
        df['sma20'] = df['close'].rolling(self.bb_period).mean()
        std = df['close'].rolling(self.bb_period).std()
        df['bb_upper'] = df['sma20'] + (std * self.bb_std)
        df['bb_lower'] = df['sma20'] - (std * self.bb_std)

        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(self.rsi_period).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        # ATR
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = true_range.rolling(self.atr_period).mean()

        # Volume average
        df['vol_avg'] = df['volume'].rolling(20).mean()

        # Candle body
        df['body_pct'] = abs(df['close'] - df['open']) / df['close']

        # Regime detection (CHOPPY filter)
        df['wick_ratio'] = (df['high'] - df['low'] - abs(df['close'] - df['open'])) / (df['high'] - df['low'] + 1e-10)
        df['choppy'] = df['wick_ratio'].rolling(20).mean() > 0.6

        return df

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate entry signals based on strategy rules"""
        df = df.copy()

        # Entry conditions (ALL must be true)
        df['bb_touch'] = df['close'] <= df['bb_lower']
        df['rsi_oversold'] = df['rsi'] <= self.rsi_threshold
        df['body_filter'] = df['body_pct'] >= self.min_body_pct
        df['vol_filter'] = df['volume'] >= (df['vol_avg'] * self.vol_mult)
        df['regime_ok'] = ~df['choppy']

        # Combined entry signal
        df['entry_signal'] = (
            df['bb_touch'] &
            df['rsi_oversold'] &
            df['body_filter'] &
            df['vol_filter'] &
            df['regime_ok']
        )

        return df

    def backtest(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Run backtest on historical data

        Returns:
            trades_df: DataFrame with all trades
            summary_df: Performance summary
        """
        # Calculate indicators
        df = self.calculate_indicators(df)

        # Generate signals
        df = self.generate_signals(df)

        # Initialize trade tracking
        trades = []
        in_position = False
        entry_price = 0
        entry_idx = 0
        entry_time = None
        sl_price = 0
        tp_price = 0

        # Iterate through data
        for i in range(len(df)):
            if in_position:
                # Check exits
                current_price = df.iloc[i]['close']
                current_high = df.iloc[i]['high']
                current_low = df.iloc[i]['low']
                current_time = df.iloc[i]['timestamp']

                # Check Stop Loss (using low of candle for realistic execution)
                if current_low <= sl_price:
                    exit_price = sl_price
                    exit_reason = 'SL'
                    pnl_pct = (exit_price - entry_price) / entry_price
                    pnl_after_fees = pnl_pct - self.fees_pct

                    trades.append({
                        'entry_time': entry_time,
                        'exit_time': current_time,
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'sl_price': sl_price,
                        'tp_price': tp_price,
                        'direction': 'LONG',
                        'pnl_pct': pnl_pct * 100,
                        'pnl_after_fees': pnl_after_fees * 100,
                        'hold_candles': i - entry_idx,
                        'exit_reason': exit_reason,
                        'winner': pnl_after_fees > 0
                    })

                    in_position = False
                    continue

                # Check Take Profit (using high of candle for realistic execution)
                if current_high >= tp_price:
                    exit_price = tp_price
                    exit_reason = 'TP'
                    pnl_pct = (exit_price - entry_price) / entry_price
                    pnl_after_fees = pnl_pct - self.fees_pct

                    trades.append({
                        'entry_time': entry_time,
                        'exit_time': current_time,
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'sl_price': sl_price,
                        'tp_price': tp_price,
                        'direction': 'LONG',
                        'pnl_pct': pnl_pct * 100,
                        'pnl_after_fees': pnl_after_fees * 100,
                        'hold_candles': i - entry_idx,
                        'exit_reason': exit_reason,
                        'winner': pnl_after_fees > 0
                    })

                    in_position = False
                    continue

                # Check Time Exit
                if (i - entry_idx) >= self.time_exit_candles:
                    exit_price = current_price
                    exit_reason = 'TIME'
                    pnl_pct = (exit_price - entry_price) / entry_price
                    pnl_after_fees = pnl_pct - self.fees_pct

                    trades.append({
                        'entry_time': entry_time,
                        'exit_time': current_time,
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'sl_price': sl_price,
                        'tp_price': tp_price,
                        'direction': 'LONG',
                        'pnl_pct': pnl_pct * 100,
                        'pnl_after_fees': pnl_after_fees * 100,
                        'hold_candles': i - entry_idx,
                        'exit_reason': exit_reason,
                        'winner': pnl_after_fees > 0
                    })

                    in_position = False
                    continue

            else:
                # Check for entry signal
                if df.iloc[i]['entry_signal']:
                    entry_price = df.iloc[i]['close']
                    entry_time = df.iloc[i]['timestamp']
                    entry_idx = i
                    atr = df.iloc[i]['atr']

                    # Calculate SL and TP
                    sl_price = entry_price - (atr * self.sl_atr_mult)
                    tp_price = entry_price + (atr * self.tp_atr_mult)

                    in_position = True

        # Create trades DataFrame
        trades_df = pd.DataFrame(trades)

        if len(trades_df) == 0:
            print("⚠️ No trades generated. Check entry conditions.")
            return pd.DataFrame(), pd.DataFrame()

        # Calculate performance metrics
        total_trades = len(trades_df)
        winners = trades_df[trades_df['winner'] == True]
        losers = trades_df[trades_df['winner'] == False]

        win_rate = len(winners) / total_trades * 100
        total_return = trades_df['pnl_after_fees'].sum()
        avg_win = winners['pnl_after_fees'].mean() if len(winners) > 0 else 0
        avg_loss = losers['pnl_after_fees'].mean() if len(losers) > 0 else 0
        avg_trade = trades_df['pnl_after_fees'].mean()

        # Calculate profit factor
        gross_profit = winners['pnl_after_fees'].sum() if len(winners) > 0 else 0
        gross_loss = abs(losers['pnl_after_fees'].sum()) if len(losers) > 0 else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

        # Calculate Sharpe ratio
        returns = trades_df['pnl_after_fees'].values
        sharpe = (returns.mean() / returns.std() * np.sqrt(252)) if returns.std() > 0 else 0

        # Calculate max drawdown
        cumulative = (1 + trades_df['pnl_after_fees'] / 100).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max * 100
        max_drawdown = drawdown.min()

        # R:R ratio (realized)
        realized_rr = abs(avg_win / avg_loss) if avg_loss != 0 else 0

        # Trades per day
        if len(trades_df) > 0:
            days = (trades_df['exit_time'].max() - trades_df['entry_time'].min()).total_seconds() / 86400
            trades_per_day = total_trades / days if days > 0 else 0
        else:
            trades_per_day = 0

        # Create summary
        summary = {
            'Total Trades': total_trades,
            'Win Rate (%)': round(win_rate, 2),
            'Total Return (%)': round(total_return, 2),
            'Avg Trade (%)': round(avg_trade, 3),
            'Avg Winner (%)': round(avg_win, 3),
            'Avg Loser (%)': round(avg_loss, 3),
            'Profit Factor': round(profit_factor, 2),
            'Sharpe Ratio': round(sharpe, 2),
            'Max Drawdown (%)': round(max_drawdown, 2),
            'R:R Ratio': round(realized_rr, 2),
            'Best Trade (%)': round(trades_df['pnl_after_fees'].max(), 2),
            'Worst Trade (%)': round(trades_df['pnl_after_fees'].min(), 2),
            'Avg Hold (candles)': round(trades_df['hold_candles'].mean(), 1),
            'Trades/Day': round(trades_per_day, 1),
            'TP Exits': len(trades_df[trades_df['exit_reason'] == 'TP']),
            'SL Exits': len(trades_df[trades_df['exit_reason'] == 'SL']),
            'Time Exits': len(trades_df[trades_df['exit_reason'] == 'TIME'])
        }

        summary_df = pd.DataFrame([summary])

        return trades_df, summary_df

    def plot_equity_curve(self, trades_df: pd.DataFrame, output_path: str = None):
        """Plot equity curve"""
        if len(trades_df) == 0:
            print("No trades to plot")
            return

        cumulative_returns = (1 + trades_df['pnl_after_fees'] / 100).cumprod()
        cumulative_pct = (cumulative_returns - 1) * 100

        # Calculate drawdown
        running_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - running_max) / running_max * 100

        # Create figure
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True)

        # Equity curve
        ax1.plot(cumulative_pct.values, linewidth=2, color='#2E86AB', label='Cumulative Return')
        ax1.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
        ax1.fill_between(range(len(cumulative_pct)), 0, cumulative_pct.values,
                         alpha=0.3, color='#2E86AB')
        ax1.set_ylabel('Cumulative Return (%)', fontsize=12, fontweight='bold')
        ax1.set_title('PEPE Strategy - Equity Curve', fontsize=14, fontweight='bold', pad=20)
        ax1.grid(True, alpha=0.3)
        ax1.legend(fontsize=10)

        # Drawdown
        ax2.fill_between(range(len(drawdown)), 0, drawdown.values,
                         alpha=0.5, color='#A23B72', label='Drawdown')
        ax2.set_xlabel('Trade Number', fontsize=12, fontweight='bold')
        ax2.set_ylabel('Drawdown (%)', fontsize=12, fontweight='bold')
        ax2.set_title('Drawdown', fontsize=12, fontweight='bold', pad=10)
        ax2.grid(True, alpha=0.3)
        ax2.legend(fontsize=10)

        plt.tight_layout()

        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            print(f"✅ Equity curve saved to: {output_path}")
        else:
            plt.show()

        plt.close()


def load_data(file_path: str) -> pd.DataFrame:
    """Load and prepare PEPE data"""
    df = pd.read_csv(file_path)

    # Ensure timestamp column
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    else:
        df['timestamp'] = pd.to_datetime(df['time'])

    # Ensure required columns
    required = ['open', 'high', 'low', 'close', 'volume']
    for col in required:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")

    # Sort by timestamp
    df = df.sort_values('timestamp').reset_index(drop=True)

    return df


def main():
    """Run PEPE strategy backtest"""
    print("=" * 80)
    print("PEPE MASTER STRATEGY - BB OVERSOLD MEAN REVERSION")
    print("=" * 80)
    print()

    # Load data
    data_file = '/workspaces/Carebiuro_windykacja/trading/pepe_usdt_1m_lbank.csv'
    print(f"📊 Loading data from: {data_file}")
    df = load_data(data_file)
    print(f"✅ Loaded {len(df):,} candles")
    print(f"📅 Period: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print()

    # Initialize strategy
    strategy = PEPEStrategy(
        bb_period=20,
        bb_std=2.0,
        rsi_period=14,
        rsi_threshold=30.0,
        atr_period=14,
        sl_atr_mult=1.5,  # 1.5x ATR stop
        tp_atr_mult=3.0,  # 3x ATR target (2:1 R:R)
        min_body_pct=0.002,  # 0.2% minimum body
        vol_mult=1.0,  # 1x average volume
        time_exit_candles=60,  # 60-minute max hold
        fees_pct=0.0007  # 0.07% round-trip
    )

    print("🔧 Strategy Parameters:")
    print(f"   BB: ({strategy.bb_period}, {strategy.bb_std})")
    print(f"   RSI: {strategy.rsi_period} period, threshold {strategy.rsi_threshold}")
    print(f"   Stop Loss: {strategy.sl_atr_mult}x ATR")
    print(f"   Take Profit: {strategy.tp_atr_mult}x ATR")
    print(f"   R:R Ratio: {strategy.tp_atr_mult / strategy.sl_atr_mult}:1")
    print(f"   Max Hold: {strategy.time_exit_candles} candles")
    print(f"   Fees: {strategy.fees_pct * 100:.2f}% round-trip")
    print()

    # Run backtest
    print("⚙️  Running backtest...")
    trades_df, summary_df = strategy.backtest(df)

    if len(trades_df) == 0:
        print("❌ No trades generated. Exiting.")
        return

    print("✅ Backtest complete!")
    print()

    # Display results
    print("=" * 80)
    print("PERFORMANCE SUMMARY")
    print("=" * 80)
    print(summary_df.to_string(index=False))
    print()

    # Exit reason breakdown
    print("📊 Exit Reason Breakdown:")
    exit_counts = trades_df['exit_reason'].value_counts()
    for reason, count in exit_counts.items():
        pct = count / len(trades_df) * 100
        print(f"   {reason}: {count} ({pct:.1f}%)")
    print()

    # Save results
    output_dir = '/workspaces/Carebiuro_windykacja/trading/results'

    # Save trades
    trades_file = f'{output_dir}/PEPE_strategy_results.csv'
    trades_df.to_csv(trades_file, index=False)
    print(f"✅ Trades saved to: {trades_file}")

    # Save summary
    summary_file = f'{output_dir}/PEPE_strategy_summary.md'
    with open(summary_file, 'w') as f:
        f.write("# PEPE Strategy - Performance Summary\n\n")
        f.write(f"**Strategy**: BB Oversold Mean Reversion\n")
        f.write(f"**Period**: {df['timestamp'].min()} to {df['timestamp'].max()}\n")
        f.write(f"**Candles**: {len(df):,}\n\n")
        f.write("## Performance Metrics\n\n")
        f.write(summary_df.to_markdown(index=False))
        f.write("\n\n## Strategy Parameters\n\n")
        f.write(f"- **Bollinger Bands**: ({strategy.bb_period}, {strategy.bb_std})\n")
        f.write(f"- **RSI**: {strategy.rsi_period} period, threshold {strategy.rsi_threshold}\n")
        f.write(f"- **Stop Loss**: {strategy.sl_atr_mult}x ATR\n")
        f.write(f"- **Take Profit**: {strategy.tp_atr_mult}x ATR\n")
        f.write(f"- **R:R Ratio**: {strategy.tp_atr_mult / strategy.sl_atr_mult}:1\n")
        f.write(f"- **Max Hold**: {strategy.time_exit_candles} candles\n")
        f.write(f"- **Fees**: {strategy.fees_pct * 100:.2f}% round-trip\n")
    print(f"✅ Summary saved to: {summary_file}")

    # Plot equity curve
    equity_file = f'{output_dir}/PEPE_strategy_equity.png'
    strategy.plot_equity_curve(trades_df, equity_file)

    print()
    print("=" * 80)
    print("🎯 STRATEGY VALIDATION")
    print("=" * 80)

    win_rate = summary_df['Win Rate (%)'].values[0]
    total_return = summary_df['Total Return (%)'].values[0]
    rr_ratio = summary_df['R:R Ratio'].values[0]

    # Validate against expected performance
    if win_rate >= 60:
        print(f"✅ Win Rate: {win_rate:.1f}% (Target: 65-73%) - ACCEPTABLE")
    else:
        print(f"⚠️  Win Rate: {win_rate:.1f}% (Target: 65-73%) - BELOW TARGET")

    if total_return > 0:
        print(f"✅ Total Return: {total_return:.2f}% - PROFITABLE")
    else:
        print(f"❌ Total Return: {total_return:.2f}% - UNPROFITABLE")

    if rr_ratio >= 1.5:
        print(f"✅ R:R Ratio: {rr_ratio:.2f}:1 (Target: 2:1) - ACCEPTABLE")
    else:
        print(f"⚠️  R:R Ratio: {rr_ratio:.2f}:1 (Target: 2:1) - BELOW TARGET")

    print()
    print("=" * 80)
    print("✅ ANALYSIS COMPLETE")
    print("=" * 80)


if __name__ == '__main__':
    main()
