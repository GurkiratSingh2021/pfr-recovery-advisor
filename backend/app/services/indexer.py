import hashlib
from typing import Iterable

from app.models import IngestDocument
from app.services.azure_clients import get_openai_client, get_search_client
from app.config import settings


def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 150) -> list[str]:
    text = ' '.join(text.split())
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        chunk = text[start:end]
        chunks.append(chunk)
        if end == len(text):
            break
        start = max(0, end - overlap)
    return chunks


async def embed_texts(texts: list[str]) -> list[list[float]]:
    client = get_openai_client()
    response = await client.embeddings.create(
        model=settings.azure_openai_embedding_deployment,
        input=texts,
    )
    return [item.embedding for item in response.data]


def _chunk_id(doc_id: str, idx: int, text: str) -> str:
    h = hashlib.sha1(f'{doc_id}:{idx}:{text}'.encode('utf-8')).hexdigest()[:12]
    return f'{doc_id}-chunk-{idx}-{h}'


async def ingest_documents(documents: list[IngestDocument]) -> tuple[int, int]:
    search_client = get_search_client()

    uploads = []
    for doc in documents:
        chunks = chunk_text(doc.content)
        embeddings = await embed_texts(chunks)
        for idx, (chunk, vector) in enumerate(zip(chunks, embeddings)):
            uploads.append({
                'id': _chunk_id(doc.id, idx, chunk),
                'doc_id': doc.id,
                'title': doc.title,
                'content': chunk,
                'machine_function': doc.machine_function,
                'failure_types': doc.failure_types,
                'source_type': doc.source_type,
                'source_url': doc.source_url,
                'content_vector': vector,
            })

    if uploads:
        search_client.upload_documents(documents=uploads)

    return len(documents), len(uploads)
