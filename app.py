"""Murat AI — рабочий Streamlit preview-интерфейс.

Цель этой ветки: дать пользователю нормальный экран проверки продукта в браузере:
- русский интерфейс без смешивания английских подписей;
- слева видео по ссылке или загруженный файл;
- справа текст/перевод/озвучка;
- выбор голоса и актёров;
- попытка реального скачивания публичного видео через yt-dlp;
- браузерная preview-озвучка выбранного текста.

Полный AI-пайплайн Whisper/translation/TTS/render MP4 должен работать на VPS/GPU.
"""

from __future__ import annotations

import html
import json
import os
import re
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from textwrap import shorten
from typing import Dict, List, Tuple

import streamlit as st
import streamlit.components.v1 as components

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
LANGS = ["ru", "tk", "tr", "en"]

UI = {
    "ru": {
        "subtitle": "Профессиональный перевод, озвучка и видеодубляж",
        "notice": "На этом экране можно реально вставить ссылку/файл, увидеть видео слева, вставить текст справа и прослушать preview-озвучку. Полный AI-рендер MP4 работает на VPS/GPU.",
        "ui_lang": "Язык интерфейса",
        "channel": "Канал / AI-агент",
        "status": "Интерфейс работает",
        "full": "Полный режим: VPS/GPU",
        "tab_studio": "🎬 Студия дубляжа",
        "tab_voice": "🎙️ Голос и аватар",
        "tab_dictionary": "📚 Словарь",
        "tab_export": "📦 Скачать результат",
        "studio_title": "🎬 Студия дубляжа Murat AI",
        "studio_help": "Слева добавь видео: ссылка или файл. Справа вставь текст, выбери язык и голос. Нажми перевод и озвучку.",
        "left_video": "1. Видео / аудио",
        "url": "Ссылка на видео",
        "url_placeholder": "Вставь ссылку YouTube, TikTok, Instagram или прямую ссылку mp4/webm",
        "show_url": "Показать ссылку слева",
        "download_url": "Скачать видео по ссылке",
        "upload": "Или загрузи файл с компьютера",
        "no_video": "Видео появится здесь",
        "download_ok": "Видео скачано и показано слева.",
        "download_fail": "Не получилось скачать ссылку. Причина:",
        "right_text": "2. Текст, перевод и озвучка",
        "source_text": "Исходный текст / распознанный текст",
        "source_text_help": "Сюда можно вставить текст вручную. В полном режиме VPS этот текст появится автоматически после распознавания речи из видео.",
        "from": "С языка",
        "to": "На язык",
        "style": "Стиль",
        "tone": "Тон",
        "emotion": "Эмоция",
        "voice": "Голос",
        "translate": "Перевести",
        "translation": "Готовый перевод",
        "speak": "Прослушать озвучку",
        "tts_note": "Preview-озвучка запускается голосами браузера. Кино-озвучка, туркменский MMS/коммерческий TTS и финальный MP4 — на VPS/GPU.",
        "actors": "Актёры и голоса",
        "segments": "Сегменты и тайминг",
        "sync": "Синхронизация",
        "sync_text": "Полный AI должен подгонять перевод под время: сокращать длинные фразы, делить реплики, добавлять паузы и не давать сценарию уходить вперёд озвучки.",
        "voice_title": "🎙️ Свой голос / AI-аватар",
        "voice_help": "Загрузи образец голоса или видео с лицом. В полном режиме система очищает шум, удаляет эхо, нормализует громкость и создаёт голосовой профиль.",
        "voice_file": "Образец голоса",
        "avatar_file": "Видео для аватара",
        "voice_name": "Название голоса / аватара",
        "consent": "Я подтверждаю, что имею право использовать этот голос/видео",
        "create_voice": "Создать голосовой профиль",
        "dictionary_title": "📚 Замена слов",
        "dictionary_help": "Если слово переведено неправильно, добавь правило. Потом Murat AI должен каждый раз подменять это слово автоматически.",
        "word_from": "Какое слово искать",
        "word_to": "На что заменить",
        "scope": "Где применять",
        "save": "Сохранить правило",
        "export_title": "📦 Готовый результат",
        "export_help": "Здесь должны появляться финальный MP4, субтитры, аудиодорожки и ZIP-пакет. Сейчас доступен экспорт текста/SRT из preview.",
        "download_text": "Скачать перевод TXT",
        "download_srt": "Скачать SRT",
        "platforms": "Платформы публикации",
        "package": "Создать пакет публикации",
    },
    "en": {
        "subtitle": "Professional translation, voiceover and video dubbing",
        "notice": "Paste a video link/file on the left, text on the right, then preview translation and voiceover. Full MP4 AI rendering runs on VPS/GPU.",
        "ui_lang": "Interface language",
        "channel": "Channel / AI agent",
        "status": "UI is online",
        "full": "Full mode: VPS/GPU",
        "tab_studio": "🎬 Dubbing studio",
        "tab_voice": "🎙️ Voice and avatar",
        "tab_dictionary": "📚 Dictionary",
        "tab_export": "📦 Downloads",
        "studio_title": "🎬 Murat AI dubbing studio",
        "studio_help": "Add video on the left, paste text on the right, choose language and voice, then translate and preview voiceover.",
        "left_video": "1. Video / audio",
        "url": "Video URL",
        "url_placeholder": "Paste YouTube, TikTok, Instagram or direct mp4/webm URL",
        "show_url": "Show URL on the left",
        "download_url": "Download video from URL",
        "upload": "Or upload file from computer",
        "no_video": "Video will appear here",
        "download_ok": "Video downloaded and shown on the left.",
        "download_fail": "Could not download the URL. Reason:",
        "right_text": "2. Text, translation and voiceover",
        "source_text": "Source / recognized text",
        "source_text_help": "Paste text manually. In full VPS mode this text appears automatically after ASR.",
        "from": "From",
        "to": "To",
        "style": "Style",
        "tone": "Tone",
        "emotion": "Emotion",
        "voice": "Voice",
        "translate": "Translate",
        "translation": "Final translation",
        "speak": "Play voice preview",
        "tts_note": "Preview voiceover uses browser voices. Cinema TTS and final MP4 rendering run on VPS/GPU.",
        "actors": "Actors and voices",
        "segments": "Segments and timing",
        "sync": "Synchronization",
        "sync_text": "Full AI must fit translation to timing: shorten long phrases, split dialogue and add pauses.",
        "voice_title": "🎙️ Custom voice / AI avatar",
        "voice_help": "Upload voice or face video. Full mode cleans noise, removes echo, normalizes loudness and creates a voice profile.",
        "voice_file": "Voice sample",
        "avatar_file": "Avatar video",
        "voice_name": "Voice / avatar name",
        "consent": "I confirm I have the right to use this voice/video",
        "create_voice": "Create voice profile",
        "dictionary_title": "📚 Word replacement",
        "dictionary_help": "Save rules for words Murat AI must replace automatically every time.",
        "word_from": "Find word",
        "word_to": "Replace with",
        "scope": "Scope",
        "save": "Save rule",
        "export_title": "📦 Result downloads",
        "export_help": "Final MP4, subtitles, audio tracks and ZIP should appear here. Preview exports text/SRT now.",
        "download_text": "Download TXT translation",
        "download_srt": "Download SRT",
        "platforms": "Publishing platforms",
        "package": "Create publishing package",
    },
}

