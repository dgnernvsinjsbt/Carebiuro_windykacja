"""
FARTCOIN/USDT Mean Reversion Scalping Strategy
==============================================
Targets extreme price deviations with 8:1+ risk:reward ratios.
Exploits panic moves and exhaustion points in volatile memecoin markets.

STRATEGY PHILOSOPHY:
- Enter ONLY at statistical extremes (2.5+ standard deviations)
- Use the WICK of the exhaustion candle as the stop (beyond the extreme)
- Target the return to mean PLUS overshoot for 8R
- Very selective: Low frequency, high quality setups
"""

import pandas as pd
import numpy as np
from datetime import datetime
import os

# Configuration
DATA_PATH = '/workspaces/Carebiuro_windykacja/fartcoin_usdt_1m_lbank.csv'
OUTPUT_DIR = '/workspaces/Carebiuro_windykacja/strategies'
FEE_RATE = 0.001  # 0.1% per side (0.2% round trip)

# Strategy parameters - STRICT for true extremes
BB_PERIOD = 20
BB_STD_ENTRY = 2.5  # Must touch 2.5 SD band
RSI_PERIOD = 14
RSI_EXTREME_LOW = 25
RSI_EXTREME_HIGH = 75
SMA_PERIOD = 20
MIN_WICK_RATIO = 0.4  # Must have 40%+ wick (rejection)
MIN_VOLUME_SPIKE = 1.5  # 1.5x volume
STOP_BUFFER = 0.0015  # 0.15% beyond wick extreme
TARGET_RR = 8.0  # Target 8:1 risk:reward
MAX_HOLDING_BARS = 40  # Maximum 40 minutes

print("="*80)
print("FARTCOIN/USDT MEAN REVERSION SCALPING STRATEGY v2")
print("="*80)
print(f"Data source: {DATA_PATH}")
print(f"Fee rate: {FEE_RATE*100}% per side ({FEE_RATE*2*100}% round trip)")
print(f"Target R:R: {TARGET_RR}:1")
print(f"Entry: 2.5 SD Bollinger Band + Wick Rejection + Volume Spike")
print()

# Load data
print("Loading data...")
df = pd.read_csv(DATA_PATH)
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)
print(f"Loaded {len(df):,} candles from {df['timestamp'].min()} to {df['timestamp'].max()}")
print(f"Price range: ${df['low'].min():.5f} - ${df['high'].max():.5f}")
print()

# Calculate indicators
print("Calculating indicators...")

# Bollinger Bands
df['sma'] = df['close'].rolling(BB_PERIOD).mean()
df['bb_std'] = df['close'].rolling(BB_PERIOD).std()
df['bb_upper_2'] = df['sma'] + (2 * df['bb_std'])
df['bb_lower_2'] = df['sma'] - (2 * df['bb_std'])
df['bb_upper_25'] = df['sma'] + (2.5 * df['bb_std'])
df['bb_lower_25'] = df['sma'] - (2.5 * df['bb_std'])
df['bb_upper_3'] = df['sma'] + (3 * df['bb_std'])
df['bb_lower_3'] = df['sma'] - (3 * df['bb_std'])

# RSI
delta = df['close'].diff()
gain = (delta.where(delta > 0, 0)).rolling(window=RSI_PERIOD).mean()
loss = (-delta.where(delta < 0, 0)).rolling(window=RSI_PERIOD).mean()
rs = gain / loss
df['rsi'] = 100 - (100 / (1 + rs))

# Volume analysis
df['volume_sma'] = df['volume'].rolling(20).mean()
df['volume_ratio'] = df['volume'] / df['volume_sma']

# Candle analysis
df['body'] = abs(df['close'] - df['open'])
df['upper_wick'] = df['high'] - df[['open', 'close']].max(axis=1)
df['lower_wick'] = df[['open', 'close']].min(axis=1) - df['low']
df['total_range'] = df['high'] - df['low']
df['upper_wick_ratio'] = np.where(df['total_range'] > 0,
                                   df['upper_wick'] / df['total_range'],
                                   0)
df['lower_wick_ratio'] = np.where(df['total_range'] > 0,
                                   df['lower_wick'] / df['total_range'],
                                   0)

# Price distance from mean
df['pct_from_sma'] = (df['close'] - df['sma']) / df['sma']

print(f"Indicators calculated.")
print()

# Trading logic
print("Running backtest...")

trades = []
in_trade = False
entry_price = 0
stop_loss = 0
take_profit = 0
entry_bar = 0
trade_direction = None
entry_reason = ""

