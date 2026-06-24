"""tests/test_quality.py"""
import unittest
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from agent_core.quality import QualityEvaluator

class TestQuality(unittest.TestCase):
    def setUp(self):
        self.evaluator = QualityEvaluator()
    
    def test_blocked_few_genes(self):
        fr = {"summary": {"significant": 5}}
        mr = {"total_matched_types": 0}
        result = self.evaluator.evaluate(fr, mr, [])
        self.assertEqual(result["grade"], "blocked")
    
    def test_ready_good_data(self):
        fr = {"summary": {"significant": 100}}
        mr = {"total_matched_types": 4}
        result = self.evaluator.evaluate(fr, mr, [])
        self.assertEqual(result["grade"], "ready")

if __name__ == "__main__":
    unittest.main()
