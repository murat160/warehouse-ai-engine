"""Built-in catalog of 23 voice profiles.

Profiles are deliberately simple — each names a ``backend_voice`` from the
underlying provider (currently OpenAI ``tts-1``: ``alloy``, ``echo``,
``fable``, ``onyx``, ``nova``, ``shimmer``) plus pitch/speed/tone metadata
the TTS layer can apply.

Turkmen profiles route to the offline Meta MMS-TTS provider (``provider=mms``)
because cloud multilingual voices currently render Turkmen poorly. MMS exposes
a single voice, so the per-profile distinctions for tk are reflected through
speed/pitch and the prompt-level emotion hint on translation.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from .models import (
    AgeStyle,
    Gender,
    PitchPreset,
    SpeedPreset,
    UseCase,
    VoiceProfile,
    VoiceTone,
)


_ALL_LANGS = ("ru", "tk", "tr", "en")
_NON_TK = ("ru", "tr", "en")


VOICE_CATALOG: Dict[str, VoiceProfile] = {
    p.id: p
    for p in [
        # 1. Generic male / female / child / teen — full coverage ----------
        VoiceProfile(
            id="male_neutral",
            label_ru="Мужской голос",
            label_en="Male voice",
            description="Базовый мужской голос для общего использования.",
            gender=Gender.MALE,
            age_style=AgeStyle.ADULT,
            tone=VoiceTone.CALM,
            languages=_NON_TK,
            provider="openai",
            backend_voice="onyx",
        ),
        VoiceProfile(
            id="female_neutral",
            label_ru="Женский голос",
            label_en="Female voice",
            description="Базовый женский голос для общего использования.",
            gender=Gender.FEMALE,
            age_style=AgeStyle.ADULT,
            tone=VoiceTone.CALM,
            languages=_NON_TK,
            provider="openai",
            backend_voice="nova",
        ),
        VoiceProfile(
            id="child_voice",
            label_ru="Детский голос",
            label_en="Child voice",
            description="Лёгкий, мягкий — для детских сюжетов и сказок.",
            gender=Gender.CHILD,
            age_style=AgeStyle.CHILD,
            tone=VoiceTone.WARM,
            languages=_NON_TK,
            speed=SpeedPreset.NORMAL,
            pitch=PitchPreset.HIGH,
            provider="openai",
            backend_voice="shimmer",
        ),
        VoiceProfile(
            id="teen_voice",
            label_ru="Подростковый голос",
            label_en="Teen voice",
            description="Молодой, неформальный — для молодёжного контента.",
            gender=Gender.TEEN,
            age_style=AgeStyle.TEEN,
            tone=VoiceTone.FRIENDLY,
            languages=_NON_TK,
            pitch=PitchPreset.HIGH,
            provider="openai",
            backend_voice="shimmer",
        ),

        # 5–8. Young / adult male & female ---------------------------------
        VoiceProfile(
            id="male_young",
            label_ru="Молодой мужской",
            label_en="Young male",
            description="Молодой энергичный мужской голос для блогов.",
            gender=Gender.MALE,
            age_style=AgeStyle.YOUNG_ADULT,
            tone=VoiceTone.ENERGETIC,
            languages=_NON_TK,
            provider="openai",
            backend_voice="echo",
        ),
        VoiceProfile(
            id="female_young",
            label_ru="Молодой женский",
            label_en="Young female",
            description="Молодой женский голос для блогов и storytelling.",
            gender=Gender.FEMALE,
            age_style=AgeStyle.YOUNG_ADULT,
            tone=VoiceTone.FRIENDLY,
            languages=_NON_TK,
            provider="openai",
            backend_voice="shimmer",
        ),
        VoiceProfile(
            id="male_adult",
            label_ru="Взрослый мужской",
            label_en="Adult male",
            description="Взрослый, уверенный — для новостей и официальной речи.",
            gender=Gender.MALE,
            age_style=AgeStyle.ADULT,
            tone=VoiceTone.SERIOUS,
            languages=_NON_TK,
            provider="openai",
            backend_voice="onyx",
        ),
        VoiceProfile(
            id="female_adult",
            label_ru="Взрослый женский",
            label_en="Adult female",
            description="Взрослый, спокойный женский — новостной/официальный.",
            gender=Gender.FEMALE,
            age_style=AgeStyle.ADULT,
            tone=VoiceTone.OFFICIAL,
            languages=_NON_TK,
            provider="openai",
            backend_voice="nova",
        ),

        # 9–10. Senior ------------------------------------------------------
        VoiceProfile(
            id="male_senior",
            label_ru="Пожилой мужской",
            label_en="Senior male",
            description="Глубокий, размеренный — для культурного и драматичного контента.",
            gender=Gender.MALE,
            age_style=AgeStyle.SENIOR,
            tone=VoiceTone.DRAMATIC,
            languages=_NON_TK,
            speed=SpeedPreset.SLOW,
            pitch=PitchPreset.LOW,
            provider="openai",
            backend_voice="onyx",
        ),
        VoiceProfile(
            id="female_senior",
            label_ru="Пожилой женский",
            label_en="Senior female",
            description="Тёплый, культурный — для повествования и интервью.",
            gender=Gender.FEMALE,
            age_style=AgeStyle.SENIOR,
            tone=VoiceTone.WARM,
            languages=_NON_TK,
            speed=SpeedPreset.SLOW,
            provider="openai",
            backend_voice="nova",
        ),

        # 11–14. Tone-specialised voices -----------------------------------
        VoiceProfile(
            id="soft_voice",
            label_ru="Мягкий голос",
            label_en="Soft voice",
            description="Тихий, доверительный — для медитаций и storytelling.",
            gender=Gender.NEUTRAL,
            age_style=AgeStyle.ADULT,
            tone=VoiceTone.WARM,
            languages=_NON_TK,
            speed=SpeedPreset.SLOW,
            provider="openai",
            backend_voice="alloy",
        ),
        VoiceProfile(
            id="serious_voice",
            label_ru="Серьёзный голос",
            label_en="Serious voice",
            description="Жёсткий, уверенный — для эксперта и драмы.",
            gender=Gender.MALE,
            age_style=AgeStyle.ADULT,
            tone=VoiceTone.SERIOUS,
            languages=_NON_TK,
            pitch=PitchPreset.LOW,
            provider="openai",
            backend_voice="onyx",
        ),
        VoiceProfile(
            id="energetic_voice",
            label_ru="Энергичный голос",
            label_en="Energetic voice",
            description="Высокий темп — для рекламы и блогов.",
            gender=Gender.NEUTRAL,
            age_style=AgeStyle.YOUNG_ADULT,
            tone=VoiceTone.ENERGETIC,
            languages=_NON_TK,
            speed=SpeedPreset.FAST,
            provider="openai",
            backend_voice="fable",
        ),
        VoiceProfile(
            id="calm_voice",
            label_ru="Спокойный голос",
            label_en="Calm voice",
            description="Размеренный, для обучения и аудиокниг.",
            gender=Gender.NEUTRAL,
            age_style=AgeStyle.ADULT,
            tone=VoiceTone.CALM,
            languages=_NON_TK,
            speed=SpeedPreset.SLOW,
            provider="openai",
            backend_voice="alloy",
        ),

        # 15–20. Use-case specialised voices --------------------------------
        VoiceProfile(
            id="news_voice",
            label_ru="Новостной голос",
            label_en="News anchor",
            description="Голос ведущего новостей — чёткий, спокойный.",
            gender=Gender.NEUTRAL,
            age_style=AgeStyle.ADULT,
            tone=VoiceTone.OFFICIAL,
            languages=_NON_TK,
            provider="openai",
            backend_voice="onyx",
            use_cases=(UseCase.VIDEO, UseCase.AUDIO),
        ),
        VoiceProfile(
            id="blogger_voice",
            label_ru="Блогерский голос",
            label_en="Blogger",
            description="Живой, энергичный — для YouTube/TikTok/Reels.",
            gender=Gender.NEUTRAL,
            age_style=AgeStyle.YOUNG_ADULT,
            tone=VoiceTone.FRIENDLY,
            languages=_NON_TK,
            provider="openai",
            backend_voice="shimmer",
            use_cases=(UseCase.VIDEO, UseCase.AUDIO),
        ),
        VoiceProfile(
            id="street_voice",
            label_ru="Уличный / повседневный",
            label_en="Street / Casual",
            description="Молодёжный, неформальный.",
            gender=Gender.NEUTRAL,
            age_style=AgeStyle.YOUNG_ADULT,
            tone=VoiceTone.STREET,
            languages=_NON_TK,
            provider="openai",
            backend_voice="echo",
            use_cases=(UseCase.VIDEO, UseCase.AUDIO),
        ),
        VoiceProfile(
            id="education_voice",
            label_ru="Образовательный голос",
            label_en="Education / Expert",
            description="Уверенный, понятный — для обучения.",
            gender=Gender.NEUTRAL,
            age_style=AgeStyle.ADULT,
            tone=VoiceTone.CALM,
            languages=_NON_TK,
            provider="openai",
            backend_voice="alloy",
            use_cases=(UseCase.VIDEO, UseCase.AUDIO),
        ),
        VoiceProfile(
            id="advertising_voice",
            label_ru="Рекламный голос",
            label_en="Advertising",
            description="Яркий, продающий — для промо.",
            gender=Gender.NEUTRAL,
            age_style=AgeStyle.YOUNG_ADULT,
            tone=VoiceTone.ENERGETIC,
            languages=_NON_TK,
            speed=SpeedPreset.FAST,
            provider="openai",
            backend_voice="fable",
            use_cases=(UseCase.VIDEO, UseCase.AUDIO),
        ),
        VoiceProfile(
            id="dramatic_voice",
            label_ru="Драматичный голос",
            label_en="Dramatic",
            description="Кинематографичный — для дубляжа и историй.",
            gender=Gender.MALE,
            age_style=AgeStyle.ADULT,
            tone=VoiceTone.DRAMATIC,
            languages=_NON_TK,
            speed=SpeedPreset.SLOW,
            pitch=PitchPreset.LOW,
            provider="openai",
            backend_voice="onyx",
            use_cases=(UseCase.VIDEO, UseCase.DUBBING),
        ),

        # 21. Children storytelling -----------------------------------------
        VoiceProfile(
            id="child_storyteller",
            label_ru="Детский сказочный",
            label_en="Children's storyteller",
            description="Тёплый, повествовательный — для детских сказок.",
            gender=Gender.FEMALE,
            age_style=AgeStyle.ADULT,
            tone=VoiceTone.WARM,
            languages=_NON_TK,
            provider="openai",
            backend_voice="shimmer",
            default_emotion="warm",
        ),

        # 22–23. Turkmen voices via Meta MMS-TTS ----------------------------
        VoiceProfile(
            id="tk_cultural",
            label_ru="Культурный туркменский",
            label_en="Cultural Turkmen",
            description="Естественный туркменский голос для культурного контента.",
            gender=Gender.NEUTRAL,
            age_style=AgeStyle.ADULT,
            tone=VoiceTone.CULTURAL,
            languages=("tk",),
            provider="mms",
            backend_voice="facebook/mms-tts-tuk-script_latin",
            use_cases=(UseCase.TEXT, UseCase.VIDEO, UseCase.AUDIO, UseCase.DUBBING),
            notes="Single MMS voice; tone delivered via translation prompt.",
        ),
        VoiceProfile(
            id="natural_video_voice",
            label_ru="Обычный голос для видео",
            label_en="Natural video voice",
            description="Дефолтная естественная озвучка для видео.",
            gender=Gender.NEUTRAL,
            age_style=AgeStyle.ADULT,
            tone=VoiceTone.CALM,
            languages=_ALL_LANGS,
            provider="auto",
            backend_voice="alloy",
            use_cases=(UseCase.VIDEO, UseCase.AUDIO, UseCase.DUBBING),
            notes="Routes to MMS for tk and OpenAI for the rest.",
        ),
    ]
}


def list_voices() -> List[VoiceProfile]:
    return list(VOICE_CATALOG.values())


def get_voice(voice_id: Optional[str]) -> Optional[VoiceProfile]:
    if not voice_id:
        return None
    return VOICE_CATALOG.get(voice_id)


def voices_for_language(code: str) -> List[VoiceProfile]:
    return [v for v in VOICE_CATALOG.values() if v.supports_language(code)]


def voices_for_use_case(use_case: UseCase) -> List[VoiceProfile]:
    return [v for v in VOICE_CATALOG.values() if use_case in v.use_cases]


__all__ = [
    "VOICE_CATALOG",
    "get_voice",
    "list_voices",
    "voices_for_language",
    "voices_for_use_case",
]
