"""OpenAI-backed implementations of the translation / STT / TTS providers.

The OpenAI client is imported lazily so the rest of the engine can be
imported (and unit-tested) without the optional dependency installed. Real
API calls only happen when ``OPENAI_API_KEY`` is set.
"""

from __future__ import annotations

import io
import logging
from typing import Optional

from ..config import Settings, get_settings
from ..translator.languages import LANGUAGES
from .base import (
    AudioBytes,
    ProviderError,
    ProviderUnavailableError,
    STTProvider,
    STTResult,
    TTSProvider,
    TTSResult,
    TranscriptSegment,
    TranslationProvider,
)

logger = logging.getLogger(__name__)


def _client(settings: Settings):
    if not settings.has_openai:
        raise ProviderUnavailableError("OPENAI_API_KEY is not set")
    try:
        from openai import OpenAI  # type: ignore
    except ImportError as exc:  # pragma: no cover - import-time guard
        raise ProviderUnavailableError(
            "openai package is not installed; pip install -r requirements.txt"
        ) from exc
    return OpenAI(api_key=settings.openai_api_key)


def _system_prompt(
    source_lang: str,
    target_lang: str,
    literary: bool,
    style: Optional[str] = None,
) -> str:
    from ..translator.styles import build_prompt_hint, get_style

    src = LANGUAGES[source_lang]
    tgt = LANGUAGES[target_lang]
    base = (
        f"You are a professional translator. Translate the user's text from "
        f"{src.name_en} ({src.code}) into {tgt.name_en} ({tgt.code}). "
        "Output ONLY the translation, with no commentary, no quotes, no "
        "language labels, and no explanation."
    )

    # Resolve the style profile: explicit style wins, otherwise legacy
    # ``literary`` flag and the priority ru<->tk pair upgrade us to literary.
    if style:
        profile = get_style(style)
    elif literary or {source_lang, target_lang} == {"ru", "tk"}:
        profile = get_style("literary")
    else:
        profile = get_style("neutral")

    base += " " + build_prompt_hint(profile, target_lang)
    base += " Preserve names, numbers and punctuation."
    return base


class OpenAIProvider(TranslationProvider, STTProvider, TTSProvider):
    """One class, three roles — convenient when a single key serves all of them."""

    name = "openai"

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()

    # -- TranslationProvider ------------------------------------------------

    def is_available(self, language: Optional[str] = None) -> bool:  # type: ignore[override]
        # Translation/STT only need a key. TTS additionally needs ``language``
        # to be one we will route through OpenAI (anything except "tk").
        if not self.settings.has_openai:
            return False
        if language is not None and language == "tk":
            # Turkmen TTS quality from OpenAI is poor — prefer the fallback.
            return False
        return True

    def translate(
        self,
        *,
        text: str,
        source_lang: str,
        target_lang: str,
        literary: bool = False,
        style: Optional[str] = None,
    ) -> str:
        if not text.strip():
            return ""
        client = _client(self.settings)
        try:
            resp = client.chat.completions.create(
                model=self.settings.openai_translation_model,
                temperature=0.2,
                messages=[
                    {
                        "role": "system",
                        "content": _system_prompt(source_lang, target_lang, literary, style),
                    },
                    {"role": "user", "content": text},
                ],
            )
        except Exception as exc:  # pragma: no cover - network path
            raise ProviderError(f"openai translate failed: {exc}") from exc
        choice = resp.choices[0].message.content if resp.choices else ""
        return (choice or "").strip()

    # -- STTProvider --------------------------------------------------------

    def transcribe(
        self,
        audio: AudioBytes,
        *,
        language_hint: Optional[str] = None,
        with_segments: bool = False,
    ) -> STTResult:
        client = _client(self.settings)
        buf = io.BytesIO(audio)
        buf.name = "audio.wav"
        try:
            resp = client.audio.transcriptions.create(
                model=self.settings.openai_stt_model,
                file=buf,
                language=language_hint,
                response_format="verbose_json" if with_segments else "json",
            )
        except Exception as exc:  # pragma: no cover - network path
            raise ProviderError(f"openai transcribe failed: {exc}") from exc
        segments = []
        if with_segments and getattr(resp, "segments", None):
            for s in resp.segments:
                segments.append(
                    TranscriptSegment(
                        start=float(getattr(s, "start", 0.0)),
                        end=float(getattr(s, "end", 0.0)),
                        text=str(getattr(s, "text", "")).strip(),
                    )
                )
        return STTResult(
            text=getattr(resp, "text", "").strip(),
            language=getattr(resp, "language", language_hint),
            segments=segments,
            duration=float(getattr(resp, "duration", 0.0)),
        )

    # -- TTSProvider --------------------------------------------------------

    def synthesize(
        self,
        text: str,
        *,
        language: str,
        voice: Optional[str] = None,
    ) -> TTSResult:
        client = _client(self.settings)
        try:
            resp = client.audio.speech.create(
                model=self.settings.openai_tts_model,
                voice=voice or self.settings.openai_tts_voice,
                input=text,
                response_format="wav",
            )
        except Exception as exc:  # pragma: no cover - network path
            raise ProviderError(f"openai tts failed: {exc}") from exc
        # The OpenAI SDK exposes either .read() or .content depending on
        # version; both yield raw audio bytes.
        if hasattr(resp, "read"):
            data = resp.read()
        else:  # pragma: no cover - older SDK
            data = bytes(getattr(resp, "content", b""))
        return TTSResult(audio=data, sample_rate=24000, format="wav")
