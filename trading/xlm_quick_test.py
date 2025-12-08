"""
XLM/USDT Quick Strategy Test
Focus on most promising strategies only
"""

import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

def load_data():
    """Load XLM/USDT 1m data"""
    df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/xlm_usdt_1m_lbank.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)
    print(f"Loaded {len(df):,} candles from {df['timestamp'].iloc[0]} to {df['timestamp'].iloc[-1]}")
    return df

def calculate_indicators(df):
    """Calculate technical indicators"""

    # ATR
    df['tr'] = np.maximum(
        df['high'] - df['low'],
        np.maximum(
            abs(df['high'] - df['close'].shift(1)),
            abs(df['low'] - df['close'].shift(1))
        )
    )
    df['atr'] = df['tr'].rolling(14).mean()

    # EMAs
    df['ema_8'] = df['close'].ewm(span=8, adjust=False).mean()
    df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()

    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))

    # Bollinger Bands
    df['bb_mid'] = df['close'].rolling(20).mean()
    df['bb_std'] = df['close'].rolling(20).std()
    df['bb_upper'] = df['bb_mid'] + 2 * df['bb_std']
    df['bb_lower'] = df['bb_mid'] - 2 * df['bb_std']

    # Volume
    df['volume_ma'] = df['volume'].rolling(20).mean()

    # Session
    df['hour'] = df['timestamp'].dt.hour

    return df

def backtest_strategy(df, strategy_name, entry_signals, sl_mult, tp_mult, order_type='market', session_filter=None):
    """Simple backtest engine"""

    capital = 1000.0
    equity = capital
    peak_equity = capital
    max_drawdown = 0.0

    in_position = False
    entry_price = 0.0
    stop_loss = 0.0
    take_profit = 0.0
    entry_idx = 0

    trades = []

    # Fees
    leverage = 10
    fee_rate = 0.001 if order_type == 'market' else 0.00035

    # Session filter
    if session_filter == 'asian':
        mask = df['hour'] < 8
    elif session_filter == 'euro':
        mask = (df['hour'] >= 8) & (df['hour'] < 14)
    elif session_filter == 'us':
        mask = (df['hour'] >= 14) & (df['hour'] < 22)
    else:
        mask = pd.Series(True, index=df.index)

    for i in range(250, len(df)):
        if not mask.iloc[i]:
            continue

        row = df.iloc[i]

        # Update drawdown
        if equity > peak_equity:
            peak_equity = equity
        current_dd = (peak_equity - equity) / peak_equity
        if current_dd > max_drawdown:
            max_drawdown = current_dd

        # Exit logic
        if in_position:
            exit_price = None
            exit_reason = None

            if row['low'] <= stop_loss:
                exit_price = stop_loss
                exit_reason = 'SL'
            elif row['high'] >= take_profit:
                exit_price = take_profit
                exit_reason = 'TP'

            if exit_price:
                price_change = (exit_price - entry_price) / entry_price
                pnl_pct = price_change * leverage - (2 * fee_rate * leverage)
                pnl_dollars = equity * pnl_pct
                equity += pnl_dollars

                trades.append({
                    'entry_time': df.iloc[entry_idx]['timestamp'],
                    'exit_time': row['timestamp'],
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl_dollars': pnl_dollars,
                    'exit_reason': exit_reason,
                    'bars_held': i - entry_idx
                })

                in_position = False

        # Entry logic
        if not in_position and entry_signals.iloc[i] == 1:
            if order_type == 'market':
                entry_price = row['close']
            else:
                entry_price = row['close'] * 1.00035
                if i + 1 < len(df):
                    next_bar = df.iloc[i + 1]
                    if next_bar['low'] > entry_price:
                        continue

            atr = row['atr']
            stop_loss = entry_price - (sl_mult * atr)
            take_profit = entry_price + (tp_mult * atr)

            in_position = True
            entry_idx = i

    # Calculate results
    if len(trades) == 0:
        return None

    trades_df = pd.DataFrame(trades)
    total_trades = len(trades_df)
    winners = len(trades_df[trades_df['pnl_dollars'] > 0])
    win_rate = winners / total_trades * 100 if total_trades > 0 else 0

    total_pnl = trades_df['pnl_dollars'].sum()
    total_pnl_pct = (equity - capital) / capital * 100

    max_dd_dollars = max_drawdown * peak_equity
    rr_ratio = total_pnl / max_dd_dollars if max_dd_dollars > 0 else 0

    return {
        'strategy': strategy_name,
        'session': session_filter or 'all',
        'order_type': order_type,
        'sl_mult': sl_mult,
        'tp_mult': tp_mult,
        'total_trades': total_trades,
        'win_rate': win_rate,
        'total_pnl_pct': total_pnl_pct,
        'max_dd_pct': max_drawdown * 100,
        'rr_ratio': rr_ratio,
        'final_equity': equity
    }

