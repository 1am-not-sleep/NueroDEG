from __future__ import annotations

import unittest

from streamlit.testing.v1 import AppTest


class StreamlitAppTests(unittest.TestCase):
    def test_app_renders_and_runs_example_analysis(self) -> None:
        app = AppTest.from_file("app.py").run(timeout=10)

        self.assertEqual(app.title[0].value, "NeuroDEG-Agent")
        self.assertEqual([button.label for button in app.button], ["Load example data", "Analyze"])

        app.button[1].click().run(timeout=20)

        metrics = {metric.label: metric.value for metric in app.metric}
        self.assertEqual(metrics["Total genes"], "40")
        self.assertEqual(metrics["Up-regulated"], "9")
        self.assertEqual(metrics["Down-regulated"], "11")
        self.assertIn("Agent confidence", metrics)
        self.assertIn("Quality", metrics)
        self.assertEqual(len(app.tabs), 8)


if __name__ == "__main__":
    unittest.main()
