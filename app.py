from __future__ import annotations

import json
import re
from datetime import datetime

import streamlit as st
import streamlit.components.v1 as components

BUILD = "streamlit-preview / no-crash-studio / 2026-05-24"
TURKMEN_TTS_BACKEND = "facebook/mms-tts-tuk-script_latin"

st.set_page_config(page_title="Murat AI", page_icon="🌐", layout="wide", initial_sidebar_state="collapsed")

LANGS = {"ru": "Русский", "tk": "Туркменский", "tr": "Турецкий", "en": "Английский"}
FORMATS = {
    "9:16 Shorts / Reels / TikTok": {"ratio": "9/16", "label": "9:16", "max_width": 390},
    "16:9 YouTube": {"ratio": "16/9", "label": "16:9", "max_width": 760},
    "1:1 Square": {"ratio": "1/1", "label": "1:1", "max_width": 520},
    "Original": {"ratio": "16/9", "label": "Original", "max_width": 760},
}
EMOTIONS = ["Автоматически по оригиналу", "Нейтрально", "Радостно", "Грустно", "Серьёзно", "Злой тон", "Спокойно", "Энергично", "Кино-драма", "Шёпот", "Волнение", "Удивление", "Страх", "Добрый тон", "Рекламный тон"]
VOICES = ["Мой загруженный голос", "Туркменский мужской — чистый", "Туркменский женский — чистый", "Туркменский диктор", "Мальчик 6–8 лет — мягкий", "Мальчик 9–12 лет — энергичный", "Девочка 6–8 лет — нежная", "Девочка 9–12 лет — радостная", "Мужской кино-диктор", "Женский блогерский"]


def init_state():
    defaults = {
        "source_text": "Привет. Я хочу сделать профессиональное короткое видео с переводом и озвучкой на туркменском.",
        "result_text": "",
        "rules": [],
        "video_file": None,
        "video_url": "",
        "voice_file": None,
        "ready": False,
        "analysis": {"emotion": "Нейтрально", "confidence": 65, "speed": 1.0, "energy": 0.65, "volume": 1.0, "pauses": "средние"},
        "actors": [{"role":"Актёр 1","voice":"Туркменский мужской — чистый"},{"role":"Актёр 2","voice":"Туркменский женский — чистый"}],
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)


def analyze(text: str):
    t = text.lower()
    if any(w in t for w in ["рад", "счаст", "ура", "отлично"]): return {"emotion":"Радостно","confidence":84,"speed":1.12,"energy":0.86,"volume":1.05,"pauses":"короткие"}
    if any(w in t for w in ["боль", "плохо", "груст", "плак"]): return {"emotion":"Грустно","confidence":82,"speed":0.86,"energy":0.42,"volume":0.78,"pauses":"длинные"}
    if any(w in t for w in ["сука", "бляд", "злой", "бесит"]): return {"emotion":"Злой тон","confidence":88,"speed":1.06,"energy":0.9,"volume":1.15,"pauses":"резкие"}
    if any(w in t for w in ["важно", "официально", "суд", "заявление"]): return {"emotion":"Серьёзно","confidence":78,"speed":0.94,"energy":0.62,"volume":0.95,"pauses":"чёткие"}
    return {"emotion":"Нейтрально","confidence":65,"speed":1.0,"energy":0.65,"volume":1.0,"pauses":"средние"}


def apply_rules(text: str):
    out = text
    for r in st.session_state.rules:
        if r.get("from") and r.get("to"):
            out = re.sub(re.escape(r["from"]), r["to"], out, flags=re.I)
    return out


