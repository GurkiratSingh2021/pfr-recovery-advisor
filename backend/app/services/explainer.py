"""
Stage B – Recovery Step Explainer.

For the MVP this is a LOCAL explainer that builds step text, validations,
and rollback from retrieved document snippets using simple template logic
(no LLM call).

The interface is identical to what an Azure OpenAI-backed explainer would
expose so it can be swapped in by setting USE_AZURE_OPENAI=true and wiring
up AZURE_OPENAI_* env vars.
"""

from __future__ import annotations

import logging

from backend.app.models.schemas import Citation, RecoveryStep
from backend.app.services.retrieval import LocalRetriever, RetrievedChunk

logger = logging.getLogger(__name__)


def _chunks_to_citations(chunks: list[RetrievedChunk]) -> list[Citation]:
    return [
        Citation(
            doc_id=c.doc_id,
            title=c.title,
            doc_type=c.doc_type,
            excerpt=c.excerpt,
            relevance_score=c.relevance_score,
        )
        for c in chunks
    ]


class LocalExplainer:
    """
    Generates recovery step text using template logic + retrieved snippets.

    Interface contract:
        explainer.explain_step(planner_step, retriever) -> RecoveryStep

    When Azure OpenAI is configured the implementation can call the Chat API
    with a structured prompt instead of using templates.
    """

    def explain_step(
        self,
        planner_step: dict,
        retriever: LocalRetriever,
        incident_description: str = "",
    ) -> RecoveryStep:
        """
        Build a RecoveryStep for the given planner_step dict.

        Retrieves relevant document chunks for the target service,
        then assembles action text, validations and rollback from those
        chunks combined with the planner's recovery_actions list.
        """
        svc_id: str = planner_step["service_id"]
        display_name: str = planner_step["display_name"]

        # ---- Retrieve relevant chunks for this service ----
        query = f"{svc_id} {display_name} recovery restart {incident_description[:200]}"
        chunks = retriever.search(query, top_k=3, service_filter=svc_id)
        if not chunks:
            # Fallback: no service filter
            chunks = retriever.search(query, top_k=2)

        citations = _chunks_to_citations(chunks)

        # ---- Build action text ----
        actions = planner_step.get("recovery_actions", [])
        if actions:
            action = actions[0]
        else:
            action = f"Recover {display_name}: verify health, restart pods, and validate signals."

        # ---- Build validations ----
        prereqs = planner_step.get("recovery_prereqs", [])
        validations: list[str] = list(prereqs)
        if len(actions) > 1:
            validations.extend(actions[1:])
        if not validations:
            validations = [
                f"Confirm {display_name} health endpoint returns 200.",
                "Check relevant SLO metrics stabilize within 5 minutes.",
            ]

        # ---- Build expected signal ----
        signal = _build_expected_signal(svc_id)

        # ---- Build rollback ----
        rollback = _build_rollback(svc_id, display_name)

        # ---- Why now ----
        why_now: str = planner_step.get("why_now", f"Recover {svc_id} per dependency order.")

        return RecoveryStep(
            step_number=planner_step["step_number"],
            target_service=svc_id,
            action=action,
            why_now=why_now,
            expected_signal=signal,
            validations=validations,
            rollback=rollback,
            citations=citations,
            is_gated=planner_step.get("is_gated", False),
        )


# ---------------------------------------------------------------------------
# Template helpers
# ---------------------------------------------------------------------------

_SIGNAL_MAP: dict[str, str] = {
    "PilotFish.DataStore": "SLO:read_latency_p99 < 50ms; SLO:write_success_rate > 99.9%",
    "PilotFish.Identity": "SLO:token_issuance_p99 < 500ms; OIDC discovery endpoint returns 200",
    "PilotFish.Config": "SLO:config_fetch_success_rate > 99%; config propagation lag < 60s",
    "PilotFish.Messaging": "SLO:message_delivery_latency < 1s; dead-letter queue depth = 0",
    "PilotFish.ControlPlane.API": "SLO:5xx_rate < 1%; SLO:latency_p99 < 500ms; /health returns 200",
    "PilotFish.ControlPlane.Worker": "SLO:job_success_rate > 99%; no pod restarts in last 5 min",
    "PilotFish.Gateway": "SLO:request_success_rate > 99.5%; gateway health probes passing",
}

_ROLLBACK_MAP: dict[str, str] = {
    "PilotFish.DataStore": "Initiate geo-failover to secondary; escalate to Azure Support if platform issue.",
    "PilotFish.Identity": "kubectl rollout undo deployment/identity-service -n pilotfish-identity",
    "PilotFish.Config": "kubectl rollout undo deployment/config-service -n pilotfish-config; remove BOOTSTRAP env var.",
    "PilotFish.Messaging": "Pause consumers; replay DLQ after root cause resolved.",
    "PilotFish.ControlPlane.API": "kubectl rollout undo deployment/controlplane-api -n pilotfish-api",
    "PilotFish.ControlPlane.Worker": "kubectl rollout undo deployment/controlplane-worker -n pilotfish-api",
    "PilotFish.Gateway": "Flush APIM cache; restore prior policy revision.",
}


def _build_expected_signal(svc_id: str) -> str:
    return _SIGNAL_MAP.get(svc_id, f"{svc_id} health endpoint returns 200 and key SLOs are within normal range.")


def _build_rollback(svc_id: str, display_name: str) -> str:
    return _ROLLBACK_MAP.get(svc_id, f"Rollback {display_name} to previous known-good revision.")
