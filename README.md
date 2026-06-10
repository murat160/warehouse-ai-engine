# Murat AI Studio

> **Murat AI Studio — профессиональная студия перевода, озвучки и дубляжа
> видео на туркменский язык.** Главный приоритет — пара **ru ↔ tk** с
> литературным регистром в обоих языках. Также поддерживаются `tr` и `en`.
>
> _Техническое имя GitHub-репозитория — `warehouse-ai-engine`. Продукт в
> интерфейсе и в публикациях называется **Murat AI Studio**._
>
> Публичный preview: `https://murat-ai.streamlit.app` (или `https://murat-ai-studio.streamlit.app`).

Финальный сайт может жить на любом субдомене, который направишь на свой
VPS — деплой полностью domain-agnostic. Примеры:

* `https://ai.murat-ai.com`
* `https://ai.ehlitrend.com`
* `https://translator.your-domain.com`

> ⚠️ Эти ссылки сами по себе **ещё не работают**: A-запись DNS должна
> быть создана у регистратора (см. [`deploy/dns-records.md`](deploy/dns-records.md)),
> и стек должен быть запущен на VPS (см.
> [`docs/self-hosted-deploy.md`](docs/self-hosted-deploy.md)).

Этот репозиторий — **отдельный AI-проект**. Он намеренно изолирован от
`warehouse-ecosystem` и не содержит кода клиентского, курьерского, продавца
или админ-панели.

## Архитектура — два независимых сервиса

```
┌──────────────────────┐         ┌──────────────────────────┐
│  Streamlit Cloud     │ ──HTTP→ │  Murat AI Backend (VPS)   │
│  app.py (UI only)    │         │  backend/main.py + GPU/CPU │
│  light deps:         │         │  FastAPI + yt-dlp + Whisper│
│   streamlit          │         │  + MMS-TTS + ffmpeg        │
│   requests           │         │  + external TTS provider   │
│   python-dotenv      │         │  storage/jobs/<id>/...      │
└──────────────────────┘         └──────────────────────────┘
         │                                  ▲
         └──── BACKEND_URL=https://ai-api.your-domain.com ────┘
```

**Murat AI Studio** работает как ОДИН ЗАКОНЧЕННЫЙ ПАКЕТ, но физически
разделён на две независимые части:

| Часть | Где крутится | Что делает |
|---|---|---|
| **Streamlit UI** | Streamlit Cloud (бесплатно) | Показывает интерфейс, общается с backend через HTTP API |
| **Murat AI Backend** | твой VPS (4 vCPU+, GPU желательно) | yt-dlp, Whisper ASR, MMS-TTS, ffmpeg рендер, all heavy AI |

⚠️ **Murat AI ИЗОЛИРОВАН от `warehouse-ecosystem`** (admin/customer/seller/
courier/staff/pickup/supervisor apps). Никаких прямых импортов или общей
БД. Если warehouse надо вызвать Murat AI — только через HTTP API endpoints
ниже.

## Как запустить

### A) Streamlit UI preview (бесплатно, без обработки)

```bash
git clone https://github.com/murat160/warehouse-ai-engine.git
cd warehouse-ai-engine
pip install -r requirements.txt   # streamlit + requests + python-dotenv
streamlit run app.py
```

Откроется на `http://localhost:8501`. Это preview UI — все кнопки видны,
но реальная обработка не работает без `BACKEND_URL`. Сверху страницы будет
красный баннер «Preview mode — Murat AI backend не подключён».

### B) Murat AI Backend на VPS

```bash
ssh root@your-vps
git clone https://github.com/murat160/warehouse-ai-engine.git
cd warehouse-ai-engine
cp .env.production.example .env.production
nano  .env.production                 # заполнить TURKMEN_TTS_* и др.
docker compose -f docker-compose.ai.yml up -d --build
```

Проверка:
```bash
curl http://localhost:8000/api/health
# → {"ok": true, "yt_dlp": true, "ffmpeg": true, "torch": true, "tts_configured": true, ...}
docker compose -f docker-compose.ai.yml logs -f murat-ai-backend
```

### C) Подключение Streamlit UI → Backend

Открой публичный backend через nginx + Certbot (см. `docs/vps-backend-setup.md`),
получи URL вида `https://ai-api.your-domain.com`. Затем в Streamlit Cloud:

`Manage app` → `⋮` → **Settings** → **Secrets**:
```toml
BACKEND_URL = "https://ai-api.your-domain.com"
```

