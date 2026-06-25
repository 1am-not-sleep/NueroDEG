"""NeuroDEG Streamlit analysis workspace."""

from __future__ import annotations

import io
import os
import tempfile
import zipfile
from dataclasses import asdict
from pathlib import Path

import pandas as pd
import streamlit as st

from analysis.loader import detect_column
from analysis.interpreter import render_report
from agent_core.conversation import handle_message
from agent_core.i18n import translate
from agent_core.memory import save_run
from agent_core.orchestrator import AnalysisRunError, run_analysis


ROOT = Path(__file__).resolve().parent
EXAMPLE_PATH = ROOT / "data" / "example_neuro_deg.csv"

st.set_page_config(page_title="NeuroDEG", layout="wide")

language = st.sidebar.segmented_control(
    "Language / 界面语言",
    ["zh", "en"],
    default="zh",
    format_func=lambda value: "中文" if value == "zh" else "English",
    key="ui_language",
)
t = lambda key: translate(language, key)

if "pending_agent_thresholds" in st.session_state:
    pending_thresholds = st.session_state.pop("pending_agent_thresholds")
    st.session_state["fc_cutoff_widget"] = pending_thresholds["fc_cutoff"]
    st.session_state["p_cutoff_widget"] = pending_thresholds["p_cutoff"]

subtitle = (
    "验证神经相关 DEG 表，识别细胞类型信号，运行离线 GO 富集，"
    "检查 Agent 决策并导出可复现的分析结果。"
    if language == "zh"
    else (
        "Validate neural DEG tables, identify cell-type signals, run offline GO enrichment, "
        "inspect agent decisions, and export a reproducible analysis bundle."
    )
)

st.markdown(
    f"""
    <style>
    .block-container {{padding-top: 1.4rem; padding-bottom: 2.5rem; max-width: 1440px;}}
    .app-kicker {{font-size: 0.78rem; color: #64748b; font-weight: 700; text-transform: uppercase;}}
    .app-title {{font-size: 2rem; font-weight: 720; color: #172033; margin: 0.2rem 0 0.3rem;}}
    .app-subtitle {{color: #526070; max-width: 900px; margin-bottom: 1.2rem;}}
    .status-ready {{color: #087f5b; font-weight: 700;}}
    .status-review {{color: #b45309; font-weight: 700;}}
    .status-blocked {{color: #b42318; font-weight: 700;}}
    div[data-testid="stMetric"] {{border-top: 2px solid #d8dee8; padding-top: 0.65rem;}}
    </style>
    <div class="app-kicker">{"生物医学分析工作台" if language == "zh" else "Biomedical analysis workspace"}</div>
    <div class="app-title">NeuroDEG</div>
    <div class="app-subtitle">{subtitle}</div>
    """,
    unsafe_allow_html=True,
)