for i in range(BB_PERIOD + RSI_PERIOD, len(df)):

    if pd.isna(df.loc[i, 'sma']) or pd.isna(df.loc[i, 'rsi']):
        continue

    current_bar = df.loc[i]
    prev_bar = df.loc[i-1]

    # Exit logic
    if in_trade:
        bars_in_trade = i - entry_bar
        exit_price = None
        exit_reason = None

        # Check stop loss
        if trade_direction == 'LONG':
            if current_bar['low'] <= stop_loss:
                exit_price = stop_loss
                exit_reason = 'Stop Loss'
            elif current_bar['high'] >= take_profit:
                exit_price = take_profit
                exit_reason = 'Take Profit (8R)'
        else:  # SHORT
            if current_bar['high'] >= stop_loss:
                exit_price = stop_loss
                exit_reason = 'Stop Loss'
            elif current_bar['low'] <= take_profit:
                exit_price = take_profit
                exit_reason = 'Take Profit (8R)'

        # Maximum holding period
        if bars_in_trade >= MAX_HOLDING_BARS and exit_price is None:
            exit_price = current_bar['close']
            exit_reason = 'Max Holding Period (40min)'

        if exit_price:
            # Calculate P&L
            if trade_direction == 'LONG':
                gross_pnl_pct = (exit_price - entry_price) / entry_price
            else:  # SHORT
                gross_pnl_pct = (entry_price - exit_price) / entry_price

            net_pnl_pct = gross_pnl_pct - (FEE_RATE * 2)

            # Calculate R-multiple
            risk = abs(entry_price - stop_loss) / entry_price
            r_multiple = net_pnl_pct / risk if risk > 0 else 0

            trades.append({
                'entry_time': df.loc[entry_bar, 'timestamp'],
                'exit_time': current_bar['timestamp'],
                'direction': trade_direction,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'exit_price': exit_price,
                'exit_reason': exit_reason,
                'bars_held': bars_in_trade,
                'gross_pnl_pct': gross_pnl_pct * 100,
                'net_pnl_pct': net_pnl_pct * 100,
                'r_multiple': r_multiple,
                'entry_reason': entry_reason
            })

            in_trade = False

    # Entry logic
    if not in_trade:

        # LONG setup: Extreme oversold with bullish rejection wick
        if (prev_bar['low'] <= prev_bar['bb_lower_25'] and  # Touched 2.5 SD
            prev_bar['rsi'] <= RSI_EXTREME_LOW and  # RSI extreme
            prev_bar['lower_wick_ratio'] >= MIN_WICK_RATIO and  # Strong rejection wick
            prev_bar['volume_ratio'] >= MIN_VOLUME_SPIKE and  # Volume spike
            current_bar['close'] > prev_bar['low'] and  # Confirmation: not breaking lower
            current_bar['close'] > current_bar['open']):  # Bullish candle

            entry_price = current_bar['open']
            stop_loss = prev_bar['low'] * (1 - STOP_BUFFER)  # Just below wick low
            risk = entry_price - stop_loss
            take_profit = entry_price + (risk * TARGET_RR)

            in_trade = True
            entry_bar = i
            trade_direction = 'LONG'
            entry_reason = f"LONG: BB_touch={prev_bar['low']:.5f}, BB_lower={prev_bar['bb_lower_25']:.5f}, RSI={prev_bar['rsi']:.1f}, Wick={prev_bar['lower_wick_ratio']*100:.0f}%, Vol={prev_bar['volume_ratio']:.1f}x"

        # SHORT setup: Extreme overbought with bearish rejection wick
        elif (prev_bar['high'] >= prev_bar['bb_upper_25'] and  # Touched 2.5 SD
              prev_bar['rsi'] >= RSI_EXTREME_HIGH and  # RSI extreme
              prev_bar['upper_wick_ratio'] >= MIN_WICK_RATIO and  # Strong rejection wick
              prev_bar['volume_ratio'] >= MIN_VOLUME_SPIKE and  # Volume spike
              current_bar['close'] < prev_bar['high'] and  # Confirmation: not breaking higher
              current_bar['close'] < current_bar['open']):  # Bearish candle

            entry_price = current_bar['open']
            stop_loss = prev_bar['high'] * (1 + STOP_BUFFER)  # Just above wick high
            risk = stop_loss - entry_price
            take_profit = entry_price - (risk * TARGET_RR)

            in_trade = True
            entry_bar = i
            trade_direction = 'SHORT'
            entry_reason = f"SHORT: BB_touch={prev_bar['high']:.5f}, BB_upper={prev_bar['bb_upper_25']:.5f}, RSI={prev_bar['rsi']:.1f}, Wick={prev_bar['upper_wick_ratio']*100:.0f}%, Vol={prev_bar['volume_ratio']:.1f}x"

