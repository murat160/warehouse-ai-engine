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
from .custom_voices import (
    ALLOWED_AUDIO_SUFFIXES,
    CustomVoiceEmotion,
    CustomVoiceError,
    CustomVoiceService,
    CustomVoiceUseCase,
    MAX_SAMPLE_BYTES,
    SAMPLE_DIR,
    VoiceClarity,
    VoiceIntensity,
    VoicePitch,
    VoiceSpeed,
    list_clarity_options,
    list_custom_voice_emotions,
    list_custom_voice_use_cases,
    list_intensity_options,
    list_pitch_options,
    list_speed_options,
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
    "ALLOWED_AUDIO_SUFFIXES",
    "AgeStyle",
    "CustomVoiceEmotion",
    "CustomVoiceError",
    "CustomVoiceService",
    "CustomVoiceUseCase",
    "Gender",
    "MAX_SAMPLE_BYTES",
    "PitchPreset",
    "SAMPLE_DIR",
    "SpeedPreset",
    "UseCase",
    "VOICE_CATALOG",
    "VoiceClarity",
    "VoiceIntensity",
    "VoicePitch",
    "VoiceProfile",
    "VoiceSpeed",
    "VoiceTone",
    "get_voice",
    "list_clarity_options",
    "list_custom_voice_emotions",
    "list_custom_voice_use_cases",
    "list_intensity_options",
    "list_pitch_options",
    "list_speed_options",
    "list_voices",
    "voices_for_language",
    "voices_for_use_case",
]
