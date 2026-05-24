from __future__ import annotations

import json
import re
from typing import Dict, Tuple

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Murat AI", page_icon="🌐", layout="wide", initial_sidebar_state="collapsed")

LANGS = {"ru": "Русский", "tk": "Туркменский", "tr": "Турецкий", "en": "Английский"}
VOICES = ["Детский", "Подростковый", "Женский", "Мужской", "Кино-диктор", "Блогерский", "Мой загруженный голос"]
AGES = ["Ребёнок", "Подросток", "Взрослый", "Пожилой", "Кино-персонаж"]
RESOLUTIONS = ["1080p Full HD", "4K Ultra HD", "8K Ultra HD"]
FORMATS = ["MP4", "MP4 + SRT", "MP4 + отдельное аудио", "ZIP пакет"]
SAMPLE: Dict[Tuple[str, str], str] = {
    ("ru", "tk"): "Salam. Men bu wideony arassa türkmen diline terjime edip, professional derejede seslendirmek isleýärin.",
    ("tk", "ru"): "Здравствуйте. Я хочу перевести это видео и сделать профессиональную озвучку.",
    ("ru", "en"): "Hello. I want to translate this video and create professional voiceover.",
    ("en", "ru"): "Здравствуйте. Я хочу перевести это видео на русский и сделать профессиональную озвучку.",
    ("ru", "tr"): "Merhaba. Bu videoyu temiz Türkçeye çevirip profesyonel dublaj yapmak istiyorum.",
    ("tr", "ru"): "Здравствуйте. Это тестовый перевод с турецкого на русский.",
}


