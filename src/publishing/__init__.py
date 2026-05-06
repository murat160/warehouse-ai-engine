"""Publishing module: package media + metadata for external platforms.

The package holds a thin scaffold: a registry of supported platforms,
a service that builds publishable packages (media file + metadata JSON +
platform-specific upload URL), and a ZIP exporter. Direct OAuth uploads to
YouTube / TikTok / Instagram / Facebook require the operator's own API
credentials and are documented in ``docs/publishing.md`` — when those are
configured, the matching ``Uploader`` plugs into ``service.publish``.
"""

from .exporter import build_zip_for_package
from .models import (
    PLATFORM_REGISTRY,
    Platform,
    PlatformDescriptor,
)
from .service import PublishingService

__all__ = [
    "PLATFORM_REGISTRY",
    "Platform",
    "PlatformDescriptor",
    "PublishingService",
    "build_zip_for_package",
]
