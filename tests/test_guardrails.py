"""tests/test_guardrails.py"""
import unittest
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from agent_core.guardrails import check_output_guardrails, check_input_guardrails

class TestGuardrails(unittest.TestCase):
    def test_output_clean(self):
        self.assertEqual(len(check_output_guardrails("正常分析结果")), 0)
    
    def test_output_with_claim(self):
        warnings = check_output_guardrails("该基因可作为诊断标记")
        self.assertTrue(len(warnings) > 0)
    
    def test_input_nonexistent(self):
        warnings = check_input_guardrails("/nonexistent.csv")
        self.assertTrue(any(w["level"] == "error" for w in warnings))

if __name__ == "__main__":
    unittest.main()
