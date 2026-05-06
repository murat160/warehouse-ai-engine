"""Voice profile catalog and registry.

Defines :class:`VoiceProfile` (a self-contained description of a TTS voice)
and a built-in catalog of 23 profiles covering male / female / child /
teen / cultural / news / blogger / dramatic / advertising voices for
ru / tk / tr / en. Profiles are *metadata* — actual audio rendering is
performed by the TTS providers; the profile drives provider selection
(MMS-TTS for Turkmen, OpenAI tts-1 voices for the rest) plus speed and
pitch hints applied during synthesis.
"""

from .catalog import (
    VOICE_CATALOG,
    get_voice,
    list_voices,
    voices_for_language,
    voices_for_use_case,
)
from .models import (
    AgeStyle,
    Gender,
    PitchPreset,
    SpeedPreset,
    UseCase,
    VoiceProfile,
    VoiceTone,
)

__all__ = [
    "AgeStyle",
    "Gender",
    "PitchPreset",
    "SpeedPreset",
    "UseCase",
    "VOICE_CATALOG",
    "VoiceProfile",
    "VoiceTone",
    "get_voice",
    "list_voices",
    "voices_for_language",
    "voices_for_use_case",
]
