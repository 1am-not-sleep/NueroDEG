"""NeuroDEG Streamlit analysis workspace."""

from __future__ import annotations

import io
import os
import tempfile
import zipfile
from pathlib import Path

import pandas as pd
import streamlit as st

from agent_core.chat import load_kb, query_cell_type, query_gene
from agent_core.orchestrator import AnalysisRunError, run_analysis
from agent_core.qa_buttons import analysis_summary, drug_association, pathway_insights


ROOT = Path(__file__).resolve().parent
EXAMPLE_PATH = ROOT / "data" / "example_neuro_deg.csv"

st.set_page_config(page_title="NeuroDEG", layout="wide")

st.markdown(
    """
    <style>
    .block-container {padding-top: 1.4rem; padding-bottom: 2.5rem; max-width: 1440px;}
    .app-kicker {font-size: 0.78rem; color: #64748b; font-weight: 700; text-transform: uppercase;}
    .app-title {font-size: 2rem; font-weight: 720; color: #172033; margin: 0.2rem 0 0.3rem;}
    .app-subtitle {color: #526070; max-width: 900px; margin-bottom: 1.2rem;}
    .status-ready {color: #087f5b; font-weight: 700;}
    .status-review {color: #b45309; font-weight: 700;}
    .status-blocked {color: #b42318; font-weight: 700;}
    div[data-testid="stMetric"] {border-top: 2px solid #d8dee8; padding-top: 0.65rem;}
    </style>
    <div class="app-kicker">Biomedical analysis workspace</div>
    <div class="app-title">NeuroDEG</div>
    <div class="app-subtitle">
      Validate neural DEG tables, identify cell-type signals, run offline GO enrichment,
      inspect agent decisions, and export a reproducible analysis bundle.
    </div>
    """,
    unsafe_allow_html=True,
)


def reset_analysis():
    for key in [
        "analysis_run",
        "active_followup",
        "analysis_source",
    ]:
        st.session_state.pop(key, None)


def create_uploaded_copy(uploaded_file):
    suffix = Path(uploaded_file.name).suffix or ".csv"
    handle = tempfile.NamedTemporaryFile(
        prefix="neurodeg_input_",
        suffix=suffix,
        delete=False,
    )
    handle.write(uploaded_file.getbuffer())
    handle.close()
    return handle.name


def build_result_bundle(run):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, path in run.state.artifacts.items():
            if path and os.path.exists(path):
                archive.write(path, arcname=os.path.basename(path))
    buffer.seek(0)
    return buffer.getvalue()


def status_class(grade):
    return {
        "ready": "status-ready",
        "review": "status-review",
        "blocked": "status-blocked",
    }.get(grade, "")


with st.sidebar:
    st.header("Analysis setup")
    data_option = st.segmented_control(
        "Data source",
        ["Example data", "Upload file"],
        default="Example data",
    )
    uploaded_file = None
    if data_option == "Upload file":
        uploaded_file = st.file_uploader("DEG file", type=["csv", "tsv", "txt"])

    st.download_button(
        "Download example CSV",
        EXAMPLE_PATH.read_bytes(),
        file_name="example_neuro_deg.csv",
        mime="text/csv",
        width="stretch",
    )

    st.divider()
    fc_cutoff = st.number_input(
        "|log2FC| cutoff",
        min_value=0.0,
        max_value=5.0,
        value=1.0,
        step=0.1,
    )
    p_cutoff = st.number_input(
        "Adjusted p-value cutoff",
        min_value=0.001,
        max_value=1.0,
        value=0.05,
        step=0.001,
        format="%.3f",
    )
    use_api = st.toggle("Try Enrichr API", value=False)

    run_button = st.button("Run analysis", type="primary", width="stretch")
    if st.button("Reset", width="stretch"):
        reset_analysis()
        st.rerun()

    with st.expander("Accepted input columns"):
        st.markdown(
            """
            Required biological fields:

            - gene symbol: `gene`, `symbol`, `gene_name`
            - fold change: `log2FC`, `logFC`, `fold_change`
            - significance: `padj`, `p_adj`, `FDR`, or `pvalue`
            """
        )


if run_button:
    if data_option == "Upload file" and uploaded_file is None:
        st.error("Select a CSV/TSV file before running the analysis.")
    else:
        input_path = (
            str(EXAMPLE_PATH)
            if data_option == "Example data"
            else create_uploaded_copy(uploaded_file)
        )
        source_name = (
            EXAMPLE_PATH.name
            if data_option == "Example data"
            else uploaded_file.name
        )
        web_output_dir = tempfile.mkdtemp(prefix="neurodeg_web_run_")

        try:
            with st.status("Running NeuroDEG tools...", expanded=True) as status:
                st.write("Validating and normalizing the DEG table")
                run = run_analysis(
                    input_file=input_path,
                    fc_cutoff=fc_cutoff,
                    p_cutoff=p_cutoff,
                    output_dir=web_output_dir,
                    use_api=use_api,
                    generate_visuals=True,
                    quiet=True,
                )
                st.write("Cell-type matching and pathway enrichment completed")
                st.write("Report, trace, and reproducibility manifest generated")
                status.update(label="Analysis complete", state="complete", expanded=False)
            st.session_state.analysis_run = run
            st.session_state.analysis_source = source_name
            st.session_state.active_followup = None
        except AnalysisRunError as exc:
            st.error(f"Analysis stopped: {exc}")
        except Exception as exc:
            st.exception(exc)


