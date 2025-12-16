import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
import time

print("="*80)
print("DOGE VOLUME ZONES - 30 DAY ANALYSIS (BingX)")
print("="*80)

def download_bingx_data(symbol, days=30):
    """Download data from BingX"""
    base_url = "https://open-api.bingx.com/openApi/swap/v3/quote/klines"
    all_data = []
    end_time = int(datetime.now().timestamp() * 1000)
    target_start = datetime.now() - timedelta(days=days)
    target_start_ms = int(target_start.timestamp() * 1000)

    batch = 0
    while True:
        batch += 1
        params = {"symbol": symbol, "interval": "1m", "endTime": end_time, "limit": 1440}
        response = requests.get(base_url, params=params, timeout=30)
        data = response.json()

        if 'data' not in data or not data['data']:
            break

        batch_data = data['data']
        all_data = batch_data + all_data

        oldest_ts = int(batch_data[0]['time'])
        if oldest_ts <= target_start_ms:
            break

        end_time = oldest_ts - 1

        if batch % 10 == 0:
            print(f"   Batch {batch}: {len(all_data)} candles...")

        time.sleep(0.1)

    df = pd.DataFrame(all_data)
    df['timestamp'] = pd.to_datetime(df['time'].astype(int), unit='ms')
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)

    cutoff = datetime.now() - timedelta(days=days)
    df = df[df['timestamp'] >= cutoff]

    return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].sort_values('timestamp').reset_index(drop=True)

print("\n1. DOWNLOADING 30 DAYS...")
df = download_bingx_data('DOGE-USDT', days=30)
print(f"   Downloaded {len(df)} candles")
print(f"   Range: {df['timestamp'].min()} to {df['timestamp'].max()}")

print("\n2. CALCULATING INDICATORS...")
tr = np.maximum(df['high'] - df['low'],
                np.maximum(abs(df['high'] - df['close'].shift(1)),
                          abs(df['low'] - df['close'].shift(1))))
df['atr'] = tr.rolling(14).mean()
df['vol_ma'] = df['volume'].rolling(20).mean()
df['vol_ratio'] = df['volume'] / df['vol_ma']
df['hour_utc'] = df['timestamp'].dt.hour

print("\n3. COMPARING 72h vs 30d CONDITIONS...")
cutoff_72h = df['timestamp'].max() - timedelta(hours=72)
df_72h = df[df['timestamp'] >= cutoff_72h]

print(f"\n{'Metric':<25} {'72h':<12} {'30d':<12} {'Diff':<10}")
print("-"*60)
print(f"{'Avg Volume':<25} {df_72h['volume'].mean():<12.0f} {df['volume'].mean():<12.0f} {(df_72h['volume'].mean()/df['volume'].mean()-1)*100:+.1f}%")
print(f"{'Avg Vol Ratio':<25} {df_72h['vol_ratio'].mean():<12.2f} {df['vol_ratio'].mean():<12.2f}")
print(f"{'High vol bars (>=1.5x)':<25} {(df_72h['vol_ratio']>=1.5).sum():<12} {(df['vol_ratio']>=1.5).sum():<12}")
print(f"{'% high vol':<25} {(df_72h['vol_ratio']>=1.5).sum()/len(df_72h)*100:<12.1f} {(df['vol_ratio']>=1.5).sum()/len(df)*100:<12.1f}")

def backtest_doge_asia_eu(df):
    """Asia/EU session (07-14 UTC), 1.5x ATR SL, 4x ATR TP"""
    SL_MULT, TP_MULT, MAX_HOLD, FEE = 1.5, 4.0, 90, 0.10
    trades = []
    in_zone, zone_bars = False, 0
    zone_highs, zone_lows = [], []

    for i in range(50, len(df) - MAX_HOLD):
        row = df.iloc[i]
        hour = row['hour_utc']
        if not (7 <= hour < 14):
            in_zone, zone_bars, zone_highs, zone_lows = False, 0, [], []
            continue
        vol_ratio = row['vol_ratio'] if not pd.isna(row['vol_ratio']) else 0
        if vol_ratio >= 1.5:
            if not in_zone:
                in_zone, zone_bars = True, 1
                zone_highs, zone_lows = [row['high']], [row['low']]
            else:
                zone_bars += 1
                zone_highs.append(row['high'])
                zone_lows.append(row['low'])
        else:
            if in_zone and zone_bars >= 5:
                zone_high, zone_low = max(zone_highs), min(zone_lows)
                lookback = df.iloc[max(0,i-25):i]
                window_low, window_high = lookback['low'].min(), lookback['high'].max()
                entry, atr = row['close'], row['atr']
                direction = None
                if zone_low <= window_low * 1.002:
                    direction = 'LONG'
                elif zone_high >= window_high * 0.998:
                    direction = 'SHORT'
                if direction and not pd.isna(atr):
                    sl = entry - SL_MULT*atr if direction=='LONG' else entry + SL_MULT*atr
                    tp = entry + TP_MULT*atr if direction=='LONG' else entry - TP_MULT*atr
                    for j in range(i+1, min(i+MAX_HOLD+1, len(df))):
                        if direction == 'LONG':
                            if df.iloc[j]['low'] <= sl:
                                trades.append({'dir':direction,'pnl':-SL_MULT*atr/entry*100-FEE,'exit':'SL'})
                                break
                            if df.iloc[j]['high'] >= tp:
                                trades.append({'dir':direction,'pnl':TP_MULT*atr/entry*100-FEE,'exit':'TP'})
                                break
                        else:
                            if df.iloc[j]['high'] >= sl:
                                trades.append({'dir':direction,'pnl':-SL_MULT*atr/entry*100-FEE,'exit':'SL'})
                                break
                            if df.iloc[j]['low'] <= tp:
                                trades.append({'dir':direction,'pnl':TP_MULT*atr/entry*100-FEE,'exit':'TP'})
                                break
                    else:
                        exit_p = df.iloc[min(i+MAX_HOLD, len(df)-1)]['close']
                        pnl = ((exit_p-entry)/entry if direction=='LONG' else (entry-exit_p)/entry)*100-FEE
                        trades.append({'dir':direction,'pnl':pnl,'exit':'TIME'})
            in_zone, zone_bars, zone_highs, zone_lows = False, 0, [], []
    return trades

