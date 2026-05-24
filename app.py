from __future__ import annotations

import json
import re
from typing import Dict, Tuple

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Murat AI", page_icon="🌐", layout="wide", initial_sidebar_state="collapsed")

LANGS = {"ru": "Русский", "tk": "Туркменский", "tr": "Турецкий", "en": "Английский"}
VOICES = [
    "Туркменский мужской — кино",
    "Туркменский женский — чистый",
    "Русский мужской — документальный",
    "Русский женский — блог",
    "Мой загруженный голос",
]
SAMPLE: Dict[Tuple[str, str], str] = {
    ("ru", "tk"): "Salam. Men bu teksti arassa türkmen diline terjime edip, professional derejede seslendirmek isleýärin.",
    ("tk", "ru"): "Здравствуйте. Я хочу перевести этот текст и сделать профессиональную озвучку.",
    ("ru", "en"): "Hello. I want to translate this text and create professional voiceover.",
    ("en", "ru"): "Здравствуйте. Я хочу перевести этот текст на русский и сделать профессиональную озвучку.",
    ("ru", "tr"): "Merhaba. Bu metni temiz Türkçeye çevirip profesyonel seslendirme yapmak istiyorum.",
    ("tr", "ru"): "Здравствуйте. Это тестовый перевод с турецкого на русский.",
}


def init() -> None:
    for k, v in {
        "video_src": None,
        "audio_src": None,
        "input_text": "Привет. Я хочу перевести это видео на чистый туркменский язык и озвучить моим голосом.",
        "final_text": "",
        "rules": [],
    }.items():
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
    t = 0
    blocks = []
    for i, p in enumerate(parts, 1):
        blocks.append(f"{i}\n00:00:{t:02d},000 --> 00:00:{t+4:02d},000\n{p}\n")
        t += 4
    return "\n".join(blocks)


def media_box(src, kind: str) -> None:
    if src is None:
        label = "Здесь появится видео" if kind == "video" else "Здесь появится аудио"
        icon = "🎬" if kind == "video" else "🎧"
        st.markdown(f"<div class='empty'>{icon}<br><br>{label}</div>", unsafe_allow_html=True)
        return
    try:
        if kind == "audio":
            st.audio(src)
        else:
            st.video(src)
    except Exception:
        st.info("Источник принят. Для ссылок лучше использовать прямую ссылку на mp4/webm или загрузить файл.")


def speak(text: str, lang: str, voice: str) -> None:
    text_json = json.dumps(text or "Нет текста")
    lang_json = json.dumps({"ru": "ru-RU", "tk": "tr-TR", "tr": "tr-TR", "en": "en-US"}.get(lang, "ru-RU"))
    components.html(f"""
    <div style='background:#111827;border:1px solid #334155;border-radius:18px;padding:14px;color:white'>
      <button id='play' style='background:#7c3aed;color:white;border:0;border-radius:12px;padding:12px 18px;font-weight:800'>▶ Прослушать озвучку</button>
      <button id='stop' style='margin-left:8px;background:#374151;color:white;border:0;border-radius:12px;padding:12px 18px;font-weight:800'>■ Стоп</button>
      <div style='margin-top:10px;color:#cbd5e1;font-size:13px'>Голос: {voice}</div>
    </div>
    <script>
      const text = {text_json}; const lang = {lang_json};
      document.getElementById('play').onclick = () => {{
        speechSynthesis.cancel();
        const u = new SpeechSynthesisUtterance(text); u.lang = lang;
        speechSynthesis.speak(u);
      }};
      document.getElementById('stop').onclick = () => speechSynthesis.cancel();
    </script>
    """, height=105)


init()

