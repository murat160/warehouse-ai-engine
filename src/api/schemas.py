"""Pydantic request/response schemas for the API."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Translation
# ---------------------------------------------------------------------------


class TranslateRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=20_000)
    source_lang: str = Field(..., examples=["ru"])
    target_lang: str = Field(..., examples=["tk"])
    style: Optional[str] = Field(
        default=None,
        description="Optional translation style: neutral|respectful|warm|formal|"
        "friendly|expressive|literary|casual",
        examples=["literary"],
    )


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
    style: str = "neutral"
    tm_hit: bool = False
    user_glossary_hits: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Speech / TTS
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


class StyleSchema(BaseModel):
    code: str
    label_ru: str
    label_en: str
    description: str


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    languages: List[str]
    providers: dict
    styles: List[StyleSchema] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# User glossary
# ---------------------------------------------------------------------------


class GlossaryEntrySchema(BaseModel):
    id: str
    source_lang: str
    target_lang: str
    source_text: str
    target_text: str
    case_sensitive: bool = False
    whole_word: bool = True
    note: Optional[str] = None


class GlossaryCreateRequest(BaseModel):
    source_lang: str = Field(..., examples=["ru"])
    target_lang: str = Field(..., examples=["tk"])
    source_text: str = Field(..., min_length=1, max_length=512)
    target_text: str = Field(..., min_length=1, max_length=512)
    case_sensitive: bool = False
    whole_word: bool = True
    note: Optional[str] = Field(default=None, max_length=2_000)


class GlossaryUpdateRequest(BaseModel):
    source_text: Optional[str] = Field(default=None, max_length=512)
    target_text: Optional[str] = Field(default=None, max_length=512)
    case_sensitive: Optional[bool] = None
    whole_word: Optional[bool] = None
    note: Optional[str] = Field(default=None, max_length=2_000)


# ---------------------------------------------------------------------------
# Translation memory
# ---------------------------------------------------------------------------


class TMEntrySchema(BaseModel):
    id: str
    source_lang: str
    target_lang: str
    source_text: str
    target_text: str
    score: float = 1.0
    note: Optional[str] = None


class TMCreateRequest(BaseModel):
    source_lang: str
    target_lang: str
    source_text: str = Field(..., min_length=1, max_length=20_000)
    target_text: str = Field(..., min_length=1, max_length=20_000)
    score: float = Field(default=1.0, ge=0.0, le=1.0)
    note: Optional[str] = Field(default=None, max_length=2_000)


class TMUpdateRequest(BaseModel):
    target_text: Optional[str] = Field(default=None, max_length=20_000)
    score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    note: Optional[str] = Field(default=None, max_length=2_000)