run = st.session_state.get("analysis_run")

if run is None:
    preview = pd.read_csv(EXAMPLE_PATH)
    st.subheader("Ready to analyze")
    st.write(
        "The example dataset is selected by default. Adjust thresholds in the sidebar "
        "or upload your own DEG table, then run the analysis."
    )
    preview_col, workflow_col = st.columns([1.6, 1])
    with preview_col:
        st.markdown("#### Example data preview")
        st.dataframe(preview.head(12), width="stretch", hide_index=True)
    with workflow_col:
        st.markdown("#### Agent workflow")
        st.markdown(
            """
            1. Input validation and column normalization
            2. DEG filtering
            3. Neural cell-type matching
            4. Offline GO and local pathway enrichment
            5. Volcano and cell-type plots
            6. Guardrails, quality grading, and report generation
            """
        )
    st.stop()


state = run.state
summary = state.filter_result["summary"]
match_result = state.match_result
enrichment = state.enrichment_result
quality = run.quality
grade = quality["grade"]

st.markdown(
    f"Source: `{st.session_state.get('analysis_source', '')}` &nbsp;·&nbsp; "
    f"Run: `{state.run_id}` &nbsp;·&nbsp; "
    f"Status: <span class='{status_class(grade)}'>{grade.upper()}</span>",
    unsafe_allow_html=True,
)

metric_columns = st.columns(6)
metric_columns[0].metric("Genes", summary["total_genes"])
metric_columns[1].metric("Significant", summary["significant"])
metric_columns[2].metric("Up", summary["up"])
metric_columns[3].metric("Down", summary["down"])
metric_columns[4].metric("Cell types", match_result["total_matched_types"])
metric_columns[5].metric("GO terms", len(enrichment.get("go", [])))

if state.warnings:
    with st.expander(f"Run notes ({len(state.warnings)})", expanded=grade != "ready"):
        for warning in state.warnings:
            st.warning(warning)

tabs = st.tabs(
    [
        "Overview",
        "Visualizations",
        "Cell types",
        "Pathway enrichment",
        "Agent trace",
        "Report",
        "Ask Agent",
    ]
)

with tabs[0]:
    left, right = st.columns([1.5, 1])
    with left:
        st.markdown("#### Differential-expression summary")
        gene_tabs = st.tabs(["Top up-regulated", "Top down-regulated"])
        with gene_tabs[0]:
            st.dataframe(
                state.filter_result["up"][["gene", "log2fc", "padj"]].head(15),
                width="stretch",
                hide_index=True,
            )
        with gene_tabs[1]:
            st.dataframe(
                state.filter_result["down"][["gene", "log2fc", "padj"]].head(15),
                width="stretch",
                hide_index=True,
            )
    with right:
        st.markdown("#### Quality assessment")
        st.markdown(
            f"<div class='{status_class(grade)}'>{grade.upper()}</div>",
            unsafe_allow_html=True,
        )
        for reason in quality.get("reasons", []):
            st.write(f"- {reason}")
        st.markdown("#### Export")
        st.download_button(
            "Download report",
            state.report,
            file_name=f"{state.run_id}_report.md",
            mime="text/markdown",
            width="stretch",
        )
        st.download_button(
            "Download result bundle",
            build_result_bundle(run),
            file_name=f"{state.run_id}_results.zip",
            mime="application/zip",
            width="stretch",
        )

with tabs[1]:
    plot_columns = st.columns(2)
    with plot_columns[0]:
        st.markdown("#### Volcano plot")
        volcano_path = state.artifacts.get("volcano_plot")
        if volcano_path and os.path.exists(volcano_path):
            st.image(volcano_path, width="stretch")
        else:
            st.info("Volcano plot was not generated.")
    with plot_columns[1]:
        st.markdown("#### Cell-type marker changes")
        cell_type_path = state.artifacts.get("cell_type_bar")
        if cell_type_path and os.path.exists(cell_type_path):
            st.image(cell_type_path, width="stretch")
        else:
            st.info("No cell-type plot is available for this run.")

