"""User-editable glossary application service (channel-aware)."""

from __future__ import annotations

import logging
import re
from typing import List, Optional

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
    """Apply user glossary rules and answer search queries.

    When ``channel_id`` is provided, channel-scoped rules are applied **after**
    the global ones — that way a channel-specific replacement always wins.
    """

    def __init__(self, repository: GlossaryRepository) -> None:
        self.repository = repository

    def _collect_rules(
        self, source_lang: str, target_lang: str, channel_id: Optional[str]
    ) -> List[GlossaryEntryDTO]:
        global_rules = self.repository.list(
            source_lang=source_lang,
            target_lang=target_lang,
            limit=1000,
            channel_id=None,  # global only
        )
        rules: List[GlossaryEntryDTO] = list(global_rules)
        if channel_id is not None:
            channel_rules = self.repository.list(
                source_lang=source_lang,
                target_lang=target_lang,
                limit=1000,
                channel_id=channel_id,
            )
            rules.extend(channel_rules)
        return rules

    def apply(
        self,
        text: str,
        *,
        source_lang: str,
        target_lang: str,
        channel_id: Optional[str] = None,
    ) -> str:
        if not text:
            return text
        rules = self._collect_rules(source_lang, target_lang, channel_id)
        if not rules:
            return text
        # Longer source first; among equal-length, channel rules last so they
        # override globals.
        rules.sort(
            key=lambda e: (len(e.source_text), 1 if e.channel_id else 0),
            reverse=True,
        )
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
        self,
        text: str,
        *,
        source_lang: str,
        target_lang: str,
        channel_id: Optional[str] = None,
    ) -> List[GlossaryEntryDTO]:
        if not text:
            return []
        rules = self._collect_rules(source_lang, target_lang, channel_id)
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
