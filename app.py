"""Murat AI Studio — Streamlit entry point.

Спецификация:
- Верхний блок: «Исходное видео» (слева) → стрелка → «Готовое видео» (справа).
  Карточки одинаковой высоты, одинаковой ширины, одинаковая рамка устройства.
- ФОРМАТ ВИДЕО и ЭКРАН ПРОСМОТРА — два независимых селектора.
- Туркменский TTS — отдельный сервис src.cloud.tts_turkmen.synthesize_turkmen_tts.
- Эмоции автоматически передаются в озвучку (speed/pitch/energy/pause/volume).
- Архитектура готова под backend: translate_to_turkmen, detect_speakers,
  fit_translation_to_timeline, create_voice_profile, clean_voice,
  apply_voice_profile.
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import streamlit as st
import streamlit.components.v1 as components

# ---------------------------------------------------------------------------
# BUILD marker (визуально вверху страницы — чтобы сразу видеть, что задеплоен
# именно этот код, а не старый кэш Streamlit Cloud).
# ---------------------------------------------------------------------------
BUILD = "claude-aligned-video-studio / 2026-05-24-22:00"
TURKMEN_TTS_BACKEND = "facebook/mms-tts-tuk-script_latin"

st.set_page_config(
    page_title="Murat AI Studio",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ---------------------------------------------------------------------------
# Константы каталогов.
# ---------------------------------------------------------------------------
LANGS: Dict[str, str] = {
    "ru": "Русский",
    "tk": "Туркменский",
    "tr": "Турецкий",
    "en": "Английский",
}

FORMATS: Dict[str, Dict[str, str]] = {
    "9:16 Shorts / Reels / TikTok": {"ratio": "9 / 16", "label": "9:16"},
    "16:9 YouTube":                  {"ratio": "16 / 9", "label": "16:9"},
    "1:1 Square":                    {"ratio": "1 / 1",  "label": "1:1"},
    "Original":                      {"ratio": "16 / 9", "label": "Оригинал"},
}

# `max` — максимальная ширина внешней рамки устройства, чтобы блок не
# раздувался на весь экран. `kind` — CSS-класс для рамки.
SCREENS: Dict[str, Dict[str, Any]] = {
    "📱 Телефон вертикальный":   {"max": 300, "kind": "phone-v", "label": "Телефон верт."},
    "📱 Телефон горизонтальный": {"max": 540, "kind": "phone-h", "label": "Телефон гориз."},
    "💻 Планшет":                {"max": 460, "kind": "tablet",  "label": "Планшет"},
    "💻 Ноутбук":                {"max": 560, "kind": "laptop",  "label": "Ноутбук"},
    "🖥 Монитор 19\"":           {"max": 520, "kind": "monitor", "label": "Монитор 19″"},
    "🖥 Монитор 24\"":           {"max": 620, "kind": "monitor", "label": "Монитор 24″"},
    "📺 Телевизор":              {"max": 640, "kind": "tv",      "label": "Телевизор"},
    "🟦 Без рамки":              {"max": 560, "kind": "bare",    "label": "Без рамки"},
}

QUALITIES = ["1080p", "4K", "8K"]

EMOTIONS = [
    "Автоматически по оригиналу",
    "Нейтрально",
    "Радостно",
    "Грустно",
    "Серьёзно",
    "Злой тон",
    "Спокойно",
    "Энергично",
    "Кино-драма",
    "Шёпот",
    "Волнение",
    "Удивление",
    "Страх",
    "Добрый тон",
    "Рекламный тон",
]

VOICE_CATALOG: List[Dict[str, Any]] = [
    {"id": "tm_male_clean",      "name": "Туркменский мужской — чистый",   "lang": "tk", "gender": "male",   "age": "взрослый", "style": "чистый",       "best_for": ["Нейтрально", "Серьёзно", "Спокойно"]},
    {"id": "tm_female_clean",    "name": "Туркменский женский — чистый",   "lang": "tk", "gender": "female", "age": "взрослый", "style": "чистый",       "best_for": ["Нейтрально", "Добрый тон", "Радостно"]},
    {"id": "tm_narrator",        "name": "Туркменский диктор",              "lang": "tk", "gender": "male",   "age": "взрослый", "style": "диктор",       "best_for": ["Серьёзно", "Кино-драма", "Спокойно"]},
    {"id": "tm_male_warm",       "name": "Туркменский мужской — тёплый",   "lang": "tk", "gender": "male",   "age": "взрослый", "style": "тёплый",       "best_for": ["Добрый тон", "Спокойно", "Нейтрально"]},
    {"id": "tm_female_warm",     "name": "Туркменский женский — тёплый",   "lang": "tk", "gender": "female", "age": "взрослый", "style": "тёплый",       "best_for": ["Добрый тон", "Радостно"]},
    {"id": "boy_6_8_soft",       "name": "Мальчик 6–8 лет — мягкий",       "lang": "ru", "gender": "male",   "age": "ребёнок",  "style": "мягкий",       "best_for": ["Добрый тон", "Грустно", "Нейтрально"]},
    {"id": "boy_9_12_energy",    "name": "Мальчик 9–12 лет — энергичный",  "lang": "ru", "gender": "male",   "age": "ребёнок",  "style": "энергичный",   "best_for": ["Радостно", "Энергично", "Удивление"]},
    {"id": "girl_6_8_soft",      "name": "Девочка 6–8 лет — нежная",       "lang": "ru", "gender": "female", "age": "ребёнок",  "style": "нежный",       "best_for": ["Добрый тон", "Радостно"]},
    {"id": "girl_9_12_happy",    "name": "Девочка 9–12 лет — радостная",   "lang": "ru", "gender": "female", "age": "ребёнок",  "style": "радостный",    "best_for": ["Радостно", "Энергично", "Волнение"]},
    {"id": "male_cinema",        "name": "Мужской кино-диктор",            "lang": "ru", "gender": "male",   "age": "взрослый", "style": "кино",          "best_for": ["Кино-драма", "Серьёзно", "Злой тон"]},
    {"id": "female_blogger",     "name": "Женский блогерский",             "lang": "ru", "gender": "female", "age": "взрослый", "style": "блогерский",   "best_for": ["Радостно", "Энергично", "Рекламный тон"]},
    {"id": "custom_voice",       "name": "Мой загруженный голос",          "lang": "any","gender": "any",    "age": "пользовательский", "style": "клон", "best_for": EMOTIONS[1:]},
]

VOICE_NAMES = [v["name"] for v in VOICE_CATALOG]

SAMPLES = {
    "ru": "Привет, это пример моего голоса для озвучки видео.",
    "tk": "Salam, bu wideony seslendirmek üçin ses nusgasydyr.",
    "tr": "Merhaba, bu video seslendirme için örnek sestir.",
    "en": "Hello, this is a sample voice for video dubbing.",
}


# ---------------------------------------------------------------------------
# Архитектурные dataclass'ы.
# ---------------------------------------------------------------------------
@dataclass
class EmotionProfile:
    emotion: str = "Нейтрально"
    confidence: int = 65
    speed: float = 1.0
    pitch: float = 1.0
    energy: float = 0.65
    pauses: str = "средние"
    volume: float = 1.0


@dataclass
class SpeakerProfile:
    id: str
    role: str
    gender: str = "any"
    age_band: str = "adult"
    dominant_emotion: str = "Нейтрально"
    suggested_voice: str = "Туркменский мужской — чистый"
    replace_mode: str = "Не заменять"
    custom_voice_file: Optional[str] = None


@dataclass
class VoiceProfile:
    id: str
    name: str
    source_path: Optional[str] = None
    cleaned: bool = False
    style: str = "natural"


# ---------------------------------------------------------------------------
# State.
# ---------------------------------------------------------------------------
def init_state() -> None:
    """Initialise session-state defaults exactly once."""

    defaults: Dict[str, Any] = {
        "video_file": None,
        "video_url": "",
        "audio_file": None,
        "voice_file": None,
        "source_text": "Привет. Я хочу сделать профессиональное короткое видео с переводом и озвучкой на туркменском.",
        "result_text": "",
        "result_ready": False,
        "tts_audio_bytes": b"",
        "tts_audio_message": "",
        "selected_voice": "Туркменский мужской — чистый",
        "rules": [],
        "actors": [
            asdict(SpeakerProfile(id="actor_1", role="Актёр 1", gender="male", suggested_voice="Туркменский мужской — чистый", dominant_emotion="Нейтрально")),
            asdict(SpeakerProfile(id="actor_2", role="Актёр 2", gender="female", suggested_voice="Туркменский женский — чистый", dominant_emotion="Добрый тон")),
        ],
        "analysis": asdict(EmotionProfile()),
        "voice_profile": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ---------------------------------------------------------------------------
# Backend-stubs (preview-safe). Реальные реализации живут на VPS.
# ---------------------------------------------------------------------------
def analyze_emotion(text: str) -> EmotionProfile:
    t = (text or "").lower()
    if any(w in t for w in ["рад", "счаст", "ура", "класс", "отлично", "wonderful", "happy"]):
        return EmotionProfile("Радостно", 84, 1.10, 1.04, 0.86, "короткие", 1.05)
    if any(w in t for w in ["боль", "плохо", "груст", "плак", "одиноко", "sad", "lonely"]):
        return EmotionProfile("Грустно", 82, 0.88, 0.96, 0.42, "длинные", 0.82)
    if any(w in t for w in ["ненавиж", "злой", "сука", "бляд", "бесит", "angry", "hate"]):
        return EmotionProfile("Злой тон", 88, 1.05, 1.06, 0.92, "резкие", 1.15)
    if any(w in t for w in ["важно", "официально", "документ", "суд", "заявление"]):
        return EmotionProfile("Серьёзно", 78, 0.95, 0.98, 0.62, "чёткие", 0.95)
    if any(w in t for w in ["купить", "скидка", "акция", "продажа", "promo"]):
        return EmotionProfile("Рекламный тон", 80, 1.12, 1.04, 0.88, "короткие", 1.08)
    if any(w in t for w in ["спокой", "тих", "calm"]):
        return EmotionProfile("Спокойно", 76, 0.95, 1.0, 0.7, "ровные", 0.92)
    return EmotionProfile()


def apply_rules(text: str) -> str:
    result = text or ""
    for rule in st.session_state.rules:
        src = (rule.get("from") or "").strip()
        dst = (rule.get("to") or "").strip()
        if src and dst:
            result = re.sub(re.escape(src), dst, result, flags=re.I)
    return result


def translate_to_turkmen(
    text: str,
    source_lang: str = "ru",
    glossary: Optional[Dict[str, str]] = None,
    style: str = "natural",
    emotion_profile: Optional[EmotionProfile] = None,
) -> str:
    """Backend-интерфейс под профессиональный туркменский перевод.

    В preview возвращаем понятный mock-перевод + помечаем стиль/эмоцию.
    На VPS подключается NLLB-200 / MADLAD-400 + туркменский glossary.
    """

    if not text or not text.strip():
        return ""
    base = {
        "ru": "Salam. Men bu wideony professional derejede terjime edip, şol bir duýgy bilen seslendirmek isleýärin.",
        "en": "Salam. Men bu wideoyi professional derejede terjime edip, şol bir duýgy bilen seslendirmek isleýärin.",
        "tr": "Salam. Men bu wideoyi hünärmen derejede terjime edip, şol duýgy bilen seslendirmek isleýärin.",
        "tk": text,
    }
    out = base.get(source_lang, f"[{LANGS.get(source_lang, source_lang)} → Туркменский] {text}")
    if glossary:
        for src, dst in glossary.items():
            out = re.sub(re.escape(src), dst, out, flags=re.I)
    return apply_rules(out)


def translate_text(text: str, src: str, dst: str) -> str:
    if not text.strip():
        return ""
    if dst == "tk":
        return translate_to_turkmen(text, source_lang=src)
    if src == "tk" and dst == "ru":
        out = "Здравствуйте. Я хочу профессионально перевести это видео и озвучить его с той же эмоцией."
    elif src == "ru" and dst == "en":
        out = "Hello. I want to professionally translate this video and dub it with the same emotion."
    elif src == "en" and dst == "ru":
        out = "Здравствуйте. Я хочу профессионально перевести это видео и озвучить его с той же эмоцией."
    elif src == "ru" and dst == "tr":
        out = "Merhaba. Bu videoyu profesyonel şekilde çevirip aynı duygu ile seslendirmek istiyorum."
    else:
        out = f"[{LANGS[src]} → {LANGS[dst]}] {text}"
    return apply_rules(out)


def synthesize_turkmen_tts_preview(
    text: str, emotion_profile: EmotionProfile, voice_profile_name: str
) -> Dict[str, Any]:
    """Прокси-вызов настоящего сервиса src/cloud/tts_turkmen.

    В Streamlit Cloud preview сервис вернёт исключение (torch/transformers нет),
    мы перехватываем и показываем понятный mock. На VPS — реальный .wav путь.
    """

    try:
        from src.cloud.tts_turkmen import (  # type: ignore
            TurkmenEmotionProfile,
            TurkmenVoiceProfile,
            get_emotion_preset,
            synthesize_turkmen_tts,
        )
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "path": "", "message": f"Сервис tts_turkmen недоступен: {exc}", "bytes": b""}

    preset = get_emotion_preset(emotion_profile.emotion)
    # Подмешиваем интенсивность из анализа оригинала.
    preset.energy = max(preset.energy, emotion_profile.energy)
    preset.volume = preset.volume * emotion_profile.volume

    vp = TurkmenVoiceProfile(id=voice_profile_name, name=voice_profile_name)
    try:
        path = synthesize_turkmen_tts(text, emotion_profile=preset, voice_profile=vp)
        with open(path, "rb") as f:
            data = f.read()
        return {"ok": True, "path": path, "message": f"Готовая туркменская озвучка: {path}", "bytes": data}
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "path": "",
            "message": (
                "Preview: настоящая туркменская озвучка через MMS-TTS работает на VPS. "
                f"Текст подготовлен ({len(text)} симв.), эмоция={preset.emotion}, "
                f"speed={preset.speed:.2f}, pitch={preset.pitch:.2f}, "
                f"energy={preset.energy:.2f}, volume={preset.volume:.2f}."
            ),
            "bytes": b"",
        }


def detect_speakers(audio_path: Optional[str]) -> List[SpeakerProfile]:
    """Backend-интерфейс под speaker diarization.

    В preview возвращает текущий ручной список из session_state.
    На VPS подключается pyannote.audio + анализ эмоций по сегменту.
    """

    return [SpeakerProfile(**a) for a in st.session_state.actors]


def create_voice_profile(audio_file: Any) -> VoiceProfile:
    if audio_file is None:
        return VoiceProfile(id="custom_voice", name="Мой голос", cleaned=False)
    return VoiceProfile(
        id=f"voice_{uuid.uuid4().hex[:6]}",
        name=getattr(audio_file, "name", "Мой голос"),
        source_path=getattr(audio_file, "name", None),
        cleaned=True,
        style="custom",
    )


def clean_voice(audio_file: Any) -> str:
    if audio_file is None:
        return ""
    return f"cleaned://{getattr(audio_file, 'name', 'voice.wav')}"


def apply_voice_profile(text: str, voice_profile: VoiceProfile, emotion_profile: EmotionProfile) -> bytes:
    # Реальный путь: MMS-TTS -> RVC/OpenVoice с custom voice.
    return b""


def fit_translation_to_timeline(
    segments: List[Dict[str, Any]],
    translated_text: str,
    max_chars_per_line: int = 42,
    max_lines: int = 2,
) -> List[Dict[str, Any]]:
    """Подгонка перевода под тайминг.

    Делит длинный перевод по предложениям, ограничивает длину строки
    `max_chars_per_line`, и распределяет по сегментам пропорционально.
    """

    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", translated_text or "") if s.strip()]
    if not sentences:
        return []
    if not segments:
        segments = [{"start": i * 4.0, "end": (i + 1) * 4.0} for i, _ in enumerate(sentences)]

    out: List[Dict[str, Any]] = []
    n = max(1, len(segments))
    bucket = max(1, len(sentences) // n)
    cursor = 0
    for i, seg in enumerate(segments):
        chunk = sentences[cursor:cursor + bucket] if i < n - 1 else sentences[cursor:]
        cursor += bucket
        joined = " ".join(chunk)
        lines: List[str] = []
        for word in joined.split():
            if not lines or len(lines[-1]) + 1 + len(word) > max_chars_per_line:
                if len(lines) >= max_lines:
                    lines[-1] += "…"
                    break
                lines.append(word)
            else:
                lines[-1] = lines[-1] + " " + word
        out.append({"start": seg["start"], "end": seg["end"], "text": "\n".join(lines)})
    return out


# ---------------------------------------------------------------------------
# Утилиты экспорта.
# ---------------------------------------------------------------------------
def srt(text: str) -> str:
    parts = [p.strip() for p in re.split(r"[.!?\n]+", text or "") if p.strip()] or ["Murat AI"]
    rows, sec = [], 0
    for i, part in enumerate(parts, 1):
        rows.append(f"{i}\n00:00:{sec:02d},000 --> 00:00:{sec + 4:02d},000\n{part}\n")
        sec += 4
    return "\n".join(rows)


def vtt(text: str) -> str:
    return "WEBVTT\n\n" + srt(text).replace(",000", ".000")


def project_json() -> bytes:
    payload = {
        "build": BUILD,
        "tts_backend_turkmen": TURKMEN_TTS_BACKEND,
        "selected_voice": st.session_state.selected_voice,
        "actors": st.session_state.actors,
        "rules": st.session_state.rules,
        "analysis": st.session_state.analysis,
        "result_text": st.session_state.result_text,
        "created_at": datetime.utcnow().isoformat(),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


# ---------------------------------------------------------------------------
# UI-хелперы.
# ---------------------------------------------------------------------------
def get_video_aspect(fmt: Dict[str, str]) -> str:
    return fmt["ratio"]


def get_device_frame(screen: Dict[str, Any]):
    return screen["kind"], int(screen["max"])


def device_frame_open(fmt: Dict[str, str], screen: Dict[str, Any]) -> None:
    kind, max_w = get_device_frame(screen)
    aspect = get_video_aspect(fmt)
    st.markdown(
        f"<div class='device device-{kind}' style='max-width:{max_w}px'>"
        f"<div class='device-screen' style='aspect-ratio:{aspect}'>",
        unsafe_allow_html=True,
    )


def device_frame_close() -> None:
    st.markdown("</div></div>", unsafe_allow_html=True)


def device_frame_empty(label: str, fmt: Dict[str, str], screen: Dict[str, Any]) -> None:
    st.markdown(
        f"<div class='device-empty'>{label}<br>"
        f"<span>{fmt['label']} · {screen['label']}</span></div>",
        unsafe_allow_html=True,
    )


def render_speak_button(
    text: str,
    lang: str,
    voice_name: str,
    emotion: str,
    speed: float,
    pitch: float,
    volume: float,
    key: str,
) -> None:
    """Браузерный TTS preview через speechSynthesis.

    Туркменский в браузере не поддерживается нативно — фолбэк на tr-TR
    (это слышно как «робот»). Настоящее качество — на VPS через MMS-TTS;
    кнопка «Сгенерировать туркменскую озвучку» вызывает src/cloud/tts_turkmen.
    """

    browser_lang = {"ru": "ru-RU", "tk": "tr-TR", "tr": "tr-TR", "en": "en-US"}.get(lang, "ru-RU")
    # Узкий диапазон — чтобы не звучало роботизированно.
    final_speed = max(0.85, min(1.15, speed))
    final_pitch = max(0.92, min(1.10, pitch))
    final_volume = max(0.3, min(1.0, volume))

    sample = text or SAMPLES.get(lang, SAMPLES["ru"])
    sample_json = json.dumps(sample)
    components.html(
        f"""
        <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
          <button id="play_{key}" style="background:#7c3aed;color:white;border:0;border-radius:12px;padding:10px 18px;font-weight:800;cursor:pointer">▶ Прослушать</button>
          <button id="stop_{key}" style="background:#263244;color:white;border:1px solid #475569;border-radius:12px;padding:10px 18px;font-weight:800;cursor:pointer">■ Стоп</button>
        </div>
        <div style="color:#94a3b8;font-size:12px;margin-top:6px">
          {voice_name} · {emotion} · темп {final_speed:.2f} · высота {final_pitch:.2f}
        </div>
        <script>
        document.getElementById('play_{key}').onclick = () => {{
            speechSynthesis.cancel();
            const u = new SpeechSynthesisUtterance({sample_json});
            u.lang = '{browser_lang}';
            u.rate = {final_speed};
            u.pitch = {final_pitch};
            u.volume = {final_volume};
            speechSynthesis.speak(u);
        }};
        document.getElementById('stop_{key}').onclick = () => speechSynthesis.cancel();
        </script>
        """,
        height=80,
    )


# ---------------------------------------------------------------------------
# Запуск.
# ---------------------------------------------------------------------------
init_state()


# === CSS / шапка =============================================================
st.markdown(
    f"""
    <style>
    #MainMenu, footer {{visibility:hidden}}
    .block-container {{max-width:1520px;padding-top:1rem;padding-bottom:5rem}}

    .build {{
        background:#052e2b;color:#99f6e4;border:1px solid #0f766e;
        border-radius:14px;padding:10px 14px;font-weight:900;margin-bottom:12px;
        font-family:ui-monospace,monospace;font-size:13px;letter-spacing:.4px
    }}

    .hero {{
        border-radius:30px;padding:24px 30px;
        background:linear-gradient(135deg,#12172a,#24124d 55%,#073042);
        border:1px solid rgba(255,255,255,.12);margin-bottom:18px
    }}
    .hero h1 {{font-size:40px;margin:0;color:#fff;letter-spacing:.3px}}
    .hero p  {{color:#dbeafe;font-size:17px;margin:8px 0 0}}

    .card {{
        border-radius:24px;background:rgba(255,255,255,.045);
        border:1px solid rgba(255,255,255,.12);padding:18px;margin-bottom:16px;
        box-shadow:0 18px 46px rgba(0,0,0,.18);height:100%;
        display:flex;flex-direction:column
    }}
    .card h2 {{margin:0 0 14px;font-size:22px;color:#fff;font-weight:900}}

    .pill {{
        display:inline-block;border-radius:999px;padding:6px 11px;margin:0 6px 6px 0;
        background:#1e293b;color:#cbd5e1;border:1px solid #334155;font-size:12px;font-weight:800
    }}
    .pill.ok {{background:#052e2b;color:#5eead4;border-color:#0f766e}}

    .stButton>button, .stDownloadButton>button {{
        border-radius:12px!important;font-weight:800!important
    }}

    /* === Studio pair (две карточки + стрелка) ============================ */
    .studio-row [data-testid="stHorizontalBlock"] {{align-items:stretch}}
    .studio-row [data-testid="column"] > div {{height:100%}}
    .arrow-col {{
        display:flex;align-items:center;justify-content:center;height:100%;
        color:#a78bfa;font-size:54px;font-weight:900;line-height:1;
        text-shadow:0 4px 12px rgba(124,58,237,.5)
    }}

    /* === Device frames ==================================================== */
    .device {{width:100%;margin:0 auto 14px;position:relative}}
    .device-screen {{
        width:100%;background:#000;overflow:hidden;
        display:flex;align-items:center;justify-content:center;
        position:relative
    }}
    .device-screen video, .device-screen img {{
        max-width:100%;max-height:100%;object-fit:contain
    }}
    .device-empty {{
        color:#dbeafe;font-size:15px;font-weight:900;text-align:center;padding:18px;line-height:1.4
    }}
    .device-empty span {{color:#a78bfa;font-weight:700;font-size:12px;display:block;margin-top:6px}}

    .device-phone-v  .device-screen {{border:10px solid #111;border-radius:34px;background:linear-gradient(180deg,#111827,#1e1b4b);box-shadow:0 18px 50px rgba(0,0,0,.45)}}
    .device-phone-v::before {{content:"";position:absolute;top:6px;left:50%;transform:translateX(-50%);width:90px;height:18px;background:#000;border-radius:0 0 14px 14px;z-index:5}}

    .device-phone-h  .device-screen {{border:10px solid #111;border-radius:24px;background:linear-gradient(180deg,#111827,#1e1b4b);box-shadow:0 18px 50px rgba(0,0,0,.45)}}
    .device-phone-h::before {{content:"";position:absolute;left:6px;top:50%;transform:translateY(-50%);width:18px;height:90px;background:#000;border-radius:14px 0 0 14px;z-index:5}}

    .device-tablet   .device-screen {{border:14px solid #1a1a1a;border-radius:22px;background:linear-gradient(180deg,#111827,#1e1b4b);box-shadow:0 18px 50px rgba(0,0,0,.45)}}

    .device-laptop   .device-screen {{border:9px solid #2b2b2b;border-top-width:22px;border-radius:14px 14px 4px 4px;background:linear-gradient(180deg,#111827,#1e1b4b);box-shadow:0 18px 50px rgba(0,0,0,.45)}}
    .device-laptop::after {{content:"";display:block;width:100%;height:14px;background:linear-gradient(180deg,#3a3a3a,#1a1a1a);border-radius:0 0 18px 18px;margin-top:-2px;box-shadow:0 10px 24px rgba(0,0,0,.35)}}

    .device-monitor  .device-screen {{border:12px solid #1a1a1a;border-radius:10px;background:linear-gradient(180deg,#111827,#1e1b4b);box-shadow:0 18px 50px rgba(0,0,0,.45)}}
    .device-monitor::after {{content:"";display:block;width:32%;height:18px;margin:6px auto 0;background:linear-gradient(180deg,#2b2b2b,#111);border-radius:0 0 10px 10px}}

    .device-tv       .device-screen {{border:18px solid #050505;border-radius:14px;background:linear-gradient(180deg,#0b1220,#1e1b4b);box-shadow:0 22px 60px rgba(0,0,0,.55)}}
    .device-tv::after {{content:"";display:block;width:24%;height:8px;margin:8px auto 0;background:#222;border-radius:6px}}

    .device-bare     .device-screen {{border-radius:14px;background:#000;box-shadow:0 12px 32px rgba(0,0,0,.35)}}
    </style>
    <div class="build">BUILD: {BUILD}</div>
    <div class="hero">
        <h1>🎬 Murat AI Studio</h1>
        <p>Профессиональная студия: видео → перевод → озвучка → готовый MP4. Слева вход, справа результат.</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# === Настройки проекта ========================================================
st.markdown("<div class='card'><h2>⚙️ Настройки проекта</h2>", unsafe_allow_html=True)

r0 = st.columns(2)
fmt_name = r0[0].selectbox(
    "🎬 ФОРМАТ ВИДЕО (соотношение сторон)",
    list(FORMATS.keys()),
    key="ui_fmt",
    help="Это форма самого видео внутри рамки. Не путать с экраном просмотра.",
)
screen_name = r0[1].selectbox(
    "🖥 ЭКРАН ПРОСМОТРА (устройство-рамка)",
    list(SCREENS.keys()),
    index=4,
    key="ui_screen",
    help="Это только рамка, внутри которой смотрим preview. Размер видео не растягивается.",
)

r1 = st.columns(5)
quality = r1[0].selectbox("Качество MP4", QUALITIES, index=1, key="ui_quality")
src_lang = r1[1].selectbox("С языка", list(LANGS.keys()), format_func=lambda c: LANGS[c], key="ui_src")
dst_lang = r1[2].selectbox("На язык", list(LANGS.keys()), index=1, format_func=lambda c: LANGS[c], key="ui_dst")
selected_voice = r1[3].selectbox(
    "Голосовой профиль",
    VOICE_NAMES,
    index=VOICE_NAMES.index(st.session_state.selected_voice) if st.session_state.selected_voice in VOICE_NAMES else 0,
    key="ui_voice",
)
st.session_state.selected_voice = selected_voice
emotion_mode = r1[4].selectbox("Эмоция", EMOTIONS, key="ui_emotion")

r2 = st.columns(6)
speed = r2[0].slider("Темп", 0.6, 1.6, 1.0, 0.05, key="ui_speed")
pitch = r2[1].slider("Высота", 0.6, 1.6, 1.0, 0.05, key="ui_pitch")
volume = r2[2].slider("Громкость", 0.1, 1.0, 1.0, 0.05, key="ui_volume")
r2[3].checkbox("Подогнать под тайминг", True, key="ui_fit_timing")
r2[4].checkbox("Очистить шум / эхо", True, key="ui_clean_noise")
r2[5].checkbox("Сохранить качество", True, key="ui_keep_quality")

fmt = FORMATS[fmt_name]
screen = SCREENS[screen_name]
st.markdown(
    f"<span class='pill ok'>Формат видео: {fmt['label']}</span>"
    f"<span class='pill ok'>Экран просмотра: {screen['label']}</span>"
    f"<span class='pill'>Качество: {quality}</span>"
    f"<span class='pill'>{LANGS[src_lang]} → {LANGS[dst_lang]}</span>",
    unsafe_allow_html=True,
)
st.markdown("</div>", unsafe_allow_html=True)

active_emotion = (
    st.session_state.analysis["emotion"]
    if emotion_mode == "Автоматически по оригиналу"
    else emotion_mode
)


# === Studio row: Исходное видео → стрелка → Готовое видео ====================
st.markdown("<div class='studio-row'>", unsafe_allow_html=True)
left, arrow, right = st.columns([10, 1.4, 10], gap="small")

# --- Левая карточка: Исходное видео --------------------------------------
with left:
    st.markdown("<div class='card'><h2>📥 Исходное видео</h2>", unsafe_allow_html=True)

    device_frame_open(fmt, screen)
    if st.session_state.video_file:
        st.video(st.session_state.video_file)
    elif st.session_state.video_url:
        st.video(st.session_state.video_url)
    else:
        device_frame_empty("Здесь появится исходное видео", fmt, screen)
    device_frame_close()

    new_url = st.text_input(
        "Вставить ссылку на видео",
        value=st.session_state.video_url,
        placeholder="YouTube / Shorts / прямая mp4-ссылка",
        key="ui_video_url_input",
    )
    if new_url != st.session_state.video_url:
        st.session_state.video_url = new_url

    c1, c2 = st.columns(2)
    if c1.button("Показать по ссылке", type="primary", use_container_width=True, key="btn_show_url"):
        st.session_state.video_file = None
        st.session_state.result_ready = False
        st.rerun()
    c2.button(
        "Скачать видео по ссылке",
        disabled=True,
        use_container_width=True,
        key="btn_download_url",
        help="Бэкенд yt-dlp работает на VPS. В Streamlit Cloud preview скачивание выключено.",
    )

    up = st.file_uploader(
        "Загрузить видео из папки",
        type=["mp4", "mov", "webm", "mkv", "m4v"],
        key="ui_video_uploader",
    )
    if up is not None:
        st.session_state.video_file = up
        st.session_state.video_url = ""
        st.session_state.result_ready = False
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

# --- Средняя колонка: стрелка --------------------------------------------
with arrow:
    st.markdown("<div class='arrow-col'>→</div>", unsafe_allow_html=True)

# --- Правая карточка: Готовое видео --------------------------------------
with right:
    st.markdown("<div class='card'><h2>📤 Готовое видео</h2>", unsafe_allow_html=True)

    device_frame_open(fmt, screen)
    if st.session_state.result_ready and st.session_state.video_file:
        st.video(st.session_state.video_file)
    elif st.session_state.result_ready and st.session_state.video_url:
        st.video(st.session_state.video_url)
    else:
        device_frame_empty("Здесь появится готовое видео", fmt, screen)
    device_frame_close()

    if st.button("✨ Создать готовое видео", type="primary", use_container_width=True, key="btn_make_video"):
        st.session_state.analysis = asdict(analyze_emotion(st.session_state.source_text))
        st.session_state.result_text = translate_text(st.session_state.source_text, src_lang, dst_lang)
        st.session_state.result_ready = True
        st.rerun()

    st.markdown(
        f"<span class='pill ok'>{fmt['label']}</span>"
        f"<span class='pill'>{screen['label']}</span>"
        f"<span class='pill'>{quality}</span>"
        f"<span class='pill'>{LANGS[dst_lang]}</span>"
        f"<span class='pill'>{selected_voice}</span>"
        f"<span class='pill'>{active_emotion}</span>",
        unsafe_allow_html=True,
    )

    d1, d2 = st.columns(2)
    d1.download_button(
        "Скачать MP4",
        data=b"MP4 preview placeholder",
        file_name="murat-ai-final.mp4",
        disabled=not st.session_state.result_ready,
        use_container_width=True,
        key="dl_mp4",
    )
    d2.download_button(
        "MP4 + SRT",
        data=srt(st.session_state.result_text).encode(),
        file_name="murat-ai-final-with-srt.txt",
        disabled=not st.session_state.result_ready,
        use_container_width=True,
        key="dl_mp4_srt",
    )
    d1.download_button(
        "Скачать WAV",
        data=b"WAV preview placeholder",
        file_name="murat-ai-audio.wav",
        disabled=not st.session_state.result_ready,
        use_container_width=True,
        key="dl_wav_top",
    )
    d2.download_button(
        "ZIP / JSON",
        data=project_json(),
        file_name="murat-ai-package.json",
        disabled=not st.session_state.result_ready,
        use_container_width=True,
        key="dl_zip",
    )

    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)  # /studio-row


# === Голос: загрузка + готовая туркменская озвучка ===========================
left, right = st.columns(2, gap="large")
with left:
    st.markdown("<div class='card'><h2>🎤 Мой голос (клон)</h2>", unsafe_allow_html=True)
    voice_file = st.file_uploader(
        "Загрузить аудио голоса (30–60 сек.)",
        type=["wav", "mp3", "m4a", "flac", "ogg"],
        key="ui_voice_uploader",
    )
    if voice_file is not None:
        st.session_state.voice_file = voice_file
        st.session_state.voice_profile = asdict(create_voice_profile(voice_file))
        st.audio(voice_file)
    elif st.session_state.voice_file:
        st.audio(st.session_state.voice_file)

    cc = st.columns(4)
    cc[0].checkbox("Очистить шум", True, key="ui_vc_noise")
    cc[1].checkbox("Удалить эхо", True, key="ui_vc_echo")
    cc[2].checkbox("Выровнять громкость", True, key="ui_vc_norm")
    cc[3].checkbox("Чистый голос", True, key="ui_vc_clean")

    if st.button("Создать голосовой профиль", use_container_width=True, key="btn_make_voice_profile"):
        st.session_state.voice_profile = asdict(create_voice_profile(st.session_state.voice_file))
        st.success("Профиль голоса создан. Он будет использован при озвучке.")

    if st.session_state.voice_profile:
        vp = st.session_state.voice_profile
        st.markdown(
            f"<span class='pill ok'>{vp['name']}</span>"
            f"<span class='pill'>{'очищен' if vp['cleaned'] else 'оригинал'}</span>"
            f"<span class='pill'>{vp['style']}</span>",
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)

with right:
    st.markdown("<div class='card'><h2>🔊 Туркменская озвучка</h2>", unsafe_allow_html=True)

    if st.button("Сгенерировать туркменскую озвучку (MMS-TTS)", type="primary", use_container_width=True, key="btn_tts_run"):
        analysis_dict = st.session_state.analysis
        ep = EmotionProfile(**analysis_dict) if isinstance(analysis_dict, dict) else EmotionProfile()
        if emotion_mode != "Автоматически по оригиналу":
            ep.emotion = emotion_mode
        text_for_tts = st.session_state.result_text or translate_text(st.session_state.source_text, src_lang, "tk")
        result = synthesize_turkmen_tts_preview(text_for_tts, ep, selected_voice)
        st.session_state.tts_audio_bytes = result["bytes"]
        st.session_state.tts_audio_message = result["message"]
        if result["ok"]:
            st.session_state.result_text = text_for_tts
            st.success(result["message"])
        else:
            st.info(result["message"])

    if st.session_state.tts_audio_bytes:
        st.audio(st.session_state.tts_audio_bytes)
    elif st.session_state.tts_audio_message:
        st.caption(st.session_state.tts_audio_message)

    # Browser preview button (НЕ продакшен, но даёт быстро услышать tone/emotion).
    render_speak_button(
        st.session_state.result_text or st.session_state.source_text,
        "tk" if dst_lang == "tk" else dst_lang,
        selected_voice,
        active_emotion,
        speed, pitch, volume,
        key="main_tts_preview",
    )

    st.caption(
        f"Бэкенд туркменского TTS: `{TURKMEN_TTS_BACKEND}`. "
        "На VPS озвучка реальная — модель MMS-TTS + post-processing по эмоции. "
        "В Streamlit Cloud preview играет браузерный голос (fallback tr-TR)."
    )

    d3, d4 = st.columns(2)
    d3.download_button(
        "Скачать WAV",
        data=st.session_state.tts_audio_bytes or b"WAV preview placeholder",
        file_name="voiceover-tk.wav",
        use_container_width=True,
        key="dl_wav_voice",
    )
    d4.download_button(
        "Скачать MP3",
        data=b"MP3 preview placeholder",
        file_name="voiceover-tk.mp3",
        use_container_width=True,
        key="dl_mp3_voice",
    )

    st.markdown("</div>", unsafe_allow_html=True)


# === Текст / сценарий / субтитры =============================================
left, right = st.columns(2, gap="large")
with left:
    st.markdown("<div class='card'><h2>📝 Текст / сценарий</h2>", unsafe_allow_html=True)
    new_src_text = st.text_area(
        "Исходный текст",
        value=st.session_state.source_text,
        height=220,
        label_visibility="collapsed",
        key="ui_source_text",
    )
    if new_src_text != st.session_state.source_text:
        st.session_state.source_text = new_src_text

    b1, b2, b3 = st.columns(3)
    if b1.button("Перевести", type="primary", use_container_width=True, key="btn_translate"):
        st.session_state.analysis = asdict(analyze_emotion(st.session_state.source_text))
        st.session_state.result_text = translate_text(st.session_state.source_text, src_lang, dst_lang)
        st.rerun()
    if b2.button("Озвучить", use_container_width=True, key="btn_voice"):
        st.session_state.analysis = asdict(analyze_emotion(st.session_state.source_text))
        if not st.session_state.result_text:
            st.session_state.result_text = translate_text(st.session_state.source_text, src_lang, dst_lang)
        st.rerun()
    if b3.button("Текст → видео", use_container_width=True, key="btn_text_to_video"):
        st.session_state.analysis = asdict(analyze_emotion(st.session_state.source_text))
        st.session_state.result_text = translate_text(st.session_state.source_text, src_lang, dst_lang)
        st.session_state.result_ready = True
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

with right:
    st.markdown("<div class='card'><h2>✅ Готовый перевод / субтитры</h2>", unsafe_allow_html=True)
    new_result_text = st.text_area(
        "Готовый текст",
        value=st.session_state.result_text,
        height=220,
        label_visibility="collapsed",
        key="ui_result_text",
    )
    if new_result_text != st.session_state.result_text:
        st.session_state.result_text = new_result_text

    t1, t2, t3 = st.columns(3)
    t1.download_button(
        "Скачать TXT",
        data=(st.session_state.result_text or "").encode(),
        file_name="murat-ai.txt",
        use_container_width=True,
        key="dl_txt",
    )
    t2.download_button(
        "Скачать SRT",
        data=srt(st.session_state.result_text).encode(),
        file_name="murat-ai.srt",
        use_container_width=True,
        key="dl_srt",
    )
    t3.download_button(
        "Скачать VTT",
        data=vtt(st.session_state.result_text).encode(),
        file_name="murat-ai.vtt",
        use_container_width=True,
        key="dl_vtt",
    )

    st.markdown("</div>", unsafe_allow_html=True)


# === Анализ оригинала ========================================================
st.markdown("<div class='card'><h2>🧠 Анализ оригинала (эмоция автоопределена)</h2>", unsafe_allow_html=True)
a = st.session_state.analysis
st.markdown(
    f"<span class='pill ok'>Эмоция: {a['emotion']}</span>"
    f"<span class='pill'>Уверенность: {a['confidence']}%</span>"
    f"<span class='pill'>Темп: {a['speed']}</span>"
    f"<span class='pill'>Высота: {a['pitch']}</span>"
    f"<span class='pill'>Энергия: {a['energy']}</span>"
    f"<span class='pill'>Громкость: {a['volume']}</span>"
    f"<span class='pill'>Паузы: {a['pauses']}</span>",
    unsafe_allow_html=True,
)
st.caption(
    "Если эмоция выбрана «Автоматически по оригиналу», эти значения автоматически "
    "пробрасываются в туркменскую озвучку (speed/pitch/energy/pause/volume)."
)
st.markdown("</div>", unsafe_allow_html=True)


# === Актёры и голоса =========================================================
st.markdown("<div class='card'><h2>🎭 Актёры и голоса</h2>", unsafe_allow_html=True)
count = st.number_input(
    "Сколько голосов / актёров в видео",
    min_value=1, max_value=12,
    value=len(st.session_state.actors),
    key="ui_actor_count",
)
while len(st.session_state.actors) < count:
    n = len(st.session_state.actors) + 1
    st.session_state.actors.append(
        asdict(SpeakerProfile(id=f"actor_{n}", role=f"Актёр {n}", suggested_voice="Туркменский мужской — чистый"))
    )
st.session_state.actors = st.session_state.actors[:count]

for i, actor in enumerate(st.session_state.actors):
    cols = st.columns([1.1, 1.8, 1.4, 1.4, 1.3])
    actor["role"] = cols[0].text_input("Роль", value=actor["role"], key=f"act_role_{i}")
    actor["suggested_voice"] = cols[1].selectbox(
        "Туркменский голос",
        VOICE_NAMES,
        index=VOICE_NAMES.index(actor["suggested_voice"]) if actor["suggested_voice"] in VOICE_NAMES else 0,
        key=f"act_voice_{i}",
    )
    actor["dominant_emotion"] = cols[2].selectbox(
        "Эмоция актёра",
        EMOTIONS[1:],
        index=EMOTIONS[1:].index(actor["dominant_emotion"]) if actor["dominant_emotion"] in EMOTIONS[1:] else 0,
        key=f"act_em_{i}",
    )
    actor["replace_mode"] = cols[3].selectbox(
        "Замена",
        ["Не заменять", "Мой загруженный голос", "Загрузить отдельный", "Выбрать из каталога"],
        index=["Не заменять", "Мой загруженный голос", "Загрузить отдельный", "Выбрать из каталога"].index(actor["replace_mode"])
        if actor["replace_mode"] in ["Не заменять", "Мой загруженный голос", "Загрузить отдельный", "Выбрать из каталога"] else 0,
        key=f"act_rep_{i}",
    )
    with cols[4]:
        render_speak_button(
            f"Это пример голоса для роли {actor['role']}.",
            "tk",
            actor["suggested_voice"],
            actor["dominant_emotion"],
            speed, pitch, volume,
            key=f"act_preview_{i}",
        )
    if actor["replace_mode"] == "Загрузить отдельный":
        st.file_uploader(
            f"Голос для роли «{actor['role']}»",
            type=["wav", "mp3", "m4a", "flac", "ogg"],
            key=f"act_file_{i}",
        )
st.session_state.actors = st.session_state.actors  # keep mutated list
st.markdown("</div>", unsafe_allow_html=True)


# === Каталог голосов =========================================================
st.markdown("<div class='card'><h2>🎙️ Каталог голосов</h2>", unsafe_allow_html=True)
for i, v in enumerate(VOICE_CATALOG):
    c1, c2 = st.columns([2, 1])
    c1.markdown(
        f"<b>{v['name']}</b><br>"
        f"<span style='color:#94a3b8'>{v['lang'].upper()} · {v['gender']} · {v['age']} · {v['style']}</span><br>"
        f"<span class='pill'>{', '.join(v['best_for'][:3])}</span>",
        unsafe_allow_html=True,
    )
    with c2:
        render_speak_button(
            f"Это пример голоса {v['name']}.",
            v["lang"] if v["lang"] in LANGS else "tk",
            v["name"],
            active_emotion,
            speed, pitch, volume,
            key=f"cat_voice_{i}",
        )
st.markdown("</div>", unsafe_allow_html=True)


# === Замена слов =============================================================
st.markdown("<div class='card'><h2>📚 Замена слов</h2>", unsafe_allow_html=True)
r = st.columns([1.4, 1.4, 1.2, 1])
old_word = r[0].text_input("Старое слово", key="ui_rule_old")
new_word = r[1].text_input("Новое слово", key="ui_rule_new")
scope = r[2].selectbox("Область", ["Глобально", "Только проект", "Только канал"], key="ui_rule_scope")
if r[3].button("Сохранить", type="primary", use_container_width=True, key="btn_save_rule") and old_word and new_word:
    st.session_state.rules.append({"from": old_word, "to": new_word, "scope": scope})
    st.session_state.result_text = apply_rules(st.session_state.result_text)
    st.rerun()
if st.session_state.rules:
    st.dataframe(st.session_state.rules, use_container_width=True, hide_index=True)
st.download_button(
    "Скачать настройки проекта JSON",
    data=project_json(),
    file_name="murat-ai-project.json",
    use_container_width=True,
    key="dl_project_json",
)
st.markdown("</div>", unsafe_allow_html=True)

st.caption(
    f"Настоящий MP4 1080p/4K/8K, клонирование голоса и модель {TURKMEN_TTS_BACKEND} "
    "работают на VPS/GPU backend. Streamlit Cloud preview показывает интерфейс и логику."
)
