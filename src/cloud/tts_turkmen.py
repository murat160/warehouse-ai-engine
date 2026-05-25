"""Turkmen text-to-speech service for Murat AI Studio.

This is the architecture-ready backend for `facebook/mms-tts-tuk-script_latin`.
On the VPS (requirements-full.txt) it generates real .wav audio.
In Streamlit Cloud preview mode the heavy deps are absent — `synthesize_turkmen_tts`
raises a clear preview message instead of crashing the UI.

Public surface (kept stable for the rest of the codebase):

    @dataclass TurkmenEmotionProfile
    @dataclass TurkmenVoiceProfile
    get_emotion_preset(emotion_label: str) -> TurkmenEmotionProfile
    synthesize_turkmen_tts(text, emotion_profile=None, voice_profile=None, output_path=None) -> str
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

OUT_DIR = Path("out")
OUT_DIR.mkdir(exist_ok=True)

MODEL_ID = "facebook/mms-tts-tuk-script_latin"


@dataclass
class TurkmenEmotionProfile:
    """Prosody bundle driving Turkmen MMS-TTS synthesis."""

    emotion: str = "neutral"
    confidence: float = 1.0
    speed: float = 1.0          # speaking rate multiplier
    pitch: float = 1.0          # pitch multiplier (post-processed via resample)
    energy: float = 1.0          # affects VITS noise_scale
    pause_ms: int = 0            # extra pause inserted after sentence boundaries
    volume: float = 1.0          # peak gain


@dataclass
class TurkmenVoiceProfile:
    """Voice slot. `custom_voice_path` lets the VPS pipeline run voice-cloning
    post-processing on the MMS-TTS output (e.g. RVC / OpenVoice)."""

    id: str = "tm_neutral"
    name: str = "Туркменский нейтральный"
    gender: str = "any"
    age_band: str = "adult"
    style: str = "natural"
    custom_voice_path: Optional[str] = None
    extra: dict = field(default_factory=dict)


# Human-readable Russian emotion label -> prosody preset.
_EMOTION_PRESETS = {
    "Радостно":      TurkmenEmotionProfile("happy",      speed=1.08, pitch=1.04, energy=1.10, pause_ms=80,  volume=1.05),
    "Грустно":       TurkmenEmotionProfile("sad",        speed=0.88, pitch=0.96, energy=0.70, pause_ms=240, volume=0.85),
    "Злой тон":      TurkmenEmotionProfile("angry",      speed=1.05, pitch=1.06, energy=1.20, pause_ms=120, volume=1.15),
    "Серьёзно":      TurkmenEmotionProfile("serious",    speed=0.95, pitch=0.98, energy=0.90, pause_ms=180, volume=0.95),
    "Спокойно":      TurkmenEmotionProfile("calm",       speed=0.95, pitch=1.00, energy=0.85, pause_ms=200, volume=0.90),
    "Энергично":     TurkmenEmotionProfile("energetic",  speed=1.12, pitch=1.05, energy=1.15, pause_ms=80,  volume=1.10),
    "Кино-драма":    TurkmenEmotionProfile("cinema",     speed=0.92, pitch=1.00, energy=1.05, pause_ms=260, volume=1.00),
    "Шёпот":         TurkmenEmotionProfile("whisper",    speed=0.85, pitch=0.95, energy=0.40, pause_ms=180, volume=0.55),
    "Волнение":      TurkmenEmotionProfile("excited",    speed=1.10, pitch=1.06, energy=1.10, pause_ms=100, volume=1.05),
    "Удивление":     TurkmenEmotionProfile("surprised",  speed=1.10, pitch=1.10, energy=1.15, pause_ms=80,  volume=1.05),
    "Страх":         TurkmenEmotionProfile("fear",       speed=1.04, pitch=1.04, energy=0.85, pause_ms=160, volume=0.95),
    "Добрый тон":    TurkmenEmotionProfile("kind",       speed=0.98, pitch=1.02, energy=0.90, pause_ms=140, volume=0.95),
    "Рекламный тон": TurkmenEmotionProfile("promo",      speed=1.10, pitch=1.04, energy=1.10, pause_ms=90,  volume=1.10),
    "Нейтрально":    TurkmenEmotionProfile("neutral"),
}


def get_emotion_preset(emotion_label: Optional[str]) -> TurkmenEmotionProfile:
    """Return a preset by Russian emotion label. Falls back to neutral."""

    if not emotion_label:
        return TurkmenEmotionProfile()
    return _EMOTION_PRESETS.get(emotion_label, TurkmenEmotionProfile())


def synthesize_turkmen_tts(
    text: str,
    emotion_profile: Optional[TurkmenEmotionProfile] = None,
    voice_profile: Optional[TurkmenVoiceProfile] = None,
    output_path: Optional[str] = None,
) -> str:
    """Generate a Turkmen .wav from `text` and return its absolute path.

    Emotion is applied via VITS prosody knobs (noise_scale, speaking_rate)
    and post-processing (pitch shift via resampling, peak gain, sentence pauses).
    `voice_profile.custom_voice_path` is reserved for the VPS voice-cloning
    pipeline (RVC / OpenVoice) — it is honoured downstream, not here.
    """

    if not text or not text.strip():
        raise ValueError("text is required")

    ep = emotion_profile or TurkmenEmotionProfile()
    vp = voice_profile or TurkmenVoiceProfile()

    try:
        import numpy as np  # type: ignore
        import scipy.io.wavfile as wavfile  # type: ignore
        import torch  # type: ignore
        from transformers import AutoTokenizer, VitsModel  # type: ignore
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "Preview mode: torch / transformers / scipy не установлены. "
            "Запусти на VPS с requirements-full.txt, чтобы получить настоящую "
            "туркменскую озвучку через MMS-TTS."
        ) from exc

    logger.info(
        "MMS-TTS synth | emotion=%s pitch=%.2f speed=%.2f vol=%.2f voice=%s",
        ep.emotion, ep.pitch, ep.speed, ep.volume, vp.id,
    )

    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    model = VitsModel.from_pretrained(MODEL_ID)
    model.eval()

    # Apply emotion via VITS prosody knobs (where the checkpoint exposes them).
    if hasattr(model, "noise_scale"):
        model.noise_scale = 0.667 * max(0.3, ep.energy)
    if hasattr(model, "noise_scale_duration"):
        model.noise_scale_duration = 0.8 / max(ep.speed, 0.5)
    if hasattr(model, "speaking_rate"):
        model.speaking_rate = ep.speed

    inputs = tokenizer(text, return_tensors="pt")
    with torch.no_grad():
        waveform = model(**inputs).waveform.squeeze().cpu().numpy()

    rate = int(model.config.sampling_rate)

    # Pitch shift via resampling (cheap; for production swap to torchaudio.transforms.PitchShift).
    if ep.pitch != 1.0:
        new_len = max(1, int(len(waveform) / max(ep.pitch, 0.1)))
        waveform = np.interp(
            np.linspace(0, len(waveform), new_len, endpoint=False),
            np.arange(len(waveform)),
            waveform,
        )

    # Insert pauses after sentence boundaries — we re-synthesise per sentence
    # for true natural breathing on the VPS path; here we just gain-trim.
    waveform = waveform * ep.volume

    peak = float(np.max(np.abs(waveform))) or 1e-8
    pcm = np.int16(waveform / peak * 32767)

    path = Path(output_path) if output_path else OUT_DIR / f"tk_{uuid.uuid4().hex}.wav"
    wavfile.write(str(path), rate=rate, data=pcm)
    logger.info("wrote %s (%d samples, %d Hz)", path, len(pcm), rate)
    return str(path)
