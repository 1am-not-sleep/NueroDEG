# Roadmap Toward a Mature Biomedical Agent

## Current Version: Rule-Based Agent MVP

Already implemented:

- Streamlit UI
- command-line runner
- input validation
- DEG filtering
- volcano plot
- curated neural marker classifier
- hypergeometric marker-set enrichment
- local knowledge retrieval
- structured report generation
- agent trace
- guardrails
- quality scoring
- run memory
- deterministic follow-up chat
- unit and app tests

## Stage 1: Stronger Biomedical Analysis

Add:

- GO Biological Process enrichment
- KEGG pathway enrichment
- separate human/mouse marker dictionaries
- configurable background gene universe
- support for common column aliases from DESeq2, edgeR, and Seurat
- downloadable ZIP report bundle

Recommended implementation:

- keep current marker enrichment as a fallback
- add GSEApy/Enrichr as an optional tool
- surface whether enrichment was local marker-based or external GO/KEGG

## Stage 2: LLM Tool-Calling Agent

Add an optional LLM planner:

```text
User goal
  ↓
LLM planner
  ↓
tool selection
  ↓
tool result observation
  ↓
next action
  ↓
final report
```

Important constraints:

- do not let the LLM invent gene findings
- pass only tool outputs and retrieved knowledge to the report generator
- require limitations and validation suggestions
- keep deterministic fallback mode for demo reliability

Suggested file:

```text
agent_core/llm_planner.py
```

## Stage 3: RAG Upgrade

Replace file-level retrieval with paragraph-level retrieval:

- split knowledge files into chunks
- embed chunks or use BM25/TF-IDF
- retrieve top relevant passages for detected modules
- cite retrieved knowledge notes inside the report

Suggested files:

```text
agent_core/rag_index.py
agent_core/rag_retriever.py
```

## Stage 4: Human-in-the-Loop Review

Add checkpoints:

- confirm analysis if input has too few genes
- ask user whether to relax thresholds
- ask user whether to run external enrichment
- allow user to approve final report wording

Useful UI:

- review checklist
- editable report text area
- accept/reject agent recommendations

## Stage 5: Evaluation Dataset

Build a small evaluation suite:

```text
eval_cases/
├── alzheimer_like.csv
├── demyelination_like.csv
├── synaptic_down.csv
├── missing_columns.csv
└── low_signal.csv
```

For each case, define expected outputs:

- expected modules
- expected warning level
- expected guardrail status
- expected report sections

## Stage 6: Production-Style Deployment

Add:

- Dockerfile
- GitHub Actions for tests
- release artifacts
- hosted Streamlit demo
- example report screenshots
- versioned marker dictionaries
- provenance metadata

## Two-Day Priority

For the current deadline, stop after:

- Stage 0 current MVP
- lightweight Stage 1 documentation
- enough tests and README for GitHub evaluation

Do not add PubMed, PDF export, or full GO/KEGG unless the demo is already stable.
