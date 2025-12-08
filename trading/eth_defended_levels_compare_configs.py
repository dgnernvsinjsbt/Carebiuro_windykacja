"""
Compare Original vs Optimized ETH Defended Levels

Shows side-by-side comparison of all configurations tested
"""

import pandas as pd
import matplotlib.pyplot as plt

def main():
    print("="*60)
    print("ETH DEFENDED LEVELS - CONFIGURATION COMPARISON")
    print("="*60)

    # Load all optimization results
    sessions = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/results/eth_defended_levels_optimize_sessions.csv')
    directions = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/results/eth_defended_levels_optimize_directions.csv')

    # Load original signals and trades
    original_signals = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/results/eth_defended_levels_signals.csv')
    original_trades = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/results/eth_defended_levels_trades.csv')

    print(f"\nORIGINAL SIGNALS (ALL 3):")
    print(original_signals[['type', 'entry_time', 'extreme_price', 'hours_held', 'avg_volume_ratio']])

    print(f"\nORIGINAL TRADES (ALL 3):")
    original_trades['entry_time'] = pd.to_datetime(original_trades['entry_time'])
    original_trades['hour'] = original_trades['entry_time'].dt.hour

    def get_session(hour):
        if 0 <= hour < 8:
            return 'Asia'
        elif 8 <= hour < 14:
            return 'Europe'
        elif 14 <= hour < 21:
            return 'US'
        else:
            return 'Overnight'

    original_trades['session'] = original_trades['hour'].apply(get_session)
    print(original_trades[['entry_time', 'direction', 'session', 'pnl_pct', 'exit_reason']])

    print(f"\n" + "="*60)
    print("SESSION FILTER OPTIMIZATION")
    print("="*60)
    print(sessions.sort_values('return_dd', ascending=False))

    print(f"\n" + "="*60)
    print("DIRECTION FILTER OPTIMIZATION")
    print("="*60)
    print(directions.sort_values('return_dd', ascending=False))

    # Create comparison table
    print(f"\n" + "="*60)
    print("BEFORE/AFTER COMPARISON")
    print("="*60)

    original_stats = {
        'Config': 'Original (Both dirs, All sessions)',
        'Signals': 3,
        'Return': '+7.7%',
        'Max DD': '-1.1%',
        'Return/DD': '7.00x',
        'Win Rate': '33.3%'
    }

    # Get best session result
    best_session = sessions.loc[sessions['return_dd'].idxmax()]
    optimized_stats = {
        'Config': f'Optimized ({best_session["session"].upper()} session only)',
        'Signals': int(best_session['signals']),
        'Return': f"{best_session['return']:+.1f}%",
        'Max DD': f"{best_session['max_dd']:.2f}%",
        'Return/DD': f"{best_session['return_dd']:.2f}x",
        'Win Rate': f"{best_session['win_rate']*100:.1f}%"
    }

    comparison_df = pd.DataFrame([original_stats, optimized_stats])
    print(comparison_df.to_string(index=False))

    # Save comprehensive comparison
    output_rows = []

    # Original
    output_rows.append({
        'config_name': 'Original',
        'direction': 'both',
        'session': 'all',
        'signals': 3,
        'trades': 3,
        'return': 7.7,
        'max_dd': -1.1,
        'return_dd': 7.00,
        'win_rate': 0.333
    })

    # Session variations
    for idx, row in sessions.iterrows():
        output_rows.append({
            'config_name': f"Session: {row['session']}",
            'direction': 'both',
            'session': row['session'],
            'signals': row['signals'],
            'trades': row['trades'],
            'return': row['return'],
            'max_dd': row['max_dd'],
            'return_dd': row['return_dd'],
            'win_rate': row['win_rate']
        })

    # Direction variations
    for idx, row in directions.iterrows():
        output_rows.append({
            'config_name': f"Direction: {row['direction']}",
            'direction': row['direction'],
            'session': 'all',
            'signals': row['signals'],
            'trades': row['trades'],
            'return': row['return'],
            'max_dd': row['max_dd'],
            'return_dd': row['return_dd'],
            'win_rate': row['win_rate']
        })

    comparison_full = pd.DataFrame(output_rows)
    comparison_full = comparison_full.sort_values('return_dd', ascending=False)

    comparison_full.to_csv('/workspaces/Carebiuro_windykacja/trading/results/eth_defended_levels_optimization_comparison.csv', index=False)
    print(f"\n✅ Full comparison saved to results/eth_defended_levels_optimization_comparison.csv")

    # Create visualization
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Return/DD comparison
    top_configs = comparison_full.head(6)
    axes[0, 0].barh(top_configs['config_name'], top_configs['return_dd'], color='green')
    axes[0, 0].set_xlabel('Return/DD Ratio')
    axes[0, 0].set_title('Return/DD Comparison (Higher is Better)')
    axes[0, 0].axvline(x=7.00, color='red', linestyle='--', label='Original (7.00x)')
    axes[0, 0].legend()

    # Return vs Max DD scatter
    axes[0, 1].scatter(comparison_full['max_dd'], comparison_full['return'], s=100, alpha=0.6)
    for idx, row in comparison_full.iterrows():
        axes[0, 1].annotate(row['config_name'][:15],
                           (row['max_dd'], row['return']),
                           fontsize=8, alpha=0.7)
    axes[0, 1].set_xlabel('Max Drawdown (%)')
    axes[0, 1].set_ylabel('Return (%)')
    axes[0, 1].set_title('Return vs Risk')
    axes[0, 1].grid(True, alpha=0.3)

    # Win rate comparison
    axes[1, 0].barh(top_configs['config_name'], top_configs['win_rate']*100, color='blue')
    axes[1, 0].set_xlabel('Win Rate (%)')
    axes[1, 0].set_title('Win Rate Comparison')
    axes[1, 0].axvline(x=33.3, color='red', linestyle='--', label='Original (33.3%)')
    axes[1, 0].legend()

    # Signal frequency
    axes[1, 1].barh(top_configs['config_name'], top_configs['signals'], color='orange')
    axes[1, 1].set_xlabel('Number of Signals')
    axes[1, 1].set_title('Signal Frequency (30 days)')
    axes[1, 1].axvline(x=3, color='red', linestyle='--', label='Original (3)')
    axes[1, 1].legend()

    plt.tight_layout()
    plt.savefig('/workspaces/Carebiuro_windykacja/trading/results/eth_defended_levels_optimization_comparison.png', dpi=150)
    print(f"✅ Visualization saved to results/eth_defended_levels_optimization_comparison.png")

if __name__ == '__main__':
    main()
