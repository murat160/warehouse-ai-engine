"""Built-in voice catalog."""

from __future__ import annotations

from src.voices import (
    UseCase,
    VOICE_CATALOG,
    get_voice,
    list_voices,
    voices_for_language,
    voices_for_use_case,
)


def test_catalog_has_23_voices():
    assert len(list_voices()) == 23
    assert len(VOICE_CATALOG) == 23


def test_each_voice_has_required_metadata():
    for voice in list_voices():
        assert voice.id
        assert voice.label_ru and voice.label_en
        assert voice.description
        assert voice.gender
        assert voice.age_style
        assert voice.tone
        assert voice.languages
        assert voice.speed and voice.pitch
        assert voice.use_cases


def test_get_voice_returns_none_for_unknown_id():
    assert get_voice("does-not-exist") is None
    assert get_voice(None) is None


def test_voices_for_language_filters():
    tk = voices_for_language("tk")
    assert tk, "expected at least one Turkmen voice"
    for voice in tk:
        assert "tk" in voice.languages

    en = voices_for_language("en")
    assert any(v.languages == ("ru", "tk", "tr", "en") or "en" in v.languages for v in en)


def test_voices_for_use_case():
    dub = voices_for_use_case(UseCase.DUBBING)
    assert any(v.id == "dramatic_voice" for v in dub)
    video = voices_for_use_case(UseCase.VIDEO)
    assert len(video) >= 10


def test_turkmen_cultural_voice_uses_mms():
    tk_cultural = get_voice("tk_cultural")
    assert tk_cultural is not None
    assert tk_cultural.provider == "mms"
    assert "tk" in tk_cultural.languages


def test_to_public_dict_serialises_enums_as_strings():
    voice = get_voice("male_neutral")
    d = voice.to_public_dict()
    assert d["gender"] == "male"
    assert d["age_style"] == "adult"
    assert isinstance(d["use_cases"], list)
    assert all(isinstance(uc, str) for uc in d["use_cases"])