def translate(text: str, src: str, dst: str):
    if src == "ru" and dst == "tk": out = "Salam. Men bu wideony professional derejede terjime edip, şol bir duýgy bilen seslendirmek isleýärin."
    elif src == "tk" and dst == "ru": out = "Здравствуйте. Я хочу профессионально перевести это видео и озвучить его с той же эмоцией."
    elif src == "ru" and dst == "en": out = "Hello. I want to professionally translate this video and dub it with the same emotion."
    elif src == "en" and dst == "ru": out = "Здравствуйте. Я хочу профессионально перевести это видео и озвучить его с той же эмоцией."
    elif src == "ru" and dst == "tr": out = "Merhaba. Bu videoyu profesyonel şekilde çevirip aynı duygu ile seslendirmek istiyorum."
    else: out = f"[{LANGS[src]} → {LANGS[dst]}] {text}"
    return apply_rules(out)


def srt(text):
    parts = [p.strip() for p in re.split(r"[.!?\n]+", text) if p.strip()] or ["Murat AI"]
    rows=[]; sec=0
    for i,p in enumerate(parts,1):
        rows.append(f"{i}\n00:00:{sec:02d},000 --> 00:00:{sec+4:02d},000\n{p}\n")
        sec += 4
    return "\n".join(rows)


def vtt(text): return "WEBVTT\n\n" + srt(text).replace(",000", ".000")


def video_box(fmt, result=False):
    label = "Здесь будет готовое видео" if result else "Здесь будет исходное видео"
    if st.session_state.video_file and (not result or st.session_state.ready): st.video(st.session_state.video_file)
    elif st.session_state.video_url and (not result or st.session_state.ready): st.video(st.session_state.video_url)
    else:
        st.markdown(f"<div class='screen' style='aspect-ratio:{fmt['ratio']};max-width:{fmt['max_width']}px'><div>{label}<br><span>{fmt['label']}</span></div></div>", unsafe_allow_html=True)


def speak(text, lang, voice, emotion, speed, pitch, volume, key):
    browser_lang = {"ru":"ru-RU","tk":"tr-TR","tr":"tr-TR","en":"en-US"}.get(lang,"ru-RU")
    if "Мальчик" in voice or "Девочка" in voice: pitch *= 1.18
    if "муж" in voice.lower() or "диктор" in voice.lower(): pitch *= .92
    if emotion in ["Грустно","Серьёзно","Кино-драма"]: speed *= .9
    if emotion in ["Радостно","Энергично","Рекламный тон"]: speed *= 1.08; pitch *= 1.05
    sample = json.dumps(text or "Пример озвучки выбранным голосом.")
    components.html(f"""
    <button id='p{key}' style='background:#7c3aed;color:white;border:0;border-radius:12px;padding:10px 16px;font-weight:800'>▶ Прослушать</button>
    <button id='s{key}' style='background:#263244;color:white;border:1px solid #475569;border-radius:12px;padding:10px 16px;margin-left:8px;font-weight:800'>■ Стоп</button>
    <div style='color:#94a3b8;font-size:12px;margin-top:8px'>{voice} · {emotion} · темп {speed:.2f} · высота {pitch:.2f}</div>
    <script>document.getElementById('p{key}').onclick=()=>{{speechSynthesis.cancel();let u=new SpeechSynthesisUtterance({sample});u.lang='{browser_lang}';u.rate={speed};u.pitch={pitch};u.volume={volume};speechSynthesis.speak(u)}};document.getElementById('s{key}').onclick=()=>speechSynthesis.cancel();</script>
    """, height=90)


def project_json():
    return json.dumps({"build":BUILD,"tts_backend_turkmen":TURKMEN_TTS_BACKEND,"analysis":st.session_state.analysis,"actors":st.session_state.actors,"rules":st.session_state.rules,"created_at":datetime.utcnow().isoformat()}, ensure_ascii=False, indent=2).encode()

init_state()

