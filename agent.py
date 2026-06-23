from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from agent_core.guardrails import input_guardrails, interpretation_guardrails
from agent_core.memory import save_run_memory
from agent_core.planner import decision_after_filter, decision_after_input, initial_plan
from agent_core.quality import evaluate_run
from agent_core.state import AgentQualityReport, AgentState, AgentStep, GuardrailCheck
from tools.deg_filter import DegSummary, filter_deg
from tools.enrichment import run_marker_enrichment
from tools.input_checker import InputCheckResult, check_input
from tools.knowledge_retriever import retrieve_knowledge
from tools.neural_classifier import ModuleHit, classify_neural_modules, module_hits_to_frame
from tools.plotting import plot_volcano
from tools.report_generator import generate_report


@dataclass
class AgentResult:
    success: bool
    message: str
    input_result: InputCheckResult
    deg_summary: DegSummary | None = None
    module_hits: list[ModuleHit] = field(default_factory=list)
    enrichment_table: pd.DataFrame | None = None
    report: str = ""
    output_paths: dict[str, Path] = field(default_factory=dict)
    state: AgentState | None = None
    trace: list[AgentStep] = field(default_factory=list)
    guardrails: list[GuardrailCheck] = field(default_factory=list)
    quality: AgentQualityReport | None = None
    run_id: str = ""


def _empty_enrichment_table() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "direction",
            "term",
            "overlap_count",
            "set_size",
            "query_size",
            "background_size",
            "p_value",
            "fdr",
            "overlap_genes",
            "method",
        ]
    )


