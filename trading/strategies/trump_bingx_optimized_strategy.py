#!/usr/bin/env python3
"""
TRUMP Volume Zones - BingX Optimized Strategy (v2.0)

Performance:
- Return/DD: 7.94x
- Return: +9.01% (32 days)
- Max DD: -1.14%
- Win Rate: 61.5%
- Trades: 13
- Top 20% Concentration: 55.4%

Configuration:
- Zone Detection: 1.3x volume, 3+ bars
- Direction: SHORT ONLY
- Stop Loss: 0.5% fixed
- Take Profit: 5:1 R:R (2.5%)
- Session: ALL (24/7)
- Limit Orders: YES (0.035% offset)
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class VolumeZone:
    """Represents a detected volume zone"""
    start_idx: int
    end_idx: int
    zone_bars: int
    zone_high: float
    zone_low: float
    entry_idx: int
    entry_price: float
    atr: float
    zone_type: str  # 'accumulation' or 'distribution'

@dataclass
class Trade:
    """Represents a completed trade"""
    direction: str
    entry_idx: int
    entry_price: float
    exit_idx: int
    exit_price: float
    exit_reason: str  # 'SL', 'TP', 'TIME'
    pnl: float
    pnl_pct: float
    bars_held: int
    zone_bars: int

class TRUMPVolumeZonesStrategy:
    """
    TRUMP Volume Zones Strategy - BingX Optimized

    Detects distribution zones (sustained volume at local highs) and
    enters SHORT positions with 0.5% stop loss and 5:1 R:R take profit.
    """

    def __init__(self, config: Optional[Dict] = None):
        """Initialize strategy with configuration"""
        self.config = config or self._default_config()

    def _default_config(self) -> Dict:
        """Return default BingX-optimized configuration"""
        return {
            # Zone Detection
            'volume_threshold': 1.3,
            'min_consecutive_bars': 3,
            'max_consecutive_bars': 15,
            'lookback_period': 20,
            'lookahead_period': 5,

            # Entry
            'direction': 'SHORT',  # SHORT ONLY for BingX
            'use_limit_orders': True,
            'limit_offset_pct': 0.035,

            # Exit
            'sl_type': 'fixed_pct',
            'sl_value': 0.5,
            'tp_type': 'rr_multiple',
            'tp_value': 5.0,
            'max_hold_bars': 90,

            # Fees
            'maker_fee': 0.0002,  # 0.02%
            'taker_fee': 0.0005,  # 0.05%

            # Risk Management
            'risk_per_trade': 0.01,  # 1% of capital
        }

    def prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate indicators needed for strategy"""
        df = df.copy()

        # Basic OHLCV
        df['range'] = df['high'] - df['low']
        df['body'] = df['close'] - df['open']

        # ATR for volatility measurement
        df['atr'] = df['range'].rolling(14).mean()
        df['atr_pct'] = (df['atr'] / df['close']) * 100

        # Volume indicators
        df['vol_ma'] = df['volume'].rolling(20).mean()
        df['vol_ratio'] = df['volume'] / df['vol_ma']

        return df

    def detect_volume_zones(self, df: pd.DataFrame) -> List[Dict]:
        """
        Detect sustained volume zones (3+ consecutive bars above 1.3x average)
        """
        zones = []
        in_zone = False
        zone_start = None
        zone_bars = 0

        vol_threshold = self.config['volume_threshold']
        min_bars = self.config['min_consecutive_bars']
        max_bars = self.config['max_consecutive_bars']

        for i in range(len(df)):
            if pd.isna(df.loc[i, 'vol_ratio']):
                continue

            is_elevated = df.loc[i, 'vol_ratio'] >= vol_threshold

            if is_elevated:
                if not in_zone:
                    in_zone = True
                    zone_start = i
                    zone_bars = 1
                else:
                    zone_bars += 1
                    # Cap zone length at max_bars
                    if zone_bars > max_bars:
                        if zone_bars >= min_bars:
                            zones.append({
                                'start': zone_start,
                                'end': i - 1,
                                'bars': zone_bars - 1
                            })
                        zone_start = i
                        zone_bars = 1
            else:
                if in_zone:
                    if zone_bars >= min_bars:
                        zones.append({
                            'start': zone_start,
                            'end': i - 1,
                            'bars': zone_bars
                        })
                    in_zone = False
                    zone_start = None
                    zone_bars = 0

        # Handle final zone
        if in_zone and zone_bars >= min_bars:
            zones.append({
                'start': zone_start,
                'end': len(df) - 1,
                'bars': zone_bars
            })

        return zones

    def classify_zones(self, df: pd.DataFrame, zones: List[Dict]) -> List[VolumeZone]:
        """
        Classify zones as accumulation (at lows) or distribution (at highs)

        For BingX optimized strategy, we only use DISTRIBUTION zones (SHORT only)
        """
        distribution_zones = []

        lookback = self.config['lookback_period']
        lookahead = self.config['lookahead_period']

        for zone in zones:
            start_idx = zone['start']
            end_idx = zone['end']

            # Need buffer before and after
            if start_idx < lookback or end_idx >= len(df) - lookahead - 1:
                continue

            zone_low = df.loc[start_idx:end_idx, 'low'].min()
            zone_high = df.loc[start_idx:end_idx, 'high'].max()

            lookback_start = max(0, start_idx - lookback)
            lookahead_end = min(len(df), end_idx + lookahead)

            # Distribution zone: volume spike at local high
            if zone_high == df.loc[lookback_start:lookahead_end, 'high'].max():
                entry_idx = end_idx + 1

                if entry_idx < len(df) and not pd.isna(df.loc[entry_idx, 'atr']):
                    distribution_zones.append(VolumeZone(
                        start_idx=start_idx,
                        end_idx=end_idx,
                        zone_bars=zone['bars'],
                        zone_high=zone_high,
                        zone_low=zone_low,
                        entry_idx=entry_idx,
                        entry_price=df.loc[entry_idx, 'close'],
                        atr=df.loc[entry_idx, 'atr'],
                        zone_type='distribution'
                    ))

        return distribution_zones

    def backtest(self, df: pd.DataFrame) -> tuple:
        """
        Backtest strategy on historical data

        Returns: (trades, equity_curve)
        """
        df = self.prepare_data(df)

        # Detect and classify zones
        raw_zones = self.detect_volume_zones(df)
        distribution_zones = self.classify_zones(df, raw_zones)

        print(f"Detected {len(raw_zones)} raw volume zones")
        print(f"Classified {len(distribution_zones)} distribution zones (SHORT setups)")

        trades = []

        # Only trade SHORT (distribution zones)
        for zone in distribution_zones:
            trade = self._execute_short_trade(df, zone)
            if trade:
                trades.append(trade)

        return trades, self._calculate_equity_curve(trades)

    def _execute_short_trade(self, df: pd.DataFrame, zone: VolumeZone) -> Optional[Trade]:
        """Execute a SHORT trade based on distribution zone"""
        entry_idx = zone.entry_idx
        entry_price = zone.entry_price

        # Limit order adjustment
        if self.config['use_limit_orders']:
            entry_price = entry_price * (1 + self.config['limit_offset_pct'] / 100)

        # Calculate stop loss
        if self.config['sl_type'] == 'fixed_pct':
            sl_distance = entry_price * (self.config['sl_value'] / 100)
            stop_loss = entry_price + sl_distance
        elif self.config['sl_type'] == 'atr':
            sl_distance = self.config['sl_value'] * zone.atr
            stop_loss = entry_price + sl_distance
        else:
            raise ValueError(f"Unknown sl_type: {self.config['sl_type']}")

        # Calculate take profit
        if self.config['tp_type'] == 'rr_multiple':
            take_profit = entry_price - (self.config['tp_value'] * sl_distance)
        elif self.config['tp_type'] == 'fixed_pct':
            take_profit = entry_price * (1 - self.config['tp_value'] / 100)
        elif self.config['tp_type'] == 'atr':
            take_profit = entry_price - (self.config['tp_value'] * zone.atr)
        else:
            raise ValueError(f"Unknown tp_type: {self.config['tp_type']}")

        # Simulate trade execution
        max_hold = self.config['max_hold_bars']

        for i in range(1, max_hold + 1):
            if entry_idx + i >= len(df):
                break

            candle = df.iloc[entry_idx + i]

            # Check stop loss (price moves against us)
            if candle['high'] >= stop_loss:
                fee = self._calculate_fee(True)
                exit_price = stop_loss
                pnl = (entry_price / exit_price - 1) - fee

                return Trade(
                    direction='SHORT',
                    entry_idx=entry_idx,
                    entry_price=entry_price,
                    exit_idx=entry_idx + i,
                    exit_price=exit_price,
                    exit_reason='SL',
                    pnl=pnl,
                    pnl_pct=pnl * 100,
                    bars_held=i,
                    zone_bars=zone.zone_bars
                )

            # Check take profit (price moves in our favor)
            if candle['low'] <= take_profit:
                fee = self._calculate_fee(True)
                exit_price = take_profit
                pnl = (entry_price / exit_price - 1) - fee

                return Trade(
                    direction='SHORT',
                    entry_idx=entry_idx,
                    entry_price=entry_price,
                    exit_idx=entry_idx + i,
                    exit_price=exit_price,
                    exit_reason='TP',
                    pnl=pnl,
                    pnl_pct=pnl * 100,
                    bars_held=i,
                    zone_bars=zone.zone_bars
                )

        # Time exit
        exit_idx = entry_idx + max_hold
        if exit_idx < len(df):
            fee = self._calculate_fee(False)
            exit_price = df.iloc[exit_idx]['close']
            pnl = (entry_price / exit_price - 1) - fee

            return Trade(
                direction='SHORT',
                entry_idx=entry_idx,
                entry_price=entry_price,
                exit_idx=exit_idx,
                exit_price=exit_price,
                exit_reason='TIME',
                pnl=pnl,
                pnl_pct=pnl * 100,
                bars_held=max_hold,
                zone_bars=zone.zone_bars
            )

        return None

    def _calculate_fee(self, hit_sl_or_tp: bool) -> float:
        """Calculate trading fees"""
        if self.config['use_limit_orders']:
            # Limit entry (maker) + market exit (taker)
            return self.config['maker_fee'] + self.config['taker_fee']
        else:
            # Market orders both ways
            return 2 * self.config['taker_fee']

    def _calculate_equity_curve(self, trades: List[Trade]) -> pd.Series:
        """Calculate cumulative equity curve from trades"""
        if not trades:
            return pd.Series([0])

        pnls = [t.pnl * 100 for t in trades]
        return pd.Series(pnls).cumsum()

    def generate_report(self, trades: List[Trade], df: pd.DataFrame) -> Dict:
        """Generate performance report"""
        if not trades:
            return {'error': 'No trades generated'}

        trades_df = pd.DataFrame([vars(t) for t in trades])

        total_return = trades_df['pnl'].sum() * 100
        win_rate = (trades_df['pnl'] > 0).mean() * 100

        winners = trades_df[trades_df['pnl'] > 0]
        losers = trades_df[trades_df['pnl'] <= 0]

        avg_winner = winners['pnl'].mean() * 100 if len(winners) > 0 else 0
        avg_loser = losers['pnl'].mean() * 100 if len(losers) > 0 else 0
        profit_factor = abs(winners['pnl'].sum() / losers['pnl'].sum()) if len(losers) > 0 and losers['pnl'].sum() != 0 else 0

        # Calculate max drawdown
        cumulative = (trades_df['pnl'] * 100).cumsum()
        running_max = cumulative.cummax()
        drawdown = cumulative - running_max
        max_dd = drawdown.min()

        return_dd_ratio = abs(total_return / max_dd) if max_dd < 0 else 0

        # Outlier analysis
        sorted_trades = trades_df.sort_values('pnl', ascending=False)
        top_20_pct = max(1, int(len(sorted_trades) * 0.2))
        top_20_contribution = sorted_trades.head(top_20_pct)['pnl'].sum() / sorted_trades['pnl'].sum() * 100

        # Exit reason breakdown
        exit_reasons = trades_df['exit_reason'].value_counts()

        return {
            'total_trades': len(trades),
            'total_return': total_return,
            'max_drawdown': max_dd,
            'return_dd_ratio': return_dd_ratio,
            'win_rate': win_rate,
            'avg_winner': avg_winner,
            'avg_loser': avg_loser,
            'profit_factor': profit_factor,
            'avg_bars_held': trades_df['bars_held'].mean(),
            'top_20_concentration': top_20_contribution,
            'exit_reasons': exit_reasons.to_dict(),
            'trades_df': trades_df
        }

