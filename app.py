"""Murat AI — Streamlit preview UI.

Один профессиональный экран без вкладок. Принцип: СЛЕВА — вход,
СПРАВА — готовый результат. Все блоки парные и одинаковой высоты.

Раскладка (соответствует утверждённому блюпринту):

  ┌─── Верхний блок настроек ─────────────────────────────────────────┐
  │  Формат · Качество · С языка · На язык · Голос · Эмоция           │
  │  Темп · Высота · Громкость · Чекбоксы (шум/эхо/тайминг/качество)  │
  └───────────────────────────────────────────────────────────────────┘

  Ряд 1   Исходное видео ──→ Готовое видео        (формат 9:16/16:9/1:1/Original)
  Ряд 2   Аудио / мой голос ──→ Готовая озвучка
  Ряд 3   Текст / сценарий ──→ Готовый перевод / субтитры
  Ряд 4   Роли актёров (на всю ширину)
  Ряд 5   Замена слов (на всю ширину)

Туркменский TTS-backend заложен под Meta MMS-TTS
``facebook/mms-tts-tuk-script_latin`` (Vits). Реальная генерация
поднимается на VPS/GPU (issue-2-ai-architecture). В preview модель не
грузится — нужен только UI и логика.
"""

from __future__ import annotations

import base64
import html
import json
import re
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import streamlit as st
import streamlit.components.v1 as components

# ---------------------------------------------------------------------------
# Streamlit page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Murat AI",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Domain constants — все опции на русском, как указано в задании
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

EMOTIONS = [
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
]

REPLACE_SCOPES = ["🌍 Глобально", "📁 Только текущий проект", "📺 Только текущий канал"]

SAMPLE_TRANSLATIONS: Dict[Tuple[str, str], str] = {
    ("ru", "tk"): "Salam. Men bu wideony arassa türkmen diline terjime edip, professional derejede seslendirmek isleýärin.",
    ("tk", "ru"): "Здравствуйте. Я хочу перевести это видео и сделать профессиональную озвучку.",
    ("ru", "en"): "Hello. I want to translate this video and make a professional voiceover.",
    ("en", "ru"): "Здравствуйте. Я хочу перевести это видео и сделать профессиональную озвучку.",
    ("ru", "tr"): "Merhaba. Bu videoyu profesyonel dublaj için çevirmek istiyorum.",
    ("tr", "ru"): "Здравствуйте. Я хочу перевести и озвучить это видео.",
}

# Backend reference shown in UI (no heavy import in preview).
TURKMEN_TTS_BACKEND = "facebook/mms-tts-tuk-script_latin"


# ---------------------------------------------------------------------------
# Session state defaults
# ---------------------------------------------------------------------------


