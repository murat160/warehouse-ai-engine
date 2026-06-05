"""Turkmen text-to-speech service для Murat AI Studio.

Этот модуль ОБЯЗАН выдавать настоящую туркменскую озвучку через
Meta MMS-TTS (`facebook/mms-tts-tuk-script_latin`).
В Streamlit Cloud preview deps (torch CPU + transformers + scipy + numpy)
подняты в requirements.txt — модель работает прямо в браузере.

Главные возможности:
- разбивка по предложениям с естественной паузой между ними;
- эмоция через VITS prosody (noise_scale, noise_scale_duration, speaking_rate);
- pitch shift через resampling;
- volume gain;
- кэширование модели в самом модуле (быстрый второй вызов).

Public API:
    @dataclass TurkmenEmotionProfile
    @dataclass TurkmenVoiceProfile
    get_emotion_preset(emotion_label) -> TurkmenEmotionProfile
    synthesize_turkmen_tts(text, emotion_profile=None, voice_profile=None, output_path=None) -> str
    normalize_turkmen_text(text) -> str
    load_mms_tts_model() -> tuple[tokenizer, model]
"""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

OUT_DIR = Path("out")
OUT_DIR.mkdir(exist_ok=True)

MODEL_ID = "facebook/mms-tts-tuk-script_latin"

# Кэш модели в памяти процесса.
_MODEL_CACHE: dict = {}


# ---------------------------------------------------------------------------
# Public dataclasses.
# ---------------------------------------------------------------------------
@dataclass
class TurkmenEmotionProfile:
    """Prosody bundle. Все значения умножаются на дефолтные модели MMS-TTS."""

    emotion: str = "neutral"
    confidence: float = 1.0
    speed: float = 1.0          # speaking rate multiplier (0.8 — медленно, 1.15 — быстро)
    pitch: float = 1.0          # pitch multiplier (резамплинг)
    energy: float = 1.0          # → VITS noise_scale (0.4..1.2)
    pause_ms: int = 120          # пауза между предложениями
    volume: float = 1.0          # peak gain (clamp на ±1.0 на выходе)


@dataclass
class TurkmenVoiceProfile:
    id: str = "tm_neutral"
    name: str = "Туркменский нейтральный"
    gender: str = "any"
    age_band: str = "adult"
    style: str = "natural"
    custom_voice_path: Optional[str] = None
    extra: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Эмоциональные пресеты — настроены по русским labels из UI.
# ---------------------------------------------------------------------------
_EMOTION_PRESETS = {
    "Радостно":      TurkmenEmotionProfile("happy",     speed=1.08, pitch=1.04, energy=1.10, pause_ms=90,  volume=1.05),
    "Грустно":       TurkmenEmotionProfile("sad",       speed=0.88, pitch=0.96, energy=0.70, pause_ms=240, volume=0.85),
    "Злой тон":      TurkmenEmotionProfile("angry",     speed=1.05, pitch=1.06, energy=1.20, pause_ms=130, volume=1.15),
    "Серьёзно":      TurkmenEmotionProfile("serious",   speed=0.95, pitch=0.98, energy=0.90, pause_ms=180, volume=0.95),
    "Спокойно":      TurkmenEmotionProfile("calm",      speed=0.95, pitch=1.00, energy=0.85, pause_ms=210, volume=0.90),
    "Энергично":     TurkmenEmotionProfile("energetic", speed=1.12, pitch=1.05, energy=1.15, pause_ms=85,  volume=1.10),
    "Кино-драма":    TurkmenEmotionProfile("cinema",    speed=0.92, pitch=1.00, energy=1.05, pause_ms=260, volume=1.00),
    "Шёпот":         TurkmenEmotionProfile("whisper",   speed=0.85, pitch=0.95, energy=0.45, pause_ms=200, volume=0.55),
    "Волнение":      TurkmenEmotionProfile("excited",   speed=1.10, pitch=1.06, energy=1.10, pause_ms=100, volume=1.05),
    "Удивление":     TurkmenEmotionProfile("surprised", speed=1.10, pitch=1.10, energy=1.15, pause_ms=80,  volume=1.05),
    "Страх":         TurkmenEmotionProfile("fear",      speed=1.04, pitch=1.04, energy=0.85, pause_ms=160, volume=0.95),
    "Добрый тон":    TurkmenEmotionProfile("kind",      speed=0.98, pitch=1.02, energy=0.90, pause_ms=150, volume=0.95),
    "Рекламный тон": TurkmenEmotionProfile("promo",     speed=1.10, pitch=1.04, energy=1.10, pause_ms=95,  volume=1.10),
    "Нейтрально":    TurkmenEmotionProfile("neutral"),
}


