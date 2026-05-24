"""Murat AI — простой рабочий preview-интерфейс: слева вход, справа готовый результат.

Ветка streamlit-preview нужна, чтобы в браузере было понятно, как должен выглядеть продукт:
- слева пользователь даёт источник: ссылка, файл, текст или образец голоса;
- справа появляется результат: готовый текст, preview-озвучка, обработанный голос или финальное видео;
- русский интерфейс без смешивания с английским;
- попытка скачивания публичной ссылки через yt-dlp;
- browser TTS для быстрой проверки озвучки текста.

Полный AI-рендер видео, клонирование голоса и чистая туркменская TTS-модель работают на VPS/GPU backend.
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
from typing import Dict, List, Tuple

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Murat AI", page_icon="🌐", layout="wide", initial_sidebar_state="collapsed")

LANG_LABELS = {"ru": "Русский", "tk": "Туркменский", "tr": "Турецкий", "en": "Английский"}
LANGS = ["ru", "tk", "tr", "en"]

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

SAMPLE_TRANSLATIONS: Dict[Tuple[str, str], str] = {
    ("ru", "tk"): "Salam. Men bu wideony arassa türkmen diline terjime edip, professional derejede seslendirmek isleýärin.",
    ("tk", "ru"): "Здравствуйте. Я хочу перевести это видео и сделать профессиональную озвучку.",
    ("ru", "en"): "Hello. I want to translate this video into clean English and create professional voiceover.",
    ("en", "ru"): "Здравствуйте. Я хочу перевести это видео на русский и сделать профессиональную озвучку.",
    ("ru", "tr"): "Merhaba. Bu videoyu temiz Türkçeye çevirip profesyonel dublaj yapmak istiyorum.",
    ("tr", "ru"): "Здравствуйте. Это тестовый перевод с турецкого на русский.",
}


def init_state() -> None:
    defaults = {
        "source_media": None,
        "final_text": "",
        "dictionary_rules": [],
        "last_action": "Ожидаю источник слева.",
        "voice_sample_name": None,
        "clean_voice_ready": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def direct_media_url(url: str) -> bool:
    return bool(re.search(r"\.(mp4|webm|mov|m4v|mp3|wav|m4a)(\?|$)", url.strip(), flags=re.I))


def download_video(url: str) -> str:
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
        mp4 = str(Path(filename).with_suffix(".mp4"))
        return mp4 if os.path.exists(mp4) else filename


def apply_dictionary(text: str) -> str:
    result = text
    for rule in st.session_state.dictionary_rules:
        src = (rule.get("from") or "").strip()
        dst = (rule.get("to") or "").strip()
        if src and dst:
            result = re.sub(re.escape(src), dst, result, flags=re.I)
    return result


def translate_preview(text: str, src: str, tgt: str) -> str:
    if not text.strip():
        return ""
    translated = SAMPLE_TRANSLATIONS.get((src, tgt), f"[{LANG_LABELS[src]} → {LANG_LABELS[tgt]}] {text}")
    return apply_dictionary(translated)


def make_srt(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()] or ["Murat AI preview"]
    out = []
    sec = 0
    for i, line in enumerate(lines, 1):
        out.append(f"{i}\n00:00:{sec:02d},000 --> 00:00:{sec + 4:02d},000\n{line}\n")
        sec += 4
    return "\n".join(out)


def speech_button(text: str, lang: str, voice: str) -> None:
    safe_text = json.dumps(text or "Нет текста для озвучки")
    browser_lang = {"ru": "ru-RU", "tk": "tr-TR", "tr": "tr-TR", "en": "en-US"}.get(lang, "ru-RU")
    safe_lang = json.dumps(browser_lang)
    safe_voice = json.dumps(voice)
    components.html(
        f"""
        <div style="font-family:Inter,Arial,sans-serif; padding:16px; border-radius:18px; background:#111827; color:white; border:1px solid #334155;">
            <button id="play" style="background:#7c3aed;color:#fff;border:0;border-radius:14px;padding:13px 20px;font-weight:800;cursor:pointer;">▶ Прослушать озвучку</button>
            <button id="stop" style="margin-left:8px;background:#334155;color:#fff;border:0;border-radius:14px;padding:13px 20px;font-weight:800;cursor:pointer;">■ Стоп</button>
            <div style="margin-top:10px;color:#cbd5e1;font-size:13px;">Preview-голос: {html.escape(voice)}. В полном режиме здесь будет реальный TTS/мой голос.</div>
        </div>
        <script>
            const text = {safe_text};
            const lang = {safe_lang};
            const voiceName = {safe_voice}.toLowerCase();
            function run() {{
                window.speechSynthesis.cancel();
                const u = new SpeechSynthesisUtterance(text);
                u.lang = lang;
                u.rate = voiceName.includes('кино') ? 0.90 : 1.0;
                u.pitch = voiceName.includes('женский') ? 1.12 : 0.95;
                const voices = window.speechSynthesis.getVoices();
                const found = voices.find(v => v.lang && v.lang.toLowerCase().startsWith(lang.slice(0,2).toLowerCase()));
                if (found) u.voice = found;
                window.speechSynthesis.speak(u);
            }}
            document.getElementById('play').onclick = run;
            document.getElementById('stop').onclick = () => window.speechSynthesis.cancel();
        </script>
        """,
        height=120,
    )


def show_media(source) -> None:
    if source is None:
        st.markdown("<div class='empty'>🎬<br><br>Здесь появится видео или аудио</div>", unsafe_allow_html=True)
        return
    try:
        if hasattr(source, "name"):
            name = source.name.lower()
            if name.endswith(("mp3", "wav", "m4a", "flac", "ogg")):
                st.audio(source)
            else:
                st.video(source)
        else:
            st.video(source)
    except Exception:
        st.info("Источник принят. Если браузер не показывает ссылку напрямую, нажми «Скачать ссылку».")


init_state()

st.markdown(
    """
    <style>
    .block-container {max-width: 1440px; padding-top: 1.8rem;}
    .hero {border-radius:28px; padding:26px 30px; background:linear-gradient(135deg,#181a2f,#261b48 55%,#0f3550); border:1px solid rgba(255,255,255,.14); margin-bottom:20px;}
    .hero h1 {margin:0; font-size:44px;}
    .hero p {font-size:18px; color:#dbeafe; margin:.5rem 0 0;}
    .panel {border-radius:26px; padding:20px; background:rgba(255,255,255,.045); border:1px solid rgba(255,255,255,.14); box-shadow:0 20px 45px rgba(0,0,0,.18); min-height:720px;}
    .panel-title {font-size:23px; font-weight:900; margin-bottom:8px;}
    .panel-sub {color:#cbd5e1; margin-bottom:16px;}
    .empty {border:2px dashed rgba(124,58,237,.75); border-radius:24px; padding:46px; min-height:330px; text-align:center; background:rgba(124,58,237,.08); display:flex; flex-direction:column; justify-content:center; color:#dbeafe; font-size:18px;}
    .ok {display:inline-block; padding:8px 13px; border-radius:999px; background:#143d2a; color:#b9ffd8; font-weight:800; margin:6px 0 12px;}
    .warn {display:inline-block; padding:8px 13px; border-radius:999px; background:#3b2a10; color:#ffe0a3; font-weight:800; margin:6px 0 12px;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    "<div class='hero'><h1>🌐 Murat AI</h1><p>Слева вставляешь источник. Справа получаешь готовый результат: текст, озвучку, обработанный голос или видео.</p></div>",
    unsafe_allow_html=True,
)

mode = st.radio(
    "Что сделать?",
    [
        "Видео → готовое видео с озвучкой",
        "Текст → озвучка",
        "Текст → готовый перевод",
        "Мой голос → чистый голос / озвучка моим голосом",
    ],
    horizontal=True,
)

left, right = st.columns([1, 1], gap="large")

with left:
    st.markdown("<div class='panel'>", unsafe_allow_html=True)
    st.markdown("<div class='panel-title'>⬅️ Входные данные</div>", unsafe_allow_html=True)
    st.markdown("<div class='panel-sub'>Сюда вставляется ссылка, файл, текст или твой голос.</div>", unsafe_allow_html=True)

    if mode == "Видео → готовое видео с озвучкой":
        url = st.text_input("Ссылка на видео", placeholder="YouTube / TikTok / Instagram / прямой mp4")
        b1, b2 = st.columns(2)
        if b1.button("Показать ссылку", use_container_width=True):
            if url.strip():
                st.session_state.source_media = url.strip()
                st.session_state.last_action = "Ссылка поставлена слева."
        if b2.button("Скачать ссылку", type="primary", use_container_width=True):
            if url.strip():
                try:
                    with st.spinner("Скачиваю видео..."):
                        st.session_state.source_media = download_video(url.strip())
                        st.session_state.last_action = "Видео скачано."
                    st.success("Видео скачано.")
                except Exception as exc:
                    st.session_state.source_media = url.strip()
                    st.error(f"Не удалось скачать. Показываю ссылку напрямую. Ошибка: {exc}")
        uploaded = st.file_uploader("Или загрузи видео/аудио с компьютера", type=["mp4", "mov", "webm", "mkv", "mp3", "wav", "m4a"])
        if uploaded is not None:
            st.session_state.source_media = uploaded
            st.session_state.last_action = "Файл загружен."
        show_media(st.session_state.source_media)
        source_text = st.text_area("Текст из видео / ручная правка текста", height=130, value="Привет. Я хочу перевести это видео на туркменский язык и озвучить моим голосом.")

    elif mode == "Текст → озвучка":
        source_text = st.text_area("Текст для озвучки", height=310, value="Привет. Это тест озвучки Murat AI. Я выбираю голос, и справа сразу слушаю результат.")
        st.info("Видео не нужно. Слева только текст, справа готовая озвучка.")

    elif mode == "Текст → готовый перевод":
        source_text = st.text_area("Текст для перевода", height=360, value="Привет. Я хочу получить чистый туркменский перевод и потом при необходимости заменить отдельные слова.")
        st.info("Слева текст, справа готовый перевод.")

    else:
        st.markdown("### 1. Загрузи свой голос")
        voice_sample = st.file_uploader("Аудиозапись твоего голоса", type=["wav", "mp3", "m4a", "flac", "ogg"])
        if voice_sample is not None:
            st.session_state.voice_sample_name = voice_sample.name
            st.audio(voice_sample)
        st.checkbox("Убрать шум", value=True)
        st.checkbox("Удалить эхо", value=True)
        st.checkbox("Выровнять громкость", value=True)
        st.checkbox("Сделать голос чистым для озвучки", value=True)
        source_text = st.text_area("Текст, который нужно озвучить моим голосом", height=170, value="Этот текст должен быть озвучен моим голосом после очистки аудио и создания голосового профиля.")
        if st.button("Обработать мой голос", type="primary", use_container_width=True):
            st.session_state.clean_voice_ready = True
            st.session_state.last_action = "Голос принят для очистки и создания профиля."

    st.markdown("</div>", unsafe_allow_html=True)

with right:
    st.markdown("<div class='panel'>", unsafe_allow_html=True)
    st.markdown("<div class='panel-title'>➡️ Готовый результат</div>", unsafe_allow_html=True)
    st.markdown("<div class='panel-sub'>Здесь появляется то, что пользователь должен получить.</div>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    src_lang = c1.selectbox("С языка", LANGS, format_func=lambda x: LANG_LABELS[x], index=0)
    tgt_lang = c2.selectbox("На язык", LANGS, format_func=lambda x: LANG_LABELS[x], index=1)
    voice = c3.selectbox("Голос", VOICE_PROFILES, index=0)

    if mode in ["Видео → готовое видео с озвучкой", "Текст → готовый перевод"]:
        if st.button("Создать результат", type="primary", use_container_width=True):
            st.session_state.final_text = translate_preview(source_text, src_lang, tgt_lang)
            st.session_state.last_action = "Перевод создан."
    elif mode == "Текст → озвучка":
        if st.button("Создать озвучку", type="primary", use_container_width=True):
            st.session_state.final_text = source_text
            st.session_state.last_action = "Озвучка готова к прослушиванию."
    else:
        if st.button("Озвучить моим голосом", type="primary", use_container_width=True):
            st.session_state.final_text = source_text
            st.session_state.last_action = "Preview-озвучка готова. Полный режим использует твой очищенный голосовой профиль."

    st.markdown(f"<span class='ok'>✅ {html.escape(st.session_state.last_action)}</span>", unsafe_allow_html=True)

    final_text = st.text_area("Готовый текст / сценарий", value=st.session_state.final_text, height=180)
    st.session_state.final_text = final_text

    if mode == "Видео → готовое видео с озвучкой":
        st.markdown("### Финальное видео")
        show_media(st.session_state.source_media)
        st.caption("В preview справа показывается исходное видео как место финального результата. На VPS здесь будет готовый MP4 с новой озвучкой.")
        speech_button(final_text or source_text, tgt_lang, voice)
    elif mode == "Текст → озвучка":
        st.markdown("### Готовая озвучка")
        speech_button(final_text or source_text, tgt_lang, voice)
    elif mode == "Текст → готовый перевод":
        st.markdown("### Готовый перевод")
        st.download_button("Скачать перевод TXT", data=(final_text or "").encode("utf-8"), file_name="murat-ai-translation.txt")
        st.download_button("Скачать субтитры SRT", data=make_srt(final_text or "").encode("utf-8"), file_name="murat-ai-subtitles.srt")
    else:
        st.markdown("### Готовый очищенный голос / озвучка моим голосом")
        if st.session_state.clean_voice_ready:
            st.markdown("<span class='ok'>✅ Голос очищен: шум, эхо и громкость обработаны в полном режиме.</span>", unsafe_allow_html=True)
        else:
            st.markdown("<span class='warn'>⚠️ Сначала загрузи голос слева и нажми «Обработать мой голос».</span>", unsafe_allow_html=True)
        speech_button(final_text or source_text, tgt_lang, "Мой загруженный голос")

    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("---")
with st.expander("📚 Замена слов — чтобы Murat AI каждый раз исправлял нужное слово"):
    d1, d2, d3 = st.columns([1, 1, 1])
    word_from = d1.text_input("Какое слово искать")
    word_to = d2.text_input("На что заменить")
    scope = d3.selectbox("Где применять", ["Глобально", "Текущий канал"])
    if st.button("Сохранить замену"):
        if word_from.strip() and word_to.strip():
            st.session_state.dictionary_rules.append({"from": word_from.strip(), "to": word_to.strip(), "scope": scope})
            st.success(f"Правило сохранено: {word_from} → {word_to}")
        else:
            st.error("Заполни оба поля.")
    if st.session_state.dictionary_rules:
        st.dataframe(st.session_state.dictionary_rules, use_container_width=True)

with st.expander("📦 Скачать / публикация"):
    platforms = st.multiselect("Куда готовить результат", ["YouTube", "TikTok", "Instagram", "Facebook", "Telegram", "X", "Скачать на компьютер"], default=["Скачать на компьютер"])
    package = {
        "platforms": platforms,
        "created_at": datetime.utcnow().isoformat(),
        "text": st.session_state.final_text,
        "mode": mode,
    }
    st.download_button("Скачать пакет JSON", data=json.dumps(package, ensure_ascii=False, indent=2).encode("utf-8"), file_name="murat-ai-package.json")

st.caption("Murat AI preview: слева вход, справа результат. Реальный MP4/голосовое клонирование/туркменская TTS-модель запускаются на VPS/GPU.")
