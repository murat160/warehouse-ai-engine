"""Murat AI — короткие видео / дубляж / озвучка.

Layout follows the user-approved wireframe:

  ┌─ Header — Murat AI · формат · качество · голос · темп ─────────────┐
  │                                                                    │
  │  ┌── ИСХОДНОЕ ВИДЕО (9:16) ─┐    ┌── ГОТОВЫЙ ПРОДУКТ (9:16) ──┐     │
  │  │  [embedded video]        │ →  │  [embedded video]          │     │
  │  │  [Вставить ссылку]       │    │  [Скачать MP4]             │     │
  │  │  [Загрузить из папки]    │    │  [MP4 + SRT] [ZIP]         │     │
  │  └──────────────────────────┘    └────────────────────────────┘     │
  │                                                                    │
  │  ┌── МОЙ ГОЛОС / АУДИО ──┐       ┌── ГОТОВАЯ ОЗВУЧКА ──┐            │
  │  │ [Загрузить голос]     │  →    │ [▶ Прослушать]      │            │
  │  │ [Очистить шум / Эхо]  │       │ голос: ...          │            │
  │  └───────────────────────┘       └─────────────────────┘            │
  │                                                                    │
  │  ┌── ТЕКСТ / СЦЕНАРИЙ / СУБТИТРЫ ───────────────────────────────┐   │
  │  │ [textarea] [Перевести] [Озвучить] [Текст → видео]            │   │
  │  └──────────────────────────────────────────────────────────────┘   │
  │                                                                    │
  │  ┌── ГОТОВЫЙ ТЕКСТ / ЗАМЕНА СЛОВ / СКАЧИВАНИЕ ──────────────────┐   │
  │  │ [готовый перевод]                                            │   │
  │  │ слово → на что  [Применить]                                  │   │
  │  │ [Скачать TXT] [Скачать SRT] [Скачать ZIP]                    │   │
  │  └──────────────────────────────────────────────────────────────┘   │
  │                                                                    │
  │  ┌── ГОЛОСА АКТЁРОВ — переназначить любой на свой ──────────────┐   │
  │  │ Голос 1 → [Мой / Мужской / Женский / Детский / ...] [Эмоция] │   │
  │  └──────────────────────────────────────────────────────────────┘   │
  └────────────────────────────────────────────────────────────────────┘

Preview-режим:
* видео отображается реально через iframe (YouTube/TikTok работают inline);
* загруженный mp4 проигрывается через data-URL в той же phone-frame;
* yt-dlp — опционально для прямой загрузки (`⬇️ Скачать видео`);
* озвучка — через Web Speech API браузера (моментальный звук без
  тяжёлых моделей; полный TTS-стек живёт в issue-2-ai-architecture).
"""

from __future__ import annotations

import html
import json
import re
import tempfile
import uuid
from pathlib import Path
from typing import Dict, Optional, Tuple

import streamlit as st
import streamlit.components.v1 as components

# ---------------------------------------------------------------------------
# Streamlit setup
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Murat AI",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="collapsed",
)

LANG_LABELS = {"ru": "Русский", "tk": "Туркменский", "tr": "Турецкий", "en": "Английский"}
LANGS = ["ru", "tk", "tr", "en"]

ASPECTS = [
    "9:16 — Shorts / Reels / TikTok",
    "16:9 — YouTube / стандарт",
    "1:1 — квадрат Instagram",
    "4:5 — портрет Instagram",
]
QUALITIES = ["1080p Full HD", "4K Ultra HD", "8K"]

VOICES = [
    "🎤 Мой загруженный голос",
    "👨 Мужской — кино",
    "👨 Мужской — документальный",
    "👩 Женский — естественный",
    "👩 Женский — блог",
    "👶 Детский",
    "🧑 Подростковый",
    "🎙 Диктор новостей",
    "🎭 Драматичный кино-голос",
]

