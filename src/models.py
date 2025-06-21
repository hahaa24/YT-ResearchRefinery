from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional, Dict, Any
from enum import Enum


class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"


class Settings(BaseModel):
    llm_provider: LLMProvider = LLMProvider.OPENAI
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    ollama_base_url: Optional[str] = None
    max_cost_limit: float = Field(default=10.00, ge=0.0)
    youtube_api_key: Optional[str] = None


class VideoRequest(BaseModel):
    url: HttpUrl
    clean_transcript: bool = False


class ClusterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    urls: List[HttpUrl] = Field(..., min_items=1)
    clean_transcripts: bool = False


class ClusterState(BaseModel):
    session_id: str
    name: str
    urls: List[str]
    status: str = "pending"  # pending, processing, completed, failed
    transcripts: Dict[str, str] = {}  # video_id -> transcript
    cleaned_transcripts: Dict[str, str] = {}
    summary: Optional[str] = None
    created_at: str
    updated_at: str


class TaskResult(BaseModel):
    task_id: str
    status: str  # pending, running, completed, failed
    result: Optional[Any] = None
    error: Optional[str] = None


class CostEstimate(BaseModel):
    estimated_cost: float
    token_count: int
    provider: str
    model: str 