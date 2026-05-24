from __future__ import annotations

import json
import re
from datetime import datetime

import streamlit as st
import streamlit.components.v1 as components

BUILD = "studio-screen-size-fixed / 2026-05-24-22:30"
TURKMEN_TTS_BACKEND = "facebook/mms-tts-tuk-script_latin"

st.set_page_config(page_title="Murat AI", page_icon="🌐", layout="wide", initial_sidebar_state="collapsed")

LANGS = {"ru": "Русский", "tk": "Туркменский", "tr": "Турецкий", "en": "Английский"}
FORMATS = {
    "9:16 Shorts / Reels / TikTok": {"ratio": "9/16", "label": "9:16"},
    "16:9 YouTube": {"ratio": "16/9", "label": "16:9"},
    "1:1 Square": {"ratio": "1/1", "label": "1:1"},
    "Original": {"ratio": "16/9", "label": "Original"},
}
SCREENS = {
    "Телефон вертикальный": {"w": 220, "h": 390, "label": "Телефон вертикальный", "kind": "phone"},
    "Телефон горизонтальный": {"w": 420, "h": 235, "label": "Телефон горизонтальный", "kind": "phone"},
    "Планшет": {"w": 480, "h": 320, "label": "Планшет", "kind": "tablet"},
    "Ноутбук": {"w": 560, "h": 330, "label": "Ноутбук", "kind": "laptop"},
    "Монитор 19 дюймов": {"w": 620, "h": 360, "label": "Монитор 19 дюймов", "kind": "monitor"},
    "Монитор 24 дюйма": {"w": 700, "h": 405, "label": "Монитор 24 дюйма", "kind": "monitor"},
    "Телевизор": {"w": 760, "h": 430, "label": "Телевизор", "kind": "tv"},
    "Без рамки": {"w": 560, "h": 315, "label": "Без рамки", "kind": "bare"},
}
QUALITIES = ["1080p", "4K", "8K"]
EMOTIONS = ["Автоматически по оригиналу", "Нейтрально", "Радостно", "Грустно", "Серьёзно", "Злой тон", "Спокойно", "Энергично", "Кино-драма", "Шёпот", "Волнение", "Удивление", "Страх", "Добрый тон", "Рекламный тон"]
VOICES = ["Мой загруженный голос", "Туркменский мужской — чистый", "Туркменский женский — чистый", "Туркменский диктор", "Мальчик 6–8 лет — мягкий", "Мальчик 9–12 лет — энергичный", "Девочка 6–8 лет — нежная", "Девочка 9–12 лет — радостная", "Мужской кино-диктор", "Женский блогерский"]


def ss(key, value):
    if key not in st.session_state:
        st.session_state[key] = value


def init_state():
    ss("source_text", "Привет. Я хочу сделать профессиональное короткое видео с переводом и озвучкой на туркменском.")
    ss("result_text", "")
    ss("rules", [])
    ss("video_url", "")
    ss("video_loaded", False)
    ss("voice_loaded", False)
    ss("ready", False)
    ss("analysis", {"emotion": "Нейтрально", "confidence": 65, "speed": 1.0, "energy": 0.65, "volume": 1.0, "pauses": "средние"})
    ss("actors", [{"role": "Актёр 1", "voice": "Туркменский мужской — чистый"}, {"role": "Актёр 2", "voice": "Туркменский женский — чистый"}])


def analyze(text: str) -> dict:
    t = text.lower()
    if any(w in t for w in ["рад", "счаст", "ура", "отлично"]):
        return {"emotion": "Радостно", "confidence": 84, "speed": 1.12, "energy": 0.86, "volume": 1.05, "pauses": "короткие"}
    if any(w in t for w in ["боль", "плохо", "груст", "плак"]):
        return {"emotion": "Грустно", "confidence": 82, "speed": 0.86, "energy": 0.42, "volume": 0.78, "pauses": "длинные"}
    if any(w in t for w in ["сука", "бляд", "злой", "бесит"]):
        return {"emotion": "Злой тон", "confidence": 88, "speed": 1.06, "energy": 0.9, "volume": 1.15, "pauses": "резкие"}
    if any(w in t for w in ["важно", "официально", "суд", "заявление"]):
        return {"emotion": "Серьёзно", "confidence": 78, "speed": 0.94, "energy": 0.62, "volume": 0.95, "pauses": "чёткие"}
    return {"emotion": "Нейтрально", "confidence": 65, "speed": 1.0, "energy": 0.65, "volume": 1.0, "pauses": "средние"}


