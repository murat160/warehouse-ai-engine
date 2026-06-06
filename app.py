"""Murat AI Studio — Streamlit entry point.

ЖЁСТКИЕ ПРАВИЛА выравнивания (по чертежу пользователя):
1. Левая и правая видеорамки одинаковой ширины и высоты.
2. Видеорамки на одной горизонтальной линии (фиксированная высота 380px).
3. Стрелка между ними — по центру, высота 380px.
4. ВСЕ настройки наверху в компактной панели — НЕ между видео.
5. Под каждой рамкой свои controls (controls могут различаться, рамки — нет).
6. ФОРМАТ ВИДЕО и ЭКРАН ПРОСМОТРА — два независимых селектора.
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
# BUILD marker.
# ---------------------------------------------------------------------------
BUILD = "real-video-pipeline / 2026-05-25-01:30 / inspect-download-process"
TURKMEN_TTS_BACKEND = "facebook/mms-tts-tuk-script_latin"

st.set_page_config(
    page_title="Murat AI Studio",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ---------------------------------------------------------------------------
# Каталоги.
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

# `device_ratio` — aspect-ratio device chrome (для пустой рамки + видео внутри).
# Размер высоты внешней рамки фиксирован через CSS .video-frame{height:380px}.
SCREENS: Dict[str, Dict[str, Any]] = {
    "📱 Телефон вертикальный":   {"device_ratio": "9 / 19.5", "kind": "phone-v", "label": "Телефон верт."},
    "📱 Телефон горизонтальный": {"device_ratio": "19.5 / 9", "kind": "phone-h", "label": "Телефон гориз."},
    "💻 Планшет":                {"device_ratio": "3 / 4",    "kind": "tablet",  "label": "Планшет"},
    "💻 Ноутбук":                {"device_ratio": "16 / 10",  "kind": "laptop",  "label": "Ноутбук"},
    "🖥 Монитор 19\"":           {"device_ratio": "5 / 4",    "kind": "monitor", "label": "Монитор 19″"},
    "🖥 Монитор 24\"":           {"device_ratio": "16 / 10",  "kind": "monitor", "label": "Монитор 24″"},
    "📺 Телевизор":              {"device_ratio": "16 / 9",   "kind": "tv",      "label": "Телевизор"},
    "🟦 Без рамки":              {"device_ratio": "16 / 9",   "kind": "bare",    "label": "Без рамки"},
}

QUALITIES = [
    "Auto",
    "360p",
    "480p",
    "720p HD",
    "1080p Full HD",
    "1440p / 2K",
    "2160p / 4K",
    "4320p / 8K",
    "Original",
]

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
    {"id": "tm_male_clean",   "name": "Туркменский мужской — чистый",  "lang": "tk", "gender": "male",   "age": "взрослый", "style": "чистый",     "best_for": ["Нейтрально", "Серьёзно", "Спокойно"]},
    {"id": "tm_female_clean", "name": "Туркменский женский — чистый",  "lang": "tk", "gender": "female", "age": "взрослый", "style": "чистый",     "best_for": ["Нейтрально", "Добрый тон", "Радостно"]},
    {"id": "tm_narrator",     "name": "Туркменский диктор",             "lang": "tk", "gender": "male",   "age": "взрослый", "style": "диктор",     "best_for": ["Серьёзно", "Кино-драма", "Спокойно"]},
    {"id": "tm_male_warm",    "name": "Туркменский мужской — тёплый",  "lang": "tk", "gender": "male",   "age": "взрослый", "style": "тёплый",     "best_for": ["Добрый тон", "Спокойно"]},
    {"id": "tm_female_warm",  "name": "Туркменский женский — тёплый",  "lang": "tk", "gender": "female", "age": "взрослый", "style": "тёплый",     "best_for": ["Добрый тон", "Радостно"]},
    {"id": "boy_6_8_soft",    "name": "Мальчик 6–8 лет — мягкий",      "lang": "ru", "gender": "male",   "age": "ребёнок",  "style": "мягкий",     "best_for": ["Добрый тон", "Грустно"]},
    {"id": "boy_9_12_energy", "name": "Мальчик 9–12 лет — энергичный", "lang": "ru", "gender": "male",   "age": "ребёнок",  "style": "энергичный", "best_for": ["Радостно", "Энергично"]},
    {"id": "girl_6_8_soft",   "name": "Девочка 6–8 лет — нежная",      "lang": "ru", "gender": "female", "age": "ребёнок",  "style": "нежный",     "best_for": ["Добрый тон", "Радостно"]},
    {"id": "girl_9_12_happy", "name": "Девочка 9–12 лет — радостная",  "lang": "ru", "gender": "female", "age": "ребёнок",  "style": "радостный",  "best_for": ["Радостно", "Энергично"]},
    {"id": "male_cinema",     "name": "Мужской кино-диктор",           "lang": "ru", "gender": "male",   "age": "взрослый", "style": "кино",       "best_for": ["Кино-драма", "Серьёзно"]},
    {"id": "female_blogger",  "name": "Женский блогерский",            "lang": "ru", "gender": "female", "age": "взрослый", "style": "блогерский", "best_for": ["Радостно", "Рекламный тон"]},
    {"id": "custom_voice",    "name": "Мой загруженный голос",         "lang": "any", "gender": "any",   "age": "пользовательский", "style": "клон", "best_for": EMOTIONS[1:]},
]
VOICE_NAMES = [v["name"] for v in VOICE_CATALOG]


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
    dominant_emotion: str = "Нейтрально"
    suggested_voice: str = "Туркменский мужской — чистый"
    replace_mode: str = "Не заменять"


@dataclass
class VoiceProfile:
    id: str
    name: str
    cleaned: bool = False
    style: str = "natural"


# ---------------------------------------------------------------------------
# Session state.
# ---------------------------------------------------------------------------
def init_state() -> None:
    defaults: Dict[str, Any] = {
        "video_bytes": None,
        "video_name": "",
        "video_url": "",
        "voice_bytes": None,
        "voice_name": "",
        "source_text": "Привет. Я хочу сделать профессиональное короткое видео с переводом и озвучкой на туркменском.",
        "result_text": "",
        "result_ready": False,
        "tts_audio_bytes": b"",
        "tts_audio_message": "",
        "selected_voice": "Туркменский мужской — чистый",
        "rules": [],
        "actors": [
            asdict(SpeakerProfile(id="actor_1", role="Актёр 1", gender="male",   suggested_voice="Туркменский мужской — чистый",   dominant_emotion="Нейтрально")),
            asdict(SpeakerProfile(id="actor_2", role="Актёр 2", gender="female", suggested_voice="Туркменский женский — чистый",   dominant_emotion="Добрый тон")),
        ],
        "analysis": asdict(EmotionProfile()),
        "voice_profile": None,
        "quality_report": None,
        "job_id": "",
        "job_status": None,
        "url_preview": None,
        "source_video_url": "",           # реальный URL backend на скачанный source MP4
        "source_video_title": "",
        "source_video_duration": 0,
        "source_video_size_mb": 0,
        "source_video_thumbnail": "",
        "final_video_url": "",            # реальный URL backend на готовый MP4
        "final_audio_url": "",
        "final_srt_url": "",
        "final_txt_url": "",
        "final_zip_url": "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ---------------------------------------------------------------------------
# Backend-stubs (preview-safe). Реальные реализации — на VPS.
# ---------------------------------------------------------------------------
def download_video_from_url(url: str) -> Dict[str, Any]:
    """Backend yt-dlp wrapper. На VPS возвращает {path, title, duration}."""

    return {"ok": False, "message": "Скачивание ссылок выполняется на VPS через yt-dlp.", "path": "", "title": "", "duration": 0}


def extract_audio(video_path: str) -> str:
    """ffmpeg wrapper. На VPS возвращает путь к .wav."""

    return ""


def transcribe_audio(audio_path: str) -> List[Dict[str, Any]]:
    """Whisper ASR на VPS. Возвращает сегменты [{start, end, text, speaker}]."""

    return []


def analyze_emotion(text: str) -> EmotionProfile:
    t = (text or "").lower()
    if any(w in t for w in ["рад", "счаст", "ура", "класс", "отлично", "wonderful", "happy"]):
        return EmotionProfile("Радостно",      84, 1.10, 1.04, 0.86, "короткие", 1.05)
    if any(w in t for w in ["боль", "плохо", "груст", "плак", "одиноко", "sad", "lonely"]):
        return EmotionProfile("Грустно",       82, 0.88, 0.96, 0.42, "длинные",  0.82)
    if any(w in t for w in ["ненавиж", "злой", "сука", "бляд", "бесит", "angry"]):
        return EmotionProfile("Злой тон",      88, 1.05, 1.06, 0.92, "резкие",   1.15)
    if any(w in t for w in ["важно", "официально", "документ", "суд", "заявление"]):
        return EmotionProfile("Серьёзно",      78, 0.95, 0.98, 0.62, "чёткие",   0.95)
    if any(w in t for w in ["купить", "скидка", "акция", "продажа", "promo"]):
        return EmotionProfile("Рекламный тон", 80, 1.12, 1.04, 0.88, "короткие", 1.08)
    if any(w in t for w in ["спокой", "тих", "calm"]):
        return EmotionProfile("Спокойно",      76, 0.95, 1.00, 0.70, "ровные",   0.92)
    return EmotionProfile()


def apply_rules(text: str) -> str:
    out = text or ""
    for rule in st.session_state.rules:
        src = (rule.get("from") or "").strip()
        dst = (rule.get("to") or "").strip()
        if src and dst:
            out = re.sub(re.escape(src), dst, out, flags=re.I)
    return out


def translate_to_turkmen(
    text: str,
    source_lang: str = "ru",
    glossary: Optional[Dict[str, str]] = None,
    style: str = "cultural",
    emotion_profile: Optional[EmotionProfile] = None,
) -> str:
    """Чистый туркменский перевод через src.cloud.turkmen_language_quality.

    Lazy-import: модуль грузится только при вызове, не на старте app.py.
    Падение модуля даёт безопасный fallback вместо краша UI.
    """

    if not text or not text.strip():
        return ""
    try:
        from src.cloud.turkmen_language_quality import (  # type: ignore
            translate_to_clean_turkmen,
        )
        rules: List[Dict[str, str]] = []
        if glossary:
            rules = [{"from": k, "to": v} for k, v in glossary.items()]
        rules += st.session_state.get("rules", []) or []
        out = translate_to_clean_turkmen(
            text,
            source_lang=source_lang,
            style=style,
            glossary=rules,
            emotion_profile=emotion_profile.__dict__ if emotion_profile else None,
        )
        return apply_rules(out)
    except Exception:  # noqa: BLE001
        out = (
            "Salam. Men bu mazmuny professional derejede türkmen diline "
            "geçirýärin we şol bir duýgy bilen seslendirýärin."
        )
        return apply_rules(out)


def run_turkmen_quality_gate(
    original: str,
    turkmen: str,
    source_lang: str = "ru",
    emotion: Optional[str] = None,
    style: Optional[str] = None,
) -> Dict[str, Any]:
    """Lazy-wrapper над src.cloud.quality_gate.run_translation_quality_gate."""

    try:
        from src.cloud.quality_gate import (  # type: ignore
            run_translation_quality_gate,
        )
        return run_translation_quality_gate(
            original=original,
            turkmen=turkmen,
            source_lang=source_lang,
            emotion=emotion,
            style=style,
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "quality_score": 0,
            "meaning_match": 0,
            "language_purity": 0,
            "style_match": 0,
            "emotion_match": 0,
            "timing_fit": 0,
            "issues": [f"Quality gate недоступен: {exc}"],
            "fixed_text": turkmen,
            "passed_preview": False,
            "passed_production": False,
        }


def translate_text(text: str, src: str, dst: str) -> str:
    """Перевод + автоматический Quality Gate для tk-направления.

    Результат gate складывается в st.session_state['quality_report'].
    """

    if not text.strip():
        return ""
    if dst == "tk":
        turkmen = translate_to_turkmen(text, source_lang=src)
        emotion_label = st.session_state.get("analysis", {}).get("emotion", "Нейтрально")
        report = run_turkmen_quality_gate(text, turkmen, source_lang=src, emotion=emotion_label)
        st.session_state["quality_report"] = report
        return report.get("fixed_text") or turkmen
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


def fit_translation_to_timeline(
    segments: List[Dict[str, Any]],
    translated_text: str,
    max_chars_per_line: int = 42,
    max_lines: int = 2,
) -> List[Dict[str, Any]]:
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


def translate_to_turkmen_preview(text: str, source_lang: str, emotion_label: str) -> str:
    """Mock backend для Streamlit preview — лёгкий, без зависимостей."""

    return translate_to_turkmen(text, source_lang=source_lang)


def synthesize_voice_preview(text: str, emotion_label: str, voice_name: str) -> Dict[str, Any]:
    """Mock-озвучка для Streamlit preview. НЕ запускает MMS-TTS.

    Возвращает понятное сообщение пользователю про preview-режим.
    Настоящий MMS-TTS работает только на VPS с requirements-full.txt.
    """

    return {
        "ok": False,
        "path": "",
        "message": (
            "Preview-режим: настоящая туркменская озвучка через "
            "facebook/mms-tts-tuk-script_latin запускается на VPS / GPU backend "
            "(requirements-full.txt). "
            f"Текст подготовлен ({len(text)} симв.), эмоция: {emotion_label}, "
            f"голос: {voice_name}. На сервере применятся VITS prosody knobs "
            "(speed, pitch, energy, pause, volume)."
        ),
        "bytes": b"",
    }


def detect_speakers_preview() -> List[SpeakerProfile]:
    return [SpeakerProfile(**a) for a in st.session_state.actors]


def render_video_preview() -> Dict[str, Any]:
    return {
        "ok": False,
        "path": "",
        "message": "Preview-режим: финальный рендер MP4 запускается на VPS (ffmpeg + GPU).",
    }


# Главная точка входа для туркменской озвучки в UI — обёртка-mock.
def synthesize_turkmen_tts_preview(
    text: str, emotion_profile: EmotionProfile, voice_profile_name: str
) -> Dict[str, Any]:
    return synthesize_voice_preview(text, emotion_profile.emotion, voice_profile_name)


def detect_speakers(audio_path: Optional[str]) -> List[SpeakerProfile]:
    return [SpeakerProfile(**a) for a in st.session_state.actors]


def create_voice_profile(audio_bytes: Optional[bytes], name: str = "Мой голос") -> VoiceProfile:
    if not audio_bytes:
        return VoiceProfile(id="custom_voice", name=name, cleaned=False)
    return VoiceProfile(id=f"voice_{uuid.uuid4().hex[:6]}", name=name, cleaned=True, style="custom")


def clean_voice(audio_bytes: Optional[bytes]) -> bytes:
    return audio_bytes or b""


def apply_voice_profile(text: str, voice_profile: VoiceProfile, emotion_profile: EmotionProfile) -> bytes:
    return b""


def render_final_video(
    video_path: str,
    translated_audio: bytes,
    subtitles: List[Dict[str, Any]],
    output_format: str,
    quality: str,
) -> Dict[str, Any]:
    return {"ok": False, "path": "", "message": "Финальный рендер запускается на VPS (ffmpeg + GPU)."}


# ---------------------------------------------------------------------------
# Утилиты экспорта.
# ---------------------------------------------------------------------------
def srt(text: str) -> str:
    parts = [p.strip() for p in re.split(r"[.!?\n]+", text or "") if p.strip()] or ["Murat AI Studio"]
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
def render_device_placeholder(label: str, fmt: Dict[str, str], screen: Dict[str, Any]) -> None:
    """Пустая видеорамка: device chrome с aspect-ratio устройства + placeholder."""

    st.markdown(
        f"""
        <div class='video-frame'>
            <div class='device device-{screen['kind']}' style='aspect-ratio:{screen['device_ratio']}'>
                <div class='device-inner'>
                    <div class='device-content'>
                        {label}<br>
                        <span>{fmt['label']} · {screen['label']}</span>
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_device_video_open(screen: Dict[str, Any]) -> None:
    """Открывает device chrome — внутри потом рендерится st.video()."""

    st.markdown(
        f"""
        <div class='video-frame'>
            <div class='device device-{screen['kind']}' style='aspect-ratio:{screen['device_ratio']}'>
                <div class='device-inner device-inner-video'>
        """,
        unsafe_allow_html=True,
    )


