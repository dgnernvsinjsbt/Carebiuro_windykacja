"""
FARTCOIN - LIMIT ORDER STRATEGY
Pomysł: Limit order wyżej (LONG) / niżej (SHORT) żeby wyciąć fake breakouts
"""

import pandas as pd
import numpy as np

def calculate_atr(high, low, close, period=14):
    """ATR calculation"""
    tr = pd.concat([
        high - low,
        abs(high - close.shift()),
        abs(low - close.shift())
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def calculate_ema(series, period):
    """EMA calculation"""
    return series.ewm(span=period, adjust=False).mean()

def generate_signals(df):
    """Generate ATR Expansion + EMA Distance 3% signals"""
    df = df.copy()
    df['atr'] = calculate_atr(df['high'], df['low'], df['close'])
    df['atr_ma'] = df['atr'].rolling(20).mean()
    df['atr_ratio'] = df['atr'] / df['atr_ma']

    df['ema20'] = calculate_ema(df['close'], 20)
    df['distance'] = abs((df['close'] - df['ema20']) / df['ema20'] * 100)

    df['bullish'] = df['close'] > df['open']
    df['bearish'] = df['close'] < df['open']
    df['atr_expanding'] = df['atr_ratio'] > 1.5

    signals = []
    for i in range(len(df)):
        if df['atr_expanding'].iloc[i] and df['distance'].iloc[i] < 3.0:
            if df['bullish'].iloc[i]:
                signals.append(('LONG', i))
            elif df['bearish'].iloc[i]:
                signals.append(('SHORT', i))

    return signals

def backtest_market_order(df, signals, config_name="MARKET"):
    """Baseline: Market order (immediate fill)"""
    df = df.copy()
    df['atr'] = calculate_atr(df['high'], df['low'], df['close'])

    trades = []

    for direction, entry_idx in signals:
        if entry_idx >= len(df) - 1:
            continue

        entry_price = df['close'].iloc[entry_idx]
        entry_atr = df['atr'].iloc[entry_idx]

        if pd.isna(entry_atr) or entry_atr == 0:
            continue

        sl_dist = 2.0 * entry_atr
        tp_dist = 8.0 * entry_atr

        if direction == 'LONG':
            sl_price = entry_price - sl_dist
            tp_price = entry_price + tp_dist
        else:
            sl_price = entry_price + sl_dist
            tp_price = entry_price - tp_dist

        # Walk forward
        exit_idx = None
        exit_price = None
        exit_reason = None

        for i in range(entry_idx + 1, min(entry_idx + 200, len(df))):
            current_high = df['high'].iloc[i]
            current_low = df['low'].iloc[i]

            if direction == 'LONG':
                if current_low <= sl_price:
                    exit_idx = i
                    exit_price = sl_price
                    exit_reason = 'SL'
                    break
                if current_high >= tp_price:
                    exit_idx = i
                    exit_price = tp_price
                    exit_reason = 'TP'
                    break
            else:
                if current_high >= sl_price:
                    exit_idx = i
                    exit_price = sl_price
                    exit_reason = 'SL'
                    break
                if current_low <= tp_price:
                    exit_idx = i
                    exit_price = tp_price
                    exit_reason = 'TP'
                    break

        if exit_idx is None:
            exit_idx = min(entry_idx + 199, len(df) - 1)
            exit_price = df['close'].iloc[exit_idx]
            exit_reason = 'TIME'

        # P&L
        if direction == 'LONG':
            pnl_pct = (exit_price - entry_price) / entry_price * 100
        else:
            pnl_pct = (entry_price - exit_price) / entry_price * 100

        pnl_pct -= 0.1  # Market fees: 0.05% x2

        trades.append({
            'config': config_name,
            'direction': direction,
            'entry_idx': entry_idx,
            'exit_idx': exit_idx,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'pnl_pct': pnl_pct,
            'exit_reason': exit_reason
        })

    return trades

def backtest_limit_order(df, signals, limit_offset_pct, max_wait_bars=5, config_name="LIMIT"):
    """
    Limit order strategy:
    - LONG: limit ABOVE signal price (wait for confirmation)
    - SHORT: limit BELOW signal price
    - Trailing SL from limit fill price
    """
    df = df.copy()
    df['atr'] = calculate_atr(df['high'], df['low'], df['close'])

    trades = []
    unfilled = 0

    for direction, signal_idx in signals:
        if signal_idx >= len(df) - 1:
            continue

        signal_price = df['close'].iloc[signal_idx]
        signal_atr = df['atr'].iloc[signal_idx]

        if pd.isna(signal_atr) or signal_atr == 0:
            continue

        # Set limit order
        if direction == 'LONG':
            limit_price = signal_price * (1 + limit_offset_pct / 100)
        else:  # SHORT
            limit_price = signal_price * (1 - limit_offset_pct / 100)

        # Try to fill limit in next X bars
        filled = False
        fill_idx = None

        for i in range(signal_idx + 1, min(signal_idx + max_wait_bars + 1, len(df))):
            current_high = df['high'].iloc[i]
            current_low = df['low'].iloc[i]

            if direction == 'LONG':
                # Fill if price reaches or exceeds limit
                if current_high >= limit_price:
                    filled = True
                    fill_idx = i
                    break
            else:  # SHORT
                # Fill if price reaches or goes below limit
                if current_low <= limit_price:
                    filled = True
                    fill_idx = i
                    break

        if not filled:
            unfilled += 1
            continue

        # Now we're filled at limit_price
        entry_price = limit_price
        entry_atr = df['atr'].iloc[fill_idx]

        # Exits from limit fill
        sl_dist = 2.0 * entry_atr
        tp_dist = 8.0 * entry_atr

        if direction == 'LONG':
            sl_price = entry_price - sl_dist
            tp_price = entry_price + tp_dist
        else:
            sl_price = entry_price + sl_dist
            tp_price = entry_price - tp_dist

        # Walk forward from fill
        exit_idx = None
        exit_price = None
        exit_reason = None

        for i in range(fill_idx + 1, min(fill_idx + 200, len(df))):
            current_high = df['high'].iloc[i]
            current_low = df['low'].iloc[i]

            if direction == 'LONG':
                if current_low <= sl_price:
                    exit_idx = i
                    exit_price = sl_price
                    exit_reason = 'SL'
                    break
                if current_high >= tp_price:
                    exit_idx = i
                    exit_price = tp_price
                    exit_reason = 'TP'
                    break
            else:
                if current_high >= sl_price:
                    exit_idx = i
                    exit_price = sl_price
                    exit_reason = 'SL'
                    break
                if current_low <= tp_price:
                    exit_idx = i
                    exit_price = tp_price
                    exit_reason = 'TP'
                    break

        if exit_idx is None:
            exit_idx = min(fill_idx + 199, len(df) - 1)
            exit_price = df['close'].iloc[exit_idx]
            exit_reason = 'TIME'

        # P&L
        if direction == 'LONG':
            pnl_pct = (exit_price - entry_price) / entry_price * 100
        else:
            pnl_pct = (entry_price - exit_price) / entry_price * 100

        # Fees: limit = 0.02% maker, exit market = 0.05% taker
        pnl_pct -= 0.07  # 0.02 + 0.05

        trades.append({
            'config': config_name,
            'direction': direction,
            'signal_idx': signal_idx,
            'fill_idx': fill_idx,
            'entry_idx': fill_idx,
            'exit_idx': exit_idx,
            'signal_price': signal_price,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'pnl_pct': pnl_pct,
            'exit_reason': exit_reason
        })

    return trades, unfilled

def analyze_results(trades, config_name):
    """Analyze with Return/DD"""
    if not trades:
        return {
            'config': config_name,
            'trades': 0,
            'win_rate': 0,
            'total_return': 0,
            'max_dd': 0,
            'return_dd': 0,
            'top10_avg': 0,
            'max_winner': 0,
            'tp_rate': 0
        }

    df_trades = pd.DataFrame(trades)
    df_trades = df_trades.sort_values('entry_idx')

    # Equity curve
    df_trades['cumulative_return'] = df_trades['pnl_pct'].cumsum()
    equity_curve = 100 + df_trades['cumulative_return']

    # Max DD
    running_max = equity_curve.cummax()
    drawdown = (equity_curve - running_max) / running_max * 100
    max_dd = drawdown.min()

    total_return = df_trades['pnl_pct'].sum()
    return_dd = total_return / abs(max_dd) if max_dd != 0 else 0

    winners = df_trades[df_trades['pnl_pct'] > 0]
    top10 = df_trades.nlargest(10, 'pnl_pct')['pnl_pct'].mean() if len(df_trades) >= 10 else df_trades['pnl_pct'].max()

    return {
        'config': config_name,
        'trades': len(trades),
        'win_rate': len(winners) / len(trades) * 100 if trades else 0,
        'total_return': total_return,
        'max_dd': max_dd,
        'return_dd': return_dd,
        'top10_avg': top10,
        'max_winner': df_trades['pnl_pct'].max(),
        'tp_rate': (df_trades['exit_reason'] == 'TP').sum() / len(trades) * 100,
        'avg_winner': winners['pnl_pct'].mean() if len(winners) > 0 else 0
    }

def main():
    print("🎯 FARTCOIN - LIMIT ORDER STRATEGY TEST\n")

    df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/fartcoin_30d_bingx.csv')
    df.columns = df.columns.str.lower()
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    print(f"📊 Data: {len(df):,} candles\n")

    # Generate signals (ATR Expansion + EMA Distance 3%)
    signals = generate_signals(df)
    print(f"📡 Generated {len(signals)} signals\n")

    # Baseline: Market order
    print("="*100)
    print("📍 BASELINE: MARKET ORDER (immediate fill)")
    print("="*100)

    market_trades = backtest_market_order(df, signals, "MARKET")
    market_results = analyze_results(market_trades, "MARKET")

    print(f"Trades: {market_results['trades']} | WR: {market_results['win_rate']:.1f}%")
    print(f"Return: {market_results['total_return']:.2f}% | DD: {market_results['max_dd']:.2f}% | R/DD: {market_results['return_dd']:.2f}x")
    print(f"Top10: {market_results['top10_avg']:.2f}% | Max: {market_results['max_winner']:.2f}%")
    print(f"TP Rate: {market_results['tp_rate']:.1f}% | Avg Winner: {market_results['avg_winner']:.2f}%\n")

    # Test limit orders with different offsets
    print("="*100)
    print("🎯 TESTING LIMIT ORDER OFFSETS")
    print("="*100)

    offsets = [0.5, 1.0, 1.5, 2.0, 2.5]
    wait_bars_options = [3, 5, 10]

    all_results = [market_results]

    for offset in offsets:
        for wait_bars in wait_bars_options:
            config_name = f"LIMIT_{offset}%_wait{wait_bars}"

            limit_trades, unfilled = backtest_limit_order(df, signals, offset, wait_bars, config_name)
            results = analyze_results(limit_trades, config_name)
            all_results.append(results)

            fill_rate = (results['trades'] / len(signals)) * 100 if len(signals) > 0 else 0
            rr_change = results['return_dd'] - market_results['return_dd']

            print(f"\n{config_name}:")
            print(f"  Filled: {results['trades']}/{len(signals)} ({fill_rate:.1f}%) | Unfilled: {unfilled}")
            print(f"  WR: {results['win_rate']:.1f}% | TP Rate: {results['tp_rate']:.1f}%")
            print(f"  Return: {results['total_return']:.2f}% | DD: {results['max_dd']:.2f}% | R/DD: {results['return_dd']:.2f}x ({rr_change:+.2f}x)")
            print(f"  Top10: {results['top10_avg']:.2f}% | Max: {results['max_winner']:.2f}%")

    # Final ranking
    print("\n" + "="*100)
    print("📊 FINAL RANKING (by Return/DD)")
    print("="*100)

    df_results = pd.DataFrame(all_results)
    df_results = df_results.sort_values('return_dd', ascending=False)
    print(df_results[['config', 'trades', 'win_rate', 'total_return', 'max_dd', 'return_dd', 'tp_rate']].head(10).to_string(index=False))

    # Save
    df_results.to_csv('/workspaces/Carebiuro_windykacja/trading/results/fartcoin_limit_order_test.csv', index=False)
    print("\n✅ Saved: trading/results/fartcoin_limit_order_test.csv")

    # Best config
    best = df_results.iloc[0]
    baseline = df_results[df_results['config'] == 'MARKET'].iloc[0]

    print("\n" + "="*100)
    print("⭐ BEST CONFIGURATION")
    print("="*100)
    print(f"Config: {best['config']}")
    print(f"Trades: {best['trades']} (Baseline: {baseline['trades']})")
    print(f"Win Rate: {best['win_rate']:.1f}% (Baseline: {baseline['win_rate']:.1f}%)")
    print(f"Return/DD: {best['return_dd']:.2f}x (Baseline: {baseline['return_dd']:.2f}x) → {best['return_dd'] - baseline['return_dd']:+.2f}x")
    print(f"Return: {best['total_return']:.2f}% (Baseline: {baseline['total_return']:.2f}%)")
    print(f"Max DD: {best['max_dd']:.2f}% (Baseline: {baseline['max_dd']:.2f}%)")

    if best['return_dd'] > baseline['return_dd']:
        print("\n✅ LIMIT ORDER IMPROVEMENT! Using this config.")
    else:
        print("\n⚠️  No improvement - proceed to winners vs losers analysis")

if __name__ == '__main__':
    main()