def apply_rules(text: str) -> str:
    out = text
    for rule in st.session_state.rules:
        old, new = rule.get("from", ""), rule.get("to", "")
        if old and new:
            out = re.sub(re.escape(old), new, out, flags=re.I)
    return out


def translate(text: str, src: str, dst: str) -> str:
    if src == "ru" and dst == "tk":
        out = "Salam. Men bu wideony professional derejede terjime edip, şol bir duýgy bilen seslendirmek isleýärin."
    elif src == "tk" and dst == "ru":
        out = "Здравствуйте. Я хочу профессионально перевести это видео и озвучить его с той же эмоцией."
    elif src == "ru" and dst == "en":
        out = "Hello. I want to professionally translate this video and dub it with the same emotion."
    elif src == "ru" and dst == "tr":
        out = "Merhaba. Bu videoyu profesyonel şekilde çevirip aynı duygu ile seslendirmek istiyorum."
    else:
        out = f"[{LANGS[src]} → {LANGS[dst]}] {text}"
    return apply_rules(out)


def srt(text: str) -> str:
    chunks = [p.strip() for p in re.split(r"[.!?\n]+", text) if p.strip()] or ["Murat AI"]
    rows, sec = [], 0
    for i, chunk in enumerate(chunks, 1):
        rows.append(f"{i}\n00:00:{sec:02d},000 --> 00:00:{sec+4:02d},000\n{chunk}\n")
        sec += 4
    return "\n".join(rows)


def project_json() -> bytes:
    return json.dumps({"build": BUILD, "tts_backend_turkmen": TURKMEN_TTS_BACKEND, "analysis": st.session_state.analysis, "actors": st.session_state.actors, "rules": st.session_state.rules, "created_at": datetime.utcnow().isoformat()}, ensure_ascii=False, indent=2).encode()


def video_box(format_name: str, screen_name: str, title: str, result: bool, uploaded_video=None):
    fmt = FORMATS[format_name]
    scr = SCREENS[screen_name]
    aspect = fmt["ratio"]
    w, h = scr["w"], scr["h"]
    css = f"--w:{w}px;--h:{h}px;--ratio:{aspect};"
    st.markdown(f"<div class='device-shell {scr['kind']}' style='{css}'><div class='screen-area'><div class='video-ratio'>", unsafe_allow_html=True)
    show_media = (not result and uploaded_video is not None) or (result and st.session_state.ready and uploaded_video is not None)
    if show_media:
        st.video(uploaded_video)
    elif st.session_state.video_url and ((not result) or st.session_state.ready):
        st.video(st.session_state.video_url)
    else:
        st.markdown(f"<div class='placeholder'>{title}<br><b>{fmt['label']}</b><br><small>{scr['label']}</small></div>", unsafe_allow_html=True)
    st.markdown("</div></div></div>", unsafe_allow_html=True)


def speak_button(text: str, lang: str, voice: str, emotion: str, speed: float, pitch: float, volume: float, key: str):
    browser_lang = {"ru": "ru-RU", "tk": "tr-TR", "tr": "tr-TR", "en": "en-US"}.get(lang, "ru-RU")
    if "Мальчик" in voice or "Девочка" in voice:
        pitch *= 1.18
    if "муж" in voice.lower() or "диктор" in voice.lower():
        pitch *= 0.92
    if emotion in ["Грустно", "Серьёзно", "Кино-драма"]:
        speed *= 0.9
    if emotion in ["Радостно", "Энергично", "Рекламный тон"]:
        speed *= 1.08
        pitch *= 1.05
    text_json = json.dumps(text or "Пример озвучки выбранным голосом.")
    components.html(f"""
    <button id='p{key}' style='background:#7c3aed;color:white;border:0;border-radius:12px;padding:10px 16px;font-weight:800'>▶ Прослушать</button>
    <button id='s{key}' style='background:#263244;color:white;border:1px solid #475569;border-radius:12px;padding:10px 16px;margin-left:8px;font-weight:800'>■ Стоп</button>
    <div style='color:#94a3b8;font-size:12px;margin-top:8px'>{voice} · {emotion} · темп {speed:.2f} · высота {pitch:.2f}</div>
    <script>document.getElementById('p{key}').onclick=()=>{{speechSynthesis.cancel();let u=new SpeechSynthesisUtterance({text_json});u.lang='{browser_lang}';u.rate={speed};u.pitch={pitch};u.volume={volume};speechSynthesis.speak(u)}};document.getElementById('s{key}').onclick=()=>speechSynthesis.cancel();</script>
    """, height=86)


init_state()