st.markdown("""
<style>
.block-container{max-width:1450px;padding-top:1.4rem}.hero{border-radius:28px;padding:24px 30px;background:linear-gradient(135deg,#17192e,#261b48 55%,#0f3550);border:1px solid rgba(255,255,255,.14);margin-bottom:18px}.hero h1{margin:0;font-size:42px}.hero p{font-size:18px;color:#dbeafe}.box{border-radius:24px;padding:18px;background:rgba(255,255,255,.045);border:1px solid rgba(255,255,255,.14);box-shadow:0 15px 35px rgba(0,0,0,.16);min-height:230px;margin-bottom:16px}.empty{border:2px dashed rgba(124,58,237,.7);border-radius:22px;padding:36px;min-height:170px;text-align:center;background:rgba(124,58,237,.08);display:flex;flex-direction:column;justify-content:center;color:#dbeafe;font-size:17px}.arrow{font-size:30px;text-align:center;padding-top:90px;color:#a78bfa}.textbig{border-radius:24px;padding:18px;background:rgba(255,255,255,.045);border:1px solid rgba(255,255,255,.14)}
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='hero'><h1>🌐 Murat AI</h1><p>Макет как на схеме: слева входные файлы и текст, справа готовые результаты.</p></div>", unsafe_allow_html=True)

src_lang, dst_lang, voice = st.columns(3)
source_lang = src_lang.selectbox("С языка", list(LANGS), format_func=lambda x: LANGS[x])
target_lang = dst_lang.selectbox("На язык", list(LANGS), format_func=lambda x: LANGS[x], index=1)
voice_name = voice.selectbox("Голос", VOICES)

left, mid, right = st.columns([1, .12, 1], gap="small")

with left:
    st.markdown("<div class='box'><h3>⬅️ Видео</h3>", unsafe_allow_html=True)
    url = st.text_input("Ссылка на видео или прямой mp4/webm")
    if st.button("Показать видео слева") and url.strip():
        st.session_state.video_src = url.strip()
    vf = st.file_uploader("Или выбери видео из папки", type=["mp4", "mov", "webm", "mkv"])
    if vf is not None:
        st.session_state.video_src = vf
    media_box(st.session_state.video_src, "video")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='box'><h3>⬅️ Аудио / мой голос</h3>", unsafe_allow_html=True)
    af = st.file_uploader("Аудиозапись голоса или аудио", type=["mp3", "wav", "m4a", "flac", "ogg"])
    if af is not None:
        st.session_state.audio_src = af
    media_box(st.session_state.audio_src, "audio")
    st.checkbox("Убрать шум", value=True); st.checkbox("Удалить эхо", value=True); st.checkbox("Выровнять громкость", value=True)
    st.markdown("</div>", unsafe_allow_html=True)

with mid:
    st.markdown("<div class='arrow'>→</div><div class='arrow'>→</div>", unsafe_allow_html=True)

with right:
    st.markdown("<div class='box'><h3>➡️ Готовое видео</h3>", unsafe_allow_html=True)
    if st.button("Создать готовое видео", type="primary"):
        st.session_state.final_text = translate(st.session_state.input_text, source_lang, target_lang)
    media_box(st.session_state.video_src, "video")
    st.caption("В полном режиме здесь будет новый MP4 с переводом и озвучкой.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='box'><h3>➡️ Готовая озвучка</h3>", unsafe_allow_html=True)
    if st.button("Озвучить текст"):
        st.session_state.final_text = st.session_state.final_text or st.session_state.input_text
    speak(st.session_state.final_text or st.session_state.input_text, target_lang, voice_name)
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<div class='textbig'><h3>📝 Текст / перевод / субтитры</h3>", unsafe_allow_html=True)
st.session_state.input_text = st.text_area("Сюда вставляешь текст, сценарий или распознанный текст из видео", value=st.session_state.input_text, height=220)
cols = st.columns(4)
if cols[0].button("Перевести", type="primary", use_container_width=True):
    st.session_state.final_text = translate(st.session_state.input_text, source_lang, target_lang)
if cols[1].button("Сделать озвучку", use_container_width=True):
    st.session_state.final_text = st.session_state.input_text
if cols[2].button("Скачать TXT", use_container_width=True):
    pass
if cols[3].button("Очистить", use_container_width=True):
    st.session_state.final_text = ""
st.text_area("Готовый текст справа / результат", value=st.session_state.final_text, height=140)
st.download_button("Скачать TXT", data=(st.session_state.final_text or "").encode("utf-8"), file_name="murat-ai-text.txt")
st.download_button("Скачать SRT", data=srt(st.session_state.final_text or st.session_state.input_text).encode("utf-8"), file_name="murat-ai-subtitles.srt")
st.markdown("</div>", unsafe_allow_html=True)

with st.expander("📚 Замена слов"):
    a, b = st.columns(2)
    fr = a.text_input("Какое слово заменить")
    to = b.text_input("На что заменить")
    if st.button("Сохранить замену") and fr and to:
        st.session_state.rules.append({"from": fr, "to": to})
        st.success(f"Сохранено: {fr} → {to}")
    if st.session_state.rules:
        st.dataframe(st.session_state.rules, use_container_width=True)

st.caption("Preview показывает дизайн и быстрый browser voice. Реальное скачивание всех ссылок, клонирование голоса и финальный MP4 требуют VPS/GPU backend.")
