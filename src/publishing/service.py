"""Service that builds, mutates and exports publishing packages."""

from __future__ import annotations

import logging
import shutil
import uuid
from pathlib import Path
from typing import List, Optional

from ..storage.repositories import (
    PublishingPackageDTO,
    PublishingRepository,
)
from .models import PublishStatus, normalize_platforms

logger = logging.getLogger(__name__)


INBOX_DIR = Path("data/publishing_inbox")
ALLOWED_VIDEO_SUFFIXES = {".mp4", ".mkv", ".mov", ".webm", ".m4v"}
ALLOWED_AUDIO_SUFFIXES = {".wav", ".mp3", ".m4a", ".ogg", ".flac"}
MAX_MEDIA_BYTES = 500 * 1024 * 1024  # 500 MB cap on packaged media


class PublishingError(RuntimeError):
    """Generic publishing failure that is safe to surface to the user."""


class PublishingService:
    def __init__(
        self,
        repository: PublishingRepository,
        *,
        inbox_dir: Path = INBOX_DIR,
    ) -> None:
        self.repository = repository
        self.inbox_dir = inbox_dir
        self.inbox_dir.mkdir(parents=True, exist_ok=True)

    # -- media handling ---------------------------------------------------

    def save_media(
        self,
        *,
        content: bytes,
        filename: str,
        kind: str,
    ) -> Path:
        if not content:
            raise PublishingError("media file is empty")
        if len(content) > MAX_MEDIA_BYTES:
            raise PublishingError(
                f"media is too large ({len(content)} bytes > {MAX_MEDIA_BYTES})"
            )
        suffix = Path(filename).suffix.lower() or (
            ".mp4" if kind == "video" else ".wav"
        )
        allowed = (
            ALLOWED_VIDEO_SUFFIXES if kind == "video" else ALLOWED_AUDIO_SUFFIXES
        )
        if suffix not in allowed:
            raise PublishingError(
                f"unsupported {kind} format: {suffix!r}. allowed: {sorted(allowed)}"
            )
        target = self.inbox_dir / f"{uuid.uuid4().hex}{suffix}"
        target.write_bytes(content)
        return target

    def delete_media(self, path: Optional[str]) -> None:
        if not path:
            return
        target = Path(path)
        try:
            if target.is_file() and self._is_inside_inbox(target):
                target.unlink()
        except OSError:
            logger.warning("failed to delete media file %s", target)

    def _is_inside_inbox(self, target: Path) -> bool:
        try:
            target.resolve().relative_to(self.inbox_dir.resolve())
            return True
        except ValueError:
            return False

    # -- CRUD façade ------------------------------------------------------

    def create(
        self,
        *,
        name: str,
        title: str,
        kind: str = "video",
        language: str = "ru",
        channel_id: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        hashtags: Optional[List[str]] = None,
        target_platforms: Optional[List[str]] = None,
        media_bytes: Optional[bytes] = None,
        media_filename: Optional[str] = None,
    ) -> PublishingPackageDTO:
        media_path: Optional[str] = None
        stored_filename: Optional[str] = None
        if media_bytes:
            saved = self.save_media(
                content=media_bytes,
                filename=media_filename or ("media.mp4" if kind == "video" else "media.wav"),
                kind=kind,
            )
            media_path = str(saved)
            stored_filename = media_filename
        try:
            return self.repository.create(
                name=name,
                title=title,
                kind=kind,
                language=language,
                channel_id=channel_id,
                description=description,
                tags=tags,
                hashtags=hashtags,
                target_platforms=normalize_platforms(target_platforms or []),
                media_path=media_path,
                media_filename=stored_filename,
                status=PublishStatus.DRAFT.value,
            )
        except Exception:
            if media_path:
                self.delete_media(media_path)
            raise

    def update(
        self,
        package_id: str,
        *,
        target_platforms: Optional[List[str]] = None,
        **kwargs,
    ) -> Optional[PublishingPackageDTO]:
        if target_platforms is not None:
            kwargs["target_platforms"] = normalize_platforms(target_platforms)
        return self.repository.update(package_id, **kwargs)

    def replace_media(
        self,
        package_id: str,
        *,
        content: bytes,
        filename: str,
    ) -> Optional[PublishingPackageDTO]:
        package = self.repository.get(package_id)
        if package is None:
            return None
        saved = self.save_media(content=content, filename=filename, kind=package.kind)
        if package.media_path:
            self.delete_media(package.media_path)
        return self.repository.update(
            package_id,
            media_path=str(saved),
            media_filename=filename,
        )

    def delete(self, package_id: str) -> bool:
        package = self.repository.get(package_id)
        if package is None:
            return False
        self.repository.delete(package_id)
        self.delete_media(package.media_path)
        return True

    def mark_published(self, package_id: str) -> Optional[PublishingPackageDTO]:
        return self.repository.update(package_id, status=PublishStatus.PUBLISHED.value)

    def mark_exported(self, package_id: str) -> Optional[PublishingPackageDTO]:
        return self.repository.update(package_id, status=PublishStatus.EXPORTED.value)


__all__ = [
    "ALLOWED_AUDIO_SUFFIXES",
    "ALLOWED_VIDEO_SUFFIXES",
    "INBOX_DIR",
    "MAX_MEDIA_BYTES",
    "PublishingError",
    "PublishingService",
]
