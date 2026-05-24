"""Murat AI — Streamlit Cloud preview.

Self-contained professional preview UI for Murat AI. Heavy AI imports are not
used here, so the browser preview stays stable while showing the intended
translation, dubbing, voice cloning, avatar, actor voice mapping and export
workflow.
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
        "subtitle": "Профессиональный AI-перевод, озвучка, аватары и видеодубляж для 4 языков",
        "notice": "Preview-режим: здесь показывается интерфейс и рабочая логика. Полные AI-модели запускаются на VPS/self-hosted.",
        "interface_language": "Язык интерфейса",
        "channel_agent": "Канал / AI-агент",
        "online": "Preview работает",
        "full_ai": "Полная нейронка: VPS/self-hosted",
        "tab_translate": "✨ Перевод",
        "tab_studio": "🎬 Dubbing Studio",
        "tab_voice": "🎙️ Голос / аватар",
        "tab_dictionary": "📚 Словарь",
        "tab_memory": "🧠 Память",
        "tab_export": "📦 Экспорт",
        "tab_publish": "📤 Публикация",
        "translate_title": "✨ Перевод текста",
        "from": "С языка",
        "to": "На язык",
        "voice": "Голос",
        "style": "Стиль",
        "tone": "Тон",
        "emotion": "Эмоция",
        "text": "Текст",
        "translate": "Перевести",
        "result": "Результат",
        "studio_title": "🎬 Профессиональная студия дубляжа",
        "studio_hint": "Загрузи видео/аудио или вставь ссылку. Справа появится перевод, тайминг, голоса актёров и подготовка финального видео.",
        "source_box": "Источник",
        "upload_video": "Загрузить видео или аудио",
        "video_url": "Или вставить ссылку на видео",
        "download_source": "Скачать видео по ссылке",
        "pipeline": "Pipeline",
        "target_language": "Целевой язык",
        "cinema_level": "Уровень озвучки",
        "sync_mode": "Синхронизация",
        "max_chars": "Макс. символов в строке",
        "max_lines": "Макс. строк на экран",
        "generate_script": "Сгенерировать перевод и тайминг",
        "translated_text": "Готовый переведённый текст",
        "actor_map": "Актёры и голоса",
        "actor": "Актёр",
        "role": "Роль",
        "assigned_voice": "Назначенный голос",
        "voice_type": "Тип голоса",
        "quality": "Качество",
        "segments": "Сегменты дубляжа",
        "fit_status": "Статус подгонки",
        "fit_ok": "AI должен автоматически сокращать, делить фразы, добавлять паузы и подгонять озвучку под тайминг видео.",
        "voice_title": "🎙️ Свой голос и AI-аватар",
        "voice_hint": "Пользователь может загрузить чистый образец голоса или видеозапись. Система должна очистить шум, проверить качество и создать профессиональный голосовой профиль.",
        "voice_sample": "Загрузить образец голоса",
        "video_sample": "Загрузить видео с лицом/голосом для аватара",
        "avatar_name": "Имя аватара / голоса",
        "consent": "Я подтверждаю согласие на использование этого голоса/видео",
        "noise_clean": "Очистка шума",
        "normalize": "Нормализация громкости",
        "remove_echo": "Удаление эха",
        "quality_check": "Проверка качества",
        "create_voice": "Создать голосовой профиль",
        "avatar_preview": "Preview аватара",
        "export_title": "📦 Готовое видео и файлы для скачивания",
        "export_hint": "После обработки здесь появится финальное видео с дубляжом, субтитры, аудиодорожки и ZIP-пакет.",
        "final_video": "Финальное видео",
        "download_video": "Скачать готовое видео",
        "download_zip": "Скачать ZIP-пакет",
        "subtitle_file": "Скачать субтитры SRT",
        "audio_tracks": "Скачать аудиодорожки",
        "dictionary_title": "📚 Личный словарь / замена слов",
        "dictionary_hint": "Слова и фразы, которые Murat AI всегда должен переводить выбранным способом.",
        "source_word": "Исходное слово",
        "preferred_translation": "Нужный перевод",
        "scope": "Область",
        "save_rule": "Сохранить правило",
        "memory_title": "🧠 Память переводов",
        "memory_hint": "Повторяющиеся фразы будут запоминаться отдельно для каждого канала/AI-агента.",
        "publish_title": "📤 Публикация на платформы",
        "publish_hint": "Выбери платформы, подготовь название, описание, теги и скачай пакет публикации или отправь через API в полной версии.",
        "video_title": "Название видео",
        "description": "Описание",
        "platforms": "Платформы",
        "create_package": "Создать пакет публикации",
    },
    "tk": {
        "subtitle": "4 dil üçin professional AI terjime, seslendirme, awatar we wideo dubляž",
        "notice": "Preview tertibi: interfeýs we iş logikasy görkezilýär. Doly AI modeller VPS/self-hosted-de işleýär.",
        "interface_language": "Interfeýs dili",
        "channel_agent": "Kanal / AI-agent",
        "online": "Preview işleýär",
        "full_ai": "Doly AI: VPS/self-hosted",
        "tab_translate": "✨ Terjime",
        "tab_studio": "🎬 Dubbing Studio",
        "tab_voice": "🎙️ Ses / awatar",
        "tab_dictionary": "📚 Sözlük",
        "tab_memory": "🧠 Ýat",
        "tab_export": "📦 Eksport",
        "tab_publish": "📤 Neşir",
        "translate_title": "✨ Tekst terjimesi",
        "from": "Haýsy dilden",
        "to": "Haýsy dile",
        "voice": "Ses",
        "style": "Stil",
        "tone": "Äheň",
        "emotion": "Duýgy",
        "text": "Tekst",
        "translate": "Terjime et",
        "result": "Netije",
        "studio_title": "🎬 Professional dubляž studiýasy",
        "studio_hint": "Wideo/audio ýükle ýa-da link goý. Sagda terjime, timing, aktýor sesleri we final wideo taýýarlygy peýda bolar.",
        "source_box": "Çeşme",
        "upload_video": "Wideo ýa-da audio ýükle",
        "video_url": "Ýa-da wideo linkini goý",
        "download_source": "Linkden wideo almak",
        "pipeline": "Pipeline",
        "target_language": "Maksat dil",
        "cinema_level": "Seslendirme derejesi",
        "sync_mode": "Sinhronlama",
        "max_chars": "Setirde iň köp nyşan",
        "max_lines": "Ekranda iň köp setir",
        "generate_script": "Terjime we timing döret",
        "translated_text": "Taýýar terjime tekst",
        "actor_map": "Aktýorlar we sesler",
        "actor": "Aktýor",
        "role": "Rol",
        "assigned_voice": "Bellenen ses",
        "voice_type": "Ses görnüşi",
        "quality": "Hil",
        "segments": "Dubляž segmentleri",
        "fit_status": "Ýerleşiş ýagdaýy",
        "fit_ok": "AI sözlemleri awtomatiki gysgaltmaly, bölmeli, pauza goşmaly we seslendirmäni wideo timingine gabat getirmeli.",
        "voice_title": "🎙️ Öz sesiň we AI-awatar",
        "voice_hint": "Ulanyjy arassa ses nusgasyny ýa-da wideo ýazgyny ýükläp biler. Sistema şumy arassalamaly, hili barlamaly we professional ses profilini döretmeli.",
        "voice_sample": "Ses nusgasyny ýükle",
        "video_sample": "Awatar üçin ýüz/ses wideosyny ýükle",
        "avatar_name": "Awatar / ses ady",
        "consent": "Bu ses/wideony ulanmaga razylyk berýärin",
        "noise_clean": "Şumy arassalamak",
        "normalize": "Ses derejesini deňlemek",
        "remove_echo": "Eho aýyrmak",
        "quality_check": "Hil barlagy",
        "create_voice": "Ses profilini döret",
        "avatar_preview": "Awatar preview",
        "export_title": "📦 Taýýar wideo we ýükleme faýllary",
        "export_hint": "Işlenenden soň bu ýerde final dubляž wideo, subtitrler, audio trackler we ZIP paket peýda bolar.",
        "final_video": "Final wideo",
        "download_video": "Taýýar wideony ýükle",
        "download_zip": "ZIP paket ýükle",
        "subtitle_file": "SRT subtitr ýükle",
        "audio_tracks": "Audio trackleri ýükle",
        "dictionary_title": "📚 Şahsy sözlük / söz çalyşma",
        "dictionary_hint": "Murat AI hemişe saýlanan görnüşde terjime etmeli sözler.",
        "source_word": "Çeşme söz",
        "preferred_translation": "Islenýän terjime",
        "scope": "Çäk",
        "save_rule": "Düzgüni sakla",
        "memory_title": "🧠 Terjime ýady",
        "memory_hint": "Gaýtalanýan sözlemler her kanal üçin aýratyn saklanar.",
        "publish_title": "📤 Platformalara neşir",
        "publish_hint": "Platformalary saýla, at/düşündiriş/tag taýýarla we paket ýükle ýa-da doly görnüşde API arkaly iber.",
        "video_title": "Wideo ady",
        "description": "Düşündiriş",
        "platforms": "Platformalar",
        "create_package": "Neşir paketini döret",
    },
    "tr": {
        "subtitle": "4 dil için profesyonel AI çeviri, seslendirme, avatar ve video dublaj",
        "notice": "Preview modu: arayüz ve iş akışı gösterilir. Tam AI modeller VPS/self-hosted çalışır.",
        "interface_language": "Arayüz dili",
        "channel_agent": "Kanal / AI ajanı",
        "online": "Preview çalışıyor",
        "full_ai": "Tam AI: VPS/self-hosted",
        "tab_translate": "✨ Çeviri",
        "tab_studio": "🎬 Dubbing Studio",
        "tab_voice": "🎙️ Ses / avatar",
        "tab_dictionary": "📚 Sözlük",
        "tab_memory": "🧠 Hafıza",
        "tab_export": "📦 Dışa aktar",
        "tab_publish": "📤 Yayın",
        "translate_title": "✨ Metin çevirisi",
        "from": "Kaynak dil",
        "to": "Hedef dil",
        "voice": "Ses",
        "style": "Stil",
        "tone": "Ton",
        "emotion": "Duygu",
        "text": "Metin",
        "translate": "Çevir",
        "result": "Sonuç",
        "studio_title": "🎬 Profesyonel dublaj stüdyosu",
        "studio_hint": "Video/ses yükle veya link ekle. Sağda çeviri, zamanlama, oyuncu sesleri ve final video hazırlığı görünür.",
        "source_box": "Kaynak",
        "upload_video": "Video veya ses yükle",
        "video_url": "Veya video linki ekle",
        "download_source": "Linkten video al",
        "pipeline": "Pipeline",
        "target_language": "Hedef dil",
        "cinema_level": "Seslendirme seviyesi",
        "sync_mode": "Senkronizasyon",
        "max_chars": "Satır başına maks. karakter",
        "max_lines": "Ekranda maks. satır",
        "generate_script": "Çeviri ve zamanlama oluştur",
        "translated_text": "Hazır çevrilmiş metin",
        "actor_map": "Oyuncular ve sesler",
        "actor": "Oyuncu",
        "role": "Rol",
        "assigned_voice": "Atanan ses",
        "voice_type": "Ses tipi",
        "quality": "Kalite",
        "segments": "Dublaj segmentleri",
        "fit_status": "Uyum durumu",
        "fit_ok": "AI cümleleri otomatik kısaltmalı, bölmeli, duraklama eklemeli ve sesi video zamanına uydurmalıdır.",
        "voice_title": "🎙️ Kendi sesin ve AI-avatar",
        "voice_hint": "Kullanıcı temiz ses örneği veya video yükleyebilir. Sistem gürültüyü temizler, kaliteyi kontrol eder ve profesyonel ses profili oluşturur.",
        "voice_sample": "Ses örneği yükle",
        "video_sample": "Avatar için yüz/ses videosu yükle",
        "avatar_name": "Avatar / ses adı",
        "consent": "Bu ses/video kullanımına izin veriyorum",
        "noise_clean": "Gürültü temizleme",
        "normalize": "Ses normalizasyonu",
        "remove_echo": "Yankı kaldırma",
        "quality_check": "Kalite kontrolü",
        "create_voice": "Ses profili oluştur",
        "avatar_preview": "Avatar preview",
        "export_title": "📦 Hazır video ve indirilecek dosyalar",
        "export_hint": "İşlemden sonra final dublaj video, altyazılar, ses kanalları ve ZIP paket burada görünür.",
        "final_video": "Final video",
        "download_video": "Hazır videoyu indir",
        "download_zip": "ZIP paket indir",
        "subtitle_file": "SRT altyazı indir",
        "audio_tracks": "Ses kanallarını indir",
        "dictionary_title": "📚 Kişisel sözlük / kelime değiştirme",
        "dictionary_hint": "Murat AI'nin her zaman seçilen şekilde çevirmesi gereken kelimeler.",
        "source_word": "Kaynak kelime",
        "preferred_translation": "Tercih edilen çeviri",
        "scope": "Kapsam",
        "save_rule": "Kuralı kaydet",
        "memory_title": "🧠 Çeviri hafızası",
        "memory_hint": "Tekrarlanan ifadeler her kanal için ayrı saklanır.",
        "publish_title": "📤 Platformlara yayın",
        "publish_hint": "Platform seç, başlık/açıklama/tag hazırla ve paket indir veya tam sürümde API ile gönder.",
        "video_title": "Video başlığı",
        "description": "Açıklama",
        "platforms": "Platformlar",
        "create_package": "Yayın paketi oluştur",
    },
    "en": {
        "subtitle": "Professional AI translation, voiceover, avatars and video dubbing for 4 languages",
        "notice": "Preview mode: this shows the interface and workflow. Full AI models run on VPS/self-hosted.",
        "interface_language": "Interface language",
        "channel_agent": "Channel / AI agent",
        "online": "Preview is online",
        "full_ai": "Full neural engine: VPS/self-hosted",
        "tab_translate": "✨ Translate",
        "tab_studio": "🎬 Dubbing Studio",
        "tab_voice": "🎙️ Voice / avatar",
        "tab_dictionary": "📚 Dictionary",
        "tab_memory": "🧠 Memory",
        "tab_export": "📦 Export",
        "tab_publish": "📤 Publish",
        "translate_title": "✨ Text translation",
        "from": "From",
        "to": "To",
        "voice": "Voice",
        "style": "Style",
        "tone": "Tone",
        "emotion": "Emotion",
        "text": "Text",
        "translate": "Translate",
        "result": "Result",
        "studio_title": "🎬 Professional dubbing studio",
        "studio_hint": "Upload video/audio or paste a link. Translation, timing, actor voices and final video preparation appear on the right.",
        "source_box": "Source",
        "upload_video": "Upload video or audio",
        "video_url": "Or paste video URL",
        "download_source": "Download video from URL",
        "pipeline": "Pipeline",
        "target_language": "Target language",
        "cinema_level": "Voiceover level",
        "sync_mode": "Synchronization",
        "max_chars": "Max characters per line",
        "max_lines": "Max lines on screen",
        "generate_script": "Generate translation and timing",
        "translated_text": "Final translated text",
        "actor_map": "Actors and voices",
        "actor": "Actor",
        "role": "Role",
        "assigned_voice": "Assigned voice",
        "voice_type": "Voice type",
        "quality": "Quality",
        "segments": "Dubbing segments",
        "fit_status": "Fit status",
        "fit_ok": "AI must automatically shorten, split phrases, add pauses and fit voiceover to video timing.",
        "voice_title": "🎙️ Custom voice and AI avatar",
        "voice_hint": "Users can upload a clean voice sample or video recording. The system should remove noise, check quality and create a professional voice profile.",
        "voice_sample": "Upload voice sample",
        "video_sample": "Upload face/voice video for avatar",
        "avatar_name": "Avatar / voice name",
        "consent": "I confirm consent to use this voice/video",
        "noise_clean": "Noise cleanup",
        "normalize": "Loudness normalization",
        "remove_echo": "Echo removal",
        "quality_check": "Quality check",
        "create_voice": "Create voice profile",
        "avatar_preview": "Avatar preview",
        "export_title": "📦 Final video and downloads",
        "export_hint": "After processing, final dubbed video, subtitles, audio tracks and a ZIP package appear here.",
        "final_video": "Final video",
        "download_video": "Download final video",
        "download_zip": "Download ZIP package",
        "subtitle_file": "Download SRT subtitles",
        "audio_tracks": "Download audio tracks",
        "dictionary_title": "📚 Personal dictionary / word replacement",
        "dictionary_hint": "Words and phrases Murat AI must always translate your chosen way.",
        "source_word": "Source word",
        "preferred_translation": "Preferred translation",
        "scope": "Scope",
        "save_rule": "Save rule",
        "memory_title": "🧠 Translation memory",
        "memory_hint": "Repeated phrases will be remembered separately for each channel/AI agent.",
        "publish_title": "📤 Publish to platforms",
        "publish_hint": "Select platforms, prepare title, description, tags and download package or send via API in full mode.",
        "video_title": "Video title",
        "description": "Description",
        "platforms": "Platforms",
        "create_package": "Create publishing package",
    },
}

STYLES = ["natural", "blogger", "conversational", "street", "literary", "formal", "news", "cultural", "expressive", "dramatic", "children", "teen", "humorous", "advertising", "expert"]
TONES = ["calm", "confident", "friendly", "warm", "serious", "cheerful", "energetic", "respectful", "soft", "firm", "cultural", "modern", "traditional", "simple", "deep", "emotional"]
EMOTIONS = ["neutral", "happy", "sad", "serious", "excited", "respectful", "warm"]
VOICE_LEVELS = ["Clean studio", "Blog / natural", "Cinema", "Documentary", "Cartoon", "News", "Commercial"]
SYNC_MODES = ["Soft natural", "Strict timing", "Cinematic pauses", "Subtitle first", "Voice first"]
VOICE_PROFILES = ["tm_male_narrator", "tm_female_clear", "tm_child_soft", "tm_teen_blogger", "ru_male_documentary", "ru_female_blog", "tr_male_confident", "tr_female_warm", "en_male_news", "en_female_natural", "custom_voice_01", "custom_actor_avatar"]
CHANNELS = ["Main / Universal", "Turkmen Culture", "Blogger Channel", "News Channel", "Street / Conversational", "Cinema Dubbing"]
PLATFORMS = ["YouTube", "TikTok", "Instagram", "Facebook", "Telegram", "X", "Download to computer"]

SAMPLE_TRANSLATIONS = {
    ("ru", "tk"): "Salam. Men bu wideony arassa türkmen diline terjime edip, professional derejede seslendirmek isleýärin.",
    ("tk", "ru"): "Здравствуйте. Я хочу перевести это видео и сделать профессиональную озвучку.",
    ("ru", "en"): "Hello. I want to translate this video into clean English and create professional dubbing.",
    ("en", "ru"): "Здравствуйте. Я хочу перевести это видео на русский и сделать профессиональную озвучку.",
    ("tr", "ru"): "Здравствуйте. Это тестовый перевод с турецкого на русский.",
    ("ru", "tr"): "Merhaba. Bu videoyu temiz Türkçeye çevirip profesyonel dublaj yapmak istiyorum.",
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
        ("00:00.0", "00:04.2", "Actor 1", "Привет. Я хочу перевести это видео.", SAMPLE_TRANSLATIONS.get(("ru", target_lang), "Preview translation for the first phrase.")),
        ("00:04.2", "00:08.5", "Actor 2", "Некоторые слова бывают длинные.", "AI shortens or splits long translated phrases so the voice ends exactly on time."),
        ("00:08.5", "00:12.0", "Narrator", "Озвучка должна идти синхронно.", "Dubbing, subtitles and translated text stay synchronized with the original video."),
    ]
    return [
        {"start": s, "end": e, "speaker": sp, "original": o, "translation": shorten(t, width=max_chars * 2, placeholder="…"), "fit": "OK"}
        for s, e, sp, o, t in raw
    ]


def actor_rows():
    return [
        {"Actor": "Actor 1", "Role": "Main character", "Assigned voice": "custom_voice_01", "Voice type": "male / cinema", "Quality": "studio clean"},
        {"Actor": "Actor 2", "Role": "Second character", "Assigned voice": "tm_female_clear", "Voice type": "female / natural", "Quality": "clean"},
        {"Actor": "Narrator", "Role": "Narrator", "Assigned voice": "ru_male_documentary", "Voice type": "documentary", "Quality": "broadcast"},
    ]


st.markdown(
    """
    <style>
    .block-container {padding-top: 2.6rem; max-width: 1380px;}
    [data-testid="stSidebar"] {background: linear-gradient(180deg,#151827 0%,#25293b 100%);}    
    .hero {border:1px solid rgba(255,255,255,.12); border-radius:24px; padding:24px; background:linear-gradient(135deg,rgba(106,76,255,.18),rgba(0,180,216,.10)); margin-bottom:18px;}
    .studio-card {border: 1px solid rgba(255,255,255,.13); border-radius: 20px; padding: 18px; background: rgba(255,255,255,.04); box-shadow:0 12px 35px rgba(0,0,0,.16);} 
    .drop-card {border: 2px dashed rgba(125,92,255,.70); border-radius: 24px; padding: 24px; min-height: 280px; background: rgba(125,92,255,.08); text-align:center;} 
    .sync-pill {display:inline-block; padding:7px 12px; border-radius:999px; background:#143d2a; color:#b9ffd8; font-weight:800;}
    .warn-pill {display:inline-block; padding:7px 12px; border-radius:999px; background:#4a3310; color:#ffe0a3; font-weight:800;}
    .small-card {border:1px solid rgba(255,255,255,.10); border-radius:18px; padding:14px; background:rgba(255,255,255,.035); min-height:120px;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.sidebar.title("🌐 Murat AI")
st.session_state["ui_lang"] = st.sidebar.selectbox(
    "Interface language / Язык интерфейса",
    LANGS,
    format_func=lambda x: LANG_LABELS[x],
    key="ui_lang_select",
)
active_channel = st.sidebar.selectbox(tr("channel_agent"), CHANNELS)
st.sidebar.markdown("---")
st.sidebar.success(tr("online"))
st.sidebar.caption(tr("full_ai"))

st.markdown(f"<div class='hero'><h1>🌐 Murat AI</h1><h3>{tr('subtitle')}</h3><p>{tr('notice')}</p></div>", unsafe_allow_html=True)

tabs = st.tabs([tr("tab_translate"), tr("tab_studio"), tr("tab_voice"), tr("tab_dictionary"), tr("tab_memory"), tr("tab_export"), tr("tab_publish")])

with tabs[0]:
    st.header(tr("translate_title"))
    c1, c2, c3 = st.columns(3)
    source_lang = c1.selectbox(tr("from"), LANGS, format_func=lambda x: LANG_LABELS[x])
    target_lang = c2.selectbox(tr("to"), LANGS, index=1, format_func=lambda x: LANG_LABELS[x])
    voice = c3.selectbox(tr("voice"), VOICE_PROFILES)
    c4, c5, c6 = st.columns(3)
    style = c4.selectbox(tr("style"), STYLES, index=0)
    tone = c5.selectbox(tr("tone"), TONES, index=2)
    emotion = c6.selectbox(tr("emotion"), EMOTIONS, index=0)
    text = st.text_area(tr("text"), value="Привет. Я хочу перевести это на чистый туркменский язык и озвучить видео.", height=150)
    if st.button(tr("translate"), type="primary"):
        st.text_area(tr("result"), value=preview_translate(text, source_lang, target_lang, style, tone, emotion), height=200)

with tabs[1]:
    st.header(tr("studio_title"))
    st.write(tr("studio_hint"))
    left, right = st.columns([1.05, 1.35], gap="large")
    with left:
        st.markdown(f"<div class='studio-card'><h3>{tr('source_box')}</h3><p>{tr('video_url')}</p></div>", unsafe_allow_html=True)
        url = st.text_input(tr("video_url"), placeholder="https://youtube.com/... / https://tiktok.com/... / direct mp4")
        if st.button(tr("download_source")):
            st.success("Preview: link accepted. Full mode downloads video and extracts audio.")
        uploaded = st.file_uploader(tr("upload_video"), type=["mp4", "mov", "webm", "mkv", "mp3", "wav", "m4a"])
        if uploaded:
            suffix = uploaded.name.lower().split(".")[-1]
            if suffix in ["mp4", "mov", "webm", "mkv"]:
                st.video(uploaded)
            else:
                st.audio(uploaded)
        else:
            st.markdown("<div class='drop-card'>🎬<br><br>Drop video/audio here<br><br>URL import + file upload</div>", unsafe_allow_html=True)
        st.subheader(tr("pipeline"))
        st.code("URL/File → Clean audio → Detect speakers → Translate → Fit timing → Assign voices → Dub → Render final video")
    with right:
        c1, c2, c3 = st.columns(3)
        media_target = c1.selectbox(tr("target_language"), LANGS, index=1, format_func=lambda x: LANG_LABELS[x], key="media_target")
        cinema_level = c2.selectbox(tr("cinema_level"), VOICE_LEVELS, index=2)
        sync_mode = c3.selectbox(tr("sync_mode"), SYNC_MODES, index=1)
        c4, c5 = st.columns(2)
        max_chars = c4.slider(tr("max_chars"), 24, 90, 42)
        max_lines = c5.slider(tr("max_lines"), 1, 3, 2)
        if st.button(tr("generate_script"), type="primary"):
            st.session_state["segments"] = make_segments(media_target, max_chars)
            st.session_state["script"] = "\n".join(row["translation"] for row in st.session_state["segments"])
        st.text_area(tr("translated_text"), value=st.session_state.get("script", ""), height=180)
        st.markdown(f"<span class='sync-pill'>✅ {tr('fit_status')}</span>", unsafe_allow_html=True)
        st.caption(tr("fit_ok"))
        st.subheader(tr("actor_map"))
        actors = st.data_editor(actor_rows(), use_container_width=True, hide_index=True, num_rows="dynamic")
        if "segments" in st.session_state:
            st.subheader(tr("segments"))
            st.dataframe(st.session_state["segments"], use_container_width=True, hide_index=True)

with tabs[2]:
    st.header(tr("voice_title"))
    st.write(tr("voice_hint"))
    v1, v2 = st.columns([1, 1], gap="large")
    with v1:
        st.markdown("<div class='studio-card'><h3>Voice Lab</h3></div>", unsafe_allow_html=True)
        avatar_name = st.text_input(tr("avatar_name"), "Murat custom voice")
        st.file_uploader(tr("voice_sample"), type=["wav", "mp3", "m4a", "flac"], key="voice_sample")
        st.checkbox(tr("noise_clean"), value=True)
        st.checkbox(tr("normalize"), value=True)
        st.checkbox(tr("remove_echo"), value=True)
        st.checkbox(tr("quality_check"), value=True)
        consent = st.checkbox(tr("consent"))
        if st.button(tr("create_voice"), type="primary"):
            if consent:
                st.success("Preview: voice profile created with clean/studio pipeline.")
            else:
                st.error("Consent is required.")
    with v2:
        st.markdown("<div class='studio-card'><h3>Avatar Studio</h3></div>", unsafe_allow_html=True)
        st.file_uploader(tr("video_sample"), type=["mp4", "mov", "webm"], key="avatar_video")
        st.selectbox(tr("cinema_level"), VOICE_LEVELS, index=2, key="avatar_level")
        st.markdown("<div class='drop-card'>🧑‍🎤<br><br>AI avatar preview<br><br>Face + voice + emotion</div>", unsafe_allow_html=True)
        st.caption(tr("avatar_preview"))

with tabs[3]:
    st.header(tr("dictionary_title"))
    st.write(tr("dictionary_hint"))
    term = st.text_input(tr("source_word"))
    replacement = st.text_input(tr("preferred_translation"))
    scope = st.radio(tr("scope"), ["Global", active_channel], horizontal=True)
    if st.button(tr("save_rule")):
        st.success(f"{term} → {replacement} ({scope})")

with tabs[4]:
    st.header(tr("memory_title"))
    st.write(tr("memory_hint"))
    st.dataframe([
        {"source": "Привет", "target": "Salam", "channel": active_channel},
        {"source": "Спасибо", "target": "Sag boluň", "channel": "Turkmen Culture"},
    ], use_container_width=True)

with tabs[5]:
    st.header(tr("export_title"))
    st.write(tr("export_hint"))
    e1, e2, e3, e4 = st.columns(4)
    e1.markdown(f"<div class='small-card'><h4>{tr('final_video')}</h4><p>MP4 · 1080p · dubbed</p></div>", unsafe_allow_html=True)
    e2.markdown("<div class='small-card'><h4>Subtitles</h4><p>SRT / VTT</p></div>", unsafe_allow_html=True)
    e3.markdown("<div class='small-card'><h4>Audio</h4><p>WAV / MP3 stems</p></div>", unsafe_allow_html=True)
    e4.markdown("<div class='small-card'><h4>Package</h4><p>ZIP for upload</p></div>", unsafe_allow_html=True)
    st.download_button(tr("download_video"), data=b"Preview video placeholder", file_name="murat-ai-final-video-preview.txt")
    st.download_button(tr("subtitle_file"), data=b"1\n00:00:00,000 --> 00:00:04,200\nMurat AI preview subtitles\n", file_name="murat-ai-subtitles.srt")
    st.download_button(tr("audio_tracks"), data=b"Preview audio tracks placeholder", file_name="murat-ai-audio-tracks.txt")
    st.download_button(tr("download_zip"), data=b"Preview ZIP package placeholder", file_name="murat-ai-publishing-package.txt")

with tabs[6]:
    st.header(tr("publish_title"))
    st.write(tr("publish_hint"))
    title = st.text_input(tr("video_title"), "Murat AI professional dubbing video")
    description = st.text_area(tr("description"), "Generated with Murat AI")
    platforms = st.multiselect(tr("platforms"), PLATFORMS, ["YouTube", "TikTok", "Download to computer"])
    if st.button(tr("create_package"), type="primary"):
        st.success(", ".join(platforms))
        st.json({"title": title, "description": description, "platforms": platforms, "created_at": datetime.utcnow().isoformat()})

st.markdown("---")
st.caption("Murat AI preview branch: streamlit-preview. Full AI branch: issue-2-ai-architecture.")
