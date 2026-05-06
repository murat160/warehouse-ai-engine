"""Custom Voice repository + service: consent, CRUD, variants, bindings."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.storage.repositories import (
    ConsentRequiredError,
    CustomVoiceRepository,
)
from src.voices.custom_voices import CustomVoiceError, CustomVoiceService


@pytest.fixture
def voice_repo(isolated_db) -> CustomVoiceRepository:
    return CustomVoiceRepository()


@pytest.fixture
def voice_service(voice_repo, tmp_path) -> CustomVoiceService:
    return CustomVoiceService(voice_repo, sample_dir=tmp_path / "voices")


# ---------------------------------------------------------------------------
# Consent
# ---------------------------------------------------------------------------


def test_create_without_consent_is_rejected(voice_repo):
    with pytest.raises(ConsentRequiredError):
        voice_repo.create(name="Мой голос", consent_given=False)


def test_create_with_consent_records_timestamp_and_text(voice_repo):
    voice = voice_repo.create(name="Мой голос", consent_given=True)
    assert voice.consent_given is True
    assert voice.consent_text and "право" in voice.consent_text
    assert voice.consent_at is not None


def test_service_create_without_consent_is_rejected(voice_service):
    with pytest.raises(ConsentRequiredError):
        voice_service.create(name="Мой голос", consent_given=False)


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


def test_create_then_get_with_settings(voice_repo):
    voice = voice_repo.create(
        name="Мой голос — блогерский",
        consent_given=True,
        language="ru",
        speed="fast",
        pitch="normal",
        emotion="energetic",
        clarity="enhanced",
        intensity="strong",
        use_case="blog",
    )
    fetched = voice_repo.get(voice.id)
    assert fetched is not None
    assert fetched.speed == "fast"
    assert fetched.emotion == "energetic"
    assert fetched.clarity == "enhanced"
    assert fetched.intensity == "strong"
    assert fetched.use_case == "blog"


def test_update_only_changes_provided_fields(voice_repo):
    voice = voice_repo.create(name="V1", consent_given=True, emotion="neutral")
    updated = voice_repo.update(voice.id, emotion="warm", intensity="strong")
    assert updated.emotion == "warm"
    assert updated.intensity == "strong"
    assert updated.speed == "normal"  # untouched


def test_delete_removes_row(voice_repo):
    voice = voice_repo.create(name="V1", consent_given=True)
    assert voice_repo.delete(voice.id) is True
    assert voice_repo.get(voice.id) is None
    assert voice_repo.delete(voice.id) is False


# ---------------------------------------------------------------------------
# Variants (parent_id chain)
# ---------------------------------------------------------------------------


def test_variant_chain(voice_repo):
    parent = voice_repo.create(name="Мой голос", consent_given=True)
    blogger = voice_repo.create(
        name="Мой голос — блогерский",
        consent_given=True,
        parent_id=parent.id,
        emotion="energetic",
        use_case="blog",
    )
    news = voice_repo.create(
        name="Мой голос — новостной",
        consent_given=True,
        parent_id=parent.id,
        emotion="serious",
        use_case="news",
    )
    variants = voice_repo.variants_of(parent.id)
    ids = {v.id for v in variants}
    assert blogger.id in ids and news.id in ids
    assert all(v.parent_id == parent.id for v in variants)


# ---------------------------------------------------------------------------
# Bindings (channel / style / video use case)
# ---------------------------------------------------------------------------


def test_bindings_persist(voice_repo):
    voice = voice_repo.create(
        name="Мой голос — туркменская озвучка",
        consent_given=True,
        language="tk",
        bound_style="cultural",
        bound_video_use_case="film",
    )
    assert voice.language == "tk"
    assert voice.bound_style == "cultural"
    assert voice.bound_video_use_case == "film"


# ---------------------------------------------------------------------------
# Sample handling — files live in tmp_path, never in the repo.
# ---------------------------------------------------------------------------


def test_save_and_delete_sample(voice_service, tmp_path):
    target = voice_service.save_sample(content=b"RIFFfake", filename="clip.wav")
    assert target.exists()
    assert target.parent == (tmp_path / "voices")
    voice_service.delete_sample(str(target))
    assert not target.exists()


def test_reject_unsupported_audio_format(voice_service):
    with pytest.raises(CustomVoiceError):
        voice_service.save_sample(content=b"x", filename="note.txt")


def test_reject_oversized_sample(voice_service):
    huge = b"x" * (26 * 1024 * 1024)
    with pytest.raises(CustomVoiceError):
        voice_service.save_sample(content=huge, filename="big.wav")


def test_service_create_with_sample(voice_service, tmp_path):
    voice = voice_service.create(
        name="V with audio",
        consent_given=True,
        sample_bytes=b"RIFFfake",
        sample_filename="me.wav",
    )
    assert voice.sample_path
    assert Path(voice.sample_path).exists()


def test_service_delete_removes_audio_file(voice_service):
    voice = voice_service.create(
        name="Cleanup",
        consent_given=True,
        sample_bytes=b"RIFFfake",
        sample_filename="me.wav",
    )
    sample = Path(voice.sample_path)
    assert sample.exists()
    voice_service.delete(voice.id)
    assert not sample.exists()


# ---------------------------------------------------------------------------
# Closest catalog voice (preview fallback)
# ---------------------------------------------------------------------------


def test_closest_catalog_voice_for_turkmen(voice_service, voice_repo):
    voice = voice_repo.create(
        name="Туркменский голос",
        consent_given=True,
        language="tk",
    )
    closest = voice_service.closest_catalog_voice(voice)
    assert closest is not None
    assert "tk" in closest.languages


def test_closest_catalog_voice_for_russian_blog(voice_service, voice_repo):
    voice = voice_repo.create(
        name="Блогерский ру",
        consent_given=True,
        language="ru",
        emotion="energetic",
        speed="fast",
    )
    closest = voice_service.closest_catalog_voice(voice)
    assert closest is not None
    assert "ru" in closest.languages
