"""
DOGE/USDT Fast Strategy Discovery
==================================
Focused backtest on most promising strategies for DOGE.
"""

import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

INITIAL_CAPITAL = 10000
FEE = 0.001  # 0.1% round-trip

def calculate_indicators(df):
    """Calculate technical indicators"""
    data = df.copy()

    # EMAs
    for period in [10, 20, 50, 200]:
        data[f'ema_{period}'] = data['close'].ewm(span=period, adjust=False).mean()

    # RSI
    delta = data['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    data['rsi'] = 100 - (100 / (1 + rs))

    # ATR
    data['tr'] = np.maximum(
        data['high'] - data['low'],
        np.maximum(
            abs(data['high'] - data['close'].shift(1)),
            abs(data['low'] - data['close'].shift(1))
        )
    )
    data['atr'] = data['tr'].rolling(14).mean()

    # MACD
    data['ema_12'] = data['close'].ewm(span=12, adjust=False).mean()
    data['ema_26'] = data['close'].ewm(span=26, adjust=False).mean()
    data['macd'] = data['ema_12'] - data['ema_26']
    data['macd_signal'] = data['macd'].ewm(span=9, adjust=False).mean()

    # Volume
    data['vol_ma'] = data['volume'].rolling(20).mean()
    data['vol_ratio'] = data['volume'] / data['vol_ma']

    return data

def backtest(df, strategy_name, get_signal_func, sl_mult=2.0, tp_mult=4.0):
    """Simple backtest engine"""
    capital = INITIAL_CAPITAL
    position = None
    trades = []

    for i in range(200, len(df)):
        row = df.iloc[i]

        # Manage existing position
        if position:
            if position['type'] == 'LONG':
                if row['high'] >= position['tp']:
                    pnl_pct = (position['tp'] - position['entry']) / position['entry'] * 100 - FEE * 100
                    capital *= (1 + pnl_pct / 100)
                    trades.append({'pnl': pnl_pct, 'type': 'TP'})
                    position = None
                elif row['low'] <= position['sl']:
                    pnl_pct = (position['sl'] - position['entry']) / position['entry'] * 100 - FEE * 100
                    capital *= (1 + pnl_pct / 100)
                    trades.append({'pnl': pnl_pct, 'type': 'SL'})
                    position = None
            else:  # SHORT
                if row['low'] <= position['tp']:
                    pnl_pct = (position['entry'] - position['tp']) / position['entry'] * 100 - FEE * 100
                    capital *= (1 + pnl_pct / 100)
                    trades.append({'pnl': pnl_pct, 'type': 'TP'})
                    position = None
                elif row['high'] >= position['sl']:
                    pnl_pct = (position['entry'] - position['sl']) / position['entry'] * 100 - FEE * 100
                    capital *= (1 + pnl_pct / 100)
                    trades.append({'pnl': pnl_pct, 'type': 'SL'})
                    position = None

        # Check for new signal
        if not position:
            signal = get_signal_func(df, i, sl_mult, tp_mult)
            if signal:
                position = signal

    if len(trades) < 30:
        return None

    trades_df = pd.DataFrame(trades)
    wins = trades_df[trades_df['pnl'] > 0]

    # Calculate drawdown
    trades_df['capital'] = INITIAL_CAPITAL
    for i in range(len(trades_df)):
        if i > 0:
            trades_df.loc[i, 'capital'] = trades_df.loc[i-1, 'capital'] * (1 + trades_df.loc[i, 'pnl'] / 100)
        else:
            trades_df.loc[i, 'capital'] = INITIAL_CAPITAL * (1 + trades_df.loc[i, 'pnl'] / 100)

    trades_df['peak'] = trades_df['capital'].cummax()
    trades_df['dd'] = (trades_df['capital'] - trades_df['peak']) / trades_df['peak'] * 100
    max_dd = abs(trades_df['dd'].min())

    total_return = (capital - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
    rr = total_return / max_dd if max_dd > 0 else 0

    return {
        'strategy': strategy_name,
        'trades': len(trades_df),
        'win_rate': len(wins) / len(trades_df) * 100,
        'avg_win': wins['pnl'].mean() if len(wins) > 0 else 0,
        'avg_loss': abs(trades_df[trades_df['pnl'] <= 0]['pnl'].mean()),
        'return': total_return,
        'max_dd': max_dd,
        'rr': rr,
        'capital': capital
    }

# ==================== STRATEGIES ====================

def ema_cross_10_50(df, i, sl_mult, tp_mult):
    """EMA 10/50 crossover"""
    row = df.iloc[i]
    prev = df.iloc[i-1]

    if prev['ema_10'] <= prev['ema_50'] and row['ema_10'] > row['ema_50']:
        return {
            'type': 'LONG',
            'entry': row['close'],
            'sl': row['close'] - row['atr'] * sl_mult,
            'tp': row['close'] + row['atr'] * tp_mult
        }
    if prev['ema_10'] >= prev['ema_50'] and row['ema_10'] < row['ema_50']:
        return {
            'type': 'SHORT',
            'entry': row['close'],
            'sl': row['close'] + row['atr'] * sl_mult,
            'tp': row['close'] - row['atr'] * tp_mult
        }
    return None

def ema_cross_20_50(df, i, sl_mult, tp_mult):
    """EMA 20/50 crossover"""
    row = df.iloc[i]
    prev = df.iloc[i-1]

    if prev['ema_20'] <= prev['ema_50'] and row['ema_20'] > row['ema_50']:
        return {
            'type': 'LONG',
            'entry': row['close'],
            'sl': row['close'] - row['atr'] * sl_mult,
            'tp': row['close'] + row['atr'] * tp_mult
        }
    if prev['ema_20'] >= prev['ema_50'] and row['ema_20'] < row['ema_50']:
        return {
            'type': 'SHORT',
            'entry': row['close'],
            'sl': row['close'] + row['atr'] * sl_mult,
            'tp': row['close'] - row['atr'] * tp_mult
        }
    return None

def rsi_oversold_long(df, i, sl_mult, tp_mult):
    """RSI oversold - long only"""
    row = df.iloc[i]
    if row['rsi'] < 30:
        return {
            'type': 'LONG',
            'entry': row['close'],
            'sl': row['close'] - row['atr'] * sl_mult,
            'tp': row['close'] + row['atr'] * tp_mult
        }
    return None

def rsi_mean_reversion(df, i, sl_mult, tp_mult):
    """RSI mean reversion - both directions"""
    row = df.iloc[i]
    if row['rsi'] < 25:
        return {
            'type': 'LONG',
            'entry': row['close'],
            'sl': row['close'] - row['atr'] * sl_mult,
            'tp': row['close'] + row['atr'] * tp_mult
        }
    if row['rsi'] > 75:
        return {
            'type': 'SHORT',
            'entry': row['close'],
            'sl': row['close'] + row['atr'] * sl_mult,
            'tp': row['close'] - row['atr'] * tp_mult
        }
    return None

def macd_cross(df, i, sl_mult, tp_mult):
    """MACD crossover"""
    row = df.iloc[i]
    prev = df.iloc[i-1]

    if prev['macd'] <= prev['macd_signal'] and row['macd'] > row['macd_signal']:
        return {
            'type': 'LONG',
            'entry': row['close'],
            'sl': row['close'] - row['atr'] * sl_mult,
            'tp': row['close'] + row['atr'] * tp_mult
        }
    if prev['macd'] >= prev['macd_signal'] and row['macd'] < row['macd_signal']:
        return {
            'type': 'SHORT',
            'entry': row['close'],
            'sl': row['close'] + row['atr'] * sl_mult,
            'tp': row['close'] - row['atr'] * tp_mult
        }
    return None

def volume_breakout(df, i, sl_mult, tp_mult):
    """Volume breakout with EMA filter"""
    row = df.iloc[i]

    if row['vol_ratio'] < 1.5:
        return None

    if row['close'] > row['ema_20']:
        return {
            'type': 'LONG',
            'entry': row['close'],
            'sl': row['close'] - row['atr'] * sl_mult,
            'tp': row['close'] + row['atr'] * tp_mult
        }
    if row['close'] < row['ema_20']:
        return {
            'type': 'SHORT',
            'entry': row['close'],
            'sl': row['close'] + row['atr'] * sl_mult,
            'tp': row['close'] - row['atr'] * tp_mult
        }
    return None

# ==================== MAIN ====================

def main():
    print("DOGE/USDT Fast Strategy Discovery")
    print("=" * 60)

    # Load data
    df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/doge_usdt_1m_lbank.csv')
    print(f"Loaded {len(df):,} candles")
    df = calculate_indicators(df)

    strategies = [
        ema_cross_10_50,
        ema_cross_20_50,
        rsi_oversold_long,
        rsi_mean_reversion,
        macd_cross,
        volume_breakout
    ]

    sl_tp_combos = [
        (1.5, 3.0),
        (2.0, 4.0),
        (2.5, 5.0),
        (3.0, 6.0)
    ]

    results = []
    total_tests = len(strategies) * len(sl_tp_combos)
    count = 0

    for strategy_func in strategies:
        for sl_mult, tp_mult in sl_tp_combos:
            count += 1
            strategy_name = f"{strategy_func.__name__}_SL{sl_mult}_TP{tp_mult}"

            result = backtest(df, strategy_name, strategy_func, sl_mult, tp_mult)
            if result:
                results.append(result)

            if count % 5 == 0:
                print(f"Progress: {count}/{total_tests}")

    print(f"\nCompleted {len(results)} successful tests")

    if results:
        results_df = pd.DataFrame(results)
        results_df = results_df.sort_values('rr', ascending=False)

        # Save
        output = '/workspaces/Carebiuro_windykacja/trading/results/doge_master_results.csv'
        results_df.to_csv(output, index=False)
        print(f"\nSaved to: {output}")

        # Display top 10
        print("\nTOP 10 STRATEGIES:")
        print("=" * 60)
        for idx, row in results_df.head(10).iterrows():
            print(f"\n{row['strategy']}")
            print(f"  Trades: {row['trades']}")
            print(f"  Win rate: {row['win_rate']:.1f}%")
            print(f"  Return: {row['return']:.2f}%")
            print(f"  Max DD: {row['max_dd']:.2f}%")
            print(f"  R:R: {row['rr']:.2f}")

        # Best
        best = results_df.iloc[0]
        print("\n" + "=" * 60)
        print("BEST STRATEGY")
        print("=" * 60)
        print(f"Name: {best['strategy']}")
        print(f"Trades: {best['trades']}")
        print(f"Win rate: {best['win_rate']:.1f}%")
        print(f"Avg win: {best['avg_win']:.2f}%")
        print(f"Avg loss: {best['avg_loss']:.2f}%")
        print(f"Total return: {best['return']:.2f}%")
        print(f"Max drawdown: {best['max_dd']:.2f}%")
        print(f"R:R ratio: {best['rr']:.2f}")
        print(f"Final capital: ${best['capital']:.2f}")

        # Criteria check
        print("\n" + "=" * 60)
        print("CRITERIA CHECK")
        print("=" * 60)
        print(f"R:R >= 2.0: {'✓' if best['rr'] >= 2.0 else '✗'} ({best['rr']:.2f})")
        print(f"Win rate >= 50%: {'✓' if best['win_rate'] >= 50 else '✗'} ({best['win_rate']:.1f}%)")
        print(f"Trades >= 30: {'✓' if best['trades'] >= 30 else '✗'} ({best['trades']})")

    else:
        print("\nNo successful strategies found.")

if __name__ == '__main__':
    main()
