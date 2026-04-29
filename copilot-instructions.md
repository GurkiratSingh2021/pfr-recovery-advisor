# PilotFish Recovery Advisor - Copilot Instructions

## Project Context
You are an expert developer building a web portal for a disaster recovery advisor. The system uses a RAG (Retrieval-Augmented Generation) architecture to turn outage inputs into recovery recommendations.

## Tech Stack
- **Backend:** FastAPI (Python)
- **Frontend:** React (Vite/TS preferred)
- **Vector DB:** Azure AI Search (Vector + Semantic search)
- **LLM:** Azure OpenAI (Chat + Embedding models)
- **Deployment:** Azure

## Architectural Rules & Standards
1. **FastAPI Backend:**
   - Use asynchronous endpoints (`async def`).
   - Standardize responses using Pydantic models.
   - Core APIs: `/api/ingest` (chunking/embedding) and `/api/recommend` (retrieval/generation).

2. **RAG Workflow:**
   - Always follow the flow: Input -> Embed -> Azure AI Search Retrieval -> Prompt Augmentation -> Azure OpenAI Reasoning.
   - Ensure the LLM cites its source documents (supporting evidence) in every recovery recommendation.

3. **Frontend (React):**
   - Use functional components and hooks.
   - Maintain a clean separation between UI components and API service layers.
   - The UI must handle streaming responses or loading states during AI "reasoning" phases.

4. **Data Handling:**
   - When ingesting TSG documents, use a semantic chunking strategy.
   - Ensure vector search and semantic ranking are both utilized in Azure AI Search for high accuracy.

## Coding Style
- **Naming:** Use snake_case for Python and camelCase for React/TypeScript.
- **Error Handling:** Use global exception handlers in FastAPI to return consistent JSON errors.
- **Documentation:** Every API endpoint must include a docstring explaining its role in the recovery lifecycle.

## Specific Constraints
- All Azure credentials (keys, endpoints) must be accessed via environment variables (.env). Never hardcode them.
- Focus on "deterministic ordering" and "dependency-aware" logic as the system scales beyond the MVP.
