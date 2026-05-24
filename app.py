"""Murat AI — Streamlit Cloud preview.

Self-contained preview UI for Murat AI. It avoids heavy AI imports so the
browser preview stays stable, while showing the intended translation, dubbing,
subtitle fitting, voice and publishing workflow.
"""

from __future__ import annotations

from datetime import datetime
from textwrap import shorten

import streamlit as st

st.set_page_config(
    page_title="Murat AI",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded",
)

LANG_LABELS = {"ru": "Русский", "tk": "Türkmençe", "tr": "Türkçe", "en": "English"}
LANGS = ["ru", "tk", "tr", "en"]

I18N = {
    "ru": {
        "brand_subtitle": "Перевод, озвучка и видеодубляж для русского, туркменского, турецкого и английского языков",
        "preview_notice": "Это preview-режим Streamlit. Здесь можно проверить интерфейс, дизайн и логику. Тяжёлые AI-модели отключены, чтобы сайт не падал.",
        "interface_language": "Язык интерфейса",
        "channel_agent": "Канал / AI-агент",
        "preview_online": "Preview-режим: интерфейс работает",
        "full_ai": "Полная AI-модель: VPS/self-hosted",
        "tab_translate": "✨ Перевод",
        "tab_media": "🎬 Видео / аудио",
        "tab_dictionary": "📚 Словарь",
        "tab_memory": "🧠 Память",
        "tab_channels": "🤖 Каналы",
        "tab_voices": "🎙️ Голоса",
        "tab_publish": "📤 Публикация",
        "text_preview": "✨ Перевод текста",
        "from": "С языка",
        "to": "На язык",
        "voice": "Голос",
        "style": "Стиль",
        "tone": "Тон",
        "emotion": "Эмоция",
        "text": "Текст",
        "translate": "Перевести",
        "result": "Результат",
        "video_workspace": "🎬 Видео-дубляж и синхронный перевод",
        "video_left": "1. Исходное видео / аудио",
        "video_right": "2. Переведённый текст и синхронизация",
        "upload_hint": "Перетащи сюда видео или аудио",
        "target_language": "Целевой язык",
        "source_auto": "Исходный язык: автоопределение",
        "fit_settings": "Настройки подгонки текста под время",
        "max_chars": "Макс. символов в строке субтитра",
        "max_lines": "Макс. строк на экран",
        "sync_mode": "Режим синхронизации",
        "sync_soft": "Мягко: естественная речь",
        "sync_strict": "Строго: точное попадание во время",
        "sync_cinematic": "Кино: паузы + эмоции",
        "generate_preview": "Сгенерировать preview-перевод",
        "translated_script": "Готовый переведённый текст",
        "segments": "Сегменты дубляжа",
        "sync_status": "Статус синхронизации",
        "sync_ok": "Текст помещается в заданные интервалы. В полной версии AI будет автоматически укорачивать, делить и подгонять фразы под длительность речи.",
        "dict_title": "📚 Личный словарь / замена слов",
        "dict_desc": "Здесь будут правила: какое слово всегда переводить именно так, глобально или только для выбранного канала.",
        "source_word": "Исходное слово",
        "preferred_translation": "Нужный перевод",
        "scope": "Область",
        "global": "Глобально",
        "current_channel": "Только текущий канал",
        "save_rule": "Сохранить правило",
        "memory_title": "🧠 Память переводов",
        "memory_desc": "Повторяющиеся фразы будут запоминаться отдельно для каждого канала/AI-агента.",
        "channels_title": "🤖 Каналы / AI-агенты",
        "channels_desc": "У каждого канала может быть свой стиль, тон, голос, словарь и память переводов.",
        "voices_title": "🎙️ Голосовые профили",
        "voices_desc": "Каталог голосов. В полной версии можно подключить TTS и пользовательские голоса.",
        "upload_voice": "Загрузить образец своего голоса",
        "voice_notice": "Клонирование голоса требует согласия и настройки полного VPS/provider-режима.",
        "publish_title": "📤 Пакеты публикации",
        "publish_desc": "Подготовка названия, описания, тегов и пакета для YouTube/TikTok/etc.",
        "video_title": "Название видео",
        "description": "Описание",
        "platforms": "Платформы",
        "create_package": "Создать пакет публикации",
    },
    "tk": {
        "brand_subtitle": "Rus, türkmen, türk we iňlis dilleri üçin terjime, seslendirme we wideo dubляž",
        "preview_notice": "Bu Streamlit preview tertibi. Bu ýerde interfeýsi, dizaýny we logikany görüp bolýar. Agyr AI modeller öçürilen.",
        "interface_language": "Interfeýs dili",
        "channel_agent": "Kanal / AI-agent",
        "preview_online": "Preview tertibi: interfeýs işleýär",
        "full_ai": "Doly AI modeli: VPS/self-hosted",
        "tab_translate": "✨ Terjime",
        "tab_media": "🎬 Wideo / audio",
        "tab_dictionary": "📚 Sözlük",
        "tab_memory": "🧠 Ýat",
        "tab_channels": "🤖 Kanallar",
        "tab_voices": "🎙️ Sesler",
        "tab_publish": "📤 Neşir",
        "text_preview": "✨ Tekst terjimesi",
        "from": "Haýsy dilden",
        "to": "Haýsy dile",
        "voice": "Ses",
        "style": "Stil",
        "tone": "Äheň",
        "emotion": "Duýgy",
        "text": "Tekst",
        "translate": "Terjime et",
        "result": "Netije",
        "video_workspace": "🎬 Wideo dubляž we sinhron terjime",
        "video_left": "1. Asyl wideo / audio",
        "video_right": "2. Terjime edilen tekst we sinhronlama",
        "upload_hint": "Wideo ýa-da audio faýly şu ýere goý",
        "target_language": "Maksat dil",
        "source_auto": "Çeşme dili: awtomatiki kesgitlenýär",
        "fit_settings": "Teksti wagta ýerleşdirmek sazlamalary",
        "max_chars": "Subtitr setirindäki iň köp nyşan",
        "max_lines": "Ekranda iň köp setir",
        "sync_mode": "Sinhronlama tertibi",
        "sync_soft": "Ýumşak: tebigy sözleýiş",
        "sync_strict": "Takyk: wagta berk gabat getirmek",
        "sync_cinematic": "Kino: pauza + duýgy",
        "generate_preview": "Preview terjime döret",
        "translated_script": "Taýýar terjime edilen tekst",
        "segments": "Dubляž segmentleri",
        "sync_status": "Sinhron ýagdaýy",
        "sync_ok": "Tekst wagt aralyklaryna ýerleşýär. Doly görnüşde AI sözleri awtomatiki gysgaldar, böler we sesiň wagtyna görä sazlar.",
        "dict_title": "📚 Şahsy sözlük / söz çalyşma",
        "dict_desc": "Bu ýerde sözleriň hemişe nähili terjime edilmelidigi saklanar.",
        "source_word": "Çeşme söz",
        "preferred_translation": "Islenýän terjime",
        "scope": "Ulanylyş çägi",
        "global": "Global",
        "current_channel": "Diňe şu kanal",
        "save_rule": "Düzgüni sakla",
        "memory_title": "🧠 Terjime ýady",
        "memory_desc": "Gaýtalanýan sözlemler her kanal üçin aýratyn ýatda saklanar.",
        "channels_title": "🤖 Kanallar / AI-agentler",
        "channels_desc": "Her kanalyň öz stili, äheňi, sesi, sözlügi we ýady bolup biler.",
        "voices_title": "🎙️ Ses profilleri",
        "voices_desc": "Ses katalogy. Doly görnüşde TTS we şahsy sesler birikdiriler.",
        "upload_voice": "Öz ses nusgaňy ýükle",
        "voice_notice": "Ses klonlamak razylyk we doly VPS/provider sazlamasyny talap edýär.",
        "publish_title": "📤 Neşir paketleri",
        "publish_desc": "YouTube/TikTok/etc üçin at, düşündiriş, taglar we paket taýýarlamak.",
        "video_title": "Wideo ady",
        "description": "Düşündiriş",
        "platforms": "Platformalar",
        "create_package": "Neşir paketini döret",
    },
    "tr": {
        "brand_subtitle": "Rusça, Türkmence, Türkçe ve İngilizce için çeviri, seslendirme ve video dublaj",
        "preview_notice": "Bu Streamlit önizleme modudur. Burada arayüz, tasarım ve mantık kontrol edilir. Ağır AI modeller kapalıdır.",
        "interface_language": "Arayüz dili",
        "channel_agent": "Kanal / AI ajanı",
        "preview_online": "Önizleme modu: arayüz çalışıyor",
        "full_ai": "Tam AI modeli: VPS/self-hosted",
        "tab_translate": "✨ Çeviri",
        "tab_media": "🎬 Video / ses",
        "tab_dictionary": "📚 Sözlük",
        "tab_memory": "🧠 Hafıza",
        "tab_channels": "🤖 Kanallar",
        "tab_voices": "🎙️ Sesler",
        "tab_publish": "📤 Yayın",
        "text_preview": "✨ Metin çevirisi",
        "from": "Kaynak dil",
        "to": "Hedef dil",
        "voice": "Ses",
        "style": "Stil",
        "tone": "Ton",
        "emotion": "Duygu",
        "text": "Metin",
        "translate": "Çevir",
        "result": "Sonuç",
        "video_workspace": "🎬 Video dublaj ve senkron çeviri",
        "video_left": "1. Orijinal video / ses",
        "video_right": "2. Çevrilmiş metin ve senkronizasyon",
        "upload_hint": "Video veya ses dosyasını buraya bırak",
        "target_language": "Hedef dil",
        "source_auto": "Kaynak dil: otomatik algılama",
        "fit_settings": "Metni zamana sığdırma ayarları",
        "max_chars": "Altyazı satırında maksimum karakter",
        "max_lines": "Ekranda maksimum satır",
        "sync_mode": "Senkron modu",
        "sync_soft": "Yumuşak: doğal konuşma",
        "sync_strict": "Sıkı: zamana tam uyum",
        "sync_cinematic": "Sinema: duraklama + duygu",
        "generate_preview": "Önizleme çevirisi oluştur",
        "translated_script": "Hazır çevrilmiş metin",
        "segments": "Dublaj segmentleri",
        "sync_status": "Senkron durumu",
        "sync_ok": "Metin zaman aralıklarına sığıyor. Tam sürümde AI cümleleri otomatik kısaltır, böler ve ses süresine göre ayarlar.",
        "dict_title": "📚 Kişisel sözlük / kelime değiştirme",
        "dict_desc": "Burada kelimelerin her zaman nasıl çevrileceği saklanır.",
        "source_word": "Kaynak kelime",
        "preferred_translation": "Tercih edilen çeviri",
        "scope": "Kapsam",
        "global": "Genel",
        "current_channel": "Sadece bu kanal",
        "save_rule": "Kuralı kaydet",
        "memory_title": "🧠 Çeviri hafızası",
        "memory_desc": "Tekrarlanan ifadeler her kanal için ayrı saklanır.",
        "channels_title": "🤖 Kanallar / AI ajanları",
        "channels_desc": "Her kanalın kendi stili, tonu, sesi, sözlüğü ve hafızası olabilir.",
        "voices_title": "🎙️ Ses profilleri",
        "voices_desc": "Ses kataloğu. Tam sürümde TTS ve özel sesler bağlanır.",
        "upload_voice": "Kendi ses örneğini yükle",
        "voice_notice": "Ses klonlama izin ve tam VPS/provider kurulumu gerektirir.",
        "publish_title": "📤 Yayın paketleri",
        "publish_desc": "YouTube/TikTok/etc için başlık, açıklama, etiket ve paket hazırlama.",
        "video_title": "Video başlığı",
        "description": "Açıklama",
        "platforms": "Platformlar",
        "create_package": "Yayın paketi oluştur",
    },
    "en": {
        "brand_subtitle": "Translator, voiceover and video dubbing for Russian, Turkmen, Turkish and English",
        "preview_notice": "This is a Streamlit preview. You can check the interface, design and workflow. Heavy AI models are disabled so the site does not crash.",
        "interface_language": "Interface language",
        "channel_agent": "Channel / AI agent",
        "preview_online": "Preview mode: UI is online",
        "full_ai": "Full AI model: VPS/self-hosted",
        "tab_translate": "✨ Translate",
        "tab_media": "🎬 Video / audio",
        "tab_dictionary": "📚 Dictionary",
        "tab_memory": "🧠 Memory",
        "tab_channels": "🤖 Channels",
        "tab_voices": "🎙️ Voices",
        "tab_publish": "📤 Publish",
        "text_preview": "✨ Text translation",
        "from": "From",
        "to": "To",
        "voice": "Voice",
        "style": "Style",
        "tone": "Tone",
        "emotion": "Emotion",
        "text": "Text",
        "translate": "Translate",
        "result": "Result",
        "video_workspace": "🎬 Video dubbing and synchronized translation",
        "video_left": "1. Source video / audio",
        "video_right": "2. Translated text and synchronization",
        "upload_hint": "Drop video or audio here",
        "target_language": "Target language",
        "source_auto": "Source language: auto-detect",
        "fit_settings": "Text fitting settings",
        "max_chars": "Max characters per subtitle line",
        "max_lines": "Max lines on screen",
        "sync_mode": "Sync mode",
        "sync_soft": "Soft: natural speech",
        "sync_strict": "Strict: exact timing",
        "sync_cinematic": "Cinema: pauses + emotion",
        "generate_preview": "Generate preview translation",
        "translated_script": "Final translated text",
        "segments": "Dubbing segments",
        "sync_status": "Synchronization status",
        "sync_ok": "Text fits the timing windows. In full mode AI will automatically shorten, split and fit phrases to speech duration.",
        "dict_title": "📚 Personal dictionary / word replacement",
        "dict_desc": "Rules for words that must always be translated your chosen way.",
        "source_word": "Source word",
        "preferred_translation": "Preferred translation",
        "scope": "Scope",
        "global": "Global",
        "current_channel": "Only current channel",
        "save_rule": "Save rule",
        "memory_title": "🧠 Translation memory",
        "memory_desc": "Repeated phrases will be remembered per channel/AI agent.",
        "channels_title": "🤖 Channels / AI agents",
        "channels_desc": "Each channel can have its own style, tone, voice, dictionary and translation memory.",
        "voices_title": "🎙️ Voice profiles",
        "voices_desc": "Voice catalog. Full mode can connect TTS and custom voices.",
        "upload_voice": "Upload custom voice sample",
        "voice_notice": "Voice cloning requires consent and full VPS/provider configuration.",
        "publish_title": "📤 Publishing packages",
        "publish_desc": "Prepare title, description, tags and upload packages for YouTube/TikTok/etc.",
        "video_title": "Video title",
        "description": "Description",
        "platforms": "Platforms",
        "create_package": "Create publishing package",
    },
}

