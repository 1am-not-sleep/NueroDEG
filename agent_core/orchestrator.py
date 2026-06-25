"""Shared NeuroDEG agent orchestration for CLI and Streamlit."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from analysis.enrichment import run_enrichment
from analysis.filter import filter_degs, get_volcano_data
from analysis.interpreter import render_report
from analysis.loader import load_deg, summarize_deg
from analysis.neural_matcher import load_knowledge_base, match_neural_types
from agent_core.guardrails import check_input_guardrails, check_output_guardrails
from agent_core.memory import make_run_id, save_run
from agent_core.quality import QualityEvaluator
from agent_core.state import AgentState
from agent_core.trace import TraceRecorder
from utils.visualizer import plot_cell_type_bar, plot_volcano


class AnalysisRunError(RuntimeError):
    """Raised when an analysis cannot continue."""


@dataclass
class AnalysisRun:
    state: AgentState
    trace: TraceRecorder
    quality: dict
    guardrail_warnings: list[dict]
    output_dir: str


def _empty_match_result():
    return {"results": [], "total_matched_types": 0}


def _empty_enrichment_result():
    return {
        "go": [],
        "local": [],
        "api": None,
        "api_status": "disabled",
        "api_error": None,
    }


def run_analysis(
    input_file,
    fc_cutoff=1.0,
    p_cutoff=0.05,
    output_dir=None,
    use_api=False,
    generate_visuals=True,
    quiet=False,
    report_language="zh",
):
    input_file = str(input_file)
    run_id = make_run_id()
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(__file__), "..", "results", run_id)
    output_dir = str(Path(output_dir).resolve())
    os.makedirs(output_dir, exist_ok=True)

    state = AgentState(
        input_file,
        {
            "fc_cutoff": fc_cutoff,
            "p_cutoff": p_cutoff,
            "use_api": use_api,
            "generate_visuals": generate_visuals,
            "report_language": report_language,
        },
        run_id=run_id,
        output_dir=output_dir,
    )
    trace = TraceRecorder()

    step = trace.start("Input Checker", {"file": str(input_file)})
    input_checks = check_input_guardrails(str(input_file))
    if any(item["level"] == "error" for item in input_checks):
        trace.finish(step, "failed", {"guardrails": input_checks})
        state.errors.extend(item["message"] for item in input_checks)
        raise AnalysisRunError("; ".join(state.errors))
    try:
        state.input_df = load_deg(str(input_file))
        if not quiet:
            summarize_deg(state.input_df, fc_cutoff, p_cutoff)
        trace.finish(step, "success", {"genes": len(state.input_df)})
    except Exception as exc:
        trace.finish(step, "failed", {"error": str(exc)})
        state.errors.append(str(exc))
        raise AnalysisRunError(str(exc)) from exc

    step = trace.start(
        "DEG Filter",
        {"fc_cutoff": fc_cutoff, "p_cutoff": p_cutoff},
    )
    state.filter_result = filter_degs(state.input_df, fc_cutoff, p_cutoff)
    trace.finish(step, "success", state.filter_result["summary"])

    significant = state.filter_result["summary"]["significant"]
    if significant == 0:
        state.warnings.append("未检测到显著差异基因，请尝试放宽阈值")

    if significant >= 10:
        decision = f"显著基因 {significant} >= 10，执行细胞类型匹配"
        step = trace.start("Neural Matcher", decision=decision)
        kb, gene_to_cell = load_knowledge_base()
        state.match_result = match_neural_types(
            state.filter_result["up"],
            state.filter_result["down"],
            kb,
            gene_to_cell,
        )
        trace.finish(
            step,
            "success",
            {"matched_types": state.match_result["total_matched_types"]},
        )

        step = trace.start("Enrichment", decision=f"显著基因 {significant} >= 10")
        state.enrichment_result = run_enrichment(
            state.filter_result["all"]["gene"].tolist(),
            use_api=use_api,
        )
        if state.enrichment_result.get("api_status") == "failed":
            message = f"Enrichr API 不可用，已使用本地 GO/通路结果: {state.enrichment_result.get('api_error', '')}"
            state.warnings.append(message)
        trace.finish(
            step,
            "success",
            {
                "go_pathways": len(state.enrichment_result["go"]),
                "local_pathways": len(state.enrichment_result["local"]),
                "api_status": state.enrichment_result.get("api_status"),
            },
        )
    else:
        message = f"显著基因 ({significant}) 不足 10 个，跳过细胞匹配和富集"
        state.warnings.append(message)
        state.match_result = _empty_match_result()
        state.enrichment_result = _empty_enrichment_result()
        step = trace.start("Neural Matcher", decision=message)
        trace.finish(step, "skipped")
        step = trace.start("Enrichment", decision=message)
        trace.finish(step, "skipped")

    if generate_visuals:
        step = trace.start("Visualization")
        try:
            volcano_path = os.path.join(output_dir, "volcano.png")
            volcano_data = get_volcano_data(state.input_df, fc_cutoff, p_cutoff)
            plot_volcano(
                volcano_data,
                volcano_path,
                title=f"Volcano Plot (|log2FC|>{fc_cutoff}, padj<{p_cutoff})",
                fc_cutoff=fc_cutoff,
                p_cutoff=p_cutoff,
            )
            state.artifacts["volcano_plot"] = volcano_path

            if state.match_result["results"]:
                cell_type_path = os.path.join(output_dir, "cell_type_bar.png")
                plot_cell_type_bar(state.match_result, cell_type_path)
                state.artifacts["cell_type_bar"] = cell_type_path

            trace.finish(step, "success", state.artifacts.copy())
        except Exception as exc:
            state.warnings.append(f"可视化生成失败: {exc}")
            trace.finish(step, "failed", {"error": str(exc)})

    step = trace.start("Report Generator")
    report_path = os.path.join(output_dir, "report.md")
    state.report = render_report(
        state.filter_result,
        state.match_result,
        state.enrichment_result,
        input_file=os.path.basename(str(input_file)),
        output_path=report_path,
        language=report_language,
    )
    state.artifacts["report"] = report_path
    trace.finish(step, "success", {"path": report_path})

    output_guardrails = check_output_guardrails(state.report)
    state.warnings.extend(item["message"] for item in output_guardrails)

    evaluator = QualityEvaluator()
    quality = evaluator.evaluate(
        state.filter_result,
        state.match_result,
        input_checks + output_guardrails,
    )

    state.artifacts.update({
        "up_genes": os.path.join(output_dir, "up_genes.csv"),
        "down_genes": os.path.join(output_dir, "down_genes.csv"),
        "run_manifest": os.path.join(output_dir, "run_manifest.json"),
    })
    save_run(state, trace, quality, output_dir=output_dir, run_id=run_id)

    return AnalysisRun(
        state=state,
        trace=trace,
        quality=quality,
        guardrail_warnings=input_checks + output_guardrails,
        output_dir=output_dir,
    )