with tabs[2]:
    if not match_result["results"]:
        st.info("No neural cell-type marker pattern passed the current decision threshold.")
    else:
        cell_rows = [
            {
                "cell_type": item["type"],
                "source": item.get("source", ""),
                "matched": item["matched"],
                "marker_total": item["total_markers"],
                "up": item["up_count"],
                "down": item["down_count"],
                "direction": item["main_direction"],
            }
            for item in match_result["results"]
        ]
        st.dataframe(pd.DataFrame(cell_rows), width="stretch", hide_index=True)
        for item in match_result["results"]:
            with st.expander(
                f"{item['type']} · {item['matched']}/{item['total_markers']} markers"
            ):
                st.write(f"Source: {item.get('source', '')}")
                st.write(f"Up-regulated markers: {item['up_genes'] or 'None'}")
                st.write(f"Down-regulated markers: {item['down_genes'] or 'None'}")
                st.write(item["interpretation"])

with tabs[3]:
    go_results = enrichment.get("go", [])
    local_results = enrichment.get("local", [])
    enrichment_tabs = st.tabs(["GO overrepresentation", "Curated pathways", "Enrichr"])
    with enrichment_tabs[0]:
        if go_results:
            go_table = pd.DataFrame(
                [
                    {
                        "GO ID": item["go_id"],
                        "term": item["go_name"],
                        "overlap": item["ratio"],
                        "p_value": item["p_value"],
                        "FDR": item["adjusted_p_value"],
                        "genes": ", ".join(item["overlap_genes"][:8]),
                    }
                    for item in go_results[:50]
                ]
            )
            st.dataframe(
                go_table,
                width="stretch",
                hide_index=True,
                column_config={
                    "p_value": st.column_config.NumberColumn(format="%.2e"),
                    "FDR": st.column_config.NumberColumn(format="%.2e"),
                },
            )
        else:
            st.info("No GO terms passed the configured criteria.")
    with enrichment_tabs[1]:
        if local_results:
            st.dataframe(pd.DataFrame(local_results), width="stretch", hide_index=True)
        else:
            st.info("No curated pathway overlap was detected.")
    with enrichment_tabs[2]:
        api_status = enrichment.get("api_status", "disabled")
        if api_status == "success":
            st.dataframe(pd.DataFrame(enrichment["api"]), width="stretch", hide_index=True)
        elif api_status == "failed":
            st.warning(
                "Enrichr was unavailable. Offline GO and curated pathway results remain valid."
            )
            st.caption(enrichment.get("api_error", ""))
        else:
            st.info("Enrichr was not requested for this run.")

with tabs[4]:
    trace_table = pd.DataFrame(run.trace.to_list())
    st.dataframe(trace_table, width="stretch", hide_index=True)
    st.markdown("#### Guardrails")
    if run.guardrail_warnings:
        st.dataframe(
            pd.DataFrame(run.guardrail_warnings),
            width="stretch",
            hide_index=True,
        )
    else:
        st.success("No guardrail warning was raised.")

with tabs[5]:
    st.download_button(
        "Download Markdown report",
        state.report,
        file_name=f"{state.run_id}_report.md",
        mime="text/markdown",
    )
    st.markdown(state.report)

with tabs[6]:
    st.markdown(
        "Use structured follow-ups to interpret pathways, inspect drug-target associations, "
        "or query the local marker knowledge base."
    )
    followup_columns = st.columns(3)
    if followup_columns[0].button("Interpret pathways", width="stretch"):
        st.session_state.active_followup = "pathways"
    if followup_columns[1].button("Drug-target associations", width="stretch"):
        st.session_state.active_followup = "drugs"
    if followup_columns[2].button("Generate concise summary", width="stretch"):
        st.session_state.active_followup = "summary"

    active = st.session_state.get("active_followup")
    if active == "pathways":
        st.markdown(
            pathway_insights(go_results, match_result, local_results)
        )
    elif active == "drugs":
        st.markdown(drug_association(go_results, local_results))
    elif active == "summary":
        concise = analysis_summary(
            state.filter_result,
            match_result,
            enrichment,
            quality,
            input_file=st.session_state.get("analysis_source", ""),
            fc_cutoff=summary["fc_cutoff"],
            p_cutoff=summary["p_cutoff"],
        )
        st.code(concise, language="text")

    st.divider()
    with st.form("knowledge_query"):
        query = st.text_input(
            "Query a gene or curated cell type",
            placeholder="Examples: GFAP, MBP, 星形胶质细胞",
        )
        submitted = st.form_submit_button("Search knowledge base")
    if submitted and query:
        kb = load_kb()
        cell_types = [
            "兴奋性神经元",
            "抑制性神经元",
            "星形胶质细胞",
            "小胶质细胞",
            "少突胶质细胞",
            "神经干细胞",
            "多巴胺能神经元",
            "胆碱能神经元",
            "血清素能神经元",
        ]
        answer = ""
        for cell_type in cell_types:
            if cell_type in query:
                direction = "up" if "上调" in query else "down" if "下调" in query else ""
                answer = query_cell_type(cell_type, direction, kb)
                break
        if not answer:
            answer = query_gene(query.strip(), kb)
        st.markdown(answer)
