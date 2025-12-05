"""
Strategy Unit Tests

Tests strategy pattern detection and signal generation
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from strategies.multi_timeframe_long import MultiTimeframeLongStrategy
from strategies.trend_distance_short import TrendDistanceShortStrategy


@pytest.fixture
def sample_1min_data():
    """Generate sample 1-minute OHLCV data"""
    dates = pd.date_range(start='2024-01-01', periods=300, freq='1min')
    
    df = pd.DataFrame({
        'timestamp': dates,
        'open': np.random.uniform(0.0001, 0.0002, 300),
        'high': np.random.uniform(0.0001, 0.0002, 300),
        'low': np.random.uniform(0.0001, 0.0002, 300),
        'close': np.random.uniform(0.0001, 0.0002, 300),
        'volume': np.random.uniform(1000, 10000, 300)
    })
    
    # Add required indicators (simplified)
    df['sma_50'] = df['close'].rolling(50).mean()
    df['sma_200'] = df['close'].rolling(200).mean()
    df['rsi'] = 50.0  # Neutral
    df['atr'] = df['close'] * 0.01
    df['vol_sma'] = df['volume'].rolling(20).mean()
    df['vol_ratio'] = df['volume'] / df['vol_sma']
    df['body'] = abs(df['close'] - df['open'])
    df['body_pct'] = (df['body'] / df['open']) * 100
    df['upper_wick'] = df['high'] - df[['open', 'close']].max(axis=1)
    df['lower_wick'] = df[['open', 'close']].min(axis=1) - df['low']
    df['is_bullish'] = df['close'] > df['open']
    df['is_bearish'] = df['close'] < df['open']
    df['uptrend'] = df['close'] > df['sma_50']
    df['downtrend'] = df['close'] < df['sma_50']
    df['volatility'] = df['atr'].rolling(50).mean()
    df['high_vol'] = df['atr'] > df['volatility'] * 1.1
    
    return df


class TestMultiTimeframeLongStrategy:
    """Test Multi-Timeframe LONG strategy"""
    
    def test_strategy_initialization(self):
        """Test strategy initializes correctly"""
        config = {
            'enabled': True,
            'base_risk_pct': 1.0,
            'max_risk_pct': 3.0,
            'max_positions': 1,
            'params': {
                'body_threshold': 1.2,
                'volume_multiplier': 3.0
            }
        }
        
        strategy = MultiTimeframeLongStrategy(config)
        assert strategy.name == 'multi_timeframe_long'
        assert strategy.body_threshold == 1.2
        assert strategy.enabled == True
    
    def test_no_signal_insufficient_data(self, sample_1min_data):
        """Test no signal generated with insufficient data"""
        config = {
            'enabled': True,
            'params': {}
        }
        
        strategy = MultiTimeframeLongStrategy(config)
        df_small = sample_1min_data.head(100)  # Only 100 candles
        
        signal = strategy.analyze(df_small)
        assert signal is None
    
    def test_position_size_calculation(self):
        """Test position sizing"""
        config = {'enabled': True, 'params': {}}
        strategy = MultiTimeframeLongStrategy(config)
        
        entry_price = 0.0001
        stop_price = 0.00009
        capital = 10000
        
        position_size = strategy.calculate_position_size(entry_price, stop_price, capital)
        assert position_size > 0
        assert position_size <= capital * 0.4  # Max 40% of capital


class TestTrendDistanceShortStrategy:
    """Test Trend+Distance SHORT strategy"""
    
    def test_strategy_initialization(self):
        """Test strategy initializes correctly"""
        config = {
            'enabled': True,
            'base_risk_pct': 1.5,
            'max_risk_pct': 4.0,
            'max_positions': 1,
            'params': {
                'body_threshold': 1.2,
                'distance_from_50sma': 2.0
            }
        }
        
        strategy = TrendDistanceShortStrategy(config)
        assert strategy.name == 'trend_distance_short'
        assert strategy.distance_from_50sma == 2.0
    
    def test_risk_scaling_on_win(self):
        """Test risk increases on win streak"""
        config = {'enabled': True, 'base_risk_pct': 1.0, 'max_risk_pct': 3.0, 'params': {}}
        strategy = TrendDistanceShortStrategy(config)
        
        initial_risk = strategy.current_risk_pct
        strategy.update_risk_sizing(trade_won=True)
        
        assert strategy.win_streak == 1
        assert strategy.current_risk_pct > initial_risk
    
    def test_risk_resets_on_loss(self):
        """Test risk resets on loss"""
        config = {'enabled': True, 'base_risk_pct': 1.0, 'max_risk_pct': 3.0, 'params': {}}
        strategy = TrendDistanceShortStrategy(config)
        
        strategy.update_risk_sizing(trade_won=True)
        strategy.update_risk_sizing(trade_won=False)
        
        assert strategy.loss_streak == 1
        assert strategy.win_streak == 0
        assert strategy.current_risk_pct == strategy.base_risk_pct


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
