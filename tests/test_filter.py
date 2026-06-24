"""tests/test_filter.py"""
import unittest
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from analysis.filter import filter_degs
import pandas as pd

class TestFilter(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame({
            "gene": ["A", "B", "C", "D", "E"],
            "log2fc": [2.5, -1.8, 0.5, -0.3, 1.2],
            "padj": [0.001, 0.03, 0.5, 0.7, 0.04]
        })
    
    def test_filter_degs(self):
        result = filter_degs(self.df, 1.0, 0.05)
        self.assertEqual(result["summary"]["significant"], 3)
        self.assertEqual(result["summary"]["up"], 2)
        self.assertEqual(result["summary"]["down"], 1)

if __name__ == "__main__":
    unittest.main()
