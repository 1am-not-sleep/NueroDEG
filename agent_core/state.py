from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4


StepStatus = Literal["planned", "running", "completed", "skipped", "blocked", "failed"]
ConfidenceLevel = Literal["high", "medium", "low"]


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


@dataclass
class AgentStep:
    step_id: str
    tool_name: str
    purpose: str
    status: StepStatus = "planned"
    decision: str = ""
    observation: str = ""
    inputs: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)
    started_at: str | None = None
    ended_at: str | None = None

    def start(self, decision: str = "", inputs: dict[str, Any] | None = None) -> None:
        self.status = "running"
        self.started_at = utc_now()
        if decision:
            self.decision = decision
        if inputs:
            self.inputs.update(inputs)

    def complete(self, observation: str, outputs: dict[str, Any] | None = None) -> None:
        self.status = "completed"
        self.observation = observation
        self.ended_at = utc_now()
        if outputs:
            self.outputs.update(outputs)

    def skip(self, reason: str) -> None:
        self.status = "skipped"
        self.observation = reason
        self.ended_at = utc_now()

    def fail(self, reason: str) -> None:
        self.status = "failed"
        self.observation = reason
        self.ended_at = utc_now()


@dataclass
class GuardrailCheck:
    name: str
    passed: bool
    severity: Literal["info", "warning", "error"]
    message: str


@dataclass
class QualityCheck:
    name: str
    passed: bool
    message: str


@dataclass
class AgentQualityReport:
    score: float
    grade: Literal["ready", "review", "blocked"]
    checks: list[QualityCheck]
    recommendations: list[str]


@dataclass
class AgentState:
    run_id: str
    comparison_info: str
    species: str
    output_dir: Path
    logfc_cutoff: float
    padj_cutoff: float
    created_at: str = field(default_factory=utc_now)
    trace: list[AgentStep] = field(default_factory=list)
    guardrails: list[GuardrailCheck] = field(default_factory=list)
    quality: AgentQualityReport | None = None
    confidence: ConfidenceLevel = "medium"
    human_review_reasons: list[str] = field(default_factory=list)
    decisions: list[str] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        comparison_info: str,
        species: str,
        output_dir: str | Path,
        logfc_cutoff: float,
        padj_cutoff: float,
    ) -> "AgentState":
        return cls(
            run_id=uuid4().hex[:12],
            comparison_info=comparison_info,
            species=species,
            output_dir=Path(output_dir),
            logfc_cutoff=logfc_cutoff,
            padj_cutoff=padj_cutoff,
        )

    def add_decision(self, decision: str) -> None:
        self.decisions.append(decision)

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["output_dir"] = str(self.output_dir)
        return data
