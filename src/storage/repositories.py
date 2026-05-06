"""Repository layer for channels, glossary and translation memory.

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

import json
from datetime import datetime, timezone

from .db import session_scope
from .models import (
    Channel,
    CustomVoiceProfile,
    GlossaryEntry,
    PublishingPackage,
    TranslationMemoryEntry,
    hash_for_match,
    normalize_for_match,
)


# ---------------------------------------------------------------------------
# Public DTOs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ChannelDTO:
    id: str
    name: str
    description: Optional[str]
    primary_lang: str
    target_lang: Optional[str]
    style: str
    tone: Optional[str]
    emotion: str
    voice_id: Optional[str]
    voice_use_case: str
    dubbing_notes: Optional[str]

    @classmethod
    def from_orm(cls, e: Channel) -> "ChannelDTO":
        return cls(
            id=e.id,
            name=e.name,
            description=e.description,
            primary_lang=e.primary_lang,
            target_lang=e.target_lang,
            style=e.style,
            tone=e.tone,
            emotion=e.emotion,
            voice_id=e.voice_id,
            voice_use_case=e.voice_use_case,
            dubbing_notes=e.dubbing_notes,
        )


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
    channel_id: Optional[str] = None

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
            channel_id=e.channel_id,
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
    channel_id: Optional[str] = None

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
            channel_id=e.channel_id,
        )


class DuplicateEntryError(ValueError):
    """Raised when a unique constraint already exists for an entry."""


# Sentinel value used to distinguish "channel filter not provided" from
# "filter for global entries (channel_id IS NULL)".
_UNSET = object()


# ---------------------------------------------------------------------------
# Channels
# ---------------------------------------------------------------------------


class ChannelRepository:
    """CRUD for channels / AI-agents."""

    def __init__(self, session_provider=session_scope) -> None:
        self._session_provider = session_provider

    def list(self, *, limit: int = 200) -> List[ChannelDTO]:
        with self._session_provider() as session:
            stmt = select(Channel).order_by(Channel.updated_at.desc()).limit(limit)
            return [ChannelDTO.from_orm(e) for e in session.execute(stmt).scalars()]

    def get(self, channel_id: str) -> Optional[ChannelDTO]:
        with self._session_provider() as session:
            entity = session.get(Channel, channel_id)
            return ChannelDTO.from_orm(entity) if entity else None

    def get_by_name(self, name: str) -> Optional[ChannelDTO]:
        with self._session_provider() as session:
            stmt = select(Channel).where(Channel.name == name).limit(1)
            entity = session.execute(stmt).scalar_one_or_none()
            return ChannelDTO.from_orm(entity) if entity else None

    def create(
        self,
        *,
        name: str,
        primary_lang: str = "ru",
        target_lang: Optional[str] = None,
        style: str = "natural",
        tone: Optional[str] = None,
        emotion: str = "neutral",
        voice_id: Optional[str] = None,
        voice_use_case: str = "video",
        description: Optional[str] = None,
        dubbing_notes: Optional[str] = None,
    ) -> ChannelDTO:
        if not name.strip():
            raise ValueError("name is required")
        with self._session_provider() as session:
            entity = Channel(
                name=name.strip(),
                primary_lang=primary_lang,
                target_lang=target_lang,
                style=style,
                tone=tone,
                emotion=emotion,
                voice_id=voice_id,
                voice_use_case=voice_use_case,
                description=description,
                dubbing_notes=dubbing_notes,
            )
            session.add(entity)
            try:
                session.flush()
            except IntegrityError as exc:
                raise DuplicateEntryError(f"channel '{name}' already exists") from exc
            return ChannelDTO.from_orm(entity)

    def update(
        self,
        channel_id: str,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        primary_lang: Optional[str] = None,
        target_lang: Optional[str] = None,
        style: Optional[str] = None,
        tone: Optional[str] = None,
        emotion: Optional[str] = None,
        voice_id: Optional[str] = None,
        voice_use_case: Optional[str] = None,
        dubbing_notes: Optional[str] = None,
    ) -> Optional[ChannelDTO]:
        with self._session_provider() as session:
            entity = session.get(Channel, channel_id)
            if entity is None:
                return None
            if name is not None:
                entity.name = name.strip()
            if description is not None:
                entity.description = description
            if primary_lang is not None:
                entity.primary_lang = primary_lang
            if target_lang is not None:
                entity.target_lang = target_lang
            if style is not None:
                entity.style = style
            if tone is not None:
                entity.tone = tone
            if emotion is not None:
                entity.emotion = emotion
            if voice_id is not None:
                entity.voice_id = voice_id
            if voice_use_case is not None:
                entity.voice_use_case = voice_use_case
            if dubbing_notes is not None:
                entity.dubbing_notes = dubbing_notes
            try:
                session.flush()
            except IntegrityError as exc:
                raise DuplicateEntryError(str(exc)) from exc
            return ChannelDTO.from_orm(entity)

    def delete(self, channel_id: str) -> bool:
        with self._session_provider() as session:
            entity = session.get(Channel, channel_id)
            if entity is None:
                return False
            session.delete(entity)
            return True


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
        channel_id=_UNSET,  # _UNSET = no filter; None = global only; str = that channel
    ) -> List[GlossaryEntryDTO]:
        with self._session_provider() as session:
            stmt = select(GlossaryEntry)
            if source_lang:
                stmt = stmt.where(GlossaryEntry.source_lang == source_lang)
            if target_lang:
                stmt = stmt.where(GlossaryEntry.target_lang == target_lang)
            if channel_id is not _UNSET:
                if channel_id is None:
                    stmt = stmt.where(GlossaryEntry.channel_id.is_(None))
                else:
                    stmt = stmt.where(GlossaryEntry.channel_id == channel_id)
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
        channel_id: Optional[str] = None,
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
                channel_id=channel_id,
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
        channel_id=_UNSET,
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
            if channel_id is not _UNSET:
                entity.channel_id = channel_id  # may be None to detach
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
        self,
        *,
        source_text: str,
        source_lang: str,
        target_lang: str,
        channel_id: Optional[str] = None,
    ) -> Optional[GlossaryEntryDTO]:
        """Return the strongest exact source-side match for ``source_text``.

        If ``channel_id`` is given, channel-scoped entries win over global ones.
        """
        if not source_text.strip():
            return None
        normalised = source_text.strip().lower()
        with self._session_provider() as session:
            stmt = (
                select(GlossaryEntry)
                .where(GlossaryEntry.source_lang == source_lang)
                .where(GlossaryEntry.target_lang == target_lang)
            )
            channel_match: Optional[GlossaryEntry] = None
            global_match: Optional[GlossaryEntry] = None
            for entity in session.execute(stmt).scalars():
                stored = entity.source_text
                if entity.case_sensitive:
                    matched = stored == source_text.strip()
                else:
                    matched = stored.lower() == normalised
                if not matched:
                    continue
                if channel_id is not None and entity.channel_id == channel_id:
                    channel_match = entity
                    break
                if entity.channel_id is None:
                    global_match = entity
            chosen = channel_match or global_match
            return GlossaryEntryDTO.from_orm(chosen) if chosen else None


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
        channel_id=_UNSET,
    ) -> List[TranslationMemoryDTO]:
        with self._session_provider() as session:
            stmt = select(TranslationMemoryEntry)
            if source_lang:
                stmt = stmt.where(TranslationMemoryEntry.source_lang == source_lang)
            if target_lang:
                stmt = stmt.where(TranslationMemoryEntry.target_lang == target_lang)
            if channel_id is not _UNSET:
                if channel_id is None:
                    stmt = stmt.where(TranslationMemoryEntry.channel_id.is_(None))
                else:
                    stmt = stmt.where(TranslationMemoryEntry.channel_id == channel_id)
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
        self,
        *,
        source_text: str,
        source_lang: str,
        target_lang: str,
        channel_id: Optional[str] = None,
    ) -> Optional[TranslationMemoryDTO]:
        """Find an exact-match TM entry. Channel-scoped wins over global."""
        if not source_text.strip():
            return None
        digest = hash_for_match(source_text)
        with self._session_provider() as session:
            stmt = (
                select(TranslationMemoryEntry)
                .where(TranslationMemoryEntry.source_lang == source_lang)
                .where(TranslationMemoryEntry.target_lang == target_lang)
                .where(TranslationMemoryEntry.source_hash == digest)
            )
            channel_match: Optional[TranslationMemoryEntry] = None
            global_match: Optional[TranslationMemoryEntry] = None
            for entity in session.execute(stmt).scalars():
                if channel_id is not None and entity.channel_id == channel_id:
                    channel_match = entity
                    break
                if entity.channel_id is None:
                    global_match = entity
            chosen = channel_match or global_match
            return TranslationMemoryDTO.from_orm(chosen) if chosen else None

    def upsert(
        self,
        *,
        source_lang: str,
        target_lang: str,
        source_text: str,
        target_text: str,
        score: float = 1.0,
        note: Optional[str] = None,
        channel_id: Optional[str] = None,
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
                .where(
                    TranslationMemoryEntry.channel_id == channel_id
                    if channel_id is not None
                    else TranslationMemoryEntry.channel_id.is_(None)
                )
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
                    channel_id=channel_id,
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
        channel_id=_UNSET,
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
            if channel_id is not _UNSET:
                entity.channel_id = channel_id
            session.flush()
            return TranslationMemoryDTO.from_orm(entity)

    def delete(self, entry_id: str) -> bool:
        with self._session_provider() as session:
            entity = session.get(TranslationMemoryEntry, entry_id)
            if entity is None:
                return False
            session.delete(entity)
            return True


# ---------------------------------------------------------------------------
# Custom voices (Custom Voice / Мой голос)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CustomVoiceDTO:
    id: str
    name: str
    description: Optional[str]
    language: str
    speed: str
    pitch: str
    emotion: str
    clarity: str
    intensity: str
    use_case: str
    parent_id: Optional[str]
    channel_id: Optional[str]
    bound_style: Optional[str]
    bound_video_use_case: Optional[str]
    sample_path: Optional[str]
    sample_duration: Optional[float]
    consent_given: bool
    consent_text: Optional[str]
    consent_at: Optional[str]

    @classmethod
    def from_orm(cls, e: CustomVoiceProfile) -> "CustomVoiceDTO":
        return cls(
            id=e.id,
            name=e.name,
            description=e.description,
            language=e.language,
            speed=e.speed,
            pitch=e.pitch,
            emotion=e.emotion,
            clarity=e.clarity,
            intensity=e.intensity,
            use_case=e.use_case,
            parent_id=e.parent_id,
            channel_id=e.channel_id,
            bound_style=e.bound_style,
            bound_video_use_case=e.bound_video_use_case,
            sample_path=e.sample_path,
            sample_duration=e.sample_duration,
            consent_given=bool(e.consent_given),
            consent_text=e.consent_text,
            consent_at=e.consent_at.isoformat() if e.consent_at else None,
        )


class ConsentRequiredError(ValueError):
    """Raised when a Custom Voice is created/saved without explicit consent."""


class CustomVoiceRepository:
    """CRUD for Custom Voices.

    Audio sample files live on disk under ``data/custom_voices/`` — only the
    *path* is stored here. Creating a profile without ``consent_given=True``
    is rejected at the repository level so the constraint cannot be bypassed
    by a buggy caller.
    """

    def __init__(self, session_provider=session_scope) -> None:
        self._session_provider = session_provider

    def list(
        self,
        *,
        language: Optional[str] = None,
        channel_id=_UNSET,
        parent_id=_UNSET,
        query: Optional[str] = None,
        limit: int = 200,
    ) -> List[CustomVoiceDTO]:
        with self._session_provider() as session:
            stmt = select(CustomVoiceProfile)
            if language:
                stmt = stmt.where(CustomVoiceProfile.language == language)
            if channel_id is not _UNSET:
                if channel_id is None:
                    stmt = stmt.where(CustomVoiceProfile.channel_id.is_(None))
                else:
                    stmt = stmt.where(CustomVoiceProfile.channel_id == channel_id)
            if parent_id is not _UNSET:
                if parent_id is None:
                    stmt = stmt.where(CustomVoiceProfile.parent_id.is_(None))
                else:
                    stmt = stmt.where(CustomVoiceProfile.parent_id == parent_id)
            if query:
                like = f"%{query.lower()}%"
                stmt = stmt.where(CustomVoiceProfile.name.ilike(like))
            stmt = stmt.order_by(CustomVoiceProfile.updated_at.desc()).limit(limit)
            return [CustomVoiceDTO.from_orm(e) for e in session.execute(stmt).scalars()]

    def get(self, voice_id: str) -> Optional[CustomVoiceDTO]:
        with self._session_provider() as session:
            entity = session.get(CustomVoiceProfile, voice_id)
            return CustomVoiceDTO.from_orm(entity) if entity else None

    def variants_of(self, parent_id: str) -> List[CustomVoiceDTO]:
        return self.list(parent_id=parent_id)

    def create(
        self,
        *,
        name: str,
        language: str = "ru",
        speed: str = "normal",
        pitch: str = "normal",
        emotion: str = "neutral",
        clarity: str = "normal",
        intensity: str = "medium",
        use_case: str = "text",
        description: Optional[str] = None,
        parent_id: Optional[str] = None,
        channel_id: Optional[str] = None,
        bound_style: Optional[str] = None,
        bound_video_use_case: Optional[str] = None,
        sample_path: Optional[str] = None,
        sample_duration: Optional[float] = None,
        consent_given: bool = False,
        consent_text: Optional[str] = None,
    ) -> CustomVoiceDTO:
        if not name.strip():
            raise ValueError("name is required")
        if not consent_given:
            raise ConsentRequiredError(
                "creating a Custom Voice requires explicit consent "
                "(consent_given=True). The user must confirm they have the "
                "right to use this voice."
            )
        with self._session_provider() as session:
            entity = CustomVoiceProfile(
                name=name.strip(),
                description=description,
                language=language,
                speed=speed,
                pitch=pitch,
                emotion=emotion,
                clarity=clarity,
                intensity=intensity,
                use_case=use_case,
                parent_id=parent_id,
                channel_id=channel_id,
                bound_style=bound_style,
                bound_video_use_case=bound_video_use_case,
                sample_path=sample_path,
                sample_duration=sample_duration,
                consent_given=True,
                consent_text=consent_text or DEFAULT_CONSENT_TEXT,
                consent_at=datetime.now(timezone.utc),
            )
            session.add(entity)
            session.flush()
            return CustomVoiceDTO.from_orm(entity)

    def update(
        self,
        voice_id: str,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        language: Optional[str] = None,
        speed: Optional[str] = None,
        pitch: Optional[str] = None,
        emotion: Optional[str] = None,
        clarity: Optional[str] = None,
        intensity: Optional[str] = None,
        use_case: Optional[str] = None,
        parent_id=_UNSET,
        channel_id=_UNSET,
        bound_style=_UNSET,
        bound_video_use_case=_UNSET,
        sample_path: Optional[str] = None,
        sample_duration: Optional[float] = None,
    ) -> Optional[CustomVoiceDTO]:
        with self._session_provider() as session:
            entity = session.get(CustomVoiceProfile, voice_id)
            if entity is None:
                return None
            if name is not None:
                entity.name = name.strip()
            if description is not None:
                entity.description = description
            if language is not None:
                entity.language = language
            if speed is not None:
                entity.speed = speed
            if pitch is not None:
                entity.pitch = pitch
            if emotion is not None:
                entity.emotion = emotion
            if clarity is not None:
                entity.clarity = clarity
            if intensity is not None:
                entity.intensity = intensity
            if use_case is not None:
                entity.use_case = use_case
            if parent_id is not _UNSET:
                entity.parent_id = parent_id
            if channel_id is not _UNSET:
                entity.channel_id = channel_id
            if bound_style is not _UNSET:
                entity.bound_style = bound_style
            if bound_video_use_case is not _UNSET:
                entity.bound_video_use_case = bound_video_use_case
            if sample_path is not None:
                entity.sample_path = sample_path
            if sample_duration is not None:
                entity.sample_duration = sample_duration
            session.flush()
            return CustomVoiceDTO.from_orm(entity)

    def delete(self, voice_id: str) -> bool:
        with self._session_provider() as session:
            entity = session.get(CustomVoiceProfile, voice_id)
            if entity is None:
                return False
            session.delete(entity)
            return True


DEFAULT_CONSENT_TEXT = (
    "Я подтверждаю, что имею право использовать этот голос. / "
    "I confirm that I have the right to use this voice."
)


# ---------------------------------------------------------------------------
# Publishing packages
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PublishingPackageDTO:
    id: str
    name: str
    kind: str
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

    @classmethod
    def from_orm(cls, e: PublishingPackage) -> "PublishingPackageDTO":
        return cls(
            id=e.id,
            name=e.name,
            kind=e.kind,
            language=e.language,
            channel_id=e.channel_id,
            title=e.title,
            description=e.description,
            tags=_loads_list(e.tags_json),
            hashtags=_loads_list(e.hashtags_json),
            target_platforms=_loads_list(e.target_platforms_json),
            media_path=e.media_path,
            media_filename=e.media_filename,
            status=e.status,
            created_at=e.created_at.isoformat() if e.created_at else None,
            updated_at=e.updated_at.isoformat() if e.updated_at else None,
        )


def _loads_list(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return []
    return [str(item) for item in value if isinstance(item, (str, int, float))]


def _dumps_list(items: Optional[List[str]]) -> Optional[str]:
    if not items:
        return None
    cleaned = [str(i).strip() for i in items if str(i).strip()]
    return json.dumps(cleaned, ensure_ascii=False) if cleaned else None


class PublishingRepository:
    """CRUD for publishing packages."""

    def __init__(self, session_provider=session_scope) -> None:
        self._session_provider = session_provider

    def list(
        self,
        *,
        language: Optional[str] = None,
        channel_id=_UNSET,
        status: Optional[str] = None,
        platform: Optional[str] = None,
        query: Optional[str] = None,
        limit: int = 200,
    ) -> List[PublishingPackageDTO]:
        with self._session_provider() as session:
            stmt = select(PublishingPackage)
            if language:
                stmt = stmt.where(PublishingPackage.language == language)
            if channel_id is not _UNSET:
                if channel_id is None:
                    stmt = stmt.where(PublishingPackage.channel_id.is_(None))
                else:
                    stmt = stmt.where(PublishingPackage.channel_id == channel_id)
            if status:
                stmt = stmt.where(PublishingPackage.status == status)
            if query:
                like = f"%{query.lower()}%"
                stmt = stmt.where(
                    or_(
                        PublishingPackage.name.ilike(like),
                        PublishingPackage.title.ilike(like),
                    )
                )
            stmt = stmt.order_by(PublishingPackage.updated_at.desc()).limit(limit)
            results = [
                PublishingPackageDTO.from_orm(e) for e in session.execute(stmt).scalars()
            ]
        if platform:
            results = [r for r in results if platform in r.target_platforms]
        return results

    def get(self, package_id: str) -> Optional[PublishingPackageDTO]:
        with self._session_provider() as session:
            entity = session.get(PublishingPackage, package_id)
            return PublishingPackageDTO.from_orm(entity) if entity else None

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
        media_path: Optional[str] = None,
        media_filename: Optional[str] = None,
        status: str = "draft",
    ) -> PublishingPackageDTO:
        if not name.strip() or not title.strip():
            raise ValueError("name and title are required")
        with self._session_provider() as session:
            entity = PublishingPackage(
                name=name.strip(),
                kind=kind,
                language=language,
                channel_id=channel_id,
                title=title.strip(),
                description=description,
                tags_json=_dumps_list(tags),
                hashtags_json=_dumps_list(hashtags),
                target_platforms_json=_dumps_list(target_platforms),
                media_path=media_path,
                media_filename=media_filename,
                status=status,
            )
            session.add(entity)
            session.flush()
            return PublishingPackageDTO.from_orm(entity)

    def update(
        self,
        package_id: str,
        *,
        name: Optional[str] = None,
        title: Optional[str] = None,
        kind: Optional[str] = None,
        language: Optional[str] = None,
        channel_id=_UNSET,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        hashtags: Optional[List[str]] = None,
        target_platforms: Optional[List[str]] = None,
        media_path: Optional[str] = None,
        media_filename: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Optional[PublishingPackageDTO]:
        with self._session_provider() as session:
            entity = session.get(PublishingPackage, package_id)
            if entity is None:
                return None
            if name is not None:
                entity.name = name.strip()
            if title is not None:
                entity.title = title.strip()
            if kind is not None:
                entity.kind = kind
            if language is not None:
                entity.language = language
            if channel_id is not _UNSET:
                entity.channel_id = channel_id
            if description is not None:
                entity.description = description
            if tags is not None:
                entity.tags_json = _dumps_list(tags)
            if hashtags is not None:
                entity.hashtags_json = _dumps_list(hashtags)
            if target_platforms is not None:
                entity.target_platforms_json = _dumps_list(target_platforms)
            if media_path is not None:
                entity.media_path = media_path
            if media_filename is not None:
                entity.media_filename = media_filename
            if status is not None:
                entity.status = status
            session.flush()
            return PublishingPackageDTO.from_orm(entity)

    def delete(self, package_id: str) -> bool:
        with self._session_provider() as session:
            entity = session.get(PublishingPackage, package_id)
            if entity is None:
                return False
            session.delete(entity)
            return True


__all__ = [
    "ChannelDTO",
    "ChannelRepository",
    "ConsentRequiredError",
    "CustomVoiceDTO",
    "CustomVoiceRepository",
    "DEFAULT_CONSENT_TEXT",
    "DuplicateEntryError",
    "GlossaryEntryDTO",
    "GlossaryRepository",
    "PublishingPackageDTO",
    "PublishingRepository",
    "TranslationMemoryDTO",
    "TranslationMemoryRepository",
    "normalize_for_match",
]
