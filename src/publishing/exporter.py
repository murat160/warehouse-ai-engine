"""ZIP-builder for finished publishing packages.

Produces a self-contained archive with the media file plus a ``metadata.json``
and platform-specific ``ready_for_<platform>.txt`` snippets the user can
paste into the upload form on each platform.
"""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path
from typing import Optional

from ..storage.repositories import PublishingPackageDTO
from .models import PLATFORM_REGISTRY, Platform


def _ready_text(package: PublishingPackageDTO, platform: Platform) -> str:
    """Build a copy-pasteable upload draft for a single platform."""
    lines: list[str] = [f"--- {package.title} ---", ""]
    if package.description:
        lines.append(package.description)
        lines.append("")
    if package.tags:
        if platform in {Platform.YOUTUBE}:
            lines.append("Tags: " + ", ".join(package.tags))
        else:
            lines.append("Tags: " + " ".join(package.tags))
        lines.append("")
    if package.hashtags:
        # Platforms that primarily use hashtags
        normalised = [h if h.startswith("#") else f"#{h}" for h in package.hashtags]
        lines.append(" ".join(normalised))
        lines.append("")
    descriptor = PLATFORM_REGISTRY[platform]
    lines.append(f"Upload page: {descriptor.upload_url}")
    return "\n".join(lines).strip() + "\n"


def build_zip_for_package(
    package: PublishingPackageDTO,
    *,
    media_path: Optional[Path] = None,
) -> bytes:
    """Return raw bytes of a ZIP archive describing the package."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1) media file (if present and on disk)
        if media_path is None and package.media_path:
            media_path = Path(package.media_path)
        if media_path and Path(media_path).is_file():
            arcname = package.media_filename or Path(media_path).name
            zf.write(media_path, arcname=f"media/{arcname}")

        # 2) metadata.json — full structured form
        metadata = {
            "id": package.id,
            "name": package.name,
            "kind": package.kind,
            "language": package.language,
            "title": package.title,
            "description": package.description,
            "tags": package.tags,
            "hashtags": package.hashtags,
            "target_platforms": package.target_platforms,
            "channel_id": package.channel_id,
            "status": package.status,
            "created_at": package.created_at,
            "updated_at": package.updated_at,
        }
        zf.writestr(
            "metadata.json", json.dumps(metadata, ensure_ascii=False, indent=2)
        )

        # 3) per-platform ready text
        for code in package.target_platforms:
            try:
                platform = Platform(code)
            except ValueError:
                continue
            zf.writestr(f"ready_for_{platform.value}.txt", _ready_text(package, platform))

        # 4) general README
        readme = (
            f"Package: {package.name}\n"
            f"Title:   {package.title}\n"
            f"Kind:    {package.kind}\n"
            f"Lang:    {package.language}\n\n"
            "Use the per-platform .txt files for ready-to-paste descriptions, "
            "or open metadata.json from any tool.\n"
        )
        zf.writestr("README.txt", readme)

    return buf.getvalue()


__all__ = ["build_zip_for_package"]
