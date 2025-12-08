"""
Intelligent Adaptive Trading System for FARTCOIN/USDT
Learns from market archaeology findings and trades WITH the market conditions
"""

import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')


class RegimeDetector:
    """Detects current market regime based on multiple indicators"""

    def __init__(self):
        self.regime_history = []

    def detect_regime(self, df, idx):
        """
        Detect market regime at given index
        Returns: regime_name, confidence_score
        """
        if idx < 200:  # Need warmup
            return 'WARMUP', 0.0

        # Get recent data
        lookback = 96  # 24 hours of 15min bars
        recent = df.iloc[max(0, idx-lookback):idx+1].copy()

        if len(recent) < 20:
            return 'WARMUP', 0.0

        # Extract latest values
        close = df.iloc[idx]['close']
        ema20 = df.iloc[idx]['ema20']
        ema50 = df.iloc[idx]['ema50']
        ema200 = df.iloc[idx]['ema200']
        adx = df.iloc[idx]['adx']
        atr = df.iloc[idx]['atr']
        atr_pct = (atr / close) * 100

        # Trend direction
        uptrend = (close > ema50) and (ema20 > ema50)
        downtrend = (close < ema50) and (ema20 < ema50)

        # Volatility state
        atr_percentile = (recent['atr'] > atr).sum() / len(recent)
        high_vol = atr_percentile > 0.75
        low_vol = atr_percentile < 0.25

        # Trend strength
        strong_trend = adx > 30
        moderate_trend = 25 <= adx <= 30
        weak_trend = adx < 25

        # Chop detection (frequent crosses)
        crosses = (recent['ema20'] > recent['ema50']).astype(int).diff().abs().sum()
        choppy = crosses > 3  # More than 3 crosses in 24 hours

        # Price position relative to EMAs
        distance_ema20 = ((close - ema20) / ema20) * 100
        distance_ema50 = ((close - ema50) / ema50) * 100

        # Regime classification
        confidence = 0.5

        # 1. BULL_RUN: Strong uptrend with good structure
        if uptrend and (strong_trend or moderate_trend) and not choppy:
            confidence = 0.8 if strong_trend else 0.6
            return 'BULL_RUN', confidence

        # 2. BEAR_TREND: Clear downtrend
        if downtrend and (strong_trend or moderate_trend) and not choppy:
            confidence = 0.8 if strong_trend else 0.6
            return 'BEAR_TREND', confidence

        # 3. HIGH_VOL_BULL: Bullish but volatile/unstable
        if uptrend and high_vol:
            return 'HIGH_VOL_BULL', 0.6

        # 4. HIGH_VOL_BEAR: Bearish and volatile
        if downtrend and high_vol:
            return 'HIGH_VOL_BEAR', 0.6

        # 5. CHOP_ZONE: No clear direction, frequent reversals
        if choppy or weak_trend:
            return 'CHOP_ZONE', 0.7

        # 6. TRANSITION: Between regimes, unclear
        return 'TRANSITION', 0.4


