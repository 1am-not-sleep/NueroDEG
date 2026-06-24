"""Tests for bilingual neural cell-type labels."""

import unittest

from agent_core.cell_types import find_cell_type_label, normalize_cell_type


class TestCellTypes(unittest.TestCase):
    def test_curated_cell_type_has_bilingual_label(self):
        labels = normalize_cell_type("星形胶质细胞", "Astrocyte")
        self.assertEqual(labels["type_zh"], "星形胶质细胞")
        self.assertEqual(labels["type_en"], "Astrocyte")
        self.assertEqual(labels["abbreviation"], "Astro")
        self.assertIn("Astrocyte", labels["display_name"])

    def test_panglao_cell_type_gets_standard_abbreviation(self):
        labels = normalize_cell_type("Oligodendrocyte progenitor cells")
        self.assertEqual(labels["type_zh"], "少突胶质前体细胞")
        self.assertEqual(labels["abbreviation"], "OPC")

    def test_lookup_by_abbreviation(self):
        labels = find_cell_type_label("OPC")
        self.assertIsNotNone(labels)
        self.assertEqual(labels["type_en"], "Oligodendrocyte progenitor cell")


if __name__ == "__main__":
    unittest.main()
