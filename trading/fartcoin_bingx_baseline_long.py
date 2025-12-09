#!/usr/bin/env python3
"""
FARTCOIN BingX - Baseline Multi-Timeframe LONG Strategy
EXACT implementation from CLAUDE.md for comparison
No modifications - baseline performance test
"""

import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')


class FartcoinBaselineLong:
    """
    Multi-Timeframe LONG from CLAUDE.md:
    - Explosive Bullish Breakout on 1-min (body >1.2%, volume >3x, minimal wicks)
    - 5-min confirmation: Close > SMA50, RSI > 57, distance > 0.6% above SMA
    - RSI 45-75, high volatility required
    - SL: 3x ATR below entry
    - TP: 12x ATR above entry

    Original LBank Performance:
    - Return: +10.38%
    - Max DD: -1.45%
    - R:R: 7.14x
    """

    def __init__(self, data_path: str, initial_capital: float = 10000):
        self.data_path = data_path
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.fee_rate = 0.001  # 0.1% per trade
        self.df = None
        self.df_5min = None
        self.trades = []
        self.equity_curve = []

        # EXACT CLAUDE.md parameters
        self.config = {
            'body_threshold': 1.2,        # >1.2% body
            'volume_multiplier': 3.0,     # >3x avg volume
            'wick_threshold': 0.35,       # Minimal wicks
            'rsi_1min_min': 45,           # RSI 45-75
            'rsi_1min_max': 75,
            'rsi_5min_min': 57,           # 5-min RSI > 57
            'sma_distance_min': 0.6,      # >0.6% above SMA50
            'stop_atr_mult': 3.0,         # 3x ATR stop
            'target_atr_mult': 12.0,      # 12x ATR target
        }

        # Simple position sizing (1% risk per trade)
        self.risk_per_trade = 0.01

    def load_data(self):
        """Load and prepare 1-min and 5-min data"""
        print(f"\n{'='*80}")
        print(f"FARTCOIN BINGX BASELINE - MULTI-TIMEFRAME LONG")
        print(f"{'='*80}")
        print(f"Strategy: EXACT CLAUDE.md specification")
        print(f"  Body Threshold:     {self.config['body_threshold']:.1f}%")
        print(f"  Volume Multiplier:  {self.config['volume_multiplier']:.1f}x")
        print(f"  RSI Range (1-min):  {self.config['rsi_1min_min']}-{self.config['rsi_1min_max']}")
        print(f"  RSI Min (5-min):    >{self.config['rsi_5min_min']}")
        print(f"  SMA Distance:       >{self.config['sma_distance_min']:.1f}%")
        print(f"  Stop:               {self.config['stop_atr_mult']:.1f}x ATR")
        print(f"  Target:             {self.config['target_atr_mult']:.1f}x ATR")
        print(f"  R:R Ratio:          {self.config['target_atr_mult']/self.config['stop_atr_mult']:.1f}:1")
        print(f"{'='*80}\n")

        # Load 1-min data
        self.df = pd.read_csv(self.data_path)
        self.df['timestamp'] = pd.to_datetime(self.df['timestamp'])
        self.df = self.df.sort_values('timestamp').reset_index(drop=True)
        self.df.set_index('timestamp', inplace=True)

        print(f"Loading 1-minute data...")
        print(f"  Period: {self.df.index.min()} to {self.df.index.max()}")
        print(f"  Candles: {len(self.df):,} ({len(self.df)/60/24:.1f} days)\n")

        # Calculate 1-min indicators
        self._calculate_1min_indicators()

        # Resample to 5-min
        print(f"Resampling to 5-minute timeframe...")
        self._resample_5min()
        self._calculate_5min_indicators()

        # Merge 5-min data back to 1-min (only indicators, not OHLCV)
        # Select only the indicator columns we need
        df_5min_indicators = self.df_5min[['sma50', 'rsi', 'sma_distance', 'uptrend']].copy()
        df_5min_indicators.columns = [f'{col}_5min' for col in df_5min_indicators.columns]

        self.df = self.df.join(df_5min_indicators, how='left')
        self.df.fillna(method='ffill', inplace=True)

        print(f"  5-min candles: {len(self.df_5min):,}\n")

        return self.df

    def _calculate_1min_indicators(self):
        """Calculate 1-minute indicators"""
        df = self.df

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

        # Bullish candle
        df['is_bullish'] = df['close'] > df['open']

    def _resample_5min(self):
        """Resample to 5-minute candles"""
        ohlc = {
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }
        self.df_5min = self.df.resample('5T').agg(ohlc).dropna()

    def _calculate_5min_indicators(self):
        """Calculate 5-minute indicators"""
        df = self.df_5min

        # SMA 50
        df['sma50'] = df['close'].rolling(50).mean()

        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        # Distance from SMA
        df['sma_distance'] = ((df['close'] - df['sma50']) / df['sma50']) * 100

        # Uptrend: close > SMA50
        df['uptrend'] = df['close'] > df['sma50']

    def check_entry_signal(self, i):
        """Check if explosive bullish pattern + 5-min confirmation"""
        row = self.df.iloc[i]

        # 1-min filters
        if not row['is_bullish']:
            return False

        if row['body_pct'] < self.config['body_threshold']:
            return False

        if row['volume_ratio'] < self.config['volume_multiplier']:
            return False

        if row['wick_ratio'] > self.config['wick_threshold']:
            return False

        if row['rsi'] < self.config['rsi_1min_min'] or row['rsi'] > self.config['rsi_1min_max']:
            return False

        # 5-min confirmation filters
        if pd.isna(row['uptrend_5min']) or not row['uptrend_5min']:
            return False

        if pd.isna(row['rsi_5min']) or row['rsi_5min'] <= self.config['rsi_5min_min']:
            return False

        if pd.isna(row['sma_distance_5min']) or row['sma_distance_5min'] < self.config['sma_distance_min']:
            return False

        return True

    def run_backtest(self):
        """Run baseline backtest"""
        print(f"Running baseline backtest...\n")

        position = None
        entry_idx = None

        for i in range(100, len(self.df)):  # Start after warmup
            row = self.df.iloc[i]

            # Skip if not enough 5-min data
            if pd.isna(row['sma50_5min']):
                continue

            # Entry logic
            if position is None and self.check_entry_signal(i):
                entry_price = row['close']
                entry_time = row.name
                atr = row['atr']

                stop_loss = entry_price - (self.config['stop_atr_mult'] * atr)
                take_profit = entry_price + (self.config['target_atr_mult'] * atr)

                risk_amount = self.capital * self.risk_per_trade
                position_size = risk_amount / (entry_price - stop_loss)

                position = {
                    'entry_price': entry_price,
                    'entry_time': entry_time,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'position_size': position_size,
                    'direction': 'LONG'
                }
                entry_idx = i

            # Exit logic
            elif position is not None:
                current_price = row['close']

                exit_reason = None
                exit_price = None

                # Check stop loss
                if current_price <= position['stop_loss']:
                    exit_price = position['stop_loss']
                    exit_reason = 'SL'

                # Check take profit
                elif current_price >= position['take_profit']:
                    exit_price = position['take_profit']
                    exit_reason = 'TP'

                if exit_reason:
                    pnl_gross = (exit_price - position['entry_price']) * position['position_size']
                    fees = (position['entry_price'] + exit_price) * position['position_size'] * self.fee_rate
                    pnl_net = pnl_gross - fees

                    self.capital += pnl_net

                    trade = {
                        'entry_time': position['entry_time'],
                        'exit_time': row.name,
                        'direction': 'LONG',
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
                unrealized = (row['close'] - position['entry_price']) * position['position_size']
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
        print(f"BASELINE RESULTS - MULTI-TIMEFRAME LONG")
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
        lbank_return = 10.38
        lbank_dd = -1.45
        lbank_rr = 7.14

        print(f"  Return:   BingX {metrics['total_return']:>6.2f}% vs LBank {lbank_return:>6.2f}%  ({metrics['total_return']-lbank_return:>+6.2f}%)")
        print(f"  Max DD:   BingX {metrics['max_drawdown']:>6.2f}% vs LBank {lbank_dd:>6.2f}%  ({metrics['max_drawdown']-lbank_dd:>+6.2f}%)")
        print(f"  R:R:      BingX {metrics['rr_ratio']:>6.2f}x vs LBank {lbank_rr:>6.2f}x  ({metrics['rr_ratio']-lbank_rr:>+6.2f}x)")

        print(f"\n{'='*80}\n")


if __name__ == "__main__":
    data_path = "/workspaces/Carebiuro_windykacja/trading/fartcoin_30d_bingx.csv"

    # Run baseline
    strategy = FartcoinBaselineLong(data_path)
    strategy.load_data()
    trades = strategy.run_backtest()

    if len(trades) > 0:
        metrics, trades_df, equity_df = strategy.calculate_metrics()
        strategy.print_results(metrics, trades_df)

        # Save trades
        trades_df.to_csv('/workspaces/Carebiuro_windykacja/trading/results/fartcoin_bingx_baseline_long_trades.csv', index=False)
        print(f"✅ Trades saved to results/fartcoin_bingx_baseline_long_trades.csv")
    else:
        print("\n⚠️  NO TRADES - Check entry conditions")
