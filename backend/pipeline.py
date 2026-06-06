"""Murat AI Studio — главный pipeline обработки jobs на VPS.

Запускается фоновым потоком. Каждый stage обновляет Job.stage / progress
через JobStore. Любой шаг может вызвать `raise` — обработчик переведёт job
в "failed" и сохранит error.

Шаги:
    extract_audio → transcribe → detect_speakers → analyze_emotions →
    translate → quality_check → tts → sync → render → done

(Скачивание происходит ДО pipeline через POST /api/video/download-url.)

Все промежуточные файлы пишутся в storage/jobs/<job_id>/work/.
Финальные — в storage/jobs/<job_id>/output/.
"""

from __future__ import annotations

import logging
import shutil
import threading
import traceback
from pathlib import Path
from typing import Any, Dict, List

from .jobs import STORE, Job
from .storage import (
    FINAL_SRT,
    FINAL_TXT,
    FINAL_VIDEO,
    FINAL_VOICEOVER,
    FINAL_VTT,
    FINAL_ZIP,
    SOURCE_AUDIO,
    SOURCE_VIDEO,
    job_output_dir,
    job_source_dir,
    job_work_dir,
)

logger = logging.getLogger(__name__)


def _set(job_id: str, stage: str, progress: int, message: str = "") -> None:
    STORE.update(job_id, stage=stage, progress=progress, message=message)


def run_pipeline(job_id: str) -> None:
    """Запускает фоновую обработку. Безопасно: ловит все exceptions."""

    job = STORE.get(job_id)
    if not job:
        logger.error("Job %s not found", job_id)
        return
    try:
        if not _ensure_source(job):
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
        _stage_finalize(job)
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
def _ensure_source(job: Job) -> bool:
    src = job_source_dir(job.id) / SOURCE_VIDEO
    if src.exists():
        STORE.update(job.id, result={**job.result, "source_path": str(src)})
        return True
    if job.upload_path and Path(job.upload_path).exists():
        if Path(job.upload_path) != src:
            shutil.copy(job.upload_path, src)
        STORE.update(job.id, result={**job.result, "source_path": str(src)})
        return True
    return False


def _stage_download(job: Job) -> None:
    _set(job.id, "downloading", 5, "Скачиваю видео…")
    if not job.url:
        raise RuntimeError("Нет ни ссылки, ни загруженного файла.")
    from src.cloud.video_downloader import download_video_from_url

    res = download_video_from_url(job.url, output_dir=str(job_source_dir(job.id)))
    if not res.get("ok"):
        raise RuntimeError(res.get("message", "Скачивание не удалось"))
    dl = Path(res["path"])
    target = job_source_dir(job.id) / SOURCE_VIDEO
    if dl != target:
        shutil.move(str(dl), str(target))
    STORE.update(job.id, result={**job.result, "source_path": str(target)})


def _stage_extract_audio(job: Job) -> None:
    _set(job.id, "extracting_audio", 15, "Извлекаю аудиодорожку…")
    from src.cloud.asr import extract_audio_from_video

    src = STORE.get(job.id).result.get("source_path", "")
    wav_tmp = extract_audio_from_video(src)
    audio_path = job_work_dir(job.id) / SOURCE_AUDIO
    if wav_tmp and Path(wav_tmp).exists():
        shutil.move(wav_tmp, str(audio_path))
    STORE.update(job.id, result={**STORE.get(job.id).result, "audio_path": str(audio_path)})


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
    from src.cloud.emotion_transfer import create_emotion_profile

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
        TurkmenVoiceProfile,
        get_emotion_preset,
        synthesize_turkmen_tts,
    )

    translated = STORE.get(job.id).result.get("translated", [])
    emotion_dict = STORE.get(job.id).result.get("emotion_profile", {})
    preset = get_emotion_preset(emotion_dict.get("emotion", "neutral"))
    voice = TurkmenVoiceProfile(id=job.voice_mode, name=job.voice_mode)
    voiceover_path = job_output_dir(job.id) / FINAL_VOICEOVER
    full_text = " ".join((seg.get("translation") or "") for seg in translated)
    if full_text.strip():
        synthesize_turkmen_tts(full_text, emotion_profile=preset, voice_profile=voice, output_path=str(voiceover_path))
    STORE.update(job.id, result={**STORE.get(job.id).result, "voiceover_path": str(voiceover_path)})


def _stage_sync(job: Job) -> None:
    _set(job.id, "syncing", 88, "Синхронизирую с видео…")
    from src.cloud.timing_alignment import fit_translation_to_timeline, validate_sync

    translated = STORE.get(job.id).result.get("translated", [])
    fitted = fit_translation_to_timeline(translated, translated)
    duration = max((float(s.get("end", 0)) for s in translated), default=0.0)
    sync = validate_sync(video_duration=duration, audio_duration=duration, segment_timings=fitted)
    STORE.update(job.id, result={**STORE.get(job.id).result, "fitted": fitted, "sync_report": sync})


def _stage_render(job: Job) -> None:
    _set(job.id, "rendering", 95, "Собираю готовый MP4…")
    from src.cloud.video_renderer import render_final_video

    out = job_output_dir(job.id) / FINAL_VIDEO
    res_data = STORE.get(job.id).result
    res = render_final_video(
        source_video_path=res_data.get("source_path"),
        dubbed_audio_path=res_data.get("voiceover_path"),
        subtitles_path=None,
        output_format="mp4",
        quality=job.quality,
        aspect_ratio=job.aspect,
        output_path=str(out),
    )
    STORE.update(job.id, result={**res_data, "final_video": res, "final_path": str(out)})


def _stage_finalize(job: Job) -> None:
    """Сохраняет subtitles.srt / .vtt / translation.txt / project.zip."""

    from src.cloud.video_renderer import export_project_zip, export_srt, export_txt, export_vtt

    out_dir = job_output_dir(job.id)
    translated = STORE.get(job.id).result.get("translated", [])
    full_text = "\n".join((seg.get("translation") or "") for seg in translated)
    (out_dir / FINAL_SRT).write_bytes(export_srt(full_text))
    (out_dir / FINAL_VTT).write_bytes(export_vtt(full_text))
    (out_dir / FINAL_TXT).write_bytes(export_txt(full_text))
    payload = {
        "job_id": job.id,
        "result_text": full_text,
        "result": STORE.get(job.id).result,
    }
    (out_dir / FINAL_ZIP).write_bytes(export_project_zip(payload))