**Reboot app** в Streamlit Cloud. Сверху появится **Статус системы** с
зелёными пилюлями: BACKEND_URL подключён ✅ · yt-dlp ✅ · ffmpeg ✅ ·
TTS provider ✅ · Real processing ✅.

### D) End-to-end test

1. Открой Streamlit UI → проверь что сверху **зелёный** статус.
2. Вставь YouTube Shorts URL → нажми **🔍 Проверить ссылку**.
3. Нажми **⬇️ Загрузить видео по ссылке** → слева в рамке появится
   скачанный MP4 (не YouTube embed).
4. Нажми **✨ Создать готовое видео на туркменском** → прогресс-карточка
   сверху + анимация в правой рамке.
5. Через ~3 минуты → справа **`final_turkmen_video.mp4`** с туркменской
   озвучкой.
6. Нажми **⬇ MP4** под правой рамкой → файл скачается в Downloads.

## HTTP API endpoints (Murat AI Backend)

```
GET  /api/health                              ← статус + что доступно
POST /api/video/inspect-url                   ← metadata по ссылке (без скачивания)
POST /api/video/download-url                  ← yt-dlp → source_video.mp4
POST /api/jobs/upload-and-create              ← локальный файл → source_video.mp4
POST /api/jobs/{job_id}/process-turkmen       ← запуск pipeline
GET  /api/jobs/{job_id}/status                ← progress + ETA
GET  /api/jobs/{job_id}/result                ← URLs готовых файлов
GET  /api/jobs/{job_id}/files/{filename}      ← отдача файла
POST /api/tts/turkmen                         ← один-шаг: текст → озвучка
POST /api/translate/turkmen                   ← один-шаг: текст → tk + quality
POST /api/voice/create-profile                ← voice cloning из 30-40 сек MP3
POST /api/speakers/detect                     ← speaker diarization
```

Если у тебя есть другой сервис (например `warehouse-ecosystem`), он может
использовать Murat AI **только через эти endpoints** — никаких прямых
импортов Python-кода или общей БД.



## Внешний Turkmen TTS provider (опционально)

Pipeline сначала пытается через внешний REST-сервис (если задан в env),
иначе falls back на MMS-TTS. Никакие ключи **никогда не вставляются в код**.

**Streamlit Cloud Secrets** (`⋮` → Settings → Secrets):
```toml
TURKMEN_TTS_PROVIDER          = "elevenlabs"
TURKMEN_TTS_API_BASE_URL      = "https://api.elevenlabs.io"
TURKMEN_TTS_API_KEY           = "sk_***"
TURKMEN_TTS_VOICE_ID          = "voice_id"
TURKMEN_TTS_ENDPOINT_TEMPLATE = "/v1/text-to-speech/{voice_id}"
TURKMEN_TTS_AUTH_HEADER       = "xi-api-key"
TURKMEN_TTS_AUTH_FORMAT       = "{key}"
TURKMEN_TTS_BODY_TEMPLATE     = '{"text":{text_json},"model_id":"eleven_multilingual_v2"}'
TURKMEN_TTS_RESPONSE_FORMAT   = "audio"
TURKMEN_TTS_OUTPUT_FORMAT     = "mp3"
```

**VPS environment** (`/etc/environment` или systemd EnvironmentFile):
```bash
export TURKMEN_TTS_PROVIDER=elevenlabs
export TURKMEN_TTS_API_BASE_URL=https://api.elevenlabs.io
export TURKMEN_TTS_API_KEY=sk_xxx
export TURKMEN_TTS_VOICE_ID=...
```

Тест endpoint без полного pipeline:
```bash
curl -X POST https://ai.your-domain.com/api/tts/turkmen \
  -H 'Content-Type: application/json' \
  -d '{"text":"Salam dostum","output_format":"mp3"}'
# → {"ok":true, "audio_url":"/api/jobs/job_xxx/files/voiceover.mp3", "provider":"elevenlabs"}
```

Полная справка по env-vars: `.env.production.example`.

## Два режима работы — что где включается

| Что | Streamlit Cloud preview | VPS / GPU full stack |
|---|---|---|
| requirements | `requirements.txt` (~50 МБ) | `requirements-full.txt` (~5 ГБ) |
| UI | Murat AI Studio ✅ | Murat AI Studio ✅ |
| Перевод ru/tk/tr/en | mock-стабы | MADLAD-400 / NLLB-200 |
| Туркменский TTS | mock-сообщение | реальный `facebook/mms-tts-tuk-script_latin` |
| Whisper ASR | — | ✅ |
| Speaker diarization | — | ✅ |
| Voice cloning | — | ✅ |
| Скачивание видео | — | yt-dlp ✅ |
| Финальный рендер MP4 | — | ffmpeg + GPU ✅ |