STYLES = ["natural", "blogger", "conversational", "street", "literary", "formal", "news", "cultural", "expressive", "dramatic", "children", "teen", "humorous", "advertising", "expert"]
TONES = ["calm", "confident", "friendly", "warm", "serious", "cheerful", "energetic", "respectful", "soft", "firm", "cultural", "modern", "traditional", "simple", "deep", "emotional"]
EMOTIONS = ["neutral", "happy", "sad", "serious", "excited", "respectful", "warm"]
VOICE_PROFILES = ["tm_male_narrator", "tm_female_clear", "tm_child_soft", "tm_teen_blogger", "ru_male_documentary", "ru_female_blog", "tr_male_confident", "tr_female_warm", "en_male_news", "en_female_natural"]
CHANNELS = ["Main / Universal", "Turkmen Culture", "Blogger Channel", "News Channel", "Street / Conversational", "Cinema Dubbing"]

SAMPLE_TRANSLATIONS = {
    ("ru", "tk"): "Salam. Men bu teksti arassa türkmen diline terjime edip, wideony seslendirmek isleýärin.",
    ("tk", "ru"): "Здравствуйте. Я хочу перевести этот текст и озвучить видео.",
    ("ru", "en"): "Hello. I want to translate this into clean English and voice the video.",
    ("en", "ru"): "Здравствуйте. Я хочу перевести это на русский и озвучить видео.",
    ("tr", "ru"): "Здравствуйте. Это тестовый перевод с турецкого на русский.",
    ("ru", "tr"): "Merhaba. Bunu temiz Türkçeye çevirip videoyu seslendirmek istiyorum.",
}


