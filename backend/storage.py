"""Murat AI Studio — структура файлов на VPS.

storage/jobs/<job_id>/source/source_video.mp4
storage/jobs/<job_id>/source/thumbnail.jpg
storage/jobs/<job_id>/output/final_turkmen_video.mp4
storage/jobs/<job_id>/output/voiceover.wav
storage/jobs/<job_id>/output/subtitles.srt
storage/jobs/<job_id>/output/subtitles.vtt
storage/jobs/<job_id>/output/translation.txt
storage/jobs/<job_id>/output/project.zip
storage/jobs/<job_id>/work/...      (intermediate files)
storage/voice_profiles/<voice_id>/
"""

from __future__ import annotations

import os
from pathlib import Path

STORAGE_ROOT = Path(os.environ.get("MURAT_AI_STORAGE", "storage"))
STORAGE_ROOT.mkdir(parents=True, exist_ok=True)


def job_root(job_id: str) -> Path:
    p = STORAGE_ROOT / "jobs" / job_id
    p.mkdir(parents=True, exist_ok=True)
    return p


def job_source_dir(job_id: str) -> Path:
    p = job_root(job_id) / "source"
    p.mkdir(parents=True, exist_ok=True)
    return p


def job_work_dir(job_id: str) -> Path:
    p = job_root(job_id) / "work"
    p.mkdir(parents=True, exist_ok=True)
    return p


def job_output_dir(job_id: str) -> Path:
    p = job_root(job_id) / "output"
    p.mkdir(parents=True, exist_ok=True)
    return p


def voice_dir(voice_id: str) -> Path:
    p = STORAGE_ROOT / "voice_profiles" / voice_id
    p.mkdir(parents=True, exist_ok=True)
    return p


# Канонические имена файлов в каждой job.
SOURCE_VIDEO = "source_video.mp4"
SOURCE_THUMB = "thumbnail.jpg"
SOURCE_AUDIO = "source_audio.wav"
FINAL_VIDEO = "final_turkmen_video.mp4"
FINAL_VOICEOVER = "voiceover.wav"
FINAL_VOICEOVER_MP3 = "voiceover.mp3"
FINAL_SRT = "subtitles.srt"
FINAL_VTT = "subtitles.vtt"
FINAL_TXT = "translation.txt"
FINAL_ZIP = "project.zip"


def job_file_url_path(job_id: str, filename: str) -> str:
    """URL path для отдачи файла клиенту."""

    return f"/api/jobs/{job_id}/files/{filename}"
