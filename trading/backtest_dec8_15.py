#!/usr/bin/env python3
"""
Backtest all 9 RSI strategies on Dec 8-15 period with fresh data
Portfolio simulation with 10% position sizing and compounding
"""

import pandas as pd
import numpy as np
from datetime import datetime

# Optimal parameters from 90-day optimization (with corrected RSI)
OPTIMAL_CONFIGS = {
    'MELANIA-USDT': {'rsi_low': 25, 'rsi_high': 75, 'limit_offset_pct': 1.5, 'stop_atr_mult': 1.0, 'tp_atr_mult': 3.0},
    'MOODENG-USDT': {'rsi_low': 27, 'rsi_high': 65, 'limit_offset_pct': 1.0, 'stop_atr_mult': 1.5, 'tp_atr_mult': 2.0},
    'XLM-USDT': {'rsi_low': 30, 'rsi_high': 70, 'limit_offset_pct': 2.0, 'stop_atr_mult': 1.0, 'tp_atr_mult': 2.0},
    'PEPE-USDT': {'rsi_low': 27, 'rsi_high': 70, 'limit_offset_pct': 0.5, 'stop_atr_mult': 1.5, 'tp_atr_mult': 1.0},
    'AIXBT-USDT': {'rsi_low': 27, 'rsi_high': 65, 'limit_offset_pct': 1.0, 'stop_atr_mult': 2.0, 'tp_atr_mult': 1.0},
    'DOGE-USDT': {'rsi_low': 25, 'rsi_high': 70, 'limit_offset_pct': 0.5, 'stop_atr_mult': 1.5, 'tp_atr_mult': 1.0},
    'TRUMPSOL-USDT': {'rsi_low': 25, 'rsi_high': 65, 'limit_offset_pct': 1.0, 'stop_atr_mult': 1.5, 'tp_atr_mult': 0.5},
    'UNI-USDT': {'rsi_low': 30, 'rsi_high': 65, 'limit_offset_pct': 1.5, 'stop_atr_mult': 1.0, 'tp_atr_mult': 3.0},
    'CRV-USDT': {'rsi_low': 30, 'rsi_high': 70, 'limit_offset_pct': 2.0, 'stop_atr_mult': 1.0, 'tp_atr_mult': 0.5},
}

def wilder_rsi(data: pd.Series, period: int = 14) -> pd.Series:
    """Wilder's RSI (corrected version)"""
    delta = data.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = pd.Series(index=data.index, dtype=float)
    avg_loss = pd.Series(index=data.index, dtype=float)

    avg_gain.iloc[period] = gain.iloc[1:period+1].mean()
    avg_loss.iloc[period] = loss.iloc[1:period+1].mean()

    for i in range(period + 1, len(data)):
        avg_gain.iloc[i] = (avg_gain.iloc[i-1] * (period - 1) + gain.iloc[i]) / period
        avg_loss.iloc[i] = (avg_loss.iloc[i-1] * (period - 1) + loss.iloc[i]) / period

    rs = avg_gain / avg_loss
    rsi_values = 100 - (100 / (1 + rs))
    return rsi_values