Streamlit Cloud = только **UI preview** (легковесный pip install за 30 сек).
Все heavy AI deps (torch, transformers, whisper, scipy, sentencepiece, ffmpeg)
живут в `requirements-full.txt` и ставятся только на VPS.

В репозитории сосуществуют две независимые реализации:

1. **Cloud MVP (`app.py` + `src/cloud/`)** — рабочее end-to-end приложение
   на Streamlit. Перевод через **MADLAD-400** (Apache 2.0), распознавание
   речи через **openai-whisper** (MIT). Туркменская озвучка — opt-in
   (commercial API через `OPENAI_API_KEY` / `MMS-TTS` под CC-BY-NC если
   явно включить). Работает без внешних API-ключей для текста и STT.
   Загружает медиа по ссылке (YouTube/TikTok через `yt-dlp`) или из
   загруженного файла.
2. **API-архитектура (`src/api/` + `src/translator/` + `src/speech/` + `src/video/` + `src/providers/`)** —
   провайдер-нейтральный сервис на FastAPI с глоссарием ru↔tk, проверкой
   качества и подключаемыми бэкендами (OpenAI / MMS-TTS).

Оба режима используют одну и ту же ветку и не зависят друг от друга.

## Возможности

- Перевод текста между всеми парами `ru ↔ tk ↔ tr ↔ en` (12 направлений).
- **15 стилей перевода** — natural (по умолчанию), blogger, conversational,
  street, literary, formal, news, cultural, expressive, dramatic, children,
  teen, humorous, advertising, expert. Полный список и инструкции —
  [`docs/style-modes.md`](docs/style-modes.md).
- **16 тонов подачи** (calm, confident, friendly, warm, serious,
  cheerful, energetic, respectful, soft, firm, cultural, modern,
  traditional, simple, deep, emotional) — ортогональны стилю.
- **7 эмоциональных пресетов** (neutral / happy / sad / serious / excited /
  respectful / warm) — управляют и переводом, и (для `tk`) озвучкой.
- **23 голосовых профиля** — мужские/женские/детские/подростковые,
  специализированные (новостной, блогерский, уличный, драматичный,
  рекламный, образовательный) + культурный туркменский. Подробности —
  [`docs/voice-profiles.md`](docs/voice-profiles.md).
- **Custom Voice / «Мой голос»** — пользовательские голоса с настройками
  (скорость, высота, эмоция, чистота, сила, тип использования), загрузкой
  или записью семпла, **обязательным согласием**, вариантами одного
  голоса, привязкой к каналу / стилю / типу видео и кнопкой «Прослушать
  пример». Подробности — [`docs/custom-voices.md`](docs/custom-voices.md).
  Аудиофайлы хранятся локально и **никогда не попадают в git**.
- **Многоязычный интерфейс** — переключатель языка UI прямо в боковой
  панели: 🇷🇺 Русский · 🇹🇲 Türkmençe · 🇹🇷 Türkçe · 🇬🇧 English.
- **Публикация на YouTube / TikTok / Instagram / Facebook / Telegram / X** —
  готовые ZIP-пакеты с медиа, метаданными и текстом для каждой платформы,
  кнопки прямого перехода на страницу загрузки. Подробности —
  [`docs/publishing.md`](docs/publishing.md). Прямой OAuth-аплоад
  включается, когда у тебя появятся API-ключи каждой платформы (инструкции
  внутри документа).
- **AI-агенты / каналы** — каждый со своим стилем, тоном, эмоцией,
  голосом, словарём и Translation Memory. Подробности —
  [`docs/ai-agent-profiles.md`](docs/ai-agent-profiles.md).
- Встроенный курируемый глоссарий + **пользовательский словарь**
  (глобальный и канал-специфичный, CRUD + поиск). Канал-словарь имеет
  приоритет выше AI.
- **Translation Memory** — сохранение целых фраз (глобально и на канал);
  при повторном запросе система отдаёт точный сохранённый вариант,
  минуя модель.
- Распознавание речи (STT) из аудио/видео.
- Озвучка переведённого текста: туркменский — через локальный
  **Meta MMS-TTS** (`facebook/mms-tts-tuk-script_latin`), остальные —
  через основного провайдера.
- Заготовка пайплайна дубляжа видео: `extract → STT → translate → TTS → mux`.

