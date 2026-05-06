"""Streamlit cloud app — Warehouse AI Translator.

Three sections (tabs):
  * Translate — text translation with style + Turkmen voice
  * Audio / Video / URL — pipeline: download → ASR → translate → TTS
  * My Dictionary — user glossary CRUD + search, Translation Memory CRUD

Models are loaded lazily on first use and cached via ``@st.cache_resource``.
The user glossary and translation memory live in a local SQLite database
(see ``src/storage``); switch to PostgreSQL by setting ``DATABASE_URL``.
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
    GlossaryRepository,
    TranslationMemoryRepository,
)
from src.translator.styles import StyleProfile, list_styles
from src.translator.translation_memory import TranslationMemoryService
from src.translator.user_glossary import UserGlossaryService
from src.ui.theme import inject as inject_theme

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

LANGS = sorted(LANG_CODE_MAP.keys())  # ["en", "ru", "tk", "tr"]
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
    """Init the SQLite schema and return the repositories + services."""
    init_db()
    glossary_repo = GlossaryRepository()
    tm_repo = TranslationMemoryRepository()
    user_glossary = UserGlossaryService(glossary_repo)
    translation_memory = TranslationMemoryService(tm_repo)
    return {
        "glossary_repo": glossary_repo,
        "tm_repo": tm_repo,
        "user_glossary": user_glossary,
        "translation_memory": translation_memory,
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


def _format_lang(code: str) -> str:
    return LANG_LABELS.get(code, code)


def _style_options() -> list[StyleProfile]:
    return list_styles()


def _style_label(profile: StyleProfile) -> str:
    return f"{profile.label_ru} — {profile.description}"


# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------


st.set_page_config(
    page_title="Warehouse AI Translator",
    page_icon="🌐",
    layout="wide",
    menu_items={
        "About": "Warehouse AI Engine — open-source RU/TK/TR/EN translator with Turkmen voice."
    },
)
inject_theme(st)


with st.sidebar:
    st.markdown("### ⚙️ Settings")
    asr_model = st.selectbox(
        "Whisper size",
        ["tiny", "base", "small", "medium"],
        index=2,
        help="'tiny'/'base' run fast on CPU; 'small' is the best quality/speed trade-off.",
    )
    st.markdown("---")
    st.caption(
        "User glossary and translation memory are stored locally in "
        "`data/warehouse_ai.db` (SQLite). Set `DATABASE_URL` to use PostgreSQL."
    )


st.markdown(
    """
    <h1>🌐 Warehouse AI Translator</h1>
    <p class="muted">RU · TK · TR · EN — translation, voice, video. Priority: ru ↔ tk literary register.</p>
    """,
    unsafe_allow_html=True,
)

tab_text, tab_media, tab_dict = st.tabs(
    ["✨ Translate", "🎬 Audio / Video / URL", "📚 My Dictionary"]
)


# ---------------------------------------------------------------------------
# Tab 1 — Text translation
# ---------------------------------------------------------------------------


def _render_translate_tab() -> None:
    storage = _bootstrap_storage()
    glossary_repo: GlossaryRepository = storage["glossary_repo"]
    tm: TranslationMemoryService = storage["translation_memory"]

    st.markdown("### Translate text")

    col_a, col_b, col_c = st.columns([2, 2, 2])
    with col_a:
        src = st.selectbox(
            "From",
            LANGS,
            index=LANGS.index("ru"),
            format_func=_format_lang,
            key="t_src",
        )
    with col_b:
        tgt = st.selectbox(
            "To",
            LANGS,
            index=LANGS.index("tk"),
            format_func=_format_lang,
            key="t_tgt",
        )
    with col_c:
        styles = _style_options()
        style_codes = [s.code for s in styles]
        style_default = (
            "literary" if {src, tgt} == {"ru", "tk"} else "neutral"
        )
        style_idx = style_codes.index(style_default) if style_default in style_codes else 0
        style = st.selectbox(
            "Style / Emotion",
            styles,
            index=style_idx,
            format_func=_style_label,
            key="t_style",
        )

    auto = st.checkbox("Auto-detect source language (ru/en/tr)", value=False)

    txt = st.text_area(
        "Text",
        height=160,
        placeholder="Введите текст для перевода…",
        key="t_input",
        label_visibility="collapsed",
    )

    btn_col1, btn_col2 = st.columns([1, 5])
    with btn_col1:
        translate_clicked = st.button("Translate", type="primary", use_container_width=True)
    with btn_col2:
        st.caption(
            "Tip: when target = tk, you can voice the result with the offline MMS-TTS model."
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
                    st.info("Could not auto-detect language — using selected source.")
                else:
                    actual_src = detected
            with st.spinner(f"Translating {actual_src} → {tgt}…"):
                result = translator.translate_full(
                    txt.strip(), actual_src, tgt, style=style.code
                )
            st.session_state["last_translation"] = {
                "source_text": txt.strip(),
                "translated_text": result.text,
                "source_lang": result.source_lang,
                "target_lang": result.target_lang,
                "style": result.style,
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

    pills = []
    pills.append(
        f"<span class='w-pill'>{_format_lang(state['source_lang'])} → {_format_lang(state['target_lang'])}</span>"
    )
    pills.append(f"<span class='w-pill muted'>style: {state['style']}</span>")
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

    # Action row -----------------------------------------------------------------------
    act_a, act_b, act_c = st.columns(3)
    with act_a:
        if state["target_lang"] == "tk" and st.button(
            "🔊 Voice (Turkmen)", use_container_width=True, key="t_voice"
        ):
            try:
                tts = get_tts()
                with st.spinner("Synthesising…"):
                    wav = tts.synthesize(state["translated_text"], emotion="neutral")
                st.audio(wav)
            except Exception as exc:  # noqa: BLE001
                st.error(f"TTS failed: {exc}")
    with act_b:
        with st.popover("✏️ Replace translation"):
            st.caption(
                "Если перевод неверный — введи правильный вариант. Он сохранится в "
                "Translation Memory и будет использоваться автоматически."
            )
            corrected = st.text_area(
                "Correct translation",
                value=state["translated_text"],
                height=120,
                key="replace_text",
            )
            if st.button("Save correction", type="primary", key="save_replace"):
                if corrected.strip() and corrected.strip() != state["translated_text"]:
                    tm.remember(
                        source_text=state["source_text"],
                        target_text=corrected.strip(),
                        source_lang=state["source_lang"],
                        target_lang=state["target_lang"],
                    )
                    st.session_state["last_translation"]["translated_text"] = corrected.strip()
                    st.session_state["last_translation"]["tm_hit"] = True
                    st.session_state["last_translation"]["provider"] = "translation-memory"
                    st.success("Saved to Translation Memory.")
                    st.rerun()
                else:
                    st.info("Nothing changed — translation memory not updated.")
    with act_c:
        with st.popover("📚 Add to dictionary"):
            st.caption(
                "Добавь точное соответствие слова или короткой фразы. Будет применяться "
                "после каждого перевода для этой пары языков."
            )
            with st.form("add_glossary_quick", clear_on_submit=True):
                src_term = st.text_input("Source term", value="")
                tgt_term = st.text_input("Target term", value="")
                whole = st.checkbox("Whole word match", value=True)
                case_sens = st.checkbox("Case sensitive", value=False)
                note = st.text_input("Note (optional)", value="")
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
                    )
                    st.success("Rule saved.")


with tab_text:
    _render_translate_tab()


# ---------------------------------------------------------------------------
# Tab 2 — Media pipeline
# ---------------------------------------------------------------------------


def _render_media_tab() -> None:
    st.markdown("### Audio / video / URL")
    st.caption(
        "Paste a YouTube / TikTok URL or upload a file. The pipeline: "
        "download → ffmpeg → Whisper ASR → NLLB-200 translate → (for tk) MMS-TTS."
    )

    url = st.text_input("Media URL", placeholder="https://www.youtube.com/watch?v=…")
    upl = st.file_uploader(
        "…or upload a file",
        type=["mp4", "mkv", "mov", "webm", "wav", "mp3", "m4a", "ogg"],
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        target = st.selectbox(
            "Target language",
            LANGS,
            index=LANGS.index("tk"),
            format_func=_format_lang,
            key="m_tgt",
        )
    with col2:
        manual_src = st.selectbox(
            "Source language",
            ["auto", *LANGS],
            index=0,
            format_func=lambda c: "Auto-detect" if c == "auto" else _format_lang(c),
            key="m_src",
        )
    with col3:
        styles = _style_options()
        style_codes = [s.code for s in styles]
        style_idx = style_codes.index("literary") if "literary" in style_codes else 0
        style = st.selectbox(
            "Style",
            styles,
            index=style_idx,
            format_func=_style_label,
            key="m_style",
        )

    if st.button("Process media", type="primary", key="m_process"):
        if not url.strip() and upl is None:
            st.warning("Provide a URL or upload a file.")
            st.stop()
        try:
            with st.status("Working…", expanded=True) as status:
                # 1) Source media path
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
                    source_text, src_lang, target, style=style.code
                )

                voiced_path: Optional[str] = None
                if target == "tk" and result.text:
                    status.write("🔊 Generating Turkmen voice…")
                    voiced_path = get_tts().synthesize(result.text, emotion="neutral")

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
# Tab 3 — Dictionary + Translation Memory
# ---------------------------------------------------------------------------


def _render_dictionary_tab() -> None:
    storage = _bootstrap_storage()
    glossary_repo: GlossaryRepository = storage["glossary_repo"]
    tm_repo: TranslationMemoryRepository = storage["tm_repo"]

    sub_dict, sub_tm = st.tabs(["📒 Glossary (words)", "🧠 Translation Memory (phrases)"])

    # ---------------- Glossary ----------------
    with sub_dict:
        st.markdown("### My glossary")
        st.caption(
            "Точные правила замены: «исходник → перевод». Применяются после каждого перевода в выбранной паре языков. "
            "Подходит для слов и устойчивых терминов."
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
                        )
                        st.success("Saved.")

        # Search bar
        search_cols = st.columns([3, 1, 1])
        with search_cols[0]:
            query = st.text_input(
                "Search", value="", placeholder="🔍 Find by source or target text",
                key="g_search",
            )
        with search_cols[1]:
            f_src = st.selectbox(
                "From",
                ["any", *LANGS],
                index=0,
                format_func=lambda c: "Any" if c == "any" else _format_lang(c),
                key="g_filter_src",
            )
        with search_cols[2]:
            f_tgt = st.selectbox(
                "To",
                ["any", *LANGS],
                index=0,
                format_func=lambda c: "Any" if c == "any" else _format_lang(c),
                key="g_filter_tgt",
            )

        entries = glossary_repo.list(
            source_lang=None if f_src == "any" else f_src,
            target_lang=None if f_tgt == "any" else f_tgt,
            query=query.strip() or None,
            limit=500,
        )

        if not entries:
            st.markdown(
                "<div class='w-empty'>No glossary rules yet — add one above.</div>",
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
                        st.caption(", ".join(flags) or "—")
                        if entry.note:
                            st.caption(f"📝 {entry.note}")
                    with cols[3]:
                        edit_key = f"edit_{entry.id}"
                        del_key = f"del_{entry.id}"
                        with st.popover("Edit"):
                            new_src = st.text_input(
                                "Source", value=entry.source_text, key=f"e_src_{entry.id}"
                            )
                            new_tgt = st.text_input(
                                "Target", value=entry.target_text, key=f"e_tgt_{entry.id}"
                            )
                            new_whole = st.checkbox(
                                "Whole word", value=entry.whole_word, key=f"e_w_{entry.id}"
                            )
                            new_case = st.checkbox(
                                "Case sensitive",
                                value=entry.case_sensitive,
                                key=f"e_c_{entry.id}",
                            )
                            new_note = st.text_input(
                                "Note", value=entry.note or "", key=f"e_n_{entry.id}"
                            )
                            if st.button("Save", type="primary", key=edit_key):
                                glossary_repo.update(
                                    entry.id,
                                    source_text=new_src,
                                    target_text=new_tgt,
                                    whole_word=new_whole,
                                    case_sensitive=new_case,
                                    note=new_note or None,
                                )
                                st.success("Updated.")
                                st.rerun()
                        if st.button("🗑️ Delete", key=del_key):
                            glossary_repo.delete(entry.id)
                            st.rerun()

    # ---------------- Translation Memory ----------------
    with sub_tm:
        st.markdown("### Translation Memory")
        st.caption(
            "Запомнившиеся целые фразы. Если ты введёшь точно такой же текст для перевода — "
            "система отдаст сохранённый вариант, минуя модель."
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
                        )
                        st.success("Saved.")

        # Search bar
        tm_cols = st.columns([3, 1, 1])
        with tm_cols[0]:
            tm_query = st.text_input(
                "Search TM", value="", placeholder="🔍 Find by source or target text",
                key="tm_search",
            )
        with tm_cols[1]:
            tm_f_src = st.selectbox(
                "From",
                ["any", *LANGS],
                index=0,
                format_func=lambda c: "Any" if c == "any" else _format_lang(c),
                key="tm_filter_src",
            )
        with tm_cols[2]:
            tm_f_tgt = st.selectbox(
                "To",
                ["any", *LANGS],
                index=0,
                format_func=lambda c: "Any" if c == "any" else _format_lang(c),
                key="tm_filter_tgt",
            )

        tm_entries = tm_repo.list(
            source_lang=None if tm_f_src == "any" else tm_f_src,
            target_lang=None if tm_f_tgt == "any" else tm_f_tgt,
            query=tm_query.strip() or None,
            limit=500,
        )

        if not tm_entries:
            st.markdown(
                "<div class='w-empty'>Translation memory is empty.</div>",
                unsafe_allow_html=True,
            )
        else:
            st.caption(f"{len(tm_entries)} entry(s)")
            for entry in tm_entries:
                with st.container(border=True):
                    cols = st.columns([3, 3, 1, 1])
                    with cols[0]:
                        st.markdown(
                            f"<span class='w-pill muted'>{_format_lang(entry.source_lang)} → "
                            f"{_format_lang(entry.target_lang)}</span>",
                            unsafe_allow_html=True,
                        )
                        st.markdown(f"**{entry.source_text}**")
                    with cols[1]:
                        st.caption("→")
                        st.markdown(entry.target_text)
                        if entry.note:
                            st.caption(f"📝 {entry.note}")
                    with cols[2]:
                        with st.popover("Edit"):
                            new_target = st.text_area(
                                "Target", value=entry.target_text, key=f"tm_e_{entry.id}", height=120
                            )
                            new_note = st.text_input(
                                "Note", value=entry.note or "", key=f"tm_en_{entry.id}"
                            )
                            if st.button(
                                "Save", type="primary", key=f"tm_save_{entry.id}"
                            ):
                                tm_repo.update(
                                    entry.id, target_text=new_target, note=new_note or None
                                )
                                st.success("Updated.")
                                st.rerun()
                    with cols[3]:
                        if st.button("🗑️", key=f"tm_del_{entry.id}"):
                            tm_repo.delete(entry.id)
                            st.rerun()


with tab_dict:
    _render_dictionary_tab()
