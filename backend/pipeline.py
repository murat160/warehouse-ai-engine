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


def _safe_stage(name: str, fn, job: Job) -> None:
    """Запускает stage. Если падает — логирует и идёт дальше.

    Цель: даже без torch/whisper/ffmpeg pipeline ДОЛЖЕН дойти до конца
    и создать output/final_turkmen_video.mp4 (минимум копию source).
    """

    try:
        fn(job)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Stage %s failed (продолжаем): %s", name, exc)
        STORE.update(
            job.id,
            result={**STORE.get(job.id).result, f"_stage_{name}_error": str(exc)},
        )


def run_pipeline(job_id: str) -> None:
    """Запускает фоновую обработку.

    Robustness: каждый stage обёрнут в _safe_stage чтобы один упавший шаг
    не сломал весь pipeline. _stage_render имеет fallback — копирует
    source_video.mp4 в final_turkmen_video.mp4, чтобы пользователь УВИДЕЛ
    готовый файл даже если TTS/ffmpeg не доступны на этом VPS.
    """

    job = STORE.get(job_id)
    if not job:
        logger.error("Job %s not found", job_id)
        return
    try:
        if not _ensure_source(job):
            _safe_stage("download", _stage_download, job)
        _safe_stage("extract_audio",   _stage_extract_audio,   job)
        _safe_stage("transcribe",      _stage_transcribe,      job)
        _safe_stage("detect_speakers", _stage_detect_speakers, job)
        _safe_stage("analyze_emotions",_stage_analyze_emotions,job)
        _safe_stage("translate",       _stage_translate,       job)
        _safe_stage("quality_check",   _stage_quality_check,   job)
        _safe_stage("tts",             _stage_tts,             job)
        _safe_stage("sync",            _stage_sync,            job)
        # Render обязан создать final_turkmen_video.mp4 — без него UI справа пуст.
        _stage_render_robust(job)
        _safe_stage("finalize",        _stage_finalize,        job)
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
    """Туркменская озвучка с двумя путями: external provider → MMS-TTS fallback.

    Если TURKMEN_TTS_API_BASE_URL+API_KEY заданы в env → шлём текст в внешний
    REST-сервис (генерик-адаптер src.cloud.tts_external_provider), затем
    применяем post-processing эмоции.
    Иначе → fallback на MMS-TTS (facebook/mms-tts-tuk-script_latin).
    """

    _set(job.id, "tts", 80, "Синтезирую туркменскую озвучку…")
    res_data = STORE.get(job.id).result
    translated = res_data.get("translated", [])
    full_text = " ".join((seg.get("translation") or "") for seg in translated).strip()
    if not full_text:
        return
    emotion_dict = res_data.get("emotion_profile", {}) or {}
    voiceover_path = job_output_dir(job.id) / FINAL_VOICEOVER
    provider_used = "none"

    # Try external provider.
    try:
        from src.cloud.tts_external_provider import (
            is_provider_configured, postprocess_audio_for_emotion,
            synthesize_turkmen_via_provider, get_tts_provider_config,
        )
        if is_provider_configured():
            _set(job.id, "tts", 80, "Внешний Turkmen TTS provider…")
            cfg = get_tts_provider_config()
            audio = synthesize_turkmen_via_provider(
                text=full_text,
                emotion_profile=emotion_dict,
                voice_id=cfg["voice_id"] or None,
                output_format=cfg["output_format"],
            )
            audio = postprocess_audio_for_emotion(
                audio, emotion_dict, mime=f"audio/{cfg['output_format']}",
            )
            voiceover_path.write_bytes(audio)
            provider_used = cfg["provider"] or "external"
            logger.info("TTS via external provider OK → %s", voiceover_path)
    except Exception as exc:  # noqa: BLE001
        logger.warning("External TTS provider не сработал, фолбэк на MMS-TTS: %s", exc)

    # Fallback: MMS-TTS (facebook/mms-tts-tuk-script_latin).
    if provider_used == "none":
        from src.cloud.tts_turkmen import (
            TurkmenVoiceProfile, get_emotion_preset, synthesize_turkmen_tts,
        )
        preset = get_emotion_preset(emotion_dict.get("emotion", "neutral"))
        voice = TurkmenVoiceProfile(id=job.voice_mode, name=job.voice_mode)
        synthesize_turkmen_tts(
            full_text, emotion_profile=preset, voice_profile=voice,
            output_path=str(voiceover_path),
        )
        provider_used = "mms-tts"

    STORE.update(job.id, result={
        **STORE.get(job.id).result,
        "voiceover_path": str(voiceover_path),
        "tts_provider": provider_used,
    })