def tr(key: str) -> str:
    lang = st.session_state.get("ui_lang", "ru")
    return I18N.get(lang, I18N["ru"]).get(key, I18N["en"].get(key, key))


def preview_translate(text: str, src: str, tgt: str, style: str, tone: str, emotion: str) -> str:
    if not text.strip():
        return ""
    base = SAMPLE_TRANSLATIONS.get((src, tgt), f"[{LANG_LABELS[src]} → {LANG_LABELS[tgt]} preview] {text}")
    return f"{base}\n\nstyle={style}; tone={tone}; emotion={emotion}. Full neural translation runs on VPS."


def make_segments(target_lang: str, max_chars: int):
    raw = [
        ("00:00.0", "00:04.2", "Привет. Я хочу перевести это видео.", SAMPLE_TRANSLATIONS.get(("ru", target_lang), "Preview translation for the first phrase.")),
        ("00:04.2", "00:08.5", "Некоторые слова бывают длинные.", "AI will shorten or split long translated phrases so the voice ends on time."),
        ("00:08.5", "00:12.0", "Озвучка должна идти синхронно.", "Dubbing, subtitles and translated text must stay synchronized."),
    ]
    return [
        {"start": s, "end": e, "original": o, "translation": shorten(t, width=max_chars * 2, placeholder="…")}
        for s, e, o, t in raw
    ]


