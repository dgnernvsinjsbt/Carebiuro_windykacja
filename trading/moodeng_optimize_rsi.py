#!/usr/bin/env python3
"""
MOODENG RSI Momentum Strategy Optimization
Base strategy: RSI 55 crossover, Body 0.5%, SL 1.5x ATR, TP 4.0x ATR
Goal: Find filters and dynamic adjustments to improve NET returns
"""

import pandas as pd
import numpy as np
from itertools import product
import warnings
warnings.filterwarnings('ignore')

# Fee assumption: BingX Futures taker = 0.05% per side = 0.10% round trip
FEE_PER_TRADE = 0.10


def load_moodeng_data() -> pd.DataFrame:
    """Load and prepare MOODENG data with all indicators"""
    df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/moodeng_usdt_1m_lbank.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)

    # Basic
    df['body'] = df['close'] - df['open']
    df['body_pct'] = abs(df['body']) / df['open'] * 100
    df['is_bullish'] = df['close'] > df['open']
    df['returns'] = df['close'].pct_change() * 100

    # ATR (multiple periods)
    df['tr'] = np.maximum(
        df['high'] - df['low'],
        np.maximum(
            abs(df['high'] - df['close'].shift(1)),
            abs(df['low'] - df['close'].shift(1))
        )
    )
    df['atr_7'] = df['tr'].rolling(7).mean()
    df['atr_14'] = df['tr'].rolling(14).mean()
    df['atr_21'] = df['tr'].rolling(21).mean()
    df['atr'] = df['atr_14']  # default
    df['atr_pct'] = df['atr'] / df['close'] * 100

    # Volatility (rolling std of returns)
    df['vol_5'] = df['returns'].rolling(5).std()
    df['vol_20'] = df['returns'].rolling(20).std()
    df['vol_60'] = df['returns'].rolling(60).std()
    df['vol_ratio'] = df['vol_5'] / df['vol_60']  # short-term vs long-term vol

    # Volume
    df['vol_ma'] = df['volume'].rolling(20).mean()
    df['volume_ratio'] = df['volume'] / df['vol_ma']

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
    df['sma_100'] = df['close'].rolling(100).mean()
    df['sma_200'] = df['close'].rolling(200).mean()

    # EMA
    df['ema_10'] = df['close'].ewm(span=10).mean()
    df['ema_20'] = df['close'].ewm(span=20).mean()
    df['ema_50'] = df['close'].ewm(span=50).mean()

    # Trend strength
    df['above_sma20'] = df['close'] > df['sma_20']
    df['above_sma50'] = df['close'] > df['sma_50']
    df['above_ema20'] = df['close'] > df['ema_20']
    df['sma20_slope'] = df['sma_20'].diff(5) / df['sma_20'].shift(5) * 100

    # Bollinger Bands
    df['bb_mid'] = df['close'].rolling(20).mean()
    df['bb_std'] = df['close'].rolling(20).std()
    df['bb_upper'] = df['bb_mid'] + 2 * df['bb_std']
    df['bb_lower'] = df['bb_mid'] - 2 * df['bb_std']
    df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])

    # Hour and day
    df['hour'] = df['timestamp'].dt.hour
    df['dayofweek'] = df['timestamp'].dt.dayofweek

    # Recent momentum
    df['mom_5'] = df['close'].pct_change(5) * 100
    df['mom_10'] = df['close'].pct_change(10) * 100

    # Consecutive candles
    df['consec_green'] = df['is_bullish'].groupby((~df['is_bullish']).cumsum()).cumcount()
    df['consec_red'] = (~df['is_bullish']).groupby(df['is_bullish'].cumsum()).cumcount()

    return df


