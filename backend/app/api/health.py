"""
GET /api/health

Lightweight liveness check.  Returns service status so load balancers and
container orchestrators can determine whether the process is running.
"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    version: str


@router.get("/health", response_model=HealthResponse, summary="Liveness check")
async def health() -> HealthResponse:
    """
    Returns ``{"status": "ok"}`` if the API process is running.

    Use this endpoint for:
    - Kubernetes liveness probes
    - Load-balancer health checks
    - Quick smoke-test after deployment
    """
    return HealthResponse(status="ok", version="0.1.0")
