"""Murat AI — lightweight Streamlit Cloud preview.

This branch is intentionally self-contained: it does not import heavy AI modules
(Whisper, Torch, Transformers, MMS-TTS). The full product code remains on
issue-2-ai-architecture and is intended for VPS/self-hosted deployment.
"""

from __future__ import annotations

from datetime import datetime

import streamlit as st

st.set_page_config(
    page_title="Murat AI",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded",
)

LANG_LABELS = {
    "ru": "Русский",
    "tk": "Türkmençe",
    "tr": "Türkçe",
    "en": "English",
}

STYLES = [
    "natural",
    "blogger",
    "conversational",
    "street",
    "literary",
    "formal",
    "news",
    "cultural",
    "expressive",
    "dramatic",
    "children",
    "teen",
    "humorous",
    "advertising",
    "expert",
]

TONES = [
    "calm",
    "confident",
    "friendly",
    "warm",
    "serious",
    "cheerful",
    "energetic",
    "respectful",
    "soft",
    "firm",
    "cultural",
    "modern",
    "traditional",
    "simple",
    "deep",
    "emotional",
]

EMOTIONS = ["neutral", "happy", "sad", "serious", "excited", "respectful", "warm"]

VOICE_PROFILES = [
    "tm_male_narrator",
    "tm_female_clear",
    "tm_child_soft",
    "tm_teen_blogger",
    "ru_male_documentary",
    "ru_female_blog",
    "tr_male_confident",
    "tr_female_warm",
    "en_male_news",
    "en_female_natural",
]

CHANNELS = [
    "Main / Universal",
    "Turkmen Culture",
    "Blogger Channel",
    "News Channel",
    "Street / Conversational",
    "Cinema Dubbing",
]

SAMPLE_TRANSLATIONS = {
    ("ru", "tk"): "Salam, bu Murat AI synag terjimesidir. Doly AI modeli VPS-de işe girizilýär.",
    ("tk", "ru"): "Здравствуйте, это тестовый перевод Murat AI. Полная AI-модель запускается на VPS.",
    ("ru", "en"): "Hello, this is a Murat AI preview translation. Full AI mode runs on VPS.",
    ("en", "ru"): "Здравствуйте, это предварительный перевод Murat AI. Полный AI-режим работает на VPS.",
    ("tr", "ru"): "Здравствуйте, это тестовый перевод с турецкого на русский.",
    ("ru", "tr"): "Merhaba, bu Rusçadan Türkçeye test çevirisidir.",
}


def preview_translate(text: str, src: str, tgt: str, style: str, tone: str, emotion: str) -> str:
    if not text.strip():
        return ""
    base = SAMPLE_TRANSLATIONS.get((src, tgt))
    if base is None:
        base = f"[{LANG_LABELS[src]} → {LANG_LABELS[tgt]} preview] {text}"
    return (
        f"{base}\n\n"
        f"Preview settings: style={style}, tone={tone}, emotion={emotion}.\n"
        "Real neural translation, ASR, TTS and dubbing are enabled in the full VPS deployment."
    )


st.sidebar.title("🌐 Murat AI")
ui_lang = st.sidebar.selectbox("Interface language", ["ru", "tk", "tr", "en"], format_func=lambda x: LANG_LABELS[x])
active_channel = st.sidebar.selectbox("AI channel / agent", CHANNELS)
st.sidebar.markdown("---")
st.sidebar.success("Preview mode: UI is online")
st.sidebar.caption("Full AI model: VPS/self-hosted install")

st.title("🌐 Murat AI")
st.subheader("Translator, voiceover and video dubbing for Russian, Turkmen, Turkish and English")
st.info(
    "This is a lightweight Streamlit preview. It proves the interface opens in the browser. "
    "Heavy AI models are intentionally disabled here so Streamlit Cloud does not crash."
)

tab_translate, tab_media, tab_dictionary, tab_memory, tab_channels, tab_voices, tab_publish = st.tabs(
    [
        "✨ Translate",
        "🎬 Audio / Video",
        "📚 Dictionary",
        "🧠 Memory",
        "🤖 Channels",
        "🎙️ Voices",
        "📤 Publish",
    ]
)

