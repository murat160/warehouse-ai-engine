from __future__ import annotations

import json
import re
from typing import Dict, Tuple

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Murat AI", page_icon="🌐", layout="wide", initial_sidebar_state="collapsed")

LANGS = {"ru": "Русский", "tk": "Туркменский", "tr": "Турецкий", "en": "Английский"}
VOICES = ["Детский голос", "Подростковый голос", "Женский голос", "Мужской голос", "Кино-диктор", "Блогерский голос", "Мой загруженный голос"]
QUALITY = ["Быстрый preview", "Чистая студия", "Кино-уровень", "Блог / естественно", "Документальный стиль"]
RESOLUTION = ["1080p Full HD", "2K", "4K Ultra HD", "8K Ultra HD"]
OUTPUT_FORMAT = ["MP4 видео", "MP4 + SRT", "MP4 + отдельная аудиодорожка", "ZIP пакет для публикации"]
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
        "input_video": None,
        "input_audio": None,
        "input_link": "",
        "input_text": "Привет. Я хочу получить готовое видео с переводом и озвучкой.",
        "result_video": None,
        "result_audio_text": "",
        "result_text": "",
        "render_status": "Готовый продукт ещё не создан.",
        "rules": [],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def apply_rules(text: str) -> str:
    out = text
    for r in st.session_state.rules:
        a = r.get("from", "").strip()
        b = r.get("to", "").strip()
        if a and b:
            out = re.sub(re.escape(a), b, out, flags=re.I)
    return out


def translate(text: str, src: str, dst: str) -> str:
    if not text.strip():
        return ""
    return apply_rules(SAMPLE.get((src, dst), f"[{LANGS[src]} → {LANGS[dst]}] {text}"))


def srt(text: str) -> str:
    parts = [p.strip() for p in re.split(r"[.!?\n]+", text) if p.strip()] or ["Murat AI"]
    sec = 0
    rows = []
    for i, part in enumerate(parts, 1):
        rows.append(f"{i}\n00:00:{sec:02d},000 --> 00:00:{sec+4:02d},000\n{part}\n")
        sec += 4
    return "\n".join(rows)


def media(src, kind: str, empty_text: str) -> None:
    if src is None or src == "":
        st.markdown(f"<div class='empty'>{empty_text}</div>", unsafe_allow_html=True)
        return
    try:
        if kind == "audio":
            st.audio(src)
        else:
            st.video(src)
    except Exception:
        st.info("Источник принят. Если ссылка не отображается, загрузи файл или используй прямую ссылку mp4/webm.")


def browser_tts(text: str, lang: str, voice: str, speed: float, pitch: float) -> None:
    text_json = json.dumps(text or "Нет текста для озвучки")
    lang_json = json.dumps({"ru": "ru-RU", "tk": "tr-TR", "tr": "tr-TR", "en": "en-US"}.get(lang, "ru-RU"))
    components.html(f"""
    <div style='background:#101827;border:1px solid #334155;border-radius:16px;padding:14px;color:white'>
      <button id='play' style='background:#7c3aed;color:white;border:0;border-radius:12px;padding:12px 18px;font-weight:800'>▶ Прослушать озвучку</button>
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
    """, height=105)


init()

