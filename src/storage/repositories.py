"""Repository layer for glossary and translation memory.

The translator service depends only on these repositories — never on
SQLAlchemy directly — so we can replace the backing store (PostgreSQL,
in-memory, JSON file) without touching downstream code.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .db import session_scope
from .models import (
    GlossaryEntry,
    TranslationMemoryEntry,
    hash_for_match,
    normalize_for_match,
)


# ---------------------------------------------------------------------------
# Public DTOs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GlossaryEntryDTO:
    id: str
    source_lang: str
    target_lang: str
    source_text: str
    target_text: str
    case_sensitive: bool = False
    whole_word: bool = True
    note: Optional[str] = None

    @classmethod
    def from_orm(cls, e: GlossaryEntry) -> "GlossaryEntryDTO":
        return cls(
            id=e.id,
            source_lang=e.source_lang,
            target_lang=e.target_lang,
            source_text=e.source_text,
            target_text=e.target_text,
            case_sensitive=bool(e.case_sensitive),
            whole_word=bool(e.whole_word),
            note=e.note,
        )


@dataclass(frozen=True)
class TranslationMemoryDTO:
    id: str
    source_lang: str
    target_lang: str
    source_text: str
    target_text: str
    score: float = 1.0
    note: Optional[str] = None

    @classmethod
    def from_orm(cls, e: TranslationMemoryEntry) -> "TranslationMemoryDTO":
        return cls(
            id=e.id,
            source_lang=e.source_lang,
            target_lang=e.target_lang,
            source_text=e.source_text,
            target_text=e.target_text,
            score=float(e.score or 1.0),
            note=e.note,
        )


class DuplicateEntryError(ValueError):
    """Raised when a unique constraint already exists for an entry."""


# ---------------------------------------------------------------------------
# Glossary
# ---------------------------------------------------------------------------


class GlossaryRepository:
    """CRUD + search for the user-editable glossary."""

    def __init__(self, session_provider=session_scope) -> None:
        self._session_provider = session_provider

    def list(
        self,
        *,
        source_lang: Optional[str] = None,
        target_lang: Optional[str] = None,
        query: Optional[str] = None,
        limit: int = 200,
    ) -> List[GlossaryEntryDTO]:
        with self._session_provider() as session:
            stmt = select(GlossaryEntry)
            if source_lang:
                stmt = stmt.where(GlossaryEntry.source_lang == source_lang)
            if target_lang:
                stmt = stmt.where(GlossaryEntry.target_lang == target_lang)
            if query:
                like = f"%{query.lower()}%"
                stmt = stmt.where(
                    or_(
                        GlossaryEntry.source_text.ilike(like),
                        GlossaryEntry.target_text.ilike(like),
                    )
                )
            stmt = stmt.order_by(GlossaryEntry.updated_at.desc()).limit(limit)
            return [GlossaryEntryDTO.from_orm(e) for e in session.execute(stmt).scalars()]

    def get(self, entry_id: str) -> Optional[GlossaryEntryDTO]:
        with self._session_provider() as session:
            entity = session.get(GlossaryEntry, entry_id)
            return GlossaryEntryDTO.from_orm(entity) if entity else None

    def create(
        self,
        *,
        source_lang: str,
        target_lang: str,
        source_text: str,
        target_text: str,
        case_sensitive: bool = False,
        whole_word: bool = True,
        note: Optional[str] = None,
    ) -> GlossaryEntryDTO:
        if not source_text.strip() or not target_text.strip():
            raise ValueError("source_text and target_text must not be empty")
        with self._session_provider() as session:
            entity = GlossaryEntry(
                source_lang=source_lang,
                target_lang=target_lang,
                source_text=source_text.strip(),
                target_text=target_text.strip(),
                case_sensitive=case_sensitive,
                whole_word=whole_word,
                note=note,
            )
            session.add(entity)
            session.flush()
            return GlossaryEntryDTO.from_orm(entity)

    def update(
        self,
        entry_id: str,
        *,
        source_text: Optional[str] = None,
        target_text: Optional[str] = None,
        case_sensitive: Optional[bool] = None,
        whole_word: Optional[bool] = None,
        note: Optional[str] = None,
    ) -> Optional[GlossaryEntryDTO]:
        with self._session_provider() as session:
            entity = session.get(GlossaryEntry, entry_id)
            if entity is None:
                return None
            if source_text is not None:
                entity.source_text = source_text.strip()
            if target_text is not None:
                entity.target_text = target_text.strip()
            if case_sensitive is not None:
                entity.case_sensitive = case_sensitive
            if whole_word is not None:
                entity.whole_word = whole_word
            if note is not None:
                entity.note = note
            session.flush()
            return GlossaryEntryDTO.from_orm(entity)

    def delete(self, entry_id: str) -> bool:
        with self._session_provider() as session:
            entity = session.get(GlossaryEntry, entry_id)
            if entity is None:
                return False
            session.delete(entity)
            return True

    def find_match(
        self, *, source_text: str, source_lang: str, target_lang: str
    ) -> Optional[GlossaryEntryDTO]:
        """Return the strongest exact source-side match for ``source_text``."""
        if not source_text.strip():
            return None
        normalised = source_text.strip().lower()
        with self._session_provider() as session:
            stmt = (
                select(GlossaryEntry)
                .where(GlossaryEntry.source_lang == source_lang)
                .where(GlossaryEntry.target_lang == target_lang)
            )
            for entity in session.execute(stmt).scalars():
                stored = entity.source_text
                if entity.case_sensitive:
                    if stored == source_text.strip():
                        return GlossaryEntryDTO.from_orm(entity)
                else:
                    if stored.lower() == normalised:
                        return GlossaryEntryDTO.from_orm(entity)
        return None


# ---------------------------------------------------------------------------
# Translation memory
# ---------------------------------------------------------------------------


class TranslationMemoryRepository:
    """CRUD + exact-match lookup for whole-segment translation memory."""

    def __init__(self, session_provider=session_scope) -> None:
        self._session_provider = session_provider

    def list(
        self,
        *,
        source_lang: Optional[str] = None,
        target_lang: Optional[str] = None,
        query: Optional[str] = None,
        limit: int = 200,
    ) -> List[TranslationMemoryDTO]:
        with self._session_provider() as session:
            stmt = select(TranslationMemoryEntry)
            if source_lang:
                stmt = stmt.where(TranslationMemoryEntry.source_lang == source_lang)
            if target_lang:
                stmt = stmt.where(TranslationMemoryEntry.target_lang == target_lang)
            if query:
                like = f"%{query.lower()}%"
                stmt = stmt.where(
                    or_(
                        TranslationMemoryEntry.source_text.ilike(like),
                        TranslationMemoryEntry.target_text.ilike(like),
                    )
                )
            stmt = stmt.order_by(TranslationMemoryEntry.updated_at.desc()).limit(limit)
            return [
                TranslationMemoryDTO.from_orm(e) for e in session.execute(stmt).scalars()
            ]

    def get(self, entry_id: str) -> Optional[TranslationMemoryDTO]:
        with self._session_provider() as session:
            entity = session.get(TranslationMemoryEntry, entry_id)
            return TranslationMemoryDTO.from_orm(entity) if entity else None

    def find_exact(
        self, *, source_text: str, source_lang: str, target_lang: str
    ) -> Optional[TranslationMemoryDTO]:
        if not source_text.strip():
            return None
        digest = hash_for_match(source_text)
        with self._session_provider() as session:
            stmt = (
                select(TranslationMemoryEntry)
                .where(TranslationMemoryEntry.source_lang == source_lang)
                .where(TranslationMemoryEntry.target_lang == target_lang)
                .where(TranslationMemoryEntry.source_hash == digest)
                .limit(1)
            )
            entity = session.execute(stmt).scalar_one_or_none()
            return TranslationMemoryDTO.from_orm(entity) if entity else None

    def upsert(
        self,
        *,
        source_lang: str,
        target_lang: str,
        source_text: str,
        target_text: str,
        score: float = 1.0,
        note: Optional[str] = None,
    ) -> TranslationMemoryDTO:
        if not source_text.strip() or not target_text.strip():
            raise ValueError("source_text and target_text must not be empty")
        digest = hash_for_match(source_text)
        with self._session_provider() as session:
            stmt = (
                select(TranslationMemoryEntry)
                .where(TranslationMemoryEntry.source_lang == source_lang)
                .where(TranslationMemoryEntry.target_lang == target_lang)
                .where(TranslationMemoryEntry.source_hash == digest)
            )
            entity = session.execute(stmt).scalar_one_or_none()
            if entity is None:
                entity = TranslationMemoryEntry(
                    source_lang=source_lang,
                    target_lang=target_lang,
                    source_text=source_text.strip(),
                    target_text=target_text.strip(),
                    source_hash=digest,
                    score=score,
                    note=note,
                )
                session.add(entity)
            else:
                entity.target_text = target_text.strip()
                entity.score = score
                if note is not None:
                    entity.note = note
            try:
                session.flush()
            except IntegrityError as exc:
                raise DuplicateEntryError(str(exc)) from exc
            return TranslationMemoryDTO.from_orm(entity)

    def update(
        self,
        entry_id: str,
        *,
        target_text: Optional[str] = None,
        score: Optional[float] = None,
        note: Optional[str] = None,
    ) -> Optional[TranslationMemoryDTO]:
        with self._session_provider() as session:
            entity = session.get(TranslationMemoryEntry, entry_id)
            if entity is None:
                return None
            if target_text is not None:
                entity.target_text = target_text.strip()
            if score is not None:
                entity.score = score
            if note is not None:
                entity.note = note
            session.flush()
            return TranslationMemoryDTO.from_orm(entity)

    def delete(self, entry_id: str) -> bool:
        with self._session_provider() as session:
            entity = session.get(TranslationMemoryEntry, entry_id)
            if entity is None:
                return False
            session.delete(entity)
            return True


__all__ = [
    "DuplicateEntryError",
    "GlossaryEntryDTO",
    "GlossaryRepository",
    "TranslationMemoryDTO",
    "TranslationMemoryRepository",
    "normalize_for_match",
]
