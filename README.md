# warehouse-ai-engine

AI-движок перевода, распознавания и озвучки речи для языков **ru, tk, tr, en**.
Главный приоритет — пара **ru ↔ tk** с литературным регистром в обоих языках.

Этот репозиторий — **отдельный AI-проект**. Он намеренно изолирован от
`warehouse-ecosystem` и не содержит кода клиентского, курьерского, продавца
или админ-панели.

## Два режима работы

В репозитории сосуществуют две независимые реализации:

1. **Cloud MVP (`app.py` + `src/cloud/`)** — рабочее end-to-end приложение
   на Streamlit. Перевод через **NLLB-200**, распознавание речи через
   **openai-whisper**, озвучка туркменского через **Meta MMS-TTS**. Работает
   без внешних API-ключей. Загружает медиа по ссылке (YouTube/TikTok через
   `yt-dlp`) или из загруженного файла.
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

## Деплой в интернет

Подробная пошаговая инструкция: [`docs/deploy.md`](docs/deploy.md).
Поддерживаются два бесплатных варианта:

1. **Hugging Face Spaces** (рекомендуется — больше RAM, нет таймаута на
   первый запуск NLLB) — `docs/deploy.md#hugging-face-spaces`.
2. **Streamlit Community Cloud** — `docs/deploy.md#streamlit-community-cloud`.

После деплоя у тебя появится публичный URL вида
`https://<имя>-warehouse-ai-engine.hf.space` или
`https://<имя>-warehouse-ai-engine.streamlit.app`.

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