st.markdown(f"""
<style>
#MainMenu, footer {{visibility:hidden}} .block-container{{max-width:1540px;padding-top:1rem;padding-bottom:5rem}}
.build{{background:#052e2b;color:#99f6e4;border:1px solid #0f766e;border-radius:14px;padding:10px 14px;font-weight:900;margin-bottom:12px}}
.hero{{border-radius:30px;padding:24px 30px;background:linear-gradient(135deg,#12172a,#24124d 60%,#073042);border:1px solid rgba(255,255,255,.12);margin-bottom:16px}}
.hero h1{{font-size:42px;margin:0;color:#fff}} .hero p{{color:#dbeafe;font-size:17px;margin:8px 0 0}}
.card{{border-radius:24px;background:rgba(255,255,255,.045);border:1px solid rgba(255,255,255,.12);padding:18px;margin-bottom:16px;box-shadow:0 18px 46px rgba(0,0,0,.18)}} .card h2{{margin:0 0 14px;font-size:25px;color:#fff}}
.screen{{width:100%;margin:0 auto 14px;border-radius:28px;background:linear-gradient(180deg,#111827,#1e1b4b);border:9px solid #111827;overflow:hidden;display:flex;align-items:center;justify-content:center;box-shadow:0 20px 60px rgba(0,0,0,.35);text-align:center;color:#dbeafe;font-size:18px;font-weight:900}} .screen span{{color:#a78bfa}}
.pill{{display:inline-block;border-radius:999px;padding:6px 10px;margin:0 6px 6px 0;background:#1e293b;color:#cbd5e1;border:1px solid #334155;font-size:12px;font-weight:800}}
.stButton>button,.stDownloadButton>button{{border-radius:12px!important;font-weight:800!important}}
</style>
<div class='build'>BUILD: {BUILD}</div>
<div class='hero'><h1>🌐 Murat AI</h1><p>Профессиональная студия: видео → перевод → озвучка → готовый MP4. Слева вход, справа результат.</p></div>
""", unsafe_allow_html=True)

st.markdown("<div class='card'><h2>⚙️ Настройки проекта</h2>", unsafe_allow_html=True)
r1=st.columns(6)
fmt_name=r1[0].selectbox("Формат видео", list(FORMATS.keys()))
quality=r1[1].selectbox("Качество", ["1080p","4K","8K"], index=1)
src=r1[2].selectbox("С языка", list(LANGS.keys()), format_func=lambda c: LANGS[c])
dst=r1[3].selectbox("На язык", list(LANGS.keys()), index=1, format_func=lambda c: LANGS[c])
voice=r1[4].selectbox("Голос", VOICES)
emotion_mode=r1[5].selectbox("Эмоция", EMOTIONS)
r2=st.columns(6)
speed=r2[0].slider("Темп", .6, 1.6, 1.0, .05)
pitch=r2[1].slider("Высота", .6, 1.6, 1.0, .05)
volume=r2[2].slider("Громкость", .1, 1.0, 1.0, .05)
r2[3].checkbox("Подогнать тайминг", True); r2[4].checkbox("Очистить шум", True); r2[5].checkbox("Сохранить качество", True)
st.markdown("</div>", unsafe_allow_html=True)
fmt=FORMATS[fmt_name]
active_emotion=st.session_state.analysis["emotion"] if emotion_mode == "Автоматически по оригиналу" else emotion_mode

left,right=st.columns(2,gap="large")
with left:
    st.markdown("<div class='card'><h2>📥 Исходное видео</h2>", unsafe_allow_html=True)
    video_box(fmt, False)
    st.session_state.video_url=st.text_input("Вставить ссылку на видео", st.session_state.video_url, placeholder="YouTube / Shorts / прямая MP4-ссылка")
    c1,c2=st.columns(2)
    if c1.button("Показать видео", type="primary", use_container_width=True): st.session_state.video_file=None; st.session_state.ready=False; st.rerun()
    c2.button("Скачать видео по ссылке", disabled=True, use_container_width=True, help="Реальное скачивание ссылок выполняется на VPS/backend.")
    up=st.file_uploader("Загрузить видео из папки", type=["mp4","mov","webm","mkv","m4v"])
    if up is not None: st.session_state.video_file=up; st.session_state.video_url=""; st.session_state.ready=False; st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