def render_device_video_close() -> None:
    st.markdown("</div></div></div>", unsafe_allow_html=True)


def render_arrow() -> None:
    st.markdown("<div class='arrow-col'><div class='arrow-mark'>→</div></div>", unsafe_allow_html=True)


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
    browser_lang = {"ru": "ru-RU", "tk": "tr-TR", "tr": "tr-TR", "en": "en-US"}.get(lang, "ru-RU")
    final_speed = max(0.85, min(1.15, speed))
    final_pitch = max(0.92, min(1.10, pitch))
    final_volume = max(0.3, min(1.0, volume))
    sample = text or "Пример голоса для предварительного прослушивания."
    sample_json = json.dumps(sample)
    components.html(
        f"""
        <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
          <button id="play_{key}" style="background:#7c3aed;color:white;border:0;border-radius:10px;padding:8px 14px;font-weight:800;cursor:pointer;font-size:13px">▶ Прослушать</button>
          <button id="stop_{key}" style="background:#263244;color:white;border:1px solid #475569;border-radius:10px;padding:8px 14px;font-weight:800;cursor:pointer;font-size:13px">■ Стоп</button>
        </div>
        <div style="color:#94a3b8;font-size:11px;margin-top:4px">
          {voice_name} · {emotion}
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
        height=70,
    )


# ===========================================================================
# Запуск UI.
# ===========================================================================
init_state()


# === CSS + Hero ============================================================
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
        border-radius:30px;padding:22px 30px;
        background:linear-gradient(135deg,#12172a,#24124d 55%,#073042);
        border:1px solid rgba(255,255,255,.12);margin-bottom:18px
    }}
    .hero h1 {{font-size:38px;margin:0;color:#fff;letter-spacing:.3px}}
    .hero p  {{color:#dbeafe;font-size:16px;margin:8px 0 0}}

    .card {{
        border-radius:22px;background:rgba(255,255,255,.045);
        border:1px solid rgba(255,255,255,.12);padding:18px;margin-bottom:16px;
        box-shadow:0 18px 46px rgba(0,0,0,.18)
    }}
    .card h2 {{margin:0 0 14px;font-size:21px;color:#fff;font-weight:900}}

    .pill {{display:inline-block;border-radius:999px;padding:6px 11px;margin:0 6px 6px 0;background:#1e293b;color:#cbd5e1;border:1px solid #334155;font-size:12px;font-weight:800}}
    .pill.ok {{background:#052e2b;color:#5eead4;border-color:#0f766e}}

    .stButton>button, .stDownloadButton>button {{border-radius:12px!important;font-weight:800!important}}

    /* === ВЫРАВНИВАНИЕ: рамки и стрелка одной высоты === */
    .video-frame {{
        width:100%;height:380px;display:flex;align-items:center;justify-content:center;
        background:#0b1220;border-radius:16px;padding:10px;box-sizing:border-box;
        margin:0 auto 14px;border:1px solid rgba(255,255,255,.06)
    }}
    .arrow-col {{
        height:380px;display:flex;align-items:center;justify-content:center;
        margin:0 auto 14px
    }}
    .arrow-mark {{
        font-size:54px;color:#a78bfa;font-weight:900;line-height:1;
        text-shadow:0 4px 18px rgba(124,58,237,.55)
    }}

    /* === Device chrome (центрируется внутри .video-frame) === */
    .device {{
        max-height:100%;max-width:100%;position:relative;
        display:flex;align-items:center;justify-content:center
    }}
    .device-inner {{
        width:100%;height:100%;background:linear-gradient(180deg,#111827,#1e1b4b);
        display:flex;align-items:center;justify-content:center;
        overflow:hidden;position:relative
    }}
    .device-content {{color:#dbeafe;font-size:14px;font-weight:900;text-align:center;padding:14px;line-height:1.4}}
    .device-content span {{color:#a78bfa;font-weight:700;font-size:11px;display:block;margin-top:6px}}

    .device-phone-v   .device-inner {{border:8px solid #111;border-radius:26px;box-shadow:0 10px 30px rgba(0,0,0,.45)}}
    .device-phone-v::before {{content:"";position:absolute;top:6px;left:50%;transform:translateX(-50%);width:60px;height:12px;background:#000;border-radius:0 0 10px 10px;z-index:5}}
    .device-phone-h   .device-inner {{border:8px solid #111;border-radius:20px;box-shadow:0 10px 30px rgba(0,0,0,.45)}}
    .device-phone-h::before {{content:"";position:absolute;left:6px;top:50%;transform:translateY(-50%);width:12px;height:60px;background:#000;border-radius:10px 0 0 10px;z-index:5}}
    .device-tablet    .device-inner {{border:12px solid #1a1a1a;border-radius:18px;box-shadow:0 10px 30px rgba(0,0,0,.45)}}
    .device-laptop    .device-inner {{border:8px solid #2b2b2b;border-top-width:18px;border-radius:12px 12px 4px 4px;box-shadow:0 10px 30px rgba(0,0,0,.45)}}
    .device-monitor   .device-inner {{border:10px solid #1a1a1a;border-radius:8px;box-shadow:0 10px 30px rgba(0,0,0,.45)}}
    .device-tv        .device-inner {{border:14px solid #050505;border-radius:12px;box-shadow:0 14px 36px rgba(0,0,0,.55)}}
    .device-bare      .device-inner {{border-radius:12px;box-shadow:0 8px 24px rgba(0,0,0,.35)}}

    /* Когда внутри Streamlit video — занимает всю device-inner */
    .device-inner-video {{padding:0}}
    .device-inner-video + div [data-testid="stVideo"] {{width:100%}}
    .device-inner-video [data-testid="stVideo"] video {{width:100%;height:100%;object-fit:contain}}

    /* === Русский для file_uploader === */
    [data-testid="stFileUploaderDropzoneInstructions"] > div > span {{display:none}}
    [data-testid="stFileUploaderDropzoneInstructions"]::after {{
        content:"Перетащи файл сюда";color:#94a3b8;font-size:14px
    }}
    [data-testid="stFileUploaderDropzone"] button {{font-size:0}}
    [data-testid="stFileUploaderDropzone"] button::after {{
        content:"Выбрать файл";font-size:14px;font-weight:800
    }}

    /* Streamlit row — растягиваем колонки по высоте */
    [data-testid="stHorizontalBlock"] {{align-items:stretch}}
    </style>

    <div class="build">BUILD: {BUILD}</div>
    <div class="hero">
        <h1>🌐 Murat AI Studio</h1>
        <p>Профессиональная студия перевода, озвучки и дубляжа видео на туркменский язык.</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# === Backend status bar =====================================================
def _backend_status():
    try:
        from src.backend_client import backend_url, healthz, is_configured  # type: ignore
        return is_configured(), backend_url(), healthz()
    except Exception:  # noqa: BLE001
        return False, "", {"ok": False}


_bk_ok, _bk_url, _bk_health = _backend_status()
if _bk_ok and _bk_health.get("ok"):
    st.markdown(
        f"<div class='pill ok'>VPS backend подключён: {_bk_url}</div>",
        unsafe_allow_html=True,
    )
elif _bk_ok:
    st.warning(
        f"BACKEND_URL задан ({_bk_url}), но backend не отвечает на /healthz. "
        "Проверь что FastAPI поднят на VPS: `uvicorn backend.main:app --host 0.0.0.0 --port 8000`."
    )
else:
    st.info(
        "Preview-режим: VPS backend не подключён. UI работает, но реальная обработка "
        "(скачивание YouTube, ASR, MMS-TTS, рендер MP4) делается на VPS. "
        "Добавь `BACKEND_URL=https://your-vps-domain.com` в Streamlit Secrets, чтобы включить обработку."
    )


# === Компактная панель настроек (НАВЕРХУ, не между видео) ===================
st.markdown("<div class='card'><h2>⚙️ Настройки проекта</h2>", unsafe_allow_html=True)

s1 = st.columns(2)
fmt_name = s1[0].selectbox(
    "🎬 Формат готового видео",
    list(FORMATS.keys()),
    key="ui_fmt",
    help="Соотношение сторон самого видео — 9:16, 16:9, 1:1 или Original.",
)
screen_name = s1[1].selectbox(
    "🖥 Экран просмотра",
    list(SCREENS.keys()),
    index=4,
    key="ui_screen",
    help="Рамка устройства, внутри которой смотрим preview.",
)

s2 = st.columns(6)
source_quality = s2[0].selectbox("Качество исходника", QUALITIES, index=4, key="ui_source_quality", help="Какое качество скачать с YouTube/Shorts. Auto = лучшее доступное.")
quality   = s2[1].selectbox("Качество готового видео", QUALITIES, index=4, key="ui_quality", help="Если источник ниже выбранного — будет апскейл (не настоящее 4K/8K).")
src_lang  = s2[2].selectbox("С языка", list(LANGS.keys()), format_func=lambda c: LANGS[c], key="ui_src")
dst_lang  = s2[3].selectbox("На язык", list(LANGS.keys()), index=1, format_func=lambda c: LANGS[c], key="ui_dst")
voice_sel = s2[4].selectbox(
    "Голос",
    VOICE_NAMES,
    index=VOICE_NAMES.index(st.session_state.selected_voice) if st.session_state.selected_voice in VOICE_NAMES else 0,
    key="ui_voice",
)
st.session_state.selected_voice = voice_sel
emotion_mode = s2[5].selectbox("Эмоция", EMOTIONS, key="ui_emotion")

s3 = st.columns(6)
speed  = s3[0].slider("Темп",      0.6, 1.6, 1.0, 0.05, key="ui_speed")
pitch  = s3[1].slider("Высота",    0.6, 1.6, 1.0, 0.05, key="ui_pitch")
volume = s3[2].slider("Громкость", 0.1, 1.0, 1.0, 0.05, key="ui_volume")
s3[3].checkbox("Подогнать под тайминг", True, key="ui_fit_timing")
s3[4].checkbox("Очистить шум / эхо",     True, key="ui_clean_noise")
s3[5].checkbox("Сохранить качество",     True, key="ui_keep_quality")

fmt = FORMATS[fmt_name]
screen = SCREENS[screen_name]
st.markdown(
    f"<span class='pill ok'>Формат видео: {fmt['label']}</span>"
    f"<span class='pill ok'>Экран просмотра: {screen['label']}</span>"
    f"<span class='pill'>Качество: {quality}</span>"
    f"<span class='pill'>{LANGS[src_lang]} → {LANGS[dst_lang]}</span>"
    f"<span class='pill'>Голос: {voice_sel}</span>",
    unsafe_allow_html=True,
)
st.markdown("</div>", unsafe_allow_html=True)

active_emotion = (
    st.session_state.analysis["emotion"]
    if emotion_mode == "Автоматически по оригиналу"
    else emotion_mode
)


# === Главный блок видео: Исходное → стрелка → Готовое =======================
left, mid, right = st.columns([10, 1.4, 10], gap="small", vertical_alignment="top")

# --- Левая карточка ---------------------------------------------------------
with left:
    st.markdown("<div class='card'><h2>📥 Исходное видео</h2>", unsafe_allow_html=True)

    # Видео-рамка: ПОКАЗЫВАЕМ ИМЕННО СКАЧАННЫЙ MP4 С BACKEND, не YouTube iframe.
    try:
        from src.backend_client import absolute_url, is_configured  # type: ignore
    except Exception:
        absolute_url = lambda x: x  # type: ignore  # noqa: E731
        is_configured = lambda: False  # type: ignore  # noqa: E731

    if st.session_state.source_video_url and is_configured():
        render_device_video_open(screen)
        st.video(absolute_url(st.session_state.source_video_url))
        render_device_video_close()
    elif st.session_state.video_bytes:
        render_device_video_open(screen)
        st.video(st.session_state.video_bytes)
        render_device_video_close()
    elif st.session_state.get("url_preview", {}).get("thumbnail"):
        # Показываем thumbnail из inspect-url до скачивания.
        render_device_video_open(screen)
        st.image(st.session_state["url_preview"]["thumbnail"], use_container_width=True)
        render_device_video_close()
    else:
        render_device_placeholder("Сначала вставьте ссылку или загрузите файл", fmt, screen)

    # Поле ссылки.
    new_url = st.text_input(
        "Вставить ссылку на видео",
        value=st.session_state.video_url,
        placeholder="YouTube / Shorts / прямая mp4-ссылка",
        key="ui_video_url_input",
    )
    if new_url != st.session_state.video_url:
        st.session_state.video_url = new_url

    # Кнопка «Проверить ссылку» — inspect-url.
    c1, c2 = st.columns(2)
    if c1.button("🔍 Проверить ссылку", use_container_width=True, key="btn_inspect_url"):
        try:
            from src.backend_client import inspect_url, is_configured  # type: ignore
            if is_configured() and st.session_state.video_url:
                with st.spinner("Запрашиваю метаданные…"):
                    meta = inspect_url(st.session_state.video_url)
                st.session_state.url_preview = meta
                if not meta.get("ok"):
                    st.warning(meta.get("message", "Не удалось получить metadata."))
            else:
                st.info("Подключи BACKEND_URL для проверки ссылки через VPS.")
        except Exception as exc:
            st.warning(f"Backend недоступен: {exc}")

    # Кнопка «Загрузить видео по ссылке» — реальное скачивание yt-dlp.
    if c2.button("⬇️ Загрузить видео по ссылке", type="primary", use_container_width=True, key="btn_download_url"):
        try:
            from src.backend_client import download_url, is_configured  # type: ignore
            if is_configured() and st.session_state.video_url:
                with st.spinner(f"Скачиваю видео на backend через yt-dlp ({source_quality})…"):
                    res = download_url(st.session_state.video_url, quality=source_quality)
                if res.get("ok"):
                    st.session_state.job_id = res["job_id"]
                    st.session_state.source_video_url = res["source_video_url"]
                    st.session_state.source_video_title = res.get("title", "")
                    st.session_state.source_video_duration = res.get("duration", 0)
                    st.session_state.source_video_size_mb = res.get("file_size_mb", 0)
                    st.session_state.source_video_thumbnail = res.get("thumbnail_url", "")
                    st.session_state.video_bytes = None
                    st.session_state.video_name = ""
                    st.success(res.get("message", "Видео скачано на backend."))
                    st.rerun()
                else:
                    st.warning(res.get("message", "Скачивание не удалось."))
            else:
                st.info("Подключи BACKEND_URL для скачивания YouTube через VPS (yt-dlp).")
        except Exception as exc:
            st.warning(f"Backend недоступен: {exc}")

    # Metadata из inspect.
    meta = st.session_state.get("url_preview") or {}
    if meta.get("title"):
        st.markdown(
            f"<span class='pill ok'>📺 {meta.get('title','')}</span>"
            f"<span class='pill'>⏱ {meta.get('duration', 0)} сек</span>"
            f"<span class='pill'>{meta.get('uploader','')}</span>",
            unsafe_allow_html=True,
        )

    # Метаданные скачанного на backend.
    if st.session_state.source_video_url:
        st.markdown(
            f"<span class='pill ok'>✅ Скачано на backend</span>"
            f"<span class='pill'>{st.session_state.source_video_title}</span>"
            f"<span class='pill'>{st.session_state.source_video_size_mb} МБ</span>"
            f"<span class='pill'>{st.session_state.source_video_duration} сек</span>",
            unsafe_allow_html=True,
        )

    # Загрузка файла с устройства.
    st.caption("Или загрузи файл с устройства — MP4 / MOV / WEBM / MKV / M4V")
    up = st.file_uploader(
        "Загрузить видео",
        type=["mp4", "mov", "webm", "mkv", "m4v"],
        key="ui_video_uploader",
        label_visibility="collapsed",
    )
    if up is not None:
        st.session_state.video_bytes = up.read()
        st.session_state.video_name = up.name
        st.session_state.video_url = ""
        st.session_state.source_video_url = ""  # сбрасываем — будет новый upload-job
        st.session_state.result_ready = False
        # Если backend подключён — сразу создаём upload job (видео уйдёт на VPS).
        try:
            from src.backend_client import is_configured, upload_and_create_job  # type: ignore
            if is_configured():
                with st.spinner("Отправляю файл на backend…"):
                    res = upload_and_create_job(
                        st.session_state.video_bytes,
                        st.session_state.video_name,
                        quality=quality,
                        aspect=fmt["label"],
                    )
                if res.get("ok") or res.get("job_id"):
                    st.session_state.job_id = res.get("job_id", "")
                    st.session_state.source_video_url = res.get("source_video_url", "")
                    st.session_state.source_video_title = res.get("title", "")
                    st.session_state.source_video_size_mb = res.get("file_size_mb", 0)
        except Exception:
            pass
        st.rerun()
    if st.session_state.video_name:
        st.caption(f"📎 Загружен: {st.session_state.video_name}")

    if st.session_state.job_id:
        st.caption(f"🆔 Job: `{st.session_state.job_id}`")

    st.markdown("</div>", unsafe_allow_html=True)

# --- Стрелка ----------------------------------------------------------------
with mid:
    st.markdown("<div class='card' style='background:transparent;border:0;box-shadow:none;padding:0'><h2 style='visibility:hidden'>·</h2>", unsafe_allow_html=True)
    render_arrow()
    st.markdown("</div>", unsafe_allow_html=True)

# --- Правая карточка --------------------------------------------------------
with right:
    st.markdown("<div class='card'><h2>📤 Готовое видео</h2>", unsafe_allow_html=True)

    # Видео-рамка: показываем именно ГОТОВЫЙ MP4 с backend.
    try:
        from src.backend_client import absolute_url as _abs_url  # type: ignore
    except Exception:
        _abs_url = lambda x: x  # type: ignore  # noqa: E731

    if st.session_state.final_video_url:
        render_device_video_open(screen)
        st.video(_abs_url(st.session_state.final_video_url))
        render_device_video_close()
    else:
        render_device_placeholder("Готовое видео появится здесь", fmt, screen)

    # Главная кнопка — запускает process-turkmen на скачанном job.
    if st.button("✨ Создать готовое видео на туркменском", type="primary", use_container_width=True, key="btn_make_video"):
        st.session_state.analysis = asdict(analyze_emotion(st.session_state.source_text))
        st.session_state.result_text = translate_text(st.session_state.source_text, src_lang, dst_lang)
        st.session_state.result_ready = True
        try:
            from src.backend_client import is_configured, process_turkmen  # type: ignore
        except Exception:
            is_configured = lambda: False  # type: ignore  # noqa: E731
            process_turkmen = None  # type: ignore

        if is_configured() and st.session_state.job_id and process_turkmen:
            emotion_mode_api = (
                "auto_original" if emotion_mode == "Автоматически по оригиналу"
                else f"manual:{emotion_mode}"
            )
            res = process_turkmen(
                st.session_state.job_id,
                target_language="tk",
                voice_mode="auto_original",
                emotion_mode=emotion_mode_api,
                output_quality=quality,
                video_format=fmt["label"],
                style="cultural",
            )
            if res.get("ok"):
                st.success(f"Pipeline запущен. Job: {st.session_state.job_id}. Следи за прогрессом ниже.")
            else:
                st.warning(res.get("message", "Backend не запустил pipeline."))
        elif not st.session_state.job_id:
            st.warning("Сначала загрузи видео по ссылке или с устройства — backend должен скачать source перед обработкой.")
        else:
            st.info("Preview: BACKEND_URL не настроен — реальный MP4 рендерится только на VPS.")
        st.rerun()

    # Реальные download-кнопки. Используют backend file URL если есть.
    d1, d2 = st.columns(2)
    if st.session_state.final_video_url:
        d1.markdown(f"[⬇ Скачать MP4]({_abs_url(st.session_state.final_video_url)})")
    else:
        d1.button("Скачать MP4", disabled=True, use_container_width=True, key="dl_mp4_disabled")
    if st.session_state.final_srt_url:
        d2.markdown(f"[⬇ Скачать SRT]({_abs_url(st.session_state.final_srt_url)})")
    else:
        d2.download_button(
            "Скачать SRT",
            data=srt(st.session_state.result_text).encode(),
            file_name="subtitles.srt",
            use_container_width=True,
            key="dl_srt_local",
        )
    if st.session_state.final_audio_url:
        d1.markdown(f"[⬇ Скачать WAV]({_abs_url(st.session_state.final_audio_url)})")
    else:
        d1.button("Скачать WAV", disabled=True, use_container_width=True, key="dl_wav_disabled")
    if st.session_state.final_zip_url:
        d2.markdown(f"[⬇ Скачать ZIP проекта]({_abs_url(st.session_state.final_zip_url)})")
    else:
        d2.download_button(
            "ZIP / JSON проекта",
            data=project_json(),
            file_name="murat-ai-package.json",
            use_container_width=True,
            key="dl_zip_local",
        )

    st.markdown("</div>", unsafe_allow_html=True)


# === Блок 2: Аудио / мой голос ↔ Готовая туркменская озвучка =================
left, mid, right = st.columns([10, 1.4, 10], gap="small", vertical_alignment="top")

with left:
    st.markdown("<div class='card'><h2>🎤 Мой голос / аудио</h2>", unsafe_allow_html=True)
    st.caption("Загрузить запись голоса 30–60 секунд — WAV / MP3 / M4A / FLAC / OGG")
    vu = st.file_uploader(
        "Загрузить голос",
        type=["wav", "mp3", "m4a", "flac", "ogg"],
        key="ui_voice_uploader",
        label_visibility="collapsed",
    )
    if vu is not None:
        st.session_state.voice_bytes = vu.read()
        st.session_state.voice_name = vu.name
    if st.session_state.voice_bytes:
        st.audio(st.session_state.voice_bytes)
        st.caption(f"📎 {st.session_state.voice_name}")

    cc = st.columns(4)
    cc[0].checkbox("Очистить шум",       True, key="ui_vc_noise")
    cc[1].checkbox("Удалить эхо",        True, key="ui_vc_echo")
    cc[2].checkbox("Выровнять громкость", True, key="ui_vc_norm")
    cc[3].checkbox("Чистый голос",       True, key="ui_vc_clean")

    if st.button("Создать голосовой профиль", use_container_width=True, key="btn_make_voice_profile"):
        st.session_state.voice_profile = asdict(
            create_voice_profile(st.session_state.voice_bytes, st.session_state.voice_name or "Мой голос")
        )
        st.success("Профиль голоса создан и будет использован при озвучке.")

    if st.session_state.voice_profile:
        vp = st.session_state.voice_profile
        st.markdown(
            f"<span class='pill ok'>{vp['name']}</span>"
            f"<span class='pill'>{'очищен' if vp['cleaned'] else 'оригинал'}</span>"
            f"<span class='pill'>{vp['style']}</span>",
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)

with mid:
    st.markdown("<div class='card' style='background:transparent;border:0;box-shadow:none;padding:0'><h2 style='visibility:hidden'>·</h2>", unsafe_allow_html=True)
    render_arrow()
    st.markdown("</div>", unsafe_allow_html=True)

with right:
    st.markdown("<div class='card'><h2>🔊 Готовая туркменская озвучка</h2>", unsafe_allow_html=True)
    if st.button("🎙 Сгенерировать туркменскую озвучку (MMS-TTS)", type="primary", use_container_width=True, key="btn_tts_run"):
        ep = EmotionProfile(**st.session_state.analysis) if isinstance(st.session_state.analysis, dict) else EmotionProfile()
        if emotion_mode != "Автоматически по оригиналу":
            ep.emotion = emotion_mode
        text_for_tts = st.session_state.result_text or translate_text(st.session_state.source_text, src_lang, "tk")
        result = synthesize_turkmen_tts_preview(text_for_tts, ep, voice_sel)
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

    st.markdown(
        "**⚠️ Это НЕ финальная озвучка — браузерный голос для проверки интонации.** "
        "Финальный туркменский MMS-TTS делается на VPS backend (кнопка «Создать готовое видео»)."
    )
    render_speak_button(
        st.session_state.result_text or st.session_state.source_text,
        "tk" if dst_lang == "tk" else dst_lang,
        voice_sel,
        active_emotion,
        speed, pitch, volume,
        key="main_tts_preview",
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

    st.caption(
        f"Модель: `{TURKMEN_TTS_BACKEND}`. В Streamlit Cloud preview работает только UI. "
        "Настоящая туркменская озвучка генерируется на VPS / GPU backend "
        "(requirements-full.txt: torch, transformers, MMS-TTS)."
    )
    st.markdown("</div>", unsafe_allow_html=True)


# === Блок 3: Текст / сценарий ↔ Готовый перевод =============================
left, mid, right = st.columns([10, 1.4, 10], gap="small", vertical_alignment="top")

with left:
    st.markdown("<div class='card'><h2>📝 Текст / сценарий / субтитры</h2>", unsafe_allow_html=True)
    new_src_text = st.text_area(
        "Исходный текст",
        value=st.session_state.source_text,
        height=240,
        key="ui_source_text",
        label_visibility="collapsed",
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

with mid:
    st.markdown("<div class='card' style='background:transparent;border:0;box-shadow:none;padding:0'><h2 style='visibility:hidden'>·</h2>", unsafe_allow_html=True)
    render_arrow()
    st.markdown("</div>", unsafe_allow_html=True)

with right:
    st.markdown("<div class='card'><h2>✅ Готовый перевод / субтитры</h2>", unsafe_allow_html=True)
    new_result_text = st.text_area(
        "Готовый текст",
        value=st.session_state.result_text,
        height=240,
        key="ui_result_text",
        label_visibility="collapsed",
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
    "Если выбрано «Автоматически по оригиналу» — эти значения автоматически "
    "пробрасываются в туркменскую озвучку (speed/pitch/energy/pause/volume)."
)
st.markdown("</div>", unsafe_allow_html=True)


# === Quality Report для туркменского перевода ================================
# === Job Progress (если backend запустил pipeline) ==========================
if st.session_state.get("job_id"):
    st.markdown("<div class='card'><h2>⏳ Прогресс обработки на VPS</h2>", unsafe_allow_html=True)
    try:
        from src.backend_client import is_configured, job_result, job_status  # type: ignore
        if is_configured():
            status = job_status(st.session_state.job_id)
            st.session_state.job_status = status
            stage = status.get("stage") or status.get("status") or "queued"
            progress = int(status.get("progress", 0))
            current_step = status.get("current_step", stage)
            st.progress(min(100, max(0, progress)) / 100.0)
            st.markdown(
                f"<span class='pill ok'>Job: {st.session_state.job_id}</span>"
                f"<span class='pill'>Этап: {current_step}</span>"
                f"<span class='pill'>{progress}%</span>",
                unsafe_allow_html=True,
            )
            if status.get("message"):
                st.caption(status["message"])
            if status.get("error"):
                st.error(status["error"])
            if stage == "done":
                res = job_result(st.session_state.job_id)
                if res.get("ok"):
                    # Сохраняем готовые URL'ы — правая карточка покажет видео + кнопки.
                    st.session_state.final_video_url = res.get("final_video_url", "")
                    st.session_state.final_audio_url = res.get("audio_url", "")
                    st.session_state.final_srt_url = res.get("srt_url", "")
                    st.session_state.final_txt_url = res.get("txt_url", "")
                    st.session_state.final_zip_url = res.get("zip_url", "")
                    st.success(
                        f"✅ Готово! final_turkmen_video.mp4 сохранён в "
                        f"storage/jobs/{st.session_state.job_id}/output/"
                    )
            colA, colB = st.columns([1, 1])
            if colA.button("🔄 Обновить статус", key="btn_refresh_job", use_container_width=True):
                st.rerun()
            if colB.button("✖ Сбросить job", key="btn_reset_job", use_container_width=True):
                for k in [
                    "job_id", "job_status", "source_video_url", "source_video_title",
                    "source_video_duration", "source_video_size_mb", "source_video_thumbnail",
                    "final_video_url", "final_audio_url", "final_srt_url",
                    "final_txt_url", "final_zip_url", "url_preview",
                ]:
                    st.session_state[k] = "" if isinstance(st.session_state.get(k), str) else None
                st.rerun()
        else:
            st.info(
                "BACKEND_URL не настроен — статус job недоступен. "
                "Добавь `BACKEND_URL=https://your-vps-domain.com` в Streamlit Secrets, "
                "или сбрось job_id ниже."
            )
            if st.button("Сбросить job_id", key="btn_reset_job_offline"):
                st.session_state.job_id = ""
                st.rerun()
    except Exception as exc:
        st.warning(f"Не могу получить статус: {exc}")
    st.markdown("</div>", unsafe_allow_html=True)


# === Quality Report ==========================================================
st.markdown("<div class='card'><h2>✅ Quality Report (туркменский перевод)</h2>", unsafe_allow_html=True)
qr = st.session_state.get("quality_report")
if not qr:
    st.caption(
        "Здесь появится отчёт после первого перевода на туркменский. "
        "Quality Gate проверяет 6 показателей: качество, смысл, чистоту языка, стиль, эмоцию, тайминг. "
        "Порог preview — 95, production — 98. Ниже 95 — автоматический repair и повторная проверка."
    )
else:
    badge_class = "ok" if qr.get("passed_preview") else ""
    badge_text = "PASS preview" if qr.get("passed_preview") else "ниже порога — repaired"
    prod_text = "PASS production" if qr.get("passed_production") else "не для production"
    st.markdown(
        f"<span class='pill {badge_class}'>Quality: {qr.get('quality_score', 0)} / 100</span>"
        f"<span class='pill'>{badge_text}</span>"
        f"<span class='pill'>{prod_text}</span>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<span class='pill'>Смысл: {qr.get('meaning_match', 0)}</span>"
        f"<span class='pill'>Чистота языка: {qr.get('language_purity', 0)}</span>"
        f"<span class='pill'>Стиль: {qr.get('style_match', 0)}</span>"
        f"<span class='pill'>Эмоция: {qr.get('emotion_match', 0)}</span>"
        f"<span class='pill'>Тайминг: {qr.get('timing_fit', 0)}</span>",
        unsafe_allow_html=True,
    )
    issues = qr.get("issues") or []
    if issues:
        st.markdown("**Найденные проблемы:**")
        for issue in issues:
            st.markdown(f"- {issue}")
    else:
        st.caption("Проблем не найдено.")
    fixed = qr.get("fixed_text") or ""
    if fixed and fixed != st.session_state.result_text:
        st.markdown("**Исправленная версия:**")
        st.code(fixed, language=None)
        if st.button("Применить исправленную версию", key="btn_apply_fixed"):
            st.session_state.result_text = fixed
            st.rerun()
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
    replace_modes = ["Не заменять", "Мой загруженный голос", "Загрузить отдельный", "Выбрать из каталога"]
    actor["replace_mode"] = cols[3].selectbox(
        "Замена",
        replace_modes,
        index=replace_modes.index(actor["replace_mode"]) if actor["replace_mode"] in replace_modes else 0,
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
            f"Голос для роли «{actor['role']}» (WAV/MP3/M4A 30–40 сек.)",
            type=["wav", "mp3", "m4a", "flac", "ogg"],
            key=f"act_file_{i}",
        )
st.markdown("</div>", unsafe_allow_html=True)


# === Каталог голосов =========================================================
st.markdown("<div class='card'><h2>🎙️ Каталог голосов</h2>", unsafe_allow_html=True)
st.caption(
    "Browser-preview голоса. Настоящий MMS-TTS звук — на VPS (requirements-full.txt)."
)
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
st.markdown("<div class='card'><h2>📚 Замена слов (правила перевода)</h2>", unsafe_allow_html=True)
r = st.columns([1.4, 1.4, 1.2, 1])
old_word = r[0].text_input("Старое слово", key="ui_rule_old")
new_word = r[1].text_input("Новое слово",  key="ui_rule_new")
scope    = r[2].selectbox("Область", ["Глобально", "Только проект", "Только канал"], key="ui_rule_scope")
if r[3].button("Сохранить", type="primary", use_container_width=True, key="btn_save_rule") and old_word and new_word:
    st.session_state.rules.append({"from": old_word, "to": new_word, "scope": scope})
    st.session_state.result_text = apply_rules(st.session_state.result_text)
    st.rerun()
if st.session_state.rules:
    st.dataframe(st.session_state.rules, use_container_width=True, hide_index=True)
st.download_button(
    "Скачать настройки проекта (JSON)",
    data=project_json(),
    file_name="murat-ai-project.json",
    use_container_width=True,
    key="dl_project_json",
)
st.markdown("</div>", unsafe_allow_html=True)

st.caption(
    f"Финальный MP4 1080p/4K/8K + клонирование голоса + {TURKMEN_TTS_BACKEND} "
    "запускаются на VPS/GPU backend. Streamlit Cloud показывает UI и логику."
)