# Strategy: EMA Pullback
def ema_pullback(df):
    signals = pd.Series(0, index=df.index)
    uptrend = df['close'] > df['ema_20']
    pullback = (df['low'].rolling(3).min() <= df['ema_20']) & (df['close'] > df['ema_20'])
    not_oversold = df['rsi'] > 40
    signals[uptrend & pullback & not_oversold] = 1
    return signals

# Strategy: BB Mean Reversion
def bb_mean_reversion(df):
    signals = pd.Series(0, index=df.index)
    touches_lower = df['low'] <= df['bb_lower']
    bounce = df['close'] > df['bb_lower']
    not_crash = df['rsi'] > 20
    signals[touches_lower & bounce & not_crash] = 1
    return signals

# Strategy: RSI Oversold
def rsi_oversold(df):
    signals = pd.Series(0, index=df.index)
    oversold = df['rsi'] < 30
    rsi_rising = df['rsi'] > df['rsi'].shift(1)
    green = df['close'] > df['open']
    signals[oversold & rsi_rising & green] = 1
    return signals

# Strategy: Momentum Breakout
def momentum_breakout(df):
    signals = pd.Series(0, index=df.index)
    recent_high = df['high'].rolling(20).max().shift(1)
    breakout = df['close'] > recent_high
    rsi_ok = df['rsi'] > 55
    volume_ok = df['volume'] > df['volume_ma'] * 1.5
    signals[breakout & rsi_ok & volume_ok] = 1
    return signals

# Main test
def run_quick_test():
    print("XLM/USDT Quick Strategy Test")
    print("=" * 80)

    df = load_data()
    df = calculate_indicators(df)

    strategies = [
        ('EMA_Pullback', ema_pullback(df)),
        ('BB_MeanReversion', bb_mean_reversion(df)),
        ('RSI_Oversold', rsi_oversold(df)),
        ('Momentum_Breakout', momentum_breakout(df))
    ]

    sl_tp_configs = [
        (1.5, 3.0),
        (2.0, 4.0),
        (2.0, 5.0),
        (2.5, 5.0),
        (3.0, 6.0)
    ]

    sessions = [None, 'asian', 'euro', 'us']
    order_types = ['market', 'limit']

    results = []

    for strategy_name, signals in strategies:
        for sl, tp in sl_tp_configs:
            for session in sessions:
                for order_type in order_types:
                    result = backtest_strategy(df, strategy_name, signals, sl, tp, order_type, session)
                    if result and result['total_trades'] >= 30:
                        results.append(result)

    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('rr_ratio', ascending=False)

    # Save results
    results_df.to_csv('/workspaces/Carebiuro_windykacja/trading/results/xlm_quick_results.csv', index=False)

    print("\nTOP 20 STRATEGIES:")
    print(results_df.head(20)[['strategy', 'session', 'order_type', 'sl_mult', 'tp_mult',
                                'total_trades', 'win_rate', 'total_pnl_pct', 'rr_ratio']].to_string(index=False))

    # Winning strategies
    winners = results_df[(results_df['rr_ratio'] >= 2.0) & (results_df['win_rate'] >= 50.0)]

    if len(winners) > 0:
        print(f"\nWINNING STRATEGIES ({len(winners)}):")
        print(winners[['strategy', 'session', 'order_type', 'sl_mult', 'tp_mult',
                       'total_trades', 'win_rate', 'total_pnl_pct', 'rr_ratio']].to_string(index=False))
    else:
        print("\nNo strategies met winning criteria (R:R >= 2.0, Win Rate >= 50%)")
        print("\nBest by R:R ratio:")
        print(results_df.head(5)[['strategy', 'session', 'win_rate', 'rr_ratio', 'total_pnl_pct']].to_string(index=False))

if __name__ == '__main__':
    run_quick_test()