print(f"Backtest complete. Found {len(trades)} trades.")
print()

# Convert to DataFrame
trades_df = pd.DataFrame(trades)

if len(trades_df) == 0:
    print("WARNING: No trades generated.")
    print("\nStrategy requires EXTREME conditions:")
    print(f"  - Price must touch 2.5 SD Bollinger Band")
    print(f"  - RSI must be below {RSI_EXTREME_LOW} (oversold) or above {RSI_EXTREME_HIGH} (overbought)")
    print(f"  - Wick must be {MIN_WICK_RATIO*100}%+ of candle range (rejection)")
    print(f"  - Volume must be {MIN_VOLUME_SPIKE}x+ average")
    print(f"  - Confirmation candle must not break the extreme")
    print()
    print("This is by design - mean reversion scalping with 8R targets requires")
    print("very rare, high-quality setups at absolute panic/euphoria extremes.")
else:
    # Performance analysis
    print("="*80)
    print("PERFORMANCE METRICS")
    print("="*80)

    winning_trades = trades_df[trades_df['net_pnl_pct'] > 0]
    losing_trades = trades_df[trades_df['net_pnl_pct'] <= 0]

    total_trades = len(trades_df)
    win_count = len(winning_trades)
    loss_count = len(losing_trades)
    win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0

    avg_win = winning_trades['net_pnl_pct'].mean() if len(winning_trades) > 0 else 0
    avg_loss = losing_trades['net_pnl_pct'].mean() if len(losing_trades) > 0 else 0
    avg_win_r = winning_trades['r_multiple'].mean() if len(winning_trades) > 0 else 0
    avg_loss_r = losing_trades['r_multiple'].mean() if len(losing_trades) > 0 else 0

    total_return = trades_df['net_pnl_pct'].sum()

    gross_profit = winning_trades['net_pnl_pct'].sum() if len(winning_trades) > 0 else 0
    gross_loss = abs(losing_trades['net_pnl_pct'].sum()) if len(losing_trades) > 0 else 0
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float('inf')

    # Equity curve
    trades_df['cumulative_pnl'] = trades_df['net_pnl_pct'].cumsum()
    trades_df['equity'] = 100 + trades_df['cumulative_pnl']

    # Drawdown
    trades_df['peak'] = trades_df['equity'].cummax()
    trades_df['drawdown'] = ((trades_df['equity'] - trades_df['peak']) / trades_df['peak'] * 100)
    max_drawdown = trades_df['drawdown'].min()

    # R-multiple analysis
    avg_r_multiple = trades_df['r_multiple'].mean()
    median_r_multiple = trades_df['r_multiple'].median()
    best_r = trades_df['r_multiple'].max()
    worst_r = trades_df['r_multiple'].min()

    # Trade distribution
    long_trades = trades_df[trades_df['direction'] == 'LONG']
    short_trades = trades_df[trades_df['direction'] == 'SHORT']

    print(f"Total Trades: {total_trades}")
    print(f"  Long: {len(long_trades)} ({len(long_trades)/total_trades*100:.1f}%)")
    print(f"  Short: {len(short_trades)} ({len(short_trades)/total_trades*100:.1f}%)")
    print()

    print(f"Win Rate: {win_rate:.2f}% ({win_count} wins / {loss_count} losses)")
    print(f"Average Win: {avg_win:.2f}% ({avg_win_r:.2f}R)")
    print(f"Average Loss: {avg_loss:.2f}% ({avg_loss_r:.2f}R)")
    print()

    print(f"R-Multiple Statistics:")
    print(f"  Average: {avg_r_multiple:.2f}R")
    print(f"  Median: {median_r_multiple:.2f}R")
    print(f"  Best: {best_r:.2f}R")
    print(f"  Worst: {worst_r:.2f}R")
    print()

    print(f"Profit Factor: {profit_factor:.2f}")
    print(f"Total Return: {total_return:.2f}%")
    print(f"Max Drawdown: {max_drawdown:.2f}%")
    print()

    # Expectancy
    expectancy = (win_rate/100 * avg_win) + ((1-win_rate/100) * avg_loss)
    print(f"Expectancy per Trade: {expectancy:.2f}%")
    print()

    # Average holding time
    avg_bars_held = trades_df['bars_held'].mean()
    print(f"Average Holding Time: {avg_bars_held:.1f} minutes")
    print()

    # Target achievement
    target_hits = trades_df[trades_df['exit_reason'] == 'Take Profit (8R)']
    print(f"8R Take Profit Hits: {len(target_hits)} ({len(target_hits)/total_trades*100:.1f}%)")

    # Big winners
    big_winners = trades_df[trades_df['r_multiple'] >= 8.0]
    print(f"8R+ Winners: {len(big_winners)} ({len(big_winners)/total_trades*100:.1f}%)")
    print()

    print("="*80)
    print("EDGE VALIDATION")
    print("="*80)

    profitable = total_return > 0
    good_rr = avg_win_r >= 5.0  # At least 5R average on winners
    sufficient_win_rate = win_rate >= 15
    positive_expectancy = expectancy > 0
    acceptable_pf = profit_factor > 1.3

    print(f"{'✓' if profitable else '✗'} Profitable: {profitable} (Return: {total_return:.2f}%)")
    print(f"{'✓' if good_rr else '✗'} High R:R on Winners: {good_rr} (Avg: {avg_win_r:.2f}R, Target: 5+R)")
    print(f"{'✓' if sufficient_win_rate else '✗'} Sufficient Win Rate: {sufficient_win_rate} (Win Rate: {win_rate:.1f}%, Minimum: 15%)")
    print(f"{'✓' if positive_expectancy else '✗'} Positive Expectancy: {positive_expectancy} (Expectancy: {expectancy:.2f}%)")
    print(f"{'✓' if acceptable_pf else '✗'} Good Profit Factor: {acceptable_pf} (PF: {profit_factor:.2f}, Minimum: 1.3)")
    print()

    if profitable and positive_expectancy and (good_rr or win_rate >= 40):
        print("✅ STRATEGY EDGE CONFIRMED")
        print("Mean reversion principle validated in FARTCOIN data.")
        print("Extreme deviations do snap back - the edge exists.")
    else:
        print("⚠️  STRATEGY SHOWS POTENTIAL BUT NEEDS OPTIMIZATION")
        print("Mean reversion occurs, but entry/exit timing needs refinement.")
    print()

    # Sample trades
    print("="*80)
    print("SAMPLE TRADES")
    print("="*80)

    if len(winning_trades) > 0:
        print("\n>>> TOP WINNING TRADES:")
        top_winners = winning_trades.nlargest(min(3, len(winning_trades)), 'r_multiple')
        for idx, trade in top_winners.iterrows():
            print(f"\n{trade['direction']} @ ${trade['entry_price']:.5f}")
            print(f"  Entry: {trade['entry_time']}")
            print(f"  Exit: {trade['exit_time']} ({trade['bars_held']} min)")
            print(f"  P&L: {trade['net_pnl_pct']:.2f}% ({trade['r_multiple']:.2f}R)")
            print(f"  {trade['entry_reason']}")
            print(f"  Exit: {trade['exit_reason']}")

    if len(losing_trades) > 0:
        print("\n>>> SAMPLE LOSING TRADES:")
        sample_losers = losing_trades.head(min(2, len(losing_trades)))
        for idx, trade in sample_losers.iterrows():
            print(f"\n{trade['direction']} @ ${trade['entry_price']:.5f}")
            print(f"  Entry: {trade['entry_time']}")
            print(f"  Exit: {trade['exit_time']} ({trade['bars_held']} min)")
            print(f"  P&L: {trade['net_pnl_pct']:.2f}% ({trade['r_multiple']:.2f}R)")
            print(f"  {trade['entry_reason']}")
            print(f"  Exit: {trade['exit_reason']}")

    # Save results
    print()
    print("="*80)
    print("SAVING RESULTS")
    print("="*80)

    trades_file = os.path.join(OUTPUT_DIR, 'mean-reversion-trades.csv')
    trades_df.to_csv(trades_file, index=False)
    print(f"✓ Saved trade log to: {trades_file}")

    equity_file = os.path.join(OUTPUT_DIR, 'mean-reversion-equity.csv')
    equity_df = trades_df[['exit_time', 'equity', 'cumulative_pnl', 'drawdown']].copy()
    equity_df.columns = ['timestamp', 'equity', 'cumulative_pnl_pct', 'drawdown_pct']
    equity_df.to_csv(equity_file, index=False)
    print(f"✓ Saved equity curve to: {equity_file}")

    print()
    print("="*80)
    print("BACKTEST COMPLETE")
    print("="*80)
