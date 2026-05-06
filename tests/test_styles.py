"""Translation styles, delivery tones and emotions."""

from __future__ import annotations

from src.translator.styles import (
    EMOTION_PROFILES,
    STYLE_PROFILES,
    TONE_PROFILES,
    TURKMEN_TARGET_GUIDANCE,
    DeliveryTone,
    Emotion,
    TranslationStyle,
    build_prompt_hint,
    get_emotion,
    get_style,
    get_tone,
    list_emotions,
    list_styles,
    list_tones,
)


def test_15_styles_exist_and_default_is_natural():
    assert len(list_styles()) == 15
    expected = {
        "natural", "blogger", "conversational", "street", "literary",
        "formal", "news", "cultural", "expressive", "dramatic",
        "children", "teen", "humorous", "advertising", "expert",
    }
    assert {s.code for s in list_styles()} == expected
    assert get_style(None).style is TranslationStyle.NATURAL
    assert get_style("").style is TranslationStyle.NATURAL


def test_natural_is_not_literary():
    assert TranslationStyle.NATURAL.value == "natural"
    assert get_style("natural").style is not TranslationStyle.LITERARY


def test_get_style_falls_back_to_natural_on_unknown():
    assert get_style("does-not-exist").style is TranslationStyle.NATURAL
    assert get_style("LITERARY").style is TranslationStyle.LITERARY


def test_16_tones_exist():
    assert len(list_tones()) == 16
    expected = {
        "calm", "confident", "friendly", "warm", "serious", "cheerful",
        "energetic", "respectful", "soft", "firm", "cultural", "modern",
        "traditional", "simple", "deep", "emotional",
    }
    assert {t.code for t in list_tones()} == expected


def test_get_tone_returns_none_on_unknown():
    assert get_tone("xyz") is None
    assert get_tone(None) is None
    assert get_tone("calm").tone is DeliveryTone.CALM


def test_7_emotions_exist():
    assert len(list_emotions()) == 7
    expected = {"neutral", "happy", "sad", "serious", "excited", "respectful", "warm"}
    assert {e.code for e in list_emotions()} == expected


def test_prompt_hint_includes_turkmen_guidance_for_tk_target():
    hint = build_prompt_hint(get_style("cultural"), "tk")
    assert TURKMEN_TARGET_GUIDANCE in hint


def test_prompt_hint_does_not_inject_turkmen_for_other_targets():
    hint = build_prompt_hint(get_style("cultural"), "en")
    assert TURKMEN_TARGET_GUIDANCE not in hint


def test_prompt_hint_combines_style_tone_emotion():
    style = get_style("blogger")
    tone = get_tone("energetic")
    emotion = get_emotion("excited")
    hint = build_prompt_hint(style, "ru", tone=tone, emotion=emotion)
    assert "blogger" not in hint  # we expose only natural-language hints, not codes
    assert "Delivery tone" in hint
    assert "Emotion" in hint
    # Russian-target guidance is appended.
    assert "Russian" in hint or "русски" in hint.lower() or "natural" in hint.lower()


def test_neutral_emotion_is_not_appended():
    hint = build_prompt_hint(
        get_style("natural"), "en",
        emotion=get_emotion("neutral"),
    )
    assert "Emotion" not in hint


def test_each_style_has_label_and_description():
    for profile in STYLE_PROFILES.values():
        assert profile.label_ru
        assert profile.label_en
        assert profile.description
        assert profile.prompt_hint


def test_each_tone_has_label_and_hint():
    for profile in TONE_PROFILES.values():
        assert profile.label_ru
        assert profile.label_en
        assert profile.prompt_hint


def test_each_emotion_has_label():
    for profile in EMOTION_PROFILES.values():
        assert profile.label_ru
        assert profile.label_en
