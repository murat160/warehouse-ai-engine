"""Channel-aware Translation Memory service."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from ..storage.repositories import TranslationMemoryDTO, TranslationMemoryRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TranslationMemoryHit:
    entry: TranslationMemoryDTO
    used_short_circuit: bool = True


class TranslationMemoryService:
    def __init__(self, repository: TranslationMemoryRepository) -> None:
        self.repository = repository

    def lookup(
        self,
        *,
        text: str,
        source_lang: str,
        target_lang: str,
        channel_id: Optional[str] = None,
    ) -> Optional[TranslationMemoryHit]:
        if not text or not text.strip():
            return None
        match = self.repository.find_exact(
            source_text=text,
            source_lang=source_lang,
            target_lang=target_lang,
            channel_id=channel_id,
        )
        if match is None:
            return None
        return TranslationMemoryHit(entry=match)

    def remember(
        self,
        *,
        source_text: str,
        target_text: str,
        source_lang: str,
        target_lang: str,
        score: float = 1.0,
        note: Optional[str] = None,
        channel_id: Optional[str] = None,
    ) -> TranslationMemoryDTO:
        return self.repository.upsert(
            source_lang=source_lang,
            target_lang=target_lang,
            source_text=source_text,
            target_text=target_text,
            score=score,
            note=note,
            channel_id=channel_id,
        )


__all__ = ["TranslationMemoryHit", "TranslationMemoryService"]