st.markdown("""
<style>
.block-container{max-width:1500px;padding-top:1.2rem}.hero{border-radius:28px;padding:24px 30px;background:linear-gradient(135deg,#15172c,#261b48 55%,#0f3550);border:1px solid rgba(255,255,255,.14);margin-bottom:18px}.hero h1{margin:0;font-size:42px}.hero p{font-size:18px;color:#dbeafe}.rowbox{border-radius:24px;padding:18px;background:rgba(255,255,255,.045);border:1px solid rgba(255,255,255,.14);box-shadow:0 14px 34px rgba(0,0,0,.16);min-height:260px;margin-bottom:16px}.rowbox h3{margin-top:0}.empty{border:2px dashed rgba(124,58,237,.7);border-radius:22px;padding:42px 20px;min-height:170px;text-align:center;background:rgba(124,58,237,.08);display:flex;align-items:center;justify-content:center;color:#dbeafe;font-size:17px}.arrow{font-size:34px;text-align:center;padding-top:110px;color:#a78bfa}.control{border-radius:24px;padding:18px;background:rgba(255,255,255,.055);border:1px solid rgba(255,255,255,.14);margin-bottom:16px}.textblock{border-radius:24px;padding:18px;background:rgba(255,255,255,.045);border:1px solid rgba(255,255,255,.14)}.resultcard{border-radius:18px;padding:14px;background:rgba(16,185,129,.10);border:1px solid rgba(16,185,129,.35);margin:10px 0;color:#d1fae5;font-weight:700}
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='hero'><h1>🌐 Murat AI</h1><p>Слева вставляешь видео, аудио, ссылку или текст — справа получаешь готовый продукт: видео с новой озвучкой в Full HD, 4K или 8K.</p></div>", unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
source_lang = c1.selectbox("С языка", list(LANGS), format_func=lambda x: LANGS[x], index=0)
target_lang = c2.selectbox("На язык", list(LANGS), format_func=lambda x: LANGS[x], index=1)
voice = c3.selectbox("Тип голоса", VOICES)
quality = c4.selectbox("Качество озвучки", QUALITY, index=2)

control = st.columns([1, 1, 1, 1])
speed = control[0].slider("Темп", 0.70, 1.30, 1.00, 0.05)
pitch = control[1].slider("Высота голоса", 0.70, 1.30, 1.00, 0.05)
resolution = control[2].selectbox("Качество готового видео", RESOLUTION, index=2)
out_format = control[3].selectbox("Что скачать", OUTPUT_FORMAT, index=0)

flags = st.columns([1, 1, 1, 1])
flags[0].checkbox("Подогнать текст под тайминг", value=True)
flags[1].checkbox("Очистить шум / эхо", value=True)
flags[2].checkbox("Сохранить исходное качество", value=True)
flags[3].checkbox("Сделать готовый MP4", value=True)

left, mid, right = st.columns([1, .10, 1], gap="small")

with left:
    st.markdown("<div class='rowbox'><h3>⬅️ 1. Вставить видео</h3>", unsafe_allow_html=True)
    video_file = st.file_uploader("Загрузить своё видео из папки", type=["mp4", "mov", "webm", "mkv"], key="video_file")
    if video_file is not None:
        st.session_state.input_video = video_file
    media(st.session_state.input_video, "video", "🎬 Видео появится здесь")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='rowbox'><h3>⬅️ 2. Вставить аудио / свой голос</h3>", unsafe_allow_html=True)
    audio_file = st.file_uploader("Загрузить аудио или запись своего голоса", type=["mp3", "wav", "m4a", "flac", "ogg"], key="audio_file")
    if audio_file is not None:
        st.session_state.input_audio = audio_file
    media(st.session_state.input_audio, "audio", "🎧 Аудио или голос появится здесь")
    st.caption("В полном режиме голос очищается, убирается шум/эхо и создаётся голосовой профиль.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='rowbox'><h3>⬅️ 3. Вставить ссылку на видео</h3>", unsafe_allow_html=True)
    link = st.text_input("Ссылка на видео", placeholder="YouTube / TikTok / Instagram / прямая ссылка mp4")
    if st.button("Показать видео по ссылке", use_container_width=True):
        st.session_state.input_link = link.strip()
        st.session_state.input_video = link.strip()
    media(st.session_state.input_link, "video", "🔗 Видео по ссылке появится здесь")
    st.caption("В полном режиме сервер скачает видео по ссылке, обработает его и отдаст готовый MP4.")
    st.markdown("</div>", unsafe_allow_html=True)

with mid:
    st.markdown("<div class='arrow'>→</div><div class='arrow'>→</div><div class='arrow'>→</div>", unsafe_allow_html=True)

with right:
    st.markdown("<div class='rowbox'><h3>➡️ 1. Готовое видео с переводом</h3>", unsafe_allow_html=True)
    if st.button("Создать готовое видео", type="primary", use_container_width=True):
        st.session_state.result_text = translate(st.session_state.input_text, source_lang, target_lang)
        st.session_state.result_video = st.session_state.input_video
        st.session_state.render_status = f"Готовится финальный MP4: {resolution}, {quality}, формат: {out_format}."
    media(st.session_state.result_video, "video", "✅ Здесь будет готовое видео с новой озвучкой")
    st.markdown(f"<div class='resultcard'>🎞 {st.session_state.render_status}</div>", unsafe_allow_html=True)
    st.caption("Preview показывает место результата. На VPS здесь будет финальный MP4 в выбранном качестве: 1080p / 2K / 4K / 8K.")
    st.download_button("Скачать готовое видео MP4", data=b"Preview: final MP4 will be generated on VPS/GPU", file_name="murat-ai-final-video-preview.txt", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='rowbox'><h3>➡️ 2. Готовая озвучка</h3>", unsafe_allow_html=True)
    if st.button("Создать озвучку", use_container_width=True):
        st.session_state.result_text = st.session_state.result_text or st.session_state.input_text
    browser_tts(st.session_state.result_text or st.session_state.input_text, target_lang, voice, speed, pitch)
    st.caption("Если выбран «Мой загруженный голос», полный режим озвучивает текст именно этим очищенным голосом.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='rowbox'><h3>➡️ 3. Текст → видео/озвучка</h3>", unsafe_allow_html=True)
    text_for_result = st.text_area("Вставить текст справа", value=st.session_state.input_text, height=105)
    if st.button("Из текста сделать озвучку/видео", use_container_width=True):
        st.session_state.input_text = text_for_result
        st.session_state.result_text = translate(text_for_result, source_lang, target_lang)
        st.session_state.render_status = f"Из текста будет создана озвучка/видео: {resolution}, голос: {voice}."
    st.text_area("Готовый текст", value=st.session_state.result_text, height=105)
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<div class='textblock'><h3>📝 Большой текстовый блок</h3>", unsafe_allow_html=True)
st.session_state.input_text = st.text_area("Сценарий, текст для озвучки, субтитры или правка распознанного текста", value=st.session_state.input_text, height=240)
b1, b2, b3, b4 = st.columns(4)
if b1.button("Перевести", type="primary", use_container_width=True):
    st.session_state.result_text = translate(st.session_state.input_text, source_lang, target_lang)
if b2.button("Озвучить", use_container_width=True):
    st.session_state.result_text = st.session_state.input_text
st.download_button("Скачать TXT", data=(st.session_state.result_text or "").encode("utf-8"), file_name="murat-ai-text.txt", use_container_width=True)
st.download_button("Скачать SRT", data=srt(st.session_state.result_text or st.session_state.input_text).encode("utf-8"), file_name="murat-ai-subtitles.srt", use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

with st.expander("📚 Замена слов"):
    r1, r2 = st.columns(2)
    old = r1.text_input("Какое слово заменить")
    new = r2.text_input("На что заменить")
    if st.button("Сохранить замену") and old and new:
        st.session_state.rules.append({"from": old, "to": new})
        st.success(f"Сохранено: {old} → {new}")
    if st.session_state.rules:
        st.dataframe(st.session_state.rules, use_container_width=True)

st.caption("Murat AI preview. Все подписи на русском. Полное скачивание ссылок, AI-клонирование голоса, рендер 4K/8K и финальный MP4 требуют VPS/GPU backend.")
