"""tests/test_neural_matcher.py"""
import unittest
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from analysis.neural_matcher import load_knowledge_base, match_neural_types
import pandas as pd

class TestNeuralMatcher(unittest.TestCase):
    def setUp(self):
        self.kb, self.g2c = load_knowledge_base()
    
    def test_kb_has_cell_types(self):
        self.assertTrue(len(self.kb["cell_types"]) > 5)
    
    def test_kb_gene_index(self):
        self.assertTrue(len(self.g2c) > 50)
    
    def test_match_neural_types(self):
        up = pd.DataFrame({"gene": ["GFAP", "AIF1"]})
        down = pd.DataFrame({"gene": ["MBP", "SNAP25"]})
        result = match_neural_types(up, down, self.kb, self.g2c)
        self.assertTrue(result["total_matched_types"] > 0)
        for cell_type in result["results"]:
            self.assertTrue(cell_type["type_en"])
            self.assertTrue(cell_type["abbreviation"])
            self.assertTrue(cell_type["display_name"])

if __name__ == "__main__":
    unittest.main()
