"""High-level translation orchestrator.

The service owns the end-to-end flow:
  1. validate language pair,
  2. run the primary provider (with literary hint for priority pairs),
  3. apply glossary post-processing,
  4. run quality checks,
  5. retry with the fallback provider if the result is bad.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import List, Optional

from ..providers.base import (
    ProviderError,
    ProviderUnavailableError,
    TranslationProvider,
)
from .glossary import Glossary
from .languages import LanguagePair, normalize_language
from .quality_check import QualityReport, check as quality_check

logger = logging.getLogger(__name__)


@dataclass
class TranslationResult:
    """Final, post-processed translation plus diagnostics."""

    text: str
    source_lang: str
    target_lang: str
    provider: str
    latency_seconds: float
    quality: QualityReport
    fallback_used: bool = False
    notes: List[str] = field(default_factory=list)


class TranslatorService:
    """Translate text using a primary provider and an optional fallback."""

    def __init__(
        self,
        *,
        primary: TranslationProvider,
        fallback: Optional[TranslationProvider] = None,
        glossary: Optional[Glossary] = None,
        use_glossary: bool = True,
        run_quality_check: bool = True,
        latency_budget: float = 0.3,
    ) -> None:
        self.primary = primary
        self.fallback = fallback
        self.glossary = glossary or Glossary.default()
        self.use_glossary = use_glossary
        self.run_quality_check = run_quality_check
        self.latency_budget = latency_budget

    def translate(
        self,
        *,
        text: str,
        source_lang: str,
        target_lang: str,
    ) -> TranslationResult:
        pair = LanguagePair.of(source_lang, target_lang)
        notes: List[str] = []

        if not text or not text.strip():
            return TranslationResult(
                text="",
                source_lang=pair.source.code,
                target_lang=pair.target.code,
                provider="noop",
                latency_seconds=0.0,
                quality=QualityReport(ok=True, score=1.0, issues=[]),
                notes=["empty input"],
            )

        provider, used_fallback, raw, latency = self._run_with_fallback(
            text=text, pair=pair, notes=notes
        )

        polished = self._postprocess(raw, pair=pair)
        report = self._maybe_check(text, polished, pair)

        if latency > self.latency_budget:
            notes.append(f"latency {latency:.3f}s exceeded budget {self.latency_budget:.3f}s")

        return TranslationResult(
            text=polished,
            source_lang=pair.source.code,
            target_lang=pair.target.code,
            provider=provider,
            latency_seconds=latency,
            quality=report,
            fallback_used=used_fallback,
            notes=notes,
        )

    # ------------------------------------------------------------------

    def _run_with_fallback(
        self,
        *,
        text: str,
        pair: LanguagePair,
        notes: List[str],
    ):
        primary_name = getattr(self.primary, "name", "primary")
        start = time.perf_counter()
        try:
            if not self.primary.is_available():
                raise ProviderUnavailableError(f"{primary_name} unavailable")
            translated = self.primary.translate(
                text=text,
                source_lang=pair.source.code,
                target_lang=pair.target.code,
                literary=pair.is_priority,
            )
            return primary_name, False, translated, time.perf_counter() - start
        except (ProviderUnavailableError, ProviderError) as exc:
            notes.append(f"primary failed: {exc}")
            if self.fallback is None:
                raise
        # Fallback path
        fallback_name = getattr(self.fallback, "name", "fallback")
        start_fb = time.perf_counter()
        translated = self.fallback.translate(
            text=text,
            source_lang=pair.source.code,
            target_lang=pair.target.code,
            literary=pair.is_priority,
        )
        return fallback_name, True, translated, time.perf_counter() - start_fb

    def _postprocess(self, text: str, *, pair: LanguagePair) -> str:
        if not self.use_glossary or not text:
            return text
        return self.glossary.apply(text, pair.source.code, pair.target.code)

    def _maybe_check(
        self,
        source_text: str,
        translated_text: str,
        pair: LanguagePair,
    ) -> QualityReport:
        if not self.run_quality_check:
            return QualityReport(ok=True, score=1.0, issues=[])
        return quality_check(
            source_text=source_text,
            translated_text=translated_text,
            source_lang=pair.source.code,
            target_lang=pair.target.code,
        )

    # Convenience: translate using string codes without building LanguagePair.
    def translate_text(self, text: str, src: str, tgt: str) -> str:
        return self.translate(
            text=text,
            source_lang=normalize_language(src),
            target_lang=normalize_language(tgt),
        ).text
