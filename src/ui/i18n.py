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
        "ru": "Murat AI",
        "tk": "Murat AI",
        "tr": "Murat AI",
        "en": "Murat AI",
    },
    "app_subtitle": {
        "ru": "Murat AI — перевод, озвучка и дубляж на русском, туркменском, "
              "турецком и английском языках.",
        "tk": "Murat AI — rus, türkmen, türk we iňlis dillerinde terjime, sesli "
              "okamak we dubläž.",
        "tr": "Murat AI — Rusça, Türkmence, Türkçe ve İngilizce dillerinde çeviri, "
              "seslendirme ve dublaj.",
        "en": "Murat AI — translation, voiceover and dubbing in Russian, Turkmen, "
              "Turkish and English.",
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
    "publish_supported_platforms": {
        "ru": "Поддерживаемые платформы",
        "tk": "Goldanýan platformalar",
        "tr": "Desteklenen platformlar",
        "en": "Supported platforms",
    },
    "publish_name_placeholder": {
        "ru": "Например: Видео для блога — выпуск 1",
        "tk": "Mysal: Blog wideosy — sany 1",
        "tr": "Örn: Blog videosu — bölüm 1",
        "en": "e.g. Blog video — episode 1",
    },
    "publish_packages_count": {"ru": "{n} пакетов", "tk": "{n} paket", "tr": "{n} paket", "en": "{n} package(s)"},
    "publish_mark_exported": {
        "ru": "📦 Отметить как экспортированный",
        "tk": "📦 Eksport edildi diýip belläň",
        "tr": "📦 Dışa aktarıldı olarak işaretle",
        "en": "📦 Mark as exported",
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
    "none_value": {"ru": "— нет —", "tk": "— ýok —", "tr": "— yok —", "en": "— none —"},
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
    "note_optional": {"ru": "Примечание (необязательно)", "tk": "Bellik (hökman däl)", "tr": "Not (isteğe bağlı)", "en": "Note (optional)"},
    "save_into_channel": {
        "ru": "Сохранить только в активный канал",
        "tk": "Diňe işjeň kanala saklaň",
        "tr": "Yalnızca aktif kanala kaydet",
        "en": "Save into the active channel only",
    },
    "status": {"ru": "Статус", "tk": "Ýagdaýy", "tr": "Durum", "en": "Status"},
    "process_working": {"ru": "Обработка…", "tk": "Işlenýär…", "tr": "İşleniyor…", "en": "Working…"},
    "process_done": {"ru": "Готово", "tk": "Taýýar", "tr": "Tamam", "en": "Done"},
    "type_text_first": {
        "ru": "Сначала введите текст.",
        "tk": "Ilki tekst giriziň.",
        "tr": "Önce metin girin.",
        "en": "Type some text first.",
    },
    "src_tgt_must_differ": {
        "ru": "Исходный и целевой языки должны отличаться.",
        "tk": "Çeşme we maksat dilleri tapawutly bolmaly.",
        "tr": "Kaynak ve hedef diller farklı olmalı.",
        "en": "Source and target languages must differ.",
    },
    "both_required": {
        "ru": "Оба поля обязательны.",
        "tk": "Iki meýdan-da hökman gerek.",
        "tr": "Her iki alan da gereklidir.",
        "en": "Both fields are required.",
    },
    "saved": {"ru": "Сохранено.", "tk": "Saklandy.", "tr": "Kaydedildi.", "en": "Saved."},
    "updated": {"ru": "Обновлено.", "tk": "Täzelendi.", "tr": "Güncellendi.", "en": "Updated."},

    # ----- media tab (extra) -----
    "media_url_placeholder": {
        "ru": "https://www.youtube.com/watch?v=…",
        "tk": "https://www.youtube.com/watch?v=…",
        "tr": "https://www.youtube.com/watch?v=…",
        "en": "https://www.youtube.com/watch?v=…",
    },
    "media_target_caption": {
        "ru": "Выберите только язык, на который перевести. Исходный язык система определит сама.",
        "tk": "Diňe terjime ediljek dili saýlaň. Çeşme dilini ulgam özi kesgitleýär.",
        "tr": "Yalnızca çevrilecek hedef dili seçin. Kaynak dili sistem otomatik algılar.",
        "en": "Choose only the target language. The source language is detected automatically.",
    },
    "media_voiceover_style": {
        "ru": "Стиль озвучки",
        "tk": "Sesli okamagyň stili",
        "tr": "Seslendirme stili",
        "en": "Voiceover style",
    },
    "media_url_or_file_required": {
        "ru": "Добавьте ссылку или загрузите файл.",
        "tk": "Salgy goşuň ýa-da fail ýükläň.",
        "tr": "Bağlantı verin veya dosya yükleyin.",
        "en": "Provide a URL or upload a file.",
    },
    "media_step_download": {"ru": "⬇️ Загрузка медиа…", "tk": "⬇️ Media göçürilýär…", "tr": "⬇️ Medya indiriliyor…", "en": "⬇️ Downloading media…"},
    "media_step_extract": {"ru": "🎧 Извлечение аудио…", "tk": "🎧 Audio çykarylýar…", "tr": "🎧 Ses çıkarılıyor…", "en": "🎧 Extracting audio…"},
    "media_step_transcribe": {"ru": "🗣️ Распознавание речи (Whisper)…", "tk": "🗣️ Sesi ykrar etmek (Whisper)…", "tr": "🗣️ Konuşma tanıma (Whisper)…", "en": "🗣️ Transcribing speech (Whisper)…"},
    "media_step_detected": {"ru": "🌐 Определён язык", "tk": "🌐 Dil kesgitlenildi", "tr": "🌐 Dil algılandı", "en": "🌐 Detected language"},
    "media_step_translate": {"ru": "🌐 Перевод…", "tk": "🌐 Terjime edilýär…", "tr": "🌐 Çeviriliyor…", "en": "🌐 Translating…"},
    "media_step_voice": {"ru": "🔊 Озвучка…", "tk": "🔊 Sesli okalyşy…", "tr": "🔊 Seslendiriliyor…", "en": "🔊 Generating voice…"},
    "media_transcript_heading": {"ru": "🗒️ Распознанный текст", "tk": "🗒️ Ykrar edilen tekst", "tr": "🗒️ Tanınan metin", "en": "🗒️ Transcript"},
    "media_translation_heading": {"ru": "🌐 Перевод", "tk": "🌐 Terjime", "tr": "🌐 Çeviri", "en": "🌐 Translation"},
    "media_voice_heading": {"ru": "🔊 Озвучка", "tk": "🔊 Sesli okalyş", "tr": "🔊 Seslendirme", "en": "🔊 Voiceover"},
    "media_unknown_lang_warning": {
        "ru": "Whisper не смог уверенно определить язык. Использую {fallback}.",
        "tk": "Whisper dili anyk kesgitläp bilmedi. {fallback} ulanylýar.",
        "tr": "Whisper dili kesin algılayamadı. {fallback} kullanılıyor.",
        "en": "Whisper could not detect the language with confidence. Using {fallback}.",
    },
    "translate_failed": {"ru": "Ошибка: {error}", "tk": "Ýalňyşlyk: {error}", "tr": "Hata: {error}", "en": "Failed: {error}"},
    "translate_synthesising": {"ru": "Синтез речи…", "tk": "Sesi sintezirlemek…", "tr": "Ses sentezleniyor…", "en": "Synthesising…"},
    "translate_cloud_tts_warn": {
        "ru": "Облачное TTS для ru/en/tr требует `OPENAI_API_KEY`. В этом Streamlit MVP "
              "локально рендерится только туркменский голос.",
        "tk": "ru/en/tr üçin bulut TTS `OPENAI_API_KEY` talap edýär. Bu Streamlit MVP-de "
              "ýerli diňe türkmen sesi rendering edilýär.",
        "tr": "ru/en/tr için bulut TTS `OPENAI_API_KEY` gerektirir. Bu Streamlit MVP'de "
              "yalnızca Türkmence ses yerel olarak oluşturulur.",
        "en": "Cloud TTS for ru/en/tr requires `OPENAI_API_KEY`. This Streamlit MVP only "
              "renders Turkmen voice locally.",
    },
    "translate_tts_failed": {"ru": "Ошибка озвучки: {error}", "tk": "Sesli ýalňyşlygy: {error}", "tr": "Ses hatası: {error}", "en": "TTS failed: {error}"},
    "translate_could_not_detect": {
        "ru": "Не удалось определить язык — используется выбранный исходный.",
        "tk": "Dili kesgitläp bolmady — saýlanan çeşme dili ulanylýar.",
        "tr": "Dil algılanamadı — seçilen kaynak dil kullanılıyor.",
        "en": "Could not auto-detect — using the selected source.",
    },
    "translate_translating": {"ru": "Перевод {src} → {tgt}…", "tk": "Terjime {src} → {tgt}…", "tr": "Çevriliyor {src} → {tgt}…", "en": "Translating {src} → {tgt}…"},
    "translate_replace_caption": {
        "ru": "Если перевод неверный — введите правильный вариант. Он сохранится в Translation "
              "Memory активного канала (или глобально, если канал не выбран).",
        "tk": "Terjime nädogry bolsa — dogry görnüşi giriziň. Ol işjeň kanalyň Translation "
              "Memory-sinde (ýa-da kanal saýlanmasa, global ýadynda) saklanar.",
        "tr": "Çeviri yanlışsa — doğru sürümü girin. Aktif kanalın Translation Memory'sine "
              "(kanal seçilmediyse global belleğe) kaydedilir.",
        "en": "If the translation is wrong — enter the correct version. It will be saved to "
              "the active channel's Translation Memory (or globally if no channel is selected).",
    },
    "translate_correct_label": {"ru": "Правильный перевод", "tk": "Dogry terjime", "tr": "Doğru çeviri", "en": "Correct translation"},
    "translate_save_correction": {"ru": "Сохранить исправление", "tk": "Düzedilen görnüşi sakla", "tr": "Düzeltmeyi kaydet", "en": "Save correction"},
    "translate_saved_to_tm": {
        "ru": "Сохранено в Translation Memory.",
        "tk": "Translation Memory-de saklandy.",
        "tr": "Translation Memory'e kaydedildi.",
        "en": "Saved to Translation Memory.",
    },
    "translate_no_change": {
        "ru": "Изменений нет — TM не обновлена.",
        "tk": "Üýtgeşik zat ýok — TM täzelenmedi.",
        "tr": "Değişiklik yok — TM güncellenmedi.",
        "en": "Nothing changed — TM not updated.",
    },
    "translate_add_caption": {
        "ru": "Добавьте точное соответствие — оно будет автоматически применяться после каждого "
              "перевода в выбранной паре языков.",
        "tk": "Anyk gabat gelýänini goşuň — saýlanan dil jübütinde her terjimeden soň awtomatiki "
              "ulanylar.",
        "tr": "Tam karşılığı ekleyin — seçilen dil çiftinde her çeviriden sonra otomatik uygulanır.",
        "en": "Add an exact match — it will be applied after every translation in the chosen pair.",
    },
    "translate_save_rule": {"ru": "Сохранить правило", "tk": "Düzgüni sakla", "tr": "Kuralı kaydet", "en": "Save rule"},
    "translate_rule_saved": {"ru": "Правило сохранено.", "tk": "Düzgün saklandy.", "tr": "Kural kaydedildi.", "en": "Rule saved."},

    # ----- dictionary / memory (extra) -----
    "dict_no_rules": {"ru": "Правил пока нет.", "tk": "Düzgünler entek ýok.", "tr": "Henüz kural yok.", "en": "No glossary rules."},
    "dict_rules_count": {"ru": "{n} правил", "tk": "{n} sany düzgün", "tr": "{n} kural", "en": "{n} rule(s)"},
    "dict_source_term": {"ru": "Слово / фраза", "tk": "Söz / söz düzümi", "tr": "Sözcük / ifade", "en": "Source word / phrase"},
    "dict_target_term": {"ru": "Перевод", "tk": "Terjime", "tr": "Çeviri", "en": "Target word / phrase"},
    "dict_whole_word": {"ru": "Целое слово", "tk": "Bütin söz", "tr": "Tam sözcük", "en": "Whole word"},
    "dict_case_sensitive": {"ru": "С учётом регистра", "tk": "Harp ölçeginde", "tr": "Büyük/küçük harf", "en": "Case sensitive"},
    "tm_no_entries": {"ru": "Память переводов пуста.", "tk": "Terjime ýady boş.", "tr": "Çeviri belleği boş.", "en": "Translation memory is empty."},
    "tm_entries_count": {"ru": "{n} записей", "tk": "{n} ýazgy", "tr": "{n} kayıt", "en": "{n} entry(s)"},
    "tm_add_phrase": {"ru": "➕ Добавить фразу", "tk": "➕ Söz düzümini goş", "tr": "➕ İfade ekle", "en": "➕ Add a phrase"},
    "tm_source_phrase": {"ru": "Исходная фраза", "tk": "Çeşme söz düzümi", "tr": "Kaynak ifade", "en": "Source phrase"},
    "tm_target_phrase": {"ru": "Перевод фразы", "tk": "Terjime", "tr": "Çeviri", "en": "Target phrase"},
    "tm_save_phrase": {"ru": "Сохранить фразу", "tk": "Söz düzümini sakla", "tr": "İfadeyi kaydet", "en": "Save phrase"},

    # ----- channels (extra) -----
    "channels_no_channels": {
        "ru": "Каналов пока нет — создайте первого AI-агента выше.",
        "tk": "Kanallar entek ýok — ýokarda ilkinji AI-agentini dörediň.",
        "tr": "Henüz kanal yok — yukarıda ilk AI ajanınızı oluşturun.",
        "en": "No channels yet — create your first AI agent above.",
    },
    "channels_default_target": {
        "ru": "Целевой язык по умолчанию",
        "tk": "Düzgün boýunça maksat dili",
        "tr": "Varsayılan hedef dil",
        "en": "Default target language",
    },
    "channels_primary_lang": {"ru": "Основной язык", "tk": "Esasy dil", "tr": "Ana dil", "en": "Primary language"},
    "channels_use_case": {"ru": "Сценарий использования", "tk": "Ulanyş ýagdaýy", "tr": "Kullanım türü", "en": "Use case"},
    "channels_create_button": {"ru": "Создать канал", "tk": "Kanal döret", "tr": "Kanal oluştur", "en": "Create channel"},
    "channels_dub_notes": {"ru": "Заметки по дубляжу (необязательно)", "tk": "Dubläž bellikleri (hökman däl)", "tr": "Dublaj notları (isteğe bağlı)", "en": "Dubbing notes (optional)"},
    "channels_name_placeholder": {
        "ru": "Например: Блог, Новости, Туркменская культура",
        "tk": "Mysal: Blog, Habarlar, Türkmen medeniýeti",
        "tr": "Örn: Blog, Haberler, Türkmen kültürü",
        "en": "e.g. Blog, News, Turkmen culture",
    },

    # ----- voices catalog (extra) -----
    "voices_filter_lang": {"ru": "Язык", "tk": "Dil", "tr": "Dil", "en": "Language"},
    "voices_filter_use_case": {"ru": "Сценарий", "tk": "Ulanyşy", "tr": "Kullanım", "en": "Use case"},
    "voices_filter_gender": {"ru": "Пол", "tk": "Jyns", "tr": "Cinsiyet", "en": "Gender"},
    "voices_no_match": {
        "ru": "Под фильтры ничего не подошло.",
        "tk": "Süzgüçler boýunça hiç zat tapylmady.",
        "tr": "Filtrelere uyan ses yok.",
        "en": "No voices match these filters.",
    },
    "voices_catalog_caption": {
        "ru": "Готовые голосовые профили: пол, возраст, тон, темп, питч, языки и сценарии. Назначайте профиль каналу на вкладке «Каналы».",
        "tk": "Taýýar ses profilleri: jyns, ýaş, äheň, tizlik, äheň-uzynlygy, diller we ulanyşlar. Profil kanala «Kanallar» bölüminde belläň.",
        "tr": "Hazır ses profilleri: cinsiyet, yaş, ton, hız, perde, diller ve kullanımlar. Profili «Kanallar» sekmesinden bir kanala atayın.",
        "en": "Built-in voice profiles: gender, age, tone, speed, pitch, languages and use cases. Assign a profile to a channel on the Channels tab.",
    },

    # ----- custom voice (extra) -----
    "cv_create_section": {"ru": "➕ Создать голос", "tk": "➕ Ses döret", "tr": "➕ Ses oluştur", "en": "➕ Create a custom voice"},
    "cv_name_placeholder": {
        "ru": "Например: Мой голос — обычный",
        "tk": "Mysal: Meniň sesim — adaty",
        "tr": "Örn: Sesim — normal",
        "en": "e.g. My voice — natural",
    },
    "cv_speed": {"ru": "Скорость", "tk": "Tizlik", "tr": "Hız", "en": "Speed"},
    "cv_pitch": {"ru": "Высота", "tk": "Beýiklik", "tr": "Perde", "en": "Pitch"},
    "cv_emotion": {"ru": "Эмоция", "tk": "Duýgy", "tr": "Duygu", "en": "Emotion"},
    "cv_clarity": {"ru": "Чистота", "tk": "Arassalygy", "tr": "Berraklık", "en": "Clarity"},
    "cv_intensity": {"ru": "Сила", "tk": "Güýji", "tr": "Yoğunluk", "en": "Intensity"},
    "cv_use_case": {"ru": "Тип использования", "tk": "Ulanyş görnüşi", "tr": "Kullanım türü", "en": "Use case"},
    "cv_bind_channel": {"ru": "Привязать к каналу", "tk": "Kanala bagla", "tr": "Kanala bağla", "en": "Bind to channel"},
    "cv_bind_style": {"ru": "Привязать к стилю", "tk": "Stile bagla", "tr": "Stile bağla", "en": "Bind to style"},
    "cv_bind_video_use_case": {"ru": "Привязать к типу видео", "tk": "Wideo görnüşine bagla", "tr": "Video türüne bağla", "en": "Bind to video use case"},
    "cv_variant_of": {"ru": "Вариант голоса (родитель)", "tk": "Sesiň görnüşi (ene)", "tr": "Ses varyantı (üst)", "en": "Variant of (parent voice)"},
    "cv_standalone": {"ru": "— самостоятельный —", "tk": "— özbaşdak —", "tr": "— bağımsız —", "en": "— standalone —"},
    "cv_audio_section": {
        "ru": "**Аудио-семпл (необязательно)** — загрузите запись или пропустите.",
        "tk": "**Ses-nusga (hökman däl)** — ýazgy ýükläň ýa-da geçiň.",
        "tr": "**Ses örneği (isteğe bağlı)** — kayıt yükleyin veya atlayın.",
        "en": "**Audio sample (optional)** — upload a recording or skip.",
    },
    "cv_upload_sample": {"ru": "Загрузить запись", "tk": "Ýazgyny ýükle", "tr": "Kayıt yükle", "en": "Upload sample"},
    "cv_record_sample": {"ru": "…или записать с микрофона", "tk": "…ýa-da mikrofondan ýazgy alyň", "tr": "…veya mikrofonla kaydedin", "en": "…or record now (microphone)"},
    "cv_consent_help": {
        "ru": "Без подтверждения нельзя создать голосовой профиль. Не используйте чужой голос без разрешения.",
        "tk": "Tassyklamasyz ses profilini döretmek mümkin däl. Başganyň sesini ygtyýarsyz ulanmaň.",
        "tr": "Onay olmadan ses profili oluşturulamaz. Başkasının sesini izinsiz kullanmayın.",
        "en": "Without consent you cannot create a voice profile. Do not use another person's voice without permission.",
    },
    "cv_consent_required_error": {
        "ru": "Поставьте галочку согласия — без неё создание Custom Voice запрещено.",
        "tk": "Razylyk gutusyny belläň — onsuz Custom Voice döretmek gadagan.",
        "tr": "Onay kutusunu işaretleyin — onsuz Custom Voice oluşturulamaz.",
        "en": "Tick the consent checkbox — Custom Voice creation requires it.",
    },
    "cv_create_button": {"ru": "Создать голос", "tk": "Ses döret", "tr": "Ses oluştur", "en": "Create voice"},
    "cv_no_voices": {
        "ru": "Здесь появятся ваши голоса после создания.",
        "tk": "Döredilen sesler şu ýerde peýda bolar.",
        "tr": "Sesler oluşturulduğunda burada görünür.",
        "en": "Custom voices will appear here once you create one.",
    },
    "cv_voices_count": {"ru": "{n} голосов", "tk": "{n} ses", "tr": "{n} ses", "en": "{n} voice(s)"},
    "cv_search_placeholder": {"ru": "🔍 Поиск по имени", "tk": "🔍 Adyna görä gözleg", "tr": "🔍 Ada göre ara", "en": "🔍 Find by name"},
    "cv_preview_button": {"ru": "🔊 Прослушать пример", "tk": "🔊 Mysaly diňle", "tr": "🔊 Örneği dinle", "en": "🔊 Preview"},
    "cv_preview_caption_tk": {
        "ru": "Превью сделано офлайн через MMS-TTS — настоящее voice cloning требует провайдер XTTS / ElevenLabs (не настроен).",
        "tk": "Mysal MMS-TTS arkaly offline döredildi — hakyky voice cloning üçin XTTS / ElevenLabs gerek (sazlanmadyk).",
        "tr": "Önizleme MMS-TTS ile çevrimdışı oluşturuldu — gerçek ses klonlama için XTTS / ElevenLabs gerekir (yapılandırılmamış).",
        "en": "Preview was rendered offline via MMS-TTS — true voice cloning requires an XTTS / ElevenLabs provider (not configured).",
    },
    "cv_preview_warn_other_lang": {
        "ru": "Превью для ru/tr/en в MVP требует настроенного облачного TTS (OPENAI_API_KEY). "
              "Используйте FastAPI-маршрут `/v1/custom-voices/{id}/preview` для рендеринга.",
        "tk": "MVP-de ru/tr/en üçin mysal sazlanan bulut TTS (OPENAI_API_KEY) talap edýär. "
              "Rendering üçin FastAPI marşruty `/v1/custom-voices/{id}/preview` ulanyň.",
        "tr": "MVP'de ru/tr/en için önizleme yapılandırılmış bulut TTS (OPENAI_API_KEY) gerektirir. "
              "Render için FastAPI rotası `/v1/custom-voices/{id}/preview` kullanın.",
        "en": "Preview for ru/tr/en in this MVP needs a configured cloud TTS (OPENAI_API_KEY). "
              "Use the FastAPI route `/v1/custom-voices/{id}/preview` to render previews.",
    },
    "cv_variant_button": {"ru": "➕ Вариант", "tk": "➕ Görnüş", "tr": "➕ Varyant", "en": "➕ Variant"},
    "cv_variant_toast": {
        "ru": "Родительский голос задан — открой форму выше, чтобы добавить вариант.",
        "tk": "Ene ses bellendi — görnüş goşmak üçin ýokardaky görnüşi açyň.",
        "tr": "Üst ses ayarlandı — varyant eklemek için yukarıdaki formu açın.",
        "en": "Parent voice set — open the create form to add a variant.",
    },
    "cv_no_sample": {"ru": "📁 Нет аудио-семпла", "tk": "📁 Ses-nusgasy ýok", "tr": "📁 Ses örneği yok", "en": "📁 no audio sample uploaded"},
    "cv_sample_missing": {"ru": "📁 Файл семпла не найден на диске", "tk": "📁 Nusga faýly diskde tapylmady", "tr": "📁 Örnek dosyası diskte yok", "en": "📁 sample file missing on disk"},
    "cv_consent_confirmed_at": {"ru": "✅ Согласие подтверждено: {ts}", "tk": "✅ Razylyk tassyklandy: {ts}", "tr": "✅ Onay verildi: {ts}", "en": "✅ consent confirmed at {ts}"},
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