with right:
    st.markdown("<div class='card'><h2>📤 Готовое видео</h2>", unsafe_allow_html=True)
    if st.button("Создать готовый продукт", type="primary", use_container_width=True): st.session_state.analysis=analyze(st.session_state.source_text); st.session_state.result_text=translate(st.session_state.source_text,src,dst); st.session_state.ready=True; st.rerun()
    video_box(fmt, True)
    st.markdown(f"<span class='pill'>{fmt['label']}</span><span class='pill'>{quality}</span><span class='pill'>{LANGS[dst]}</span><span class='pill'>{voice}</span><span class='pill'>{active_emotion}</span>", unsafe_allow_html=True)
    d1,d2=st.columns(2)
    d1.download_button("Скачать MP4", b"MP4 preview placeholder", "murat-ai-final.mp4", disabled=not st.session_state.ready, use_container_width=True)
    d2.download_button("Скачать MP4 + SRT", srt(st.session_state.result_text).encode(), "murat-ai-final-srt.txt", disabled=not st.session_state.ready, use_container_width=True)
    d1.download_button("Скачать аудио", b"WAV preview placeholder", "voiceover.wav", disabled=not st.session_state.ready, use_container_width=True)
    d2.download_button("Скачать ZIP/JSON", project_json(), "murat-ai-package.json", disabled=not st.session_state.ready, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

left,right=st.columns(2,gap="large")
with left:
    st.markdown("<div class='card'><h2>🎤 Аудио / мой голос</h2>", unsafe_allow_html=True)
    vf=st.file_uploader("Загрузить аудио голоса", type=["wav","mp3","m4a","flac","ogg"], key="voiceup")
    if vf is not None: st.session_state.voice_file=vf; st.audio(vf)
    elif st.session_state.voice_file: st.audio(st.session_state.voice_file)
    cols=st.columns(4); cols[0].checkbox("Очистить шум", True); cols[1].checkbox("Удалить эхо", True); cols[2].checkbox("Выровнять громкость", True); cols[3].checkbox("Чистый голос", True)
    st.button("Создать голосовой профиль", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)
with right:
    st.markdown("<div class='card'><h2>🔊 Готовая озвучка</h2>", unsafe_allow_html=True)
    if st.button("Создать озвучку", type="primary", use_container_width=True): st.session_state.analysis=analyze(st.session_state.source_text); st.session_state.result_text=st.session_state.result_text or translate(st.session_state.source_text,src,dst)
    speak(st.session_state.result_text or st.session_state.source_text, dst, voice, active_emotion, speed, pitch, volume, "main")
    st.caption(f"Туркменский TTS backend: {TURKMEN_TTS_BACKEND}. Эмоция передаётся через speed/pitch/energy/pause/volume.")
    st.download_button("Скачать WAV", b"WAV preview placeholder", "voiceover.wav", use_container_width=True)
    st.download_button("Скачать MP3", b"MP3 preview placeholder", "voiceover.mp3", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

left,right=st.columns(2,gap="large")
with left:
    st.markdown("<div class='card'><h2>📝 Текст / сценарий / субтитры</h2>", unsafe_allow_html=True)
    st.session_state.source_text=st.text_area("Исходный текст", st.session_state.source_text, height=220, label_visibility="collapsed")
    b1,b2,b3=st.columns(3)
    if b1.button("Перевести", type="primary", use_container_width=True): st.session_state.analysis=analyze(st.session_state.source_text); st.session_state.result_text=translate(st.session_state.source_text,src,dst); st.rerun()
    if b2.button("Озвучить", use_container_width=True): st.session_state.analysis=analyze(st.session_state.source_text); st.session_state.result_text=st.session_state.result_text or translate(st.session_state.source_text,src,dst); st.rerun()
    if b3.button("Текст → видео", use_container_width=True): st.session_state.analysis=analyze(st.session_state.source_text); st.session_state.result_text=translate(st.session_state.source_text,src,dst); st.session_state.ready=True; st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
with right:
    st.markdown("<div class='card'><h2>✅ Готовый перевод / субтитры</h2>", unsafe_allow_html=True)
    st.session_state.result_text=st.text_area("Готовый текст", st.session_state.result_text, height=220, label_visibility="collapsed")
    t1,t2,t3=st.columns(3)
    t1.download_button("Скачать TXT", st.session_state.result_text.encode(), "murat-ai.txt", use_container_width=True)
    t2.download_button("Скачать SRT", srt(st.session_state.result_text).encode(), "murat-ai.srt", use_container_width=True)
    t3.download_button("Скачать VTT", vtt(st.session_state.result_text).encode(), "murat-ai.vtt", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<div class='card'><h2>🧠 Анализ оригинала</h2>", unsafe_allow_html=True)
a=st.session_state.analysis
st.markdown(f"<span class='pill'>Эмоция: {a['emotion']}</span><span class='pill'>Уверенность: {a['confidence']}%</span><span class='pill'>Темп: {a['speed']}</span><span class='pill'>Энергия: {a['energy']}</span><span class='pill'>Громкость: {a['volume']}</span><span class='pill'>Паузы: {a['pauses']}</span>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<div class='card'><h2>🎭 Роли и голоса</h2>", unsafe_allow_html=True)
count=st.number_input("Сколько голосов / актёров в видео", 1, 12, len(st.session_state.actors))
while len(st.session_state.actors)<count: st.session_state.actors.append({"role":f"Актёр {len(st.session_state.actors)+1}","voice":"Туркменский мужской — чистый"})
st.session_state.actors=st.session_state.actors[:count]
for i,a in enumerate(st.session_state.actors):
    cols=st.columns([1.2,1.8,1.3,1.2])
    a["role"]=cols[0].text_input("Роль", a["role"], key=f"role{i}")
    a["voice"]=cols[1].selectbox("Голос", VOICES, index=VOICES.index(a["voice"]) if a["voice"] in VOICES else 0, key=f"actorvoice{i}")
    rep=cols[2].selectbox("Замена", ["Не заменять","Мой загруженный голос","Загрузить отдельный"], key=f"rep{i}")
    with cols[3]: speak(f"Это пример голоса для роли {a['role']}", dst, a["voice"], active_emotion, speed, pitch, volume, f"actor{i}")
    if rep=="Загрузить отдельный": st.file_uploader(f"Голос для {a['role']}", type=["wav","mp3","m4a","flac","ogg"], key=f"actorfile{i}")
st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<div class='card'><h2>🎙️ Каталог голосов</h2>", unsafe_allow_html=True)
for i,v in enumerate(VOICES):
    c1,c2=st.columns([2,1])
    c1.markdown(f"<b>{v}</b><br><span style='color:#94a3b8'>Можно прослушать перед выбором.</span>", unsafe_allow_html=True)
    with c2: speak("Это пример выбранного голоса.", dst, v, active_emotion, speed, pitch, volume, f"cat{i}")
st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<div class='card'><h2>📚 Замена слов</h2>", unsafe_allow_html=True)
r1,r2,r3,r4=st.columns([1.4,1.4,1.2,1])
old=r1.text_input("Старое слово")
new=r2.text_input("Новое слово")
scope=r3.selectbox("Область", ["Глобально","Только проект","Только канал"])
if r4.button("Сохранить", type="primary", use_container_width=True) and old and new:
    st.session_state.rules.append({"from":old,"to":new,"scope":scope}); st.session_state.result_text=apply_rules(st.session_state.result_text); st.rerun()
if st.session_state.rules: st.dataframe(st.session_state.rules, use_container_width=True, hide_index=True)
st.download_button("Скачать настройки проекта JSON", project_json(), "murat-ai-project.json", use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)
st.caption(f"Настоящий MP4 4K/8K, клонирование голоса и модель {TURKMEN_TTS_BACKEND} должны работать на VPS/GPU backend. Preview показывает интерфейс и рабочую логику.")
