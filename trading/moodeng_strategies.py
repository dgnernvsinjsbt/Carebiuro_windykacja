#!/usr/bin/env python3
"""
MOODENG-Specific Trading Strategies
Developed from data analysis showing:
- Lower body thresholds needed (0.5-0.7% vs 1.2%)
- Bullish momentum continuation works
- Bearish moves mean-revert (contrarian buy)
- Peak volatility 14:00-21:00 UTC
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')


def load_moodeng_data() -> pd.DataFrame:
    """Load and prepare MOODENG data"""
    df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/moodeng_usdt_1m_lbank.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)

    # Calculate indicators
    df['body'] = df['close'] - df['open']
    df['body_pct'] = abs(df['body']) / df['open'] * 100
    df['range_pct'] = (df['high'] - df['low']) / df['low'] * 100
    df['is_bullish'] = df['close'] > df['open']
    df['returns'] = df['close'].pct_change() * 100

    # ATR
    df['tr'] = np.maximum(
        df['high'] - df['low'],
        np.maximum(
            abs(df['high'] - df['close'].shift(1)),
            abs(df['low'] - df['close'].shift(1))
        )
    )
    df['atr'] = df['tr'].rolling(14).mean()
    df['atr_pct'] = df['atr'] / df['close'] * 100

    # Volume
    df['vol_ma'] = df['volume'].rolling(20).mean()
    df['vol_ratio'] = df['volume'] / df['vol_ma']

    # RSI
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))

    # SMAs
    df['sma_10'] = df['close'].rolling(10).mean()
    df['sma_20'] = df['close'].rolling(20).mean()
    df['sma_50'] = df['close'].rolling(50).mean()

    # Hour
    df['hour'] = df['timestamp'].dt.hour

    # Momentum (last N candles direction)
    df['mom_3'] = df['close'].diff(3)
    df['mom_5'] = df['close'].diff(5)

    return df


def strategy_1_momentum_continuation(df: pd.DataFrame,
                                      body_thresh: float = 0.7,
                                      vol_thresh: float = 2.0,
                                      sl_mult: float = 1.5,
                                      tp_mult: float = 4.0,
                                      max_bars: int = 30) -> dict:
    """
    Strategy 1: Bullish Momentum Continuation
    - Entry: Bullish candle with body > threshold + volume spike
    - Exit: ATR-based SL/TP or time-based
    - Based on finding: bullish big moves have +5.76% avg upside in 5 bars
    """
    trades = []
    in_position = False
    entry_price = entry_idx = stop_loss = take_profit = 0

    for i in range(50, len(df)):
        row = df.iloc[i]

        if not in_position:
            # Entry: Bullish explosive candle + volume
            if (row['is_bullish'] and
                row['body_pct'] > body_thresh and
                row['vol_ratio'] > vol_thresh and
                row['rsi'] < 70):  # Not overbought

                in_position = True
                entry_price = row['close']
                entry_idx = i
                atr = row['atr']
                stop_loss = entry_price - (atr * sl_mult)
                take_profit = entry_price + (atr * tp_mult)
        else:
            bars_held = i - entry_idx

            # Check exits
            if row['low'] <= stop_loss:
                pnl = (stop_loss - entry_price) / entry_price * 100
                trades.append({'entry_idx': entry_idx, 'exit_idx': i,
                              'pnl_pct': pnl, 'result': 'SL', 'bars': bars_held})
                in_position = False

            elif row['high'] >= take_profit:
                pnl = (take_profit - entry_price) / entry_price * 100
                trades.append({'entry_idx': entry_idx, 'exit_idx': i,
                              'pnl_pct': pnl, 'result': 'TP', 'bars': bars_held})
                in_position = False

            elif bars_held >= max_bars:  # Time exit
                exit_price = row['close']
                pnl = (exit_price - entry_price) / entry_price * 100
                trades.append({'entry_idx': entry_idx, 'exit_idx': i,
                              'pnl_pct': pnl, 'result': 'TIME', 'bars': bars_held})
                in_position = False

    return {'name': 'Momentum Continuation', 'trades': trades,
            'params': {'body': body_thresh, 'vol': vol_thresh, 'sl': sl_mult, 'tp': tp_mult}}


def strategy_2_mean_reversion_after_bearish(df: pd.DataFrame,
                                             body_thresh: float = 0.7,
                                             sl_mult: float = 2.0,
                                             tp_mult: float = 3.0,
                                             max_bars: int = 60) -> dict:
    """
    Strategy 2: Mean Reversion After Bearish Drop
    - Entry: After bearish candle with big body (contrarian buy)
    - Exit: ATR-based or time-based
    - Based on finding: bearish moves tend to recover (+0.79% avg after 60 bars)
    """
    trades = []
    in_position = False
    entry_price = entry_idx = stop_loss = take_profit = 0

    for i in range(50, len(df)):
        row = df.iloc[i]

        if not in_position:
            # Entry: After bearish explosive candle (contrarian)
            if (not row['is_bullish'] and
                row['body_pct'] > body_thresh and
                row['rsi'] < 45):  # Oversold-ish

                in_position = True
                entry_price = row['close']
                entry_idx = i
                atr = row['atr']
                stop_loss = entry_price - (atr * sl_mult)
                take_profit = entry_price + (atr * tp_mult)
        else:
            bars_held = i - entry_idx

            if row['low'] <= stop_loss:
                pnl = (stop_loss - entry_price) / entry_price * 100
                trades.append({'entry_idx': entry_idx, 'exit_idx': i,
                              'pnl_pct': pnl, 'result': 'SL', 'bars': bars_held})
                in_position = False

            elif row['high'] >= take_profit:
                pnl = (take_profit - entry_price) / entry_price * 100
                trades.append({'entry_idx': entry_idx, 'exit_idx': i,
                              'pnl_pct': pnl, 'result': 'TP', 'bars': bars_held})
                in_position = False

            elif bars_held >= max_bars:
                exit_price = row['close']
                pnl = (exit_price - entry_price) / entry_price * 100
                trades.append({'entry_idx': entry_idx, 'exit_idx': i,
                              'pnl_pct': pnl, 'result': 'TIME', 'bars': bars_held})
                in_position = False

    return {'name': 'Mean Reversion', 'trades': trades,
            'params': {'body': body_thresh, 'sl': sl_mult, 'tp': tp_mult}}


def strategy_3_session_breakout(df: pd.DataFrame,
                                 body_thresh: float = 0.5,
                                 vol_thresh: float = 2.5,
                                 sl_mult: float = 1.5,
                                 tp_mult: float = 5.0,
                                 active_hours: tuple = (14, 21)) -> dict:
    """
    Strategy 3: Session Breakout (Peak Hours Only)
    - Entry: During peak volatility hours (14:00-21:00 UTC)
    - Higher probability of continuation during active sessions
    """
    trades = []
    in_position = False
    entry_price = entry_idx = stop_loss = take_profit = 0

    for i in range(50, len(df)):
        row = df.iloc[i]

        if not in_position:
            # Only trade during active hours
            hour_ok = active_hours[0] <= row['hour'] <= active_hours[1]

            if (hour_ok and
                row['is_bullish'] and
                row['body_pct'] > body_thresh and
                row['vol_ratio'] > vol_thresh):

                in_position = True
                entry_price = row['close']
                entry_idx = i
                atr = row['atr']
                stop_loss = entry_price - (atr * sl_mult)
                take_profit = entry_price + (atr * tp_mult)
        else:
            bars_held = i - entry_idx

            if row['low'] <= stop_loss:
                pnl = (stop_loss - entry_price) / entry_price * 100
                trades.append({'entry_idx': entry_idx, 'exit_idx': i,
                              'pnl_pct': pnl, 'result': 'SL', 'bars': bars_held})
                in_position = False

            elif row['high'] >= take_profit:
                pnl = (take_profit - entry_price) / entry_price * 100
                trades.append({'entry_idx': entry_idx, 'exit_idx': i,
                              'pnl_pct': pnl, 'result': 'TP', 'bars': bars_held})
                in_position = False

            elif bars_held >= 60:  # 1 hour max
                exit_price = row['close']
                pnl = (exit_price - entry_price) / entry_price * 100
                trades.append({'entry_idx': entry_idx, 'exit_idx': i,
                              'pnl_pct': pnl, 'result': 'TIME', 'bars': bars_held})
                in_position = False

    return {'name': 'Session Breakout', 'trades': trades,
            'params': {'body': body_thresh, 'vol': vol_thresh, 'hours': active_hours}}


def strategy_4_rsi_momentum(df: pd.DataFrame,
                            rsi_entry: float = 55,
                            body_thresh: float = 0.5,
                            sl_mult: float = 1.5,
                            tp_mult: float = 4.0) -> dict:
    """
    Strategy 4: RSI Momentum Breakout
    - Entry: RSI crosses above threshold + bullish candle
    - Riding momentum when RSI shows strength
    """
    trades = []
    in_position = False
    entry_price = entry_idx = stop_loss = take_profit = 0

    for i in range(50, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i-1]

        if not in_position:
            # RSI crossing up + bullish confirmation
            rsi_cross = prev['rsi'] < rsi_entry and row['rsi'] >= rsi_entry

            if (rsi_cross and
                row['is_bullish'] and
                row['body_pct'] > body_thresh):

                in_position = True
                entry_price = row['close']
                entry_idx = i
                atr = row['atr']
                stop_loss = entry_price - (atr * sl_mult)
                take_profit = entry_price + (atr * tp_mult)
        else:
            bars_held = i - entry_idx

            if row['low'] <= stop_loss:
                pnl = (stop_loss - entry_price) / entry_price * 100
                trades.append({'entry_idx': entry_idx, 'exit_idx': i,
                              'pnl_pct': pnl, 'result': 'SL', 'bars': bars_held})
                in_position = False

            elif row['high'] >= take_profit:
                pnl = (take_profit - entry_price) / entry_price * 100
                trades.append({'entry_idx': entry_idx, 'exit_idx': i,
                              'pnl_pct': pnl, 'result': 'TP', 'bars': bars_held})
                in_position = False

            elif bars_held >= 60:
                exit_price = row['close']
                pnl = (exit_price - entry_price) / entry_price * 100
                trades.append({'entry_idx': entry_idx, 'exit_idx': i,
                              'pnl_pct': pnl, 'result': 'TIME', 'bars': bars_held})
                in_position = False

    return {'name': 'RSI Momentum', 'trades': trades,
            'params': {'rsi': rsi_entry, 'body': body_thresh}}


def strategy_5_volume_spike_scalp(df: pd.DataFrame,
                                   vol_thresh: float = 4.0,
                                   sl_mult: float = 1.0,
                                   tp_mult: float = 2.0,
                                   max_bars: int = 15) -> dict:
    """
    Strategy 5: Volume Spike Scalp
    - Entry: Extreme volume spike (4x+) with bullish candle
    - Quick scalp with tight stops
    """
    trades = []
    in_position = False
    entry_price = entry_idx = stop_loss = take_profit = 0

    for i in range(50, len(df)):
        row = df.iloc[i]

        if not in_position:
            if (row['is_bullish'] and
                row['vol_ratio'] > vol_thresh and
                row['body_pct'] > 0.3):  # Lower threshold for scalp

                in_position = True
                entry_price = row['close']
                entry_idx = i
                atr = row['atr']
                stop_loss = entry_price - (atr * sl_mult)
                take_profit = entry_price + (atr * tp_mult)
        else:
            bars_held = i - entry_idx

            if row['low'] <= stop_loss:
                pnl = (stop_loss - entry_price) / entry_price * 100
                trades.append({'entry_idx': entry_idx, 'exit_idx': i,
                              'pnl_pct': pnl, 'result': 'SL', 'bars': bars_held})
                in_position = False

            elif row['high'] >= take_profit:
                pnl = (take_profit - entry_price) / entry_price * 100
                trades.append({'entry_idx': entry_idx, 'exit_idx': i,
                              'pnl_pct': pnl, 'result': 'TP', 'bars': bars_held})
                in_position = False

            elif bars_held >= max_bars:
                exit_price = row['close']
                pnl = (exit_price - entry_price) / entry_price * 100
                trades.append({'entry_idx': entry_idx, 'exit_idx': i,
                              'pnl_pct': pnl, 'result': 'TIME', 'bars': bars_held})
                in_position = False

    return {'name': 'Volume Spike Scalp', 'trades': trades,
            'params': {'vol': vol_thresh, 'sl': sl_mult, 'tp': tp_mult}}


def analyze_results(result: dict) -> dict:
    """Analyze strategy results"""
    trades = result['trades']
    if not trades:
        return {**result, 'stats': {'trades': 0, 'return': 0, 'win_rate': 0, 'rr': 0, 'pf': 0, 'dd': 0}}

    df_trades = pd.DataFrame(trades)

    winners = df_trades[df_trades['pnl_pct'] > 0]
    losers = df_trades[df_trades['pnl_pct'] <= 0]

    total_trades = len(df_trades)
    win_rate = len(winners) / total_trades * 100

    avg_win = winners['pnl_pct'].mean() if len(winners) > 0 else 0
    avg_loss = abs(losers['pnl_pct'].mean()) if len(losers) > 0 else 0

    gross_profit = winners['pnl_pct'].sum() if len(winners) > 0 else 0
    gross_loss = abs(losers['pnl_pct'].sum()) if len(losers) > 0 else 0

    pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')
    rr = avg_win / avg_loss if avg_loss > 0 else float('inf')

    # Equity curve and drawdown
    equity = [100]
    for pnl in df_trades['pnl_pct']:
        equity.append(equity[-1] * (1 + pnl/100))

    peak = equity[0]
    max_dd = 0
    for e in equity:
        if e > peak:
            peak = e
        dd = (peak - e) / peak * 100
        max_dd = max(max_dd, dd)

    total_return = equity[-1] - 100

    return {
        **result,
        'stats': {
            'trades': total_trades,
            'return': total_return,
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'rr': rr,
            'pf': pf,
            'dd': max_dd,
            'avg_bars': df_trades['bars'].mean()
        }
    }


def run_all_strategies():
    """Run all strategies with multiple parameter sets"""
    print("=" * 80)
    print("MOODENG CUSTOM STRATEGY BACKTEST")
    print("=" * 80)

    df = load_moodeng_data()
    print(f"Loaded {len(df):,} candles")
    print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")

    all_results = []

    # Strategy 1: Momentum Continuation - multiple variants
    print("\n" + "-" * 40)
    print("STRATEGY 1: MOMENTUM CONTINUATION")
    print("-" * 40)

    variants_1 = [
        {'body_thresh': 0.5, 'vol_thresh': 2.0, 'sl_mult': 1.5, 'tp_mult': 3.0},
        {'body_thresh': 0.5, 'vol_thresh': 2.0, 'sl_mult': 1.5, 'tp_mult': 4.0},
        {'body_thresh': 0.5, 'vol_thresh': 2.0, 'sl_mult': 1.5, 'tp_mult': 5.0},
        {'body_thresh': 0.7, 'vol_thresh': 2.0, 'sl_mult': 1.5, 'tp_mult': 4.0},
        {'body_thresh': 0.7, 'vol_thresh': 2.5, 'sl_mult': 1.5, 'tp_mult': 4.0},
        {'body_thresh': 0.7, 'vol_thresh': 2.5, 'sl_mult': 2.0, 'tp_mult': 5.0},
        {'body_thresh': 1.0, 'vol_thresh': 2.0, 'sl_mult': 2.0, 'tp_mult': 6.0},
    ]

    for v in variants_1:
        result = strategy_1_momentum_continuation(df, **v)
        result = analyze_results(result)
        all_results.append(result)
        s = result['stats']
        print(f"Body {v['body_thresh']}, Vol {v['vol_thresh']}, SL {v['sl_mult']}x, TP {v['tp_mult']}x: "
              f"{s['trades']} trades, {s['return']:+.2f}%, WR {s['win_rate']:.0f}%, R:R {s['rr']:.1f}x")

    # Strategy 2: Mean Reversion after bearish
    print("\n" + "-" * 40)
    print("STRATEGY 2: MEAN REVERSION (BUY AFTER BEARISH)")
    print("-" * 40)

    variants_2 = [
        {'body_thresh': 0.5, 'sl_mult': 1.5, 'tp_mult': 2.0},
        {'body_thresh': 0.5, 'sl_mult': 2.0, 'tp_mult': 3.0},
        {'body_thresh': 0.7, 'sl_mult': 1.5, 'tp_mult': 2.5},
        {'body_thresh': 0.7, 'sl_mult': 2.0, 'tp_mult': 3.0},
        {'body_thresh': 1.0, 'sl_mult': 2.0, 'tp_mult': 4.0},
    ]

    for v in variants_2:
        result = strategy_2_mean_reversion_after_bearish(df, **v)
        result = analyze_results(result)
        all_results.append(result)
        s = result['stats']
        print(f"Body {v['body_thresh']}, SL {v['sl_mult']}x, TP {v['tp_mult']}x: "
              f"{s['trades']} trades, {s['return']:+.2f}%, WR {s['win_rate']:.0f}%, R:R {s['rr']:.1f}x")

    # Strategy 3: Session Breakout
    print("\n" + "-" * 40)
    print("STRATEGY 3: SESSION BREAKOUT (14:00-21:00 UTC)")
    print("-" * 40)

    variants_3 = [
        {'body_thresh': 0.5, 'vol_thresh': 2.0, 'sl_mult': 1.5, 'tp_mult': 4.0},
        {'body_thresh': 0.5, 'vol_thresh': 2.5, 'sl_mult': 1.5, 'tp_mult': 5.0},
        {'body_thresh': 0.7, 'vol_thresh': 2.5, 'sl_mult': 2.0, 'tp_mult': 5.0},
    ]

    for v in variants_3:
        result = strategy_3_session_breakout(df, **v)
        result = analyze_results(result)
        all_results.append(result)
        s = result['stats']
        print(f"Body {v['body_thresh']}, Vol {v['vol_thresh']}, SL {v['sl_mult']}x, TP {v['tp_mult']}x: "
              f"{s['trades']} trades, {s['return']:+.2f}%, WR {s['win_rate']:.0f}%, R:R {s['rr']:.1f}x")

    # Strategy 4: RSI Momentum
    print("\n" + "-" * 40)
    print("STRATEGY 4: RSI MOMENTUM BREAKOUT")
    print("-" * 40)

    variants_4 = [
        {'rsi_entry': 50, 'body_thresh': 0.3, 'sl_mult': 1.5, 'tp_mult': 3.0},
        {'rsi_entry': 55, 'body_thresh': 0.5, 'sl_mult': 1.5, 'tp_mult': 4.0},
        {'rsi_entry': 55, 'body_thresh': 0.5, 'sl_mult': 2.0, 'tp_mult': 5.0},
        {'rsi_entry': 60, 'body_thresh': 0.5, 'sl_mult': 1.5, 'tp_mult': 4.0},
    ]

    for v in variants_4:
        result = strategy_4_rsi_momentum(df, **v)
        result = analyze_results(result)
        all_results.append(result)
        s = result['stats']
        print(f"RSI {v['rsi_entry']}, Body {v['body_thresh']}, SL {v['sl_mult']}x, TP {v['tp_mult']}x: "
              f"{s['trades']} trades, {s['return']:+.2f}%, WR {s['win_rate']:.0f}%, R:R {s['rr']:.1f}x")

    # Strategy 5: Volume Spike Scalp
    print("\n" + "-" * 40)
    print("STRATEGY 5: VOLUME SPIKE SCALP")
    print("-" * 40)

    variants_5 = [
        {'vol_thresh': 3.0, 'sl_mult': 1.0, 'tp_mult': 2.0, 'max_bars': 10},
        {'vol_thresh': 4.0, 'sl_mult': 1.0, 'tp_mult': 2.0, 'max_bars': 15},
        {'vol_thresh': 4.0, 'sl_mult': 1.5, 'tp_mult': 3.0, 'max_bars': 15},
        {'vol_thresh': 5.0, 'sl_mult': 1.0, 'tp_mult': 2.5, 'max_bars': 20},
    ]

    for v in variants_5:
        result = strategy_5_volume_spike_scalp(df, **v)
        result = analyze_results(result)
        all_results.append(result)
        s = result['stats']
        print(f"Vol {v['vol_thresh']}x, SL {v['sl_mult']}x, TP {v['tp_mult']}x, Max {v['max_bars']} bars: "
              f"{s['trades']} trades, {s['return']:+.2f}%, WR {s['win_rate']:.0f}%, R:R {s['rr']:.1f}x")

    # Summary - Top performers
    print("\n" + "=" * 80)
    print("TOP 10 STRATEGIES BY RETURN")
    print("=" * 80)

    # Sort by return
    sorted_results = sorted(all_results, key=lambda x: x['stats']['return'], reverse=True)

    print(f"\n{'Strategy':<25} {'Trades':>7} {'Return':>10} {'WinRate':>8} {'R:R':>6} {'PF':>6} {'MaxDD':>8}")
    print("-" * 80)

    for r in sorted_results[:10]:
        s = r['stats']
        print(f"{r['name']:<25} {s['trades']:>7} {s['return']:>+9.2f}% {s['win_rate']:>7.1f}% "
              f"{s['rr']:>5.1f}x {s['pf']:>5.2f} {s['dd']:>7.2f}%")

    # Save all results
    results_data = []
    for r in all_results:
        row = {'strategy': r['name'], **r['params'], **r['stats']}
        results_data.append(row)

    df_results = pd.DataFrame(results_data)
    df_results.to_csv('/workspaces/Carebiuro_windykacja/trading/results/moodeng_custom_strategies.csv', index=False)
    print(f"\nResults saved to: /workspaces/Carebiuro_windykacja/trading/results/moodeng_custom_strategies.csv")

    return sorted_results


if __name__ == "__main__":
    run_all_strategies()
