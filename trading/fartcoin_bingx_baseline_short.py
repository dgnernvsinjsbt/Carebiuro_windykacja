#!/usr/bin/env python3
"""
FARTCOIN BingX - Baseline Trend Distance SHORT Strategy
EXACT implementation from CLAUDE.md for comparison
No modifications - baseline performance test
"""

import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')


class FartcoinBaselineShort:
    """
    Trend Distance SHORT from CLAUDE.md:
    - Price below BOTH 50 and 200 SMA (strong downtrend)
    - At least 2% distance below 50 SMA
    - Explosive Bearish Breakdown (body >1.2%, volume >3x, minimal wicks)
    - RSI 25-55
    - SL: 3x ATR above entry
    - TP: 15x ATR below entry

    Original LBank Performance:
    - Return: +20.08%
    - Max DD: -2.26%
    - R:R: 8.88x
    """

    def __init__(self, data_path: str, initial_capital: float = 10000):
        self.data_path = data_path
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.fee_rate = 0.001  # 0.1% per trade
        self.df = None
        self.trades = []
        self.equity_curve = []

        # EXACT CLAUDE.md parameters
        self.config = {
            'body_threshold': 1.2,        # >1.2% body
            'volume_multiplier': 3.0,     # >3x avg volume
            'wick_threshold': 0.35,       # Minimal wicks
            'rsi_min': 25,                # RSI 25-55
            'rsi_max': 55,
            'sma_distance_min': 2.0,      # At least 2% below SMA50
            'stop_atr_mult': 3.0,         # 3x ATR stop
            'target_atr_mult': 15.0,      # 15x ATR target
        }

        # Simple position sizing (1% risk per trade)
        self.risk_per_trade = 0.01

    def load_data(self):
        """Load and prepare data"""
        print(f"\n{'='*80}")
        print(f"FARTCOIN BINGX BASELINE - TREND DISTANCE SHORT")
        print(f"{'='*80}")
        print(f"Strategy: EXACT CLAUDE.md specification")
        print(f"  Body Threshold:     {self.config['body_threshold']:.1f}%")
        print(f"  Volume Multiplier:  {self.config['volume_multiplier']:.1f}x")
        print(f"  RSI Range:          {self.config['rsi_min']}-{self.config['rsi_max']}")
        print(f"  SMA Distance:       >{self.config['sma_distance_min']:.1f}% below")
        print(f"  Stop:               {self.config['stop_atr_mult']:.1f}x ATR")
        print(f"  Target:             {self.config['target_atr_mult']:.1f}x ATR")
        print(f"  R:R Ratio:          {self.config['target_atr_mult']/self.config['stop_atr_mult']:.1f}:1")
        print(f"{'='*80}\n")

        # Load data
        self.df = pd.read_csv(self.data_path)
        self.df['timestamp'] = pd.to_datetime(self.df['timestamp'])
        self.df = self.df.sort_values('timestamp').reset_index(drop=True)
        self.df.set_index('timestamp', inplace=True)

        print(f"Loading 1-minute data...")
        print(f"  Period: {self.df.index.min()} to {self.df.index.max()}")
        print(f"  Candles: {len(self.df):,} ({len(self.df)/60/24:.1f} days)\n")

        # Calculate indicators
        self._calculate_indicators()

        return self.df

    def _calculate_indicators(self):
        """Calculate all indicators"""
        df = self.df

        # SMAs
        df['sma50'] = df['close'].rolling(50).mean()
        df['sma200'] = df['close'].rolling(200).mean()

        # Distance from SMA50 (negative = below)
        df['sma_distance'] = ((df['close'] - df['sma50']) / df['sma50']) * 100

        # Downtrend: price below BOTH SMAs
        df['downtrend'] = (df['close'] < df['sma50']) & (df['close'] < df['sma200'])

        # ATR for stop/target
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
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        # Volume metrics
        df['volume_sma'] = df['volume'].rolling(20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']

        # Candle metrics
        df['body'] = abs(df['close'] - df['open'])
        df['body_pct'] = (df['body'] / df['open']) * 100
        df['upper_wick'] = df['high'] - np.maximum(df['open'], df['close'])
        df['lower_wick'] = np.minimum(df['open'], df['close']) - df['low']
        df['wick_ratio'] = (df['upper_wick'] + df['lower_wick']) / df['body']

        # Bearish candle
        df['is_bearish'] = df['close'] < df['open']

    def check_entry_signal(self, i):
        """Check if explosive bearish breakdown + strong downtrend"""
        row = self.df.iloc[i]

        # Must be in downtrend (below BOTH SMAs)
        if not row['downtrend']:
            return False

        # Must be at least 2% below SMA50
        if row['sma_distance'] > -self.config['sma_distance_min']:  # Note: negative distance
            return False

        # Bearish candle
        if not row['is_bearish']:
            return False

        # Explosive breakdown
        if row['body_pct'] < self.config['body_threshold']:
            return False

        if row['volume_ratio'] < self.config['volume_multiplier']:
            return False

        if row['wick_ratio'] > self.config['wick_threshold']:
            return False

        # RSI filter
        if row['rsi'] < self.config['rsi_min'] or row['rsi'] > self.config['rsi_max']:
            return False

        return True

    def run_backtest(self):
        """Run baseline backtest"""
        print(f"Running baseline backtest...\n")

        position = None
        entry_idx = None

        for i in range(200, len(self.df)):  # Start after warmup (need 200 for SMA200)
            row = self.df.iloc[i]

            # Entry logic
            if position is None and self.check_entry_signal(i):
                entry_price = row['close']
                entry_time = row.name
                atr = row['atr']

                stop_loss = entry_price + (self.config['stop_atr_mult'] * atr)  # Above for short
                take_profit = entry_price - (self.config['target_atr_mult'] * atr)  # Below for short

                risk_amount = self.capital * self.risk_per_trade
                position_size = risk_amount / (stop_loss - entry_price)

                position = {
                    'entry_price': entry_price,
                    'entry_time': entry_time,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'position_size': position_size,
                    'direction': 'SHORT'
                }
                entry_idx = i

            # Exit logic
            elif position is not None:
                current_price = row['close']

                exit_reason = None
                exit_price = None

                # Check stop loss (price goes UP for short)
                if current_price >= position['stop_loss']:
                    exit_price = position['stop_loss']
                    exit_reason = 'SL'

                # Check take profit (price goes DOWN for short)
                elif current_price <= position['take_profit']:
                    exit_price = position['take_profit']
                    exit_reason = 'TP'

                if exit_reason:
                    # Short P&L: profit when price goes down
                    pnl_gross = (position['entry_price'] - exit_price) * position['position_size']
                    fees = (position['entry_price'] + exit_price) * position['position_size'] * self.fee_rate
                    pnl_net = pnl_gross - fees

                    self.capital += pnl_net

                    trade = {
                        'entry_time': position['entry_time'],
                        'exit_time': row.name,
                        'direction': 'SHORT',
                        'entry_price': position['entry_price'],
                        'exit_price': exit_price,
                        'stop_loss': position['stop_loss'],
                        'take_profit': position['take_profit'],
                        'position_size': position['position_size'],
                        'pnl_gross': pnl_gross,
                        'fees': fees,
                        'pnl_net': pnl_net,
                        'return_pct': (pnl_net / self.capital) * 100,
                        'exit_reason': exit_reason,
                        'bars_held': i - entry_idx
                    }
                    self.trades.append(trade)

                    position = None
                    entry_idx = None

            # Update equity curve
            equity = self.capital
            if position is not None:
                # Short unrealized: profit when price drops
                unrealized = (position['entry_price'] - row['close']) * position['position_size']
                equity += unrealized

            self.equity_curve.append({
                'timestamp': row.name,
                'equity': equity
            })

        print(f"Backtest complete!")
        print(f"  Total trades: {len(self.trades)}")

        return self.trades

    def calculate_metrics(self):
        """Calculate performance metrics"""
        if len(self.trades) == 0:
            print("\n⚠️  NO TRADES EXECUTED")
            return None

        trades_df = pd.DataFrame(self.trades)
        equity_df = pd.DataFrame(self.equity_curve)

        # Calculate returns
        total_return = ((self.capital - self.initial_capital) / self.initial_capital) * 100

        # Calculate drawdown
        equity_df['peak'] = equity_df['equity'].cummax()
        equity_df['drawdown'] = ((equity_df['equity'] - equity_df['peak']) / equity_df['peak']) * 100
        max_drawdown = equity_df['drawdown'].min()

        # Win rate
        winners = trades_df[trades_df['pnl_net'] > 0]
        win_rate = len(winners) / len(trades_df) * 100 if len(trades_df) > 0 else 0

        # R:R ratio (Return/DD)
        rr_ratio = abs(total_return / max_drawdown) if max_drawdown != 0 else 0

        # Average metrics
        avg_win = winners['pnl_net'].mean() if len(winners) > 0 else 0
        losers = trades_df[trades_df['pnl_net'] <= 0]
        avg_loss = losers['pnl_net'].mean() if len(losers) > 0 else 0

        metrics = {
            'total_trades': len(trades_df),
            'winners': len(winners),
            'losers': len(losers),
            'win_rate': win_rate,
            'total_return': total_return,
            'max_drawdown': max_drawdown,
            'rr_ratio': rr_ratio,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'final_capital': self.capital
        }

        return metrics, trades_df, equity_df

    def print_results(self, metrics, trades_df):
        """Print backtest results"""
        print(f"\n{'='*80}")
        print(f"BASELINE RESULTS - TREND DISTANCE SHORT")
        print(f"{'='*80}")

        print(f"\n📊 PERFORMANCE METRICS")
        print(f"  Total Return:       {metrics['total_return']:>8.2f}%")
        print(f"  Max Drawdown:       {metrics['max_drawdown']:>8.2f}%")
        print(f"  R:R Ratio:          {metrics['rr_ratio']:>8.2f}x")
        print(f"  Final Capital:      ${metrics['final_capital']:>8,.2f}")

        print(f"\n📈 TRADE STATISTICS")
        print(f"  Total Trades:       {metrics['total_trades']:>8}")
        print(f"  Winners:            {metrics['winners']:>8}")
        print(f"  Losers:             {metrics['losers']:>8}")
        print(f"  Win Rate:           {metrics['win_rate']:>8.1f}%")
        print(f"  Avg Win:            ${metrics['avg_win']:>8.2f}")
        print(f"  Avg Loss:           ${metrics['avg_loss']:>8.2f}")

        print(f"\n🎯 VS LBANK BASELINE")
        lbank_return = 20.08
        lbank_dd = -2.26
        lbank_rr = 8.88

        print(f"  Return:   BingX {metrics['total_return']:>6.2f}% vs LBank {lbank_return:>6.2f}%  ({metrics['total_return']-lbank_return:>+6.2f}%)")
        print(f"  Max DD:   BingX {metrics['max_drawdown']:>6.2f}% vs LBank {lbank_dd:>6.2f}%  ({metrics['max_drawdown']-lbank_dd:>+6.2f}%)")
        print(f"  R:R:      BingX {metrics['rr_ratio']:>6.2f}x vs LBank {lbank_rr:>6.2f}x  ({metrics['rr_ratio']-lbank_rr:>+6.2f}x)")

        print(f"\n{'='*80}\n")


if __name__ == "__main__":
    data_path = "/workspaces/Carebiuro_windykacja/trading/fartcoin_30d_bingx.csv"

    # Run baseline
    strategy = FartcoinBaselineShort(data_path)
    strategy.load_data()
    trades = strategy.run_backtest()

    if len(trades) > 0:
        metrics, trades_df, equity_df = strategy.calculate_metrics()
        strategy.print_results(metrics, trades_df)

        # Save trades
        trades_df.to_csv('/workspaces/Carebiuro_windykacja/trading/results/fartcoin_bingx_baseline_short_trades.csv', index=False)
        print(f"✅ Trades saved to results/fartcoin_bingx_baseline_short_trades.csv")
    else:
        print("\n⚠️  NO TRADES - Check entry conditions")