def init_state() -> None:
    defaults = {
        # Source
        "source_url": "",
        "source_file_bytes": None,
        "source_file_name": "",
        # Result
        "result_ready": False,
        # Voice sample
        "voice_sample_bytes": None,
        "voice_sample_name": "",
        "voice_profile_ready": False,
        # Voice generation
        "voice_generated": False,
        # Text
        "source_text": "Привет. Я хочу сделать профессиональное короткое видео с переводом и озвучкой на туркменском.",
        "translated_text": "",
        # Word replacement
        "replace_from": "",
        "replace_to": "",
        "replace_scope": REPLACE_SCOPES[0],
        "rules": [],
        # Roles
        "actor_count": 2,
        "actors": [
            {"role": "Актёр 1", "voice": "👨 Мужской", "emotion": "🎭 Кино-драма",
             "replace_mode": "⭐ Мой загруженный голос", "sample_name": ""},
            {"role": "Актёр 2", "voice": "👩 Женский", "emotion": "🧘 Спокойно",
             "replace_mode": "Не заменять", "sample_name": ""},
        ],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_state()


# ---------------------------------------------------------------------------
# CSS — calm dark theme, adaptive video frames, symmetric cards
# ---------------------------------------------------------------------------


def inject_css(aspect_css: str, frame_max_width: int) -> None:
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

        html, body, [class*="css"] {{ font-family: 'Inter', -apple-system, sans-serif; }}
        .block-container {{ max-width: 1480px; padding-top: 1.4rem; padding-bottom: 4rem; }}

        /* Hero */
        .hero {{
            border-radius: 24px; padding: 22px 26px;
            background: linear-gradient(135deg, #1a1c2e 0%, #2a1e4d 60%, #0e3550 100%);
            border: 1px solid rgba(255,255,255,.10);
            margin-bottom: 18px;
        }}
        .hero h1 {{ margin: 0; font-size: 34px; font-weight: 800; color: #fff; }}
        .hero .tag {{ color: #c4b5fd; font-weight: 600; font-size: 15px; margin-top: 4px; }}

        /* Symmetric cards */
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

        /* Video frame — формат меняется через aspect_css */
        .video-frame {{
            width: 100%;
            max-width: {frame_max_width}px;
            aspect-ratio: {aspect_css};
            margin: 4px auto 16px;
            border-radius: 22px; overflow: hidden;
            background: #0b0d12;
            border: 2px solid rgba(255,255,255,.10);
            box-shadow: 0 18px 35px rgba(0,0,0,.45),
                         inset 0 0 0 1px rgba(255,255,255,.04);
            position: relative;
        }}
        .video-frame.original {{
            aspect-ratio: auto; min-height: 320px;
        }}
        .video-frame iframe, .video-frame video {{
            width: 100% !important; height: 100% !important;
            border: 0; display: block; object-fit: cover;
        }}
        .video-empty {{
            display: flex; align-items: center; justify-content: center;
            text-align: center; color: #94a3b8; font-size: 14px;
            min-height: 280px; padding: 24px; line-height: 1.5;
        }}
        .video-empty .emoji {{ font-size: 54px; display: block; margin-bottom: 14px; }}

        /* Inputs polish */
        .stTextInput input, .stTextArea textarea, .stSelectbox > div > div,
        .stMultiSelect > div > div, .stNumberInput input {{
            background: #11141b !important;
            border: 1px solid rgba(255,255,255,.10) !important;
            border-radius: 12px !important;
            color: #e5e7eb !important;
        }}
        .stButton > button {{
            border-radius: 12px !important;
            font-weight: 700 !important;
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

        /* Pills */
        .pill {{
            display: inline-block; padding: 5px 11px; border-radius: 999px;
            font-size: 12px; font-weight: 700; margin: 0 6px 6px 0;
            background: rgba(124,58,237,.18); color: #c4b5fd;
            border: 1px solid rgba(124,58,237,.30);
        }}
        .pill.ok {{ background: rgba(34,197,94,.15); color: #86efac;
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

        .small-note {{
            color: #94a3b8; font-size: 13px; margin-top: 6px;
        }}

        /* Hide Streamlit chrome */
        #MainMenu {{ visibility: hidden; }}
        footer {{ visibility: hidden; }}
        header[data-testid="stHeader"] {{ background: transparent; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Helpers — embedding video, downloading, rules, TTS
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
    url: Optional[str],
    file_bytes: Optional[bytes],
    file_name: str,
    fmt_class: str,
    placeholder_emoji: str,
    placeholder_text: str,
) -> None:
    """Render an adaptive video frame (9:16 / 16:9 / 1:1 / original)."""
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
            f'Поддерживаются YouTube, TikTok и прямые mp4-ссылки.'
            f'</div></div>',
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
            f'<source src="data:{mime};base64,{b64}" type="{mime}">'
            f'</video></div>',
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
        out.append(f"{a} --> {b}")
        out.append(line)
        out.append("")
        sec += 4
    return "\n".join(out)


def speak_button(
    text: str, lang: str, voice: str, emotion: str,
    tempo: float, pitch: float, volume: float, key: str,
) -> None:
    """Browser Web Speech API player — реальный звук без TTS-моделей."""
    browser_lang = {"ru": "ru-RU", "tk": "tr-TR", "tr": "tr-TR", "en": "en-US"}.get(lang, "ru-RU")
    rate = tempo
    p = pitch
    voice_l = voice.lower()
    if "женский" in voice_l or "детский" in voice_l:
        p *= 1.15
    elif "мужской" in voice_l and "подрост" not in voice_l:
        p *= 0.92
    if "кино" in voice_l or "драматич" in voice_l:
        rate *= 0.92; p *= 0.95
    if "грустно" in emotion.lower() or "серьёзно" in emotion.lower():
        rate *= 0.94; p *= 0.94
    if "радостно" in emotion.lower() or "энергично" in emotion.lower():
        p *= 1.07
    if "шёпот" in emotion.lower():
        rate *= 0.85
    if "злой" in emotion.lower():
        rate *= 0.98; p *= 0.92

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
                <b style="color:#cbd5e1;">{html.escape(voice)}</b> · {html.escape(emotion)}<br/>
                темп {rate:.2f}× · высота {p:.2f}× · громкость {volume:.2f}
                {('<br/><span style="color:#fcd34d;">Туркменский в preview звучит ближе всего к tr-TR. На VPS реальный голос даст backend ' + TURKMEN_TTS_BACKEND + '.</span>') if is_turkmen else ''}
            </div>
        </div>
        <script>
        (function() {{
            const text = {safe_text};
            const lang = "{browser_lang}";
            const rate = {rate};
            const pitch = {p};
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
        height=140,
    )


# ===========================================================================
# Header — настройки
# ===========================================================================

st.markdown(
    """
    <div class='hero'>
      <h1>🌐 Murat AI</h1>
      <div class='tag'>Перевод · озвучка · дубляж видео на русском, туркменском, турецком и английском</div>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.container():
    st.markdown("<div class='card'><div class='card-title'>⚙️ Настройки проекта</div>",
                unsafe_allow_html=True)

    r1 = st.columns([1.3, 1.0, 1.0, 1.0, 1.0, 1.0])
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
        emotion_main = st.selectbox("Эмоция", EMOTIONS, index=0)

    r2 = st.columns([1.0, 1.0, 1.0, 1.0, 1.0, 1.0])
    with r2[0]:
        tempo = st.slider("Темп речи", 0.6, 1.6, 1.0, 0.05)
    with r2[1]:
        pitch = st.slider("Высота голоса", 0.6, 1.6, 1.0, 0.05)
    with r2[2]:
        volume = st.slider("Громкость", 0.1, 1.0, 1.0, 0.05)
    with r2[3]:
        fit_timing = st.checkbox("Подогнать текст под тайминг", value=True)
    with r2[4]:
        clean_noise = st.checkbox("Очистить шум / эхо", value=True)
    with r2[5]:
        preserve_quality = st.checkbox("Сохранить качество исходника", value=True)

    st.markdown("</div>", unsafe_allow_html=True)

# Resolve current format characteristics & inject matching CSS.
aspect_css, frame_max_width, fmt_class = FORMATS[fmt_label]
inject_css(aspect_css, frame_max_width)


# ===========================================================================
# Ряд 1 — Исходное видео ↔ Готовое видео
# ===========================================================================

col_src, col_out = st.columns(2, gap="large")

with col_src:
    st.markdown("<div class='card'><div class='card-title'>📥 Исходное видео</div>",
                unsafe_allow_html=True)

    render_video_frame(
        st.session_state.source_url or None,
        st.session_state.source_file_bytes,
        st.session_state.source_file_name,
        fmt_class=fmt_class,
        placeholder_emoji="🎬",
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
                        "В preview-режиме прямое скачивание ограничено платформой. "
                        "«📺 Показать видео» проигрывает ссылку inline без скачивания."
                    )

    up = st.file_uploader(
        "Загрузить видео из папки",
        type=["mp4", "mov", "webm", "mkv", "m4v"],
        label_visibility="visible",
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
            st.session_state.source_file_bytes,
            st.session_state.source_file_name,
            fmt_class=fmt_class,
            placeholder_emoji="✅",
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

    # Параметры готового видео — pills
    st.markdown(
        f"<div style='margin: 4px 0 12px'>"
        f"<span class='pill'>{html.escape(fmt_label.split(' — ')[0])}</span>"
        f"<span class='pill'>{html.escape(quality)}</span>"
        f"<span class='pill ok'>{html.escape(LANG_LABELS[target_lang])}</span>"
        f"<span class='pill mute'>{html.escape(voice_main)}</span>"
        f"<span class='pill mute'>{html.escape(emotion_main)}</span>"
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

    d1, d2 = st.columns(2)
    placeholder_mp4 = st.session_state.source_file_bytes or b"Murat AI preview MP4 placeholder."
    srt_text = make_srt(st.session_state.translated_text or st.session_state.source_text)
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
        "Загрузить аудио (wav / mp3 / m4a / flac / ogg, 30–60 сек чистого голоса)",
        type=["wav", "mp3", "m4a", "flac", "ogg"],
        key="voice_sample_input",
    )
    if vs is not None:
        st.session_state.voice_sample_bytes = vs.read()
        st.session_state.voice_sample_name = vs.name
        st.audio(st.session_state.voice_sample_bytes)

    if st.session_state.voice_sample_bytes is not None and vs is None:
        # show the previously-loaded sample preview after a rerun
        st.audio(st.session_state.voice_sample_bytes)

    cc1, cc2 = st.columns(2)
    with cc1:
        opt_noise = st.checkbox("🧹 Очистить шум", value=True)
        opt_level = st.checkbox("📐 Выровнять громкость", value=True)
    with cc2:
        opt_echo = st.checkbox("🔇 Удалить эхо", value=True)
        opt_clean_voice = st.checkbox("✨ Сделать голос чистым для озвучки",
                                       value=True)

    if st.button("💾 Создать голосовой профиль",
                  type="primary", use_container_width=True):
        if not st.session_state.voice_sample_bytes:
            st.error("Сначала загрузи аудио-образец голоса.")
        else:
            st.session_state.voice_profile_ready = True
            st.success(
                f"Профиль создан: «{html.escape(st.session_state.voice_sample_name or 'мой голос')}»."
            )
    if st.session_state.voice_profile_ready:
        st.markdown(
            "<span class='pill ok'>профиль готов</span>"
            f"<span class='pill mute'>шум: {'убран' if opt_noise else 'нет'}</span>"
            f"<span class='pill mute'>эхо: {'убрано' if opt_echo else 'нет'}</span>"
            f"<span class='pill mute'>громкость: {'выровнена' if opt_level else 'нет'}</span>",
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
    speak_button(
        preview_text, target_lang,
        voice_main, emotion_main,
        tempo=tempo, pitch=pitch, volume=volume,
        key="voice_top",
    )

    if voice_main == "⭐ Мой загруженный голос":
        st.info(
            "В полном режиме озвучка будет создана **этим очищенным голосом** "
            "через voice-cloning backend на VPS. В preview звучит браузерным голосом — "
            "это просто демонстрация параметров."
        )

    if target_lang == "tk":
        st.caption(
            f"Туркменский голос на VPS использует backend "
            f"`{TURKMEN_TTS_BACKEND}` (Meta MMS-TTS / VITS) с управлением эмоциями "
            "через speed/pitch/energy/pause/volume."
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
            st.session_state.translated_text = translate_preview(
                text_in, source_lang, target_lang,
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
        st.download_button(
            "⬇️ Скачать TXT",
            data=result_text or "Murat AI preview",
            file_name="murat-ai.txt",
            use_container_width=True,
        )
    with dl_t2:
        st.download_button(
            "⬇️ Скачать SRT",
            data=make_srt(result_text or text_in),
            file_name="murat-ai.srt",
            use_container_width=True,
        )
    with dl_t3:
        st.download_button(
            "⬇️ Скачать VTT",
            data=make_vtt(result_text or text_in),
            file_name="murat-ai.vtt",
            use_container_width=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)


# ===========================================================================
# Ряд 4 — Роли актёров / голоса
# ===========================================================================

st.markdown("<div class='card'><div class='card-title'>🎭 Роли и голоса в видео</div>",
            unsafe_allow_html=True)
st.caption(
    "Список ролей (актёров), которых слышно в исходном видео. Для каждой можно "
    "оставить готовый голос, выбрать эмоцию и заменить голос на «Мой загруженный голос» "
    "или загрузить отдельный голос именно для этой роли."
)

cnt_col1, cnt_col2 = st.columns([1, 5])
with cnt_col1:
    desired_count = st.number_input("Сколько голосов / актёров",
                                     min_value=1, max_value=12,
                                     value=len(st.session_state.actors), step=1)
# Reshape actor list to match desired count.
while len(st.session_state.actors) < desired_count:
    n = len(st.session_state.actors) + 1
    st.session_state.actors.append({
        "role": f"Актёр {n}", "voice": "👨 Мужской",
        "emotion": "🙂 Нейтрально", "replace_mode": "Не заменять",
        "sample_name": "",
    })
while len(st.session_state.actors) > desired_count:
    st.session_state.actors.pop()

REPLACE_MODES = ["Не заменять", "⭐ Мой загруженный голос", "🎤 Другой голос (см. ниже)"]

for i, actor in enumerate(st.session_state.actors):
    with st.container():
        st.markdown("<div class='actor-card'>", unsafe_allow_html=True)
        r1c = st.columns([1.0, 1.4, 1.2, 1.4, 1.2])
        with r1c[0]:
            actor["role"] = st.text_input(
                "Название роли", value=actor["role"],
                key=f"actor_role_{i}",
            )
        with r1c[1]:
            actor["voice"] = st.selectbox(
                "Голос", VOICES,
                index=VOICES.index(actor["voice"]) if actor["voice"] in VOICES else 3,
                key=f"actor_voice_{i}",
            )
        with r1c[2]:
            actor["emotion"] = st.selectbox(
                "Эмоция", EMOTIONS,
                index=EMOTIONS.index(actor["emotion"]) if actor["emotion"] in EMOTIONS else 0,
                key=f"actor_emotion_{i}",
            )
        with r1c[3]:
            actor["replace_mode"] = st.selectbox(
                "Заменить голос на", REPLACE_MODES,
                index=REPLACE_MODES.index(actor["replace_mode"])
                if actor["replace_mode"] in REPLACE_MODES else 0,
                key=f"actor_replace_{i}",
            )
        with r1c[4]:
            preview_text_actor = (st.session_state.translated_text
                                    or SAMPLE_TRANSLATIONS.get(
                                        (source_lang, target_lang),
                                        st.session_state.source_text))
            speak_button(
                preview_text_actor, target_lang,
                actor["voice"], actor["emotion"],
                tempo=tempo, pitch=pitch, volume=volume,
                key=f"actor_{i}",
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
            # сразу применить к текущему переводу
            st.session_state.translated_text = apply_rules(st.session_state.translated_text)
            st.session_state.replace_from = ""
            st.session_state.replace_to = ""
            st.rerun()

if st.session_state.rules:
    table_rows = []
    for r in st.session_state.rules:
        table_rows.append({
            "Старое слово": r["from"],
            "Новое слово": r["to"],
            "Область": r.get("scope", REPLACE_SCOPES[0]),
        })
    st.dataframe(table_rows, use_container_width=True, hide_index=True)
    if st.button("🗑 Очистить все замены"):
        st.session_state.rules = []
        st.rerun()
else:
    st.caption("Замен пока нет. Заполни поля выше и нажми «Сохранить замену».")

st.markdown("</div>", unsafe_allow_html=True)


# ===========================================================================
# Project settings JSON — внизу, как дополнительный экспорт (НЕ главный)
# ===========================================================================

with st.expander("⚙️ Скачать настройки проекта (JSON)", expanded=False):
    project_settings = {
        "created_at": datetime.utcnow().isoformat(),
        "format": fmt_label,
        "quality": quality,
        "source_lang": source_lang,
        "target_lang": target_lang,
        "voice": voice_main,
        "emotion": emotion_main,
        "tempo": tempo,
        "pitch": pitch,
        "volume": volume,
        "fit_timing": fit_timing,
        "clean_noise": clean_noise,
        "preserve_quality": preserve_quality,
        "turkmen_tts_backend": TURKMEN_TTS_BACKEND,
        "actors": st.session_state.actors,
        "replacements": st.session_state.rules,
    }
    st.download_button(
        "💾 Скачать настройки (JSON)",
        data=json.dumps(project_settings, ensure_ascii=False, indent=2),
        file_name="murat-ai-project.json",
        mime="application/json",
        use_container_width=True,
    )

st.markdown("---")
st.caption(
    f"Murat AI preview. Настоящий MP4 4K/8K, клонирование голоса и "
    f"туркменская TTS-модель `{TURKMEN_TTS_BACKEND}` работают на VPS / GPU backend "
    "(ветка `issue-2-ai-architecture`)."
)
