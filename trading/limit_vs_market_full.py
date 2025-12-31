"""
Pełne porównanie: Market vs Limit Entry
Z uwzględnieniem compounding i lepszych cen
"""
import pandas as pd
import numpy as np

# Load data
df = pd.read_csv('trading/doge_1h_jun_dec_2025.csv', parse_dates=['timestamp'])

# Parameters
PERIOD = 15
TP_ATR = 4.0
SL_ATR = 4.0
RISK_PCT = 3.0
MAX_LEVERAGE = 5.0
FEE_PCT = 0.07
LIMIT_OFFSET_PCT = 0.5
WAIT_BARS = 1

# Calculate indicators
df['atr'] = (df['high'] - df['low']).rolling(14).mean()
df['donchian_upper'] = df['high'].rolling(PERIOD).max().shift(1)
df['donchian_lower'] = df['low'].rolling(PERIOD).min().shift(1)

def backtest(use_limit=False, offset_pct=0.5, wait_bars=1):
    """Backtest z market lub limit orders"""
    equity = 100.0
    max_equity = equity
    max_dd = 0
    trades = []
    
    i = PERIOD + 14
    while i < len(df) - 50:
        row = df.iloc[i]
        atr = row['atr']
        
        # Check for signal
        signal_dir = None
        if row['close'] > row['donchian_upper']:
            signal_dir = 'LONG'
            signal_price = row['close']
        elif row['close'] < row['donchian_lower']:
            signal_dir = 'SHORT'
            signal_price = row['close']
        
        if signal_dir is None:
            i += 1
            continue
        
        # MARKET ORDER: enter immediately
        if not use_limit:
            entry_price = signal_price
            entry_bar = i
        else:
            # LIMIT ORDER: calculate limit price and wait
            if signal_dir == 'LONG':
                limit_price = signal_price * (1 - offset_pct / 100)
            else:
                limit_price = signal_price * (1 + offset_pct / 100)
            
            # Check if filled within wait_bars
            filled = False
            for j in range(1, wait_bars + 1):
                if i + j >= len(df):
                    break
                candle = df.iloc[i + j]
                if signal_dir == 'LONG' and candle['low'] <= limit_price:
                    filled = True
                    entry_price = limit_price
                    entry_bar = i + j
                    break
                elif signal_dir == 'SHORT' and candle['high'] >= limit_price:
                    filled = True
                    entry_price = limit_price
                    entry_bar = i + j
                    break
            
            if not filled:
                i += 1
                continue
        
        # Calculate TP/SL from ENTRY PRICE (not signal price!)
        if signal_dir == 'LONG':
            tp_price = entry_price + TP_ATR * atr
            sl_price = entry_price - SL_ATR * atr
        else:
            tp_price = entry_price - TP_ATR * atr
            sl_price = entry_price + SL_ATR * atr
        
        # Calculate position size
        if signal_dir == 'LONG':
            sl_dist_pct = (entry_price - sl_price) / entry_price * 100
        else:
            sl_dist_pct = (sl_price - entry_price) / entry_price * 100
        
        leverage = min(RISK_PCT / sl_dist_pct, MAX_LEVERAGE)
        
        # Simulate trade
        outcome = None
        exit_price = None
        
        for j in range(entry_bar + 1, min(entry_bar + 100, len(df))):
            candle = df.iloc[j]
            
            if signal_dir == 'LONG':
                if candle['low'] <= sl_price:
                    outcome = 'SL'
                    exit_price = sl_price
                    exit_bar = j
                    break
                if candle['high'] >= tp_price:
                    outcome = 'TP'
                    exit_price = tp_price
                    exit_bar = j
                    break
            else:
                if candle['high'] >= sl_price:
                    outcome = 'SL'
                    exit_price = sl_price
                    exit_bar = j
                    break
                if candle['low'] <= tp_price:
                    outcome = 'TP'
                    exit_price = tp_price
                    exit_bar = j
                    break
        
        if outcome is None:
            i += 1
            continue
        
        # Calculate PnL
        if signal_dir == 'LONG':
            pnl_pct = (exit_price - entry_price) / entry_price * 100
        else:
            pnl_pct = (entry_price - exit_price) / entry_price * 100
        
        # Apply fees
        pnl_pct -= 2 * FEE_PCT
        
        # Update equity
        equity_change = leverage * pnl_pct / 100
        equity *= (1 + equity_change)
        
        # Update max drawdown
        max_equity = max(max_equity, equity)
        dd = (max_equity - equity) / max_equity * 100
        max_dd = max(max_dd, dd)
        
        trades.append({
            'outcome': outcome,
            'pnl_pct': pnl_pct,
            'entry_price': entry_price,
            'signal_price': signal_price if use_limit else entry_price,
            'improvement': (signal_price - entry_price) / signal_price * 100 if signal_dir == 'LONG' else (entry_price - signal_price) / signal_price * 100
        })
        
        i = exit_bar + 1
    
    return {
        'equity': equity,
        'return_pct': (equity / 100 - 1) * 100,
        'max_dd': max_dd,
        'rr_ratio': (equity / 100 - 1) * 100 / max_dd if max_dd > 0 else 0,
        'trades': len(trades),
        'wins': sum(1 for t in trades if t['outcome'] == 'TP'),
        'losses': sum(1 for t in trades if t['outcome'] == 'SL'),
        'avg_improvement': np.mean([t['improvement'] for t in trades]) if trades else 0
    }

