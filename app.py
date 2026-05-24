from __future__ import annotations

import base64
import json
import re
from datetime import datetime
from typing import Dict

import streamlit as st
import streamlit.components.v1 as components

BUILD = "streamlit-preview / force-full-studio / 2026-05-24"
TURKMEN_TTS_BACKEND = "facebook/mms-tts-tuk-script_latin"

st.set_page_config(page_title="Murat AI", page_icon="🌐", layout="wide", initial_sidebar_state="collapsed")

LANGS = {"ru": "Русский", "tk": "Туркменский", "tr": "Турецкий", "en": "Английский"}
FORMATS = {
    "9:16 Shorts / Reels / TikTok": {"ratio": "9/16", "max": 380, "label": "9:16"},
    "16:9 YouTube": {"ratio": "16/9", "max": 760, "label": "16:9"},
    "1:1 Square": {"ratio": "1/1", "max": 520, "label": "1:1"},
    "Original": {"ratio": "16/9", "max": 760, "label": "Original"},
}
QUALITIES = ["1080p", "4K", "8K"]
EMOTIONS = [
    "Автоматически по оригиналу", "Нейтрально", "Радостно", "Грустно", "Серьёзно", "Злой тон",
    "Спокойно", "Энергично", "Кино-драма", "Шёпот", "Волнение", "Удивление", "Страх", "Добрый тон", "Рекламный тон",
]
VOICE_CATALOG = [
    {"id": "boy_6_8_soft", "name": "Мальчик 6–8 лет — мягкий", "lang": "Русский", "age": "ребёнок", "style": "мягкий", "emotions": ["Нейтрально", "Добрый тон", "Грустно"]},
    {"id": "boy_9_12_energy", "name": "Мальчик 9–12 лет — энергичный", "lang": "Русский", "age": "ребёнок", "style": "энергичный", "emotions": ["Радостно", "Энергично", "Удивление"]},
    {"id": "girl_6_8_soft", "name": "Девочка 6–8 лет — нежная", "lang": "Русский", "age": "ребёнок", "style": "нежный", "emotions": ["Добрый тон", "Радостно", "Грустно"]},
    {"id": "girl_9_12_happy", "name": "Девочка 9–12 лет — радостная", "lang": "Русский", "age": "ребёнок", "style": "радостный", "emotions": ["Радостно", "Энергично", "Волнение"]},
    {"id": "tm_male_clean", "name": "Туркменский мужской — чистый", "lang": "Туркменский", "age": "взрослый", "style": "чистый", "emotions": ["Нейтрально", "Серьёзно", "Спокойно"]},
    {"id": "tm_female_clean", "name": "Туркменский женский — чистый", "lang": "Туркменский", "age": "взрослый", "style": "чистый", "emotions": ["Нейтрально", "Добрый тон", "Радостно"]},
    {"id": "tm_narrator", "name": "Туркменский диктор", "lang": "Туркменский", "age": "взрослый", "style": "диктор", "emotions": ["Серьёзно", "Кино-драма", "Спокойно"]},
    {"id": "male_cinema", "name": "Мужской кино-диктор", "lang": "Русский", "age": "взрослый", "style": "кино", "emotions": ["Кино-драма", "Серьёзно", "Злой тон"]},
    {"id": "female_blogger", "name": "Женский блогерский", "lang": "Русский", "age": "взрослый", "style": "блогерский", "emotions": ["Радостно", "Энергично", "Рекламный тон"]},
    {"id": "custom_voice", "name": "Мой загруженный голос", "lang": "Любой", "age": "пользовательский", "style": "мой голос", "emotions": EMOTIONS[1:]},
]
SAMPLES = {"ru": "Привет, это пример моего голоса для озвучки видео.", "tk": "Salam, bu wideony seslendirmek üçin ses nusgasydyr.", "tr": "Merhaba, bu video seslendirme için örnek sestir.", "en": "Hello, this is a sample voice for video dubbing."}
TRANSLATIONS = {
    ("ru", "tk"): "Salam. Men bu wideony professional derejede terjime edip, şol bir duýgy bilen seslendirmek isleýärin.",
    ("tk", "ru"): "Здравствуйте. Я хочу профессионально перевести это видео и озвучить его с той же эмоцией.",
    ("ru", "en"): "Hello. I want to professionally translate this video and dub it with the same emotion.",
    ("en", "ru"): "Здравствуйте. Я хочу профессионально перевести это видео и озвучить его с той же эмоцией.",
    ("ru", "tr"): "Merhaba. Bu videoyu profesyonel şekilde çevirip aynı duygu ile seslendirmek istiyorum.",
    ("tr", "ru"): "Здравствуйте. Я хочу профессионально перевести это видео и озвучить его с той же эмоцией.",
}