def reset_analysis():
    for key in [
        "analysis_run",
        "active_followup",
        "analysis_source",
        "agent_messages",
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


def read_preview(uploaded_file):
    """Read an uploaded table without consuming the Streamlit upload object."""
    separator = "\t" if Path(uploaded_file.name).suffix.lower() in {".tsv", ".txt"} else ","
    payload = uploaded_file.getvalue()
    try:
        return pd.read_csv(io.BytesIO(payload), sep=separator, encoding="utf-8"), None
    except UnicodeDecodeError:
        try:
            return pd.read_csv(io.BytesIO(payload), sep=separator, encoding="gbk"), None
        except Exception as exc:
            return None, str(exc)
    except Exception as exc:
        return None, str(exc)


def input_column_mapping(frame):
    gene_column = detect_column(frame, "gene")
    fold_change_column = detect_column(frame, "log2fc")
    adjusted_column = detect_column(frame, "padj")
    raw_p_column = detect_column(frame, "pval")
    return {
        "gene": gene_column,
        "log2FC": fold_change_column,
        "significance": adjusted_column or raw_p_column,
    }


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


def preview_artifact(label, path):
    suffix = Path(path).suffix.lower()
    if suffix == ".csv":
        frame = pd.read_csv(path)
        st.dataframe(frame, width="stretch", hide_index=True)
        st.caption(
            f"{len(frame)} {t('rows').lower()} · "
            f"{len(frame.columns)} {t('columns').lower()}"
        )
    elif suffix == ".json":
        import json

        with open(path, encoding="utf-8") as handle:
            st.json(json.load(handle))
    elif suffix in {".md", ".txt"}:
        content = Path(path).read_text(encoding="utf-8")
        if suffix == ".md":
            st.markdown(content)
        else:
            st.code(content, language="text")
    elif suffix in {".png", ".jpg", ".jpeg"}:
        st.image(path, width="stretch")
    else:
        st.info(
            f"{'暂不支持预览' if language == 'zh' else 'Preview is not available for'} {label}."
        )


def render_agent_messages(has_run=False):
    messages = st.session_state.get("agent_messages", [])
    if not messages:
        with st.chat_message("assistant"):
            if language == "zh":
                st.markdown(
                    "我是 NeuroDEG Agent。我会先判断你的目标，再选择分析、基因查询、"
                    "细胞类型解释、通路解释、药物靶点、质量检查或 Trace 工具。"
                )
                st.caption(
                    "可直接输入：分析当前数据；解释 GFAP；解释 MG；总结 GO 通路；"
                    "展示分析步骤。"
                )
            else:
                st.markdown(
                    "I am the NeuroDEG Agent. I plan each request and select analysis, "
                    "gene, cell-type, pathway, drug-target, quality, or trace tools."
                )
                st.caption(
                    "Try: Analyze the current data; explain GFAP; explain MG; "
                    "summarize GO pathways; show the analysis steps."
                )
            if has_run:
                st.success(
                    "已连接当前分析结果，可以继续追问或要求重新分析。"
                    if language == "zh"
                    else "Connected to the current run. You can ask follow-ups or request reanalysis."
                )

    for message in messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            actions = message.get("actions", [])
            if actions:
                label = (
                    f"Agent 操作 ({len(actions)})"
                    if language == "zh"
                    else f"Agent actions ({len(actions)})"
                )
                with st.expander(label, expanded=False):
                    st.caption(
                        "计划 → 工具 → 观察"
                        if language == "zh"
                        else "Plan → Tool → Observation"
                    )
                    for index, action in enumerate(actions, start=1):
                        status = action.get("status", "success")
                        symbol = {
                            "success": "✓",
                            "failed": "✕",
                            "blocked": "!",
                            "review": "?",
                        }.get(status, "•")
                        st.markdown(
                            f"**{index}. {symbol} {action['tool']}**  \n"
                            f"{'原因' if language == 'zh' else 'Reason'}: {action['reason']}  \n"
                            f"{'观察' if language == 'zh' else 'Observation'}: "
                            f"{action['observation']}"
                        )


def process_agent_prompt(prompt, current_run, agent_input_file):
    st.session_state.setdefault("agent_messages", [])
    st.session_state.agent_messages.append({"role": "user", "content": prompt})
    reply = handle_message(
        prompt,
        current_run=current_run,
        input_file=agent_input_file,
        language=language,
        fc_cutoff=fc_cutoff,
        p_cutoff=p_cutoff,
        use_api=use_api,
    )
    st.session_state.agent_messages.append(
        {
            "role": "assistant",
            "content": reply.content,
            "actions": [asdict(action) for action in reply.actions],
        }
    )
    if reply.updated_run is not None:
        st.session_state.analysis_run = reply.updated_run
        st.session_state.analysis_source = os.path.basename(
            reply.updated_run.state.input_file
        )
        st.session_state.active_followup = None
        st.session_state.pending_agent_thresholds = {
            "fc_cutoff": reply.updated_run.state.params["fc_cutoff"],
            "p_cutoff": reply.updated_run.state.params["p_cutoff"],
        }
    st.rerun()


selected_preview = None
selected_preview_error = None

with st.sidebar:
    st.header(t("analysis_setup"))
    data_option = st.segmented_control(
        t("data_source"),
        ["example", "upload"],
        default="example",
        format_func=lambda value: t("example_data") if value == "example" else t("upload_file"),
    )
    uploaded_file = None
    if data_option == "upload":
        uploaded_file = st.file_uploader(t("deg_file"), type=["csv", "tsv", "txt"])
        if uploaded_file is not None:
            selected_preview, selected_preview_error = read_preview(uploaded_file)
    else:
        selected_preview = pd.read_csv(EXAMPLE_PATH)

    st.download_button(
        t("download_example"),
        EXAMPLE_PATH.read_bytes(),
        file_name="example_neuro_deg.csv",
        mime="text/csv",
        width="stretch",
    )

    st.divider()
    fc_cutoff = st.number_input(
        t("fc_cutoff"),
        min_value=0.0,
        max_value=5.0,
        value=1.0,
        step=0.1,
        key="fc_cutoff_widget",
    )
    p_cutoff = st.number_input(
        t("p_cutoff"),
        min_value=0.001,
        max_value=1.0,
        value=0.05,
        step=0.001,
        format="%.3f",
        key="p_cutoff_widget",
    )
    use_api = st.toggle(t("try_enrichr"), value=False)

    upload_unavailable = data_option == "upload" and (
        uploaded_file is None or selected_preview_error is not None
    )
    run_button = st.button(
        t("run_analysis"),
        type="primary",
        width="stretch",
        disabled=upload_unavailable,
    )
    if st.button(t("reset"), width="stretch"):
        reset_analysis()
        st.rerun()

    with st.expander(t("accepted_columns")):
        st.markdown(
            f"""
            {"必要生物学字段：" if language == "zh" else "Required biological fields:"}

            - {"基因名" if language == "zh" else "gene symbol"}: `gene`, `symbol`, `gene_name`
            - {"倍数变化" if language == "zh" else "fold change"}: `log2FC`, `logFC`, `fold_change`
            - {"显著性" if language == "zh" else "significance"}: `padj`, `p_adj`, `FDR`, `pvalue`
            """
        )


if selected_preview_error:
    st.error(
        f"{'无法预览上传表格' if language == 'zh' else 'Unable to preview the uploaded table'}: "
        f"{selected_preview_error}"
    )
elif selected_preview is not None:
    mapping = input_column_mapping(selected_preview)
    missing_fields = [name for name, column in mapping.items() if column is None]
    with st.expander(
        f"{t('input_preview')} · {len(selected_preview)} "
        f"{'行' if language == 'zh' else 'rows'} × "
        f"{len(selected_preview.columns)} {'列' if language == 'zh' else 'columns'}",
        expanded=st.session_state.get("analysis_run") is None,
    ):
        preview_metrics = st.columns(4)
        preview_metrics[0].metric(t("rows"), len(selected_preview))
        preview_metrics[1].metric(t("columns"), len(selected_preview.columns))
        preview_metrics[2].metric(
            t("gene_column"),
            mapping["gene"] or ("未找到" if language == "zh" else "Not found"),
        )
        preview_metrics[3].metric(
            t("significance"),
            mapping["significance"] or ("未找到" if language == "zh" else "Not found"),
        )
        st.caption(
            f"{t('detected_mapping')}: "
            f"gene = {mapping['gene'] or 'missing'}, "
            f"log2FC = {mapping['log2FC'] or 'missing'}, "
            f"significance = {mapping['significance'] or 'missing'}"
        )
        st.dataframe(selected_preview.head(20), width="stretch", hide_index=True)
        if missing_fields:
            st.warning(
                f"{t('missing_fields')}: "
                + ", ".join(missing_fields)
            )
        else:
            st.success(t("columns_detected"))


if run_button:
    if data_option == "upload" and uploaded_file is None:
        st.error(
            "请先选择 CSV/TSV 文件。" if language == "zh"
            else "Select a CSV/TSV file before running the analysis."
        )
    else:
        input_path = (
            str(EXAMPLE_PATH)
            if data_option == "example"
            else create_uploaded_copy(uploaded_file)
        )
        source_name = (
            EXAMPLE_PATH.name
            if data_option == "example"
            else uploaded_file.name
        )
        web_output_dir = tempfile.mkdtemp(prefix="neurodeg_web_run_")

        try:
            with st.status(t("running"), expanded=True) as status:
                st.write(
                    "正在校验并标准化 DEG 表"
                    if language == "zh"
                    else "Validating and normalizing the DEG table"
                )
                run = run_analysis(
                    input_file=input_path,
                    fc_cutoff=fc_cutoff,
                    p_cutoff=p_cutoff,
                    output_dir=web_output_dir,
                    use_api=use_api,
                    generate_visuals=True,
                    quiet=True,
                    report_language=language,
                )
                st.write(
                    "细胞类型匹配与通路富集完成"
                    if language == "zh"
                    else "Cell-type matching and pathway enrichment completed"
                )
                st.write(
                    "已生成报告、Agent 轨迹和可复现 manifest"
                    if language == "zh"
                    else "Report, trace, and reproducibility manifest generated"
                )
                status.update(label=t("analysis_complete"), state="complete", expanded=False)
            st.session_state.analysis_run = run
            st.session_state.analysis_source = source_name
            st.session_state.active_followup = None
        except AnalysisRunError as exc:
            st.error(f"{t('analysis_stopped')}: {exc}")
        except Exception as exc:
            st.exception(exc)


run = st.session_state.get("analysis_run")

if run is None:
    st.subheader(t("ready"))
    st.write(t("ready_text"))
    workflow_col, output_col = st.columns(2)
    with workflow_col:
        st.markdown(f"#### {t('agent_workflow')}")
        st.markdown(
            """
            1. 输入校验 / Input validation
            2. DEG 筛选 / DEG filtering
            3. 细胞类型匹配 / Cell-type matching
            4. GO 与本地通路富集 / Pathway enrichment
            5. 火山图与细胞类型图 / Visualizations
            6. 安全检查、质量评级和报告 / Guardrails and report
            """
        )
    with output_col:
        st.markdown(f"#### {t('output_previews')}")
        st.markdown(
            f"""
            {"分析后可直接预览：" if language == "zh" else "After analysis, preview:"}

            - {"火山图与细胞类型图" if language == "zh" else "volcano and cell-type plots"}
            - {"上下调 DEG 表" if language == "zh" else "up/down DEG tables"}
            - {"GO 与精选通路结果" if language == "zh" else "GO and curated pathways"}
            - {"Markdown 报告" if language == "zh" else "Markdown report"}
            - {"运行 manifest 与 Agent 轨迹" if language == "zh" else "run manifest and agent trace"}
            """
        )

    st.divider()
    st.markdown(
        "#### 对话式 Agent"
        if language == "zh"
        else "#### Conversational Agent"
    )
    st.caption(
        "直接说“分析当前数据”，或指定阈值：“用 log2FC 1.5、padj 0.01 分析”。"
        if language == "zh"
        else "Try: “Analyze the current data” or “Analyze with log2FC 1.5 and padj 0.01.”"
    )
    render_agent_messages(has_run=False)
    initial_prompt = st.chat_input(
        "告诉 Agent 你的分析目标..."
        if language == "zh"
        else "Tell the agent what you want to analyze..."
    )
    if initial_prompt:
        agent_input_file = None
        if data_option == "example":
            agent_input_file = str(EXAMPLE_PATH)
        elif uploaded_file is not None:
            agent_input_file = create_uploaded_copy(uploaded_file)
        process_agent_prompt(initial_prompt, None, agent_input_file)
    st.stop()


state = run.state
if state.params.get("report_language") != language:
    report_path = state.artifacts.get("report")
    state.report = render_report(
        state.filter_result,
        state.match_result,
        state.enrichment_result,
        input_file=st.session_state.get("analysis_source", ""),
        output_path=report_path,
        language=language,
    )
    state.params["report_language"] = language
    save_run(
        state,
        run.trace,
        run.quality,
        output_dir=run.output_dir,
        run_id=state.run_id,
    )

summary = state.filter_result["summary"]
match_result = state.match_result
enrichment = state.enrichment_result
quality = run.quality
grade = quality["grade"]

st.markdown(
    f"{t('source')}: `{st.session_state.get('analysis_source', '')}` &nbsp;·&nbsp; "
    f"{t('run')}: `{state.run_id}` &nbsp;·&nbsp; "
    f"{t('status')}: <span class='{status_class(grade)}'>{grade.upper()}</span>",
    unsafe_allow_html=True,
)

metric_columns = st.columns(6)
metric_columns[0].metric(t("genes"), summary["total_genes"])
metric_columns[1].metric(t("significant"), summary["significant"])
metric_columns[2].metric(t("up"), summary["up"])
metric_columns[3].metric(t("down"), summary["down"])
metric_columns[4].metric(t("cell_types"), match_result["total_matched_types"])
metric_columns[5].metric(t("go_terms"), len(enrichment.get("go", [])))

if state.warnings:
    with st.expander(f"{t('run_notes')} ({len(state.warnings)})", expanded=grade != "ready"):
        for warning in state.warnings:
            st.warning(warning)

tabs = st.tabs(
    [
        t("ask_agent"),
        t("overview"),
        t("visualizations"),
        t("cell_types"),
        t("pathway_enrichment"),
        t("agent_trace"),
        t("report"),
        t("artifacts"),
    ]
)

with tabs[1]:
    left, right = st.columns([1.5, 1])
    with left:
        st.markdown(f"#### {t('deg_summary')}")
        gene_tabs = st.tabs([t("top_up"), t("top_down")])
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
        st.markdown(f"#### {t('quality')}")
        st.markdown(
            f"<div class='{status_class(grade)}'>{grade.upper()}</div>",
            unsafe_allow_html=True,
        )
        if language == "en":
            quality_messages = {
                "ready": "Input validation, cell-type matching, and safety checks passed.",
                "review": "The analysis completed, but one or more findings require review.",
                "blocked": "The current input does not support a reliable biological interpretation.",
            }
            st.write(f"- {quality_messages.get(grade, grade)}")
        else:
            for reason in quality.get("reasons", []):
                st.write(f"- {reason}")
        st.markdown(f"#### {t('export')}")
        st.download_button(
            t("download_report"),
            state.report,
            file_name=f"{state.run_id}_report.md",
            mime="text/markdown",
            width="stretch",
        )
        st.download_button(
            t("download_bundle"),
            build_result_bundle(run),
            file_name=f"{state.run_id}_results.zip",
            mime="application/zip",
            width="stretch",
        )

with tabs[2]:
    plot_columns = st.columns(2)
    with plot_columns[0]:
        st.markdown(f"#### {t('volcano_plot')}")
        volcano_path = state.artifacts.get("volcano_plot")
        if volcano_path and os.path.exists(volcano_path):
            st.image(volcano_path, width="stretch")
        else:
            st.info("未生成火山图。" if language == "zh" else "Volcano plot was not generated.")
    with plot_columns[1]:
        st.markdown(f"#### {t('cell_type_changes')}")
        cell_type_path = state.artifacts.get("cell_type_bar")
        if cell_type_path and os.path.exists(cell_type_path):
            st.image(cell_type_path, width="stretch")
        else:
            st.info(
                "当前运行没有细胞类型图。"
                if language == "zh"
                else "No cell-type plot is available for this run."
            )

with tabs[3]:
    if not match_result["results"]:
        st.info(t("no_cell_type"))
    else:
        cell_rows = [
            {
                t("chinese_name"): item.get("type_zh", ""),
                t("english_name"): item.get("type_en", item["type"]),
                t("abbreviation"): item.get("abbreviation", ""),
                ("来源" if language == "zh" else "Source"): item.get("source", ""),
                ("匹配 marker" if language == "zh" else "Matched"): item["matched"],
                ("marker 总数" if language == "zh" else "Marker total"): item["total_markers"],
                t("up"): item["up_count"],
                t("down"): item["down_count"],
                ("主要方向" if language == "zh" else "Direction"): item["main_direction"],
            }
            for item in match_result["results"]
        ]
        st.dataframe(pd.DataFrame(cell_rows), width="stretch", hide_index=True)
        for item in match_result["results"]:
            with st.expander(
                f"{item.get('display_name', item['type'])} · "
                f"{item['matched']}/{item['total_markers']} markers"
            ):
                st.write(
                    f"{'来源' if language == 'zh' else 'Source'}: {item.get('source', '')}"
                )
                st.write(
                    f"{'上调 marker' if language == 'zh' else 'Up-regulated markers'}: "
                    f"{item['up_genes'] or ('无' if language == 'zh' else 'None')}"
                )
                st.write(
                    f"{'下调 marker' if language == 'zh' else 'Down-regulated markers'}: "
                    f"{item['down_genes'] or ('无' if language == 'zh' else 'None')}"
                )
                st.write(item["interpretation"])

with tabs[4]:
    go_results = enrichment.get("go", [])
    local_results = enrichment.get("local", [])
    enrichment_tabs = st.tabs(
        [t("go_overrepresentation"), t("curated_pathways"), t("enrichr")]
    )
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
            st.info(
                "未发现符合当前标准的 GO 通路。"
                if language == "zh"
                else "No GO terms passed the configured criteria."
            )
    with enrichment_tabs[1]:
        if local_results:
            st.dataframe(pd.DataFrame(local_results), width="stretch", hide_index=True)
        else:
            st.info(
                "未检测到精选通路重叠。"
                if language == "zh"
                else "No curated pathway overlap was detected."
            )
    with enrichment_tabs[2]:
        api_status = enrichment.get("api_status", "disabled")
        if api_status == "success":
            st.dataframe(pd.DataFrame(enrichment["api"]), width="stretch", hide_index=True)
        elif api_status == "failed":
            st.warning(
                "Enrichr 不可用，离线 GO 与精选通路结果仍然有效。"
                if language == "zh"
                else "Enrichr was unavailable. Offline GO and curated pathway results remain valid."
            )
            st.caption(enrichment.get("api_error", ""))
        else:
            st.info(
                "当前运行未启用 Enrichr。"
                if language == "zh"
                else "Enrichr was not requested for this run."
            )

with tabs[5]:
    trace_table = pd.DataFrame(run.trace.to_list())
    st.dataframe(trace_table, width="stretch", hide_index=True)
    st.markdown(f"#### {t('guardrails')}")
    if run.guardrail_warnings:
        st.dataframe(
            pd.DataFrame(run.guardrail_warnings),
            width="stretch",
            hide_index=True,
        )
    else:
        st.success(t("no_guardrail"))

with tabs[6]:
    st.download_button(
        t("download_report"),
        state.report,
        file_name=f"{state.run_id}_report.md",
        mime="text/markdown",
    )
    st.markdown(state.report)

with tabs[7]:
    artifact_rows = []
    for name, path in state.artifacts.items():
        if path and os.path.exists(path):
            artifact_rows.append(
                {
                    "artifact": name,
                    "file": os.path.basename(path),
                    "type": Path(path).suffix.lower().lstrip("."),
                    "size_kb": round(os.path.getsize(path) / 1024, 1),
                    "path": path,
                }
            )

    st.dataframe(
        pd.DataFrame(artifact_rows).drop(columns=["path"]),
        width="stretch",
        hide_index=True,
    )
    artifact_options = {
        f"{row['artifact']} · {row['file']}": row["path"]
        for row in artifact_rows
    }
    selected_artifact = st.selectbox(
        t("preview_artifact"),
        list(artifact_options),
    )
    if selected_artifact:
        preview_artifact(selected_artifact, artifact_options[selected_artifact])

with tabs[0]:
    st.markdown(
        "使用自然语言要求 Agent 调用分析工具、调整阈值、解释结果或说明局限。"
        if language == "zh"
        else (
            "Ask the agent to call analysis tools, change thresholds, explain results, "
            "or describe limitations."
        )
    )
    quick_prompts = (
        [
            "总结本次结果",
            "解释 MG 和 Oligo 的变化",
            "最显著的 GO 通路是什么？",
            "这些结论有哪些局限？",
        ]
        if language == "zh"
        else [
            "Summarize this run",
            "Explain MG and Oligo changes",
            "What are the top GO pathways?",
            "What are the limitations?",
        ]
    )
    quick_columns = st.columns(4)
    for index, quick_prompt in enumerate(quick_prompts):
        if quick_columns[index].button(
            quick_prompt,
            key=f"agent_quick_{language}_{index}",
            width="stretch",
        ):
            process_agent_prompt(
                quick_prompt,
                run,
                run.state.input_file,
            )

    render_agent_messages(has_run=True)
    chat_prompt = st.chat_input(
        "例如：用 log2FC 1.5、padj 0.01 重新分析"
        if language == "zh"
        else "Example: Reanalyze with log2FC 1.5 and padj 0.01"
    )
    if chat_prompt:
        process_agent_prompt(
            chat_prompt,
            run,
            run.state.input_file,
        )
