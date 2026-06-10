"""Murat AI Studio — внешний Turkmen TTS provider (generic).

Универсальный адаптер: подключает ЛЮБОЙ REST TTS-сервис через env-vars
без хардкода ключей или URL в коде.

Env (Streamlit Secrets / VPS environment):
    TURKMEN_TTS_PROVIDER          — имя провайдера для логов (например "elevenlabs")
    TURKMEN_TTS_API_BASE_URL      — base URL (например "https://api.elevenlabs.io")
    TURKMEN_TTS_API_KEY           — API ключ
    TURKMEN_TTS_VOICE_ID          — id голоса (опционально)
    TURKMEN_TTS_ENDPOINT_TEMPLATE — путь, может содержать {voice_id}
                                    (default "/v1/text-to-speech/{voice_id}")
    TURKMEN_TTS_AUTH_HEADER       — имя header'а (default "xi-api-key")
    TURKMEN_TTS_AUTH_FORMAT       — формат значения ("{key}" / "Bearer {key}",
                                    default "{key}")
    TURKMEN_TTS_BODY_TEMPLATE     — JSON-шаблон body (placeholders: {text},
                                    {voice_id}, {format}, {speed}, {pitch})
    TURKMEN_TTS_RESPONSE_FORMAT   — "audio" (raw bytes) | "json_url"
                                    (default "audio")
    TURKMEN_TTS_RESPONSE_URL_FIELD — для json_url: поле в ответе с URL аудио
                                     (default "audio_url")
    TURKMEN_TTS_OUTPUT_FORMAT     — "mp3" | "wav" (default "mp3")
    TURKMEN_TTS_TIMEOUT_SEC       — timeout запроса (default 60)

Не хранит ключ в коде. Если TURKMEN_TTS_API_KEY не задан — функция вернёт
`{"ok": False, "fallback": True}` чтобы pipeline переключился на MMS-TTS.

Public API:
    get_tts_provider_config() -> dict
    is_provider_configured() -> bool
    synthesize_turkmen_via_provider(
        text, emotion_profile=None, voice_id=None, output_format="mp3"
    ) -> bytes
    postprocess_audio_for_emotion(audio_bytes, emotion_profile, mime) -> bytes
"""

from __future__ import annotations

import json as _json
import logging
import os
import re
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Config.
# ---------------------------------------------------------------------------
def get_tts_provider_config() -> Dict[str, Any]:
    """Читает env, возвращает config dict. Ключ не возвращается в логи."""

    return {
        "provider":            os.environ.get("TURKMEN_TTS_PROVIDER", "").strip(),
        "base_url":            os.environ.get("TURKMEN_TTS_API_BASE_URL", "").strip().rstrip("/"),
        "api_key":             os.environ.get("TURKMEN_TTS_API_KEY", "").strip(),
        "voice_id":            os.environ.get("TURKMEN_TTS_VOICE_ID", "").strip(),
        "endpoint_template":   os.environ.get(
            "TURKMEN_TTS_ENDPOINT_TEMPLATE", "/v1/text-to-speech/{voice_id}"
        ),
        "auth_header":         os.environ.get("TURKMEN_TTS_AUTH_HEADER", "xi-api-key"),
        "auth_format":         os.environ.get("TURKMEN_TTS_AUTH_FORMAT", "{key}"),
        "body_template":       os.environ.get("TURKMEN_TTS_BODY_TEMPLATE", ""),
        "response_format":     os.environ.get("TURKMEN_TTS_RESPONSE_FORMAT", "audio"),
        "response_url_field":  os.environ.get("TURKMEN_TTS_RESPONSE_URL_FIELD", "audio_url"),
        "output_format":       os.environ.get("TURKMEN_TTS_OUTPUT_FORMAT", "mp3"),
        "timeout_sec":         int(os.environ.get("TURKMEN_TTS_TIMEOUT_SEC", "60")),
    }


def is_provider_configured() -> bool:
    cfg = get_tts_provider_config()
    return bool(cfg["base_url"] and cfg["api_key"])


def _safe_provider_label() -> str:
    """Для логов — провайдер + base_url, БЕЗ ключа."""

    cfg = get_tts_provider_config()
    return f"{cfg['provider'] or 'unknown'}@{cfg['base_url']}"


# ---------------------------------------------------------------------------
# Body template rendering (без eval, чистый str.replace).
# ---------------------------------------------------------------------------
_DEFAULT_BODY = (
    '{{"text": {text_json}, "voice_id": {voice_id_json}, '
    '"output_format": {format_json}, "speed": {speed}, "pitch": {pitch}}}'
)


def _render_body(template: str, **placeholders: Any) -> Dict[str, Any]:
    """Подставляет {text}/{voice_id}/{format}/{speed}/{pitch} → JSON dict.

    Использует *_json варианты (с экранированием) чтобы пользовательский
    текст не сломал JSON. Если template пустой — берёт _DEFAULT_BODY.
    """

    tmpl = template.strip() or _DEFAULT_BODY
    rendered = tmpl.format(
        text=placeholders.get("text", ""),
        voice_id=placeholders.get("voice_id", ""),
        format=placeholders.get("format", "mp3"),
        speed=placeholders.get("speed", 1.0),
        pitch=placeholders.get("pitch", 1.0),
        text_json=_json.dumps(placeholders.get("text", ""), ensure_ascii=False),
        voice_id_json=_json.dumps(placeholders.get("voice_id", "")),
        format_json=_json.dumps(placeholders.get("format", "mp3")),
    )
    try:
        return _json.loads(rendered)
    except Exception as exc:  # noqa: BLE001
        logger.error("Невалидный JSON в TURKMEN_TTS_BODY_TEMPLATE: %s", exc)
        raise


