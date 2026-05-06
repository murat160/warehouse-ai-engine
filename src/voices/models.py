"""Voice-profile dataclasses + enums."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    CHILD = "child"
    TEEN = "teenager"
    NEUTRAL = "neutral"


class AgeStyle(str, Enum):
    CHILD = "child"
    TEEN = "teen"
    YOUNG_ADULT = "young_adult"
    ADULT = "adult"
    SENIOR = "senior"


class VoiceTone(str, Enum):
    CALM = "calm"
    WARM = "warm"
    SERIOUS = "serious"
    ENERGETIC = "energetic"
    FRIENDLY = "friendly"
    OFFICIAL = "official"
    DRAMATIC = "dramatic"
    STREET = "street"
    CULTURAL = "cultural"


class SpeedPreset(str, Enum):
    SLOW = "slow"
    NORMAL = "normal"
    FAST = "fast"


class PitchPreset(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class UseCase(str, Enum):
    TEXT = "text"
    VIDEO = "video"
    AUDIO = "audio"
    DUBBING = "dubbing"


@dataclass(frozen=True)
class VoiceProfile:
    """Self-contained voice description used by TTS routing and the UI."""

    id: str
    label_ru: str
    label_en: str
    description: str

    gender: Gender
    age_style: AgeStyle
    tone: VoiceTone

    languages: tuple[str, ...]              # codes from {ru, tk, tr, en}
    speed: SpeedPreset = SpeedPreset.NORMAL
    pitch: PitchPreset = PitchPreset.NORMAL
    default_emotion: str = "neutral"

    use_cases: tuple[UseCase, ...] = field(
        default_factory=lambda: (UseCase.TEXT, UseCase.VIDEO, UseCase.AUDIO)
    )

    # Provider hints — interpreted by the TTS layer:
    #   ``provider`` selects which backend renders this profile; ``backend_voice``
    #   maps to the upstream voice id (e.g. an OpenAI tts-1 voice name).
    provider: str = "openai"                # "openai" | "mms" | "auto"
    backend_voice: Optional[str] = None     # e.g. "alloy", "nova", "shimmer"
    notes: Optional[str] = None

    def supports_language(self, code: str) -> bool:
        return code in self.languages

    def to_public_dict(self) -> dict:
        return {
            "id": self.id,
            "label_ru": self.label_ru,
            "label_en": self.label_en,
            "description": self.description,
            "gender": self.gender.value,
            "age_style": self.age_style.value,
            "tone": self.tone.value,
            "languages": list(self.languages),
            "speed": self.speed.value,
            "pitch": self.pitch.value,
            "default_emotion": self.default_emotion,
            "use_cases": [u.value for u in self.use_cases],
            "provider": self.provider,
            "backend_voice": self.backend_voice,
            "notes": self.notes,
        }


__all__ = [
    "AgeStyle",
    "Gender",
    "PitchPreset",
    "SpeedPreset",
    "UseCase",
    "VoiceProfile",
    "VoiceTone",
]
