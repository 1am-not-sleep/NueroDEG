"""End-to-end tests for the shared agent orchestrator."""

import json
import os
import subprocess
import sys
import tempfile
import unittest

from agent_core.orchestrator import run_analysis


class TestOrchestrator(unittest.TestCase):
    def test_example_run_generates_complete_bundle(self):
        with tempfile.TemporaryDirectory() as output_dir:
            run = run_analysis(
                "data/example_neuro_deg.csv",
                output_dir=output_dir,
                quiet=True,
            )

            self.assertEqual(run.quality["grade"], "ready")
            self.assertGreater(run.state.match_result["total_matched_types"], 0)
            self.assertGreater(len(run.state.enrichment_result["go"]), 0)

            expected = [
                "report.md",
                "volcano.png",
                "cell_type_bar.png",
                "up_genes.csv",
                "down_genes.csv",
                "run_manifest.json",
            ]
            for filename in expected:
                self.assertTrue(os.path.exists(os.path.join(output_dir, filename)), filename)

            with open(os.path.join(output_dir, "run_manifest.json"), encoding="utf-8") as handle:
                manifest = json.load(handle)
            self.assertEqual(manifest["quality"]["grade"], "ready")
            self.assertIn("cell_type_bar", manifest["artifacts"])

    def test_cli_returns_nonzero_for_invalid_input(self):
        completed = subprocess.run(
            [
                sys.executable,
                "app.py",
                "data/missing_p_adj.csv",
                "--no-vis",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 1)
        self.assertIn("ERROR:", completed.stderr)

    def test_english_report_generation(self):
        with tempfile.TemporaryDirectory() as output_dir:
            run = run_analysis(
                "data/example_neuro_deg.csv",
                output_dir=output_dir,
                generate_visuals=False,
                quiet=True,
                report_language="en",
            )
            self.assertTrue(
                run.state.report.startswith(
                    "# NeuroDEG Differential-Expression Report"
                )
            )
            self.assertEqual(run.state.params["report_language"], "en")


if __name__ == "__main__":
    unittest.main()
