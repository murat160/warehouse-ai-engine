"""Pydantic request/response schemas for the API."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class TranslateRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=20_000)
    source_lang: str = Field(..., examples=["ru"])
    target_lang: str = Field(..., examples=["tk"])


class QualityReportSchema(BaseModel):
    ok: bool
    score: float
    issues: List[str] = Field(default_factory=list)


class TranslateResponse(BaseModel):
    text: str
    source_lang: str
    target_lang: str
    provider: str
    latency_seconds: float
    quality: QualityReportSchema
    fallback_used: bool = False
    notes: List[str] = Field(default_factory=list)


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5_000)
    language: str
    voice: Optional[str] = None


class STTResponseSegment(BaseModel):
    start: float
    end: float
    text: str


class STTResponse(BaseModel):
    text: str
    language: Optional[str] = None
    duration: float = 0.0
    segments: List[STTResponseSegment] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    languages: List[str]
    providers: dict