def run_agent(
    df: pd.DataFrame,
    comparison_info: str = "",
    species: str = "human",
    output_dir: str | Path = "results",
    logfc_cutoff: float = 1.0,
    padj_cutoff: float = 0.05,
) -> AgentResult:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    state = AgentState.create(
        comparison_info=comparison_info,
        species=species,
        output_dir=output_dir,
        logfc_cutoff=logfc_cutoff,
        padj_cutoff=padj_cutoff,
    )
    state.trace = initial_plan()

    state.trace[0].start(
        "Validate the uploaded table before running any biological interpretation.",
        {"columns": list(df.columns), "rows": len(df)},
    )
    input_result = check_input(df)
    state.guardrails.extend(input_guardrails(input_result))
    continue_analysis, input_decision = decision_after_input(input_result)
    state.add_decision(input_decision)
    state.trace[0].complete(
        input_result.message,
        {
            "valid": input_result.valid,
            "warnings": input_result.warnings,
            "missing_columns": input_result.missing_columns,
        },
    )

    if not input_result.valid:
        for step in state.trace[1:]:
            step.skip("Blocked because the input table did not pass validation.")
        state.confidence = "low"
        state.human_review_reasons.append(input_result.message)
        return AgentResult(
            False,
            input_result.message,
            input_result=input_result,
            state=state,
            trace=state.trace,
            guardrails=state.guardrails,
            run_id=state.run_id,
        )

    assert input_result.df is not None
    state.trace[1].start(
        "Input is valid, so filter up/down DEG sets with configured thresholds.",
        {"logfc_cutoff": logfc_cutoff, "padj_cutoff": padj_cutoff},
    )
    deg_summary = filter_deg(input_result.df, logfc_cutoff=logfc_cutoff, padj_cutoff=padj_cutoff)
    run_enrichment, filter_decision, review_reasons, confidence = decision_after_filter(deg_summary)
    state.add_decision(filter_decision)
    state.human_review_reasons.extend(review_reasons)
    state.confidence = confidence
    state.trace[1].complete(
        f"Detected {deg_summary.up_count} up-regulated and {deg_summary.down_count} down-regulated genes.",
        {
            "total_genes": deg_summary.total_genes,
            "significant_genes": deg_summary.significant_genes,
            "up_count": deg_summary.up_count,
            "down_count": deg_summary.down_count,
            "confidence": state.confidence,
        },
    )

    up_path = output_dir / "up_genes.csv"
    down_path = output_dir / "down_genes.csv"
    annotated_path = output_dir / "annotated_genes.csv"
    volcano_path = output_dir / "volcano_plot.png"
    modules_path = output_dir / "neural_modules.csv"
    enrichment_path = output_dir / "marker_enrichment.csv"
    report_path = output_dir / "report.md"

    deg_summary.up.to_csv(up_path, index=False)
    deg_summary.down.to_csv(down_path, index=False)
    deg_summary.annotated.to_csv(annotated_path, index=False)

    state.trace[2].start("Generate a volcano plot because the input and DEG filtering steps succeeded.")
    plot_volcano(deg_summary.annotated, volcano_path, logfc_cutoff=logfc_cutoff, padj_cutoff=padj_cutoff)
    state.trace[2].complete("Volcano plot generated.", {"path": str(volcano_path)})

    state.trace[3].start("Classify significant genes against curated neural marker modules.")
    module_hits = classify_neural_modules(deg_summary.up, deg_summary.down)
    module_frame = module_hits_to_frame(module_hits)
    module_frame.to_csv(modules_path, index=False)
    state.trace[3].complete(
        f"Detected {len(module_hits)} neural module hit(s).",
        {"modules": [hit.label for hit in module_hits]},
    )

    if run_enrichment:
        state.trace[4].start("Run marker-set enrichment because the significant gene set is large enough.")
        enrichment_table = run_marker_enrichment(deg_summary.up, deg_summary.down, deg_summary.annotated)
        state.trace[4].complete(
            f"Generated {len(enrichment_table)} marker-set enrichment row(s).",
            {"rows": len(enrichment_table)},
        )
    else:
        enrichment_table = _empty_enrichment_table()
        state.trace[4].skip(filter_decision)
    enrichment_table.to_csv(enrichment_path, index=False)

    state.trace[5].start("Retrieve local knowledge notes mapped to detected modules.")
    knowledge_notes = retrieve_knowledge(module_hits)
    state.trace[5].complete(
        f"Retrieved {len(knowledge_notes)} knowledge note(s).",
        {"documents": list(knowledge_notes.keys())},
    )

    state.trace[6].start("Generate a constrained biomedical report from tool outputs and retrieved notes.")
    report = generate_report(
        comparison_info=comparison_info,
        species=species,
        input_result=input_result,
        deg_summary=deg_summary,
        module_hits=module_hits,
        enrichment_table=enrichment_table,
        knowledge_notes=knowledge_notes,
        run_id=state.run_id,
        confidence=state.confidence,
        agent_decisions=state.decisions,
        human_review_reasons=state.human_review_reasons,
    )
    report_path.write_text(report, encoding="utf-8")
    state.trace[6].complete("Report generated.", {"path": str(report_path), "characters": len(report)})

    state.trace[7].start("Check report for required sections and overconfident biomedical language.")
    state.guardrails.extend(interpretation_guardrails(report, deg_summary))
    failed_guardrails = [check.name for check in state.guardrails if not check.passed and check.severity == "error"]
    state.trace[7].complete(
        "Output guardrails completed.",
        {"error_failures": failed_guardrails, "guardrail_count": len(state.guardrails)},
    )

    output_paths = {
        "up_genes": up_path,
        "down_genes": down_path,
        "annotated_genes": annotated_path,
        "volcano_plot": volcano_path,
        "neural_modules": modules_path,
        "marker_enrichment": enrichment_path,
        "report": report_path,
    }

    state.trace[8].start("Evaluate whether this run is demo-ready or needs human review.")
    quality = evaluate_run(
        summary=deg_summary,
        module_hits=module_hits,
        enrichment_table=enrichment_table,
        report=report,
        output_paths=output_paths,
        guardrails=state.guardrails,
    )
    state.quality = quality
    state.trace[8].complete(
        f"Quality grade: {quality.grade}; score: {quality.score}.",
        {
            "score": quality.score,
            "grade": quality.grade,
            "recommendations": quality.recommendations,
        },
    )

    state.trace[9].start("Persist a JSON manifest for reproducibility and agent observability.")
    manifest_path = output_dir / "runs" / state.run_id / "run_manifest.json"
    output_paths["run_manifest"] = manifest_path
    state.trace[9].complete("Run manifest persisted.", {"path": str(manifest_path)})
    manifest_path = save_run_memory(
        state,
        {
            "comparison_info": comparison_info,
            "species": species,
            "output_paths": {name: str(path) for name, path in output_paths.items()},
            "summary": {
                "total_genes": deg_summary.total_genes,
                "up_count": deg_summary.up_count,
                "down_count": deg_summary.down_count,
                "significant_genes": deg_summary.significant_genes,
            },
        },
    )

    return AgentResult(
        True,
        "Analysis completed.",
        input_result=input_result,
        deg_summary=deg_summary,
        module_hits=module_hits,
        enrichment_table=enrichment_table,
        report=report,
        output_paths=output_paths,
        state=state,
        trace=state.trace,
        guardrails=state.guardrails,
        quality=quality,
        run_id=state.run_id,
    )
