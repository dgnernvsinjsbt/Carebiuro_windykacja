"""Update all strategy files with optimized parameters from corrected RSI"""
import re
from pathlib import Path

OPTIMIZED_PARAMS = {
    'melania_rsi_swing': {'rsi_low': 25, 'rsi_high': 75, 'limit_offset_pct': 1.5, 'stop_atr_mult': 1.0, 'tp_atr_mult': 3.0, 'return_dd': 31.70, 'return_pct': 9.08, 'max_dd': -0.29, 'win_rate': 80.0, 'trades': 10},
    'crv_rsi_swing': {'rsi_low': 25, 'rsi_high': 70, 'limit_offset_pct': 2.0, 'stop_atr_mult': 1.0, 'tp_atr_mult': 1.0, 'return_dd': 15.20, 'return_pct': 2.58, 'max_dd': -0.17, 'win_rate': 84.6, 'trades': 13},
    'xlm_rsi_swing': {'rsi_low': 30, 'rsi_high': 75, 'limit_offset_pct': 1.5, 'stop_atr_mult': 1.0, 'tp_atr_mult': 1.5, 'return_dd': 14.76, 'return_pct': 3.03, 'max_dd': -0.21, 'win_rate': 81.2, 'trades': 16},
    'pepe_rsi_swing': {'rsi_low': 27, 'rsi_high': 65, 'limit_offset_pct': 2.0, 'stop_atr_mult': 1.0, 'tp_atr_mult': 1.0, 'return_dd': 11.39, 'return_pct': 2.96, 'max_dd': -0.26, 'win_rate': 84.2, 'trades': 19},
    'doge_rsi_swing': {'rsi_low': 25, 'rsi_high': 65, 'limit_offset_pct': 2.0, 'stop_atr_mult': 1.5, 'tp_atr_mult': 1.5, 'return_dd': 10.58, 'return_pct': 2.32, 'max_dd': -0.22, 'win_rate': 92.3, 'trades': 13},
    'aixbt_rsi_swing': {'rsi_low': 25, 'rsi_high': 65, 'limit_offset_pct': 2.0, 'stop_atr_mult': 1.0, 'tp_atr_mult': 1.0, 'return_dd': 7.34, 'return_pct': 3.62, 'max_dd': -0.49, 'win_rate': 69.2, 'trades': 26},
    'uni_rsi_swing': {'rsi_low': 27, 'rsi_high': 70, 'limit_offset_pct': 1.5, 'stop_atr_mult': 1.5, 'tp_atr_mult': 1.0, 'return_dd': 7.23, 'return_pct': 2.81, 'max_dd': -0.39, 'win_rate': 88.2, 'trades': 17},
    'moodeng_rsi_swing': {'rsi_low': 27, 'rsi_high': 65, 'limit_offset_pct': 2.0, 'stop_atr_mult': 1.0, 'tp_atr_mult': 1.0, 'return_dd': 4.92, 'return_pct': 2.94, 'max_dd': -0.60, 'win_rate': 71.4, 'trades': 21},
    'trumpsol_rsi_swing': {'rsi_low': 30, 'rsi_high': 65, 'limit_offset_pct': 1.5, 'stop_atr_mult': 2.0, 'tp_atr_mult': 1.5, 'return_dd': 2.10, 'return_pct': 1.31, 'max_dd': -0.62, 'win_rate': 76.9, 'trades': 13}
}

for strategy_name, params in OPTIMIZED_PARAMS.items():
    file_path = f'bingx-trading-bot/strategies/{strategy_name}.py'
    with open(file_path, 'r') as f:
        content = f.read()
    
    coin_name = strategy_name.replace('_rsi_swing', '').upper()
    new_docstring = f'''"""
{coin_name} RSI Swing Strategy - CORRECTED RSI

Performance (90 days, 1h candles - WITH FIXED WILDER'S RSI):
- Return/DD: {params['return_dd']:.2f}x
- Return: {params['return_pct']:+.2f}%
- Max DD: {params['max_dd']:.2f}%
- Win Rate: {params['win_rate']:.1f}%
- Trades: {params['trades']}

Entry: RSI(14) crosses above {params['rsi_low']} (LONG) or below {params['rsi_high']} (SHORT)
Limit: {params['limit_offset_pct']:.1f}% offset from signal price (wait max 5 bars)
Exit: {params['stop_atr_mult']:.1f}x ATR stop loss, {params['tp_atr_mult']:.1f}x ATR take profit, or RSI reversal
"""'''
    
    content = re.sub(r'"""[\s\S]*?"""', new_docstring, content, count=1)
    content = re.sub(r"self\.rsi_low = config\.get\('rsi_low', \d+\)", f"self.rsi_low = config.get('rsi_low', {params['rsi_low']})", content)
    content = re.sub(r"self\.rsi_high = config\.get\('rsi_high', \d+\)", f"self.rsi_high = config.get('rsi_high', {params['rsi_high']})", content)
    content = re.sub(r"self\.limit_offset_pct = config\.get\('limit_offset_pct', [\d.]+\)", f"self.limit_offset_pct = config.get('limit_offset_pct', {params['limit_offset_pct']})", content)
    content = re.sub(r"self\.stop_atr_mult = config\.get\('stop_atr_mult', [\d.]+\)", f"self.stop_atr_mult = config.get('stop_atr_mult', {params['stop_atr_mult']})", content)
    content = re.sub(r"self\.tp_atr_mult = config\.get\('tp_atr_mult', [\d.]+\)", f"self.tp_atr_mult = config.get('tp_atr_mult', {params['tp_atr_mult']})", content)
    
    with open(file_path, 'w') as f:
        f.write(content)
    print(f"✅ Updated {strategy_name}.py")

print("\n✅ All strategy files updated!")
