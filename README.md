# PFR Recovery Advisor

Starter repo skeleton for a **Recovery Advisor** that combines:
- **FastAPI** backend
- **Azure OpenAI** for grounded recommendations
- **Azure AI Search** for retrieval / indexing
- **React + Vite** frontend for operator workflow

> This is a **starter scaffold**, not production-ready code. It is designed to help you move from the page prototype to a real repo that you can open in VS Code and extend with GitHub Copilot.

## Repo layout

```text
pfr-recovery-advisor/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── models.py
│   │   ├── prompts.py
│   │   └── services/
│   │       ├── azure_clients.py
│   │       ├── indexer.py
│   │       └── recommender.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── api.ts
│       └── types.ts
└── .gitignore
```

## Quick start

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```



Before using `/api/ingest`, create the search index once:

```bash
python -c "from app.services.search_schema import create_or_update_index; print(create_or_update_index())"
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Environment variables

Copy `backend/.env.example` to `backend/.env` and fill in the values:

- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_CHAT_DEPLOYMENT`
- `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`
- `AZURE_SEARCH_ENDPOINT`
- `AZURE_SEARCH_INDEX_NAME`
- Optional:
  - `AZURE_OPENAI_API_KEY`
  - `AZURE_SEARCH_API_KEY`

## Suggested next steps

1. Replace the sample dependency graph with your PilotFish dependency graph.
2. Add real TSG / drill / RCA ingestion.
3. Add auth and role-based access.
4. Add evaluation datasets for known recovery scenarios.
5. Add observability and prompt/version tracking.

## Starter GitHub Copilot prompts

- “Add a chunking strategy optimized for TSGs and RCA-style incident documents.”
- “Add an Azure AI Search index creator with vector fields and filterable metadata.”
- “Add a dependency-aware recovery planner that flags circular dependencies.”
- “Add citations and evidence snippets to every recovery recommendation.”
- “Write tests for DM data-loss recovery where DM depends on SEC and DS.”
