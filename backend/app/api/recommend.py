"""
POST /api/recommend

Core recommendation endpoint.  Runs the 2-stage recovery planning pipeline:

  Stage A – Deterministic planner:
    Loads the dependency graph from ``data/dependencies.json``, expands
    the impacted services to their hard-dependency closure, and
    topologically sorts them to produce a safe recovery ordering.

  Stage B – Local explainer (MVP) / Azure OpenAI explainer (production):
    For each planned step, retrieves relevant document chunks from the
    local knowledge store and generates action text, validations, rollback,
    and citations.
"""

import logging
from pathlib import Path

from fastapi import APIRouter, Depends

from backend.app.core.config import Settings, get_settings
from backend.app.models.schemas import (
    IncidentInput,
    RecoveryPlan,
    RecoveryStep,
    SafetyCheck,
)
from backend.app.services.explainer import LocalExplainer
from backend.app.services.planner import RecoveryPlanner
from backend.app.services.retrieval import LocalRetriever

logger = logging.getLogger(__name__)
router = APIRouter(tags=["recommend"])


# ---------------------------------------------------------------------------
# Dependency-injection helpers
# ---------------------------------------------------------------------------


def _get_planner(settings: Settings = Depends(get_settings)) -> RecoveryPlanner:
    return RecoveryPlanner(dependencies_path=settings.dependencies_file)


def _get_retriever(settings: Settings = Depends(get_settings)) -> LocalRetriever:
    retriever = LocalRetriever(
        docs_dir=settings.docs_dir,
        store_path=settings.ingest_store,
    )
    retriever.load_docs()
    return retriever


def _get_explainer() -> LocalExplainer:
    return LocalExplainer()


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post(
    "/recommend",
    response_model=RecoveryPlan,
    summary="Generate a dependency-aware recovery plan for an incident",
)
async def recommend(
    incident: IncidentInput,
    planner: RecoveryPlanner = Depends(_get_planner),
    retriever: LocalRetriever = Depends(_get_retriever),
    explainer: LocalExplainer = Depends(_get_explainer),
) -> RecoveryPlan:
    """
    **Recovery lifecycle role:** This is the primary advisor endpoint.

    Given an incident description and list of impacted services, it:

    1. Runs **Stage A** (deterministic planner) to build a dependency-aware
       ordered recovery sequence from ``data/dependencies.json``.
    2. Runs **Stage B** (explainer) for each step to generate concrete
       actions, validations, rollback procedures, and evidence citations
       from the local knowledge store.
    3. Returns a structured ``RecoveryPlan`` with all steps and safety checks.

    **Upgrading to Azure OpenAI:**
    Set ``USE_AZURE_OPENAI=true`` and configure ``AZURE_OPENAI_*`` env vars;
    the planner stage remains deterministic while the explainer calls the
    Chat API instead of using templates.
    """
    logger.info(
        "recommend: incident_id=%s impacted=%s",
        incident.incident_id,
        incident.impacted_services,
    )

    # ------------------------------------------------------------------
    # Stage A – deterministic ordering
    # ------------------------------------------------------------------
    planner_steps = planner.plan(
        impacted_services=incident.impacted_services,
        incident_description=incident.description,
    )

    if not planner_steps:
        logger.warning("Planner returned no steps for incident %s", incident.incident_id)

    # ------------------------------------------------------------------
    # Stage B – explainer per step
    # ------------------------------------------------------------------
    recovery_steps: list[RecoveryStep] = []
    for step in planner_steps:
        rs = explainer.explain_step(
            planner_step=step,
            retriever=retriever,
            incident_description=incident.description,
        )
        recovery_steps.append(rs)

    # ------------------------------------------------------------------
    # Safety checks
    # ------------------------------------------------------------------
    safety_checks = _build_safety_checks(planner_steps, incident)

    # ------------------------------------------------------------------
    # Open questions
    # ------------------------------------------------------------------
    open_questions = _build_open_questions(incident)

    # ------------------------------------------------------------------
    # Confidence
    # ------------------------------------------------------------------
    confidence = _compute_confidence(planner_steps, incident)

    # ------------------------------------------------------------------
    # Incident summary
    # ------------------------------------------------------------------
    detected = [s["service_id"] for s in planner_steps]
    summary = (
        f"Incident '{incident.title or incident.incident_id}': "
        f"{len(detected)} service(s) affected. "
        f"Recovery ordered across {len(recovery_steps)} step(s)."
    )

    return RecoveryPlan(
        incident_id=incident.incident_id or "unknown",
        incident_summary=summary,
        detected_services=detected,
        recovery_steps=recovery_steps,
        safety_checks=safety_checks,
        open_questions=open_questions,
        confidence=confidence,
        planner_version="local-v1",
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_safety_checks(planner_steps: list[dict], incident: IncidentInput) -> list[SafetyCheck]:
    checks: list[SafetyCheck] = []

    # Check: dependencies.json was loaded (non-empty plan for non-empty input)
    if incident.impacted_services and not planner_steps:
        checks.append(
            SafetyCheck(
                check="Dependency graph loaded",
                passed=False,
                reason="No steps were generated; verify data/dependencies.json exists and lists the reported services.",
            )
        )
    else:
        checks.append(SafetyCheck(check="Dependency graph loaded", passed=True))

    # Check: all explicitly reported services appear in plan
    plan_services = {s["service_id"] for s in planner_steps}
    for svc in incident.impacted_services:
        if svc not in plan_services:
            checks.append(
                SafetyCheck(
                    check=f"{svc} in dependency graph",
                    passed=False,
                    reason=f"'{svc}' was reported as impacted but is not in dependencies.json. Add it or check the service ID.",
                )
            )
        else:
            checks.append(SafetyCheck(check=f"{svc} in dependency graph", passed=True))

    return checks


def _build_open_questions(incident: IncidentInput) -> list[str]:
    questions: list[str] = []
    if not incident.observed_signals:
        questions.append(
            "No observed signals provided. Attaching live metric data (5xx_rate, latency_p99) would improve confidence."
        )
    if not incident.region:
        questions.append("Region not specified. Region-specific failover procedures may apply.")
    if incident.severity == 1 and not incident.incident_id:
        questions.append("Sev1 incident without an ICM ID – open an ICM immediately if not done.")
    return questions


def _compute_confidence(planner_steps: list[dict], incident: IncidentInput) -> float:
    score = 0.5  # base
    if planner_steps:
        score += 0.2
    if incident.impacted_services:
        score += 0.1
    if incident.observed_signals:
        score += 0.1
    if incident.description and len(incident.description) > 50:
        score += 0.1
    return round(min(score, 1.0), 2)
