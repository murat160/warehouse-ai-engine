"""Subtitle (SRT / WebVTT) generation from STT segments."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

from ..providers.base import TranscriptSegment


@dataclass(frozen=True)
class SubtitleEntry:
    index: int
    start: float
    end: float
    text: str


def from_segments(segments: Iterable[TranscriptSegment]) -> List[SubtitleEntry]:
    entries: List[SubtitleEntry] = []
    for i, s in enumerate(segments, start=1):
        text = (s.text or "").strip()
        if not text:
            continue
        entries.append(SubtitleEntry(index=i, start=s.start, end=s.end, text=text))
    return entries


def _format_time(seconds: float, *, sep: str) -> str:
    if seconds < 0:
        seconds = 0.0
    total_ms = int(round(seconds * 1000))
    hours, rem = divmod(total_ms, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, ms = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}{sep}{ms:03d}"


def build_srt(entries: Iterable[SubtitleEntry]) -> str:
    out: List[str] = []
    for e in entries:
        out.append(str(e.index))
        out.append(f"{_format_time(e.start, sep=',')} --> {_format_time(e.end, sep=',')}")
        out.append(e.text)
        out.append("")
    return "\n".join(out).rstrip("\n") + "\n"


def build_vtt(entries: Iterable[SubtitleEntry]) -> str:
    out: List[str] = ["WEBVTT", ""]
    for e in entries:
        out.append(f"{_format_time(e.start, sep='.')} --> {_format_time(e.end, sep='.')}")
        out.append(e.text)
        out.append("")
    return "\n".join(out).rstrip("\n") + "\n"
