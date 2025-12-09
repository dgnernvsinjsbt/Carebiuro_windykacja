#!/usr/bin/env python3
"""
MOODENG RSI Momentum Strategy - BingX Implementation

⚠️ WARNING: This strategy is NOT RECOMMENDED for live trading due to:
- 361% profit concentration in top 20% of trades
- 56.5% of profit from single trade
- 97 consecutive loss maximum streak

Use ONLY for:
- Research purposes
- Paper trading
- Portfolio diversification (10-20% allocation max)
- Fully automated execution with 12-month commitment

Performance (32 days BingX):
- NET Return: +18.78%
- Max DD: -5.21%
- Return/DD: 3.60x
- Win Rate: 31%
- Trades: 127
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, List


class MOODENGRSIStrategy:
    """
    RSI Momentum Long Strategy for MOODENG/USDT

    Entry:
    - RSI(14) crosses above 55
    - Bullish candle with body > 0.5%
    - Price above SMA(20)

    Exit:
    - SL: 1.0x ATR below entry
    - TP: 4.0x ATR above entry
    - Time: 60 bars maximum
    """

    def __init__(self,
                 rsi_period: int = 14,
                 rsi_entry: float = 55,
                 body_thresh: float = 0.5,
                 sma_period: int = 20,
                 atr_period: int = 14,
                 sl_mult: float = 1.0,
                 tp_mult: float = 4.0,
                 max_bars: int = 60):
        """
        Initialize strategy parameters

        Args:
            rsi_period: RSI calculation period (default 14)
            rsi_entry: RSI crossover threshold (default 55)
            body_thresh: Minimum candle body % (default 0.5)
            sma_period: SMA trend filter period (default 20)
            atr_period: ATR calculation period (default 14)
            sl_mult: Stop loss ATR multiplier (default 1.0)
            tp_mult: Take profit ATR multiplier (default 4.0)
            max_bars: Maximum hold time in bars (default 60)
        """
        self.rsi_period = rsi_period
        self.rsi_entry = rsi_entry
        self.body_thresh = body_thresh
        self.sma_period = sma_period
        self.atr_period = atr_period
        self.sl_mult = sl_mult
        self.tp_mult = tp_mult
        self.max_bars = max_bars

        # Position tracking
        self.in_position = False
        self.entry_price = 0
        self.entry_idx = 0
        self.stop_loss = 0
        self.take_profit = 0
        self.entry_atr = 0

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate all required indicators"""

        # Candle properties
        df['body'] = df['close'] - df['open']
        df['body_pct'] = abs(df['body']) / df['open'] * 100
        df['is_bullish'] = df['close'] > df['open']

        # ATR
        df['tr'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(
                abs(df['high'] - df['close'].shift(1)),
                abs(df['low'] - df['close'].shift(1))
            )
        )
        df['atr'] = df['tr'].rolling(self.atr_period).mean()

        # RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(self.rsi_period).mean()
        rs = gain / (loss + 0.0001)
        df['rsi'] = 100 - (100 / (1 + rs))

        # SMA
        df['sma'] = df['close'].rolling(self.sma_period).mean()
        df['above_sma'] = df['close'] > df['sma']

        return df

    def check_entry(self, current: pd.Series, previous: pd.Series) -> bool:
        """
        Check if entry conditions are met

        Returns:
            True if all entry conditions satisfied
        """
        # RSI crossover
        rsi_cross = previous['rsi'] < self.rsi_entry and current['rsi'] >= self.rsi_entry

        # Bullish candle with sufficient body
        bullish_body = current['is_bullish'] and current['body_pct'] > self.body_thresh

        # Above SMA trend filter
        above_sma = current['above_sma']

        return rsi_cross and bullish_body and above_sma

    def enter_position(self, row: pd.Series, idx: int):
        """Execute entry logic"""
        self.in_position = True
        self.entry_price = row['close']
        self.entry_idx = idx
        self.entry_atr = row['atr']

        # Calculate stops
        self.stop_loss = self.entry_price - (self.entry_atr * self.sl_mult)
        self.take_profit = self.entry_price + (self.entry_atr * self.tp_mult)

    def check_exit(self, row: pd.Series, idx: int) -> Optional[Dict]:
        """
        Check exit conditions

        Returns:
            Trade dict if exit triggered, None otherwise
        """
        bars_held = idx - self.entry_idx

        # Stop Loss
        if row['low'] <= self.stop_loss:
            pnl = (self.stop_loss - self.entry_price) / self.entry_price * 100
            return {
                'entry_idx': self.entry_idx,
                'exit_idx': idx,
                'entry_price': self.entry_price,
                'exit_price': self.stop_loss,
                'pnl_pct': pnl,
                'result': 'SL',
                'bars_held': bars_held
            }

        # Take Profit
        if row['high'] >= self.take_profit:
            pnl = (self.take_profit - self.entry_price) / self.entry_price * 100
            return {
                'entry_idx': self.entry_idx,
                'exit_idx': idx,
                'entry_price': self.entry_price,
                'exit_price': self.take_profit,
                'pnl_pct': pnl,
                'result': 'TP',
                'bars_held': bars_held
            }

        # Time Exit
        if bars_held >= self.max_bars:
            exit_price = row['close']
            pnl = (exit_price - self.entry_price) / self.entry_price * 100
            return {
                'entry_idx': self.entry_idx,
                'exit_idx': idx,
                'entry_price': self.entry_price,
                'exit_price': exit_price,
                'pnl_pct': pnl,
                'result': 'TIME',
                'bars_held': bars_held
            }

        return None

    def exit_position(self):
        """Reset position tracking"""
        self.in_position = False
        self.entry_price = 0
        self.entry_idx = 0
        self.stop_loss = 0
        self.take_profit = 0
        self.entry_atr = 0

    def backtest(self, df: pd.DataFrame) -> List[Dict]:
        """
        Run full backtest on historical data

        Args:
            df: DataFrame with OHLCV data

        Returns:
            List of trade dictionaries
        """
        # Calculate indicators
        df = self.calculate_indicators(df)

        # Reset position state
        self.in_position = False
        trades = []

        # Start after indicator warmup period
        start_idx = max(self.rsi_period, self.sma_period, self.atr_period) * 2

        for i in range(start_idx, len(df)):
            current_row = df.iloc[i]
            previous_row = df.iloc[i-1]

            if not self.in_position:
                # Check entry
                if self.check_entry(current_row, previous_row):
                    self.enter_position(current_row, i)
            else:
                # Check exit
                trade = self.check_exit(current_row, i)
                if trade:
                    trades.append(trade)
                    self.exit_position()

        return trades

    def analyze_results(self, trades: List[Dict], fee_pct: float = 0.10) -> Dict:
        """
        Analyze backtest results

        Args:
            trades: List of trade dictionaries
            fee_pct: Round-trip fee percentage (default 0.10 for BingX)

        Returns:
            Dictionary of performance metrics
        """
        if not trades:
            return {'error': 'No trades generated'}

        df_trades = pd.DataFrame(trades)

        # Win rate
        winners = df_trades[df_trades['pnl_pct'] > 0]
        losers = df_trades[df_trades['pnl_pct'] <= 0]
        win_rate = len(winners) / len(df_trades) * 100

        # Average win/loss
        avg_win = winners['pnl_pct'].mean() if len(winners) > 0 else 0
        avg_loss = abs(losers['pnl_pct'].mean()) if len(losers) > 0 else 0

        # Gross profit/loss
        gross_profit = winners['pnl_pct'].sum() if len(winners) > 0 else 0
        gross_loss = abs(losers['pnl_pct'].sum()) if len(losers) > 0 else 0

        # Profit factor and R:R
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        rr_ratio = avg_win / avg_loss if avg_loss > 0 else float('inf')

        # Equity curve
        equity = [100]
        for pnl in df_trades['pnl_pct']:
            equity.append(equity[-1] * (1 + pnl/100))

        # Drawdown
        peak = equity[0]
        max_dd = 0
        for e in equity:
            if e > peak:
                peak = e
            dd = (peak - e) / peak * 100
            max_dd = max(max_dd, dd)

        # Returns
        gross_return = equity[-1] - 100
        fee_cost = len(df_trades) * fee_pct
        net_return = gross_return - fee_cost

        # Return/DD ratio
        return_dd = abs(net_return / max_dd) if max_dd > 0 else 0

        # Exit breakdown
        exit_counts = df_trades['result'].value_counts().to_dict()

        return {
            'total_trades': len(df_trades),
            'winners': len(winners),
            'losers': len(losers),
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'gross_profit': gross_profit,
            'gross_loss': gross_loss,
            'profit_factor': profit_factor,
            'rr_ratio': rr_ratio,
            'gross_return': gross_return,
            'fee_cost': fee_cost,
            'net_return': net_return,
            'max_drawdown': max_dd,
            'return_dd': return_dd,
            'avg_bars_held': df_trades['bars_held'].mean(),
            'exit_breakdown': exit_counts
        }

    def print_results(self, results: Dict):
        """Print formatted backtest results"""
        print("="*70)
        print("MOODENG RSI MOMENTUM STRATEGY - BACKTEST RESULTS")
        print("="*70)
        print(f"\nTrade Statistics:")
        print(f"  Total Trades:    {results['total_trades']}")
        print(f"  Winners:         {results['winners']}")
        print(f"  Losers:          {results['losers']}")
        print(f"  Win Rate:        {results['win_rate']:.1f}%")
        print(f"  Avg Win:         {results['avg_win']:+.2f}%")
        print(f"  Avg Loss:        {results['avg_loss']:.2f}%")
        print(f"  Profit Factor:   {results['profit_factor']:.2f}")
        print(f"  Risk:Reward:     {results['rr_ratio']:.2f}:1")

        print(f"\nReturns:")
        print(f"  Gross Return:    {results['gross_return']:+.2f}%")
        print(f"  Fee Cost:        -{results['fee_cost']:.2f}%")
        print(f"  NET Return:      {results['net_return']:+.2f}%")
        print(f"  Max Drawdown:    -{results['max_drawdown']:.2f}%")
        print(f"  Return/DD Ratio: {results['return_dd']:.2f}x")

        print(f"\nTrade Details:")
        print(f"  Avg Hold Time:   {results['avg_bars_held']:.1f} bars")
        print(f"  Exit Breakdown:")
        for exit_type, count in results['exit_breakdown'].items():
            print(f"    {exit_type}: {count} trades")


def main():
    """Example usage"""
    # Load data
    df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/moodeng_30d_bingx.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)

    print(f"Loaded {len(df):,} candles")
    print(f"Date range: {df['timestamp'].iloc[0]} to {df['timestamp'].iloc[-1]}\n")

    # Run baseline strategy
    strategy = MOODENGRSIStrategy(
        rsi_entry=55,
        body_thresh=0.5,
        sl_mult=1.0,
        tp_mult=4.0,
        max_bars=60
    )

    trades = strategy.backtest(df)
    results = strategy.analyze_results(trades, fee_pct=0.10)
    strategy.print_results(results)

    # Save trades
    if trades:
        df_trades = pd.DataFrame(trades)
        output_path = '/workspaces/Carebiuro_windykacja/trading/results/moodeng_rsi_bingx_trades.csv'
        df_trades.to_csv(output_path, index=False)
        print(f"\n✅ Trades saved to: {output_path}")


if __name__ == "__main__":
    main()
