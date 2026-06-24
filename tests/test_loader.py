"""tests/test_loader.py"""
import unittest
import os
import sys
import tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from analysis.loader import load_deg, detect_column
import pandas as pd

class TestLoader(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False)
        self.tmp.write("gene,log2FC,p_adj\nSNAP25,-1.4,0.004\nMBP,-2.1,0.001\n")
        self.tmp.close()
    
    def tearDown(self):
        os.unlink(self.tmp.name)
    
    def test_load_deg(self):
        df = load_deg(self.tmp.name)
        self.assertEqual(len(df), 2)
        self.assertIn("gene", df.columns)
        self.assertIn("log2fc", df.columns)
        self.assertIn("padj", df.columns)
    
    def test_load_nonexistent(self):
        with self.assertRaises(FileNotFoundError):
            load_deg("/nonexistent/file.csv")

if __name__ == "__main__":
    unittest.main()
