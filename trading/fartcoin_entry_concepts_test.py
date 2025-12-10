"""
FARTCOIN PUMP/DUMP STRATEGY - PHASE 1: WIDE NET
Testuj 7 różnych entry concepts z minimalnym filtrowaniem
Cel: Złap JAK NAJWIĘCEJ winners (high recall)
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple

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

def calculate_rsi(close, period=14):
    """RSI calculation"""
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_bollinger_bands(close, period=20, std=2):
    """Bollinger Bands"""
    sma = close.rolling(period).mean()
    std_dev = close.rolling(period).std()
    upper = sma + (std_dev * std)
    lower = sma - (std_dev * std)
    bandwidth = (upper - lower) / sma * 100
    return upper, lower, bandwidth

# ====================================================================================
# CONCEPT 1: EMA CROSSOVER + VOLUME
# ====================================================================================
def concept_1_ema_cross(df):
    """
    Fast EMA crosses slow EMA + volume confirmation
    MINIMAL filters - let it catch everything
    """
    df['ema8'] = calculate_ema(df['close'], 8)
    df['ema21'] = calculate_ema(df['close'], 21)
    df['ema_cross_up'] = (df['ema8'] > df['ema21']) & (df['ema8'].shift(1) <= df['ema21'].shift(1))
    df['ema_cross_down'] = (df['ema8'] < df['ema21']) & (df['ema8'].shift(1) >= df['ema21'].shift(1))

    # Volume filter (light)
    df['vol_ma'] = df['volume'].rolling(20).mean()
    df['high_vol'] = df['volume'] > df['vol_ma'] * 1.2

    signals = []
    for i in range(len(df)):
        if df['ema_cross_up'].iloc[i] and df['high_vol'].iloc[i]:
            signals.append(('LONG', i))
        elif df['ema_cross_down'].iloc[i] and df['high_vol'].iloc[i]:
            signals.append(('SHORT', i))

    return signals

# ====================================================================================
# CONCEPT 2: RSI MOMENTUM
# ====================================================================================
def concept_2_rsi_momentum(df):
    """
    RSI crosses threshold = momentum shift
    Like MOODENG but wider thresholds
    """
    df['rsi'] = calculate_rsi(df['close'])
    df['sma20'] = df['close'].rolling(20).mean()

    # RSI momentum
    df['rsi_cross_up'] = (df['rsi'] >= 55) & (df['rsi'].shift(1) < 55)
    df['rsi_cross_down'] = (df['rsi'] <= 45) & (df['rsi'].shift(1) > 45)

    # Candle strength (minimal)
    df['body_pct'] = abs(df['close'] - df['open']) / df['open'] * 100

    signals = []
    for i in range(len(df)):
        if df['rsi_cross_up'].iloc[i] and df['body_pct'].iloc[i] > 0.3:
            signals.append(('LONG', i))
        elif df['rsi_cross_down'].iloc[i] and df['body_pct'].iloc[i] > 0.3:
            signals.append(('SHORT', i))

    return signals

# ====================================================================================
# CONCEPT 3: ATR EXPANSION (Volatility Breakout)
# ====================================================================================
def concept_3_atr_expansion(df):
    """
    ATR spikes = volatility breakout = beginning of big move
    """
    df['atr'] = calculate_atr(df['high'], df['low'], df['close'])
    df['atr_ma'] = df['atr'].rolling(20).mean()
    df['atr_ratio'] = df['atr'] / df['atr_ma']

    # Direction from price action
    df['bullish'] = df['close'] > df['open']
    df['bearish'] = df['close'] < df['open']

    # ATR expansion
    df['atr_expanding'] = df['atr_ratio'] > 1.5

    signals = []
    for i in range(len(df)):
        if df['atr_expanding'].iloc[i]:
            if df['bullish'].iloc[i]:
                signals.append(('LONG', i))
            elif df['bearish'].iloc[i]:
                signals.append(('SHORT', i))

    return signals

# ====================================================================================
# CONCEPT 4: VOLUME ZONES (Like TRUMP/DOGE)
# ====================================================================================
def concept_4_volume_zones(df):
    """
    Sustained volume at price extremes
    """
    df['vol_ma'] = df['volume'].rolling(20).mean()
    df['high_vol'] = df['volume'] > df['vol_ma'] * 1.5

    # Find zones (5+ consecutive high vol bars)
    df['vol_zone'] = 0
    zone_count = 0
    for i in range(len(df)):
        if df['high_vol'].iloc[i]:
            zone_count += 1
        else:
            zone_count = 0
        df.loc[df.index[i], 'vol_zone'] = zone_count

    # Price extremes (20 bar lookback)
    df['local_low'] = df['low'] == df['low'].rolling(20, center=True).min()
    df['local_high'] = df['high'] == df['high'].rolling(20, center=True).max()

    signals = []
    for i in range(len(df)):
        if df['vol_zone'].iloc[i] >= 5:
            # Wait for zone to end
            if i < len(df) - 1 and df['high_vol'].iloc[i+1] == False:
                if df['local_low'].iloc[i]:
                    signals.append(('LONG', i+1))
                elif df['local_high'].iloc[i]:
                    signals.append(('SHORT', i+1))

    return signals

# ====================================================================================
# CONCEPT 5: MULTI-TIMEFRAME ALIGNMENT
# ====================================================================================
def concept_5_multi_tf(df):
    """
    1m explosive + 5m confirmation (simplified)
    """
    # 5m proxy: 5-bar rolling indicators
    df['close_5m'] = df['close'].rolling(5).mean()
    df['sma50_5m'] = df['close'].rolling(250).mean()  # 50 candles on 5m = 250 on 1m

    # 1m explosive candle
    df['body_pct'] = abs(df['close'] - df['open']) / df['open'] * 100
    df['explosive'] = df['body_pct'] > 1.0
    df['vol_ma'] = df['volume'].rolling(20).mean()
    df['vol_spike'] = df['volume'] > df['vol_ma'] * 2.0

    # 5m trend
    df['uptrend_5m'] = df['close_5m'] > df['sma50_5m']
    df['downtrend_5m'] = df['close_5m'] < df['sma50_5m']

    signals = []
    for i in range(len(df)):
        if df['explosive'].iloc[i] and df['vol_spike'].iloc[i]:
            if df['close'].iloc[i] > df['open'].iloc[i] and df['uptrend_5m'].iloc[i]:
                signals.append(('LONG', i))
            elif df['close'].iloc[i] < df['open'].iloc[i] and df['downtrend_5m'].iloc[i]:
                signals.append(('SHORT', i))

    return signals

# ====================================================================================
# CONCEPT 6: BOLLINGER SQUEEZE BREAKOUT
# ====================================================================================
def concept_6_bb_squeeze(df):
    """
    BB bandwidth contracts (squeeze) then expands (breakout)
    """
    upper, lower, bandwidth = calculate_bollinger_bands(df['close'])
    df['bb_upper'] = upper
    df['bb_lower'] = lower
    df['bb_width'] = bandwidth

    # Squeeze = narrow bands
    df['bb_squeeze'] = df['bb_width'] < df['bb_width'].rolling(20).mean() * 0.8

    # Breakout = price breaks bands
    df['breakout_up'] = df['close'] > df['bb_upper']
    df['breakout_down'] = df['close'] < df['bb_lower']

    signals = []
    # Look for breakout after squeeze
    for i in range(5, len(df)):
        # Was there a squeeze in last 5 bars?
        recent_squeeze = df['bb_squeeze'].iloc[i-5:i].any()

        if recent_squeeze:
            if df['breakout_up'].iloc[i]:
                signals.append(('LONG', i))
            elif df['breakout_down'].iloc[i]:
                signals.append(('SHORT', i))

    return signals

# ====================================================================================
# CONCEPT 7: EMA DISTANCE (Mean Reversion or Continuation)
# ====================================================================================
def concept_7_ema_distance(df):
    """
    Price far from EMA = either reversion or continuation
    Test both approaches
    """
    df['ema20'] = calculate_ema(df['close'], 20)
    df['distance'] = (df['close'] - df['ema20']) / df['ema20'] * 100

    # Extreme distance
    df['far_above'] = df['distance'] > 2.0
    df['far_below'] = df['distance'] < -2.0

    # Momentum
    df['rsi'] = calculate_rsi(df['close'])

    signals = []
    for i in range(len(df)):
        # Continuation approach (momentum in same direction)
        if df['far_above'].iloc[i] and df['rsi'].iloc[i] > 60:
            signals.append(('LONG', i))
        elif df['far_below'].iloc[i] and df['rsi'].iloc[i] < 40:
            signals.append(('SHORT', i))

    return signals

# ====================================================================================
# BACKTESTING ENGINE
# ====================================================================================
def backtest_concept(df, signals, concept_name):
    """
    Backtest with wide TP (8x ATR) and trailing stop option
    """
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

        # Exit rules
        sl_dist = 2.0 * entry_atr
        tp_dist = 8.0 * entry_atr

        if direction == 'LONG':
            sl_price = entry_price - sl_dist
            tp_price = entry_price + tp_dist
        else:  # SHORT
            sl_price = entry_price + sl_dist
            tp_price = entry_price - tp_dist

        # Walk forward to find exit
        exit_idx = None
        exit_price = None
        exit_reason = None
        max_profit = 0

        for i in range(entry_idx + 1, min(entry_idx + 200, len(df))):  # Max 200 bars (3.3 hours)
            current_high = df['high'].iloc[i]
            current_low = df['low'].iloc[i]
            current_close = df['close'].iloc[i]

            if direction == 'LONG':
                # Check SL
                if current_low <= sl_price:
                    exit_idx = i
                    exit_price = sl_price
                    exit_reason = 'SL'
                    break
                # Check TP
                if current_high >= tp_price:
                    exit_idx = i
                    exit_price = tp_price
                    exit_reason = 'TP'
                    break
                # Track max profit for trailing stop
                profit_pct = (current_high - entry_price) / entry_price * 100
                max_profit = max(max_profit, profit_pct)

            else:  # SHORT
                # Check SL
                if current_high >= sl_price:
                    exit_idx = i
                    exit_price = sl_price
                    exit_reason = 'SL'
                    break
                # Check TP
                if current_low <= tp_price:
                    exit_idx = i
                    exit_price = tp_price
                    exit_reason = 'TP'
                    break
                # Track max profit
                profit_pct = (entry_price - current_low) / entry_price * 100
                max_profit = max(max_profit, profit_pct)

        # Time exit if no SL/TP hit
        if exit_idx is None:
            exit_idx = min(entry_idx + 199, len(df) - 1)
            exit_price = df['close'].iloc[exit_idx]
            exit_reason = 'TIME'

        # Calculate P&L
        if direction == 'LONG':
            pnl_pct = (exit_price - entry_price) / entry_price * 100
        else:
            pnl_pct = (entry_price - exit_price) / entry_price * 100

        # Fees
        pnl_pct -= 0.1  # 0.05% x2

        trades.append({
            'concept': concept_name,
            'direction': direction,
            'entry_idx': entry_idx,
            'exit_idx': exit_idx,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'pnl_pct': pnl_pct,
            'exit_reason': exit_reason,
            'bars_held': exit_idx - entry_idx,
            'max_profit_pct': max_profit
        })

    return trades

def analyze_results(trades, concept_name):
    """Analyze trade results"""
    if not trades:
        return {
            'concept': concept_name,
            'total_trades': 0,
            'win_rate': 0,
            'avg_winner': 0,
            'avg_loser': 0,
            'total_return': 0,
            'max_winner': 0,
            'top10_avg': 0
        }

    df_trades = pd.DataFrame(trades)

    winners = df_trades[df_trades['pnl_pct'] > 0]
    losers = df_trades[df_trades['pnl_pct'] <= 0]

    top10_winners = df_trades.nlargest(10, 'pnl_pct')['pnl_pct'].mean() if len(df_trades) >= 10 else df_trades['pnl_pct'].max()

    return {
        'concept': concept_name,
        'total_trades': len(trades),
        'win_rate': len(winners) / len(trades) * 100 if trades else 0,
        'avg_winner': winners['pnl_pct'].mean() if len(winners) > 0 else 0,
        'avg_loser': losers['pnl_pct'].mean() if len(losers) > 0 else 0,
        'total_return': df_trades['pnl_pct'].sum(),
        'max_winner': df_trades['pnl_pct'].max(),
        'top10_avg': top10_winners,
        'avg_bars_held': df_trades['bars_held'].mean(),
        'tp_rate': (df_trades['exit_reason'] == 'TP').sum() / len(trades) * 100
    }

# ====================================================================================
# MAIN
# ====================================================================================
def main():
    print("🔍 FARTCOIN - PHASE 1: TESTING ENTRY CONCEPTS\n")

    # Load data
    df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/fartcoin_30d_bingx.csv')
    df.columns = df.columns.str.lower()
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    print(f"📊 Data: {len(df):,} candles ({df['timestamp'].min()} to {df['timestamp'].max()})\n")

    # Test all concepts
    concepts = [
        ("1_EMA_Cross", concept_1_ema_cross),
        ("2_RSI_Momentum", concept_2_rsi_momentum),
        ("3_ATR_Expansion", concept_3_atr_expansion),
        ("4_Volume_Zones", concept_4_volume_zones),
        ("5_Multi_TF", concept_5_multi_tf),
        ("6_BB_Squeeze", concept_6_bb_squeeze),
        ("7_EMA_Distance", concept_7_ema_distance)
    ]

    all_results = []
    all_trades = []

    for concept_name, concept_func in concepts:
        print(f"⚡ Testing: {concept_name}...")

        # Generate signals
        signals = concept_func(df.copy())

        # Backtest
        trades = backtest_concept(df, signals, concept_name)
        all_trades.extend(trades)

        # Analyze
        results = analyze_results(trades, concept_name)
        all_results.append(results)

        print(f"   Signals: {len(signals)} | Trades: {results['total_trades']} | Win%: {results['win_rate']:.1f}% | Return: {results['total_return']:.2f}%")
        print(f"   Top10 Avg: {results['top10_avg']:.2f}% | Max Winner: {results['max_winner']:.2f}% | TP Rate: {results['tp_rate']:.1f}%\n")

    # Summary
    df_results = pd.DataFrame(all_results)
    df_results = df_results.sort_values('top10_avg', ascending=False)

    print("\n" + "="*100)
    print("📊 RESULTS RANKED BY TOP 10 AVG (Best at catching BIG winners)")
    print("="*100)
    print(df_results.to_string(index=False))

    # Save
    df_results.to_csv('/workspaces/Carebiuro_windykacja/trading/results/fartcoin_concept_comparison.csv', index=False)

    df_all_trades = pd.DataFrame(all_trades)
    df_all_trades.to_csv('/workspaces/Carebiuro_windykacja/trading/results/fartcoin_all_concept_trades.csv', index=False)

    print("\n✅ Saved:")
    print("   - trading/results/fartcoin_concept_comparison.csv")
    print("   - trading/results/fartcoin_all_concept_trades.csv")

    # Recommendation
    best = df_results.iloc[0]
    print("\n" + "="*100)
    print("⭐ BEST CONCEPT FOR CATCHING BIG WINNERS")
    print("="*100)
    print(f"Concept: {best['concept']}")
    print(f"Top 10 Average: {best['top10_avg']:.2f}%")
    print(f"Max Winner: {best['max_winner']:.2f}%")
    print(f"Total Trades: {best['total_trades']}")
    print(f"Win Rate: {best['win_rate']:.1f}%")
    print(f"\n👉 NEXT: Add filters to remove losers while keeping these big winners")

if __name__ == '__main__':
    main()
