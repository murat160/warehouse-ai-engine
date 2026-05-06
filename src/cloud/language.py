"""Lightweight language detection wrapper.

``langdetect`` does not ship a Turkmen model — when the input is actually
Turkmen we fall back to ``"tk"`` only if the caller explicitly asks for it
elsewhere. For ru/en/tr the library is reliable enough for routing.
"""

from __future__ import annotations

from langdetect import DetectorFactory, detect

# Make detection deterministic so identical input always routes the same way.
DetectorFactory.seed = 0


def detect_lang(text: str) -> str:
    if not text or not text.strip():
        return "unknown"
    try:
        code = detect(text)
    except Exception:
        return "unknown"
    if code in {"ru", "en", "tr"}:
        return code
    # langdetect has no native Turkmen model; treat anything else as unknown
    # so callers can decide how to route (e.g. ask the user).
    return "unknown"
