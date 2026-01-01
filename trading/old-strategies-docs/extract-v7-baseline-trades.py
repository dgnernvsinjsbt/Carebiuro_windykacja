#!/usr/bin/env python3
"""
Extract exact V7 baseline trades with proper backtest engine.
This uses the EXACT same logic as explosive-v7-advanced.py for the "Trend + Distance 2%" config.
"""

import pandas as pd
import numpy as np
import json

class V7BaselineBacktest:
    def __init__(self, csv_path):
        print("Loading FARTCOIN data...")
        self.df = pd.read_csv(csv_path)
        self.df['timestamp'] = pd.to_datetime(self.df['timestamp'])

        # V7 Baseline config (Trend + Distance 2%)
        self.config = {
            'body_threshold': 1.0,
            'volume_multiplier': 2.5,
            'wick_threshold': 0.35,
            'require_strong_trend': True,
            'sma_distance_min': 2.0,
            'short_only_in_downtrend': True,
            'long_only_in_uptrend': True,
            'rsi_short_max': 55,
            'rsi_short_min': 25,
            'rsi_long_min': 45,
            'rsi_long_max': 75,
            'require_high_vol': True,
            'atr_percentile_min': 50,
            'stop_atr_mult': 3.0,
            'dynamic_tp': False,
            'tp_atr_high_vol': 15.0,
            'base_risk_pct': 1.5,
            'max_risk_pct': 5.0,
            'win_streak_scaling': 0.5,
            'use_trailing_stop': True,
            'use_partial_exits': True,
            'max_hold_hours': 24,
            'trade_both_directions': True
        }

        self.capital = 10000.0
        self.trades = []
        self.fee_rate = 0.001

        self.calculate_indicators()

    def calculate_indicators(self):
        """Calculate all technical indicators exactly as V7"""
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

        # Trends
        self.df['uptrend_50'] = self.df['close'] > self.df['sma_50']
        self.df['downtrend_50'] = self.df['close'] < self.df['sma_50']
        self.df['uptrend_200'] = self.df['close'] > self.df['sma_200']
        self.df['downtrend_200'] = self.df['close'] < self.df['sma_200']
        self.df['strong_uptrend'] = self.df['uptrend_50'] & self.df['uptrend_200']
        self.df['strong_downtrend'] = self.df['downtrend_50'] & self.df['downtrend_200']

        # Distance from SMA
        self.df['distance_from_50'] = abs((self.df['close'] - self.df['sma_50']) / self.df['sma_50']) * 100

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

        # ATR percentile
        self.df['atr_percentile'] = self.df['atr'].rolling(100).apply(
            lambda x: (x.iloc[-1] > x).sum() / len(x) * 100 if len(x) > 0 else 50
        )
        self.df['high_vol'] = self.df['atr_percentile'] >= 50

    def detect_signal(self, idx):
        """Detect signals exactly as V7"""
        if idx < 200:
            return None

        row = self.df.loc[idx]
        cfg = self.config

        # Base checks
        body = row['body']
        if body == 0:
            return None

        wick_ratio_lower = row['lower_wick'] / body
        wick_ratio_upper = row['upper_wick'] / body

        body_ok = row['body_pct'] > cfg['body_threshold']
        volume_ok = row['vol_ratio'] > cfg['volume_multiplier']
        wicks_ok = wick_ratio_lower < cfg['wick_threshold'] and wick_ratio_upper < cfg['wick_threshold']
        vol_ok = row['high_vol']

        if not (body_ok and volume_ok and wicks_ok and vol_ok):
            return None

        # Trend and distance check
        distance_ok = row['distance_from_50'] >= cfg['sma_distance_min']

        # Explosive Bearish Breakdown
        if row['is_bearish'] and row['strong_downtrend'] and distance_ok:
            if cfg['rsi_short_min'] < row['rsi'] < cfg['rsi_short_max']:
                return {
                    'direction': 'short',
                    'pattern': 'Explosive Bearish Breakdown',
                    'atr_percentile': row['atr_percentile']
                }

        # Explosive Bullish Breakout
        if cfg['trade_both_directions']:
            if row['is_bullish'] and row['strong_uptrend'] and distance_ok:
                if cfg['rsi_long_min'] < row['rsi'] < cfg['rsi_long_max']:
                    return {
                        'direction': 'long',
                        'pattern': 'Explosive Bullish Breakout',
                        'atr_percentile': row['atr_percentile']
                    }

        return None

    def update_risk_sizing(self, win):
        """Update risk sizing based on win/loss"""
        if win:
            self.current_risk_pct = min(
                self.current_risk_pct + self.config['win_streak_scaling'],
                self.config['max_risk_pct']
            )
        else:
            self.current_risk_pct = self.config['base_risk_pct']

    def run(self):
        """Run backtest with exact V7 logic"""
        self.current_risk_pct = self.config['base_risk_pct']
        in_position = False
        position = None
        trade_count = 0

        print("\nRunning V7 baseline backtest...")

        for idx in range(200, len(self.df)):
            row = self.df.loc[idx]

            # Manage position
            if in_position and position:
                hours_held = (row['timestamp'] - position['entry_time']).total_seconds() / 3600
                current_price = row['close']

                # Calculate current R-multiple
                if position['direction'] == 'long':
                    pnl = current_price - position['entry_price']
                else:
                    pnl = position['entry_price'] - current_price

                initial_risk = abs(position['entry_price'] - position['initial_stop'])
                r_multiple = pnl / initial_risk if initial_risk > 0 else 0

                exit_triggered = False
                exit_reason = None
                exit_price = current_price

                # Trailing stop logic
                if self.config['use_trailing_stop'] and not position.get('partial_1_taken'):
                    if r_multiple >= 3.0:
                        position['stop_loss'] = position['entry_price']

                    if r_multiple >= 5.0:
                        atr = row['atr']
                        if position['direction'] == 'long':
                            new_stop = current_price - (2 * atr)
                            position['stop_loss'] = max(position['stop_loss'], new_stop)
                        else:
                            new_stop = current_price + (2 * atr)
                            position['stop_loss'] = min(position['stop_loss'], new_stop)

                # Partial exits
                if self.config['use_partial_exits']:
                    if r_multiple >= 2.0 and not position.get('partial_1_taken'):
                        position['partial_1_taken'] = True
                        position['remaining_size'] = position['position_size'] * 0.7
                        partial_pnl = position['position_size'] * 0.3 * (pnl / position['entry_price'])
                        self.capital += partial_pnl

                    if r_multiple >= 4.0 and not position.get('partial_2_taken'):
                        position['partial_2_taken'] = True
                        position['remaining_size'] = position['position_size'] * 0.3
                        partial_pnl = position['position_size'] * 0.4 * (pnl / position['entry_price'])
                        self.capital += partial_pnl

                # Stop loss check
                if position['direction'] == 'long' and current_price <= position['stop_loss']:
                    exit_triggered, exit_reason = True, 'Stop Loss'
                    exit_price = position['stop_loss']
                elif position['direction'] == 'short' and current_price >= position['stop_loss']:
                    exit_triggered, exit_reason = True, 'Stop Loss'
                    exit_price = position['stop_loss']

                # Take profit check
                if position['direction'] == 'long' and current_price >= position['take_profit']:
                    exit_triggered, exit_reason = True, 'Take Profit'
                    exit_price = position['take_profit']
                elif position['direction'] == 'short' and current_price <= position['take_profit']:
                    exit_triggered, exit_reason = True, 'Take Profit'
                    exit_price = position['take_profit']

                # Time stop
                if hours_held >= self.config['max_hold_hours']:
                    exit_triggered, exit_reason = True, 'Time Stop'

                if exit_triggered:
                    # Calculate final P&L
                    if position['direction'] == 'long':
                        final_pnl_pct = ((exit_price - position['entry_price']) / position['entry_price']) * 100
                    else:
                        final_pnl_pct = ((position['entry_price'] - exit_price) / position['entry_price']) * 100

                    remaining_size = position.get('remaining_size', position['position_size'])
                    final_pnl_pct -= (self.fee_rate * 2 * 100)  # Entry + exit fees
                    pnl_amount = remaining_size * (final_pnl_pct / 100)
                    self.capital += pnl_amount

                    total_pnl_pct = ((self.capital - position['capital_at_entry']) / position['capital_at_entry']) * 100

                    self.trades.append({
                        'trade_num': trade_count + 1,
                        'entry_time': position['entry_time'],
                        'exit_time': row['timestamp'],
                        'direction': position['direction'],
                        'pattern': position['pattern'],
                        'entry_price': position['entry_price'],
                        'exit_price': exit_price,
                        'stop_loss': position['initial_stop'],
                        'take_profit': position['take_profit'],
                        'exit_reason': exit_reason,
                        'pnl_pct': total_pnl_pct,
                        'pnl_amount': self.capital - position['capital_at_entry'],
                        'capital': self.capital,
                        'risk_pct': position['risk_pct'],
                        'hours_held': hours_held
                    })

                    self.update_risk_sizing(self.capital > position['capital_at_entry'])
                    trade_count += 1
                    in_position = False
                    position = None

            # Look for entry
            if not in_position:
                signal = self.detect_signal(idx)

                if signal:
                    atr = row['atr']
                    entry_price = row['close']

                    # Calculate stop and target
                    if signal['direction'] == 'long':
                        stop_loss = entry_price - (self.config['stop_atr_mult'] * atr)
                        take_profit = entry_price + (self.config['tp_atr_high_vol'] * atr)
                    else:
                        stop_loss = entry_price + (self.config['stop_atr_mult'] * atr)
                        take_profit = entry_price - (self.config['tp_atr_high_vol'] * atr)

                    # Position sizing
                    risk_per_share = abs(entry_price - stop_loss)
                    risk_dollar = self.capital * (self.current_risk_pct / 100)
                    position_size = risk_dollar / (risk_per_share / entry_price)

                    position = {
                        'direction': signal['direction'],
                        'pattern': signal['pattern'],
                        'entry_price': entry_price,
                        'entry_time': row['timestamp'],
                        'stop_loss': stop_loss,
                        'initial_stop': stop_loss,
                        'take_profit': take_profit,
                        'position_size': position_size,
                        'capital_at_entry': self.capital,
                        'risk_pct': self.current_risk_pct
                    }

                    in_position = True

        # Close any remaining position
        if in_position and position:
            row = self.df.iloc[-1]
            exit_price = row['close']

            if position['direction'] == 'long':
                final_pnl_pct = ((exit_price - position['entry_price']) / position['entry_price']) * 100
            else:
                final_pnl_pct = ((position['entry_price'] - exit_price) / position['entry_price']) * 100

            remaining_size = position.get('remaining_size', position['position_size'])
            final_pnl_pct -= (self.fee_rate * 2 * 100)
            pnl_amount = remaining_size * (final_pnl_pct / 100)
            self.capital += pnl_amount

            total_pnl_pct = ((self.capital - position['capital_at_entry']) / position['capital_at_entry']) * 100

            self.trades.append({
                'trade_num': trade_count + 1,
                'entry_time': position['entry_time'],
                'exit_time': row['timestamp'],
                'direction': position['direction'],
                'pattern': position['pattern'],
                'entry_price': position['entry_price'],
                'exit_price': exit_price,
                'stop_loss': position['initial_stop'],
                'take_profit': position['take_profit'],
                'exit_reason': 'End of Data',
                'pnl_pct': total_pnl_pct,
                'pnl_amount': self.capital - position['capital_at_entry'],
                'capital': self.capital,
                'risk_pct': position['risk_pct'],
                'hours_held': 0
            })

        return pd.DataFrame(self.trades)

