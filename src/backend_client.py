"""Murat AI Studio — клиент Streamlit Cloud → VPS backend.

Использует ТОЛЬКО `requests` (есть в light requirements.txt). Никаких
torch/transformers/ffmpeg. Все тяжёлые операции делегируются backend через
HTTP API (см. backend/main.py).

BACKEND_URL берётся из env (Streamlit Cloud Secrets):
    BACKEND_URL=https://your-vps-domain.com

Если BACKEND_URL не задан — клиент работает в OFFLINE-режиме: возвращает
понятные сообщения «Подключи VPS backend в Secrets» без падения UI.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

try:
    import requests
except Exception:  # noqa: BLE001
    requests = None  # type: ignore


def backend_url() -> str:
    return os.environ.get("BACKEND_URL", "").strip().rstrip("/")


def is_configured() -> bool:
    return bool(backend_url())


def _post(path: str, **kw: Any) -> Dict[str, Any]:
    if not is_configured() or requests is None:
        return {"ok": False, "offline": True, "message": "BACKEND_URL не настроен. Реальная обработка работает на VPS."}
    try:
        r = requests.post(backend_url() + path, timeout=kw.pop("timeout", 30), **kw)
        if r.status_code >= 400:
            return {"ok": False, "status": r.status_code, "message": r.text}
        return r.json()
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "message": f"Backend недоступен: {exc}"}


def _get(path: str, **kw: Any) -> Dict[str, Any]:
    if not is_configured() or requests is None:
        return {"ok": False, "offline": True, "message": "BACKEND_URL не настроен."}
    try:
        r = requests.get(backend_url() + path, timeout=kw.pop("timeout", 30), **kw)
        if r.status_code >= 400:
            return {"ok": False, "status": r.status_code, "message": r.text}
        return r.json()
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "message": f"Backend недоступен: {exc}"}


# ---------------------------------------------------------------------------
# Public API (one wrapper per endpoint).
# ---------------------------------------------------------------------------
def healthz() -> Dict[str, Any]:
    return _get("/healthz")


def preview_url(url: str) -> Dict[str, Any]:
    return _post("/api/preview/url", json={"url": url})


def create_job(
    url: str = "",
    target_lang: str = "tk",
    quality: str = "1080p",
    aspect: str = "16:9",
    voice_mode: str = "auto",
    emotion_mode: str = "auto",
    style: str = "cultural",
) -> Dict[str, Any]:
    return _post(
        "/api/jobs/create",
        json={
            "url": url,
            "target_lang": target_lang,
            "quality": quality,
            "aspect": aspect,
            "voice_mode": voice_mode,
            "emotion_mode": emotion_mode,
            "style": style,
        },
    )


def upload_and_create_job(
    file_bytes: bytes,
    filename: str,
    target_lang: str = "tk",
    quality: str = "1080p",
    aspect: str = "16:9",
    voice_mode: str = "auto",
    emotion_mode: str = "auto",
    style: str = "cultural",
) -> Dict[str, Any]:
    if not is_configured() or requests is None:
        return {"ok": False, "offline": True, "message": "BACKEND_URL не настроен."}
    try:
        r = requests.post(
            backend_url() + "/api/jobs/upload-and-create",
            files={"file": (filename, file_bytes)},
            data={
                "target_lang": target_lang,
                "quality": quality,
                "aspect": aspect,
                "voice_mode": voice_mode,
                "emotion_mode": emotion_mode,
                "style": style,
            },
            timeout=120,
        )
        if r.status_code >= 400:
            return {"ok": False, "status": r.status_code, "message": r.text}
        return r.json()
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "message": f"Backend недоступен: {exc}"}


def start_job(job_id: str) -> Dict[str, Any]:
    return _post(f"/api/jobs/{job_id}/start")


def job_status(job_id: str) -> Dict[str, Any]:
    return _get(f"/api/jobs/{job_id}/status")


def job_result(job_id: str) -> Dict[str, Any]:
    return _get(f"/api/jobs/{job_id}/result")


def file_url(job_id: str, name: str) -> str:
    return f"{backend_url()}/api/files/{job_id}/{name}"


def translate_turkmen(text: str, source_lang: str = "ru", style: str = "cultural", emotion: Optional[str] = None) -> Dict[str, Any]:
    return _post(
        "/api/translate/turkmen",
        json={"text": text, "source_lang": source_lang, "style": style, "emotion": emotion},
    )