def analyze(trades, days):
    if not trades:
        return {'trades':0,'tpd':0,'wr':0,'pnl':0,'dd':0,'rdd':0,'tp_rate':0}
    tdf = pd.DataFrame(trades)
    tdf['cum'] = tdf['pnl'].cumsum()
    equity = 100 + tdf['cum']
    dd = ((equity - equity.cummax()) / equity.cummax() * 100).min()
    pnl = tdf['pnl'].sum()
    return {
        'trades':len(trades),'tpd':len(trades)/days,'wr':(tdf['pnl']>0).mean()*100,
        'pnl':pnl,'dd':dd,'rdd':pnl/abs(dd) if dd!=0 else 0,
        'tp_rate':(tdf['exit']=='TP').sum()/len(tdf)*100
    }

print("\n4. BACKTEST RESULTS...")
trades_30d = backtest_doge_asia_eu(df)
trades_72h = backtest_doge_asia_eu(df_72h)

r_30d = analyze(trades_30d, 30)
r_72h = analyze(trades_72h, 3)

print(f"\n{'Metric':<20} {'30d':<12} {'72h':<12} {'Original':<12}")
print("-"*60)
print(f"{'Trades':<20} {r_30d['trades']:<12} {r_72h['trades']:<12} 22")
print(f"{'T/day':<20} {r_30d['tpd']:<12.2f} {r_72h['tpd']:<12.2f} 0.69")
print(f"{'WR %':<20} {r_30d['wr']:<12.1f} {r_72h['wr']:<12.1f} 63.6")
print(f"{'TP Rate %':<20} {r_30d['tp_rate']:<12.1f} {r_72h['tp_rate']:<12.1f} -")
print(f"{'P/L %':<20} {r_30d['pnl']:<+12.2f} {r_72h['pnl']:<+12.2f} +5.15")
print(f"{'Max DD %':<20} {r_30d['dd']:<12.2f} {r_72h['dd']:<12.2f} -0.48")
print(f"{'Return/DD':<20} {r_30d['rdd']:<12.2f} {r_72h['rdd']:<12.2f} 10.75")

if trades_30d:
    tdf = pd.DataFrame(trades_30d)
    long_pnl = tdf[tdf['dir']=='LONG']['pnl'].sum()
    short_pnl = tdf[tdf['dir']=='SHORT']['pnl'].sum()
    print(f"\n5. DIRECTION BREAKDOWN (30d):")
    print(f"   LONG:  {len(tdf[tdf['dir']=='LONG'])} trades, P/L={long_pnl:+.2f}%")
    print(f"   SHORT: {len(tdf[tdf['dir']=='SHORT'])} trades, P/L={short_pnl:+.2f}%")

    top5 = tdf.nlargest(5, 'pnl')['pnl'].sum()
    print(f"\n   Top 5 trades: {top5:+.2f}% ({top5/r_30d['pnl']*100:.1f}% of total)")

print("\n" + "="*80)
print("CONCLUSION:")
print("="*80)
print(f"""
Original backtest: LBank data, Overnight session (21-07 UTC)
Current test: BingX data, Asia/EU session (07-14 UTC) per CLAUDE.md

BingX performance vs Original:
- Trades/day: {r_30d['tpd']:.2f} vs 0.69 ({(r_30d['tpd']/0.69-1)*100:+.0f}%)
- Win Rate: {r_30d['wr']:.1f}% vs 63.6% ({r_30d['wr']-63.6:+.1f}pp)
- Return/DD: {r_30d['rdd']:.2f}x vs 10.75x ({(r_30d['rdd']/10.75-1)*100:+.0f}%)

Strategy appears to be performing {'WORSE' if r_30d['rdd'] < 5 else 'DIFFERENTLY'} on BingX vs original LBank data.
72h period is {'WORSE' if r_72h['pnl'] < 0 else 'SIMILAR'} than 30d average.
""")
