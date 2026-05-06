"""Lightweight post-translation quality checks.

These checks are heuristics, not a real evaluation metric — their job is to
flag obviously broken output (empty, untranslated, script mismatch, length
explosion) so callers can fall back to another provider or warn the user.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List

# Scripts: rough character class for each language we care about.
_CYRILLIC = re.compile(r"[Ѐ-ӿ]")
_LATIN = re.compile(r"[A-Za-zÄÇĞİÖŞÜÝŇä-ÿýňğşöüçı]")
_TK_DIACRITICS = re.compile(r"[äÄýÝňŇöÖüÜçÇşŞ]")


@dataclass
class QualityReport:
    ok: bool
    score: float  # 0.0 .. 1.0
    issues: List[str]

    def as_dict(self) -> dict:
        return {"ok": self.ok, "score": round(self.score, 3), "issues": list(self.issues)}


def check(
    *,
    source_text: str,
    translated_text: str,
    source_lang: str,
    target_lang: str,
) -> QualityReport:
    """Run a fast, conservative quality assessment of a translation."""

    issues: List[str] = []
    if translated_text is None or not translated_text.strip():
        return QualityReport(ok=False, score=0.0, issues=["empty translation"])

    src = (source_text or "").strip()
    out = translated_text.strip()

    # 1) Length sanity: extreme expansion/contraction usually means the model
    #    refused, repeated itself, or echoed the prompt.
    if src:
        ratio = len(out) / max(len(src), 1)
        if ratio < 0.25:
            issues.append(f"output too short (ratio={ratio:.2f})")
        elif ratio > 4.0:
            issues.append(f"output too long (ratio={ratio:.2f})")

    # 2) "Untranslated" guard: when the model returned the source verbatim.
    if src and out.lower() == src.lower():
        issues.append("output equals source")

    # 3) Script check per target language.
    if target_lang == "ru":
        if not _CYRILLIC.search(out):
            issues.append("expected Cyrillic in Russian output")
    elif target_lang in {"tk", "tr", "en"}:
        if not _LATIN.search(out):
            issues.append("expected Latin script in target output")
        if _CYRILLIC.search(out):
            issues.append("unexpected Cyrillic in Latin-script output")

    # 4) Turkmen literary cue: well-formed Turkmen text usually contains at
    #    least one of its characteristic diacritics within ~80 characters.
    if target_lang == "tk" and len(out) >= 80 and not _TK_DIACRITICS.search(out):
        issues.append("Turkmen output lacks diacritics — possibly machine-rough")

    # Score: 1.0 minus 0.2 per issue, floored at 0.0.
    score = max(0.0, 1.0 - 0.2 * len(issues))
    return QualityReport(ok=not issues, score=score, issues=issues)
