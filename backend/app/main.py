"""
PilotFish Recovery Advisor – FastAPI application entry point.

Starts the API server, registers routers, configures CORS, and sets up
a global exception handler so every error returns consistent JSON.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.api import health, ingest, recommend

app = FastAPI(
    title="PFR Recovery Advisor",
    description=(
        "Dependency-aware, step-by-step recovery advisor for PilotFish "
        "control-plane outages. Powered by a 2-stage planner + retrieval pipeline."
    ),
    version="0.1.0",
)

# ---------------------------------------------------------------------------
# CORS – allow the Vite dev server (port 5173) and any localhost origin.
# In production, restrict this to your actual frontend domain.
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(health.router, prefix="/api")
app.include_router(ingest.router, prefix="/api")
app.include_router(recommend.router, prefix="/api")


# ---------------------------------------------------------------------------
# Global exception handler – returns consistent JSON for unhandled errors
# ---------------------------------------------------------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "detail": str(exc),
        },
    )