def init_state() -> None:
    defaults = {
        "video_url": "", "video_bytes": None, "video_name": "", "result_ready": False,
        "voice_bytes": None, "voice_name": "", "voice_ready": False,
        "source_text": "Привет. Я хочу сделать профессиональное короткое видео с переводом и озвучкой на туркменском.",
        "result_text": "", "selected_voice": "Мой загруженный голос", "rules": [],
        "actors": [
            {"role": "Актёр 1", "voice": "Туркменский мужской — чистый", "emotion_mode": "Авто по реплике", "replace": "Не заменять"},
            {"role": "Актёр 2", "voice": "Туркменский женский — чистый", "emotion_mode": "Авто по оригиналу", "replace": "Не заменять"},
        ],
        "analysis": {"emotion": "Нейтрально", "confidence": 0.65, "speed": 1.0, "energy": 0.65, "volume": 1.0, "pauses": "средние"},
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def apply_rules(text: str) -> str:
    out = text
    for rule in st.session_state.rules:
        old = rule.get("from", "").strip(); new = rule.get("to", "").strip()
        if old and new:
            out = re.sub(re.escape(old), new, out, flags=re.I)
    return out


def analyze_emotion(text: str) -> Dict[str, object]:
    t = text.lower()
    if any(w in t for w in ["рад", "счаст", "ура", "класс", "отлично"]):
        return {"emotion": "Радостно", "confidence": 0.84, "speed": 1.12, "energy": 0.86, "volume": 1.05, "pauses": "короткие"}
    if any(w in t for w in ["боль", "плохо", "груст", "плак", "одиноко"]):
        return {"emotion": "Грустно", "confidence": 0.82, "speed": 0.86, "energy": 0.42, "volume": 0.78, "pauses": "длинные"}
    if any(w in t for w in ["ненавиж", "злой", "сука", "бляд", "бесит"]):
        return {"emotion": "Злой тон", "confidence": 0.88, "speed": 1.06, "energy": 0.9, "volume": 1.15, "pauses": "резкие"}
    if any(w in t for w in ["важно", "официально", "документ", "суд", "заявление"]):
        return {"emotion": "Серьёзно", "confidence": 0.78, "speed": 0.94, "energy": 0.62, "volume": 0.95, "pauses": "чёткие"}
    if any(w in t for w in ["купить", "скидка", "акция", "продажа"]):
        return {"emotion": "Рекламный тон", "confidence": 0.8, "speed": 1.15, "energy": 0.88, "volume": 1.08, "pauses": "короткие"}
    return {"emotion": "Нейтрально", "confidence": 0.65, "speed": 1.0, "energy": 0.65, "volume": 1.0, "pauses": "средние"}


def translate_text(text: str, src: str, dst: str) -> str:
    return apply_rules(TRANSLATIONS.get((src, dst), f"[{LANGS[src]} → {LANGS[dst]}] {text}"))


def srt(text: str) -> str:
    chunks = [x.strip() for x in re.split(r"[.!?\n]+", text) if x.strip()] or ["Murat AI"]
    out, sec = [], 0
    for i, c in enumerate(chunks, 1):
        out.append(f"{i}\n00:00:{sec:02d},000 --> 00:00:{sec+4:02d},000\n{c}\n")
        sec += 4
    return "\n".join(out)


def vtt(text: str) -> str:
    return "WEBVTT\n\n" + srt(text).replace(",000", ".000")


def media_html(data, name: str, url: str, fmt: dict, label: str) -> str:
    ratio, maxw = fmt["ratio"], fmt["max"]
    if data:
        ext = (name.rsplit(".", 1)[-1] if "." in name else "mp4").lower()
        mime = {"webm": "video/webm", "mov": "video/quicktime", "mkv": "video/x-matroska"}.get(ext, "video/mp4")
        b64 = base64.b64encode(data).decode("ascii")
        inner = f"<video controls playsinline><source src='data:{mime};base64,{b64}' type='{mime}'></video>"
    elif url:
        if "youtube.com/shorts/" in url:
            vid = url.split("/shorts/")[-1].split("?")[0]; inner = f"<iframe src='https://www.youtube.com/embed/{vid}' allowfullscreen></iframe>"
        elif "youtube.com/watch" in url and "v=" in url:
            vid = url.split("v=")[-1].split("&")[0]; inner = f"<iframe src='https://www.youtube.com/embed/{vid}' allowfullscreen></iframe>"
        elif "youtu.be/" in url:
            vid = url.split("youtu.be/")[-1].split("?")[0]; inner = f"<iframe src='https://www.youtube.com/embed/{vid}' allowfullscreen></iframe>"
        elif re.search(r"\.(mp4|webm|mov|m4v)(\?|$)", url, re.I):
            inner = f"<video controls playsinline src='{url}'></video>"
        else:
            inner = "<div class='empty'>Ссылка принята.<br>Для просмотра нужна YouTube или прямая mp4-ссылка.</div>"
    else:
        inner = f"<div class='empty'>{label}</div>"
    return f"<div class='screen' style='aspect-ratio:{ratio};max-width:{maxw}px'>{inner}</div>"


def speak(text: str, lang: str, voice: str, emotion: str, tempo: float, pitch: float, volume: float, key: str):
    browser_lang = {"ru": "ru-RU", "tk": "tr-TR", "tr": "tr-TR", "en": "en-US"}.get(lang, "ru-RU")
    txt = json.dumps(text or SAMPLES.get(lang, SAMPLES["ru"]))
    rate = tempo; p = pitch
    if "Мальчик" in voice or "Девочка" in voice: p *= 1.2
    if "муж" in voice.lower() or "диктор" in voice.lower(): p *= 0.92
    if emotion in ["Грустно", "Серьёзно", "Кино-драма"]: rate *= 0.9
    if emotion in ["Радостно", "Энергично", "Рекламный тон"]: rate *= 1.08; p *= 1.05
    components.html(f"""
    <button id='p{key}' style='background:#7c3aed;color:white;border:0;border-radius:12px;padding:10px 16px;font-weight:800'>▶ Прослушать</button>
    <button id='s{key}' style='background:#263244;color:white;border:1px solid #475569;border-radius:12px;padding:10px 16px;margin-left:8px;font-weight:800'>■ Стоп</button>
    <div style='color:#94a3b8;font-size:12px;margin-top:8px'>{voice} · {emotion} · темп {rate:.2f} · высота {p:.2f}</div>
    <script>document.getElementById('p{key}').onclick=()=>{{speechSynthesis.cancel();let u=new SpeechSynthesisUtterance({txt});u.lang='{browser_lang}';u.rate={rate};u.pitch={p};u.volume={volume};speechSynthesis.speak(u)}};document.getElementById('s{key}').onclick=()=>speechSynthesis.cancel();</script>
    """, height=92)


def project_json() -> bytes:
    payload = {"build": BUILD, "tts_backend_turkmen": TURKMEN_TTS_BACKEND, "emotion_mode": "auto_from_original", "analysis": st.session_state.analysis, "selected_voice": st.session_state.selected_voice, "actors": st.session_state.actors, "replacements": st.session_state.rules, "created_at": datetime.utcnow().isoformat()}
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")

init_state()

st.markdown(f"""
<style>
.block-container{{max-width:1540px;padding-top:1rem;padding-bottom:5rem}}
#MainMenu, footer{{visibility:hidden}}
.hero{{border-radius:30px;padding:24px 30px;background:linear-gradient(135deg,#12172a,#24124d 60%,#073042);border:1px solid rgba(255,255,255,.12);margin-bottom:16px}}
.hero h1{{font-size:42px;margin:0;color:#fff}} .hero p{{color:#dbeafe;font-size:17px;margin:8px 0 0}}
.build{{background:#052e2b;color:#99f6e4;border:1px solid #0f766e;border-radius:14px;padding:10px 14px;font-weight:800;margin-bottom:12px}}
.card{{border-radius:24px;background:rgba(255,255,255,.045);border:1px solid rgba(255,255,255,.12);padding:18px;margin-bottom:16px;box-shadow:0 18px 46px rgba(0,0,0,.18)}}
.card h2{{margin:0 0 14px;font-size:25px;color:#fff}} .sub{{color:#94a3b8;font-size:13px}}
.screen{{width:100%;margin:0 auto 14px;border-radius:28px;background:linear-gradient(180deg,#111827,#1e1b4b);border:9px solid #111827;overflow:hidden;display:flex;align-items:center;justify-content:center;box-shadow:0 20px 60px rgba(0,0,0,.35)}}
.screen video,.screen iframe{{width:100%;height:100%;border:0;object-fit:cover}} .empty{{text-align:center;color:#dbeafe;font-size:18px;font-weight:900;line-height:1.5;padding:22px}}
.pill{{display:inline-block;border-radius:999px;padding:6px 10px;margin:0 6px 6px 0;background:#1e293b;color:#cbd5e1;border:1px solid #334155;font-size:12px;font-weight:800}}
.voice-card{{border:1px solid #334155;background:#0f172a;border-radius:18px;padding:14px;margin-bottom:10px}}
.voice-title{{font-weight:900;color:#fff;font-size:16px;margin-bottom:6px}}
.stButton>button,.stDownloadButton>button{{border-radius:12px!important;font-weight:800!important}}
</style>
<div class='build'>BUILD: {BUILD}</div>
<div class='hero'><h1>🌐 Murat AI</h1><p>Профессиональная студия: видео → перевод → озвучка → готовый MP4. Слева вход, справа результат.</p></div>
""", unsafe_allow_html=True)

st.markdown("<div class='card'><h2>⚙️ Настройки проекта</h2>", unsafe_allow_html=True)
r1 = st.columns(6)
fmt_name = r1[0].selectbox("Формат видео", list(FORMATS.keys()))
quality = r1[1].selectbox("Качество", QUALITIES, index=1)
src_lang = r1[2].selectbox("С языка", list(LANGS), format_func=lambda x: LANGS[x])
dst_lang = r1[3].selectbox("На язык", list(LANGS), index=1, format_func=lambda x: LANGS[x])
voice_names = [v["name"] for v in VOICE_CATALOG]
st.session_state.selected_voice = r1[4].selectbox("Голосовой профиль", voice_names, index=voice_names.index(st.session_state.selected_voice) if st.session_state.selected_voice in voice_names else 0)
emotion_mode = r1[5].selectbox("Эмоция", EMOTIONS)
r2 = st.columns(6)
tempo = r2[0].slider("Темп", 0.6, 1.6, 1.0, 0.05)
pitch = r2[1].slider("Высота", 0.6, 1.6, 1.0, 0.05)
volume = r2[2].slider("Громкость", 0.1, 1.0, 1.0, 0.05)
r2[3].checkbox("Подогнать под тайминг", True); r2[4].checkbox("Очистить шум / эхо", True); r2[5].checkbox("Сохранить качество", True)
st.markdown("</div>", unsafe_allow_html=True)
fmt = FORMATS[fmt_name]
active_emotion = st.session_state.analysis["emotion"] if emotion_mode == "Автоматически по оригиналу" else emotion_mode

left, right = st.columns(2, gap="large")
with left:
    st.markdown("<div class='card'><h2>📥 Исходное видео</h2>", unsafe_allow_html=True)
    st.markdown(media_html(st.session_state.video_bytes, st.session_state.video_name, st.session_state.video_url, fmt, "Здесь будет исходное видео"), unsafe_allow_html=True)
    url = st.text_input("Вставить ссылку на видео", value=st.session_state.video_url, placeholder="YouTube / Shorts / прямая mp4-ссылка")
    c1, c2 = st.columns(2)
    if c1.button("Показать видео", type="primary", use_container_width=True):
        st.session_state.video_url = url.strip(); st.session_state.video_bytes = None; st.session_state.result_ready = False; st.rerun()
    c2.button("Скачать видео по ссылке", use_container_width=True, disabled=True, help="Реальное скачивание ссылок выполняется на VPS/backend. В preview ссылка показывается в окне.")
    up = st.file_uploader("Загрузить видео из папки", type=["mp4", "mov", "webm", "mkv", "m4v"], key="video_upload")
    if up is not None:
        st.session_state.video_bytes = up.read(); st.session_state.video_name = up.name; st.session_state.video_url = ""; st.session_state.result_ready = False; st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
with right:
    st.markdown("<div class='card'><h2>📤 Готовое видео</h2>", unsafe_allow_html=True)
    if st.button("Создать готовое видео", type="primary", use_container_width=True):
        st.session_state.analysis = analyze_emotion(st.session_state.source_text); st.session_state.result_text = translate_text(st.session_state.source_text, src_lang, dst_lang); st.session_state.result_ready = True; st.rerun()
    st.markdown(media_html(st.session_state.video_bytes if st.session_state.result_ready else None, st.session_state.video_name, st.session_state.video_url if st.session_state.result_ready else "", fmt, f"Здесь будет готовое видео<br>{fmt['label']} / {quality}"), unsafe_allow_html=True)
    st.markdown(f"<span class='pill'>{fmt['label']}</span><span class='pill'>{quality}</span><span class='pill'>{LANGS[dst_lang]}</span><span class='pill'>{st.session_state.selected_voice}</span><span class='pill'>{active_emotion}</span>", unsafe_allow_html=True)
    d1, d2 = st.columns(2)
    d1.download_button("Скачать MP4", data=st.session_state.video_bytes or b"MP4 preview placeholder", file_name="murat-ai-final.mp4", disabled=not st.session_state.result_ready, use_container_width=True)
    d2.download_button("Скачать MP4 + SRT", data=(st.session_state.video_bytes or b"MP4") + b"\n" + srt(st.session_state.result_text).encode(), file_name="murat-ai-final-srt.mp4", disabled=not st.session_state.result_ready, use_container_width=True)
    d1.download_button("Скачать аудио", data=b"WAV preview placeholder", file_name="murat-ai-audio.wav", disabled=not st.session_state.result_ready, use_container_width=True)
    d2.download_button("Скачать ZIP пакет", data=project_json(), file_name="murat-ai-package.json", disabled=not st.session_state.result_ready, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

left, right = st.columns(2, gap="large")
with left:
    st.markdown("<div class='card'><h2>🎤 Аудио / мой голос</h2>", unsafe_allow_html=True)
    voice_file = st.file_uploader("Загрузить аудио голоса", type=["wav", "mp3", "m4a", "flac", "ogg"], key="voice_file")
    if voice_file is not None:
        st.session_state.voice_bytes = voice_file.read(); st.session_state.voice_name = voice_file.name; st.audio(st.session_state.voice_bytes)
    elif st.session_state.voice_bytes: st.audio(st.session_state.voice_bytes)
    cc = st.columns(4); cc[0].checkbox("Очистить шум", True); cc[1].checkbox("Удалить эхо", True); cc[2].checkbox("Выровнять громкость", True); cc[3].checkbox("Сделать голос чистым", True)
    if st.button("Создать голосовой профиль", use_container_width=True):
        st.session_state.voice_ready = bool(st.session_state.voice_bytes); st.success("Голосовой профиль создан для preview.") if st.session_state.voice_ready else st.error("Сначала загрузи запись голоса.")
    st.markdown("</div>", unsafe_allow_html=True)
with right:
    st.markdown("<div class='card'><h2>🔊 Готовая озвучка</h2>", unsafe_allow_html=True)
    if st.button("Создать озвучку", type="primary", use_container_width=True):
        st.session_state.analysis = analyze_emotion(st.session_state.source_text); st.session_state.result_text = st.session_state.result_text or translate_text(st.session_state.source_text, src_lang, dst_lang)
    speak(st.session_state.result_text or st.session_state.source_text, dst_lang, st.session_state.selected_voice, active_emotion, tempo, pitch, volume, "main")
    st.caption(f"Туркменский TTS backend: {TURKMEN_TTS_BACKEND}. Эмоция передаётся через speed/pitch/energy/pause/volume.")
    a1, a2 = st.columns(2); a1.download_button("Скачать WAV", data=b"WAV preview placeholder", file_name="voiceover.wav", use_container_width=True); a2.download_button("Скачать MP3", data=b"MP3 preview placeholder", file_name="voiceover.mp3", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

left, right = st.columns(2, gap="large")
with left:
    st.markdown("<div class='card'><h2>📝 Текст / сценарий / субтитры</h2>", unsafe_allow_html=True)
    st.session_state.source_text = st.text_area("", value=st.session_state.source_text, height=220, label_visibility="collapsed")
    b1, b2, b3 = st.columns(3)
    if b1.button("Перевести", type="primary", use_container_width=True): st.session_state.analysis = analyze_emotion(st.session_state.source_text); st.session_state.result_text = translate_text(st.session_state.source_text, src_lang, dst_lang); st.rerun()
    if b2.button("Озвучить", use_container_width=True): st.session_state.analysis = analyze_emotion(st.session_state.source_text); st.session_state.result_text = st.session_state.result_text or translate_text(st.session_state.source_text, src_lang, dst_lang); st.rerun()
    if b3.button("Текст → видео", use_container_width=True): st.session_state.analysis = analyze_emotion(st.session_state.source_text); st.session_state.result_text = translate_text(st.session_state.source_text, src_lang, dst_lang); st.session_state.result_ready = True; st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
with right:
    st.markdown("<div class='card'><h2>✅ Готовый перевод / субтитры</h2>", unsafe_allow_html=True)
    st.session_state.result_text = st.text_area("", value=st.session_state.result_text, height=220, label_visibility="collapsed")
    t1, t2, t3 = st.columns(3); t1.download_button("Скачать TXT", data=st.session_state.result_text.encode(), file_name="murat-ai.txt", use_container_width=True); t2.download_button("Скачать SRT", data=srt(st.session_state.result_text).encode(), file_name="murat-ai.srt", use_container_width=True); t3.download_button("Скачать VTT", data=vtt(st.session_state.result_text).encode(), file_name="murat-ai.vtt", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<div class='card'><h2>🧠 Анализ оригинала</h2>", unsafe_allow_html=True)
a = st.session_state.analysis
st.markdown(f"<span class='pill'>Эмоция: {a['emotion']}</span><span class='pill'>Уверенность: {int(float(a['confidence'])*100)}%</span><span class='pill'>Темп: {a['speed']}</span><span class='pill'>Энергия: {a['energy']}</span><span class='pill'>Громкость: {a['volume']}</span><span class='pill'>Паузы: {a['pauses']}</span><span class='pill'>Источник: текст / аудио / видео</span>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<div class='card'><h2>🎭 Роли и голоса</h2>", unsafe_allow_html=True)
count = st.number_input("Сколько голосов / актёров в видео", 1, 12, len(st.session_state.actors))
while len(st.session_state.actors) < count: st.session_state.actors.append({"role": f"Актёр {len(st.session_state.actors)+1}", "voice": "Туркменский мужской — чистый", "emotion_mode": "Авто по реплике", "replace": "Не заменять"})
st.session_state.actors = st.session_state.actors[:count]
for i, actor in enumerate(st.session_state.actors):
    c = st.columns([1.2, 1.6, 1.2, 1.2, 1.0])
    actor["role"] = c[0].text_input("Роль", actor["role"], key=f"r{i}")
    actor["voice"] = c[1].selectbox("Голос", voice_names, index=voice_names.index(actor["voice"]) if actor["voice"] in voice_names else 0, key=f"v{i}")
    actor["emotion_mode"] = c[2].selectbox("Эмоция", ["Авто по реплике", "Авто по оригиналу", "Вручную"], key=f"e{i}")
    actor["replace"] = c[3].selectbox("Заменить голос", ["Не заменять", "Мой загруженный голос", "Загрузить отдельный"], key=f"z{i}")
    with c[4]: speak(f"Это пример голоса для роли {actor['role']}", dst_lang, actor["voice"], active_emotion, tempo, pitch, volume, f"act{i}")
    if actor["replace"] == "Загрузить отдельный": st.file_uploader(f"Голос для роли {actor['role']}", type=["wav", "mp3", "m4a", "flac", "ogg"], key=f"fu{i}")
st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<div class='card'><h2>🎙️ Каталог голосов</h2>", unsafe_allow_html=True)
filter_lang = st.selectbox("Фильтр по языку", ["Все", "Русский", "Туркменский", "Любой"])
grid = st.columns(3); shown = 0
for v in VOICE_CATALOG:
    if filter_lang != "Все" and v["lang"] != filter_lang: continue
    with grid[shown % 3]:
        st.markdown(f"<div class='voice-card'><div class='voice-title'>{v['name']}</div><div class='sub'>Язык: {v['lang']} · возраст: {v['age']} · стиль: {v['style']}</div><div class='sub'>Эмоции: {', '.join(v['emotions'][:4])}</div></div>", unsafe_allow_html=True)
        speak(SAMPLES.get(dst_lang, SAMPLES["ru"]), dst_lang, v["name"], active_emotion, tempo, pitch, volume, f"cat{shown}")
        if st.button("Выбрать этот голос", key=f"select_voice_{v['id']}", use_container_width=True): st.session_state.selected_voice = v["name"]; st.rerun()
    shown += 1
st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<div class='card'><h2>📚 Замена слов</h2>", unsafe_allow_html=True)
r1, r2, r3, r4 = st.columns([1.4, 1.4, 1.2, 1.0])
old = r1.text_input("Какое слово заменить"); new = r2.text_input("На что заменить"); scope = r3.selectbox("Область", ["Глобально", "Только текущий проект", "Только текущий канал"])
if r4.button("Сохранить", type="primary", use_container_width=True) and old and new: st.session_state.rules.append({"from": old, "to": new, "scope": scope}); st.session_state.result_text = apply_rules(st.session_state.result_text); st.rerun()
if st.session_state.rules: st.dataframe(st.session_state.rules, use_container_width=True, hide_index=True)
st.download_button("Скачать настройки проекта JSON", data=project_json(), file_name="murat-ai-project.json", use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

st.caption(f"Настоящий MP4 4K/8K, клонирование голоса и туркменская TTS-модель {TURKMEN_TTS_BACKEND} работают на VPS/GPU backend. Preview показывает интерфейс и рабочую логику.")
