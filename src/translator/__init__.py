"""Text translation subsystem (ru, tk, tr, en) with ru<->tk priority."""

from .languages import LANGUAGES, Language, LanguagePair, normalize_language
from .translator_service import TranslationResult, TranslatorService

__all__ = [
    "LANGUAGES",
    "Language",
    "LanguagePair",
    "TranslationResult",
    "TranslatorService",
    "normalize_language",
]