def main():
    """Example usage"""
    import sys

    # Load data
    if len(sys.argv) > 1:
        data_file = sys.argv[1]
    else:
        data_file = '/workspaces/Carebiuro_windykacja/trading/trumpsol_30d_bingx.csv'

    print(f"Loading data from {data_file}...")
    df = pd.read_csv(data_file)
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    print(f"Loaded {len(df):,} candles from {df['timestamp'].min()} to {df['timestamp'].max()}")

    # Initialize strategy
    strategy = TRUMPVolumeZonesStrategy()

    # Backtest
    print("\nRunning backtest...")
    trades, equity = strategy.backtest(df)

    # Generate report
    report = strategy.generate_report(trades, df)

    print("\n" + "="*80)
    print("TRUMP VOLUME ZONES - BingX Optimized Strategy Results")
    print("="*80)
    print(f"Total Trades:          {report['total_trades']}")
    print(f"Total Return:          {report['total_return']:+.2f}%")
    print(f"Max Drawdown:          {report['max_drawdown']:.2f}%")
    print(f"Return/DD Ratio:       {report['return_dd_ratio']:.2f}x")
    print(f"Win Rate:              {report['win_rate']:.1f}%")
    print(f"Avg Winner:            {report['avg_winner']:+.2f}%")
    print(f"Avg Loser:             {report['avg_loser']:+.2f}%")
    print(f"Profit Factor:         {report['profit_factor']:.2f}")
    print(f"Avg Hold Time:         {report['avg_bars_held']:.1f} bars")
    print(f"Top 20% Concentration: {report['top_20_concentration']:.1f}%")
    print("\nExit Reasons:")
    for reason, count in report['exit_reasons'].items():
        print(f"  {reason}: {count} trades ({count/report['total_trades']*100:.1f}%)")

    # Save trades
    output_file = 'results/TRUMP_bingx_strategy_backtest.csv'
    report['trades_df'].to_csv(output_file, index=False)
    print(f"\n✅ Trades saved to {output_file}")

if __name__ == '__main__':
    main()
