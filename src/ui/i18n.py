"""UI string catalog for ru / tk / tr / en.

The catalog is intentionally flat — one dictionary per key with one entry
per supported UI language. Missing translations fall back to English so a
new key never crashes the UI.

Usage:

    from src.ui.i18n import t, set_ui_lang
    st.write(t("translate_button"))             # uses st.session_state["ui_lang"]
    st.write(t("translate_button", lang="tk"))  # explicit override
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Mapping, Optional

import streamlit as st

SUPPORTED_UI_LANGS: tuple[str, ...] = ("ru", "tk", "tr", "en")
DEFAULT_UI_LANG = "ru"

UI_LANG_LABELS: Dict[str, str] = {
    "ru": "🇷🇺 Русский",
    "tk": "🇹🇲 Türkmençe",
    "tr": "🇹🇷 Türkçe",
    "en": "🇬🇧 English",
}


# Short helper to read the active UI language from Streamlit session state
# without forcing every call site to import streamlit.
def get_ui_lang() -> str:
    try:
        value = st.session_state.get("ui_lang") if hasattr(st, "session_state") else None
    except Exception:
        value = None
    return value if value in SUPPORTED_UI_LANGS else DEFAULT_UI_LANG


def set_ui_lang(lang: str) -> None:
    if lang in SUPPORTED_UI_LANGS:
        st.session_state["ui_lang"] = lang


# ---------------------------------------------------------------------------
# Strings — every key must include all four languages. ``en`` is the canonical
# fallback when a translation is missing.
# ---------------------------------------------------------------------------


STRINGS: Dict[str, Mapping[str, str]] = {
    # ----- chrome -----
    "app_title": {
        "ru": "Warehouse AI Translator",
        "tk": "Warehouse AI Terjimeçi",
        "tr": "Warehouse AI Çevirmen",
        "en": "Warehouse AI Translator",
    },
    "app_subtitle": {
        "ru": "RU · TK · TR · EN — перевод, голос, видео. Приоритет: ru ↔ tk.",
        "tk": "RU · TK · TR · EN — terjime, ses, wideo. Esasy ugur: ru ↔ tk.",
        "tr": "RU · TK · TR · EN — çeviri, ses, video. Öncelik: ru ↔ tk.",
        "en": "RU · TK · TR · EN — translation, voice, video. Priority: ru ↔ tk.",
    },

    # ----- sidebar -----
    "sidebar_channels": {
        "ru": "🤖 Каналы (AI-агенты)",
        "tk": "🤖 Kanallar (AI-agentleri)",
        "tr": "🤖 Kanallar (AI ajanları)",
        "en": "🤖 Channels (AI agents)",
    },
    "sidebar_active_channel": {
        "ru": "Активный канал",
        "tk": "Işjeň kanal",
        "tr": "Aktif kanal",
        "en": "Active channel",
    },
    "sidebar_global": {
        "ru": "🌍 Без канала",
        "tk": "🌍 Kanalsyz",
        "tr": "🌍 Kanalsız",
        "en": "🌍 Global (no channel)",
    },
    "sidebar_settings": {
        "ru": "⚙️ Настройки",
        "tk": "⚙️ Sazlamalar",
        "tr": "⚙️ Ayarlar",
        "en": "⚙️ Settings",
    },
    "sidebar_ui_language": {
        "ru": "Язык интерфейса",
        "tk": "Interfeýs dili",
        "tr": "Arayüz dili",
        "en": "UI language",
    },
    "sidebar_whisper_size": {
        "ru": "Размер Whisper",
        "tk": "Whisper ölçegi",
        "tr": "Whisper boyutu",
        "en": "Whisper size",
    },
    "sidebar_whisper_help": {
        "ru": "'tiny'/'base' быстро на CPU; 'small' — лучший компромисс качества и скорости.",
        "tk": "'tiny'/'base' CPU-da çalt; 'small' — hil we tizlik üçin iň gowy çözgüt.",
        "tr": "'tiny'/'base' CPU'da hızlı; 'small' kalite/hız için en iyi denge.",
        "en": "'tiny'/'base' run fast on CPU; 'small' is the best quality/speed trade-off.",
    },
    "sidebar_storage_caption": {
        "ru": "Каналы, словарь, TM и Custom Voices хранятся локально в SQLite. "
              "Для переключения на PostgreSQL задайте `DATABASE_URL`.",
        "tk": "Kanallar, sözlük, TM we Custom Voices SQLite-da ýerli saklanýar. "
              "PostgreSQL-e geçmek üçin `DATABASE_URL` belläň.",
        "tr": "Kanallar, sözlük, TM ve Custom Voices yerel SQLite'ta saklanır. "
              "PostgreSQL'e geçmek için `DATABASE_URL` ayarlayın.",
        "en": "Channels, glossary, TM and Custom Voices live in local SQLite. "
              "Set `DATABASE_URL` to switch to PostgreSQL.",
    },

    # ----- tabs -----
    "tab_translate": {"ru": "✨ Перевод", "tk": "✨ Terjime", "tr": "✨ Çeviri", "en": "✨ Translate"},
    "tab_media": {"ru": "🎬 Аудио / Видео / URL", "tk": "🎬 Audio / Wideo / URL", "tr": "🎬 Ses / Video / URL", "en": "🎬 Audio / Video / URL"},
    "tab_dictionary": {"ru": "📚 Словарь", "tk": "📚 Sözlük", "tr": "📚 Sözlük", "en": "📚 Dictionary"},
    "tab_memory": {"ru": "🧠 Память переводов", "tk": "🧠 Terjime ýady", "tr": "🧠 Çeviri belleği", "en": "🧠 Translation Memory"},
    "tab_channels": {"ru": "🤖 Каналы", "tk": "🤖 Kanallar", "tr": "🤖 Kanallar", "en": "🤖 Channels"},
    "tab_voices": {"ru": "🎙️ Голоса", "tk": "🎙️ Sesler", "tr": "🎙️ Sesler", "en": "🎙️ Voices"},
    "tab_publish": {"ru": "📤 Публикация", "tk": "📤 Çap etmek", "tr": "📤 Yayınlama", "en": "📤 Publish"},

    # ----- translate tab -----
    "translate_heading": {
        "ru": "Перевод текста",
        "tk": "Tekst terjimesi",
        "tr": "Metin çevirisi",
        "en": "Translate text",
    },
    "translate_from": {"ru": "С", "tk": "Çeşme", "tr": "Kaynak", "en": "From"},
    "translate_to": {"ru": "На", "tk": "Maksat", "tr": "Hedef", "en": "To"},
    "translate_style": {"ru": "Стиль", "tk": "Stil", "tr": "Stil", "en": "Style"},
    "translate_tone": {"ru": "Тон подачи", "tk": "Çykyş äheňi", "tr": "Sunum tonu", "en": "Delivery tone"},
    "translate_emotion": {"ru": "Эмоция", "tk": "Duýgy", "tr": "Duygu", "en": "Emotion"},
    "translate_voice": {"ru": "Голос", "tk": "Ses", "tr": "Ses", "en": "Voice"},
    "translate_input_placeholder": {
        "ru": "Введите текст для перевода…",
        "tk": "Terjime etmek üçin tekst giriziň…",
        "tr": "Çevrilecek metni girin…",
        "en": "Enter text to translate…",
    },
    "translate_button": {"ru": "Перевести", "tk": "Terjime et", "tr": "Çevir", "en": "Translate"},
    "translate_voice_button": {"ru": "🔊 Озвучить", "tk": "🔊 Sesli", "tr": "🔊 Seslendir", "en": "🔊 Voice"},
    "translate_replace_button": {
        "ru": "✏️ Заменить перевод",
        "tk": "✏️ Terjimäni çalşyr",
        "tr": "✏️ Çeviriyi değiştir",
        "en": "✏️ Replace translation",
    },
    "translate_add_to_dict": {
        "ru": "📚 Добавить в словарь",
        "tk": "📚 Sözlüge goş",
        "tr": "📚 Sözlüğe ekle",
        "en": "📚 Add to dictionary",
    },
    "translate_no_result": {
        "ru": "Здесь появится перевод. Введите текст и нажмите «Перевести».",
        "tk": "Bu ýerde terjime peýda bolar. Tekst giriziň we «Terjime et» düwmesine basyň.",
        "tr": "Çeviri burada görünecek. Metin girin ve «Çevir»'e basın.",
        "en": "Translation will appear here. Enter text and press «Translate».",
    },
    "translate_auto_detect": {
        "ru": "Авто-определение языка (ru/en/tr)",
        "tk": "Awto-kesgitleme (ru/en/tr)",
        "tr": "Otomatik dil algılama (ru/en/tr)",
        "en": "Auto-detect source (ru/en/tr)",
    },
    "translate_hint": {
        "ru": "По умолчанию — естественный живой стиль. Меняй стиль/тон/эмоцию для блогерского, "
              "новостного, культурного и других режимов.",
        "tk": "Düzgün boýunça — tebigy, janly stil. Bloger, habar, medeni we beýleki rejeler üçin "
              "stili / äheňi / duýgyny üýtgediň.",
        "tr": "Varsayılan: doğal, canlı stil. Blog, haber, kültürel vb. modlar için "
              "stil / ton / duygu seçin.",
        "en": "Default is the natural, living style. Change style/tone/emotion for blogger, "
              "news, cultural and other modes.",
    },

    # ----- media tab -----
    "media_heading": {
        "ru": "Аудио / видео / ссылка",
        "tk": "Audio / wideo / salgy",
        "tr": "Ses / video / bağlantı",
        "en": "Audio / video / URL",
    },
    "media_caption": {
        "ru": "Вставь ссылку YouTube/TikTok или загрузи файл. Пайплайн: "
              "загрузка → ffmpeg → Whisper ASR → NLLB-200 → (для tk) MMS-TTS.",
        "tk": "YouTube/TikTok salgysyny goýuň ýa-da fail ýükläň. Tertip: "
              "göçürip almak → ffmpeg → Whisper ASR → NLLB-200 → (tk üçin) MMS-TTS.",
        "tr": "YouTube/TikTok bağlantısı yapıştırın veya dosya yükleyin. Akış: "
              "indirme → ffmpeg → Whisper ASR → NLLB-200 → (tk için) MMS-TTS.",
        "en": "Paste a YouTube/TikTok URL or upload a file. Pipeline: "
              "download → ffmpeg → Whisper ASR → NLLB-200 → (for tk) MMS-TTS.",
    },
    "media_url": {"ru": "Ссылка на медиа", "tk": "Media salgysy", "tr": "Medya bağlantısı", "en": "Media URL"},
    "media_upload": {"ru": "…или загрузите файл", "tk": "…ýa-da fail ýükläň", "tr": "…veya dosya yükleyin", "en": "…or upload a file"},
    "media_target_lang": {"ru": "Целевой язык", "tk": "Maksatly dil", "tr": "Hedef dil", "en": "Target language"},
    "media_source_lang": {"ru": "Исходный язык", "tk": "Çeşme dili", "tr": "Kaynak dil", "en": "Source language"},
    "media_auto": {"ru": "Авто", "tk": "Awto", "tr": "Otomatik", "en": "Auto-detect"},
    "media_process": {"ru": "Обработать", "tk": "Işle", "tr": "İşle", "en": "Process media"},

    # ----- dictionary / memory -----
    "dict_heading": {"ru": "Мой словарь", "tk": "Meniň sözlügim", "tr": "Sözlüğüm", "en": "My glossary"},
    "dict_caption": {
        "ru": "Точные правила замены: «исходник → перевод». Применяются после перевода. "
              "Правила канала имеют приоритет над глобальными.",
        "tk": "Anyk çalşyk düzgünleri: «çeşme → terjime». Terjimeden soň ulanylýar. "
              "Kanal düzgünleri global düzgünlerden has wajyp.",
        "tr": "Tam değiştirme kuralları: «kaynak → çeviri». Çeviriden sonra uygulanır. "
              "Kanal kuralları globallerden önceliklidir.",
        "en": "Exact replacement rules: «source → target». Applied after translation. "
              "Channel rules win over global ones.",
    },
    "dict_add": {"ru": "➕ Добавить правило", "tk": "➕ Düzgün goş", "tr": "➕ Kural ekle", "en": "➕ Add a new rule"},
    "dict_search_placeholder": {
        "ru": "🔍 Поиск по исходнику или переводу",
        "tk": "🔍 Çeşme ýa-da terjime boýunça gözleg",
        "tr": "🔍 Kaynak veya hedefte ara",
        "en": "🔍 Find by source or target text",
    },
    "memory_heading": {"ru": "Память переводов", "tk": "Terjime ýady", "tr": "Çeviri belleği", "en": "Translation memory"},
    "memory_caption": {
        "ru": "Если ввести точно такой же текст для перевода — система отдаст сохранённый "
              "вариант, минуя модель.",
        "tk": "Şol bir tekst ýene-de terjime üçin girizilse — ulgam modele ýüz tutman, "
              "saklanan görnüşi gaýtaryp berer.",
        "tr": "Aynı metin tekrar girilirse — sistem modeli atlayıp kayıtlı çeviriyi döndürür.",
        "en": "If you enter the exact same text again — the system returns the saved "
              "translation, bypassing the model.",
    },

    # ----- channels tab -----
    "channels_heading": {
        "ru": "Каналы (AI-агенты)",
        "tk": "Kanallar (AI-agentleri)",
        "tr": "Kanallar (AI ajanları)",
        "en": "Channels (AI agents)",
    },
    "channels_caption": {
        "ru": "Каналы — профили вашего контента. У каждого свой стиль, тон, эмоция, голос, словарь и память.",
        "tk": "Kanallar — kontentiňiziň profilleri. Hersiniň öz stili, äheňi, duýgy, sesi, sözlügi we ýady bar.",
        "tr": "Kanallar — içerik profilleriniz. Her birinin kendi stili, tonu, duygusu, sesi, sözlüğü ve hafızası var.",
        "en": "Channels are your content profiles. Each has its own style, tone, emotion, voice, glossary and memory.",
    },
    "channels_create": {
        "ru": "➕ Создать канал",
        "tk": "➕ Kanal döret",
        "tr": "➕ Kanal oluştur",
        "en": "➕ Create a channel",
    },
    "channels_activate": {"ru": "Активировать", "tk": "Işjeňleşdir", "tr": "Etkinleştir", "en": "Activate"},

    # ----- voices -----
    "voices_catalog_heading": {
        "ru": "Каталог голосов (23 профиля)",
        "tk": "Sesler katalogy (23 profil)",
        "tr": "Ses kataloğu (23 profil)",
        "en": "Built-in voice catalog (23 profiles)",
    },
    "voices_my_heading": {
        "ru": "Мои голоса / Custom Voices",
        "tk": "Meniň seslerim / Custom Voices",
        "tr": "Seslerim / Custom Voices",
        "en": "My Custom Voices",
    },
    "voices_my_caption": {
        "ru": "Загрузи или запиши свой голос, настрой параметры и привяжи к каналу, стилю или типу видео. "
              "Аудиофайлы хранятся локально и **никогда не попадают в git**.",
        "tk": "Sesiňizi ýükläň ýa-da ýazyň, sazlamalary kesgitläň we kanala, stile ýa-da wideo görnüşine "
              "baglaň. Audiofaýllar ýerli saklanýar we **hiç haçan git-e düşmeýär**.",
        "tr": "Sesinizi yükleyin veya kaydedin, ayarları yapın ve kanal, stil veya video türüne bağlayın. "
              "Ses dosyaları yerel saklanır ve **asla git'e gönderilmez**.",
        "en": "Upload or record your voice, configure settings and bind to a channel, style or video type. "
              "Audio files live locally and are **never** committed to git.",
    },
    "voices_consent_label": {
        "ru": "✅ Я подтверждаю, что имею право использовать этот голос.",
        "tk": "✅ Bu sesi ulanmaga hakymyň bardygyny tassyklaýaryn.",
        "tr": "✅ Bu sesi kullanma hakkına sahip olduğumu onaylıyorum.",
        "en": "✅ I confirm I have the right to use this voice.",
    },
    "voices_preview": {
        "ru": "🔊 Прослушать пример",
        "tk": "🔊 Mysaly diňle",
        "tr": "🔊 Önizlemeyi dinle",
        "en": "🔊 Preview",
    },

    # ----- publish tab -----
    "publish_heading": {
        "ru": "Готовые видео и аудио для публикации",
        "tk": "Çap etmek üçin taýýar wideolar we audio",
        "tr": "Yayınlanmaya hazır videolar ve sesler",
        "en": "Media ready for publishing",
    },
    "publish_caption": {
        "ru": "Собирай готовый пакет: медиа + название + описание + теги + хэштеги. Скачай ZIP "
              "или открой страницу загрузки YouTube / TikTok / Instagram / Facebook.",
        "tk": "Taýýar paket ýygnaň: media + ady + düşündiriş + bellikler + hashtaglar. ZIP-i göçürip alyň "
              "ýa-da YouTube / TikTok / Instagram / Facebook ýüklemek sahypasyny açyň.",
        "tr": "Hazır paket oluşturun: medya + başlık + açıklama + etiketler + hashtag'ler. ZIP indirin "
              "veya YouTube / TikTok / Instagram / Facebook yükleme sayfasını açın.",
        "en": "Assemble a ready-to-publish package: media + title + description + tags + hashtags. "
              "Download as ZIP or open the YouTube / TikTok / Instagram / Facebook upload page.",
    },
    "publish_create": {
        "ru": "➕ Создать пакет публикации",
        "tk": "➕ Çap paketini döret",
        "tr": "➕ Yayın paketi oluştur",
        "en": "➕ Create publishing package",
    },
    "publish_export": {
        "ru": "📦 Скачать ZIP",
        "tk": "📦 ZIP göçürip al",
        "tr": "📦 ZIP indir",
        "en": "📦 Download ZIP",
    },
    "publish_open_target": {
        "ru": "Открыть страницу загрузки",
        "tk": "Ýüklemek sahypasyny aç",
        "tr": "Yükleme sayfasını aç",
        "en": "Open upload page",
    },
    "publish_platforms": {
        "ru": "Целевые платформы",
        "tk": "Maksatly platformalar",
        "tr": "Hedef platformlar",
        "en": "Target platforms",
    },
    "publish_title_field": {"ru": "Название", "tk": "Ady", "tr": "Başlık", "en": "Title"},
    "publish_description_field": {"ru": "Описание", "tk": "Düşündiriş", "tr": "Açıklama", "en": "Description"},
    "publish_tags_field": {"ru": "Теги (через запятую)", "tk": "Bellikler (otur bilen)", "tr": "Etiketler (virgülle)", "en": "Tags (comma-separated)"},
    "publish_hashtags_field": {"ru": "Хэштеги (через пробел)", "tk": "Hashtaglar (boşluk bilen)", "tr": "Hashtag'ler (boşlukla)", "en": "Hashtags (space-separated)"},
    "publish_kind": {"ru": "Тип", "tk": "Görnüşi", "tr": "Tür", "en": "Kind"},
    "publish_kind_video": {"ru": "видео", "tk": "wideo", "tr": "video", "en": "video"},
    "publish_kind_audio": {"ru": "аудио", "tk": "audio", "tr": "ses", "en": "audio"},
    "publish_status_draft": {"ru": "черновик", "tk": "çykyş ýok", "tr": "taslak", "en": "draft"},
    "publish_status_exported": {"ru": "экспортирован", "tk": "eksport edildi", "tr": "dışa aktarıldı", "en": "exported"},
    "publish_status_published": {"ru": "опубликован", "tk": "çap edildi", "tr": "yayınlandı", "en": "published"},
    "publish_mark_published": {"ru": "Отметить опубликованным", "tk": "Çap edildi diýip belläň", "tr": "Yayınlandı olarak işaretle", "en": "Mark as published"},
    "publish_no_packages": {
        "ru": "Пакетов пока нет. Создайте первый выше.",
        "tk": "Paketler entek ýok. Ýokarda birinjini dörediň.",
        "tr": "Henüz paket yok. Yukarıda ilkini oluşturun.",
        "en": "No packages yet. Create the first one above.",
    },
    "publish_auth_warning": {
        "ru": "Прямая публикация на YouTube/TikTok/Instagram/Facebook требует ваших собственных API-ключей "
              "(OAuth-приложение в Google Cloud / TikTok for Developers / Meta for Developers). "
              "Сейчас доступен экспорт ZIP-пакета и кнопка «Открыть страницу загрузки».",
        "tk": "YouTube/TikTok/Instagram/Facebook-a göni çap etmek üçin öz API açarlaryňyz gerek "
              "(Google Cloud / TikTok for Developers / Meta for Developers OAuth programmasy). "
              "Häzir ZIP paketini eksport etmek we «Ýüklemek sahypasyny aç» düwmesi elýeterli.",
        "tr": "YouTube/TikTok/Instagram/Facebook'a doğrudan yayınlama için kendi API anahtarlarınız gerekir "
              "(Google Cloud / TikTok for Developers / Meta for Developers'da OAuth uygulaması). "
              "Şu an ZIP paket dışa aktarımı ve «Yükleme sayfasını aç» düğmesi mevcut.",
        "en": "Direct publishing to YouTube/TikTok/Instagram/Facebook requires your own API credentials "
              "(an OAuth app in Google Cloud / TikTok for Developers / Meta for Developers). "
              "For now you can export a ZIP package and use the «Open upload page» button.",
    },

    # ----- common controls -----
    "any": {"ru": "Любой", "tk": "Islendik", "tr": "Tümü", "en": "Any"},
    "none_dash": {"ru": "—", "tk": "—", "tr": "—", "en": "—"},
    "edit": {"ru": "Редактировать", "tk": "Üýtgetmek", "tr": "Düzenle", "en": "Edit"},
    "save": {"ru": "Сохранить", "tk": "Sakla", "tr": "Kaydet", "en": "Save"},
    "delete": {"ru": "Удалить", "tk": "Poz", "tr": "Sil", "en": "Delete"},
    "cancel": {"ru": "Отмена", "tk": "Goý bolsun", "tr": "İptal", "en": "Cancel"},
    "create": {"ru": "Создать", "tk": "Döret", "tr": "Oluştur", "en": "Create"},
    "search": {"ru": "Поиск", "tk": "Gözleg", "tr": "Arama", "en": "Search"},
    "scope": {"ru": "Область", "tk": "Çäk", "tr": "Kapsam", "en": "Scope"},
    "scope_all": {"ru": "все", "tk": "ählisi", "tr": "tümü", "en": "all"},
    "scope_global": {"ru": "глобально", "tk": "global", "tr": "global", "en": "global"},
    "scope_channel": {"ru": "канал", "tk": "kanal", "tr": "kanal", "en": "channel"},
    "language": {"ru": "Язык", "tk": "Dil", "tr": "Dil", "en": "Language"},
    "name": {"ru": "Имя", "tk": "Ady", "tr": "Ad", "en": "Name"},
    "description": {"ru": "Описание", "tk": "Düşündiriş", "tr": "Açıklama", "en": "Description"},
}


def t(key: str, *, lang: Optional[str] = None) -> str:
    """Return the localised string for ``key``.

    Falls back to English if the active language has no translation, then to
    the key itself if even English is missing — that way a typo never blanks
    out the UI.
    """
    active = lang if lang in SUPPORTED_UI_LANGS else get_ui_lang()
    bundle = STRINGS.get(key)
    if bundle is None:
        return key
    return bundle.get(active) or bundle.get("en") or key


def available_keys() -> Iterable[str]:
    return STRINGS.keys()


def lang_options() -> List[tuple[str, str]]:
    return [(code, UI_LANG_LABELS[code]) for code in SUPPORTED_UI_LANGS]


__all__ = [
    "DEFAULT_UI_LANG",
    "STRINGS",
    "SUPPORTED_UI_LANGS",
    "UI_LANG_LABELS",
    "available_keys",
    "get_ui_lang",
    "lang_options",
    "set_ui_lang",
    "t",
]