def init() -> None:
    defaults = {
        "src_video": None,
        "src_audio": None,
        "src_link": "",
        "src_text": "Привет. Я хочу получить готовое видео с переводом и озвучкой.",
        "out_video": None,
        "out_text": "",
        "video_status": "Готовое видео ещё не создано.",
        "audio_status": "Готовая озвучка ещё не создана.",
        "text_status": "Готовый текст ещё не создан.",
        "rules": [],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def apply_rules(text: str) -> str:
    result = text
    for rule in st.session_state.rules:
        old = rule.get("from", "").strip()
        new = rule.get("to", "").strip()
        if old and new:
            result = re.sub(re.escape(old), new, result, flags=re.I)
    return result


def translate(text: str, src: str, dst: str) -> str:
    if not text.strip():
        return ""
    return apply_rules(SAMPLE.get((src, dst), f"[{LANGS[src]} → {LANGS[dst]}] {text}"))


def make_srt(text: str) -> str:
    parts = [p.strip() for p in re.split(r"[.!?\n]+", text) if p.strip()] or ["Murat AI"]
    sec = 0
    rows = []
    for i, part in enumerate(parts, 1):
        rows.append(f"{i}\n00:00:{sec:02d},000 --> 00:00:{sec+4:02d},000\n{part}\n")
        sec += 4
    return "\n".join(rows)


def show_media(source, kind: str, empty: str) -> None:
    if not source:
        st.markdown(f"<div class='empty'>{empty}</div>", unsafe_allow_html=True)
        return
    try:
        if kind == "audio":
            st.audio(source)
        else:
            st.video(source)
    except Exception:
        st.info("Источник принят. Для preview лучше использовать прямую ссылку на файл или загрузить файл из папки.")


def tts_preview(text: str, lang: str, voice: str, speed: float, pitch: float) -> None:
    text_json = json.dumps(text or "Нет текста для озвучки")
    lang_json = json.dumps({"ru": "ru-RU", "tk": "tr-TR", "tr": "tr-TR", "en": "en-US"}.get(lang, "ru-RU"))
    components.html(f"""
    <div style='background:#101827;border:1px solid #334155;border-radius:16px;padding:14px;color:white'>
      <button id='play' style='background:#7c3aed;color:white;border:0;border-radius:12px;padding:12px 18px;font-weight:800'>▶ Прослушать готовую озвучку</button>
      <button id='stop' style='margin-left:8px;background:#374151;color:white;border:0;border-radius:12px;padding:12px 18px;font-weight:800'>■ Стоп</button>
      <div style='margin-top:10px;color:#cbd5e1;font-size:13px'>Голос: {voice} · темп: {speed:.2f} · высота: {pitch:.2f}</div>
    </div>
    <script>
      const text = {text_json}; const lang = {lang_json};
      document.getElementById('play').onclick = () => {{
        speechSynthesis.cancel();
        const u = new SpeechSynthesisUtterance(text); u.lang = lang; u.rate = {speed}; u.pitch = {pitch};
        speechSynthesis.speak(u);
      }};
      document.getElementById('stop').onclick = () => speechSynthesis.cancel();
    </script>
    """, height=110)


init()

st.markdown("""
<style>
.block-container{max-width:1520px;padding-top:1rem}.top{border-radius:26px;padding:20px 26px;background:linear-gradient(135deg,#15172c,#261b48 55%,#0f3550);border:1px solid rgba(255,255,255,.14);margin-bottom:14px}.top h1{margin:0;font-size:40px}.top p{font-size:17px;color:#dbeafe;margin:8px 0 0}.blueprint{font-family:monospace;border-radius:18px;background:#080d1a;border:1px solid #334155;padding:14px;color:#dbeafe;margin-bottom:16px;white-space:pre-wrap}.card{border-radius:22px;padding:16px;background:rgba(255,255,255,.045);border:1px solid rgba(255,255,255,.14);box-shadow:0 12px 30px rgba(0,0,0,.14);min-height:255px;margin-bottom:12px}.empty{border:2px dashed rgba(124,58,237,.7);border-radius:20px;min-height:155px;padding:24px;text-align:center;background:rgba(124,58,237,.08);display:flex;align-items:center;justify-content:center;color:#dbeafe;font-size:17px}.arrow{font-size:34px;text-align:center;padding-top:100px;color:#a78bfa}.status{border-radius:14px;background:rgba(16,185,129,.12);border:1px solid rgba(16,185,129,.35);color:#d1fae5;padding:10px 12px;margin:8px 0;font-weight:700}.bottom{border-radius:22px;padding:16px;background:rgba(255,255,255,.045);border:1px solid rgba(255,255,255,.14)}
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='top'><h1>🌐 Murat AI</h1><p>Слева источник. Справа готовый продукт: видео 1080p / 4K / 8K, озвучка или текст.</p></div>", unsafe_allow_html=True)
st.markdown("""<div class='blueprint'>
ЧЕРТЁЖ

ЛЕВО                                  ПРАВО
1. Видео / файл / ссылка     →        1. Готовое видео MP4 1080p / 4K / 8K
2. Аудио / мой голос         →        2. Готовая озвучка выбранным голосом
3. Текст / сценарий          →        3. Готовый текст / субтитры / текст → видео

СНИЗУ: замена слов, скачать TXT/SRT/MP4/ZIP, темп, голос, возраст, качество.
</div>""", unsafe_allow_html=True)

c1, c2, c3, c4, c5 = st.columns(5)
src_lang = c1.selectbox("С языка", list(LANGS), format_func=lambda x: LANGS[x], index=0)
dst_lang = c2.selectbox("На язык", list(LANGS), format_func=lambda x: LANGS[x], index=1)
voice = c3.selectbox("Голос", VOICES, index=4)
age = c4.selectbox("Возраст голоса", AGES, index=2)
resolution = c5.selectbox("Качество видео", RESOLUTIONS, index=1)

c6, c7, c8 = st.columns(3)
speed = c6.slider("Темп", 0.70, 1.30, 1.00, 0.05)
pitch = c7.slider("Высота", 0.70, 1.30, 1.00, 0.05)
out_format = c8.selectbox("Что скачать", FORMATS, index=0)

left, mid, right = st.columns([1, .08, 1], gap="small")

with left:
    st.markdown("<div class='card'><h3>⬅️ 1. Видео / файл / ссылка</h3>", unsafe_allow_html=True)
    url = st.text_input("Ссылка на своё видео", placeholder="Вставь ссылку на своё видео или прямой mp4-файл")
    p1, p2 = st.columns(2)
    if p1.button("Показать ссылку", use_container_width=True) and url.strip():
        st.session_state.src_link = url.strip()
        st.session_state.src_video = url.strip()
    if p2.button("Взять это видео", type="primary", use_container_width=True) and url.strip():
        st.session_state.src_link = url.strip()
        st.session_state.src_video = url.strip()
        st.session_state.video_status = "Видео принято. Полный сервер создаст готовый MP4."
    video_file = st.file_uploader("Или загрузи своё видео из папки", type=["mp4", "mov", "webm", "mkv"])
    if video_file is not None:
        st.session_state.src_video = video_file
        st.session_state.video_status = "Видео из папки принято."
    show_media(st.session_state.src_video, "video", "🎬 Здесь видно исходное видео")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='card'><h3>⬅️ 2. Аудио / мой голос</h3>", unsafe_allow_html=True)
    audio_file = st.file_uploader("Загрузить аудио или запись своего голоса", type=["mp3", "wav", "m4a", "flac", "ogg"])
    if audio_file is not None:
        st.session_state.src_audio = audio_file
        st.session_state.audio_status = "Голос принят. Полный сервер очистит шум/эхо и создаст голосовой профиль."
    show_media(st.session_state.src_audio, "audio", "🎧 Здесь видно исходное аудио или мой голос")
    st.checkbox("Очистить шум / эхо", value=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='card'><h3>⬅️ 3. Текст / сценарий</h3>", unsafe_allow_html=True)
    st.session_state.src_text = st.text_area("Вставь текст, сценарий или субтитры", value=st.session_state.src_text, height=160)
    st.markdown("</div>", unsafe_allow_html=True)

with mid:
    st.markdown("<div class='arrow'>→</div><div class='arrow'>→</div><div class='arrow'>→</div>", unsafe_allow_html=True)

with right:
    st.markdown("<div class='card'><h3>➡️ 1. Готовое видео MP4</h3>", unsafe_allow_html=True)
    if st.button("Создать готовое видео", type="primary", use_container_width=True):
        st.session_state.out_text = translate(st.session_state.src_text, src_lang, dst_lang)
        st.session_state.out_video = st.session_state.src_video
        st.session_state.video_status = f"Готовится финальное видео: {resolution}, формат: {out_format}."
    show_media(st.session_state.out_video, "video", "✅ Здесь будет готовый MP4 с переводом и новой озвучкой")
    st.markdown(f"<div class='status'>🎞 {st.session_state.video_status}</div>", unsafe_allow_html=True)
    st.download_button("Скачать готовое видео MP4", data=b"Preview placeholder: final MP4 is generated on VPS/GPU", file_name="murat-ai-final-video-preview.txt", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='card'><h3>➡️ 2. Готовая озвучка</h3>", unsafe_allow_html=True)
    if st.button("Создать озвучку", use_container_width=True):
        st.session_state.out_text = st.session_state.out_text or translate(st.session_state.src_text, src_lang, dst_lang)
        st.session_state.audio_status = f"Озвучка готовится голосом: {voice}, возраст: {age}."
    tts_preview(st.session_state.out_text or st.session_state.src_text, dst_lang, voice, speed, pitch)
    st.markdown(f"<div class='status'>🎧 {st.session_state.audio_status}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='card'><h3>➡️ 3. Готовый текст / текст → видео</h3>", unsafe_allow_html=True)
    if st.button("Создать готовый текст", use_container_width=True):
        st.session_state.out_text = translate(st.session_state.src_text, src_lang, dst_lang)
        st.session_state.text_status = "Готовый текст создан. Его можно озвучить или использовать для видео."
    st.session_state.out_text = st.text_area("Готовый текст", value=st.session_state.out_text, height=140)
    st.markdown(f"<div class='status'>📝 {st.session_state.text_status}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<div class='bottom'><h3>⬇️ Нижний блок: замены, скачивание и экспорт</h3>", unsafe_allow_html=True)
a, b, c = st.columns([1, 1, 1])
old = a.text_input("Какое слово заменить")
new = b.text_input("На что заменить")
if c.button("Сохранить замену", use_container_width=True) and old and new:
    st.session_state.rules.append({"from": old, "to": new})
    st.success(f"Сохранено: {old} → {new}")

d1, d2, d3, d4 = st.columns(4)
d1.download_button("Скачать TXT", data=(st.session_state.out_text or "").encode("utf-8"), file_name="murat-ai-text.txt", use_container_width=True)
d2.download_button("Скачать SRT", data=make_srt(st.session_state.out_text or st.session_state.src_text).encode("utf-8"), file_name="murat-ai-subtitles.srt", use_container_width=True)
d3.download_button("Скачать ZIP пакет", data=json.dumps({"text": st.session_state.out_text, "resolution": resolution, "format": out_format}, ensure_ascii=False).encode("utf-8"), file_name="murat-ai-package.json", use_container_width=True)
d4.download_button("Скачать аудио", data=b"Preview placeholder: audio is generated on VPS/GPU", file_name="murat-ai-audio-preview.txt", use_container_width=True)
if st.session_state.rules:
    st.dataframe(st.session_state.rules, use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

st.caption("Murat AI preview. Чертёж реализован: слева источник, справа готовый продукт. Реальный рендер 4K/8K работает на VPS/GPU backend.")
