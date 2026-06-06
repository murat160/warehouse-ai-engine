"""Murat AI Studio — FastAPI backend.

Запускается на VPS. Streamlit Cloud дёргает эти endpoints через BACKEND_URL.

Эндпойнты:
    GET  /healthz
    POST /api/preview/url              — метаданные ссылки (yt-dlp)
    POST /api/jobs/create               — создать job
    POST /api/jobs/{job_id}/start       — запустить pipeline
    GET  /api/jobs/{job_id}/status      — прогресс
    GET  /api/jobs/{job_id}/result      — ссылки на готовые файлы
    POST /api/voice/create-profile      — voice profile из 30–40 сек MP3/WAV
    POST /api/speakers/detect           — определить актёров
    POST /api/translate/turkmen         — перевод + quality gate
    POST /api/render/final-video        — финальный ffmpeg рендер
    GET  /api/files/{job_id}/{name}     — отдача готовых файлов
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from fastapi import FastAPI, HTTPException, UploadFile, File, Form
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import FileResponse, JSONResponse
    from pydantic import BaseModel
except Exception as exc:  # noqa: BLE001
    raise SystemExit(
        "FastAPI не установлен. Поставь requirements-full.txt: "
        "`pip install -r requirements-full.txt`."
    ) from exc

from .jobs import STORE
from .pipeline import OUT_ROOT, run_pipeline_async

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Murat AI Studio Backend",
    version="1.0.0",
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


class PreviewUrlIn(BaseModel):
    url: str


# ---------------------------------------------------------------------------
# Endpoints.
# ---------------------------------------------------------------------------
@app.get("/healthz")
def healthz() -> Dict[str, Any]:
    return {"ok": True, "service": "murat-ai-studio-backend", "version": "1.0.0"}


@app.post("/api/preview/url")
def preview_url(body: PreviewUrlIn) -> Dict[str, Any]:
    from src.cloud.video_downloader import extract_video_metadata, get_video_preview, validate_url

    check = validate_url(body.url)
    if not check["ok"]:
        raise HTTPException(status_code=400, detail=check["message"])
    meta = extract_video_metadata(body.url)
    preview = get_video_preview(body.url)
    return {"ok": True, "metadata": meta.get("metadata", {}), "preview": preview, "meta_message": meta.get("message")}


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
    uploads = OUT_ROOT / "uploads"
    uploads.mkdir(parents=True, exist_ok=True)
    path = uploads / file.filename
    with open(path, "wb") as fh:
        fh.write(await file.read())
    job = STORE.create(
        upload_path=str(path),
        target_lang=target_lang,
        quality=quality,
        aspect=aspect,
        voice_mode=voice_mode,
        emotion_mode=emotion_mode,
        style=style,
    )
    return job.to_dict()


@app.post("/api/jobs/{job_id}/start")
def jobs_start(job_id: str) -> Dict[str, Any]:
    job = STORE.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    run_pipeline_async(job_id)
    return {"ok": True, "id": job_id, "stage": "queued"}


@app.get("/api/jobs/{job_id}/status")
def jobs_status(job_id: str) -> Dict[str, Any]:
    job = STORE.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return job.to_dict()


@app.get("/api/jobs/{job_id}/result")
def jobs_result(job_id: str) -> Dict[str, Any]:
    job = STORE.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    if job.stage != "done":
        return JSONResponse(status_code=409, content={"ok": False, "stage": job.stage, "message": "Job ещё не готов."})
    return {"ok": True, "id": job.id, "result": job.result}


@app.get("/api/files/{job_id}/{name}")
def file_get(job_id: str, name: str):
    path = OUT_ROOT / job_id / name
    if not path.exists():
        raise HTTPException(status_code=404, detail="file not found")
    return FileResponse(str(path), filename=name)


@app.post("/api/voice/create-profile")
async def voice_create(file: UploadFile = File(...)) -> Dict[str, Any]:
    from src.cloud.voice_profile import create_voice_profile

    uploads = OUT_ROOT / "voice"
    uploads.mkdir(parents=True, exist_ok=True)
    path = uploads / file.filename
    with open(path, "wb") as fh:
        fh.write(await file.read())
    profile = create_voice_profile(str(path))
    return {"ok": True, "profile": profile.__dict__}


@app.post("/api/speakers/detect")
async def speakers_detect(file: UploadFile = File(...)) -> Dict[str, Any]:
    from src.cloud.speaker_diarization import detect_speakers

    uploads = OUT_ROOT / "voice"
    uploads.mkdir(parents=True, exist_ok=True)
    path = uploads / file.filename
    with open(path, "wb") as fh:
        fh.write(await file.read())
    speakers = [s.__dict__ for s in detect_speakers(str(path))]
    return {"ok": True, "speakers": speakers}


@app.post("/api/translate/turkmen")
def translate_turkmen(body: TranslateIn) -> Dict[str, Any]:
    from src.cloud.quality_gate import run_translation_quality_gate
    from src.cloud.turkmen_language_quality import translate_to_clean_turkmen

    tk = translate_to_clean_turkmen(
        body.text,
        source_lang=body.source_lang,
        style=body.style,
    )
    report = run_translation_quality_gate(
        original=body.text,
        turkmen=tk,
        source_lang=body.source_lang,
        emotion=body.emotion,
        style=body.style,
    )
    return {"ok": True, "translation": report.get("fixed_text") or tk, "quality_report": report}


class RenderIn(BaseModel):
    source_video_path: str
    dubbed_audio_path: str
    subtitles_path: Optional[str] = None
    output_format: str = "mp4"
    quality: str = "1080p"
    aspect_ratio: str = "16:9"


@app.post("/api/render/final-video")
def render_final(body: RenderIn) -> Dict[str, Any]:
    from src.cloud.video_renderer import render_final_video

    out = OUT_ROOT / "render" / f"final_{body.quality}.{body.output_format.split('_')[0]}"
    out.parent.mkdir(parents=True, exist_ok=True)
    res = render_final_video(
        source_video_path=body.source_video_path,
        dubbed_audio_path=body.dubbed_audio_path,
        subtitles_path=body.subtitles_path,
        output_format=body.output_format,
        quality=body.quality,
        aspect_ratio=body.aspect_ratio,
        output_path=str(out),
    )
    return res


# Local dev: `uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload`
