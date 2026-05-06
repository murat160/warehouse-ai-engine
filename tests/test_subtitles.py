"""Subtitle formatting (SRT / VTT)."""

from __future__ import annotations

from src.providers.base import TranscriptSegment
from src.video.subtitles import build_srt, build_vtt, from_segments


def _segments():
    return [
        TranscriptSegment(start=0.0, end=1.5, text="Привет"),
        TranscriptSegment(start=1.5, end=3.25, text="как дела"),
        TranscriptSegment(start=3.25, end=3.25, text="   "),  # filtered: empty
    ]


def test_from_segments_skips_empty():
    entries = from_segments(_segments())
    assert len(entries) == 2
    assert entries[0].index == 1
    assert entries[1].index == 2


def test_build_srt_format():
    out = build_srt(from_segments(_segments()))
    assert "00:00:00,000 --> 00:00:01,500" in out
    assert "00:00:01,500 --> 00:00:03,250" in out
    assert "Привет" in out


def test_build_vtt_format():
    out = build_vtt(from_segments(_segments()))
    assert out.startswith("WEBVTT")
    assert "00:00:01.500 --> 00:00:03.250" in out
