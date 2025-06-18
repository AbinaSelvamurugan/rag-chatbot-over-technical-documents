from __future__ import annotations
from pydantic import BaseModel, Field, HttpUrl

class Scope(BaseModel):
    collection: str = Field(default='default', pattern=r'^[A-Za-z0-9_-]{1,64}$')
    document_ids: list[str] = Field(default_factory=list, max_length=30)

class ChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=4000)
    session_id: str | None = Field(default=None, max_length=80)
    scope: Scope = Field(default_factory=Scope)

class RetrievalRequest(BaseModel):
    question: str = Field(min_length=2, max_length=4000)
    scope: Scope = Field(default_factory=Scope)
    k: int | None = Field(default=None, ge=1, le=40)

class Passage(BaseModel):
    citation_id: str
    chunk_id: str
    document_id: str
    title: str
    uri: str | None = None
    section: str | None = None
    page_number: int | None = None
    text: str
    rank: int
    distance: float | None = None
    selected: bool = True

class Claim(BaseModel):
    text: str
    source_ids: list[str]

class ChatResponse(BaseModel):
    session_id: str
    answer: str
    abstained: bool
    claims: list[Claim] = Field(default_factory=list)
    sources: list[Passage] = Field(default_factory=list)
    trace: dict = Field(default_factory=dict)
    token_usage: dict = Field(default_factory=dict)
    latency_ms: float

class UrlRequest(BaseModel):
    url: HttpUrl
    collection: str = Field(default='default', pattern=r'^[A-Za-z0-9_-]{1,64}$')

class EvaluationRequest(BaseModel):
    dataset: str = Field(default='local_questions.json', pattern=r'^[A-Za-z0-9_-]+\.json$')
    k: int = Field(default=5, ge=1, le=40)
    generate: bool = False

class ErrorResponse(BaseModel):
    detail: str

class CollectionResetRequest(BaseModel):
    collection: str = Field(pattern=r'^[A-Za-z0-9_-]{1,64}$')
    confirmation: str = Field(min_length=8,max_length=80)
