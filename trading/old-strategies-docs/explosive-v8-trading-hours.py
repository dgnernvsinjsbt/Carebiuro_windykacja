#!/usr/bin/env python3
"""
V8: Trading Hours Optimization
Test if restricting to specific trading hours improves R:R ratio.

Key hypothesis: US market hours (14:30-21:00 UTC) may have:
- Higher liquidity
- Stronger trends
- Better follow-through
- Less fake-outs during low-volume hours

Scenarios to test:
1. US Market Hours (14:30-21:00 UTC / 9:30am-4pm ET)
2. Extended Hours (13:00-22:00 UTC / 8am-5pm ET)
3. Avoid Asian Hours (00:00-08:00 UTC)
4. Prime Hours Only (15:00-20:00 UTC / 10am-3pm ET)
5. Pre-Market + Market (12:00-21:00 UTC / 7am-4pm ET)
6. 24/7 (baseline from V7)
"""

import pandas as pd
import numpy as np
from datetime import datetime, time

class TradingHoursBacktest:
    def __init__(self, csv_path: str):
        print("Loading data...")
        self.df = pd.read_csv(csv_path)
        self.df['timestamp'] = pd.to_datetime(self.df['timestamp'])

        # Calculate indicators
        self.calculate_indicators()

        # Base config from V7 winner
        self.config = {
            'body_threshold': 1.0,
            'volume_multiplier': 2.5,
            'wick_threshold': 0.35,
            'require_strong_trend': True,
            'sma_distance_min': 2.0,
            'rsi_short_max': 55,
            'rsi_short_min': 25,
            'rsi_long_min': 45,
            'rsi_long_max': 75,
            'require_high_vol': True,
            'atr_percentile_min': 50,
            'stop_atr_mult': 3.0,
            'tp_atr_high_vol': 15.0,
            'base_risk_pct': 1.5,
            'max_risk_pct': 5.0,
            'win_streak_scaling': 0.5,
            'use_trailing_stop': True,
            'use_partial_exits': True,
            'max_hold_hours': 24,
            'trade_both_directions': True
        }

        self.balance = 10000.0
        self.trades = []

    def calculate_indicators(self):
        """Calculate all technical indicators"""
        # Body and wicks
        self.df['body'] = abs(self.df['close'] - self.df['open'])
        self.df['body_pct'] = (self.df['body'] / self.df['open']) * 100
        self.df['upper_wick'] = self.df['high'] - self.df[['open', 'close']].max(axis=1)
        self.df['lower_wick'] = self.df[['open', 'close']].min(axis=1) - self.df['low']
        self.df['is_bullish'] = self.df['close'] > self.df['open']
        self.df['is_bearish'] = self.df['close'] < self.df['open']

        # Volume
        self.df['vol_ma'] = self.df['volume'].rolling(20).mean()
        self.df['vol_ratio'] = self.df['volume'] / self.df['vol_ma']

        # SMAs
        self.df['sma_50'] = self.df['close'].rolling(50).mean()
        self.df['sma_200'] = self.df['close'].rolling(200).mean()
        self.df['uptrend'] = self.df['close'] > self.df['sma_50']
        self.df['downtrend'] = self.df['close'] < self.df['sma_50']

        # Distance from SMA
        self.df['distance_from_sma50_pct'] = abs(self.df['close'] - self.df['sma_50']) / self.df['sma_50'] * 100

        # RSI
        delta = self.df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        self.df['rsi'] = 100 - (100 / (1 + rs))

        # ATR
        high_low = self.df['high'] - self.df['low']
        high_close = abs(self.df['high'] - self.df['close'].shift())
        low_close = abs(self.df['low'] - self.df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        self.df['atr'] = tr.rolling(14).mean()

        # ATR percentile for volatility regime
        self.df['atr_percentile'] = self.df['atr'].rolling(100).apply(
            lambda x: (x.iloc[-1] > x).sum() / len(x) * 100 if len(x) > 0 else 50
        )
        self.df['high_vol'] = self.df['atr_percentile'] >= 50

        # Add hour of day (UTC)
        self.df['hour_utc'] = self.df['timestamp'].dt.hour

    def is_in_trading_window(self, timestamp, window_type):
        """Check if timestamp falls within specified trading window"""
        hour = timestamp.hour

        if window_type == '24/7':
            return True
        elif window_type == 'US_MARKET':  # 14:30-21:00 UTC (9:30am-4pm ET)
            return 14 <= hour < 21 or (hour == 14)  # Includes 14:30
        elif window_type == 'EXTENDED':  # 13:00-22:00 UTC (8am-5pm ET)
            return 13 <= hour < 22
        elif window_type == 'NO_ASIAN':  # Avoid 00:00-08:00 UTC
            return hour >= 8
        elif window_type == 'PRIME':  # 15:00-20:00 UTC (10am-3pm ET)
            return 15 <= hour < 20
        elif window_type == 'PRE_PLUS_MARKET':  # 12:00-21:00 UTC (7am-4pm ET)
            return 12 <= hour < 21
        elif window_type == 'EUROPEAN':  # 08:00-16:00 UTC
            return 8 <= hour < 16
        elif window_type == 'LONDON_SESSION':  # 08:00-17:00 UTC
            return 8 <= hour < 17
        elif window_type == 'US_ONLY_STRICT':  # 14:30-20:00 UTC (9:30am-3pm ET - main session)
            return 14 <= hour < 20 or (hour == 14)

        return True

    def detect_signal(self, idx: int):
        """Detect Explosive Bearish/Bullish patterns (V7 winner logic)"""
        if idx < 200:
            return None

        row = self.df.loc[idx]
        cfg = self.config

        # Calculate wick ratios
        body = row['body']
        if body == 0:
            return None

        wick_ratio_lower = row['lower_wick'] / body if body > 0 else 999
        wick_ratio_upper = row['upper_wick'] / body if body > 0 else 999

        # Base pattern checks
        body_ok = row['body_pct'] > cfg['body_threshold']
        volume_ok = row['vol_ratio'] > cfg['volume_multiplier']
        wicks_ok = (wick_ratio_lower < cfg['wick_threshold'] and
                   wick_ratio_upper < cfg['wick_threshold'])
        vol_ok = row['high_vol'] if cfg['require_high_vol'] else True

        if not (body_ok and volume_ok and wicks_ok and vol_ok):
            return None

        # Check trend filters
        strong_downtrend = (row['close'] < row['sma_50'] and
                           row['close'] < row['sma_200'])
        strong_uptrend = (row['close'] > row['sma_50'] and
                         row['close'] > row['sma_200'])

        # Distance filter
        distance_ok = row['distance_from_sma50_pct'] >= cfg['sma_distance_min']

        # Explosive Bearish Breakdown
        if (row['is_bearish'] and strong_downtrend and distance_ok and
            cfg['rsi_short_min'] < row['rsi'] < cfg['rsi_short_max']):
            return {
                'direction': 'short',
                'pattern': 'Explosive Bearish Breakdown',
                'entry_price': row['close'],
                'stop_loss': row['close'] + (cfg['stop_atr_mult'] * row['atr']),
                'take_profit': row['close'] - (cfg['tp_atr_high_vol'] * row['atr']),
                'timestamp': row['timestamp'],
                'atr': row['atr']
            }

        # Explosive Bullish Breakout
        if (row['is_bullish'] and strong_uptrend and distance_ok and
            cfg['rsi_long_min'] < row['rsi'] < cfg['rsi_long_max']):
            return {
                'direction': 'long',
                'pattern': 'Explosive Bullish Breakout',
                'entry_price': row['close'],
                'stop_loss': row['close'] - (cfg['stop_atr_mult'] * row['atr']),
                'take_profit': row['close'] + (cfg['tp_atr_high_vol'] * row['atr']),
                'timestamp': row['timestamp'],
                'atr': row['atr']
            }

        return None

    def run_backtest(self, window_type='24/7'):
        """Run backtest with specified trading hours window"""
        self.balance = 10000.0
        self.trades = []
        position = None
        win_streak = 0
        loss_streak = 0
        current_risk_pct = self.config['base_risk_pct']

        for idx in range(200, len(self.df)):
            row = self.df.loc[idx]

            # Manage existing position
            if position:
                hours_held = (row['timestamp'] - position['entry_time']).total_seconds() / 3600

                # Check exits
                exit_reason = None
                exit_price = None

                if position['direction'] == 'long':
                    if row['high'] >= position['take_profit']:
                        exit_price = position['take_profit']
                        exit_reason = 'TP Hit'
                    elif row['low'] <= position['stop_loss']:
                        exit_price = position['stop_loss']
                        exit_reason = 'SL Hit'
                    elif hours_held >= self.config['max_hold_hours']:
                        exit_price = row['close']
                        exit_reason = 'Time Stop'
                else:  # short
                    if row['low'] <= position['take_profit']:
                        exit_price = position['take_profit']
                        exit_reason = 'TP Hit'
                    elif row['high'] >= position['stop_loss']:
                        exit_price = position['stop_loss']
                        exit_reason = 'SL Hit'
                    elif hours_held >= self.config['max_hold_hours']:
                        exit_price = row['close']
                        exit_reason = 'Time Stop'

                if exit_reason:
                    # Calculate P&L
                    if position['direction'] == 'long':
                        pnl_pct = ((exit_price - position['entry_price']) / position['entry_price']) * 100
                    else:
                        pnl_pct = ((position['entry_price'] - exit_price) / position['entry_price']) * 100

                    pnl_dollar = (pnl_pct / 100) * position['position_size']
                    self.balance += pnl_dollar

                    # Update streaks
                    if pnl_pct > 0:
                        win_streak += 1
                        loss_streak = 0
                        current_risk_pct = min(
                            current_risk_pct + self.config['win_streak_scaling'],
                            self.config['max_risk_pct']
                        )
                    else:
                        loss_streak += 1
                        win_streak = 0
                        current_risk_pct = self.config['base_risk_pct']

                    # Record trade
                    self.trades.append({
                        'entry_time': position['entry_time'],
                        'exit_time': row['timestamp'],
                        'direction': position['direction'],
                        'pattern': position['pattern'],
                        'entry_price': position['entry_price'],
                        'exit_price': exit_price,
                        'stop_loss': position['stop_loss'],
                        'take_profit': position['take_profit'],
                        'exit_reason': exit_reason,
                        'pnl_pct': pnl_pct,
                        'pnl_dollar': pnl_dollar,
                        'balance': self.balance,
                        'hours_held': hours_held,
                        'risk_pct': position['risk_pct']
                    })

                    position = None

            # Look for new entry (only if no position and in trading window)
            if not position and self.is_in_trading_window(row['timestamp'], window_type):
                signal = self.detect_signal(idx)

                if signal:
                    # Calculate position size
                    entry_price = signal['entry_price']
                    stop_loss = signal['stop_loss']
                    risk_per_share = abs(entry_price - stop_loss)
                    risk_dollar = self.balance * (current_risk_pct / 100)
                    position_size = risk_dollar / (risk_per_share / entry_price)

                    position = {
                        'direction': signal['direction'],
                        'pattern': signal['pattern'],
                        'entry_price': entry_price,
                        'entry_time': row['timestamp'],
                        'stop_loss': stop_loss,
                        'take_profit': signal['take_profit'],
                        'position_size': position_size,
                        'risk_pct': current_risk_pct
                    }

        # Close any remaining position at end
        if position:
            row = self.df.iloc[-1]
            exit_price = row['close']

            if position['direction'] == 'long':
                pnl_pct = ((exit_price - position['entry_price']) / position['entry_price']) * 100
            else:
                pnl_pct = ((position['entry_price'] - exit_price) / position['entry_price']) * 100

            pnl_dollar = (pnl_pct / 100) * position['position_size']
            self.balance += pnl_dollar

            self.trades.append({
                'entry_time': position['entry_time'],
                'exit_time': row['timestamp'],
                'direction': position['direction'],
                'pattern': position['pattern'],
                'entry_price': position['entry_price'],
                'exit_price': exit_price,
                'stop_loss': position['stop_loss'],
                'take_profit': position['take_profit'],
                'exit_reason': 'End of Data',
                'pnl_pct': pnl_pct,
                'pnl_dollar': pnl_dollar,
                'balance': self.balance,
                'hours_held': 0,
                'risk_pct': position['risk_pct']
            })

        return self.calculate_metrics()

    def calculate_metrics(self):
        """Calculate performance metrics"""
        if not self.trades:
            return None

        df_trades = pd.DataFrame(self.trades)

        total_return_pct = ((self.balance - 10000) / 10000) * 100

        # Calculate drawdown
        df_trades['cumulative_pnl_pct'] = df_trades['pnl_pct'].cumsum()
        df_trades['running_peak'] = df_trades['cumulative_pnl_pct'].expanding().max()
        df_trades['drawdown'] = df_trades['cumulative_pnl_pct'] - df_trades['running_peak']
        max_drawdown_pct = abs(df_trades['drawdown'].min()) if len(df_trades) > 0 else 0

        # R:R ratio
        rr_ratio = total_return_pct / max_drawdown_pct if max_drawdown_pct > 0 else 0

        # Win rate
        wins = len(df_trades[df_trades['pnl_pct'] > 0])
        win_rate = (wins / len(df_trades)) * 100 if len(df_trades) > 0 else 0

        # Profit factor
        gross_profit = df_trades[df_trades['pnl_dollar'] > 0]['pnl_dollar'].sum()
        gross_loss = abs(df_trades[df_trades['pnl_dollar'] < 0]['pnl_dollar'].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

        return {
            'total_trades': len(df_trades),
            'return_pct': total_return_pct,
            'max_drawdown_pct': max_drawdown_pct,
            'rr_ratio': rr_ratio,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'final_balance': self.balance,
            'avg_win': df_trades[df_trades['pnl_pct'] > 0]['pnl_pct'].mean() if wins > 0 else 0,
            'avg_loss': df_trades[df_trades['pnl_pct'] < 0]['pnl_pct'].mean() if wins < len(df_trades) else 0
        }

def main():
    csv_path = '/workspaces/Carebiuro_windykacja/fartcoin_usdt_1m_lbank.csv'

    # Trading windows to test
    windows = [
        ('24/7', '24/7 (V7 Baseline)'),
        ('US_MARKET', 'US Market Hours (14:30-21:00 UTC / 9:30am-4pm ET)'),
        ('EXTENDED', 'Extended Hours (13:00-22:00 UTC / 8am-5pm ET)'),
        ('NO_ASIAN', 'No Asian Hours (08:00+ UTC)'),
        ('PRIME', 'Prime Hours (15:00-20:00 UTC / 10am-3pm ET)'),
        ('PRE_PLUS_MARKET', 'Pre-Market + Market (12:00-21:00 UTC)'),
        ('EUROPEAN', 'European Hours (08:00-16:00 UTC)'),
        ('LONDON_SESSION', 'London Session (08:00-17:00 UTC)'),
        ('US_ONLY_STRICT', 'US Strict (14:30-20:00 UTC / 9:30am-3pm ET)')
    ]

    print("=" * 80)
    print("V8: TRADING HOURS OPTIMIZATION")
    print("=" * 80)
    print("\nTesting if restricting trading to specific hours improves R:R ratio...")
    print("\nBase Configuration: V7 Winner (Trend + Distance 2%)")
    print("  - Strong trend filter (50 & 200 SMA aligned)")
    print("  - 2% distance from 50 SMA")
    print("  - Fixed 5:1 R:R per trade (15x ATR TP, 3x ATR SL)")
    print("  - Dynamic position sizing (1.5-5%)")
    print("\n" + "=" * 80)

    results = []

    for window_code, window_name in windows:
        print(f"\n🕐 Testing: {window_name}")
        print("   " + "-" * 70)

        bt = TradingHoursBacktest(csv_path)
        metrics = bt.run_backtest(window_type=window_code)

        if metrics:
            results.append({
                'window': window_name,
                'window_code': window_code,
                **metrics
            })

            print(f"   Trades: {metrics['total_trades']}")
            print(f"   Return: {metrics['return_pct']:+.2f}%")
            print(f"   Max DD: {metrics['max_drawdown_pct']:.2f}%")
            print(f"   R:R Ratio: {metrics['rr_ratio']:.2f}x")
            print(f"   Win Rate: {metrics['win_rate']:.1f}%")
            print(f"   Profit Factor: {metrics['profit_factor']:.2f}")
        else:
            print(f"   ❌ No trades found in this window")

    # Summary
    print("\n" + "=" * 80)
    print("RESULTS SUMMARY - Ranked by R:R Ratio")
    print("=" * 80)

    df_results = pd.DataFrame(results)
    df_results = df_results.sort_values('rr_ratio', ascending=False)

    print(f"\n{'Rank':<5} {'Window':<45} {'R:R':<8} {'Return':<10} {'DD':<10} {'Trades':<8}")
    print("-" * 95)

    rank_count = 0
    for idx, row in df_results.iterrows():
        rank_count += 1
        rank = "🥇" if rank_count == 1 else \
               "🥈" if rank_count == 2 else \
               "🥉" if rank_count == 3 else "  "

        print(f"{rank:<5} {row['window']:<45} {row['rr_ratio']:<8.2f} "
              f"{row['return_pct']:>8.2f}% {row['max_drawdown_pct']:>8.2f}% {row['total_trades']:>8}")

    # Best window
    best = df_results.iloc[0]
    baseline = df_results[df_results['window_code'] == '24/7'].iloc[0] if len(df_results[df_results['window_code'] == '24/7']) > 0 else None

    print("\n" + "=" * 80)
    print("🏆 WINNER")
    print("=" * 80)

    print(f"\nBest Window: {best['window']}")
    print(f"  R:R Ratio: {best['rr_ratio']:.2f}x")
    print(f"  Return: {best['return_pct']:+.2f}%")
    print(f"  Max Drawdown: {best['max_drawdown_pct']:.2f}%")
    print(f"  Win Rate: {best['win_rate']:.1f}%")
    print(f"  Profit Factor: {best['profit_factor']:.2f}")
    print(f"  Total Trades: {best['total_trades']}")

    if baseline is not None and best['window_code'] != '24/7':
        improvement = ((best['rr_ratio'] - baseline['rr_ratio']) / baseline['rr_ratio']) * 100
        print(f"\n📈 Improvement vs 24/7 Baseline:")
        print(f"  R:R: {baseline['rr_ratio']:.2f}x → {best['rr_ratio']:.2f}x ({improvement:+.1f}%)")
        print(f"  Return: {baseline['return_pct']:+.2f}% → {best['return_pct']:+.2f}%")
        print(f"  Max DD: {baseline['max_drawdown_pct']:.2f}% → {best['max_drawdown_pct']:.2f}%")
        print(f"  Trades: {baseline['total_trades']} → {best['total_trades']}")

    # Save results
    df_results.to_csv('strategies/trading-hours-results.csv', index=False)
    print(f"\n💾 Results saved to: strategies/trading-hours-results.csv")

    print("\n" + "=" * 80)
    print("ANALYSIS")
    print("=" * 80)

    # Analyze patterns
    us_windows = df_results[df_results['window_code'].str.contains('US')]
    eu_windows = df_results[df_results['window_code'].str.contains('EURO|LONDON')]

    if len(us_windows) > 0:
        print(f"\n🇺🇸 US Hours Average R:R: {us_windows['rr_ratio'].mean():.2f}x")
    if len(eu_windows) > 0:
        print(f"🇪🇺 EU Hours Average R:R: {eu_windows['rr_ratio'].mean():.2f}x")

    # Trade distribution
    print(f"\n📊 Trade Count Range: {df_results['total_trades'].min()}-{df_results['total_trades'].max()}")
    print(f"   Avg: {df_results['total_trades'].mean():.1f}")

    # Key insight
    if best['total_trades'] < 10:
        print(f"\n⚠️  WARNING: Winner has only {best['total_trades']} trades - small sample!")
        print(f"   Consider using window with more trades for statistical reliability.")

    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()
