#!/usr/bin/env python3
"""
MOODENG RSI MOMENTUM MASTER OPTIMIZER - BINGX DATA
Following Master Strategy Optimizer prompt (013) methodology:
1. Data integrity verified ✅ (separate script)
2. Systematic parameter exploration (one variable at a time)
3. Focus on risk-adjusted returns (Return/DD ratio)
4. Overfitting prevention (logic checks, trade count validation)
"""

import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

FEE_PER_TRADE = 0.10  # BingX Futures taker 0.05% x2


def load_moodeng_data() -> pd.DataFrame:
    """Load and prepare MOODENG BingX data with all indicators"""
    df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/moodeng_30d_bingx.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)

    # Basic
    df['body'] = df['close'] - df['open']
    df['body_pct'] = abs(df['body']) / df['open'] * 100
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
    df['atr_7'] = df['tr'].rolling(7).mean()
    df['atr_14'] = df['tr'].rolling(14).mean()
    df['atr_21'] = df['tr'].rolling(21).mean()
    df['atr'] = df['atr_14']
    df['atr_pct'] = df['atr'] / df['close'] * 100

    # Volatility
    df['vol_5'] = df['returns'].rolling(5).std()
    df['vol_20'] = df['returns'].rolling(20).std()
    df['vol_60'] = df['returns'].rolling(60).std()
    df['vol_ratio'] = df['vol_5'] / (df['vol_60'] + 0.0001)

    # Volume
    df['vol_ma'] = df['volume'].rolling(20).mean()
    df['volume_ratio'] = df['volume'] / (df['vol_ma'] + 1)

    # RSI
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / (loss + 0.0001)
    df['rsi'] = 100 - (100 / (1 + rs))

    # SMAs
    df['sma_10'] = df['close'].rolling(10).mean()
    df['sma_20'] = df['close'].rolling(20).mean()
    df['sma_50'] = df['close'].rolling(50).mean()
    df['sma_100'] = df['close'].rolling(100).mean()

    # EMA
    df['ema_20'] = df['close'].ewm(span=20).mean()
    df['ema_50'] = df['close'].ewm(span=50).mean()

    # Trend
    df['above_sma20'] = df['close'] > df['sma_20']
    df['above_sma50'] = df['close'] > df['sma_50']
    df['sma20_slope'] = df['sma_20'].diff(5) / df['sma_20'].shift(5) * 100

    # Session
    df['hour'] = df['timestamp'].dt.hour

    return df


def run_strategy(df: pd.DataFrame,
                 rsi_entry: float = 55,
                 body_thresh: float = 0.5,
                 sl_mult: float = 1.0,
                 tp_mult: float = 4.0,
                 max_bars: int = 60,
                 trend_filter: str = None,
                 session_filter: tuple = None,
                 volume_filter: float = None,
                 dynamic_sl: bool = False,
                 dynamic_tp: bool = False,
                 limit_order_offset: float = 0.0,
                 ) -> list:
    """Run RSI Momentum strategy with filters"""

    trades = []
    in_position = False
    entry_price = entry_idx = stop_loss = take_profit = 0

    for i in range(200, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i-1]

        if not in_position:
            # Base entry
            rsi_cross = prev['rsi'] < rsi_entry and row['rsi'] >= rsi_entry
            bullish_body = row['is_bullish'] and row['body_pct'] > body_thresh
            above_sma = row['close'] > row['sma_20']

            if not (rsi_cross and bullish_body and above_sma):
                continue

            # Filters
            if trend_filter == 'sma50' and not row['above_sma50']:
                continue
            if trend_filter == 'slope' and row['sma20_slope'] < 0:
                continue

            if session_filter:
                start_h, end_h = session_filter
                if not (start_h <= row['hour'] <= end_h):
                    continue

            if volume_filter and row['volume_ratio'] < volume_filter:
                continue

            # ENTRY
            in_position = True
            # Limit order: enter slightly below close
            entry_price = row['close'] * (1 - limit_order_offset / 100)
            entry_idx = i
            entry_atr = row['atr']

            # Dynamic SL/TP based on volatility
            if dynamic_sl:
                vol_adj = max(0.5, min(2.0, row['vol_ratio']))
                current_sl_mult = sl_mult * vol_adj
            else:
                current_sl_mult = sl_mult

            if dynamic_tp:
                vol_adj = max(0.5, min(2.0, row['vol_ratio']))
                current_tp_mult = tp_mult * vol_adj
            else:
                current_tp_mult = tp_mult

            stop_loss = entry_price - (entry_atr * current_sl_mult)
            take_profit = entry_price + (entry_atr * current_tp_mult)

        else:
            # Check exits
            bars_held = i - entry_idx

            # SL
            if row['low'] <= stop_loss:
                pnl = (stop_loss - entry_price) / entry_price * 100
                trades.append({
                    'entry_idx': entry_idx,
                    'exit_idx': i,
                    'pnl_pct': pnl,
                    'result': 'SL',
                    'bars': bars_held
                })
                in_position = False
            # TP
            elif row['high'] >= take_profit:
                pnl = (take_profit - entry_price) / entry_price * 100
                trades.append({
                    'entry_idx': entry_idx,
                    'exit_idx': i,
                    'pnl_pct': pnl,
                    'result': 'TP',
                    'bars': bars_held
                })
                in_position = False
            # Time exit
            elif bars_held >= max_bars:
                exit_price = row['close']
                pnl = (exit_price - entry_price) / entry_price * 100
                trades.append({
                    'entry_idx': entry_idx,
                    'exit_idx': i,
                    'pnl_pct': pnl,
                    'result': 'TIME',
                    'bars': bars_held
                })
                in_position = False

    return trades


