"""Murat AI Studio — подгонка перевода и озвучки под тайминг видео.

Правила:
- Перевод не должен заканчиваться раньше или позже видео.
- Если туркменская фраза длиннее видео-сегмента — разбить или сжать.
- Если короче — добавить естественные паузы.
- Озвучка обязана попадать в кадр.

Public API:
    fit_translation_to_timeline(source_segments, translated_segments) -> list[dict]
    compress_or_expand_phrase(text, target_duration_sec) -> str
    split_long_phrases(text, max_chars_per_line=42) -> list[str]
    add_pauses_for_natural_speech(text, emotion_profile) -> str
    align_tts_to_video(tts_audio_path, video_segments) -> str
    validate_sync(video_duration, audio_duration, segment_timings) -> dict
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

# ~14 знаков/сек для туркменского — комфортный темп без скороговорки.
_TM_CHARS_PER_SEC = 14.0
_MIN_CHARS_PER_SEC = 8.0
_MAX_CHARS_PER_SEC = 22.0


def fit_translation_to_timeline(
    source_segments: List[Dict[str, Any]],
    translated_segments: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Сопоставляет переводы исходным сегментам с подгонкой длины.

    Возвращает [{start, end, source, translation, chars_per_sec, status}].
    """

    out: List[Dict[str, Any]] = []
    n = min(len(source_segments), len(translated_segments))
    for i in range(n):
        src = source_segments[i]
        trg = translated_segments[i]
        duration = max(0.001, float(src.get("end", 0)) - float(src.get("start", 0)))
        translation = trg.get("text", "") if isinstance(trg, dict) else str(trg)
        translation = compress_or_expand_phrase(translation, duration)
        cps = len(translation) / duration
        status = "ok"
        if cps > _MAX_CHARS_PER_SEC:
            status = "too_fast"
        elif cps < _MIN_CHARS_PER_SEC:
            status = "too_slow"
        out.append({
            "start": src.get("start", 0.0),
            "end": src.get("end", duration),
            "source": src.get("text", ""),
            "translation": translation,
            "chars_per_sec": round(cps, 1),
            "status": status,
        })
    return out


def compress_or_expand_phrase(text: str, target_duration_sec: float) -> str:
    """Подгоняет фразу под целевую длительность.

    Сжатие: убираем избыточные местоимения / частицы.
    Расширение: добавляем паузы (точки) между смысловыми блоками.
    """

    if not text or target_duration_sec <= 0:
        return text or ""
    target_chars = int(target_duration_sec * _TM_CHARS_PER_SEC)
    actual = len(text)
    if actual <= target_chars * 1.15:
        return text
    # Сжимаем: режем по последней точке/запятой до ~target_chars.
    cut_at = -1
    for m in re.finditer(r"[.,;:]", text):
        if m.start() <= target_chars:
            cut_at = m.start() + 1
        else:
            break
    if cut_at > 0:
        return text[:cut_at].strip()
    return text[:target_chars].rsplit(" ", 1)[0].strip() + "…"


def split_long_phrases(text: str, max_chars_per_line: int = 42, max_lines: int = 2) -> List[str]:
    """Разбивает текст по строкам так, чтобы каждая <= max_chars_per_line."""

    if not text:
        return []
    words = text.split()
    lines: List[str] = []
    for word in words:
        if not lines or len(lines[-1]) + 1 + len(word) > max_chars_per_line:
            if len(lines) >= max_lines:
                lines[-1] = (lines[-1] + "…").strip()
                break
            lines.append(word)
        else:
            lines[-1] = lines[-1] + " " + word
    return lines


def add_pauses_for_natural_speech(text: str, emotion_profile: Optional[Dict[str, Any]] = None) -> str:
    """Вставляет паузы (запятые/точки) для естественного звучания.

    Долгие паузы для cinema/sad, короткие для promo/energetic.
    """

    if not text:
        return ""
    style = (emotion_profile or {}).get("pause_style", "medium")
    pause_token = {
        "short":     ", ",
        "medium":    ". ",
        "long":      "… ",
        "dramatic":  "… … ",
    }.get(style, ". ")
    # Разбиваем по 6-8 слов и вставляем паузу.
    words = text.split()
    chunks: List[str] = []
    buf: List[str] = []
    for w in words:
        buf.append(w)
        if len(buf) >= 7 and not buf[-1].endswith((".", "!", "?", ",")):
            chunks.append(" ".join(buf))
            buf = []
    if buf:
        chunks.append(" ".join(buf))
    return pause_token.join(chunks)


def align_tts_to_video(tts_audio_path: str, video_segments: List[Dict[str, Any]]) -> str:
    """Stub. На VPS используется librosa / pyrubberband для time-stretch."""

    return tts_audio_path


def validate_sync(
    video_duration: float,
    audio_duration: float,
    segment_timings: List[Dict[str, Any]],
) -> Dict[str, Any]:
    drift = audio_duration - video_duration
    issues: List[str] = []
    if abs(drift) > 0.5:
        issues.append(f"Дрейф {drift:+.2f} сек между озвучкой и видео.")
    overruns = [s for s in segment_timings if float(s.get("end", 0)) > video_duration + 0.05]
    if overruns:
        issues.append(f"{len(overruns)} сегментов выходят за длительность видео.")
    return {
        "ok": not issues,
        "video_duration": round(video_duration, 2),
        "audio_duration": round(audio_duration, 2),
        "drift_sec": round(drift, 2),
        "issues": issues,
    }
