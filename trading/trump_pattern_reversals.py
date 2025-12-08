"""
TRUMP Chart Pattern Reversal Trading
Test various reversal patterns to see if they work better than scalping (-0.59%)
"""

import pandas as pd
import numpy as np
from datetime import datetime

def load_data():
    df = pd.read_csv('trump_usdt_1m_mexc.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df

def calculate_indicators(df):
    """Calculate technical indicators for pattern detection"""
    df['sma_20'] = df['close'].rolling(20).mean()
    df['sma_50'] = df['close'].rolling(50).mean()
    df['ema_20'] = df['close'].ewm(span=20).mean()

    # ATR for stops
    df['tr'] = np.maximum(
        df['high'] - df['low'],
        np.maximum(
            abs(df['high'] - df['close'].shift(1)),
            abs(df['low'] - df['close'].shift(1))
        )
    )
    df['atr'] = df['tr'].rolling(14).mean()

    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))

    # Swing highs/lows for pattern detection
    df['swing_high'] = df['high'].rolling(5, center=True).max() == df['high']
    df['swing_low'] = df['low'].rolling(5, center=True).min() == df['low']

    return df

def detect_double_bottom(df, i, lookback=20):
    """Detect double bottom reversal pattern"""
    if i < lookback + 10:
        return False

    # Find two lows within lookback period
    window = df.iloc[i-lookback:i]
    lows = window[window['swing_low']].copy()

    if len(lows) < 2:
        return False

    # Get last two swing lows
    last_two = lows.tail(2)
    low1_price = last_two.iloc[0]['low']
    low2_price = last_two.iloc[1]['low']

    # Check if lows are similar (within 0.3%)
    if abs(low1_price - low2_price) / low1_price > 0.003:
        return False

    # Check if current price broke above the high between the lows
    between_high = window.loc[last_two.index[0]:last_two.index[1], 'high'].max()
    if df.loc[i, 'close'] > between_high * 1.001:  # 0.1% above
        return True

    return False

def detect_double_top(df, i, lookback=20):
    """Detect double top reversal pattern"""
    if i < lookback + 10:
        return False

    window = df.iloc[i-lookback:i]
    highs = window[window['swing_high']].copy()

    if len(highs) < 2:
        return False

    last_two = highs.tail(2)
    high1_price = last_two.iloc[0]['high']
    high2_price = last_two.iloc[1]['high']

    if abs(high1_price - high2_price) / high1_price > 0.003:
        return False

    between_low = window.loc[last_two.index[0]:last_two.index[1], 'low'].min()
    if df.loc[i, 'close'] < between_low * 0.999:
        return True

    return False

def detect_support_bounce(df, i, lookback=30):
    """Price bounces off support level (previous swing low)"""
    if i < lookback + 10:
        return False

    window = df.iloc[i-lookback:i]
    swing_lows = window[window['swing_low']]['low'].values

    if len(swing_lows) < 2:
        return False

    # Find support level (cluster of swing lows)
    support = np.median(swing_lows)

    # Check if price touched support and bounced
    recent_low = df.iloc[i-3:i]['low'].min()
    current_close = df.loc[i, 'close']

    if abs(recent_low - support) / support < 0.002:  # Touched support
        if current_close > recent_low * 1.002:  # Bounced 0.2%
            return True

    return False

def detect_resistance_reject(df, i, lookback=30):
    """Price rejects resistance level (previous swing high)"""
    if i < lookback + 10:
        return False

    window = df.iloc[i-lookback:i]
    swing_highs = window[window['swing_high']]['high'].values

    if len(swing_highs) < 2:
        return False

    resistance = np.median(swing_highs)
    recent_high = df.iloc[i-3:i]['high'].max()
    current_close = df.loc[i, 'close']

    if abs(recent_high - resistance) / resistance < 0.002:
        if current_close < recent_high * 0.998:
            return True

    return False

def detect_v_bottom(df, i):
    """Sharp V-shaped bottom (exhaustion reversal)"""
    if i < 10:
        return False

    # Check for sharp decline followed by sharp rise
    lookback = df.iloc[i-10:i]

    # Find the lowest point
    min_idx = lookback['low'].idxmin()
    min_price = lookback.loc[min_idx, 'low']

    # Check decline before low
    before_decline = lookback.loc[:min_idx]['close']
    if len(before_decline) < 3:
        return False

    decline_pct = (before_decline.iloc[0] - min_price) / before_decline.iloc[0]

    # Check rise after low
    after_rise = lookback.loc[min_idx:]['close']
    if len(after_rise) < 3:
        return False

    rise_pct = (after_rise.iloc[-1] - min_price) / min_price

    # V pattern: decline > 0.4%, rise > 0.3%, RSI oversold
    if decline_pct > 0.004 and rise_pct > 0.003 and df.loc[i, 'rsi'] < 35:
        return True

    return False