# Run the backtest
bt = V7BaselineBacktest('/workspaces/Carebiuro_windykacja/fartcoin_usdt_1m_lbank.csv')
df_trades = bt.run()

# Calculate metrics
total_return = ((bt.capital - 10000) / 10000) * 100

df_trades['cumulative_pnl'] = df_trades['pnl_pct'].cumsum()
df_trades['running_peak'] = df_trades['cumulative_pnl'].expanding().max()
df_trades['drawdown'] = df_trades['cumulative_pnl'] - df_trades['running_peak']
max_drawdown = abs(df_trades['drawdown'].min())

rr_ratio = total_return / max_drawdown if max_drawdown > 0 else 0

wins = df_trades[df_trades['pnl_pct'] > 0]
losses = df_trades[df_trades['pnl_pct'] < 0]
win_rate = len(wins) / len(df_trades) * 100 if len(df_trades) > 0 else 0

gross_profit = wins['pnl_amount'].sum()
gross_loss = abs(losses['pnl_amount'].sum())
profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

# Print results
print("\n" + "=" * 80)
print("V7 BASELINE RESULTS - Trend + Distance 2%")
print("=" * 80)

print(f"\nTotal Trades: {len(df_trades)}")
print(f"Total Return: {total_return:.2f}%")
print(f"Max Drawdown: {max_drawdown:.2f}%")
print(f"R:R Ratio: {rr_ratio:.2f}x")
print(f"Win Rate: {win_rate:.1f}% ({len(wins)}/{len(df_trades)})")
print(f"Profit Factor: {profit_factor:.2f}")
print(f"Final Capital: ${bt.capital:,.2f}")

