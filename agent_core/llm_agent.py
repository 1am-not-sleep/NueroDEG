"""Optional OpenAI Responses API planner with deterministic local tool execution."""

from __future__ import annotations

import json
import os

import requests

from agent_core.conversation import ConversationAction, ConversationReply, handle_message


DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")
RESPONSES_URL = "https://api.openai.com/v1/responses"

TOOLS = [
    {
        "type": "function",
        "name": "analyze_data",
        "description": "Run or rerun the NeuroDEG analysis with explicit thresholds.",
        "parameters": {
            "type": "object",
            "properties": {
                "fc_cutoff": {"type": "number", "minimum": 0, "maximum": 5},
                "p_cutoff": {"type": "number", "minimum": 0.001, "maximum": 1},
                "use_enrichr": {"type": "boolean"},
            },
            "required": ["fc_cutoff", "p_cutoff", "use_enrichr"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "summarize_run",
        "description": "Summarize DEG counts, cell types, pathways, and quality.",
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        "strict": True,
    },
    {
        "type": "function",
        "name": "explain_gene",
        "description": "Explain a gene using current DEG statistics and the local marker knowledge base.",
        "parameters": {
            "type": "object",
            "properties": {"gene": {"type": "string"}},
            "required": ["gene"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "explain_cell_type",
        "description": "Explain a neural cell type, English name, Chinese name, or abbreviation.",
        "parameters": {
            "type": "object",
            "properties": {"cell_type": {"type": "string"}},
            "required": ["cell_type"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "explain_pathways",
        "description": "Interpret GO and curated pathway results from the current run.",
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        "strict": True,
    },
    {
        "type": "function",
        "name": "match_drug_targets",
        "description": "Match current pathways to the local research-only drug-target knowledge base.",
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        "strict": True,
    },
    {
        "type": "function",
        "name": "show_limitations",
        "description": "Explain uncertainty, safety boundaries, and methodological limitations.",
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        "strict": True,
    },
    {
        "type": "function",
        "name": "show_trace",
        "description": "Show the current run's tool execution trace.",
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        "strict": True,
    },
]


def _response_text(payload):
    if payload.get("output_text"):
        return payload["output_text"]
    chunks = []
    for item in payload.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") == "output_text":
                chunks.append(content.get("text", ""))
    return "\n".join(chunk for chunk in chunks if chunk)


def _request(api_key, payload, timeout=45):
    response = requests.post(
        RESPONSES_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()


def _tool_prompt(name, arguments, language):
    zh = language == "zh"
    if name == "analyze_data":
        return (
            f"用 log2FC {arguments['fc_cutoff']}、padj {arguments['p_cutoff']} "
            f"重新分析{'，启用 Enrichr' if arguments['use_enrichr'] else ''}"
        )
    if name == "summarize_run":
        return "总结本次结果" if zh else "Summarize this run"
    if name == "explain_gene":
        return f"解释基因 {arguments['gene']}"
    if name == "explain_cell_type":
        return f"解释细胞类型 {arguments['cell_type']}"
    if name == "explain_pathways":
        return "解释最显著的 GO 通路" if zh else "Explain the top GO pathways"
    if name == "match_drug_targets":
        return "分析药物靶点关联" if zh else "Analyze drug-target associations"
    if name == "show_limitations":
        return "这些结论有哪些局限？" if zh else "What are the limitations?"
    if name == "show_trace":
        return "展示 Agent 分析步骤" if zh else "Show the agent trace"
    raise ValueError(f"Unsupported tool: {name}")


def handle_llm_message(
    prompt,
    api_key,
    current_run=None,
    input_file=None,
    language="zh",
    fc_cutoff=1.0,
    p_cutoff=0.05,
    use_api=False,
    model=DEFAULT_MODEL,
):
    """Let an LLM select one local tool, then synthesize only from its output."""
    context = (
        "No analysis run is available."
        if current_run is None
        else (
            f"Current run: {current_run.state.run_id}; "
            f"fc={current_run.state.params['fc_cutoff']}; "
            f"p={current_run.state.params['p_cutoff']}; "
            f"quality={current_run.quality['grade']}."
        )
    )
    instructions = (
        "You are the planning layer for NeuroDEG, a research-only biomedical analysis agent. "
        "Choose exactly one provided tool. Never invent genes, statistics, pathways, citations, "
        "medical diagnoses, or treatment advice. Drug matches are research hypotheses only. "
        f"Answer in {'Chinese' if language == 'zh' else 'English'}. {context}"
    )
    first = _request(
        api_key,
        {
            "model": model,
            "instructions": instructions,
            "input": prompt,
            "tools": TOOLS,
            "tool_choice": "required",
            "parallel_tool_calls": False,
        },
    )
    calls = [item for item in first.get("output", []) if item.get("type") == "function_call"]
    if len(calls) != 1:
        raise RuntimeError("The model did not select exactly one NeuroDEG tool.")

    call = calls[0]
    arguments = json.loads(call.get("arguments") or "{}")
    local_reply = handle_message(
        _tool_prompt(call["name"], arguments, language),
        current_run=current_run,
        input_file=input_file,
        language=language,
        fc_cutoff=fc_cutoff,
        p_cutoff=p_cutoff,
        use_api=use_api or bool(arguments.get("use_enrichr")),
    )
    second = _request(
        api_key,
        {
            "model": model,
            "instructions": (
                instructions
                + " Summarize the tool output faithfully and concisely. Preserve numerical values. "
                "End with: Sources: [Current DEG run], [NeuroDEG local knowledge base]."
            ),
            "previous_response_id": first["id"],
            "input": [
                {
                    "type": "function_call_output",
                    "call_id": call["call_id"],
                    "output": local_reply.content,
                }
            ],
        },
    )
    content = _response_text(second) or local_reply.content
    actions = [
        ConversationAction(
            "OpenAI Planner",
            "Selected a structured local NeuroDEG tool.",
            f"Tool selected: {call['name']} ({model}).",
        ),
        *local_reply.actions,
    ]
    return ConversationReply(content, actions, local_reply.updated_run)


def handle_agent_message(*, api_key=None, **kwargs):
    """Use LLM planning when configured; fall back safely on any API failure."""
    if not api_key:
        return handle_message(**kwargs)
    try:
        return handle_llm_message(api_key=api_key, **kwargs)
    except Exception as exc:
        reply = handle_message(**kwargs)
        reply.actions.insert(
            0,
            ConversationAction(
                "LLM Fallback",
                "The optional OpenAI planner was unavailable.",
                f"Used deterministic local routing instead: {type(exc).__name__}.",
                status="review",
            ),
        )
        return reply
