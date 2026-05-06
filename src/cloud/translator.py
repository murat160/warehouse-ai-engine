"""NLLB-200 powered translation service for the cloud MVP (channel-aware).

Loads the model on first use and caches it. Honours user glossary, TM,
channel-scoping, style / tone / emotion (style/tone/emotion are surfaced
on the result for display; NLLB has no native control over them, so the
glossary + TM are the practical enforcement points).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

from ..translator.styles import (
    Emotion,
    StyleProfile,
    get_emotion,
    get_style,
    get_tone,
)
from ..translator.translation_memory import TranslationMemoryService
from ..translator.user_glossary import UserGlossaryService
from .config import LANG_CODE_MAP, SUPPORTED_ROUTES

logger = logging.getLogger(__name__)


@dataclass
class CloudTranslationResult:
    text: str
    source_lang: str
    target_lang: str
    style: str
    tone: Optional[str] = None
    emotion: str = Emotion.NEUTRAL.value
    channel_id: Optional[str] = None
    tm_hit: bool = False
    user_glossary_hits: List[str] = field(default_factory=list)
    provider: str = "nllb-200"


class TranslatorService:
    """Translate text between any of the supported (ru/tk/tr/en) languages."""

    def __init__(
        self,
        *,
        device: str = "cpu",
        num_beams: int = 4,
        user_glossary: Optional[UserGlossaryService] = None,
        translation_memory: Optional[TranslationMemoryService] = None,
    ) -> None:
        self.device = device
        self.num_beams = num_beams
        self.user_glossary = user_glossary
        self.translation_memory = translation_memory
        self._cache: Dict[str, Tuple[AutoTokenizer, AutoModelForSeq2SeqLM]] = {}

    def _load(self, model_name: str):
        if model_name in self._cache:
            return self._cache[model_name]
        logger.info("loading translation model %s", model_name)
        tok = AutoTokenizer.from_pretrained(model_name)
        mdl = AutoModelForSeq2SeqLM.from_pretrained(model_name).to(self.device)
        mdl.eval()
        self._cache[model_name] = (tok, mdl)
        return tok, mdl

    def translate(
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
        return self.translate_full(
            text, src, tgt,
            style=style, tone=tone, emotion=emotion, channel_id=channel_id,
        ).text

    def translate_full(
        self,
        text: str,
        src: str,
        tgt: str,
        *,
        style: Optional[str] = None,
        tone: Optional[str] = None,
        emotion: Optional[str] = None,
        channel_id: Optional[str] = None,
    ) -> CloudTranslationResult:
        profile = get_style(style)
        tone_profile = get_tone(tone)
        emotion_profile = get_emotion(emotion)
        emotion_code = emotion_profile.code if emotion_profile else Emotion.NEUTRAL.value

        if not text or not text.strip():
            return CloudTranslationResult(
                text="",
                source_lang=src,
                target_lang=tgt,
                style=profile.code,
                tone=tone_profile.code if tone_profile else None,
                emotion=emotion_code,
                channel_id=channel_id,
            )

        route = (src, tgt)
        if route not in SUPPORTED_ROUTES:
            raise ValueError(
                f"unsupported route: {src}->{tgt}. "
                f"supported: {sorted(SUPPORTED_ROUTES.keys())}"
            )
        if src not in LANG_CODE_MAP or tgt not in LANG_CODE_MAP:
            raise ValueError(f"unsupported language pair: {src}->{tgt}")

        # 1) Translation memory short-circuit (channel-scoped first).
        if self.translation_memory is not None:
            hit = self.translation_memory.lookup(
                text=text,
                source_lang=src,
                target_lang=tgt,
                channel_id=channel_id,
            )
            if hit is not None:
                polished = self._apply_user_glossary(
                    hit.entry.target_text, src, tgt, channel_id
                )
                return CloudTranslationResult(
                    text=polished,
                    source_lang=src,
                    target_lang=tgt,
                    style=profile.code,
                    tone=tone_profile.code if tone_profile else None,
                    emotion=emotion_code,
                    channel_id=channel_id,
                    tm_hit=True,
                    user_glossary_hits=self._detect_user_terms(polished, src, tgt, channel_id),
                    provider="translation-memory",
                )

        # 2) NLLB-200 generation.
        tok, mdl = self._load(SUPPORTED_ROUTES[route])
        tok.src_lang = LANG_CODE_MAP[src]
        framed = self._frame_for_style(text, profile)
        inputs = tok(
            framed,
            return_tensors="pt",
            truncation=True,
            max_length=512,
        ).to(self.device)
        with torch.no_grad():
            out = mdl.generate(
                **inputs,
                forced_bos_token_id=tok.convert_tokens_to_ids(LANG_CODE_MAP[tgt]),
                max_length=512,
                num_beams=self.num_beams,
            )
        decoded = tok.batch_decode(out, skip_special_tokens=True)[0].strip()

        # 3) User glossary post-processing.
        polished = self._apply_user_glossary(decoded, src, tgt, channel_id)

        return CloudTranslationResult(
            text=polished,
            source_lang=src,
            target_lang=tgt,
            style=profile.code,
            tone=tone_profile.code if tone_profile else None,
            emotion=emotion_code,
            channel_id=channel_id,
            tm_hit=False,
            user_glossary_hits=self._detect_user_terms(polished, src, tgt, channel_id),
        )

    @staticmethod
    def _frame_for_style(text: str, profile: StyleProfile) -> str:
        return text  # NLLB has no native style control; rely on glossary/TM.

    def _apply_user_glossary(
        self, text: str, src: str, tgt: str, channel_id: Optional[str]
    ) -> str:
        if self.user_glossary is None or not text:
            return text
        try:
            return self.user_glossary.apply(
                text, source_lang=src, target_lang=tgt, channel_id=channel_id
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("user glossary apply failed: %s", exc)
            return text

    def _detect_user_terms(
        self, text: str, src: str, tgt: str, channel_id: Optional[str]
    ) -> List[str]:
        if self.user_glossary is None or not text:
            return []
        try:
            return [
                e.target_text
                for e in self.user_glossary.detect_terms(
                    text, source_lang=src, target_lang=tgt, channel_id=channel_id,
                )
            ]
        except Exception:  # noqa: BLE001
            return []
