from __future__ import annotations

import json
import re
from datetime import datetime

import streamlit as st
import streamlit.components.v1 as components

BUILD = "screen-preview-fixed-v2 / 2026-05-24-21:30"
TURKMEN_TTS_BACKEND = "facebook/mms-tts-tuk-script_latin"

st.set_page_config(page_title="Murat AI", page_icon="🌐", layout="wide", initial_sidebar_state="collapsed")

LANGS = {"ru": "Русский", "tk": "Туркменский", "tr": "Турецкий", "en": "Английский"}
FORMATS = {
    "9:16 Shorts / Reels / TikTok": {"ratio": "9/16", "label": "9:16"},
    "16:9 YouTube":                  {"ratio": "16/9", "label": "16:9"},
    "1:1 Square":                    {"ratio": "1/1",  "label": "1:1"},
    "Original":                      {"ratio": "16/9", "label": "Original"},
}
SCREENS = {
    "📱 Телефон вертикальный":    {"max": 300, "kind": "phone-v", "label": "Телефон верт."},
    "📱 Телефон горизонтальный":  {"max": 620, "kind": "phone-h", "label": "Телефон гориз."},
    "💻 Планшет":                 {"max": 560, "kind": "tablet",  "label": "Планшет"},
    "💻 Ноутбук":                 {"max": 760, "kind": "laptop",  "label": "Ноутбук"},
    "🖥 Монитор 19\"":            {"max": 720, "kind": "monitor", "label": "Монитор 19″"},
    "🖥 Монитор 24\"":            {"max": 880, "kind": "monitor", "label": "Монитор 24″"},
    "📺 Телевизор":               {"max": 960, "kind": "tv",      "label": "Телевизор"},
    "🟦 Без рамки":               {"max": 760, "kind": "bare",    "label": "Без рамки"},
}
QUALITIES = ["1080p", "4K", "8K"]
EMOTIONS = [
    "Автоматически по оригиналу",
    "Нейтрально",
    "Радостно",
    "Грустно",
    "Серьёзно",
    "Злой тон",
    "Спокойно",
    "Энергично",
    "Кино-драма",
    "Шёпот",
    "Волнение",
    "Удивление",
    "Страх",
    "Добрый тон",
    "Рекламный тон",
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
    {"id": "custom_voice", "name": "Мой загруженный голос", "lang": "Любой", "age": "пользовательский", "style": "мой очищенный голос", "emotions": EMOTIONS[1:]},
]
SAMPLES = {
    "ru": "Привет, это пример моего голоса для озвучки видео.",
    "tk": "Salam, bu wideony seslendirmek üçin ses nusgasydyr.",
    "tr": "Merhaba, bu video seslendirme için örnek sestir.",
    "en": "Hello, this is a sample voice for video dubbing.",
}


