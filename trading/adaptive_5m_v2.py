"""
FARTCOIN Adaptive Trading Strategy V2 - 5-Minute Data
======================================================

Improved adaptive system with:
1. More realistic regime detection (not overly conservative)
2. Balanced filtering (quality over quantity, but not extreme)
3. Multiple proven strategies
4. Dynamic position sizing
5. Better risk management

Key Philosophy:
- Trade when conditions are favorable, not just perfect
- Use multiple strategies to capture different opportunities
- Adapt position size to confidence level
- Exit quickly when conditions deteriorate
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Tuple
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')


def calculate_indicators(df):
    """Calculate all technical indicators"""
    data = df.copy()

    # EMAs
    for period in [5, 10, 20, 50, 100, 200]:
        data[f'ema_{period}'] = data['close'].ewm(span=period, adjust=False).mean()

    # RSI
    delta = data['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    data['rsi'] = 100 - (100 / (1 + rs))

    # Bollinger Bands
    data['bb_middle'] = data['close'].rolling(20).mean()
    bb_std = data['close'].rolling(20).std()
    data['bb_upper'] = data['bb_middle'] + (2 * bb_std)
    data['bb_lower'] = data['bb_middle'] - (2 * bb_std)

    # ATR
    high_low = data['high'] - data['low']
    high_close = (data['high'] - data['close'].shift()).abs()
    low_close = (data['low'] - data['close'].shift()).abs()
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    data['atr'] = true_range.rolling(14).mean()

    # Volume MA
    data['volume_ma'] = data['volume'].rolling(50).mean()

    # Price ROC (Rate of Change)
    data['roc_5'] = data['close'].pct_change(5) * 100
    data['roc_20'] = data['close'].pct_change(20) * 100

    return data


class RegimeDetector:
    """Practical regime detection - identifies truly bad vs tradeable conditions"""

    def detect(self, data):
        """Classify market into: GOOD, NEUTRAL, BAD"""

        # Trend indicators
        ema_alignment_bull = (data['ema_20'] > data['ema_50']) & (data['ema_50'] > data['ema_100'])
        ema_alignment_bear = (data['ema_20'] < data['ema_50']) & (data['ema_50'] < data['ema_100'])
        has_trend = ema_alignment_bull | ema_alignment_bear

        # Volatility (normalized)
        atr_pct = (data['atr'] / data['close']) * 100
        atr_ma = atr_pct.rolling(100).mean()
        vol_normal = (atr_pct > atr_ma * 0.3) & (atr_pct < atr_ma * 2.5)

        # Volume
        vol_adequate = data['volume'] > data['volume_ma'] * 0.3

        # Price action quality (not whipsawing)
        price_crosses_ema20 = (
            (data['close'] > data['ema_20']) !=
            (data['close'].shift(1) > data['ema_20'].shift(1))
        ).rolling(20).sum()
        not_whipsaw = price_crosses_ema20 < 10

        # Regime classification
        regime = pd.Series('NEUTRAL', index=data.index)

        # GOOD: Has trend, normal vol, adequate volume, not whipsawing
        good_conditions = has_trend & vol_normal & vol_adequate & not_whipsaw
        regime[good_conditions] = 'GOOD'

        # BAD: Whipsawing OR extreme vol OR very low volume
        bad_conditions = (~not_whipsaw) | (~vol_normal) | (~vol_adequate)
        regime[bad_conditions] = 'BAD'

        return regime


class MultiStrategySystem:
    """
    Combines multiple strategies:
    1. EMA Pullback (trend following)
    2. Bollinger Bounce (mean reversion)
    3. Momentum Breakout (momentum)
    4. RSI Extremes (contrarian)
    """

    def __init__(self, data):
        self.data = calculate_indicators(data)
        self.regime = RegimeDetector().detect(self.data)

    def strategy_ema_pullback_long(self):
        """Buy pullbacks in uptrend"""
        signals = pd.DataFrame(index=self.data.index)
        signals['entry'] = 0
        signals['sl'] = np.nan
        signals['tp'] = np.nan
        signals['confidence'] = 0.0

        # Conditions
        uptrend = (self.data['ema_20'] > self.data['ema_50'])
        pullback = (self.data['close'] < self.data['ema_20']) & (self.data['close'] > self.data['ema_50'])
        rsi_ok = (self.data['rsi'] > 35) & (self.data['rsi'] < 65)
        bullish_candle = self.data['close'] > self.data['open']

        entry = uptrend & pullback & rsi_ok & bullish_candle

        signals.loc[entry, 'entry'] = 1
        signals.loc[entry, 'sl'] = self.data['ema_50'] * 0.995
        signals.loc[entry, 'tp'] = self.data['close'] * 1.015
        signals.loc[entry, 'confidence'] = 0.7

        return signals

    def strategy_ema_pullback_short(self):
        """Sell bounces in downtrend"""
        signals = pd.DataFrame(index=self.data.index)
        signals['entry'] = 0
        signals['sl'] = np.nan
        signals['tp'] = np.nan
        signals['confidence'] = 0.0

        downtrend = (self.data['ema_20'] < self.data['ema_50'])
        bounce = (self.data['close'] > self.data['ema_20']) & (self.data['close'] < self.data['ema_50'])
        rsi_ok = (self.data['rsi'] > 35) & (self.data['rsi'] < 65)
        bearish_candle = self.data['close'] < self.data['open']

        entry = downtrend & bounce & rsi_ok & bearish_candle

        signals.loc[entry, 'entry'] = -1
        signals.loc[entry, 'sl'] = self.data['ema_50'] * 1.005
        signals.loc[entry, 'tp'] = self.data['close'] * 0.985
        signals.loc[entry, 'confidence'] = 0.7

        return signals

    def strategy_bb_bounce_long(self):
        """Buy bounces from lower BB"""
        signals = pd.DataFrame(index=self.data.index)
        signals['entry'] = 0
        signals['sl'] = np.nan
        signals['tp'] = np.nan
        signals['confidence'] = 0.0

        touched_lower = self.data['low'] <= self.data['bb_lower'] * 1.003
        bouncing = self.data['close'] > self.data['open']
        rsi_oversold = self.data['rsi'] < 35

        entry = touched_lower & bouncing & rsi_oversold

        signals.loc[entry, 'entry'] = 1
        signals.loc[entry, 'sl'] = self.data['bb_lower'] * 0.993
        signals.loc[entry, 'tp'] = self.data['bb_middle']
        signals.loc[entry, 'confidence'] = 0.8

        return signals

    def strategy_bb_bounce_short(self):
        """Sell rejections from upper BB"""
        signals = pd.DataFrame(index=self.data.index)
        signals['entry'] = 0
        signals['sl'] = np.nan
        signals['tp'] = np.nan
        signals['confidence'] = 0.0

        touched_upper = self.data['high'] >= self.data['bb_upper'] * 0.997
        rejecting = self.data['close'] < self.data['open']
        rsi_overbought = self.data['rsi'] > 65

        entry = touched_upper & rejecting & rsi_overbought

        signals.loc[entry, 'entry'] = -1
        signals.loc[entry, 'sl'] = self.data['bb_upper'] * 1.007
        signals.loc[entry, 'tp'] = self.data['bb_middle']
        signals.loc[entry, 'confidence'] = 0.8

        return signals

    def strategy_momentum_long(self):
        """Buy strong momentum with volume"""
        signals = pd.DataFrame(index=self.data.index)
        signals['entry'] = 0
        signals['sl'] = np.nan
        signals['tp'] = np.nan
        signals['confidence'] = 0.0

        strong_move = self.data['roc_5'] > 1.5  # 1.5% move in 5 candles
        volume_spike = self.data['volume'] > self.data['volume_ma'] * 1.5
        rsi_momentum = (self.data['rsi'] > 55) & (self.data['rsi'] < 80)
        above_ema = self.data['close'] > self.data['ema_20']

        entry = strong_move & volume_spike & rsi_momentum & above_ema

        signals.loc[entry, 'entry'] = 1
        signals.loc[entry, 'sl'] = self.data['close'] * 0.992
        signals.loc[entry, 'tp'] = self.data['close'] * 1.018
        signals.loc[entry, 'confidence'] = 0.6

        return signals

    def strategy_rsi_extreme_long(self):
        """Buy extreme RSI oversold with reversal"""
        signals = pd.DataFrame(index=self.data.index)
        signals['entry'] = 0
        signals['sl'] = np.nan
        signals['tp'] = np.nan
        signals['confidence'] = 0.0

        rsi_extreme = self.data['rsi'] < 25
        rsi_turning = self.data['rsi'] > self.data['rsi'].shift(1)
        bullish_candle = self.data['close'] > self.data['open']

        entry = rsi_extreme & rsi_turning & bullish_candle

        signals.loc[entry, 'entry'] = 1
        signals.loc[entry, 'sl'] = self.data['close'] * 0.985
        signals.loc[entry, 'tp'] = self.data['close'] * 1.025
        signals.loc[entry, 'confidence'] = 0.75

        return signals

    def strategy_rsi_extreme_short(self):
        """Sell extreme RSI overbought with reversal"""
        signals = pd.DataFrame(index=self.data.index)
        signals['entry'] = 0
        signals['sl'] = np.nan
        signals['tp'] = np.nan
        signals['confidence'] = 0.0

        rsi_extreme = self.data['rsi'] > 75
        rsi_turning = self.data['rsi'] < self.data['rsi'].shift(1)
        bearish_candle = self.data['close'] < self.data['open']

        entry = rsi_extreme & rsi_turning & bearish_candle

        signals.loc[entry, 'entry'] = -1
        signals.loc[entry, 'sl'] = self.data['close'] * 1.015
        signals.loc[entry, 'tp'] = self.data['close'] * 0.975
        signals.loc[entry, 'confidence'] = 0.75

        return signals

    def combine_strategies(self):
        """Combine all strategies with regime filtering"""

        all_strategies = [
            ('EMA_PB_LONG', self.strategy_ema_pullback_long()),
            ('EMA_PB_SHORT', self.strategy_ema_pullback_short()),
            ('BB_BOUNCE_LONG', self.strategy_bb_bounce_long()),
            ('BB_BOUNCE_SHORT', self.strategy_bb_bounce_short()),
            ('MOMENTUM_LONG', self.strategy_momentum_long()),
            ('RSI_EXT_LONG', self.strategy_rsi_extreme_long()),
            ('RSI_EXT_SHORT', self.strategy_rsi_extreme_short()),
        ]

        # Initialize combined signals
        combined = pd.DataFrame(index=self.data.index)
        combined['entry'] = 0
        combined['sl'] = np.nan
        combined['tp'] = np.nan
        combined['confidence'] = 0.0
        combined['strategy'] = 'NONE'

        # For each row, take the highest confidence signal
        for name, signals in all_strategies:
            mask = signals['entry'] != 0

            # Only take this signal if it's higher confidence than current
            better = (signals['confidence'] > combined['confidence']) & mask

            combined.loc[better, 'entry'] = signals.loc[better, 'entry']
            combined.loc[better, 'sl'] = signals.loc[better, 'sl']
            combined.loc[better, 'tp'] = signals.loc[better, 'tp']
            combined.loc[better, 'confidence'] = signals.loc[better, 'confidence']
            combined.loc[better, 'strategy'] = name

        # Apply regime filter - only trade in GOOD or NEUTRAL regimes
        bad_regime = self.regime == 'BAD'
        combined.loc[bad_regime, 'entry'] = 0
        combined.loc[bad_regime, 'strategy'] = 'FILTERED_BAD_REGIME'

        return combined

    def backtest(self, initial_capital=10000):
        """Run backtest with dynamic position sizing"""

        signals = self.combine_strategies()

        capital = initial_capital
        position = None
        trades = []
        equity_curve = []

        consecutive_losses = 0
        recent_trades = []  # Track last 20 trades

        for idx in range(len(self.data)):
            row = self.data.iloc[idx]
            signal = signals.iloc[idx]

            # Record equity
            if position is None:
                equity_curve.append({
                    'timestamp': row['timestamp'],
                    'equity': capital,
                    'regime': self.regime.iloc[idx]
                })

            # Manage existing position
            if position is not None:
                exit_triggered = False
                exit_price = None
                exit_reason = None

                # Check stop loss
                if position['direction'] == 'LONG':
                    if row['low'] <= position['sl']:
                        exit_triggered = True
                        exit_price = position['sl']
                        exit_reason = 'STOP_LOSS'
                else:  # SHORT
                    if row['high'] >= position['sl']:
                        exit_triggered = True
                        exit_price = position['sl']
                        exit_reason = 'STOP_LOSS'

                # Check take profit
                if not exit_triggered:
                    if position['direction'] == 'LONG':
                        if row['high'] >= position['tp']:
                            exit_triggered = True
                            exit_price = position['tp']
                            exit_reason = 'TAKE_PROFIT'
                    else:  # SHORT
                        if row['low'] <= position['tp']:
                            exit_triggered = True
                            exit_price = position['tp']
                            exit_reason = 'TAKE_PROFIT'

                # Time exit (max 60 candles = 5 hours)
                if not exit_triggered and (idx - position['entry_idx']) >= 60:
                    exit_triggered = True
                    exit_price = row['close']
                    exit_reason = 'TIME_EXIT'

                # Regime change exit
                if not exit_triggered and self.regime.iloc[idx] == 'BAD':
                    exit_triggered = True
                    exit_price = row['close']
                    exit_reason = 'REGIME_CHANGE'

                if exit_triggered:
                    # Calculate P&L
                    if position['direction'] == 'LONG':
                        pnl_pct = (exit_price - position['entry_price']) / position['entry_price']
                    else:
                        pnl_pct = (position['entry_price'] - exit_price) / position['entry_price']

                    pnl_usd = capital * pnl_pct * position['position_size']
                    capital += pnl_usd

                    # Record trade
                    trade = {
                        'entry_time': position['entry_time'],
                        'exit_time': row['timestamp'],
                        'direction': position['direction'],
                        'entry_price': position['entry_price'],
                        'exit_price': exit_price,
                        'pnl_pct': pnl_pct * 100,
                        'pnl_usd': pnl_usd,
                        'exit_reason': exit_reason,
                        'strategy': position['strategy'],
                        'regime': position['regime']
                    }
                    trades.append(trade)
                    recent_trades.append(1 if pnl_usd > 0 else 0)
                    if len(recent_trades) > 20:
                        recent_trades.pop(0)

                    if pnl_usd < 0:
                        consecutive_losses += 1
                    else:
                        consecutive_losses = 0

                    position = None

            # Entry management
            if position is None and signal['entry'] != 0:
                # Risk management filters

                # Filter 1: Don't trade after 7 consecutive losses
                if consecutive_losses >= 7:
                    continue

                # Filter 2: Don't trade if recent win rate < 25% (with at least 10 trades)
                if len(recent_trades) >= 10:
                    recent_wr = sum(recent_trades) / len(recent_trades)
                    if recent_wr < 0.25:
                        continue

                # Filter 3: Don't trade if drawdown > 25%
                if (capital - initial_capital) / initial_capital < -0.25:
                    continue

                # Dynamic position sizing based on confidence
                base_size = 0.10  # 10% base position
                confidence_multiplier = signal['confidence']
                position_size = base_size * confidence_multiplier

                # Reduce size after losses
                if consecutive_losses > 0:
                    position_size *= (0.8 ** consecutive_losses)

                # Increase size on winning streak
                if len(recent_trades) >= 5 and sum(recent_trades[-5:]) == 5:
                    position_size *= 1.3

                # Cap at 15%
                position_size = min(position_size, 0.15)

                position = {
                    'entry_time': row['timestamp'],
                    'entry_idx': idx,
                    'entry_price': row['close'],
                    'sl': signal['sl'],
                    'tp': signal['tp'],
                    'direction': 'LONG' if signal['entry'] == 1 else 'SHORT',
                    'position_size': position_size,
                    'strategy': signal['strategy'],
                    'regime': self.regime.iloc[idx]
                }

        # Convert to DataFrames
        trades_df = pd.DataFrame(trades)
        equity_df = pd.DataFrame(equity_curve)

        # Calculate metrics
        if len(trades_df) > 0:
            total_return = (capital - initial_capital) / initial_capital * 100
            win_trades = trades_df[trades_df['pnl_pct'] > 0]
            win_rate = len(win_trades) / len(trades_df) * 100

            avg_win = win_trades['pnl_pct'].mean() if len(win_trades) > 0 else 0
            losing_trades = trades_df[trades_df['pnl_pct'] < 0]
            avg_loss = losing_trades['pnl_pct'].mean() if len(losing_trades) > 0 else 0

            # Max drawdown
            equity_df['running_max'] = equity_df['equity'].expanding().max()
            equity_df['drawdown'] = (equity_df['equity'] - equity_df['running_max']) / equity_df['running_max'] * 100
            max_dd = equity_df['drawdown'].min()

            # Sharpe
            if len(trades_df) > 1:
                returns = trades_df['pnl_pct'].values / 100
                sharpe = (np.mean(returns) / np.std(returns)) * np.sqrt(252) if np.std(returns) > 0 else 0
            else:
                sharpe = 0

            # Profit factor
            total_wins = win_trades['pnl_pct'].sum()
            total_losses = abs(losing_trades['pnl_pct'].sum())
            profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')

            metrics = {
                'total_return': total_return,
                'final_capital': capital,
                'total_trades': len(trades_df),
                'win_rate': win_rate,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'max_drawdown': max_dd,
                'sharpe_ratio': sharpe,
                'profit_factor': profit_factor
            }
        else:
            metrics = {
                'total_return': 0,
                'final_capital': initial_capital,
                'total_trades': 0,
                'win_rate': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0,
                'profit_factor': 0
            }

        return trades_df, equity_df, metrics, signals


def main():
    print("=" * 80)
    print("FARTCOIN ADAPTIVE STRATEGY V2 - 5-MINUTE DATA")
    print("=" * 80)

    # Load data
    print("\nLoading data...")
    data = pd.read_csv('fartcoin_5m_max.csv')
    data['timestamp'] = pd.to_datetime(data['timestamp'])

    print(f"Loaded {len(data)} candles")
    print(f"Period: {data['timestamp'].min()} to {data['timestamp'].max()}")
    print(f"Days: {(data['timestamp'].max() - data['timestamp'].min()).days}")

    # Run system
    print("\nInitializing system...")
    system = MultiStrategySystem(data)

    print("\nRegime distribution:")
    print(system.regime.value_counts())

    print("\nRunning backtest...")
    trades_df, equity_df, metrics, signals = system.backtest()

    # Print results
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(f"Total Return: {metrics['total_return']:.2f}%")
    print(f"Final Capital: ${metrics['final_capital']:.2f}")
    print(f"Total Trades: {metrics['total_trades']}")
    print(f"Win Rate: {metrics['win_rate']:.2f}%")
    print(f"Avg Win: {metrics['avg_win']:.2f}%")
    print(f"Avg Loss: {metrics['avg_loss']:.2f}%")
    print(f"Max Drawdown: {metrics['max_drawdown']:.2f}%")
    print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
    print(f"Profit Factor: {metrics['profit_factor']:.2f}")

    if len(trades_df) > 0:
        print("\n" + "=" * 80)
        print("STRATEGY BREAKDOWN")
        print("=" * 80)
        strat_perf = trades_df.groupby('strategy').agg({
            'pnl_pct': ['count', 'mean', lambda x: (x > 0).sum() / len(x) * 100]
        }).round(2)
        strat_perf.columns = ['Trades', 'Avg P&L %', 'Win Rate %']
        print(strat_perf)

        print("\n" + "=" * 80)
        print("REGIME BREAKDOWN")
        print("=" * 80)
        regime_perf = trades_df.groupby('regime').agg({
            'pnl_pct': ['count', 'mean', lambda x: (x > 0).sum() / len(x) * 100]
        }).round(2)
        regime_perf.columns = ['Trades', 'Avg P&L %', 'Win Rate %']
        print(regime_perf)

    # Save results
    print("\nSaving results...")
    trades_df.to_csv('./results/adaptive_5m_results.csv', index=False)

    # Create visualizations
    fig = plt.figure(figsize=(16, 12))

    # Equity curve
    ax1 = plt.subplot(4, 1, 1)
    ax1.plot(equity_df['timestamp'], equity_df['equity'], linewidth=2)
    ax1.set_title('Equity Curve', fontsize=14, fontweight='bold')
    ax1.set_ylabel('Capital ($)')
    ax1.grid(True, alpha=0.3)

    # Drawdown
    ax2 = plt.subplot(4, 1, 2)
    ax2.fill_between(equity_df['timestamp'], equity_df['drawdown'], 0, color='red', alpha=0.3)
    ax2.plot(equity_df['timestamp'], equity_df['drawdown'], color='red', linewidth=1)
    ax2.set_title('Drawdown', fontsize=14, fontweight='bold')
    ax2.set_ylabel('Drawdown %')
    ax2.grid(True, alpha=0.3)

    # Price with regime
    ax3 = plt.subplot(4, 1, 3)
    ax3.plot(system.data['timestamp'], system.data['close'], linewidth=1, color='black', alpha=0.6)

    # Color by regime
    good_mask = system.regime == 'GOOD'
    neutral_mask = system.regime == 'NEUTRAL'
    bad_mask = system.regime == 'BAD'

    ax3.scatter(system.data.loc[good_mask, 'timestamp'], system.data.loc[good_mask, 'close'],
                c='green', s=0.5, alpha=0.5, label='GOOD')
    ax3.scatter(system.data.loc[neutral_mask, 'timestamp'], system.data.loc[neutral_mask, 'close'],
                c='blue', s=0.5, alpha=0.5, label='NEUTRAL')
    ax3.scatter(system.data.loc[bad_mask, 'timestamp'], system.data.loc[bad_mask, 'close'],
                c='red', s=0.5, alpha=0.5, label='BAD')

    ax3.set_title('Price with Regime Detection', fontsize=14, fontweight='bold')
    ax3.set_ylabel('Price')
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    # Trade distribution
    ax4 = plt.subplot(4, 1, 4)
    if len(trades_df) > 0:
        # Plot trade entries
        long_trades = trades_df[trades_df['direction'] == 'LONG']
        short_trades = trades_df[trades_df['direction'] == 'SHORT']

        if len(long_trades) > 0:
            ax4.scatter(pd.to_datetime(long_trades['entry_time']),
                       long_trades['entry_price'],
                       c='green', marker='^', s=100, alpha=0.7, label='LONG')
        if len(short_trades) > 0:
            ax4.scatter(pd.to_datetime(short_trades['entry_time']),
                       short_trades['entry_price'],
                       c='red', marker='v', s=100, alpha=0.7, label='SHORT')

    ax4.plot(system.data['timestamp'], system.data['close'], linewidth=1, color='black', alpha=0.3)
    ax4.set_title('Trade Entries', fontsize=14, fontweight='bold')
    ax4.set_xlabel('Time')
    ax4.set_ylabel('Price')
    ax4.legend()
    ax4.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('./results/adaptive_5m_equity.png', dpi=150, bbox_inches='tight')
    print("✓ Saved to ./results/adaptive_5m_equity.png")

    # Create analysis document
    analysis = f"""# FARTCOIN Adaptive Strategy V2 - Analysis

