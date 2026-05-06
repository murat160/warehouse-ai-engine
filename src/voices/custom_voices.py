"""Custom Voice service: enums, sample storage, preview rendering.

Audio samples live on disk under ``data/custom_voices/`` (in ``.gitignore``).
Only the *path* and metadata go into SQLite. Voice cloning itself is not
shipped — preview falls back to the catalog voice with the closest matching
metadata so the user gets an honest, immediate audible cue without any
remote cloning service. When an XTTS / ElevenLabs / OpenVoice provider is
plugged in later, ``render_preview`` is the single place to change.
"""

from __future__ import annotations

import logging
import shutil
import uuid
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional

from ..storage.repositories import (
    ConsentRequiredError,
    CustomVoiceDTO,
    CustomVoiceRepository,
    DEFAULT_CONSENT_TEXT,
)
from .catalog import VOICE_CATALOG, voices_for_language
from .models import VoiceProfile

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Custom-voice-specific enums (a superset of the built-in catalog enums)
# ---------------------------------------------------------------------------


class VoiceClarity(str, Enum):
    NORMAL = "normal"
    ENHANCED = "enhanced"
    STUDIO = "studio"


class VoiceIntensity(str, Enum):
    CALM = "calm"
    MEDIUM = "medium"
    STRONG = "strong"


class CustomVoiceEmotion(str, Enum):
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    SERIOUS = "serious"
    CONFIDENT = "confident"
    WARM = "warm"
    ENERGETIC = "energetic"
    DRAMATIC = "dramatic"
    RESPECTFUL = "respectful"


class CustomVoiceUseCase(str, Enum):
    TEXT = "text"
    BLOG = "blog"
    NEWS = "news"
    ADVERTISING = "advertising"
    FILM = "film"
    CHILDREN = "children"
    EDUCATIONAL = "educational"
    DUBBING = "dubbing"


class VoiceSpeed(str, Enum):
    SLOW = "slow"
    NORMAL = "normal"
    FAST = "fast"


