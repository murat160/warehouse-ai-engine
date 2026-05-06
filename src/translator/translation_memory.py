"""Translation Memory service: exact-segment lookup and curation.

Distinct from the user glossary — TM stores whole-segment overrides
("быстрая доставка" → curated translation) so the engine can short-circuit
the model when a known phrase is requested again.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from ..storage.repositories import TranslationMemoryDTO, TranslationMemoryRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TranslationMemoryHit:
    """Result of a TM lookup that the orchestrator can short-circuit on."""

    entry: TranslationMemoryDTO
    used_short_circuit: bool = True


class TranslationMemoryService:
    def __init__(self, repository: TranslationMemoryRepository) -> None:
        self.repository = repository

    def lookup(
        self, *, text: str, source_lang: str, target_lang: str
    ) -> Optional[TranslationMemoryHit]:
        """Return a hit when ``text`` (normalised) matches a stored segment."""
        if not text or not text.strip():
            return None
        match = self.repository.find_exact(
            source_text=text, source_lang=source_lang, target_lang=target_lang
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
    ) -> TranslationMemoryDTO:
        """Persist a new (or update an existing) segment-level override."""
        return self.repository.upsert(
            source_lang=source_lang,
            target_lang=target_lang,
            source_text=source_text,
            target_text=target_text,
            score=score,
            note=note,
        )


__all__ = ["TranslationMemoryHit", "TranslationMemoryService"]
