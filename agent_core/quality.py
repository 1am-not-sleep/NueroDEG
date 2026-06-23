from __future__ import annotations

from pathlib import Path

import pandas as pd

from agent_core.state import AgentQualityReport, GuardrailCheck, QualityCheck
from tools.deg_filter import DegSummary
from tools.neural_classifier import ModuleHit


def evaluate_run(
    summary: DegSummary,
    module_hits: list[ModuleHit],
    enrichment_table: pd.DataFrame,
    report: str,
    output_paths: dict[str, Path],
    guardrails: list[GuardrailCheck],
) -> AgentQualityReport:
    checks = [
        QualityCheck("has_significant_gene_summary", summary.significant_genes >= 0, "DEG summary was generated."),
        QualityCheck("has_volcano_plot", output_paths.get("volcano_plot", Path()).exists(), "Volcano plot exists."),
        QualityCheck("has_report", bool(report.strip()), "Markdown report was generated."),
        QualityCheck("has_modules", len(module_hits) > 0, "At least one neural module was detected."),
        QualityCheck(
            "has_enrichment_table",
            enrichment_table is not None,
            "Marker-set overrepresentation table was created, even if empty.",
        ),
        QualityCheck("has_limitations", "## 9. Limitations" in report, "Report includes limitations."),
        QualityCheck("has_validation", "## 10. Suggested Validation" in report, "Report includes validation suggestions."),
        QualityCheck(
            "guardrails_passed",
            all(check.passed or check.severity != "error" for check in guardrails),
            "No error-level guardrail failures.",
        ),
    ]

    passed = sum(1 for check in checks if check.passed)
    score = round(passed / len(checks), 3)
    recommendations: list[str] = []

    if summary.significant_genes < 5:
        recommendations.append("Use a richer DEG table or lower-confidence language because very few genes passed cutoffs.")
    if not module_hits:
        recommendations.append("Expand the marker dictionary or run GO/KEGG enrichment for broader biological coverage.")
    if not all(check.passed or check.severity != "error" for check in guardrails):
        recommendations.append("Fix error-level guardrail failures before using the report in a presentation.")
    if enrichment_table is not None and enrichment_table.empty:
        recommendations.append("Marker enrichment was empty; consider GSEApy or a larger background gene universe.")

    if any(not check.passed and check.severity == "error" for check in guardrails):
        grade = "blocked"
    elif score < 0.75 or recommendations:
        grade = "review"
    else:
        grade = "ready"

    return AgentQualityReport(score=score, grade=grade, checks=checks, recommendations=recommendations)