st.markdown(f"""
<style>
#MainMenu, footer {{visibility:hidden}}
.block-container {{max-width:1500px;padding-top:1rem;padding-bottom:5rem}}
.build {{background:#052e2b;color:#99f6e4;border:1px solid #0f766e;border-radius:14px;padding:10px 14px;font-weight:900;margin-bottom:12px}}
.hero {{border-radius:28px;padding:22px 28px;background:linear-gradient(135deg,#12172a,#24124d 60%,#073042);border:1px solid rgba(255,255,255,.12);margin-bottom:16px}}
.hero h1 {{font-size:38px;margin:0;color:#fff}}
.hero p {{color:#dbeafe;font-size:16px;margin:8px 0 0}}
.card {{border-radius:22px;background:rgba(255,255,255,.045);border:1px solid rgba(255,255,255,.12);padding:16px;margin-bottom:16px;box-shadow:0 18px 46px rgba(0,0,0,.18)}}
.card h2 {{margin:0 0 14px;font-size:23px;color:#fff}}
.pill {{display:inline-block;border-radius:999px;padding:6px 10px;margin:0 6px 6px 0;background:#1e293b;color:#cbd5e1;border:1px solid #334155;font-size:12px;font-weight:800}}
.device-shell {{width:100%;max-width:min(var(--w),100%);height:var(--h);max-height:430px;margin:0 auto 14px;display:flex;align-items:center;justify-content:center;position:relative}}
.screen-area {{width:100%;height:100%;display:flex;align-items:center;justify-content:center;background:#050816;overflow:hidden;box-shadow:0 18px 42px rgba(0,0,0,.35)}}
.video-ratio {{width:100%;max-width:100%;height:auto;aspect-ratio:var(--ratio);max-height:100%;display:flex;align-items:center;justify-content:center;background:linear-gradient(180deg,#111827,#1e1b4b);overflow:hidden}}
.video-ratio video,.video-ratio iframe {{width:100%!important;height:100%!important;object-fit:contain!important}}
.placeholder {{text-align:center;color:#dbeafe;font-size:17px;font-weight:900;line-height:1.55;padding:16px}}
.placeholder b {{color:#a78bfa}} .placeholder small {{color:#94a3b8}}
.phone .screen-area {{border:10px solid #111;border-radius:30px}}
.tablet .screen-area {{border:12px solid #161616;border-radius:22px}}
.laptop .screen-area {{border:9px solid #252525;border-top-width:20px;border-radius:12px}}
.laptop::after {{content:"";position:absolute;bottom:-10px;width:85%;height:12px;background:#222;border-radius:0 0 16px 16px}}
.monitor .screen-area {{border:12px solid #111;border-radius:8px}}
.monitor::after {{content:"";position:absolute;bottom:-18px;width:30%;height:18px;background:#151515;border-radius:0 0 10px 10px}}
.tv .screen-area {{border:16px solid #050505;border-radius:14px}}
.bare .screen-area {{border:1px solid #334155;border-radius:14px}}
.stButton>button,.stDownloadButton>button {{border-radius:12px!important;font-weight:800!important}}
</style>
<div class='build'>BUILD: {BUILD}</div>
<div class='hero'><h1>🌐 Murat AI</h1><p>Слева — исходник: ссылка / видео / аудио / текст. Справа — готовый продукт. Формат видео и экран просмотра выбираются отдельно.</p></div>
""", unsafe_allow_html=True)