def run_strategy(df: pd.DataFrame,
                 # Entry params
                 rsi_entry: float = 55,
                 body_thresh: float = 0.5,
                 volume_filter: float = None,
                 # Exit params
                 sl_mult: float = 1.5,
                 tp_mult: float = 4.0,
                 dynamic_sl: bool = False,
                 dynamic_tp: bool = False,
                 trailing_sl: bool = False,
                 max_bars: int = 60,
                 # Filters
                 trend_filter: str = None,  # 'sma20', 'sma50', 'ema20', 'slope'
                 vol_filter: str = None,     # 'high', 'low', 'expanding'
                 session_filter: tuple = None,  # (start_hour, end_hour)
                 bb_filter: str = None,      # 'lower_half', 'near_lower'
                 momentum_filter: str = None, # 'positive', 'strong'
                 weekday_filter: list = None, # [0,1,2,3,4] = Mon-Fri
                 # ATR period
                 atr_period: int = 14,
                 ) -> dict:
    """
    Run RSI Momentum strategy with various filters and dynamic exits
    """

    trades = []
    in_position = False
    entry_price = entry_idx = stop_loss = take_profit = entry_atr = 0
    highest_since_entry = 0

    # Select ATR column
    atr_col = f'atr_{atr_period}' if f'atr_{atr_period}' in df.columns else 'atr'

    for i in range(200, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i-1]

        if not in_position:
            # Base entry: RSI crossover + bullish candle
            rsi_cross = prev['rsi'] < rsi_entry and row['rsi'] >= rsi_entry
            bullish_body = row['is_bullish'] and row['body_pct'] > body_thresh

            if not (rsi_cross and bullish_body):
                continue

            # Apply filters
            entry_ok = True

            # Volume filter
            if volume_filter and row['volume_ratio'] < volume_filter:
                entry_ok = False

            # Trend filter
            if trend_filter == 'sma20' and not row['above_sma20']:
                entry_ok = False
            elif trend_filter == 'sma50' and not row['above_sma50']:
                entry_ok = False
            elif trend_filter == 'ema20' and not row['above_ema20']:
                entry_ok = False
            elif trend_filter == 'slope' and row['sma20_slope'] < 0:
                entry_ok = False

            # Volatility filter
            if vol_filter == 'high' and row['vol_ratio'] < 1.2:
                entry_ok = False
            elif vol_filter == 'low' and row['vol_ratio'] > 0.8:
                entry_ok = False
            elif vol_filter == 'expanding' and row['vol_5'] < row['vol_20']:
                entry_ok = False

            # Session filter
            if session_filter:
                start_h, end_h = session_filter
                if not (start_h <= row['hour'] <= end_h):
                    entry_ok = False

            # Bollinger filter
            if bb_filter == 'lower_half' and row['bb_position'] > 0.5:
                entry_ok = False
            elif bb_filter == 'near_lower' and row['bb_position'] > 0.3:
                entry_ok = False

            # Momentum filter
            if momentum_filter == 'positive' and row['mom_5'] < 0:
                entry_ok = False
            elif momentum_filter == 'strong' and row['mom_5'] < 0.5:
                entry_ok = False

            # Weekday filter
            if weekday_filter and row['dayofweek'] not in weekday_filter:
                entry_ok = False

            if not entry_ok:
                continue

            # ENTRY
            in_position = True
            entry_price = row['close']
            entry_idx = i
            entry_atr = row[atr_col]
            highest_since_entry = entry_price

            # Calculate SL/TP
            if dynamic_sl:
                # Tighter SL in low vol, wider in high vol
                vol_adj = max(0.5, min(2.0, row['vol_ratio']))
                current_sl_mult = sl_mult * vol_adj
            else:
                current_sl_mult = sl_mult

            if dynamic_tp:
                # Larger TP in high vol, smaller in low vol
                vol_adj = max(0.5, min(2.0, row['vol_ratio']))
                current_tp_mult = tp_mult * vol_adj
            else:
                current_tp_mult = tp_mult

            stop_loss = entry_price - (entry_atr * current_sl_mult)
            take_profit = entry_price + (entry_atr * current_tp_mult)

        else:
            # In position - check exits
            bars_held = i - entry_idx
            highest_since_entry = max(highest_since_entry, row['high'])

            # Trailing stop
            if trailing_sl:
                trail_stop = highest_since_entry - (entry_atr * sl_mult)
                stop_loss = max(stop_loss, trail_stop)

            # Check SL
            if row['low'] <= stop_loss:
                pnl = (stop_loss - entry_price) / entry_price * 100
                trades.append({
                    'entry_idx': entry_idx, 'exit_idx': i,
                    'entry_price': entry_price, 'exit_price': stop_loss,
                    'pnl_pct': pnl, 'result': 'SL', 'bars': bars_held,
                    'hour': df.iloc[entry_idx]['hour']
                })
                in_position = False
                continue

            # Check TP
            if row['high'] >= take_profit:
                pnl = (take_profit - entry_price) / entry_price * 100
                trades.append({
                    'entry_idx': entry_idx, 'exit_idx': i,
                    'entry_price': entry_price, 'exit_price': take_profit,
                    'pnl_pct': pnl, 'result': 'TP', 'bars': bars_held,
                    'hour': df.iloc[entry_idx]['hour']
                })
                in_position = False
                continue

            # Time exit
            if bars_held >= max_bars:
                exit_price = row['close']
                pnl = (exit_price - entry_price) / entry_price * 100
                trades.append({
                    'entry_idx': entry_idx, 'exit_idx': i,
                    'entry_price': entry_price, 'exit_price': exit_price,
                    'pnl_pct': pnl, 'result': 'TIME', 'bars': bars_held,
                    'hour': df.iloc[entry_idx]['hour']
                })
                in_position = False

    return trades


