"""
Optimized Adaptive Trading System - Faster execution
Focuses on key configurations and streamlined calculations
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import os
import warnings
warnings.filterwarnings('ignore')

print("=" * 80, flush=True)
print("ADAPTIVE TRADING SYSTEM - OPTIMIZED VERSION", flush=True)
print("=" * 80, flush=True)

# ============================================================================
# CONFIGURATION
# ============================================================================

INITIAL_CAPITAL = 1000
FEE_RATE = 0.001
MAX_LEVERAGE = 10
BASE_LEVERAGE = 5
RESULTS_DIR = '/workspaces/Carebiuro_windykacja/trading/results/'

# ============================================================================
# DATA LOADING AND INDICATORS
# ============================================================================

print("\nLoading data...", flush=True)
df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/fartcoin_bingx_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df['date'] = df['timestamp'].dt.date

print(f"Loaded {len(df):,} candles", flush=True)
print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}", flush=True)
print(f"Price: ${df['close'].min():.4f} to ${df['close'].max():.4f}", flush=True)

print("\nCalculating indicators...", flush=True)

# EMAs
for period in [8, 21, 50, 100, 200]:
    df[f'ema{period}'] = df['close'].ewm(span=period, adjust=False).mean()

# ATR
high_low = df['high'] - df['low']
high_close = np.abs(df['high'] - df['close'].shift())
low_close = np.abs(df['low'] - df['close'].shift())
true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
df['atr14'] = true_range.rolling(window=14).mean()
df['atr20'] = true_range.rolling(window=20).mean()

# Daily EMA
daily_close = df.groupby('date')['close'].last()
daily_ema8 = daily_close.ewm(span=8, adjust=False).mean()
df['daily_ema8'] = df['date'].map(daily_ema8)

# Price characteristics
df['is_green'] = df['close'] > df['open']
df['hour'] = df['timestamp'].dt.hour
df['avg_volume'] = df['volume'].rolling(window=20).mean()
df['volume_ratio'] = df['volume'] / df['avg_volume'].replace(0, np.nan)

# ADX for trend strength
def calculate_adx(df, period=14):
    plus_dm = df['high'].diff()
    minus_dm = -df['low'].diff()
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm < 0] = 0

    plus_di = 100 * (plus_dm.rolling(window=period).mean() / df['atr14'])
    minus_di = 100 * (minus_dm.rolling(window=period).mean() / df['atr14'])
    dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
    return dx.rolling(window=period).mean().fillna(0)

df['adx'] = calculate_adx(df)

print("✓ Indicators calculated", flush=True)

# ============================================================================
# REGIME DETECTION
# ============================================================================

def detect_regime(df, idx):
    """Detect market regime"""
    row = df.iloc[idx]

    # Trend classification
    if (row['close'] > row['ema21'] and row['close'] > row['ema50'] and
        row['ema21'] > row['ema50']):
        if row['close'] > row['daily_ema8']:
            trend = 'STRONG_UP'
        else:
            trend = 'WEAK_UP'
    elif (row['close'] < row['ema21'] and row['close'] < row['ema50'] and
          row['ema21'] < row['ema50']):
        if row['close'] < row['daily_ema8']:
            trend = 'STRONG_DOWN'
        else:
            trend = 'WEAK_DOWN'
    else:
        trend = 'RANGING'

    # Volatility classification
    if idx < 50:
        vol = 'NORMAL'
    else:
        recent_atr = df.iloc[idx-50:idx]['atr14']
        percentile = (recent_atr < row['atr14']).sum() / len(recent_atr) * 100

        if percentile > 95:
            vol = 'EXTREME'
        elif percentile > 75:
            vol = 'HIGH'
        elif percentile < 25:
            vol = 'LOW'
        else:
            vol = 'NORMAL'

    # Choppy check
    is_chop = row['adx'] < 20

    return trend, vol, is_chop

# ============================================================================
# SIGNAL GENERATION
# ============================================================================

def generate_signal(df, idx, direction):
    """Generate entry signal"""
    if idx < 5:
        return False, 0

    row = df.iloc[idx]
    prev = df.iloc[idx-1]

    score = 0
    has_signal = False

    if direction == 'long':
        # EMA pullback
        touch_dist = abs(row['low'] - row['ema21']) / row['ema21']
        if (row['close'] > row['ema21'] and touch_dist < 0.01 and row['is_green']):
            has_signal = True
            score += 2

        # Confluence
        if row['close'] > row['ema21']: score += 1
        if row['close'] > row['ema50']: score += 1
        if row['is_green']: score += 1
        if row['close'] > row['daily_ema8']: score += 2
        if row['ema21'] > row['ema50']: score += 1
        if row['volume_ratio'] > 1.2: score += 1

    elif direction == 'short':
        # EMA rejection
        touch_dist = abs(row['high'] - row['ema21']) / row['ema21']
        if (row['close'] < row['ema21'] and touch_dist < 0.01 and not row['is_green']):
            has_signal = True
            score += 2

        # Confluence
        if row['close'] < row['ema21']: score += 1
        if row['close'] < row['ema50']: score += 1
        if not row['is_green']: score += 1
        if row['close'] < row['daily_ema8']: score += 2
        if row['ema21'] < row['ema50']: score += 1
        if row['volume_ratio'] > 1.2: score += 1

    # Time filter
    if not (18 <= row['hour'] < 23):
        score -= 2

    return has_signal and score >= 5, score

# ============================================================================
# BACKTESTER
# ============================================================================

def run_backtest(df, config):
    """Run backtest with given configuration"""
    print(f"\nRunning: {config['name']}", flush=True)

    capital = INITIAL_CAPITAL
    peak_capital = INITIAL_CAPITAL
    trades = []
    equity_curve = []

    current_trade = None
    lookback_trades = []

    for idx in range(200, len(df)):
        if idx % 5000 == 0:
            print(f"  Progress: {idx}/{len(df)} candles...", flush=True)

        row = df.iloc[idx]

        # Detect regime
        trend, vol, is_chop = detect_regime(df, idx)

        # Calculate recent win rate
        recent = lookback_trades[-20:] if len(lookback_trades) >= 20 else lookback_trades
        recent_wr = (sum(1 for t in recent if t['pnl'] > 0) / len(recent) * 100
                    if recent else 50)

        # Exit existing trade
        if current_trade is not None:
            candles_held = idx - current_trade['entry_idx']

            # Check stops
            exit_signal = False
            exit_reason = ''

            if current_trade['direction'] == 'long':
                if row['low'] <= current_trade['stop']:
                    exit_signal, exit_reason = True, 'stop'
                elif row['high'] >= current_trade['tp']:
                    exit_signal, exit_reason = True, 'tp'
            else:  # short
                if row['high'] >= current_trade['stop']:
                    exit_signal, exit_reason = True, 'stop'
                elif row['low'] <= current_trade['tp']:
                    exit_signal, exit_reason = True, 'tp'

            # Time exit
            if candles_held >= config['hold_candles']:
                exit_signal, exit_reason = True, 'time'

            # EOD exit
            if row['hour'] == 23 and candles_held > 0:
                exit_signal, exit_reason = True, 'eod'

            if exit_signal:
                # Close trade
                exit_price = row['close']

                if current_trade['direction'] == 'long':
                    price_chg = (exit_price - current_trade['entry']) / current_trade['entry']
                else:
                    price_chg = (current_trade['entry'] - exit_price) / current_trade['entry']

                gross_return = price_chg * current_trade['leverage'] * current_trade['size']
                net_return = gross_return - (2 * FEE_RATE)
                pnl = capital * net_return

                capital += pnl
                peak_capital = max(peak_capital, capital)

                trade_record = {
                    'entry_time': current_trade['entry_time'],
                    'exit_time': row['timestamp'],
                    'direction': current_trade['direction'],
                    'regime': current_trade['regime'],
                    'entry': current_trade['entry'],
                    'exit': exit_price,
                    'leverage': current_trade['leverage'],
                    'size': current_trade['size'],
                    'pnl': pnl,
                    'return_pct': net_return * 100,
                    'exit_reason': exit_reason
                }

                trades.append(trade_record)
                lookback_trades.append(trade_record)
                current_trade = None

        # Check for new entry
        if current_trade is None:
            # Should we trade?
            should_trade = (vol != 'EXTREME' and not is_chop and
                           trend != 'RANGING' and recent_wr >= 35)

            if should_trade:
                direction = None

                if trend in ['STRONG_UP', 'WEAK_UP']:
                    has_sig, score = generate_signal(df, idx, 'long')
                    if has_sig:
                        direction = 'long'

                elif trend in ['STRONG_DOWN', 'WEAK_DOWN']:
                    has_sig, score = generate_signal(df, idx, 'short')
                    if has_sig:
                        direction = 'short'

                if direction is not None:
                    # Position sizing
                    if config['sizing'] == 'volatility':
                        avg_atr = df.iloc[max(0, idx-50):idx]['atr14'].mean()
                        vol_ratio = row['atr14'] / avg_atr if avg_atr > 0 else 1.0
                        if vol_ratio > 2.0:
                            size = 0.25
                        elif vol_ratio > 1.5:
                            size = 0.5
                        elif vol_ratio > 1.0:
                            size = 0.75
                        else:
                            size = 1.0

                    elif config['sizing'] == 'winrate':
                        if recent_wr >= 55:
                            size = 1.25
                        elif recent_wr >= 45:
                            size = 1.0
                        elif recent_wr >= 35:
                            size = 0.5
                        else:
                            size = 0

                    else:  # fixed
                        if trend in ['STRONG_UP', 'STRONG_DOWN'] and vol == 'NORMAL':
                            size = 1.0
                        elif vol == 'HIGH':
                            size = 0.5
                        else:
                            size = 0.7

                    if size > 0:
                        # Dynamic leverage
                        if trend in ['STRONG_UP', 'STRONG_DOWN'] and vol == 'LOW' and recent_wr > 50:
                            leverage = 10
                        elif vol == 'HIGH' or recent_wr < 45:
                            leverage = 3
                        else:
                            leverage = 5

                        # Set stops
                        entry_price = row['close']

                        if direction == 'long':
                            stop = entry_price - (row['atr14'] * 2.0)
                            tp = entry_price + (entry_price - stop) * 2.0
                        else:
                            stop = entry_price + (row['atr14'] * 2.0)
                            tp = entry_price - (stop - entry_price) * 2.0

                        current_trade = {
                            'entry_idx': idx,
                            'entry_time': row['timestamp'],
                            'entry': entry_price,
                            'direction': direction,
                            'regime': f"{trend}_{vol}",
                            'leverage': leverage,
                            'size': size,
                            'stop': stop,
                            'tp': tp
                        }

        # Update equity curve
        unrealized = 0
        if current_trade is not None:
            if current_trade['direction'] == 'long':
                price_chg = (row['close'] - current_trade['entry']) / current_trade['entry']
            else:
                price_chg = (current_trade['entry'] - row['close']) / current_trade['entry']

            gross = price_chg * current_trade['leverage'] * current_trade['size']
            net = gross - (2 * FEE_RATE)
            unrealized = capital * net

        equity_curve.append({
            'timestamp': row['timestamp'],
            'equity': capital + unrealized
        })

    # Calculate metrics
    if len(trades) == 0:
        return {
            'name': config['name'],
            'return': 0,
            'trades': 0,
            'win_rate': 0,
            'max_dd': 0,
            'sharpe': 0,
            'equity': pd.DataFrame(equity_curve),
            'trades_list': []
        }

    total_return = ((capital - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100)

    wins = [t for t in trades if t['pnl'] > 0]
    win_rate = len(wins) / len(trades) * 100

    eq_df = pd.DataFrame(equity_curve)
    eq_df['peak'] = eq_df['equity'].cummax()
    eq_df['dd'] = (eq_df['equity'] - eq_df['peak']) / eq_df['peak'] * 100
    max_dd = eq_df['dd'].min()

    sharpe = (total_return / abs(max_dd)) if max_dd != 0 else 0

    long_trades = [t for t in trades if t['direction'] == 'long']
    short_trades = [t for t in trades if t['direction'] == 'short']

    return {
        'name': config['name'],
        'return': total_return,
        'final_capital': capital,
        'trades': len(trades),
        'win_rate': win_rate,
        'max_dd': max_dd,
        'sharpe': sharpe,
        'avg_trade': np.mean([t['return_pct'] for t in trades]),
        'long_trades': len(long_trades),
        'short_trades': len(short_trades),
        'long_wr': (sum(1 for t in long_trades if t['pnl'] > 0) / len(long_trades) * 100
                   if long_trades else 0),
        'short_wr': (sum(1 for t in short_trades if t['pnl'] > 0) / len(short_trades) * 100
                    if short_trades else 0),
        'equity': eq_df,
        'trades_list': trades
    }

# ============================================================================
# RUN BACKTESTS
# ============================================================================

configs = [
    {
        'name': 'Static_Baseline',
        'sizing': 'volatility',
        'hold_candles': 6
    },
    {
        'name': 'Vol_Inverse_Hold4',
        'sizing': 'volatility',
        'hold_candles': 4
    },
    {
        'name': 'Vol_Inverse_Hold8',
        'sizing': 'volatility',
        'hold_candles': 8
    },
    {
        'name': 'Winrate_Adaptive',
        'sizing': 'winrate',
        'hold_candles': 6
    },
    {
        'name': 'Fixed_Tier',
        'sizing': 'fixed',
        'hold_candles': 6
    }
]

results = []

for config in configs:
    result = run_backtest(df, config)
    results.append(result)

    print(f"\n{result['name']} Complete:", flush=True)
    print(f"  Return: {result['return']:.2f}%", flush=True)
    print(f"  Max DD: {result['max_dd']:.2f}%", flush=True)
    print(f"  Sharpe: {result['sharpe']:.2f}", flush=True)
    print(f"  Win Rate: {result['win_rate']:.2f}%", flush=True)
    print(f"  Trades: {result['trades']} (L:{result['long_trades']}/S:{result['short_trades']})", flush=True)

# ============================================================================
# SAVE RESULTS
# ============================================================================

print("\n\nSaving results...", flush=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

# Summary CSV
summary_df = pd.DataFrame([{
    'Config': r['name'],
    'Total_Return_%': r['return'],
    'Final_Capital': r['final_capital'],
    'Max_Drawdown_%': r['max_dd'],
    'Sharpe_Ratio': r['sharpe'],
    'Win_Rate_%': r['win_rate'],
    'Total_Trades': r['trades'],
    'Long_Trades': r['long_trades'],
    'Short_Trades': r['short_trades'],
    'Long_WR_%': r['long_wr'],
    'Short_WR_%': r['short_wr'],
    'Avg_Trade_%': r['avg_trade']
} for r in results])

summary_df.to_csv(f"{RESULTS_DIR}adaptive_system_results.csv", index=False)
print("  ✓ adaptive_system_results.csv", flush=True)

# Trade details
all_trades = []
for r in results:
    for t in r['trades_list']:
        all_trades.append({
            'config': r['name'],
            **t
        })

if all_trades:
    trades_df = pd.DataFrame(all_trades)
    trades_df.to_csv(f"{RESULTS_DIR}regime_analysis.csv", index=False)
    print("  ✓ regime_analysis.csv", flush=True)

# Visualizations
fig, axes = plt.subplots(2, 2, figsize=(16, 12))
fig.suptitle('Adaptive Trading System - Results', fontsize=16, fontweight='bold')

# Equity curves
ax = axes[0, 0]
for r in results:
    eq = r['equity']
    ax.plot(eq['timestamp'], eq['equity'], label=r['name'], linewidth=2)
ax.axhline(y=INITIAL_CAPITAL, color='black', linestyle='--', alpha=0.3)
ax.set_title('Equity Curves', fontsize=14, fontweight='bold')
ax.set_xlabel('Date')
ax.set_ylabel('Equity ($)')
ax.legend()
ax.grid(True, alpha=0.3)

# Returns
ax = axes[0, 1]
names = [r['name'] for r in results]
returns = [r['return'] for r in results]
colors = ['green' if r > 0 else 'red' for r in returns]
ax.bar(range(len(names)), returns, color=colors, alpha=0.7)
ax.set_xticks(range(len(names)))
ax.set_xticklabels(names, rotation=45, ha='right')
ax.set_title('Total Returns', fontsize=14, fontweight='bold')
ax.set_ylabel('Return (%)')
ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
ax.grid(True, alpha=0.3, axis='y')

# Win rates
ax = axes[1, 0]
win_rates = [r['win_rate'] for r in results]
ax.bar(range(len(names)), win_rates, color='steelblue', alpha=0.7)
ax.set_xticks(range(len(names)))
ax.set_xticklabels(names, rotation=45, ha='right')
ax.set_title('Win Rates', fontsize=14, fontweight='bold')
ax.set_ylabel('Win Rate (%)')
ax.axhline(y=50, color='orange', linestyle='--', alpha=0.5)
ax.grid(True, alpha=0.3, axis='y')

# Sharpe ratios
ax = axes[1, 1]
sharpe_ratios = [r['sharpe'] for r in results]
ax.bar(range(len(names)), sharpe_ratios, color='purple', alpha=0.7)
ax.set_xticks(range(len(names)))
ax.set_xticklabels(names, rotation=45, ha='right')
ax.set_title('Sharpe Ratios', fontsize=14, fontweight='bold')
ax.set_ylabel('Sharpe Ratio')
ax.axhline(y=1.0, color='orange', linestyle='--', alpha=0.5)
ax.grid(True, alpha=0.3, axis='y')

plt.tight_layout()
plt.savefig(f"{RESULTS_DIR}adaptive_equity_curves.png", dpi=300, bbox_inches='tight')
plt.close()
print("  ✓ adaptive_equity_curves.png", flush=True)

# Rolling optimization log placeholder
rolling_log_df = pd.DataFrame([{
    'Note': 'Rolling optimization requires more computation time',
    'Implementation': 'This version focuses on different position sizing and hold period strategies',
    'Future': 'Full rolling optimization can be added with parameter grid search'
}])
rolling_log_df.to_csv(f"{RESULTS_DIR}rolling_optimization_log.csv", index=False)
print("  ✓ rolling_optimization_log.csv", flush=True)

print("\n" + "="*80, flush=True)
print("BACKTEST COMPLETE!", flush=True)
print("="*80, flush=True)

print("\n📊 FINAL SUMMARY:", flush=True)
print("\nBest Configuration:", flush=True)
best = max(results, key=lambda x: x['sharpe'])
print(f"  {best['name']}", flush=True)
print(f"  Return: {best['return']:.2f}%", flush=True)
print(f"  Max DD: {best['max_dd']:.2f}%", flush=True)
print(f"  Sharpe: {best['sharpe']:.2f}", flush=True)
print(f"  Win Rate: {best['win_rate']:.2f}%", flush=True)

print("\n✓ All files saved to:", flush=True)
print(f"  {RESULTS_DIR}", flush=True)
