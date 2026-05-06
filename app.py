"""Streamlit cloud MVP: text + video translation with Turkmen MMS voice.

Models are loaded lazily on first use and kept warm via ``@st.cache_resource``
so subsequent requests do not re-download/re-instantiate the weights.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

import streamlit as st

from src.cloud.asr import ASRService
from src.cloud.config import LANG_CODE_MAP, SUPPORTED_ROUTES
from src.cloud.language import detect_lang
from src.cloud.translator import TranslatorService
from src.cloud.tts_mms import MMSTurkmenTTS
from src.cloud.video_io import download_video, extract_wav

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

LANGS = sorted(LANG_CODE_MAP.keys())  # ["en", "ru", "tk", "tr"]


# ---------------------------------------------------------------------------
# Cached service factories — built once per Streamlit session.
# ---------------------------------------------------------------------------


@st.cache_resource(show_spinner="Loading translation model…")
def get_translator() -> TranslatorService:
    return TranslatorService()


@st.cache_resource(show_spinner="Loading speech recogniser…")
def get_asr(model_name: str) -> ASRService:
    return ASRService(model_name=model_name)


@st.cache_resource(show_spinner="Loading Turkmen voice…")
def get_tts() -> MMSTurkmenTTS:
    return MMSTurkmenTTS()


def _translate_safe(translator: TranslatorService, text: str, src: str, tgt: str) -> str:
    if (src, tgt) not in SUPPORTED_ROUTES:
        raise ValueError(f"Unsupported direction: {src}->{tgt}")
    return translator.translate(text, src, tgt)


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------


st.set_page_config(
    page_title="Warehouse AI Engine — Translator",
    page_icon="🌍",
    layout="centered",
)

st.title("🌍 Warehouse AI Engine — RU/TK/TR/EN translator + Turkmen voice")
st.caption(
    "Text + audio + video translation in any direction between ru / tk / tr / en. "
    "Turkmen output can be voiced with the offline Meta MMS-TTS model."
)

with st.sidebar:
    st.header("Settings")
    asr_model = st.selectbox(
        "Whisper size",
        ["tiny", "base", "small", "medium"],
        index=2,
        help="'tiny' / 'base' are fast on CPU; 'small' is the best quality/speed trade-off.",
    )

# ---------------------------------------------------------------------------
# Tab 1 — text translation
# ---------------------------------------------------------------------------

tab_text, tab_video = st.tabs(["Text", "Audio / Video / URL"])

with tab_text:
    st.subheader("Text translation")
    txt = st.text_area("Input text", height=160, key="text-input")
    c1, c2 = st.columns(2)
    with c1:
        src = st.selectbox("Source", LANGS, index=LANGS.index("ru"), key="text-src")
    with c2:
        tgt = st.selectbox("Target", LANGS, index=LANGS.index("tk"), key="text-tgt")
    auto = st.checkbox("Auto-detect source (ru/en/tr only)", value=False)

    voice_emotion = st.selectbox(
        "Turkmen voice emotion (used only when target=tk)",
        ["neutral", "happy", "sad", "angry"],
        index=0,
        key="text-emotion",
    )

    if st.button("Translate text", type="primary"):
        if not txt.strip():
            st.warning("Type or paste some text first.")
        else:
            try:
                translator = get_translator()
                source = detect_lang(txt) if auto else src
                if source == "unknown":
                    st.warning("Could not auto-detect language. Falling back to the dropdown.")
                    source = src
                result = _translate_safe(translator, txt.strip(), source, tgt)
                st.success(f"{source} → {tgt}")
                st.markdown(f"**Translation:**\n\n{result}")
                if tgt == "tk" and result:
                    tts = get_tts()
                    wav = tts.synthesize(result, emotion=voice_emotion)
                    st.audio(wav)
            except Exception as exc:  # noqa: BLE001 - shown to the user
                logger.exception("text translation failed")
                st.error(f"Failed: {exc}")

# ---------------------------------------------------------------------------
# Tab 2 — video / URL pipeline (download -> ASR -> translate -> TTS)
# ---------------------------------------------------------------------------

with tab_video:
    st.subheader("Audio / video / URL")
    st.caption(
        "Paste a YouTube / TikTok URL or upload a media file. The app will "
        "extract audio, transcribe, translate and (for tk) re-voice it."
    )

    url = st.text_input("Media URL", placeholder="https://www.youtube.com/watch?v=…")
    upl = st.file_uploader(
        "…or upload a file",
        type=["mp4", "mkv", "mov", "webm", "wav", "mp3", "m4a", "ogg"],
    )

    c3, c4 = st.columns(2)
    with c3:
        target = st.selectbox("Target language", LANGS, index=LANGS.index("tk"), key="vid-tgt")
    with c4:
        manual_src = st.selectbox(
            "Source (or auto)",
            ["auto", "ru", "en", "tr", "tk"],
            index=0,
            key="vid-src",
        )
    emo = st.selectbox(
        "Turkmen voice emotion",
        ["neutral", "happy", "sad", "angry"],
        index=0,
        key="vid-emotion",
    )

    if st.button("Process media", type="primary"):
        if not url.strip() and upl is None:
            st.warning("Provide a URL or upload a file.")
            st.stop()
        try:
            with st.status("Working…", expanded=True) as status:
                # --- 1. Get a local file path for the source media -----
                if url.strip():
                    status.write("⬇️ Downloading media…")
                    media_path = download_video(url.strip())
                else:
                    suffix = Path(upl.name).suffix or ".mp4"
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                        tmp.write(upl.read())
                        media_path = Path(tmp.name)
                    status.write(f"📁 Using uploaded file `{media_path.name}`")

                # --- 2. Extract audio -----
                status.write("🎧 Extracting audio…")
                wav = extract_wav(media_path)

                # --- 3. ASR -----
                status.write(f"🗣️ Transcribing with whisper-{asr_model}…")
                asr = get_asr(asr_model)
                asr_lang = None if manual_src == "auto" else manual_src
                source_text = asr.transcribe(str(wav), language=asr_lang)
                if not source_text:
                    raise RuntimeError("Transcription returned empty text.")

                # --- 4. Decide source language -----
                if manual_src == "auto":
                    detected = detect_lang(source_text)
                    src_lang = detected if detected != "unknown" else "ru"
                else:
                    src_lang = manual_src

                # --- 5. Translate -----
                status.write(f"🌐 Translating {src_lang} → {target}…")
                translator = get_translator()
                translated = _translate_safe(translator, source_text, src_lang, target)

                # --- 6. Voice (only Turkmen) -----
                voiced_path = None
                if target == "tk" and translated:
                    status.write("🔊 Generating Turkmen voice…")
                    voiced_path = get_tts().synthesize(translated, emotion=emo)

                status.update(label="Done", state="complete")

            st.markdown("### 🗒️ Transcript")
            st.write(source_text)
            st.markdown(f"### 🌐 Translation ({src_lang} → {target})")
            st.write(translated)
            if voiced_path:
                st.markdown("### 🔊 Turkmen voice")
                st.audio(voiced_path)
        except Exception as exc:  # noqa: BLE001 - shown to the user
            logger.exception("media pipeline failed")
            st.error(f"Failed: {exc}")