def get_emotion_preset(emotion_label: Optional[str]) -> TurkmenEmotionProfile:
    if not emotion_label:
        return TurkmenEmotionProfile()
    return _EMOTION_PRESETS.get(emotion_label, TurkmenEmotionProfile())


# ---------------------------------------------------------------------------
# Загрузка модели (кэшируется на процесс).
# ---------------------------------------------------------------------------
def load_mms_tts_model() -> Tuple:
    """Возвращает (tokenizer, model). Кэшируется в памяти процесса."""

    if "tok" in _MODEL_CACHE and "model" in _MODEL_CACHE:
        return _MODEL_CACHE["tok"], _MODEL_CACHE["model"]

    from transformers import AutoTokenizer, VitsModel  # type: ignore

    logger.info("Загрузка MMS-TTS %s …", MODEL_ID)
    tok = AutoTokenizer.from_pretrained(MODEL_ID)
    model = VitsModel.from_pretrained(MODEL_ID)
    model.eval()
    _MODEL_CACHE["tok"] = tok
    _MODEL_CACHE["model"] = model
    logger.info("MMS-TTS загружен (sampling_rate=%d)", int(model.config.sampling_rate))
    return tok, model


# ---------------------------------------------------------------------------
# Нормализация текста — модель ждёт латиницу (туркменский алфавит).
# ---------------------------------------------------------------------------
# Минимальная транслитерация рус→тм (для случая когда туркменский текст
# случайно пришёл в кириллице — модель не должна крашиться).
_CYR_TO_LAT = {
    "а": "a", "б": "b", "в": "w", "г": "g", "д": "d", "е": "ý",  "ё": "ýo",
    "ж": "ž", "з": "z", "и": "i", "й": "ý", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "h", "ц": "ts","ч": "ç", "ш": "ş", "щ": "şç","ъ": "",
    "ы": "y", "ь": "", "э": "e", "ю": "ýu","я": "ýa","ң": "ň", "ө": "ö",
    "ү": "ü", "ә": "ä", "җ": "j",
}


def normalize_turkmen_text(text: str) -> str:
    """Приводит текст к чистой туркменской латинице для MMS-TTS.

    Если внутри попалась кириллица — транслитерируем.
    Выкидываем символы, которые сбивают prosody (несколько пробелов, кавычки).
    """

    if not text:
        return ""
    s = text.strip()
    out_chars = []
    for ch in s:
        low = ch.lower()
        if low in _CYR_TO_LAT:
            rep = _CYR_TO_LAT[low]
            out_chars.append(rep.upper() if ch.isupper() else rep)
        else:
            out_chars.append(ch)
    s = "".join(out_chars)
    s = re.sub(r"\s+", " ", s)
    s = s.replace("«", '"').replace("»", '"')
    return s.strip()


# ---------------------------------------------------------------------------
# Сплит по предложениям.
# ---------------------------------------------------------------------------
def split_sentences(text: str) -> List[str]:
    """Разбивает текст на предложения. Между ними потом вставляется пауза."""

    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


