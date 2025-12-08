"""
FARTCOIN Adaptive Strategy - FIXED VERSION
Fixed stop loss placement bug - stops now guaranteed to be on correct side
"""

import pandas as pd
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt

# Load data
data = pd.read_csv('fartcoin_5m_max.csv')
data['timestamp'] = pd.to_datetime(data['timestamp'])

print("="*80)
print("FARTCOIN ADAPTIVE STRATEGY - FIXED STOPS")
print("="*80)
print(f"\nData: {len(data)} candles from {data['timestamp'].min()} to {data['timestamp'].max()}")

# Calculate indicators
data['ema_20'] = data['close'].ewm(span=20).mean()
data['ema_50'] = data['close'].ewm(span=50).mean()

delta = data['close'].diff()
gain = (delta.where(delta > 0, 0)).rolling(14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
rs = gain / loss
data['rsi'] = 100 - (100 / (1 + rs))

data['bb_mid'] = data['close'].rolling(20).mean()
bb_std = data['close'].rolling(20).std()
data['bb_upper'] = data['bb_mid'] + 2 * bb_std
data['bb_lower'] = data['bb_mid'] - 2 * bb_std

high_low = data['high'] - data['low']
high_close = (data['high'] - data['close'].shift()).abs()
low_close = (data['low'] - data['close'].shift()).abs()
ranges = pd.concat([high_low, high_close, low_close], axis=1)
tr = ranges.max(axis=1)
data['atr'] = tr.rolling(14).mean()

data['volume_ma'] = data['volume'].rolling(50).mean()

# Run FIXED strategy
print("\nRunning backtest with FIXED stop loss logic...")

capital = 10000
position = None
trades = []
equity = []

for idx in range(200, len(data)):
    row = data.iloc[idx]

    # Track equity
    if position is None:
        equity.append({'timestamp': row['timestamp'], 'equity': capital})

    # Exit logic
    if position is not None:
        exit_price = None
        exit_reason = None

        # Check stops/targets
        if position['direction'] == 'LONG':
            if row['low'] <= position['sl']:
                exit_price = position['sl']
                exit_reason = 'STOP'
            elif row['high'] >= position['tp']:
                exit_price = position['tp']
                exit_reason = 'TARGET'
            elif idx - position['entry_idx'] >= 50:
                exit_price = row['close']
                exit_reason = 'TIME'
        else:  # SHORT
            if row['high'] >= position['sl']:
                exit_price = position['sl']
                exit_reason = 'STOP'
            elif row['low'] <= position['tp']:
                exit_price = position['tp']
                exit_reason = 'TARGET'
            elif idx - position['entry_idx'] >= 50:
                exit_price = row['close']
                exit_reason = 'TIME'

        if exit_price is not None:
            if position['direction'] == 'LONG':
                pnl_pct = (exit_price / position['entry_price'] - 1) * 100
            else:
                pnl_pct = (position['entry_price'] / exit_price - 1) * 100

            # 20% position size
            pnl_usd = capital * (pnl_pct / 100) * 0.20
            capital += pnl_usd

            trades.append({
                'entry_time': position['entry_time'],
                'exit_time': row['timestamp'],
                'direction': position['direction'],
                'entry_price': position['entry_price'],
                'exit_price': exit_price,
                'pnl_pct': pnl_pct,
                'pnl_usd': pnl_usd,
                'exit_reason': exit_reason,
                'strategy': position['strategy']
            })

            position = None

    # Entry logic - FIXED STOP PLACEMENT
    if position is None:
        # BB Bounce LONG
        if (row['low'] <= row['bb_lower'] * 1.003 and
            row['close'] > row['open'] and
            row['rsi'] < 45 and
            row['volume'] > row['volume_ma'] * 0.3):

            entry = row['close']
            # FIXED: Use entry price as reference, ensure SL is BELOW
            sl_distance = entry * 0.015  # 1.5% stop loss
            stop_loss = entry - sl_distance
            take_profit = row['bb_mid']

            # Ensure TP is above entry for LONG
            if take_profit <= entry:
                take_profit = entry * 1.02

            position = {
                'entry_time': row['timestamp'],
                'entry_idx': idx,
                'entry_price': entry,
                'sl': stop_loss,
                'tp': take_profit,
                'direction': 'LONG',
                'strategy': 'BB_BOUNCE_LONG'
            }

        # Mean Rev SHORT
        elif (row['high'] >= row['bb_upper'] * 0.997 and
              row['close'] < row['open'] and
              row['rsi'] > 65):

            entry = row['close']
            # FIXED: Use entry price as reference, ensure SL is ABOVE
            sl_distance = entry * 0.015  # 1.5% stop loss
            stop_loss = entry + sl_distance
            take_profit = row['bb_mid']

            # Ensure TP is below entry for SHORT
            if take_profit >= entry:
                take_profit = entry * 0.98

            position = {
                'entry_time': row['timestamp'],
                'entry_idx': idx,
                'entry_price': entry,
                'sl': stop_loss,
                'tp': take_profit,
                'direction': 'SHORT',
                'strategy': 'MEAN_REV_SHORT'
            }

        # EMA Pullback LONG
        elif (row['ema_20'] > row['ema_50'] and
              row['close'] < row['ema_20'] and
              row['close'] > row['ema_50'] and
              40 < row['rsi'] < 65):

            entry = row['close']
            # FIXED: Use EMA50 as support, but ensure SL is BELOW entry
            sl_candidate = row['ema_50'] * 0.995
            stop_loss = min(sl_candidate, entry * 0.985)  # Ensure it's below entry
            take_profit = entry * 1.015

            position = {
                'entry_time': row['timestamp'],
                'entry_idx': idx,
                'entry_price': entry,
                'sl': stop_loss,
                'tp': take_profit,
                'direction': 'LONG',
                'strategy': 'EMA_PB_LONG'
            }

# Results
trades_df = pd.DataFrame(trades)
equity_df = pd.DataFrame(equity)

print("\n" + "="*80)
print("FIXED RESULTS")
print("="*80)

if len(trades_df) > 0:
    total_return = (capital - 10000) / 10000 * 100
    wins = trades_df[trades_df['pnl_pct'] > 0]
    win_rate = len(wins) / len(trades_df) * 100

    equity_df['running_max'] = equity_df['equity'].expanding().max()
    equity_df['dd'] = (equity_df['equity'] - equity_df['running_max']) / equity_df['running_max'] * 100
    max_dd = equity_df['dd'].min()

    print(f"Total Return: {total_return:.2f}%")
    print(f"Final Capital: ${capital:.2f}")
    print(f"Total Trades: {len(trades_df)}")
    print(f"Win Rate: {win_rate:.2f}%")
    print(f"Avg Win: {wins['pnl_pct'].mean():.2f}%")
    print(f"Avg Loss: {trades_df[trades_df['pnl_pct']<0]['pnl_pct'].mean():.2f}%")
    print(f"Max Drawdown: {max_dd:.2f}%")

    # Verify no profitable stops
    profitable_stops = trades_df[(trades_df['exit_reason'] == 'STOP') & (trades_df['pnl_pct'] > 0)]
    print(f"\n✓ Profitable STOP exits: {len(profitable_stops)} (should be 0)")

    print("\n" + "="*80)
    print("STRATEGY BREAKDOWN")
    print("="*80)
    for strat in trades_df['strategy'].unique():
        strat_trades = trades_df[trades_df['strategy'] == strat]
        strat_wins = strat_trades[strat_trades['pnl_pct'] > 0]

        # Calculate R:R
        wins_strat = strat_trades[strat_trades['pnl_pct'] > 0]
        losses_strat = strat_trades[strat_trades['pnl_pct'] < 0]
        avg_win = wins_strat['pnl_pct'].mean() if len(wins_strat) > 0 else 0
        avg_loss = abs(losses_strat['pnl_pct'].mean()) if len(losses_strat) > 0 else 0
        rr = avg_win / avg_loss if avg_loss > 0 else 0

        print(f"\n{strat}:")
        print(f"  Trades: {len(strat_trades)}")
        print(f"  Win Rate: {len(strat_wins)/len(strat_trades)*100:.1f}%")
        print(f"  Avg Win: {avg_win:.2f}% | Avg Loss: {avg_loss:.2f}%")
        print(f"  R:R: {rr:.2f}")
        print(f"  Total P&L: {strat_trades['pnl_pct'].sum():.2f}%")

    # Compare to buggy version
    print("\n" + "="*80)
    print("COMPARISON: BUGGY vs FIXED")
    print("="*80)
    print(f"Buggy:  128.26% return, -6.27% DD, 1678 trades")
    print(f"Fixed:  {total_return:.2f}% return, {max_dd:.2f}% DD, {len(trades_df)} trades")
    print(f"Impact: {total_return - 128.26:+.2f}% return, {max_dd - (-6.27):.2f}% DD change")

    # Save
    trades_df.to_csv('./results/adaptive_5m_fixed_results.csv', index=False)

    # Plot
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(16, 12))

    ax1.plot(equity_df['timestamp'], equity_df['equity'], 'b-', linewidth=2)
    ax1.axhline(10000, color='gray', linestyle='--', alpha=0.5)
    ax1.set_title(f'FIXED Equity Curve - Return: {total_return:.2f}%', fontsize=14, fontweight='bold')
    ax1.set_ylabel('Capital ($)')
    ax1.grid(True, alpha=0.3)

    ax2.fill_between(equity_df['timestamp'], equity_df['dd'], 0, color='red', alpha=0.3)
    ax2.plot(equity_df['timestamp'], equity_df['dd'], 'r-', linewidth=1)
    ax2.axhline(-30, color='red', linestyle='--', alpha=0.7, label='30% Limit')
    ax2.set_title(f'Drawdown - Max: {max_dd:.2f}%', fontsize=14, fontweight='bold')
    ax2.set_ylabel('Drawdown %')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    ax3.plot(data['timestamp'], data['close'], 'k-', linewidth=1, alpha=0.5)
    longs = trades_df[trades_df['direction'] == 'LONG']
    shorts = trades_df[trades_df['direction'] == 'SHORT']
    long_wins = longs[longs['pnl_pct'] > 0]
    long_loss = longs[longs['pnl_pct'] < 0]
    short_wins = shorts[shorts['pnl_pct'] > 0]
    short_loss = shorts[shorts['pnl_pct'] < 0]

    if len(long_wins) > 0:
        ax3.scatter(pd.to_datetime(long_wins['entry_time']), long_wins['entry_price'],
                   c='green', marker='^', s=80, alpha=0.8, label='LONG Win')
    if len(long_loss) > 0:
        ax3.scatter(pd.to_datetime(long_loss['entry_time']), long_loss['entry_price'],
                   c='lightgreen', marker='^', s=50, alpha=0.5, label='LONG Loss')
    if len(short_wins) > 0:
        ax3.scatter(pd.to_datetime(short_wins['entry_time']), short_wins['entry_price'],
                   c='red', marker='v', s=80, alpha=0.8, label='SHORT Win')
    if len(short_loss) > 0:
        ax3.scatter(pd.to_datetime(short_loss['entry_time']), short_loss['entry_price'],
                   c='pink', marker='v', s=50, alpha=0.5, label='SHORT Loss')

    ax3.set_title('Price with Trades', fontsize=14, fontweight='bold')
    ax3.set_xlabel('Time')
    ax3.set_ylabel('Price')
    ax3.legend(loc='upper right', fontsize=8)
    ax3.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('./results/adaptive_5m_fixed_equity.png', dpi=150, bbox_inches='tight')
    print("\n✓ Saved fixed results to ./results/")

    # Analysis
    analysis = f"""# FARTCOIN Adaptive Strategy - FIXED VERSION (Accurate)

## Performance Summary

- **Period**: {data['timestamp'].min()} to {data['timestamp'].max()}
- **Initial Capital**: $10,000
- **Final Capital**: ${capital:.2f}
- **Total Return**: {total_return:.2f}%
- **Max Drawdown**: {max_dd:.2f}%

## Trade Statistics

- **Total Trades**: {len(trades_df)}
- **Win Rate**: {win_rate:.2f}%
- **Average Win**: {wins['pnl_pct'].mean():.2f}%
- **Average Loss**: {trades_df[trades_df['pnl_pct']<0]['pnl_pct'].mean():.2f}%

## Strategy Breakdown

"""

    for strat in trades_df['strategy'].unique():
        strat_trades = trades_df[trades_df['strategy'] == strat]
        strat_wins = strat_trades[strat_trades['pnl_pct'] > 0]
        wins_strat = strat_trades[strat_trades['pnl_pct'] > 0]
        losses_strat = strat_trades[strat_trades['pnl_pct'] < 0]
        avg_win = wins_strat['pnl_pct'].mean() if len(wins_strat) > 0 else 0
        avg_loss = abs(losses_strat['pnl_pct'].mean()) if len(losses_strat) > 0 else 0
        rr = avg_win / avg_loss if avg_loss > 0 else 0

        analysis += f"""
### {strat}
- Trades: {len(strat_trades)}
- Win Rate: {len(strat_wins)/len(strat_trades)*100:.1f}%
- Avg Win: {avg_win:.2f}% | Avg Loss: {avg_loss:.2f}%
- R:R Ratio: {rr:.2f}
- Total P&L: {strat_trades['pnl_pct'].sum():.2f}%
"""

    analysis += f"""
## Bug Fix Details

**Issue**: Stop losses were placed using Bollinger Band levels as reference, which caused stops to be on the wrong side when entry price was beyond the bands.

**Fix**:
1. All stops now use entry price as reference point
2. LONG stops: entry - 1.5% (guaranteed below entry)
3. SHORT stops: entry + 1.5% (guaranteed above entry)
4. Target prices validated to be in profit direction

**Verification**: Profitable STOP exits = {len(profitable_stops)} (must be 0)

## Impact of Bug Fix

| Metric | Buggy | Fixed | Change |
|--------|-------|-------|--------|
| Return | 128.26% | {total_return:.2f}% | {total_return - 128.26:+.2f}% |
| Max DD | -6.27% | {max_dd:.2f}% | {max_dd - (-6.27):+.2f}% |
| Trades | 1678 | {len(trades_df)} | {len(trades_df) - 1678:+d} |

## Results Analysis

{'✅ **BREAKTHROUGH SUCCESS**' if total_return > 200 else '✅ **EXCELLENT SUCCESS**' if total_return > 100 else '✅ **SUCCESS**' if total_return > 50 else '⚠️ **NEEDS IMPROVEMENT**'}

- Minimum target (>50%): {'✅ PASS' if total_return > 50 else '❌ FAIL'}
- Excellent target (>100%): {'✅ PASS' if total_return > 100 else '❌ FAIL'}
- Breakthrough target (>200%): {'✅ PASS' if total_return > 200 else '❌ FAIL'}
- Max DD < 30%: {'✅ PASS' if max_dd > -30 else '❌ FAIL'}

## Final Strategy Composition

This CORRECTED strategy uses 3 mean-reversion approaches:
1. **Mean Reversion SHORT** - Fade overbought moves at BB upper
2. **Bollinger Bounce LONG** - Buy oversold bounces at BB lower
3. **EMA Pullback LONG** - Buy pullbacks in uptrend

Position sizing: **20% per trade**
Stop loss: **Fixed 1.5% from entry** (no longer BB-relative)

---
*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*This version has CORRECT stop loss placement*
"""

    with open('./results/adaptive_5m_fixed_analysis.md', 'w') as f:
        f.write(analysis)

    print("="*80)
    print("FIX COMPLETE - ACCURATE DATA GENERATED")
    print("="*80)
else:
    print("No trades generated")
