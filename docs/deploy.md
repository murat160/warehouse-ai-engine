# Deploy guide

`warehouse-ai-engine` — это обычное Python/Streamlit-приложение. Ниже два
готовых бесплатных пути в интернет. Авторизация делается **только тобой**:
у меня нет доступа к твоим аккаунтам, поэтому самой кнопки «Deploy» я
нажать не могу. Зато всё в репозитории уже подготовлено к 1-click деплою.

---

## Hugging Face Spaces (рекомендуется)

**Почему**: до 16 GB RAM на free, нет таймаута на холодный старт NLLB-200,
системный `ffmpeg` доступен из коробки.

1. Открой https://huggingface.co/spaces и нажми **Create new Space**.
2. Заполни:
   - Owner — твой логин.
   - Space name — например `warehouse-ai-translator`.
   - License — `apache-2.0`.
   - **SDK — `Streamlit`**.
   - Hardware — `CPU basic` (или больше, если есть кредиты).
   - Visibility — `Public` или `Private`.
3. Подключи репозиторий: вкладка **Files → Add → Upload files** или клонируй
   Space локально и скопируй содержимое:
   ```bash
   git clone https://huggingface.co/spaces/<your-username>/warehouse-ai-translator
   cp -r warehouse-ai-engine/* warehouse-ai-translator/
   cd warehouse-ai-translator
   git add .
   git commit -m "deploy: warehouse-ai-engine"
   git push
   ```
4. Открой вкладку **App** — Spaces сами подхватят `requirements.txt`,
   `packages.txt` и точку входа `app.py`. Первый запуск долгий
   (загрузка NLLB-200 ~1.2 ГБ + Whisper-small ~244 МБ), последующие —
   мгновенные.
5. Финальная ссылка будет такой:
   `https://<your-username>-warehouse-ai-translator.hf.space`.

### Переменные окружения (если нужны OpenAI / Postgres)

В Settings → **Variables and secrets** добавь:

| Имя              | Назначение                                        |
|------------------|---------------------------------------------------|
| `OPENAI_API_KEY` | (не обязательно) если хочешь использовать FastAPI-маршрут с OpenAI. |
| `DATABASE_URL`   | (не обязательно) `postgresql+psycopg://…` чтобы хранить словарь и TM в Postgres. |

> ⚠️ **Важно**: Hugging Face Spaces сбрасывает локальные файлы при
> рестарте. Чтобы пользовательский словарь и Translation Memory не
> теряли данные, обязательно укажи `DATABASE_URL` на внешний Postgres
> (Supabase / Neon / Railway — у всех есть бесплатные планы).

---

## Streamlit Community Cloud

**Почему**: проще всего связать с GitHub. Ограничение — ~1 GB RAM на free,
NLLB-200 + Whisper могут не уместиться, лучше выбирать Whisper-tiny.

1. https://share.streamlit.io → **Sign in with GitHub**.
2. Кнопка **New app**:
   - Repository — `murat160/warehouse-ai-engine`.
   - Branch — `main` (после слияния PR) **или** `issue-2-ai-architecture`.
   - Main file path — `app.py`.
3. Advanced settings → Python version `3.11`.
4. Если нужны секреты, добавь их в **Secrets** (TOML-формат):
   ```toml
   OPENAI_API_KEY = "sk-..."
   DATABASE_URL = "postgresql+psycopg://..."
   ```
5. **Deploy**. Через 5–10 минут получишь URL вида
   `https://<your-username>-warehouse-ai-engine-app-XXXX.streamlit.app/`.

> Streamlit Cloud также сбрасывает контейнер. Для долговременного
> хранения словаря и TM укажи `DATABASE_URL`.

---

## Self-hosted Docker

Минимальный `Dockerfile` (можно использовать на Render, Railway, fly.io,
Hetzner, любом VPS):

```dockerfile
FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . ./
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]
```

Запуск:

```bash
docker build -t warehouse-ai-translator .
docker run -p 8501:8501 -v $(pwd)/data:/app/data warehouse-ai-translator
```

---

## После деплоя — финальный шаг

1. Открой URL, проверь все три вкладки (`Translate`, `Audio / Video / URL`,
   `My Dictionary`).
2. Создай PR `issue-2-ai-architecture` → `main`:
   https://github.com/murat160/warehouse-ai-engine/compare/main...issue-2-ai-architecture
3. Добавь публичную ссылку в описание PR — это и будет «финальная рабочая
   интернет-ссылка» из требований задачи.