# Пока для туркменского и турецкого используем английский fallback, но русский полностью русский.
UI["tk"] = UI["en"]
UI["tr"] = UI["en"]

CHANNELS = [
    "Основной канал",
    "Туркменская культура",
    "Блог",
    "Новости",
    "Уличный разговорный стиль",
    "Кино-дубляж",
]
STYLES = ["Естественный", "Блогерский", "Разговорный", "Уличный", "Литературный", "Официальный", "Кино", "Реклама"]
TONES = ["Спокойный", "Уверенный", "Дружелюбный", "Тёплый", "Серьёзный", "Эмоциональный", "Культурный"]
EMOTIONS = ["Нейтрально", "Радостно", "Грустно", "Серьёзно", "Взволнованно", "Тепло"]
VOICE_PROFILES = [
    "Туркменский мужской — кино",
    "Туркменский женский — чистый",
    "Туркменский подростковый",
    "Русский мужской — документальный",
    "Русский женский — блог",
    "Турецкий мужской — уверенный",
    "Английский женский — естественный",
    "Мой загруженный голос",
]
PLATFORMS = ["YouTube", "TikTok", "Instagram", "Facebook", "Telegram", "X", "Скачать на компьютер"]

SAMPLE_TRANSLATIONS: Dict[Tuple[str, str], str] = {
    ("ru", "tk"): "Salam. Men bu wideony arassa türkmen diline terjime edip, professional derejede seslendirmek isleýärin.",
    ("tk", "ru"): "Здравствуйте. Я хочу перевести это видео и сделать профессиональную озвучку.",
    ("ru", "en"): "Hello. I want to translate this video into clean English and create professional dubbing.",
    ("en", "ru"): "Здравствуйте. Я хочу перевести это видео на русский и сделать профессиональную озвучку.",
    ("ru", "tr"): "Merhaba. Bu videoyu temiz Türkçeye çevirip profesyonel dublaj yapmak istiyorum.",
    ("tr", "ru"): "Здравствуйте. Это тестовый перевод с турецкого на русский.",
}


