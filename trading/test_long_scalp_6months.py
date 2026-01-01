#!/usr/bin/env python3
import pandas as pd

df = pd.read_csv('fartcoin_6months_bingx_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

ENTRY_OFFSET_PCT = 2.0
TP_PCT = 2.0
SL_PCT = 10.0
INITIAL_EQUITY = 100.0

print("="*140)
print("LONG SCALP STRATEGY - 6 MONTH BREAKDOWN")
print(f"Entry: LONG when dips {ENTRY_OFFSET_PCT}% below daily high, TP: {TP_PCT}%, SL: {SL_PCT}%")
print("Rule: TP = can trade again, SL = stop for the day")
print("="*140)
print()

df['month'] = df['timestamp'].dt.to_period('M')
months = df['month'].unique()

monthly_results = []
cumulative_equity = INITIAL_EQUITY

for month in sorted(months):
    df_month = df[df['month'] == month].copy().reset_index(drop=True)
    
    equity = cumulative_equity
    peak_equity = equity
    max_dd = 0.0
    trades = []
    
    current_day, daily_high, in_position, stopped_out_today, position = None, 0, False, False, None
    
    for i in range(len(df_month)):
        row = df_month.iloc[i]
        day = row['timestamp'].date()
        
        if day != current_day:
            current_day, daily_high, stopped_out_today = day, row['high'], False
            if in_position:
                pnl_pct = ((row['open'] - position['entry_price']) / position['entry_price']) * 100
                equity += position['position_size'] * (pnl_pct / 100)
                in_position, position = False, None
        
        if row['high'] > daily_high:
            daily_high = row['high']
        
        if not in_position and not stopped_out_today:
            trigger_price = daily_high * (1 - ENTRY_OFFSET_PCT / 100)
            if row['low'] <= trigger_price:
                entry_price = trigger_price
                sl_price = entry_price * (1 - SL_PCT / 100)
                tp_price = entry_price * (1 + TP_PCT / 100)
                position_size = (equity * 5.0) / SL_PCT
                if position_size > 0:
                    in_position, position = True, {
                        'entry_price': entry_price,
                        'sl_price': sl_price,
                        'tp_price': tp_price,
                        'position_size': position_size
                    }
        
        if in_position:
            hit_sl = row['low'] <= position['sl_price']
            hit_tp = row['high'] >= position['tp_price']
            
            if hit_sl or hit_tp:
                exit_price = position['sl_price'] if hit_sl else position['tp_price']
                pnl_pct = ((exit_price - position['entry_price']) / position['entry_price']) * 100
                equity += position['position_size'] * (pnl_pct / 100)
                
                if equity > peak_equity:
                    peak_equity = equity
                dd = ((peak_equity - equity) / peak_equity) * 100
                if dd > max_dd:
                    max_dd = dd
                
                trades.append({'result': 'TP' if hit_tp else 'SL'})
                in_position, position = False, None
                
                if hit_sl:
                    stopped_out_today = True
    
    month_start = cumulative_equity
    month_return = ((equity - month_start) / month_start) * 100
    return_dd = month_return / max_dd if max_dd > 0 else 0
    trades_df = pd.DataFrame(trades)
    win_rate = (trades_df['result'] == 'TP').sum() / len(trades_df) * 100 if len(trades_df) > 0 else 0
    
    monthly_results.append({
        'month': str(month),
        'start_equity': month_start,
        'end_equity': equity,
        'return': month_return,
        'max_dd': max_dd,
        'return_dd': return_dd,
        'trades': len(trades_df),
        'win_rate': win_rate
    })
    
    cumulative_equity = equity

print("MONTHLY BREAKDOWN:")
print("-"*140)
print(f"{'Month':<12} {'Start $':<12} {'End $':<12} {'Return':<12} {'Max DD':<12} {'R/DD':<10} {'Trades':<10} {'WR %':<10}")
print("-"*140)

for result in monthly_results:
    status = "✅" if result['return'] > 0 else "❌"
    print(f"{result['month']:<12} ${result['start_equity']:>10.2f} ${result['end_equity']:>10.2f} {result['return']:>+10.2f}%  {result['max_dd']:>10.2f}%  {result['return_dd']:>8.2f}x  {result['trades']:<10.0f} {result['win_rate']:>8.1f}%  {status}")

print()
print("="*140)
print()

total_return = ((cumulative_equity - INITIAL_EQUITY) / INITIAL_EQUITY) * 100
overall_max_dd = max([r['max_dd'] for r in monthly_results])
overall_return_dd = total_return / overall_max_dd if overall_max_dd > 0 else 0
total_trades = sum([r['trades'] for r in monthly_results])
profitable_months = sum([1 for r in monthly_results if r['return'] > 0])

print("OVERALL PERFORMANCE (6 months):")
print(f"  Initial Capital: ${INITIAL_EQUITY:.2f}")
print(f"  Final Capital: ${cumulative_equity:.2f}")
print(f"  Total Return: {total_return:+.2f}%")
print(f"  Max Monthly DD: {overall_max_dd:.2f}%")
print(f"  Return/DD Ratio: {overall_return_dd:.2f}x")
print(f"  Total Trades: {total_trades}")
print(f"  Profitable Months: {profitable_months}/6")
print(f"  Avg Trades/Month: {total_trades/6:.1f}")

print()

if profitable_months >= 5:
    print("🔥 EXCELLENT: Very consistent performance")
elif profitable_months >= 4:
    print("✅ GOOD: Mostly profitable")
elif profitable_months >= 3:
    print("⚠️  MEDIOCRE: Inconsistent performance")
else:
    print("❌ POOR: More losing than winning months")

print()
print("="*140)
print()
print("COMPARE TO SHORT STRATEGY:")
print("  Total Return: -94.94% (turned $100 into $5.06)")
print("  Profitable Months: 1/6")
print("="*140)
