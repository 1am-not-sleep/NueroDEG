# NeuroDEG-Agent Architecture

This document describes the upgraded agent architecture used in the current MVP.

## Design Goal

The project started as a fixed DEG analysis pipeline. The upgraded version is designed as a rule-based biomedical agent that can later be migrated to OpenAI Agents SDK, LangGraph, or another tool-calling runtime.

The key design goals are:

- keep the demo runnable without API keys
- make every tool call observable
- route decisions based on intermediate results
- prevent overconfident biomedical claims
- persist reproducible run metadata
- provide a chat-style follow-up interface

## Reference Patterns

The architecture follows common patterns from mature agent systems:

- tool-based execution: each analysis operation is a named tool
- stateful orchestration: shared state records decisions, outputs, and confidence
- conditional routing: low-signal data can skip unstable enrichment
- guardrails: report text is checked for unsafe absolute biomedical claims
- tracing: every tool call has a status, decision, and observation
- memory: each run writes a manifest for reproducibility
- evaluation: each run receives a quality score and recommendations
- human review: weak or risky outputs are surfaced instead of hidden

## Runtime Flow

```text
User DEG table
  ↓
Agent Planner
  ↓
Input Checker
  ↓
Decision: continue or block
  ↓
DEG Filter
  ↓
Decision: run enrichment or skip as low-confidence
  ↓
Volcano Plot Tool
  ↓
Neural Module Classifier
  ↓
Marker Enrichment Tool
  ↓
Knowledge Retriever
  ↓
Report Generator
  ↓
Output Guardrails
  ↓
Quality Evaluator
  ↓
Run Memory
```

## Files

```text
agent.py
  Orchestrates the full run and returns AgentResult.

agent_core/state.py
  Defines AgentState, AgentStep, guardrail checks, and quality checks.

agent_core/planner.py
  Creates the initial tool plan and decides whether to continue, skip enrichment, or request review.

agent_core/guardrails.py
  Validates input and checks the generated report for unsafe language.

agent_core/quality.py
  Scores whether the run is ready, review-needed, or blocked.

agent_core/memory.py
  Writes JSON run manifests to results/runs/<run_id>/run_manifest.json.

agent_core/chat.py
  Provides deterministic follow-up answers from the current run context.
```

## Agent Trace

Each `AgentStep` records:

```text
step_id
tool_name
purpose
status
decision
observation
inputs
outputs
started_at
ended_at
```

This trace is shown in Streamlit and saved to the run manifest. It is intentionally not a hidden chain-of-thought log; it is a user-facing operational trace.

## Guardrails

The current guardrails check:

- required input columns
- non-empty input
- missing or risky input warnings
- report includes limitations
- report includes suggested validation
- report avoids unsupported absolute biomedical claims such as "proves that" or "diagnoses"

This is important because DEG interpretation is hypothesis-generating and should not be presented as diagnostic proof.

## Quality Evaluation

The quality evaluator checks:

- DEG summary exists
- volcano plot exists
- report exists
- at least one module was detected
- enrichment table exists
- limitations are present
- validation suggestions are present
- no error-level guardrails failed

The result is:

```text
ready   - usable for demo
review  - usable but needs human review
blocked - unsafe or invalid
```

## Why This Is More Agent-Like

The upgraded version is no longer only a fixed script. It now has:

- a plan
- state
- tool invocation records
- conditional decisions
- retrieved knowledge
- guardrails
- quality evaluation
- persistent memory
- follow-up interaction

The next step is to replace the rule-based planner and deterministic chat with an LLM planner while keeping the same tools and guardrails.
