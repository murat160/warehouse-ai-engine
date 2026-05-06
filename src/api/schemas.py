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
        description="One of the 15 TranslationStyle codes. Default: natural.",
    )
    tone: Optional[str] = Field(default=None, description="One of the 16 DeliveryTone codes.")
    emotion: Optional[str] = Field(default=None, description="One of the 7 Emotion codes.")
    channel_id: Optional[str] = Field(default=None, description="Apply this channel's glossary/TM/defaults.")


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
    style: str = "natural"
    tone: Optional[str] = None
    emotion: str = "neutral"
    channel_id: Optional[str] = None
    tm_hit: bool = False
    user_glossary_hits: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Speech / TTS
# ---------------------------------------------------------------------------


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5_000)
    language: str
    voice: Optional[str] = None
    voice_id: Optional[str] = Field(
        default=None,
        description="Built-in VoiceProfile id; overrides ``voice`` when set.",
    )
    emotion: Optional[str] = None


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
# Catalog: styles / tones / emotions / voices
# ---------------------------------------------------------------------------


class StyleSchema(BaseModel):
    code: str
    label_ru: str
    label_en: str
    description: str


class ToneSchema(BaseModel):
    code: str
    label_ru: str
    label_en: str


class EmotionSchema(BaseModel):
    code: str
    label_ru: str
    label_en: str


class VoiceProfileSchema(BaseModel):
    id: str
    label_ru: str
    label_en: str
    description: str
    gender: str
    age_style: str
    tone: str
    languages: List[str]
    speed: str
    pitch: str
    default_emotion: str
    use_cases: List[str]
    provider: str
    backend_voice: Optional[str] = None
    notes: Optional[str] = None


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    languages: List[str]
    providers: dict
    styles_count: int = 0
    tones_count: int = 0
    emotions_count: int = 0
    voices_count: int = 0


# ---------------------------------------------------------------------------
# Channels (AI agents)
# ---------------------------------------------------------------------------


class ChannelSchema(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    primary_lang: str = "ru"
    target_lang: Optional[str] = None
    style: str = "natural"
    tone: Optional[str] = None
    emotion: str = "neutral"
    voice_id: Optional[str] = None
    voice_use_case: str = "video"
    dubbing_notes: Optional[str] = None


class ChannelCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=2_000)
    primary_lang: str = "ru"
    target_lang: Optional[str] = None
    style: str = "natural"
    tone: Optional[str] = None
    emotion: str = "neutral"
    voice_id: Optional[str] = None
    voice_use_case: str = "video"
    dubbing_notes: Optional[str] = Field(default=None, max_length=4_000)


class ChannelUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, max_length=120)
    description: Optional[str] = None
    primary_lang: Optional[str] = None
    target_lang: Optional[str] = None
    style: Optional[str] = None
    tone: Optional[str] = None
    emotion: Optional[str] = None
    voice_id: Optional[str] = None
    voice_use_case: Optional[str] = None
    dubbing_notes: Optional[str] = None


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
    channel_id: Optional[str] = None


class GlossaryCreateRequest(BaseModel):
    source_lang: str = Field(..., examples=["ru"])
    target_lang: str = Field(..., examples=["tk"])
    source_text: str = Field(..., min_length=1, max_length=512)
    target_text: str = Field(..., min_length=1, max_length=512)
    case_sensitive: bool = False
    whole_word: bool = True
    note: Optional[str] = Field(default=None, max_length=2_000)
    channel_id: Optional[str] = None


class GlossaryUpdateRequest(BaseModel):
    source_text: Optional[str] = Field(default=None, max_length=512)
    target_text: Optional[str] = Field(default=None, max_length=512)
    case_sensitive: Optional[bool] = None
    whole_word: Optional[bool] = None
    note: Optional[str] = Field(default=None, max_length=2_000)
    channel_id: Optional[str] = None


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
    channel_id: Optional[str] = None


class TMCreateRequest(BaseModel):
    source_lang: str
    target_lang: str
    source_text: str = Field(..., min_length=1, max_length=20_000)
    target_text: str = Field(..., min_length=1, max_length=20_000)
    score: float = Field(default=1.0, ge=0.0, le=1.0)
    note: Optional[str] = Field(default=None, max_length=2_000)
    channel_id: Optional[str] = None


class TMUpdateRequest(BaseModel):
    target_text: Optional[str] = Field(default=None, max_length=20_000)
    score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    note: Optional[str] = Field(default=None, max_length=2_000)
    channel_id: Optional[str] = None