print(f"\nAverage Win: {wins['pnl_pct'].mean():.2f}%")
print(f"Average Loss: {losses['pnl_pct'].mean():.2f}%")
print(f"Largest Win: {wins['pnl_pct'].max():.2f}%")
print(f"Largest Loss: {losses['pnl_pct'].min():.2f}%")

# Save trades
output_file = '/workspaces/Carebiuro_windykacja/strategies/v7-baseline-trades.csv'
df_trades.to_csv(output_file, index=False)
print(f"\n✓ Saved trades to: {output_file}")

# Save summary
summary = {
    "config_name": "V7 Baseline - Trend + Distance 2%",
    "metrics": {
        "total_trades": len(df_trades),
        "total_return_pct": total_return,
        "max_drawdown_pct": max_drawdown,
        "rr_ratio": rr_ratio,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "avg_win": wins['pnl_pct'].mean() if len(wins) > 0 else 0,
        "avg_loss": losses['pnl_pct'].mean() if len(losses) > 0 else 0
    },
    "config": bt.config
}

with open('/workspaces/Carebiuro_windykacja/strategies/v7-baseline-summary.json', 'w') as f:
    json.dump(summary, f, indent=2)

print("\n" + "=" * 80)
print("ALL TRADES:")
print("=" * 80)
print(df_trades[['trade_num', 'entry_time', 'direction', 'entry_price', 'exit_price', 'exit_reason', 'pnl_pct', 'capital']].to_string(index=False))

print(f"\n✓ Complete! This is the exact V7 baseline with proper implementation.")
