"""
Test LONG and SHORT strategies in parallel on FARTCOIN
Goal: Hedge against prolonged trends in either direction
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def calculate_ema(df, span):
    return df['close'].ewm(span=span, adjust=False).mean()

def calculate_atr(df, period=14):
    high_low = df['high'] - df['low']
    high_close = (df['high'] - df['close'].shift()).abs()
    low_close = (df['low'] - df['close'].shift()).abs()
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    tr = ranges.max(axis=1)
    return tr.rolling(period).mean()

def calculate_rsi(df, period=14):
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def backtest_strategy(df, strategy_type='short', use_dynamic_sizing=True):
    """
    strategy_type: 'short', 'long', or 'both'
    """
    df = df.copy()

    # Calculate indicators
    df['ema_3'] = calculate_ema(df, 3)
    df['ema_15'] = calculate_ema(df, 15)
    df['momentum_7d'] = df['close'].pct_change(336) * 100
    df['atr'] = calculate_atr(df)
    df['atr_pct'] = (df['atr'] / df['close']) * 100
    df['rsi'] = calculate_rsi(df)

    # Filters for SHORT and LONG
    df['allow_short'] = (df['momentum_7d'] < 0) & (df['atr_pct'] < 6) & (df['rsi'] < 60)
    df['allow_long'] = (df['momentum_7d'] > 0) & (df['atr_pct'] < 6) & (df['rsi'] > 40)

    # Run backtest
    trades = []
    in_position = False
    position_type = None
    entry_price = 0
    entry_date = None
    entry_atr = 0
    stop_loss = 0
    take_profit = 0
    fee = 0.0001

    for i in range(1, len(df)):
        row = df.iloc[i]
        prev_row = df.iloc[i-1]

        if not in_position:
            # Check for SHORT entry
            if strategy_type in ['short', 'both']:
                if (row['ema_3'] < row['ema_15'] and
                    prev_row['ema_3'] >= prev_row['ema_15'] and
                    row['allow_short']):

                    in_position = True
                    position_type = 'SHORT'
                    entry_price = row['close']
                    entry_date = row['timestamp']
                    entry_atr = row['atr_pct']

                    # SHORT: Fixed 3% SL, Adaptive TP (3x ATR)
                    stop_loss = entry_price * 1.03
                    tp_ratio = min(max(entry_atr / 100 * 3.0, 0.04), 0.15)
                    take_profit = entry_price * (1 - tp_ratio)

            # Check for LONG entry (only if not already in SHORT)
            if not in_position and strategy_type in ['long', 'both']:
                if (row['ema_3'] > row['ema_15'] and
                    prev_row['ema_3'] <= prev_row['ema_15'] and
                    row['allow_long']):

                    in_position = True
                    position_type = 'LONG'
                    entry_price = row['close']
                    entry_date = row['timestamp']
                    entry_atr = row['atr_pct']

                    # LONG: Fixed 3% SL, Adaptive TP (3x ATR)
                    stop_loss = entry_price * 0.97  # 3% below for longs
                    tp_ratio = min(max(entry_atr / 100 * 3.0, 0.04), 0.15)
                    take_profit = entry_price * (1 + tp_ratio)  # Above for longs

        else:
            exit_type = None
            exit_price = None

            if position_type == 'SHORT':
                if row['high'] >= stop_loss:
                    exit_price = stop_loss
                    exit_type = 'SL'
                    pnl = (entry_price - stop_loss) / entry_price - fee
                elif row['low'] <= take_profit:
                    exit_price = take_profit
                    exit_type = 'TP'
                    pnl = (entry_price - take_profit) / entry_price - fee

            elif position_type == 'LONG':
                if row['low'] <= stop_loss:
                    exit_price = stop_loss
                    exit_type = 'SL'
                    pnl = (exit_price - entry_price) / entry_price - fee
                elif row['high'] >= take_profit:
                    exit_price = take_profit
                    exit_type = 'TP'
                    pnl = (exit_price - entry_price) / entry_price - fee

            if exit_type:
                trades.append({
                    'entry_date': entry_date,
                    'exit_date': row['timestamp'],
                    'pnl_pct': pnl * 100,
                    'exit_type': exit_type,
                    'position_type': position_type,
                    'win': pnl > 0
                })
                in_position = False
                position_type = None

    if len(trades) == 0:
        return None

    trades_df = pd.DataFrame(trades)
    trades_df = trades_df.sort_values('exit_date').reset_index(drop=True)

    # Calculate equity with position sizing
    equity = 1.0
    position_size = 1.0
    equity_curve = [equity]

    for _, trade in trades_df.iterrows():
        trade_pnl = trade['pnl_pct'] * position_size
        equity *= (1 + trade_pnl / 100)
        equity_curve.append(equity)

        if use_dynamic_sizing:
            if trade['pnl_pct'] > 0:
                position_size = min(position_size + 0.25, 2.0)
            else:
                position_size = max(position_size - 0.03, 0.5)

    # Calculate metrics
    equity_series = pd.Series(equity_curve)
    running_max = equity_series.expanding().max()
    drawdown = (equity_series - running_max) / running_max * 100
    max_dd = drawdown.min()
    total_return = (equity - 1) * 100

    winners = len(trades_df[trades_df['win']])
    win_rate = winners / len(trades_df) * 100

    # Count shorts and longs
    shorts = trades_df[trades_df['position_type'] == 'SHORT']
    longs = trades_df[trades_df['position_type'] == 'LONG']

    return {
        'trades': len(trades_df),
        'return': total_return,
        'max_dd': max_dd,
        'win_rate': win_rate,
        'final_equity': equity,
        'rr_ratio': total_return / abs(max_dd),
        'equity_curve': equity_curve,
        'avg_win': trades_df[trades_df['pnl_pct'] > 0]['pnl_pct'].mean() if winners > 0 else 0,
        'avg_loss': trades_df[trades_df['pnl_pct'] < 0]['pnl_pct'].mean() if len(trades_df) > winners else 0,
        'shorts': len(shorts),
        'shorts_wr': len(shorts[shorts['win']]) / len(shorts) * 100 if len(shorts) > 0 else 0,
        'longs': len(longs),
        'longs_wr': len(longs[longs['win']]) / len(longs) * 100 if len(longs) > 0 else 0,
        'trades_df': trades_df
    }

# Load data
df = pd.read_csv('fartcoin_30m_jan2025.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

print("="*100)
print("LONG + SHORT PARALLEL STRATEGY TEST - FARTCOIN (Last 11 months)")
print("="*100)
print(f"\nData Range: {df['timestamp'].min().strftime('%Y-%m-%d')} to {df['timestamp'].max().strftime('%Y-%m-%d')}")
print(f"Total Candles: {len(df)}")

# Test three scenarios
print("\n" + "="*100)
print("TESTING THREE SCENARIOS")
print("="*100)

# 1. SHORT only (our proven strategy)
print("\n1️⃣  SHORT ONLY (Baseline)")
short_only = backtest_strategy(df, strategy_type='short', use_dynamic_sizing=True)

# 2. LONG only (mirrored strategy)
print("2️⃣  LONG ONLY (Mirrored)")
long_only = backtest_strategy(df, strategy_type='long', use_dynamic_sizing=True)

# 3. BOTH (parallel hedged strategy)
print("3️⃣  LONG + SHORT PARALLEL (Hedged)")
both = backtest_strategy(df, strategy_type='both', use_dynamic_sizing=True)

# Results table
results = []

if short_only:
    results.append({
        'strategy': 'SHORT Only',
        'trades': short_only['trades'],
        'return': short_only['return'],
        'max_dd': short_only['max_dd'],
        'win_rate': short_only['win_rate'],
        'rr_ratio': short_only['rr_ratio'],
        'avg_win': short_only['avg_win'],
        'avg_loss': short_only['avg_loss'],
        'shorts': short_only['shorts'],
        'longs': 0
    })

if long_only:
    results.append({
        'strategy': 'LONG Only',
        'trades': long_only['trades'],
        'return': long_only['return'],
        'max_dd': long_only['max_dd'],
        'win_rate': long_only['win_rate'],
        'rr_ratio': long_only['rr_ratio'],
        'avg_win': long_only['avg_win'],
        'avg_loss': long_only['avg_loss'],
        'shorts': 0,
        'longs': long_only['longs']
    })

if both:
    results.append({
        'strategy': 'LONG + SHORT',
        'trades': both['trades'],
        'return': both['return'],
        'max_dd': both['max_dd'],
        'win_rate': both['win_rate'],
        'rr_ratio': both['rr_ratio'],
        'avg_win': both['avg_win'],
        'avg_loss': both['avg_loss'],
        'shorts': both['shorts'],
        'longs': both['longs']
    })

results_df = pd.DataFrame(results)

print("\n" + "="*100)
print("PERFORMANCE COMPARISON")
print("="*100)
print(f"\n{'Strategy':<18} {'Trades':<8} {'Shorts':<8} {'Longs':<8} {'Return':<12} {'Max DD':<12} {'R:R':<8} {'WR%':<8}")
print("-"*100)

for _, row in results_df.iterrows():
    print(f"{row['strategy']:<18} {row['trades']:<8.0f} {row['shorts']:<8.0f} {row['longs']:<8.0f} "
          f"{row['return']:<11.2f}% {row['max_dd']:<11.2f}% {row['rr_ratio']:<7.2f} {row['win_rate']:<7.1f}%")

print("\n" + "="*100)
print("DETAILED BREAKDOWN")
print("="*100)

for idx, (_, row) in enumerate(results_df.iterrows(), 1):
    print(f"\n{idx}. {row['strategy']}")
    print(f"   Total Trades: {row['trades']:.0f} ({row['shorts']:.0f} shorts, {row['longs']:.0f} longs)")
    print(f"   Return: {row['return']:.2f}%")
    print(f"   Max DD: {row['max_dd']:.2f}%")
    print(f"   R:R Ratio: {row['rr_ratio']:.2f}")
    print(f"   Win Rate: {row['win_rate']:.1f}%")
    print(f"   Avg Win/Loss: {row['avg_win']:.2f}% / {row['avg_loss']:.2f}%")

# Analyze BOTH strategy in detail
if both:
    print("\n" + "="*100)
    print("LONG + SHORT STRATEGY ANALYSIS")
    print("="*100)

    shorts_df = both['trades_df'][both['trades_df']['position_type'] == 'SHORT']
    longs_df = both['trades_df'][both['trades_df']['position_type'] == 'LONG']

    print(f"\n📊 SHORT Trades: {len(shorts_df)} ({both['shorts_wr']:.1f}% win rate)")
    if len(shorts_df) > 0:
        print(f"   Avg Win: {shorts_df[shorts_df['pnl_pct'] > 0]['pnl_pct'].mean():.2f}%")
        print(f"   Avg Loss: {shorts_df[shorts_df['pnl_pct'] < 0]['pnl_pct'].mean():.2f}%")

    print(f"\n📈 LONG Trades: {len(longs_df)} ({both['longs_wr']:.1f}% win rate)")
    if len(longs_df) > 0:
        print(f"   Avg Win: {longs_df[longs_df['pnl_pct'] > 0]['pnl_pct'].mean():.2f}%")
        print(f"   Avg Loss: {longs_df[longs_df['pnl_pct'] < 0]['pnl_pct'].mean():.2f}%")

# Visualization
fig = plt.figure(figsize=(20, 12))
gs = fig.add_gridspec(3, 2, height_ratios=[2, 1.5, 1])

ax1 = fig.add_subplot(gs[0, :])  # Equity curves
ax2 = fig.add_subplot(gs[1, 0])  # Drawdowns
ax3 = fig.add_subplot(gs[1, 1])  # Trade count by type
ax4 = fig.add_subplot(gs[2, :])  # Monthly comparison

colors = {'SHORT Only': '#C73E1D', 'LONG Only': '#6A994E', 'LONG + SHORT': '#2E86AB'}

# Plot 1: Equity Curves
for strategy, result in [('SHORT Only', short_only), ('LONG Only', long_only), ('LONG + SHORT', both)]:
    if result:
        ec = result['equity_curve']
        dates = pd.date_range(start=df['timestamp'].min(), periods=len(ec), freq='1D')
        ax1.plot(range(len(ec)), ec, linewidth=2.5, label=strategy,
                color=colors.get(strategy, 'gray'), alpha=0.9)

ax1.axhline(y=1, color='gray', linestyle='--', alpha=0.5)
ax1.set_ylabel('Equity Multiple', fontsize=13, fontweight='bold')
ax1.set_title('FARTCOIN: SHORT vs LONG vs BOTH Strategies (Last 11 Months)\n' +
              'Complete Optimized Stack: Filters + Dynamic Sizing + Adaptive TP',
              fontsize=15, fontweight='bold', pad=20)
ax1.legend(loc='upper left', fontsize=12)
ax1.grid(True, alpha=0.3)
ax1.set_xlabel('Trade Number', fontsize=11)

# Plot 2: Drawdown Comparison
for strategy, result in [('SHORT Only', short_only), ('LONG Only', long_only), ('LONG + SHORT', both)]:
    if result:
        ec = result['equity_curve']
        equity_series = pd.Series(ec)
        running_max = equity_series.expanding().max()
        drawdown = (equity_series - running_max) / running_max * 100
        ax2.plot(range(len(drawdown)), drawdown, linewidth=2,
                label=strategy, color=colors.get(strategy, 'gray'), alpha=0.8)

ax2.axhline(y=0, color='gray', linestyle='-', alpha=0.5)
ax2.set_ylabel('Drawdown %', fontsize=11, fontweight='bold')
ax2.set_title('Drawdown Comparison', fontsize=12, fontweight='bold')
ax2.legend(loc='lower left', fontsize=10)
ax2.grid(True, alpha=0.3)
ax2.set_xlabel('Trade Number', fontsize=11)

# Plot 3: Trade Count by Type
strategies = ['SHORT Only', 'LONG Only', 'LONG + SHORT']
short_counts = [short_only['shorts'] if short_only else 0,
                0,
                both['shorts'] if both else 0]
long_counts = [0,
               long_only['longs'] if long_only else 0,
               both['longs'] if both else 0]

x = np.arange(len(strategies))
width = 0.35

bars1 = ax3.bar(x - width/2, short_counts, width, label='SHORT Trades',
                color='#C73E1D', alpha=0.8)
bars2 = ax3.bar(x + width/2, long_counts, width, label='LONG Trades',
                color='#6A994E', alpha=0.8)

ax3.set_ylabel('Number of Trades', fontsize=11, fontweight='bold')
ax3.set_title('Trade Distribution', fontsize=12, fontweight='bold')
ax3.set_xticks(x)
ax3.set_xticklabels(strategies, rotation=15, ha='right')
ax3.legend(loc='upper left', fontsize=10)
ax3.grid(True, alpha=0.3, axis='y')

# Add value labels on bars
for bars in [bars1, bars2]:
    for bar in bars:
        height = bar.get_height()
        if height > 0:
            ax3.text(bar.get_x() + bar.get_width()/2., height,
                    f'{int(height)}',
                    ha='center', va='bottom', fontsize=9, fontweight='bold')

# Plot 4: Summary Table
ax4.axis('tight')
ax4.axis('off')

table_data = [['Strategy', 'Return', 'Max DD', 'R:R', 'Win Rate', 'Trades']]
for _, row in results_df.iterrows():
    table_data.append([
        row['strategy'],
        f"{row['return']:.1f}%",
        f"{row['max_dd']:.1f}%",
        f"{row['rr_ratio']:.2f}",
        f"{row['win_rate']:.1f}%",
        f"{row['trades']:.0f}"
    ])

table = ax4.table(cellText=table_data, cellLoc='center', loc='center',
                 colWidths=[0.2, 0.15, 0.15, 0.15, 0.15, 0.15])
table.auto_set_font_size(False)
table.set_fontsize(11)
table.scale(1, 2.5)

# Style header
for i in range(6):
    table[(0, i)].set_facecolor('#2E86AB')
    table[(0, i)].set_text_props(weight='bold', color='white')

# Color rows
for i, strategy in enumerate(['SHORT Only', 'LONG Only', 'LONG + SHORT'], 1):
    for j in range(6):
        table[(i, j)].set_facecolor(colors.get(strategy, 'gray'))
        table[(i, j)].set_alpha(0.3)

plt.tight_layout()
plt.savefig('results/long_short_parallel_comparison.png', dpi=300, bbox_inches='tight')
print("\n✓ Saved visualization to results/long_short_parallel_comparison.png")

# Save results
results_df.to_csv('results/long_short_parallel_results.csv', index=False)
print("✓ Saved results to results/long_short_parallel_results.csv")

print("\n" + "="*100)
print("FINAL VERDICT")
print("="*100)

best = results_df.sort_values('rr_ratio', ascending=False).iloc[0]
print(f"\n🏆 Best Strategy by R:R: {best['strategy']}")
print(f"   Return: {best['return']:.2f}%")
print(f"   Max DD: {best['max_dd']:.2f}%")
print(f"   R:R Ratio: {best['rr_ratio']:.2f}")

best_return = results_df.sort_values('return', ascending=False).iloc[0]
print(f"\n💰 Best Strategy by Return: {best_return['strategy']}")
print(f"   Return: {best_return['return']:.2f}%")

if both:
    improvement_over_short = both['return'] - short_only['return']
    dd_change = both['max_dd'] - short_only['max_dd']

    print(f"\n📊 LONG + SHORT vs SHORT Only:")
    print(f"   Return: {improvement_over_short:+.2f}%")
    print(f"   Max DD: {dd_change:+.2f}%")

    if improvement_over_short > 50 and dd_change > -10:
        print(f"\n✅ PARALLEL STRATEGY IS BETTER - adds significant returns with manageable DD increase")
    elif improvement_over_short > 0:
        print(f"\n⚠️  PARALLEL STRATEGY improves returns but needs DD evaluation")
    else:
        print(f"\n❌ SHORT ONLY IS BETTER - parallel strategy doesn't add value")

print("\n" + "="*100)
