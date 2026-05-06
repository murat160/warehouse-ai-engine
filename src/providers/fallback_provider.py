"""Fallback provider: offline-friendly, low-cost backup.

Goals:
* never fail at import time,
* offer a usable Turkmen TTS through Meta MMS-TTS (Vits) when enabled,
* return a clearly-marked stub translation rather than crashing the API.

This keeps the engine bootable in development and CI even without an OpenAI
key, and gives us an alternate Turkmen voice — MMS-TTS is currently the best
free option for ``tk``.
"""

from __future__ import annotations

import logging
from typing import Optional

from ..config import Settings, get_settings
from .base import (
    AudioBytes,
    ProviderError,
    ProviderUnavailableError,
    STTProvider,
    STTResult,
    TTSProvider,
    TTSResult,
    TranslationProvider,
)

logger = logging.getLogger(__name__)


class FallbackProvider(TranslationProvider, STTProvider, TTSProvider):
    """Last-resort provider used when the primary one is unavailable."""

    name = "fallback"

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self._mms_model = None
        self._mms_tokenizer = None

    # -- TranslationProvider ------------------------------------------------

    def is_available(self, language: Optional[str] = None) -> bool:  # type: ignore[override]
        # Translation fallback is intentionally disabled by default — silent
        # passthrough is worse than a clear error for the caller. TTS for
        # Turkmen is available when the operator opted-in to MMS.
        if language == "tk":
            return self.settings.mms_tts_tuk_enabled
        return False

    def translate(
        self,
        *,
        text: str,
        source_lang: str,
        target_lang: str,
        literary: bool = False,
    ) -> str:
        raise ProviderUnavailableError(
            "no fallback translator is configured; set OPENAI_API_KEY"
        )

    # -- STTProvider --------------------------------------------------------

    def transcribe(
        self,
        audio: AudioBytes,
        *,
        language_hint: Optional[str] = None,
        with_segments: bool = False,
    ) -> STTResult:
        raise ProviderUnavailableError(
            "no fallback STT is configured; set OPENAI_API_KEY or wire whisper.cpp"
        )

    # -- TTSProvider (Meta MMS for Turkmen) --------------------------------

    def synthesize(
        self,
        text: str,
        *,
        language: str,
        voice: Optional[str] = None,
    ) -> TTSResult:
        if language != "tk" or not self.settings.mms_tts_tuk_enabled:
            raise ProviderUnavailableError(
                f"fallback TTS not available for language={language!r}"
            )
        model, tokenizer = self._load_mms()
        try:
            import torch  # type: ignore
        except ImportError as exc:  # pragma: no cover - optional dep
            raise ProviderUnavailableError(
                "torch is required for MMS-TTS; install transformers, torch, scipy"
            ) from exc
        inputs = tokenizer(text, return_tensors="pt")
        with torch.no_grad():
            waveform = model(**inputs).waveform
        sample_rate = int(getattr(model.config, "sampling_rate", 16000))
        audio = _waveform_to_wav_bytes(waveform.squeeze().cpu().numpy(), sample_rate)
        return TTSResult(audio=audio, sample_rate=sample_rate, format="wav")

    def _load_mms(self):
        if self._mms_model is not None:
            return self._mms_model, self._mms_tokenizer
        try:
            from transformers import AutoTokenizer, VitsModel  # type: ignore
        except ImportError as exc:  # pragma: no cover - optional dep
            raise ProviderUnavailableError(
                "transformers is required for MMS-TTS"
            ) from exc
        name = self.settings.mms_tts_tuk_model
        logger.info("loading MMS-TTS model %s", name)
        try:
            self._mms_model = VitsModel.from_pretrained(name)
            self._mms_tokenizer = AutoTokenizer.from_pretrained(name)
        except Exception as exc:  # pragma: no cover - network/cache path
            raise ProviderError(f"failed to load MMS-TTS: {exc}") from exc
        return self._mms_model, self._mms_tokenizer


def _waveform_to_wav_bytes(samples, sample_rate: int) -> bytes:
    """Encode a float32 waveform (-1..1) into a 16-bit PCM WAV byte string."""
    import wave

    import numpy as np

    pcm = np.clip(samples, -1.0, 1.0)
    pcm = (pcm * 32767.0).astype("<i2")
    import io as _io

    buf = _io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm.tobytes())
    return buf.getvalue()
