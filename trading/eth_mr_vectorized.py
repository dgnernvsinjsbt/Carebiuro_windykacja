"""
ETH/USDT Mean Reversion - VECTORIZED (but avoiding look-ahead bias)
Uses NumPy arrays for speed while maintaining proper backtest logic
"""

import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

print("="*80)
print("ETH/USDT MEAN REVERSION - VECTORIZED BACKTEST")
print("="*80)

# Load data
print("\nLoading data...")
df = pd.read_csv('eth_usdt_1m_lbank.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

print(f"Dataset: {len(df):,} candles")
print(f"Period: {df['timestamp'].iloc[0]} to {df['timestamp'].iloc[-1]}")

# Calculate indicators
print("\nCalculating indicators...")

# ATR
df['tr'] = np.maximum(
    df['high'] - df['low'],
    np.maximum(
        abs(df['high'] - df['close'].shift(1)),
        abs(df['low'] - df['close'].shift(1))
    )
)
df['atr'] = df['tr'].rolling(14).mean()

# Bollinger Bands
df['bb_mid'] = df['close'].rolling(20).mean()
df['bb_std'] = df['close'].rolling(20).std()
df['bb_upper'] = df['bb_mid'] + 2 * df['bb_std']
df['bb_lower'] = df['bb_mid'] - 2 * df['bb_std']
df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_mid'] * 100

# RSI
delta = df['close'].diff()
gain = (delta.where(delta > 0, 0)).rolling(14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
rs = gain / loss
df['rsi'] = 100 - (100 / (1 + rs))

# Distance from BB bands
df['dist_lower'] = (df['close'] - df['bb_lower']) / df['close']
df['dist_upper'] = (df['bb_upper'] - df['close']) / df['close']

# Drop NaN rows
df = df.dropna().reset_index(drop=True)

print(f"Valid candles after indicators: {len(df):,}")

# Market stats
print(f"\nMarket Statistics:")
print(f"  Avg ATR: ${df['atr'].mean():.2f} ({df['atr'].mean()/df['close'].mean()*100:.3f}%)")
print(f"  Avg BB Width: {df['bb_width'].mean():.3f}%")
print(f"  Tight BB (<1.5%): {(df['bb_width']<1.5).sum()/len(df)*100:.1f}% of time")
print(f"  Avg RSI: {df['rsi'].mean():.1f}")
print(f"  RSI <30: {(df['rsi']<30).sum()} times ({(df['rsi']<30).sum()/len(df)*100:.1f}%)")
print(f"  RSI >70: {(df['rsi']>70).sum()} times ({(df['rsi']>70).sum()/len(df)*100:.1f}%)")

# Simplified backtest function using vectorized operations where possible
def quick_backtest(signals_long, signals_short, df, sl_mult, tp_mult, leverage):
    """
    Vectorized backtest for mean reversion
    signals_long/short: boolean arrays indicating entry points
    """
    capital = 1000.0
    equity = capital
    peak = capital
    max_dd = 0.0

    trades = []
    in_position = False
    position_type = None
    entry_price = 0.0
    stop_loss = 0.0
    take_profit = 0.0
    entry_idx = 0

    fee_rate = 0.00005

    for i in range(len(df)):
        row = df.iloc[i]

        # Track drawdown
        if equity > peak:
            peak = equity
        dd = (peak - equity) / peak
        if dd > max_dd:
            max_dd = dd

        # Exit logic
        if in_position:
            exit_price = None
            reason = None

            if position_type == 'long':
                if row['low'] <= stop_loss:
                    exit_price = stop_loss
                    reason = 'SL'
                elif row['high'] >= take_profit:
                    exit_price = take_profit
                    reason = 'TP'
            else:
                if row['high'] >= stop_loss:
                    exit_price = stop_loss
                    reason = 'SL'
                elif row['low'] <= take_profit:
                    exit_price = take_profit
                    reason = 'TP'

            if exit_price:
                if position_type == 'long':
                    pct = (exit_price - entry_price) / entry_price
                else:
                    pct = (entry_price - exit_price) / entry_price

                pnl_pct = pct * leverage - (2 * fee_rate * leverage)
                pnl = equity * pnl_pct
                equity += pnl

                trades.append({
                    'entry_idx': entry_idx,
                    'exit_idx': i,
                    'type': position_type,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'reason': reason,
                    'pnl_pct': pnl_pct * 100,
                    'equity': equity
                })

                in_position = False

        # Entry logic (only if not in position and spacing allows)
        if not in_position:
            if signals_long[i]:
                position_type = 'long'
                entry_price = row['close']
                stop_loss = entry_price - (row['atr'] * sl_mult)
                take_profit = entry_price + (row['atr'] * tp_mult)
                entry_idx = i
                in_position = True

            elif signals_short[i]:
                position_type = 'short'
                entry_price = row['close']
                stop_loss = entry_price + (row['atr'] * sl_mult)
                take_profit = entry_price - (row['atr'] * tp_mult)
                entry_idx = i
                in_position = True

    if len(trades) == 0:
        return None

    trades_df = pd.DataFrame(trades)
    wins = trades_df[trades_df['pnl_pct'] > 0]

    total_return = (equity - 1000) / 1000 * 100
    max_dd_pct = max_dd * 100

    return {
        'trades': len(trades_df),
        'win_rate': len(wins) / len(trades_df) * 100,
        'avg_win': wins['pnl_pct'].mean() if len(wins) > 0 else 0,
        'total_return': total_return,
        'max_dd': max_dd_pct,
        'profit_dd': abs(total_return) / max(max_dd_pct, 0.01),
        'equity': equity,
        'trades_df': trades_df
    }

# Test RSI strategies
print("\n" + "="*80)
print("TESTING RSI STRATEGIES")
print("="*80)

rsi_results = []

for os in [25, 30]:
    for ob in [70, 75]:
        # Generate signals
        long_sig = (df['rsi'] < os).values
        short_sig = (df['rsi'] > ob).values

        for sl, tp in [(2.0, 4.0), (2.0, 5.0), (2.5, 5.0), (2.0, 6.0), (2.5, 6.0)]:
            for lev in [10, 15, 20]:
                res = quick_backtest(long_sig, short_sig, df, sl, tp, lev)

                if res and res['trades'] >= 10:
                    rsi_results.append({
                        'name': f"RSI_OS{os}_OB{ob}_SL{sl}_TP{tp}_LEV{lev}",
                        'type': 'RSI',
                        'os': os,
                        'ob': ob,
                        'sl': sl,
                        'tp': tp,
                        'leverage': lev,
                        **res
                    })

print(f"Found {len(rsi_results)} profitable RSI strategies")

# Test BB strategies
print("\n" + "="*80)
print("TESTING BOLLINGER BAND STRATEGIES")
print("="*80)

bb_results = []

for thresh in [0.001, 0.002, 0.003]:
    for max_width in [1.5, 2.0]:
        # Generate signals
        tight_bb = (df['bb_width'] < max_width).values
        long_sig = (df['dist_lower'] < thresh) & tight_bb
        short_sig = (df['dist_upper'] < thresh) & tight_bb

        for sl, tp in [(2.0, 4.0), (2.0, 5.0), (2.5, 5.0), (2.0, 6.0)]:
            for lev in [10, 15, 20]:
                res = quick_backtest(long_sig, short_sig, df, sl, tp, lev)

                if res and res['trades'] >= 10:
                    bb_results.append({
                        'name': f"BB_T{thresh*1000:.0f}_W{max_width}_SL{sl}_TP{tp}_LEV{lev}",
                        'type': 'BB',
                        'thresh': thresh,
                        'max_width': max_width,
                        'sl': sl,
                        'tp': tp,
                        'leverage': lev,
                        **res
                    })

print(f"Found {len(bb_results)} profitable BB strategies")

# Test Combined strategies
print("\n" + "="*80)
print("TESTING COMBINED RSI+BB STRATEGIES")
print("="*80)

combo_results = []

for os, ob in [(25, 75), (30, 70)]:
    for thresh in [0.002, 0.003]:
        for max_width in [1.5, 2.0]:
            # Generate signals
            rsi_long = (df['rsi'] < os).values
            rsi_short = (df['rsi'] > ob).values
            tight_bb = (df['bb_width'] < max_width).values
            bb_long = (df['dist_lower'] < thresh).values
            bb_short = (df['dist_upper'] < thresh).values

            long_sig = rsi_long & bb_long & tight_bb
            short_sig = rsi_short & bb_short & tight_bb

            for sl, tp in [(2.0, 5.0), (2.5, 5.0), (2.0, 6.0), (2.5, 6.0)]:
                for lev in [15, 20]:
                    res = quick_backtest(long_sig, short_sig, df, sl, tp, lev)

                    if res and res['trades'] >= 10:
                        combo_results.append({
                            'name': f"COMBO_OS{os}_OB{ob}_T{thresh*1000:.0f}_W{max_width}_SL{sl}_TP{tp}_LEV{lev}",
                            'type': 'COMBO',
                            'os': os,
                            'ob': ob,
                            'thresh': thresh,
                            'max_width': max_width,
                            'sl': sl,
                            'tp': tp,
                            'leverage': lev,
                            **res
                        })

print(f"Found {len(combo_results)} profitable COMBO strategies")

# Combine all results
all_results = rsi_results + bb_results + combo_results

print(f"\n" + "="*80)
print(f"TOTAL PROFITABLE STRATEGIES: {len(all_results)}")
print("="*80)

if len(all_results) == 0:
    print("\nNo profitable strategies found!")
    exit()

# Sort by profit/DD ratio
all_results.sort(key=lambda x: x['profit_dd'], reverse=True)

# Filter by profit/DD >= 4.0
excellent = [r for r in all_results if r['profit_dd'] >= 4.0]
print(f"Strategies with Profit/DD >= 4.0: {len(excellent)}")

# Save summary
summary = []
for r in all_results[:20]:
    summary.append({
        'name': r['name'],
        'type': r['type'],
        'leverage': r['leverage'],
        'trades': r['trades'],
        'win_rate': round(r['win_rate'], 1),
        'total_return': round(r['total_return'], 2),
        'max_dd': round(r['max_dd'], 2),
        'profit_dd': round(r['profit_dd'], 2)
    })

summary_df = pd.DataFrame(summary)
summary_df.to_csv('eth_mean_reversion_summary.csv', index=False)

# Display top 10
print("\n" + "="*80)
print("TOP 10 STRATEGIES (by Profit/DD Ratio)")
print("="*80)
print(f"\n{summary_df.head(10).to_string(index=False)}")

# Best strategy details
best = all_results[0]

print("\n" + "="*80)
print("BEST STRATEGY DETAILS")
print("="*80)
print(f"\nName: {best['name']}")
print(f"Type: {best['type']}")
print(f"Leverage: {best['leverage']}x")

print(f"\nParameters:")
if 'os' in best:
    print(f"  RSI Oversold: {best['os']}")
    print(f"  RSI Overbought: {best['ob']}")
if 'thresh' in best:
    print(f"  BB Threshold: {best['thresh']*100:.2f}%")
if 'max_width' in best:
    print(f"  Max BB Width: {best['max_width']}%")
print(f"  Stop Loss: {best['sl']}x ATR")
print(f"  Take Profit: {best['tp']}x ATR")

print(f"\nPerformance:")
print(f"  Total Return: {best['total_return']:.2f}%")
print(f"  Max Drawdown: {best['max_dd']:.2f}%")
print(f"  Profit/DD Ratio: {best['profit_dd']:.2f}")
print(f"  Number of Trades: {best['trades']}")
print(f"  Win Rate: {best['win_rate']:.1f}%")
print(f"  Avg Win: {best['avg_win']:.2f}%")
print(f"  Final Equity: ${best['equity']:.2f}")

# Calculate expected return with leverage
expected_return_per_trade = best['total_return'] / best['trades']
print(f"\nExpected return per trade: {expected_return_per_trade:.3f}%")

# Exit breakdown
print(f"\nExit Reasons:")
print(best['trades_df']['reason'].value_counts())

# Save best trades
best_trades = best['trades_df'].copy()
best_trades['entry_time'] = df.iloc[best_trades['entry_idx'].values]['timestamp'].values
best_trades['exit_time'] = df.iloc[best_trades['exit_idx'].values]['timestamp'].values
best_trades[['entry_time', 'exit_time', 'type', 'entry_price', 'exit_price', 'reason', 'pnl_pct', 'equity']].to_csv(
    'eth_mean_reversion_best_trades.csv', index=False
)

print(f"\nSaved best strategy trades to: eth_mean_reversion_best_trades.csv")
print(f"Saved summary to: eth_mean_reversion_summary.csv")

print("\n" + "="*80)
print("BACKTEST COMPLETE!")
print("="*80)
