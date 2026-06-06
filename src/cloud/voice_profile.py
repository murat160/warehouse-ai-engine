"""Murat AI Studio — voice cloning / голосовой профиль пользователя.

Пользователь загружает 30–40 сек MP3/WAV. Сервис:
1. чистит шум,
2. удаляет эхо,
3. выравнивает громкость,
4. строит voice profile (на VPS: RVC / OpenVoice embedding),
5. применяет профиль к синтезированной туркменской речи.

Preview-safe: возвращает dataclass без реальных эмбеддингов.

Public API:
    clean_voice(audio_file) -> bytes
    remove_noise(audio_file) -> bytes
    remove_echo(audio_file) -> bytes
    normalize_voice(audio_file) -> bytes
    create_voice_profile(audio_file) -> VoiceProfile
    apply_voice_profile(text, voice_profile, emotion_profile) -> bytes
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Union

logger = logging.getLogger(__name__)

OUT_DIR = Path("out") / "voice"
OUT_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class VoiceProfile:
    id: str
    name: str
    source_path: Optional[str] = None
    cleaned: bool = False
    style: str = "natural"
    sample_seconds: float = 0.0
    embedding_path: Optional[str] = None     # на VPS: путь к .npy embedding
    extra: Dict[str, Any] = field(default_factory=dict)


def _load_bytes(audio_file: Union[str, bytes, Path]) -> bytes:
    if isinstance(audio_file, bytes):
        return audio_file
    return Path(audio_file).read_bytes() if Path(audio_file).exists() else b""


def remove_noise(audio_file: Union[str, bytes, Path]) -> bytes:
    """Шумоподавление. На VPS — noisereduce / RNNoise. В preview — pass-through."""

    return _load_bytes(audio_file)


def remove_echo(audio_file: Union[str, bytes, Path]) -> bytes:
    """Удаление эха. На VPS — librosa / speexdsp. В preview — pass-through."""

    return _load_bytes(audio_file)


def normalize_voice(audio_file: Union[str, bytes, Path]) -> bytes:
    """Громкость → -1 dB headroom. На VPS — pyloudnorm. В preview — pass-through."""

    return _load_bytes(audio_file)


def clean_voice(audio_file: Union[str, bytes, Path]) -> bytes:
    """Полная очистка: noise → echo → normalize."""

    data = remove_noise(audio_file)
    data = remove_echo(data)
    data = normalize_voice(data)
    return data


def create_voice_profile(audio_file: Union[str, bytes, Path], name: str = "Мой голос") -> VoiceProfile:
    """Создаёт voice profile. На VPS — RVC / OpenVoice embedding extraction."""

    source = str(audio_file) if not isinstance(audio_file, bytes) else "memory"
    return VoiceProfile(
        id=f"voice_{uuid.uuid4().hex[:8]}",
        name=name,
        source_path=source,
        cleaned=True,
        style="custom",
        sample_seconds=30.0,
    )


def apply_voice_profile(
    text: str,
    voice_profile: VoiceProfile,
    emotion_profile: Optional[Dict[str, Any]] = None,
) -> bytes:
    """Применяет voice profile к туркменскому тексту.

    На VPS pipeline:
        1) synthesize_turkmen_tts → base WAV
        2) RVC convert через voice_profile.embedding_path
        3) post-process emotion (speed/pitch/energy)
    Preview: пробуем синтез MMS-TTS, возвращаем bytes.
    """

    try:
        from .tts_turkmen import (  # type: ignore
            TurkmenEmotionProfile,
            TurkmenVoiceProfile,
            get_emotion_preset,
            synthesize_turkmen_tts,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("MMS-TTS unavailable: %s", exc)
        return b""
    emotion_label = (emotion_profile or {}).get("emotion") if emotion_profile else "Нейтрально"
    preset = get_emotion_preset(emotion_label)
    vp = TurkmenVoiceProfile(id=voice_profile.id, name=voice_profile.name, custom_voice_path=voice_profile.source_path)
    try:
        path = synthesize_turkmen_tts(text, emotion_profile=preset, voice_profile=vp)
        return Path(path).read_bytes()
    except Exception as exc:  # noqa: BLE001
        logger.warning("synthesize_turkmen_tts failed: %s", exc)
        return b""