def analyze_trades(trades: list, label: str = '') -> dict:
    """Analyze trades and return stats"""
    if not trades:
        return {'label': label, 'trades': 0, 'gross': 0, 'net': 0, 'win_rate': 0,
                'avg_win': 0, 'avg_loss': 0, 'rr': 0, 'pf': 0, 'dd': 0, 'avg_bars': 0}

    df = pd.DataFrame(trades)

    winners = df[df['pnl_pct'] > 0]
    losers = df[df['pnl_pct'] <= 0]

    total = len(df)
    win_rate = len(winners) / total * 100

    avg_win = winners['pnl_pct'].mean() if len(winners) > 0 else 0
    avg_loss = abs(losers['pnl_pct'].mean()) if len(losers) > 0 else 0

    gross_profit = winners['pnl_pct'].sum() if len(winners) > 0 else 0
    gross_loss = abs(losers['pnl_pct'].sum()) if len(losers) > 0 else 0

    pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')
    rr = avg_win / avg_loss if avg_loss > 0 else float('inf')

    # Equity curve
    equity = [100]
    for pnl in df['pnl_pct']:
        equity.append(equity[-1] * (1 + pnl/100))

    peak = equity[0]
    max_dd = 0
    for e in equity:
        if e > peak:
            peak = e
        dd = (peak - e) / peak * 100
        max_dd = max(max_dd, dd)

    gross_return = equity[-1] - 100
    fee_cost = total * FEE_PER_TRADE
    net_return = gross_return - fee_cost

    return {
        'label': label,
        'trades': total,
        'gross': gross_return,
        'fees': fee_cost,
        'net': net_return,
        'win_rate': win_rate,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'rr': rr,
        'pf': pf,
        'dd': max_dd,
        'avg_bars': df['bars'].mean()
    }


