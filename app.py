"""Murat AI — Streamlit preview UI.

Один профессиональный экран без вкладок и без боковой панели. Слева —
вход (видео / аудио / текст), справа — готовый результат. Видео-окно
адаптируется под формат (9:16 / 16:9 / 1:1 / Original).

Этот файл обязан показывать BUILD-метку в самом верху страницы — она
читает короткий commit-sha напрямую из ``.git/HEAD`` репозитория, то
есть «доказывает», что Streamlit Cloud запустил именно эту версию.

Новое в этой ревизии:
* верхний BUILD-баннер (ветка / sha / дата);
* боковая панель Streamlit полностью скрыта;
* английские строки нативных виджетов (drop-zone, кнопки file uploader)
  переписаны через CSS;
* добавлен режим эмоции «🤖 Автоматически по оригиналу» (default) +
  блок «📊 Анализ оригинала» с EmotionProfile-метриками;
* для каждой роли актёра — собственный режим эмоции (по реплике /
  по оригиналу / вручную);
* project JSON сохраняет ``emotion_mode`` и полный ``emotion_profile``
  (emotion, confidence, speed, pitch, energy, pause, volume, source,
  language, actor_id, segment_start/end).
"""

from __future__ import annotations

import base64
import html
import json
import re
import tempfile
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import streamlit as st
import streamlit.components.v1 as components

# ---------------------------------------------------------------------------
# Page config & BUILD info
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Murat AI",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def _read_commit_sha() -> str:
    """Read the short HEAD SHA from .git/ on disk.

    Streamlit Cloud clones the repository, so ``.git/HEAD`` is available
    at runtime. If anything goes wrong we degrade to ``unknown`` rather
    than crashing the UI.
    """
    try:
        head = Path(".git/HEAD").read_text(encoding="utf-8").strip()
        if head.startswith("ref: "):
            ref = head[5:]
            ref_path = Path(".git") / ref
            if ref_path.exists():
                return ref_path.read_text(encoding="utf-8").strip()[:7]
        return head[:7] if head else "unknown"
    except Exception:
        return "unknown"


def _read_commit_date() -> str:
    """Modification time of the entry-point file → friendly build date."""
    try:
        ts = Path(__file__).stat().st_mtime
        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


BUILD_BRANCH = "streamlit-preview"
BUILD_COMMIT = _read_commit_sha()
BUILD_DATE = _read_commit_date()
BUILD_BANNER = f"BUILD: {BUILD_BRANCH} / {BUILD_COMMIT} / {BUILD_DATE}"


# ---------------------------------------------------------------------------
# Domain constants
# ---------------------------------------------------------------------------

LANG_LABELS = {"ru": "Русский", "tk": "Туркменский", "tr": "Турецкий", "en": "Английский"}
LANGS = ["ru", "tk", "tr", "en"]

FORMATS = {
    "9:16 — Shorts / Reels / TikTok": ("9 / 16", 360, "vertical"),
    "16:9 — YouTube": ("16 / 9", 720, "horizontal"),
    "1:1 — Square": ("1 / 1", 480, "square"),
    "Original — как у исходника": ("auto", 720, "original"),
}

QUALITIES = ["1080p Full HD", "4K Ultra HD", "8K"]

VOICES = [
    "👶 Детский",
    "🧑 Подростковый",
    "👩 Женский",
    "👨 Мужской",
    "🎬 Кино-диктор",
    "🎤 Блогерский",
    "⭐ Мой загруженный голос",
]

EMOTIONS_MANUAL = [
    "🙂 Нейтрально",
    "😄 Радостно",
    "🥺 Грустно",
    "🎯 Серьёзно",
    "😠 Злой тон",
    "🧘 Спокойно",
    "⚡ Энергично",
    "🎭 Кино-драма",
    "🤫 Шёпот",
    "😨 Волнение",
    "😲 Удивление",
    "😱 Страх",
    "❤️ Добрый тон",
    "🌟 Сказочный тон",
    "💎 Рекламный тон",
]
EMOTION_AUTO = "🤖 Автоматически по оригиналу"
EMOTIONS_ALL = [EMOTION_AUTO, *EMOTIONS_MANUAL]

# Per-emotion prosody knobs (clean keys w/o emoji).
EMOTION_PARAMS: Dict[str, Dict[str, float]] = {
    "Нейтрально":      {"speed": 1.00, "pitch": 1.00, "energy": 0.50, "pause": 1.00, "volume": 1.00},
    "Радостно":        {"speed": 1.10, "pitch": 1.12, "energy": 0.80, "pause": 0.85, "volume": 1.00},
    "Грустно":         {"speed": 0.85, "pitch": 0.92, "energy": 0.40, "pause": 1.30, "volume": 0.75},
    "Серьёзно":        {"speed": 0.95, "pitch": 0.95, "energy": 0.65, "pause": 1.10, "volume": 1.00},
    "Злой тон":        {"speed": 1.05, "pitch": 0.90, "energy": 0.95, "pause": 0.80, "volume": 1.00},
    "Спокойно":        {"speed": 0.92, "pitch": 0.98, "energy": 0.40, "pause": 1.15, "volume": 0.85},
    "Энергично":       {"speed": 1.15, "pitch": 1.08, "energy": 0.90, "pause": 0.75, "volume": 1.00},
    "Кино-драма":      {"speed": 0.88, "pitch": 0.92, "energy": 0.75, "pause": 1.20, "volume": 1.00},
    "Шёпот":           {"speed": 0.85, "pitch": 1.00, "energy": 0.20, "pause": 1.30, "volume": 0.45},
    "Волнение":        {"speed": 1.10, "pitch": 1.10, "energy": 0.80, "pause": 0.85, "volume": 1.00},
    "Удивление":       {"speed": 1.05, "pitch": 1.15, "energy": 0.70, "pause": 0.85, "volume": 1.00},
    "Страх":           {"speed": 1.12, "pitch": 1.05, "energy": 0.70, "pause": 0.90, "volume": 0.85},
    "Добрый тон":      {"speed": 0.95, "pitch": 1.02, "energy": 0.55, "pause": 1.05, "volume": 0.95},
    "Сказочный тон":   {"speed": 0.95, "pitch": 1.08, "energy": 0.60, "pause": 1.10, "volume": 0.95},
    "Рекламный тон":   {"speed": 1.10, "pitch": 1.10, "energy": 0.85, "pause": 0.80, "volume": 1.00},
}

# Keyword bank for fast text-based emotion detection in preview.
EMOTION_KEYWORDS: Dict[str, List[str]] = {
    "Радостно":      ["рад", "счастлив", "ура", "восторг", "люблю", "begendim", "şat", "şatlyk", "happy", "great", "awesome"],
    "Грустно":       ["грустно", "плакать", "печал", "тоск", "плохо", "обидно", "gam", "gynan", "sad", "cry"],
    "Злой тон":      ["ненавижу", "злой", "ненависть", "враг", "ублюдок", "сука", "блядь", "идиот", "gahar", "hate", "angry"],
    "Серьёзно":      ["важно", "официально", "документ", "правил", "закон", "проблем", "möhüm", "resmi", "official"],
    "Спокойно":      ["спокой", "размеренн", "тих", "rahat", "asuda", "calm"],
    "Рекламный тон": ["купить", "скидк", "акция", "цен", "купи", "satyn al", "arzanladyş", "buy", "sale", "promo"],
    "Сказочный тон": ["сказк", "однажды", "царь", "королев", "ertek", "patyşa", "once upon"],
    "Удивление":     ["удивит", "ничего себе", "вау", "geňirge", "wow", "amazing"],
    "Страх":         ["страх", "испугал", "боюсь", "ужас", "gork", "scared", "afraid"],
    "Волнение":      ["волну", "тревож", "переживаю", "alada", "worried", "nervous"],
    "Энергично":     ["вперёд", "давай", "погнали", "ýaňy", "let's go"],
    "Кино-драма":    ["судьба", "герой", "финал", "пафос", "epic"],
    "Шёпот":         ["шёпот", "тихонь", "pyşyrda"],
    "Добрый тон":    ["мама", "семья", "родн", "люб", "maşgala", "love", "family"],
}

REPLACE_SCOPES = ["🌍 Глобально", "📁 Только текущий проект", "📺 Только текущий канал"]

# Per-actor emotion modes
ACTOR_EMOTION_MODES = [
    "🤖 Автоматически по реплике",
    "🤖 Автоматически по оригиналу",
    *EMOTIONS_MANUAL,
]

REPLACE_MODES = ["Не заменять", "⭐ Мой загруженный голос", "🎤 Другой голос (см. ниже)"]

