"""Murat AI Studio backend — централизованные настройки.

Все env-vars читаются ОДИН раз здесь. Никакой src.cloud.* не должен лезть
в os.environ напрямую — только через эти getters.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    # --- Хранилище ---
    storage_root: Path

    # --- CORS / hosting ---
    cors_origins: list

    # --- TTS provider (опционально) ---
    tts_provider:        str
    tts_api_base_url:    str
    tts_api_key:         str
    tts_voice_id:        str

    # --- Прочее ---
    service_name:        str
    service_version:     str


def get_settings() -> Settings:
    return Settings(
        storage_root      = Path(os.environ.get("MURAT_AI_STORAGE", "storage")),
        cors_origins      = os.environ.get("MURAT_AI_CORS_ORIGINS", "*").split(","),
        tts_provider      = os.environ.get("TURKMEN_TTS_PROVIDER", ""),
        tts_api_base_url  = os.environ.get("TURKMEN_TTS_API_BASE_URL", ""),
        tts_api_key       = os.environ.get("TURKMEN_TTS_API_KEY", ""),
        tts_voice_id      = os.environ.get("TURKMEN_TTS_VOICE_ID", ""),
        service_name      = "Murat AI Studio Backend",
        service_version   = "2.1.0",
    )


def healthcheck_payload() -> dict:
    """Расширенный healthcheck — что доступно на этом backend."""

    s = get_settings()

    def _has(mod: str) -> bool:
        try:
            __import__(mod)
            return True
        except Exception:  # noqa: BLE001
            return False

    storage_ready = s.storage_root.exists() or _try_mkdir(s.storage_root)
    return {
        "ok":              True,
        "service":         s.service_name,
        "version":         s.service_version,
        "storage_ready":   storage_ready,
        "storage_root":    str(s.storage_root),
        "yt_dlp":          _has("yt_dlp"),
        "ffmpeg":          _has("ffmpeg"),
        "torch":           _has("torch"),
        "transformers":    _has("transformers"),
        "whisper":         _has("whisper"),
        "scipy":           _has("scipy"),
        "tts_provider":    s.tts_provider if (s.tts_api_base_url and s.tts_api_key) else "",
        "tts_configured":  bool(s.tts_api_base_url and s.tts_api_key),
    }


def _try_mkdir(p: Path) -> bool:
    try:
        p.mkdir(parents=True, exist_ok=True)
        return True
    except Exception:  # noqa: BLE001
        return False
