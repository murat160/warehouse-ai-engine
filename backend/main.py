"""Murat AI Studio — FastAPI backend.

Запускается на VPS. Streamlit Cloud дёргает endpoints через BACKEND_URL.

Эндпойнты:
    GET  /healthz

    POST /api/video/inspect-url           — метаданные ссылки (yt-dlp --skip-download)
    POST /api/video/download-url          — скачать видео → save source/source_video.mp4

    POST /api/jobs/create                 — создать пустой job (для upload)
    POST /api/jobs/upload-and-create      — загрузить локальный mp4 → save source/source_video.mp4
    POST /api/jobs/{job_id}/start         — запустить старый pipeline (back-compat)
    POST /api/jobs/{job_id}/process-turkmen — главный endpoint: запускает full pipeline
    GET  /api/jobs/{job_id}/status        — прогресс stage + step
    GET  /api/jobs/{job_id}/result        — URLs готовых файлов

    GET  /api/jobs/{job_id}/files/{name}  — отдача любых файлов из storage/jobs/<id>/

    POST /api/voice/create-profile
    POST /api/speakers/detect
    POST /api/translate/turkmen
    POST /api/render/final-video
"""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from fastapi import FastAPI, File, Form, HTTPException, UploadFile
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import FileResponse, JSONResponse
    from pydantic import BaseModel
except Exception as exc:  # noqa: BLE001
    raise SystemExit(
        "FastAPI не установлен. Поставь requirements-full.txt: "
        "`pip install -r requirements-full.txt`."
    ) from exc

from .jobs import STORE
from .pipeline import run_pipeline_async
from .storage import (
    FINAL_SRT,
    FINAL_TXT,
    FINAL_VIDEO,
    FINAL_VOICEOVER,
    FINAL_VOICEOVER_MP3,
    FINAL_VTT,
    FINAL_ZIP,
    SOURCE_VIDEO,
    job_file_url_path,
    job_output_dir,
    job_root,
    job_source_dir,
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Murat AI Studio Backend",
    version="2.0.0",
    description="VPS pipeline для туркменского дубляжа (yt-dlp + Whisper + MMS-TTS + ffmpeg).",
)