SAMPLE_TRANSLATIONS: Dict[Tuple[str, str], str] = {
    ("ru", "tk"): "Salam. Men bu wideony arassa türkmen diline terjime edip, professional derejede seslendirmek isleýärin.",
    ("tk", "ru"): "Здравствуйте. Я хочу перевести это видео и сделать профессиональную озвучку.",
    ("ru", "en"): "Hello. I want to translate this video and make a professional voiceover.",
    ("en", "ru"): "Здравствуйте. Я хочу перевести это видео и сделать профессиональную озвучку.",
    ("ru", "tr"): "Merhaba. Bu videoyu profesyonel dublaj için çevirmek istiyorum.",
    ("tr", "ru"): "Здравствуйте. Я хочу перевести и озвучить это видео.",
}

TURKMEN_TTS_BACKEND = "facebook/mms-tts-tuk-script_latin"


# ---------------------------------------------------------------------------
# EmotionProfile + analyzers
# ---------------------------------------------------------------------------


@dataclass
class EmotionProfile:
    """Параметры эмоции которые применяются к озвучке и сохраняются в JSON."""

    emotion: str = "Нейтрально"
    confidence: float = 0.6
    speed: float = 1.00
    pitch: float = 1.00
    energy: float = 0.50
    pause: float = 1.00
    volume: float = 1.00
    source: str = "text"        # text / audio / video
    language: str = "ru"
    actor_id: Optional[str] = None
    segment_start: Optional[float] = None
    segment_end: Optional[float] = None

    def to_dict(self) -> dict:
        return asdict(self)


def clean_emotion_label(label: str) -> str:
    """Убирает эмодзи-префикс из лейбла эмоции для сопоставления с EMOTION_PARAMS."""
    if not label:
        return "Нейтрально"
    if label == EMOTION_AUTO:
        return "Нейтрально"
    parts = label.split(" ", 1)
    return parts[1] if len(parts) == 2 else parts[0]


def emotion_label_from_clean(clean: str) -> str:
    """Обратное: по чистому имени найти UI-лейбл с эмодзи."""
    for label in EMOTIONS_MANUAL:
        if clean_emotion_label(label) == clean:
            return label
    return "🙂 Нейтрально"


def profile_for_emotion(
    clean_emotion: str,
    *,
    confidence: float = 0.7,
    source: str = "text",
    language: str = "ru",
    actor_id: Optional[str] = None,
) -> EmotionProfile:
    p = EMOTION_PARAMS.get(clean_emotion, EMOTION_PARAMS["Нейтрально"])
    return EmotionProfile(
        emotion=clean_emotion,
        confidence=confidence,
        speed=p["speed"],
        pitch=p["pitch"],
        energy=p["energy"],
        pause=p["pause"],
        volume=p["volume"],
        source=source,
        language=language,
        actor_id=actor_id,
    )


def analyze_text_emotion(text: str, *, language: str = "ru",
                          actor_id: Optional[str] = None) -> EmotionProfile:
    """Лёгкий keyword-based анализ для preview. Реальный backend — на VPS."""
    if not text or not text.strip():
        return profile_for_emotion("Нейтрально", confidence=0.5,
                                    source="text", language=language,
                                    actor_id=actor_id)
    t = text.lower()
    scores: Dict[str, int] = {}
    for emo, keywords in EMOTION_KEYWORDS.items():
        scores[emo] = sum(1 for kw in keywords if kw in t)
    best, hits = max(scores.items(), key=lambda kv: kv[1])
    if hits == 0:
        return profile_for_emotion("Нейтрально", confidence=0.6,
                                    source="text", language=language,
                                    actor_id=actor_id)
    confidence = min(0.95, 0.55 + 0.10 * hits)
    return profile_for_emotion(best, confidence=confidence,
                                source="text", language=language,
                                actor_id=actor_id)


def analyze_audio_emotion(_: bytes, *, language: str = "ru") -> EmotionProfile:
    """Заглушка: в preview просто отдаёт нейтральный профиль с пометкой source=audio."""
    return profile_for_emotion("Нейтрально", confidence=0.55,
                                source="audio", language=language)


def analyze_video_emotion(_: bytes, *, language: str = "ru") -> EmotionProfile:
    """Заглушка: для preview ровно та же логика что у аудио."""
    return profile_for_emotion("Нейтрально", confidence=0.5,
                                source="video", language=language)


def apply_emotion_to_tts(_: str, voice: str, profile: EmotionProfile) -> Dict[str, float]:
    """Готовый набор TTS-параметров под текущую эмоцию + голос (для backend)."""
    base_speed = profile.speed
    base_pitch = profile.pitch
    v = voice.lower()
    if "детский" in v or "женский" in v:
        base_pitch *= 1.10
    elif "мужской" in v and "подрост" not in v:
        base_pitch *= 0.94
    if "кино" in v or "драматич" in v:
        base_speed *= 0.94
        base_pitch *= 0.96
    return {
        "speed": round(base_speed, 3),
        "pitch": round(base_pitch, 3),
        "energy": round(profile.energy, 3),
        "pause": round(profile.pause, 3),
        "volume": round(profile.volume, 3),
    }


def preserve_emotion_in_translation(
    source_text: str, translated_text: str, profile: EmotionProfile,
) -> str:
    """Маркер для translator-backend: сохрани эмоциональную окраску.

    В preview просто возвращает translated_text — реальный backend на VPS
    использует profile.emotion как hint в системном промте провайдера.
    """
    return translated_text


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------


