#!/usr/bin/env python3
"""
Backtest FARTCOIN strategies (7.14x and 8.88x R:R) on meme coins
With 3 volatility-adjusted versions per coin
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys
import warnings
warnings.filterwarnings('ignore')

def load_data(coin: str) -> pd.DataFrame:
    """Load 1-minute data for a coin"""
    trading_dir = Path('/workspaces/Carebiuro_windykacja/trading')

    # Try different file patterns (prioritize exchange-specific files)
    patterns = [
        f"{coin.lower()}_usdt_1m_mexc.csv",
        f"{coin.lower()}_usdt_1m_gate.csv",
        f"{coin.lower()}_usdt_1m_lbank.csv",
        f"{coin.lower()}_usdt_1m_*.csv",
        f"{coin.lower()}_1m_*.csv",
    ]

    for pattern in patterns:
        files = list(trading_dir.glob(pattern))
        if files:
            df = pd.read_csv(files[0])
            if 'timestamp' not in df.columns and 'time' in df.columns:
                df['timestamp'] = df['time']
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp').reset_index(drop=True)
            return df

    raise FileNotFoundError(f"No data file found for {coin}")


def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate all required indicators"""
    df = df.copy()

    # Price changes
    df['body'] = df['close'] - df['open']
    df['body_pct'] = abs(df['body']) / df['open'] * 100
    df['is_bullish'] = df['close'] > df['open']
    df['is_bearish'] = df['close'] < df['open']

    # ATR
    df['tr'] = np.maximum(
        df['high'] - df['low'],
        np.maximum(
            abs(df['high'] - df['close'].shift(1)),
            abs(df['low'] - df['close'].shift(1))
        )
    )
    df['atr'] = df['tr'].rolling(14).mean()

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
    df['sma_20'] = df['close'].rolling(20).mean()
    df['sma_50'] = df['close'].rolling(50).mean()
    df['sma_200'] = df['close'].rolling(200).mean()

    # 5-minute RSI (approximate with 5-bar)
    delta_5 = df['close'].diff(5)
    gain_5 = delta_5.where(delta_5 > 0, 0).rolling(14).mean()
    loss_5 = (-delta_5.where(delta_5 < 0, 0)).rolling(14).mean()
    rs_5 = gain_5 / loss_5
    df['rsi_5m'] = 100 - (100 / (1 + rs_5))

    # Distance from SMA
    df['dist_from_sma50'] = (df['close'] - df['sma_50']) / df['sma_50'] * 100

    return df


def backtest_long_strategy(df: pd.DataFrame, sl_mult: float, tp_mult: float,
                           body_thresh: float, vol_thresh: float) -> dict:
    """
    Multi-Timeframe LONG Strategy (7.14x R:R base)
    - Entry: Explosive bullish candle + volume + RSI conditions
    - Exit: ATR-based SL/TP
    """
    df = df.copy()

    trades = []
    in_position = False
    entry_price = 0
    entry_idx = 0
    stop_loss = 0
    take_profit = 0

    for i in range(200, len(df)):
        row = df.iloc[i]

        if not in_position:
            # Entry conditions
            explosive_bullish = (
                row['is_bullish'] and
                row['body_pct'] > body_thresh and
                row['vol_ratio'] > vol_thresh
            )
            rsi_ok = 45 <= row['rsi'] <= 75
            trend_ok = row['rsi_5m'] > 55 if not pd.isna(row['rsi_5m']) else True

            if explosive_bullish and rsi_ok and trend_ok:
                in_position = True
                entry_price = row['close']
                entry_idx = i
                atr = row['atr']
                stop_loss = entry_price - (atr * sl_mult)
                take_profit = entry_price + (atr * tp_mult)

        else:
            # Check exits
            if row['low'] <= stop_loss:
                # Stop loss hit
                exit_price = stop_loss
                pnl_pct = (exit_price - entry_price) / entry_price * 100
                trades.append({
                    'entry_idx': entry_idx,
                    'exit_idx': i,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl_pct': pnl_pct,
                    'result': 'SL',
                    'bars_held': i - entry_idx
                })
                in_position = False

            elif row['high'] >= take_profit:
                # Take profit hit
                exit_price = take_profit
                pnl_pct = (exit_price - entry_price) / entry_price * 100
                trades.append({
                    'entry_idx': entry_idx,
                    'exit_idx': i,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl_pct': pnl_pct,
                    'result': 'TP',
                    'bars_held': i - entry_idx
                })
                in_position = False

    return analyze_trades(trades, "LONG")


