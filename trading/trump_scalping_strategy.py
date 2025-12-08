#!/usr/bin/env python3
"""
TRUMP Scalping Strategy - Testing the #1 recommended approach
Based on pattern analysis that rated Scalping 8.5/10

Key insights to exploit:
- US session has 1.47x volume and highest ATR (0.1479%)
- Quick moves, take profits fast
- Low volatility = need tight targets
- Momentum-based entries (not mean reversion)
"""

import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

def load_data(filepath):
    """Load and prepare TRUMP data"""
    df = pd.read_csv(filepath)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)

    # Add hour for session filtering
    df['hour'] = df['timestamp'].dt.hour

    # Calculate indicators
    df['returns'] = df['close'].pct_change()
    df['atr'] = calculate_atr(df, 14)
    df['sma_20'] = df['close'].rolling(20).mean()
    df['sma_50'] = df['close'].rolling(50).mean()
    df['ema_9'] = df['close'].ewm(span=9).mean()
    df['ema_21'] = df['close'].ewm(span=21).mean()
    df['rsi'] = calculate_rsi(df['close'], 14)
    df['volume_sma'] = df['volume'].rolling(20).mean()
    df['volume_ratio'] = df['volume'] / df['volume_sma']

    # Momentum indicators
    df['momentum'] = df['close'] - df['close'].shift(5)
    df['roc'] = (df['close'] - df['close'].shift(5)) / df['close'].shift(5) * 100

    # Candle analysis
    df['body'] = abs(df['close'] - df['open'])
    df['body_pct'] = df['body'] / df['open'] * 100
    df['is_green'] = df['close'] > df['open']

    return df.dropna().reset_index(drop=True)

