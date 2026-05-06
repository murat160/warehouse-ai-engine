"""NLLB-200 routing and language-code mapping for the cloud MVP."""

from __future__ import annotations

from itertools import permutations
from typing import Dict, FrozenSet, Tuple

# We use a single multilingual model for every direction. Listing the routes
# explicitly keeps room to swap individual pairs to a stronger checkpoint
# (for example, a future ru<->tk LoRA fine-tune) without touching call sites.
NLLB_MODEL = "facebook/nllb-200-distilled-600M"

LANG_CODE_MAP: Dict[str, str] = {
    "ru": "rus_Cyrl",
    "tk": "tuk_Latn",
    "tr": "tur_Latn",
    "en": "eng_Latn",
}

# Every ordered pair of {ru, tk, tr, en} is supported (12 directions). The
# value is the model id to use; defaulting to NLLB-200 across the board.
SUPPORTED_ROUTES: Dict[Tuple[str, str], str] = {
    pair: NLLB_MODEL for pair in permutations(LANG_CODE_MAP.keys(), 2)
}

SUPPORTED_LANGS: FrozenSet[str] = frozenset(LANG_CODE_MAP.keys())