def backtest_short_strategy(df: pd.DataFrame, sl_mult: float, tp_mult: float,
                            body_thresh: float, dist_thresh: float) -> dict:
    """
    Trend Distance SHORT Strategy (8.88x R:R base)
    - Entry: Price below SMAs, distance from SMA50, explosive bearish
    - Exit: ATR-based SL/TP
    """
    df = df.copy()

    trades = []
    in_position = False
    entry_price = 0
    entry_idx = 0
    stop_loss = 0
    take_profit = 0

    for i in range(200, len(df)):
        row = df.iloc[i]

        if not in_position:
            # Entry conditions
            below_smas = (
                row['close'] < row['sma_50'] and
                row['close'] < row['sma_200']
            ) if not pd.isna(row['sma_200']) else row['close'] < row['sma_50']

            distance_ok = row['dist_from_sma50'] < -dist_thresh
            explosive_bearish = row['is_bearish'] and row['body_pct'] > body_thresh
            rsi_ok = 25 <= row['rsi'] <= 55

            if below_smas and distance_ok and explosive_bearish and rsi_ok:
                in_position = True
                entry_price = row['close']
                entry_idx = i
                atr = row['atr']
                stop_loss = entry_price + (atr * sl_mult)  # SL above for short
                take_profit = entry_price - (atr * tp_mult)  # TP below for short

        else:
            # Check exits (reversed for short)
            if row['high'] >= stop_loss:
                # Stop loss hit
                exit_price = stop_loss
                pnl_pct = (entry_price - exit_price) / entry_price * 100
                trades.append({
                    'entry_idx': entry_idx,
                    'exit_idx': i,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl_pct': pnl_pct,
                    'result': 'SL',
                    'bars_held': i - entry_idx
                })
                in_position = False

            elif row['low'] <= take_profit:
                # Take profit hit
                exit_price = take_profit
                pnl_pct = (entry_price - exit_price) / entry_price * 100
                trades.append({
                    'entry_idx': entry_idx,
                    'exit_idx': i,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl_pct': pnl_pct,
                    'result': 'TP',
                    'bars_held': i - entry_idx
                })
                in_position = False

    return analyze_trades(trades, "SHORT")


def analyze_trades(trades: list, direction: str) -> dict:
    """Analyze trade results"""
    if not trades:
        return {
            'direction': direction,
            'total_trades': 0,
            'win_rate': 0,
            'total_return': 0,
            'avg_win': 0,
            'avg_loss': 0,
            'profit_factor': 0,
            'max_drawdown': 0,
            'rr_ratio': 0
        }

    df_trades = pd.DataFrame(trades)

    winners = df_trades[df_trades['pnl_pct'] > 0]
    losers = df_trades[df_trades['pnl_pct'] <= 0]

    total_trades = len(df_trades)
    win_rate = len(winners) / total_trades * 100 if total_trades > 0 else 0

    avg_win = winners['pnl_pct'].mean() if len(winners) > 0 else 0
    avg_loss = abs(losers['pnl_pct'].mean()) if len(losers) > 0 else 0

    gross_profit = winners['pnl_pct'].sum() if len(winners) > 0 else 0
    gross_loss = abs(losers['pnl_pct'].sum()) if len(losers) > 0 else 0

    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

    # Calculate drawdown
    equity = [100]
    for pnl in df_trades['pnl_pct']:
        equity.append(equity[-1] * (1 + pnl/100))

    peak = equity[0]
    max_dd = 0
    for e in equity:
        if e > peak:
            peak = e
        dd = (peak - e) / peak * 100
        if dd > max_dd:
            max_dd = dd

    total_return = (equity[-1] - 100)
    rr_ratio = avg_win / avg_loss if avg_loss > 0 else float('inf')

    return {
        'direction': direction,
        'total_trades': total_trades,
        'win_rate': win_rate,
        'total_return': total_return,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'profit_factor': profit_factor,
        'max_drawdown': max_dd,
        'rr_ratio': rr_ratio
    }


