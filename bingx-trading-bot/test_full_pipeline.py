#!/usr/bin/env python3
"""
Full Pipeline Test - All 8 Coins with Historical Data
Tests signal generation end-to-end without API connection
"""
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from strategies.donchian_breakout import DonchianBreakout, COIN_PARAMS
from data.indicators import IndicatorCalculator

DATA_DIR = Path(__file__).parent.parent / 'trading'

# Map symbols to data files
DATA_FILES = {
    'PENGU-USDT': 'pengu_1h_jun_dec_2025.csv',
    'DOGE-USDT': 'doge_1h_jun_dec_2025.csv',
    'FARTCOIN-USDT': 'fartcoin_1h_jun_dec_2025.csv',
    'ETH-USDT': 'eth_1h_2025.csv',
    'UNI-USDT': 'uni_1h_jun_dec_2025.csv',
    'PI-USDT': 'pi_1h_jun_dec_2025.csv',
    'CRV-USDT': 'crv_1h_jun_dec_2025.csv',
    'AIXBT-USDT': 'aixbt_1h_jun_dec_2025.csv',
}

def test_coin(symbol: str) -> dict:
    """Test signal generation for one coin"""
    
    data_file = DATA_DIR / DATA_FILES.get(symbol, '')
    if not data_file.exists():
        return {'symbol': symbol, 'status': 'NO_DATA', 'signals': 0}
    
    # Load data
    df = pd.read_csv(data_file)
    df.columns = [c.lower() for c in df.columns]
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    for col in ['open', 'high', 'low', 'close', 'volume']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Calculate indicators
    calc = IndicatorCalculator(df)
    df = calc.add_all_indicators()
    
    # Create strategy
    config = {'enabled': True, 'risk_pct': 3.0, 'max_leverage': 5.0}
    strategy = DonchianBreakout(config, symbol)
    
    # Simulate last 100 bars (most recent period)
    signals = []
    start_idx = max(len(df) - 100, strategy.period + 14)
    
    for i in range(start_idx, len(df)):
        df_slice = df.iloc[:i+1].copy()
        signal = strategy.generate_signals(df_slice, current_positions=[])
        if signal:
            signals.append({
                'timestamp': df_slice.iloc[-1]['timestamp'],
                'direction': signal['direction'],
                'entry': signal['entry_price'],
                'sl': signal['stop_loss'],
                'tp': signal['take_profit']
            })
    
    return {
        'symbol': symbol,
        'status': 'OK',
        'data_rows': len(df),
        'signals': len(signals),
        'longs': sum(1 for s in signals if s['direction'] == 'LONG'),
        'shorts': sum(1 for s in signals if s['direction'] == 'SHORT'),
        'params': f"TP={strategy.tp_atr}, SL={strategy.sl_atr}, P={strategy.period}",
        'last_signal': signals[-1] if signals else None
    }

if __name__ == '__main__':
    print("=" * 80)
    print("FULL PIPELINE TEST - ALL 8 COINS")
    print("Testing signal generation with historical data")
    print("=" * 80)
    
    results = []
    for symbol in COIN_PARAMS.keys():
        print(f"\nTesting {symbol}...")
        result = test_coin(symbol)
        results.append(result)
        
        if result['status'] == 'OK':
            print(f"  ✅ {result['signals']} signals ({result['longs']}L/{result['shorts']}S)")
            print(f"     Params: {result['params']}")
            if result['last_signal']:
                ls = result['last_signal']
                print(f"     Last: {ls['timestamp']} {ls['direction']} @ ${ls['entry']:.4f}")
        else:
            print(f"  ❌ {result['status']}")
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    ok_count = sum(1 for r in results if r['status'] == 'OK')
    total_signals = sum(r.get('signals', 0) for r in results)
    
    print(f"\nCoins tested: {ok_count}/{len(COIN_PARAMS)}")
    print(f"Total signals generated: {total_signals}")
    
    print(f"\n{'Symbol':<15} {'Status':<10} {'Signals':<10} {'Params':<25}")
    print("-" * 60)
    for r in results:
        status = "✅ OK" if r['status'] == 'OK' else "❌ " + r['status']
        signals = r.get('signals', 0)
        params = r.get('params', 'N/A')
        print(f"{r['symbol']:<15} {status:<10} {signals:<10} {params:<25}")
    
    if ok_count == len(COIN_PARAMS):
        print("\n🎉 ALL 8 COINS WORKING - Pipeline is ready!")
    else:
        print(f"\n⚠️ {len(COIN_PARAMS) - ok_count} coins missing data files")
