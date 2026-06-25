"""Tests for bilingual cell-type queries."""

import unittest

from agent_core.chat import query_cell_type


class TestChat(unittest.TestCase):
    def test_query_curated_type_by_english_name(self):
        answer = query_cell_type("Astrocyte")
        self.assertIn("星形胶质细胞", answer)
        self.assertIn("Astrocyte", answer)

    def test_query_supplement_type_by_abbreviation(self):
        answer = query_cell_type("OPC")
        self.assertIn("少突胶质前体细胞", answer)
        self.assertIn("Oligodendrocyte progenitor cell", answer)


if __name__ == "__main__":
    unittest.main()
