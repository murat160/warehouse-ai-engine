"""Murat AI Studio — словарь и правила замены терминов на туркменский.

Хранение: in-memory dict, key = (project_id, scope). На VPS подменяется
на Postgres-репозиторий из src.storage.

Scopes: 'global' | 'project' | 'channel' | 'actor'.

Public API:
    load_glossary(project_id, scope='global') -> list[dict]
    save_glossary_rule(source_word, target_word, scope, project_id=None) -> dict
    apply_glossary(text, scope='global', project_id=None) -> str
    auto_detect_terms(text) -> list[str]
    suggest_turkmen_terms(terms) -> dict[str, str]
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional

# In-memory store. {(project_id, scope): [{from, to, scope}, ...]}
_STORE: Dict[tuple, List[Dict[str, str]]] = {}


@dataclass
class GlossaryRule:
    id: str
    source_word: str
    target_word: str
    scope: str
    project_id: Optional[str] = None
    channel_id: Optional[str] = None
    actor_id: Optional[str] = None
    notes: str = ""


# Базовый встроенный туркменский glossary — частые термины из IT/блогинга/видео.
_BUILTIN_TM_TERMS: Dict[str, str] = {
    "видео":         "wideo",
    "канал":         "kanal",
    "подписка":      "abuna",
    "лайк":          "halajakdyr",
    "комментарий":   "düşündiriş",
    "магазин":       "dükan",
    "товар":         "haryt",
    "цена":          "baha",
    "скидка":        "arzanladyş",
    "качество":      "hil",
    "доставка":      "eltip bermek",
    "заказ":         "buýurma",
    "клиент":        "müşderi",
    "продавец":      "satyjy",
    "курьер":        "kurýer",
    "пункт выдачи":  "alyş nokady",
    "Здравствуйте":  "Salam",
    "Привет":        "Salam",
    "Спасибо":       "Sag boluň",
    "Пожалуйста":    "Hoş geldiňiz",
    "Hello":         "Salam",
    "Thank you":     "Sag boluň",
    "Merhaba":       "Salam",
}


# ---------------------------------------------------------------------------
# API.
# ---------------------------------------------------------------------------
def load_glossary(project_id: Optional[str] = None, scope: str = "global") -> List[Dict[str, str]]:
    """Возвращает merged glossary: built-in + сохранённые правила scope."""

    saved = _STORE.get((project_id, scope), [])
    builtin = [{"id": f"builtin_{i}", "from": k, "to": v, "scope": "builtin"} for i, (k, v) in enumerate(_BUILTIN_TM_TERMS.items())]
    return builtin + saved


def save_glossary_rule(
    source_word: str,
    target_word: str,
    scope: str = "global",
    project_id: Optional[str] = None,
    channel_id: Optional[str] = None,
    actor_id: Optional[str] = None,
) -> Dict[str, str]:
    if not source_word or not target_word:
        raise ValueError("source_word и target_word обязательны")
    rule = {
        "id": f"rule_{uuid.uuid4().hex[:8]}",
        "from": source_word.strip(),
        "to": target_word.strip(),
        "scope": scope,
        "project_id": project_id,
        "channel_id": channel_id,
        "actor_id": actor_id,
    }
    key = (project_id, scope)
    _STORE.setdefault(key, []).append(rule)
    return rule


def apply_glossary(text: str, scope: str = "global", project_id: Optional[str] = None) -> str:
    """Применяет правила scope (+ all upper scopes) к тексту."""

    if not text:
        return text or ""
    rules = []
    rules += load_glossary(project_id, scope)
    if scope != "global":
        rules += load_glossary(project_id, "global")
    seen: set = set()
    out = text
    # Длиннее — раньше, чтобы фразы не разваливались.
    for rule in sorted(rules, key=lambda r: -len(r["from"])):
        if rule["from"] in seen:
            continue
        seen.add(rule["from"])
        out = re.sub(re.escape(rule["from"]), rule["to"], out, flags=re.I)
    return out


def auto_detect_terms(text: str) -> List[str]:
    """Выделяет термины-кандидаты: capitalized words длиннее 3 символов."""

    if not text:
        return []
    terms = re.findall(r"\b[A-ZА-ЯЁ][a-zа-яё]{3,}\b", text)
    return sorted(set(terms))


def suggest_turkmen_terms(terms: List[str]) -> Dict[str, str]:
    """Возвращает предложения переводов из встроенной базы."""

    suggestions: Dict[str, str] = {}
    for term in terms or []:
        lower = term.lower()
        for k, v in _BUILTIN_TM_TERMS.items():
            if k.lower() == lower:
                suggestions[term] = v
                break
    return suggestions
