"""Murat AI Studio — перенос эмоции оригинала в туркменскую озвучку.

EmotionProfile содержит всё что нужно VITS-модели и post-processing для того,
чтобы туркменская речь звучала с той же подачей, что и оригинал.

Если пользователь ничего не выбрал — берётся эмоция оригинала (через
analyze_emotion_from_audio / analyze_emotion_from_text) и переносится
в tts_params (см. src.cloud.tts_turkmen).

Public API:
    @dataclass EmotionProfile
    analyze_emotion_from_text(text) -> EmotionProfile
    analyze_emotion_from_audio(audio_path) -> EmotionProfile
    create_emotion_profile(source_audio, source_text) -> EmotionProfile
    transfer_emotion_to_tts(emotion_profile, tts_params) -> dict
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


EMOTIONS_CANON = {
    "neutral", "happy", "sad", "angry", "dramatic",
    "calm", "fear", "surprise", "kind", "energetic", "whisper", "promo",
}


@dataclass
class EmotionProfile:
    emotion: str = "neutral"
    intensity: float = 0.5
    speed: float = 1.0
    pitch: float = 1.0
    energy: float = 0.65
    volume: float = 1.0
    pause_style: str = "medium"          # short / medium / long / dramatic
    voice_style: str = "natural"          # cinema / natural / news / child / official / blogger
    confidence: float = 0.5
    source: str = "auto"                  # "manual" если выбрано пользователем

    def to_dict(self) -> Dict[str, Any]:
        return {
            "emotion": self.emotion,
            "intensity": self.intensity,
            "speed": self.speed,
            "pitch": self.pitch,
            "energy": self.energy,
            "volume": self.volume,
            "pause_style": self.pause_style,
            "voice_style": self.voice_style,
            "confidence": self.confidence,
            "source": self.source,
        }


# ---------------------------------------------------------------------------
# Text-based detection.
# ---------------------------------------------------------------------------
_TEXT_RULES = [
    (["happy", "радост", "ура", "счаст", "şat", "begenç"],     EmotionProfile("happy",     0.85, 1.08, 1.04, 0.86, 1.05, "short",     "natural", 0.85)),
    (["sad",   "груст", "плак", "одиноко", "gam", "agla"],     EmotionProfile("sad",       0.80, 0.88, 0.96, 0.42, 0.82, "long",      "cinema",  0.82)),
    (["angry", "злой",  "ненавиж", "сука", "бесит", "gahar"],  EmotionProfile("angry",     0.90, 1.05, 1.06, 0.92, 1.15, "dramatic",  "cinema",  0.88)),
    (["calm",  "спокой","тих",     "rahat"],                   EmotionProfile("calm",      0.55, 0.95, 1.00, 0.70, 0.92, "long",      "natural", 0.76)),
    (["fear",  "страх", "бояз",    "gorky"],                   EmotionProfile("fear",      0.70, 1.04, 1.04, 0.85, 0.95, "medium",    "cinema",  0.74)),
    (["promo", "скидк", "купить",  "арзан"],                   EmotionProfile("promo",     0.80, 1.12, 1.04, 0.88, 1.08, "short",     "promo",   0.80)),
    (["surprise","удивл","ого",    "wow",   "geň"],            EmotionProfile("surprise",  0.75, 1.10, 1.10, 1.15, 1.05, "short",     "natural", 0.72)),
    (["whisper","шёпот","gizlin"],                             EmotionProfile("whisper",   0.50, 0.85, 0.95, 0.40, 0.55, "long",      "natural", 0.65)),
    (["dramatic","кино","drama"],                              EmotionProfile("dramatic",  0.85, 0.92, 1.00, 1.05, 1.00, "dramatic",  "cinema",  0.78)),
]


def analyze_emotion_from_text(text: str) -> EmotionProfile:
    if not text:
        return EmotionProfile()
    t = text.lower()
    for keywords, profile in _TEXT_RULES:
        if any(k in t for k in keywords):
            return profile
    return EmotionProfile()


# ---------------------------------------------------------------------------
# Audio-based detection (preview = stub, VPS = wav2vec/pyAudioAnalysis).
# ---------------------------------------------------------------------------
def analyze_emotion_from_audio(audio_path: Optional[str]) -> EmotionProfile:
    """Stub. На VPS подключается wav2vec2-emotion classifier."""

    return EmotionProfile(source="audio-stub", confidence=0.0)


# ---------------------------------------------------------------------------
# Combined.
# ---------------------------------------------------------------------------
def create_emotion_profile(source_audio: Optional[str], source_text: Optional[str]) -> EmotionProfile:
    """Объединяет оценки audio + text. Audio имеет приоритет если confidence > 0.7."""

    audio_prof = analyze_emotion_from_audio(source_audio)
    text_prof = analyze_emotion_from_text(source_text or "")
    if audio_prof.confidence > 0.7:
        return audio_prof
    return text_prof


# ---------------------------------------------------------------------------
# Transfer to TTS params.
# ---------------------------------------------------------------------------
def transfer_emotion_to_tts(emotion_profile: EmotionProfile, tts_params: Dict[str, Any]) -> Dict[str, Any]:
    """Заливает emotion knobs в готовый словарь tts_params (mutating-safe)."""

    out = dict(tts_params or {})
    out["emotion"] = emotion_profile.emotion
    out["speed"] = emotion_profile.speed
    out["pitch"] = emotion_profile.pitch
    out["energy"] = emotion_profile.energy
    out["volume"] = emotion_profile.volume
    pause_ms = {"short": 80, "medium": 140, "long": 220, "dramatic": 280}.get(emotion_profile.pause_style, 140)
    out["pause_ms"] = pause_ms
    out["voice_style"] = emotion_profile.voice_style
    return out
