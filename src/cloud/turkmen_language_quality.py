"""Murat AI Studio — туркменский перевод с контролем качества.

Цель модуля: получить **чистый туркменский язык** на выходе, не дословный,
естественный, с правильным тоном/стилем/эмоцией. На VPS подключается
NLLB-200 / MADLAD-400 (Apache 2.0), в preview работают normalize/glossary/style.

Public API:
    detect_source_language(text_or_segments) -> str
    normalize_turkmen_text(text) -> str
    translate_to_clean_turkmen(text, source_lang, style, glossary, emotion_profile) -> str
    validate_turkmen_translation(original_text, turkmen_text, source_lang) -> dict
    repair_turkmen_translation(original_text, turkmen_text, validation_report) -> str
    apply_turkmen_glossary(text, glossary_rules) -> str
    score_turkmen_quality(original_text, turkmen_text) -> int

Стили (TurkmenStyle):
    NEUTRAL / CULTURAL / COLLOQUIAL / OFFICIAL / CINEMA /
    CHILD / NEWS / PROMO / BLOGGER
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Стили туркменского.
# ---------------------------------------------------------------------------
class TurkmenStyle:
    NEUTRAL = "neutral"
    CULTURAL = "cultural"
    COLLOQUIAL = "colloquial"
    OFFICIAL = "official"
    CINEMA = "cinema"
    CHILD = "child"
    NEWS = "news"
    PROMO = "promo"
    BLOGGER = "blogger"


_STYLE_FRAMES = {
    TurkmenStyle.NEUTRAL:    "",
    TurkmenStyle.CULTURAL:   "Hormatly diňleýji, ",
    TurkmenStyle.COLLOQUIAL: "Dostum, ",
    TurkmenStyle.OFFICIAL:   "Resmi habar: ",
    TurkmenStyle.CINEMA:     "(kinodrama) ",
    TurkmenStyle.CHILD:      "Çagajyklar, ",
    TurkmenStyle.NEWS:       "Habar: ",
    TurkmenStyle.PROMO:      "Üns beriň! ",
    TurkmenStyle.BLOGGER:    "Salam dostlar! ",
}


# ---------------------------------------------------------------------------
# Транслит кириллицы для случая если пришёл туркменский в кириллице.
# ---------------------------------------------------------------------------
_CYR_TO_LAT = {
    "а": "a", "б": "b", "в": "w", "г": "g", "д": "d", "е": "e", "ё": "ýo",
    "ж": "ž", "з": "z", "и": "i", "й": "ý", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "h", "ц": "ts", "ч": "ç", "ш": "ş", "щ": "şç", "ъ": "",
    "ы": "y", "ь": "", "э": "e", "ю": "ýu", "я": "ýa",
    "ң": "ň", "ө": "ö", "ү": "ü", "ә": "ä",
}


# ---------------------------------------------------------------------------
# 1) Определение исходного языка.
# ---------------------------------------------------------------------------
def detect_source_language(text_or_segments: Any) -> str:
    """Возвращает 'ru' / 'tk' / 'tr' / 'en' / 'unknown'.

    Эвристика по характерным символам и словам. На VPS лучше подменить
    на langdetect / cld3. Preview-safe.
    """

    if isinstance(text_or_segments, list):
        text = " ".join(seg.get("text", "") for seg in text_or_segments)
    else:
        text = str(text_or_segments or "")
    if not text.strip():
        return "unknown"
    t = text.lower()
    if re.search(r"[ňöüäžş]", t):
        return "tk"
    if re.search(r"[ığşçöü]", t):
        return "tr"
    if re.search(r"[а-яё]", t):
        return "ru"
    if re.search(r"[a-z]", t):
        return "en"
    return "unknown"


# ---------------------------------------------------------------------------
# 2) Нормализация туркменского текста.
# ---------------------------------------------------------------------------
def normalize_turkmen_text(text: str) -> str:
    """Чистит туркменский текст: транслит кириллицы, лишние пробелы, кавычки."""

    if not text:
        return ""
    out = []
    for ch in text:
        low = ch.lower()
        if low in _CYR_TO_LAT:
            rep = _CYR_TO_LAT[low]
            out.append(rep.upper() if ch.isupper() else rep)
        else:
            out.append(ch)
    s = "".join(out)
    s = re.sub(r"\s+", " ", s)
    s = s.replace("«", '"').replace("»", '"').replace("“", '"').replace("”", '"')
    return s.strip()


# ---------------------------------------------------------------------------
# 3) Glossary application.
# ---------------------------------------------------------------------------
def apply_turkmen_glossary(text: str, glossary_rules: List[Dict[str, str]]) -> str:
    """Жёстко заменяет термины. Регистронезависимо. Длиннее — раньше."""

    if not text or not glossary_rules:
        return text or ""
    rules = sorted(
        (r for r in glossary_rules if r.get("from") and r.get("to")),
        key=lambda r: -len(r["from"]),
    )
    out = text
    for r in rules:
        out = re.sub(re.escape(r["from"]), r["to"], out, flags=re.I)
    return out


# ---------------------------------------------------------------------------
# 4) Чистый туркменский перевод.
# ---------------------------------------------------------------------------
def translate_to_clean_turkmen(
    text: str,
    source_lang: str = "ru",
    style: str = TurkmenStyle.CULTURAL,
    glossary: Optional[List[Dict[str, str]]] = None,
    emotion_profile: Optional[Dict[str, Any]] = None,
) -> str:
    """Главная функция: возвращает чистый туркменский текст.

    На VPS подключается NLLB-200 / MADLAD-400. Здесь — preview-safe слой:
    стили, glossary, нормализация, чтобы UI всегда был на туркменском
    (а не на mix-русско-английском).
    """

    if not text or not text.strip():
        return ""

    # 4.1) Если уже туркменский — только нормализация + glossary.
    if source_lang == "tk":
        out = normalize_turkmen_text(text)
        if glossary:
            out = apply_turkmen_glossary(out, glossary)
        return out

    # 4.2) Preview: словарные базы для распространённых фраз.
    base_phrases = {
        ("ru", "Привет"):    "Salam",
        ("ru", "Здравствуйте"): "Hormatly dostum",
        ("ru", "Спасибо"):   "Sag boluň",
        ("en", "Hello"):     "Salam",
        ("en", "Thank you"): "Sag boluň",
        ("tr", "Merhaba"):   "Salam",
    }

    # Простой morph-free перевод фразы целиком — это mock-уровень для preview.
    # На VPS этот вызов заменяется на model.generate(...).
    out = (
        f"{_STYLE_FRAMES.get(style, '')}"
        "Salam. Men bu mazmuny professional derejede türkmen diline geçirýärin "
        "we şol bir duýgy bilen seslendirmek isleýärin."
    )

    if glossary:
        out = apply_turkmen_glossary(out, glossary)
    out = normalize_turkmen_text(out)
    return out


# ---------------------------------------------------------------------------
# 5) Validation report.
# ---------------------------------------------------------------------------
@dataclass
class ValidationReport:
    quality_score: int
    meaning_match: int
    language_purity: int
    style_match: int
    issues: List[str]


def validate_turkmen_translation(
    original_text: str, turkmen_text: str, source_lang: str = "ru"
) -> Dict[str, Any]:
    """Возвращает report по правилам:

    - language_purity: нет русских/английских слов внутри туркменского.
    - meaning_match: длина перевода в разумных границах от оригинала.
    - issues: список проблем.
    """

    issues: List[str] = []
    purity = 100
    meaning = 100
    style = 100

    if not turkmen_text or not turkmen_text.strip():
        return {
            "quality_score": 0,
            "meaning_match": 0,
            "language_purity": 0,
            "style_match": 0,
            "issues": ["Туркменский перевод пустой."],
        }

    # 5.1) Чистота языка — никакой кириллицы.
    cyr = re.findall(r"[а-яёА-ЯЁ]+", turkmen_text)
    if cyr:
        purity -= min(50, 10 * len(cyr))
        issues.append(f"Кириллица в туркменском: {', '.join(cyr[:5])}")

    # 5.2) Случайные английские слова (грубая эвристика).
    eng_words = [w for w in re.findall(r"[A-Za-z]{3,}", turkmen_text) if w.lower() not in {"murat", "ai", "studio", "mp4", "wav", "srt"}]
    suspect_eng = [w for w in eng_words if w[0].islower() and w not in {"www", "com", "tk", "ru", "en"}]
    if suspect_eng:
        purity -= min(30, 5 * len(suspect_eng))
        issues.append(f"Возможно английский внутри туркменского: {', '.join(suspect_eng[:5])}")

    # 5.3) Соответствие смысла по длине.
    src_len = len(original_text or "")
    tk_len = len(turkmen_text)
    if src_len > 0:
        ratio = tk_len / src_len
        if ratio < 0.4:
            meaning -= 40
            issues.append("Туркменский перевод подозрительно короткий.")
        elif ratio > 2.5:
            meaning -= 25
            issues.append("Туркменский перевод подозрительно длинный.")

    # 5.4) Повторы слов 3+ раза подряд.
    repeats = re.findall(r"\b(\w+)\s+\1\s+\1\b", turkmen_text, flags=re.I)
    if repeats:
        style -= 20
        issues.append(f"Повторы слов: {', '.join(set(repeats))}")

    quality = max(0, int(0.4 * purity + 0.4 * meaning + 0.2 * style))
    return {
        "quality_score": quality,
        "meaning_match": meaning,
        "language_purity": purity,
        "style_match": style,
        "issues": issues,
    }


# ---------------------------------------------------------------------------
# 6) Repair after validation.
# ---------------------------------------------------------------------------
def repair_turkmen_translation(
    original_text: str, turkmen_text: str, validation_report: Dict[str, Any]
) -> str:
    """Простой пост-процессинг: транслит кириллицы, чистка пробелов, повторов."""

    out = normalize_turkmen_text(turkmen_text)
    # Удалить тройные повторы слов.
    out = re.sub(r"\b(\w+)(\s+\1){2,}", r"\1", out, flags=re.I)
    # Если кириллица всё ещё есть — заменяем на безопасный fallback.
    if re.search(r"[а-яё]", out, flags=re.I):
        out = translate_to_clean_turkmen(original_text or out, source_lang="ru")
    return out


# ---------------------------------------------------------------------------
# 7) Quick quality score.
# ---------------------------------------------------------------------------
def score_turkmen_quality(original_text: str, turkmen_text: str) -> int:
    return validate_turkmen_translation(original_text, turkmen_text)["quality_score"]
