"""
Test: Czy filtry jakości sygnału działają na WSZYSTKICH miesiącach?
Sprawdzamy czy to nie jest curve-fitting tylko do Sep vs Dec
"""
import pandas as pd

# Wczytaj szczegółowe dane tradów
sep_dec = pd.read_csv('sep_dec_trades_detailed.csv')
jul_aug = pd.read_csv('jul_aug_trades_detailed.csv')

# Połącz wszystkie trady
all_trades = pd.concat([
    jul_aug.assign(period='Jul-Aug BAD'),
    sep_dec.assign(period='Sep-Dec')
], ignore_index=True)

print('=' * 80)
print('TEST FILTRÓW JAKOŚCI SYGNAŁU - WSZYSTKIE MIESIĄCE')
print('=' * 80)

# Zaproponowane filtry z analizy Dec vs Sep
filters = {
    'entry_ret_20 > 1.5%': lambda df: df['entry_ret_20'] > 1.5,
    'entry_ret_96 > 0%': lambda df: df['entry_ret_96'] > 0,
    'entry_range_20 > 3.5%': lambda df: df['entry_range_20'] > 3.5,
}

print(f'\nBEZ FILTRÓW (baseline):')
print(f'  Total trades: {len(all_trades)}')
print(f'  Win rate: {(all_trades["pnl_pct"] > 0).sum() / len(all_trades) * 100:.1f}%')
print(f'  Avg P&L: {all_trades["pnl_pct"].mean():+.2f}%')

print(f'\n' + '=' * 80)
print('TESTOWANIE KAŻDEGO FILTRU OSOBNO:')
print('=' * 80)

for filter_name, filter_func in filters.items():
    filtered = all_trades[filter_func(all_trades)]
    
    if len(filtered) > 0:
        win_rate = (filtered['pnl_pct'] > 0).sum() / len(filtered) * 100
        avg_pnl = filtered['pnl_pct'].mean()
        removed_pct = (1 - len(filtered)/len(all_trades)) * 100
        
        print(f'\nFilter: {filter_name}')
        print(f'  Kept: {len(filtered)}/{len(all_trades)} trades ({100-removed_pct:.0f}%)')
        print(f'  Win rate: {win_rate:.1f}%')
        print(f'  Avg P&L: {avg_pnl:+.2f}%')
        print(f'  Improvement: {win_rate - ((all_trades["pnl_pct"] > 0).sum() / len(all_trades) * 100):+.1f}% win rate')

print(f'\n' + '=' * 80)
print('KOMBINOWANE FILTRY:')
print('=' * 80)

# Test kombinacji
combos = [
    ('ret_20 > 1.5%', lambda df: df['entry_ret_20'] > 1.5),
    ('ret_20 > 1.5% AND ret_96 > 0%', lambda df: (df['entry_ret_20'] > 1.5) & (df['entry_ret_96'] > 0)),
    ('ret_20 > 1.5% AND range_20 > 3.5%', lambda df: (df['entry_ret_20'] > 1.5) & (df['entry_range_20'] > 3.5)),
    ('ALL THREE', lambda df: (df['entry_ret_20'] > 1.5) & (df['entry_ret_96'] > 0) & (df['entry_range_20'] > 3.5)),
]

for combo_name, combo_func in combos:
    filtered = all_trades[combo_func(all_trades)]
    
    if len(filtered) > 0:
        win_rate = (filtered['pnl_pct'] > 0).sum() / len(filtered) * 100
        avg_pnl = filtered['pnl_pct'].mean()
        
        print(f'\n{combo_name}:')
        print(f'  Trades: {len(filtered)}/{len(all_trades)} ({len(filtered)/len(all_trades)*100:.0f}%)')
        print(f'  Win rate: {win_rate:.1f}%')
        print(f'  Avg P&L: {avg_pnl:+.2f}%')
        
        # Breakdown po okresach
        for period in ['Jul-Aug BAD', 'Sep-Dec']:
            period_filtered = filtered[filtered['period'] == period]
            if len(period_filtered) > 0:
                period_win = (period_filtered['pnl_pct'] > 0).sum() / len(period_filtered) * 100
                print(f'    {period}: {len(period_filtered)} trades, {period_win:.1f}% win')

print(f'\n' + '=' * 80)
print('WNIOSKI:')
print('=' * 80)

# Najlepszy filtr
best_filtered = all_trades[(all_trades['entry_ret_20'] > 1.5) & (all_trades['entry_ret_96'] > 0) & (all_trades['entry_range_20'] > 3.5)]

if len(best_filtered) > 0:
    baseline_win = (all_trades['pnl_pct'] > 0).sum() / len(all_trades) * 100
    filtered_win = (best_filtered['pnl_pct'] > 0).sum() / len(best_filtered) * 100
    
    print(f'\nCzy filtry działają UNIWERSALNIE?')
    print(f'  Baseline: {len(all_trades)} trades, {baseline_win:.1f}% win rate')
    print(f'  Z filtrami: {len(best_filtered)} trades, {filtered_win:.1f}% win rate')
    print(f'  Improvement: {filtered_win - baseline_win:+.1f}% points')
    
    if filtered_win > baseline_win + 10:
        print(f'\n✅ TAK! Filtry poprawiają win rate o >{filtered_win - baseline_win:.0f}% - to NIE jest overfitting')
    elif filtered_win > baseline_win:
        print(f'\n⚠️  Małe improvement ({filtered_win - baseline_win:.1f}%) - może być curve-fitting')
    else:
        print(f'\n❌ NIE! Filtry nie pomagają - to jest overfitting do Dec vs Sep')
else:
    print(f'\n❌ Filtry wyrzucają WSZYSTKIE trady - za restrykcyjne')

