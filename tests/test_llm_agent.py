"""Tests for optional LLM planning and deterministic fallback."""

import unittest
from unittest.mock import patch

from agent_core.llm_agent import handle_agent_message


class TestLLMAgent(unittest.TestCase):
    @patch("agent_core.llm_agent._request")
    @patch("agent_core.llm_agent.handle_message")
    def test_structured_tool_call_is_executed_locally(self, local_handler, request):
        from agent_core.conversation import ConversationReply

        local_handler.return_value = ConversationReply("Local summary")
        request.side_effect = [
            {
                "id": "resp_1",
                "output": [
                    {
                        "type": "function_call",
                        "name": "summarize_run",
                        "arguments": "{}",
                        "call_id": "call_1",
                    }
                ],
            },
            {
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": "Grounded summary"}],
                    }
                ]
            },
        ]

        reply = handle_agent_message(
            prompt="Summarize",
            api_key="test-key",
            language="en",
        )

        self.assertEqual(reply.content, "Grounded summary")
        self.assertEqual(reply.actions[0].tool, "OpenAI Planner")
        local_handler.assert_called_once()

    @patch("agent_core.llm_agent._request", side_effect=TimeoutError)
    def test_api_failure_falls_back_to_local_router(self, _request):
        reply = handle_agent_message(
            prompt="分析当前数据",
            api_key="test-key",
            language="zh",
        )

        self.assertEqual(reply.actions[0].tool, "LLM Fallback")
        self.assertEqual(reply.actions[1].status, "blocked")


if __name__ == "__main__":
    unittest.main()
