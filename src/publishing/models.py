"""Platform registry + DTOs for the publishing layer."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional


class Platform(str, Enum):
    """Where a finished package should land."""

    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    TELEGRAM = "telegram"
    X = "x"


class PublishStatus(str, Enum):
    DRAFT = "draft"
    EXPORTED = "exported"
    PUBLISHED = "published"


@dataclass(frozen=True)
class PlatformDescriptor:
    """Static metadata about a platform — used by the UI/API."""

    platform: Platform
    label: str
    upload_url: str
    icon: str
    notes: str

    def to_dict(self) -> dict:
        return {
            "code": self.platform.value,
            "label": self.label,
            "upload_url": self.upload_url,
            "icon": self.icon,
            "notes": self.notes,
        }


PLATFORM_REGISTRY: Dict[Platform, PlatformDescriptor] = {
    Platform.YOUTUBE: PlatformDescriptor(
        platform=Platform.YOUTUBE,
        label="YouTube",
        upload_url="https://studio.youtube.com/channel/UC/videos/upload",
        icon="📺",
        notes=(
            "Direct upload requires Google Cloud OAuth (YouTube Data API v3). "
            "Until configured, use Download ZIP and upload via YouTube Studio."
        ),
    ),
    Platform.TIKTOK: PlatformDescriptor(
        platform=Platform.TIKTOK,
        label="TikTok",
        upload_url="https://www.tiktok.com/upload",
        icon="🎵",
        notes=(
            "Direct upload requires the TikTok Content Posting API. "
            "Until configured, use Download ZIP and upload via tiktok.com/upload."
        ),
    ),
    Platform.INSTAGRAM: PlatformDescriptor(
        platform=Platform.INSTAGRAM,
        label="Instagram",
        upload_url="https://www.instagram.com/",
        icon="📸",
        notes=(
            "Direct upload requires the Instagram Graph API and a Business "
            "account linked to a Facebook Page (Meta for Developers)."
        ),
    ),
    Platform.FACEBOOK: PlatformDescriptor(
        platform=Platform.FACEBOOK,
        label="Facebook",
        upload_url="https://www.facebook.com/",
        icon="🌐",
        notes=(
            "Direct upload requires a Facebook Page Access Token via the "
            "Facebook Graph API."
        ),
    ),
    Platform.TELEGRAM: PlatformDescriptor(
        platform=Platform.TELEGRAM,
        label="Telegram",
        upload_url="https://web.telegram.org/",
        icon="✈️",
        notes=(
            "Direct upload requires a Telegram bot token and the Bot API "
            "(no OAuth needed). Until configured, use Download ZIP."
        ),
    ),
    Platform.X: PlatformDescriptor(
        platform=Platform.X,
        label="X (Twitter)",
        upload_url="https://x.com/compose/post",
        icon="✖️",
        notes=(
            "Direct posting requires the X v2 API + OAuth 2.0. "
            "Until configured, use Download ZIP and post manually."
        ),
    ),
}


def list_platforms() -> List[PlatformDescriptor]:
    return list(PLATFORM_REGISTRY.values())


def get_platform(code: str) -> Optional[PlatformDescriptor]:
    try:
        return PLATFORM_REGISTRY[Platform(code.lower())]
    except (KeyError, ValueError):
        return None


def normalize_platforms(values: List[str]) -> List[str]:
    """Canonicalise a list of platform codes (case-insensitive, dedup)."""
    seen: List[str] = []
    for value in values or []:
        if not value:
            continue
        try:
            code = Platform(value.lower()).value
        except ValueError:
            continue
        if code not in seen:
            seen.append(code)
    return seen


@dataclass(frozen=True)
class PublishingPackageDTO:
    id: str
    name: str
    kind: str  # "video" or "audio"
    language: str
    channel_id: Optional[str]
    title: str
    description: Optional[str]
    tags: List[str]
    hashtags: List[str]
    target_platforms: List[str]
    media_path: Optional[str]
    media_filename: Optional[str]
    status: str
    created_at: Optional[str]
    updated_at: Optional[str]


__all__ = [
    "PLATFORM_REGISTRY",
    "Platform",
    "PlatformDescriptor",
    "PublishStatus",
    "PublishingPackageDTO",
    "get_platform",
    "list_platforms",
    "normalize_platforms",
]
