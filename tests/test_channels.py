"""Channel repository CRUD + duplicate detection."""

from __future__ import annotations

import pytest

from src.storage.repositories import ChannelRepository, DuplicateEntryError


@pytest.fixture
def channel_repo(isolated_db) -> ChannelRepository:
    return ChannelRepository()


def test_create_then_get(channel_repo):
    channel = channel_repo.create(
        name="Блог",
        primary_lang="ru",
        target_lang="tk",
        style="blogger",
        tone="energetic",
        emotion="happy",
        voice_id="blogger_voice",
    )
    assert channel.id
    fetched = channel_repo.get(channel.id)
    assert fetched is not None
    assert fetched.name == "Блог"
    assert fetched.style == "blogger"
    assert fetched.voice_id == "blogger_voice"


def test_duplicate_name_rejected(channel_repo):
    channel_repo.create(name="Новости", style="news")
    with pytest.raises(DuplicateEntryError):
        channel_repo.create(name="Новости", style="news")


def test_update(channel_repo):
    channel = channel_repo.create(name="Улица", style="street")
    updated = channel_repo.update(
        channel.id, style="teen", tone="modern", voice_id="teen_voice"
    )
    assert updated.style == "teen"
    assert updated.tone == "modern"
    assert updated.voice_id == "teen_voice"


def test_delete(channel_repo):
    channel = channel_repo.create(name="Детский", style="children")
    assert channel_repo.delete(channel.id) is True
    assert channel_repo.get(channel.id) is None
    assert channel_repo.delete(channel.id) is False


def test_list_orders_recent_first(channel_repo):
    a = channel_repo.create(name="Канал A")
    b = channel_repo.create(name="Канал B")
    listed = channel_repo.list()
    ids = [c.id for c in listed]
    assert b.id in ids and a.id in ids
    # Most recently updated should appear first.
    assert ids.index(b.id) < ids.index(a.id)


def test_get_by_name(channel_repo):
    channel_repo.create(name="Эксперт", style="expert")
    found = channel_repo.get_by_name("Эксперт")
    assert found is not None and found.name == "Эксперт"
    assert channel_repo.get_by_name("Несуществующий") is None