def t(key: str) -> str:
    lang = st.session_state.get("ui_lang", "ru")
    return UI.get(lang, UI["ru"]).get(key, key)


def is_direct_video_url(url: str) -> bool:
    return bool(re.search(r"\.(mp4|webm|mov|m4v)(\?|$)", url.strip(), flags=re.I))


def download_video(url: str) -> str:
    """Download a public URL with yt-dlp and return local file path."""
    from yt_dlp import YoutubeDL  # type: ignore

    target_dir = Path(tempfile.gettempdir()) / "murat_ai_preview"
    target_dir.mkdir(parents=True, exist_ok=True)
    outtmpl = str(target_dir / f"{uuid.uuid4().hex}.%(ext)s")
    opts = {
        "outtmpl": outtmpl,
        "format": "best[ext=mp4][vcodec!=none][acodec!=none]/best[ext=mp4]/best",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 30,
        "retries": 1,
        "merge_output_format": "mp4",
    }
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        if not filename.endswith(".mp4") and os.path.exists(Path(filename).with_suffix(".mp4")):
            filename = str(Path(filename).with_suffix(".mp4"))
    return filename


def apply_dictionary_rules(text: str, rules: List[Dict[str, str]]) -> str:
    result = text
    for rule in rules:
        src = (rule.get("from") or "").strip()
        dst = (rule.get("to") or "").strip()
        if src and dst:
            result = re.sub(re.escape(src), dst, result, flags=re.I)
    return result


def translate_preview(text: str, src: str, tgt: str) -> str:
    if not text.strip():
        return ""
    base = SAMPLE_TRANSLATIONS.get((src, tgt))
    if base:
        return base
    return f"[{LANG_LABELS[src]} → {LANG_LABELS[tgt]}] {text}"


