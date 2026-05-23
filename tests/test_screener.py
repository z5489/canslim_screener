import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np
from datetime import datetime, timezone

# Add parent directory to sys.path so we can import scripts
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts.fetch_batch import evaluate_criteria

class TestCanslimScreener(unittest.TestCase):
    
    def setUp(self):
        # Create standard passing mock data
        self.mock_info = {
            'longName': 'Test Stock',
            'currentPrice': 100.0,
            'fiftyTwoWeekLow': 50.0,  # 100 >= 50 * 1.70 (+100% > +70%)
            'marketCap': 500_000_000, # >= 300M
            'averageVolume': 600_000, # > 500K
            'floatShares': 100_000_000, # <= 150M
            'exchange': 'NMS'        # US Market
        }
        
        # 3 months of historical data (60 business days)
        # Price rising from 90 to 100, so price >= SMA 50.
        dates = pd.date_range(end=datetime.now(), periods=60, freq='B')
        self.mock_hist = pd.DataFrame({
            'Open': np.linspace(90, 100, 60),
            'High': np.linspace(95, 105, 60), # High is ~6-7% above low, yielding >3% volatility
            'Low': np.linspace(89, 99, 60),
            'Close': np.linspace(90, 100, 60),
            'Volume': [600_000] * 60
        }, index=dates)
        
        # 5 quarters of income statements
        # EPS growth: 1.0 -> 1.5 (+50% > +25%)
        # Revenue growth: 10M -> 15M (+50% > +25%)
        quarters = pd.to_datetime(['2026-03-31', '2025-12-31', '2025-09-30', '2025-06-30', '2025-03-31'])
        self.mock_inc = pd.DataFrame({
            quarters[0]: [1.5, 15_000_000.0],
            quarters[1]: [1.4, 14_000_000.0],
            quarters[2]: [1.3, 13_000_000.0],
            quarters[3]: [1.2, 12_000_000.0],
            quarters[4]: [1.0, 10_000_000.0]
        }, index=['Diluted EPS', 'Total Revenue'])

    @patch('scripts.fetch_batch.yf.Ticker')
    def test_evaluate_criteria_passing(self, mock_ticker_cls):
        # Setup mock Ticker instance
        mock_ticker = MagicMock()
        mock_ticker.info = self.mock_info
        mock_ticker.history.return_ok = True
        mock_ticker.history.return_value = self.mock_hist
        mock_ticker.quarterly_income_stmt = self.mock_inc
        mock_ticker_cls.return_value = mock_ticker
        
        res = evaluate_criteria("TEST")
        
        self.assertEqual(res["ticker"], "TEST")
        self.assertEqual(res["name"], "Test Stock")
        self.assertEqual(res["price"], 100.0)
        self.assertTrue(res["c1_price_vs_52w_low_passes"])
        self.assertTrue(res["c2_market_cap_passes"])
        self.assertTrue(res["c3_eps_growth_passes"])
        self.assertTrue(res["c4_avg_volume_passes"])
        self.assertTrue(res["c5_price_vs_sma50_passes"])
        self.assertTrue(res["c6_volatility_1m_passes"])
        self.assertTrue(res["c7_revenue_growth_passes"])
        self.assertTrue(res["c8_float_passes"])
        self.assertTrue(res["c9_us_market_passes"])
        self.assertTrue(res["passes_all"])
        self.assertEqual(res["error"], "")

    @patch('scripts.fetch_batch.yf.Ticker')
    def test_evaluate_criteria_failing_some(self, mock_ticker_cls):
        # Modify mock to fail C1 (price vs 52w low) and C8 (float too high)
        info = self.mock_info.copy()
        info['fiftyTwoWeekLow'] = 90.0 # 100.0 is not >= 90.0 * 1.70 (153.0)
        info['floatShares'] = 200_000_000 # > 150M
        
        mock_ticker = MagicMock()
        mock_ticker.info = info
        mock_ticker.history.return_value = self.mock_hist
        mock_ticker.quarterly_income_stmt = self.mock_inc
        mock_ticker_cls.return_value = mock_ticker
        
        res = evaluate_criteria("TEST")
        
        self.assertFalse(res["c1_price_vs_52w_low_passes"])
        self.assertFalse(res["c8_float_passes"])
        self.assertTrue(res["c2_market_cap_passes"]) # still passes cap
        self.assertFalse(res["passes_all"]) # overall false

    @patch('scripts.fetch_batch.yf.Ticker')
    def test_evaluate_criteria_missing_quarterly_data(self, mock_ticker_cls):
        # Income stmt is empty
        mock_ticker = MagicMock()
        mock_ticker.info = self.mock_info
        mock_ticker.history.return_value = self.mock_hist
        mock_ticker.quarterly_income_stmt = pd.DataFrame() # Empty
        mock_ticker_cls.return_value = mock_ticker
        
        res = evaluate_criteria("TEST")
        
        # Missing quarterly data should lead to N/A (None) in passes and "N/A" in value
        self.assertIsNone(res["c3_eps_growth_passes"])
        self.assertEqual(res["c3_eps_growth_value"], "N/A")
        self.assertIsNone(res["c7_revenue_growth_passes"])
        self.assertEqual(res["c7_revenue_growth_value"], "N/A")
        self.assertFalse(res["passes_all"]) # Cannot pass all since some are None

    @patch('scripts.fetch_batch.yf.Ticker')
    def test_evaluate_criteria_error_handling(self, mock_ticker_cls):
        # Force Ticker method to raise exception
        mock_ticker = MagicMock()
        mock_ticker.history.side_effect = Exception("API connection timed out")
        mock_ticker_cls.return_value = mock_ticker
        
        res = evaluate_criteria("TEST")
        
        self.assertEqual(res["ticker"], "TEST")
        self.assertEqual(res["price"], None)
        self.assertFalse(res["passes_all"])
        self.assertIn("API connection timed out", res["error"])

if __name__ == '__main__':
    unittest.main()