st.markdown("<div class='card'><h2>⚙️ Настройки проекта</h2>", unsafe_allow_html=True)
r0 = st.columns(2)
format_name = r0[0].selectbox("🎬 Формат видео", list(FORMATS.keys()))
screen_name = r0[1].selectbox("🖥 Экран просмотра", list(SCREENS.keys()), index=4)
r1 = st.columns(5)
quality = r1[0].selectbox("Качество", QUALITIES, index=1)
src = r1[1].selectbox("С языка", list(LANGS.keys()), format_func=lambda x: LANGS[x])
dst = r1[2].selectbox("На язык", list(LANGS.keys()), index=1, format_func=lambda x: LANGS[x])
voice = r1[3].selectbox("Голосовой профиль", VOICES)
emotion_mode = r1[4].selectbox("Эмоция", EMOTIONS)
r2 = st.columns(6)
speed = r2[0].slider("Темп", 0.6, 1.6, 1.0, 0.05)
pitch = r2[1].slider("Высота", 0.6, 1.6, 1.0, 0.05)
volume = r2[2].slider("Громкость", 0.1, 1.0, 1.0, 0.05)
r2[3].checkbox("Подогнать под тайминг", True)
r2[4].checkbox("Очистить шум / эхо", True)
r2[5].checkbox("Сохранить качество", True)
st.markdown(f"<span class='pill'>Формат видео: {FORMATS[format_name]['label']}</span><span class='pill'>Экран: {SCREENS[screen_name]['label']}</span><span class='pill'>Качество: {quality}</span>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

active_emotion = st.session_state.analysis["emotion"] if emotion_mode == "Автоматически по оригиналу" else emotion_mode

left, right = st.columns(2, gap="large")
with left:
    st.markdown("<div class='card'><h2>📥 Исходное видео</h2>", unsafe_allow_html=True)
    uploaded_video = st.file_uploader("Загрузить видео из папки", type=["mp4", "mov", "webm", "mkv", "m4v"], key="video_upload_widget")
    if uploaded_video is not None:
        st.session_state.video_loaded = True
    video_box(format_name, screen_name, "Здесь будет исходное видео", False, uploaded_video)
    st.session_state.video_url = st.text_input("Вставить ссылку на видео", st.session_state.video_url, placeholder="YouTube / Shorts / прямая mp4-ссылка")
    c1, c2 = st.columns(2)
    if c1.button("Показать по ссылке", type="primary", use_container_width=True):
        st.session_state.ready = False
        st.rerun()
    c2.button("Скачать видео по ссылке", disabled=True, use_container_width=True, help="На Streamlit preview показан макет. Реальное скачивание ссылки выполняется на VPS/backend через yt-dlp.")
    st.markdown("</div>", unsafe_allow_html=True)

with right:
    st.markdown("<div class='card'><h2>📤 Готовое видео</h2>", unsafe_allow_html=True)
    if st.button("Создать готовое видео", type="primary", use_container_width=True):
        st.session_state.analysis = analyze(st.session_state.source_text)
        st.session_state.result_text = translate(st.session_state.source_text, src, dst)
        st.session_state.ready = True
        st.rerun()
    video_box(format_name, screen_name, "Здесь будет готовое видео", True, uploaded_video)
    st.markdown(f"<span class='pill'>{FORMATS[format_name]['label']}</span><span class='pill'>{SCREENS[screen_name]['label']}</span><span class='pill'>{LANGS[dst]}</span><span class='pill'>{voice}</span><span class='pill'>{active_emotion}</span>", unsafe_allow_html=True)
    d1, d2 = st.columns(2)
    d1.download_button("Скачать MP4", b"MP4 preview placeholder", "murat-ai-final.mp4", disabled=not st.session_state.ready, use_container_width=True)
    d2.download_button("Скачать MP4 + SRT", srt(st.session_state.result_text).encode(), "murat-ai-final-srt.txt", disabled=not st.session_state.ready, use_container_width=True)
    d1.download_button("Скачать аудио WAV", b"WAV preview placeholder", "voiceover.wav", disabled=not st.session_state.ready, use_container_width=True)
    d2.download_button("Скачать проект JSON", project_json(), "murat-ai-project.json", disabled=not st.session_state.ready, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

left, right = st.columns(2, gap="large")
with left:
    st.markdown("<div class='card'><h2>🎤 Аудио / мой голос</h2>", unsafe_allow_html=True)
    voice_upload = st.file_uploader("Загрузить аудио голоса", type=["wav", "mp3", "m4a", "flac", "ogg"], key="voice_upload_widget")
    if voice_upload is not None:
        st.session_state.voice_loaded = True
        st.audio(voice_upload)
    cols = st.columns(4)
    cols[0].checkbox("Очистить шум", True)
    cols[1].checkbox("Удалить эхо", True)
    cols[2].checkbox("Выровнять громкость", True)
    cols[3].checkbox("Сделать голос чистым", True)
    st.button("Создать голосовой профиль", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with right:
    st.markdown("<div class='card'><h2>🔊 Готовая озвучка</h2>", unsafe_allow_html=True)
    if st.button("Создать озвучку", type="primary", use_container_width=True):
        st.session_state.analysis = analyze(st.session_state.source_text)
        st.session_state.result_text = st.session_state.result_text or translate(st.session_state.source_text, src, dst)
    speak_button(st.session_state.result_text or st.session_state.source_text, dst, voice, active_emotion, speed, pitch, volume, "main")
    st.caption(f"Туркменский TTS backend: {TURKMEN_TTS_BACKEND}. В preview эмоция имитируется через темп/высоту/громкость. На VPS будет реальная TTS-обработка.")
    st.download_button("Скачать WAV", b"WAV preview placeholder", "voiceover.wav", use_container_width=True)
    st.download_button("Скачать MP3", b"MP3 preview placeholder", "voiceover.mp3", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

left, right = st.columns(2, gap="large")
with left:
    st.markdown("<div class='card'><h2>📝 Текст / сценарий / субтитры</h2>", unsafe_allow_html=True)
    st.session_state.source_text = st.text_area("Исходный текст", st.session_state.source_text, height=220, label_visibility="collapsed")
    b1, b2, b3 = st.columns(3)
    if b1.button("Перевести", type="primary", use_container_width=True):
        st.session_state.analysis = analyze(st.session_state.source_text)
        st.session_state.result_text = translate(st.session_state.source_text, src, dst)
        st.rerun()
    if b2.button("Озвучить", use_container_width=True):
        st.session_state.analysis = analyze(st.session_state.source_text)
        st.session_state.result_text = st.session_state.result_text or translate(st.session_state.source_text, src, dst)
        st.rerun()
    if b3.button("Текст → видео", use_container_width=True):
        st.session_state.analysis = analyze(st.session_state.source_text)
        st.session_state.result_text = translate(st.session_state.source_text, src, dst)
        st.session_state.ready = True
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

with right:
    st.markdown("<div class='card'><h2>✅ Готовый перевод / субтитры</h2>", unsafe_allow_html=True)
    st.session_state.result_text = st.text_area("Готовый текст", st.session_state.result_text, height=220, label_visibility="collapsed")
    t1, t2, t3 = st.columns(3)
    t1.download_button("Скачать TXT", st.session_state.result_text.encode(), "murat-ai.txt", use_container_width=True)
    t2.download_button("Скачать SRT", srt(st.session_state.result_text).encode(), "murat-ai.srt", use_container_width=True)
    t3.download_button("Скачать VTT", ("WEBVTT\n\n" + srt(st.session_state.result_text).replace(",000", ".000")).encode(), "murat-ai.vtt", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<div class='card'><h2>🧠 Анализ оригинала</h2>", unsafe_allow_html=True)
a = st.session_state.analysis
st.markdown(f"<span class='pill'>Эмоция: {a['emotion']}</span><span class='pill'>Уверенность: {a['confidence']}%</span><span class='pill'>Темп: {a['speed']}</span><span class='pill'>Энергия: {a['energy']}</span><span class='pill'>Громкость: {a['volume']}</span><span class='pill'>Паузы: {a['pauses']}</span>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<div class='card'><h2>🎭 Роли и голоса</h2>", unsafe_allow_html=True)
count = st.number_input("Сколько голосов / актёров в видео", 1, 12, len(st.session_state.actors))
while len(st.session_state.actors) < count:
    st.session_state.actors.append({"role": f"Актёр {len(st.session_state.actors)+1}", "voice": "Туркменский мужской — чистый"})
st.session_state.actors = st.session_state.actors[:count]
for i, actor in enumerate(st.session_state.actors):
    cols = st.columns([1.2, 1.8, 1.2, 1.0])
    actor["role"] = cols[0].text_input("Роль", actor["role"], key=f"role_{i}")
    actor["voice"] = cols[1].selectbox("Голос", VOICES, index=VOICES.index(actor["voice"]) if actor["voice"] in VOICES else 0, key=f"actor_voice_{i}")
    cols[2].selectbox("Замена", ["Не заменять", "Мой загруженный голос", "Загрузить отдельный"], key=f"actor_replace_{i}")
    with cols[3]:
        speak_button(f"Это пример голоса для роли {actor['role']}", dst, actor["voice"], active_emotion, speed, pitch, volume, f"actor_{i}")
st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<div class='card'><h2>📚 Замена слов</h2>", unsafe_allow_html=True)
r1, r2, r3, r4 = st.columns([1.4, 1.4, 1.2, 1.0])
old = r1.text_input("Старое слово")
new = r2.text_input("Новое слово")
scope = r3.selectbox("Область", ["Глобально", "Только проект", "Только канал"])
if r4.button("Сохранить", type="primary", use_container_width=True) and old and new:
    st.session_state.rules.append({"from": old, "to": new, "scope": scope})
    st.session_state.result_text = apply_rules(st.session_state.result_text)
    st.rerun()
if st.session_state.rules:
    st.dataframe(st.session_state.rules, use_container_width=True, hide_index=True)
st.download_button("Скачать настройки проекта JSON", project_json(), "murat-ai-project.json", use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

st.caption(f"Настоящее скачивание ссылок, MP4 4K/8K, voice cloning и модель {TURKMEN_TTS_BACKEND} должны работать на VPS/GPU backend. Streamlit preview показывает структуру интерфейса и рабочую логику.")
