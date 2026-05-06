"""Translation style enum + prompt assembly."""

from __future__ import annotations

from src.translator.styles import (
    STYLE_PROFILES,
    TURKMEN_TARGET_GUIDANCE,
    TranslationStyle,
    build_prompt_hint,
    get_style,
    list_styles,
)


def test_all_required_styles_exist():
    expected = {
        "neutral", "respectful", "warm", "formal",
        "friendly", "expressive", "literary", "casual",
    }
    assert {s.code for s in list_styles()} == expected


def test_get_style_falls_back_to_neutral():
    assert get_style(None).style is TranslationStyle.NEUTRAL
    assert get_style("").style is TranslationStyle.NEUTRAL
    assert get_style("does-not-exist").style is TranslationStyle.NEUTRAL


def test_get_style_is_case_insensitive():
    assert get_style("LITERARY").style is TranslationStyle.LITERARY
    assert get_style("Friendly").style is TranslationStyle.FRIENDLY


def test_prompt_hint_includes_turkmen_guidance_for_tk_target():
    profile = get_style("respectful")
    hint = build_prompt_hint(profile, "tk")
    assert "Siz" in hint  # respectful clue
    assert TURKMEN_TARGET_GUIDANCE in hint


def test_prompt_hint_does_not_inject_turkmen_for_other_targets():
    hint = build_prompt_hint(get_style("respectful"), "en")
    assert TURKMEN_TARGET_GUIDANCE not in hint


def test_each_profile_has_label_and_description():
    for profile in STYLE_PROFILES.values():
        assert profile.label_ru
        assert profile.label_en
        assert profile.description
        assert profile.prompt_hint
