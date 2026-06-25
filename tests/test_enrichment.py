"""Tests for enrichment statistics."""

import unittest

from analysis.enrichment import _benjamini_hochberg


class TestEnrichment(unittest.TestCase):
    def test_bh_adjustment_uses_cumulative_minimum(self):
        adjusted = _benjamini_hochberg([0.01, 0.04, 0.03, 0.002])
        self.assertEqual(len(adjusted), 4)
        self.assertTrue(all(0 <= value <= 1 for value in adjusted))
        ranked = sorted(zip([0.01, 0.04, 0.03, 0.002], adjusted))
        self.assertTrue(
            all(ranked[index][1] <= ranked[index + 1][1] for index in range(len(ranked) - 1))
        )


if __name__ == "__main__":
    unittest.main()
