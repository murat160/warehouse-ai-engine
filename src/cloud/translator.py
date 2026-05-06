"""NLLB-200 powered translation service for the cloud MVP.

Loads each underlying model on first use and caches it in process memory.
Designed to run on CPU; pass ``device="cuda"`` to move weights to a GPU.
"""

from __future__ import annotations

import logging
from typing import Dict, Tuple

import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

from .config import LANG_CODE_MAP, SUPPORTED_ROUTES

logger = logging.getLogger(__name__)


class TranslatorService:
    """Translate text between any of the supported (ru/tk/tr/en) languages."""

    def __init__(self, *, device: str = "cpu", num_beams: int = 4) -> None:
        self.device = device
        self.num_beams = num_beams
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

    def translate(self, text: str, src: str, tgt: str) -> str:
        if not text or not text.strip():
            return ""
        route = (src, tgt)
        if route not in SUPPORTED_ROUTES:
            raise ValueError(
                f"unsupported route: {src}->{tgt}. "
                f"supported: {sorted(SUPPORTED_ROUTES.keys())}"
            )
        if src not in LANG_CODE_MAP or tgt not in LANG_CODE_MAP:
            raise ValueError(f"unsupported language pair: {src}->{tgt}")

        tok, mdl = self._load(SUPPORTED_ROUTES[route])
        tok.src_lang = LANG_CODE_MAP[src]
        inputs = tok(
            text,
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
        return tok.batch_decode(out, skip_special_tokens=True)[0].strip()