class VoicePitch(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


@dataclass(frozen=True)
class _Labelled:
    code: str
    label_ru: str
    label_en: str


def list_speed_options() -> List[_Labelled]:
    return [
        _Labelled("slow", "Медленно", "Slow"),
        _Labelled("normal", "Нормально", "Normal"),
        _Labelled("fast", "Быстро", "Fast"),
    ]


def list_pitch_options() -> List[_Labelled]:
    return [
        _Labelled("low", "Низкий", "Low"),
        _Labelled("normal", "Обычный", "Normal"),
        _Labelled("high", "Высокий", "High"),
    ]


def list_clarity_options() -> List[_Labelled]:
    return [
        _Labelled("normal", "Обычная", "Normal"),
        _Labelled("enhanced", "Улучшенная", "Enhanced"),
        _Labelled("studio", "Студийная", "Studio"),
    ]


def list_intensity_options() -> List[_Labelled]:
    return [
        _Labelled("calm", "Спокойно", "Calm"),
        _Labelled("medium", "Средне", "Medium"),
        _Labelled("strong", "Сильно", "Strong"),
    ]


def list_custom_voice_emotions() -> List[_Labelled]:
    return [
        _Labelled("neutral", "Нейтрально", "Neutral"),
        _Labelled("happy", "Радостно", "Happy"),
        _Labelled("sad", "Грустно", "Sad"),
        _Labelled("serious", "Серьёзно", "Serious"),
        _Labelled("confident", "Уверенно", "Confident"),
        _Labelled("warm", "Тепло", "Warm"),
        _Labelled("energetic", "Энергично", "Energetic"),
        _Labelled("dramatic", "Драматично", "Dramatic"),
        _Labelled("respectful", "Уважительно", "Respectful"),
    ]


def list_custom_voice_use_cases() -> List[_Labelled]:
    return [
        _Labelled("text", "Текст", "Text"),
        _Labelled("blog", "Блог", "Blog"),
        _Labelled("news", "Новости", "News"),
        _Labelled("advertising", "Реклама", "Advertising"),
        _Labelled("film", "Фильм", "Film"),
        _Labelled("children", "Детский контент", "Children"),
        _Labelled("educational", "Образовательное видео", "Educational"),
        _Labelled("dubbing", "Дубляж", "Dubbing"),
    ]


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


SAMPLE_DIR = Path("data/custom_voices")
ALLOWED_AUDIO_SUFFIXES = {".wav", ".mp3", ".ogg", ".m4a", ".flac", ".webm"}
MAX_SAMPLE_BYTES = 25 * 1024 * 1024  # 25 MB hard cap on uploads


class CustomVoiceError(RuntimeError):
    """Generic custom-voice failure that is safe to surface to the user."""


class CustomVoiceService:
    """File-system + repository orchestrator for Custom Voices."""

    def __init__(
        self,
        repository: CustomVoiceRepository,
        *,
        sample_dir: Path = SAMPLE_DIR,
    ) -> None:
        self.repository = repository
        self.sample_dir = sample_dir
        self.sample_dir.mkdir(parents=True, exist_ok=True)

    # -- sample handling ---------------------------------------------------

    def save_sample(self, *, content: bytes, filename: str) -> Path:
        """Persist an uploaded/recorded audio sample under ``sample_dir``."""
        if not content:
            raise CustomVoiceError("audio sample is empty")
        if len(content) > MAX_SAMPLE_BYTES:
            raise CustomVoiceError(
                f"sample is too large ({len(content)} bytes > {MAX_SAMPLE_BYTES})"
            )
        suffix = Path(filename).suffix.lower() or ".wav"
        if suffix not in ALLOWED_AUDIO_SUFFIXES:
            raise CustomVoiceError(
                f"unsupported audio format: {suffix!r}. "
                f"allowed: {sorted(ALLOWED_AUDIO_SUFFIXES)}"
            )
        target = self.sample_dir / f"{uuid.uuid4().hex}{suffix}"
        target.write_bytes(content)
        return target

    def delete_sample(self, path: Optional[str]) -> None:
        if not path:
            return
        target = Path(path)
        try:
            if target.is_file() and self._is_inside_sample_dir(target):
                target.unlink()
        except OSError:
            logger.warning("failed to delete custom-voice sample %s", target)

    def _is_inside_sample_dir(self, target: Path) -> bool:
        try:
            target.resolve().relative_to(self.sample_dir.resolve())
            return True
        except ValueError:
            return False

    # -- CRUD façade -------------------------------------------------------

    def create(
        self,
        *,
        name: str,
        consent_given: bool,
        language: str = "ru",
        speed: str = "normal",
        pitch: str = "normal",
        emotion: str = "neutral",
        clarity: str = "normal",
        intensity: str = "medium",
        use_case: str = "text",
        description: Optional[str] = None,
        parent_id: Optional[str] = None,
        channel_id: Optional[str] = None,
        bound_style: Optional[str] = None,
        bound_video_use_case: Optional[str] = None,
        sample_bytes: Optional[bytes] = None,
        sample_filename: Optional[str] = None,
    ) -> CustomVoiceDTO:
        """Create a profile. Persists the sample (if any) before the row."""
        if not consent_given:
            raise ConsentRequiredError(
                "Custom Voice creation requires explicit consent: tick the "
                "«Я подтверждаю, что имею право использовать этот голос» box."
            )

        sample_path: Optional[str] = None
        if sample_bytes:
            saved = self.save_sample(
                content=sample_bytes, filename=sample_filename or "sample.wav"
            )
            sample_path = str(saved)

        try:
            return self.repository.create(
                name=name,
                description=description,
                language=language,
                speed=speed,
                pitch=pitch,
                emotion=emotion,
                clarity=clarity,
                intensity=intensity,
                use_case=use_case,
                parent_id=parent_id,
                channel_id=channel_id,
                bound_style=bound_style,
                bound_video_use_case=bound_video_use_case,
                sample_path=sample_path,
                consent_given=True,
                consent_text=DEFAULT_CONSENT_TEXT,
            )
        except Exception:
            # Roll back the saved file if the DB row failed.
            if sample_path:
                self.delete_sample(sample_path)
            raise

    def delete(self, voice_id: str) -> bool:
        existing = self.repository.get(voice_id)
        if existing is None:
            return False
        self.repository.delete(voice_id)
        self.delete_sample(existing.sample_path)
        return True

    # -- preview -----------------------------------------------------------

    def closest_catalog_voice(self, profile: CustomVoiceDTO) -> Optional[VoiceProfile]:
        """Pick the catalog voice that best matches the profile.

        Used by ``render_preview`` to give the user an audible approximation
        until a real voice-cloning provider is wired in.
        """
        candidates = voices_for_language(profile.language) or list(VOICE_CATALOG.values())
        if not candidates:
            return None

        wanted_tone = _emotion_to_tone(profile.emotion)

        def score(voice: VoiceProfile) -> int:
            s = 0
            if voice.speed.value == profile.speed:
                s += 2
            if voice.pitch.value == profile.pitch:
                s += 2
            if wanted_tone and voice.tone.value == wanted_tone:
                s += 3
            if voice.default_emotion == profile.emotion:
                s += 1
            return s

        return max(candidates, key=score)


def _emotion_to_tone(emotion: str) -> Optional[str]:
    mapping = {
        "happy": "friendly",
        "sad": "warm",
        "serious": "serious",
        "confident": "serious",
        "warm": "warm",
        "energetic": "energetic",
        "dramatic": "dramatic",
        "respectful": "official",
    }
    return mapping.get(emotion)


__all__ = [
    "ALLOWED_AUDIO_SUFFIXES",
    "CustomVoiceEmotion",
    "CustomVoiceError",
    "CustomVoiceService",
    "CustomVoiceUseCase",
    "DEFAULT_CONSENT_TEXT",
    "MAX_SAMPLE_BYTES",
    "SAMPLE_DIR",
    "VoiceClarity",
    "VoiceIntensity",
    "VoicePitch",
    "VoiceSpeed",
    "list_clarity_options",
    "list_custom_voice_emotions",
    "list_custom_voice_use_cases",
    "list_intensity_options",
    "list_pitch_options",
    "list_speed_options",
]
