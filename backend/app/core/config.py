from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import re
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[3]

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(ROOT / '.env'), extra='ignore')
    data_dir: Path = ROOT / 'runtime'
    documents_dir: Path = ROOT / 'data' / 'sample_documents'
    chroma_dir: Path = ROOT / 'runtime' / 'chroma'
    registry_path: Path = ROOT / 'runtime' / 'registry.sqlite3'
    collection_name: str = 'technicaldocs'
    embedding_model: str = 'sentence-transformers/all-MiniLM-L6-v2'
    embedding_batch_size: int = Field(default=32, ge=1, le=256)
    groq_api_key: str = ''
    groq_model: str = ''
    groq_timeout: float = Field(default=35, gt=0, le=120)
    admin_token: str = ''
    allowed_hosts: str = 'www.juniper.net'
    allow_url_ingestion: bool = False
    cors_origins: str = 'http://localhost:5173,http://127.0.0.1:5173'
    max_upload_mb: int = Field(default=15, ge=1, le=200)
    max_chunks: int = Field(default=5000, ge=1)
    chunk_size: int = Field(default=1100, ge=100, le=8000)
    chunk_overlap: int = Field(default=150, ge=0, le=1000)
    retrieval_strategy: str = 'dense'
    reranker_model: str = ''
    retrieval_k: int = Field(default=8, ge=1, le=40)
    context_k: int = Field(default=5, ge=1, le=20)
    max_context_chars: int = Field(default=12000, ge=500, le=100000)
    distance_threshold: float | None = Field(default=None, ge=0)
    session_ttl_hours: int = Field(default=12, ge=1, le=720)
    log_level: str = 'INFO'

    @field_validator('collection_name')
    @classmethod
    def safe_collection(cls, v: str) -> str:
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{2,62}', v):
            raise ValueError('Collection name must be 3-63 safe characters')
        return v

    @field_validator('retrieval_strategy')
    @classmethod
    def valid_strategy(cls, v: str) -> str:
        if v not in ('dense','hybrid','mmr'):
            raise ValueError('Retrieval strategy must be dense, hybrid or mmr')
        return v

    @field_validator('chunk_overlap')
    @classmethod
    def valid_overlap(cls, v: int) -> int:
        return v

    @property
    def hosts(self) -> set[str]:
        return {x.strip().lower() for x in self.allowed_hosts.split(',') if x.strip()}

    @property
    def origins(self) -> list[str]:
        return [x.strip() for x in self.cors_origins.split(',') if x.strip()]

@lru_cache
def settings() -> Settings:
    return Settings()
