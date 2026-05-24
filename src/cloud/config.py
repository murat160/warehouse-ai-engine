"""Translation model routing and language-code mapping for Murat AI.

The default translation backend is **MADLAD-400** by Google
(``google/madlad400-3b-mt``), released under **Apache 2.0** — permissive,
commercial-friendly, no attribution-required clauses beyond the standard
notice. It covers 400+ languages including Turkmen, Russian, Turkish and
English, so a single checkpoint serves every pair we care about.

History note: earlier revisions used ``facebook/nllb-200-distilled-600M``
which ships under **CC-BY-NC 4.0** (non-commercial only). MADLAD-400 is a
drop-in replacement with the same multilingual coverage and a permissive
licence, so Murat AI is now licence-clean by default. The NLLB id remains
available as an opt-in override (``MURAT_AI_TRANSLATION_MODEL=facebook/nllb-200-distilled-600M``)
for users who explicitly accept the CC-BY-NC terms.
"""

from __future__ import annotations

import os
from itertools import permutations
from typing import Dict, FrozenSet, Tuple

# ---------------------------------------------------------------------------
# Active translation checkpoint
# ---------------------------------------------------------------------------

# Apache 2.0, 400+ languages, Turkmen included.
MADLAD_MODEL = "google/madlad400-3b-mt"

# Operators can override (e.g. swap in a fine-tune they trained) without
# touching code: set MURAT_AI_TRANSLATION_MODEL in .env.production.
TRANSLATION_MODEL = os.environ.get("MURAT_AI_TRANSLATION_MODEL", MADLAD_MODEL)

# True when the configured model is the MADLAD family. MADLAD uses an
# inline target-language tag (``<2tk> hello``) instead of NLLB's
# ``forced_bos_token_id`` — the translator service branches on this flag.
USE_MADLAD = TRANSLATION_MODEL.startswith("google/madlad400")


# ---------------------------------------------------------------------------
# Language codes per backend
# ---------------------------------------------------------------------------

# ISO 639-1 codes the rest of Murat AI works with.
SUPPORTED_LANGS: FrozenSet[str] = frozenset({"ru", "tk", "tr", "en"})

# MADLAD-400 expects the target language as an inline tag at the start of
# the source text, e.g. ``<2tk> Hello, world!`` to translate to Turkmen.
# Source language is NOT tagged — the model detects it.
MADLAD_TARGET_TAGS: Dict[str, str] = {
    "ru": "<2ru>",
    "tk": "<2tk>",
    "tr": "<2tr>",
    "en": "<2en>",
}

# NLLB-200 BCP-47 codes — only used when an operator has explicitly opted
# in to the NLLB checkpoint via MURAT_AI_TRANSLATION_MODEL. Kept here so
# the translator service can serve both backends from the same config.
NLLB_LANG_CODES: Dict[str, str] = {
    "ru": "rus_Cyrl",
    "tk": "tuk_Latn",
    "tr": "tur_Latn",
    "en": "eng_Latn",
}

# Back-compat alias — older modules still import LANG_CODE_MAP. It now
# points at whichever map matches the active backend.
LANG_CODE_MAP: Dict[str, str] = MADLAD_TARGET_TAGS if USE_MADLAD else NLLB_LANG_CODES

# Every ordered pair of supported languages is served by the same model.
SUPPORTED_ROUTES: Dict[Tuple[str, str], str] = {
    pair: TRANSLATION_MODEL for pair in permutations(SUPPORTED_LANGS, 2)
}
