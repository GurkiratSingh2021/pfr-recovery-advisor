"""
POST /api/ingest

Accepts a document payload, chunks it, and stores it in the local JSONL
knowledge store so it is available for retrieval during recommendations.

In a production deployment, this endpoint would also embed the chunks and
upsert them into Azure AI Search.  The interface is identical; only the
retrieval backend changes.
"""

import logging

from fastapi import APIRouter, Depends

from backend.app.core.config import Settings, get_settings
from backend.app.models.schemas import IngestRequest, IngestResponse
from backend.app.services.retrieval import LocalRetriever

logger = logging.getLogger(__name__)
router = APIRouter(tags=["ingest"])


def _get_retriever(settings: Settings = Depends(get_settings)) -> LocalRetriever:
    retriever = LocalRetriever(
        docs_dir=settings.docs_dir,
        store_path=settings.ingest_store,
    )
    retriever.load_docs()
    return retriever


@router.post("/ingest", response_model=IngestResponse, summary="Ingest a document into the knowledge store")
async def ingest(
    payload: IngestRequest,
    retriever: LocalRetriever = Depends(_get_retriever),
) -> IngestResponse:
    """
    Chunks the supplied document and persists it to the local JSONL store.

    **Recovery lifecycle role:** This endpoint populates the knowledge base
    that Stage B of the recovery planner queries to generate evidence-backed
    step explanations.

    - For the MVP, documents are stored as text chunks in ``data/ingested_docs.jsonl``.
    - With Azure AI Search configured, chunks would be embedded and upserted
      to the search index instead.

    The ``doc_type`` field controls retrieval priority:
    ``TSG > DRILL_REPORT > RCA > ARCH_DOC > CODE_DEP``
    """
    chunks_stored = retriever.ingest(
        content=payload.content,
        doc_id=payload.doc_id,
        title=payload.title or payload.doc_id,
        doc_type=payload.doc_type,
        service=payload.service,
        source_path=payload.source_path,
    )
    logger.info("Ingested doc_id=%s into %d chunks", payload.doc_id, chunks_stored)
    return IngestResponse(
        doc_id=payload.doc_id,
        chunks_stored=chunks_stored,
        message=f"Successfully ingested '{payload.doc_id}' into {chunks_stored} chunks.",
    )
