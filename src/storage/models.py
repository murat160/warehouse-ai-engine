"""ORM models for the user glossary and the translation memory."""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def _uuid() -> str:
    return uuid.uuid4().hex


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def normalize_for_match(text: str) -> str:
    """Normalise text for translation-memory exact lookup.

    The TM only uses this to detect when *the same input* was translated
    before — case, surrounding whitespace and trivial punctuation differences
    should not block a hit.
    """
    if not text:
        return ""
    collapsed = " ".join(text.strip().split())
    return collapsed.lower()


def hash_for_match(text: str) -> str:
    return hashlib.sha256(normalize_for_match(text).encode("utf-8")).hexdigest()


class GlossaryEntry(Base):
    """User-editable, per-pair word/phrase replacement."""

    __tablename__ = "glossary_entries"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    source_lang: Mapped[str] = mapped_column(String(8), index=True)
    target_lang: Mapped[str] = mapped_column(String(8), index=True)
    source_text: Mapped[str] = mapped_column(String(512))
    target_text: Mapped[str] = mapped_column(String(512))
    case_sensitive: Mapped[bool] = mapped_column(Boolean, default=False)
    whole_word: Mapped[bool] = mapped_column(Boolean, default=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow
    )

    __table_args__ = (
        Index(
            "ix_glossary_pair_source",
            "source_lang", "target_lang", "source_text",
        ),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source_lang": self.source_lang,
            "target_lang": self.target_lang,
            "source_text": self.source_text,
            "target_text": self.target_text,
            "case_sensitive": self.case_sensitive,
            "whole_word": self.whole_word,
            "note": self.note,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class TranslationMemoryEntry(Base):
    """Whole-segment translation memory (input → curated translation)."""

    __tablename__ = "translation_memory"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    source_lang: Mapped[str] = mapped_column(String(8), index=True)
    target_lang: Mapped[str] = mapped_column(String(8), index=True)
    source_text: Mapped[str] = mapped_column(Text)
    target_text: Mapped[str] = mapped_column(Text)
    source_hash: Mapped[str] = mapped_column(String(64), index=True)
    score: Mapped[float] = mapped_column(Float, default=1.0)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow
    )

    __table_args__ = (
        UniqueConstraint(
            "source_lang", "target_lang", "source_hash",
            name="uq_tm_pair_hash",
        ),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source_lang": self.source_lang,
            "target_lang": self.target_lang,
            "source_text": self.source_text,
            "target_text": self.target_text,
            "score": self.score,
            "note": self.note,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