with tab_translate:
    st.header("✨ Text translation preview")
    c1, c2, c3 = st.columns(3)
    with c1:
        source_lang = st.selectbox("From", ["ru", "tk", "tr", "en"], format_func=lambda x: LANG_LABELS[x])
    with c2:
        target_lang = st.selectbox("To", ["tk", "ru", "tr", "en"], index=0, format_func=lambda x: LANG_LABELS[x])
    with c3:
        voice = st.selectbox("Voice", VOICE_PROFILES)

    c4, c5, c6 = st.columns(3)
    with c4:
        style = st.selectbox("Style", STYLES, index=0)
    with c5:
        tone = st.selectbox("Tone", TONES, index=2)
    with c6:
        emotion = st.selectbox("Emotion", EMOTIONS, index=0)

    text = st.text_area(
        "Text",
        value="Привет. Я хочу перевести это на чистый туркменский язык и озвучить видео.",
        height=160,
    )
    if st.button("Translate", type="primary"):
        st.text_area(
            "Result",
            value=preview_translate(text, source_lang, target_lang, style, tone, emotion),
            height=220,
        )

with tab_media:
    st.header("🎬 Audio / video dubbing preview")
    uploaded = st.file_uploader("Upload audio/video file", type=["mp3", "wav", "mp4", "mov", "m4a", "webm"])
    target_media_lang = st.selectbox("Target language", ["tk", "ru", "tr", "en"], format_func=lambda x: LANG_LABELS[x])
    st.write("Pipeline planned:")
    st.code("video/audio → speech recognition → translation → voice selection → dubbing → export")
    if uploaded:
        st.warning("Preview mode: file received, but real ASR/TTS/dubbing runs on VPS/full install.")

with tab_dictionary:
    st.header("📚 Personal dictionary / word replacement")
    st.write("Here you will manage words that Murat AI must always translate in your chosen way.")
    term = st.text_input("Source word")
    replacement = st.text_input("Preferred translation")
    scope = st.radio("Scope", ["Global", "Only current channel"], horizontal=True)
    if st.button("Save dictionary rule"):
        st.success(f"Preview saved: {term} → {replacement} ({scope})")

with tab_memory:
    st.header("🧠 Translation memory")
    st.write("Repeated phrases will be remembered per channel/AI-agent in full mode.")
    st.dataframe(
        [
            {"source": "Привет", "target": "Salam", "channel": active_channel},
            {"source": "Спасибо", "target": "Sag boluň", "channel": "Turkmen Culture"},
        ],
        use_container_width=True,
    )

with tab_channels:
    st.header("🤖 Channels / AI agents")
    st.write("Each channel can have its own style, tone, voice, dictionary and translation memory.")
    st.dataframe(
        [
            {"channel": c, "style": "natural", "tone": "friendly", "voice": VOICE_PROFILES[i % len(VOICE_PROFILES)]}
            for i, c in enumerate(CHANNELS)
        ],
        use_container_width=True,
    )

with tab_voices:
    st.header("🎙️ Voice profiles")
    st.write("Preview catalog. Full mode can connect real TTS/voice-cloning providers.")
    for voice_name in VOICE_PROFILES:
        st.markdown(f"- **{voice_name}** — selectable voice profile")
    st.file_uploader("Upload custom voice sample", type=["wav", "mp3", "m4a"])
    st.caption("Voice cloning requires consent and full VPS/provider configuration.")

with tab_publish:
    st.header("📤 Publishing packages")
    st.write("Prepare title, description, tags and upload packages for YouTube/TikTok/etc.")
    title = st.text_input("Video title", "Murat AI preview video")
    description = st.text_area("Description", "Generated with Murat AI")
    platforms = st.multiselect("Platforms", ["YouTube", "TikTok", "Instagram", "Facebook", "Telegram", "X"], ["YouTube"])
    if st.button("Create publishing package"):
        st.success(f"Preview package created for: {', '.join(platforms)}")
        st.json({"title": title, "description": description, "platforms": platforms, "created_at": datetime.utcnow().isoformat()})

st.markdown("---")
st.caption("Murat AI preview branch: streamlit-preview. Full AI branch: issue-2-ai-architecture.")
