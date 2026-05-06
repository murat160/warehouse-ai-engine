"""FastAPI app exposing translate / stt / tts / glossary / TM endpoints.

The factory functions :func:`build_app` and :func:`create_app` keep the
default and the dependency-injected variants apart — production code uses
:func:`create_app` (reads settings, wires real providers); tests use
:func:`build_app` to inject fakes without env vars.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from .. import __version__
from ..config import Settings, get_settings
from ..providers.base import (
    ProviderError,
    ProviderUnavailableError,
    STTProvider,
    TTSProvider,
    TranslationProvider,
)
from ..providers.fallback_provider import FallbackProvider
from ..providers.openai_provider import OpenAIProvider
from ..speech.speech_to_text import SpeechToText
from ..speech.text_to_speech import TextToSpeech
from ..storage import init_db
from ..storage.repositories import (
    GlossaryRepository,
    TranslationMemoryRepository,
)
from ..translator.languages import SUPPORTED_CODES, UnsupportedLanguageError
from ..translator.styles import list_styles
from ..translator.translation_memory import TranslationMemoryService
from ..translator.translator_service import TranslatorService
from ..translator.user_glossary import UserGlossaryService
from . import routes_glossary, routes_memory
from .schemas import (
    HealthResponse,
    QualityReportSchema,
    STTResponse,
    STTResponseSegment,
    StyleSchema,
    TTSRequest,
    TranslateRequest,
    TranslateResponse,
)

logger = logging.getLogger(__name__)


def build_app(
    *,
    translator: TranslatorService,
    stt: Optional[SpeechToText] = None,
    tts: Optional[TextToSpeech] = None,
    glossary_repository: Optional[GlossaryRepository] = None,
    memory_repository: Optional[TranslationMemoryRepository] = None,
    settings: Optional[Settings] = None,
) -> FastAPI:
    """Build a FastAPI app from already-constructed services."""
    settings = settings or get_settings()
    app = FastAPI(
        title="warehouse-ai-engine",
        version=__version__,
        description="Translation, STT, TTS and video dubbing for ru/tk/tr/en.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(
            version=__version__,
            languages=sorted(SUPPORTED_CODES),
            providers={
                "translation": getattr(translator.primary, "name", "?"),
                "translation_fallback": getattr(translator.fallback, "name", None),
                "stt": getattr(stt.provider, "name", None) if stt else None,
                "tts": getattr(tts.primary, "name", None) if tts else None,
                "tts_fallback": getattr(tts.fallback, "name", None) if tts and tts.fallback else None,
                "user_glossary": "sqlite" if translator.user_glossary else None,
                "translation_memory": "sqlite" if translator.translation_memory else None,
            },
            styles=[
                StyleSchema(
                    code=s.code,
                    label_ru=s.label_ru,
                    label_en=s.label_en,
                    description=s.description,
                )
                for s in list_styles()
            ],
        )

    @app.get("/v1/styles", response_model=list[StyleSchema])
    def styles() -> list[StyleSchema]:
        return [
            StyleSchema(
                code=s.code,
                label_ru=s.label_ru,
                label_en=s.label_en,
                description=s.description,
            )
            for s in list_styles()
        ]

    @app.post("/v1/translate", response_model=TranslateResponse)
    def translate(req: TranslateRequest) -> TranslateResponse:
        try:
            result = translator.translate(
                text=req.text,
                source_lang=req.source_lang,
                target_lang=req.target_lang,
                style=req.style,
            )
        except UnsupportedLanguageError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        except ProviderUnavailableError as exc:
            raise HTTPException(status_code=503, detail=str(exc))
        except ProviderError as exc:
            raise HTTPException(status_code=502, detail=str(exc))
        return TranslateResponse(
            text=result.text,
            source_lang=result.source_lang,
            target_lang=result.target_lang,
            provider=result.provider,
            latency_seconds=result.latency_seconds,
            quality=QualityReportSchema(**result.quality.as_dict()),
            fallback_used=result.fallback_used,
            notes=result.notes,
            style=result.style,
            tm_hit=result.tm_hit,
            user_glossary_hits=result.user_glossary_hits,
        )

    if stt is not None:
        @app.post("/v1/stt", response_model=STTResponse)
        async def transcribe(
            audio: UploadFile = File(...),
            language: Optional[str] = Form(default=None),
            with_segments: bool = Form(default=False),
        ) -> STTResponse:
            data = await audio.read()
            try:
                result = stt.transcribe(
                    data, language_hint=language, with_segments=with_segments
                )
            except UnsupportedLanguageError as exc:
                raise HTTPException(status_code=400, detail=str(exc))
            except ProviderUnavailableError as exc:
                raise HTTPException(status_code=503, detail=str(exc))
            except ProviderError as exc:
                raise HTTPException(status_code=502, detail=str(exc))
            return STTResponse(
                text=result.text,
                language=result.language,
                duration=result.duration,
                segments=[
                    STTResponseSegment(start=s.start, end=s.end, text=s.text)
                    for s in result.segments
                ],
            )

    if tts is not None:
        @app.post("/v1/tts")
        def synthesize(req: TTSRequest) -> Response:
            try:
                out = tts.synthesize(req.text, language=req.language, voice=req.voice)
            except UnsupportedLanguageError as exc:
                raise HTTPException(status_code=400, detail=str(exc))
            except ProviderUnavailableError as exc:
                raise HTTPException(status_code=503, detail=str(exc))
            except ProviderError as exc:
                raise HTTPException(status_code=502, detail=str(exc))
            media_type = "audio/wav" if out.format == "wav" else f"audio/{out.format}"
            return Response(content=out.audio, media_type=media_type)

    if glossary_repository is not None:
        app.include_router(routes_glossary.build_router(glossary_repository))
    if memory_repository is not None:
        app.include_router(routes_memory.build_router(memory_repository))

    return app


def create_app() -> FastAPI:
    """Production factory: wire real providers + storage from settings."""
    settings = get_settings()
    init_db()

    glossary_repo = GlossaryRepository()
    memory_repo = TranslationMemoryRepository()
    user_glossary = UserGlossaryService(glossary_repo)
    translation_memory = TranslationMemoryService(memory_repo)

    primary_translation: TranslationProvider = OpenAIProvider(settings)
    fallback_translation: TranslationProvider = FallbackProvider(settings)
    translator = TranslatorService(
        primary=primary_translation,
        fallback=fallback_translation,
        user_glossary=user_glossary,
        translation_memory=translation_memory,
        use_glossary=settings.translator_use_glossary,
        run_quality_check=settings.translator_quality_check,
        latency_budget=settings.translator_latency_budget,
    )

    stt_provider: STTProvider = OpenAIProvider(settings)
    stt = SpeechToText(stt_provider)

    tts_primary: TTSProvider = OpenAIProvider(settings)
    tts_fallback: TTSProvider = FallbackProvider(settings)
    tts = TextToSpeech(primary=tts_primary, fallback=tts_fallback)

    return build_app(
        translator=translator,
        stt=stt,
        tts=tts,
        glossary_repository=glossary_repo,
        memory_repository=memory_repo,
        settings=settings,
    )


# ASGI entry point for `uvicorn --factory src.api.main:create_app`.
app = None  # populated lazily by uvicorn via the factory; see README.
