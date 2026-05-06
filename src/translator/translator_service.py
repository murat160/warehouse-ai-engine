"""High-level, channel-aware translation orchestrator.

Flow per request:

  1. validate language pair,
  2. consult **Translation Memory** — first the active channel's TM, then
     the global TM. On hit: short-circuit, apply user glossary, run QA.
  3. otherwise call the primary provider with the requested style + tone +
     emotion; fall back to a secondary provider on error.
  4. apply the static curated glossary (built-in ru<->tk fixes),
  5. apply the **user glossary** — global rules first, channel rules last
     so channel rules always win,
  6. run the heuristic quality check.
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
from .styles import (
    DeliveryTone,
    Emotion,
    TranslationStyle,
    get_emotion,
    get_style,
    get_tone,
)
from .translation_memory import TranslationMemoryService
from .user_glossary import UserGlossaryService

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
    style: str = TranslationStyle.NATURAL.value
    tone: Optional[str] = None
    emotion: str = Emotion.NEUTRAL.value
    channel_id: Optional[str] = None
    tm_hit: bool = False
    user_glossary_hits: List[str] = field(default_factory=list)


class TranslatorService:
    """Translate text using TM + glossaries + provider chain."""

    def __init__(
        self,
        *,
        primary: TranslationProvider,
        fallback: Optional[TranslationProvider] = None,
        glossary: Optional[Glossary] = None,
        user_glossary: Optional[UserGlossaryService] = None,
        translation_memory: Optional[TranslationMemoryService] = None,
        use_glossary: bool = True,
        run_quality_check: bool = True,
        latency_budget: float = 0.3,
        default_style: str = TranslationStyle.NATURAL.value,
    ) -> None:
        self.primary = primary
        self.fallback = fallback
        self.glossary = glossary or Glossary.default()
        self.user_glossary = user_glossary
        self.translation_memory = translation_memory
        self.use_glossary = use_glossary
        self.run_quality_check = run_quality_check
        self.latency_budget = latency_budget
        self.default_style = default_style

    def translate(
        self,
        *,
        text: str,
        source_lang: str,
        target_lang: str,
        style: Optional[str] = None,
        tone: Optional[str] = None,
        emotion: Optional[str] = None,
        channel_id: Optional[str] = None,
    ) -> TranslationResult:
        pair = LanguagePair.of(source_lang, target_lang)
        notes: List[str] = []
        resolved_style = get_style(style or self.default_style)
        resolved_tone = get_tone(tone)
        resolved_emotion = get_emotion(emotion)

        if not text or not text.strip():
            return TranslationResult(
                text="",
                source_lang=pair.source.code,
                target_lang=pair.target.code,
                provider="noop",
                latency_seconds=0.0,
                quality=QualityReport(ok=True, score=1.0, issues=[]),
                notes=["empty input"],
                style=resolved_style.code,
                tone=resolved_tone.code if resolved_tone else None,
                emotion=resolved_emotion.code if resolved_emotion else Emotion.NEUTRAL.value,
                channel_id=channel_id,
            )

        # 1) Translation Memory short-circuit (channel-scoped first).
        tm_hit = False
        if self.translation_memory is not None:
            hit = self.translation_memory.lookup(
                text=text,
                source_lang=pair.source.code,
                target_lang=pair.target.code,
                channel_id=channel_id,
            )
            if hit is not None:
                tm_hit = True
                polished = self._apply_user_glossary(
                    hit.entry.target_text, pair, channel_id, notes
                )
                report = self._maybe_check(text, polished, pair)
                return TranslationResult(
                    text=polished,
                    source_lang=pair.source.code,
                    target_lang=pair.target.code,
                    provider="translation-memory",
                    latency_seconds=0.0,
                    quality=report,
                    fallback_used=False,
                    notes=notes + ["translation memory hit"],
                    style=resolved_style.code,
                    tone=resolved_tone.code if resolved_tone else None,
                    emotion=resolved_emotion.code if resolved_emotion else Emotion.NEUTRAL.value,
                    channel_id=channel_id,
                    tm_hit=True,
                    user_glossary_hits=self._detect_user_terms(polished, pair, channel_id),
                )

        # 2) Provider call (with fallback).
        provider, used_fallback, raw, latency = self._run_with_fallback(
            text=text,
            pair=pair,
            notes=notes,
            style=resolved_style.code,
            tone=resolved_tone.code if resolved_tone else None,
            emotion=resolved_emotion.code if resolved_emotion else None,
        )

        # 3) Static curated glossary post-processing.
        polished = self._postprocess(raw, pair=pair)
        # 4) User glossary post-processing — channel rules win.
        polished = self._apply_user_glossary(polished, pair, channel_id, notes)

        report = self._maybe_check(text, polished, pair)

        if latency > self.latency_budget:
            notes.append(
                f"latency {latency:.3f}s exceeded budget {self.latency_budget:.3f}s"
            )

        return TranslationResult(
            text=polished,
            source_lang=pair.source.code,
            target_lang=pair.target.code,
            provider=provider,
            latency_seconds=latency,
            quality=report,
            fallback_used=used_fallback,
            notes=notes,
            style=resolved_style.code,
            tone=resolved_tone.code if resolved_tone else None,
            emotion=resolved_emotion.code if resolved_emotion else Emotion.NEUTRAL.value,
            channel_id=channel_id,
            tm_hit=tm_hit,
            user_glossary_hits=self._detect_user_terms(polished, pair, channel_id),
        )

    # ------------------------------------------------------------------

    def _run_with_fallback(
        self,
        *,
        text: str,
        pair: LanguagePair,
        notes: List[str],
        style: str,
        tone: Optional[str],
        emotion: Optional[str],
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
                style=style,
                tone=tone,
                emotion=emotion,
            )
            return primary_name, False, translated, time.perf_counter() - start
        except (ProviderUnavailableError, ProviderError) as exc:
            notes.append(f"primary failed: {exc}")
            if self.fallback is None:
                raise

        fallback_name = getattr(self.fallback, "name", "fallback")
        start_fb = time.perf_counter()
        translated = self.fallback.translate(
            text=text,
            source_lang=pair.source.code,
            target_lang=pair.target.code,
            literary=pair.is_priority,
            style=style,
            tone=tone,
            emotion=emotion,
        )
        return fallback_name, True, translated, time.perf_counter() - start_fb

    def _postprocess(self, text: str, *, pair: LanguagePair) -> str:
        if not self.use_glossary or not text:
            return text
        return self.glossary.apply(text, pair.source.code, pair.target.code)

    def _apply_user_glossary(
        self,
        text: str,
        pair: LanguagePair,
        channel_id: Optional[str],
        notes: List[str],
    ) -> str:
        if self.user_glossary is None or not text:
            return text
        try:
            return self.user_glossary.apply(
                text,
                source_lang=pair.source.code,
                target_lang=pair.target.code,
                channel_id=channel_id,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("user glossary apply failed: %s", exc)
            notes.append(f"user glossary error: {exc}")
            return text

    def _detect_user_terms(
        self,
        text: str,
        pair: LanguagePair,
        channel_id: Optional[str],
    ) -> List[str]:
        if self.user_glossary is None or not text:
            return []
        try:
            hits = self.user_glossary.detect_terms(
                text,
                source_lang=pair.source.code,
                target_lang=pair.target.code,
                channel_id=channel_id,
            )
        except Exception:  # noqa: BLE001
            return []
        return [h.target_text for h in hits]

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

    def translate_text(
        self,
        text: str,
        src: str,
        tgt: str,
        *,
        style: Optional[str] = None,
        tone: Optional[str] = None,
        emotion: Optional[str] = None,
        channel_id: Optional[str] = None,
    ) -> str:
        return self.translate(
            text=text,
            source_lang=normalize_language(src),
            target_lang=normalize_language(tgt),
            style=style,
            tone=tone,
            emotion=emotion,
            channel_id=channel_id,
        ).text
