"""Publishing repository + service + ZIP export."""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import pytest

from src.publishing import PublishingService, build_zip_for_package
from src.publishing.models import (
    PLATFORM_REGISTRY,
    Platform,
    list_platforms,
    normalize_platforms,
)
from src.storage.repositories import PublishingRepository


@pytest.fixture
def publish_repo(isolated_db) -> PublishingRepository:
    return PublishingRepository()


@pytest.fixture
def publish_service(publish_repo, tmp_path) -> PublishingService:
    return PublishingService(publish_repo, inbox_dir=tmp_path / "publishing")


# ---------------------------------------------------------------------------
# Platform registry
# ---------------------------------------------------------------------------


def test_registry_covers_required_platforms():
    codes = {p.platform.value for p in list_platforms()}
    for required in {"youtube", "tiktok", "instagram", "facebook", "telegram", "x"}:
        assert required in codes


def test_normalize_platforms_dedups_and_lowercases():
    out = normalize_platforms(["YouTube", "youtube", "TikTok", "garbage", ""])
    assert out == ["youtube", "tiktok"]


def test_normalize_platforms_handles_none():
    assert normalize_platforms([]) == []


# ---------------------------------------------------------------------------
# Repository CRUD
# ---------------------------------------------------------------------------


def test_create_with_metadata(publish_repo):
    pkg = publish_repo.create(
        name="Видео блога #1",
        title="Привет, мир",
        kind="video",
        language="ru",
        description="Короткий тест",
        tags=["test", "blog"],
        hashtags=["#hi", "#bye"],
        target_platforms=["youtube", "tiktok"],
    )
    assert pkg.id
    assert pkg.tags == ["test", "blog"]
    assert pkg.hashtags == ["#hi", "#bye"]
    assert pkg.target_platforms == ["youtube", "tiktok"]
    assert pkg.status == "draft"


def test_list_filters_by_platform(publish_repo):
    publish_repo.create(name="A", title="A", target_platforms=["youtube"])
    publish_repo.create(name="B", title="B", target_platforms=["tiktok"])
    yt = publish_repo.list(platform="youtube")
    assert len(yt) == 1 and yt[0].name == "A"


def test_update_changes_only_provided_fields(publish_repo):
    pkg = publish_repo.create(name="Pkg", title="t1", description="old")
    updated = publish_repo.update(pkg.id, title="t2", tags=["x"])
    assert updated.title == "t2"
    assert updated.tags == ["x"]
    assert updated.description == "old"


def test_delete(publish_repo):
    pkg = publish_repo.create(name="Pkg", title="t")
    assert publish_repo.delete(pkg.id) is True
    assert publish_repo.get(pkg.id) is None
    assert publish_repo.delete(pkg.id) is False


# ---------------------------------------------------------------------------
# Service: media handling
# ---------------------------------------------------------------------------


def test_save_and_delete_media(publish_service):
    saved = publish_service.save_media(
        content=b"\x00\x00", filename="clip.mp4", kind="video",
    )
    assert saved.exists()
    publish_service.delete_media(str(saved))
    assert not saved.exists()


def test_reject_unsupported_media(publish_service):
    from src.publishing.service import PublishingError

    with pytest.raises(PublishingError):
        publish_service.save_media(content=b"x", filename="note.txt", kind="video")


def test_create_with_media_then_delete_removes_file(publish_service):
    pkg = publish_service.create(
        name="With media",
        title="t",
        kind="video",
        media_bytes=b"\x00",
        media_filename="clip.mp4",
    )
    assert pkg.media_path
    assert Path(pkg.media_path).exists()
    publish_service.delete(pkg.id)
    assert not Path(pkg.media_path).exists()


def test_replace_media_swaps_files(publish_service):
    pkg = publish_service.create(
        name="r", title="t", kind="audio",
        media_bytes=b"\x00", media_filename="a.wav",
    )
    first = Path(pkg.media_path)
    updated = publish_service.replace_media(
        pkg.id, content=b"\x00\x01", filename="b.wav",
    )
    assert updated.media_path != str(first)
    assert Path(updated.media_path).exists()
    assert not first.exists()


# ---------------------------------------------------------------------------
# ZIP export
# ---------------------------------------------------------------------------


def test_zip_contains_metadata_and_per_platform_text(publish_repo):
    pkg = publish_repo.create(
        name="N", title="My Title",
        description="Hello",
        tags=["a", "b"], hashtags=["x", "y"],
        target_platforms=["youtube", "tiktok"],
    )
    archive = build_zip_for_package(pkg)
    with zipfile.ZipFile(io.BytesIO(archive)) as zf:
        names = set(zf.namelist())
        assert "metadata.json" in names
        assert "ready_for_youtube.txt" in names
        assert "ready_for_tiktok.txt" in names
        assert "README.txt" in names

        meta = json.loads(zf.read("metadata.json").decode("utf-8"))
        assert meta["title"] == "My Title"
        assert meta["target_platforms"] == ["youtube", "tiktok"]
        assert meta["tags"] == ["a", "b"]

        yt_text = zf.read("ready_for_youtube.txt").decode("utf-8")
        assert "My Title" in yt_text
        assert PLATFORM_REGISTRY[Platform.YOUTUBE].upload_url in yt_text


def test_zip_includes_media_when_file_exists(publish_service, publish_repo, tmp_path):
    pkg = publish_service.create(
        name="With media",
        title="t",
        kind="video",
        target_platforms=["youtube"],
        media_bytes=b"FAKEVIDEO",
        media_filename="clip.mp4",
    )
    refreshed = publish_repo.get(pkg.id)
    archive = build_zip_for_package(refreshed)
    with zipfile.ZipFile(io.BytesIO(archive)) as zf:
        media_files = [n for n in zf.namelist() if n.startswith("media/")]
        assert media_files, "expected media file inside the zip"
        assert zf.read(media_files[0]) == b"FAKEVIDEO"
