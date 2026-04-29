"""
Tests for POST /api/recommend – validates response schema and core behaviour.

Run with:
    cd <repo-root>
    pip install -r backend/requirements.txt
    pytest backend/tests/ -v
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

SAMPLE_INCIDENT_PATH = Path("data/sample_incidents/dm_outage_001.json")


def _load_sample_incident() -> dict:
    if SAMPLE_INCIDENT_PATH.exists():
        return json.loads(SAMPLE_INCIDENT_PATH.read_text())
    return {
        "incident_id": "TEST-001",
        "title": "Control plane degraded",
        "description": "Config service returning 503; API pods in CrashLoopBackOff; 42% 5xx rate.",
        "impacted_services": ["PilotFish.ControlPlane.API", "PilotFish.Config"],
        "observed_signals": {"SLO:5xx_rate": "42%", "SLO:config_fetch_success_rate": "12%"},
        "region": "eastus2",
        "severity": 2,
    }


# ---------------------------------------------------------------------------
# Health endpoint sanity
# ---------------------------------------------------------------------------


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "version" in body


# ---------------------------------------------------------------------------
# /api/recommend – schema validation
# ---------------------------------------------------------------------------


def test_recommend_returns_200():
    payload = _load_sample_incident()
    response = client.post("/api/recommend", json=payload)
    assert response.status_code == 200, response.text


def test_recommend_response_has_required_fields():
    payload = _load_sample_incident()
    body = client.post("/api/recommend", json=payload).json()

    # Top-level required fields
    assert "incident_id" in body
    assert "incident_summary" in body
    assert "detected_services" in body
    assert "recovery_steps" in body
    assert "safety_checks" in body
    assert "open_questions" in body
    assert "confidence" in body
    assert "planner_version" in body


def test_recommend_recovery_steps_schema():
    payload = _load_sample_incident()
    body = client.post("/api/recommend", json=payload).json()

    steps = body["recovery_steps"]
    assert isinstance(steps, list)
    assert len(steps) > 0, "Expected at least one recovery step"

    for step in steps:
        assert "step_number" in step
        assert "target_service" in step
        assert "action" in step
        assert "why_now" in step
        assert "expected_signal" in step
        assert "validations" in step
        assert isinstance(step["validations"], list)
        assert "citations" in step
        assert isinstance(step["citations"], list)
        assert "is_gated" in step


def test_recommend_steps_are_ordered():
    """step_number values must be monotonically increasing from 1."""
    payload = _load_sample_incident()
    body = client.post("/api/recommend", json=payload).json()
    step_numbers = [s["step_number"] for s in body["recovery_steps"]]
    assert step_numbers == list(range(1, len(step_numbers) + 1))


def test_recommend_confidence_is_valid():
    payload = _load_sample_incident()
    body = client.post("/api/recommend", json=payload).json()
    confidence = body["confidence"]
    assert isinstance(confidence, float)
    assert 0.0 <= confidence <= 1.0


def test_recommend_dependency_order():
    """
    When both PilotFish.Config and PilotFish.ControlPlane.API are impacted,
    Config (tier 1) must appear before ControlPlane.API (tier 2) in the plan.
    """
    payload = {
        "incident_id": "ORDER-TEST",
        "title": "Order test",
        "description": "Config and API both down",
        "impacted_services": ["PilotFish.ControlPlane.API", "PilotFish.Config"],
        "observed_signals": {},
        "region": "eastus2",
        "severity": 2,
    }
    body = client.post("/api/recommend", json=payload).json()
    steps = body["recovery_steps"]
    service_order = [s["target_service"] for s in steps]

    assert "PilotFish.Config" in service_order
    assert "PilotFish.ControlPlane.API" in service_order
    config_pos = service_order.index("PilotFish.Config")
    api_pos = service_order.index("PilotFish.ControlPlane.API")
    assert config_pos < api_pos, (
        f"Config (pos {config_pos}) must come before ControlPlane.API (pos {api_pos})"
    )


def test_recommend_citations_have_schema():
    """Citations must have doc_id, title, doc_type, excerpt, relevance_score."""
    payload = _load_sample_incident()
    body = client.post("/api/recommend", json=payload).json()
    for step in body["recovery_steps"]:
        for citation in step["citations"]:
            assert "doc_id" in citation
            assert "title" in citation
            assert "doc_type" in citation
            assert "excerpt" in citation
            assert "relevance_score" in citation
            score = citation["relevance_score"]
            assert 0.0 <= score <= 1.0


def test_recommend_missing_description_422():
    """description is required; omitting it must return 422."""
    payload = {"impacted_services": ["PilotFish.Config"]}
    response = client.post("/api/recommend", json=payload)
    assert response.status_code == 422


def test_recommend_unknown_service_returns_plan():
    """An unknown service should not crash the endpoint."""
    payload = {
        "description": "Unknown service is down",
        "impacted_services": ["PilotFish.UnknownService"],
    }
    response = client.post("/api/recommend", json=payload)
    assert response.status_code == 200


def test_recommend_empty_impacted_infers_from_description():
    """When impacted_services is empty, planner should infer from description."""
    payload = {
        "description": "PilotFish Identity service is returning 503. Auth failures observed.",
        "impacted_services": [],
    }
    body = client.post("/api/recommend", json=payload).json()
    # Should produce a plan (planner infers Identity from description keywords)
    assert body["recovery_steps"] is not None
