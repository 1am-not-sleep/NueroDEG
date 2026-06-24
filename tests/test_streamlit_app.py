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
        self.assertEqual(metrics["基因数"], "94")
        self.assertEqual(metrics["显著 DEG"], "39")
        self.assertEqual(metrics["细胞类型"], "7")
        self.assertEqual(metrics["行数"], "94")

        app.button[0].click().run(timeout=30)
        self.assertEqual(run_id, app.session_state["analysis_run"].state.run_id)
        self.assertEqual(len(app.exception), 0)

        app.get("button_group")[0].set_value("en").run(timeout=30)
        self.assertEqual(run_id, app.session_state["analysis_run"].state.run_id)
        self.assertTrue(
            app.session_state["analysis_run"].state.report.startswith(
                "# NeuroDEG Differential-Expression Report"
            )
        )
        english_metrics = {metric.label: metric.value for metric in app.metric}
        self.assertEqual(english_metrics["Genes"], "94")
        self.assertEqual(english_metrics["Cell types"], "7")
        self.assertEqual(len(app.exception), 0)


if __name__ == "__main__":
    unittest.main()
