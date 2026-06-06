"""Murat AI Studio — скачивание видео по ссылке через yt-dlp.

В Streamlit Cloud preview yt-dlp не установлен и скачивать видео мы не можем —
функция возвращает понятное сообщение. На VPS yt-dlp есть в
requirements-full.txt и реально скачивает.

Public API:
    download_video_from_url(url, output_dir) -> dict
    validate_url(url) -> dict
    extract_video_metadata(url) -> dict
    get_video_preview(url) -> dict
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

OUT_DIR = Path("out") / "video"
OUT_DIR.mkdir(parents=True, exist_ok=True)

_URL_RE = re.compile(r"^https?://[\w.\-]+(/[^\s]*)?$", re.I)
_SUPPORTED_HOSTS = (
    "youtube.com", "youtu.be", "tiktok.com", "instagram.com",
    "facebook.com", "vimeo.com", "twitter.com", "x.com",
)


def validate_url(url: str) -> Dict[str, Any]:
    if not url or not isinstance(url, str):
        return {"ok": False, "message": "Пустой URL."}
    if not _URL_RE.match(url.strip()):
        return {"ok": False, "message": "Неверный формат URL (должен начинаться с http:// или https://)."}
    return {"ok": True, "message": "URL принят."}


def extract_video_metadata(url: str) -> Dict[str, Any]:
    """Возвращает title/duration/uploader. На VPS — yt-dlp --print-json."""

    try:
        import yt_dlp  # type: ignore
    except Exception:  # noqa: BLE001
        return {
            "ok": False,
            "message": "yt-dlp не установлен в preview. Метаданные ссылок доступны только на VPS.",
            "metadata": {},
        }
    try:
        with yt_dlp.YoutubeDL({"quiet": True, "skip_download": True}) as ydl:
            info = ydl.extract_info(url, download=False)
        return {
            "ok": True,
            "message": "Метаданные получены.",
            "metadata": {
                "title": info.get("title"),
                "duration": info.get("duration"),
                "uploader": info.get("uploader"),
                "thumbnail": info.get("thumbnail"),
            },
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "message": f"Ошибка yt-dlp: {exc}", "metadata": {}}


def download_video_from_url(url: str, output_dir: Optional[str] = None) -> Dict[str, Any]:
    """Скачивает видео по ссылке. На VPS — реальный yt-dlp."""

    check = validate_url(url)
    if not check["ok"]:
        return {"ok": False, "message": check["message"], "path": ""}

    try:
        import yt_dlp  # type: ignore
    except Exception:  # noqa: BLE001
        return {
            "ok": False,
            "message": (
                "Скачивание ссылок работает на VPS / backend через yt-dlp. "
                "В Streamlit Cloud preview этот модуль не установлен — "
                "используйте загрузку файла вручную."
            ),
            "path": "",
        }

    out = Path(output_dir or OUT_DIR)
    out.mkdir(parents=True, exist_ok=True)
    opts = {
        "outtmpl": str(out / "%(id)s.%(ext)s"),
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "quiet": True,
        "noprogress": True,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
        return {"ok": True, "message": "Видео скачано.", "path": filename}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "message": f"Ошибка скачивания: {exc}", "path": ""}


def get_video_preview(url: str) -> Dict[str, Any]:
    """Возвращает thumbnail + 5-секундный embed. На preview — ссылка YouTube embed."""

    if "youtube.com/watch" in url or "youtu.be/" in url:
        vid = ""
        m = re.search(r"(?:v=|youtu\.be/)([\w\-]+)", url)
        if m:
            vid = m.group(1)
        return {
            "ok": True,
            "embed_url": f"https://www.youtube.com/embed/{vid}" if vid else "",
            "thumbnail": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg" if vid else "",
        }
    return {"ok": True, "embed_url": url, "thumbnail": ""}
