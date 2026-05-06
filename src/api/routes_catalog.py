"""Read-only routes that expose static catalogs (styles, tones, emotions, voices)."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from ..translator.styles import (
    list_emotions,
    list_styles,
    list_tones,
)
from ..voices import (
    UseCase,
    VOICE_CATALOG,
    list_voices,
    voices_for_language,
    voices_for_use_case,
)
from .schemas import (
    EmotionSchema,
    StyleSchema,
    ToneSchema,
    VoiceProfileSchema,
)


router = APIRouter(tags=["catalog"])


@router.get("/v1/styles", response_model=List[StyleSchema])
def list_style_profiles() -> List[StyleSchema]:
    return [
        StyleSchema(
            code=s.code, label_ru=s.label_ru, label_en=s.label_en,
            description=s.description,
        )
        for s in list_styles()
    ]


@router.get("/v1/tones", response_model=List[ToneSchema])
def list_tone_profiles() -> List[ToneSchema]:
    return [
        ToneSchema(code=t.code, label_ru=t.label_ru, label_en=t.label_en)
        for t in list_tones()
    ]


@router.get("/v1/emotions", response_model=List[EmotionSchema])
def list_emotion_profiles() -> List[EmotionSchema]:
    return [
        EmotionSchema(code=e.code, label_ru=e.label_ru, label_en=e.label_en)
        for e in list_emotions()
    ]


@router.get("/v1/voices", response_model=List[VoiceProfileSchema])
def list_voice_profiles(
    language: Optional[str] = Query(default=None),
    use_case: Optional[str] = Query(default=None),
) -> List[VoiceProfileSchema]:
    voices = list_voices()
    if language:
        voices = voices_for_language(language)
    if use_case:
        try:
            uc = UseCase(use_case.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"unknown use_case={use_case!r}")
        wanted = {v.id for v in voices_for_use_case(uc)}
        voices = [v for v in voices if v.id in wanted]
    return [VoiceProfileSchema(**v.to_public_dict()) for v in voices]


@router.get("/v1/voices/{voice_id}", response_model=VoiceProfileSchema)
def get_voice_profile(voice_id: str) -> VoiceProfileSchema:
    profile = VOICE_CATALOG.get(voice_id)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"voice {voice_id} not found")
    return VoiceProfileSchema(**profile.to_public_dict())
