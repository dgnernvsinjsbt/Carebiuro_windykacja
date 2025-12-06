"""
Integration Tests

Tests complete trading flow and component integration
"""

import pytest
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config
from database.trade_logger import TradeLogger
from monitoring.metrics import PerformanceTracker


class TestConfiguration:
    """Test configuration loading"""
    
    def test_config_loads_successfully(self):
        """Test config file loads"""
        config = Config('../config.yaml')
        # Config should raise error if file doesn't exist
        # This tests the path is correct


class TestDatabase:
    """Test database operations"""
    
    def test_database_initialization(self):
        """Test database initializes"""
        db = TradeLogger('sqlite:///:memory:', echo=False)
        stats = db.get_statistics()
        
        assert stats['total_trades'] == 0
        assert stats['open_trades'] == 0


class TestPerformanceTracking:
    """Test performance metrics"""
    
    def test_tracker_initialization(self):
        """Test tracker initializes correctly"""
        tracker = PerformanceTracker(initial_capital=10000)
        
        summary = tracker.get_summary()
        assert summary['capital']['initial'] == 10000
        assert summary['capital']['current'] == 10000
        assert summary['trades']['total'] == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