def init_state() -> None:
    defaults = {
        "video_file": None,
        "video_name": "",
        "video_url": "",
        "source_text": "Привет. Я хочу сделать профессиональное короткое видео с переводом и озвучкой на туркменском.",
        "result_text": "",
        "result_ready": False,
        "voice_file": None,
        "voice_name": "",
        "selected_voice": "Мой загруженный голос",
        "rules": [],
        "analysis": {"emotion": "Нейтрально", "confidence": 65, "speed": 1.0, "energy": 0.65, "volume": 1.0, "pauses": "средние"},
        "actors": [
            {"role": "Актёр 1", "voice": "Туркменский мужской — чистый", "emotion": "Авто по реплике", "replace": "Не заменять"},
            {"role": "Актёр 2", "voice": "Туркменский женский — чистый", "emotion": "Авто по оригиналу", "replace": "Не заменять"},
        ],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def analyze_emotion(text: str) -> dict:
    t = text.lower()
    if any(w in t for w in ["рад", "счаст", "ура", "класс", "отлично"]):
        return {"emotion": "Радостно", "confidence": 84, "speed": 1.12, "energy": 0.86, "volume": 1.05, "pauses": "короткие"}
    if any(w in t for w in ["боль", "плохо", "груст", "плак", "одиноко"]):
        return {"emotion": "Грустно", "confidence": 82, "speed": 0.86, "energy": 0.42, "volume": 0.78, "pauses": "длинные"}
    if any(w in t for w in ["ненавиж", "злой", "сука", "бляд", "бесит"]):
        return {"emotion": "Злой тон", "confidence": 88, "speed": 1.06, "energy": 0.9, "volume": 1.15, "pauses": "резкие"}
    if any(w in t for w in ["важно", "официально", "документ", "суд", "заявление"]):
        return {"emotion": "Серьёзно", "confidence": 78, "speed": 0.94, "energy": 0.62, "volume": 0.95, "pauses": "чёткие"}
    if any(w in t for w in ["купить", "скидка", "акция", "продажа"]):
        return {"emotion": "Рекламный тон", "confidence": 80, "speed": 1.15, "energy": 0.88, "volume": 1.08, "pauses": "короткие"}
    return {"emotion": "Нейтрально", "confidence": 65, "speed": 1.0, "energy": 0.65, "volume": 1.0, "pauses": "средние"}


def apply_rules(text: str) -> str:
    result = text
    for rule in st.session_state.rules:
        old = rule.get("from", "").strip()
        new = rule.get("to", "").strip()
        if old and new:
            result = re.sub(re.escape(old), new, result, flags=re.I)
    return result


def translate_text(text: str, src: str, dst: str) -> str:
    if not text.strip():
        return ""
    if src == "ru" and dst == "tk":
        out = "Salam. Men bu wideony professional derejede terjime edip, şol bir duýgy bilen seslendirmek isleýärin."
    elif src == "tk" and dst == "ru":
        out = "Здравствуйте. Я хочу профессионально перевести это видео и озвучить его с той же эмоцией."
    elif src == "ru" and dst == "en":
        out = "Hello. I want to professionally translate this video and dub it with the same emotion."
    elif src == "en" and dst == "ru":
        out = "Здравствуйте. Я хочу профессионально перевести это видео и озвучить его с той же эмоцией."
    elif src == "ru" and dst == "tr":
        out = "Merhaba. Bu videoyu profesyonel şekilde çevirip aynı duygu ile seslendirmek istiyorum."
    else:
        out = f"[{LANGS[src]} → {LANGS[dst]}] {text}"
    return apply_rules(out)


def srt(text: str) -> str:
    parts = [p.strip() for p in re.split(r"[.!?\n]+", text) if p.strip()] or ["Murat AI"]
    rows, sec = [], 0
    for i, part in enumerate(parts, 1):
        rows.append(f"{i}\n00:00:{sec:02d},000 --> 00:00:{sec+4:02d},000\n{part}\n")
        sec += 4
    return "\n".join(rows)


def vtt(text: str) -> str:
    return "WEBVTT\n\n" + srt(text).replace(",000", ".000")


def get_video_aspect(fmt: dict) -> str:
    return fmt["ratio"]


def get_device_frame(screen: dict):
    return screen["kind"], screen["max"]


def video_screen(fmt: dict, screen: dict, result: bool = False) -> None:
    label = "Здесь будет готовое видео" if result else "Здесь будет исходное видео"
    kind, max_w = get_device_frame(screen)
    aspect = get_video_aspect(fmt)
    st.markdown(
        f"<div class='device device-{kind}' style='max-width:{max_w}px'><div class='device-screen' style='aspect-ratio:{aspect}'>",
        unsafe_allow_html=True,
    )
    if st.session_state.video_file and (not result or st.session_state.result_ready):
        st.video(st.session_state.video_file)
    elif st.session_state.video_url and (not result or st.session_state.result_ready):
        st.video(st.session_state.video_url)
    else:
        st.markdown(
            f"<div class='device-empty'>{label}<br><span>{fmt['label']} · {screen['label']}</span></div>",
            unsafe_allow_html=True,
        )
    st.markdown("</div></div>", unsafe_allow_html=True)


def speak_button(text: str, lang: str, voice: str, emotion: str, speed: float, pitch: float, volume: float, key: str) -> None:
    browser_lang = {"ru": "ru-RU", "tk": "tr-TR", "tr": "tr-TR", "en": "en-US"}.get(lang, "ru-RU")
    final_speed = speed
    final_pitch = pitch
    if "Мальчик" in voice or "Девочка" in voice:
        final_pitch *= 1.18
    if "диктор" in voice.lower() or "муж" in voice.lower():
        final_pitch *= 0.92
    if emotion in ["Грустно", "Серьёзно", "Кино-драма"]:
        final_speed *= 0.9
    if emotion in ["Радостно", "Энергично", "Рекламный тон"]:
        final_speed *= 1.08
        final_pitch *= 1.05
    text_json = json.dumps(text or SAMPLES.get(lang, SAMPLES["ru"]))
    components.html(
        f"""
        <button id="play_{key}" style="background:#7c3aed;color:white;border:0;border-radius:12px;padding:10px 16px;font-weight:800;cursor:pointer">▶ Прослушать</button>
        <button id="stop_{key}" style="background:#263244;color:white;border:1px solid #475569;border-radius:12px;padding:10px 16px;margin-left:8px;font-weight:800;cursor:pointer">■ Стоп</button>
        <div style="color:#94a3b8;font-size:12px;margin-top:8px">{voice} · {emotion} · темп {final_speed:.2f} · высота {final_pitch:.2f}</div>
        <script>
        document.getElementById('play_{key}').onclick = () => {{
            speechSynthesis.cancel();
            const u = new SpeechSynthesisUtterance({text_json});
            u.lang = '{browser_lang}';
            u.rate = {final_speed};
            u.pitch = {final_pitch};
            u.volume = {volume};
            speechSynthesis.speak(u);
        }};
        document.getElementById('stop_{key}').onclick = () => speechSynthesis.cancel();
        </script>
        """,
        height=90,
    )


def project_json() -> bytes:
    payload = {
        "build": BUILD,
        "tts_backend_turkmen": TURKMEN_TTS_BACKEND,
        "emotion_mode": "auto_from_original",
        "emotion_profile": st.session_state.analysis,
        "selected_voice": st.session_state.selected_voice,
        "actors": st.session_state.actors,
        "replacements": st.session_state.rules,
        "created_at": datetime.utcnow().isoformat(),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


init_state()

st.markdown(
    f"""
    <style>
    #MainMenu, footer {{visibility:hidden}}
    .block-container {{max-width:1540px;padding-top:1rem;padding-bottom:5rem}}
    .build {{background:#052e2b;color:#99f6e4;border:1px solid #0f766e;border-radius:14px;padding:10px 14px;font-weight:800;margin-bottom:12px}}
    .hero {{border-radius:30px;padding:24px 30px;background:linear-gradient(135deg,#12172a,#24124d 60%,#073042);border:1px solid rgba(255,255,255,.12);margin-bottom:16px}}
    .hero h1 {{font-size:42px;margin:0;color:#fff}}
    .hero p {{color:#dbeafe;font-size:17px;margin:8px 0 0}}
    .card {{border-radius:24px;background:rgba(255,255,255,.045);border:1px solid rgba(255,255,255,.12);padding:18px;margin-bottom:16px;box-shadow:0 18px 46px rgba(0,0,0,.18)}}
    .card h2 {{margin:0 0 14px;font-size:25px;color:#fff}}
    .pill {{display:inline-block;border-radius:999px;padding:6px 10px;margin:0 6px 6px 0;background:#1e293b;color:#cbd5e1;border:1px solid #334155;font-size:12px;font-weight:800}}
    .device {{width:100%;margin:0 auto 14px;position:relative}}
    .device-screen {{width:100%;background:#000;overflow:hidden;display:flex;align-items:center;justify-content:center;position:relative}}
    .device-empty {{color:#dbeafe;font-size:16px;font-weight:900;text-align:center;padding:18px}}
    .device-empty span {{color:#a78bfa;font-weight:700;font-size:13px}}
    .device-phone-v .device-screen {{border:10px solid #111;border-radius:34px;background:linear-gradient(180deg,#111827,#1e1b4b);box-shadow:0 18px 50px rgba(0,0,0,.45)}}
    .device-phone-v::before {{content:"";position:absolute;top:6px;left:50%;transform:translateX(-50%);width:90px;height:18px;background:#000;border-radius:0 0 14px 14px;z-index:5}}
    .device-phone-h .device-screen {{border:10px solid #111;border-radius:24px;background:linear-gradient(180deg,#111827,#1e1b4b);box-shadow:0 18px 50px rgba(0,0,0,.45)}}
    .device-phone-h::before {{content:"";position:absolute;left:6px;top:50%;transform:translateY(-50%);width:18px;height:90px;background:#000;border-radius:14px 0 0 14px;z-index:5}}
    .device-tablet .device-screen {{border:14px solid #1a1a1a;border-radius:22px;background:linear-gradient(180deg,#111827,#1e1b4b);box-shadow:0 18px 50px rgba(0,0,0,.45)}}
    .device-laptop .device-screen {{border:9px solid #2b2b2b;border-top-width:22px;border-radius:14px 14px 4px 4px;background:linear-gradient(180deg,#111827,#1e1b4b);box-shadow:0 18px 50px rgba(0,0,0,.45)}}
    .device-laptop::after {{content:"";display:block;width:100%;height:14px;background:linear-gradient(180deg,#3a3a3a,#1a1a1a);border-radius:0 0 18px 18px;margin-top:-2px;box-shadow:0 10px 24px rgba(0,0,0,.35)}}
    .device-monitor .device-screen {{border:12px solid #1a1a1a;border-radius:8px;background:linear-gradient(180deg,#111827,#1e1b4b);box-shadow:0 18px 50px rgba(0,0,0,.45)}}
    .device-monitor::after {{content:"";display:block;width:32%;height:18px;margin:6px auto 0;background:linear-gradient(180deg,#2b2b2b,#111);border-radius:0 0 10px 10px}}
    .device-tv .device-screen {{border:18px solid #050505;border-radius:14px;background:linear-gradient(180deg,#0b1220,#1e1b4b);box-shadow:0 22px 60px rgba(0,0,0,.55)}}
    .device-tv::after {{content:"";display:block;width:24%;height:8px;margin:8px auto 0;background:#222;border-radius:6px}}
    .device-bare .device-screen {{border-radius:14px;background:#000;box-shadow:0 12px 32px rgba(0,0,0,.35)}}
    .voice-card {{border:1px solid #334155;background:#0f172a;border-radius:18px;padding:14px;margin-bottom:10px}}
    .voice-title {{font-weight:900;color:#fff;font-size:16px;margin-bottom:6px}}
    .sub {{color:#94a3b8;font-size:13px}}
    .stButton>button,.stDownloadButton>button {{border-radius:12px!important;font-weight:800!important}}
    </style>
    <div class="build">BUILD: {BUILD}</div>
    <div class="hero"><h1>🌐 Murat AI</h1><p>Профессиональная студия: видео → перевод → озвучка → готовый MP4. Слева вход, справа результат.</p></div>
    """,
    unsafe_allow_html=True,
)

st.markdown("<div class='card'><h2>⚙️ Настройки проекта</h2>", unsafe_allow_html=True)
r0 = st.columns(2)
fmt_name = r0[0].selectbox("🎬 ФОРМАТ ВИДЕО (соотношение сторон)", list(FORMATS.keys()))
screen_name = r0[1].selectbox("🖥 ЭКРАН ПРОСМОТРА (устройство-рамка)", list(SCREENS.keys()), index=4)
r1 = st.columns(5)
quality = r1[0].selectbox("Качество", QUALITIES, index=1)
src_lang = r1[1].selectbox("С языка", list(LANGS.keys()), format_func=lambda c: LANGS[c])
dst_lang = r1[2].selectbox("На язык", list(LANGS.keys()), index=1, format_func=lambda c: LANGS[c])
voice_names = [v["name"] for v in VOICE_CATALOG]
st.session_state.selected_voice = r1[3].selectbox("Голосовой профиль", voice_names, index=voice_names.index(st.session_state.selected_voice) if st.session_state.selected_voice in voice_names else 0)
emotion_mode = r1[4].selectbox("Эмоция", EMOTIONS)
r2 = st.columns(6)
speed = r2[0].slider("Темп", 0.6, 1.6, 1.0, 0.05)
pitch = r2[1].slider("Высота", 0.6, 1.6, 1.0, 0.05)
volume = r2[2].slider("Громкость", 0.1, 1.0, 1.0, 0.05)
r2[3].checkbox("Подогнать под тайминг", True)
r2[4].checkbox("Очистить шум / эхо", True)
r2[5].checkbox("Сохранить качество", True)
fmt = FORMATS[fmt_name]
screen = SCREENS[screen_name]
st.markdown(
    f"<span class='pill'>Формат видео: {fmt['label']}</span><span class='pill'>Экран просмотра: {screen['label']}</span>",
    unsafe_allow_html=True,
)
st.markdown("</div>", unsafe_allow_html=True)

active_emotion = st.session_state.analysis["emotion"] if emotion_mode == "Автоматически по оригиналу" else emotion_mode

left, right = st.columns(2, gap="large")
with left:
    st.markdown("<div class='card'><h2>📥 Исходное видео</h2>", unsafe_allow_html=True)
    video_screen(fmt, screen, result=False)
    st.session_state.video_url = st.text_input("Вставить ссылку на видео", value=st.session_state.video_url, placeholder="YouTube / Shorts / прямая mp4-ссылка")
    c1, c2 = st.columns(2)
    if c1.button("Показать видео", type="primary", use_container_width=True):
        st.session_state.video_file = None
        st.session_state.video_name = ""
        st.session_state.result_ready = False
        st.rerun()
    c2.button("Скачать видео по ссылке", disabled=True, use_container_width=True, help="Реальное скачивание ссылок выполняется на VPS/backend.")
    up = st.file_uploader("Загрузить видео из папки", type=["mp4", "mov", "webm", "mkv", "m4v"])
    if up is not None:
        st.session_state.video_file = up
        st.session_state.video_name = up.name
        st.session_state.video_url = ""
        st.session_state.result_ready = False
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

with right:
    st.markdown("<div class='card'><h2>📤 Готовое видео</h2>", unsafe_allow_html=True)
    if st.button("Создать готовое видео", type="primary", use_container_width=True):
        st.session_state.analysis = analyze_emotion(st.session_state.source_text)
        st.session_state.result_text = translate_text(st.session_state.source_text, src_lang, dst_lang)
        st.session_state.result_ready = True
        st.rerun()
    video_screen(fmt, screen, result=True)
    st.markdown(f"<span class='pill'>{fmt['label']}</span><span class='pill'>{screen['label']}</span><span class='pill'>{quality}</span><span class='pill'>{LANGS[dst_lang]}</span><span class='pill'>{st.session_state.selected_voice}</span><span class='pill'>{active_emotion}</span>", unsafe_allow_html=True)
    d1, d2 = st.columns(2)
    d1.download_button("Скачать MP4", data=b"MP4 preview placeholder", file_name="murat-ai-final.mp4", disabled=not st.session_state.result_ready, use_container_width=True)
    d2.download_button("Скачать MP4 + SRT", data=srt(st.session_state.result_text).encode(), file_name="murat-ai-final-with-srt.txt", disabled=not st.session_state.result_ready, use_container_width=True)
    d1.download_button("Скачать аудио", data=b"WAV preview placeholder", file_name="murat-ai-audio.wav", disabled=not st.session_state.result_ready, use_container_width=True)
    d2.download_button("Скачать ZIP пакет", data=project_json(), file_name="murat-ai-package.json", disabled=not st.session_state.result_ready, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

left, right = st.columns(2, gap="large")
with left:
    st.markdown("<div class='card'><h2>🎤 Аудио / мой голос</h2>", unsafe_allow_html=True)
    voice_file = st.file_uploader("Загрузить аудио голоса", type=["wav", "mp3", "m4a", "flac", "ogg"], key="voice_file")
    if voice_file is not None:
        st.session_state.voice_file = voice_file
        st.session_state.voice_name = voice_file.name
        st.audio(voice_file)
    elif st.session_state.voice_file:
        st.audio(st.session_state.voice_file)
    cc = st.columns(4)
    cc[0].checkbox("Очистить шум", True)
    cc[1].checkbox("Удалить эхо", True)
    cc[2].checkbox("Выровнять громкость", True)
    cc[3].checkbox("Сделать голос чистым", True)
    if st.button("Создать голосовой профиль", use_container_width=True):
        st.success("Голосовой профиль создан для preview." if st.session_state.voice_file else "Сначала загрузи запись голоса.")
    st.markdown("</div>", unsafe_allow_html=True)

with right:
    st.markdown("<div class='card'><h2>🔊 Готовая озвучка</h2>", unsafe_allow_html=True)
    if st.button("Создать озвучку", type="primary", use_container_width=True):
        st.session_state.analysis = analyze_emotion(st.session_state.source_text)
        st.session_state.result_text = st.session_state.result_text or translate_text(st.session_state.source_text, src_lang, dst_lang)
    speak_button(st.session_state.result_text or st.session_state.source_text, dst_lang, st.session_state.selected_voice, active_emotion, speed, pitch, volume, "main")
    st.caption(f"Туркменский TTS backend: {TURKMEN_TTS_BACKEND}. Эмоция передаётся через speed/pitch/energy/pause/volume.")
    a1, a2 = st.columns(2)
    a1.download_button("Скачать WAV", data=b"WAV preview placeholder", file_name="voiceover.wav", use_container_width=True)
    a2.download_button("Скачать MP3", data=b"MP3 preview placeholder", file_name="voiceover.mp3", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

left, right = st.columns(2, gap="large")
with left:
    st.markdown("<div class='card'><h2>📝 Текст / сценарий / субтитры</h2>", unsafe_allow_html=True)
    st.session_state.source_text = st.text_area("Исходный текст", value=st.session_state.source_text, height=220, label_visibility="collapsed")
    b1, b2, b3 = st.columns(3)
    if b1.button("Перевести", type="primary", use_container_width=True):
        st.session_state.analysis = analyze_emotion(st.session_state.source_text)
        st.session_state.result_text = translate_text(st.session_state.source_text, src_lang, dst_lang)
        st.rerun()
    if b2.button("Озвучить", use_container_width=True):
        st.session_state.analysis = analyze_emotion(st.session_state.source_text)
        st.session_state.result_text = st.session_state.result_text or translate_text(st.session_state.source_text, src_lang, dst_lang)
        st.rerun()
    if b3.button("Текст → видео", use_container_width=True):
        st.session_state.analysis = analyze_emotion(st.session_state.source_text)
        st.session_state.result_text = translate_text(st.session_state.source_text, src_lang, dst_lang)
        st.session_state.result_ready = True
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

with right:
    st.markdown("<div class='card'><h2>✅ Готовый перевод / субтитры</h2>", unsafe_allow_html=True)
    st.session_state.result_text = st.text_area("Готовый текст", value=st.session_state.result_text, height=220, label_visibility="collapsed")
    t1, t2, t3 = st.columns(3)
    t1.download_button("Скачать TXT", data=st.session_state.result_text.encode(), file_name="murat-ai.txt", use_container_width=True)
    t2.download_button("Скачать SRT", data=srt(st.session_state.result_text).encode(), file_name="murat-ai.srt", use_container_width=True)
    t3.download_button("Скачать VTT", data=vtt(st.session_state.result_text).encode(), file_name="murat-ai.vtt", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<div class='card'><h2>🧠 Анализ оригинала</h2>", unsafe_allow_html=True)
a = st.session_state.analysis
st.markdown(f"<span class='pill'>Эмоция: {a['emotion']}</span><span class='pill'>Уверенность: {a['confidence']}%</span><span class='pill'>Темп: {a['speed']}</span><span class='pill'>Энергия: {a['energy']}</span><span class='pill'>Громкость: {a['volume']}</span><span class='pill'>Паузы: {a['pauses']}</span><span class='pill'>Источник: текст / аудио / видео</span>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<div class='card'><h2>🎭 Роли и голоса</h2>", unsafe_allow_html=True)
actor_count = st.number_input("Сколько голосов / актёров в видео", min_value=1, max_value=12, value=len(st.session_state.actors))
while len(st.session_state.actors) < actor_count:
    st.session_state.actors.append({"role": f"Актёр {len(st.session_state.actors)+1}", "voice": "Туркменский мужской — чистый", "emotion": "Авто по реплике", "replace": "Не заменять"})
st.session_state.actors = st.session_state.actors[:actor_count]
for i, actor in enumerate(st.session_state.actors):
    cols = st.columns([1.2, 1.6, 1.2, 1.2, 1.0])
    actor["role"] = cols[0].text_input("Роль", actor["role"], key=f"role_{i}")
    actor["voice"] = cols[1].selectbox("Голос", voice_names, index=voice_names.index(actor["voice"]) if actor["voice"] in voice_names else 0, key=f"voice_{i}")
    actor["emotion"] = cols[2].selectbox("Эмоция", ["Авто по реплике", "Авто по оригиналу", "Вручную"], key=f"emotion_{i}")
    actor["replace"] = cols[3].selectbox("Заменить голос", ["Не заменять", "Мой загруженный голос", "Загрузить отдельный"], key=f"replace_{i}")
    with cols[4]:
        speak_button(f"Это пример голоса для роли {actor['role']}", dst_lang, actor["voice"], active_emotion, speed, pitch, volume, f"actor_{i}")
    if actor["replace"] == "Загрузить отдельный":
        st.file_uploader(f"Голос для роли {actor['role']}", type=["wav", "mp3", "m4a", "flac", "ogg"], key=f"role_voice_{i}")
st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<div class='card'><h2>🎙️ Каталог голосов</h2>", unsafe_allow_html=True)
filter_lang = st.selectbox("Фильтр по языку", ["Все", "Русский", "Туркменский", "Любой"])
grid = st.columns(3)
shown = 0
for voice in VOICE_CATALOG:
    if filter_lang != "Все" and voice["lang"] != filter_lang:
        continue
    with grid[shown % 3]:
        st.markdown(f"<div class='voice-card'><div class='voice-title'>{voice['name']}</div><div class='sub'>Язык: {voice['lang']} · возраст: {voice['age']} · стиль: {voice['style']}</div><div class='sub'>Эмоции: {', '.join(voice['emotions'][:4])}</div></div>", unsafe_allow_html=True)
        speak_button(SAMPLES.get(dst_lang, SAMPLES["ru"]), dst_lang, voice["name"], active_emotion, speed, pitch, volume, f"cat_{shown}")
        if st.button("Выбрать этот голос", key=f"select_{voice['id']}", use_container_width=True):
            st.session_state.selected_voice = voice["name"]
            st.rerun()
    shown += 1
st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<div class='card'><h2>📚 Замена слов</h2>", unsafe_allow_html=True)
r1, r2, r3, r4 = st.columns([1.4, 1.4, 1.2, 1.0])
old_word = r1.text_input("Какое слово заменить")
new_word = r2.text_input("На что заменить")
scope = r3.selectbox("Область", ["Глобально", "Только текущий проект", "Только текущий канал"])
if r4.button("Сохранить", type="primary", use_container_width=True) and old_word and new_word:
    st.session_state.rules.append({"from": old_word, "to": new_word, "scope": scope})
    st.session_state.result_text = apply_rules(st.session_state.result_text)
    st.rerun()
if st.session_state.rules:
    st.dataframe(st.session_state.rules, use_container_width=True, hide_index=True)
st.download_button("Скачать настройки проекта JSON", data=project_json(), file_name="murat-ai-project.json", use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

st.caption(f"Настоящий MP4 4K/8K, клонирование голоса и туркменская TTS-модель {TURKMEN_TTS_BACKEND} работают на VPS/GPU backend. Preview показывает интерфейс и рабочую логику.")