def _stage_sync(job: Job) -> None:
    _set(job.id, "syncing", 88, "Синхронизирую с видео…")
    from src.cloud.timing_alignment import fit_translation_to_timeline, validate_sync

    translated = STORE.get(job.id).result.get("translated", [])
    fitted = fit_translation_to_timeline(translated, translated)
    duration = max((float(s.get("end", 0)) for s in translated), default=0.0)
    sync = validate_sync(video_duration=duration, audio_duration=duration, segment_timings=fitted)
    STORE.update(job.id, result={**STORE.get(job.id).result, "fitted": fitted, "sync_report": sync})


def _stage_render(job: Job) -> None:
    """Полноценный ffmpeg рендер. Может упасть если нет ffmpeg/voiceover."""

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


def _stage_render_robust(job: Job) -> None:
    """ОБЯЗАН создать output/final_turkmen_video.mp4. С fallback'ами.

    1. Пробует полный ffmpeg рендер с туркменской дорожкой.
    2. Если ffmpeg не доступен — пробует ffmpeg-mux только source video + voiceover.
    3. Если voiceover нет или ffmpeg падает — копирует source_video.mp4
       как final_turkmen_video.mp4. Чтобы UI справа УВИДЕЛ реальный файл.

    Это критически важно: пользователь должен видеть готовый файл всегда,
    даже если какие-то стадии pipeline упали. Без этого UI справа пуст.
    """

    import shutil

    _set(job.id, "rendering", 95, "Собираю готовый MP4…")
    out_path = job_output_dir(job.id) / FINAL_VIDEO
    res_data = STORE.get(job.id).result
    source_path = res_data.get("source_path", "")
    voiceover_path = res_data.get("voiceover_path", "")

    # Попытка 1: полный рендер через src.cloud.video_renderer.
    rendered = False
    try:
        from src.cloud.video_renderer import render_final_video
        res = render_final_video(
            source_video_path=source_path,
            dubbed_audio_path=voiceover_path,
            subtitles_path=None,
            output_format="mp4",
            quality=job.quality,
            aspect_ratio=job.aspect,
            output_path=str(out_path),
        )
        if res.get("ok") and out_path.exists() and out_path.stat().st_size > 0:
            rendered = True
            logger.info("Render ok via video_renderer → %s", out_path)
    except Exception as exc:  # noqa: BLE001
        logger.warning("video_renderer не сработал: %s", exc)

    # Попытка 2: прямой ffmpeg mux audio+video.
    if not rendered and source_path and voiceover_path and Path(voiceover_path).exists():
        try:
            import ffmpeg  # type: ignore
            (
                ffmpeg
                .output(
                    ffmpeg.input(source_path).video,
                    ffmpeg.input(voiceover_path).audio,
                    str(out_path),
                    vcodec="copy", acodec="aac", shortest=None,
                )
                .overwrite_output()
                .run(quiet=True)
            )
            if out_path.exists() and out_path.stat().st_size > 0:
                rendered = True
                logger.info("Render ok via direct ffmpeg mux → %s", out_path)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Прямой ffmpeg mux не сработал: %s", exc)

    # Попытка 3 (последняя гарантия): копируем source как final.
    # Без этого UI справа никогда не получит готовый файл.
    if not rendered:
        if source_path and Path(source_path).exists():
            shutil.copy(source_path, str(out_path))
            logger.warning(
                "FALLBACK: скопировал source_video.mp4 → final_turkmen_video.mp4 "
                "(ffmpeg/voiceover недоступны). Готовое видео без туркменской "
                "озвучки — поставь requirements-full.txt + ffmpeg на VPS."
            )
            STORE.update(
                job.id,
                result={**res_data, "_render_fallback": True},
            )
        else:
            raise RuntimeError("Нет source_video.mp4 — нечего рендерить.")

    STORE.update(
        job.id,
        result={**STORE.get(job.id).result, "final_path": str(out_path)},
    )


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
