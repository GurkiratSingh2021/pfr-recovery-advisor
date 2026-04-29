from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.models import IngestRequest, IngestResponse, RecommendRequest, RecommendResponse
from app.services.indexer import ingest_documents
from app.services.recommender import recommend

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.get('/health')
async def health():
    return {'status': 'ok', 'app': settings.app_name}


@app.post('/api/ingest', response_model=IngestResponse)
async def ingest(payload: IngestRequest):
    indexed_documents, indexed_chunks = await ingest_documents(payload.documents)
    return IngestResponse(indexed_documents=indexed_documents, indexed_chunks=indexed_chunks)


@app.post('/api/recommend', response_model=RecommendResponse)
async def recommend_endpoint(payload: RecommendRequest):
    return await recommend(payload)