def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average True Range"""
    high = df['high']
    low = df['low']
    close = df['close']

    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    atr_values = tr.rolling(window=period).mean()
    return atr_values

def backtest_strategy(df: pd.DataFrame, symbol: str, config: dict):
    """Backtest single strategy"""
    df = df.copy()

    # Calculate indicators
    df['rsi'] = wilder_rsi(df['close'], 14)
    df['atr'] = atr(df, 14)

    # Identify signals
    df['rsi_prev'] = df['rsi'].shift(1)

    # LONG: RSI crosses above rsi_low
    df['long_signal'] = (df['rsi'] > config['rsi_low']) & (df['rsi_prev'] <= config['rsi_low'])

    # SHORT: RSI crosses below rsi_high
    df['short_signal'] = (df['rsi'] < config['rsi_high']) & (df['rsi_prev'] >= config['rsi_high'])

    trades = []

    # Process signals
    for i in range(len(df)):
        if pd.isna(df['rsi'].iloc[i]) or pd.isna(df['atr'].iloc[i]):
            continue

        row = df.iloc[i]
        signal_price = row['close']
        signal_time = row['timestamp']

        # LONG signals
        if row['long_signal']:
            # Limit order: buy ABOVE current price
            limit_price = signal_price * (1 + config['limit_offset_pct'] / 100)

            # Check next 5 bars for fill
            filled = False
            fill_price = None
            fill_time = None

            for j in range(i+1, min(i+6, len(df))):
                if df['high'].iloc[j] >= limit_price:
                    fill_price = limit_price
                    fill_time = df['timestamp'].iloc[j]
                    fill_idx = j
                    filled = True
                    break

            if not filled:
                continue

            # Set stops
            atr_val = df['atr'].iloc[fill_idx]
            stop_loss = fill_price - (config['stop_atr_mult'] * atr_val)
            take_profit = fill_price + (config['tp_atr_mult'] * atr_val)

            # Find exit
            exit_price = None
            exit_time = None
            exit_reason = None

            for k in range(fill_idx+1, len(df)):
                bar = df.iloc[k]

                # Check SL
                if bar['low'] <= stop_loss:
                    exit_price = stop_loss
                    exit_time = bar['timestamp']
                    exit_reason = 'SL'
                    break

                # Check TP
                if bar['high'] >= take_profit:
                    exit_price = take_profit
                    exit_time = bar['timestamp']
                    exit_reason = 'TP'
                    break

                # Check RSI exit (crosses below rsi_high)
                if bar['rsi'] < config['rsi_high'] and df['rsi'].iloc[k-1] >= config['rsi_high']:
                    exit_price = bar['close']
                    exit_time = bar['timestamp']
                    exit_reason = 'RSI_EXIT'
                    break

            if exit_price:
                pnl_pct = ((exit_price - fill_price) / fill_price) * 100
                trades.append({
                    'symbol': symbol,
                    'direction': 'LONG',
                    'signal_time': signal_time,
                    'signal_price': signal_price,
                    'entry_time': fill_time,
                    'entry_price': fill_price,
                    'exit_time': exit_time,
                    'exit_price': exit_price,
                    'exit_reason': exit_reason,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'pnl_pct': pnl_pct,
                    'atr': atr_val
                })

        # SHORT signals
        elif row['short_signal']:
            # Limit order: sell BELOW current price
            limit_price = signal_price * (1 - config['limit_offset_pct'] / 100)

            # Check next 5 bars for fill
            filled = False
            fill_price = None
            fill_time = None

            for j in range(i+1, min(i+6, len(df))):
                if df['low'].iloc[j] <= limit_price:
                    fill_price = limit_price
                    fill_time = df['timestamp'].iloc[j]
                    fill_idx = j
                    filled = True
                    break

            if not filled:
                continue

            # Set stops
            atr_val = df['atr'].iloc[fill_idx]
            stop_loss = fill_price + (config['stop_atr_mult'] * atr_val)
            take_profit = fill_price - (config['tp_atr_mult'] * atr_val)

            # Find exit
            exit_price = None
            exit_time = None
            exit_reason = None

            for k in range(fill_idx+1, len(df)):
                bar = df.iloc[k]

                # Check SL
                if bar['high'] >= stop_loss:
                    exit_price = stop_loss
                    exit_time = bar['timestamp']
                    exit_reason = 'SL'
                    break

                # Check TP
                if bar['low'] <= take_profit:
                    exit_price = take_profit
                    exit_time = bar['timestamp']
                    exit_reason = 'TP'
                    break

                # Check RSI exit (crosses above rsi_low)
                if bar['rsi'] > config['rsi_low'] and df['rsi'].iloc[k-1] <= config['rsi_low']:
                    exit_price = bar['close']
                    exit_time = bar['timestamp']
                    exit_reason = 'RSI_EXIT'
                    break

            if exit_price:
                pnl_pct = ((fill_price - exit_price) / fill_price) * 100
                trades.append({
                    'symbol': symbol,
                    'direction': 'SHORT',
                    'signal_time': signal_time,
                    'signal_price': signal_price,
                    'entry_time': fill_time,
                    'entry_price': fill_price,
                    'exit_time': exit_time,
                    'exit_price': exit_price,
                    'exit_reason': exit_reason,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'pnl_pct': pnl_pct,
                    'atr': atr_val
                })

    return trades

def main():
    print("=" * 80)
    print("BACKTEST: DEC 8-15, 2025 (Fresh Data)")
    print("=" * 80)

    # Map coin names to files
    coin_files = {
        'MELANIA-USDT': 'melania_recent_10d.csv',
        'CRV-USDT': 'crv_recent_10d.csv',
        'XLM-USDT': 'xlm_recent_10d.csv',
        'PEPE-USDT': '1000pepe_recent_10d.csv',
        'DOGE-USDT': 'doge_recent_10d.csv',
        'AIXBT-USDT': 'aixbt_recent_10d.csv',
        'UNI-USDT': 'uni_recent_10d.csv',
        'MOODENG-USDT': 'moodeng_recent_10d.csv',
        'TRUMPSOL-USDT': 'trumpsol_recent_10d.csv',
    }

    all_trades = []

    # Run backtest for each coin
    for symbol, filename in coin_files.items():
        print(f"\nProcessing {symbol}...")

        df = pd.read_csv(filename)
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        # Filter to Dec 8-15 period
        df = df[(df['timestamp'] >= '2025-12-08 00:00:00') &
                (df['timestamp'] <= '2025-12-15 23:59:59')]

        print(f"  Data range: {df['timestamp'].min()} to {df['timestamp'].max()}")
        print(f"  Candles: {len(df)}")

        config = OPTIMAL_CONFIGS[symbol]
        trades = backtest_strategy(df, symbol, config)

        print(f"  Trades: {len(trades)}")
        all_trades.extend(trades)

    # Convert to DataFrame
    trades_df = pd.DataFrame(all_trades)

    if len(trades_df) == 0:
        print("\n⚠️ NO TRADES GENERATED IN DEC 8-15 PERIOD!")
        return

    # Sort chronologically
    trades_df = trades_df.sort_values('entry_time').reset_index(drop=True)

    # Portfolio simulation with compounding
    print("\n" + "=" * 80)
    print("PORTFOLIO SIMULATION (10% Position Sizing, Compounding)")
    print("=" * 80)

    initial_capital = 100.0
    capital = initial_capital
    trades_df['capital_before'] = 0.0
    trades_df['position_size_usd'] = 0.0
    trades_df['pnl_usd'] = 0.0
    trades_df['capital_after'] = 0.0

    for idx, trade in trades_df.iterrows():
        position_size = capital * 0.10  # 10% of current capital
        pnl_usd = position_size * (trade['pnl_pct'] / 100)

        trades_df.loc[idx, 'capital_before'] = capital
        trades_df.loc[idx, 'position_size_usd'] = position_size
        trades_df.loc[idx, 'pnl_usd'] = pnl_usd

        capital += pnl_usd
        trades_df.loc[idx, 'capital_after'] = capital

    # Calculate metrics
    final_capital = capital
    total_return_pct = ((final_capital - initial_capital) / initial_capital) * 100

    # Max drawdown
    trades_df['peak'] = trades_df['capital_after'].cummax()
    trades_df['drawdown_pct'] = ((trades_df['capital_after'] - trades_df['peak']) / trades_df['peak']) * 100
    max_drawdown_pct = trades_df['drawdown_pct'].min()

    # Win rate
    winners = trades_df[trades_df['pnl_pct'] > 0]
    losers = trades_df[trades_df['pnl_pct'] <= 0]
    win_rate = (len(winners) / len(trades_df)) * 100

    # Return/DD ratio
    return_dd_ratio = abs(total_return_pct / max_drawdown_pct) if max_drawdown_pct != 0 else 0

    # Profit factor
    gross_profit = winners['pnl_usd'].sum() if len(winners) > 0 else 0
    gross_loss = abs(losers['pnl_usd'].sum()) if len(losers) > 0 else 0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

    # Display results
    print(f"\n📊 OVERALL PERFORMANCE (Dec 8-15):")
    print(f"  Starting Capital: ${initial_capital:.2f}")
    print(f"  Final Capital: ${final_capital:.2f}")
    print(f"  Total Return: {total_return_pct:+.2f}%")
    print(f"  Max Drawdown: {max_drawdown_pct:.2f}%")
    print(f"  Return/DD Ratio: {return_dd_ratio:.2f}x")
    print(f"  Win Rate: {win_rate:.1f}% ({len(winners)}W / {len(losers)}L)")
    print(f"  Profit Factor: {profit_factor:.2f}x")
    print(f"  Total Trades: {len(trades_df)}")
    print(f"  Avg Trade: {trades_df['pnl_pct'].mean():.2f}%")
    print(f"  Best Trade: {trades_df['pnl_pct'].max():.2f}%")
    print(f"  Worst Trade: {trades_df['pnl_pct'].min():.2f}%")

    # Performance by coin
    print(f"\n📈 PERFORMANCE BY COIN:")
    print(f"{'Coin':<15} {'Trades':>7} {'Win%':>7} {'Total P&L':>12} {'Avg P&L':>10}")
    print("-" * 60)

    coin_stats = []
    for symbol in sorted(trades_df['symbol'].unique()):
        coin_trades = trades_df[trades_df['symbol'] == symbol]
        coin_winners = coin_trades[coin_trades['pnl_pct'] > 0]
        coin_win_rate = (len(coin_winners) / len(coin_trades)) * 100
        total_pnl = coin_trades['pnl_usd'].sum()
        avg_pnl = coin_trades['pnl_pct'].mean()

        coin_stats.append({
            'symbol': symbol,
            'trades': len(coin_trades),
            'win_rate': coin_win_rate,
            'total_pnl': total_pnl,
            'avg_pnl': avg_pnl
        })

        print(f"{symbol:<15} {len(coin_trades):>7} {coin_win_rate:>6.1f}% {total_pnl:>+11.2f}$ {avg_pnl:>+9.2f}%")

    # Sort by total P&L
    coin_stats_df = pd.DataFrame(coin_stats).sort_values('total_pnl', ascending=False)

    # Daily breakdown
    print(f"\n📅 DAILY BREAKDOWN:")
    trades_df['date'] = pd.to_datetime(trades_df['entry_time']).dt.date
    daily = trades_df.groupby('date').agg({
        'pnl_usd': ['sum', 'count'],
        'pnl_pct': 'mean'
    }).round(2)

    print(daily.to_string())

    # Save results
    trades_df.to_csv('dec8_15_all_trades.csv', index=False)
    coin_stats_df.to_csv('dec8_15_by_coin.csv', index=False)

    print(f"\n✅ Results saved to:")
    print(f"  - dec8_15_all_trades.csv")
    print(f"  - dec8_15_by_coin.csv")

    # Show sample trades
    print(f"\n🔍 SAMPLE TRADES (first 10):")
    display_cols = ['symbol', 'direction', 'entry_time', 'entry_price', 'exit_price',
                    'exit_reason', 'pnl_pct', 'pnl_usd', 'capital_after']
    print(trades_df[display_cols].head(10).to_string(index=False))

    if len(trades_df) > 10:
        print(f"\n... ({len(trades_df) - 10} more trades)")

if __name__ == '__main__':
    main()