## Performance Summary

**Period**: {data['timestamp'].min()} to {data['timestamp'].max()}
**Duration**: {(data['timestamp'].max() - data['timestamp'].min()).days} days
**Initial Capital**: $10,000
**Final Capital**: ${metrics['final_capital']:.2f}
**Total Return**: {metrics['total_return']:.2f}%
**Max Drawdown**: {metrics['max_drawdown']:.2f}%

## Key Metrics

- **Total Trades**: {metrics['total_trades']}
- **Win Rate**: {metrics['win_rate']:.2f}%
- **Average Win**: {metrics['avg_win']:.2f}%
- **Average Loss**: {metrics['avg_loss']:.2f}%
- **Profit Factor**: {metrics['profit_factor']:.2f}
- **Sharpe Ratio**: {metrics['sharpe_ratio']:.2f}

## Strategy Approach

This version uses a multi-strategy ensemble with:

1. **EMA Pullback** (Long/Short): Trend-following entries on pullbacks
2. **Bollinger Bounce** (Long/Short): Mean-reversion at bands
3. **Momentum Breakout**: Quick momentum scalps
4. **RSI Extremes** (Long/Short): Contrarian plays at extremes

Each strategy has a confidence score. The system selects the highest-confidence signal for each candle.

## Regime Detection