# ---------------------------------------------------------------------------
# Synthesis call.
# ---------------------------------------------------------------------------
def synthesize_turkmen_via_provider(
    text: str,
    emotion_profile: Optional[Dict[str, Any]] = None,
    voice_id: Optional[str] = None,
    output_format: str = "mp3",
) -> bytes:
    """Запрос на внешний TTS-сервис. Возвращает audio bytes.

    На ошибку (нет ключа / 4xx / 5xx / сетевая) — поднимает RuntimeError;
    pipeline это ловит и фолбэкается на MMS-TTS.

    Эмоция применяется ДВУМЯ путями:
    1. Передаём speed/pitch в body (если сервис их поддерживает).
    2. После получения audio — post-processing (см. postprocess_audio_for_emotion).
    """

    if not text or not text.strip():
        raise ValueError("text is required")

    cfg = get_tts_provider_config()
    if not cfg["base_url"] or not cfg["api_key"]:
        raise RuntimeError(
            "External TTS provider не настроен: задай TURKMEN_TTS_API_BASE_URL "
            "и TURKMEN_TTS_API_KEY в Streamlit Secrets или env."
        )

    try:
        import requests
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("requests не установлен — добавь в requirements") from exc

    ep = emotion_profile or {}
    speed = float(ep.get("speed", 1.0))
    pitch = float(ep.get("pitch", 1.0))
    vid = voice_id or cfg["voice_id"]
    fmt = output_format or cfg["output_format"]

    endpoint = cfg["endpoint_template"].format(voice_id=vid)
    url = cfg["base_url"] + endpoint

    headers = {
        cfg["auth_header"]: cfg["auth_format"].format(key=cfg["api_key"]),
        "Content-Type": "application/json",
        "Accept": f"audio/{fmt}" if cfg["response_format"] == "audio" else "application/json",
    }

    body = _render_body(
        cfg["body_template"],
        text=text, voice_id=vid, format=fmt, speed=speed, pitch=pitch,
    )

    logger.info(
        "External TTS request → %s (text=%d chars, voice=%s, format=%s)",
        _safe_provider_label(), len(text), vid or "default", fmt,
    )

    try:
        resp = requests.post(url, headers=headers, json=body, timeout=cfg["timeout_sec"])
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"External TTS network error: {exc}") from exc

    if resp.status_code >= 400:
        # БЕЗ ключа в логах.
        body_preview = resp.text[:300] if resp.text else "(empty body)"
        raise RuntimeError(
            f"External TTS HTTP {resp.status_code}: {body_preview}"
        )

    if cfg["response_format"] == "audio":
        return resp.content

    # JSON-ответ с URL: скачиваем по URL отдельным запросом.
    data = resp.json()
    audio_url = data.get(cfg["response_url_field"])
    if not audio_url:
        raise RuntimeError(
            f"External TTS: в JSON нет поля '{cfg['response_url_field']}'. "
            f"Ответ: {_json.dumps(data)[:200]}"
        )
    audio_resp = requests.get(audio_url, timeout=cfg["timeout_sec"])
    if audio_resp.status_code >= 400:
        raise RuntimeError(f"External TTS audio download HTTP {audio_resp.status_code}")
    return audio_resp.content


# ---------------------------------------------------------------------------
# Post-processing для эмоции (поверх любого provider audio).
# ---------------------------------------------------------------------------
def postprocess_audio_for_emotion(
    audio_bytes: bytes,
    emotion_profile: Optional[Dict[str, Any]] = None,
    mime: str = "audio/mp3",
) -> bytes:
    """Применяет эмоциональный post-processing через ffmpeg/pydub.

    На VPS (requirements-full.txt с pydub/librosa/ffmpeg):
    - speed       → atempo filter (0.5..2.0)
    - pitch       → asetrate + atempo комбо (приближённо)
    - volume      → volume filter
    - energy      → дополнительная компрессия + boost
    - pause       → удлинение пауз между фразами (не в этом базовом слое)

    Если pydub/ffmpeg недоступны (Streamlit Cloud preview) — возвращает
    оригинальные bytes без модификации.
    """

    ep = emotion_profile or {}
    speed = float(ep.get("speed", 1.0))
    pitch = float(ep.get("pitch", 1.0))
    volume = float(ep.get("volume", 1.0))

    if abs(speed - 1.0) < 1e-3 and abs(pitch - 1.0) < 1e-3 and abs(volume - 1.0) < 1e-3:
        return audio_bytes

    try:
        from pydub import AudioSegment  # type: ignore
    except Exception:  # noqa: BLE001
        logger.warning("pydub не установлен — post-processing пропущен")
        return audio_bytes

    try:
        fmt = "mp3" if "mp3" in mime else ("wav" if "wav" in mime else "mp3")
        import io as _io
        seg = AudioSegment.from_file(_io.BytesIO(audio_bytes), format=fmt)
        # Pitch shift через frame_rate-trick (приближённо, для production
        # лучше librosa.effects.pitch_shift).
        if abs(pitch - 1.0) > 1e-3:
            new_sr = int(seg.frame_rate * pitch)
            seg = seg._spawn(seg.raw_data, overrides={"frame_rate": new_sr})
            seg = seg.set_frame_rate(44100)
        # Speed через speedup.
        if abs(speed - 1.0) > 1e-3:
            seg = seg.speedup(playback_speed=max(0.5, min(2.0, speed)))
        # Volume gain в dB.
        if abs(volume - 1.0) > 1e-3:
            import math as _m
            gain_db = 20 * _m.log10(max(0.01, volume))
            seg = seg + gain_db

        out = _io.BytesIO()
        seg.export(out, format=fmt)
        return out.getvalue()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Post-processing упал, возвращаю исходник: %s", exc)
        return audio_bytes