ALLOWED = os.environ.get("MURAT_AI_CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request schemas.
# ---------------------------------------------------------------------------
class InspectUrlIn(BaseModel):
    url: str


class DownloadUrlIn(BaseModel):
    url: str
    quality: str = "1080p"
    format: str = "mp4"


class ProcessTurkmenIn(BaseModel):
    target_language: str = "tk"
    voice_mode: str = "auto_original"     # auto_original / male / female / custom
    emotion_mode: str = "auto_original"   # auto_original / manual:<emotion>
    output_quality: str = "1080p"
    video_format: str = "16:9"
    style: str = "cultural"


class CreateJobIn(BaseModel):
    url: str = ""
    target_lang: str = "tk"
    quality: str = "1080p"
    aspect: str = "16:9"
    voice_mode: str = "auto"
    emotion_mode: str = "auto"
    style: str = "cultural"


class TranslateIn(BaseModel):
    text: str
    source_lang: str = "ru"
    style: str = "cultural"
    emotion: Optional[str] = None


class RenderIn(BaseModel):
    source_video_path: str
    dubbed_audio_path: str
    subtitles_path: Optional[str] = None
    output_format: str = "mp4"
    quality: str = "1080p"
    aspect_ratio: str = "16:9"


# ---------------------------------------------------------------------------
# Helpers.
# ---------------------------------------------------------------------------
def _quality_to_height(label: str) -> int:
    table = {
        "Auto": 1080,
        "360p": 360,
        "480p": 480,
        "720p": 720, "720p HD": 720,
        "1080p": 1080, "1080p Full HD": 1080,
        "1440p": 1440, "1440p / 2K": 1440, "2K": 1440,
        "2160p": 2160, "2160p / 4K": 2160, "4K": 2160,
        "4320p": 4320, "4320p / 8K": 4320, "8K": 4320,
        "Original": 4320,
        "Same as source": 1080,
    }
    return table.get(label, 1080)


def _yt_dlp_format(quality: str) -> str:
    h = _quality_to_height(quality)
    return f"bestvideo[height<={h}][ext=mp4]+bestaudio[ext=m4a]/best[height<={h}][ext=mp4]/best"


# ---------------------------------------------------------------------------
# Health.
# ---------------------------------------------------------------------------
@app.get("/healthz")
def healthz() -> Dict[str, Any]:
    return {"ok": True, "service": "murat-ai-studio-backend", "version": "2.0.0"}


# ---------------------------------------------------------------------------
# Video: inspect / download.
# ---------------------------------------------------------------------------
@app.post("/api/video/inspect-url")
def video_inspect_url(body: InspectUrlIn) -> Dict[str, Any]:
    """Возвращает title/duration/thumbnail/available_qualities БЕЗ скачивания."""

    try:
        import yt_dlp  # type: ignore
    except Exception:  # noqa: BLE001
        raise HTTPException(status_code=503, detail="yt-dlp не установлен на backend.")
    try:
        with yt_dlp.YoutubeDL({"quiet": True, "skip_download": True, "no_warnings": True}) as ydl:
            info = ydl.extract_info(body.url, download=False)
        heights = sorted({f.get("height") for f in info.get("formats") or [] if f.get("height")})
        qualities: list = []
        for h in heights:
            if h <= 360: qualities.append("360p")
            elif h <= 480: qualities.append("480p")
            elif h <= 720: qualities.append("720p HD")
            elif h <= 1080: qualities.append("1080p Full HD")
            elif h <= 1440: qualities.append("1440p / 2K")
            elif h <= 2160: qualities.append("2160p / 4K")
            else: qualities.append("4320p / 8K")
        qualities = sorted(set(qualities), key=_quality_to_height)
        return {
            "ok": True,
            "title": info.get("title") or "",
            "duration": int(info.get("duration") or 0),
            "thumbnail": info.get("thumbnail") or "",
            "uploader": info.get("uploader") or "",
            "available_qualities": qualities,
            "source_platform": (info.get("extractor") or "").lower(),
            "is_downloadable": True,
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "message": f"Не удалось получить метаданные: {exc}"}


@app.post("/api/video/download-url")
def video_download_url(body: DownloadUrlIn) -> Dict[str, Any]:
    """Скачивает видео и сохраняет в storage/jobs/<job_id>/source/source_video.mp4."""

    try:
        import yt_dlp  # type: ignore
    except Exception:  # noqa: BLE001
        raise HTTPException(status_code=503, detail="yt-dlp не установлен на backend.")

    job = STORE.create(url=body.url, quality=body.quality)
    src_dir = job_source_dir(job.id)
    target = src_dir / SOURCE_VIDEO
    work_tmpl = str(src_dir / "%(id)s.%(ext)s")
    opts = {
        "outtmpl": work_tmpl,
        "format": _yt_dlp_format(body.quality),
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "writethumbnail": True,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(body.url, download=True)
            downloaded = ydl.prepare_filename(info)
        # Переименовываем в каноничное имя.
        downloaded_path = Path(downloaded)
        if downloaded_path.exists() and downloaded_path != target:
            shutil.move(str(downloaded_path), str(target))
        # Thumbnail.
        for ext in ("webp", "jpg", "jpeg", "png"):
            thumb = src_dir / f"{info.get('id', 'source')}.{ext}"
            if thumb.exists():
                shutil.move(str(thumb), str(src_dir / "thumbnail.jpg"))
                break
        size_mb = round(target.stat().st_size / 1024 / 1024, 2) if target.exists() else 0
        STORE.update(
            job.id,
            stage="downloaded",
            progress=10,
            message=f"Скачано: {target.name} ({size_mb} МБ)",
            result={
                "source_path": str(target),
                "title": info.get("title") or "",
                "duration": int(info.get("duration") or 0),
                "quality": body.quality,
                "file_size_mb": size_mb,
                "thumbnail": str(src_dir / "thumbnail.jpg") if (src_dir / "thumbnail.jpg").exists() else "",
            },
        )
        return {
            "ok": True,
            "job_id": job.id,
            "source_video_url": job_file_url_path(job.id, SOURCE_VIDEO),
            "thumbnail_url": job_file_url_path(job.id, "thumbnail.jpg"),
            "title": info.get("title") or "",
            "duration": int(info.get("duration") or 0),
            "quality": body.quality,
            "file_size_mb": size_mb,
            "message": f"Видео скачано и сохранено на backend ({size_mb} МБ)",
        }
    except Exception as exc:  # noqa: BLE001
        STORE.update(job.id, stage="failed", error=str(exc), message=str(exc))
        return {"ok": False, "job_id": job.id, "message": f"Ошибка скачивания: {exc}"}


# ---------------------------------------------------------------------------
# Job-level: create / upload / process.
# ---------------------------------------------------------------------------
@app.post("/api/jobs/create")
def jobs_create(body: CreateJobIn) -> Dict[str, Any]:
    job = STORE.create(**body.model_dump())
    return job.to_dict()


@app.post("/api/jobs/upload-and-create")
async def jobs_upload(
    file: UploadFile = File(...),
    target_lang: str = Form("tk"),
    quality: str = Form("1080p"),
    aspect: str = Form("16:9"),
    voice_mode: str = Form("auto"),
    emotion_mode: str = Form("auto"),
    style: str = Form("cultural"),
) -> Dict[str, Any]:
    job = STORE.create(
        target_lang=target_lang,
        quality=quality,
        aspect=aspect,
        voice_mode=voice_mode,
        emotion_mode=emotion_mode,
        style=style,
    )
    src_dir = job_source_dir(job.id)
    target = src_dir / SOURCE_VIDEO
    data = await file.read()
    target.write_bytes(data)
    size_mb = round(target.stat().st_size / 1024 / 1024, 2)
    STORE.update(
        job.id,
        upload_path=str(target),
        stage="downloaded",
        progress=10,
        message=f"Загружено: {file.filename} ({size_mb} МБ)",
        result={
            "source_path": str(target),
            "title": file.filename or "uploaded.mp4",
            "file_size_mb": size_mb,
            "quality": quality,
        },
    )
    return {
        "ok": True,
        "job_id": job.id,
        "source_video_url": job_file_url_path(job.id, SOURCE_VIDEO),
        "title": file.filename or "uploaded.mp4",
        "file_size_mb": size_mb,
    }


@app.post("/api/jobs/{job_id}/start")
def jobs_start(job_id: str) -> Dict[str, Any]:
    job = STORE.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    run_pipeline_async(job_id)
    return {"ok": True, "id": job_id, "stage": "queued"}


@app.post("/api/jobs/{job_id}/process-turkmen")
def jobs_process_turkmen(job_id: str, body: ProcessTurkmenIn) -> Dict[str, Any]:
    """Главный endpoint: запускает full pipeline на скачанном/загруженном видео."""

    job = STORE.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    STORE.update(
        job_id,
        target_lang=body.target_language,
        quality=body.output_quality,
        aspect=body.video_format,
        voice_mode=body.voice_mode,
        emotion_mode=body.emotion_mode,
        style=body.style,
        stage="queued",
        progress=0,
        message="Pipeline запущен.",
    )
    run_pipeline_async(job_id)
    return {"ok": True, "job_id": job_id, "stage": "queued"}


@app.get("/api/jobs/{job_id}/status")
def jobs_status(job_id: str) -> Dict[str, Any]:
    job = STORE.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    stage_label_ru = {
        "queued":              "В очереди",
        "downloaded":          "Скачано, готов к обработке",
        "downloading":         "Скачивание",
        "extracting_audio":    "Извлечение аудио",
        "transcribing":        "Распознавание речи",
        "detecting_speakers":  "Определение актёров",
        "analyzing_emotions":  "Анализ эмоций",
        "translating":         "Перевод на туркменский",
        "quality_check":       "Проверка качества",
        "tts":                 "Туркменская озвучка (MMS-TTS)",
        "syncing":             "Синхронизация с видео",
        "rendering":           "Сборка финального MP4",
        "done":                "Готово",
        "failed":              "Ошибка",
    }
    return {
        **job.to_dict(),
        "current_step": stage_label_ru.get(job.stage, job.stage),
        "status": job.stage,
    }


@app.get("/api/jobs/{job_id}/result")
def jobs_result(job_id: str) -> Dict[str, Any]:
    job = STORE.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    if job.stage != "done":
        return JSONResponse(status_code=409, content={"ok": False, "stage": job.stage, "message": "Job ещё не готов."})
    out = job_output_dir(job_id)
    return {
        "ok": True,
        "job_id": job_id,
        "final_video_url": job_file_url_path(job_id, FINAL_VIDEO)         if (out / FINAL_VIDEO).exists() else "",
        "audio_url":       job_file_url_path(job_id, FINAL_VOICEOVER)     if (out / FINAL_VOICEOVER).exists() else "",
        "mp3_url":         job_file_url_path(job_id, FINAL_VOICEOVER_MP3) if (out / FINAL_VOICEOVER_MP3).exists() else "",
        "srt_url":         job_file_url_path(job_id, FINAL_SRT)           if (out / FINAL_SRT).exists() else "",
        "vtt_url":         job_file_url_path(job_id, FINAL_VTT)           if (out / FINAL_VTT).exists() else "",
        "txt_url":         job_file_url_path(job_id, FINAL_TXT)           if (out / FINAL_TXT).exists() else "",
        "zip_url":         job_file_url_path(job_id, FINAL_ZIP)           if (out / FINAL_ZIP).exists() else "",
        "result":          job.result,
    }


@app.get("/api/jobs/{job_id}/files/{filename}")
def job_file(job_id: str, filename: str):
    """Отдаёт файл из storage/jobs/<job_id>/ (source/ или output/)."""

    root = job_root(job_id)
    for sub in ("source", "output", "work"):
        candidate = root / sub / filename
        if candidate.exists():
            return FileResponse(str(candidate), filename=filename)
    raise HTTPException(status_code=404, detail="file not found")


# ---------------------------------------------------------------------------
# Voice / speakers / translate / render.
# ---------------------------------------------------------------------------
@app.post("/api/voice/create-profile")
async def voice_create(file: UploadFile = File(...)) -> Dict[str, Any]:
    from src.cloud.voice_profile import create_voice_profile

    from .storage import voice_dir

    voice_id = f"voice_{file.filename.rsplit('.', 1)[0]}"
    vdir = voice_dir(voice_id)
    path = vdir / file.filename
    path.write_bytes(await file.read())
    profile = create_voice_profile(str(path), name=file.filename)
    return {"ok": True, "profile": profile.__dict__}


@app.post("/api/speakers/detect")
async def speakers_detect(file: UploadFile = File(...)) -> Dict[str, Any]:
    from src.cloud.speaker_diarization import detect_speakers

    tmp = Path(os.environ.get("MURAT_AI_STORAGE", "storage")) / "tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    path = tmp / file.filename
    path.write_bytes(await file.read())
    speakers = [s.__dict__ for s in detect_speakers(str(path))]
    return {"ok": True, "speakers": speakers}


@app.post("/api/translate/turkmen")
def translate_turkmen(body: TranslateIn) -> Dict[str, Any]:
    from src.cloud.quality_gate import run_translation_quality_gate
    from src.cloud.turkmen_language_quality import translate_to_clean_turkmen

    tk = translate_to_clean_turkmen(body.text, source_lang=body.source_lang, style=body.style)
    report = run_translation_quality_gate(
        original=body.text, turkmen=tk,
        source_lang=body.source_lang, emotion=body.emotion, style=body.style,
    )
    return {"ok": True, "translation": report.get("fixed_text") or tk, "quality_report": report}


@app.post("/api/render/final-video")
def render_final(body: RenderIn) -> Dict[str, Any]:
    from src.cloud.video_renderer import render_final_video

    out = Path(os.environ.get("MURAT_AI_STORAGE", "storage")) / "render"
    out.mkdir(parents=True, exist_ok=True)
    return render_final_video(
        source_video_path=body.source_video_path,
        dubbed_audio_path=body.dubbed_audio_path,
        subtitles_path=body.subtitles_path,
        output_format=body.output_format,
        quality=body.quality,
        aspect_ratio=body.aspect_ratio,
        output_path=str(out / f"final_{body.quality}.{body.output_format.split('_')[0]}"),
    )


# Запуск:
#   uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 2
