"""Streamlit cloud app — Warehouse AI Translator.

Sections:
  * Sidebar — channel switcher (AI agents) + global settings
  * 🌐 Translate — text translation with style/tone/emotion/voice
  * 🎬 Audio / Video / URL — extract → ASR → translate → TTS pipeline
  * 📚 Dictionary — user glossary (CRUD + search)
  * 🧠 Memory — translation memory (CRUD + search)
  * 🤖 Channels — AI-agents CRUD
  * 🎙️ Voices — built-in voice catalog (23 profiles)

Models load lazily and are cached via ``@st.cache_resource``. Storage
defaults to local SQLite (``data/warehouse_ai.db``) and can be moved to
PostgreSQL by setting ``DATABASE_URL``.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Optional

import streamlit as st

from src.cloud.asr import ASRService
from src.cloud.config import LANG_CODE_MAP, SUPPORTED_ROUTES
from src.cloud.language import detect_lang
from src.cloud.translator import TranslatorService
from src.cloud.tts_mms import MMSTurkmenTTS
from src.cloud.video_io import download_video, extract_wav
from src.storage import init_db
from src.storage.repositories import (
    ChannelDTO,
    ChannelRepository,
    DuplicateEntryError,
    GlossaryRepository,
    TranslationMemoryRepository,
)
from src.translator.styles import (
    EMOTION_PROFILES,
    STYLE_PROFILES,
    TONE_PROFILES,
    Emotion,
    list_emotions,
    list_styles,
    list_tones,
)
from src.translator.translation_memory import TranslationMemoryService
from src.translator.user_glossary import UserGlossaryService
from src.ui.theme import inject as inject_theme
from src.voices import VOICE_CATALOG, list_voices, voices_for_language

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

LANGS = sorted(LANG_CODE_MAP.keys())
LANG_LABELS = {
    "ru": "🇷🇺 Русский",
    "tk": "🇹🇲 Türkmençe",
    "tr": "🇹🇷 Türkçe",
    "en": "🇬🇧 English",
}


# ---------------------------------------------------------------------------
# Cached services
# ---------------------------------------------------------------------------


@st.cache_resource(show_spinner=False)
def _bootstrap_storage():
    init_db()
    glossary_repo = GlossaryRepository()
    tm_repo = TranslationMemoryRepository()
    channel_repo = ChannelRepository()
    return {
        "glossary_repo": glossary_repo,
        "tm_repo": tm_repo,
        "channel_repo": channel_repo,
        "user_glossary": UserGlossaryService(glossary_repo),
        "translation_memory": TranslationMemoryService(tm_repo),
    }


@st.cache_resource(show_spinner="Loading translation model…")
def get_translator() -> TranslatorService:
    storage = _bootstrap_storage()
    return TranslatorService(
        user_glossary=storage["user_glossary"],
        translation_memory=storage["translation_memory"],
    )


@st.cache_resource(show_spinner="Loading speech recogniser…")
def get_asr(model_name: str) -> ASRService:
    return ASRService(model_name=model_name)


@st.cache_resource(show_spinner="Loading Turkmen voice…")
def get_tts() -> MMSTurkmenTTS:
    return MMSTurkmenTTS()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _format_lang(code: str) -> str:
    return LANG_LABELS.get(code, code)


def _style_label(profile) -> str:
    return f"{profile.label_ru} — {profile.description}"


def _tone_label(profile) -> str:
    return profile.label_ru


def _emotion_label(profile) -> str:
    return profile.label_ru


def _voice_label(voice) -> str:
    langs = ", ".join(voice.languages)
    return f"{voice.label_ru} · {voice.gender.value} · {voice.tone.value} · {langs}"


def _selected_channel() -> Optional[ChannelDTO]:
    storage = _bootstrap_storage()
    channel_repo: ChannelRepository = storage["channel_repo"]
    cid = st.session_state.get("active_channel_id")
    if not cid:
        return None
    return channel_repo.get(cid)


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------


st.set_page_config(
    page_title="Warehouse AI Translator",
    page_icon="🌐",
    layout="wide",
    menu_items={
        "About": "Warehouse AI Engine — multilingual translator with channels, "
        "user glossary, translation memory and Turkmen voice."
    },
)
inject_theme(st)


# ---------------------------------------------------------------------------
# Sidebar: channels + global settings
# ---------------------------------------------------------------------------


def _render_sidebar() -> None:
    storage = _bootstrap_storage()
    channel_repo: ChannelRepository = storage["channel_repo"]

    with st.sidebar:
        st.markdown("### 🤖 Channels (AI agents)")
        channels = channel_repo.list(limit=200)
        options = [("__none__", "🌍 Global (no channel)")] + [
            (c.id, f"📺 {c.name}") for c in channels
        ]
        ids = [opt[0] for opt in options]
        labels = {opt[0]: opt[1] for opt in options}
        active = st.session_state.get("active_channel_id") or "__none__"
        if active not in ids:
            active = "__none__"
        chosen = st.selectbox(
            "Active channel",
            ids,
            index=ids.index(active),
            format_func=lambda v: labels.get(v, v),
            key="sidebar_channel_select",
        )
        st.session_state["active_channel_id"] = (
            None if chosen == "__none__" else chosen
        )

        active_channel = _selected_channel()
        if active_channel:
            st.markdown(
                f"<div class='w-card'><strong>{active_channel.name}</strong>"
                f"<br/><span class='caption-soft'>"
                f"style: <code>{active_channel.style}</code> · "
                f"tone: <code>{active_channel.tone or '—'}</code> · "
                f"emotion: <code>{active_channel.emotion}</code><br/>"
                f"voice: <code>{active_channel.voice_id or '—'}</code> · "
                f"primary: {active_channel.primary_lang}</span></div>",
                unsafe_allow_html=True,
            )

        st.markdown("---")
        st.markdown("### ⚙️ Settings")
        st.selectbox(
            "Whisper size",
            ["tiny", "base", "small", "medium"],
            index=2,
            key="asr_model",
            help="'tiny'/'base' run fast on CPU; 'small' is the best trade-off.",
        )
        st.caption(
            "User glossary, TM and channels live in `data/warehouse_ai.db` (SQLite). "
            "Set `DATABASE_URL` to switch to PostgreSQL."
        )


_render_sidebar()


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------


st.markdown(
    """
    <h1>🌐 Warehouse AI Translator</h1>
    <p class="muted">RU · TK · TR · EN · 15 styles · 16 tones · 7 emotions · 23 voices · channels (AI agents).</p>
    """,
    unsafe_allow_html=True,
)


tab_translate, tab_media, tab_dict, tab_memory, tab_channels, tab_voices = st.tabs(
    ["✨ Translate", "🎬 Audio / Video / URL",
     "📚 Dictionary", "🧠 Memory", "🤖 Channels", "🎙️ Voices"]
)


# ---------------------------------------------------------------------------
# Translate tab
# ---------------------------------------------------------------------------


def _render_translate_tab() -> None:
    storage = _bootstrap_storage()
    glossary_repo: GlossaryRepository = storage["glossary_repo"]
    tm: TranslationMemoryService = storage["translation_memory"]
    active_channel = _selected_channel()
    channel_id = active_channel.id if active_channel else None

    # Channel-driven defaults
    default_style_code = active_channel.style if active_channel else "natural"
    default_tone_code = active_channel.tone if active_channel else None
    default_emotion_code = active_channel.emotion if active_channel else "neutral"
    default_voice_id = active_channel.voice_id if active_channel else None
    default_target_lang = (
        active_channel.target_lang if active_channel and active_channel.target_lang else "tk"
    )
    default_source_lang = active_channel.primary_lang if active_channel else "ru"
    if default_source_lang not in LANGS:
        default_source_lang = "ru"
    if default_target_lang not in LANGS:
        default_target_lang = "tk"

    st.markdown("### Translate text")

    row1 = st.columns([2, 2])
    with row1[0]:
        src = st.selectbox(
            "From", LANGS, index=LANGS.index(default_source_lang),
            format_func=_format_lang, key="t_src",
        )
    with row1[1]:
        tgt = st.selectbox(
            "To", LANGS, index=LANGS.index(default_target_lang),
            format_func=_format_lang, key="t_tgt",
        )

    row2 = st.columns([2, 2, 2])
    with row2[0]:
        styles = list_styles()
        style_codes = [s.code for s in styles]
        default_idx = style_codes.index(default_style_code) if default_style_code in style_codes else 0
        style = st.selectbox(
            "Style", styles, index=default_idx,
            format_func=_style_label, key="t_style",
        )
    with row2[1]:
        tones = list_tones()
        tone_codes = [t.code for t in tones]
        tone_options = [None, *tones]
        if default_tone_code and default_tone_code in tone_codes:
            default_tone_idx = 1 + tone_codes.index(default_tone_code)
        else:
            default_tone_idx = 0
        tone = st.selectbox(
            "Tone (delivery)",
            tone_options,
            index=default_tone_idx,
            format_func=lambda t: "— none —" if t is None else _tone_label(t),
            key="t_tone",
        )
    with row2[2]:
        emotions = list_emotions()
        emotion_codes = [e.code for e in emotions]
        emotion_idx = emotion_codes.index(default_emotion_code) if default_emotion_code in emotion_codes else 0
        emotion = st.selectbox(
            "Emotion", emotions, index=emotion_idx,
            format_func=_emotion_label, key="t_emotion",
        )

    row3 = st.columns([3, 2])
    with row3[0]:
        candidates = voices_for_language(tgt)
        if not candidates:
            candidates = list(VOICE_CATALOG.values())
        voice_ids = [v.id for v in candidates]
        voice_idx = (
            voice_ids.index(default_voice_id)
            if default_voice_id and default_voice_id in voice_ids
            else 0
        )
        voice = st.selectbox(
            "Voice (used for «Voice» button)",
            candidates,
            index=voice_idx,
            format_func=_voice_label,
            key="t_voice",
        )
    with row3[1]:
        auto = st.checkbox(
            "Auto-detect source (ru/en/tr)", value=False, key="t_auto"
        )

    txt = st.text_area(
        "Text", height=160,
        placeholder="Введите текст для перевода…",
        key="t_input", label_visibility="collapsed",
    )

    btn_cols = st.columns([1, 5])
    with btn_cols[0]:
        translate_clicked = st.button(
            "Translate", type="primary", use_container_width=True
        )
    with btn_cols[1]:
        st.caption(
            "По умолчанию — естественный живой стиль. Меняй стиль/тон/эмоцию для "
            "блогерского, новостного, культурного и других режимов."
        )

    if translate_clicked:
        if not txt.strip():
            st.warning("Type some text first.")
            st.stop()
        if src == tgt:
            st.error("Source and target languages must differ.")
            st.stop()
        try:
            translator = get_translator()
            actual_src = src
            if auto:
                detected = detect_lang(txt)
                if detected == "unknown":
                    st.info("Could not auto-detect — using selected source.")
                else:
                    actual_src = detected
            with st.spinner(f"Translating {actual_src} → {tgt}…"):
                result = translator.translate_full(
                    txt.strip(), actual_src, tgt,
                    style=style.code,
                    tone=tone.code if tone else None,
                    emotion=emotion.code,
                    channel_id=channel_id,
                )
            st.session_state["last_translation"] = {
                "source_text": txt.strip(),
                "translated_text": result.text,
                "source_lang": result.source_lang,
                "target_lang": result.target_lang,
                "style": result.style,
                "tone": result.tone,
                "emotion": result.emotion,
                "voice_id": voice.id if voice else None,
                "channel_id": result.channel_id,
                "tm_hit": result.tm_hit,
                "user_glossary_hits": list(result.user_glossary_hits),
                "provider": result.provider,
            }
        except Exception as exc:  # noqa: BLE001
            logger.exception("translation failed")
            st.error(f"Failed: {exc}")
            return

    state = st.session_state.get("last_translation")
    if not state:
        st.markdown(
            "<div class='w-empty'>No translation yet. Enter text and press Translate.</div>",
            unsafe_allow_html=True,
        )
        return

    pills = [
        f"<span class='w-pill'>{_format_lang(state['source_lang'])} → {_format_lang(state['target_lang'])}</span>",
        f"<span class='w-pill muted'>style: {state['style']}</span>",
    ]
    if state.get("tone"):
        pills.append(f"<span class='w-pill muted'>tone: {state['tone']}</span>")
    if state.get("emotion") and state["emotion"] != "neutral":
        pills.append(f"<span class='w-pill muted'>emotion: {state['emotion']}</span>")
    if state.get("channel_id"):
        chan = _bootstrap_storage()["channel_repo"].get(state["channel_id"])
        if chan:
            pills.append(f"<span class='w-pill'>📺 {chan.name}</span>")
    if state["tm_hit"]:
        pills.append("<span class='w-pill good'>✓ from translation memory</span>")
    pills.append(f"<span class='w-pill muted'>via {state['provider']}</span>")
    if state["user_glossary_hits"]:
        joined = ", ".join(sorted(set(state["user_glossary_hits"])))
        pills.append(f"<span class='w-pill good'>glossary: {joined}</span>")

    st.markdown("".join(pills), unsafe_allow_html=True)
    st.markdown(
        f"<div class='w-translation'>{state['translated_text']}</div>",
        unsafe_allow_html=True,
    )

    act = st.columns(3)
    with act[0]:
        if st.button("🔊 Voice", use_container_width=True, key="t_btn_voice"):
            try:
                target_lang = state["target_lang"]
                voice_profile = VOICE_CATALOG.get(state.get("voice_id") or "")
                if target_lang == "tk" or (voice_profile and voice_profile.provider == "mms"):
                    tts = get_tts()
                    with st.spinner("Synthesising…"):
                        wav = tts.synthesize(state["translated_text"], emotion=state.get("emotion") or "neutral")
                    st.audio(wav)
                else:
                    st.info(
                        "Cloud TTS for ru/en/tr currently requires `OPENAI_API_KEY`. "
                        "Selected voice metadata is sent to the API; this Streamlit "
                        "MVP only renders Turkmen voice locally."
                    )
            except Exception as exc:  # noqa: BLE001
                st.error(f"TTS failed: {exc}")
    with act[1]:
        with st.popover("✏️ Replace translation"):
            st.caption(
                "Если перевод неверный — введи правильный вариант. Сохранится в "
                "Translation Memory выбранного канала (или глобально, если канал не выбран)."
            )
            corrected = st.text_area(
                "Correct translation",
                value=state["translated_text"],
                height=120, key="replace_text",
            )
            if st.button("Save correction", type="primary", key="save_replace"):
                if corrected.strip() and corrected.strip() != state["translated_text"]:
                    tm.remember(
                        source_text=state["source_text"],
                        target_text=corrected.strip(),
                        source_lang=state["source_lang"],
                        target_lang=state["target_lang"],
                        channel_id=state.get("channel_id"),
                    )
                    st.session_state["last_translation"]["translated_text"] = corrected.strip()
                    st.session_state["last_translation"]["tm_hit"] = True
                    st.session_state["last_translation"]["provider"] = "translation-memory"
                    st.success("Saved to Translation Memory.")
                    st.rerun()
                else:
                    st.info("Nothing changed — TM not updated.")
    with act[2]:
        with st.popover("📚 Add to dictionary"):
            st.caption(
                "Добавь точное соответствие. Будет применяться после каждого "
                "перевода в выбранной паре языков."
            )
            with st.form("add_glossary_quick", clear_on_submit=True):
                src_term = st.text_input("Source term")
                tgt_term = st.text_input("Target term")
                whole = st.checkbox("Whole word match", value=True)
                case_sens = st.checkbox("Case sensitive", value=False)
                scope_channel = st.checkbox(
                    "Save into the active channel only",
                    value=bool(state.get("channel_id")),
                    disabled=not state.get("channel_id"),
                )
                note = st.text_input("Note (optional)")
                submitted = st.form_submit_button("Save rule", type="primary")
            if submitted:
                if not src_term.strip() or not tgt_term.strip():
                    st.warning("Both source and target are required.")
                else:
                    glossary_repo.create(
                        source_lang=state["source_lang"],
                        target_lang=state["target_lang"],
                        source_text=src_term.strip(),
                        target_text=tgt_term.strip(),
                        whole_word=whole,
                        case_sensitive=case_sens,
                        note=note.strip() or None,
                        channel_id=state.get("channel_id") if scope_channel else None,
                    )
                    st.success("Rule saved.")


with tab_translate:
    _render_translate_tab()


# ---------------------------------------------------------------------------
# Media tab
# ---------------------------------------------------------------------------


def _render_media_tab() -> None:
    active_channel = _selected_channel()
    channel_id = active_channel.id if active_channel else None

    default_style_code = active_channel.style if active_channel else "natural"
    default_voice_id = active_channel.voice_id if active_channel else None
    default_emotion_code = active_channel.emotion if active_channel else "neutral"

    st.markdown("### Audio / video / URL")
    st.caption(
        "Paste a YouTube/TikTok URL or upload a file. Pipeline: "
        "download → ffmpeg → Whisper ASR → NLLB-200 translate → TTS."
    )

    url = st.text_input("Media URL", placeholder="https://www.youtube.com/watch?v=…")
    upl = st.file_uploader(
        "…or upload a file",
        type=["mp4", "mkv", "mov", "webm", "wav", "mp3", "m4a", "ogg"],
    )

    row = st.columns(3)
    with row[0]:
        target = st.selectbox(
            "Target language", LANGS,
            index=LANGS.index("tk"),
            format_func=_format_lang, key="m_tgt",
        )
    with row[1]:
        manual_src = st.selectbox(
            "Source language", ["auto", *LANGS], index=0,
            format_func=lambda c: "Auto-detect" if c == "auto" else _format_lang(c),
            key="m_src",
        )
    with row[2]:
        styles = list_styles()
        style_codes = [s.code for s in styles]
        default_idx = style_codes.index(default_style_code) if default_style_code in style_codes else 0
        style = st.selectbox(
            "Voiceover style", styles,
            index=default_idx,
            format_func=_style_label, key="m_style",
        )

    row2 = st.columns([2, 2, 2])
    with row2[0]:
        tones = list_tones()
        tone_options = [None, *tones]
        tone = st.selectbox(
            "Tone", tone_options, index=0,
            format_func=lambda t: "— none —" if t is None else _tone_label(t),
            key="m_tone",
        )
    with row2[1]:
        emotions = list_emotions()
        emotion_codes = [e.code for e in emotions]
        emotion_idx = emotion_codes.index(default_emotion_code) if default_emotion_code in emotion_codes else 0
        emotion = st.selectbox(
            "Emotion", emotions, index=emotion_idx,
            format_func=_emotion_label, key="m_emotion",
        )
    with row2[2]:
        candidates = voices_for_language(target) or list(VOICE_CATALOG.values())
        voice_ids = [v.id for v in candidates]
        voice_idx = (
            voice_ids.index(default_voice_id)
            if default_voice_id and default_voice_id in voice_ids else 0
        )
        voice = st.selectbox(
            "Voice", candidates, index=voice_idx,
            format_func=_voice_label, key="m_voice",
        )

    if st.button("Process media", type="primary", key="m_process"):
        if not url.strip() and upl is None:
            st.warning("Provide a URL or upload a file.")
            st.stop()
        try:
            with st.status("Working…", expanded=True) as status:
                if url.strip():
                    status.write("⬇️ Downloading media…")
                    media_path = download_video(url.strip())
                else:
                    suffix = Path(upl.name).suffix or ".mp4"
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                        tmp.write(upl.read())
                        media_path = Path(tmp.name)
                    status.write(f"📁 Using uploaded file `{media_path.name}`")

                status.write("🎧 Extracting audio…")
                wav = extract_wav(media_path)

                asr_model = st.session_state.get("asr_model", "small")
                status.write(f"🗣️ Transcribing with whisper-{asr_model}…")
                asr = get_asr(asr_model)
                hint = None if manual_src == "auto" else manual_src
                source_text = asr.transcribe(str(wav), language=hint)
                if not source_text:
                    raise RuntimeError("Transcription returned empty text.")

                if manual_src == "auto":
                    detected = detect_lang(source_text)
                    src_lang = detected if detected != "unknown" else "ru"
                else:
                    src_lang = manual_src

                status.write(f"🌐 Translating {src_lang} → {target}…")
                translator = get_translator()
                result = translator.translate_full(
                    source_text, src_lang, target,
                    style=style.code,
                    tone=tone.code if tone else None,
                    emotion=emotion.code,
                    channel_id=channel_id,
                )

                voiced_path: Optional[str] = None
                if target == "tk" and result.text:
                    status.write("🔊 Generating Turkmen voice…")
                    voiced_path = get_tts().synthesize(
                        result.text, emotion=emotion.code or "neutral"
                    )

                status.update(label="Done", state="complete")

            st.markdown("#### 🗒️ Transcript")
            st.markdown(
                f"<div class='w-translation'>{source_text}</div>",
                unsafe_allow_html=True,
            )
            st.markdown(f"#### 🌐 Translation ({src_lang} → {target})")
            pills = [
                f"<span class='w-pill muted'>style: {result.style}</span>",
                f"<span class='w-pill muted'>via {result.provider}</span>",
            ]
            if result.tone:
                pills.append(f"<span class='w-pill muted'>tone: {result.tone}</span>")
            if result.emotion and result.emotion != "neutral":
                pills.append(f"<span class='w-pill muted'>emotion: {result.emotion}</span>")
            if result.tm_hit:
                pills.append("<span class='w-pill good'>✓ TM hit</span>")
            st.markdown("".join(pills), unsafe_allow_html=True)
            st.markdown(
                f"<div class='w-translation'>{result.text}</div>",
                unsafe_allow_html=True,
            )
            if voiced_path:
                st.markdown("#### 🔊 Turkmen voice")
                st.audio(voiced_path)
        except Exception as exc:  # noqa: BLE001
            logger.exception("media pipeline failed")
            st.error(f"Failed: {exc}")


with tab_media:
    _render_media_tab()


# ---------------------------------------------------------------------------
# Dictionary tab
# ---------------------------------------------------------------------------


def _render_dictionary_tab() -> None:
    storage = _bootstrap_storage()
    glossary_repo: GlossaryRepository = storage["glossary_repo"]
    active_channel = _selected_channel()

    st.markdown("### My glossary")
    st.caption(
        "Точные правила замены: «исходник → перевод». Применяются после "
        "перевода. Канал виден в боковой панели — правила канала "
        "имеют приоритет над глобальными."
    )

    with st.expander("➕ Add a new rule", expanded=False):
        with st.form("add_glossary_full", clear_on_submit=True):
            cols = st.columns([1, 1])
            with cols[0]:
                g_src = st.selectbox(
                    "From", LANGS, index=LANGS.index("ru"),
                    format_func=_format_lang, key="g_src",
                )
            with cols[1]:
                g_tgt = st.selectbox(
                    "To", LANGS, index=LANGS.index("tk"),
                    format_func=_format_lang, key="g_tgt",
                )
            cols2 = st.columns([1, 1])
            with cols2[0]:
                g_source = st.text_input("Source word / phrase")
            with cols2[1]:
                g_target = st.text_input("Target word / phrase")
            cols3 = st.columns([1, 1, 2])
            with cols3[0]:
                g_whole = st.checkbox("Whole word", value=True)
            with cols3[1]:
                g_case = st.checkbox("Case sensitive", value=False)
            with cols3[2]:
                g_note = st.text_input("Note (optional)")
            scope_channel = st.checkbox(
                "Save into the active channel only",
                value=bool(active_channel),
                disabled=not active_channel,
            )
            if st.form_submit_button("Save rule", type="primary"):
                if g_src == g_tgt:
                    st.error("Source and target languages must differ.")
                elif not g_source.strip() or not g_target.strip():
                    st.warning("Both source and target are required.")
                else:
                    glossary_repo.create(
                        source_lang=g_src,
                        target_lang=g_tgt,
                        source_text=g_source.strip(),
                        target_text=g_target.strip(),
                        whole_word=g_whole,
                        case_sensitive=g_case,
                        note=g_note.strip() or None,
                        channel_id=active_channel.id if active_channel and scope_channel else None,
                    )
                    st.success("Saved.")

    search_cols = st.columns([3, 1, 1, 1])
    with search_cols[0]:
        query = st.text_input(
            "Search", value="", placeholder="🔍 Find by source or target text",
            key="g_search",
        )
    with search_cols[1]:
        f_src = st.selectbox(
            "From", ["any", *LANGS], index=0,
            format_func=lambda c: "Any" if c == "any" else _format_lang(c),
            key="g_filter_src",
        )
    with search_cols[2]:
        f_tgt = st.selectbox(
            "To", ["any", *LANGS], index=0,
            format_func=lambda c: "Any" if c == "any" else _format_lang(c),
            key="g_filter_tgt",
        )
    with search_cols[3]:
        scope = st.selectbox(
            "Scope",
            ["all", "global", "channel"],
            index=0,
            help="«channel» = только активный канал. «global» = только глобальные.",
            key="g_filter_scope",
        )

    list_kwargs = dict(
        source_lang=None if f_src == "any" else f_src,
        target_lang=None if f_tgt == "any" else f_tgt,
        query=query.strip() or None,
        limit=500,
    )
    if scope == "channel":
        list_kwargs["channel_id"] = active_channel.id if active_channel else "__none__"
    elif scope == "global":
        list_kwargs["channel_id"] = None
    entries = glossary_repo.list(**list_kwargs)

    if not entries:
        st.markdown(
            "<div class='w-empty'>No glossary rules.</div>",
            unsafe_allow_html=True,
        )
    else:
        st.caption(f"{len(entries)} rule(s)")
        for entry in entries:
            with st.container(border=True):
                cols = st.columns([3, 3, 2, 2])
                with cols[0]:
                    st.markdown(
                        f"**{entry.source_text}** "
                        f"<span class='w-pill muted'>{_format_lang(entry.source_lang)}</span>",
                        unsafe_allow_html=True,
                    )
                with cols[1]:
                    st.markdown(
                        f"**{entry.target_text}** "
                        f"<span class='w-pill muted'>{_format_lang(entry.target_lang)}</span>",
                        unsafe_allow_html=True,
                    )
                with cols[2]:
                    flags = []
                    if entry.whole_word:
                        flags.append("whole word")
                    if entry.case_sensitive:
                        flags.append("case-sensitive")
                    if entry.channel_id:
                        flags.append("📺 channel")
                    else:
                        flags.append("🌍 global")
                    st.caption(", ".join(flags) or "—")
                    if entry.note:
                        st.caption(f"📝 {entry.note}")
                with cols[3]:
                    with st.popover("Edit"):
                        new_src = st.text_input("Source", value=entry.source_text, key=f"e_src_{entry.id}")
                        new_tgt = st.text_input("Target", value=entry.target_text, key=f"e_tgt_{entry.id}")
                        new_whole = st.checkbox("Whole word", value=entry.whole_word, key=f"e_w_{entry.id}")
                        new_case = st.checkbox("Case sensitive", value=entry.case_sensitive, key=f"e_c_{entry.id}")
                        new_note = st.text_input("Note", value=entry.note or "", key=f"e_n_{entry.id}")
                        if st.button("Save", type="primary", key=f"e_save_{entry.id}"):
                            glossary_repo.update(
                                entry.id, source_text=new_src, target_text=new_tgt,
                                whole_word=new_whole, case_sensitive=new_case,
                                note=new_note or None,
                            )
                            st.success("Updated.")
                            st.rerun()
                    if st.button("🗑️", key=f"e_del_{entry.id}"):
                        glossary_repo.delete(entry.id)
                        st.rerun()


with tab_dict:
    _render_dictionary_tab()


# ---------------------------------------------------------------------------
# Memory tab
# ---------------------------------------------------------------------------


def _render_memory_tab() -> None:
    storage = _bootstrap_storage()
    tm_repo: TranslationMemoryRepository = storage["tm_repo"]
    active_channel = _selected_channel()

    st.markdown("### Translation memory")
    st.caption(
        "Если ввести точно такой же текст для перевода — система отдаст "
        "сохранённый вариант, минуя модель. Канал даёт приоритет над глобальной TM."
    )

    with st.expander("➕ Add a phrase", expanded=False):
        with st.form("add_tm_full", clear_on_submit=True):
            cols = st.columns([1, 1])
            with cols[0]:
                t_src = st.selectbox(
                    "From", LANGS, index=LANGS.index("ru"),
                    format_func=_format_lang, key="tm_src",
                )
            with cols[1]:
                t_tgt = st.selectbox(
                    "To", LANGS, index=LANGS.index("tk"),
                    format_func=_format_lang, key="tm_tgt",
                )
            t_source = st.text_area("Source phrase", height=80)
            t_target = st.text_area("Target phrase", height=80)
            t_note = st.text_input("Note (optional)")
            scope_channel = st.checkbox(
                "Save into the active channel only",
                value=bool(active_channel),
                disabled=not active_channel,
            )
            if st.form_submit_button("Save phrase", type="primary"):
                if t_src == t_tgt:
                    st.error("Source and target languages must differ.")
                elif not t_source.strip() or not t_target.strip():
                    st.warning("Both source and target are required.")
                else:
                    tm_repo.upsert(
                        source_lang=t_src,
                        target_lang=t_tgt,
                        source_text=t_source.strip(),
                        target_text=t_target.strip(),
                        note=t_note.strip() or None,
                        channel_id=active_channel.id if active_channel and scope_channel else None,
                    )
                    st.success("Saved.")

    cols = st.columns([3, 1, 1, 1])
    with cols[0]:
        tm_query = st.text_input(
            "Search", value="", placeholder="🔍 Find by source or target text",
            key="tm_search",
        )
    with cols[1]:
        tm_f_src = st.selectbox(
            "From", ["any", *LANGS], index=0,
            format_func=lambda c: "Any" if c == "any" else _format_lang(c),
            key="tm_filter_src",
        )
    with cols[2]:
        tm_f_tgt = st.selectbox(
            "To", ["any", *LANGS], index=0,
            format_func=lambda c: "Any" if c == "any" else _format_lang(c),
            key="tm_filter_tgt",
        )
    with cols[3]:
        scope = st.selectbox(
            "Scope", ["all", "global", "channel"], index=0,
            key="tm_filter_scope",
        )

    list_kwargs = dict(
        source_lang=None if tm_f_src == "any" else tm_f_src,
        target_lang=None if tm_f_tgt == "any" else tm_f_tgt,
        query=tm_query.strip() or None,
        limit=500,
    )
    if scope == "channel":
        list_kwargs["channel_id"] = active_channel.id if active_channel else "__none__"
    elif scope == "global":
        list_kwargs["channel_id"] = None
    tm_entries = tm_repo.list(**list_kwargs)

    if not tm_entries:
        st.markdown(
            "<div class='w-empty'>Translation memory is empty.</div>",
            unsafe_allow_html=True,
        )
    else:
        st.caption(f"{len(tm_entries)} entry(s)")
        for entry in tm_entries:
            with st.container(border=True):
                row = st.columns([3, 3, 1, 1])
                with row[0]:
                    st.markdown(
                        f"<span class='w-pill muted'>{_format_lang(entry.source_lang)} → "
                        f"{_format_lang(entry.target_lang)}</span> "
                        f"<span class='w-pill muted'>{'📺 channel' if entry.channel_id else '🌍 global'}</span>",
                        unsafe_allow_html=True,
                    )
                    st.markdown(f"**{entry.source_text}**")
                with row[1]:
                    st.markdown(entry.target_text)
                    if entry.note:
                        st.caption(f"📝 {entry.note}")
                with row[2]:
                    with st.popover("Edit"):
                        new_target = st.text_area(
                            "Target", value=entry.target_text,
                            key=f"tm_e_{entry.id}", height=120,
                        )
                        new_note = st.text_input(
                            "Note", value=entry.note or "", key=f"tm_en_{entry.id}",
                        )
                        if st.button("Save", type="primary", key=f"tm_save_{entry.id}"):
                            tm_repo.update(
                                entry.id, target_text=new_target,
                                note=new_note or None,
                            )
                            st.success("Updated.")
                            st.rerun()
                with row[3]:
                    if st.button("🗑️", key=f"tm_del_{entry.id}"):
                        tm_repo.delete(entry.id)
                        st.rerun()


with tab_memory:
    _render_memory_tab()


# ---------------------------------------------------------------------------
# Channels tab
# ---------------------------------------------------------------------------


def _render_channels_tab() -> None:
    storage = _bootstrap_storage()
    channel_repo: ChannelRepository = storage["channel_repo"]

    st.markdown("### Channels (AI agents)")
    st.caption(
        "Каналы — это профили вашего контента. У каждого канала свой стиль, тон, "
        "эмоция, голос, словарь и Translation Memory. Активный канал переключается "
        "в боковой панели."
    )

    with st.expander("➕ Create a channel", expanded=False):
        with st.form("create_channel", clear_on_submit=True):
            name = st.text_input("Name", placeholder="Например: Блог, Новости, Туркменская культура")
            description = st.text_area("Description", height=80)
            cols = st.columns(2)
            with cols[0]:
                primary_lang = st.selectbox(
                    "Primary language", LANGS, index=LANGS.index("ru"),
                    format_func=_format_lang,
                )
            with cols[1]:
                target_lang = st.selectbox(
                    "Default target language", ["—", *LANGS],
                    index=1 + LANGS.index("tk"),
                    format_func=lambda c: "—" if c == "—" else _format_lang(c),
                )
            cols2 = st.columns(3)
            with cols2[0]:
                style = st.selectbox(
                    "Style", list_styles(), index=0, format_func=_style_label,
                )
            with cols2[1]:
                tone_options = [None, *list_tones()]
                tone = st.selectbox(
                    "Tone", tone_options, index=0,
                    format_func=lambda t: "— none —" if t is None else _tone_label(t),
                )
            with cols2[2]:
                emotion = st.selectbox(
                    "Emotion", list_emotions(), index=0, format_func=_emotion_label,
                )
            cols3 = st.columns(2)
            with cols3[0]:
                voice = st.selectbox(
                    "Voice", [None, *list_voices()],
                    format_func=lambda v: "— none —" if v is None else _voice_label(v),
                )
            with cols3[1]:
                voice_use_case = st.selectbox(
                    "Use case", ["video", "audio", "text", "dubbing"], index=0,
                )
            dubbing_notes = st.text_area("Dubbing notes (optional)", height=60)

            if st.form_submit_button("Create channel", type="primary"):
                if not name.strip():
                    st.warning("Name is required.")
                else:
                    try:
                        channel_repo.create(
                            name=name.strip(),
                            description=description.strip() or None,
                            primary_lang=primary_lang,
                            target_lang=None if target_lang == "—" else target_lang,
                            style=style.code,
                            tone=tone.code if tone else None,
                            emotion=emotion.code,
                            voice_id=voice.id if voice else None,
                            voice_use_case=voice_use_case,
                            dubbing_notes=dubbing_notes.strip() or None,
                        )
                        st.success(f"Channel «{name}» created.")
                        st.rerun()
                    except DuplicateEntryError as exc:
                        st.error(str(exc))

    channels = channel_repo.list(limit=500)
    if not channels:
        st.markdown(
            "<div class='w-empty'>No channels yet — create your first AI-agent above.</div>",
            unsafe_allow_html=True,
        )
        return

    for channel in channels:
        with st.container(border=True):
            top = st.columns([4, 2, 2])
            with top[0]:
                st.markdown(f"### 📺 {channel.name}")
                if channel.description:
                    st.caption(channel.description)
            with top[1]:
                st.markdown(
                    f"<span class='w-pill'>style: {channel.style}</span>"
                    f"<span class='w-pill muted'>tone: {channel.tone or '—'}</span>"
                    f"<span class='w-pill muted'>emotion: {channel.emotion}</span>",
                    unsafe_allow_html=True,
                )
                st.caption(
                    f"primary: {channel.primary_lang} → target: {channel.target_lang or 'auto'} · "
                    f"voice: {channel.voice_id or '—'} · use case: {channel.voice_use_case}"
                )
            with top[2]:
                if st.button("Activate", key=f"activate_{channel.id}", use_container_width=True):
                    st.session_state["active_channel_id"] = channel.id
                    st.rerun()
                with st.popover("Edit", use_container_width=True):
                    e_name = st.text_input("Name", value=channel.name, key=f"c_name_{channel.id}")
                    e_desc = st.text_area("Description", value=channel.description or "", key=f"c_desc_{channel.id}")
                    e_style = st.selectbox(
                        "Style", list_styles(),
                        index=[s.code for s in list_styles()].index(channel.style)
                        if channel.style in [s.code for s in list_styles()] else 0,
                        format_func=_style_label,
                        key=f"c_st_{channel.id}",
                    )
                    tone_opts = [None, *list_tones()]
                    if channel.tone and any(t.code == channel.tone for t in list_tones()):
                        e_tone_idx = 1 + [t.code for t in list_tones()].index(channel.tone)
                    else:
                        e_tone_idx = 0
                    e_tone = st.selectbox(
                        "Tone", tone_opts, index=e_tone_idx,
                        format_func=lambda t: "— none —" if t is None else _tone_label(t),
                        key=f"c_tn_{channel.id}",
                    )
                    e_emo = st.selectbox(
                        "Emotion", list_emotions(),
                        index=[e.code for e in list_emotions()].index(channel.emotion)
                        if channel.emotion in [e.code for e in list_emotions()] else 0,
                        format_func=_emotion_label,
                        key=f"c_em_{channel.id}",
                    )
                    voice_opts = [None, *list_voices()]
                    voice_idx = 0
                    if channel.voice_id:
                        voice_codes = [v.id if v else "" for v in voice_opts]
                        if channel.voice_id in voice_codes:
                            voice_idx = voice_codes.index(channel.voice_id)
                    e_voice = st.selectbox(
                        "Voice", voice_opts, index=voice_idx,
                        format_func=lambda v: "— none —" if v is None else _voice_label(v),
                        key=f"c_v_{channel.id}",
                    )
                    e_uc = st.selectbox(
                        "Use case", ["video", "audio", "text", "dubbing"],
                        index=["video", "audio", "text", "dubbing"].index(channel.voice_use_case)
                        if channel.voice_use_case in ["video", "audio", "text", "dubbing"] else 0,
                        key=f"c_uc_{channel.id}",
                    )
                    if st.button("Save", type="primary", key=f"c_save_{channel.id}"):
                        channel_repo.update(
                            channel.id,
                            name=e_name,
                            description=e_desc or None,
                            style=e_style.code,
                            tone=e_tone.code if e_tone else None,
                            emotion=e_emo.code,
                            voice_id=e_voice.id if e_voice else None,
                            voice_use_case=e_uc,
                        )
                        st.success("Updated.")
                        st.rerun()
                if st.button("🗑️ Delete", key=f"c_del_{channel.id}", use_container_width=True):
                    channel_repo.delete(channel.id)
                    if st.session_state.get("active_channel_id") == channel.id:
                        st.session_state["active_channel_id"] = None
                    st.rerun()


with tab_channels:
    _render_channels_tab()


# ---------------------------------------------------------------------------
# Voices tab
# ---------------------------------------------------------------------------


def _render_voices_tab() -> None:
    st.markdown("### Built-in voice catalog (23 profiles)")
    st.caption(
        "Готовые голосовые профили: пол, возраст, тон, темп, питч, поддерживаемые "
        "языки и use cases. Назначай профиль каналу на вкладке «Channels»."
    )

    cols = st.columns(3)
    with cols[0]:
        f_lang = st.selectbox(
            "Language", ["any", *LANGS], index=0,
            format_func=lambda c: "Any" if c == "any" else _format_lang(c),
            key="v_lang",
        )
    with cols[1]:
        f_uc = st.selectbox(
            "Use case", ["any", "text", "video", "audio", "dubbing"], index=0,
            key="v_uc",
        )
    with cols[2]:
        f_gender = st.selectbox(
            "Gender", ["any", "male", "female", "child", "teenager", "neutral"], index=0,
            key="v_gender",
        )

    voices = list_voices()
    if f_lang != "any":
        voices = [v for v in voices if f_lang in v.languages]
    if f_uc != "any":
        voices = [v for v in voices if any(u.value == f_uc for u in v.use_cases)]
    if f_gender != "any":
        voices = [v for v in voices if v.gender.value == f_gender]

    if not voices:
        st.markdown(
            "<div class='w-empty'>No voices match these filters.</div>",
            unsafe_allow_html=True,
        )
        return

    for voice in voices:
        with st.container(border=True):
            cols = st.columns([3, 3, 2])
            with cols[0]:
                st.markdown(f"**{voice.label_ru}** _{voice.label_en}_")
                st.caption(voice.description)
            with cols[1]:
                pills = [
                    f"<span class='w-pill muted'>gender: {voice.gender.value}</span>",
                    f"<span class='w-pill muted'>age: {voice.age_style.value}</span>",
                    f"<span class='w-pill muted'>tone: {voice.tone.value}</span>",
                    f"<span class='w-pill muted'>speed: {voice.speed.value}</span>",
                    f"<span class='w-pill muted'>pitch: {voice.pitch.value}</span>",
                ]
                st.markdown("".join(pills), unsafe_allow_html=True)
                st.caption(
                    f"languages: {', '.join(voice.languages)} · "
                    f"use cases: {', '.join(u.value for u in voice.use_cases)}"
                )
            with cols[2]:
                st.code(voice.id)
                if voice.notes:
                    st.caption(f"📝 {voice.notes}")


with tab_voices:
    _render_voices_tab()
