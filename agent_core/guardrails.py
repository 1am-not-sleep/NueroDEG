from __future__ import annotations

import re

from agent_core.state import GuardrailCheck
from tools.deg_filter import DegSummary
from tools.input_checker import InputCheckResult


ABSOLUTE_CLAIM_PATTERNS = [
    r"\bproves that\b",
    r"\bdefinitively proves\b",
    r"\bdiagnoses\b",
    r"\bcures\b",
    r"\bwill cure\b",
    r"\bconfirms the disease mechanism\b",
    r"\bguarantees\b",
]


def input_guardrails(input_result: InputCheckResult) -> list[GuardrailCheck]:
    checks = [
        GuardrailCheck(
            "required_columns",
            input_result.valid,
            "error" if not input_result.valid else "info",
            input_result.message,
        )
    ]

    if input_result.df is not None:
        checks.append(
            GuardrailCheck(
                "non_empty_table",
                len(input_result.df) > 0,
                "error",
                f"Input contains {len(input_result.df)} rows.",
            )
        )

    for warning in input_result.warnings:
        checks.append(GuardrailCheck("input_warning", True, "warning", warning))

    return checks


def interpretation_guardrails(report: str, summary: DegSummary) -> list[GuardrailCheck]:
    lowered = report.lower()
    checks: list[GuardrailCheck] = []

    absolute_hits = [
        pattern for pattern in ABSOLUTE_CLAIM_PATTERNS if re.search(pattern, lowered, flags=re.IGNORECASE)
    ]
    checks.append(
        GuardrailCheck(
            "no_absolute_biomedical_claims",
            not absolute_hits,
            "error" if absolute_hits else "info",
            "No unsupported absolute biomedical claims were detected."
            if not absolute_hits
            else f"Unsupported absolute claim pattern(s) detected: {', '.join(absolute_hits)}",
        )
    )

    checks.append(
        GuardrailCheck(
            "has_limitations",
            "## 9. Limitations" in report,
            "error",
            "Report includes a limitations section.",
        )
    )
    checks.append(
        GuardrailCheck(
            "has_validation",
            "## 10. Suggested Validation" in report,
            "warning",
            "Report includes suggested biological validation steps.",
        )
    )

    if summary.significant_genes < 5:
        checks.append(
            GuardrailCheck(
                "low_signal_warning",
                "small" in lowered or "exploratory" in lowered,
                "warning",
                "Low significant-gene count is explicitly surfaced in the report.",
            )
        )

    return checks
