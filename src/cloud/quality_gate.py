"""Murat AI Studio — Quality Gate для туркменского перевода.

Каждый перевод обязан пройти gate. Возвращается отчёт:

    {
        "quality_score": 0-100,
        "meaning_match": 0-100,
        "language_purity": 0-100,
        "style_match": 0-100,
        "emotion_match": 0-100,
        "timing_fit": 0-100,
        "issues": [...],
        "fixed_text": "..."
    }

Пороги:
    >= 95 — допускается в preview
    >= 98 — допускается в production
    < 95  — система должна repair + повторить gate

Public API:
    run_translation_quality_gate(original, turkmen, source_lang, emotion=None, segment_dur=None) -> dict
    check_missing_meaning(original, turkmen) -> int
    check_extra_meaning(original, turkmen) -> int
    check_wrong_language_mix(turkmen) -> tuple[int, list[str]]
    check_repeated_words(turkmen) -> tuple[int, list[str]]
    check_style_match(original, turkmen, target_style) -> int
    check_emotion_match(original_emotion, turkmen) -> int
    check_timing_fit(turkmen, segment_duration_sec) -> int
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from .turkmen_language_quality import (
    normalize_turkmen_text,
    repair_turkmen_translation,
    validate_turkmen_translation,
)

PREVIEW_THRESHOLD = 95
PRODUCTION_THRESHOLD = 98
MAX_REPAIR_ITERATIONS = 3


# ---------------------------------------------------------------------------
# Атомарные чеки.
# ---------------------------------------------------------------------------
def check_missing_meaning(original: str, turkmen: str) -> int:
    """Оценивает не потерян ли смысл по соотношению длин и числу слов."""

    if not original:
        return 100
    src_words = len(original.split())
    tk_words = len(turkmen.split())
    if src_words == 0:
        return 100
    ratio = tk_words / src_words
    if ratio >= 0.8:
        return 100
    if ratio >= 0.6:
        return 90
    if ratio >= 0.4:
        return 70
    return 40


def check_extra_meaning(original: str, turkmen: str) -> int:
    src_words = max(1, len(original.split()))
    tk_words = len(turkmen.split())
    ratio = tk_words / src_words
    if ratio <= 1.6:
        return 100
    if ratio <= 2.2:
        return 85
    if ratio <= 3.0:
        return 60
    return 40


def check_wrong_language_mix(turkmen: str) -> Tuple[int, List[str]]:
    issues: List[str] = []
    score = 100
    cyr = re.findall(r"[а-яёА-ЯЁ]+", turkmen)
    if cyr:
        score -= min(60, 10 * len(cyr))
        issues.append(f"Кириллица: {', '.join(cyr[:5])}")
    allowed = {"murat", "ai", "studio", "mp4", "wav", "mp3", "srt", "vtt"}
    eng = [w for w in re.findall(r"\b[A-Za-z]{3,}\b", turkmen) if w.lower() not in allowed]
    bad_eng = [w for w in eng if w[0].islower()]
    if bad_eng:
        score -= min(40, 6 * len(bad_eng))
        issues.append(f"Английские слова: {', '.join(bad_eng[:5])}")
    return max(0, score), issues


def check_repeated_words(turkmen: str) -> Tuple[int, List[str]]:
    issues: List[str] = []
    repeats = re.findall(r"\b(\w{3,})(\s+\1){2,}", turkmen, flags=re.I)
    if not repeats:
        return 100, issues
    words = sorted({m[0] for m in repeats})
    issues.append(f"Повторы 3+ раз: {', '.join(words)}")
    return max(40, 100 - 15 * len(words)), issues


def check_style_match(original: str, turkmen: str, target_style: Optional[str] = None) -> int:
    if not target_style:
        return 100
    markers = {
        "cinema":  ["kinodrama", "kino"],
        "child":   ["çagajyk", "balajyk"],
        "official":["resmi", "hormatly"],
        "news":    ["habar", "ýaýlyşda"],
        "promo":   ["üns beriň", "arzanlady"],
        "blogger": ["dostlar", "kanal"],
    }
    needed = markers.get(target_style, [])
    if not needed:
        return 100
    found = sum(1 for m in needed if m.lower() in turkmen.lower())
    return 100 if found else 75


def check_emotion_match(original_emotion: Optional[str], turkmen: str) -> int:
    if not original_emotion or original_emotion.lower() in {"neutral", "нейтрально"}:
        return 100
    sad = ["gyn", "gam", "agla"]
    angry = ["gaz", "gahar"]
    happy = ["şat", "begenç", "şatlykly"]
    pool = {
        "happy": happy, "радостно": happy,
        "sad": sad, "грустно": sad,
        "angry": angry, "злой тон": angry,
    }
    needed = pool.get(original_emotion.lower(), [])
    if not needed:
        return 100
    found = any(n in turkmen.lower() for n in needed)
    return 100 if found else 80


def check_timing_fit(turkmen: str, segment_duration_sec: Optional[float]) -> int:
    if not segment_duration_sec or segment_duration_sec <= 0:
        return 100
    # ~14 знаков/сек для туркменского как комфортный темп.
    target = segment_duration_sec * 14
    actual = len(turkmen)
    diff = abs(actual - target) / max(1.0, target)
    if diff <= 0.15:
        return 100
    if diff <= 0.30:
        return 85
    if diff <= 0.50:
        return 65
    return 40


# ---------------------------------------------------------------------------
# Главный gate.
# ---------------------------------------------------------------------------
def run_translation_quality_gate(
    original: str,
    turkmen: str,
    source_lang: str = "ru",
    emotion: Optional[str] = None,
    style: Optional[str] = None,
    segment_duration_sec: Optional[float] = None,
) -> Dict[str, Any]:
    """Запускает все чеки и при необходимости — repair-loop."""

    text = normalize_turkmen_text(turkmen)
    fixed = text
    all_issues: List[str] = []

    for _iter in range(MAX_REPAIR_ITERATIONS):
        meaning = min(check_missing_meaning(original, fixed), check_extra_meaning(original, fixed))
        purity, purity_issues = check_wrong_language_mix(fixed)
        repeats, repeat_issues = check_repeated_words(fixed)
        style_score = check_style_match(original, fixed, style)
        emotion_score = check_emotion_match(emotion, fixed)
        timing = check_timing_fit(fixed, segment_duration_sec)

        iter_issues = purity_issues + repeat_issues
        all_issues = iter_issues

        quality = int(
            0.30 * meaning
            + 0.25 * purity
            + 0.15 * style_score
            + 0.15 * emotion_score
            + 0.10 * timing
            + 0.05 * repeats
        )

        if quality >= PREVIEW_THRESHOLD or not all_issues:
            break

        # Repair и повторяем gate.
        report = validate_turkmen_translation(original, fixed, source_lang)
        fixed = repair_turkmen_translation(original, fixed, report)

    return {
        "quality_score": quality,
        "meaning_match": meaning,
        "language_purity": purity,
        "style_match": style_score,
        "emotion_match": emotion_score,
        "timing_fit": timing,
        "issues": all_issues,
        "fixed_text": fixed,
        "passed_preview": quality >= PREVIEW_THRESHOLD,
        "passed_production": quality >= PRODUCTION_THRESHOLD,
    }
