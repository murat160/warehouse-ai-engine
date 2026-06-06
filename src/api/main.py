"""FastAPI app: translate / stt / tts / glossary / TM / channels / catalog."""

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
from ..publishing import PublishingService
from ..storage import init_db
from ..storage.repositories import (
    ChannelRepository,
    CustomVoiceRepository,
    GlossaryRepository,
    PublishingRepository,
    TranslationMemoryRepository,
)
from ..translator.languages import SUPPORTED_CODES, UnsupportedLanguageError
from ..translator.styles import list_emotions, list_styles, list_tones
from ..translator.translation_memory import TranslationMemoryService
from ..translator.translator_service import TranslatorService
from ..translator.user_glossary import UserGlossaryService
from ..voices import VOICE_CATALOG, CustomVoiceService, get_voice
from . import (
    routes_catalog,
    routes_channels,
    routes_custom_voices,
    routes_glossary,
    routes_memory,
    routes_publishing,
)
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
    glossary_repository: Optional[GlossaryRepository] = None,
    memory_repository: Optional[TranslationMemoryRepository] = None,
    channel_repository: Optional[ChannelRepository] = None,
    custom_voice_repository: Optional[CustomVoiceRepository] = None,
    custom_voice_service: Optional[CustomVoiceService] = None,
    publishing_repository: Optional[PublishingRepository] = None,
    publishing_service: Optional[PublishingService] = None,
    settings: Optional[Settings] = None,
) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(
        title="Murat AI Studio",
        version=__version__,
        description=(
            "Murat AI Studio — профессиональная студия перевода, озвучки и дубляжа "
            "видео на туркменский язык. ru/tk/tr/en. "
            "User glossary, translation memory, channels (AI agents), "
            "15 styles, 16 tones, 7 emotions, 23 voice profiles."
        ),
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
                "channels": "sqlite" if channel_repository else None,
            },
            styles_count=len(list_styles()),
            tones_count=len(list_tones()),
            emotions_count=len(list_emotions()),
            voices_count=len(VOICE_CATALOG),
        )

    @app.post("/v1/translate", response_model=TranslateResponse)
    def translate(req: TranslateRequest) -> TranslateResponse:
        try:
            result = translator.translate(
                text=req.text,
                source_lang=req.source_lang,
                target_lang=req.target_lang,
                style=req.style,
                tone=req.tone,
                emotion=req.emotion,
                channel_id=req.channel_id,
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
            tone=result.tone,
            emotion=result.emotion,
            channel_id=result.channel_id,
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
            voice = req.voice
            if req.voice_id:
                profile = get_voice(req.voice_id)
                if profile is None:
                    raise HTTPException(
                        status_code=400, detail=f"unknown voice_id={req.voice_id!r}"
                    )
                voice = profile.backend_voice or voice
            try:
                out = tts.synthesize(req.text, language=req.language, voice=voice)
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
    if channel_repository is not None:
        app.include_router(routes_channels.build_router(channel_repository))
    if custom_voice_repository is not None and custom_voice_service is not None:
        app.include_router(
            routes_custom_voices.build_router(
                custom_voice_repository, custom_voice_service, tts=tts,
            )
        )
    if publishing_repository is not None and publishing_service is not None:
        app.include_router(
            routes_publishing.build_router(publishing_repository, publishing_service)
        )
    app.include_router(routes_catalog.router)

    return app


def create_app() -> FastAPI:
    """Production factory: wire real providers + storage from settings."""
    settings = get_settings()
    init_db()

    glossary_repo = GlossaryRepository()
    memory_repo = TranslationMemoryRepository()
    channel_repo = ChannelRepository()
    custom_voice_repo = CustomVoiceRepository()
    custom_voice_service = CustomVoiceService(custom_voice_repo)
    publishing_repo = PublishingRepository()
    publishing_service = PublishingService(publishing_repo)
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
        channel_repository=channel_repo,
        custom_voice_repository=custom_voice_repo,
        custom_voice_service=custom_voice_service,
        publishing_repository=publishing_repo,
        publishing_service=publishing_service,
        settings=settings,
    )


app = None  # ASGI lazy entry point; use `uvicorn --factory src.api.main:create_app`