## Как «учится» переводчик

Каждый перевод проходит цепочку:

```
input → [Translation Memory exact match? ──► return curated text]
      └► provider (NLLB-200 / OpenAI) с подсказкой стиля
      └► curated glossary (ru↔tk built-in)
      └► user glossary  ← правила, добавленные пользователем
      └► quality check
```

- **Замена прямо после перевода** — кнопка «✏️ Replace translation»
  сохраняет правильный вариант в Translation Memory; следующий такой же
  запрос вернёт сохранённый текст без обращения к модели.
- **Добавить в словарь** — кнопка «📚 Add to dictionary» создаёт правило
  замены, которое автоматически применяется ко всем будущим переводам в
  этой языковой паре.
- **Поиск** в разделе «My Dictionary» — мгновенный фильтр по исходнику
  и переводу.
- **Хранилище** — локальный SQLite (`data/warehouse_ai.db`). Чтобы
  переключиться на PostgreSQL, задайте `DATABASE_URL=postgresql+psycopg://…`
  — код менять не нужно.
- HTTP API на FastAPI: `/v1/translate`, `/v1/stt`, `/v1/tts`, `/health`.

## Структура

```
src/
  translator/    # перевод текста + статический и пользовательский глоссарий
                 # + Translation Memory + стили/эмоции + проверка качества
  speech/        # STT и TTS фасады
  video/         # ffmpeg-обвязка, субтитры, дубляж
  providers/     # базовые интерфейсы и реализации (OpenAI, MMS-TTS)
  storage/       # SQLAlchemy: glossary + TM (SQLite по умолчанию, ready for PG)
  api/           # FastAPI приложение и pydantic-схемы
  cloud/         # cloud MVP: NLLB-200 + Whisper + MMS-TTS
  ui/            # тема и общие UI-элементы для Streamlit
app.py           # точка входа Streamlit
docs/translator-architecture.md
tests/           # юнит-, интеграционные и API-тесты на фейковых провайдерах
.env.example
requirements.txt
```

Подробное описание архитектуры — [`docs/translator-architecture.md`](docs/translator-architecture.md).

## Установка

Требуется Python 3.10+ и `ffmpeg` в `PATH` (нужен только для видео-пайплайна).

```bash
python -m venv .venv
# Linux / macOS:
source .venv/bin/activate
# Windows PowerShell:
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

Опционально, для офлайн-озвучки туркменского через Meta MMS-TTS:

```bash
pip install transformers torch scipy
```

## Конфигурация

Скопируйте `.env.example` в `.env` и заполните значения. **Никогда не
коммитьте `.env` с реальными ключами** — он в `.gitignore`.

Минимально необходимые переменные:

| Переменная                  | Описание                                                |
|-----------------------------|---------------------------------------------------------|
| `OPENAI_API_KEY`            | Ключ для перевода / STT / TTS (ru/tr/en).              |
| `MMS_TTS_TUK_ENABLED`       | `true` — включить локальную озвучку туркменского.      |
| `TRANSLATOR_USE_GLOSSARY`   | Применять ru↔tk глоссарий после перевода.              |
| `TRANSLATOR_QUALITY_CHECK`  | Запускать эвристическую проверку качества.             |
| `TRANSLATOR_LATENCY_BUDGET` | Мягкий бюджет латентности на запрос (сек).             |
| `DATABASE_URL`              | URL базы для словаря и TM. По умолчанию SQLite.        |

## Запуск Streamlit Cloud MVP (`app.py`)

```bash
pip install -r requirements.txt
streamlit run app.py
```

После запуска откройте `http://localhost:8501`. UI:

- **Боковая панель** — переключатель активного канала (AI-агента) и
  глобальные настройки.
- **✨ Translate** — текст, выбор From/To из ru/tk/tr/en, стиль (15),
  тон (16, опционально), эмоция (7), голос (23 профиля). Кнопки:
  «🔊 Voice», «✏️ Replace translation» (сохранить в TM канала или
  глобально), «📚 Add to dictionary» (создать правило-замену в словаре).
- **🎬 Audio / Video / URL** — вставьте ссылку (YouTube/TikTok через
  `yt-dlp`) или загрузите файл. Пайплайн: `download → ffmpeg → Whisper
  ASR → NLLB-200 → (для tk) MMS-TTS`. Стиль/тон/эмоция/голос для
  озвучки выбираются перед запуском.
- **📚 Dictionary** — пользовательский словарь с поиском, фильтрами по
  языку и scope (global / channel / all).
