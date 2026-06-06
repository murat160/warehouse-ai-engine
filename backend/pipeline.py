"""Murat AI Studio — главный pipeline обработки jobs на VPS.

Запускается фоновым потоком. Каждый stage обновляет Job.stage / progress
через JobStore. Любой шаг может вызвать `raise` — обработчик переведёт job
в "failed" и сохранит error.

Шаги:
    download → extract_audio → transcribe → detect_speakers →
    analyze_emotions → translate → quality_check (repair) →
    tts → sync → render → done
"""

from __future__ import annotations

import logging
import os
import threading
import traceback
from pathlib import Path
from typing import Any, Dict, List

from .jobs import STORE, Job

logger = logging.getLogger(__name__)

OUT_ROOT = Path(os.environ.get("MURAT_AI_OUT", "out"))
OUT_ROOT.mkdir(parents=True, exist_ok=True)


def _set(job_id: str, stage: str, progress: int, message: str = "") -> None:
    STORE.update(job_id, stage=stage, progress=progress, message=message)


def run_pipeline(job_id: str) -> None:
    """Запускает фоновую обработку. Безопасно: ловит все exceptions."""

    job = STORE.get(job_id)
    if not job:
        logger.error("Job %s not found", job_id)
        return
    try:
        _stage_download(job)
        _stage_extract_audio(job)
        _stage_transcribe(job)
        _stage_detect_speakers(job)
        _stage_analyze_emotions(job)
        _stage_translate(job)
        _stage_quality_check(job)
        _stage_tts(job)
        _stage_sync(job)
        _stage_render(job)
        _set(job.id, "done", 100, "Готово.")
    except Exception as exc:  # noqa: BLE001
        tb = traceback.format_exc()
        logger.error("Pipeline %s failed: %s\n%s", job.id, exc, tb)
        STORE.update(job.id, stage="failed", error=str(exc), message=str(exc))


def run_pipeline_async(job_id: str) -> None:
    th = threading.Thread(target=run_pipeline, args=(job_id,), daemon=True)
    th.start()


# ---------------------------------------------------------------------------
# Stages.
# ---------------------------------------------------------------------------
def _stage_download(job: Job) -> None:
    _set(job.id, "downloading", 5, "Скачиваю видео…")
    if job.upload_path:
        STORE.update(job.id, result={**job.result, "source_path": job.upload_path})
        return
    from src.cloud.video_downloader import download_video_from_url

    res = download_video_from_url(job.url, output_dir=str(OUT_ROOT / job.id))
    if not res.get("ok"):
        raise RuntimeError(res.get("message", "Скачивание не удалось"))
    STORE.update(job.id, result={**job.result, "source_path": res["path"]})


def _stage_extract_audio(job: Job) -> None:
    _set(job.id, "extracting_audio", 15, "Извлекаю аудиодорожку…")
    from src.cloud.asr import extract_audio_from_video

    src = STORE.get(job.id).result.get("source_path", "")
    wav = extract_audio_from_video(src)
    STORE.update(job.id, result={**STORE.get(job.id).result, "audio_path": wav})


def _stage_transcribe(job: Job) -> None:
    _set(job.id, "transcribing", 25, "Распознаю речь (Whisper)…")
    from src.cloud.asr import transcribe_audio

    audio = STORE.get(job.id).result.get("audio_path", "")
    segments = transcribe_audio(audio, source_lang="auto")
    STORE.update(job.id, result={**STORE.get(job.id).result, "segments": segments})


def _stage_detect_speakers(job: Job) -> None:
    _set(job.id, "detecting_speakers", 35, "Определяю актёров…")
    from src.cloud.speaker_diarization import detect_speakers

    audio = STORE.get(job.id).result.get("audio_path", "")
    speakers = [s.__dict__ for s in detect_speakers(audio)]
    STORE.update(job.id, result={**STORE.get(job.id).result, "speakers": speakers})


def _stage_analyze_emotions(job: Job) -> None:
    _set(job.id, "analyzing_emotions", 45, "Анализирую эмоции…")
    from src.cloud.emotion_transfer import analyze_emotion_from_text, create_emotion_profile

    segments = STORE.get(job.id).result.get("segments", [])
    text = " ".join(seg.get("text", "") for seg in segments)
    audio = STORE.get(job.id).result.get("audio_path", "")
    profile = create_emotion_profile(audio, text)
    STORE.update(job.id, result={**STORE.get(job.id).result, "emotion_profile": profile.to_dict()})