def detect_v_top(df, i):
    """Sharp V-shaped top (exhaustion reversal)"""
    if i < 10:
        return False

    lookback = df.iloc[i-10:i]
    max_idx = lookback['high'].idxmax()
    max_price = lookback.loc[max_idx, 'high']

    before_rise = lookback.loc[:max_idx]['close']
    if len(before_rise) < 3:
        return False

    rise_pct = (max_price - before_rise.iloc[0]) / before_rise.iloc[0]

    after_decline = lookback.loc[max_idx:]['close']
    if len(after_decline) < 3:
        return False

    decline_pct = (max_price - after_decline.iloc[-1]) / max_price

    if rise_pct > 0.004 and decline_pct > 0.003 and df.loc[i, 'rsi'] > 65:
        return True

    return False

def backtest_pattern_strategy(df, pattern_name, entry_func, sl_atr_mult, tp_atr_mult, direction):
    """Backtest a pattern-based reversal strategy"""

    df = df.copy()
    trades = []
    position = None

    for i in range(100, len(df)):
        idx = df.index[i]

        # Check exit conditions
        if position:
            entry_price = position['entry_price']
            sl_price = position['sl_price']
            tp_price = position['tp_price']
            current_price = df.loc[idx, 'close']
            bars_held = i - position['entry_idx']

            exit_reason = None
            exit_price = current_price

            if direction == 'long':
                if current_price <= sl_price:
                    exit_reason = 'sl'
                    exit_price = sl_price
                elif current_price >= tp_price:
                    exit_reason = 'tp'
                    exit_price = tp_price
            else:  # short
                if current_price >= sl_price:
                    exit_reason = 'sl'
                    exit_price = sl_price
                elif current_price <= tp_price:
                    exit_reason = 'tp'
                    exit_price = tp_price

            # Time-based exit
            if bars_held >= 60 and not exit_reason:
                exit_reason = 'time'
                exit_price = current_price

            if exit_reason:
                # Close trade
                if direction == 'long':
                    pnl_pct = (exit_price - entry_price) / entry_price - 0.001  # 0.1% fees
                else:
                    pnl_pct = (entry_price - exit_price) / entry_price - 0.001

                trades.append({
                    'entry_time': position['entry_time'],
                    'exit_time': df.loc[idx, 'timestamp'],
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'direction': direction,
                    'pnl_pct': pnl_pct,
                    'bars_held': bars_held,
                    'exit_reason': exit_reason
                })
                position = None

        # Check entry conditions
        if not position and entry_func(df, i):
            entry_price = df.loc[idx, 'close']
            atr = df.loc[idx, 'atr']

            if direction == 'long':
                sl_price = entry_price - sl_atr_mult * atr
                tp_price = entry_price + tp_atr_mult * atr
            else:
                sl_price = entry_price + sl_atr_mult * atr
                tp_price = entry_price - tp_atr_mult * atr

            position = {
                'entry_time': df.loc[idx, 'timestamp'],
                'entry_price': entry_price,
                'sl_price': sl_price,
                'tp_price': tp_price,
                'entry_idx': i
            }

    if len(trades) == 0:
        return None

    # Calculate metrics
    trades_df = pd.DataFrame(trades)
    total_return = trades_df['pnl_pct'].sum() * 100
    win_rate = (trades_df['pnl_pct'] > 0).mean() * 100

    winners = trades_df[trades_df['pnl_pct'] > 0]
    losers = trades_df[trades_df['pnl_pct'] <= 0]

    avg_win = winners['pnl_pct'].mean() * 100 if len(winners) > 0 else 0
    avg_loss = losers['pnl_pct'].mean() * 100 if len(losers) > 0 else 0

    profit_factor = abs(winners['pnl_pct'].sum() / losers['pnl_pct'].sum()) if len(losers) > 0 else 0

    return {
        'pattern': pattern_name,
        'trades': len(trades),
        'return': total_return,
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'avg_bars': trades_df['bars_held'].mean(),
        'trades_df': trades_df
    }

