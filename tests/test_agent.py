from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from agent import run_agent
from tools.input_checker import check_input


class NeuroDegAgentTests(unittest.TestCase):
    def test_valid_example_runs_end_to_end(self) -> None:
        df = pd.read_csv("data/example_neuro_deg.csv")
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_agent(df, output_dir=tmpdir)

            self.assertTrue(result.success)
            self.assertIsNotNone(result.deg_summary)
            self.assertGreater(result.deg_summary.up_count, 0)
            self.assertGreater(result.deg_summary.down_count, 0)
            self.assertIn("NeuroDEG-Agent Report", result.report)
            self.assertTrue((Path(tmpdir) / "volcano_plot.png").exists())
            self.assertTrue((Path(tmpdir) / "report.md").exists())
            self.assertEqual(len(result.trace), 10)
            self.assertIsNotNone(result.quality)
            self.assertIn(result.quality.grade, {"ready", "review", "blocked"})
            self.assertTrue(result.output_paths["run_manifest"].exists())

    def test_missing_padj_is_rejected(self) -> None:
        df = pd.read_csv("data/missing_p_adj.csv")
        checked = check_input(df)

        self.assertFalse(checked.valid)
        self.assertIn("p_adj", checked.message)

    def test_few_significant_genes_reports_low_signal_note(self) -> None:
        df = pd.read_csv("data/few_significant_genes.csv")
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_agent(df, output_dir=tmpdir)

            self.assertTrue(result.success)
            self.assertIn("small", result.report)
            self.assertEqual(result.state.confidence, "low")
            self.assertEqual(result.trace[4].status, "skipped")


if __name__ == "__main__":
    unittest.main()
