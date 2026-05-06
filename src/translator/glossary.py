"""Bidirectional glossary, primarily for ru<->tk literary cleanup.

The glossary is intentionally small and conservative: it only fixes common
domain-specific or stylistic mistakes that machine translators make
(literal/awkward renderings, wrong register, missed proper nouns). Anything
ambiguous is left to the model — the glossary must never inject a wrong
translation into a correct sentence.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Tuple


@dataclass(frozen=True)
class GlossaryEntry:
    """A single source -> target replacement rule."""

    source: str
    target: str
    case_sensitive: bool = False
    whole_word: bool = True


# Curated ru -> tk literary-register fixes. Keys are intentionally short and
# unambiguous; multi-word patterns take precedence over single words because
# we apply rules sorted by source length (descending).
RU_TK: Tuple[GlossaryEntry, ...] = (
    GlossaryEntry("здравствуйте", "salam"),
    GlossaryEntry("спасибо", "sag boluň"),
    GlossaryEntry("пожалуйста", "haýyş edýärin"),
    GlossaryEntry("доброе утро", "ertiriňiz haýyrly bolsun"),
    GlossaryEntry("добрый день", "günüňiz haýyrly bolsun"),
    GlossaryEntry("добрый вечер", "agşamyňyz haýyrly bolsun"),
    GlossaryEntry("склад", "ammar"),
    GlossaryEntry("товар", "haryt"),
    GlossaryEntry("заказ", "sargyt"),
    GlossaryEntry("курьер", "kurýer"),
    GlossaryEntry("клиент", "müşderi"),
    GlossaryEntry("продавец", "satyjy"),
    GlossaryEntry("покупатель", "alyjy"),
    GlossaryEntry("доставка", "eltip bermek"),
    GlossaryEntry("оплата", "töleg"),
)

TK_RU: Tuple[GlossaryEntry, ...] = tuple(
    GlossaryEntry(source=e.target, target=e.source, case_sensitive=e.case_sensitive)
    for e in RU_TK
)

# A few cross-language fixes for proper nouns / brand-style words that should
# never be transliterated weirdly.
COMMON: Tuple[GlossaryEntry, ...] = (
    GlossaryEntry("Ehli Trend", "Ehli Trend", case_sensitive=True),
)


@dataclass
class Glossary:
    """Stores per-pair entries and applies them to translated output."""

    entries: Dict[Tuple[str, str], List[GlossaryEntry]] = field(default_factory=dict)
    common: List[GlossaryEntry] = field(default_factory=list)

    @classmethod
    def default(cls) -> "Glossary":
        return cls(
            entries={
                ("ru", "tk"): list(RU_TK),
                ("tk", "ru"): list(TK_RU),
            },
            common=list(COMMON),
        )

    def add(self, source_lang: str, target_lang: str, entries: Iterable[GlossaryEntry]) -> None:
        key = (source_lang, target_lang)
        bucket = self.entries.setdefault(key, [])
        bucket.extend(entries)

    def apply(self, text: str, source_lang: str, target_lang: str) -> str:
        """Apply both pair-specific and common rules to ``text``."""
        if not text:
            return text
        rules = list(self.common) + list(self.entries.get((source_lang, target_lang), ()))
        # longer source first to avoid partial overshadowing
        rules.sort(key=lambda e: len(e.source), reverse=True)
        result = text
        for rule in rules:
            result = _apply_rule(result, rule)
        return result


def _apply_rule(text: str, rule: GlossaryEntry) -> str:
    flags = 0 if rule.case_sensitive else re.IGNORECASE | re.UNICODE
    pattern = re.escape(rule.source)
    if rule.whole_word:
        # \b does not work reliably with non-ASCII characters, so we guard the
        # match with explicit non-letter look-arounds that include Cyrillic /
        # Latin letter ranges.
        pattern = rf"(?<![\wÀ-ɏЀ-ӿ]){pattern}(?![\wÀ-ɏЀ-ӿ])"
    return re.sub(pattern, rule.target, text, flags=flags)