st.markdown(
    """
    <style>
    .block-container {padding-top: 3rem; max-width: 1320px;}
    [data-testid="stSidebar"] {background: linear-gradient(180deg,#161827 0%,#222638 100%);}    
    .studio-card {border: 1px solid rgba(255,255,255,.12); border-radius: 18px; padding: 18px; background: rgba(255,255,255,.035);} 
    .drop-card {border: 2px dashed rgba(125,92,255,.65); border-radius: 22px; padding: 22px; min-height: 300px; background: rgba(125,92,255,.08);} 
    .sync-pill {display:inline-block; padding:6px 10px; border-radius:999px; background:#143d2a; color:#b9ffd8; font-weight:700;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.sidebar.title("🌐 Murat AI")
st.session_state["ui_lang"] = st.sidebar.selectbox(
    "Interface language / Язык интерфейса",
    ["ru", "tk", "tr", "en"],
    format_func=lambda x: LANG_LABELS[x],
    key="ui_lang_select",
)
active_channel = st.sidebar.selectbox(tr("channel_agent"), CHANNELS)
st.sidebar.markdown("---")
st.sidebar.success(tr("preview_online"))
st.sidebar.caption(tr("full_ai"))

st.title("🌐 Murat AI")
st.subheader(tr("brand_subtitle"))
st.info(tr("preview_notice"))

tabs = st.tabs([tr("tab_translate"), tr("tab_media"), tr("tab_dictionary"), tr("tab_memory"), tr("tab_channels"), tr("tab_voices"), tr("tab_publish")])

with tabs[0]:
    st.header(tr("text_preview"))
    c1, c2, c3 = st.columns(3)
    with c1:
        source_lang = st.selectbox(tr("from"), LANGS, format_func=lambda x: LANG_LABELS[x])
    with c2:
        target_lang = st.selectbox(tr("to"), LANGS, index=1, format_func=lambda x: LANG_LABELS[x])
    with c3:
        voice = st.selectbox(tr("voice"), VOICE_PROFILES)
    c4, c5, c6 = st.columns(3)
    with c4:
        style = st.selectbox(tr("style"), STYLES, index=0)
    with c5:
        tone = st.selectbox(tr("tone"), TONES, index=2)
    with c6:
        emotion = st.selectbox(tr("emotion"), EMOTIONS, index=0)
    text = st.text_area(tr("text"), value="Привет. Я хочу перевести это на чистый туркменский язык и озвучить видео.", height=150)
    if st.button(tr("translate"), type="primary"):
        st.text_area(tr("result"), value=preview_translate(text, source_lang, target_lang, style, tone, emotion), height=200)

with tabs[1]:
    st.header(tr("video_workspace"))
    left, right = st.columns([1.05, 1.25], gap="large")
    with left:
        st.markdown(f"<div class='studio-card'><h3>{tr('video_left')}</h3><p>{tr('source_auto')}</p></div>", unsafe_allow_html=True)
        uploaded = st.file_uploader(tr("upload_hint"), type=["mp4", "mov", "webm", "mkv", "mp3", "wav", "m4a"])
        if uploaded:
            suffix = uploaded.name.lower().split(".")[-1]
            if suffix in ["mp4", "mov", "webm", "mkv"]:
                st.video(uploaded)
            else:
                st.audio(uploaded)
        else:
            st.markdown("<div class='drop-card'>🎬<br><br>Drop zone<br><br>Video / Audio preview will appear here</div>", unsafe_allow_html=True)
        with st.expander(tr("fit_settings"), expanded=True):
            max_chars = st.slider(tr("max_chars"), 24, 80, 42)
            max_lines = st.slider(tr("max_lines"), 1, 3, 2)
            sync_mode = st.radio(tr("sync_mode"), [tr("sync_soft"), tr("sync_strict"), tr("sync_cinematic")])
    with right:
        st.markdown(f"<div class='studio-card'><h3>{tr('video_right')}</h3></div>", unsafe_allow_html=True)
        media_target = st.selectbox(tr("target_language"), LANGS, index=1, format_func=lambda x: LANG_LABELS[x], key="media_target")
        if st.button(tr("generate_preview"), type="primary"):
            st.session_state["segments"] = make_segments(media_target, max_chars)
            st.session_state["script"] = "\n".join(row["translation"] for row in st.session_state["segments"])
        script = st.text_area(tr("translated_script"), value=st.session_state.get("script", ""), height=220)
        st.markdown(f"<span class='sync-pill'>✅ {tr('sync_status')}</span>", unsafe_allow_html=True)
        st.caption(tr("sync_ok"))
        if "segments" in st.session_state:
            st.subheader(tr("segments"))
            st.dataframe(st.session_state["segments"], use_container_width=True, hide_index=True)

with tabs[2]:
    st.header(tr("dict_title"))
    st.write(tr("dict_desc"))
    term = st.text_input(tr("source_word"))
    replacement = st.text_input(tr("preferred_translation"))
    scope = st.radio(tr("scope"), [tr("global"), tr("current_channel")], horizontal=True)
    if st.button(tr("save_rule")):
        st.success(f"{term} → {replacement} ({scope})")

with tabs[3]:
    st.header(tr("memory_title"))
    st.write(tr("memory_desc"))
    st.dataframe([
        {"source": "Привет", "target": "Salam", "channel": active_channel},
        {"source": "Спасибо", "target": "Sag boluň", "channel": "Turkmen Culture"},
    ], use_container_width=True)

with tabs[4]:
    st.header(tr("channels_title"))
    st.write(tr("channels_desc"))
    st.dataframe([
        {"channel": c, "style": "natural", "tone": "friendly", "voice": VOICE_PROFILES[i % len(VOICE_PROFILES)]}
        for i, c in enumerate(CHANNELS)
    ], use_container_width=True)

with tabs[5]:
    st.header(tr("voices_title"))
    st.write(tr("voices_desc"))
    for voice_name in VOICE_PROFILES:
        st.markdown(f"- **{voice_name}**")
    st.file_uploader(tr("upload_voice"), type=["wav", "mp3", "m4a"])
    st.caption(tr("voice_notice"))

with tabs[6]:
    st.header(tr("publish_title"))
    st.write(tr("publish_desc"))
    title = st.text_input(tr("video_title"), "Murat AI preview video")
    description = st.text_area(tr("description"), "Generated with Murat AI")
    platforms = st.multiselect(tr("platforms"), ["YouTube", "TikTok", "Instagram", "Facebook", "Telegram", "X"], ["YouTube"])
    if st.button(tr("create_package")):
        st.success(", ".join(platforms))
        st.json({"title": title, "description": description, "platforms": platforms, "created_at": datetime.utcnow().isoformat()})

st.markdown("---")
st.caption("Murat AI preview branch: streamlit-preview. Full AI branch: issue-2-ai-architecture.")