Simplified regime classification:
- **GOOD**: Trending, normal volatility, adequate volume, clean price action
- **NEUTRAL**: No clear trend but tradeable conditions
- **BAD**: Whipsawing, extreme volatility, or low volume

Trading is allowed in GOOD and NEUTRAL regimes only.

## Risk Management

- **Dynamic Position Sizing**: 10% base, scaled by strategy confidence (6-15%)
- **Drawdown Protection**: Trading halts if DD > 25%
- **Consecutive Loss Filter**: No trading after 7 straight losses
- **Win Rate Filter**: No trading if recent WR < 25% (min 10 trades)
- **Time Exits**: Max 60 candles (5 hours) per trade
- **Regime Change Exits**: Exit immediately if regime turns BAD

## Results by Strategy

"""

    if len(trades_df) > 0:
        strat_perf = trades_df.groupby('strategy').agg({
            'pnl_pct': ['count', 'mean', lambda x: (x > 0).sum() / len(x) * 100, 'sum']
        }).round(2)
        strat_perf.columns = ['Trades', 'Avg P&L %', 'Win Rate %', 'Total P&L %']
        analysis += "\n" + strat_perf.to_markdown() + "\n"

        analysis += "\n## Results by Regime\n\n"
        regime_perf = trades_df.groupby('regime').agg({
            'pnl_pct': ['count', 'mean', lambda x: (x > 0).sum() / len(x) * 100, 'sum']
        }).round(2)
        regime_perf.columns = ['Trades', 'Avg P&L %', 'Win Rate %', 'Total P&L %']
        analysis += regime_perf.to_markdown() + "\n"

    analysis += f"""

## Conclusions

{'✅ SUCCESS' if metrics['total_return'] > 50 else '⚠️ NEEDS IMPROVEMENT'} - Target was >50% return

The adaptive system {'successfully' if metrics['total_return'] > 50 else 'struggled to'} {'achieve' if metrics['total_return'] > 50 else 'reach'} profitable returns by:
- Combining multiple strategies for different market conditions
- Using regime detection to avoid bad trading environments
- Applying dynamic position sizing based on confidence
- Implementing strict risk management filters

**Regime Effectiveness**: {(system.regime == 'BAD').sum() / len(system.regime) * 100:.1f}% of candles filtered as BAD regime

## Files

- `./results/adaptive_5m_results.csv` - Trade details
- `./results/adaptive_5m_equity.png` - Visualizations
- `./results/adaptive_5m_analysis.md` - This document

---
*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

    with open('./results/adaptive_5m_analysis.md', 'w') as f:
        f.write(analysis)
    print("✓ Saved to ./results/adaptive_5m_analysis.md")

    print("\n" + "=" * 80)
    print("COMPLETE!")
    print("=" * 80)


if __name__ == '__main__':
    main()
