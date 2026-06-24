"""Streamlit workspace regression test."""

import unittest

from streamlit.testing.v1 import AppTest


class TestStreamlitApp(unittest.TestCase):
    def test_example_analysis_and_followup_reuse_same_run(self):
        app = AppTest.from_file("streamlit_app.py").run(timeout=30)
        self.assertEqual(len(app.exception), 0)

        app.button[0].click().run(timeout=60)
        self.assertEqual(len(app.exception), 0)
        run_id = app.session_state["analysis_run"].state.run_id

        metrics = {metric.label: metric.value for metric in app.metric}
        self.assertEqual(metrics["Genes"], "94")
        self.assertEqual(metrics["Significant"], "39")
        self.assertEqual(metrics["Cell types"], "7")

        app.button[0].click().run(timeout=30)
        self.assertEqual(run_id, app.session_state["analysis_run"].state.run_id)
        self.assertEqual(len(app.exception), 0)


if __name__ == "__main__":
    unittest.main()
