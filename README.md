# PFR Recovery Advisor

> **Dependency-aware, step-by-step recovery advisor for PilotFish control-plane outages.**

PFR Recovery Advisor reduces RTO by analysing dependency signals and TSG knowledge to produce a
safe, ordered recovery plan for on-call DRIs — no tribal knowledge required.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Frontend (Vite + React + TS)  ←→  FastAPI Backend              │
│  localhost:5173                     localhost:8000               │
└─────────────────────────────────────────────────────────────────┘
                          │
         ┌────────────────┴─────────────────┐
         ▼                                  ▼
  Stage A – Deterministic Planner    Stage B – Explainer
  data/dependencies.json             Local keyword retrieval
  Topological sort (hard deps first) (BM25 over data/sample_docs)
         │                                  │
         └─────────── RecoveryPlan ─────────┘
                (structured JSON response)
```

### Two-stage pipeline

| Stage | Description | MVP impl | Production upgrade |
|---|---|---|---|
| **A – Planner** | Topologically sorts impacted services using `data/dependencies.json`. Hard dependencies always recover first. | Deterministic (no LLM) | Same – planner stays deterministic |
| **B – Explainer** | Generates per-step action text, validations, rollback, and citations | Local BM25 retrieval over `data/sample_docs/` | Replace with Azure OpenAI Chat API + Azure AI Search |

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+

### 1 – Backend

```bash
# From repo root
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -r backend/requirements.txt

# Copy and (optionally) fill in Azure env vars
cp .env.example .env

uvicorn backend.app.main:app --reload
# → http://localhost:8000
# → Swagger UI: http://localhost:8000/docs
```

### 2 – Frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

Open [http://localhost:5173](http://localhost:5173), paste an incident JSON (or click **Load sample**), and click **⚡ Get Recovery Plan**.

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/health` | Liveness check |
| `POST` | `/api/ingest` | Ingest a document into the local knowledge store |
| `POST` | `/api/recommend` | Generate a dependency-aware recovery plan |

Full interactive docs: **http://localhost:8000/docs**

### POST /api/recommend – example

```json
{
  "incident_id": "ICM-20240315-001",
  "title": "Control Plane API degraded",
  "description": "Config service returning 503. API pods in CrashLoopBackOff. 42% 5xx rate.",
  "impacted_services": ["PilotFish.ControlPlane.API", "PilotFish.Config"],
  "observed_signals": { "SLO:5xx_rate": "42%", "SLO:config_fetch_success_rate": "12%" },
  "region": "eastus2",
  "severity": 2
}
```

Response includes:
- `incident_summary` – normalised summary
- `detected_services` – all impacted + transitive hard deps
- `recovery_steps[]` – ordered steps, each with `action`, `why_now`, `expected_signal`, `validations`, `rollback`, `citations[]`
- `safety_checks[]` – blocking assertions
- `open_questions[]` – signals that would improve confidence
- `confidence` – 0–1 plan confidence score

---

## Running Tests

```bash
# From repo root (backend activated)
pytest backend/tests/ -v
```

---

## Repository Structure

```
pfr-recovery-advisor/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app, CORS, exception handler
│   │   ├── api/
│   │   │   ├── health.py            # GET /api/health
│   │   │   ├── ingest.py            # POST /api/ingest
│   │   │   └── recommend.py         # POST /api/recommend
│   │   ├── core/
│   │   │   └── config.py            # Settings (env vars, feature flags)
│   │   ├── models/
│   │   │   └── schemas.py           # Pydantic request/response schemas
│   │   └── services/
│   │       ├── planner.py           # Stage A – deterministic dependency planner
│   │       ├── retrieval.py         # Stage B – local BM25 retriever
│   │       └── explainer.py         # Stage B – step explainer (local / Azure OpenAI)
│   ├── tests/
│   │   └── test_recommend.py        # Backend tests
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── api/client.ts            # API service layer
│       ├── types/api.ts             # TypeScript types (mirrors Pydantic schemas)
│       ├── components/
│       │   ├── IncidentForm.tsx     # Left panel – incident input
│       │   ├── PlanSummary.tsx      # Plan header, safety checks, open questions
│       │   └── RecoveryStepCard.tsx # Expandable step card with citations
│       └── App.tsx
├── data/
│   ├── dependencies.json            # PilotFish service dependency graph
│   ├── sample_incidents/            # Example incident payloads
│   └── sample_docs/                 # TSG-like markdown documents
├── .env.example
├── pyproject.toml                   # ruff + pytest config
└── README.md
```

---

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI resource endpoint | `""` |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key | `""` |
| `AZURE_OPENAI_CHAT_DEPLOYMENT` | Chat model deployment name | `gpt-4o` |
| `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` | Embedding model deployment name | `text-embedding-3-small` |
| `AZURE_SEARCH_ENDPOINT` | Azure AI Search endpoint | `""` |
| `AZURE_SEARCH_API_KEY` | Azure AI Search API key | `""` |
| `AZURE_SEARCH_INDEX_NAME` | Search index name | `pfr-knowledge` |
| `USE_AZURE_OPENAI` | Use Azure OpenAI for Stage B | `false` |
| `USE_AZURE_SEARCH` | Use Azure AI Search for retrieval | `false` |
| `DEPENDENCIES_FILE` | Path to dependency graph JSON | `data/dependencies.json` |
| `DOCS_DIR` | Path to TSG documents directory | `data/sample_docs` |
| `INGEST_STORE` | Path to JSONL chunk store | `data/ingested_docs.jsonl` |

---

## Upgrading to Azure

1. Set Azure credentials in `.env`
2. Set `USE_AZURE_OPENAI=true` and `USE_AZURE_SEARCH=true`
3. In `backend/app/services/explainer.py`, replace `LocalExplainer.explain_step` with an
   Azure OpenAI Chat completion call using the retrieved chunks as context
4. In `backend/app/services/retrieval.py`, add an `AzureSearchRetriever` class that
   queries Azure AI Search with the same `search(query, top_k)` interface

Stage A (planner) stays deterministic regardless of this choice.

---

## Ports

| Service | Default Port |
|---|---|
| FastAPI backend | `8000` |
| Vite frontend | `5173` |

The Vite dev server proxies `/api/*` to `http://localhost:8000` automatically.
