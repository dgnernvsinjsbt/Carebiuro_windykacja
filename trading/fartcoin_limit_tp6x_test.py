"""
FARTCOIN - LIMIT ORDER z TP 6x ATR + pełne fees 0.1%
Test czy tighter TP da lepszy Return/DD
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

def backtest_limit_order(df, signals, limit_offset_pct, tp_atr_mult, max_wait_bars=3, fee_pct=0.1, config_name="LIMIT"):
    """
    Limit order strategy with configurable TP
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
                if current_high >= limit_price:
                    filled = True
                    fill_idx = i
                    break
            else:  # SHORT
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
        tp_dist = tp_atr_mult * entry_atr  # Configurable TP

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

        pnl_pct -= fee_pct  # Fees

        trades.append({
            'config': config_name,
            'direction': direction,
            'signal_idx': signal_idx,
            'fill_idx': fill_idx,
            'entry_idx': fill_idx,
            'exit_idx': exit_idx,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'pnl_pct': pnl_pct,
            'exit_reason': exit_reason,
            'tp_atr_mult': tp_atr_mult
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
            'tp_rate': 0,
            'avg_winner': 0
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
    print("🎯 FARTCOIN - LIMIT ORDER: TP 6x ATR + Full Fees Test\n")

    df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/fartcoin_30d_bingx.csv')
    df.columns = df.columns.str.lower()
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    print(f"📊 Data: {len(df):,} candles\n")

    # Generate signals
    signals = generate_signals(df)
    print(f"📡 Generated {len(signals)} signals\n")

    # Test configurations
    configs = [
        # Previous best
        {'offset': 1.0, 'tp_mult': 8.0, 'wait': 3, 'fee': 0.07, 'name': 'LIMIT_1.0%_TP8x_Fee0.07'},
        {'offset': 1.0, 'tp_mult': 8.0, 'wait': 3, 'fee': 0.10, 'name': 'LIMIT_1.0%_TP8x_Fee0.10'},

        # New: TP 6x with different fees
        {'offset': 1.0, 'tp_mult': 6.0, 'wait': 3, 'fee': 0.07, 'name': 'LIMIT_1.0%_TP6x_Fee0.07'},
        {'offset': 1.0, 'tp_mult': 6.0, 'wait': 3, 'fee': 0.10, 'name': 'LIMIT_1.0%_TP6x_Fee0.10'},

        # Also test TP 5x and 7x
        {'offset': 1.0, 'tp_mult': 5.0, 'wait': 3, 'fee': 0.10, 'name': 'LIMIT_1.0%_TP5x_Fee0.10'},
        {'offset': 1.0, 'tp_mult': 7.0, 'wait': 3, 'fee': 0.10, 'name': 'LIMIT_1.0%_TP7x_Fee0.10'},

        # Different offsets with TP6x
        {'offset': 0.5, 'tp_mult': 6.0, 'wait': 3, 'fee': 0.10, 'name': 'LIMIT_0.5%_TP6x_Fee0.10'},
        {'offset': 1.5, 'tp_mult': 6.0, 'wait': 3, 'fee': 0.10, 'name': 'LIMIT_1.5%_TP6x_Fee0.10'},
    ]

    all_results = []

    for config in configs:
        trades, unfilled = backtest_limit_order(
            df,
            signals,
            config['offset'],
            config['tp_mult'],
            config['wait'],
            config['fee'],
            config['name']
        )

        results = analyze_results(trades, config['name'])
        all_results.append(results)

        fill_rate = (results['trades'] / len(signals)) * 100 if len(signals) > 0 else 0

        print(f"{config['name']}:")
        print(f"  Filled: {results['trades']}/{len(signals)} ({fill_rate:.1f}%)")
        print(f"  WR: {results['win_rate']:.1f}% | TP Rate: {results['tp_rate']:.1f}%")
        print(f"  Return: {results['total_return']:.2f}% | DD: {results['max_dd']:.2f}% | R/DD: {results['return_dd']:.2f}x")
        print(f"  Top10: {results['top10_avg']:.2f}% | Avg Winner: {results['avg_winner']:.2f}%\n")

    # Final ranking
    print("="*100)
    print("📊 FINAL RANKING (by Return/DD)")
    print("="*100)

    df_results = pd.DataFrame(all_results)
    df_results = df_results.sort_values('return_dd', ascending=False)
    print(df_results[['config', 'trades', 'win_rate', 'total_return', 'max_dd', 'return_dd', 'tp_rate']].to_string(index=False))

    # Save
    df_results.to_csv('/workspaces/Carebiuro_windykacja/trading/results/fartcoin_limit_tp6x_test.csv', index=False)
    print("\n✅ Saved: trading/results/fartcoin_limit_tp6x_test.csv")

    # Best config
    best = df_results.iloc[0]
    print("\n" + "="*100)
    print("⭐ BEST CONFIGURATION")
    print("="*100)
    print(f"Config: {best['config']}")
    print(f"Trades: {best['trades']}")
    print(f"Win Rate: {best['win_rate']:.1f}%")
    print(f"TP Rate: {best['tp_rate']:.1f}%")
    print(f"Return: {best['total_return']:.2f}%")
    print(f"Max DD: {best['max_dd']:.2f}%")
    print(f"Return/DD: {best['return_dd']:.2f}x")
    print(f"Top 10 Avg: {best['top10_avg']:.2f}%")

if __name__ == '__main__':
    main()
