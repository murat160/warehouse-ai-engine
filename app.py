from __future__ import annotations

import json
import re
from typing import Dict, Tuple

import streamlit as st

st.set_page_config(page_title="Murat AI", page_icon="🌐", layout="wide", initial_sidebar_state="collapsed")

LANGS = {"ru": "Русский", "tk": "Туркменский", "tr": "Турецкий", "en": "Английский"}
VOICES = ["Мой голос", "Мужской", "Женский", "Детский", "Подростковый", "Кино-диктор", "Персонаж 1", "Персонаж 2", "Персонаж 3"]
EMOTIONS = ["Нейтрально", "Радостно", "Грустно", "Серьёзно", "Злой тон", "Спокойно", "Энергично", "Кино-драма", "Шёпот", "Волнение"]
RESOLUTIONS = ["1080p Full HD", "4K Ultra HD", "8K Ultra HD"]
ASPECTS = ["9:16 Shorts/Reels/TikTok", "16:9 YouTube", "1:1 Square"]
DOWNLOADS = ["Готовое видео MP4", "MP4 + субтитры SRT", "MP4 + отдельное аудио", "ZIP пакет"]

SAMPLE: Dict[Tuple[str, str], str] = {
    ("ru", "tk"): "Salam. Men bu wideony arassa türkmen diline terjime edip, professional derejede seslendirmek isleýärin.",
    ("tk", "ru"): "Здравствуйте. Я хочу перевести это видео и сделать профессиональную озвучку.",
    ("ru", "en"): "Hello. I want to translate this video and create professional dubbing.",
    ("en", "ru"): "Здравствуйте. Я хочу перевести это видео и сделать профессиональную озвучку.",
    ("ru", "tr"): "Merhaba. Bu videoyu profesyonel dublaj için çevirmek istiyorum.",
    ("tr", "ru"): "Здравствуйте. Я хочу перевести это видео и озвучить его.",
}