class StrategyPlaybook:
    """Defines exact trading rules for each regime"""

    def __init__(self):
        self.fees = 0.001  # 0.1% per trade

    def get_strategy(self, regime, confidence):
        """
        Return strategy parameters for given regime
        Returns: {
            'trade_type': 'LONG', 'SHORT', or 'CASH',
            'position_size': 0-1 (fraction of capital),
            'leverage': 1-10,
            'stop_loss_pct': percentage,
            'take_profit_pct': percentage,
            'entry_logic': function
        }
        """

        # Default: CASH (sit out)
        if confidence < 0.5:
            return self._cash_strategy()

        if regime == 'BULL_RUN':
            return self._bull_run_strategy(confidence)
        elif regime == 'BEAR_TREND':
            return self._bear_trend_strategy(confidence)
        elif regime == 'HIGH_VOL_BULL':
            return self._high_vol_bull_strategy(confidence)
        elif regime == 'HIGH_VOL_BEAR':
            return self._high_vol_bear_strategy(confidence)
        elif regime == 'CHOP_ZONE':
            return self._chop_zone_strategy(confidence)
        else:  # TRANSITION, WARMUP
            return self._cash_strategy()

    def _cash_strategy(self):
        """Sit out - no trades"""
        return {
            'trade_type': 'CASH',
            'position_size': 0,
            'leverage': 1,
            'stop_loss_pct': 0,
            'take_profit_pct': 0
        }

    def _bull_run_strategy(self, confidence):
        """
        BULL_RUN: Buy pullbacks to EMA20 in uptrend
        Based on July 2025 success (+556% with trend following longs)
        CONSERVATIVE: Lower leverage, better risk management
        """
        return {
            'trade_type': 'LONG',
            'position_size': 0.1,  # Only risk 10% per trade
            'leverage': 3,  # Much lower leverage
            'stop_loss_pct': 3.0,  # Wider stop for volatility
            'take_profit_pct': 6.0,  # 2:1 R:R
            'entry_signal': 'pullback_to_ema20'
        }

    def _bear_trend_strategy(self, confidence):
        """
        BEAR_TREND: Sell rallies to EMA20 in downtrend
        Based on February & May 2025 (shorts worked better)
        CONSERVATIVE: Lower risk
        """
        return {
            'trade_type': 'SHORT',
            'position_size': 0.1,  # 10% risk
            'leverage': 3,  # Lower leverage
            'stop_loss_pct': 3.0,
            'take_profit_pct': 6.0,
            'entry_signal': 'rally_to_ema20'
        }

    def _high_vol_bull_strategy(self, confidence):
        """
        HIGH_VOL_BULL: Bullish but unstable - sit out mostly
        High vol periods are dangerous, archaeology showed losses
        """
        return self._cash_strategy()  # Sit out high vol

    def _high_vol_bear_strategy(self, confidence):
        """
        HIGH_VOL_BEAR: Bearish and volatile - sit out
        """
        return self._cash_strategy()  # Sit out high vol

    def _chop_zone_strategy(self, confidence):
        """
        CHOP_ZONE: No clear edge - sit out
        Most months showed losses, so we avoid trading chop
        """
        return self._cash_strategy()