# ---------------------------------------------------------------------------
# Главная функция синтеза.
# ---------------------------------------------------------------------------
def synthesize_turkmen_tts(
    text: str,
    emotion_profile: Optional[TurkmenEmotionProfile] = None,
    voice_profile: Optional[TurkmenVoiceProfile] = None,
    output_path: Optional[str] = None,
) -> str:
    """Генерирует туркменский .wav и возвращает путь к нему.

    Алгоритм:
      1. Нормализация текста (кириллица→латиница, чистка пробелов).
      2. Разбивка на предложения.
      3. Для каждого предложения — отдельный inference (MMS-TTS).
      4. Между предложениями — пауза emotion_profile.pause_ms.
      5. Pitch shift через resample, volume gain, peak normalisation.
      6. Запись в .wav.

    На VPS / Streamlit Cloud работает одинаково — torch CPU тянет модель.
    """

    if not text or not text.strip():
        raise ValueError("text is required")

    ep = emotion_profile or TurkmenEmotionProfile()
    vp = voice_profile or TurkmenVoiceProfile()

    try:
        import numpy as np  # type: ignore
        import scipy.io.wavfile as wavfile  # type: ignore
        import torch  # type: ignore
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "Не установлены torch / scipy / numpy. Они есть в requirements.txt — "
            "если ты их видишь, значит Streamlit Cloud не пересобрался."
        ) from exc

    tok, model = load_mms_tts_model()
    sampling_rate = int(model.config.sampling_rate)

    # Применяем эмоцию к модели (там где чекпоинт это поддерживает).
    if hasattr(model, "noise_scale"):
        model.noise_scale = max(0.3, min(1.4, 0.667 * ep.energy))
    if hasattr(model, "noise_scale_duration"):
        model.noise_scale_duration = 0.8 / max(ep.speed, 0.5)
    if hasattr(model, "speaking_rate"):
        model.speaking_rate = ep.speed

    norm_text = normalize_turkmen_text(text)
    sentences = split_sentences(norm_text) or [norm_text]

    pause_samples = int(sampling_rate * ep.pause_ms / 1000.0)
    silence = np.zeros(pause_samples, dtype=np.float32)

    waveforms: List[np.ndarray] = []
    for i, sentence in enumerate(sentences):
        if not sentence.strip():
            continue
        inputs = tok(sentence, return_tensors="pt")
        with torch.no_grad():
            chunk = model(**inputs).waveform.squeeze().cpu().numpy().astype(np.float32)
        waveforms.append(chunk)
        if i < len(sentences) - 1 and pause_samples > 0:
            waveforms.append(silence.copy())

    if not waveforms:
        raise RuntimeError("Синтез не дал ни одного предложения.")

    waveform = np.concatenate(waveforms)

    # Pitch shift через resample (изменяет одновременно тон и длительность).
    if abs(ep.pitch - 1.0) > 1e-3:
        new_len = max(1, int(len(waveform) / max(ep.pitch, 0.1)))
        idx = np.linspace(0, len(waveform), new_len, endpoint=False)
        waveform = np.interp(idx, np.arange(len(waveform)), waveform).astype(np.float32)

    # Volume gain.
    waveform = waveform * ep.volume

    # Peak normalisation (−1 dB headroom).
    peak = float(np.max(np.abs(waveform))) or 1e-8
    target = 0.89  # ≈ -1 dB
    if peak > 0:
        waveform = waveform * (target / peak)

    pcm = np.int16(np.clip(waveform, -1.0, 1.0) * 32767)

    path = Path(output_path) if output_path else OUT_DIR / f"tk_{uuid.uuid4().hex}.wav"
    wavfile.write(str(path), rate=sampling_rate, data=pcm)
    logger.info(
        "MMS-TTS done: %s | %d sentences | %.1fs | emotion=%s",
        path, len(sentences), len(pcm) / sampling_rate, ep.emotion,
    )
    return str(path)
