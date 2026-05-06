"""Persistent storage for user glossary and translation memory.

Defaults to a local SQLite file, but the SQLAlchemy ORM layer means switching
to PostgreSQL only requires changing ``DATABASE_URL``.
"""

from .db import Base, init_db, session_scope
from .models import GlossaryEntry, TranslationMemoryEntry
from .repositories import GlossaryRepository, TranslationMemoryRepository

__all__ = [
    "Base",
    "GlossaryEntry",
    "GlossaryRepository",
    "TranslationMemoryEntry",
    "TranslationMemoryRepository",
    "init_db",
    "session_scope",
]
