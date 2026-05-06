"""i18n catalog completeness."""

from __future__ import annotations

from src.ui.i18n import (
    DEFAULT_UI_LANG,
    STRINGS,
    SUPPORTED_UI_LANGS,
    available_keys,
    t,
)


def test_supported_languages_are_exactly_four():
    assert SUPPORTED_UI_LANGS == ("ru", "tk", "tr", "en")
    assert DEFAULT_UI_LANG in SUPPORTED_UI_LANGS


def test_every_string_has_all_four_languages():
    missing = []
    for key, bundle in STRINGS.items():
        for lang in SUPPORTED_UI_LANGS:
            value = bundle.get(lang)
            if not value or not value.strip():
                missing.append(f"{key}/{lang}")
    assert not missing, f"missing translations: {missing[:10]}"


def test_t_returns_localised_string():
    # Sanity: a known key returns 4 different non-empty strings.
    seen = {t("translate_button", lang=lang) for lang in SUPPORTED_UI_LANGS}
    assert all(seen)
    # Russian / English variants must not be identical (different scripts).
    assert t("translate_button", lang="ru") != t("translate_button", lang="en")


def test_t_unknown_key_falls_back_to_key():
    assert t("does-not-exist-zzz", lang="ru") == "does-not-exist-zzz"


def test_available_keys_contains_core_chrome():
    keys = set(available_keys())
    for required in {
        "app_title", "app_subtitle",
        "tab_translate", "tab_media", "tab_dictionary",
        "tab_memory", "tab_channels", "tab_voices", "tab_publish",
        "translate_button", "translate_voice_button",
        "publish_heading", "publish_export",
    }:
        assert required in keys, f"missing key: {required}"