def main():
    print("="*60)
    print("TRUMP CHART PATTERN REVERSAL TRADING")
    print("Testing if pattern-based reversals beat scalping (-0.59%)")
    print("="*60)

    df = load_data()
    df = calculate_indicators(df)

    print(f"\nData loaded: {len(df)} candles")
    print(f"Period: {df['timestamp'].min()} to {df['timestamp'].max()}\n")

    # Test various pattern strategies
    strategies = [
        # Double bottom/top patterns
        {
            'name': 'Double Bottom (Long)',
            'func': lambda df, i: detect_double_bottom(df, i, lookback=30),
            'sl': 1.5,
            'tp': 3.0,
            'direction': 'long'
        },
        {
            'name': 'Double Top (Short)',
            'func': lambda df, i: detect_double_top(df, i, lookback=30),
            'sl': 1.5,
            'tp': 3.0,
            'direction': 'short'
        },
        # Support/Resistance bounces
        {
            'name': 'Support Bounce (Long)',
            'func': lambda df, i: detect_support_bounce(df, i, lookback=40),
            'sl': 1.0,
            'tp': 2.5,
            'direction': 'long'
        },
        {
            'name': 'Resistance Reject (Short)',
            'func': lambda df, i: detect_resistance_reject(df, i, lookback=40),
            'sl': 1.0,
            'tp': 2.5,
            'direction': 'short'
        },
        # V-shaped reversals
        {
            'name': 'V-Bottom Reversal (Long)',
            'func': detect_v_bottom,
            'sl': 1.0,
            'tp': 2.0,
            'direction': 'long'
        },
        {
            'name': 'V-Top Reversal (Short)',
            'func': detect_v_top,
            'sl': 1.0,
            'tp': 2.0,
            'direction': 'short'
        },
        # Tight stops for patterns
        {
            'name': 'Support Bounce Tight (Long)',
            'func': lambda df, i: detect_support_bounce(df, i, lookback=40),
            'sl': 0.75,
            'tp': 2.0,
            'direction': 'long'
        },
        {
            'name': 'V-Bottom Wide R:R (Long)',
            'func': detect_v_bottom,
            'sl': 0.75,
            'tp': 3.0,
            'direction': 'long'
        },
    ]

    results = []

    for strat in strategies:
        print(f"\n{'='*60}")
        print(f"Strategy: {strat['name']}")
        print(f"{'='*60}")

        result = backtest_pattern_strategy(
            df,
            strat['name'],
            strat['func'],
            strat['sl'],
            strat['tp'],
            strat['direction']
        )

        if result is None:
            print(f"No trades generated")
            continue

        results.append(result)

        print(f"Total Trades: {result['trades']}")
        print(f"Total Return: {result['return']:.2f}%")
        print(f"Win Rate: {result['win_rate']:.1f}%")
        print(f"Profit Factor: {result['profit_factor']:.2f}")
        print(f"Avg Win: {result['avg_win']:.2f}%")
        print(f"Avg Loss: {result['avg_loss']:.2f}%")
        print(f"Avg Bars Held: {result['avg_bars']:.1f}")

        # Show exit reasons
        exit_counts = result['trades_df']['exit_reason'].value_counts()
        print(f"\nExit Reasons: {dict(exit_counts)}")

    # Summary comparison
    if results:
        print("\n" + "="*80)
        print("PATTERN REVERSAL STRATEGY COMPARISON")
        print("="*80)
        print(f"{'Strategy':<35} {'Trades':>7} {'Return':>8} {'WinRate':>9} {'PF':>6} {'AvgBars':>8}")
        print("-"*80)

        results_sorted = sorted(results, key=lambda x: x['return'], reverse=True)
        for r in results_sorted:
            print(f"{r['pattern']:<35} {r['trades']:>7} {r['return']:>7.2f}% {r['win_rate']:>8.1f}% {r['profit_factor']:>5.2f} {r['avg_bars']:>8.1f}")

        best = results_sorted[0]
        print("\n" + "="*60)
        print(f"BEST PATTERN STRATEGY: {best['pattern']}")
        print("="*60)
        print(f"Return: {best['return']:.2f}%")
        print(f"Win Rate: {best['win_rate']:.1f}%")
        print(f"Profit Factor: {best['profit_factor']:.2f}")

        # Compare to scalping
        print("\n" + "="*60)
        print("COMPARISON TO PREVIOUS BEST APPROACHES")
        print("="*60)
        print(f"Scalping (Momentum 1:3):        -0.59%")
        print(f"Mean-Reversion (RSI < 20):      -2.91%")
        print(f"Pattern Reversal ({best['pattern']}): {best['return']:+.2f}%")

        # Save best trades
        best['trades_df'].to_csv('results/TRUMP_pattern_reversal_trades.csv', index=False)
        print(f"\nBest strategy trades saved to results/TRUMP_pattern_reversal_trades.csv")

if __name__ == "__main__":
    main()