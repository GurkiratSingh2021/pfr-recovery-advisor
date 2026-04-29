"""
Pydantic schemas shared across request/response payloads.

All public API contracts are defined here so they can be imported by
routers, services, and tests without circular dependencies.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Ingest
# ---------------------------------------------------------------------------


class IngestRequest(BaseModel):
    """Payload for POST /api/ingest."""

    content: str = Field(..., description="Raw document text to ingest.")
    doc_id: str = Field(..., description="Unique identifier for this document.")
    title: str = Field(default="", description="Human-readable document title.")
    doc_type: str = Field(
        default="TSG",
        description="Document category: TSG | RCA | DRILL_REPORT | ARCH_DOC | CODE_DEP",
    )
    service: str = Field(
        default="",
        description="PilotFish service this document primarily relates to.",
    )
    source_path: str = Field(default="", description="File path or URL of source document.")


class IngestResponse(BaseModel):
    """Response for POST /api/ingest."""

    doc_id: str
    chunks_stored: int
    message: str


# ---------------------------------------------------------------------------
# Recommend – request
# ---------------------------------------------------------------------------


class IncidentInput(BaseModel):
    """Incident description submitted to POST /api/recommend."""

    incident_id: str = Field(default="", description="Optional ICM or ticket identifier.")
    title: str = Field(default="", description="Short incident title.")
    description: str = Field(
        ...,
        description="Free-text description of the incident, observed symptoms and signals.",
    )
    impacted_services: list[str] = Field(
        default_factory=list,
        description="List of known impacted service IDs (from dependencies.json).",
    )
    observed_signals: dict[str, Any] = Field(
        default_factory=dict,
        description="Key/value map of metric or ICM signals (e.g. SLO:5xx_rate: '42%').",
    )
    region: str = Field(default="", description="Azure region where the incident is occurring.")
    severity: int = Field(default=2, ge=1, le=4, description="ICM severity level (1=critical).")


# ---------------------------------------------------------------------------
# Recommend – response
# ---------------------------------------------------------------------------


class DependencyType(str, Enum):
    HARD = "hard"
    SOFT = "soft"


class Citation(BaseModel):
    """A reference to a source document chunk used to justify a recovery step."""

    doc_id: str
    title: str
    doc_type: str
    excerpt: str = Field(description="Relevant snippet from the source document.")
    relevance_score: float = Field(ge=0.0, le=1.0)


class RecoveryStep(BaseModel):
    """A single ordered step in the recovery plan."""

    step_number: int
    target_service: str
    action: str = Field(description="Concise action the DRI must take.")
    why_now: str = Field(
        description="Dependency-aware explanation of why this step comes at this position."
    )
    expected_signal: str = Field(
        description="Observable metric or log signal that confirms this step succeeded."
    )
    validations: list[str] = Field(
        default_factory=list,
        description="Checklist of conditions to verify before proceeding to the next step.",
    )
    rollback: str = Field(
        default="",
        description="Rollback procedure if this step makes things worse.",
    )
    citations: list[Citation] = Field(
        default_factory=list,
        description="Supporting evidence from retrieved documents.",
    )
    is_gated: bool = Field(
        default=False,
        description="True if this step must not be executed until a prior step completes.",
    )


class SafetyCheck(BaseModel):
    """A blocking safety assertion that must pass before a step or the overall plan."""

    check: str
    passed: bool
    reason: str = ""


class RecoveryPlan(BaseModel):
    """
    Full structured recovery plan returned by POST /api/recommend.

    The plan is deterministically ordered (Stage A planner) with per-step
    guidance generated from retrieved document snippets (Stage B explainer).
    """

    incident_id: str
    incident_summary: str
    detected_services: list[str] = Field(
        description="All impacted services including inferred transitive dependencies."
    )
    recovery_steps: list[RecoveryStep]
    safety_checks: list[SafetyCheck] = Field(default_factory=list)
    open_questions: list[str] = Field(
        default_factory=list,
        description="Missing signals or context that would affect the recommended ordering.",
    )
    confidence: float = Field(
        ge=0.0, le=1.0, description="Overall plan confidence (0=low, 1=high)."
    )
    planner_version: str = Field(default="local-v1")