class IntelligentTradingSystem:
    """Main trading system that combines regime detection and strategy execution"""

    def __init__(self, csv_path, initial_capital=10000):
        print("Initializing Intelligent Trading System...")
        self.df = pd.read_csv(csv_path)
        self.df['timestamp'] = pd.to_datetime(self.df['timestamp'])
        self.df = self.df.sort_values('timestamp').reset_index(drop=True)

        self.initial_capital = initial_capital
        self.capital = initial_capital

        # Calculate indicators
        self._calculate_indicators()

        # Initialize components
        self.regime_detector = RegimeDetector()
        self.playbook = StrategyPlaybook()

        # Tracking
        self.trades = []
        self.equity_curve = []
        self.regime_log = []

        print(f"Loaded {len(self.df)} candles from {self.df['timestamp'].min()} to {self.df['timestamp'].max()}")

    def _calculate_indicators(self):
        """Calculate all technical indicators"""
        # EMAs
        self.df['ema20'] = self.df['close'].ewm(span=20, adjust=False).mean()
        self.df['ema50'] = self.df['close'].ewm(span=50, adjust=False).mean()
        self.df['ema200'] = self.df['close'].ewm(span=200, adjust=False).mean()

        # ATR
        high_low = self.df['high'] - self.df['low']
        high_close = np.abs(self.df['high'] - self.df['close'].shift())
        low_close = np.abs(self.df['low'] - self.df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        self.df['atr'] = true_range.rolling(window=14).mean()

        # ADX
        plus_dm = self.df['high'].diff()
        minus_dm = -self.df['low'].diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0

        tr_smooth = true_range.rolling(window=14).sum()
        plus_di = 100 * (plus_dm.rolling(window=14).sum() / tr_smooth)
        minus_di = 100 * (minus_dm.rolling(window=14).sum() / tr_smooth)

        dx = (np.abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
        self.df['adx'] = dx.rolling(window=14).mean()

    def _check_entry_signal(self, idx, strategy):
        """Check if entry conditions are met"""
        if strategy['trade_type'] == 'CASH':
            return False

        signal_type = strategy.get('entry_signal', '')
        close = self.df.iloc[idx]['close']
        ema20 = self.df.iloc[idx]['ema20']
        ema50 = self.df.iloc[idx]['ema50']

        # Avoid entering if already in a trade
        if hasattr(self, 'open_trade') and self.open_trade is not None:
            return False

        if signal_type == 'pullback_to_ema20':
            # Long: Price pulls back to/near EMA20, and EMA20 > EMA50
            if (ema20 > ema50 and
                close <= ema20 * 1.005 and  # Within 0.5% of EMA20
                close > ema20 * 0.995):  # Not too far below
                return True

        elif signal_type == 'rally_to_ema20':
            # Short: Price rallies to/near EMA20, and EMA20 < EMA50
            if (ema20 < ema50 and
                close >= ema20 * 0.995 and  # Within 0.5% of EMA20
                close < ema20 * 1.005):  # Not too far above
                return True

        return False

    def run_backtest(self):
        """Run the intelligent adaptive backtest"""
        print("\nStarting intelligent backtest...")

        self.open_trade = None
        trade_id = 0

        for idx in range(200, len(self.df)):  # Skip warmup
            row = self.df.iloc[idx]

            # Detect current regime
            regime, confidence = self.regime_detector.detect_regime(self.df, idx)

            # Get strategy for this regime
            strategy = self.playbook.get_strategy(regime, confidence)

            # Log regime
            self.regime_log.append({
                'timestamp': row['timestamp'],
                'regime': regime,
                'confidence': confidence,
                'strategy': strategy['trade_type']
            })

            # Manage existing trade
            if self.open_trade is not None:
                trade = self.open_trade
                entry_price = trade['entry_price']
                direction = trade['direction']

                # Check stop loss and take profit
                if direction == 'LONG':
                    pct_change = ((row['high'] - entry_price) / entry_price) * 100
                    loss_check = ((row['low'] - entry_price) / entry_price) * 100

                    # Hit stop loss?
                    if loss_check <= -trade['stop_loss_pct']:
                        exit_price = entry_price * (1 - trade['stop_loss_pct'] / 100)
                        pnl_pct = -trade['stop_loss_pct']
                        exit_reason = 'STOP_LOSS'
                    # Hit take profit?
                    elif pct_change >= trade['take_profit_pct']:
                        exit_price = entry_price * (1 + trade['take_profit_pct'] / 100)
                        pnl_pct = trade['take_profit_pct']
                        exit_reason = 'TAKE_PROFIT'
                    else:
                        exit_price = None
                        pnl_pct = None
                        exit_reason = None

                else:  # SHORT
                    pct_change = ((entry_price - row['low']) / entry_price) * 100
                    loss_check = ((entry_price - row['high']) / entry_price) * 100

                    # Hit stop loss?
                    if loss_check <= -trade['stop_loss_pct']:
                        exit_price = entry_price * (1 + trade['stop_loss_pct'] / 100)
                        pnl_pct = -trade['stop_loss_pct']
                        exit_reason = 'STOP_LOSS'
                    # Hit take profit?
                    elif pct_change >= trade['take_profit_pct']:
                        exit_price = entry_price * (1 - trade['take_profit_pct'] / 100)
                        pnl_pct = trade['take_profit_pct']
                        exit_reason = 'TAKE_PROFIT'
                    else:
                        exit_price = None
                        pnl_pct = None
                        exit_reason = None

                # Close trade if exit triggered
                if exit_price is not None:
                    # Apply leverage to P&L
                    leveraged_pnl = pnl_pct * trade['leverage']
                    fees_total = 0.2  # 0.1% entry + 0.1% exit = 0.2% total
                    net_pnl = leveraged_pnl - fees_total

                    # Update capital - only risk position_size portion
                    risk_amount = trade['capital_before'] * trade['position_size']
                    pnl_dollars = risk_amount * (net_pnl / 100)
                    self.capital = trade['capital_before'] + pnl_dollars

                    # Prevent going negative
                    if self.capital < 0:
                        self.capital = 0

                    # Record trade
                    trade['exit_timestamp'] = row['timestamp']
                    trade['exit_price'] = exit_price
                    trade['pnl_pct'] = pnl_pct
                    trade['leveraged_pnl'] = leveraged_pnl
                    trade['net_pnl'] = net_pnl
                    trade['pnl_dollars'] = pnl_dollars
                    trade['exit_reason'] = exit_reason
                    trade['capital_after'] = self.capital

                    self.trades.append(trade)
                    self.open_trade = None

            # Check for new entry (only if we have capital left)
            if self.open_trade is None and self.capital > self.initial_capital * 0.1:  # Stop if below 10%
                if self._check_entry_signal(idx, strategy):
                    trade_id += 1
                    self.open_trade = {
                        'trade_id': trade_id,
                        'entry_timestamp': row['timestamp'],
                        'entry_price': row['close'],
                        'direction': strategy['trade_type'],
                        'position_size': strategy['position_size'],
                        'leverage': strategy['leverage'],
                        'stop_loss_pct': strategy['stop_loss_pct'],
                        'take_profit_pct': strategy['take_profit_pct'],
                        'regime': regime,
                        'confidence': confidence,
                        'capital_before': self.capital
                    }

            # Record equity
            self.equity_curve.append({
                'timestamp': row['timestamp'],
                'capital': self.capital,
                'regime': regime
            })

            # Progress
            if idx % 5000 == 0:
                progress = (idx / len(self.df)) * 100
                print(f"Progress: {progress:.1f}% | Capital: ${self.capital:,.2f} | Trades: {len(self.trades)}")

        print(f"\nBacktest complete! Final capital: ${self.capital:,.2f}")
        return self.trades, self.equity_curve, self.regime_log

    def generate_results(self):
        """Generate comprehensive results"""
        if not self.trades:
            print("No trades executed!")
            return

        trades_df = pd.DataFrame(self.trades)
        equity_df = pd.DataFrame(self.equity_curve)
        regime_df = pd.DataFrame(self.regime_log)

        # Overall metrics
        total_return = ((self.capital - self.initial_capital) / self.initial_capital) * 100
        num_trades = len(trades_df)
        winning_trades = (trades_df['net_pnl'] > 0).sum()
        losing_trades = (trades_df['net_pnl'] <= 0).sum()
        win_rate = (winning_trades / num_trades) * 100 if num_trades > 0 else 0

        avg_win = trades_df[trades_df['net_pnl'] > 0]['net_pnl'].mean() if winning_trades > 0 else 0
        avg_loss = trades_df[trades_df['net_pnl'] <= 0]['net_pnl'].mean() if losing_trades > 0 else 0

        # Drawdown
        equity_df['peak'] = equity_df['capital'].cummax()
        equity_df['drawdown'] = ((equity_df['capital'] - equity_df['peak']) / equity_df['peak']) * 100
        max_drawdown = equity_df['drawdown'].min()

        # By regime
        regime_stats = trades_df.groupby('regime').agg({
            'trade_id': 'count',
            'net_pnl': ['mean', 'sum'],
        }).round(2)

        print("\n" + "="*80)
        print("INTELLIGENT TRADING SYSTEM RESULTS")
        print("="*80)
        print(f"\nInitial Capital: ${self.initial_capital:,.2f}")
        print(f"Final Capital:   ${self.capital:,.2f}")
        print(f"Total Return:    {total_return:+.2f}%")
        print(f"Max Drawdown:    {max_drawdown:.2f}%")
        print(f"\nTotal Trades:    {num_trades}")
        print(f"Win Rate:        {win_rate:.1f}%")
        print(f"Avg Win:         {avg_win:+.2f}%")
        print(f"Avg Loss:        {avg_loss:+.2f}%")
        print(f"\nBy Regime:")
        print(regime_stats)

        # Save results
        trades_df.to_csv('/workspaces/Carebiuro_windykacja/trading/results/intelligent_backtest.csv', index=False)
        equity_df.to_csv('/workspaces/Carebiuro_windykacja/trading/results/intelligent_equity.csv', index=False)
        regime_df.to_csv('/workspaces/Carebiuro_windykacja/trading/results/regime_log.csv', index=False)

        # Regime performance
        regime_performance = trades_df.groupby('regime').agg({
            'trade_id': 'count',
            'net_pnl': ['mean', 'sum', 'std'],
            'pnl_dollars': 'sum'
        }).round(2)
        regime_performance.columns = ['Trades', 'Avg_PnL_%', 'Total_PnL_%', 'Std_PnL_%', 'PnL_Dollars']
        regime_performance['Win_Rate'] = trades_df.groupby('regime').apply(
            lambda x: (x['net_pnl'] > 0).sum() / len(x) * 100
        ).round(1)

        regime_performance.to_csv('/workspaces/Carebiuro_windykacja/trading/results/regime_performance.csv')

        print("\nResults saved to trading/results/")

        return {
            'total_return': total_return,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'num_trades': num_trades
        }


def main():
    csv_path = '/workspaces/Carebiuro_windykacja/trading/fartcoin_bingx_15m.csv'

    # Initialize and run
    system = IntelligentTradingSystem(csv_path, initial_capital=10000)
    trades, equity, regimes = system.run_backtest()
    results = system.generate_results()

    return system, results


if __name__ == '__main__':
    system, results = main()
