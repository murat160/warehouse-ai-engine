"""Translation style / emotional register selectors.

Picking a style adds a system-prompt hint to the OpenAI provider and an
input-side prefix for the offline NLLB provider. Turkmen target gets extra
guidance regardless of style, so the output stays idiomatic instead of
mirroring Russian sentence structure word-by-word.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional


class TranslationStyle(str, Enum):
    NEUTRAL = "neutral"
    RESPECTFUL = "respectful"
    WARM = "warm"
    FORMAL = "formal"
    FRIENDLY = "friendly"
    EXPRESSIVE = "expressive"
    LITERARY = "literary"
    CASUAL = "casual"


@dataclass(frozen=True)
class StyleProfile:
    """Display metadata + provider-side hints for a style."""

    style: TranslationStyle
    label_ru: str
    label_en: str
    description: str
    prompt_hint: str
    nllb_prefix: str = ""

    @property
    def code(self) -> str:
        return self.style.value


STYLE_PROFILES: Dict[TranslationStyle, StyleProfile] = {
    TranslationStyle.NEUTRAL: StyleProfile(
        style=TranslationStyle.NEUTRAL,
        label_ru="Нейтральный",
        label_en="Neutral",
        description="Сбалансированный регистр без эмоций.",
        prompt_hint="Use a neutral, balanced register; no extra colouring.",
    ),
    TranslationStyle.RESPECTFUL: StyleProfile(
        style=TranslationStyle.RESPECTFUL,
        label_ru="Уважительный",
        label_en="Respectful",
        description="Подчёркнуто вежливый. Туркменский — в форме «Siz».",
        prompt_hint=(
            "Use a respectful register. For Russian, prefer 'Вы' addressing. "
            "For Turkmen, use 'Siz' addressing and polite verb suffixes."
        ),
        nllb_prefix="(уважительно) ",
    ),
    TranslationStyle.WARM: StyleProfile(
        style=TranslationStyle.WARM,
        label_ru="Тёплый",
        label_en="Warm",
        description="Мягкий, доброжелательный тон.",
        prompt_hint=(
            "Use a warm, kind tone; choose softer wording and gentle phrasing "
            "without being sentimental."
        ),
        nllb_prefix="(тепло) ",
    ),
    TranslationStyle.FORMAL: StyleProfile(
        style=TranslationStyle.FORMAL,
        label_ru="Официальный",
        label_en="Formal",
        description="Деловой стиль для договоров, писем, документов.",
        prompt_hint=(
            "Use a strictly formal, business-appropriate register. Avoid "
            "contractions, slang and emotional colouring. Preserve titles."
        ),
        nllb_prefix="(официально) ",
    ),
    TranslationStyle.FRIENDLY: StyleProfile(
        style=TranslationStyle.FRIENDLY,
        label_ru="Дружеский",
        label_en="Friendly",
        description="Лёгкий, доверительный тон. Туркменский — форма «sen», когда уместно.",
        prompt_hint=(
            "Use a friendly conversational register. For Turkmen, prefer the "
            "'sen' form when contextually appropriate."
        ),
        nllb_prefix="(по-дружески) ",
    ),
    TranslationStyle.EXPRESSIVE: StyleProfile(
        style=TranslationStyle.EXPRESSIVE,
        label_ru="Эмоциональный",
        label_en="Expressive",
        description="Живой, выразительный язык без потери точности.",
        prompt_hint=(
            "Use expressive, emotionally engaging language while keeping "
            "the meaning fully accurate."
        ),
        nllb_prefix="(эмоционально) ",
    ),
    TranslationStyle.LITERARY: StyleProfile(
        style=TranslationStyle.LITERARY,
        label_ru="Литературный",
        label_en="Literary",
        description="Книжный регистр, идиомы, чистый письменный язык.",
        prompt_hint=(
            "Use a literary register. Prefer idiomatic phrasing and rich "
            "vocabulary. Avoid awkward calques."
        ),
        nllb_prefix="(литературно) ",
    ),
    TranslationStyle.CASUAL: StyleProfile(
        style=TranslationStyle.CASUAL,
        label_ru="Простой разговорный",
        label_en="Casual",
        description="Простые короткие фразы, разговорный язык.",
        prompt_hint=(
            "Use simple, casual spoken language. Short sentences are fine; "
            "everyday vocabulary preferred."
        ),
        nllb_prefix="(разговорно) ",
    ),
}


# Always-on guidance for Turkmen target — added on top of any style.
TURKMEN_TARGET_GUIDANCE = (
    "When the target is Turkmen: write idiomatic, native-sounding Turkmen "
    "with proper diacritics (ä, ý, ň, ö, ü, ç, ş). Do not transliterate from "
    "Russian or English. Do not copy the source sentence structure when "
    "Turkmen idiom would differ. Prefer fluent native phrasing over literal "
    "renderings; respect Turkmen word order and politeness conventions."
)


# Always-on guidance for Russian target.
RUSSIAN_TARGET_GUIDANCE = (
    "When the target is Russian: write fluent, natural literary Russian. "
    "Translate the meaning, do not transliterate. Keep proper names but "
    "render foreign words by their accepted Russian equivalent when one exists."
)


def get_style(value: Optional[str]) -> StyleProfile:
    """Resolve a style code (case-insensitive) to a profile, default neutral."""
    if not value:
        return STYLE_PROFILES[TranslationStyle.NEUTRAL]
    try:
        return STYLE_PROFILES[TranslationStyle(value.lower())]
    except (ValueError, KeyError):
        return STYLE_PROFILES[TranslationStyle.NEUTRAL]


def list_styles() -> list[StyleProfile]:
    return list(STYLE_PROFILES.values())


def build_prompt_hint(style: StyleProfile, target_lang: str) -> str:
    """Compose the style-specific guidance for a system prompt."""
    chunks = [style.prompt_hint]
    if target_lang == "tk":
        chunks.append(TURKMEN_TARGET_GUIDANCE)
    elif target_lang == "ru":
        chunks.append(RUSSIAN_TARGET_GUIDANCE)
    return " ".join(chunks)


__all__ = [
    "STYLE_PROFILES",
    "StyleProfile",
    "TURKMEN_TARGET_GUIDANCE",
    "TranslationStyle",
    "build_prompt_hint",
    "get_style",
    "list_styles",
]
