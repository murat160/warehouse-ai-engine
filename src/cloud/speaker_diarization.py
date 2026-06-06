"""Murat AI Studio — speaker diarization (актёры/спикеры в видео).

На VPS подключается pyannote.audio:
    from pyannote.audio import Pipeline
    pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1")

Preview-safe: возвращает mock-сегментацию по длине файла.

Public API:
    @dataclass SpeakerSegment
    @dataclass SpeakerProfile
    detect_speakers(audio_path) -> list[SpeakerProfile]
    split_audio_by_speaker(audio_path, segments) -> dict
    assign_voice_to_speaker(speaker_id, voice_profile) -> dict
    replace_speaker_voice(speaker_id, custom_voice_profile) -> dict
    render_multispeaker_dubbing(segments, translations, speaker_profiles) -> list[dict]
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SpeakerSegment:
    speaker_id: str
    start: float
    end: float
    text: str = ""
    emotion: str = "neutral"


@dataclass
class SpeakerProfile:
    speaker_id: str
    role: str
    gender: str = "any"
    age_band: str = "adult"
    dominant_emotion: str = "neutral"
    suggested_voice: str = "Туркменский мужской — чистый"
    replace_mode: str = "Не заменять"
    custom_voice_file: Optional[str] = None
    sample_seconds: float = 0.0


# In-memory voice assignments (на VPS — в Postgres).
_VOICE_ASSIGNMENTS: Dict[str, Dict[str, Any]] = {}


def detect_speakers(audio_path: Optional[str]) -> List[SpeakerProfile]:
    """Mock: возвращает двух дефолтных спикеров.

    На VPS: pyannote.audio Pipeline.from_pretrained("pyannote/speaker-diarization-3.1")
    с прокладкой для эмоции каждого сегмента (wav2vec2-emotion).
    """

    return [
        SpeakerProfile(
            speaker_id="speaker_1",
            role="Актёр 1",
            gender="male",
            dominant_emotion="Нейтрально",
            suggested_voice="Туркменский мужской — чистый",
        ),
        SpeakerProfile(
            speaker_id="speaker_2",
            role="Актёр 2",
            gender="female",
            dominant_emotion="Добрый тон",
            suggested_voice="Туркменский женский — чистый",
        ),
    ]


def split_audio_by_speaker(audio_path: str, segments: List[SpeakerSegment]) -> Dict[str, str]:
    """Возвращает {speaker_id: path_to_concat_audio}. Stub в preview."""

    return {seg.speaker_id: "" for seg in segments}


def assign_voice_to_speaker(speaker_id: str, voice_profile: Dict[str, Any]) -> Dict[str, Any]:
    _VOICE_ASSIGNMENTS[speaker_id] = {"voice_profile": voice_profile, "mode": "catalog"}
    return _VOICE_ASSIGNMENTS[speaker_id]


def replace_speaker_voice(speaker_id: str, custom_voice_profile: Dict[str, Any]) -> Dict[str, Any]:
    _VOICE_ASSIGNMENTS[speaker_id] = {"voice_profile": custom_voice_profile, "mode": "custom"}
    return _VOICE_ASSIGNMENTS[speaker_id]


def render_multispeaker_dubbing(
    segments: List[SpeakerSegment],
    translations: Dict[str, str],
    speaker_profiles: List[SpeakerProfile],
) -> List[Dict[str, Any]]:
    """Возвращает план рендера: что и для кого синтезировать на VPS.

    Используется в src.cloud.video_renderer.render_final_video.
    """

    profiles_by_id = {p.speaker_id: p for p in speaker_profiles}
    plan: List[Dict[str, Any]] = []
    for seg in segments:
        profile = profiles_by_id.get(seg.speaker_id)
        if profile is None:
            continue
        plan.append({
            "speaker_id": seg.speaker_id,
            "start": seg.start,
            "end": seg.end,
            "translation": translations.get(seg.speaker_id, seg.text),
            "voice": profile.suggested_voice,
            "emotion": profile.dominant_emotion,
            "replace_mode": profile.replace_mode,
            "custom_voice_file": profile.custom_voice_file,
        })
    return plan