print("="*70)
print("MARKET vs LIMIT ORDER - PEŁNA SYMULACJA")
print("="*70)

# Market orders
market = backtest(use_limit=False)
print(f"\n📊 MARKET ORDER (wchodzimy od razu):")
print(f"   Trades: {market['trades']} ({market['wins']}W / {market['losses']}L)")
print(f"   Win Rate: {market['wins'] / (market['wins'] + market['losses']) * 100:.1f}%")
print(f"   Return: +{market['return_pct']:.1f}%")
print(f"   Max DD: -{market['max_dd']:.1f}%")
print(f"   R:R Ratio: {market['rr_ratio']:.2f}x")

# Limit orders
limit = backtest(use_limit=True, offset_pct=0.5, wait_bars=1)
print(f"\n📊 LIMIT ORDER (0.5% offset, 1 bar wait):")
print(f"   Trades: {limit['trades']} ({limit['wins']}W / {limit['losses']}L)")
print(f"   Win Rate: {limit['wins'] / (limit['wins'] + limit['losses']) * 100:.1f}%")
print(f"   Return: +{limit['return_pct']:.1f}%")
print(f"   Max DD: -{limit['max_dd']:.1f}%")
print(f"   R:R Ratio: {limit['rr_ratio']:.2f}x")
print(f"   Avg Entry Improvement: {limit['avg_improvement']:.2f}%")

print("\n" + "="*70)
print("PODSUMOWANIE")
print("="*70)
print(f"\nZmiana R:R: {market['rr_ratio']:.2f}x → {limit['rr_ratio']:.2f}x ({(limit['rr_ratio']/market['rr_ratio']-1)*100:+.1f}%)")
print(f"Zmiana Return: +{market['return_pct']:.1f}% → +{limit['return_pct']:.1f}%")
print(f"Zmiana Trades: {market['trades']} → {limit['trades']} (-{market['trades']-limit['trades']})")

# Test różnych offsetów
print("\n" + "="*70)
print("TEST RÓŻNYCH OFFSETÓW (1 bar wait)")
print("="*70)
print(f"{'Offset':<10} {'Trades':<10} {'WR%':<10} {'Return':<12} {'MaxDD':<10} {'R:R':<10}")
print("-"*62)

for offset in [0.1, 0.2, 0.3, 0.4, 0.5, 0.75, 1.0]:
    r = backtest(use_limit=True, offset_pct=offset, wait_bars=1)
    wr = r['wins'] / (r['wins'] + r['losses']) * 100 if r['trades'] > 0 else 0
    print(f"{offset}%{'':<6} {r['trades']:<10} {wr:<10.1f} +{r['return_pct']:<10.1f}% -{r['max_dd']:<8.1f}% {r['rr_ratio']:<10.2f}x")

print("-"*62)
print(f"Market{'':<3} {market['trades']:<10} {market['wins']/(market['wins']+market['losses'])*100:<10.1f} +{market['return_pct']:<10.1f}% -{market['max_dd']:<8.1f}% {market['rr_ratio']:<10.2f}x")