def make_srt(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        lines = ["Murat AI preview"]
    blocks = []
    sec = 0
    for idx, line in enumerate(lines, 1):
        start = f"00:00:{sec:02d},000"
        sec += 4
        end = f"00:00:{sec:02d},000"
        blocks.append(f"{idx}\n{start} --> {end}\n{line}\n")
    return "\n".join(blocks)


def make_segments(text: str) -> List[Dict[str, str]]:
    chunks = [c.strip() for c in re.split(r"[.!?\n]+", text) if c.strip()]
    if not chunks:
        chunks = ["Готовый перевод появится здесь"]
    rows = []
    current = 0
    actors = ["Актёр 1", "Актёр 2", "Диктор"]
    for i, chunk in enumerate(chunks[:8]):
        duration = max(3, min(7, len(chunk) // 18 + 3))
        rows.append({
            "Начало": f"00:{current:02d}",
            "Конец": f"00:{current + duration:02d}",
            "Кто говорит": actors[i % len(actors)],
            "Текст": shorten(chunk, width=90, placeholder="…"),
            "Статус": "Помещается",
        })
        current += duration
    return rows


def speech_component(text: str, lang: str, voice_name: str, button_label: str) -> None:
    safe_text = json.dumps(text)
    safe_lang = json.dumps({"ru": "ru-RU", "tk": "tr-TR", "tr": "tr-TR", "en": "en-US"}.get(lang, "ru-RU"))
    safe_voice = json.dumps(voice_name)
    components.html(
        f"""
        <div style="font-family:Inter,Arial,sans-serif; padding:14px; border-radius:16px; background:#111827; color:white; border:1px solid #374151;">
          <button id="speakBtn" style="background:#7c3aed;color:white;border:0;border-radius:12px;padding:12px 18px;font-weight:800;cursor:pointer;">▶ {html.escape(button_label)}</button>
          <button id="stopBtn" style="margin-left:8px;background:#374151;color:white;border:0;border-radius:12px;padding:12px 18px;font-weight:700;cursor:pointer;">■ Стоп</button>
          <div style="margin-top:10px;color:#cbd5e1;font-size:13px;">Голос: {html.escape(voice_name)} · preview через браузер</div>
        </div>
        <script>
          const text = {safe_text};
          const lang = {safe_lang};
          const voiceHint = {safe_voice}.toLowerCase();
          const speak = () => {{
            window.speechSynthesis.cancel();
            const utter = new SpeechSynthesisUtterance(text || 'Нет текста для озвучки');
            utter.lang = lang;
            utter.rate = voiceHint.includes('кино') ? 0.92 : 1.0;
            utter.pitch = voiceHint.includes('женский') ? 1.12 : 0.95;
            const voices = window.speechSynthesis.getVoices();
            const match = voices.find(v => v.lang && v.lang.toLowerCase().startsWith(lang.slice(0,2).toLowerCase()));
            if (match) utter.voice = match;
            window.speechSynthesis.speak(utter);
          }};
          document.getElementById('speakBtn').onclick = speak;
          document.getElementById('stopBtn').onclick = () => window.speechSynthesis.cancel();
        </script>
        """,
        height=115,
    )


st.markdown(
    """
    <style>
    .block-container {padding-top: 2.2rem; max-width: 1420px;}
    [data-testid="stSidebar"] {background: linear-gradient(180deg,#121426,#24283a);}    
    .hero {border:1px solid rgba(255,255,255,.12); border-radius:24px; padding:24px; background:linear-gradient(135deg,rgba(124,58,237,.18),rgba(14,165,233,.10)); margin-bottom:18px;}
    .card {border:1px solid rgba(255,255,255,.14); border-radius:22px; padding:18px; background:rgba(255,255,255,.045); box-shadow:0 14px 40px rgba(0,0,0,.16);} 
    .drop {border:2px dashed rgba(124,58,237,.75); border-radius:24px; padding:28px; min-height:310px; text-align:center; background:rgba(124,58,237,.08); display:flex; flex-direction:column; justify-content:center;}
    .pill {display:inline-block; padding:7px 12px; border-radius:999px; background:#143d2a; color:#b9ffd8; font-weight:800;}
    </style>
    """,
    unsafe_allow_html=True,
)

if "dictionary_rules" not in st.session_state:
    st.session_state.dictionary_rules = []
if "downloaded_video" not in st.session_state:
    st.session_state.downloaded_video = None
if "translation_text" not in st.session_state:
    st.session_state.translation_text = ""

st.sidebar.title("🌐 Murat AI")
st.session_state["ui_lang"] = st.sidebar.selectbox(
    "Язык интерфейса",
    LANGS,
    format_func=lambda x: LANG_LABELS[x],
    index=0,
    key="ui_lang_select",
)
active_channel = st.sidebar.selectbox(t("channel"), CHANNELS)
st.sidebar.success(t("status"))
st.sidebar.caption(t("full"))

st.markdown(f"<div class='hero'><h1>🌐 Murat AI</h1><h3>{t('subtitle')}</h3><p>{t('notice')}</p></div>", unsafe_allow_html=True)

tab_studio, tab_voice, tab_dictionary, tab_export = st.tabs([
    t("tab_studio"),
    t("tab_voice"),
    t("tab_dictionary"),
    t("tab_export"),
])

with tab_studio:
    st.header(t("studio_title"))
    st.write(t("studio_help"))
    left, right = st.columns([1.05, 1.25], gap="large")

    with left:
        st.markdown(f"<div class='card'><h3>{t('left_video')}</h3></div>", unsafe_allow_html=True)
        video_url = st.text_input(t("url"), placeholder=t("url_placeholder"))
        c_show, c_download = st.columns(2)
        with c_show:
            show_clicked = st.button(t("show_url"), use_container_width=True)
        with c_download:
            download_clicked = st.button(t("download_url"), use_container_width=True, type="primary")

        if show_clicked and video_url.strip():
            st.session_state.downloaded_video = video_url.strip()

        if download_clicked and video_url.strip():
            with st.spinner("Скачиваю видео..."):
                try:
                    st.session_state.downloaded_video = download_video(video_url.strip())
                    st.success(t("download_ok"))
                except Exception as exc:  # noqa: BLE001
                    st.error(f"{t('download_fail')} {exc}")
                    st.session_state.downloaded_video = video_url.strip()

        uploaded = st.file_uploader(t("upload"), type=["mp4", "mov", "webm", "mkv", "mp3", "wav", "m4a"])
        if uploaded is not None:
            st.session_state.downloaded_video = uploaded

        source = st.session_state.downloaded_video
        if source is None:
            st.markdown(f"<div class='drop'>🎬<br><br>{t('no_video')}</div>", unsafe_allow_html=True)
        else:
            try:
                if isinstance(source, str):
                    if is_direct_video_url(source) or os.path.exists(source):
                        st.video(source)
                    else:
                        st.video(source)
                else:
                    name = getattr(source, "name", "").lower()
                    if name.endswith(("mp3", "wav", "m4a")):
                        st.audio(source)
                    else:
                        st.video(source)
            except Exception:
                st.info("Ссылка принята. Если браузер не показывает видео, нажми «Скачать видео по ссылке».")

    with right:
        st.markdown(f"<div class='card'><h3>{t('right_text')}</h3></div>", unsafe_allow_html=True)
        r1, r2, r3 = st.columns(3)
        source_lang = r1.selectbox(t("from"), LANGS, format_func=lambda x: LANG_LABELS[x], index=0)
        target_lang = r2.selectbox(t("to"), LANGS, format_func=lambda x: LANG_LABELS[x], index=1)
        voice = r3.selectbox(t("voice"), VOICE_PROFILES, index=0)
        r4, r5, r6 = st.columns(3)
        style = r4.selectbox(t("style"), STYLES, index=0)
        tone = r5.selectbox(t("tone"), TONES, index=2)
        emotion = r6.selectbox(t("emotion"), EMOTIONS, index=0)

        source_text = st.text_area(
            t("source_text"),
            value="Привет. Я хочу перевести это видео на чистый туркменский язык и сделать профессиональную озвучку.",
            height=150,
            help=t("source_text_help"),
        )
        if st.button(t("translate"), type="primary", use_container_width=True):
            translated = translate_preview(source_text, source_lang, target_lang)
            translated = apply_dictionary_rules(translated, st.session_state.dictionary_rules)
            st.session_state.translation_text = translated
            st.session_state.segments = make_segments(translated)

        translation = st.text_area(t("translation"), value=st.session_state.translation_text, height=160)
        st.session_state.translation_text = translation
        st.caption(t("tts_note"))
        speech_component(translation or source_text, target_lang, voice, t("speak"))

        st.subheader(t("actors"))
        actor_rows = [
            {"Актёр": "Актёр 1", "Роль": "Главный герой", "Голос": voice, "Качество": "Кино"},
            {"Актёр": "Актёр 2", "Роль": "Второй герой", "Голос": "Туркменский женский — чистый", "Качество": "Студия"},
            {"Актёр": "Диктор", "Роль": "Закадровый голос", "Голос": "Русский мужской — документальный", "Качество": "Broadcast"},
        ]
        st.data_editor(actor_rows, use_container_width=True, hide_index=True, num_rows="dynamic")

        st.subheader(t("segments"))
        st.dataframe(st.session_state.get("segments", make_segments(translation or source_text)), use_container_width=True, hide_index=True)
        st.markdown(f"<span class='pill'>✅ {t('sync')}</span>", unsafe_allow_html=True)
        st.caption(t("sync_text"))

with tab_voice:
    st.header(t("voice_title"))
    st.write(t("voice_help"))
    v1, v2 = st.columns(2, gap="large")
    with v1:
        voice_name = st.text_input(t("voice_name"), "Мой голос")
        st.file_uploader(t("voice_file"), type=["wav", "mp3", "m4a", "flac"], key="voice_sample")
        st.checkbox("Очистить шум", value=True)
        st.checkbox("Удалить эхо", value=True)
        st.checkbox("Нормализовать громкость", value=True)
        consent = st.checkbox(t("consent"))
        if st.button(t("create_voice"), type="primary"):
            if consent:
                st.success(f"Голосовой профиль «{voice_name}» принят для обработки.")
            else:
                st.error("Нужно подтвердить право на использование голоса/видео.")
    with v2:
        st.file_uploader(t("avatar_file"), type=["mp4", "mov", "webm"], key="avatar_sample")
        st.markdown("<div class='drop'>🧑‍🎤<br><br>Здесь будет preview аватара</div>", unsafe_allow_html=True)

with tab_dictionary:
    st.header(t("dictionary_title"))
    st.write(t("dictionary_help"))
    d1, d2, d3 = st.columns([1, 1, 1])
    word_from = d1.text_input(t("word_from"))
    word_to = d2.text_input(t("word_to"))
    scope = d3.selectbox(t("scope"), ["Глобально", active_channel])
    if st.button(t("save"), type="primary"):
        if word_from.strip() and word_to.strip():
            st.session_state.dictionary_rules.append({"from": word_from.strip(), "to": word_to.strip(), "scope": scope})
            st.success(f"Правило сохранено: {word_from} → {word_to}")
        else:
            st.error("Заполни оба поля.")
    if st.session_state.dictionary_rules:
        st.dataframe(st.session_state.dictionary_rules, use_container_width=True)

with tab_export:
    st.header(t("export_title"))
    st.write(t("export_help"))
    final_text = st.session_state.translation_text or "Murat AI preview"
    st.download_button(t("download_text"), data=final_text.encode("utf-8"), file_name="murat-ai-translation.txt")
    st.download_button(t("download_srt"), data=make_srt(final_text).encode("utf-8"), file_name="murat-ai-subtitles.srt")
    platforms = st.multiselect(t("platforms"), PLATFORMS, default=["YouTube", "TikTok", "Скачать на компьютер"])
    if st.button(t("package"), type="primary"):
        st.json({
            "platforms": platforms,
            "created_at": datetime.utcnow().isoformat(),
            "translation": final_text,
            "status": "preview_package_created",
        })

st.markdown("---")
st.caption("Murat AI · streamlit-preview. Реальный AI-рендер видео запускается только на VPS/GPU backend.")
