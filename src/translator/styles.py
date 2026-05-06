"""Translation styles, delivery tones and emotion presets.

The translator exposes three orthogonal axes the caller can combine:

* :class:`TranslationStyle` — the *register* / *genre* of the output
  (15 values; the default is :data:`TranslationStyle.NATURAL` — a living,
  natural language, NOT literary).
* :class:`DeliveryTone` — the *manner* of delivery, independent of style
  (16 values: calm, confident, friendly, …).
* :class:`Emotion` — the *emotional colouring* (7 values: neutral, happy,
  sad, serious, excited, respectful, warm).

Every axis carries a short prompt hint that is composed into the OpenAI
system prompt; offline NLLB has no native control over these, so we keep
the hints visible in the UI and let the user-glossary / TM enforce wording.
Turkmen and Russian targets always receive an extra guidance block that
asks the model to write idiomatic native phrasing instead of mirroring
the source structure.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Style (15 values) — the genre/register of the translation
# ---------------------------------------------------------------------------


class TranslationStyle(str, Enum):
    NATURAL = "natural"
    BLOGGER = "blogger"
    CONVERSATIONAL = "conversational"
    STREET = "street"
    LITERARY = "literary"
    FORMAL = "formal"
    NEWS = "news"
    CULTURAL = "cultural"
    EXPRESSIVE = "expressive"
    DRAMATIC = "dramatic"
    CHILDREN = "children"
    TEEN = "teen"
    HUMOROUS = "humorous"
    ADVERTISING = "advertising"
    EXPERT = "expert"


@dataclass(frozen=True)
class StyleProfile:
    style: TranslationStyle
    label_ru: str
    label_en: str
    description: str
    prompt_hint: str

    @property
    def code(self) -> str:
        return self.style.value


STYLE_PROFILES: Dict[TranslationStyle, StyleProfile] = {
    TranslationStyle.NATURAL: StyleProfile(
        style=TranslationStyle.NATURAL,
        label_ru="Обычный естественный",
        label_en="Natural",
        description="Живой, естественный язык, как в обычном тексте или видео.",
        prompt_hint=(
            "Translate into living, natural everyday language. Avoid "
            "machine-translation feel, avoid rigid literary register and "
            "avoid word-for-word calques. Aim for the way a native speaker "
            "would naturally say this in a normal context."
        ),
    ),
    TranslationStyle.BLOGGER: StyleProfile(
        style=TranslationStyle.BLOGGER,
        label_ru="Блогерский",
        label_en="Blogger",
        description="Живой, энергичный голос — YouTube, TikTok, Reels, Shorts.",
        prompt_hint=(
            "Translate as a content creator would speak on YouTube/TikTok: "
            "engaging, lively, conversational, slightly informal but never "
            "rude. Short sentences are fine. Keep hooks intact."
        ),
    ),
    TranslationStyle.CONVERSATIONAL: StyleProfile(
        style=TranslationStyle.CONVERSATIONAL,
        label_ru="Разговорный",
        label_en="Conversational",
        description="Простая человеческая речь, как в обычной беседе.",
        prompt_hint=(
            "Translate as plain spoken language used between people in a "
            "normal conversation. Simple words, short clauses, no jargon."
        ),
    ),
    TranslationStyle.STREET: StyleProfile(
        style=TranslationStyle.STREET,
        label_ru="Уличный / повседневный",
        label_en="Street / Casual",
        description="Современный молодёжный язык. Без грубости по умолчанию.",
        prompt_hint=(
            "Translate in a modern street/casual register that young people "
            "actually use online. Free, contemporary, not formal — but do "
            "NOT add slurs, profanity or insults unless the source has them."
        ),
    ),
    TranslationStyle.LITERARY: StyleProfile(
        style=TranslationStyle.LITERARY,
        label_ru="Литературный",
        label_en="Literary",
        description="Книжный регистр. Только когда явно выбран — не дефолт.",
        prompt_hint=(
            "Translate in a polished literary register suitable for books "
            "and serious narration. Rich vocabulary, well-formed sentences. "
            "Use ONLY when the user explicitly asked for literary."
        ),
    ),
    TranslationStyle.FORMAL: StyleProfile(
        style=TranslationStyle.FORMAL,
        label_ru="Официальный",
        label_en="Formal",
        description="Деловой регистр для документов и объявлений.",
        prompt_hint=(
            "Translate in a strictly formal, business-appropriate register. "
            "Precise terminology, no contractions, no slang, no emotional "
            "colouring. Preserve titles and structure of documents."
        ),
    ),
    TranslationStyle.NEWS: StyleProfile(
        style=TranslationStyle.NEWS,
        label_ru="Новостной",
        label_en="News",
        description="Дикторская подача — чётко, спокойно, уверенно.",
        prompt_hint=(
            "Translate as a professional news anchor would read it: "
            "clear, calm, confident. No humour, no slang. Keep dates, "
            "numbers, places and names exact."
        ),
    ),
    TranslationStyle.CULTURAL: StyleProfile(
        style=TranslationStyle.CULTURAL,
        label_ru="Культурный",
        label_en="Cultural",
        description="С уважением к языку. Особенно важно для туркменского.",
        prompt_hint=(
            "Translate respecting the cultural conventions of the target "
            "language. For Turkmen specifically: write the way a native "
            "speaker would; do not mirror Russian sentence structure if "
            "Turkmen idiom would phrase it differently. Use polite forms "
            "where appropriate."
        ),
    ),
    TranslationStyle.EXPRESSIVE: StyleProfile(
        style=TranslationStyle.EXPRESSIVE,
        label_ru="Эмоциональный",
        label_en="Expressive",
        description="Живо и выразительно — для сильных видео и историй.",
        prompt_hint=(
            "Translate with rich, expressive language while keeping the "
            "meaning fully accurate. Suitable for storytelling and "
            "powerful video voiceovers."
        ),
    ),
    TranslationStyle.DRAMATIC: StyleProfile(
        style=TranslationStyle.DRAMATIC,
        label_ru="Драматичный",
        label_en="Dramatic",
        description="Кинематографичный — для озвучки фильмов и историй.",
        prompt_hint=(
            "Translate for dramatic delivery: build tension, preserve "
            "rhythm, allow for pauses. Suitable for film dubbing and "
            "narrative voiceover."
        ),
    ),
    TranslationStyle.CHILDREN: StyleProfile(
        style=TranslationStyle.CHILDREN,
        label_ru="Детский",
        label_en="Children",
        description="Простой и мягкий язык, понятный детям.",
        prompt_hint=(
            "Translate with simple, soft, child-friendly vocabulary. "
            "Short sentences, no complex words, no scary phrasing."
        ),
    ),
    TranslationStyle.TEEN: StyleProfile(
        style=TranslationStyle.TEEN,
        label_ru="Подростковый",
        label_en="Teen",
        description="Современный молодёжный язык без официальности.",
        prompt_hint=(
            "Translate in a modern teen voice: contemporary, lively, not "
            "formal. Use phrasing today's teenagers actually use, but "
            "without profanity unless the source has it."
        ),
    ),
    TranslationStyle.HUMOROUS: StyleProfile(
        style=TranslationStyle.HUMOROUS,
        label_ru="Юмористический",
        label_en="Humorous",
        description="Лёгкая подача, шутки адаптируются под язык.",
        prompt_hint=(
            "Translate with light, humorous tone. Adapt jokes and "
            "wordplay to the target language and culture rather than "
            "translating them literally."
        ),
    ),
    TranslationStyle.ADVERTISING: StyleProfile(
        style=TranslationStyle.ADVERTISING,
        label_ru="Рекламный",
        label_en="Advertising",
        description="Продающий, короткий, яркий — для промо.",
        prompt_hint=(
            "Translate as advertising/marketing copy: short, punchy, "
            "value-forward. Highlight benefits. Keep the call to action "
            "front and centre."
        ),
    ),
    TranslationStyle.EXPERT: StyleProfile(
        style=TranslationStyle.EXPERT,
        label_ru="Экспертный",
        label_en="Expert",
        description="Уверенно и понятно — для обучающих видео.",
        prompt_hint=(
            "Translate as a confident, clear expert teaching the topic. "
            "Use precise terminology but explain it simply. No filler."
        ),
    ),
}


# ---------------------------------------------------------------------------
# Delivery tone (16 values) — orthogonal to style
# ---------------------------------------------------------------------------


class DeliveryTone(str, Enum):
    CALM = "calm"
    CONFIDENT = "confident"
    FRIENDLY = "friendly"
    WARM = "warm"
    SERIOUS = "serious"
    CHEERFUL = "cheerful"
    ENERGETIC = "energetic"
    RESPECTFUL = "respectful"
    SOFT = "soft"
    FIRM = "firm"
    CULTURAL = "cultural"
    MODERN = "modern"
    TRADITIONAL = "traditional"
    SIMPLE = "simple"
    DEEP = "deep"
    EMOTIONAL = "emotional"


@dataclass(frozen=True)
class ToneProfile:
    tone: DeliveryTone
    label_ru: str
    label_en: str
    prompt_hint: str

    @property
    def code(self) -> str:
        return self.tone.value


TONE_PROFILES: Dict[DeliveryTone, ToneProfile] = {
    DeliveryTone.CALM: ToneProfile(DeliveryTone.CALM, "Спокойный", "Calm",
        "Maintain a calm, measured delivery; no rushed phrasing."),
    DeliveryTone.CONFIDENT: ToneProfile(DeliveryTone.CONFIDENT, "Уверенный", "Confident",
        "Project quiet confidence; use definitive verbs, avoid hedging."),
    DeliveryTone.FRIENDLY: ToneProfile(DeliveryTone.FRIENDLY, "Дружеский", "Friendly",
        "Sound friendly and approachable; close to the listener."),
    DeliveryTone.WARM: ToneProfile(DeliveryTone.WARM, "Тёплый", "Warm",
        "Use warm, kind phrasing; be gentle without being sentimental."),
    DeliveryTone.SERIOUS: ToneProfile(DeliveryTone.SERIOUS, "Серьёзный", "Serious",
        "Be serious and earnest; no humour or filler."),
    DeliveryTone.CHEERFUL: ToneProfile(DeliveryTone.CHEERFUL, "Весёлый", "Cheerful",
        "Sound upbeat and cheerful while staying tasteful."),
    DeliveryTone.ENERGETIC: ToneProfile(DeliveryTone.ENERGETIC, "Энергичный", "Energetic",
        "High energy; momentum-driven phrasing, action verbs."),
    DeliveryTone.RESPECTFUL: ToneProfile(DeliveryTone.RESPECTFUL, "Уважительный", "Respectful",
        "Use respectful forms (Russian Вы / Turkmen Siz) and polite suffixes."),
    DeliveryTone.SOFT: ToneProfile(DeliveryTone.SOFT, "Мягкий", "Soft",
        "Soft, gentle delivery; avoid harsh imperatives."),
    DeliveryTone.FIRM: ToneProfile(DeliveryTone.FIRM, "Жёсткий", "Firm",
        "Firm, direct, decisive — but never rude."),
    DeliveryTone.CULTURAL: ToneProfile(DeliveryTone.CULTURAL, "Культурный", "Cultural",
        "Respect target-language culture; prefer native idioms over calques."),
    DeliveryTone.MODERN: ToneProfile(DeliveryTone.MODERN, "Современный", "Modern",
        "Use modern, contemporary phrasing the way people speak today."),
    DeliveryTone.TRADITIONAL: ToneProfile(DeliveryTone.TRADITIONAL, "Традиционный", "Traditional",
        "Lean on traditional phrasings and idioms."),
    DeliveryTone.SIMPLE: ToneProfile(DeliveryTone.SIMPLE, "Простой", "Simple",
        "Use the simplest words and shortest clauses that convey the meaning."),
    DeliveryTone.DEEP: ToneProfile(DeliveryTone.DEEP, "Глубокий", "Deep",
        "Convey depth and weight; thoughtful, considered phrasing."),
    DeliveryTone.EMOTIONAL: ToneProfile(DeliveryTone.EMOTIONAL, "Эмоциональный", "Emotional",
        "Allow visible emotion to come through in the wording."),
}


# ---------------------------------------------------------------------------
# Emotion preset (7 values) — used both for translation prompt and TTS
# ---------------------------------------------------------------------------


class Emotion(str, Enum):
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    SERIOUS = "serious"
    EXCITED = "excited"
    RESPECTFUL = "respectful"
    WARM = "warm"


@dataclass(frozen=True)
class EmotionProfile:
    emotion: Emotion
    label_ru: str
    label_en: str
    prompt_hint: str

    @property
    def code(self) -> str:
        return self.emotion.value


EMOTION_PROFILES: Dict[Emotion, EmotionProfile] = {
    Emotion.NEUTRAL: EmotionProfile(Emotion.NEUTRAL, "Нейтральная", "Neutral",
        "No specific emotional colouring."),
    Emotion.HAPPY: EmotionProfile(Emotion.HAPPY, "Радостная", "Happy",
        "Lift the wording slightly; choose positive synonyms where natural."),
    Emotion.SAD: EmotionProfile(Emotion.SAD, "Грустная", "Sad",
        "Subdued phrasing; gentler synonyms; do not invent extra sadness."),
    Emotion.SERIOUS: EmotionProfile(Emotion.SERIOUS, "Серьёзная", "Serious",
        "Serious, weighty wording; no joking."),
    Emotion.EXCITED: EmotionProfile(Emotion.EXCITED, "Восторженная", "Excited",
        "Excitement and momentum; vivid synonyms while staying accurate."),
    Emotion.RESPECTFUL: EmotionProfile(Emotion.RESPECTFUL, "Уважительная", "Respectful",
        "Polite, respectful forms; honour titles and seniority."),
    Emotion.WARM: EmotionProfile(Emotion.WARM, "Тёплая", "Warm",
        "Warm and kind; soften imperatives."),
}


# ---------------------------------------------------------------------------
# Always-on language guidance (kept independent from style/tone choices)
# ---------------------------------------------------------------------------


TURKMEN_TARGET_GUIDANCE = (
    "When the target is Turkmen: write idiomatic, native-sounding Turkmen "
    "with proper diacritics (ä, ý, ň, ö, ü, ç, ş). Do not transliterate "
    "from Russian or English. Do not copy the source sentence structure "
    "when Turkmen idiom would differ. Prefer fluent native phrasing over "
    "literal renderings; respect Turkmen word order and politeness conventions."
)

RUSSIAN_TARGET_GUIDANCE = (
    "When the target is Russian: write fluent, natural Russian as a native "
    "speaker would. Translate the meaning, do not transliterate. Avoid "
    "wooden machine-translation phrasing."
)

ENGLISH_TARGET_GUIDANCE = (
    "When the target is English: write fluent, natural English as a native "
    "speaker would. Avoid awkward calques from the source language."
)

TURKISH_TARGET_GUIDANCE = (
    "When the target is Turkish: write fluent, natural Turkish as a native "
    "speaker would; respect Turkish vowel harmony and politeness conventions."
)


# ---------------------------------------------------------------------------
# Resolution helpers
# ---------------------------------------------------------------------------


def get_style(value: Optional[str]) -> StyleProfile:
    if not value:
        return STYLE_PROFILES[TranslationStyle.NATURAL]
    try:
        return STYLE_PROFILES[TranslationStyle(value.lower())]
    except (ValueError, KeyError):
        return STYLE_PROFILES[TranslationStyle.NATURAL]


def get_tone(value: Optional[str]) -> Optional[ToneProfile]:
    if not value:
        return None
    try:
        return TONE_PROFILES[DeliveryTone(value.lower())]
    except (ValueError, KeyError):
        return None


def get_emotion(value: Optional[str]) -> Optional[EmotionProfile]:
    if not value:
        return None
    try:
        return EMOTION_PROFILES[Emotion(value.lower())]
    except (ValueError, KeyError):
        return None


def list_styles() -> List[StyleProfile]:
    return list(STYLE_PROFILES.values())


def list_tones() -> List[ToneProfile]:
    return list(TONE_PROFILES.values())


def list_emotions() -> List[EmotionProfile]:
    return list(EMOTION_PROFILES.values())


def build_prompt_hint(
    style: StyleProfile,
    target_lang: str,
    *,
    tone: Optional[ToneProfile] = None,
    emotion: Optional[EmotionProfile] = None,
) -> str:
    """Compose style + tone + emotion + per-language guidance into one block."""
    chunks: List[str] = [style.prompt_hint]
    if tone is not None:
        chunks.append(f"Delivery tone: {tone.prompt_hint}")
    if emotion is not None and emotion.emotion is not Emotion.NEUTRAL:
        chunks.append(f"Emotion: {emotion.prompt_hint}")
    if target_lang == "tk":
        chunks.append(TURKMEN_TARGET_GUIDANCE)
    elif target_lang == "ru":
        chunks.append(RUSSIAN_TARGET_GUIDANCE)
    elif target_lang == "en":
        chunks.append(ENGLISH_TARGET_GUIDANCE)
    elif target_lang == "tr":
        chunks.append(TURKISH_TARGET_GUIDANCE)
    return " ".join(chunks)


__all__ = [
    "DeliveryTone",
    "EMOTION_PROFILES",
    "Emotion",
    "EmotionProfile",
    "STYLE_PROFILES",
    "StyleProfile",
    "TONE_PROFILES",
    "ToneProfile",
    "TURKMEN_TARGET_GUIDANCE",
    "TranslationStyle",
    "build_prompt_hint",
    "get_emotion",
    "get_style",
    "get_tone",
    "list_emotions",
    "list_styles",
    "list_tones",
]