EMOTIONS = [
    "🙂 Нейтрально",
    "😄 Радостно",
    "🥺 Грустно",
    "🎯 Серьёзно",
    "💪 Уверенно",
    "❤️ Тепло",
    "⚡ Энергично",
    "🎬 Драматично",
    "🙇 Уважительно",
]

TEMPOS = ["Медленно", "Нормально", "Быстро"]

SAMPLE_TRANSLATIONS: Dict[Tuple[str, str], str] = {
    ("ru", "tk"): "Salam. Men bu wideony arassa türkmen diline terjime edip, professional derejede seslendirmek isleýärin.",
    ("tk", "ru"): "Здравствуйте. Я хочу перевести это видео и сделать профессиональную озвучку.",
    ("ru", "en"): "Hello. I want to translate this video and make a professional voiceover.",
    ("en", "ru"): "Здравствуйте. Я хочу перевести это видео и сделать профессиональную озвучку.",
    ("ru", "tr"): "Merhaba. Bu videoyu profesyonel dublaj için çevirmek istiyorum.",
    ("tr", "ru"): "Здравствуйте. Я хочу перевести и озвучить это видео.",
}


# ---------------------------------------------------------------------------
# Session state defaults
# ---------------------------------------------------------------------------


def init_state() -> None:
    defaults = {
        "source_url": "",
        "source_file_bytes": None,
        "source_file_name": "",
        "result_ready": False,
        "voice_sample_name": None,
        "voice_sample_ok": False,
        "source_text": "Привет. Я хочу сделать короткое видео с переводом и озвучкой на туркменском.",
        "translated_text": "",
        "replace_from": "",
        "replace_to": "",
        "rules": [],
        "actors": [
            {"role": "Голос 1", "voice": "🎤 Мой загруженный голос", "emotion": "🎬 Драматично"},
            {"role": "Голос 2", "voice": "👩 Женский — естественный", "emotion": "❤️ Тепло"},
            {"role": "Голос 3", "voice": "👶 Детский", "emotion": "😄 Радостно"},
        ],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_state()


# ---------------------------------------------------------------------------
# CSS — calm dark theme, 9:16 phone frame, big buttons
# ---------------------------------------------------------------------------

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', -apple-system, sans-serif; }

    .block-container { max-width: 1440px; padding-top: 1.4rem; padding-bottom: 4rem; }

    .hero {
        border-radius: 24px; padding: 22px 26px;
        background: linear-gradient(135deg,#1a1c2e 0%,#2a1e4d 60%,#0e3550 100%);
        border: 1px solid rgba(255,255,255,.10); margin-bottom: 18px;
    }
    .hero h1 { margin: 0; font-size: 34px; font-weight: 800; color: #fff; }
    .hero .tag { color: #c4b5fd; font-weight: 600; font-size: 15px; margin-top: 4px; }

    .card {
        border-radius: 22px; padding: 18px 18px 16px;
        background: rgba(255,255,255,.04);
        border: 1px solid rgba(255,255,255,.10);
        box-shadow: 0 14px 32px rgba(0,0,0,.20);
    }
    .card-title { font-size: 16px; font-weight: 800; color: #e5e7eb; margin-bottom: 12px;
                   display: flex; align-items: center; gap: 8px; }
    .arrow-col { display: flex; align-items: center; justify-content: center;
                  font-size: 28px; color: #7c3aed; font-weight: 900;
                  min-height: 120px; }

    /* 9:16 phone frame */
    .phone-9-16 {
        width: 100%; max-width: 280px; aspect-ratio: 9 / 16;
        margin: 4px auto 12px;
        border-radius: 22px; overflow: hidden;
        background: #0b0d12;
        border: 2px solid rgba(255,255,255,.10);
        box-shadow: 0 18px 35px rgba(0,0,0,.45),
                     inset 0 0 0 1px rgba(255,255,255,.04);
    }
    .phone-9-16 iframe, .phone-9-16 video {
        width: 100% !important; height: 100% !important;
        border: 0; display: block; object-fit: cover;
    }
    .phone-empty {
        display: flex; align-items: center; justify-content: center;
        text-align: center; color: #94a3b8; font-size: 13px;
        height: 100%; padding: 14px; line-height: 1.4;
    }
    .phone-empty .emoji { font-size: 44px; display: block; margin-bottom: 10px; }

    .stTextInput input, .stTextArea textarea, .stSelectbox > div > div {
        background: #11141b !important;
        border: 1px solid rgba(255,255,255,.10) !important;
        border-radius: 12px !important; color: #e5e7eb !important;
    }
    .stButton > button {
        border-radius: 12px !important; font-weight: 700 !important;
        border: 1px solid rgba(255,255,255,.12) !important;
        padding: 0.55rem 1.0rem !important;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg,#7c3aed 0%,#06b6d4 100%) !important;
        color: #fff !important; border: 0 !important;
        box-shadow: 0 8px 20px rgba(124,58,237,.25);
    }
    .stDownloadButton > button {
        border-radius: 12px !important; font-weight: 700 !important;
        background: #1f2937 !important; color: #e5e7eb !important;
        border: 1px solid rgba(255,255,255,.10) !important;
    }

    .pill {
        display: inline-block; padding: 5px 10px; border-radius: 999px;
        font-size: 12px; font-weight: 700; margin-right: 6px; margin-bottom: 4px;
        background: rgba(124,58,237,.18); color: #c4b5fd;
        border: 1px solid rgba(124,58,237,.30);
    }
    .pill.ok { background: rgba(34,197,94,.15); color: #86efac; border-color: rgba(34,197,94,.30); }
    .pill.warn { background: rgba(245,158,11,.15); color: #fcd34d; border-color: rgba(245,158,11,.30); }

    .actor-card {
        background: rgba(255,255,255,.03);
        border: 1px solid rgba(255,255,255,.08);
        border-radius: 14px; padding: 8px 12px; margin-bottom: 8px;
    }

    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header[data-testid="stHeader"] { background: transparent; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

YT_RE = re.compile(
    r"(?:youtube\.com/(?:watch\?v=|shorts/|embed/)|youtu\.be/)([A-Za-z0-9_-]{6,})"
)
TIKTOK_RE = re.compile(r"tiktok\.com/.+/video/(\d+)")


def youtube_embed(url: str) -> Optional[str]:
    m = YT_RE.search(url)
    if not m:
        return None
    return f"https://www.youtube.com/embed/{m.group(1)}?rel=0&modestbranding=1"


def tiktok_embed(url: str) -> Optional[str]:
    m = TIKTOK_RE.search(url)
    if not m:
        return None
    return f"https://www.tiktok.com/embed/v2/{m.group(1)}"


def direct_media_url(url: str) -> bool:
    return bool(re.search(r"\.(mp4|webm|mov|m4v|mp3|wav|m4a)(\?|$)", url.strip(), flags=re.I))


def render_phone_player(url: Optional[str], file_bytes: Optional[bytes], file_name: str,
                        placeholder_emoji: str, placeholder_text: str) -> None:
    """Render a 9:16 phone-shaped player for URL/file/placeholder."""
    if url:
        yt = youtube_embed(url)
        if yt:
            st.markdown(
                f'<div class="phone-9-16">'
                f'<iframe src="{html.escape(yt)}" allow="autoplay; encrypted-media; picture-in-picture" allowfullscreen></iframe>'
                f'</div>',
                unsafe_allow_html=True,
            )
            return
        tt = tiktok_embed(url)
        if tt:
            st.markdown(
                f'<div class="phone-9-16">'
                f'<iframe src="{html.escape(tt)}" allow="autoplay; encrypted-media" allowfullscreen></iframe>'
                f'</div>',
                unsafe_allow_html=True,
            )
            return
        if direct_media_url(url):
            st.markdown(
                f'<div class="phone-9-16">'
                f'<video src="{html.escape(url)}" controls playsinline></video>'
                f'</div>',
                unsafe_allow_html=True,
            )
            return
        st.markdown(
            f"<div class='phone-9-16'><div class='phone-empty'>"
            f"<span class='emoji'>🔗</span>Ссылка принята.<br/>"
            f"Поддерживаются YouTube, TikTok и прямые mp4.</div></div>",
            unsafe_allow_html=True,
        )
        return

    if file_bytes:
        ext = (file_name or "").lower().rsplit(".", 1)[-1] if file_name else ""
        if ext in {"mp3", "wav", "m4a", "flac", "ogg"}:
            st.audio(file_bytes)
            return
        import base64 as _b64
        mime = {
            "mp4": "video/mp4", "webm": "video/webm",
            "mov": "video/quicktime", "mkv": "video/x-matroska",
            "m4v": "video/mp4",
        }.get(ext, "video/mp4")
        b64 = _b64.b64encode(file_bytes).decode("ascii")
        st.markdown(
            f'<div class="phone-9-16"><video controls playsinline>'
            f'<source src="data:{mime};base64,{b64}" type="{mime}"></video></div>',
            unsafe_allow_html=True,
        )
        return

    st.markdown(
        f"<div class='phone-9-16'><div class='phone-empty'>"
        f"<span class='emoji'>{placeholder_emoji}</span>{placeholder_text}"
        f"</div></div>",
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
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": 30,
            "retries": 1,
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
        a = f"00:00:{sec:02d},000"
        b = f"00:00:{sec + 4:02d},000"
        blocks.append(f"{i}\n{a} --> {b}\n{line}\n")
        sec += 4
    return "\n".join(blocks)


def speak_button(text: str, lang: str, voice: str, emotion: str, tempo: str,
                  key: str) -> None:
    """Browser Web Speech API player — works without any TTS model."""
    browser_lang = {"ru": "ru-RU", "tk": "tr-TR", "tr": "tr-TR", "en": "en-US"}.get(lang, "ru-RU")
    rate = {"Медленно": 0.85, "Нормально": 1.0, "Быстро": 1.15}.get(tempo, 1.0)
    pitch = 1.0
    voice_l = voice.lower()
    if "женский" in voice_l or "детский" in voice_l:
        pitch = 1.18
    elif "мужской" in voice_l and "молод" not in voice_l:
        pitch = 0.92
    if "драматич" in voice_l or "кино" in voice_l:
        rate *= 0.92; pitch *= 0.96
    if "грустно" in emotion.lower(): rate *= 0.92; pitch *= 0.96
    if "радостно" in emotion.lower() or "энергично" in emotion.lower(): pitch *= 1.06
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
          <div style="margin-top:8px;color:#94a3b8;font-size:12px;">
            Голос: {html.escape(voice)} · Эмоция: {html.escape(emotion)} · Темп: {html.escape(tempo)}
          </div>
        </div>
        <script>
          (function() {{
            const text  = {safe_text};
            const lang  = "{browser_lang}";
            const rate  = {rate};
            const pitch = {pitch};
            function speak() {{
              window.speechSynthesis.cancel();
              const u = new SpeechSynthesisUtterance(text);
              u.lang = lang; u.rate = rate; u.pitch = pitch;
              const voices = window.speechSynthesis.getVoices();
              const v = voices.find(x => x.lang &&
                        x.lang.toLowerCase().startsWith(lang.slice(0,2).toLowerCase()));
              if (v) u.voice = v;
              window.speechSynthesis.speak(u);
            }}
            document.getElementById('play-{key}').onclick = speak;
            document.getElementById('stop-{key}').onclick = () => window.speechSynthesis.cancel();
          }})();
        </script>
        """,
        height=110,
    )


# ---------------------------------------------------------------------------
# HEADER
# ---------------------------------------------------------------------------

st.markdown(
    """
    <div class='hero'>
      <h1>🌐 Murat AI — короткие видео · дубляж · озвучка</h1>
      <div class='tag'>Перевод, профессиональная озвучка и подготовка видео на ru · tk · tr · en</div>
    </div>
    """,
    unsafe_allow_html=True,
)

h1, h2, h3, h4, h5 = st.columns([1.1, 1.1, 1.3, 1.2, 1.1])
with h1:
    source_lang = st.selectbox("С языка", LANGS, index=0, format_func=lambda x: LANG_LABELS[x])
with h2:
    target_lang = st.selectbox("На язык", LANGS, index=1, format_func=lambda x: LANG_LABELS[x])
with h3:
    aspect = st.selectbox("Формат", ASPECTS, index=0)
with h4:
    quality = st.selectbox("Качество", QUALITIES, index=0)
with h5:
    tempo = st.selectbox("Темп речи", TEMPOS, index=1)


# ---------------------------------------------------------------------------
# ROW 1 — ИСХОДНОЕ ВИДЕО  →  ГОТОВЫЙ ПРОДУКТ
# ---------------------------------------------------------------------------

c_src, c_arr, c_out = st.columns([1, 0.15, 1])

with c_src:
    st.markdown("<div class='card'><div class='card-title'>📥 Исходное видео</div>",
                unsafe_allow_html=True)
    render_phone_player(
        st.session_state.source_url or None,
        st.session_state.source_file_bytes,
        st.session_state.source_file_name,
        placeholder_emoji="🎬",
        placeholder_text="Вставь ссылку YouTube / TikTok / mp4 ниже,<br/>или загрузи файл — сразу появится здесь.",
    )

    url_in = st.text_input(
        "Ссылка на видео",
        value=st.session_state.source_url,
        placeholder="https://youtube.com/shorts/... · https://tiktok.com/... · прямой mp4",
        label_visibility="collapsed",
        key="src_url_input",
    )

    b1, b2 = st.columns(2)
    with b1:
        if st.button("📺 Открыть по ссылке", use_container_width=True, type="primary"):
            if url_in.strip():
                st.session_state.source_url = url_in.strip()
                st.session_state.source_file_bytes = None
                st.session_state.source_file_name = ""
                st.rerun()
    with b2:
        if st.button("⬇️ Скачать видео", use_container_width=True):
            if url_in.strip():
                with st.spinner("Скачиваю видео через yt-dlp…"):
                    data = try_download_via_ytdlp(url_in.strip())
                if data:
                    st.session_state.source_file_bytes = data
                    st.session_state.source_file_name = "downloaded.mp4"
                    st.session_state.source_url = ""
                    st.success(f"Скачано {len(data) // 1024} КБ.")
                    st.rerun()
                else:
                    st.warning(
                        "Прямое скачивание недоступно в preview. "
                        "Используй «📺 Открыть по ссылке» — видео проигрывается inline."
                    )

    up = st.file_uploader(
        "Или загрузить файл с компьютера",
        type=["mp4", "mov", "webm", "mkv", "m4v"],
        label_visibility="collapsed",
        key="src_file_input",
    )
    if up is not None:
        st.session_state.source_file_bytes = up.read()
        st.session_state.source_file_name = up.name
        st.session_state.source_url = ""
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

with c_arr:
    st.markdown("<div class='arrow-col'>→</div>", unsafe_allow_html=True)

with c_out:
    st.markdown("<div class='card'><div class='card-title'>📤 Готовый продукт</div>",
                unsafe_allow_html=True)

    if st.session_state.result_ready:
        render_phone_player(
            st.session_state.source_url or None,
            st.session_state.source_file_bytes,
            st.session_state.source_file_name,
            placeholder_emoji="✅",
            placeholder_text="Готовое видео.",
        )
    else:
        st.markdown(
            "<div class='phone-9-16'><div class='phone-empty'>"
            "<span class='emoji'>📦</span>Здесь появится финальное видео<br/>"
            "с переводом и озвучкой.<br/><br/>"
            "Нажми «✨ Сгенерировать всё»<br/>в блоке текста ниже.</div></div>",
            unsafe_allow_html=True,
        )

    st.markdown(
        f"<div style='margin: 8px 0 12px'>"
        f"<span class='pill'>{html.escape(aspect.split(' — ')[0])}</span>"
        f"<span class='pill'>{html.escape(quality)}</span>"
        f"<span class='pill ok'>{html.escape(LANG_LABELS[target_lang])}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    placeholder_mp4 = (st.session_state.source_file_bytes
                       or b"Murat AI preview MP4 placeholder.")
    srt_text = make_srt(st.session_state.translated_text
                         or st.session_state.source_text)

    d1, d2 = st.columns(2)
    with d1:
        st.download_button("⬇️ MP4", data=placeholder_mp4,
                            file_name="murat-ai-final.mp4",
                            use_container_width=True,
                            disabled=not st.session_state.result_ready)
        st.download_button("⬇️ SRT", data=srt_text,
                            file_name="murat-ai.srt",
                            use_container_width=True,
                            disabled=not st.session_state.result_ready)
    with d2:
        st.download_button("📦 ZIP", data=b"Murat AI preview ZIP.",
                            file_name="murat-ai-package.zip",
                            use_container_width=True,
                            disabled=not st.session_state.result_ready)
        st.download_button("🔊 WAV", data=placeholder_mp4,
                            file_name="murat-ai-voiceover.wav",
                            use_container_width=True,
                            disabled=not st.session_state.result_ready)
    st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# ROW 2 — МОЙ ГОЛОС  →  ГОТОВАЯ ОЗВУЧКА
# ---------------------------------------------------------------------------

c_vin, c_va, c_vout = st.columns([1, 0.15, 1])

with c_vin:
    st.markdown("<div class='card'><div class='card-title'>🎤 Мой голос / аудио</div>",
                unsafe_allow_html=True)
    vs = st.file_uploader(
        "Загрузить образец моего голоса (30–60 сек, чистый звук)",
        type=["wav", "mp3", "m4a", "flac", "ogg"],
        key="voice_sample_input",
    )
    if vs is not None:
        st.session_state.voice_sample_name = vs.name
        st.session_state.voice_sample_ok = True
        st.audio(vs)
    if st.session_state.voice_sample_ok:
        st.markdown(
            f"<span class='pill ok'>загружено: {html.escape(st.session_state.voice_sample_name or '')}</span>",
            unsafe_allow_html=True,
        )

    vc1, vc2 = st.columns(2)
    with vc1:
        clean = st.checkbox("🧹 Очистить шум", value=True)
        st.checkbox("📐 Нормализация громкости", value=True)
    with vc2:
        echo = st.checkbox("🔇 Удалить эхо", value=True)
        consent = st.checkbox("✅ Я подтверждаю права на этот голос", value=True)

    if st.button("💾 Создать профиль голоса", type="primary", use_container_width=True):
        if not st.session_state.voice_sample_ok:
            st.error("Сначала загрузи аудио-образец голоса.")
        elif not consent:
            st.error("Поставь галочку согласия на использование голоса.")
        else:
            st.success(f"Профиль «{html.escape(st.session_state.voice_sample_name or 'мой голос')}» создан.")
    st.markdown("</div>", unsafe_allow_html=True)

with c_va:
    st.markdown("<div class='arrow-col'>→</div>", unsafe_allow_html=True)

with c_vout:
    st.markdown("<div class='card'><div class='card-title'>🔊 Готовая озвучка</div>",
                unsafe_allow_html=True)
    preview_voice = st.session_state.actors[0]["voice"]
    preview_emotion = st.session_state.actors[0]["emotion"]
    preview_text = (st.session_state.translated_text
                     or SAMPLE_TRANSLATIONS.get((source_lang, target_lang), st.session_state.source_text))
    speak_button(preview_text, target_lang, preview_voice, preview_emotion, tempo, key="voice_top")
    st.markdown(
        f"<div style='margin-top:10px'>"
        f"<span class='pill'>{html.escape(preview_voice)}</span>"
        f"<span class='pill'>{html.escape(preview_emotion)}</span>"
        f"<span class='pill'>{html.escape(LANG_LABELS[target_lang])}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )
    st.caption(
        "Preview-режим использует встроенный голосовой движок браузера. "
        "На VPS озвучка идёт через Meta MMS-TTS для туркменского "
        "и коммерческие провайдеры для остальных языков."
    )
    st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# ROW 3 — ТЕКСТ / СЦЕНАРИЙ / СУБТИТРЫ (full width)
# ---------------------------------------------------------------------------

st.markdown(
    "<div class='card' style='margin-top:14px'>"
    "<div class='card-title'>📝 Текст / сценарий / субтитры</div>",
    unsafe_allow_html=True,
)

text_in = st.text_area(
    "Текст для перевода и озвучки",
    value=st.session_state.source_text, height=130,
    label_visibility="collapsed",
)
st.session_state.source_text = text_in

ta1, ta2, ta3, ta4 = st.columns(4)
with ta1:
    if st.button("🌐 Перевести", type="primary", use_container_width=True):
        st.session_state.translated_text = translate_preview(text_in, source_lang, target_lang)
        st.rerun()
with ta2:
    if st.button("🔊 Озвучить", use_container_width=True):
        if not st.session_state.translated_text:
            st.session_state.translated_text = translate_preview(text_in, source_lang, target_lang)
        st.rerun()
with ta3:
    if st.button("🎬 Текст → видео", use_container_width=True):
        if not st.session_state.translated_text:
            st.session_state.translated_text = translate_preview(text_in, source_lang, target_lang)
        st.session_state.result_ready = True
        st.toast("Готовое видео собрано. Смотри блок «Готовый продукт» сверху.")
        st.rerun()
with ta4:
    if st.button("✨ Сгенерировать всё", type="primary", use_container_width=True):
        st.session_state.translated_text = translate_preview(text_in, source_lang, target_lang)
        st.session_state.result_ready = True
        st.rerun()

st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# ROW 4 — ГОТОВЫЙ ТЕКСТ / ЗАМЕНА СЛОВ / СКАЧИВАНИЕ (full width)
# ---------------------------------------------------------------------------

st.markdown(
    "<div class='card' style='margin-top:14px'>"
    "<div class='card-title'>✅ Готовый текст · замена слов · скачивание</div>",
    unsafe_allow_html=True,
)

result_text = st.text_area(
    "Готовый перевод",
    value=st.session_state.translated_text,
    height=140, label_visibility="collapsed",
    key="result_text_area",
)
st.session_state.translated_text = result_text

st.markdown("<div style='margin:6px 0 4px'><b>Заменить слово</b></div>", unsafe_allow_html=True)
rc1, rc2, rc3 = st.columns([1, 1, 0.6])
with rc1:
    st.session_state.replace_from = st.text_input(
        "Что заменить", value=st.session_state.replace_from,
        label_visibility="collapsed", placeholder="старое слово",
    )
with rc2:
    st.session_state.replace_to = st.text_input(
        "На что", value=st.session_state.replace_to,
        label_visibility="collapsed", placeholder="новое слово",
    )
with rc3:
    if st.button("➕ Применить", use_container_width=True):
        if st.session_state.replace_from.strip() and st.session_state.replace_to.strip():
            st.session_state.rules.append({
                "from": st.session_state.replace_from,
                "to": st.session_state.replace_to,
            })
            st.session_state.translated_text = apply_rules(st.session_state.translated_text)
            st.session_state.replace_from = ""
            st.session_state.replace_to = ""
            st.rerun()

if st.session_state.rules:
    st.caption("Сохранённые замены:")
    for i, r in enumerate(st.session_state.rules):
        cc1, cc2 = st.columns([6, 1])
        cc1.markdown(
            f"<span class='pill'>{html.escape(r['from'])}</span> → "
            f"<span class='pill ok'>{html.escape(r['to'])}</span>",
            unsafe_allow_html=True,
        )
        if cc2.button("✕", key=f"rule_del_{i}"):
            st.session_state.rules.pop(i)
            st.rerun()

dl1, dl2, dl3 = st.columns(3)
with dl1:
    st.download_button("⬇️ Скачать TXT",
                        data=st.session_state.translated_text or "Murat AI preview",
                        file_name="murat-ai.txt",
                        use_container_width=True)
with dl2:
    st.download_button("⬇️ Скачать SRT",
                        data=make_srt(st.session_state.translated_text or st.session_state.source_text),
                        file_name="murat-ai.srt",
                        use_container_width=True)
with dl3:
    st.download_button("📦 Скачать ZIP",
                        data=b"Murat AI preview ZIP (TXT + SRT placeholders).",
                        file_name="murat-ai-text-pack.zip",
                        use_container_width=True)

st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# ROW 5 — ГОЛОСА АКТЁРОВ (переназначение)
# ---------------------------------------------------------------------------

st.markdown(
    "<div class='card' style='margin-top:14px'>"
    "<div class='card-title'>🎭 Голоса актёров — назначь любой роли свой голос или готовый</div>",
    unsafe_allow_html=True,
)

st.caption(
    "Слева — список ролей. Для каждой можно поставить «Мой загруженный голос», "
    "выбрать любой из готовых и эмоцию. Это та самая «замена голоса на конкретного "
    "актёра», которую ты описывал."
)

for i, actor in enumerate(st.session_state.actors):
    st.markdown("<div class='actor-card'>", unsafe_allow_html=True)
    a1, a2, a3, a4 = st.columns([1.1, 2, 1.6, 1.6])
    with a1:
        actor["role"] = st.text_input(
            "Роль", value=actor["role"], key=f"actor_role_{i}",
            label_visibility="collapsed",
        )
    with a2:
        actor["voice"] = st.selectbox(
            "Голос", VOICES,
            index=VOICES.index(actor["voice"]) if actor["voice"] in VOICES else 0,
            key=f"actor_voice_{i}", label_visibility="collapsed",
        )
    with a3:
        actor["emotion"] = st.selectbox(
            "Эмоция", EMOTIONS,
            index=EMOTIONS.index(actor["emotion"]) if actor["emotion"] in EMOTIONS else 0,
            key=f"actor_emotion_{i}", label_visibility="collapsed",
        )
    with a4:
        preview_line = (st.session_state.translated_text
                         or SAMPLE_TRANSLATIONS.get((source_lang, target_lang),
                                                     st.session_state.source_text))
        speak_button(preview_line, target_lang, actor["voice"], actor["emotion"],
                      tempo, key=f"actor_{i}")
    st.markdown("</div>", unsafe_allow_html=True)

ab1, ab2 = st.columns(2)
with ab1:
    if st.button("➕ Добавить ещё одну роль", use_container_width=True):
        n = len(st.session_state.actors) + 1
        st.session_state.actors.append({
            "role": f"Голос {n}",
            "voice": "👨 Мужской — кино",
            "emotion": "🙂 Нейтрально",
        })
        st.rerun()
with ab2:
    if st.button("🗑 Удалить последнюю", use_container_width=True):
        if len(st.session_state.actors) > 1:
            st.session_state.actors.pop()
            st.rerun()

st.markdown("</div>", unsafe_allow_html=True)

st.markdown("---")
st.caption(
    "Preview-ветка `streamlit-preview` показывает рабочий UI без тяжёлых моделей. "
    "Полная нейронная озвучка (туркменский MMS-TTS, NLLB/MADLAD, Whisper) "
    "работает на VPS — ветка `issue-2-ai-architecture`."
)
