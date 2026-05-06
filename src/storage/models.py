"""ORM models for channels, glossary and translation memory."""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey, Index, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _uuid() -> str:
    return uuid.uuid4().hex


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def normalize_for_match(text: str) -> str:
    """Normalise text for translation-memory exact lookup."""
    if not text:
        return ""
    collapsed = " ".join(text.strip().split())
    return collapsed.lower()


def hash_for_match(text: str) -> str:
    return hashlib.sha256(normalize_for_match(text).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Channel / AI-agent
# ---------------------------------------------------------------------------


class Channel(Base):
    """An AI-agent / content channel — bundles default style, tone, voice."""

    __tablename__ = "channels"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)

    primary_lang: Mapped[str] = mapped_column(String(8), default="ru")
    target_lang: Mapped[Optional[str]] = mapped_column(String(8), nullable=True, default=None)

    style: Mapped[str] = mapped_column(String(40), default="natural")
    tone: Mapped[Optional[str]] = mapped_column(String(40), nullable=True, default=None)
    emotion: Mapped[str] = mapped_column(String(40), default="neutral")
    voice_id: Mapped[Optional[str]] = mapped_column(String(80), nullable=True, default=None)

    voice_use_case: Mapped[str] = mapped_column(String(20), default="video")
    dubbing_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow
    )

    glossary_entries: Mapped[list["GlossaryEntry"]] = relationship(
        back_populates="channel", cascade="all, delete-orphan"
    )
    memory_entries: Mapped[list["TranslationMemoryEntry"]] = relationship(
        back_populates="channel", cascade="all, delete-orphan"
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "primary_lang": self.primary_lang,
            "target_lang": self.target_lang,
            "style": self.style,
            "tone": self.tone,
            "emotion": self.emotion,
            "voice_id": self.voice_id,
            "voice_use_case": self.voice_use_case,
            "dubbing_notes": self.dubbing_notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# ---------------------------------------------------------------------------
# Glossary
# ---------------------------------------------------------------------------


class GlossaryEntry(Base):
    """User-editable, per-pair word/phrase replacement."""

    __tablename__ = "glossary_entries"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    channel_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("channels.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        default=None,
    )
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

    channel: Mapped[Optional["Channel"]] = relationship(back_populates="glossary_entries")

    __table_args__ = (
        Index(
            "ix_glossary_pair_source",
            "source_lang", "target_lang", "source_text",
        ),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "channel_id": self.channel_id,
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


# ---------------------------------------------------------------------------
# Translation memory
# ---------------------------------------------------------------------------


class CustomVoiceProfile(Base):
    """User-defined voice profile (Custom Voice).

    Stores profile metadata + a path to the locally-stored audio sample.
    Audio files are NEVER committed to git — they live under ``data/custom_voices/``,
    which is in ``.gitignore``. The ``consent_given`` flag must be ``True``
    before a profile can be created.
    """

    __tablename__ = "custom_voices"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)

    # ----- voice settings -----
    language: Mapped[str] = mapped_column(String(8), default="ru")
    speed: Mapped[str] = mapped_column(String(20), default="normal")
    pitch: Mapped[str] = mapped_column(String(20), default="normal")
    emotion: Mapped[str] = mapped_column(String(40), default="neutral")
    clarity: Mapped[str] = mapped_column(String(20), default="normal")
    intensity: Mapped[str] = mapped_column(String(20), default="medium")
    use_case: Mapped[str] = mapped_column(String(20), default="text")

    # ----- variant chain (e.g. "Мой голос — блогерский") -----
    parent_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("custom_voices.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        default=None,
    )

    # ----- bindings (all optional) -----
    channel_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("channels.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        default=None,
    )
    bound_style: Mapped[Optional[str]] = mapped_column(String(40), nullable=True, default=None)
    bound_video_use_case: Mapped[Optional[str]] = mapped_column(
        String(40), nullable=True, default=None,
    )

    # ----- audio sample (local only) -----
    sample_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    sample_duration: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=None)

    # ----- consent (REQUIRED) -----
    consent_given: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    consent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, default=None,
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "language": self.language,
            "speed": self.speed,
            "pitch": self.pitch,
            "emotion": self.emotion,
            "clarity": self.clarity,
            "intensity": self.intensity,
            "use_case": self.use_case,
            "parent_id": self.parent_id,
            "channel_id": self.channel_id,
            "bound_style": self.bound_style,
            "bound_video_use_case": self.bound_video_use_case,
            "sample_path": self.sample_path,
            "sample_duration": self.sample_duration,
            "consent_given": bool(self.consent_given),
            "consent_text": self.consent_text,
            "consent_at": self.consent_at.isoformat() if self.consent_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class TranslationMemoryEntry(Base):
    """Whole-segment translation memory (input → curated translation)."""

    __tablename__ = "translation_memory"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    channel_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("channels.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        default=None,
    )
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

    channel: Mapped[Optional["Channel"]] = relationship(back_populates="memory_entries")

    __table_args__ = (
        UniqueConstraint(
            "source_lang", "target_lang", "source_hash", "channel_id",
            name="uq_tm_pair_hash",
        ),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "channel_id": self.channel_id,
            "source_lang": self.source_lang,
            "target_lang": self.target_lang,
            "source_text": self.source_text,
            "target_text": self.target_text,
            "score": self.score,
            "note": self.note,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
