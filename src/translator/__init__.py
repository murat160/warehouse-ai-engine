"""Text translation subsystem (ru, tk, tr, en) with ru<->tk priority."""

from .languages import LANGUAGES, Language, LanguagePair, normalize_language
from .styles import (
    EMOTION_PROFILES,
    STYLE_PROFILES,
    TONE_PROFILES,
    DeliveryTone,
    Emotion,
    EmotionProfile,
    StyleProfile,
    ToneProfile,
    TranslationStyle,
    build_prompt_hint,
    get_emotion,
    get_style,
    get_tone,
    list_emotions,
    list_styles,
    list_tones,
)
from .translation_memory import TranslationMemoryHit, TranslationMemoryService
from .translator_service import TranslationResult, TranslatorService
from .user_glossary import UserGlossaryService

__all__ = [
    "DeliveryTone",
    "EMOTION_PROFILES",
    "Emotion",
    "EmotionProfile",
    "LANGUAGES",
    "Language",
    "LanguagePair",
    "STYLE_PROFILES",
    "StyleProfile",
    "TONE_PROFILES",
    "ToneProfile",
    "TranslationMemoryHit",
    "TranslationMemoryService",
    "TranslationResult",
    "TranslationStyle",
    "TranslatorService",
    "UserGlossaryService",
    "build_prompt_hint",
    "get_emotion",
    "get_style",
    "get_tone",
    "list_emotions",
    "list_styles",
    "list_tones",
    "normalize_language",
]
