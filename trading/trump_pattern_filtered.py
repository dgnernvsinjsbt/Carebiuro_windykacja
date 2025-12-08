"""
TRUMP Chart Pattern Reversal Trading - FILTERED VERSION
Apply strict filters to reduce from 1,600 trades to ~100-200 quality setups
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
    df['sma_200'] = df['close'].rolling(200).mean()
    df['ema_20'] = df['close'].ewm(span=20).mean()

    # Higher timeframe trend (15m)
    df['htf_close'] = df['close'].rolling(15).mean()
    df['htf_sma50'] = df['htf_close'].rolling(50).mean()

    # ATR for stops and volatility filter
    df['tr'] = np.maximum(
        df['high'] - df['low'],
        np.maximum(
            abs(df['high'] - df['close'].shift(1)),
            abs(df['low'] - df['close'].shift(1))
        )
    )
    df['atr'] = df['tr'].rolling(14).mean()
    df['atr_pct'] = (df['atr'] / df['close']) * 100

    # Volume filters
    df['volume_sma'] = df['volume'].rolling(20).mean()
    df['volume_ratio'] = df['volume'] / df['volume_sma']

    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))

    # Swing highs/lows for pattern detection
    df['swing_high'] = df['high'].rolling(5, center=True).max() == df['high']
    df['swing_low'] = df['low'].rolling(5, center=True).min() == df['low']

    # Momentum/chop detection
    df['price_change_10'] = df['close'].pct_change(10)
    df['volatility_10'] = df['close'].rolling(10).std() / df['close']

    return df

def is_high_quality_setup(df, i, direction):
    """Apply strict filters to ensure high-quality setups only"""

    # 1. VOLATILITY FILTER: ATR must be above median (avoid dead zones)
    atr_pct = df.loc[i, 'atr_pct']
    if pd.isna(atr_pct) or atr_pct < 0.15:  # Below 0.15% ATR = too quiet
        return False

    # 2. VOLUME FILTER: Volume must be 1.5x+ average
    volume_ratio = df.loc[i, 'volume_ratio']
    if pd.isna(volume_ratio) or volume_ratio < 1.5:
        return False

    # 3. SESSION FILTER: Only trade during active sessions (US/EU hours)
    hour = df.loc[i, 'timestamp'].hour
    # EU: 7-12 UTC, US: 13-21 UTC
    if not (7 <= hour <= 21):
        return False

    # 4. HIGHER TIMEFRAME ALIGNMENT
    htf_close = df.loc[i, 'htf_close']
    htf_sma50 = df.loc[i, 'htf_sma50']

    if pd.isna(htf_close) or pd.isna(htf_sma50):
        return False

    if direction == 'long':
        # For longs: 15m trend should be up or at least not strongly down
        if htf_close < htf_sma50 * 0.998:  # 15m below SMA50
            return False
    else:  # short
        # For shorts: 15m trend should be down or at least not strongly up
        if htf_close > htf_sma50 * 1.002:
            return False

    # 5. MOMENTUM FILTER: Recent price movement (avoid extreme chop)
    price_change_10 = df.loc[i, 'price_change_10']
    if pd.isna(price_change_10):
        return False

    if direction == 'long':
        # Don't buy into extreme downtrend
        if price_change_10 < -0.008:  # -0.8% in 10 bars
            return False
    else:
        # Don't short into extreme uptrend
        if price_change_10 > 0.008:
            return False

    # 6. RSI FILTER: Not in extreme territory
    rsi = df.loc[i, 'rsi']
    if pd.isna(rsi):
        return False

    if direction == 'long':
        # For longs: RSI should be oversold/neutral (not overbought)
        if rsi > 60:
            return False
    else:
        # For shorts: RSI should be overbought/neutral (not oversold)
        if rsi < 40:
            return False

    return True

def detect_double_bottom_filtered(df, i, lookback=30):
    """Detect double bottom with strict quality filters"""
    if i < lookback + 10:
        return False

    window = df.iloc[i-lookback:i]
    lows = window[window['swing_low']].copy()

    if len(lows) < 2:
        return False

    last_two = lows.tail(2)
    low1_price = last_two.iloc[0]['low']
    low2_price = last_two.iloc[1]['low']

    # Tighter tolerance for pattern match
    if abs(low1_price - low2_price) / low1_price > 0.002:  # 0.2% tolerance
        return False

    # Check neckline break
    between_high = window.loc[last_two.index[0]:last_two.index[1], 'high'].max()
    if df.loc[i, 'close'] <= between_high * 1.002:  # Must break neckline by 0.2%
        return False

    # Apply quality filters
    if not is_high_quality_setup(df, i, 'long'):
        return False

    return True

def detect_double_top_filtered(df, i, lookback=30):
    """Detect double top with strict quality filters"""
    if i < lookback + 10:
        return False

    window = df.iloc[i-lookback:i]
    highs = window[window['swing_high']].copy()

    if len(highs) < 2:
        return False

    last_two = highs.tail(2)
    high1_price = last_two.iloc[0]['high']
    high2_price = last_two.iloc[1]['high']

    if abs(high1_price - high2_price) / high1_price > 0.002:
        return False

    between_low = window.loc[last_two.index[0]:last_two.index[1], 'low'].min()
    if df.loc[i, 'close'] >= between_low * 0.998:
        return False

    if not is_high_quality_setup(df, i, 'short'):
        return False

    return True

def detect_support_bounce_filtered(df, i, lookback=40):
    """Support bounce with strict filters"""
    if i < lookback + 10:
        return False

    window = df.iloc[i-lookback:i]
    swing_lows = window[window['swing_low']]['low'].values

    if len(swing_lows) < 3:  # Need at least 3 touches
        return False

    support = np.median(swing_lows)
    recent_low = df.iloc[i-3:i]['low'].min()
    current_close = df.loc[i, 'close']

    # Must touch support tightly
    if abs(recent_low - support) / support > 0.0015:
        return False

    # Must bounce convincingly (0.3%+)
    if current_close <= recent_low * 1.003:
        return False

    if not is_high_quality_setup(df, i, 'long'):
        return False

    return True

def detect_resistance_reject_filtered(df, i, lookback=40):
    """Resistance rejection with strict filters"""
    if i < lookback + 10:
        return False

    window = df.iloc[i-lookback:i]
    swing_highs = window[window['swing_high']]['high'].values

    if len(swing_highs) < 3:
        return False

    resistance = np.median(swing_highs)
    recent_high = df.iloc[i-3:i]['high'].max()
    current_close = df.loc[i, 'close']

    if abs(recent_high - resistance) / resistance > 0.0015:
        return False

    if current_close >= recent_high * 0.997:
        return False

    if not is_high_quality_setup(df, i, 'short'):
        return False

    return True

def detect_v_bottom_filtered(df, i):
    """V-bottom with strict quality check"""
    if i < 12:
        return False

    lookback = df.iloc[i-12:i]
    min_idx = lookback['low'].idxmin()
    min_price = lookback.loc[min_idx, 'low']

    before_decline = lookback.loc[:min_idx]['close']
    if len(before_decline) < 4:
        return False

    decline_pct = (before_decline.iloc[0] - min_price) / before_decline.iloc[0]

    after_rise = lookback.loc[min_idx:]['close']
    if len(after_rise) < 4:
        return False

    rise_pct = (after_rise.iloc[-1] - min_price) / min_price

    # Stronger V pattern required
    if decline_pct < 0.005 or rise_pct < 0.004:  # 0.5%+ drop, 0.4%+ rise
        return False

    if not is_high_quality_setup(df, i, 'long'):
        return False

    return True

def detect_v_top_filtered(df, i):
    """V-top with strict quality check"""
    if i < 12:
        return False

    lookback = df.iloc[i-12:i]
    max_idx = lookback['high'].idxmax()
    max_price = lookback.loc[max_idx, 'high']

    before_rise = lookback.loc[:max_idx]['close']
    if len(before_rise) < 4:
        return False

    rise_pct = (max_price - before_rise.iloc[0]) / before_rise.iloc[0]

    after_decline = lookback.loc[max_idx:]['close']
    if len(after_decline) < 4:
        return False

    decline_pct = (max_price - after_decline.iloc[-1]) / max_price

    if rise_pct < 0.005 or decline_pct < 0.004:
        return False

    if not is_high_quality_setup(df, i, 'short'):
        return False

    return True

def backtest_pattern_strategy(df, pattern_name, entry_func, sl_atr_mult, tp_atr_mult, direction):
    """Backtest a pattern-based reversal strategy"""

    df = df.copy()
    trades = []
    position = None

    for i in range(250, len(df)):  # Start later to have HTF data
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
                    pnl_pct = (exit_price - entry_price) / entry_price - 0.001
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
    print("TRUMP PATTERN REVERSALS - FILTERED VERSION")
    print("Strict filters: HTF trend, volume, volatility, session")
    print("Goal: ~100-200 quality trades vs 1,600 garbage signals")
    print("="*60)

    df = load_data()
    df = calculate_indicators(df)

    print(f"\nData loaded: {len(df)} candles")
    print(f"Period: {df['timestamp'].min()} to {df['timestamp'].max()}\n")

    # Test various pattern strategies with FILTERS
    strategies = [
        {
            'name': 'Double Bottom FILTERED (Long)',
            'func': lambda df, i: detect_double_bottom_filtered(df, i, lookback=30),
            'sl': 1.5,
            'tp': 3.0,
            'direction': 'long'
        },
        {
            'name': 'Double Top FILTERED (Short)',
            'func': lambda df, i: detect_double_top_filtered(df, i, lookback=30),
            'sl': 1.5,
            'tp': 3.0,
            'direction': 'short'
        },
        {
            'name': 'Support Bounce FILTERED (Long)',
            'func': lambda df, i: detect_support_bounce_filtered(df, i, lookback=40),
            'sl': 1.0,
            'tp': 2.5,
            'direction': 'long'
        },
        {
            'name': 'Resistance Reject FILTERED (Short)',
            'func': lambda df, i: detect_resistance_reject_filtered(df, i, lookback=40),
            'sl': 1.0,
            'tp': 2.5,
            'direction': 'short'
        },
        {
            'name': 'V-Bottom FILTERED (Long)',
            'func': detect_v_bottom_filtered,
            'sl': 1.0,
            'tp': 2.5,
            'direction': 'long'
        },
        {
            'name': 'V-Top FILTERED (Short)',
            'func': detect_v_top_filtered,
            'sl': 1.0,
            'tp': 2.5,
            'direction': 'short'
        },
        {
            'name': 'V-Bottom FILTERED Wide R:R (Long)',
            'func': detect_v_bottom_filtered,
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
            print(f"No trades generated (filters too strict)")
            continue

        results.append(result)

        print(f"Total Trades: {result['trades']}")
        print(f"Total Return: {result['return']:.2f}%")
        print(f"Win Rate: {result['win_rate']:.1f}%")
        print(f"Profit Factor: {result['profit_factor']:.2f}")
        print(f"Avg Win: {result['avg_win']:.2f}%")
        print(f"Avg Loss: {result['avg_loss']:.2f}%")
        print(f"Avg Bars Held: {result['avg_bars']:.1f}")

        exit_counts = result['trades_df']['exit_reason'].value_counts()
        print(f"\nExit Reasons: {dict(exit_counts)}")

    # Summary comparison
    if results:
        print("\n" + "="*80)
        print("FILTERED PATTERN STRATEGY COMPARISON")
        print("="*80)
        print(f"{'Strategy':<40} {'Trades':>7} {'Return':>8} {'WinRate':>9} {'PF':>6}")
        print("-"*80)

        results_sorted = sorted(results, key=lambda x: x['return'], reverse=True)
        for r in results_sorted:
            print(f"{r['pattern']:<40} {r['trades']:>7} {r['return']:>7.2f}% {r['win_rate']:>8.1f}% {r['profit_factor']:>5.2f}")

        best = results_sorted[0]
        print("\n" + "="*60)
        print(f"BEST FILTERED STRATEGY: {best['pattern']}")
        print("="*60)
        print(f"Return: {best['return']:.2f}%")
        print(f"Win Rate: {best['win_rate']:.1f}%")
        print(f"Profit Factor: {best['profit_factor']:.2f}")
        print(f"Trades: {best['trades']}")

        # Compare to unfiltered and scalping
        print("\n" + "="*60)
        print("COMPARISON")
        print("="*60)
        print(f"Scalping (no patterns):              -0.59% | 160 trades")
        print(f"Patterns UNFILTERED (Double Bottom): -130.16% | 1,336 trades")
        print(f"Patterns FILTERED ({best['pattern'][:30]}): {best['return']:+.2f}% | {best['trades']} trades")

        # Save best trades
        best['trades_df'].to_csv('results/TRUMP_pattern_filtered_trades.csv', index=False)
        print(f"\nBest strategy trades saved to results/TRUMP_pattern_filtered_trades.csv")
    else:
        print("\n⚠️ NO TRADES GENERATED - Filters eliminated all setups")

if __name__ == "__main__":
    main()