def init_state() -> None:
    defaults = {
        "source_video": None,
        "source_url": "",
        "voice_sample": None,
        "source_text": "Привет. Я хочу сделать профессиональное видео с переводом и озвучкой.",
        "result_text": "",
        "ready": False,
        "rules": [],
        "actors": [
            {"Роль": "Актёр 1", "Голос": "Мужской", "Эмоция": "Кино-драма", "Замена": "Нет"},
            {"Роль": "Актёр 2", "Голос": "Женский", "Эмоция": "Спокойно", "Замена": "Нет"},
        ],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def apply_rules(text: str) -> str:
    result = text
    for rule in st.session_state.rules:
        src = rule.get("from", "").strip()
        dst = rule.get("to", "").strip()
        if src and dst:
            result = re.sub(re.escape(src), dst, result, flags=re.I)
    return result


def translate(text: str, src: str, dst: str) -> str:
    if not text.strip():
        return ""
    return apply_rules(SAMPLE.get((src, dst), f"[{LANGS[src]} → {LANGS[dst]}] {text}"))


def make_srt(text: str) -> str:
    parts = [p.strip() for p in re.split(r"[.!?\n]+", text) if p.strip()] or ["Murat AI"]
    out = []
    t = 0
    for i, part in enumerate(parts, 1):
        out.append(f"{i}\n00:00:{t:02d},000 --> 00:00:{t+4:02d},000\n{part}\n")
        t += 4
    return "\n".join(out)


def project_json(aspect: str, resolution: str, voice: str, emotion: str, text: str) -> bytes:
    payload = {
        "product": "Murat AI",
        "mode": "professional_dubbing",
        "video_format": aspect,
        "output_resolution": resolution,
        "voice": voice,
        "emotion": emotion,
        "text": text,
        "actors": st.session_state.actors,
        "turkmen_tts_backend": {
            "provider": "HuggingFace Transformers",
            "model": "facebook/mms-tts-tuk-script_latin",
            "note": "Полная озвучка запускается на VPS/GPU backend, не в лёгком preview Streamlit.",
        },
    }
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


init_state()

st.markdown(
    """
<style>
.block-container{max-width:1500px;padding-top:18px}.hero{border-radius:30px;padding:24px 30px;background:linear-gradient(135deg,#0f172a,#24124d 60%,#083344);border:1px solid rgba(255,255,255,.14);margin-bottom:18px}.hero h1{font-size:44px;margin:0}.hero p{color:#dbeafe;font-size:18px;margin-top:8px}.card{border-radius:26px;padding:18px;background:rgba(255,255,255,.045);border:1px solid rgba(255,255,255,.14);box-shadow:0 18px 50px rgba(0,0,0,.18);margin-bottom:16px}.phone{height:620px;max-width:350px;margin:auto;border:10px solid #111827;border-radius:38px;background:linear-gradient(180deg,#111827,#1e1b4b);display:flex;align-items:center;justify-content:center;text-align:center;color:#dbeafe;font-size:20px;font-weight:900;padding:24px;box-shadow:0 30px 80px rgba(0,0,0,.45)}.status{background:rgba(16,185,129,.13);border:1px solid rgba(16,185,129,.36);color:#d1fae5;border-radius:16px;padding:12px 14px;font-weight:900}.arrow{font-size:54px;text-align:center;color:#a78bfa;padding-top:300px}.small{color:#cbd5e1;font-size:14px}.downloadbox{background:rgba(124,58,237,.12);border:1px solid rgba(124,58,237,.34);border-radius:18px;padding:14px}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown("<div class='hero'><h1>🌐 Murat AI</h1><p>Профессиональная студия: 9:16 видео, дубляж, эмоции, роли актёров, свой голос и понятное скачивание результата.</p></div>", unsafe_allow_html=True)

s1, s2, s3, s4, s5 = st.columns(5)
src_lang = s1.selectbox("С языка", list(LANGS), format_func=lambda x: LANGS[x])
dst_lang = s2.selectbox("На язык", list(LANGS), format_func=lambda x: LANGS[x], index=1)
main_voice = s3.selectbox("Основной голос", VOICES, index=0)
main_emotion = s4.selectbox("Эмоция", EMOTIONS, index=0)
aspect = s5.selectbox("Формат", ASPECTS, index=0)

s6, s7, s8, s9 = st.columns(4)
resolution = s6.selectbox("Качество видео", RESOLUTIONS, index=1)
tempo = s7.slider("Темп озвучки", 0.70, 1.30, 1.00, 0.05)
volume = s8.slider("Громкость", 0.50, 1.50, 1.00, 0.05)
download_type = s9.selectbox("Что скачать", DOWNLOADS, index=0)

left, middle, right = st.columns([1, 0.12, 1], gap="small")

with left:
    st.markdown("<div class='card'><h2>⬅️ Исходное видео</h2>", unsafe_allow_html=True)
    st.session_state.source_url = st.text_input("Ссылка на видео", value=st.session_state.source_url, placeholder="Вставь ссылку или загрузи видео из папки")
    video_file = st.file_uploader("Загрузить видео", type=["mp4", "mov", "webm", "mkv"])
    if video_file is not None:
        st.session_state.source_video = video_file
    if st.button("Показать видео по ссылке", use_container_width=True) and st.session_state.source_url.strip():
        st.session_state.source_video = st.session_state.source_url.strip()
    if st.session_state.source_video:
        st.video(st.session_state.source_video)
    else:
        st.markdown("<div class='phone'>Здесь будет исходное видео 9:16</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='card'><h2>🎙️ Свой голос</h2>", unsafe_allow_html=True)
    voice_file = st.file_uploader("Загрузить образец голоса", type=["mp3", "wav", "m4a", "flac", "ogg"])
    if voice_file is not None:
        st.session_state.voice_sample = voice_file
        st.audio(voice_file)
        st.success("Голос принят. Полный backend очистит шум, эхо и сделает голосовой профиль.")
    st.checkbox("Очистить шум", value=True)
    st.checkbox("Удалить эхо", value=True)
    st.checkbox("Выровнять громкость", value=True)
    st.markdown("</div>", unsafe_allow_html=True)

with middle:
    st.markdown("<div class='arrow'>→</div>", unsafe_allow_html=True)

with right:
    st.markdown("<div class='card'><h2>➡️ Готовое видео</h2>", unsafe_allow_html=True)
    if st.button("Создать готовый продукт", type="primary", use_container_width=True):
        st.session_state.result_text = translate(st.session_state.source_text, src_lang, dst_lang)
        st.session_state.ready = True
    if st.session_state.ready and st.session_state.source_video:
        st.video(st.session_state.source_video)
    else:
        st.markdown("<div class='phone'>Здесь будет готовое видео MP4 9:16 / 4K / 8K</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='status'>Готовится: {aspect}, {resolution}, голос: {main_voice}, эмоция: {main_emotion}, темп: {tempo}, громкость: {volume}</div>", unsafe_allow_html=True)
    st.markdown("<div class='downloadbox'>", unsafe_allow_html=True)
    st.download_button("⬇️ Скачать готовое видео MP4", data=b"Preview. Full MP4 renders on VPS/GPU backend.", file_name="murat-ai-final-video-preview.txt", use_container_width=True)
    st.download_button("⬇️ Скачать проект ZIP/JSON", data=project_json(aspect, resolution, main_voice, main_emotion, st.session_state.result_text), file_name="murat-ai-project.json", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<div class='card'><h2>📝 Текст, перевод и озвучка</h2>", unsafe_allow_html=True)
t1, t2 = st.columns(2)
with t1:
    st.session_state.source_text = st.text_area("Исходный текст / сценарий / субтитры", value=st.session_state.source_text, height=190)
    if st.button("Перевести текст", type="primary", use_container_width=True):
        st.session_state.result_text = translate(st.session_state.source_text, src_lang, dst_lang)
with t2:
    st.session_state.result_text = st.text_area("Готовый текст", value=st.session_state.result_text, height=190)
    st.info("Туркменская озвучка: модель facebook/mms-tts-tuk-script_latin подключается на VPS/GPU backend. Preview показывает сценарий и настройки.")
st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<div class='card'><h2>🎭 Роли, голоса и эмоции</h2>", unsafe_allow_html=True)
actors_count = st.number_input("Сколько голосов / актёров в видео", min_value=1, max_value=10, value=len(st.session_state.actors), step=1)
while len(st.session_state.actors) < actors_count:
    st.session_state.actors.append({"Роль": f"Актёр {len(st.session_state.actors)+1}", "Голос": "Мужской", "Эмоция": "Нейтрально", "Замена": "Нет"})
st.session_state.actors = st.session_state.actors[:actors_count]
for i in range(actors_count):
    a, b, c, d = st.columns([1.2, 1, 1, 1.2])
    st.session_state.actors[i]["Роль"] = a.text_input(f"Роль {i+1}", value=st.session_state.actors[i]["Роль"], key=f"role_{i}")
    st.session_state.actors[i]["Голос"] = b.selectbox(f"Голос {i+1}", VOICES, index=VOICES.index(st.session_state.actors[i]["Голос"]) if st.session_state.actors[i]["Голос"] in VOICES else 0, key=f"voice_{i}")
    st.session_state.actors[i]["Эмоция"] = c.selectbox(f"Эмоция {i+1}", EMOTIONS, index=EMOTIONS.index(st.session_state.actors[i]["Эмоция"]) if st.session_state.actors[i]["Эмоция"] in EMOTIONS else 0, key=f"emotion_{i}")
    st.session_state.actors[i]["Замена"] = d.selectbox(f"Заменить голос {i+1}", ["Нет", "Моим голосом", "Загруженным голосом", "Другим актёром"], key=f"replace_{i}")
st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<div class='card'><h2>📚 Замена слов и скачивание</h2>", unsafe_allow_html=True)
r1, r2, r3 = st.columns(3)
old = r1.text_input("Какое слово заменить")
new = r2.text_input("На что заменить")
if r3.button("Сохранить замену", use_container_width=True) and old and new:
    st.session_state.rules.append({"from": old, "to": new})
    st.success(f"Сохранено: {old} → {new}")
d1, d2, d3 = st.columns(3)
d1.download_button("Скачать TXT", data=(st.session_state.result_text or "").encode("utf-8"), file_name="murat-ai-text.txt", use_container_width=True)
d2.download_button("Скачать SRT", data=make_srt(st.session_state.result_text or st.session_state.source_text).encode("utf-8"), file_name="murat-ai-subtitles.srt", use_container_width=True)
d3.download_button("Скачать настройки проекта", data=project_json(aspect, resolution, main_voice, main_emotion, st.session_state.result_text), file_name="murat-ai-project.json", use_container_width=True)
if st.session_state.rules:
    st.dataframe(st.session_state.rules, use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

st.caption("Murat AI preview. Финальный MP4, клонирование голоса, туркменский MMS-TTS и 4K/8K рендер запускаются на VPS/GPU backend.")
