from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from agent_core.chat import answer_followup
from agent import run_agent
from tools.neural_classifier import module_hits_to_frame


st.set_page_config(page_title="NeuroDEG-Agent", layout="wide")

ROOT = Path(__file__).parent
EXAMPLE_PATH = ROOT / "data" / "example_neuro_deg.csv"
RESULTS_DIR = ROOT / "results"


def load_uploaded_csv(uploaded_file) -> pd.DataFrame:
    return pd.read_csv(uploaded_file)


st.title("NeuroDEG-Agent")

with st.sidebar:
    st.header("Analysis")
    species = st.selectbox("Species", ["human", "mouse"], index=0)
    comparison_info = st.text_input("Comparison", value="Alzheimer's disease cortex vs control cortex")
    logfc_cutoff = st.number_input("log2FC cutoff", min_value=0.0, max_value=5.0, value=1.0, step=0.1)
    padj_cutoff = st.number_input("Adjusted p-value cutoff", min_value=0.001, max_value=1.0, value=0.05, step=0.001)

uploaded = st.file_uploader("Upload DEG CSV", type=["csv"])
use_example = st.button("Load example data", width="stretch")

df: pd.DataFrame | None = None
source_label = ""

if uploaded is not None:
    df = load_uploaded_csv(uploaded)
    source_label = uploaded.name
elif use_example or EXAMPLE_PATH.exists():
    df = pd.read_csv(EXAMPLE_PATH)
    source_label = "data/example_neuro_deg.csv"

if df is None:
    st.info("Upload a CSV with gene, log2FC, and p_adj columns.")
    st.stop()

left, right = st.columns([2, 1])
with left:
    st.subheader("Input Preview")
    st.caption(source_label)
    st.dataframe(df.head(30), width="stretch", hide_index=True)

with right:
    st.subheader("Run")
    analyze = st.button("Analyze", type="primary", width="stretch")
    st.metric("Rows", len(df))
    st.metric("Columns", len(df.columns))

if not analyze:
    st.stop()

result = run_agent(
    df,
    comparison_info=comparison_info,
    species=species,
    output_dir=RESULTS_DIR,
    logfc_cutoff=logfc_cutoff,
    padj_cutoff=padj_cutoff,
)

if not result.success:
    st.error(result.message)
    if result.input_result.missing_columns:
        st.write("Missing columns:", ", ".join(result.input_result.missing_columns))
    st.stop()

assert result.deg_summary is not None

summary = result.deg_summary
metric_cols = st.columns(4)
metric_cols[0].metric("Total genes", summary.total_genes)
metric_cols[1].metric("Significant genes", summary.significant_genes)
metric_cols[2].metric("Up-regulated", summary.up_count)
metric_cols[3].metric("Down-regulated", summary.down_count)

agent_cols = st.columns(3)
agent_cols[0].metric("Agent confidence", result.state.confidence if result.state else "unknown")
agent_cols[1].metric("Run ID", result.run_id)
agent_cols[2].metric("Quality", result.quality.grade if result.quality else "unknown")

if result.input_result.warnings:
    with st.expander("Input warnings", expanded=False):
        for warning in result.input_result.warnings:
            st.warning(warning)

tabs = st.tabs(["Volcano", "Agent Trace", "Neural Modules", "Enrichment", "Report", "Quality", "Ask Agent", "Output Files"])

with tabs[0]:
    st.image(str(result.output_paths["volcano_plot"]), width="stretch")
    st.dataframe(summary.annotated.sort_values("p_adj").head(30), width="stretch", hide_index=True)

with tabs[1]:
    trace_rows = [
        {
            "step": step.step_id,
            "tool": step.tool_name,
            "status": step.status,
            "decision": step.decision,
            "observation": step.observation,
        }
        for step in result.trace
    ]
    st.dataframe(pd.DataFrame(trace_rows), width="stretch", hide_index=True)
    if result.state and result.state.decisions:
        st.markdown("#### Agent Decisions")
        for decision in result.state.decisions:
            st.write(f"- {decision}")
    if result.state and result.state.human_review_reasons:
        st.markdown("#### Human Review Reasons")
        for reason in result.state.human_review_reasons:
            st.warning(reason)

with tabs[2]:
    module_frame = module_hits_to_frame(result.module_hits)
    if module_frame.empty:
        st.info("No neural marker module matched the significant DEG lists.")
    else:
        st.dataframe(module_frame, width="stretch", hide_index=True)

with tabs[3]:
    if result.enrichment_table is None or result.enrichment_table.empty:
        st.info("No marker-set overlap terms were detected.")
    else:
        st.dataframe(result.enrichment_table, width="stretch", hide_index=True)

with tabs[4]:
    st.markdown(result.report)
    st.download_button(
        "Download report.md",
        data=result.report,
        file_name="neurodeg_report.md",
        mime="text/markdown",
        width="stretch",
    )

with tabs[5]:
    if result.guardrails:
        guardrail_rows = [
            {
                "name": check.name,
                "passed": check.passed,
                "severity": check.severity,
                "message": check.message,
            }
            for check in result.guardrails
        ]
        st.markdown("#### Guardrails")
        st.dataframe(pd.DataFrame(guardrail_rows), width="stretch", hide_index=True)

    if result.quality:
        st.markdown("#### Quality Checklist")
        quality_rows = [
            {
                "name": check.name,
                "passed": check.passed,
                "message": check.message,
            }
            for check in result.quality.checks
        ]
        st.metric("Quality score", result.quality.score)
        st.metric("Quality grade", result.quality.grade)
        st.dataframe(pd.DataFrame(quality_rows), width="stretch", hide_index=True)
        if result.quality.recommendations:
            st.markdown("#### Recommendations")
            for recommendation in result.quality.recommendations:
                st.write(f"- {recommendation}")

with tabs[6]:
    st.markdown("Ask follow-up questions about detected modules, limitations, validation, or summary counts.")
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    prompt = st.chat_input("Ask about this analysis")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        answer = answer_followup(prompt, summary, result.module_hits, result.report)
        st.session_state.messages.append({"role": "assistant", "content": answer})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            st.markdown(answer)

with tabs[7]:
    for name, path in result.output_paths.items():
        st.code(f"{name}: {path}")
