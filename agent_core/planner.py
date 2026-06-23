from __future__ import annotations

from agent_core.state import AgentStep
from tools.deg_filter import DegSummary
from tools.input_checker import InputCheckResult


def initial_plan() -> list[AgentStep]:
    return [
        AgentStep("01", "Input Checker", "Validate the uploaded DEG table and normalize accepted column aliases."),
        AgentStep("02", "DEG Filter", "Filter statistically significant up- and down-regulated genes."),
        AgentStep("03", "Volcano Plot Tool", "Generate a volcano plot for quality inspection and presentation."),
        AgentStep("04", "Neural Module Classifier", "Detect neural cell-type and function modules from marker genes."),
        AgentStep("05", "Marker Enrichment Tool", "Run marker-set overrepresentation analysis with FDR correction."),
        AgentStep("06", "Knowledge Retriever", "Retrieve local biomedical knowledge relevant to detected modules."),
        AgentStep("07", "Report Generator", "Generate a structured biological interpretation report."),
        AgentStep("08", "Output Guardrails", "Check the report for unsafe or overconfident biomedical claims."),
        AgentStep("09", "Quality Evaluator", "Score whether the run is ready for demo or needs human review."),
        AgentStep("10", "Run Memory", "Persist trace, manifest, and quality metadata for reproducibility."),
    ]


def decision_after_input(result: InputCheckResult) -> tuple[bool, str]:
    if not result.valid:
        return False, f"Input is invalid: {result.message}"
    if result.warnings:
        return True, "Input is valid with warnings; continue analysis and surface warnings to the user."
    return True, "Input is valid; continue with DEG filtering."


def decision_after_filter(summary: DegSummary) -> tuple[bool, str, list[str], str]:
    reasons: list[str] = []
    confidence = "medium"
    run_enrichment = True

    if summary.significant_genes == 0:
        run_enrichment = False
        confidence = "low"
        reasons.append("No significant genes passed the configured cutoffs.")
    elif summary.significant_genes < 5:
        run_enrichment = False
        confidence = "low"
        reasons.append("Fewer than five significant genes passed the cutoffs; enrichment is unstable.")
    elif summary.significant_genes < 15:
        confidence = "medium"
        reasons.append("The significant gene set is modest; interpretation should remain exploratory.")
    else:
        confidence = "high"

    if run_enrichment:
        decision = "Significant gene count is sufficient for marker-set overrepresentation."
    else:
        decision = "Skip marker-set enrichment and generate a low-confidence interpretation."

    return run_enrichment, decision, reasons, confidence
