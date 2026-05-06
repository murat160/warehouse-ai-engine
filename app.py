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
from src.publishing import PublishingService, build_zip_for_package
from src.publishing.models import list_platforms
from src.storage import init_db
from src.storage.repositories import (
    ChannelDTO,
    ChannelRepository,
    CustomVoiceRepository,
    DuplicateEntryError,
    GlossaryRepository,
    PublishingRepository,
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
from src.ui.i18n import (
    SUPPORTED_UI_LANGS,
    UI_LANG_LABELS,
    get_ui_lang,
    lang_options,
    t,
)
from src.ui.theme import inject as inject_theme
from src.voices import (
    VOICE_CATALOG,
    CustomVoiceError,
    CustomVoiceService,
    list_clarity_options,
    list_custom_voice_emotions,
    list_custom_voice_use_cases,
    list_intensity_options,
    list_pitch_options,
    list_speed_options,
    list_voices,
    voices_for_language,
)

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
    custom_voice_repo = CustomVoiceRepository()
    publishing_repo = PublishingRepository()
    return {
        "glossary_repo": glossary_repo,
        "tm_repo": tm_repo,
        "channel_repo": channel_repo,
        "custom_voice_repo": custom_voice_repo,
        "custom_voice_service": CustomVoiceService(custom_voice_repo),
        "publishing_repo": publishing_repo,
        "publishing_service": PublishingService(publishing_repo),
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
        # ----- UI language picker (always first so labels render correctly) -----
        st.markdown(f"### 🌐 {t('sidebar_ui_language')}")
        codes = [code for code, _ in lang_options()]
        active_lang = get_ui_lang()
        chosen_lang = st.selectbox(
            t("sidebar_ui_language"),
            codes,
            index=codes.index(active_lang) if active_lang in codes else 0,
            format_func=lambda c: UI_LANG_LABELS.get(c, c),
            key="ui_lang_select",
            label_visibility="collapsed",
        )
        if chosen_lang != active_lang:
            st.session_state["ui_lang"] = chosen_lang
            st.rerun()

        st.markdown("---")
        st.markdown(f"### {t('sidebar_channels')}")
        channels = channel_repo.list(limit=200)
        options = [("__none__", t("sidebar_global"))] + [
            (c.id, f"📺 {c.name}") for c in channels
        ]
        ids = [opt[0] for opt in options]
        labels = {opt[0]: opt[1] for opt in options}
        active = st.session_state.get("active_channel_id") or "__none__"
        if active not in ids:
            active = "__none__"
        chosen = st.selectbox(
            t("sidebar_active_channel"),
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
        st.markdown(f"### {t('sidebar_settings')}")
        st.selectbox(
            t("sidebar_whisper_size"),
            ["tiny", "base", "small", "medium"],
            index=2,
            key="asr_model",
            help=t("sidebar_whisper_help"),
        )
        st.caption(t("sidebar_storage_caption"))


_render_sidebar()


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------


st.markdown(
    f"""
    <h1>🌐 {t('app_title')}</h1>
    <p class="muted">{t('app_subtitle')}</p>
    """,
    unsafe_allow_html=True,
)


(
    tab_translate, tab_media, tab_dict, tab_memory,
    tab_channels, tab_voices, tab_publish,
) = st.tabs(
    [
        t("tab_translate"),
        t("tab_media"),
        t("tab_dictionary"),
        t("tab_memory"),
        t("tab_channels"),
        t("tab_voices"),
        t("tab_publish"),
    ]
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

    st.markdown(f"### {t('translate_heading')}")

    row1 = st.columns([2, 2])
    with row1[0]:
        src = st.selectbox(
            t("translate_from"), LANGS, index=LANGS.index(default_source_lang),
            format_func=_format_lang, key="t_src",
        )
    with row1[1]:
        tgt = st.selectbox(
            t("translate_to"), LANGS, index=LANGS.index(default_target_lang),
            format_func=_format_lang, key="t_tgt",
        )

    row2 = st.columns([2, 2, 2])
    with row2[0]:
        styles = list_styles()
        style_codes = [s.code for s in styles]
        default_idx = style_codes.index(default_style_code) if default_style_code in style_codes else 0
        style = st.selectbox(
            t("translate_style"), styles, index=default_idx,
            format_func=_style_label, key="t_style",
        )
    with row2[1]:
        tones = list_tones()
        tone_codes = [tn.code for tn in tones]
        tone_options = [None, *tones]
        if default_tone_code and default_tone_code in tone_codes:
            default_tone_idx = 1 + tone_codes.index(default_tone_code)
        else:
            default_tone_idx = 0
        tone = st.selectbox(
            t("translate_tone"),
            tone_options,
            index=default_tone_idx,
            format_func=lambda v: t("none_dash") if v is None else _tone_label(v),
            key="t_tone",
        )
    with row2[2]:
        emotions = list_emotions()
        emotion_codes = [e.code for e in emotions]
        emotion_idx = emotion_codes.index(default_emotion_code) if default_emotion_code in emotion_codes else 0
        emotion = st.selectbox(
            t("translate_emotion"), emotions, index=emotion_idx,
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
            t("translate_voice"),
            candidates,
            index=voice_idx,
            format_func=_voice_label,
            key="t_voice",
        )
    with row3[1]:
        auto = st.checkbox(t("translate_auto_detect"), value=True, key="t_auto")

    txt = st.text_area(
        "Text", height=160,
        placeholder=t("translate_input_placeholder"),
        key="t_input", label_visibility="collapsed",
    )

    btn_cols = st.columns([1, 5])
    with btn_cols[0]:
        translate_clicked = st.button(
            t("translate_button"), type="primary", use_container_width=True
        )
    with btn_cols[1]:
        st.caption(t("translate_hint"))

    if translate_clicked:
        if not txt.strip():
            st.warning(t("type_text_first"))
            st.stop()
        if src == tgt:
            st.error(t("src_tgt_must_differ"))
            st.stop()
        try:
            translator = get_translator()
            actual_src = src
            if auto:
                detected = detect_lang(txt)
                if detected == "unknown":
                    st.info(t("translate_could_not_detect"))
                else:
                    actual_src = detected
            with st.spinner(t("translate_translating").format(src=actual_src, tgt=tgt)):
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
            st.error(t("translate_failed").format(error=exc))
            return

    state = st.session_state.get("last_translation")
    if not state:
        st.markdown(
            f"<div class='w-empty'>{t('translate_no_result')}</div>",
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
        if st.button(t("translate_voice_button"), use_container_width=True, key="t_btn_voice"):
            try:
                target_lang = state["target_lang"]
                voice_profile = VOICE_CATALOG.get(state.get("voice_id") or "")
                if target_lang == "tk" or (voice_profile and voice_profile.provider == "mms"):
                    tts = get_tts()
                    with st.spinner(t("translate_synthesising")):
                        wav = tts.synthesize(state["translated_text"], emotion=state.get("emotion") or "neutral")
                    st.audio(wav)
                else:
                    st.info(t("translate_cloud_tts_warn"))
            except Exception as exc:  # noqa: BLE001
                st.error(t("translate_tts_failed").format(error=exc))
    with act[1]:
        with st.popover(t("translate_replace_button")):
            st.caption(t("translate_replace_caption"))
            corrected = st.text_area(
                t("translate_correct_label"),
                value=state["translated_text"],
                height=120, key="replace_text",
            )
            if st.button(t("translate_save_correction"), type="primary", key="save_replace"):
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
                    st.success(t("translate_saved_to_tm"))
                    st.rerun()
                else:
                    st.info(t("translate_no_change"))
    with act[2]:
        with st.popover(t("translate_add_to_dict")):
            st.caption(t("translate_add_caption"))
            with st.form("add_glossary_quick", clear_on_submit=True):
                src_term = st.text_input(t("dict_source_term"))
                tgt_term = st.text_input(t("dict_target_term"))
                whole = st.checkbox(t("dict_whole_word"), value=True)
                case_sens = st.checkbox(t("dict_case_sensitive"), value=False)
                scope_channel = st.checkbox(
                    t("save_into_channel"),
                    value=bool(state.get("channel_id")),
                    disabled=not state.get("channel_id"),
                )
                note = st.text_input(t("note_optional"))
                submitted = st.form_submit_button(t("translate_save_rule"), type="primary")
            if submitted:
                if not src_term.strip() or not tgt_term.strip():
                    st.warning(t("both_required"))
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
                    st.success(t("translate_rule_saved"))


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

    st.markdown(f"### {t('media_heading')}")
    st.caption(t("media_caption"))
    st.info(t("media_target_caption"))

    url = st.text_input(t("media_url"), placeholder=t("media_url_placeholder"))
    upl = st.file_uploader(
        t("media_upload"),
        type=["mp4", "mkv", "mov", "webm", "wav", "mp3", "m4a", "ogg"],
    )

    row = st.columns(2)
    with row[0]:
        target = st.selectbox(
            t("media_target_lang"), LANGS,
            index=LANGS.index("tk"),
            format_func=_format_lang, key="m_tgt",
        )
    with row[1]:
        styles = list_styles()
        style_codes = [s.code for s in styles]
        default_idx = style_codes.index(default_style_code) if default_style_code in style_codes else 0
        style = st.selectbox(
            t("media_voiceover_style"), styles,
            index=default_idx,
            format_func=_style_label, key="m_style",
        )

    row2 = st.columns([2, 2, 2])
    with row2[0]:
        tones = list_tones()
        tone_options = [None, *tones]
        tone = st.selectbox(
            t("translate_tone"), tone_options, index=0,
            format_func=lambda v: t("none_value") if v is None else _tone_label(v),
            key="m_tone",
        )
    with row2[1]:
        emotions = list_emotions()
        emotion_codes = [e.code for e in emotions]
        emotion_idx = emotion_codes.index(default_emotion_code) if default_emotion_code in emotion_codes else 0
        emotion = st.selectbox(
            t("translate_emotion"), emotions, index=emotion_idx,
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
            t("translate_voice"), candidates, index=voice_idx,
            format_func=_voice_label, key="m_voice",
        )

    if st.button(t("media_process"), type="primary", key="m_process"):
        if not url.strip() and upl is None:
            st.warning(t("media_url_or_file_required"))
            st.stop()
        try:
            with st.status(t("process_working"), expanded=True) as status:
                if url.strip():
                    status.write(t("media_step_download"))
                    media_path = download_video(url.strip())
                else:
                    suffix = Path(upl.name).suffix or ".mp4"
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                        tmp.write(upl.read())
                        media_path = Path(tmp.name)
                    status.write(f"📁 `{media_path.name}`")

                status.write(t("media_step_extract"))
                wav = extract_wav(media_path)

                asr_model = st.session_state.get("asr_model", "small")
                status.write(t("media_step_transcribe"))
                asr = get_asr(asr_model)
                # Always auto-detect: pass language=None so Whisper tells us.
                asr_result = asr.transcribe(str(wav), language=None)
                source_text = asr_result.text
                if not source_text:
                    raise RuntimeError("Transcription returned empty text.")

                detected = (asr_result.language or "").lower()
                if detected in {"ru", "tk", "tr", "en"}:
                    src_lang = detected
                else:
                    fallback = detect_lang(source_text)
                    if fallback in {"ru", "tk", "tr", "en"}:
                        src_lang = fallback
                    else:
                        src_lang = "ru"
                        st.warning(
                            t("media_unknown_lang_warning").format(
                                fallback=_format_lang(src_lang)
                            )
                        )
                status.write(f"{t('media_step_detected')}: {_format_lang(src_lang)}")

                if src_lang == target:
                    # Same language — nothing to translate; reuse the transcript.
                    result_text = source_text
                    result_provider = "passthrough"
                    result_style = style.code
                    result_tone_code = tone.code if tone else None
                    result_emotion = emotion.code
                    result_tm_hit = False
                else:
                    status.write(
                        f"{t('media_step_translate')} ({_format_lang(src_lang)} → {_format_lang(target)})"
                    )
                    translator = get_translator()
                    full = translator.translate_full(
                        source_text, src_lang, target,
                        style=style.code,
                        tone=tone.code if tone else None,
                        emotion=emotion.code,
                        channel_id=channel_id,
                    )
                    result_text = full.text
                    result_provider = full.provider
                    result_style = full.style
                    result_tone_code = full.tone
                    result_emotion = full.emotion
                    result_tm_hit = full.tm_hit

                voiced_path: Optional[str] = None
                if target == "tk" and result_text:
                    status.write(t("media_step_voice"))
                    voiced_path = get_tts().synthesize(
                        result_text, emotion=emotion.code or "neutral"
                    )

                status.update(label=t("process_done"), state="complete")

            st.markdown(f"#### {t('media_transcript_heading')} ({_format_lang(src_lang)})")
            st.markdown(
                f"<div class='w-translation'>{source_text}</div>",
                unsafe_allow_html=True,
            )
            st.markdown(
                f"#### {t('media_translation_heading')} "
                f"({_format_lang(src_lang)} → {_format_lang(target)})"
            )
            pills = [
                f"<span class='w-pill muted'>style: {result_style}</span>",
                f"<span class='w-pill muted'>via {result_provider}</span>",
            ]
            if result_tone_code:
                pills.append(f"<span class='w-pill muted'>tone: {result_tone_code}</span>")
            if result_emotion and result_emotion != "neutral":
                pills.append(f"<span class='w-pill muted'>emotion: {result_emotion}</span>")
            if result_tm_hit:
                pills.append("<span class='w-pill good'>✓ TM hit</span>")
            st.markdown("".join(pills), unsafe_allow_html=True)
            st.markdown(
                f"<div class='w-translation'>{result_text}</div>",
                unsafe_allow_html=True,
            )
            if voiced_path:
                st.markdown(f"#### {t('media_voice_heading')}")
                st.audio(voiced_path)
        except Exception as exc:  # noqa: BLE001
            logger.exception("media pipeline failed")
            st.error(t("translate_failed").format(error=exc))


with tab_media:
    _render_media_tab()


# ---------------------------------------------------------------------------
# Dictionary tab
# ---------------------------------------------------------------------------


def _render_dictionary_tab() -> None:
    storage = _bootstrap_storage()
    glossary_repo: GlossaryRepository = storage["glossary_repo"]
    active_channel = _selected_channel()

    st.markdown(f"### {t('dict_heading')}")
    st.caption(t("dict_caption"))

    with st.expander(t("dict_add"), expanded=False):
        with st.form("add_glossary_full", clear_on_submit=True):
            cols = st.columns([1, 1])
            with cols[0]:
                g_src = st.selectbox(
                    t("translate_from"), LANGS, index=LANGS.index("ru"),
                    format_func=_format_lang, key="g_src",
                )
            with cols[1]:
                g_tgt = st.selectbox(
                    t("translate_to"), LANGS, index=LANGS.index("tk"),
                    format_func=_format_lang, key="g_tgt",
                )
            cols2 = st.columns([1, 1])
            with cols2[0]:
                g_source = st.text_input(t("dict_source_term"))
            with cols2[1]:
                g_target = st.text_input(t("dict_target_term"))
            cols3 = st.columns([1, 1, 2])
            with cols3[0]:
                g_whole = st.checkbox(t("dict_whole_word"), value=True)
            with cols3[1]:
                g_case = st.checkbox(t("dict_case_sensitive"), value=False)
            with cols3[2]:
                g_note = st.text_input(t("note_optional"))
            scope_channel = st.checkbox(
                t("save_into_channel"),
                value=bool(active_channel),
                disabled=not active_channel,
            )
            if st.form_submit_button(t("save"), type="primary"):
                if g_src == g_tgt:
                    st.error(t("src_tgt_must_differ"))
                elif not g_source.strip() or not g_target.strip():
                    st.warning(t("both_required"))
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
                    st.success(t("saved"))

    search_cols = st.columns([3, 1, 1, 1])
    with search_cols[0]:
        query = st.text_input(
            t("search"), value="", placeholder=t("dict_search_placeholder"),
            key="g_search",
        )
    with search_cols[1]:
        f_src = st.selectbox(
            t("translate_from"), ["any", *LANGS], index=0,
            format_func=lambda c: t("any") if c == "any" else _format_lang(c),
            key="g_filter_src",
        )
    with search_cols[2]:
        f_tgt = st.selectbox(
            t("translate_to"), ["any", *LANGS], index=0,
            format_func=lambda c: t("any") if c == "any" else _format_lang(c),
            key="g_filter_tgt",
        )
    with search_cols[3]:
        scope = st.selectbox(
            t("scope"),
            ["all", "global", "channel"],
            index=0,
            format_func=lambda v: t(f"scope_{v}"),
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
            f"<div class='w-empty'>{t('dict_no_rules')}</div>",
            unsafe_allow_html=True,
        )
    else:
        st.caption(t("dict_rules_count").format(n=len(entries)))
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
                    with st.popover(t("edit")):
                        new_src = st.text_input(t("dict_source_term"), value=entry.source_text, key=f"e_src_{entry.id}")
                        new_tgt = st.text_input(t("dict_target_term"), value=entry.target_text, key=f"e_tgt_{entry.id}")
                        new_whole = st.checkbox(t("dict_whole_word"), value=entry.whole_word, key=f"e_w_{entry.id}")
                        new_case = st.checkbox(t("dict_case_sensitive"), value=entry.case_sensitive, key=f"e_c_{entry.id}")
                        new_note = st.text_input(t("note_optional"), value=entry.note or "", key=f"e_n_{entry.id}")
                        if st.button(t("save"), type="primary", key=f"e_save_{entry.id}"):
                            glossary_repo.update(
                                entry.id, source_text=new_src, target_text=new_tgt,
                                whole_word=new_whole, case_sensitive=new_case,
                                note=new_note or None,
                            )
                            st.success(t("updated"))
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

    st.markdown(f"### {t('memory_heading')}")
    st.caption(t("memory_caption"))

    with st.expander(t("tm_add_phrase"), expanded=False):
        with st.form("add_tm_full", clear_on_submit=True):
            cols = st.columns([1, 1])
            with cols[0]:
                t_src = st.selectbox(
                    t("translate_from"), LANGS, index=LANGS.index("ru"),
                    format_func=_format_lang, key="tm_src",
                )
            with cols[1]:
                t_tgt = st.selectbox(
                    t("translate_to"), LANGS, index=LANGS.index("tk"),
                    format_func=_format_lang, key="tm_tgt",
                )
            t_source = st.text_area(t("tm_source_phrase"), height=80)
            t_target = st.text_area(t("tm_target_phrase"), height=80)
            t_note = st.text_input(t("note_optional"))
            scope_channel = st.checkbox(
                t("save_into_channel"),
                value=bool(active_channel),
                disabled=not active_channel,
            )
            if st.form_submit_button(t("tm_save_phrase"), type="primary"):
                if t_src == t_tgt:
                    st.error(t("src_tgt_must_differ"))
                elif not t_source.strip() or not t_target.strip():
                    st.warning(t("both_required"))
                else:
                    tm_repo.upsert(
                        source_lang=t_src,
                        target_lang=t_tgt,
                        source_text=t_source.strip(),
                        target_text=t_target.strip(),
                        note=t_note.strip() or None,
                        channel_id=active_channel.id if active_channel and scope_channel else None,
                    )
                    st.success(t("saved"))

    cols = st.columns([3, 1, 1, 1])
    with cols[0]:
        tm_query = st.text_input(
            t("search"), value="", placeholder=t("dict_search_placeholder"),
            key="tm_search",
        )
    with cols[1]:
        tm_f_src = st.selectbox(
            t("translate_from"), ["any", *LANGS], index=0,
            format_func=lambda c: t("any") if c == "any" else _format_lang(c),
            key="tm_filter_src",
        )
    with cols[2]:
        tm_f_tgt = st.selectbox(
            t("translate_to"), ["any", *LANGS], index=0,
            format_func=lambda c: t("any") if c == "any" else _format_lang(c),
            key="tm_filter_tgt",
        )
    with cols[3]:
        scope = st.selectbox(
            t("scope"), ["all", "global", "channel"], index=0,
            format_func=lambda v: t(f"scope_{v}"),
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
            f"<div class='w-empty'>{t('tm_no_entries')}</div>",
            unsafe_allow_html=True,
        )
    else:
        st.caption(t("tm_entries_count").format(n=len(tm_entries)))
        for entry in tm_entries:
            with st.container(border=True):
                row = st.columns([3, 3, 1, 1])
                with row[0]:
                    scope_label = (
                        f"📺 {t('scope_channel')}" if entry.channel_id
                        else f"🌍 {t('scope_global')}"
                    )
                    st.markdown(
                        f"<span class='w-pill muted'>{_format_lang(entry.source_lang)} → "
                        f"{_format_lang(entry.target_lang)}</span> "
                        f"<span class='w-pill muted'>{scope_label}</span>",
                        unsafe_allow_html=True,
                    )
                    st.markdown(f"**{entry.source_text}**")
                with row[1]:
                    st.markdown(entry.target_text)
                    if entry.note:
                        st.caption(f"📝 {entry.note}")
                with row[2]:
                    with st.popover(t("edit")):
                        new_target = st.text_area(
                            t("dict_target_term"), value=entry.target_text,
                            key=f"tm_e_{entry.id}", height=120,
                        )
                        new_note = st.text_input(
                            t("note_optional"), value=entry.note or "", key=f"tm_en_{entry.id}",
                        )
                        if st.button(t("save"), type="primary", key=f"tm_save_{entry.id}"):
                            tm_repo.update(
                                entry.id, target_text=new_target,
                                note=new_note or None,
                            )
                            st.success(t("updated"))
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

    st.markdown(f"### {t('channels_heading')}")
    st.caption(t("channels_caption"))

    with st.expander(t("channels_create"), expanded=False):
        with st.form("create_channel", clear_on_submit=True):
            name = st.text_input(t("name"), placeholder=t("channels_name_placeholder"))
            description = st.text_area(t("description"), height=80)
            cols = st.columns(2)
            with cols[0]:
                primary_lang = st.selectbox(
                    t("channels_primary_lang"), LANGS, index=LANGS.index("ru"),
                    format_func=_format_lang,
                )
            with cols[1]:
                target_lang = st.selectbox(
                    t("channels_default_target"), ["—", *LANGS],
                    index=1 + LANGS.index("tk"),
                    format_func=lambda c: "—" if c == "—" else _format_lang(c),
                )
            cols2 = st.columns(3)
            with cols2[0]:
                style = st.selectbox(
                    t("translate_style"), list_styles(), index=0, format_func=_style_label,
                )
            with cols2[1]:
                tone_options = [None, *list_tones()]
                tone = st.selectbox(
                    t("translate_tone"), tone_options, index=0,
                    format_func=lambda v: t("none_value") if v is None else _tone_label(v),
                )
            with cols2[2]:
                emotion = st.selectbox(
                    t("translate_emotion"), list_emotions(), index=0, format_func=_emotion_label,
                )
            cols3 = st.columns(2)
            with cols3[0]:
                voice = st.selectbox(
                    t("translate_voice"), [None, *list_voices()],
                    format_func=lambda v: t("none_value") if v is None else _voice_label(v),
                )
            with cols3[1]:
                voice_use_case = st.selectbox(
                    t("channels_use_case"), ["video", "audio", "text", "dubbing"], index=0,
                )
            dubbing_notes = st.text_area(t("channels_dub_notes"), height=60)

            if st.form_submit_button(t("channels_create_button"), type="primary"):
                if not name.strip():
                    st.warning(t("both_required"))
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
                        st.success(f"OK · {name}")
                        st.rerun()
                    except DuplicateEntryError as exc:
                        st.error(str(exc))

    channels = channel_repo.list(limit=500)
    if not channels:
        st.markdown(
            f"<div class='w-empty'>{t('channels_no_channels')}</div>",
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
                if st.button(t("channels_activate"), key=f"activate_{channel.id}", use_container_width=True):
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
                    if channel.tone and any(tn.code == channel.tone for tn in list_tones()):
                        e_tone_idx = 1 + [tn.code for tn in list_tones()].index(channel.tone)
                    else:
                        e_tone_idx = 0
                    e_tone = st.selectbox(
                        "Tone", tone_opts, index=e_tone_idx,
                        format_func=lambda v: t("none_value") if v is None else _tone_label(v),
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
                        format_func=lambda v: t("none_value") if v is None else _voice_label(v),
                        key=f"c_v_{channel.id}",
                    )
                    e_uc = st.selectbox(
                        "Use case", ["video", "audio", "text", "dubbing"],
                        index=["video", "audio", "text", "dubbing"].index(channel.voice_use_case)
                        if channel.voice_use_case in ["video", "audio", "text", "dubbing"] else 0,
                        key=f"c_uc_{channel.id}",
                    )
                    if st.button(t("save"), type="primary", key=f"c_save_{channel.id}"):
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
                        st.success(t("updated"))
                        st.rerun()
                if st.button("🗑️ " + t("delete"), key=f"c_del_{channel.id}", use_container_width=True):
                    channel_repo.delete(channel.id)
                    if st.session_state.get("active_channel_id") == channel.id:
                        st.session_state["active_channel_id"] = None
                    st.rerun()


with tab_channels:
    _render_channels_tab()


# ---------------------------------------------------------------------------
# Voices tab
# ---------------------------------------------------------------------------


def _render_voices_catalog() -> None:
    st.markdown(f"### {t('voices_catalog_heading')}")
    st.caption(t("voices_catalog_caption"))

    cols = st.columns(3)
    with cols[0]:
        f_lang = st.selectbox(
            t("voices_filter_lang"), ["any", *LANGS], index=0,
            format_func=lambda c: t("any") if c == "any" else _format_lang(c),
            key="v_lang",
        )
    with cols[1]:
        f_uc = st.selectbox(
            t("voices_filter_use_case"),
            ["any", "text", "video", "audio", "dubbing"], index=0,
            format_func=lambda v: t("any") if v == "any" else v,
            key="v_uc",
        )
    with cols[2]:
        f_gender = st.selectbox(
            t("voices_filter_gender"),
            ["any", "male", "female", "child", "teenager", "neutral"], index=0,
            format_func=lambda v: t("any") if v == "any" else v,
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
            f"<div class='w-empty'>{t('voices_no_match')}</div>",
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


def _render_custom_voices() -> None:
    storage = _bootstrap_storage()
    repo: CustomVoiceRepository = storage["custom_voice_repo"]
    service: CustomVoiceService = storage["custom_voice_service"]
    channel_repo: ChannelRepository = storage["channel_repo"]

    st.markdown(f"### {t('voices_my_heading')}")
    st.caption(t("voices_my_caption"))

    speeds = list_speed_options()
    pitches = list_pitch_options()
    emotions = list_custom_voice_emotions()
    clarities = list_clarity_options()
    intensities = list_intensity_options()
    cv_use_cases = list_custom_voice_use_cases()

    def _fmt(opts):
        return lambda c: next((o.label_ru for o in opts if o.code == c), c)

    # ---------------- Create form ----------------
    with st.expander(t("cv_create_section"), expanded=False):
        with st.form("create_custom_voice", clear_on_submit=False):
            name = st.text_input(
                t("name"), placeholder=t("cv_name_placeholder"),
                key="cv_create_name",
            )
            description = st.text_area(t("description"), height=60, key="cv_create_desc")
            row = st.columns(3)
            with row[0]:
                language = st.selectbox(
                    t("language"), LANGS, index=LANGS.index("ru"),
                    format_func=_format_lang, key="cv_create_lang",
                )
            with row[1]:
                speed = st.selectbox(
                    t("cv_speed"), [s.code for s in speeds], index=1,
                    format_func=_fmt(speeds), key="cv_create_speed",
                )
            with row[2]:
                pitch = st.selectbox(
                    t("cv_pitch"), [p.code for p in pitches], index=1,
                    format_func=_fmt(pitches), key="cv_create_pitch",
                )
            row2 = st.columns(3)
            with row2[0]:
                emotion = st.selectbox(
                    t("cv_emotion"), [e.code for e in emotions], index=0,
                    format_func=_fmt(emotions), key="cv_create_emotion",
                )
            with row2[1]:
                clarity = st.selectbox(
                    t("cv_clarity"), [c.code for c in clarities], index=0,
                    format_func=_fmt(clarities), key="cv_create_clarity",
                )
            with row2[2]:
                intensity = st.selectbox(
                    t("cv_intensity"), [i.code for i in intensities], index=1,
                    format_func=_fmt(intensities), key="cv_create_intensity",
                )
            row3 = st.columns(3)
            with row3[0]:
                use_case = st.selectbox(
                    t("cv_use_case"), [u.code for u in cv_use_cases], index=0,
                    format_func=_fmt(cv_use_cases), key="cv_create_use_case",
                )
            with row3[1]:
                channels = channel_repo.list(limit=200)
                channel_options = [None, *[c.id for c in channels]]
                channel_id = st.selectbox(
                    t("cv_bind_channel"),
                    channel_options,
                    index=0,
                    format_func=lambda v: t("none_value") if v is None else next(
                        (c.name for c in channels if c.id == v), v
                    ),
                    key="cv_create_channel",
                )
            with row3[2]:
                style_codes = [None, *[s.code for s in list_styles()]]
                bound_style = st.selectbox(
                    t("cv_bind_style"),
                    style_codes,
                    index=0,
                    format_func=lambda v: t("none_value") if v is None else v,
                    key="cv_create_bstyle",
                )

            row4 = st.columns(2)
            with row4[0]:
                bound_video_use_case = st.selectbox(
                    t("cv_bind_video_use_case"),
                    [None, *[u.code for u in cv_use_cases]],
                    index=0,
                    format_func=lambda v: t("none_value") if v is None else _fmt(cv_use_cases)(v),
                    key="cv_create_bvuc",
                )
            with row4[1]:
                parents = repo.list(limit=200)
                parents = [p for p in parents if p.parent_id is None]
                parent_options = [None, *[p.id for p in parents]]
                parent_id = st.selectbox(
                    t("cv_variant_of"),
                    parent_options,
                    index=0,
                    format_func=lambda v: t("cv_standalone") if v is None else next(
                        (p.name for p in parents if p.id == v), v
                    ),
                    key="cv_create_parent",
                )

            st.markdown(t("cv_audio_section"))
            sample_upload = st.file_uploader(
                t("cv_upload_sample"),
                type=["wav", "mp3", "m4a", "ogg", "flac", "webm"],
                key="cv_create_upload",
            )
            recorded = None
            if hasattr(st, "audio_input"):
                recorded = st.audio_input(
                    t("cv_record_sample"), key="cv_create_record"
                )

            st.markdown("---")
            consent = st.checkbox(
                t("voices_consent_label"),
                value=False,
                key="cv_create_consent",
                help=t("cv_consent_help"),
            )

            submitted = st.form_submit_button(
                t("cv_create_button"), type="primary", disabled=False
            )

        if submitted:
            if not consent:
                st.error(t("cv_consent_required_error"))
            elif not name.strip():
                st.warning(t("type_text_first"))
            else:
                sample_bytes = None
                sample_filename = None
                if recorded is not None:
                    sample_bytes = recorded.getvalue() if hasattr(recorded, "getvalue") else recorded.read()
                    sample_filename = "recording.wav"
                elif sample_upload is not None:
                    sample_bytes = sample_upload.read()
                    sample_filename = sample_upload.name
                try:
                    service.create(
                        name=name,
                        consent_given=True,
                        description=description.strip() or None,
                        language=language,
                        speed=speed,
                        pitch=pitch,
                        emotion=emotion,
                        clarity=clarity,
                        intensity=intensity,
                        use_case=use_case,
                        channel_id=channel_id,
                        bound_style=bound_style,
                        bound_video_use_case=bound_video_use_case,
                        parent_id=parent_id,
                        sample_bytes=sample_bytes,
                        sample_filename=sample_filename,
                    )
                    st.success(f"Voice «{name}» created.")
                    st.rerun()
                except CustomVoiceError as exc:
                    st.error(str(exc))
                except Exception as exc:  # noqa: BLE001
                    logger.exception("custom voice create failed")
                    st.error(f"Failed: {exc}")

    # ---------------- Filters + list ----------------
    flt = st.columns([3, 1, 1])
    with flt[0]:
        q = st.text_input(
            t("search"), value="", placeholder=t("cv_search_placeholder"), key="cv_q",
        )
    with flt[1]:
        f_lang = st.selectbox(
            t("voices_filter_lang"), ["any", *LANGS], index=0,
            format_func=lambda c: t("any") if c == "any" else _format_lang(c),
            key="cv_filter_lang",
        )
    with flt[2]:
        f_scope = st.selectbox(
            t("scope"), ["all", "channel", "global"], index=0,
            format_func=lambda v: t(f"scope_{v}"),
            key="cv_filter_scope",
        )

    list_kwargs = {"query": q.strip() or None, "limit": 500}
    if f_lang != "any":
        list_kwargs["language"] = f_lang
    if f_scope == "channel":
        active = _selected_channel()
        list_kwargs["channel_id"] = active.id if active else "__none__"
    elif f_scope == "global":
        list_kwargs["channel_id"] = None
    voices = repo.list(**list_kwargs)

    if not voices:
        st.markdown(
            f"<div class='w-empty'>{t('cv_no_voices')}</div>",
            unsafe_allow_html=True,
        )
        return

    st.caption(t("cv_voices_count").format(n=len(voices)))
    for voice in voices:
        with st.container(border=True):
            top = st.columns([3, 3, 2])
            with top[0]:
                title = f"### 🎤 {voice.name}"
                if voice.parent_id:
                    title += f" <span class='w-pill muted'>variant</span>"
                st.markdown(title, unsafe_allow_html=True)
                if voice.description:
                    st.caption(voice.description)
                pills = [
                    f"<span class='w-pill muted'>{_format_lang(voice.language)}</span>",
                    f"<span class='w-pill muted'>{t('cv_speed')}: {voice.speed}</span>",
                    f"<span class='w-pill muted'>{t('cv_pitch')}: {voice.pitch}</span>",
                    f"<span class='w-pill muted'>{t('cv_emotion')}: {voice.emotion}</span>",
                    f"<span class='w-pill muted'>{t('cv_clarity')}: {voice.clarity}</span>",
                    f"<span class='w-pill muted'>{t('cv_intensity')}: {voice.intensity}</span>",
                    f"<span class='w-pill muted'>{t('cv_use_case')}: {voice.use_case}</span>",
                ]
                st.markdown("".join(pills), unsafe_allow_html=True)
                bindings = []
                if voice.channel_id:
                    chan = channel_repo.get(voice.channel_id)
                    bindings.append(f"📺 {chan.name if chan else voice.channel_id}")
                if voice.bound_style:
                    bindings.append(f"🎨 {t('translate_style')}: {voice.bound_style}")
                if voice.bound_video_use_case:
                    bindings.append(f"🎬 {voice.bound_video_use_case}")
                if bindings:
                    st.caption(" · ".join(bindings))
                if voice.sample_path:
                    sample = Path(voice.sample_path)
                    if sample.exists():
                        st.audio(str(sample))
                    else:
                        st.caption(t("cv_sample_missing"))
                else:
                    st.caption(t("cv_no_sample"))
                if voice.consent_given:
                    st.caption(t("cv_consent_confirmed_at").format(ts=voice.consent_at or "—"))
            with top[1]:
                with st.popover(t("cv_preview_button"), use_container_width=True):
                    sample_text_default = {
                        "ru": "Привет! Это тестовая озвучка моего голоса.",
                        "tk": "Salam! Bu meniň sesimiň synag ýazgysy.",
                        "tr": "Merhaba! Bu sesimin örnek seslendirilmesidir.",
                        "en": "Hello! This is a quick preview of my voice.",
                    }.get(voice.language, "Hello!")
                    text_input = st.text_area(
                        t("translate_input_placeholder"),
                        value=sample_text_default,
                        height=80,
                        key=f"cv_pv_{voice.id}",
                    )
                    if st.button(t("cv_preview_button"), type="primary", key=f"cv_pv_btn_{voice.id}"):
                        try:
                            if voice.language == "tk":
                                tts = get_tts()
                                wav = tts.synthesize(text_input, emotion=voice.emotion or "neutral")
                                st.audio(wav)
                                st.caption(t("cv_preview_caption_tk"))
                            else:
                                st.warning(t("cv_preview_warn_other_lang"))
                        except Exception as exc:  # noqa: BLE001
                            logger.exception("preview failed")
                            st.error(t("translate_failed").format(error=exc))
            with top[2]:
                if st.button(t("cv_variant_button"), key=f"cv_var_{voice.id}", use_container_width=True):
                    st.session_state["cv_create_parent"] = voice.id
                    st.toast(t("cv_variant_toast"))
                with st.popover(t("edit"), use_container_width=True):
                    e_name = st.text_input(t("name"), value=voice.name, key=f"cv_e_n_{voice.id}")
                    e_desc = st.text_area(t("description"), value=voice.description or "", key=f"cv_e_d_{voice.id}")
                    e_speed = st.selectbox(
                        t("cv_speed"), [s.code for s in speeds],
                        index=[s.code for s in speeds].index(voice.speed)
                        if voice.speed in [s.code for s in speeds] else 1,
                        format_func=_fmt(speeds), key=f"cv_e_sp_{voice.id}",
                    )
                    e_pitch = st.selectbox(
                        t("cv_pitch"), [p.code for p in pitches],
                        index=[p.code for p in pitches].index(voice.pitch)
                        if voice.pitch in [p.code for p in pitches] else 1,
                        format_func=_fmt(pitches), key=f"cv_e_pi_{voice.id}",
                    )
                    e_emotion = st.selectbox(
                        t("cv_emotion"), [e.code for e in emotions],
                        index=[e.code for e in emotions].index(voice.emotion)
                        if voice.emotion in [e.code for e in emotions] else 0,
                        format_func=_fmt(emotions), key=f"cv_e_em_{voice.id}",
                    )
                    e_clarity = st.selectbox(
                        t("cv_clarity"), [c.code for c in clarities],
                        index=[c.code for c in clarities].index(voice.clarity)
                        if voice.clarity in [c.code for c in clarities] else 0,
                        format_func=_fmt(clarities), key=f"cv_e_cl_{voice.id}",
                    )
                    e_intensity = st.selectbox(
                        t("cv_intensity"), [i.code for i in intensities],
                        index=[i.code for i in intensities].index(voice.intensity)
                        if voice.intensity in [i.code for i in intensities] else 1,
                        format_func=_fmt(intensities), key=f"cv_e_in_{voice.id}",
                    )
                    e_uc = st.selectbox(
                        t("cv_use_case"), [u.code for u in cv_use_cases],
                        index=[u.code for u in cv_use_cases].index(voice.use_case)
                        if voice.use_case in [u.code for u in cv_use_cases] else 0,
                        format_func=_fmt(cv_use_cases), key=f"cv_e_uc_{voice.id}",
                    )
                    if st.button(t("save"), type="primary", key=f"cv_e_save_{voice.id}"):
                        repo.update(
                            voice.id,
                            name=e_name,
                            description=e_desc or None,
                            speed=e_speed,
                            pitch=e_pitch,
                            emotion=e_emotion,
                            clarity=e_clarity,
                            intensity=e_intensity,
                            use_case=e_uc,
                        )
                        st.success(t("updated"))
                        st.rerun()
                if st.button("🗑️ " + t("delete"), key=f"cv_del_{voice.id}", use_container_width=True):
                    service.delete(voice.id)
                    st.rerun()


def _render_voices_tab() -> None:
    sub_catalog, sub_custom = st.tabs(
        [t("voices_catalog_heading"), t("voices_my_heading")]
    )
    with sub_catalog:
        _render_voices_catalog()
    with sub_custom:
        _render_custom_voices()


with tab_voices:
    _render_voices_tab()


# ---------------------------------------------------------------------------
# Publish tab
# ---------------------------------------------------------------------------


def _render_publish_tab() -> None:
    storage = _bootstrap_storage()
    repo: PublishingRepository = storage["publishing_repo"]
    service: PublishingService = storage["publishing_service"]
    channel_repo: ChannelRepository = storage["channel_repo"]
    active_channel = _selected_channel()

    st.markdown(f"### {t('publish_heading')}")
    st.caption(t("publish_caption"))
    st.warning(t("publish_auth_warning"))

    platforms = list_platforms()

    # ---------------- Create form ----------------
    with st.expander(t("publish_create"), expanded=False):
        with st.form("create_publish", clear_on_submit=True):
            row = st.columns([2, 1, 1])
            with row[0]:
                p_name = st.text_input(
                    t("name"),
                    placeholder=t("publish_name_placeholder"),
                    key="pub_name",
                )
            with row[1]:
                p_kind = st.selectbox(
                    t("publish_kind"),
                    ["video", "audio"],
                    index=0,
                    format_func=lambda v: t(f"publish_kind_{v}"),
                    key="pub_kind",
                )
            with row[2]:
                p_lang = st.selectbox(
                    t("language"),
                    LANGS,
                    index=LANGS.index("ru"),
                    format_func=_format_lang,
                    key="pub_lang",
                )

            p_title = st.text_input(t("publish_title_field"), key="pub_title")
            p_desc = st.text_area(
                t("publish_description_field"), height=120, key="pub_desc"
            )

            row2 = st.columns(2)
            with row2[0]:
                p_tags_raw = st.text_input(t("publish_tags_field"), key="pub_tags")
            with row2[1]:
                p_hashtags_raw = st.text_input(t("publish_hashtags_field"), key="pub_hashtags")

            p_platforms = st.multiselect(
                t("publish_platforms"),
                [p.platform.value for p in platforms],
                default=["youtube", "tiktok"],
                format_func=lambda code: f"{next((p.icon for p in platforms if p.platform.value == code), '')} "
                                         f"{next((p.label for p in platforms if p.platform.value == code), code)}",
                key="pub_platforms",
            )

            channels = channel_repo.list(limit=200)
            channel_choices = [None, *[c.id for c in channels]]
            default_channel_idx = (
                channel_choices.index(active_channel.id)
                if active_channel and active_channel.id in channel_choices
                else 0
            )
            p_channel = st.selectbox(
                t("sidebar_channels"),
                channel_choices,
                index=default_channel_idx,
                format_func=lambda v: t("sidebar_global") if v is None else next(
                    (c.name for c in channels if c.id == v), v
                ),
                key="pub_channel",
            )

            p_media = st.file_uploader(
                t("media_upload"),
                type=["mp4", "mkv", "mov", "webm", "wav", "mp3", "m4a", "ogg", "flac"],
                key="pub_media",
            )

            if st.form_submit_button(t("create"), type="primary"):
                if not p_name.strip() or not p_title.strip():
                    st.warning(t("both_required"))
                else:
                    tags = [s.strip() for s in (p_tags_raw or "").split(",") if s.strip()]
                    hashtags = [s.strip() for s in (p_hashtags_raw or "").split() if s.strip()]
                    media_bytes = p_media.read() if p_media is not None else None
                    media_filename = p_media.name if p_media is not None else None
                    try:
                        service.create(
                            name=p_name,
                            title=p_title,
                            kind=p_kind,
                            language=p_lang,
                            channel_id=p_channel,
                            description=p_desc.strip() or None,
                            tags=tags,
                            hashtags=hashtags,
                            target_platforms=p_platforms,
                            media_bytes=media_bytes,
                            media_filename=media_filename,
                        )
                        st.success("OK")
                        st.rerun()
                    except Exception as exc:  # noqa: BLE001
                        logger.exception("publishing create failed")
                        st.error(f"Failed: {exc}")

    # ---------------- List ----------------
    cols = st.columns([3, 1, 1])
    with cols[0]:
        q = st.text_input(t("search"), value="", key="pub_q")
    with cols[1]:
        f_lang = st.selectbox(
            t("language"), ["any", *LANGS], index=0,
            format_func=lambda c: t("any") if c == "any" else _format_lang(c),
            key="pub_filter_lang",
        )
    with cols[2]:
        f_status = st.selectbox(
            t("status"),
            ["any", "draft", "exported", "published"],
            index=0,
            format_func=lambda v: t("any") if v == "any" else t(f"publish_status_{v}"),
            key="pub_filter_status",
        )

    list_kwargs = {"query": q.strip() or None, "limit": 500}
    if f_lang != "any":
        list_kwargs["language"] = f_lang
    if f_status != "any":
        list_kwargs["status"] = f_status
    packages = repo.list(**list_kwargs)

    if not packages:
        st.markdown(
            f"<div class='w-empty'>{t('publish_no_packages')}</div>",
            unsafe_allow_html=True,
        )
        return

    st.caption(t("publish_packages_count").format(n=len(packages)))
    for package in packages:
        with st.container(border=True):
            row = st.columns([4, 3])
            with row[0]:
                st.markdown(f"### 📦 {package.name}")
                st.caption(
                    f"{t('publish_kind')}: {t(f'publish_kind_{package.kind}')} · "
                    f"{_format_lang(package.language)} · "
                    f"status: {t(f'publish_status_{package.status}')}"
                )
                st.markdown(f"**{package.title}**")
                if package.description:
                    st.caption(package.description[:280] + ("…" if len(package.description) > 280 else ""))
                meta_pills = []
                if package.tags:
                    meta_pills.append(
                        f"<span class='w-pill muted'>tags: {', '.join(package.tags[:6])}</span>"
                    )
                if package.hashtags:
                    meta_pills.append(
                        f"<span class='w-pill muted'>{' '.join(['#' + h.lstrip('#') for h in package.hashtags[:6]])}</span>"
                    )
                if package.target_platforms:
                    icons = " ".join(
                        next((p.icon for p in platforms if p.platform.value == code), "·")
                        for code in package.target_platforms
                    )
                    meta_pills.append(f"<span class='w-pill'>{icons}</span>")
                if meta_pills:
                    st.markdown("".join(meta_pills), unsafe_allow_html=True)

                if package.media_path:
                    media_file = Path(package.media_path)
                    if media_file.exists():
                        if package.kind == "video":
                            st.video(str(media_file))
                        else:
                            st.audio(str(media_file))
                    else:
                        st.caption("📁 media file missing on disk")
                else:
                    st.caption("📁 no media uploaded")

            with row[1]:
                # Download ZIP — full archive with metadata + per-platform text.
                archive = build_zip_for_package(package)
                st.download_button(
                    t("publish_export"),
                    data=archive,
                    file_name=f"{(package.name or package.id).replace(' ', '_')}.zip",
                    mime="application/zip",
                    key=f"pub_dl_{package.id}",
                    use_container_width=True,
                )
                if st.button(
                    t("publish_mark_exported"),
                    key=f"pub_me_{package.id}",
                    use_container_width=True,
                ):
                    service.mark_exported(package.id)
                    st.rerun()
                # Open external upload page links
                for code in package.target_platforms:
                    descriptor = next(
                        (p for p in platforms if p.platform.value == code), None
                    )
                    if descriptor is None:
                        continue
                    st.link_button(
                        f"{descriptor.icon} {t('publish_open_target')}: {descriptor.label}",
                        descriptor.upload_url,
                        use_container_width=True,
                    )
                if package.status != "published" and st.button(
                    t("publish_mark_published"),
                    key=f"pub_pub_{package.id}",
                    use_container_width=True,
                ):
                    service.mark_published(package.id)
                    st.rerun()
                if st.button(
                    "🗑️ " + t("delete"),
                    key=f"pub_del_{package.id}",
                    use_container_width=True,
                ):
                    service.delete(package.id)
                    st.rerun()

    # Platform reference cards (for users who want to set up direct API later).
    st.markdown("---")
    st.markdown(f"#### {t('publish_supported_platforms')}")
    cards = st.columns(min(len(platforms), 3))
    for i, descriptor in enumerate(platforms):
        with cards[i % len(cards)]:
            with st.container(border=True):
                st.markdown(f"### {descriptor.icon} {descriptor.label}")
                st.caption(descriptor.notes)
                st.link_button(
                    t("publish_open_target"),
                    descriptor.upload_url,
                    use_container_width=True,
                )


with tab_publish:
    _render_publish_tab()