- **🧠 Memory** — Translation Memory с теми же фильтрами.
- **🤖 Channels** — CRUD AI-агентов: задаёшь стиль, тон, эмоцию, голос,
  use case. Кнопка «Activate» делает канал активным.
- **🎙️ Voices** — каталог из 23 голосов с фильтрами по языку, use-case
  и полу.

> ⚠️ **Реалистичные задержки** (без GPU, на free CPU):
> текстовый перевод короткой фразы — ~0.3–1 с,
> Whisper-small — ~1–3 с на минуту аудио,
> MMS-TTS — ~1–3 с,
> полный пайплайн «видео → озвучка на туркменском» — ~30–90 с
> на минуту видео. Миллисекундные задержки достижимы только на GPU и со
> стримингом.

## Production deployment on own VPS

**Основной путь деплоя** — собственный VPS с твоим доменом и твоей базой
PostgreSQL. Полная инструкция:
[`docs/self-hosted-deploy.md`](docs/self-hosted-deploy.md).

> ⚠️ **Статус доменов**: `ai.murat-ai.com` упоминается в документации
> только как пример — соответствующая DNS-запись пока не создана,
> поэтому публичной ссылки **ещё нет**. Деплой работает на любой
> субдомен, который ты направишь на VPS — например `ai.murat-ai.com`,
> `ai.ehlitrend.com` или `translator.your-domain.com`. Точные DNS-настройки —
> [`deploy/dns-records.md`](deploy/dns-records.md).

В репозитории уже есть всё необходимое:

| Файл                                | Назначение                                    |
|-------------------------------------|-----------------------------------------------|
| `Dockerfile`                        | Production-образ Streamlit (CPU-only torch)   |
| `docker-compose.yml`                | App + Postgres + persistent volumes           |
| `.env.production.example`           | Шаблон секретов (реальный `.env.production` не коммитится) |
| `deploy/nginx/murat-ai.conf`        | nginx site template (placeholder `__MURAT_AI_DOMAIN__`) |
| `deploy/install-nginx.sh`           | Подменяет placeholder на твой домен и активирует site |
| `deploy/dns-records.md`             | Точные DNS-записи (тип, имя, значение)        |
| `docs/self-hosted-deploy.md`        | Пошаговая инструкция (Ubuntu)                  |

VPS, к которому привязан проект: **`46.202.189.230`** (Ubuntu).

### DNS-запись (одна строчка у регистратора)

| Type | Name | Content          | Proxy / Cloud                  | TTL |
|------|------|------------------|--------------------------------|-----|
| A    | `ai` | `46.202.189.230` | DNS only → потом Proxied (CF)  | 300 |

«Name = `ai`» в зоне `murat-ai.com` даёт `ai.murat-ai.com`. В зоне
`ehlitrend.com` — `ai.ehlitrend.com`. См.
[`deploy/dns-records.md`](deploy/dns-records.md).

### Короткая версия деплоя (Ubuntu 22.04 / 24.04)

```bash
# 0. На любой машине — настрой DNS (см. таблицу выше).

# 1. На VPS
cd /opt
sudo git clone https://github.com/murat160/warehouse-ai-engine.git
sudo chown -R $USER:$USER warehouse-ai-engine
cd warehouse-ai-engine
git checkout issue-2-ai-architecture

# 2. Domain — выбери ОДИН и подставь в команды ниже
export MURAT_AI_DOMAIN=ai.murat-ai.com         # или ai.ehlitrend.com

# 3. Секреты + контейнеры
cp .env.production.example .env.production
chmod 600 .env.production
nano .env.production              # задать POSTGRES_PASSWORD
docker compose up -d --build

# 4. nginx HTTP-bootstrap (нужен Certbot-у для верификации)
sudo apt install -y nginx snapd
sudo snap install --classic certbot
sudo ln -sf /snap/bin/certbot /usr/bin/certbot
sudo deploy/install-nginx.sh --bootstrap "$MURAT_AI_DOMAIN"

# 5. SSL
sudo certbot --nginx -d "$MURAT_AI_DOMAIN" --redirect \
             --agree-tos -m you@your-domain.com -n

# 6. Финальный nginx с WebSocket / 500 МБ uploads / 600s timeouts
sudo deploy/install-nginx.sh "$MURAT_AI_DOMAIN"

# 7. Проверка
curl -I "https://$MURAT_AI_DOMAIN/_stcore/health"   # → 200 OK
```

После этого `https://$MURAT_AI_DOMAIN` показывает Murat AI.