def calculate_atr(df, period=14):
    """Calculate Average True Range"""
    high = df['high']
    low = df['low']
    close = df['close'].shift(1)

    tr1 = high - low
    tr2 = abs(high - close)
    tr3 = abs(low - close)

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def calculate_rsi(prices, period=14):
    """Calculate RSI"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def is_us_session(hour):
    """Check if hour is in US session (14:00-21:00 UTC)"""
    return 14 <= hour <= 20

def run_scalping_backtest(df, config, name="Scalping"):
    """
    Run scalping backtest with given config

    Scalping approach:
    - Quick momentum entries
    - Tight stops and targets
    - US session focus
    """

    initial_capital = 10000
    capital = initial_capital
    position = None
    trades = []

    # Unpack config
    entry_type = config.get('entry_type', 'momentum')
    sl_atr = config.get('sl_atr', 1.0)
    tp_atr = config.get('tp_atr', 2.0)
    session_filter = config.get('session_filter', True)
    max_hold_bars = config.get('max_hold_bars', 30)  # 30 min max hold for scalping
    position_size_pct = config.get('position_size', 0.02)
    fee_pct = config.get('fee_pct', 0.001)  # 0.1% total

    for i in range(50, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i-1]

        # Session filter
        if session_filter and not is_us_session(row['hour']):
            # Close any open position at session end
            if position is not None:
                exit_price = row['close']
                pnl_pct = (exit_price - position['entry_price']) / position['entry_price']
                if position['direction'] == 'short':
                    pnl_pct = -pnl_pct
                pnl_pct -= fee_pct  # Exit fee

                pnl_dollar = position['size'] * pnl_pct
                capital += pnl_dollar

                trades.append({
                    'entry_time': position['entry_time'],
                    'exit_time': row['timestamp'],
                    'direction': position['direction'],
                    'entry_price': position['entry_price'],
                    'exit_price': exit_price,
                    'pnl_pct': pnl_pct * 100,
                    'pnl_dollar': pnl_dollar,
                    'exit_reason': 'session_end',
                    'bars_held': i - position['entry_bar']
                })
                position = None
            continue

        # Check exits first
        if position is not None:
            bars_held = i - position['entry_bar']

            # Check SL/TP
            if position['direction'] == 'long':
                # Check if SL hit
                if row['low'] <= position['sl']:
                    exit_price = position['sl']
                    exit_reason = 'sl'
                # Check if TP hit
                elif row['high'] >= position['tp']:
                    exit_price = position['tp']
                    exit_reason = 'tp'
                # Time exit
                elif bars_held >= max_hold_bars:
                    exit_price = row['close']
                    exit_reason = 'time'
                else:
                    exit_price = None

            else:  # short
                if row['high'] >= position['sl']:
                    exit_price = position['sl']
                    exit_reason = 'sl'
                elif row['low'] <= position['tp']:
                    exit_price = position['tp']
                    exit_reason = 'tp'
                elif bars_held >= max_hold_bars:
                    exit_price = row['close']
                    exit_reason = 'time'
                else:
                    exit_price = None

            if exit_price is not None:
                pnl_pct = (exit_price - position['entry_price']) / position['entry_price']
                if position['direction'] == 'short':
                    pnl_pct = -pnl_pct
                pnl_pct -= fee_pct

                pnl_dollar = position['size'] * pnl_pct
                capital += pnl_dollar

                trades.append({
                    'entry_time': position['entry_time'],
                    'exit_time': row['timestamp'],
                    'direction': position['direction'],
                    'entry_price': position['entry_price'],
                    'exit_price': exit_price,
                    'pnl_pct': pnl_pct * 100,
                    'pnl_dollar': pnl_dollar,
                    'exit_reason': exit_reason,
                    'bars_held': bars_held
                })
                position = None
                continue

        # Entry signals (only if no position)
        if position is None:
            signal = None

            if entry_type == 'momentum':
                # Momentum scalping: trade with short-term momentum
                # LONG: EMA9 crosses above EMA21 + positive momentum
                if (prev['ema_9'] <= prev['ema_21'] and
                    row['ema_9'] > row['ema_21'] and
                    row['momentum'] > 0 and
                    row['volume_ratio'] > 1.0):
                    signal = 'long'
                # SHORT: EMA9 crosses below EMA21 + negative momentum
                elif (prev['ema_9'] >= prev['ema_21'] and
                      row['ema_9'] < row['ema_21'] and
                      row['momentum'] < 0 and
                      row['volume_ratio'] > 1.0):
                    signal = 'short'

            elif entry_type == 'breakout':
                # Breakout scalping: trade when price breaks recent range
                high_5 = df['high'].iloc[i-5:i].max()
                low_5 = df['low'].iloc[i-5:i].min()

                # LONG: Break above 5-bar high with volume
                if row['close'] > high_5 and row['volume_ratio'] > 1.2:
                    signal = 'long'
                # SHORT: Break below 5-bar low with volume
                elif row['close'] < low_5 and row['volume_ratio'] > 1.2:
                    signal = 'short'

            elif entry_type == 'rsi_momentum':
                # RSI momentum: trade when RSI shows strength
                # LONG: RSI crossing above 50 with momentum
                if prev['rsi'] < 50 and row['rsi'] >= 50 and row['momentum'] > 0:
                    signal = 'long'
                # SHORT: RSI crossing below 50 with momentum
                elif prev['rsi'] > 50 and row['rsi'] <= 50 and row['momentum'] < 0:
                    signal = 'short'

            elif entry_type == 'candle_momentum':
                # Strong candle momentum
                # LONG: Strong green candle with volume
                if (row['is_green'] and
                    row['body_pct'] > 0.15 and  # Decent body
                    row['volume_ratio'] > 1.5 and
                    row['close'] > row['sma_20']):
                    signal = 'long'
                # SHORT: Strong red candle with volume
                elif (not row['is_green'] and
                      row['body_pct'] > 0.15 and
                      row['volume_ratio'] > 1.5 and
                      row['close'] < row['sma_20']):
                    signal = 'short'

            if signal is not None:
                entry_price = row['close']
                atr = row['atr']
                position_size = capital * position_size_pct

                if signal == 'long':
                    sl = entry_price - (atr * sl_atr)
                    tp = entry_price + (atr * tp_atr)
                else:
                    sl = entry_price + (atr * sl_atr)
                    tp = entry_price - (atr * tp_atr)

                # Deduct entry fee
                capital -= position_size * fee_pct

                position = {
                    'direction': signal,
                    'entry_price': entry_price,
                    'entry_time': row['timestamp'],
                    'entry_bar': i,
                    'sl': sl,
                    'tp': tp,
                    'size': position_size,
                    'atr': atr
                }

    # Close any remaining position
    if position is not None:
        row = df.iloc[-1]
        exit_price = row['close']
        pnl_pct = (exit_price - position['entry_price']) / position['entry_price']
        if position['direction'] == 'short':
            pnl_pct = -pnl_pct
        pnl_pct -= fee_pct

        pnl_dollar = position['size'] * pnl_pct
        capital += pnl_dollar

        trades.append({
            'entry_time': position['entry_time'],
            'exit_time': row['timestamp'],
            'direction': position['direction'],
            'entry_price': position['entry_price'],
            'exit_price': exit_price,
            'pnl_pct': pnl_pct * 100,
            'pnl_dollar': pnl_dollar,
            'exit_reason': 'end',
            'bars_held': len(df) - position['entry_bar']
        })

    return calculate_metrics(trades, initial_capital, capital, name, config)

def calculate_metrics(trades, initial_capital, final_capital, name, config):
    """Calculate performance metrics"""
    if not trades:
        return {
            'name': name,
            'config': config,
            'total_trades': 0,
            'total_return_pct': 0,
            'win_rate': 0,
            'profit_factor': 0,
            'avg_trade_pct': 0,
            'max_drawdown': 0,
            'trades': []
        }

    trades_df = pd.DataFrame(trades)

    winners = trades_df[trades_df['pnl_pct'] > 0]
    losers = trades_df[trades_df['pnl_pct'] <= 0]

    win_rate = len(winners) / len(trades_df) * 100 if len(trades_df) > 0 else 0

    gross_profit = winners['pnl_dollar'].sum() if len(winners) > 0 else 0
    gross_loss = abs(losers['pnl_dollar'].sum()) if len(losers) > 0 else 0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

    total_return = (final_capital - initial_capital) / initial_capital * 100
    avg_trade = trades_df['pnl_pct'].mean()

    # Calculate max drawdown
    equity = [initial_capital]
    for t in trades:
        equity.append(equity[-1] + t['pnl_dollar'])
    equity = pd.Series(equity)
    rolling_max = equity.expanding().max()
    drawdown = (equity - rolling_max) / rolling_max * 100
    max_dd = drawdown.min()

    # Exit reason breakdown
    exit_reasons = trades_df['exit_reason'].value_counts().to_dict()

    # Direction breakdown
    longs = trades_df[trades_df['direction'] == 'long']
    shorts = trades_df[trades_df['direction'] == 'short']

    long_wr = len(longs[longs['pnl_pct'] > 0]) / len(longs) * 100 if len(longs) > 0 else 0
    short_wr = len(shorts[shorts['pnl_pct'] > 0]) / len(shorts) * 100 if len(shorts) > 0 else 0

    return {
        'name': name,
        'config': config,
        'total_trades': len(trades_df),
        'total_return_pct': total_return,
        'final_capital': final_capital,
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'avg_trade_pct': avg_trade,
        'avg_win_pct': winners['pnl_pct'].mean() if len(winners) > 0 else 0,
        'avg_loss_pct': losers['pnl_pct'].mean() if len(losers) > 0 else 0,
        'max_drawdown': max_dd,
        'avg_bars_held': trades_df['bars_held'].mean(),
        'long_trades': len(longs),
        'short_trades': len(shorts),
        'long_win_rate': long_wr,
        'short_win_rate': short_wr,
        'exit_reasons': exit_reasons,
        'trades': trades
    }

def print_results(result):
    """Print formatted results"""
    print(f"\n{'='*60}")
    print(f"Strategy: {result['name']}")
    print(f"{'='*60}")
    print(f"Total Trades: {result['total_trades']}")
    print(f"Total Return: {result['total_return_pct']:.2f}%")
    print(f"Win Rate: {result['win_rate']:.1f}%")
    print(f"Profit Factor: {result['profit_factor']:.2f}")
    print(f"Avg Trade: {result['avg_trade_pct']:.3f}%")
    print(f"Avg Win: {result.get('avg_win_pct', 0):.3f}%")
    print(f"Avg Loss: {result.get('avg_loss_pct', 0):.3f}%")
    print(f"Max Drawdown: {result['max_drawdown']:.2f}%")
    print(f"Avg Bars Held: {result.get('avg_bars_held', 0):.1f}")
    print(f"\nLongs: {result.get('long_trades', 0)} (WR: {result.get('long_win_rate', 0):.1f}%)")
    print(f"Shorts: {result.get('short_trades', 0)} (WR: {result.get('short_win_rate', 0):.1f}%)")
    print(f"\nExit Reasons: {result.get('exit_reasons', {})}")

    # Config
    print(f"\nConfig: {result['config']}")

def main():
    print("="*60)
    print("TRUMP SCALPING STRATEGY BACKTEST")
    print("Testing the #1 recommended approach (8.5/10 score)")
    print("="*60)

    # Load data
    df = load_data('trump_usdt_1m_mexc.csv')
    print(f"\nData loaded: {len(df)} candles")
    print(f"Period: {df['timestamp'].min()} to {df['timestamp'].max()}")

    # Test different scalping configurations
    configs = [
        # Momentum-based scalping
        {
            'name': 'Momentum Scalp (EMA Cross)',
            'entry_type': 'momentum',
            'sl_atr': 1.0,
            'tp_atr': 2.0,
            'session_filter': True,
            'max_hold_bars': 30,
            'position_size': 0.02,
            'fee_pct': 0.001
        },
        {
            'name': 'Momentum Scalp (Tight)',
            'entry_type': 'momentum',
            'sl_atr': 0.75,
            'tp_atr': 1.5,
            'session_filter': True,
            'max_hold_bars': 20,
            'position_size': 0.02,
            'fee_pct': 0.001
        },
        # Breakout scalping
        {
            'name': 'Breakout Scalp',
            'entry_type': 'breakout',
            'sl_atr': 1.0,
            'tp_atr': 2.0,
            'session_filter': True,
            'max_hold_bars': 30,
            'position_size': 0.02,
            'fee_pct': 0.001
        },
        {
            'name': 'Breakout Scalp (Wide)',
            'entry_type': 'breakout',
            'sl_atr': 1.5,
            'tp_atr': 3.0,
            'session_filter': True,
            'max_hold_bars': 45,
            'position_size': 0.02,
            'fee_pct': 0.001
        },
        # RSI momentum
        {
            'name': 'RSI Momentum Scalp',
            'entry_type': 'rsi_momentum',
            'sl_atr': 1.0,
            'tp_atr': 2.0,
            'session_filter': True,
            'max_hold_bars': 30,
            'position_size': 0.02,
            'fee_pct': 0.001
        },
        # Candle momentum
        {
            'name': 'Candle Momentum Scalp',
            'entry_type': 'candle_momentum',
            'sl_atr': 1.0,
            'tp_atr': 2.0,
            'session_filter': True,
            'max_hold_bars': 30,
            'position_size': 0.02,
            'fee_pct': 0.001
        },
        # All sessions (no filter)
        {
            'name': 'Momentum All Sessions',
            'entry_type': 'momentum',
            'sl_atr': 1.0,
            'tp_atr': 2.0,
            'session_filter': False,
            'max_hold_bars': 30,
            'position_size': 0.02,
            'fee_pct': 0.001
        },
        # Wider R:R
        {
            'name': 'Momentum Wide R:R (1:3)',
            'entry_type': 'momentum',
            'sl_atr': 1.0,
            'tp_atr': 3.0,
            'session_filter': True,
            'max_hold_bars': 45,
            'position_size': 0.02,
            'fee_pct': 0.001
        },
    ]

    results = []
    for config in configs:
        name = config.pop('name')
        result = run_scalping_backtest(df, config, name)
        results.append(result)
        print_results(result)

    # Summary comparison
    print("\n" + "="*80)
    print("SCALPING STRATEGY COMPARISON SUMMARY")
    print("="*80)
    print(f"{'Strategy':<30} {'Trades':>7} {'Return':>10} {'WinRate':>10} {'PF':>8} {'MaxDD':>10}")
    print("-"*80)

    for r in sorted(results, key=lambda x: x['total_return_pct'], reverse=True):
        print(f"{r['name']:<30} {r['total_trades']:>7} {r['total_return_pct']:>9.2f}% {r['win_rate']:>9.1f}% {r['profit_factor']:>7.2f} {r['max_drawdown']:>9.2f}%")

    # Best strategy
    best = max(results, key=lambda x: x['total_return_pct'])
    print(f"\n{'='*60}")
    print(f"BEST SCALPING STRATEGY: {best['name']}")
    print(f"{'='*60}")
    print(f"Return: {best['total_return_pct']:.2f}%")
    print(f"Win Rate: {best['win_rate']:.1f}%")
    print(f"Profit Factor: {best['profit_factor']:.2f}")

    # Save results
    results_df = pd.DataFrame([{
        'strategy': r['name'],
        'trades': r['total_trades'],
        'return_pct': r['total_return_pct'],
        'win_rate': r['win_rate'],
        'profit_factor': r['profit_factor'],
        'avg_trade_pct': r['avg_trade_pct'],
        'max_drawdown': r['max_drawdown'],
        'long_trades': r.get('long_trades', 0),
        'short_trades': r.get('short_trades', 0),
        'long_wr': r.get('long_win_rate', 0),
        'short_wr': r.get('short_win_rate', 0),
    } for r in results])

    results_df.to_csv('results/TRUMP_scalping_comparison.csv', index=False)
    print(f"\nResults saved to results/TRUMP_scalping_comparison.csv")

    # Save best strategy trades
    if best['trades']:
        trades_df = pd.DataFrame(best['trades'])
        trades_df.to_csv('results/TRUMP_scalping_best_trades.csv', index=False)
        print(f"Best strategy trades saved to results/TRUMP_scalping_best_trades.csv")

    return results, best

if __name__ == "__main__":
    results, best = main()
