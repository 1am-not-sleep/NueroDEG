"""Tests for the conversational NeuroDEG tool router."""

import tempfile
import unittest

from agent_core.conversation import handle_message
from agent_core.orchestrator import run_analysis


class TestConversation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output_dir = tempfile.TemporaryDirectory()
        cls.analysis_run = run_analysis(
            "data/example_neuro_deg.csv",
            output_dir=cls.output_dir.name,
            generate_visuals=False,
            quiet=True,
        )

    @classmethod
    def tearDownClass(cls):
        cls.output_dir.cleanup()

    def test_agent_can_start_analysis_from_natural_language(self):
        reply = handle_message(
            "分析当前数据",
            input_file="data/example_neuro_deg.csv",
            fc_cutoff=1.2,
            p_cutoff=0.02,
            language="zh",
        )

        self.assertIsNotNone(reply.updated_run)
        self.assertEqual(reply.updated_run.state.params["fc_cutoff"], 1.2)
        self.assertEqual(reply.updated_run.state.params["p_cutoff"], 0.02)
        self.assertEqual([action.tool for action in reply.actions], ["Planner", "NeuroDEG Analysis"])

    def test_agent_can_reanalyze_with_thresholds(self):
        reply = handle_message(
            "用 log2FC 1.5、padj 0.01 重新分析",
            current_run=self.analysis_run,
            language="zh",
        )

        self.assertIsNotNone(reply.updated_run)
        self.assertEqual(reply.updated_run.state.params["fc_cutoff"], 1.5)
        self.assertEqual(reply.updated_run.state.params["p_cutoff"], 0.01)

    def test_analysis_result_question_does_not_trigger_reanalysis(self):
        reply = handle_message(
            "分析结果有哪些局限？",
            current_run=self.analysis_run,
            language="zh",
        )

        self.assertIsNone(reply.updated_run)
        self.assertEqual(reply.actions[0].tool, "Safety Guardrail")
        self.assertIn("marker overlap", reply.content)

    def test_summary_cell_type_gene_and_pathway_tools(self):
        cases = [
            ("总结本次结果", "Analysis Summary"),
            ("解释 MG 的变化", "Cell-Type Interpreter"),
            ("GFAP 在本次结果中如何变化？", "Gene Inspector"),
            ("最显著的 GO 通路是什么？", "Pathway Interpreter"),
            ("展示 Agent 的分析步骤", "Trace Reader"),
        ]

        for prompt, expected_tool in cases:
            with self.subTest(prompt=prompt):
                reply = handle_message(
                    prompt,
                    current_run=self.analysis_run,
                    language="zh",
                )
                self.assertIsNone(reply.updated_run)
                self.assertEqual(reply.actions[0].tool, expected_tool)
                self.assertTrue(reply.content)

    def test_agent_reports_missing_input_context(self):
        reply = handle_message("分析当前数据", language="zh")

        self.assertIsNone(reply.updated_run)
        self.assertEqual(reply.actions[0].status, "blocked")
        self.assertIn("选择示例数据", reply.content)


if __name__ == "__main__":
    unittest.main()
