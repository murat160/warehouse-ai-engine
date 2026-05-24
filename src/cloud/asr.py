"""Speech-to-text service for Murat AI.

Full AI mode uses openai-whisper locally. Streamlit Cloud preview may not have
Whisper installed, so this module imports it lazily and returns a clear preview
message instead of crashing the whole UI.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ASRResult:
    text: str
    language: Optional[str] = None  # ISO 639-1 (or None when unknown)


class ASRService:
    """Wraps an openai-whisper model and exposes a single ``transcribe`` call."""

    def __init__(self, model_name: str = "small") -> None:
        logger.info("loading whisper model %s", model_name)
        self.model_name = model_name
        self.model: Optional[Any] = None
        self.preview_reason: Optional[str] = None
        try:
            import whisper  # type: ignore

            self.model = whisper.load_model(model_name)
        except Exception as exc:  # noqa: BLE001
            self.preview_reason = str(exc)
            logger.warning("Whisper unavailable; ASR runs in preview mode: %s", exc)

    def transcribe(
        self, wav_path: str, *, language: Optional[str] = None
    ) -> ASRResult:
        """Transcribe ``wav_path``. ``language`` is an optional hint."""
        if self.model is None:
            return ASRResult(
                text=(
                    "[Murat AI preview mode: speech recognition model is not "
                    "installed here. Deploy on VPS with requirements-full.txt "
                    "for real audio/video transcription.]"
                ),
                language=language,
            )
        result = self.model.transcribe(
            wav_path,
            task="transcribe",
            language=language,
        )
        text = (result.get("text") or "").strip()
        detected = result.get("language") or language
        return ASRResult(text=text, language=detected)
