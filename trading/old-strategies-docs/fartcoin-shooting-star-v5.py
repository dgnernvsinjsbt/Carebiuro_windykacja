#!/usr/bin/env python3
"""
FARTCOIN/USDT Shooting Star Strategy V5
Focus: Ride reversals MUCH longer with tight stops
Goal: Achieve 8:1+ Return/Drawdown ratio
"""

import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')


class ShootingStarStrategy:
    """
    Specialized Shooting Star reversal strategy:
    - Stop just above the shooting star high (tight!)
    - MUCH larger profit targets (ride the reversal)
    - Multiple TP scenarios to test
    """

    def __init__(self, data_path: str, initial_capital: float = 10000,
                 tp_multiplier: float = 15.0, max_hold_hours: int = 12):
        self.data_path = data_path
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.fee_rate = 0.001
        self.df = None
        self.trades = []
        self.equity_curve = []

        # Configurable parameters
        self.tp_multiplier = tp_multiplier  # TP = entry - (tp_multiplier × stop_distance)
        self.max_hold_hours = max_hold_hours

        # Fixed position sizing (no dynamic for now)
        self.risk_pct = 1.0  # Risk 1% per trade

    def load_data(self):
        """Load data with indicators"""
        print(f"\n{'='*70}")
        print(f"SHOOTING STAR REVERSAL STRATEGY V5")
        print(f"{'='*70}")
        print(f"Configuration:")
        print(f"  TP Multiplier: {self.tp_multiplier}x stop distance")
        print(f"  Max Hold: {self.max_hold_hours} hours")
        print(f"  Risk per trade: {self.risk_pct}%")
        print(f"{'='*70}\n")

        self.df = pd.read_csv(self.data_path)
        self.df['timestamp'] = pd.to_datetime(self.df['timestamp'])
        self.df = self.df.sort_values('timestamp').reset_index(drop=True)

        print(f"Period: {self.df['timestamp'].min()} to {self.df['timestamp'].max()}")
        print(f"Candles: {len(self.df):,} ({len(self.df)/60/24:.1f} days)")

        # ATR
        self.df['tr'] = np.maximum(
            self.df['high'] - self.df['low'],
            np.maximum(
                abs(self.df['high'] - self.df['close'].shift(1)),
                abs(self.df['low'] - self.df['close'].shift(1))
            )
        )
        self.df['atr'] = self.df['tr'].rolling(14).mean()

        # Volume
        self.df['vol_sma'] = self.df['volume'].rolling(20).mean()
        self.df['vol_ratio'] = self.df['volume'] / self.df['vol_sma']

        # Price structure
        self.df['body'] = abs(self.df['close'] - self.df['open'])
        self.df['body_pct'] = (self.df['body'] / self.df['open']) * 100
        self.df['upper_wick'] = self.df['high'] - self.df[['open', 'close']].max(axis=1)
        self.df['lower_wick'] = self.df[['open', 'close']].min(axis=1) - self.df['low']
        self.df['is_bullish'] = self.df['close'] > self.df['open']
        self.df['is_bearish'] = self.df['close'] < self.df['open']

        # Trend
        self.df['sma_50'] = self.df['close'].rolling(50).mean()
        self.df['uptrend'] = self.df['close'] > self.df['sma_50']

        # RSI
        delta = self.df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        self.df['rsi'] = 100 - (100 / (1 + rs))

        print(f"✓ Indicators loaded\n")
        return self.df

    def detect_shooting_star(self, idx: int):
        """
        Detect high-quality Shooting Star pattern
        Requirements:
        - In uptrend
        - Long upper wick (>2.5x body)
        - Small lower wick
        - Volume surge
        - Overbought RSI
        """
        if idx < 200:
            return None

        row = self.df.loc[idx]

        # Shooting Star criteria (matching V3 exactly for comparability)
        if (row['upper_wick'] > 2.0 * row['body'] and  # Long upper wick
            row['lower_wick'] < row['body'] * 0.7 and   # Small lower wick
            row['vol_ratio'] > 1.2 and                   # Volume surge
            row['rsi'] > 55):                            # Somewhat overbought

            return {
                'direction': 'short',
                'pattern': 'Shooting Star',
                'entry_price': row['close'],
                'stop_loss': row['high'],  # Stop just above the high
                'timestamp': row['timestamp'],
                'rsi': row['rsi'],
                'vol_ratio': row['vol_ratio'],
                'wick_ratio': row['upper_wick'] / row['body'] if row['body'] > 0 else 0
            }

        return None

    def calculate_position_size(self, entry_price: float, stop_price: float):
        """Fixed risk position sizing"""
        risk_amount = self.capital * (self.risk_pct / 100)
        stop_distance = abs(entry_price - stop_price) / entry_price

        if stop_distance == 0 or stop_distance > 0.05:  # Reject if stop > 5%
            return 0

        position_size = risk_amount / stop_distance
        max_position = self.capital * 0.5  # Cap at 50%
        return min(position_size, max_position)

    def backtest(self):
        """Run backtest"""
        print(f"{'='*70}")
        print("Running Backtest")
        print(f"{'='*70}\n")

        in_position = False
        position = None
        trade_count = 0
        shooting_stars_found = 0

        for idx in range(200, len(self.df)):
            row = self.df.loc[idx]

            # Exit logic
            if in_position and position:
                current_price = row['close']

                # Calculate P&L
                pnl_pct = ((position['entry_price'] - current_price) / position['entry_price']) * 100

                exit_triggered = False
                exit_reason = None

                # Stop loss (just above shooting star high)
                if current_price >= position['stop_loss']:
                    exit_triggered = True
                    exit_reason = 'Stop Loss'
                    current_price = position['stop_loss']

                # Take profit
                if current_price <= position['take_profit']:
                    exit_triggered = True
                    exit_reason = 'Take Profit'
                    current_price = position['take_profit']

                # Time stop
                hours_held = (row['timestamp'] - position['entry_time']).total_seconds() / 3600
                if hours_held >= self.max_hold_hours:
                    exit_triggered = True
                    exit_reason = f'Time Stop ({self.max_hold_hours}h)'

                if exit_triggered:
                    # Final P&L
                    pnl_pct = ((position['entry_price'] - current_price) / position['entry_price']) * 100
                    pnl_pct -= (self.fee_rate * 2 * 100)  # Fees
                    pnl_amount = position['position_size'] * (pnl_pct / 100)
                    self.capital += pnl_amount

                    # Calculate R-multiple
                    risk = (position['stop_loss'] - position['entry_price']) / position['entry_price']
                    actual_return = (position['entry_price'] - current_price) / position['entry_price']
                    r_multiple = actual_return / abs(risk) if risk != 0 else 0

                    self.trades.append({
                        'entry_time': position['entry_time'],
                        'exit_time': row['timestamp'],
                        'entry_price': position['entry_price'],
                        'exit_price': current_price,
                        'stop_loss': position['stop_loss'],
                        'take_profit': position['take_profit'],
                        'position_size': position['position_size'],
                        'pnl_pct': pnl_pct,
                        'pnl_amount': pnl_amount,
                        'r_multiple': r_multiple,
                        'exit_reason': exit_reason,
                        'capital': self.capital,
                        'hours_held': hours_held,
                        'rsi': position['rsi'],
                        'vol_ratio': position['vol_ratio'],
                        'wick_ratio': position['wick_ratio']
                    })

                    trade_count += 1

                    if trade_count <= 20 or trade_count % 5 == 0:
                        print(f"Trade {trade_count}: Entry ${position['entry_price']:.5f} → "
                              f"Exit ${current_price:.5f} | {exit_reason:15s} | "
                              f"{pnl_pct:+6.2f}% ({r_multiple:+5.2f}R) | "
                              f"Capital: ${self.capital:,.0f}")

                    in_position = False
                    position = None

            # Entry logic
            if not in_position:
                signal = self.detect_shooting_star(idx)

                if signal:
                    shooting_stars_found += 1

                    entry_price = signal['entry_price']
                    stop_loss = signal['stop_loss']

                    # Calculate TP based on multiplier
                    stop_distance = abs(stop_loss - entry_price)
                    take_profit = entry_price - (self.tp_multiplier * stop_distance)

                    position_size = self.calculate_position_size(entry_price, stop_loss)

                    if position_size > 0:
                        position = {
                            'entry_time': signal['timestamp'],
                            'entry_price': entry_price,
                            'stop_loss': stop_loss,
                            'take_profit': take_profit,
                            'position_size': position_size,
                            'rsi': signal['rsi'],
                            'vol_ratio': signal['vol_ratio'],
                            'wick_ratio': signal['wick_ratio']
                        }
                        in_position = True

            # Track equity
            self.equity_curve.append({
                'timestamp': row['timestamp'],
                'capital': self.capital,
                'in_position': in_position
            })

        print(f"\n✓ Shooting Stars Found: {shooting_stars_found}")
        print(f"✓ Trades Taken: {trade_count}\n")

        return self.analyze_results()

    def analyze_results(self):
        """Analyze results"""
        print(f"{'='*70}")
        print("RESULTS")
        print(f"{'='*70}\n")

        if not self.trades:
            print("❌ No trades generated!")
            return None

        df_trades = pd.DataFrame(self.trades)
        df_equity = pd.DataFrame(self.equity_curve)

        # Core metrics
        total_trades = len(df_trades)
        wins = len(df_trades[df_trades['pnl_amount'] > 0])
        losses = len(df_trades[df_trades['pnl_amount'] <= 0])
        win_rate = (wins / total_trades) * 100

        total_return_pct = ((self.capital - self.initial_capital) / self.initial_capital) * 100
        total_return = self.capital - self.initial_capital

        # Drawdown
        df_equity['peak'] = df_equity['capital'].cummax()
        df_equity['drawdown'] = ((df_equity['capital'] - df_equity['peak']) / df_equity['peak']) * 100
        max_dd = df_equity['drawdown'].min()

        # R:R
        rr_ratio = abs(total_return_pct / max_dd) if max_dd < 0 else (float('inf') if total_return_pct > 0 else 0)

        # Stats
        avg_win = df_trades[df_trades['pnl_pct'] > 0]['pnl_pct'].mean() if wins > 0 else 0
        avg_loss = df_trades[df_trades['pnl_pct'] <= 0]['pnl_pct'].mean() if losses > 0 else 0
        avg_r_win = df_trades[df_trades['r_multiple'] > 0]['r_multiple'].mean() if wins > 0 else 0
        avg_r_loss = df_trades[df_trades['r_multiple'] <= 0]['r_multiple'].mean() if losses > 0 else 0

        gross_profit = df_trades[df_trades['pnl_amount'] > 0]['pnl_amount'].sum()
        gross_loss = abs(df_trades[df_trades['pnl_amount'] <= 0]['pnl_amount'].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

        # Avg holding time
        avg_hours = df_trades['hours_held'].mean()

        # Print
        print(f"📊 PERFORMANCE")
        print(f"{'-'*70}")
        print(f"Initial Capital:      ${self.initial_capital:,.2f}")
        print(f"Final Capital:        ${self.capital:,.2f}")
        print(f"Total Return:         ${total_return:+,.2f} ({total_return_pct:+.2f}%)")
        print(f"Max Drawdown:         {max_dd:.2f}%")
        print(f"")
        print(f"🎯 RETURN/DRAWDOWN:   {rr_ratio:.2f}x")
        print(f"   {'✅ TARGET MET!' if rr_ratio >= 8.0 else f'❌ Target: 8.0x (need {8.0 - rr_ratio:.2f}x more)'}")
        print(f"")
        print(f"📈 TRADE STATISTICS")
        print(f"{'-'*70}")
        print(f"Total Trades:         {total_trades}")
        print(f"Winners:              {wins} ({win_rate:.1f}%)")
        print(f"Losers:               {losses}")
        print(f"")
        print(f"Avg Win:              {avg_win:+.2f}% ({avg_r_win:+.2f}R)")
        print(f"Avg Loss:             {avg_loss:+.2f}% ({avg_r_loss:+.2f}R)")
        print(f"Profit Factor:        {profit_factor:.2f}")
        print(f"Avg Hold Time:        {avg_hours:.1f} hours")

        # Best/Worst
        if len(df_trades) > 0:
            best = df_trades.loc[df_trades['pnl_pct'].idxmax()]
            worst = df_trades.loc[df_trades['pnl_pct'].idxmin()]

            print(f"\n🏆 BEST TRADE")
            print(f"{'-'*70}")
            print(f"Entry: ${best['entry_price']:.5f} @ {best['entry_time']}")
            print(f"Exit:  ${best['exit_price']:.5f} @ {best['exit_time']}")
            print(f"P&L:   {best['pnl_pct']:+.2f}% ({best['r_multiple']:+.2f}R)")
            print(f"Reason: {best['exit_reason']}")
            print(f"Held: {best['hours_held']:.1f} hours | RSI: {best['rsi']:.1f} | Vol: {best['vol_ratio']:.1f}x")

            print(f"\n📉 WORST TRADE")
            print(f"{'-'*70}")
            print(f"Entry: ${worst['entry_price']:.5f} @ {worst['entry_time']}")
            print(f"Exit:  ${worst['exit_price']:.5f} @ {worst['exit_time']}")
            print(f"P&L:   {worst['pnl_pct']:+.2f}% ({worst['r_multiple']:+.2f}R)")
            print(f"Reason: {worst['exit_reason']}")
            print(f"Held: {worst['hours_held']:.1f} hours | RSI: {worst['rsi']:.1f} | Vol: {worst['vol_ratio']:.1f}x")

        # Exit reason breakdown
        print(f"\n📊 EXIT REASONS")
        print(f"{'-'*70}")
        for reason in df_trades['exit_reason'].unique():
            count = len(df_trades[df_trades['exit_reason'] == reason])
            pct = (count / total_trades) * 100
            avg_pnl = df_trades[df_trades['exit_reason'] == reason]['pnl_pct'].mean()
            print(f"{reason:20s}: {count:3d} ({pct:5.1f}%) | Avg P&L: {avg_pnl:+6.2f}%")

        # Save
        filename_trades = f'./strategies/shooting-star-trades-tp{int(self.tp_multiplier)}x-h{self.max_hold_hours}.csv'
        filename_equity = f'./strategies/shooting-star-equity-tp{int(self.tp_multiplier)}x-h{self.max_hold_hours}.csv'

        df_trades.to_csv(filename_trades, index=False)
        df_equity.to_csv(filename_equity, index=False)

        print(f"\n✓ Saved: {filename_trades}")
        print(f"✓ Saved: {filename_equity}")

        # Verdict
        print(f"\n{'='*70}")
        print("VERDICT")
        print(f"{'='*70}")

        is_profitable = total_return_pct > 0
        has_good_rr = rr_ratio >= 8.0

        print(f"✓ Profitable:   {'YES ✅' if is_profitable else 'NO ❌'} ({total_return_pct:+.2f}%)")
        print(f"✓ R:R ≥ 8.0x:   {'YES ✅' if has_good_rr else 'NO ❌'} (got {rr_ratio:.2f}x)")

        if is_profitable and has_good_rr:
            print(f"\n🎉 MISSION ACCOMPLISHED!")
            print(f"Shooting Star strategy with {self.tp_multiplier}x TP achieves {rr_ratio:.1f}x R:R!")
        elif is_profitable:
            print(f"\n⚠️ Profitable but need better R:R ratio")
            print(f"Try: Wider TP ({self.tp_multiplier * 1.5:.0f}x) or longer hold ({self.max_hold_hours * 1.5:.0f}h)")
        else:
            print(f"\n❌ Not profitable with current parameters")
            print(f"Try: Tighter filters or different TP/hold settings")

        return {
            'total_return_pct': total_return_pct,
            'max_drawdown': max_dd,
            'rr_ratio': rr_ratio,
            'profit_factor': profit_factor,
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'total_trades': total_trades
        }


def run_multiple_scenarios():
    """Test multiple TP and hold time scenarios"""
    print(f"\n{'='*70}")
    print("TESTING MULTIPLE SCENARIOS")
    print(f"{'='*70}\n")

    scenarios = [
        # (TP_multiplier, max_hold_hours)
        (10, 8),   # Conservative
        (15, 12),  # Moderate
        (20, 16),  # Aggressive
        (25, 24),  # Very aggressive
        (30, 24),  # Extreme
        (40, 48),  # Ultra extreme (ride it til it dies)
    ]

    results = []

    for tp_mult, max_hold in scenarios:
        print(f"\n{'#'*70}")
        print(f"# SCENARIO: TP={tp_mult}x | Hold={max_hold}h")
        print(f"{'#'*70}")

        strategy = ShootingStarStrategy(
            data_path='/workspaces/Carebiuro_windykacja/fartcoin_usdt_1m_lbank.csv',
            initial_capital=10000,
            tp_multiplier=tp_mult,
            max_hold_hours=max_hold
        )

        strategy.load_data()
        result = strategy.backtest()

        if result:
            result['tp_mult'] = tp_mult
            result['max_hold'] = max_hold
            results.append(result)

    # Summary comparison
    if results:
        print(f"\n{'='*70}")
        print("SCENARIO COMPARISON")
        print(f"{'='*70}\n")
        print(f"{'TP':>4s} | {'Hold':>5s} | {'Return':>8s} | {'MaxDD':>7s} | {'R:R':>6s} | {'PF':>5s} | {'WR':>6s} | {'Trades':>6s}")
        print(f"{'-'*70}")

        for r in results:
            print(f"{r['tp_mult']:>4.0f}x | {r['max_hold']:>4.0f}h | "
                  f"{r['total_return_pct']:>+7.2f}% | "
                  f"{r['max_drawdown']:>6.2f}% | "
                  f"{r['rr_ratio']:>5.2f}x | "
                  f"{r['profit_factor']:>4.2f} | "
                  f"{r['win_rate']:>5.1f}% | "
                  f"{r['total_trades']:>6.0f}")

        # Find best R:R
        best = max(results, key=lambda x: x['rr_ratio'])
        print(f"\n🏆 BEST R:R RATIO: {best['rr_ratio']:.2f}x")
        print(f"   Config: TP={best['tp_mult']:.0f}x, Hold={best['max_hold']:.0f}h")
        print(f"   Return: {best['total_return_pct']:+.2f}%, MaxDD: {best['max_drawdown']:.2f}%")


if __name__ == "__main__":
    # Run all scenarios
    run_multiple_scenarios()
