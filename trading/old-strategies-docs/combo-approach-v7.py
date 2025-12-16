#!/usr/bin/env python3
"""
FARTCOIN/USDT Combination Approach V7
Implements 3 key enhancements:
1. Confirmation candle requirement
2. Support/Resistance entry timing with tighter stops
3. Dynamic TP based on volatility expansion

Goal: 5-8x Return/Drawdown ratio
"""

import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')


class ComboApproachV7:
    """
    Enhanced strategy combining:
    - Confirmation candle filtering
    - Support/Resistance timing
    - Dynamic volatility-based targets
    """

    def __init__(self, data_path: str, initial_capital: float = 10000):
        self.data_path = data_path
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.fee_rate = 0.001
        self.df = None
        self.trades = []
        self.equity_curve = []

        # Configuration - Optimized for 5-8x R:R target
        self.config = {
            'body_threshold': 1.2,           # Min body % for entry
            'volume_multiplier': 3.0,        # Min volume surge
            'confirmation_vol_mult': 1.2,    # NEW: Confirmation candle volume
            'rsi_short_max': 55,             # Max RSI for short
            'stop_atr_mult': 2.5,            # NEW: Tighter stop (vs 3x baseline)
            'target_atr_mult_normal': 15.0,  # Wider standard target (6:1 R:R)
            'target_atr_mult_high_vol': 22.0, # NEW: Even wider high vol target (8.8:1)
            'base_risk_pct': 2.0,            # More aggressive base risk
            'max_risk_pct': 5.0,             # Higher max risk
            'win_streak_scaling': 0.7,       # Faster risk scaling on wins
            'use_trailing_stop': True,       # Enable trailing stops
            'use_partial_exits': True,       # Enable partial profit taking
            'max_hold_hours': 48,            # Even longer hold time for winners
            'support_proximity_pct': 6.0,    # NEW: Wider support range for more entries
            'swing_low_period': 15,          # NEW: Shorter lookback = more recent support
            'volatility_expansion': 1.08     # NEW: More sensitive vol detection
        }

        # Position sizing
        self.base_risk_pct = self.config['base_risk_pct']
        self.current_risk_pct = self.base_risk_pct
        self.win_streak = 0
        self.loss_streak = 0

    def load_data(self):
        """Load and prepare data"""
        print(f"\n{'='*70}")
        print(f"COMBO APPROACH V7 - Confirmation + Support/Resistance + Dynamic TP")
        print(f"{'='*70}")
        print(f"Configuration:")
        print(f"  Body Threshold:     {self.config['body_threshold']:.1f}%")
        print(f"  Volume Multiplier:  {self.config['volume_multiplier']:.1f}x")
        print(f"  Confirmation Vol:   {self.config['confirmation_vol_mult']:.1f}x")
        print(f"  Stop Distance:      {self.config['stop_atr_mult']:.1f}x ATR (TIGHTER)")
        print(f"  Normal Target:      {self.config['target_atr_mult_normal']:.1f}x ATR")
        print(f"  High Vol Target:    {self.config['target_atr_mult_high_vol']:.1f}x ATR")
        print(f"  Support Proximity:  {self.config['support_proximity_pct']:.1f}%")
        print(f"  Trailing Stop:      {self.config['use_trailing_stop']}")
        print(f"  Partial Exits:      {self.config['use_partial_exits']}")
        print(f"{'='*70}\n")

        self.df = pd.read_csv(self.data_path)
        self.df['timestamp'] = pd.to_datetime(self.df['timestamp'])
        self.df = self.df.sort_values('timestamp').reset_index(drop=True)

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

        # Price
        self.df['body'] = abs(self.df['close'] - self.df['open'])
        self.df['body_pct'] = (self.df['body'] / self.df['open']) * 100
        self.df['upper_wick'] = self.df['high'] - self.df[['open', 'close']].max(axis=1)
        self.df['lower_wick'] = self.df[['open', 'close']].min(axis=1) - self.df['low']
        self.df['is_bullish'] = self.df['close'] > self.df['open']
        self.df['is_bearish'] = self.df['close'] < self.df['open']

        # Trend
        self.df['sma_50'] = self.df['close'].rolling(50).mean()
        self.df['downtrend'] = self.df['close'] < self.df['sma_50']

        # RSI
        delta = self.df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        self.df['rsi'] = 100 - (100 / (1 + rs))

        # NEW: Volatility metrics for dynamic targets
        self.df['atr_50'] = self.df['atr'].rolling(50).mean()
        self.df['atr_expansion'] = self.df['atr'] / self.df['atr_50']
        self.df['high_vol_regime'] = self.df['atr_expansion'] > self.config['volatility_expansion']

        # NEW: Support/Resistance - Swing lows
        self.df['swing_low'] = self.df['low'].rolling(
            window=self.config['swing_low_period'],
            center=True
        ).min()

        print(f"Period: {self.df['timestamp'].min()} to {self.df['timestamp'].max()}")
        print(f"Candles: {len(self.df):,} ({len(self.df)/60/24:.1f} days)\n")

        return self.df

    def detect_explosive_pattern(self, idx: int):
        """Detect initial Explosive Breakdown pattern"""
        if idx < 200:
            return False

        row = self.df.loc[idx]
        cfg = self.config

        # EXPLOSIVE BEARISH BREAKDOWN
        if (row['is_bearish'] and
            row['downtrend'] and
            row['body_pct'] > cfg['body_threshold'] and
            row['vol_ratio'] > cfg['volume_multiplier'] and
            row['lower_wick'] < row['body'] * 0.35 and
            row['upper_wick'] < row['body'] * 0.35 and
            row['rsi'] < cfg['rsi_short_max'] and row['rsi'] > 25):
            return True

        return False

    def check_confirmation_candle(self, idx: int):
        """NEW: Check if next candle confirms the breakdown (relaxed)"""
        if idx >= len(self.df) - 1:
            return False

        prev_row = self.df.loc[idx]
        curr_row = self.df.loc[idx + 1]

        # Relaxed confirmation requirements (at least 2 of 3):
        confirmation_score = 0

        # 1. Also bearish
        if curr_row['is_bearish']:
            confirmation_score += 1

        # 2. Continues downward
        if curr_row['close'] < prev_row['close']:
            confirmation_score += 1

        # 3. Volume still elevated
        if curr_row['vol_ratio'] >= self.config['confirmation_vol_mult']:
            confirmation_score += 1

        # Pass if at least 2 of 3 criteria met
        return confirmation_score >= 2

    def check_support_proximity(self, idx: int):
        """NEW: Check if price is near support level"""
        row = self.df.loc[idx]

        # Get most recent swing low (support)
        # Look back to find the last valid swing low
        support_level = None
        for i in range(idx - 1, max(0, idx - 100), -1):
            if not pd.isna(self.df.loc[i, 'swing_low']):
                support_level = self.df.loc[i, 'swing_low']
                break

        if support_level is None:
            return False

        # Check if current price is within proximity of support
        price_to_support_pct = abs((row['close'] - support_level) / support_level) * 100

        return price_to_support_pct <= self.config['support_proximity_pct']

    def calculate_position_size(self, entry_price: float, stop_price: float):
        """Dynamic position sizing"""
        risk_amount = self.capital * (self.current_risk_pct / 100)
        stop_distance = abs(entry_price - stop_price) / entry_price

        if stop_distance == 0:
            return 0

        position_size = risk_amount / stop_distance
        max_position = self.capital * 0.6
        return min(position_size, max_position)

    def update_risk_sizing(self, trade_won: bool):
        """Position sizing on win streaks"""
        if trade_won:
            self.win_streak += 1
            self.loss_streak = 0
            self.current_risk_pct = min(
                self.base_risk_pct + (self.win_streak * self.config['win_streak_scaling']),
                self.config['max_risk_pct']
            )
        else:
            self.loss_streak += 1
            self.win_streak = 0
            self.current_risk_pct = self.base_risk_pct

    def backtest(self):
        """Run backtest with all 3 enhancements"""
        print(f"Running Backtest...\n")

        in_position = False
        position = None
        trade_count = 0
        confirmed_signals = 0
        support_entries = 0
        high_vol_entries = 0
        pattern_detected_idx = None  # Track when pattern is detected

        for idx in range(200, len(self.df) - 1):  # -1 to allow confirmation check
            row = self.df.loc[idx]

            # Exit logic
            if in_position and position:
                current_price = row['close']
                hours_held = (row['timestamp'] - position['entry_time']).total_seconds() / 3600

                # Calculate current P&L and R-multiple
                pnl = position['entry_price'] - current_price
                initial_risk = abs(position['entry_price'] - position['initial_stop'])
                r_multiple = pnl / initial_risk if initial_risk > 0 else 0

                exit_triggered = False
                exit_reason = None
                exit_price = current_price

                # Trailing stop logic
                if self.config['use_trailing_stop'] and not position.get('partial_1_taken'):
                    if r_multiple >= 3.0 and position['stop_loss'] != position['entry_price']:
                        # Move stop to breakeven at 3R
                        position['stop_loss'] = position['entry_price']

                    if r_multiple >= 5.0:
                        # Trail at 2R above current price
                        atr = row['atr']
                        new_stop = current_price + (2 * atr)
                        position['stop_loss'] = min(position['stop_loss'], new_stop)

                # Partial profit taking
                if self.config['use_partial_exits']:
                    # 30% at 2R
                    if r_multiple >= 2.0 and not position.get('partial_1_taken'):
                        position['partial_1_taken'] = True
                        position['remaining_size'] = position['position_size'] * 0.7
                        partial_pnl = position['position_size'] * 0.3 * (pnl / position['entry_price'])
                        self.capital += partial_pnl

                    # 40% at 4R (total 70% closed)
                    if r_multiple >= 4.0 and not position.get('partial_2_taken'):
                        position['partial_2_taken'] = True
                        position['remaining_size'] = position['position_size'] * 0.3
                        partial_pnl = position['position_size'] * 0.4 * (pnl / position['entry_price'])
                        self.capital += partial_pnl

                # Stop loss
                if current_price >= position['stop_loss']:
                    exit_triggered, exit_reason = True, 'Stop Loss'
                    exit_price = position['stop_loss']

                # Take profit
                if current_price <= position['take_profit']:
                    exit_triggered, exit_reason = True, 'Take Profit'
                    exit_price = position['take_profit']

                # Time stop (only if not in high vol regime)
                if not position['high_vol_entry'] and hours_held >= self.config['max_hold_hours']:
                    exit_triggered, exit_reason = True, f'Time Stop ({self.config["max_hold_hours"]}h)'

                if exit_triggered:
                    # Final P&L on remaining position
                    final_pnl_pct = ((position['entry_price'] - exit_price) / position['entry_price']) * 100

                    # Account for what's still open
                    remaining_size = position.get('remaining_size', position['position_size'])
                    final_pnl_pct -= (self.fee_rate * 2 * 100)  # Fees
                    pnl_amount = remaining_size * (final_pnl_pct / 100)
                    self.capital += pnl_amount

                    # Total P&L for trade (including partials already booked)
                    total_pnl_pct = ((self.capital - position['capital_at_entry']) / position['capital_at_entry']) * 100

                    self.trades.append({
                        'entry_time': position['entry_time'],
                        'exit_time': row['timestamp'],
                        'direction': 'short',
                        'pattern': position['pattern'],
                        'entry_price': position['entry_price'],
                        'exit_price': exit_price,
                        'stop_loss': position['stop_loss'],
                        'take_profit': position['take_profit'],
                        'position_size': position['position_size'],
                        'pnl_pct': total_pnl_pct,
                        'pnl_amount': self.capital - position['capital_at_entry'],
                        'exit_reason': exit_reason,
                        'capital': self.capital,
                        'risk_pct': position['risk_pct'],
                        'hours_held': hours_held,
                        'r_multiple': r_multiple,
                        'high_vol_entry': position['high_vol_entry'],
                        'support_entry': position['support_entry']
                    })

                    self.update_risk_sizing(self.capital > position['capital_at_entry'])
                    trade_count += 1

                    if trade_count <= 20 or trade_count % 10 == 0:
                        vol_marker = "HiVol" if position['high_vol_entry'] else "NormVol"
                        supp_marker = "NearSupp" if position['support_entry'] else ""
                        print(f"Trade {trade_count}: {vol_marker:7s} {supp_marker:8s} | "
                              f"{exit_reason:15s} | {total_pnl_pct:+6.2f}% ({r_multiple:+.1f}R) | Capital: ${self.capital:,.0f}")

                    in_position = False
                    position = None

            # Entry logic with 3 enhancements
            if not in_position:
                # ENHANCEMENT 1: Detect pattern, then wait for confirmation
                if pattern_detected_idx is None:
                    # Check for explosive pattern
                    if self.detect_explosive_pattern(idx):
                        pattern_detected_idx = idx
                        continue  # Wait for next candle to confirm

                # If we detected a pattern on previous candle, check confirmation now
                if pattern_detected_idx == idx - 1:
                    # ENHANCEMENT 1: Confirmation candle check
                    has_confirmation = self.check_confirmation_candle(pattern_detected_idx)

                    if has_confirmation:
                        confirmed_signals += 1

                        # ENHANCEMENT 2: Support/Resistance proximity check
                        near_support = self.check_support_proximity(idx)

                        if near_support:
                            support_entries += 1

                            entry_price = row['close']
                            atr = row['atr']

                            # ENHANCEMENT 2: Tighter stop (2x ATR instead of 3x)
                            stop_loss = entry_price + (self.config['stop_atr_mult'] * atr)

                            # ENHANCEMENT 3: Dynamic TP based on volatility
                            high_vol_regime = row['high_vol_regime']
                            if high_vol_regime:
                                high_vol_entries += 1
                                take_profit = entry_price - (self.config['target_atr_mult_high_vol'] * atr)
                            else:
                                take_profit = entry_price - (self.config['target_atr_mult_normal'] * atr)

                            position_size = self.calculate_position_size(entry_price, stop_loss)

                            if position_size > 0:
                                position = {
                                    'entry_time': row['timestamp'],
                                    'entry_price': entry_price,
                                    'direction': 'short',
                                    'pattern': 'Confirmed Explosive Bearish + Support',
                                    'stop_loss': stop_loss,
                                    'initial_stop': stop_loss,
                                    'take_profit': take_profit,
                                    'position_size': position_size,
                                    'remaining_size': position_size,
                                    'risk_pct': self.current_risk_pct,
                                    'capital_at_entry': self.capital,
                                    'high_vol_entry': high_vol_regime,
                                    'support_entry': near_support
                                }
                                in_position = True

                    # Reset pattern detection
                    pattern_detected_idx = None

            # Track equity
            self.equity_curve.append({
                'timestamp': row['timestamp'],
                'capital': self.capital,
                'in_position': in_position
            })

        print(f"\n✓ Total Trades: {trade_count}")
        print(f"✓ Confirmed Signals: {confirmed_signals}")
        print(f"✓ Support Entries: {support_entries}")
        print(f"✓ High Vol Entries: {high_vol_entries}\n")

        return self.analyze_results()

    def analyze_results(self):
        """Analyze results"""
        print(f"{'='*70}")
        print("RESULTS - COMBO APPROACH V7")
        print(f"{'='*70}\n")

        if not self.trades:
            print("❌ No trades!")
            return None

        df_trades = pd.DataFrame(self.trades)
        df_equity = pd.DataFrame(self.equity_curve)

        # Save to CSV
        df_trades.to_csv('/workspaces/Carebiuro_windykacja/strategies/combo-approach-trades.csv', index=False)
        df_equity.to_csv('/workspaces/Carebiuro_windykacja/strategies/combo-approach-equity.csv', index=False)
        print("✓ Saved: combo-approach-trades.csv")
        print("✓ Saved: combo-approach-equity.csv\n")

        # Metrics
        total_trades = len(df_trades)
        wins = len(df_trades[df_trades['pnl_amount'] > 0])
        losses = len(df_trades[df_trades['pnl_amount'] <= 0])
        win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0

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

        gross_profit = df_trades[df_trades['pnl_amount'] > 0]['pnl_amount'].sum()
        gross_loss = abs(df_trades[df_trades['pnl_amount'] <= 0]['pnl_amount'].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

        # R-multiple stats
        avg_r = df_trades['r_multiple'].mean()
        max_r = df_trades['r_multiple'].max()

        # Print
        print(f"📊 PERFORMANCE")
        print(f"{'-'*70}")
        print(f"Initial Capital:      ${self.initial_capital:,.2f}")
        print(f"Final Capital:        ${self.capital:,.2f}")
        print(f"Total Return:         ${total_return:+,.2f} ({total_return_pct:+.2f}%)")
        print(f"Max Drawdown:         {max_dd:.2f}%")
        print(f"")
        print(f"🎯 RETURN/DRAWDOWN:   {rr_ratio:.2f}x")
        if rr_ratio >= 5.0:
            print(f"   ✅ TARGET MET! (Goal: 5-8x)")
        else:
            print(f"   Target: 5-8x (Current: {rr_ratio:.2f}x)")
        print(f"")
        print(f"📈 TRADES")
        print(f"{'-'*70}")
        print(f"Total:         {total_trades}")
        print(f"Winners:       {wins} ({win_rate:.1f}%)")
        print(f"Losers:        {losses}")
        print(f"Avg Win:       {avg_win:+.2f}%")
        print(f"Avg Loss:      {avg_loss:+.2f}%")
        print(f"Profit Factor: {profit_factor:.2f}")
        print(f"Avg R-multiple: {avg_r:+.2f}R")
        print(f"Max R-multiple: {max_r:+.2f}R")

        # Enhancement breakdown
        print(f"\n📊 ENHANCEMENT BREAKDOWN")
        print(f"{'-'*70}")
        high_vol_trades = df_trades[df_trades['high_vol_entry'] == True]
        normal_vol_trades = df_trades[df_trades['high_vol_entry'] == False]

        if len(high_vol_trades) > 0:
            hv_return = high_vol_trades['pnl_amount'].sum()
            hv_wr = (len(high_vol_trades[high_vol_trades['pnl_amount'] > 0]) / len(high_vol_trades)) * 100
            print(f"High Vol Regime:  {len(high_vol_trades):3d} trades | WR: {hv_wr:5.1f}% | ${hv_return:+,.2f}")

        if len(normal_vol_trades) > 0:
            nv_return = normal_vol_trades['pnl_amount'].sum()
            nv_wr = (len(normal_vol_trades[normal_vol_trades['pnl_amount'] > 0]) / len(normal_vol_trades)) * 100
            print(f"Normal Vol:       {len(normal_vol_trades):3d} trades | WR: {nv_wr:5.1f}% | ${nv_return:+,.2f}")

        # Comparison to baseline
        print(f"\n📊 COMPARISON TO CONSERVATIVE BASELINE")
        print(f"{'-'*70}")
        print(f"                    Baseline    →    Combo V7    →    Change")
        print(f"{'-'*70}")
        baseline_return = 11.41
        baseline_dd = -5.76
        baseline_rr = 1.98

        return_change = total_return_pct - baseline_return
        dd_change = max_dd - baseline_dd
        rr_change = rr_ratio - baseline_rr

        print(f"Return:           {baseline_return:+7.2f}%     {total_return_pct:+7.2f}%    {return_change:+7.2f}%")
        print(f"Max Drawdown:     {baseline_dd:7.2f}%     {max_dd:7.2f}%    {dd_change:+7.2f}%")
        print(f"R:R Ratio:        {baseline_rr:7.2f}x     {rr_ratio:7.2f}x    {rr_change:+7.2f}x")

        # Success criteria check
        print(f"\n{'='*70}")
        print("SUCCESS CRITERIA CHECK")
        print(f"{'='*70}")

        criteria = [
            ("R:R ratio: 4-8x", rr_ratio >= 4.0 and rr_ratio <= 8.0, f"{rr_ratio:.2f}x"),
            ("Return: +12-20%", total_return_pct >= 12.0 and total_return_pct <= 20.0, f"{total_return_pct:+.2f}%"),
            ("Max DD: -2 to -4%", max_dd >= -4.0 and max_dd <= -2.0, f"{max_dd:.2f}%"),
            ("Win rate: 40-50%", win_rate >= 40.0 and win_rate <= 50.0, f"{win_rate:.1f}%"),
            ("Profit factor: 1.8+", profit_factor >= 1.8, f"{profit_factor:.2f}"),
            ("Trades: 10-18", total_trades >= 10 and total_trades <= 18, f"{total_trades}")
        ]

        passed = 0
        for criterion, met, value in criteria:
            status = "✅" if met else "❌"
            print(f"{status} {criterion:25s} = {value}")
            if met:
                passed += 1

        print(f"\n{'='*70}")
        print(f"OVERALL: {passed}/{len(criteria)} criteria met")
        print(f"{'='*70}\n")

        return {
            'total_return_pct': total_return_pct,
            'max_drawdown': max_dd,
            'rr_ratio': rr_ratio,
            'profit_factor': profit_factor,
            'win_rate': win_rate,
            'total_trades': total_trades,
            'avg_r_multiple': avg_r,
            'criteria_passed': passed,
            'criteria_total': len(criteria)
        }


if __name__ == "__main__":
    strategy = ComboApproachV7(
        data_path='/workspaces/Carebiuro_windykacja/fartcoin_usdt_1m_lbank.csv',
        initial_capital=10000
    )

    strategy.load_data()
    result = strategy.backtest()

    if result:
        print(f"\n🎯 FINAL METRICS:")
        print(f"   Total Return:   {result['total_return_pct']:+.2f}%")
        print(f"   Max Drawdown:   {result['max_drawdown']:.2f}%")
        print(f"   R:R Ratio:      {result['rr_ratio']:.2f}x")
        print(f"   Win Rate:       {result['win_rate']:.1f}%")
        print(f"   Profit Factor:  {result['profit_factor']:.2f}")
        print(f"   Total Trades:   {result['total_trades']}")
        print(f"   Avg R-multiple: {result['avg_r_multiple']:+.2f}R")
        print(f"\n   Success Rate:   {result['criteria_passed']}/{result['criteria_total']} criteria met")