def _stage_translate(job: Job) -> None:
    _set(job.id, "translating", 60, "Перевожу на туркменский…")
    from src.cloud.turkmen_language_quality import translate_to_clean_turkmen

    segments = STORE.get(job.id).result.get("segments", [])
    emotion = STORE.get(job.id).result.get("emotion_profile", {})
    translated: List[Dict[str, Any]] = []
    for seg in segments:
        tk = translate_to_clean_turkmen(
            seg.get("text", ""),
            source_lang=seg.get("language", "ru"),
            style=job.style,
            emotion_profile=emotion,
        )
        translated.append({**seg, "translation": tk})
    STORE.update(job.id, result={**STORE.get(job.id).result, "translated": translated})


def _stage_quality_check(job: Job) -> None:
    _set(job.id, "quality_check", 70, "Проверка качества перевода…")
    from src.cloud.quality_gate import run_translation_quality_gate

    translated = STORE.get(job.id).result.get("translated", [])
    emotion = (STORE.get(job.id).result.get("emotion_profile") or {}).get("emotion")
    reports: List[Dict[str, Any]] = []
    fixed: List[Dict[str, Any]] = []
    for seg in translated:
        report = run_translation_quality_gate(
            seg.get("text", ""),
            seg.get("translation", ""),
            source_lang=seg.get("language", "ru"),
            emotion=emotion,
            style=job.style,
            segment_duration_sec=float(seg.get("end", 0)) - float(seg.get("start", 0)),
        )
        reports.append(report)
        fixed.append({**seg, "translation": report.get("fixed_text") or seg.get("translation")})
    STORE.update(job.id, result={**STORE.get(job.id).result, "quality_reports": reports, "translated": fixed})


def _stage_tts(job: Job) -> None:
    _set(job.id, "tts", 80, "Синтезирую туркменскую озвучку (MMS-TTS)…")
    from src.cloud.tts_turkmen import (
        TurkmenEmotionProfile,
        TurkmenVoiceProfile,
        get_emotion_preset,
        synthesize_turkmen_tts,
    )

    translated = STORE.get(job.id).result.get("translated", [])
    emotion_dict = STORE.get(job.id).result.get("emotion_profile", {})
    emotion_label = emotion_dict.get("emotion", "neutral")
    preset = get_emotion_preset(emotion_label)
    voice = TurkmenVoiceProfile(id=job.voice_mode, name=job.voice_mode)
    tracks: List[str] = []
    for seg in translated:
        text = seg.get("translation", "")
        if not text:
            continue
        path = synthesize_turkmen_tts(text, emotion_profile=preset, voice_profile=voice)
        tracks.append(path)
    STORE.update(job.id, result={**STORE.get(job.id).result, "tts_tracks": tracks})


def _stage_sync(job: Job) -> None:
    _set(job.id, "syncing", 88, "Синхронизирую с видео…")
    from src.cloud.timing_alignment import fit_translation_to_timeline, validate_sync

    translated = STORE.get(job.id).result.get("translated", [])
    fitted = fit_translation_to_timeline(translated, translated)
    sync_report = validate_sync(
        video_duration=max((float(s.get("end", 0)) for s in translated), default=0.0),
        audio_duration=max((float(s.get("end", 0)) for s in translated), default=0.0),
        segment_timings=fitted,
    )
    STORE.update(job.id, result={**STORE.get(job.id).result, "fitted": fitted, "sync_report": sync_report})


def _stage_render(job: Job) -> None:
    _set(job.id, "rendering", 95, "Собираю готовый MP4…")
    from src.cloud.video_renderer import render_final_video

    res_data = STORE.get(job.id).result
    out = OUT_ROOT / job.id / f"final_{job.quality}.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)
    render = render_final_video(
        source_video_path=res_data.get("source_path"),
        dubbed_audio_path=(res_data.get("tts_tracks") or [None])[0],
        subtitles_path=None,
        output_format="mp4",
        quality=job.quality,
        aspect_ratio=job.aspect,
        output_path=str(out),
    )
    STORE.update(job.id, result={**res_data, "final_video": render, "final_path": str(out)})
