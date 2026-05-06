"""Text translation subsystem (ru, tk, tr, en) with ru<->tk priority."""

from .languages import LANGUAGES, Language, LanguagePair, normalize_language
from .styles import STYLE_PROFILES, StyleProfile, TranslationStyle, build_prompt_hint, get_style, list_styles
from .translation_memory import TranslationMemoryHit, TranslationMemoryService
from .translator_service import TranslationResult, TranslatorService
from .user_glossary import UserGlossaryService

__all__ = [
    "LANGUAGES",
    "Language",
    "LanguagePair",
    "STYLE_PROFILES",
    "StyleProfile",
    "TranslationMemoryHit",
    "TranslationMemoryService",
    "TranslationResult",
    "TranslationStyle",
    "TranslatorService",
    "UserGlossaryService",
    "build_prompt_hint",
    "get_style",
    "list_styles",
    "normalize_language",
]
