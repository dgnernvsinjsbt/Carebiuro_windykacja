"""
Analiza zmienności i trendowności dla wszystkich coinów z BingX
Cel: Znaleźć top 3 coiny pod trend following
"""

import pandas as pd
import numpy as np
from pathlib import Path

def calculate_metrics(df, coin_name):
    """Oblicz metryki zmienności i trendowności"""

    # Podstawowe statystyki
    df['returns'] = df['close'].pct_change()

    # 1. VOLATILITY METRICS
    daily_volatility = df['returns'].std() * np.sqrt(1440)  # annualized dla 1m
    max_1d_pump = df['close'].pct_change(1440).max() * 100  # max wzrost w 1 dzień
    max_1d_dump = df['close'].pct_change(1440).min() * 100  # max spadek w 1 dzień
    avg_candle_range = ((df['high'] - df['low']) / df['close'] * 100).mean()

    # 2. TREND FOLLOWING METRICS

    # a) ADX (Average Directional Index) - siła trendu
    def calculate_adx(high, low, close, period=14):
        """ADX: >25 = trend, <20 = chop"""
        plus_dm = high.diff()
        minus_dm = -low.diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0

        tr = pd.concat([
            high - low,
            abs(high - close.shift()),
            abs(low - close.shift())
        ], axis=1).max(axis=1)

        atr = tr.rolling(period).mean()
        plus_di = 100 * (plus_dm.rolling(period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(period).mean() / atr)

        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(period).mean()

        return adx

    df['adx'] = calculate_adx(df['high'], df['low'], df['close'])
    avg_adx = df['adx'].mean()
    pct_trending = (df['adx'] > 25).sum() / len(df) * 100  # % czasu w trendzie

    # b) Autocorrelation - momentum persistence
    # Pozytywna autocorrelacja = trendy trwają
    autocorr_1 = df['returns'].autocorr(lag=1)
    autocorr_5 = df['returns'].autocorr(lag=5)
    autocorr_15 = df['returns'].autocorr(lag=15)

    # c) Trend Strength - % dni z wyraźnym trendem
    df['sma20'] = df['close'].rolling(20).mean()
    df['sma50'] = df['close'].rolling(50).mean()
    trend_up = (df['close'] > df['sma20']) & (df['sma20'] > df['sma50'])
    trend_down = (df['close'] < df['sma20']) & (df['sma20'] < df['sma50'])
    pct_in_clear_trend = ((trend_up | trend_down).sum() / len(df) * 100)

    # d) Average Trend Duration (w minutach)
    df['in_trend'] = (df['adx'] > 25).astype(int)
    trend_changes = df['in_trend'].diff().fillna(0)
    trend_starts = (trend_changes == 1)
    trend_ends = (trend_changes == -1)

    if trend_starts.sum() > 0:
        avg_trend_duration = len(df[df['in_trend'] == 1]) / trend_starts.sum()
    else:
        avg_trend_duration = 0

    # 3. PUMP/DUMP CHARACTERISTICS

    # Top 10 największych świec (% zmiana)
    top_pumps = df['returns'].nlargest(10).mean() * 100
    top_dumps = df['returns'].nsmallest(10).mean() * 100

    # Skewness - asymetria (dodatnia = więcej pumpów)
    skewness = df['returns'].skew()

    # Kurtosis - "fat tails" (wysokie wartości = ekstremalne ruchy)
    kurtosis = df['returns'].kurtosis()

    # 4. TREND FOLLOWING SCORE (composite)
    # Wyższy = lepszy dla trend following
    trend_score = (
        (avg_adx / 30) * 0.3 +  # ADX strength (normalized)
        (pct_trending / 50) * 0.2 +  # % czasu w trendzie
        (autocorr_15 + 1) * 0.2 +  # Momentum persistence
        (pct_in_clear_trend / 50) * 0.2 +  # Clear trends
        (avg_trend_duration / 100) * 0.1  # Trend duration
    ) * 100

    return {
        'Coin': coin_name,

        # Volatility
        'Daily_Vol_%': round(daily_volatility * 100, 2),
        'Max_1D_Pump_%': round(max_1d_pump, 2),
        'Max_1D_Dump_%': round(max_1d_dump, 2),
        'Avg_Candle_Range_%': round(avg_candle_range, 3),

        # Trend Metrics
        'Avg_ADX': round(avg_adx, 1),
        'Pct_Trending': round(pct_trending, 1),
        'Autocorr_1m': round(autocorr_1, 3),
        'Autocorr_5m': round(autocorr_5, 3),
        'Autocorr_15m': round(autocorr_15, 3),
        'Pct_Clear_Trend': round(pct_in_clear_trend, 1),
        'Avg_Trend_Duration_mins': round(avg_trend_duration, 0),

        # Pump/Dump
        'Top10_Pumps_%': round(top_pumps, 3),
        'Top10_Dumps_%': round(top_dumps, 3),
        'Skewness': round(skewness, 2),
        'Kurtosis': round(kurtosis, 1),

        # Overall Score
        'Trend_Following_Score': round(trend_score, 1)
    }


def main():
    # BingX coins
    coins = {
        'DOGE': 'doge_30d_bingx.csv',
        'FARTCOIN': 'fartcoin_30d_bingx.csv',
        'MOODENG': 'moodeng_30d_bingx.csv',
        'PEPE': 'pepe_30d_bingx.csv',
        'TRUMPSOL': 'trumpsol_30d_bingx.csv',
        'UNI': 'uni_30d_bingx.csv'
    }

    results = []

    for coin_name, filename in coins.items():
        filepath = Path('/workspaces/Carebiuro_windykacja/trading') / filename

        if not filepath.exists():
            print(f"⚠️  Brak pliku: {filename}")
            continue

        print(f"📊 Analizuję {coin_name}...")

        df = pd.read_csv(filepath)
        df.columns = df.columns.str.lower()

        # Konwersja timestamp jeśli potrzeba
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])

        metrics = calculate_metrics(df, coin_name)
        results.append(metrics)

    # DataFrame wyników
    df_results = pd.DataFrame(results)

    # Sortowanie
    df_volatility = df_results.sort_values('Daily_Vol_%', ascending=False)
    df_trend = df_results.sort_values('Trend_Following_Score', ascending=False)

    print("\n" + "="*100)
    print("🚀 RANKING: NAJBARDZIEJ ZMIENNE (PUMP/DUMP)")
    print("="*100)
    print(df_volatility[['Coin', 'Daily_Vol_%', 'Max_1D_Pump_%', 'Max_1D_Dump_%',
                          'Top10_Pumps_%', 'Top10_Dumps_%', 'Kurtosis']].to_string(index=False))

    print("\n" + "="*100)
    print("📈 RANKING: NAJLEPSZE POD TREND FOLLOWING")
    print("="*100)
    print(df_trend[['Coin', 'Trend_Following_Score', 'Avg_ADX', 'Pct_Trending',
                     'Autocorr_15m', 'Avg_Trend_Duration_mins']].to_string(index=False))

    print("\n" + "="*100)
    print("📋 PEŁNA TABELA")
    print("="*100)
    print(df_results.to_string(index=False))

    # Eksport
    output_path = '/workspaces/Carebiuro_windykacja/trading/results/bingx_volatility_analysis.csv'
    df_results.to_csv(output_path, index=False)
    print(f"\n✅ Zapisano: {output_path}")

    # TOP 3 RECOMMENDATION
    print("\n" + "="*100)
    print("⭐ REKOMENDACJA TOP 3 POD TREND FOLLOWING")
    print("="*100)
    top3 = df_trend.head(3)
    for i, row in top3.iterrows():
        print(f"\n{i+1}. {row['Coin']}")
        print(f"   Score: {row['Trend_Following_Score']}")
        print(f"   ADX: {row['Avg_ADX']} | Trending: {row['Pct_Trending']}% czasu")
        print(f"   Momentum Persistence: {row['Autocorr_15m']}")
        print(f"   Avg Trend: {row['Avg_Trend_Duration_mins']} minut")


if __name__ == '__main__':
    main()
