"""
XLM/USDT Comprehensive Strategy Test
Test multiple strategies with conservative position sizing
"""

import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

def load_and_prep_data():
    """Load and calculate all indicators"""
    df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/xlm_usdt_1m_lbank.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # ATR
    df['tr'] = np.maximum(
        df['high'] - df['low'],
        np.maximum(abs(df['high'] - df['close'].shift(1)), abs(df['low'] - df['close'].shift(1)))
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
    df['volume_ratio'] = df['volume'] / df['volume_ma']

    # Trend detection
    df['uptrend'] = (df['ema_8'] > df['ema_20']) & (df['ema_20'] > df['ema_50'])

    return df

def backtest(df, entry_func, name, sl_atr, tp_atr, risk_pct=0.02):
    """
    Backtest with proper position sizing
    risk_pct: % of equity to risk per trade
    """
    capital = 1000
    equity = capital
    peak = capital
    max_dd = 0
    trades = []
    in_pos = False

    leverage = 10
    fee_rate = 0.001  # 0.1% per side = 0.2% round trip = 2% with 10x leverage

    for i in range(250, len(df)):
        row = df.iloc[i]

        # Update drawdown
        if equity > peak:
            peak = equity
        dd = (peak - equity) / peak
        if dd > max_dd:
            max_dd = dd

        # Exit logic
        if in_pos:
            exit_occurred = False
            if row['low'] <= sl:
                exit_price = sl
                exit_reason = 'SL'
                exit_occurred = True
            elif row['high'] >= tp:
                exit_price = tp
                exit_reason = 'TP'
                exit_occurred = True

            if exit_occurred:
                # Calculate P&L with position sizing
                price_change_pct = (exit_price - entry) / entry

                # Risk-based position sizing
                # If we're risking 2% of equity and SL is X% away, position size = 2% / X%
                sl_distance_pct = abs(entry - sl) / entry
                position_size_multiplier = min(risk_pct / sl_distance_pct, leverage)  # Cap at leverage

                pnl_pct = price_change_pct * position_size_multiplier
                total_fees = 2 * fee_rate * position_size_multiplier
                pnl_pct -= total_fees

                pnl_dollars = equity * pnl_pct
                equity += pnl_dollars

                trades.append({
                    'pnl_pct': pnl_pct * 100,
                    'pnl_dollars': pnl_dollars,
                    'reason': exit_reason,
                    'equity': equity
                })
                in_pos = False

        # Entry logic
        if not in_pos and equity > 0:
            signal = entry_func(df, i)
            if signal:
                entry = row['close']
                sl = entry - sl_atr * row['atr']
                tp = entry + tp_atr * row['atr']
                in_pos = True

    # Calculate metrics
    if len(trades) == 0:
        return None

    trades_df = pd.DataFrame(trades)
    total = len(trades_df)
    winners = len(trades_df[trades_df['pnl_dollars'] > 0])
    losers = total - winners
    win_rate = winners / total * 100

    avg_win = trades_df[trades_df['pnl_dollars'] > 0]['pnl_dollars'].mean() if winners > 0 else 0
    avg_loss = abs(trades_df[trades_df['pnl_dollars'] < 0]['pnl_dollars'].mean()) if losers > 0 else 0

    total_pnl = (equity - capital) / capital * 100
    max_dd_dollars = max_dd * peak
    rr = (equity - capital) / max_dd_dollars if max_dd_dollars > 0 else 0

    return {
        'strategy': name,
        'sl_atr': sl_atr,
        'tp_atr': tp_atr,
        'trades': total,
        'win_rate': win_rate,
        'total_pnl': total_pnl,
        'max_dd': max_dd * 100,
        'rr_ratio': rr,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'final_equity': equity
    }

# Strategy definitions
def strategy_ema_pullback(df, i):
    """EMA20 pullback during uptrend"""
    row = df.iloc[i]
    uptrend = row['close'] > row['ema_20']
    pullback = row['low'] <= row['ema_20'] and row['close'] > row['ema_20']
    rsi_ok = row['rsi'] > 40 and row['rsi'] < 60
    return uptrend and pullback and rsi_ok

def strategy_bb_bounce(df, i):
    """Bounce from lower BB"""
    row = df.iloc[i]
    prev = df.iloc[i-1]
    touches_lower = row['low'] <= row['bb_lower']
    bounces = row['close'] > row['bb_lower']
    rsi_ok = row['rsi'] > 25 and row['rsi'] < 35
    uptrend = row['close'] > row['ema_50']
    return touches_lower and bounces and rsi_ok and uptrend

def strategy_rsi_oversold_bounce(df, i):
    """RSI oversold with bounce confirmation"""
    row = df.iloc[i]
    prev = df.iloc[i-1]
    oversold = prev['rsi'] < 30
    turning_up = row['rsi'] > prev['rsi']
    green_candle = row['close'] > row['open']
    uptrend = row['close'] > row['ema_50']
    return oversold and turning_up and green_candle and uptrend

def strategy_momentum_breakout(df, i):
    """Breakout with volume confirmation"""
    row = df.iloc[i]
    recent_high = df.iloc[max(0,i-20):i]['high'].max()
    breakout = row['close'] > recent_high
    volume_ok = row['volume_ratio'] > 1.5
    rsi_ok = row['rsi'] > 50 and row['rsi'] < 70
    return breakout and volume_ok and rsi_ok

def strategy_conservative_trend(df, i):
    """Only trade in strong uptrends with pullbacks"""
    row = df.iloc[i]
    strong_uptrend = row['uptrend'] and row['close'] > row['ema_50']
    pullback_to_8 = row['low'] <= row['ema_8'] and row['close'] > row['ema_8']
    rsi_ok = row['rsi'] > 45 and row['rsi'] < 65
    not_extended = row['close'] < row['bb_upper']
    return strong_uptrend and pullback_to_8 and rsi_ok and not_extended

# Run all tests
def run_tests():
    print("XLM/USDT Comprehensive Strategy Test")
    print("=" * 80)

    df = load_and_prep_data()
    print(f"Loaded {len(df):,} candles")
    print(f"Period: {df['timestamp'].iloc[0]} to {df['timestamp'].iloc[-1]}\n")

    strategies = [
        ('EMA20_Pullback', strategy_ema_pullback),
        ('BB_Bounce', strategy_bb_bounce),
        ('RSI_Oversold_Bounce', strategy_rsi_oversold_bounce),
        ('Momentum_Breakout', strategy_momentum_breakout),
        ('Conservative_Trend', strategy_conservative_trend),
    ]

    sl_tp_configs = [
        (1.5, 3.0),
        (2.0, 4.0),
        (2.5, 5.0),
        (3.0, 6.0),
    ]

    results = []

    for name, func in strategies:
        for sl, tp in sl_tp_configs:
            result = backtest(df, func, name, sl, tp, risk_pct=0.02)
            if result and result['trades'] >= 30:
                results.append(result)
                print(f"✓ {name} (SL:{sl}, TP:{tp}): {result['trades']} trades, {result['win_rate']:.1f}% WR, {result['total_pnl']:.1f}% PnL, R:R {result['rr_ratio']:.2f}")

    # Sort and save results
    results_df = pd.DataFrame(results)
    if len(results_df) > 0:
        results_df = results_df.sort_values('rr_ratio', ascending=False)
        results_df.to_csv('/workspaces/Carebiuro_windykacja/trading/results/xlm_master_results.csv', index=False)

        print("\n" + "=" * 80)
        print("TOP 10 STRATEGIES BY R:R RATIO")
        print("=" * 80)
        print(results_df.head(10)[['strategy', 'sl_atr', 'tp_atr', 'trades', 'win_rate', 'total_pnl', 'rr_ratio']].to_string(index=False))

        # Winners
        winners = results_df[(results_df['rr_ratio'] >= 2.0) & (results_df['win_rate'] >= 50.0)]
        if len(winners) > 0:
            print(f"\n✅ WINNING STRATEGIES ({len(winners)}):")
            print(winners[['strategy', 'sl_atr', 'tp_atr', 'trades', 'win_rate', 'total_pnl', 'rr_ratio']].to_string(index=False))
        else:
            print("\n⚠️  No strategies met winning criteria (R:R >= 2.0, WR >= 50%)")
            print("\nBest performers:")
            print(results_df.head(5)[['strategy', 'win_rate', 'total_pnl', 'rr_ratio']].to_string(index=False))
    else:
        print("\n❌ No strategies generated enough trades (min 30)")

if __name__ == '__main__':
    run_tests()
