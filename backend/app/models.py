from pydantic import BaseModel, Field


class RecommendRequest(BaseModel):
    incident_prompt: str = Field(..., description='Natural-language incident description')
    outage_type: str = Field(..., description='Data Loss | Hardware Failure | Service Loss | Power Outage')
    affected_machine_functions: list[str] = Field(default_factory=list)
    top_k: int = 5


class Citation(BaseModel):
    title: str | None = None
    content: str | None = None
    filepath: str | None = None
    url: str | None = None
    chunk_id: str | None = None


class RecommendResponse(BaseModel):
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    debug: dict = Field(default_factory=dict)


class IngestDocument(BaseModel):
    id: str
    title: str
    content: str
    machine_function: str | None = None
    failure_types: list[str] = Field(default_factory=list)
    source_type: str | None = None
    source_url: str | None = None


class IngestRequest(BaseModel):
    documents: list[IngestDocument]


class IngestResponse(BaseModel):
    indexed_documents: int
    indexed_chunks: int
