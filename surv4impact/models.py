from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, Field


Severity = Literal["Crítica", "Elevada", "Moderada", "Baixa", "Informativa"]
ReviewDecision = Literal["Pendente", "Aceitar", "Modificar", "Rejeitar", "N.A."]


@dataclass(slots=True)
class QuestionnaireMetadata:
    title: str = "Questionário sem título"
    application_mode: str = ""
    primary_device: str = ""
    target_audience: str = ""
    audience_profile: str = ""
    accessibility_needs: str = ""
    accommodations: str = ""
    has_progress_indicator: bool | None = None
    automatic_routing: bool | None = None
    tested_on_device: bool | None = None
    layout_evidence_available: bool = False
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Question:
    id: str
    label: str
    text: str
    section: str = "Sem secção"
    options: list[str] = field(default_factory=list)
    question_type: str = "aberta"
    source: str = ""
    word_count: int = 0
    matrix_rows: int = 0
    matrix_columns: int = 0
    min_font_pt: float | None = None
    routing_text: str = ""
    required: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Questionnaire:
    title: str
    questions: list[Question] = field(default_factory=list)
    sections: list[str] = field(default_factory=list)
    instructions: list[str] = field(default_factory=list)
    raw_text: str = ""
    source_name: str = ""
    parse_warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "questions": [question.to_dict() for question in self.questions],
            "sections": self.sections,
            "instructions": self.instructions,
            "raw_text": self.raw_text,
            "source_name": self.source_name,
            "parse_warnings": self.parse_warnings,
        }


@dataclass(slots=True)
class Finding:
    finding_id: str
    criterion_id: str
    rule_id: str
    element_id: str
    element_text: str
    title: str
    finding_type: str
    severity: str
    confidence: float
    evidence: str
    explanation: str
    recommendation: str
    method: str
    source: str = ""
    component: str = ""
    related_criteria: list[str] = field(default_factory=list)
    improved_wording: str = ""
    expert_decision: str = "Pendente"
    expert_severity: str = ""
    expert_comment: str = ""
    expert_recommendation: str = ""

    @property
    def effective_severity(self) -> str:
        return self.expert_severity or self.severity

    @property
    def effective_recommendation(self) -> str:
        return self.expert_recommendation or self.recommendation

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["effective_severity"] = self.effective_severity
        result["effective_recommendation"] = self.effective_recommendation
        return result


@dataclass(slots=True)
class Synthesis:
    classification: str
    status: str
    rationale: str
    confirmed_counts: dict[str, int]
    proposed_counts: dict[str, int]
    evidence_complete: bool
    reviewed_findings: int
    total_findings: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class AISemanticFinding(BaseModel):
    criterion_id: str = Field(description="Identificador do critério SURV4IMPACT P0")
    question_id: str
    assessment: Literal["sem_problema", "potencial_problema", "evidencia_insuficiente"]
    title: str
    severity: Literal["Crítica", "Elevada", "Moderada", "Baixa", "Informativa"]
    confidence: float = Field(ge=0, le=1)
    evidence: str
    explanation: str
    recommendation: str
    improved_wording: str = ""
    related_criteria: list[str] = Field(default_factory=list)


class AISemanticReview(BaseModel):
    findings: list[AISemanticFinding]


class AIRewrite(BaseModel):
    improved_wording: str
    reason: str
    alternatives: list[str] = Field(default_factory=list)