Все пользовательские данные хранятся **на твоей машине**, не в GitHub:

* `./data/` — пользовательский словарь, Custom Voice семплы, publishing
  inbox, ffmpeg-артефакты.
* docker-volume `postgres_data` — Postgres-таблицы (каналы, TM, glossary,
  Custom Voices, publishing packages).
* docker-volume `hf_cache` — веса NLLB-200 / Whisper / MMS-TTS.

### Альтернативные варианты (для быстрых демо)

Hugging Face Spaces / Streamlit Community Cloud — только для
демонстраций: эти сервисы сбрасывают контейнер при перезапуске и не
подходят для production. Подробности и оговорки — в
[`docs/deploy.md`](docs/deploy.md).

## Запуск FastAPI-архитектуры

```bash
# из корня репозитория
uvicorn --factory src.api.main:create_app --host 0.0.0.0 --port 8000
```

Проверка живости:

```bash
curl http://localhost:8000/health
```

Перевод текста:

```bash
curl -X POST http://localhost:8000/v1/translate \
  -H "Content-Type: application/json" \
  -d '{"text":"Спасибо за заказ","source_lang":"ru","target_lang":"tk"}'
```

Распознавание речи:

```bash
curl -X POST http://localhost:8000/v1/stt \
  -F "audio=@clip.wav" \
  -F "language=ru" \
  -F "with_segments=true"
```

Озвучка:

```bash
curl -X POST http://localhost:8000/v1/tts \
  -H "Content-Type: application/json" \
  -d '{"text":"Salam, dünýä","language":"tk"}' \
  --output salam.wav
```

## Программный API

```python
from src.config import get_settings
from src.providers.openai_provider import OpenAIProvider
from src.providers.fallback_provider import FallbackProvider
from src.translator.translator_service import TranslatorService

settings = get_settings()
service = TranslatorService(
    primary=OpenAIProvider(settings),
    fallback=FallbackProvider(settings),
    latency_budget=settings.translator_latency_budget,
)
result = service.translate(text="Сколько стоит доставка?",
                           source_lang="ru", target_lang="tk")
print(result.text, result.quality.score, result.latency_seconds)
```

## Тесты

```bash
pytest -q
```

Все тесты используют фейковые провайдеры — для запуска не требуется ни
`OPENAI_API_KEY`, ни сетевой доступ, ни загрузка моделей.

## Безопасность

- Секреты (API-ключи) хранятся **только** в `.env` и переменных окружения.
- В коде, тестах, документации и истории git нет реальных ключей.
- `.env` исключён из коммита в `.gitignore`.

## Attribution & лицензии моделей

**Murat AI — licence-clean by default.** Каждый бэкенд, включённый
сразу из коробки, под permissive-лицензией (Apache 2.0 / MIT / Unlicense)
либо это коммерческий API, output которого принадлежит тебе.

| Компонент | Назначение | Лицензия | Коммерческое использование |
|---|---|---|---|
| **MADLAD-400** (`google/madlad400-3b-mt`) | перевод текста (дефолт) | **Apache 2.0** | ✅ да |
| **OpenAI Whisper** (локально) | STT | **MIT** | ✅ да |
| **OpenAI API** (опционально) | TTS / перевод для ru/tr/en | OpenAI ToS — output owned by user | ✅ да |
| **Streamlit, FastAPI, SQLAlchemy, transformers, torch, yt-dlp, langdetect, ffmpeg-python** | runtime | Apache / MIT / BSD / Unlicense | ✅ да |
| **ffmpeg** (slim Docker image) | аудио/видео | **LGPL 2.1+** (LGPL build, safe to redistribute) | ✅ да |

**Opt-in (CC-BY-NC, выключено по умолчанию):**

| Компонент | Активация | Лицензия |
|---|---|---|
| `facebook/nllb-200-distilled-600M` | `MURAT_AI_TRANSLATION_MODEL=facebook/nllb-200-distilled-600M` | CC-BY-NC 4.0 |
| `facebook/mms-tts-tuk-script_latin` (Turkmen TTS) | `MMS_TTS_TUK_ENABLED=true` | CC-BY-NC 4.0 |

Полная таблица, BibTeX-цитаты и политика коммерческого использования —
[`docs/attributions.md`](docs/attributions.md). Если хочешь Turkmen TTS
без NC-ограничения: подключи коммерческий API (`OPENAI_API_KEY`,
Google Cloud TTS, ElevenLabs, Azure Speech) — output этих API
принадлежит тебе. Архитектура provider-agnostic — это конфиг, не код.