def main():
    print("=" * 90)
    print("MOODENG RSI MOMENTUM OPTIMIZATION")
    print("=" * 90)

    df = load_moodeng_data()
    print(f"Loaded {len(df):,} candles\n")

    all_results = []

    # 1. BASELINE
    print("-" * 50)
    print("1. BASELINE (RSI 55, Body 0.5, SL 1.5x, TP 4.0x)")
    print("-" * 50)
    trades = run_strategy(df)
    result = analyze_trades(trades, 'Baseline')
    all_results.append(result)
    print(f"Trades: {result['trades']}, Gross: {result['gross']:+.2f}%, "
          f"NET: {result['net']:+.2f}%, WR: {result['win_rate']:.0f}%, DD: {result['dd']:.2f}%")

    # 2. TREND FILTERS
    print("\n" + "-" * 50)
    print("2. TREND FILTERS")
    print("-" * 50)
    for filt in ['sma20', 'sma50', 'ema20', 'slope']:
        trades = run_strategy(df, trend_filter=filt)
        result = analyze_trades(trades, f'Trend:{filt}')
        all_results.append(result)
        print(f"{filt:<10}: {result['trades']:>4} trades, NET: {result['net']:+7.2f}%, "
              f"WR: {result['win_rate']:>4.0f}%, DD: {result['dd']:>5.2f}%")

    # 3. VOLATILITY FILTERS
    print("\n" + "-" * 50)
    print("3. VOLATILITY FILTERS")
    print("-" * 50)
    for filt in ['high', 'low', 'expanding']:
        trades = run_strategy(df, vol_filter=filt)
        result = analyze_trades(trades, f'Vol:{filt}')
        all_results.append(result)
        print(f"{filt:<10}: {result['trades']:>4} trades, NET: {result['net']:+7.2f}%, "
              f"WR: {result['win_rate']:>4.0f}%, DD: {result['dd']:>5.2f}%")

    # 4. SESSION FILTERS
    print("\n" + "-" * 50)
    print("4. SESSION FILTERS (UTC hours)")
    print("-" * 50)
    sessions = [
        ((0, 8), 'Asia 00-08'),
        ((8, 14), 'Europe 08-14'),
        ((14, 21), 'US 14-21'),
        ((21, 23), 'Late 21-23'),
        ((12, 20), 'Prime 12-20'),
        ((14, 18), 'US Open 14-18'),
    ]
    for (start, end), name in sessions:
        trades = run_strategy(df, session_filter=(start, end))
        result = analyze_trades(trades, f'Session:{name}')
        all_results.append(result)
        print(f"{name:<15}: {result['trades']:>4} trades, NET: {result['net']:+7.2f}%, "
              f"WR: {result['win_rate']:>4.0f}%, DD: {result['dd']:>5.2f}%")

    # 5. BOLLINGER FILTERS
    print("\n" + "-" * 50)
    print("5. BOLLINGER BAND FILTERS")
    print("-" * 50)
    for filt in ['lower_half', 'near_lower']:
        trades = run_strategy(df, bb_filter=filt)
        result = analyze_trades(trades, f'BB:{filt}')
        all_results.append(result)
        print(f"{filt:<12}: {result['trades']:>4} trades, NET: {result['net']:+7.2f}%, "
              f"WR: {result['win_rate']:>4.0f}%, DD: {result['dd']:>5.2f}%")

    # 6. VOLUME FILTER
    print("\n" + "-" * 50)
    print("6. VOLUME FILTERS")
    print("-" * 50)
    for vol in [1.5, 2.0, 2.5, 3.0]:
        trades = run_strategy(df, volume_filter=vol)
        result = analyze_trades(trades, f'MinVol:{vol}x')
        all_results.append(result)
        print(f"Vol>{vol}x: {result['trades']:>4} trades, NET: {result['net']:+7.2f}%, "
              f"WR: {result['win_rate']:>4.0f}%, DD: {result['dd']:>5.2f}%")

    # 7. DYNAMIC SL/TP
    print("\n" + "-" * 50)
    print("7. DYNAMIC SL/TP (volatility-adjusted)")
    print("-" * 50)

    trades = run_strategy(df, dynamic_sl=True)
    result = analyze_trades(trades, 'Dynamic SL')
    all_results.append(result)
    print(f"Dynamic SL:     {result['trades']:>4} trades, NET: {result['net']:+7.2f}%, "
          f"WR: {result['win_rate']:>4.0f}%, DD: {result['dd']:>5.2f}%")

    trades = run_strategy(df, dynamic_tp=True)
    result = analyze_trades(trades, 'Dynamic TP')
    all_results.append(result)
    print(f"Dynamic TP:     {result['trades']:>4} trades, NET: {result['net']:+7.2f}%, "
          f"WR: {result['win_rate']:>4.0f}%, DD: {result['dd']:>5.2f}%")

    trades = run_strategy(df, dynamic_sl=True, dynamic_tp=True)
    result = analyze_trades(trades, 'Dynamic Both')
    all_results.append(result)
    print(f"Dynamic Both:   {result['trades']:>4} trades, NET: {result['net']:+7.2f}%, "
          f"WR: {result['win_rate']:>4.0f}%, DD: {result['dd']:>5.2f}%")

    trades = run_strategy(df, trailing_sl=True)
    result = analyze_trades(trades, 'Trailing SL')
    all_results.append(result)
    print(f"Trailing SL:    {result['trades']:>4} trades, NET: {result['net']:+7.2f}%, "
          f"WR: {result['win_rate']:>4.0f}%, DD: {result['dd']:>5.2f}%")

    # 8. DIFFERENT SL/TP RATIOS
    print("\n" + "-" * 50)
    print("8. SL/TP RATIO OPTIMIZATION")
    print("-" * 50)
    ratios = [
        (1.0, 3.0), (1.0, 4.0), (1.0, 5.0),
        (1.5, 4.0), (1.5, 5.0), (1.5, 6.0),
        (2.0, 5.0), (2.0, 6.0), (2.0, 8.0),
    ]
    for sl, tp in ratios:
        trades = run_strategy(df, sl_mult=sl, tp_mult=tp)
        result = analyze_trades(trades, f'SL{sl}/TP{tp}')
        all_results.append(result)
        print(f"SL {sl}x / TP {tp}x: {result['trades']:>4} trades, NET: {result['net']:+7.2f}%, "
              f"WR: {result['win_rate']:>4.0f}%, R:R: {result['rr']:.1f}x, DD: {result['dd']:>5.2f}%")

    # 9. ATR PERIOD
    print("\n" + "-" * 50)
    print("9. ATR PERIOD OPTIMIZATION")
    print("-" * 50)
    for period in [7, 14, 21]:
        trades = run_strategy(df, atr_period=period)
        result = analyze_trades(trades, f'ATR{period}')
        all_results.append(result)
        print(f"ATR {period}:  {result['trades']:>4} trades, NET: {result['net']:+7.2f}%, "
              f"WR: {result['win_rate']:>4.0f}%, DD: {result['dd']:>5.2f}%")

    # 10. COMBINED FILTERS (best combinations)
    print("\n" + "-" * 50)
    print("10. COMBINED FILTERS (testing best combinations)")
    print("-" * 50)

    combos = [
        {'trend_filter': 'ema20', 'session_filter': (14, 21)},
        {'trend_filter': 'slope', 'vol_filter': 'high'},
        {'session_filter': (14, 21), 'volume_filter': 2.0},
        {'trend_filter': 'ema20', 'dynamic_sl': True, 'dynamic_tp': True},
        {'trend_filter': 'slope', 'session_filter': (14, 21), 'volume_filter': 1.5},
        {'vol_filter': 'expanding', 'trailing_sl': True},
        {'trend_filter': 'ema20', 'bb_filter': 'lower_half'},
        {'session_filter': (14, 21), 'trailing_sl': True, 'sl_mult': 1.0, 'tp_mult': 5.0},
        {'trend_filter': 'slope', 'vol_filter': 'expanding', 'session_filter': (12, 20)},
        {'trend_filter': 'ema20', 'volume_filter': 1.5, 'sl_mult': 1.0, 'tp_mult': 5.0},
    ]

    for i, combo in enumerate(combos):
        trades = run_strategy(df, **combo)
        label = '+'.join([f"{k[:3]}:{str(v)[:6]}" for k,v in combo.items()])[:30]
        result = analyze_trades(trades, f'Combo{i+1}')
        result['combo'] = combo
        all_results.append(result)
        print(f"Combo {i+1}: {result['trades']:>4} trades, NET: {result['net']:+7.2f}%, "
              f"WR: {result['win_rate']:>4.0f}%, DD: {result['dd']:>5.2f}%  | {label}")

    # SUMMARY - Top 15 by NET return
    print("\n" + "=" * 90)
    print("TOP 15 STRATEGIES BY NET RETURN")
    print("=" * 90)

    sorted_results = sorted(all_results, key=lambda x: x['net'], reverse=True)

    print(f"\n{'Rank':<5} {'Strategy':<25} {'Trades':>7} {'Gross':>9} {'Fees':>7} {'NET':>9} {'WR':>6} {'R:R':>6} {'DD':>7}")
    print("-" * 90)

    for i, r in enumerate(sorted_results[:15], 1):
        print(f"{i:<5} {r['label']:<25} {r['trades']:>7} {r['gross']:>+8.2f}% {r['fees']:>6.2f}% "
              f"{r['net']:>+8.2f}% {r['win_rate']:>5.0f}% {r['rr']:>5.1f}x {r['dd']:>6.2f}%")

    # Save results
    df_results = pd.DataFrame(all_results)
    df_results.to_csv('/workspaces/Carebiuro_windykacja/trading/results/moodeng_optimization.csv', index=False)
    print(f"\nResults saved to: /workspaces/Carebiuro_windykacja/trading/results/moodeng_optimization.csv")

    # Best strategy details
    best = sorted_results[0]
    print("\n" + "=" * 90)
    print(f"BEST STRATEGY: {best['label']}")
    print("=" * 90)
    print(f"Trades: {best['trades']}")
    print(f"Gross Return: {best['gross']:+.2f}%")
    print(f"Fee Cost: {best['fees']:.2f}%")
    print(f"NET Return: {best['net']:+.2f}%")
    print(f"Win Rate: {best['win_rate']:.1f}%")
    print(f"Risk:Reward: {best['rr']:.2f}x")
    print(f"Profit Factor: {best['pf']:.2f}")
    print(f"Max Drawdown: {best['dd']:.2f}%")
    print(f"Avg Bars Held: {best['avg_bars']:.1f}")
    if 'combo' in best:
        print(f"Parameters: {best['combo']}")


if __name__ == "__main__":
    main()
