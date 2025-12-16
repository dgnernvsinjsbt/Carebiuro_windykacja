"""
PROPER Portfolio Simulation

- Start with $100 total
- Enter each trade with 100% of AVAILABLE capital (not locked in open positions)
- Track open positions (multiple strategies can be open at same time)
- Split available capital when multiple signals at same time
- Reinvest all profits
- 1x leverage, 0.07% round-trip fees
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime


def simulate_portfolio_proper(trades_file, starting_capital=100, fee_pct=0.07):
    """
    Proper portfolio simulation with position tracking

    Args:
        trades_file: Path to combined trades CSV
        starting_capital: Starting capital in USDT
        fee_pct: Round-trip fee percentage (0.07 = 0.07%)
    """

    # Load all trades
    trades = pd.read_csv(trades_file)
    trades['entry_time'] = pd.to_datetime(trades['entry_time'])
    trades['exit_time'] = pd.to_datetime(trades['exit_time'])

    # Sort chronologically
    trades = trades.sort_values('entry_time').reset_index(drop=True)

    print(f"\n{'='*70}")
    print(f"PROPER PORTFOLIO SIMULATION")
    print(f"{'='*70}")
    print(f"Total trades: {len(trades)}")
    print(f"Symbols: {', '.join(sorted(trades['symbol'].unique()))}")
    print(f"Starting capital: ${starting_capital:.2f} USDT")
    print(f"Method: 100% of available capital per trade (reinvesting)")
    print(f"Leverage: 1x")
    print(f"Fees: {fee_pct}% round-trip")
    print(f"{'='*70}\n")

    # Portfolio state
    total_equity = starting_capital
    open_positions = {}  # {trade_idx: {'symbol': ..., 'capital': ..., 'entry_time': ...}}
    equity_curve = []
    peak_equity = starting_capital
    max_drawdown = 0

    # Create timeline of all entry/exit events
    events = []

    for idx, trade in trades.iterrows():
        events.append({
            'timestamp': trade['entry_time'],
            'type': 'entry',
            'trade_idx': idx,
            'symbol': trade['symbol'],
            'pnl_pct': trade['pnl_pct']
        })
        events.append({
            'timestamp': trade['exit_time'],
            'type': 'exit',
            'trade_idx': idx,
            'symbol': trade['symbol'],
            'pnl_pct': trade['pnl_pct']
        })

    # Sort events chronologically
    events = sorted(events, key=lambda x: (x['timestamp'], x['type'] == 'entry'))  # Exits before entries on same timestamp

    # Process events
    for event in events:
        if event['type'] == 'entry':
            # Calculate available capital (total equity - locked in open positions)
            locked_capital = sum(pos['capital'] for pos in open_positions.values())
            available_capital = total_equity - locked_capital

            # If no available capital, skip this trade
            if available_capital <= 0:
                continue

            # Count how many entries at this exact timestamp
            same_time_entries = [e for e in events
                                  if e['timestamp'] == event['timestamp']
                                  and e['type'] == 'entry'
                                  and e['trade_idx'] >= event['trade_idx']]

            # Split available capital among concurrent entries
            num_concurrent = len([e for e in same_time_entries if e['trade_idx'] not in open_positions])
            position_capital = available_capital / num_concurrent if num_concurrent > 0 else available_capital

            # Open position
            open_positions[event['trade_idx']] = {
                'symbol': event['symbol'],
                'capital': position_capital,
                'entry_time': event['timestamp'],
                'pnl_pct': event['pnl_pct']
            }

        elif event['type'] == 'exit':
            # Close position if it was opened
            if event['trade_idx'] in open_positions:
                pos = open_positions[event['trade_idx']]

                # Calculate P/L
                gross_pnl = pos['capital'] * (pos['pnl_pct'] / 100)
                fees = pos['capital'] * (fee_pct / 100)
                net_pnl = gross_pnl - fees

                # Return capital + P/L to equity
                total_equity += net_pnl

                # Remove from open positions
                del open_positions[event['trade_idx']]

                # Update peak and drawdown
                if total_equity > peak_equity:
                    peak_equity = total_equity

                current_drawdown = ((total_equity / peak_equity) - 1) * 100
                if current_drawdown < max_drawdown:
                    max_drawdown = current_drawdown

                # Record equity point
                equity_curve.append({
                    'timestamp': event['timestamp'],
                    'equity': total_equity,
                    'peak': peak_equity,
                    'drawdown_pct': current_drawdown,
                    'open_positions': len(open_positions),
                    'net_pnl': net_pnl,
                    'symbol': pos['symbol']
                })

    # Convert to DataFrame
    equity_df = pd.DataFrame(equity_curve)

    # Calculate metrics
    total_return = ((total_equity / starting_capital) - 1) * 100
    return_dd_ratio = abs(total_return / max_drawdown) if max_drawdown < 0 else 0

    # Count wins/losses
    winners = equity_df[equity_df['net_pnl'] > 0]
    losers = equity_df[equity_df['net_pnl'] <= 0]

    win_rate = (len(winners) / len(equity_df)) * 100 if len(equity_df) > 0 else 0

    # Profit factor
    gross_profit = winners['net_pnl'].sum() if len(winners) > 0 else 0
    gross_loss = abs(losers['net_pnl'].sum()) if len(losers) > 0 else 0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

    # Average concurrent positions
    avg_concurrent = equity_df['open_positions'].mean() if len(equity_df) > 0 else 0
    max_concurrent = equity_df['open_positions'].max() if len(equity_df) > 0 else 0

    metrics = {
        'starting_capital': starting_capital,
        'ending_equity': total_equity,
        'total_return_pct': total_return,
        'total_return_usd': total_equity - starting_capital,
        'max_drawdown_pct': max_drawdown,
        'return_dd_ratio': return_dd_ratio,
        'total_trades': len(equity_df),
        'winners': len(winners),
        'losers': len(losers),
        'win_rate_pct': win_rate,
        'profit_factor': profit_factor,
        'avg_concurrent_positions': avg_concurrent,
        'max_concurrent_positions': max_concurrent,
        'total_signals': len(trades),
        'filled_trades': len(equity_df),
        'skipped_no_capital': len(trades) - len(equity_df)
    }

    return equity_df, metrics


def print_metrics(metrics):
    """Print metrics"""

    print(f"\n{'='*70}")
    print(f"PORTFOLIO PERFORMANCE")
    print(f"{'='*70}\n")

    print(f"💰 Capital:")
    print(f"  Starting:          ${metrics['starting_capital']:.2f} USDT")
    print(f"  Ending:            ${metrics['ending_equity']:.2f} USDT")
    print(f"  Net Profit:        ${metrics['total_return_usd']:.2f} USDT")
    print()

    print(f"📊 Returns:")
    print(f"  Total Return:      {metrics['total_return_pct']:.2f}%")
    print(f"  Max Drawdown:      {metrics['max_drawdown_pct']:.2f}%")
    print(f"  Return/DD Ratio:   {metrics['return_dd_ratio']:.2f}x")
    print()

    print(f"🎯 Trading Stats:")
    print(f"  Total Signals:     {metrics['total_signals']}")
    print(f"  Filled Trades:     {metrics['filled_trades']}")
    print(f"  Skipped (no cap):  {metrics['skipped_no_capital']}")
    print(f"  Winners:           {metrics['winners']} ({metrics['win_rate_pct']:.1f}%)")
    print(f"  Losers:            {metrics['losers']} ({100 - metrics['win_rate_pct']:.1f}%)")
    print(f"  Profit Factor:     {metrics['profit_factor']:.2f}")
    print()

    print(f"📈 Position Management:")
    print(f"  Avg Concurrent:    {metrics['avg_concurrent_positions']:.1f} positions")
    print(f"  Max Concurrent:    {int(metrics['max_concurrent_positions'])} positions")
    print()

    print(f"{'='*70}")


def main():
    """Run proper portfolio simulation"""

    trades_file = Path("trading/results/all_10_strategies_trades.csv")

    if not trades_file.exists():
        print(f"❌ Error: {trades_file} not found")
        return

    # Run simulation
    equity_df, metrics = simulate_portfolio_proper(
        trades_file=trades_file,
        starting_capital=100,
        fee_pct=0.07
    )

    # Print results
    print_metrics(metrics)

    # Save results
    equity_df.to_csv("trading/results/portfolio_proper_equity_curve.csv", index=False)
    print(f"✅ Equity curve saved to trading/results/portfolio_proper_equity_curve.csv")


if __name__ == '__main__':
    main()
