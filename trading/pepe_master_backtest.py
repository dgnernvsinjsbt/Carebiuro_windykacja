#!/usr/bin/env python3
"""
PEPE/USDT Strategy Discovery - Comprehensive Backtest
Objective: Find profitable strategy with R:R >= 2.0
"""

import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Load data
print("Loading PEPE/USDT 1m data...")
df = pd.read_csv('pepe_usdt_1m_lbank.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print(f"Data: {len(df)} candles from {df['timestamp'].iloc[0]} to {df['timestamp'].iloc[-1]}")
print(f"Price range: ${df['close'].min():.8f} to ${df['close'].max():.8f}")
print(f"Average volume: {df['volume'].mean():.2e}\n")

# Calculate indicators
df['returns'] = df['close'].pct_change()

# Bollinger Bands (multiple periods)
for period in [20, 50, 100]:
    df[f'bb_mid_{period}'] = df['close'].rolling(period).mean()
    df[f'bb_std_{period}'] = df['close'].rolling(period).std()
    df[f'bb_upper_{period}'] = df[f'bb_mid_{period}'] + 2 * df[f'bb_std_{period}']
    df[f'bb_lower_{period}'] = df[f'bb_mid_{period}'] - 2 * df[f'bb_std_{period}']
    df[f'bb_width_{period}'] = (df[f'bb_upper_{period}'] - df[f'bb_lower_{period}']) / df[f'bb_mid_{period}']

# EMAs (multiple periods)
for period in [9, 20, 50, 100, 200]:
    df[f'ema_{period}'] = df['close'].ewm(span=period).mean()

# RSI
for period in [7, 14, 21]:
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = -delta.where(delta < 0, 0).rolling(period).mean()
    rs = gain / loss
    df[f'rsi_{period}'] = 100 - (100 / (1 + rs))

# MACD
df['macd'] = df['close'].ewm(span=12).mean() - df['close'].ewm(span=26).mean()
df['macd_signal'] = df['macd'].ewm(span=9).mean()
df['macd_hist'] = df['macd'] - df['macd_signal']

# ATR for volatility-based stops
for period in [10, 14, 20]:
    high_low = df['high'] - df['low']
    high_close = abs(df['high'] - df['close'].shift())
    low_close = abs(df['low'] - df['close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df[f'atr_{period}'] = tr.rolling(period).mean()

# Volume indicators
df['vol_sma_20'] = df['volume'].rolling(20).mean()
df['vol_ratio'] = df['volume'] / df['vol_sma_20']

# Volatility measures
df['volatility_10'] = df['returns'].rolling(10).std()
df['volatility_20'] = df['returns'].rolling(20).std()

# Session indicators (UTC)
df['hour'] = df['timestamp'].dt.hour
df['asian_session'] = (df['hour'] >= 0) & (df['hour'] < 8)
df['euro_session'] = (df['hour'] >= 8) & (df['hour'] < 14)
df['us_session'] = (df['hour'] >= 14) & (df['hour'] < 22)

# Drop NaN rows
df = df.dropna().reset_index(drop=True)
print(f"After indicators: {len(df)} candles\n")


def backtest_strategy(df, strategy_name, entry_signal, exit_signal=None,
                     fee_pct=0.1, use_atr_stops=False, atr_period=14,
                     atr_sl_mult=2.0, atr_tp_mult=4.0,
                     session_filter=None, vol_filter=None):
    """
    Generic backtesting function

    Parameters:
    - entry_signal: boolean series for entry
    - exit_signal: boolean series for exit (optional)
    - use_atr_stops: use ATR-based SL/TP instead of fixed
    - session_filter: 'asian', 'euro', 'us', or None
    - vol_filter: tuple (min_vol, max_vol) for volatility filtering
    """

    trades = []
    position = None

    for i in range(len(df)):
        row = df.iloc[i]

        # Session filter
        if session_filter == 'asian' and not row['asian_session']:
            continue
        elif session_filter == 'euro' and not row['euro_session']:
            continue
        elif session_filter == 'us' and not row['us_session']:
            continue

        # Volatility filter
        if vol_filter:
            min_vol, max_vol = vol_filter
            if row['volatility_20'] < min_vol or row['volatility_20'] > max_vol:
                continue

        # Entry logic
        if position is None and entry_signal.iloc[i]:
            entry_price = row['close']

            if use_atr_stops:
                atr_col = f'atr_{atr_period}'
                stop_loss = entry_price - (row[atr_col] * atr_sl_mult)
                take_profit = entry_price + (row[atr_col] * atr_tp_mult)
            else:
                # Fixed 2% SL, 4% TP for baseline
                stop_loss = entry_price * 0.98
                take_profit = entry_price * 1.04

            position = {
                'entry_time': row['timestamp'],
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'entry_idx': i
            }

        # Exit logic
        elif position is not None:
            exit_triggered = False
            exit_price = None
            exit_reason = None

            # Check SL/TP
            if row['low'] <= position['stop_loss']:
                exit_price = position['stop_loss']
                exit_reason = 'SL'
                exit_triggered = True
            elif row['high'] >= position['take_profit']:
                exit_price = position['take_profit']
                exit_reason = 'TP'
                exit_triggered = True
            elif exit_signal is not None and exit_signal.iloc[i]:
                exit_price = row['close']
                exit_reason = 'Signal'
                exit_triggered = True

            if exit_triggered:
                pnl_pct = ((exit_price / position['entry_price']) - 1) * 100
                pnl_net = pnl_pct - fee_pct

                trades.append({
                    'entry_time': position['entry_time'],
                    'exit_time': row['timestamp'],
                    'entry_price': position['entry_price'],
                    'exit_price': exit_price,
                    'pnl_gross': pnl_pct,
                    'pnl_net': pnl_net,
                    'exit_reason': exit_reason,
                    'duration_mins': i - position['entry_idx']
                })

                position = None

    # Calculate metrics
    if len(trades) == 0:
        return None

    trades_df = pd.DataFrame(trades)

    total_pnl = trades_df['pnl_net'].sum()
    win_trades = trades_df[trades_df['pnl_net'] > 0]
    loss_trades = trades_df[trades_df['pnl_net'] <= 0]

    win_rate = len(win_trades) / len(trades_df) * 100
    avg_win = win_trades['pnl_net'].mean() if len(win_trades) > 0 else 0
    avg_loss = loss_trades['pnl_net'].mean() if len(loss_trades) > 0 else 0

    # Calculate max drawdown
    cumulative = trades_df['pnl_net'].cumsum()
    running_max = cumulative.expanding().max()
    drawdown = cumulative - running_max
    max_dd = abs(drawdown.min()) if len(drawdown) > 0 else 0.01

    # R:R ratio
    rr_ratio = total_pnl / max_dd if max_dd > 0 else 0

    return {
        'strategy': strategy_name,
        'total_trades': len(trades_df),
        'win_rate': win_rate,
        'total_pnl': total_pnl,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'max_dd': max_dd,
        'rr_ratio': rr_ratio,
        'avg_duration_mins': trades_df['duration_mins'].mean()
    }


# =============================================================================
# STRATEGY DEFINITIONS
# =============================================================================

results = []

print("=" * 80)
print("TESTING STRATEGIES FOR PEPE/USDT")
print("=" * 80)

# -----------------------------------------------------------------------------
# 1. BOLLINGER BAND MEAN REVERSION (Multiple Configurations)
# -----------------------------------------------------------------------------
print("\n[1] Testing Bollinger Band Mean Reversion Strategies...")

for bb_period in [20, 50, 100]:
    for session in [None, 'asian', 'euro', 'us']:
        for atr_mult in [(1.5, 3.0), (2.0, 4.0), (3.0, 6.0)]:

            # Long: Buy at lower band, sell at upper band
            entry_long = df['close'] < df[f'bb_lower_{bb_period}']
            exit_long = df['close'] > df[f'bb_upper_{bb_period}']

            session_name = session if session else '24h'
            strategy_name = f"BB{bb_period}_Long_{session_name}_ATR_{atr_mult[0]}x{atr_mult[1]}"

            result = backtest_strategy(
                df, strategy_name, entry_long, exit_long,
                fee_pct=0.1, use_atr_stops=True, atr_period=14,
                atr_sl_mult=atr_mult[0], atr_tp_mult=atr_mult[1],
                session_filter=session
            )

            if result and result['total_trades'] >= 30:
                results.append(result)
                print(f"  {strategy_name}: {result['total_trades']} trades, "
                      f"WR={result['win_rate']:.1f}%, PnL={result['total_pnl']:.2f}%, "
                      f"R:R={result['rr_ratio']:.2f}")

# -----------------------------------------------------------------------------
# 2. EMA TREND FOLLOWING
# -----------------------------------------------------------------------------
print("\n[2] Testing EMA Trend Following Strategies...")

for fast_ema in [9, 20]:
    for slow_ema in [50, 100, 200]:
        if fast_ema >= slow_ema:
            continue

        for session in [None, 'asian', 'euro', 'us']:
            for atr_mult in [(2.0, 4.0), (3.0, 6.0)]:

                # Long: Fast EMA crosses above slow EMA
                entry_long = (df[f'ema_{fast_ema}'] > df[f'ema_{slow_ema}']) & \
                            (df[f'ema_{fast_ema}'].shift(1) <= df[f'ema_{slow_ema}'].shift(1))

                exit_long = (df[f'ema_{fast_ema}'] < df[f'ema_{slow_ema}']) & \
                           (df[f'ema_{fast_ema}'].shift(1) >= df[f'ema_{slow_ema}'].shift(1))

                session_name = session if session else '24h'
                strategy_name = f"EMA{fast_ema}_{slow_ema}_Long_{session_name}_ATR_{atr_mult[0]}x{atr_mult[1]}"

                result = backtest_strategy(
                    df, strategy_name, entry_long, exit_long,
                    fee_pct=0.1, use_atr_stops=True, atr_period=14,
                    atr_sl_mult=atr_mult[0], atr_tp_mult=atr_mult[1],
                    session_filter=session
                )

                if result and result['total_trades'] >= 30:
                    results.append(result)
                    print(f"  {strategy_name}: {result['total_trades']} trades, "
                          f"WR={result['win_rate']:.1f}%, PnL={result['total_pnl']:.2f}%, "
                          f"R:R={result['rr_ratio']:.2f}")

# -----------------------------------------------------------------------------
# 3. RSI MEAN REVERSION
# -----------------------------------------------------------------------------
print("\n[3] Testing RSI Mean Reversion Strategies...")

for rsi_period in [7, 14, 21]:
    for oversold in [20, 25, 30]:
        for overbought in [70, 75, 80]:
            for session in [None, 'asian', 'euro', 'us']:

                # Long: RSI oversold
                entry_long = df[f'rsi_{rsi_period}'] < oversold
                exit_long = df[f'rsi_{rsi_period}'] > overbought

                session_name = session if session else '24h'
                strategy_name = f"RSI{rsi_period}_{oversold}_{overbought}_{session_name}"

                result = backtest_strategy(
                    df, strategy_name, entry_long, exit_long,
                    fee_pct=0.1, use_atr_stops=True, atr_period=14,
                    atr_sl_mult=2.0, atr_tp_mult=4.0,
                    session_filter=session
                )

                if result and result['total_trades'] >= 30:
                    results.append(result)
                    print(f"  {strategy_name}: {result['total_trades']} trades, "
                          f"WR={result['win_rate']:.1f}%, PnL={result['total_pnl']:.2f}%, "
                          f"R:R={result['rr_ratio']:.2f}")

# -----------------------------------------------------------------------------
# 4. MACD MOMENTUM
# -----------------------------------------------------------------------------
print("\n[4] Testing MACD Momentum Strategies...")

for session in [None, 'asian', 'euro', 'us']:
    for atr_mult in [(2.0, 4.0), (3.0, 6.0)]:

        # Long: MACD crosses above signal
        entry_long = (df['macd'] > df['macd_signal']) & \
                    (df['macd'].shift(1) <= df['macd_signal'].shift(1))

        exit_long = (df['macd'] < df['macd_signal']) & \
                   (df['macd'].shift(1) >= df['macd_signal'].shift(1))

        session_name = session if session else '24h'
        strategy_name = f"MACD_Long_{session_name}_ATR_{atr_mult[0]}x{atr_mult[1]}"

        result = backtest_strategy(
            df, strategy_name, entry_long, exit_long,
            fee_pct=0.1, use_atr_stops=True, atr_period=14,
            atr_sl_mult=atr_mult[0], atr_tp_mult=atr_mult[1],
            session_filter=session
        )

        if result and result['total_trades'] >= 30:
            results.append(result)
            print(f"  {strategy_name}: {result['total_trades']} trades, "
                  f"WR={result['win_rate']:.1f}%, PnL={result['total_pnl']:.2f}%, "
                  f"R:R={result['rr_ratio']:.2f}")

# -----------------------------------------------------------------------------
# 5. VOLUME SURGE MOMENTUM (Meme Coin Specific)
# -----------------------------------------------------------------------------
print("\n[5] Testing Volume Surge Momentum Strategies...")

for vol_threshold in [2.0, 3.0, 5.0]:
    for session in [None, 'asian', 'euro', 'us']:

        # Long: Volume spike + price rising
        entry_long = (df['vol_ratio'] > vol_threshold) & (df['close'] > df['close'].shift(1))

        session_name = session if session else '24h'
        strategy_name = f"VolSurge_{vol_threshold}x_{session_name}"

        result = backtest_strategy(
            df, strategy_name, entry_long, exit_signal=None,
            fee_pct=0.1, use_atr_stops=True, atr_period=14,
            atr_sl_mult=2.0, atr_tp_mult=4.0,
            session_filter=session
        )

        if result and result['total_trades'] >= 30:
            results.append(result)
            print(f"  {strategy_name}: {result['total_trades']} trades, "
                  f"WR={result['win_rate']:.1f}%, PnL={result['total_pnl']:.2f}%, "
                  f"R:R={result['rr_ratio']:.2f}")

# -----------------------------------------------------------------------------
# 6. VOLATILITY BREAKOUT
# -----------------------------------------------------------------------------
print("\n[6] Testing Volatility Breakout Strategies...")

for bb_period in [20, 50]:
    for width_threshold in [0.02, 0.03, 0.04]:  # BB width thresholds
        for session in [None, 'asian', 'euro', 'us']:

            # Long: Bollinger squeeze followed by breakout
            squeeze = df[f'bb_width_{bb_period}'] < width_threshold
            breakout_up = (df['close'] > df[f'bb_upper_{bb_period}']) & squeeze.shift(1)

            session_name = session if session else '24h'
            strategy_name = f"BBSqueeze{bb_period}_{width_threshold}_{session_name}"

            result = backtest_strategy(
                df, strategy_name, breakout_up, exit_signal=None,
                fee_pct=0.1, use_atr_stops=True, atr_period=14,
                atr_sl_mult=2.0, atr_tp_mult=5.0,
                session_filter=session
            )

            if result and result['total_trades'] >= 30:
                results.append(result)
                print(f"  {strategy_name}: {result['total_trades']} trades, "
                      f"WR={result['win_rate']:.1f}%, PnL={result['total_pnl']:.2f}%, "
                      f"R:R={result['rr_ratio']:.2f}")

# -----------------------------------------------------------------------------
# 7. HYBRID: EMA + RSI COMBO
# -----------------------------------------------------------------------------
print("\n[7] Testing Hybrid EMA + RSI Strategies...")

for session in [None, 'asian', 'euro', 'us']:
    # Long: Price above EMA20, RSI oversold (pullback in uptrend)
    entry_long = (df['close'] > df['ema_20']) & (df['rsi_14'] < 30)
    exit_long = df['rsi_14'] > 70

    session_name = session if session else '24h'
    strategy_name = f"EMA20_RSI_Pullback_{session_name}"

    result = backtest_strategy(
        df, strategy_name, entry_long, exit_long,
        fee_pct=0.1, use_atr_stops=True, atr_period=14,
        atr_sl_mult=2.0, atr_tp_mult=4.0,
        session_filter=session
    )

    if result and result['total_trades'] >= 30:
        results.append(result)
        print(f"  {strategy_name}: {result['total_trades']} trades, "
              f"WR={result['win_rate']:.1f}%, PnL={result['total_pnl']:.2f}%, "
              f"R:R={result['rr_ratio']:.2f}")

# =============================================================================
# RESULTS COMPILATION
# =============================================================================

if len(results) == 0:
    print("\nNo strategies met minimum requirements (30+ trades)")
else:
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('rr_ratio', ascending=False)

    # Save all results
    results_df.to_csv('results/pepe_master_results.csv', index=False)
    print(f"\n{'=' * 80}")
    print(f"TOTAL STRATEGIES TESTED: {len(results_df)}")
    print(f"Results saved to: results/pepe_master_results.csv")
    print(f"{'=' * 80}")

    # Show top 20 strategies
    print("\nTOP 20 STRATEGIES BY R:R RATIO:")
    print("=" * 80)

    top20 = results_df.head(20)
    for idx, row in top20.iterrows():
        print(f"\n{row['strategy']}")
        print(f"  Trades: {row['total_trades']}")
        print(f"  Win Rate: {row['win_rate']:.1f}%")
        print(f"  Total PnL: {row['total_pnl']:.2f}%")
        print(f"  Avg Win: {row['avg_win']:.2f}% | Avg Loss: {row['avg_loss']:.2f}%")
        print(f"  Max DD: {row['max_dd']:.2f}%")
        print(f"  R:R Ratio: {row['rr_ratio']:.2f}")
        print(f"  Avg Duration: {row['avg_duration_mins']:.0f} mins")

    # Filter strategies with R:R >= 2.0
    profitable = results_df[results_df['rr_ratio'] >= 2.0]

    if len(profitable) > 0:
        print(f"\n{'=' * 80}")
        print(f"STRATEGIES WITH R:R >= 2.0: {len(profitable)}")
        print(f"{'=' * 80}")

        for idx, row in profitable.iterrows():
            print(f"\n{row['strategy']}")
            print(f"  R:R: {row['rr_ratio']:.2f} | PnL: {row['total_pnl']:.2f}% | "
                  f"WR: {row['win_rate']:.1f}% | Trades: {row['total_trades']}")
    else:
        print(f"\n{'=' * 80}")
        print("NO STRATEGIES ACHIEVED R:R >= 2.0")
        print("Consider:")
        print("  1. Different timeframes (5m, 15m)")
        print("  2. Short strategies")
        print("  3. Different fee structures (limit orders)")
        print("  4. More aggressive volatility filters")
        print(f"{'=' * 80}")

print("\nBacktest complete!")