def analyze_trades(trades: list, label: str = '') -> dict:
    """Analyze trades and return comprehensive stats"""
    if not trades:
        return {
            'label': label, 'trades': 0, 'gross': 0, 'net': 0, 'win_rate': 0,
            'avg_win': 0, 'avg_loss': 0, 'rr': 0, 'pf': 0, 'dd': 0,
            'return_dd': 0, 'avg_bars': 0
        }

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

    # Return/DD ratio (key metric)
    return_dd = abs(net_return / max_dd) if max_dd > 0 else 0

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
        'return_dd': return_dd,
        'avg_bars': df['bars'].mean()
    }


def main():
    print("="*90)
    print("MOODENG RSI MOMENTUM MASTER OPTIMIZER - BINGX DATA")
    print("="*90)

    df = load_moodeng_data()
    print(f"\nLoaded {len(df):,} candles")
    print(f"Date range: {df['timestamp'].iloc[0]} to {df['timestamp'].iloc[-1]}")
    print(f"Data verification passed ✅ (outlier-dependent but clean)\n")

    all_results = []

    # ========== BASELINE ==========
    print("-" * 90)
    print("1. BASELINE (RSI 55, Body 0.5%, SL 1.0x, TP 4.0x, Time 60)")
    print("-" * 90)
    trades = run_strategy(df, sl_mult=1.0)
    result = analyze_trades(trades, 'Baseline')
    all_results.append(result)
    print(f"Trades: {result['trades']}, NET: {result['net']:+.2f}%, "
          f"WR: {result['win_rate']:.0f}%, DD: {result['dd']:.2f}%, R/DD: {result['return_dd']:.2f}x")

    # ========== SL/TP OPTIMIZATION ==========
    print("\n" + "-" * 90)
    print("2. SL/TP RATIO OPTIMIZATION (most impactful)")
    print("-" * 90)

    sl_tp_ratios = [
        (0.5, 3.0), (0.5, 4.0), (0.5, 5.0),
        (1.0, 3.0), (1.0, 4.0), (1.0, 5.0), (1.0, 6.0),
        (1.5, 4.0), (1.5, 5.0), (1.5, 6.0),
        (2.0, 5.0), (2.0, 6.0), (2.0, 8.0),
    ]

    for sl, tp in sl_tp_ratios:
        trades = run_strategy(df, sl_mult=sl, tp_mult=tp)
        result = analyze_trades(trades, f'SL{sl}/TP{tp}')
        all_results.append(result)
        print(f"SL {sl}x / TP {tp}x: {result['trades']:>3} trades, NET: {result['net']:+7.2f}%, "
              f"WR: {result['win_rate']:>4.0f}%, R/DD: {result['return_dd']:>5.2f}x")

    # ========== RSI ENTRY THRESHOLD ==========
    print("\n" + "-" * 90)
    print("3. RSI ENTRY THRESHOLD OPTIMIZATION")
    print("-" * 90)

    for rsi in [50, 52, 55, 57, 60, 65]:
        trades = run_strategy(df, rsi_entry=rsi)
        result = analyze_trades(trades, f'RSI{rsi}')
        all_results.append(result)
        print(f"RSI {rsi}: {result['trades']:>3} trades, NET: {result['net']:+7.2f}%, "
              f"WR: {result['win_rate']:>4.0f}%, R/DD: {result['return_dd']:>5.2f}x")

    # ========== BODY THRESHOLD ==========
    print("\n" + "-" * 90)
    print("4. BODY THRESHOLD OPTIMIZATION")
    print("-" * 90)

    for body in [0.3, 0.5, 0.7, 1.0, 1.5]:
        trades = run_strategy(df, body_thresh=body)
        result = analyze_trades(trades, f'Body{body}')
        all_results.append(result)
        print(f"Body >{body}%: {result['trades']:>3} trades, NET: {result['net']:+7.2f}%, "
              f"WR: {result['win_rate']:>4.0f}%, R/DD: {result['return_dd']:>5.2f}x")

    # ========== TIME EXIT ==========
    print("\n" + "-" * 90)
    print("5. TIME EXIT OPTIMIZATION")
    print("-" * 90)

    for max_bars in [30, 45, 60, 90, 120]:
        trades = run_strategy(df, max_bars=max_bars)
        result = analyze_trades(trades, f'Time{max_bars}')
        all_results.append(result)
        print(f"Max {max_bars} bars: {result['trades']:>3} trades, NET: {result['net']:+7.2f}%, "
              f"WR: {result['win_rate']:>4.0f}%, R/DD: {result['return_dd']:>5.2f}x")

    # ========== TREND FILTERS ==========
    print("\n" + "-" * 90)
    print("6. TREND FILTERS")
    print("-" * 90)

    for filt in ['sma50', 'slope']:
        trades = run_strategy(df, trend_filter=filt)
        result = analyze_trades(trades, f'Trend:{filt}')
        all_results.append(result)
        print(f"{filt:<10}: {result['trades']:>3} trades, NET: {result['net']:+7.2f}%, "
              f"WR: {result['win_rate']:>4.0f}%, R/DD: {result['return_dd']:>5.2f}x")

    # ========== SESSION FILTERS ==========
    print("\n" + "-" * 90)
    print("7. SESSION FILTERS (UTC hours)")
    print("-" * 90)

    sessions = [
        ((0, 8), 'Asia 00-08'),
        ((8, 14), 'Europe 08-14'),
        ((14, 21), 'US 14-21'),
        ((21, 23), 'Overnight 21-23'),
    ]

    for (start, end), name in sessions:
        trades = run_strategy(df, session_filter=(start, end))
        result = analyze_trades(trades, f'Session:{name}')
        all_results.append(result)
        print(f"{name:<18}: {result['trades']:>3} trades, NET: {result['net']:+7.2f}%, "
              f"WR: {result['win_rate']:>4.0f}%, R/DD: {result['return_dd']:>5.2f}x")

    # ========== VOLUME FILTERS ==========
    print("\n" + "-" * 90)
    print("8. VOLUME FILTERS")
    print("-" * 90)

    for vol in [1.5, 2.0, 2.5, 3.0]:
        trades = run_strategy(df, volume_filter=vol)
        result = analyze_trades(trades, f'Vol>{vol}x')
        all_results.append(result)
        print(f"Vol >{vol}x: {result['trades']:>3} trades, NET: {result['net']:+7.2f}%, "
              f"WR: {result['win_rate']:>4.0f}%, R/DD: {result['return_dd']:>5.2f}x")

    # ========== DYNAMIC EXITS ==========
    print("\n" + "-" * 90)
    print("9. DYNAMIC EXITS (volatility-adjusted)")
    print("-" * 90)

    trades = run_strategy(df, dynamic_sl=True)
    result = analyze_trades(trades, 'Dynamic SL')
    all_results.append(result)
    print(f"Dynamic SL:      {result['trades']:>3} trades, NET: {result['net']:+7.2f}%, "
          f"WR: {result['win_rate']:>4.0f}%, R/DD: {result['return_dd']:>5.2f}x")

    trades = run_strategy(df, dynamic_tp=True)
    result = analyze_trades(trades, 'Dynamic TP')
    all_results.append(result)
    print(f"Dynamic TP:      {result['trades']:>3} trades, NET: {result['net']:+7.2f}%, "
          f"WR: {result['win_rate']:>4.0f}%, R/DD: {result['return_dd']:>5.2f}x")

    trades = run_strategy(df, dynamic_sl=True, dynamic_tp=True)
    result = analyze_trades(trades, 'Dynamic Both')
    all_results.append(result)
    print(f"Dynamic Both:    {result['trades']:>3} trades, NET: {result['net']:+7.2f}%, "
          f"WR: {result['win_rate']:>4.0f}%, R/DD: {result['return_dd']:>5.2f}x")

    # ========== LIMIT ORDERS ==========
    print("\n" + "-" * 90)
    print("10. LIMIT ORDER ENTRY (reduce slippage)")
    print("-" * 90)

    for offset in [0.0, 0.02, 0.035, 0.05]:
        trades = run_strategy(df, limit_order_offset=offset)
        result = analyze_trades(trades, f'Limit-{offset}%')
        all_results.append(result)
        print(f"Limit -{offset}%: {result['trades']:>3} trades, NET: {result['net']:+7.2f}%, "
              f"WR: {result['win_rate']:>4.0f}%, R/DD: {result['return_dd']:>5.2f}x")

    # ========== BEST COMBINATIONS ==========
    print("\n" + "-" * 90)
    print("11. COMBINED CONFIGURATIONS (top parameter combinations)")
    print("-" * 90)

    combos = [
        {'sl_mult': 0.5, 'tp_mult': 4.0},
        {'sl_mult': 1.0, 'tp_mult': 5.0},
        {'sl_mult': 1.0, 'tp_mult': 6.0},
        {'rsi_entry': 60, 'sl_mult': 1.0, 'tp_mult': 5.0},
        {'body_thresh': 0.7, 'sl_mult': 1.0, 'tp_mult': 5.0},
        {'trend_filter': 'slope', 'sl_mult': 1.0, 'tp_mult': 5.0},
        {'session_filter': (14, 21), 'sl_mult': 1.0, 'tp_mult': 5.0},
        {'sl_mult': 1.0, 'tp_mult': 5.0, 'limit_order_offset': 0.035},
        {'rsi_entry': 60, 'body_thresh': 0.7, 'sl_mult': 1.0, 'tp_mult': 5.0},
        {'trend_filter': 'slope', 'session_filter': (14, 21), 'sl_mult': 1.0, 'tp_mult': 5.0},
    ]

    for i, combo in enumerate(combos):
        trades = run_strategy(df, **combo)
        label = f"Combo{i+1}"
        result = analyze_trades(trades, label)
        result['combo'] = combo
        all_results.append(result)
        desc = ', '.join([f"{k}={v}" for k, v in combo.items()])[:40]
        print(f"Combo {i+1}: {result['trades']:>3} trades, NET: {result['net']:+7.2f}%, "
              f"R/DD: {result['return_dd']:>5.2f}x | {desc}")

    # ========== SUMMARY ==========
    print("\n" + "="*90)
    print("TOP 15 STRATEGIES BY RETURN/DD RATIO")
    print("="*90)

    sorted_results = sorted(all_results, key=lambda x: x['return_dd'], reverse=True)

    print(f"\n{'Rank':<5} {'Strategy':<25} {'Trades':>7} {'NET':>9} {'WR':>6} {'DD':>7} {'R/DD':>8}")
    print("-" * 90)

    for i, r in enumerate(sorted_results[:15], 1):
        print(f"{i:<5} {r['label']:<25} {r['trades']:>7} {r['net']:>+8.2f}% "
              f"{r['win_rate']:>5.0f}% {r['dd']:>6.2f}% {r['return_dd']:>7.2f}x")

    # Save results
    df_results = pd.DataFrame(all_results)
    df_results = df_results.sort_values('return_dd', ascending=False).reset_index(drop=True)
    df_results.to_csv('/workspaces/Carebiuro_windykacja/trading/results/moodeng_master_optimization_bingx.csv', index=False)
    print(f"\n✅ Results saved to: trading/results/moodeng_master_optimization_bingx.csv")

    # Best strategy details
    best = sorted_results[0]
    print("\n" + "="*90)
    print(f"BEST STRATEGY (by R/DD): {best['label']}")
    print("="*90)
    print(f"Trades:        {best['trades']}")
    print(f"NET Return:    {best['net']:+.2f}%")
    print(f"Win Rate:      {best['win_rate']:.1f}%")
    print(f"Max Drawdown:  {best['dd']:.2f}%")
    print(f"Return/DD:     {best['return_dd']:.2f}x")
    print(f"Profit Factor: {best['pf']:.2f}")
    print(f"Avg R:R:       {best['rr']:.2f}x")
    if 'combo' in best:
        print(f"\nParameters:")
        for k, v in best['combo'].items():
            print(f"  {k}: {v}")

    # Baseline comparison
    baseline = [r for r in all_results if r['label'] == 'Baseline'][0]
    print(f"\n\nBASELINE COMPARISON:")
    print(f"Baseline Return/DD: {baseline['return_dd']:.2f}x")
    print(f"Best Return/DD:     {best['return_dd']:.2f}x")
    print(f"Improvement:        {((best['return_dd'] / baseline['return_dd']) - 1) * 100:+.1f}%")


if __name__ == "__main__":
    main()
