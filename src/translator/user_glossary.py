"""User-editable glossary application service.

Wraps :class:`GlossaryRepository` to provide post-translation replacement
that respects per-entry case-sensitivity and whole-word flags. Distinct from
the static curated :mod:`src.translator.glossary` — that one ships built-in
ru↔tk fixes, this one is whatever the operator added at runtime.
"""

from __future__ import annotations

import logging
import re
from typing import List

from ..storage.repositories import GlossaryEntryDTO, GlossaryRepository

logger = logging.getLogger(__name__)


def _build_pattern(entry: GlossaryEntryDTO) -> re.Pattern[str]:
    body = re.escape(entry.source_text)
    if entry.whole_word:
        body = rf"(?<![\wÀ-ɏЀ-ӿ]){body}(?![\wÀ-ɏЀ-ӿ])"
    flags = re.UNICODE
    if not entry.case_sensitive:
        flags |= re.IGNORECASE
    return re.compile(body, flags)


class UserGlossaryService:
    """Apply user glossary rules and answer search queries."""

    def __init__(self, repository: GlossaryRepository) -> None:
        self.repository = repository

    def apply(self, text: str, *, source_lang: str, target_lang: str) -> str:
        """Substitute every glossary match in ``text`` with its target form."""
        if not text:
            return text
        rules = self.repository.list(
            source_lang=source_lang, target_lang=target_lang, limit=1000
        )
        if not rules:
            return text
        # Apply longer source first so multi-word rules win over single-word ones.
        rules.sort(key=lambda e: len(e.source_text), reverse=True)
        result = text
        for rule in rules:
            try:
                pattern = _build_pattern(rule)
            except re.error:
                logger.warning("invalid regex for glossary entry %s — skipped", rule.id)
                continue
            result = pattern.sub(rule.target_text, result)
        return result

    def detect_terms(
        self, text: str, *, source_lang: str, target_lang: str
    ) -> List[GlossaryEntryDTO]:
        """Return every glossary entry whose source appears in ``text``."""
        if not text:
            return []
        rules = self.repository.list(
            source_lang=source_lang, target_lang=target_lang, limit=1000
        )
        hits: List[GlossaryEntryDTO] = []
        for rule in rules:
            try:
                pattern = _build_pattern(rule)
            except re.error:
                continue
            if pattern.search(text):
                hits.append(rule)
        return hits


__all__ = ["UserGlossaryService"]