def init_state() -> None:
    defaults = {
        "source_url": "",
        "source_file_bytes": None,
        "source_file_name": "",
        "result_ready": False,

        "voice_sample_bytes": None,
        "voice_sample_name": "",
        "voice_profile_ready": False,
        "voice_generated": False,

        "source_text": "Привет. Я хочу сделать профессиональное короткое видео с переводом и озвучкой на туркменском.",
        "translated_text": "",

        "replace_from": "",
        "replace_to": "",
        "replace_scope": REPLACE_SCOPES[0],
        "rules": [],

        # Emotion mode
        "emotion_mode": EMOTION_AUTO,
        "emotion_profile": None,    # dict

        # Roles
        "actors": [
            {"role": "Актёр 1", "voice": "👨 Мужской", "emotion_mode": ACTOR_EMOTION_MODES[0],
             "replace_mode": "Не заменять", "sample_name": ""},
            {"role": "Актёр 2", "voice": "👩 Женский", "emotion_mode": ACTOR_EMOTION_MODES[0],
             "replace_mode": "Не заменять", "sample_name": ""},
        ],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_state()


# ---------------------------------------------------------------------------
# CSS — hide sidebar completely, localise English file-uploader strings,
# adaptive video frames, calm dark theme
# ---------------------------------------------------------------------------


def inject_css(aspect_css: str, frame_max_width: int) -> None:
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@500;700&display=swap');

        html, body, [class*="css"] {{ font-family: 'Inter', -apple-system, sans-serif; }}

        /* HIDE SIDEBAR COMPLETELY */
        [data-testid="stSidebar"],
        [data-testid="stSidebarCollapsedControl"],
        [data-testid="collapsedControl"],
        section[data-testid="stSidebar"] {{
            display: none !important; visibility: hidden !important; width: 0 !important;
        }}
        [data-testid="stAppViewContainer"] > section:first-of-type {{
            display: none !important;
        }}
        [data-testid="stAppViewContainer"] > .main {{ margin-left: 0 !important; }}

        .block-container {{ max-width: 1480px; padding-top: 0.4rem; padding-bottom: 4rem; }}

        /* BUILD banner */
        .build-banner {{
            background: linear-gradient(135deg, #facc15 0%, #f59e0b 100%);
            color: #0f172a; font-family: 'JetBrains Mono', monospace;
            font-weight: 800; font-size: 13px; text-align: center;
            padding: 8px 16px; border-radius: 10px;
            margin: 0 0 14px; letter-spacing: 0.3px;
            border: 1px solid rgba(0,0,0,.10);
            box-shadow: 0 4px 16px rgba(250, 204, 21, 0.18);
        }}

        /* Hero */
        .hero {{
            border-radius: 24px; padding: 22px 26px;
            background: linear-gradient(135deg, #1a1c2e 0%, #2a1e4d 60%, #0e3550 100%);
            border: 1px solid rgba(255,255,255,.10);
            margin-bottom: 18px;
        }}
        .hero h1 {{ margin: 0; font-size: 34px; font-weight: 800; color: #fff; }}
        .hero .tag {{ color: #c4b5fd; font-weight: 600; font-size: 15px; margin-top: 4px; }}

        /* Cards */
        .card {{
            border-radius: 22px; padding: 20px 20px 18px;
            background: rgba(255,255,255,.04);
            border: 1px solid rgba(255,255,255,.10);
            box-shadow: 0 14px 32px rgba(0,0,0,.20);
            margin-bottom: 14px;
        }}
        .card-title {{
            font-size: 17px; font-weight: 800; color: #fff; margin-bottom: 14px;
            display: flex; align-items: center; gap: 8px;
        }}

        /* Video frame — adaptive */
        .video-frame {{
            width: 100%; max-width: {frame_max_width}px;
            aspect-ratio: {aspect_css};
            margin: 4px auto 16px;
            border-radius: 22px; overflow: hidden;
            background: #0b0d12;
            border: 2px solid rgba(255,255,255,.10);
            box-shadow: 0 18px 35px rgba(0,0,0,.45),
                         inset 0 0 0 1px rgba(255,255,255,.04);
            position: relative;
        }}
        .video-frame.original {{ aspect-ratio: auto; min-height: 360px; }}
        .video-frame iframe, .video-frame video {{
            width: 100% !important; height: 100% !important;
            border: 0; display: block; object-fit: cover;
        }}
        .video-empty {{
            display: flex; align-items: center; justify-content: center;
            text-align: center; color: #94a3b8; font-size: 14px;
            min-height: 320px; padding: 24px; line-height: 1.5;
        }}
        .video-empty .emoji {{ font-size: 54px; display: block; margin-bottom: 14px; }}

        /* Inputs */
        .stTextInput input, .stTextArea textarea, .stSelectbox > div > div,
        .stMultiSelect > div > div, .stNumberInput input {{
            background: #11141b !important;
            border: 1px solid rgba(255,255,255,.10) !important;
            border-radius: 12px !important;
            color: #e5e7eb !important;
        }}
        .stButton > button {{
            border-radius: 12px !important; font-weight: 700 !important;
            border: 1px solid rgba(255,255,255,.12) !important;
            padding: 0.6rem 1.0rem !important;
        }}
        .stButton > button[kind="primary"] {{
            background: linear-gradient(135deg, #7c3aed 0%, #06b6d4 100%) !important;
            color: #fff !important; border: 0 !important;
            box-shadow: 0 8px 20px rgba(124,58,237,.25);
        }}
        .stDownloadButton > button {{
            border-radius: 12px !important; font-weight: 700 !important;
            background: #1f2937 !important; color: #e5e7eb !important;
            border: 1px solid rgba(255,255,255,.10) !important;
        }}

        /* Localise Streamlit file_uploader English strings via CSS hack */
        [data-testid="stFileUploaderDropzoneInstructions"] > div > span {{ display: none; }}
        [data-testid="stFileUploaderDropzoneInstructions"] > div::after {{
            content: "Перетащи файл сюда";
            color: #e5e7eb; font-weight: 600;
        }}
        [data-testid="stFileUploaderDropzoneInstructions"] > div > small {{ display: none; }}
        [data-testid="stFileUploaderDropzone"] button {{
            font-size: 0 !important; min-width: 110px !important;
        }}
        [data-testid="stFileUploaderDropzone"] button::after {{
            content: "Выбрать";
            font-size: 14px !important; font-weight: 700;
        }}

        /* Pills */
        .pill {{
            display: inline-block; padding: 5px 11px; border-radius: 999px;
            font-size: 12px; font-weight: 700; margin: 0 6px 6px 0;
            background: rgba(124,58,237,.18); color: #c4b5fd;
            border: 1px solid rgba(124,58,237,.30);
        }}
        .pill.ok   {{ background: rgba(34,197,94,.15); color: #86efac;
                       border-color: rgba(34,197,94,.30); }}
        .pill.warn {{ background: rgba(245,158,11,.15); color: #fcd34d;
                       border-color: rgba(245,158,11,.30); }}
        .pill.mute {{ background: rgba(255,255,255,.05); color: #cbd5e1;
                       border-color: rgba(255,255,255,.10); }}

        .actor-card {{
            background: rgba(255,255,255,.03);
            border: 1px solid rgba(255,255,255,.08);
            border-radius: 14px; padding: 12px 14px; margin-bottom: 8px;
        }}

        /* Analysis bars */
        .metric-row {{ display: grid; grid-template-columns: 130px 1fr 70px;
                       gap: 10px; align-items: center; margin: 6px 0; }}
        .metric-label {{ color: #cbd5e1; font-weight: 600; font-size: 13px; }}
        .metric-track {{
            height: 8px; background: rgba(255,255,255,.06);
            border-radius: 999px; overflow: hidden;
        }}
        .metric-fill {{
            height: 100%; border-radius: 999px;
            background: linear-gradient(135deg, #7c3aed 0%, #06b6d4 100%);
        }}
        .metric-value {{ color: #e5e7eb; font-family: 'JetBrains Mono', monospace;
                         font-size: 13px; font-weight: 700; text-align: right; }}

        .small-note {{ color: #94a3b8; font-size: 13px; margin-top: 6px; }}

        #MainMenu {{ visibility: hidden; }}
        footer {{ visibility: hidden; }}
        header[data-testid="stHeader"] {{ background: transparent; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Video / media helpers
# ---------------------------------------------------------------------------

YT_RE = re.compile(
    r"(?:youtube\.com/(?:watch\?v=|shorts/|embed/)|youtu\.be/)([A-Za-z0-9_-]{6,})"
)
TIKTOK_RE = re.compile(r"tiktok\.com/.+/video/(\d+)")


def youtube_embed(url: str) -> Optional[str]:
    m = YT_RE.search(url)
    return f"https://www.youtube.com/embed/{m.group(1)}?rel=0&modestbranding=1" if m else None


def tiktok_embed(url: str) -> Optional[str]:
    m = TIKTOK_RE.search(url)
    return f"https://www.tiktok.com/embed/v2/{m.group(1)}" if m else None


def direct_media_url(url: str) -> bool:
    return bool(re.search(r"\.(mp4|webm|mov|m4v|mp3|wav|m4a)(\?|$)", url.strip(), flags=re.I))


def render_video_frame(
    url: Optional[str], file_bytes: Optional[bytes], file_name: str,
    fmt_class: str, placeholder_emoji: str, placeholder_text: str,
) -> None:
    klass = "video-frame original" if fmt_class == "original" else "video-frame"

    if url:
        yt = youtube_embed(url)
        if yt:
            st.markdown(
                f'<div class="{klass}"><iframe src="{html.escape(yt)}" '
                f'allow="autoplay; encrypted-media; picture-in-picture" '
                f'allowfullscreen></iframe></div>',
                unsafe_allow_html=True,
            )
            return
        tt = tiktok_embed(url)
        if tt:
            st.markdown(
                f'<div class="{klass}"><iframe src="{html.escape(tt)}" '
                f'allow="autoplay; encrypted-media" allowfullscreen></iframe></div>',
                unsafe_allow_html=True,
            )
            return
        if direct_media_url(url):
            st.markdown(
                f'<div class="{klass}"><video src="{html.escape(url)}" '
                f'controls playsinline></video></div>',
                unsafe_allow_html=True,
            )
            return
        st.markdown(
            f'<div class="{klass}"><div class="video-empty">'
            f'<span class="emoji">🔗</span>Ссылка принята.<br/>'
            f'Поддерживаются YouTube, TikTok и прямые mp4-ссылки.</div></div>',
            unsafe_allow_html=True,
        )
        return

    if file_bytes:
        ext = (file_name or "").lower().rsplit(".", 1)[-1] if file_name else ""
        if ext in {"mp3", "wav", "m4a", "flac", "ogg"}:
            st.audio(file_bytes)
            return
        mime = {
            "mp4": "video/mp4", "webm": "video/webm",
            "mov": "video/quicktime", "mkv": "video/x-matroska",
            "m4v": "video/mp4",
        }.get(ext, "video/mp4")
        b64 = base64.b64encode(file_bytes).decode("ascii")
        st.markdown(
            f'<div class="{klass}"><video controls playsinline>'
            f'<source src="data:{mime};base64,{b64}" type="{mime}"></video></div>',
            unsafe_allow_html=True,
        )
        return

    st.markdown(
        f'<div class="{klass}"><div class="video-empty">'
        f'<span class="emoji">{placeholder_emoji}</span>{placeholder_text}'
        f'</div></div>',
        unsafe_allow_html=True,
    )


def try_download_via_ytdlp(url: str) -> Optional[bytes]:
    try:
        from yt_dlp import YoutubeDL  # type: ignore
    except Exception:
        return None
    try:
        target_dir = Path(tempfile.gettempdir()) / "murat_ai_preview"
        target_dir.mkdir(parents=True, exist_ok=True)
        out = str(target_dir / f"{uuid.uuid4().hex}.%(ext)s")
        opts = {
            "outtmpl": out,
            "format": "best[ext=mp4][vcodec!=none][acodec!=none]/best",
            "noplaylist": True, "quiet": True, "no_warnings": True,
            "socket_timeout": 30, "retries": 1,
        }
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            path = ydl.prepare_filename(info)
            mp4 = Path(path).with_suffix(".mp4")
            chosen = mp4 if mp4.exists() else Path(path)
            return chosen.read_bytes() if chosen.exists() else None
    except Exception:
        return None


def apply_rules(text: str) -> str:
    out = text
    for r in st.session_state.rules:
        a = (r.get("from") or "").strip()
        b = (r.get("to") or "").strip()
        if a and b:
            out = re.sub(re.escape(a), b, out, flags=re.IGNORECASE)
    return out


def translate_preview(text: str, src: str, tgt: str) -> str:
    if not text.strip():
        return ""
    base = SAMPLE_TRANSLATIONS.get((src, tgt), text)
    return apply_rules(base)


def make_srt(text: str) -> str:
    lines = [s.strip() for s in text.splitlines() if s.strip()] or ["Murat AI preview"]
    blocks, sec = [], 0
    for i, line in enumerate(lines, 1):
        a, b = f"00:00:{sec:02d},000", f"00:00:{sec + 4:02d},000"
        blocks.append(f"{i}\n{a} --> {b}\n{line}\n")
        sec += 4
    return "\n".join(blocks)


def make_vtt(text: str) -> str:
    lines = [s.strip() for s in text.splitlines() if s.strip()] or ["Murat AI preview"]
    out = ["WEBVTT", ""]
    sec = 0
    for line in lines:
        a, b = f"00:00:{sec:02d}.000", f"00:00:{sec + 4:02d}.000"
        out.append(f"{a} --> {b}"); out.append(line); out.append("")
        sec += 4
    return "\n".join(out)


def speak_button(
    text: str, lang: str, voice: str, profile: EmotionProfile,
    extra_tempo: float, extra_pitch: float, extra_volume: float, key: str,
) -> None:
    """Browser Web Speech API player — реальный звук, использует EmotionProfile."""
    browser_lang = {"ru": "ru-RU", "tk": "tr-TR", "tr": "tr-TR", "en": "en-US"}.get(lang, "ru-RU")
    rate = profile.speed * extra_tempo
    pitch = profile.pitch * extra_pitch
    volume = profile.volume * extra_volume
    voice_l = voice.lower()
    if "женский" in voice_l or "детский" in voice_l:
        pitch *= 1.10
    elif "мужской" in voice_l and "подрост" not in voice_l:
        pitch *= 0.94
    if "кино" in voice_l or "драматич" in voice_l:
        rate *= 0.94
        pitch *= 0.96

    is_turkmen = lang == "tk"
    safe_text = json.dumps(text or "Текста нет.")

    components.html(
        f"""
        <div style="font-family:Inter,Arial,sans-serif;">
            <button id="play-{key}" style="background:linear-gradient(135deg,#7c3aed,#06b6d4);
                color:#fff;border:0;border-radius:12px;padding:11px 18px;font-weight:800;
                cursor:pointer;font-size:14px;">▶ Прослушать</button>
            <button id="stop-{key}" style="margin-left:8px;background:#1f2937;color:#fff;
                border:1px solid #374151;border-radius:12px;padding:11px 18px;font-weight:700;
                cursor:pointer;font-size:14px;">■ Стоп</button>
            <div style="margin-top:10px;color:#94a3b8;font-size:12px;line-height:1.5;">
                <b style="color:#cbd5e1;">{html.escape(voice)}</b> · {html.escape(profile.emotion)}<br/>
                speed {rate:.2f} · pitch {pitch:.2f} · energy {profile.energy:.2f}
                · pause {profile.pause:.2f} · volume {volume:.2f}
                {('<br/><span style="color:#fcd34d;">Туркменский в preview звучит через tr-TR. Реальный голос даст backend ' + TURKMEN_TTS_BACKEND + '.</span>') if is_turkmen else ''}
            </div>
        </div>
        <script>
        (function() {{
            const text = {safe_text};
            const lang = "{browser_lang}";
            const rate = {rate};
            const pitch = {pitch};
            const volume = {volume};
            function speak() {{
                window.speechSynthesis.cancel();
                const u = new SpeechSynthesisUtterance(text);
                u.lang = lang; u.rate = rate; u.pitch = pitch; u.volume = volume;
                const voices = window.speechSynthesis.getVoices();
                const v = voices.find(x => x.lang &&
                          x.lang.toLowerCase().startsWith(lang.slice(0,2).toLowerCase()));
                if (v) u.voice = v;
                window.speechSynthesis.speak(u);
            }}
            document.getElementById('play-{key}').onclick = speak;
            document.getElementById('stop-{key}').onclick =
                () => window.speechSynthesis.cancel();
        }})();
        </script>
        """,
        height=150,
    )


# ===========================================================================
# BUILD banner + Hero
# ===========================================================================

st.markdown(
    f"<div class='build-banner'>🔧 {BUILD_BANNER}</div>",
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class='hero'>
      <h1>🌐 Murat AI</h1>
      <div class='tag'>Перевод · озвучка · дубляж видео на русском, туркменском, турецком и английском</div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ===========================================================================
# Settings card
# ===========================================================================

with st.container():
    st.markdown("<div class='card'><div class='card-title'>⚙️ Настройки проекта</div>",
                unsafe_allow_html=True)

    r1 = st.columns([1.3, 1.0, 1.0, 1.0, 1.0, 1.4])
    with r1[0]:
        fmt_label = st.selectbox("Формат видео", list(FORMATS.keys()), index=0)
    with r1[1]:
        quality = st.selectbox("Качество", QUALITIES, index=0)
    with r1[2]:
        source_lang = st.selectbox("С языка", LANGS, index=0,
                                    format_func=lambda x: LANG_LABELS[x])
    with r1[3]:
        target_lang = st.selectbox("На язык", LANGS, index=1,
                                    format_func=lambda x: LANG_LABELS[x])
    with r1[4]:
        voice_main = st.selectbox("Голос", VOICES, index=3)
    with r1[5]:
        st.session_state.emotion_mode = st.selectbox(
            "Эмоция",
            EMOTIONS_ALL,
            index=EMOTIONS_ALL.index(st.session_state.emotion_mode)
            if st.session_state.emotion_mode in EMOTIONS_ALL else 0,
            help="«🤖 Автоматически по оригиналу» — система сама определит эмоцию по тексту/аудио/видео.",
        )

    r2 = st.columns([1.0, 1.0, 1.0, 1.0, 1.0, 1.0])
    with r2[0]:
        tempo = st.slider("Темп речи", 0.6, 1.6, 1.0, 0.05)
    with r2[1]:
        pitch_user = st.slider("Высота голоса", 0.6, 1.6, 1.0, 0.05)
    with r2[2]:
        volume = st.slider("Громкость", 0.1, 1.0, 1.0, 0.05)
    with r2[3]:
        fit_timing = st.checkbox("Подогнать текст под тайминг", value=True)
    with r2[4]:
        clean_noise = st.checkbox("Очистить шум / эхо", value=True)
    with r2[5]:
        preserve_quality = st.checkbox("Сохранить качество исходника", value=True)

    st.markdown("</div>", unsafe_allow_html=True)

aspect_css, frame_max_width, fmt_class = FORMATS[fmt_label]
inject_css(aspect_css, frame_max_width)


# ===========================================================================
# Compute effective EmotionProfile
# ===========================================================================


def compute_effective_emotion() -> EmotionProfile:
    """Главный режим эмоции (без учёта актёрских ролей)."""
    if st.session_state.emotion_mode == EMOTION_AUTO:
        # Источник анализа: видео → audio → text (в preview всё сводится к тексту).
        if st.session_state.source_file_bytes:
            name = (st.session_state.source_file_name or "").lower()
            if name.endswith((".mp3", ".wav", ".m4a", ".flac", ".ogg")):
                prof = analyze_audio_emotion(st.session_state.source_file_bytes,
                                              language=source_lang)
            else:
                prof = analyze_video_emotion(st.session_state.source_file_bytes,
                                              language=source_lang)
            # В preview всё равно дополняем разбором текста, если он есть.
            if st.session_state.source_text.strip():
                text_prof = analyze_text_emotion(st.session_state.source_text,
                                                  language=source_lang)
                if text_prof.confidence > prof.confidence:
                    prof = text_prof
            return prof
        return analyze_text_emotion(st.session_state.source_text, language=source_lang)
    clean = clean_emotion_label(st.session_state.emotion_mode)
    return profile_for_emotion(clean, confidence=1.0, source="manual", language=source_lang)


effective_profile = compute_effective_emotion()
st.session_state.emotion_profile = effective_profile.to_dict()


# ===========================================================================
# Original analysis panel — shown when in auto mode
# ===========================================================================


def render_analysis_panel(profile: EmotionProfile) -> None:
    is_auto = st.session_state.emotion_mode == EMOTION_AUTO
    badge_text = "🤖 авто-режим" if is_auto else "✋ выбрано вручную"
    badge_class = "pill ok" if is_auto else "pill mute"

    st.markdown(
        "<div class='card'><div class='card-title'>📊 Анализ оригинала</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<span class='{badge_class}'>{badge_text}</span>"
        f"<span class='pill'>эмоция: {html.escape(profile.emotion)}</span>"
        f"<span class='pill mute'>источник: {html.escape(profile.source)}</span>"
        f"<span class='pill mute'>язык: {html.escape(LANG_LABELS.get(profile.language, profile.language))}</span>"
        f"<span class='pill mute'>спикеры: {len(st.session_state.actors)}</span>",
        unsafe_allow_html=True,
    )

    metrics = [
        ("Темп речи", profile.speed, "× от обычного"),
        ("Высота", profile.pitch, "× от обычной"),
        ("Энергия", profile.energy, ""),
        ("Паузы", profile.pause, "× от обычных"),
        ("Громкость", profile.volume, ""),
        ("Уверенность", profile.confidence, ""),
    ]
    for label, val, suffix in metrics:
        bar = min(max(val, 0.0), 1.6) / 1.6 * 100
        st.markdown(
            f"<div class='metric-row'>"
            f"<div class='metric-label'>{html.escape(label)}</div>"
            f"<div class='metric-track'><div class='metric-fill' style='width:{bar:.1f}%'></div></div>"
            f"<div class='metric-value'>{val:.2f} {html.escape(suffix)}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    # Per-actor analysis (text-only preview)
    if st.session_state.translated_text or st.session_state.source_text:
        with st.expander("Реплики и эмоции актёров (preview)", expanded=False):
            for i, actor in enumerate(st.session_state.actors):
                # Pretend each actor takes the i-th paragraph of source text.
                paragraphs = [p.strip() for p in
                              re.split(r"[\n\.\!\?]+", st.session_state.source_text)
                              if p.strip()]
                line = paragraphs[i % max(len(paragraphs), 1)] if paragraphs else ""
                actor_profile = analyze_text_emotion(line, language=source_lang,
                                                      actor_id=f"actor_{i + 1}")
                st.markdown(
                    f"<b>{html.escape(actor['role'])}</b>: "
                    f"<span class='pill'>{html.escape(actor_profile.emotion)}</span> "
                    f"<span class='pill mute'>уверенность {actor_profile.confidence:.0%}</span>"
                    f"<br/><span style='color:#94a3b8;font-size:13px'>"
                    f"{html.escape(line[:140]) + ('…' if len(line) > 140 else '')}</span>",
                    unsafe_allow_html=True,
                )

    st.caption(
        "В preview анализ работает по ключевым словам в тексте. "
        "В полном режиме на VPS подключаются модели эмоции по аудио/видео "
        f"и сохраняют эмоции по каждому актёру и реплике. Туркменский голос "
        f"использует backend `{TURKMEN_TTS_BACKEND}` с post-processing через "
        "speed / pitch / energy / pause / volume."
    )
    st.markdown("</div>", unsafe_allow_html=True)


render_analysis_panel(effective_profile)


# ===========================================================================
# Ряд 1 — Исходное видео ↔ Готовое видео
# ===========================================================================

col_src, col_out = st.columns(2, gap="large")

with col_src:
    st.markdown("<div class='card'><div class='card-title'>📥 Исходное видео</div>",
                unsafe_allow_html=True)

    render_video_frame(
        st.session_state.source_url or None,
        st.session_state.source_file_bytes, st.session_state.source_file_name,
        fmt_class=fmt_class, placeholder_emoji="🎬",
        placeholder_text="Вставь ссылку или загрузи файл —<br/>видео сразу появится здесь.",
    )

    url_in = st.text_input(
        "Ссылка на видео (YouTube / TikTok / mp4)",
        value=st.session_state.source_url,
        placeholder="https://youtube.com/shorts/...   ·   https://tiktok.com/...",
    )

    bb1, bb2 = st.columns(2)
    with bb1:
        if st.button("📺 Показать видео", type="primary", use_container_width=True):
            if url_in.strip():
                st.session_state.source_url = url_in.strip()
                st.session_state.source_file_bytes = None
                st.session_state.source_file_name = ""
                st.rerun()
    with bb2:
        if st.button("⬇️ Скачать видео по ссылке", use_container_width=True):
            if url_in.strip():
                with st.spinner("Скачиваю через yt-dlp…"):
                    data = try_download_via_ytdlp(url_in.strip())
                if data:
                    st.session_state.source_file_bytes = data
                    st.session_state.source_file_name = "downloaded.mp4"
                    st.session_state.source_url = ""
                    st.success(f"Скачано {len(data) // 1024} КБ.")
                    st.rerun()
                else:
                    st.warning(
                        "В preview-режиме прямое скачивание ограничено. "
                        "«📺 Показать видео» проигрывает ссылку inline."
                    )

    up = st.file_uploader(
        "Загрузить видео из папки",
        type=["mp4", "mov", "webm", "mkv", "m4v"],
        key="src_file_input",
    )
    if up is not None:
        st.session_state.source_file_bytes = up.read()
        st.session_state.source_file_name = up.name
        st.session_state.source_url = ""
        st.rerun()

    st.markdown(
        f"<div class='small-note'>Формат preview: <b>{html.escape(fmt_label)}</b></div>",
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

with col_out:
    st.markdown("<div class='card'><div class='card-title'>📤 Готовое видео</div>",
                unsafe_allow_html=True)

    if st.session_state.result_ready:
        render_video_frame(
            st.session_state.source_url or None,
            st.session_state.source_file_bytes, st.session_state.source_file_name,
            fmt_class=fmt_class, placeholder_emoji="✅",
            placeholder_text="Готовое видео.",
        )
    else:
        st.markdown(
            f"<div class='video-frame{' original' if fmt_class == 'original' else ''}'>"
            f"<div class='video-empty'><span class='emoji'>📦</span>"
            f"Нажми «Создать готовое видео»,<br/>результат появится здесь в формате<br/>"
            f"<b>{html.escape(fmt_label.split(' — ')[0])}</b>.</div></div>",
            unsafe_allow_html=True,
        )

    st.markdown(
        f"<div style='margin: 4px 0 12px'>"
        f"<span class='pill'>{html.escape(fmt_label.split(' — ')[0])}</span>"
        f"<span class='pill'>{html.escape(quality)}</span>"
        f"<span class='pill ok'>{html.escape(LANG_LABELS[target_lang])}</span>"
        f"<span class='pill mute'>{html.escape(voice_main)}</span>"
        f"<span class='pill mute'>эмоция: {html.escape(effective_profile.emotion)}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    if st.button("🎬 Создать готовое видео", type="primary",
                  use_container_width=True, key="generate_video"):
        if not st.session_state.translated_text:
            st.session_state.translated_text = translate_preview(
                st.session_state.source_text, source_lang, target_lang,
            )
        st.session_state.result_ready = True
        st.session_state.voice_generated = True
        st.rerun()

    placeholder_mp4 = st.session_state.source_file_bytes or b"Murat AI preview MP4 placeholder."
    srt_text = make_srt(st.session_state.translated_text or st.session_state.source_text)
    d1, d2 = st.columns(2)
    with d1:
        st.download_button("⬇️ Скачать MP4", data=placeholder_mp4,
                            file_name="murat-ai-final.mp4",
                            use_container_width=True,
                            disabled=not st.session_state.result_ready)
        st.download_button("⬇️ Скачать MP4 + SRT",
                            data=placeholder_mp4 + b"\n--SRT--\n" + srt_text.encode("utf-8"),
                            file_name="murat-ai-final-with-srt.mp4",
                            use_container_width=True,
                            disabled=not st.session_state.result_ready)
    with d2:
        st.download_button("🔊 Скачать аудио (WAV)",
                            data=b"Murat AI preview WAV placeholder.",
                            file_name="murat-ai-voiceover.wav",
                            use_container_width=True,
                            disabled=not st.session_state.result_ready)
        st.download_button("📦 Скачать ZIP пакет",
                            data=b"Murat AI preview ZIP placeholder.",
                            file_name="murat-ai-package.zip",
                            use_container_width=True,
                            disabled=not st.session_state.result_ready)
    st.markdown("</div>", unsafe_allow_html=True)


# ===========================================================================
# Ряд 2 — Аудио / мой голос ↔ Готовая озвучка
# ===========================================================================

col_vin, col_vout = st.columns(2, gap="large")

with col_vin:
    st.markdown("<div class='card'><div class='card-title'>🎤 Аудио / мой голос</div>",
                unsafe_allow_html=True)
    vs = st.file_uploader(
        "Загрузить аудио (wav / mp3 / m4a / flac / ogg)",
        type=["wav", "mp3", "m4a", "flac", "ogg"],
        key="voice_sample_input",
    )
    if vs is not None:
        st.session_state.voice_sample_bytes = vs.read()
        st.session_state.voice_sample_name = vs.name
        st.audio(st.session_state.voice_sample_bytes)
    if st.session_state.voice_sample_bytes is not None and vs is None:
        st.audio(st.session_state.voice_sample_bytes)

    cc1, cc2 = st.columns(2)
    with cc1:
        opt_noise = st.checkbox("🧹 Очистить шум", value=True)
        opt_level = st.checkbox("📐 Выровнять громкость", value=True)
    with cc2:
        opt_echo = st.checkbox("🔇 Удалить эхо", value=True)
        opt_clean_voice = st.checkbox("✨ Сделать голос чистым для озвучки", value=True)

    if st.button("💾 Создать голосовой профиль",
                  type="primary", use_container_width=True):
        if not st.session_state.voice_sample_bytes:
            st.error("Сначала загрузи аудио-образец голоса.")
        else:
            st.session_state.voice_profile_ready = True
            st.success(f"Профиль создан: «{html.escape(st.session_state.voice_sample_name or 'мой голос')}».")
    if st.session_state.voice_profile_ready:
        st.markdown(
            "<span class='pill ok'>профиль готов</span>"
            f"<span class='pill mute'>шум: {'убран' if opt_noise else 'нет'}</span>"
            f"<span class='pill mute'>эхо: {'убрано' if opt_echo else 'нет'}</span>",
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)

with col_vout:
    st.markdown("<div class='card'><div class='card-title'>🔊 Готовая озвучка</div>",
                unsafe_allow_html=True)

    if st.button("🎙 Создать озвучку", type="primary",
                  use_container_width=True, key="generate_voice"):
        if not st.session_state.translated_text:
            st.session_state.translated_text = translate_preview(
                st.session_state.source_text, source_lang, target_lang,
            )
        st.session_state.voice_generated = True
        st.rerun()

    preview_text = (st.session_state.translated_text
                     or SAMPLE_TRANSLATIONS.get((source_lang, target_lang),
                                                  st.session_state.source_text))
    target_profile = EmotionProfile(
        **{**effective_profile.to_dict(),
           "language": target_lang},
    )
    speak_button(preview_text, target_lang, voice_main, target_profile,
                  extra_tempo=tempo, extra_pitch=pitch_user, extra_volume=volume,
                  key="voice_top")

    if voice_main == "⭐ Мой загруженный голос":
        st.info(
            "Голос остаётся ваш загруженный — эмоция берётся из анализа оригинала "
            "(см. блок «Анализ оригинала»). В полном режиме voice-cloning backend "
            "применит ваш голос с эмоцией оригинала."
        )

    if target_lang == "tk":
        st.caption(
            f"Туркменский голос на VPS использует backend `{TURKMEN_TTS_BACKEND}` "
            "(Meta MMS-TTS / VITS) с управлением эмоциями через "
            "speed / pitch / energy / pause / volume."
        )

    st.download_button(
        "⬇️ Скачать озвучку (WAV)",
        data=b"Murat AI preview WAV placeholder.",
        file_name="murat-ai-voiceover.wav",
        use_container_width=True,
        disabled=not st.session_state.voice_generated,
    )
    st.download_button(
        "⬇️ Скачать озвучку (MP3)",
        data=b"Murat AI preview MP3 placeholder.",
        file_name="murat-ai-voiceover.mp3",
        use_container_width=True,
        disabled=not st.session_state.voice_generated,
    )
    st.markdown("</div>", unsafe_allow_html=True)


# ===========================================================================
# Ряд 3 — Текст / сценарий ↔ Готовый перевод / субтитры
# ===========================================================================

col_tin, col_tout = st.columns(2, gap="large")

with col_tin:
    st.markdown("<div class='card'><div class='card-title'>📝 Текст / сценарий / субтитры</div>",
                unsafe_allow_html=True)
    text_in = st.text_area(
        "Текст для перевода и озвучки",
        value=st.session_state.source_text,
        height=200, label_visibility="collapsed",
    )
    st.session_state.source_text = text_in
    bb1, bb2, bb3 = st.columns(3)
    with bb1:
        if st.button("🌐 Перевести текст", type="primary",
                      use_container_width=True, key="tr_text"):
            st.session_state.translated_text = preserve_emotion_in_translation(
                text_in,
                translate_preview(text_in, source_lang, target_lang),
                effective_profile,
            )
            st.rerun()
    with bb2:
        if st.button("🔊 Озвучить текст", use_container_width=True, key="tr_voice"):
            if not st.session_state.translated_text:
                st.session_state.translated_text = translate_preview(
                    text_in, source_lang, target_lang,
                )
            st.session_state.voice_generated = True
            st.rerun()
    with bb3:
        if st.button("🎬 Текст → видео", use_container_width=True, key="tr_video"):
            if not st.session_state.translated_text:
                st.session_state.translated_text = translate_preview(
                    text_in, source_lang, target_lang,
                )
            st.session_state.result_ready = True
            st.session_state.voice_generated = True
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

with col_tout:
    st.markdown("<div class='card'><div class='card-title'>✅ Готовый перевод / субтитры</div>",
                unsafe_allow_html=True)
    result_text = st.text_area(
        "Готовый перевод",
        value=st.session_state.translated_text,
        height=200, label_visibility="collapsed",
        key="result_text_area",
    )
    st.session_state.translated_text = result_text
    dl_t1, dl_t2, dl_t3 = st.columns(3)
    with dl_t1:
        st.download_button("⬇️ Скачать TXT",
                            data=result_text or "Murat AI preview",
                            file_name="murat-ai.txt",
                            use_container_width=True)
    with dl_t2:
        st.download_button("⬇️ Скачать SRT",
                            data=make_srt(result_text or text_in),
                            file_name="murat-ai.srt",
                            use_container_width=True)
    with dl_t3:
        st.download_button("⬇️ Скачать VTT",
                            data=make_vtt(result_text or text_in),
                            file_name="murat-ai.vtt",
                            use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)


# ===========================================================================
# Ряд 4 — Роли актёров / голоса
# ===========================================================================

st.markdown("<div class='card'><div class='card-title'>🎭 Роли и голоса в видео</div>",
            unsafe_allow_html=True)
st.caption(
    "Список ролей (актёров) в исходном видео. Для каждой можно выбрать готовый "
    "голос, режим эмоции и заменить голос на «Мой загруженный голос» или "
    "загрузить отдельный голос именно для этой роли."
)

cnt_col1, cnt_col2 = st.columns([1, 5])
with cnt_col1:
    desired_count = st.number_input("Сколько голосов / актёров",
                                     min_value=1, max_value=12,
                                     value=len(st.session_state.actors), step=1)
while len(st.session_state.actors) < desired_count:
    n = len(st.session_state.actors) + 1
    st.session_state.actors.append({
        "role": f"Актёр {n}", "voice": "👨 Мужской",
        "emotion_mode": ACTOR_EMOTION_MODES[0],
        "replace_mode": "Не заменять", "sample_name": "",
    })
while len(st.session_state.actors) > desired_count:
    st.session_state.actors.pop()


def actor_effective_profile(actor: dict, idx: int) -> EmotionProfile:
    mode = actor.get("emotion_mode", ACTOR_EMOTION_MODES[0])
    if mode == "🤖 Автоматически по реплике":
        paragraphs = [p.strip() for p in
                      re.split(r"[\n\.\!\?]+", st.session_state.source_text)
                      if p.strip()]
        line = paragraphs[idx % max(len(paragraphs), 1)] if paragraphs else ""
        return analyze_text_emotion(line, language=source_lang,
                                      actor_id=f"actor_{idx + 1}")
    if mode == "🤖 Автоматически по оригиналу":
        prof = EmotionProfile(**effective_profile.to_dict())
        prof.actor_id = f"actor_{idx + 1}"
        return prof
    clean = clean_emotion_label(mode)
    return profile_for_emotion(clean, confidence=1.0, source="manual",
                                language=source_lang,
                                actor_id=f"actor_{idx + 1}")


actor_profiles: List[EmotionProfile] = []

for i, actor in enumerate(st.session_state.actors):
    with st.container():
        st.markdown("<div class='actor-card'>", unsafe_allow_html=True)
        r1c = st.columns([1.0, 1.4, 1.4, 1.2, 1.0])
        with r1c[0]:
            actor["role"] = st.text_input(
                "Название роли", value=actor["role"], key=f"actor_role_{i}",
            )
        with r1c[1]:
            actor["voice"] = st.selectbox(
                "Голос", VOICES,
                index=VOICES.index(actor["voice"]) if actor["voice"] in VOICES else 3,
                key=f"actor_voice_{i}",
            )
        with r1c[2]:
            actor["emotion_mode"] = st.selectbox(
                "Эмоция роли", ACTOR_EMOTION_MODES,
                index=ACTOR_EMOTION_MODES.index(actor["emotion_mode"])
                if actor["emotion_mode"] in ACTOR_EMOTION_MODES else 0,
                key=f"actor_emo_{i}",
            )
        with r1c[3]:
            actor["replace_mode"] = st.selectbox(
                "Заменить голос на", REPLACE_MODES,
                index=REPLACE_MODES.index(actor["replace_mode"])
                if actor["replace_mode"] in REPLACE_MODES else 0,
                key=f"actor_replace_{i}",
            )
        with r1c[4]:
            ap = actor_effective_profile(actor, i)
            actor_profiles.append(ap)
            line_text = (st.session_state.translated_text
                          or SAMPLE_TRANSLATIONS.get((source_lang, target_lang),
                                                       st.session_state.source_text))
            target_prof_actor = EmotionProfile(**{**ap.to_dict(),
                                                    "language": target_lang})
            speak_button(line_text, target_lang, actor["voice"], target_prof_actor,
                          extra_tempo=tempo, extra_pitch=pitch_user, extra_volume=volume,
                          key=f"actor_{i}")
        # show resolved emotion
        st.markdown(
            f"<span class='pill ok'>эффективная эмоция: "
            f"{html.escape(ap.emotion)} · {ap.confidence:.0%}</span>",
            unsafe_allow_html=True,
        )
        if actor["replace_mode"] == "🎤 Другой голос (см. ниже)":
            up_actor = st.file_uploader(
                f"Загрузить отдельный голос для роли «{actor['role']}»",
                type=["wav", "mp3", "m4a", "flac", "ogg"],
                key=f"actor_upload_{i}",
            )
            if up_actor is not None:
                actor["sample_name"] = up_actor.name
                st.audio(up_actor.read())
                st.success(f"Голос для роли «{actor['role']}» принят.")
        st.markdown("</div>", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)


# ===========================================================================
# Ряд 5 — Замена слов
# ===========================================================================

st.markdown("<div class='card'><div class='card-title'>📚 Замена слов в переводе</div>",
            unsafe_allow_html=True)
st.caption(
    "Запоминаем правила. Каждый раз, когда AI делает перевод, эти замены "
    "применяются автоматически. Пример: «машина» → «автомобиль»."
)

w1, w2, w3, w4 = st.columns([1.5, 1.5, 1.4, 0.9])
with w1:
    st.session_state.replace_from = st.text_input(
        "Какое слово заменить",
        value=st.session_state.replace_from,
        placeholder="старое слово",
    )
with w2:
    st.session_state.replace_to = st.text_input(
        "На что заменить",
        value=st.session_state.replace_to,
        placeholder="новое слово",
    )
with w3:
    st.session_state.replace_scope = st.selectbox(
        "Область действия", REPLACE_SCOPES,
        index=REPLACE_SCOPES.index(st.session_state.replace_scope)
        if st.session_state.replace_scope in REPLACE_SCOPES else 0,
    )
with w4:
    st.markdown("<div style='margin-top:30px'></div>", unsafe_allow_html=True)
    if st.button("💾 Сохранить замену", use_container_width=True, type="primary"):
        if st.session_state.replace_from.strip() and st.session_state.replace_to.strip():
            st.session_state.rules.append({
                "from": st.session_state.replace_from,
                "to": st.session_state.replace_to,
                "scope": st.session_state.replace_scope,
            })
            st.session_state.translated_text = apply_rules(st.session_state.translated_text)
            st.session_state.replace_from = ""
            st.session_state.replace_to = ""
            st.rerun()

if st.session_state.rules:
    table_rows = [{"Старое слово": r["from"],
                    "Новое слово": r["to"],
                    "Область": r.get("scope", REPLACE_SCOPES[0])}
                   for r in st.session_state.rules]
    st.dataframe(table_rows, use_container_width=True, hide_index=True)
    if st.button("🗑 Очистить все замены"):
        st.session_state.rules = []
        st.rerun()
else:
    st.caption("Замен пока нет. Заполни поля выше и нажми «Сохранить замену».")

st.markdown("</div>", unsafe_allow_html=True)


# ===========================================================================
# Ряд 6 — Каталог голосов (карточки)
# ===========================================================================

VOICE_CATALOG: List[Dict] = [
    {"id": "boy_6_8_soft", "name": "Мальчик 6–8 — мягкий, спокойный",
     "lang": "ru", "age": "ребёнок", "gender": "мальчик", "style": "мягкий",
     "emotions": ["🙂 Нейтрально", "🧘 Спокойно", "❤️ Добрый тон", "🌟 Сказочный тон"],
     "use": ["детский контент", "сказка", "аудиокнига"]},
    {"id": "boy_9_12_energetic", "name": "Мальчик 9–12 — энергичный",
     "lang": "ru", "age": "ребёнок", "gender": "мальчик", "style": "энергичный",
     "emotions": ["😄 Радостно", "⚡ Энергично", "😲 Удивление", "😨 Волнение"],
     "use": ["Shorts", "детский контент", "реклама"]},
    {"id": "girl_6_8_tender", "name": "Девочка 6–8 — нежная",
     "lang": "ru", "age": "ребёнок", "gender": "девочка", "style": "нежная",
     "emotions": ["❤️ Добрый тон", "🌟 Сказочный тон", "🧘 Спокойно"],
     "use": ["сказка", "детский контент"]},
    {"id": "girl_9_12_happy", "name": "Девочка 9–12 — радостная",
     "lang": "ru", "age": "ребёнок", "gender": "девочка", "style": "радостная",
     "emotions": ["😄 Радостно", "⚡ Энергично", "🌟 Сказочный тон"],
     "use": ["Shorts", "реклама"]},
    {"id": "teen_blogger", "name": "Подросток — блогерский",
     "lang": "ru", "age": "подросток", "gender": "нейтральный", "style": "блогерский",
     "emotions": ["😄 Радостно", "⚡ Энергично", "😲 Удивление"],
     "use": ["YouTube", "Shorts", "Reels"]},
    {"id": "male_cinema", "name": "Мужской — кино-диктор",
     "lang": "ru", "age": "взрослый", "gender": "мужской", "style": "кино",
     "emotions": ["🎭 Кино-драма", "🎯 Серьёзно", "🧘 Спокойно", "😱 Страх"],
     "use": ["кино", "дубляж", "аудиокнига"]},
    {"id": "male_documentary", "name": "Мужской — документальный",
     "lang": "ru", "age": "взрослый", "gender": "мужской", "style": "документальный",
     "emotions": ["🎯 Серьёзно", "🧘 Спокойно", "❤️ Добрый тон"],
     "use": ["новости", "документальное"]},
    {"id": "female_soft", "name": "Женский — мягкий",
     "lang": "ru", "age": "взрослый", "gender": "женский", "style": "мягкий",
     "emotions": ["❤️ Добрый тон", "🧘 Спокойно", "🌟 Сказочный тон"],
     "use": ["аудиокнига", "детский контент"]},
    {"id": "female_blogger", "name": "Женский — блогерский",
     "lang": "ru", "age": "взрослый", "gender": "женский", "style": "блогерский",
     "emotions": ["😄 Радостно", "⚡ Энергично", "💎 Рекламный тон"],
     "use": ["YouTube", "Shorts", "реклама"]},
    {"id": "tk_male_clean", "name": "Туркменский мужской — чистый",
     "lang": "tk", "age": "взрослый", "gender": "мужской", "style": "чистый",
     "emotions": ["🙂 Нейтрально", "🎯 Серьёзно", "🧘 Спокойно", "❤️ Добрый тон"],
     "use": ["новости", "дубляж", "культурный контент"]},
    {"id": "tk_female_clean", "name": "Туркменский женский — чистый",
     "lang": "tk", "age": "взрослый", "gender": "женский", "style": "чистый",
     "emotions": ["🙂 Нейтрально", "❤️ Добрый тон", "🧘 Спокойно", "🌟 Сказочный тон"],
     "use": ["дубляж", "аудиокнига"]},
    {"id": "tk_anchor", "name": "Туркменский диктор",
     "lang": "tk", "age": "взрослый", "gender": "нейтральный", "style": "новостной",
     "emotions": ["🎯 Серьёзно", "🧘 Спокойно"],
     "use": ["новости", "официальное"]},
    {"id": "tk_cultural", "name": "Туркменский — культурный стиль",
     "lang": "tk", "age": "взрослый", "gender": "нейтральный", "style": "культурный",
     "emotions": ["❤️ Добрый тон", "🧘 Спокойно", "🌟 Сказочный тон"],
     "use": ["культурный контент", "образование"]},
    {"id": "tk_dramatic", "name": "Туркменский — кино-дубляж",
     "lang": "tk", "age": "взрослый", "gender": "мужской", "style": "драматичный",
     "emotions": ["🎭 Кино-драма", "😱 Страх", "🎯 Серьёзно"],
     "use": ["кино", "дубляж"]},
    {"id": "en_male_news", "name": "English male — news",
     "lang": "en", "age": "взрослый", "gender": "мужской", "style": "новостной",
     "emotions": ["🎯 Серьёзно", "🧘 Спокойно"],
     "use": ["news", "documentary"]},
    {"id": "en_female_natural", "name": "English female — natural",
     "lang": "en", "age": "взрослый", "gender": "женский", "style": "естественный",
     "emotions": ["🙂 Нейтрально", "❤️ Добрый тон", "😄 Радостно"],
     "use": ["blog", "YouTube"]},
    {"id": "tr_male_confident", "name": "Türkçe erkek — kendinden emin",
     "lang": "tr", "age": "взрослый", "gender": "мужской", "style": "уверенный",
     "emotions": ["💪 Уверенно" if "💪 Уверенно" in EMOTIONS_MANUAL else "🎯 Серьёзно",
                  "🎯 Серьёзно", "🧘 Спокойно"],
     "use": ["новости", "образование"]},
    {"id": "custom_my_voice", "name": "⭐ Мой загруженный голос",
     "lang": "auto", "age": "любой", "gender": "пользователь", "style": "клонированный",
     "emotions": ["🤖 Автоматически по оригиналу"],
     "use": ["любой контент"], "is_custom": True},
]

if "selected_catalog_voice" not in st.session_state:
    st.session_state.selected_catalog_voice = "male_cinema"
if "catalog_filter_lang" not in st.session_state:
    st.session_state.catalog_filter_lang = "все"
if "catalog_filter_age" not in st.session_state:
    st.session_state.catalog_filter_age = "все"
if "catalog_search" not in st.session_state:
    st.session_state.catalog_search = ""

st.markdown("<div class='card'><div class='card-title'>🎙️ Каталог голосов</div>",
            unsafe_allow_html=True)
st.caption(
    "Конкретные голосовые профили вместо общих «Детский / Мужской». "
    "Прослушай пример, выбери голос — он станет основным и появится в "
    "выпадашке голоса актёров (выше) и в верхней панели настроек."
)

# ---- filters ----
fl1, fl2, fl3 = st.columns([1, 1, 2])
with fl1:
    st.session_state.catalog_filter_lang = st.selectbox(
        "Язык", ["все", "ru", "tk", "tr", "en", "auto"],
        index=["все", "ru", "tk", "tr", "en", "auto"].index(
            st.session_state.catalog_filter_lang
        ) if st.session_state.catalog_filter_lang in
           ["все", "ru", "tk", "tr", "en", "auto"] else 0,
        format_func=lambda c: "все" if c == "все"
        else ("любой (свой)" if c == "auto" else LANG_LABELS.get(c, c)),
        key="cat_lang_select",
    )
with fl2:
    st.session_state.catalog_filter_age = st.selectbox(
        "Возраст", ["все", "ребёнок", "подросток", "взрослый"],
        index=["все", "ребёнок", "подросток", "взрослый"].index(
            st.session_state.catalog_filter_age
        ) if st.session_state.catalog_filter_age in
           ["все", "ребёнок", "подросток", "взрослый"] else 0,
        key="cat_age_select",
    )
with fl3:
    st.session_state.catalog_search = st.text_input(
        "Поиск по названию",
        value=st.session_state.catalog_search,
        placeholder="например: туркменский, кино, блогер",
        key="cat_search_input",
    )


def voice_matches(v: Dict) -> bool:
    if st.session_state.catalog_filter_lang != "все" \
            and v["lang"] != st.session_state.catalog_filter_lang:
        return False
    if st.session_state.catalog_filter_age != "все" \
            and v["age"] != st.session_state.catalog_filter_age:
        return False
    q = st.session_state.catalog_search.strip().lower()
    if q and q not in v["name"].lower() and q not in v.get("style", "").lower():
        if not any(q in u.lower() for u in v.get("use", [])):
            return False
    return True


CATALOG_SAMPLE = {
    "ru": "Привет, это пример моего голоса для озвучки видео.",
    "tk": "Salam, bu wideony seslendirmek üçin ses nusgasydyr.",
    "tr": "Merhaba, bu video seslendirme için örnek sestir.",
    "en": "Hello, this is a sample voice for video dubbing.",
}

filtered = [v for v in VOICE_CATALOG if voice_matches(v)]
if not filtered:
    st.info("Под фильтры не подошёл ни один голос. Очистите поиск или измените фильтры.")
else:
    # 3 cards per row
    for chunk_start in range(0, len(filtered), 3):
        cols_v = st.columns(3, gap="medium")
        for j, v in enumerate(filtered[chunk_start:chunk_start + 3]):
            with cols_v[j]:
                selected_class = (
                    "border:2px solid #06b6d4; box-shadow:0 8px 24px rgba(6,182,212,.30);"
                    if v["id"] == st.session_state.selected_catalog_voice else ""
                )
                st.markdown(
                    f"<div class='actor-card' style='{selected_class} min-height:230px;'>"
                    f"<div style='font-weight:800;color:#fff;font-size:15px;margin-bottom:8px'>"
                    f"{html.escape(v['name'])}"
                    f"{' ✓' if v['id'] == st.session_state.selected_catalog_voice else ''}"
                    f"</div>"
                    f"<div style='margin-bottom:6px'>"
                    f"<span class='pill mute'>{html.escape(LANG_LABELS.get(v['lang'], v['lang']))}</span>"
                    f"<span class='pill mute'>{html.escape(v['age'])}</span>"
                    f"<span class='pill mute'>{html.escape(v['gender'])}</span>"
                    f"</div>"
                    f"<div style='color:#94a3b8;font-size:12px;margin-bottom:6px'>"
                    f"стиль: {html.escape(v['style'])}<br/>"
                    f"подходит: {html.escape(', '.join(v.get('use', [])))}<br/>"
                    f"эмоции: {html.escape(', '.join(v.get('emotions', [])))}"
                    f"</div></div>",
                    unsafe_allow_html=True,
                )
                # Speak sample.
                sample_lang = v["lang"] if v["lang"] != "auto" else target_lang
                sample_text = CATALOG_SAMPLE.get(sample_lang, CATALOG_SAMPLE["ru"])
                sample_prof = profile_for_emotion(
                    "Нейтрально", confidence=1.0, source="catalog", language=sample_lang,
                )
                speak_button(
                    sample_text, sample_lang, v["name"], sample_prof,
                    extra_tempo=tempo, extra_pitch=pitch_user, extra_volume=volume,
                    key=f"cat_{v['id']}",
                )
                if st.button("✓ Выбрать этот голос", use_container_width=True,
                              key=f"cat_pick_{v['id']}",
                              type="primary" if v["id"] != st.session_state.selected_catalog_voice
                              else "secondary"):
                    st.session_state.selected_catalog_voice = v["id"]
                    st.toast(f"Выбран голос: {v['name']}")
                    st.rerun()

# Surface the selected voice as a status pill near the bottom of the card.
sel = next((v for v in VOICE_CATALOG
            if v["id"] == st.session_state.selected_catalog_voice), VOICE_CATALOG[0])
st.markdown(
    f"<div style='margin-top:10px'>"
    f"<span class='pill ok'>Выбран: {html.escape(sel['name'])}</span>"
    f"<span class='pill mute'>{html.escape(LANG_LABELS.get(sel['lang'], sel['lang']))}</span>"
    f"<span class='pill mute'>стиль: {html.escape(sel['style'])}</span>"
    f"</div>",
    unsafe_allow_html=True,
)

st.markdown("</div>", unsafe_allow_html=True)


# ===========================================================================
# Project settings JSON
# ===========================================================================

with st.expander("⚙️ Скачать настройки проекта (JSON)", expanded=False):
    actors_payload = []
    for i, a in enumerate(st.session_state.actors):
        actors_payload.append({
            "role": a["role"], "voice": a["voice"],
            "emotion_mode": a["emotion_mode"],
            "replace_mode": a["replace_mode"],
            "sample_name": a.get("sample_name", ""),
            "role_emotion_profile": actor_profiles[i].to_dict(),
        })
    project = {
        "build": {"branch": BUILD_BRANCH, "commit": BUILD_COMMIT, "date": BUILD_DATE},
        "created_at": datetime.now(timezone.utc).isoformat(),
        "format": fmt_label,
        "quality": quality,
        "source_lang": source_lang,
        "target_lang": target_lang,
        "voice": voice_main,
        "tempo": tempo, "pitch": pitch_user, "volume": volume,
        "fit_timing": fit_timing, "clean_noise": clean_noise,
        "preserve_quality": preserve_quality,
        "emotion_mode": ("auto_from_original"
                          if st.session_state.emotion_mode == EMOTION_AUTO
                          else "manual"),
        "emotion_label": st.session_state.emotion_mode,
        "emotion_profile": effective_profile.to_dict(),
        "turkmen_tts_backend": TURKMEN_TTS_BACKEND,
        "catalog_voice_id": st.session_state.get("selected_catalog_voice"),
        "catalog_voice": sel,
        "actors": actors_payload,
        "replacements": st.session_state.rules,
    }
    st.download_button(
        "💾 Скачать настройки (JSON)",
        data=json.dumps(project, ensure_ascii=False, indent=2),
        file_name="murat-ai-project.json",
        mime="application/json",
        use_container_width=True,
    )

st.markdown("---")
st.caption(
    f"Murat AI preview. Настоящий MP4 4K/8K, клонирование голоса, "
    f"анализ эмоции по аудио/видео и туркменская TTS-модель "
    f"`{TURKMEN_TTS_BACKEND}` работают на VPS / GPU backend "
    "(ветка `issue-2-ai-architecture`)."
)