def run_backtest_for_coin(coin: str):
    """Run all strategy variants for a single coin"""
    print(f"\n{'='*70}")
    print(f"BACKTESTING: {coin}")
    print(f"{'='*70}\n")

    try:
        df = load_data(coin)
        print(f"Loaded {len(df):,} candles")
        print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")

        # Calculate volatility to adjust parameters
        df['returns'] = df['close'].pct_change() * 100
        coin_vol = df['returns'].std()
        fartcoin_vol = 0.322  # Baseline from FARTCOIN

        vol_ratio = coin_vol / fartcoin_vol
        print(f"Volatility: {coin_vol:.3f}% (vs FARTCOIN {fartcoin_vol:.3f}%, ratio: {vol_ratio:.2f}x)")

        df = calculate_indicators(df)

    except Exception as e:
        print(f"ERROR loading {coin}: {e}")
        return None

    # Define 3 versions with volatility adjustments
    # Base FARTCOIN params: SL 3x ATR, TP 12x (LONG) / 15x (SHORT)

    versions = {
        'Conservative': {
            'sl_mult': 2.0 * vol_ratio,  # Tighter stop adjusted for vol
            'tp_mult_long': 8.0 * vol_ratio,
            'tp_mult_short': 10.0 * vol_ratio,
            'body_thresh': 1.0 * vol_ratio,
            'vol_thresh': 2.5,
            'dist_thresh': 1.5 * vol_ratio
        },
        'Baseline': {
            'sl_mult': 3.0,  # Same as FARTCOIN
            'tp_mult_long': 12.0,
            'tp_mult_short': 15.0,
            'body_thresh': 1.2,
            'vol_thresh': 3.0,
            'dist_thresh': 2.0
        },
        'Aggressive': {
            'sl_mult': 4.0 / vol_ratio,  # Wider stop for volatile coins
            'tp_mult_long': 16.0 / vol_ratio,
            'tp_mult_short': 20.0 / vol_ratio,
            'body_thresh': 1.5 / vol_ratio,
            'vol_thresh': 3.5,
            'dist_thresh': 2.5 / vol_ratio
        }
    }

    results = []

    for version_name, params in versions.items():
        print(f"\n--- {version_name} Version ---")
        print(f"    SL: {params['sl_mult']:.1f}x ATR, Body: {params['body_thresh']:.2f}%")

        # LONG strategy
        long_result = backtest_long_strategy(
            df,
            sl_mult=params['sl_mult'],
            tp_mult=params['tp_mult_long'],
            body_thresh=params['body_thresh'],
            vol_thresh=params['vol_thresh']
        )
        long_result['version'] = version_name
        long_result['coin'] = coin
        results.append(long_result)

        print(f"    LONG:  {long_result['total_trades']} trades, "
              f"WR: {long_result['win_rate']:.1f}%, "
              f"Return: {long_result['total_return']:+.2f}%, "
              f"R:R: {long_result['rr_ratio']:.2f}x")

        # SHORT strategy
        short_result = backtest_short_strategy(
            df,
            sl_mult=params['sl_mult'],
            tp_mult=params['tp_mult_short'],
            body_thresh=params['body_thresh'],
            dist_thresh=params['dist_thresh']
        )
        short_result['version'] = version_name
        short_result['coin'] = coin
        results.append(short_result)

        print(f"    SHORT: {short_result['total_trades']} trades, "
              f"WR: {short_result['win_rate']:.1f}%, "
              f"Return: {short_result['total_return']:+.2f}%, "
              f"R:R: {short_result['rr_ratio']:.2f}x")

    # Find best performing version
    print(f"\n{'='*70}")
    print(f"BEST RESULTS FOR {coin}")
    print(f"{'='*70}")

    df_results = pd.DataFrame(results)

    best_long = df_results[df_results['direction'] == 'LONG'].sort_values('total_return', ascending=False).iloc[0]
    best_short = df_results[df_results['direction'] == 'SHORT'].sort_values('total_return', ascending=False).iloc[0]

    print(f"\nBest LONG:  {best_long['version']} - {best_long['total_return']:+.2f}% return, "
          f"{best_long['rr_ratio']:.2f}x R:R, {best_long['win_rate']:.1f}% WR")
    print(f"Best SHORT: {best_short['version']} - {best_short['total_return']:+.2f}% return, "
          f"{best_short['rr_ratio']:.2f}x R:R, {best_short['win_rate']:.1f}% WR")

    # Save results
    output_file = f"/workspaces/Carebiuro_windykacja/trading/results/{coin.lower()}_strategy_backtest.csv"
    df_results.to_csv(output_file, index=False)
    print(f"\nResults saved to: {output_file}")

    return df_results


if __name__ == "__main__":
    if len(sys.argv) > 1:
        coin = sys.argv[1].upper()
        run_backtest_for_coin(coin)
    else:
        print("Usage: python backtest_meme_strategies.py COIN")
        print("Example: python backtest_meme_strategies.py PNUT")
