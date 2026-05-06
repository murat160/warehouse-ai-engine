"""Persistent storage for user glossary and translation memory.

Defaults to a local SQLite file, but the SQLAlchemy ORM layer means switching
to PostgreSQL only requires changing ``DATABASE_URL``.
"""

from .db import Base, init_db, session_scope
from .models import (
    Channel,
    CustomVoiceProfile,
    GlossaryEntry,
    PublishingPackage,
    TranslationMemoryEntry,
)
from .repositories import (
    ChannelRepository,
    CustomVoiceRepository,
    GlossaryRepository,
    PublishingRepository,
    TranslationMemoryRepository,
)

__all__ = [
    "Base",
    "Channel",
    "ChannelRepository",
    "CustomVoiceProfile",
    "CustomVoiceRepository",
    "GlossaryEntry",
    "GlossaryRepository",
    "PublishingPackage",
    "PublishingRepository",
    "TranslationMemoryEntry",
    "TranslationMemoryRepository",
    "init_db",
    "session_scope",
]
