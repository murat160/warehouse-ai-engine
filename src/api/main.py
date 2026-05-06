"""FastAPI app exposing translate / stt / tts endpoints.

The factory functions :func:`build_app` and :func:`create_app` keep the
default and the dependency-injected variants apart — production code uses
:func:`create_app` (reads settings, wires real providers); tests use
:func:`build_app` to inject fakes without env vars.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
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
from ..translator.languages import (
    SUPPORTED_CODES,
    UnsupportedLanguageError,
)
from ..translator.translator_service import TranslatorService
from .schemas import (
    HealthResponse,
    QualityReportSchema,
    STTResponse,
    STTResponseSegment,
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
            },
        )

    @app.post("/v1/translate", response_model=TranslateResponse)
    def translate(req: TranslateRequest) -> TranslateResponse:
        try:
            result = translator.translate(
                text=req.text,
                source_lang=req.source_lang,
                target_lang=req.target_lang,
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

    return app


def create_app() -> FastAPI:
    """Production factory: wire real providers from settings."""
    settings = get_settings()

    primary_translation: TranslationProvider = OpenAIProvider(settings)
    fallback_translation: TranslationProvider = FallbackProvider(settings)
    translator = TranslatorService(
        primary=primary_translation,
        fallback=fallback_translation,
        use_glossary=settings.translator_use_glossary,
        run_quality_check=settings.translator_quality_check,
        latency_budget=settings.translator_latency_budget,
    )

    stt_provider: STTProvider = OpenAIProvider(settings)
    stt = SpeechToText(stt_provider)

    tts_primary: TTSProvider = OpenAIProvider(settings)
    tts_fallback: TTSProvider = FallbackProvider(settings)
    tts = TextToSpeech(primary=tts_primary, fallback=tts_fallback)

    return build_app(translator=translator, stt=stt, tts=tts, settings=settings)


# ASGI entry point for `uvicorn src.api.main:app`.
app = None  # populated lazily by uvicorn via the factory; see README.
