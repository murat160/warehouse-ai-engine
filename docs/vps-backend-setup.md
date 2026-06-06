# VPS backend setup для Murat AI Studio

Streamlit Cloud показывает только UI. Вся реальная обработка
(скачивание YouTube, Whisper ASR, MMS-TTS, ffmpeg рендер) делается на VPS.

## 1) Что нужно на VPS

- Ubuntu 22.04 / 24.04, минимум 4 vCPU + 8 ГБ RAM. Для 4K/8K — GPU.
- Python 3.11
- ffmpeg, git, build-essential
- Открытый порт (например 8000) или nginx + Certbot для HTTPS

## 2) Установка

```bash
sudo apt update && sudo apt install -y python3.11 python3.11-venv ffmpeg git build-essential
git clone https://github.com/murat160/warehouse-ai-engine.git
cd warehouse-ai-engine
git checkout issue-2-ai-architecture
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements-full.txt
```

## 3) Запуск FastAPI backend

```bash
export MURAT_AI_OUT=/var/lib/murat-ai/out
export MURAT_AI_CORS_ORIGINS="*"
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 2
```

Проверка:
```bash
curl http://localhost:8000/healthz
# → {"ok": true, "service": "murat-ai-studio-backend", "version": "1.0.0"}
```

## 4) systemd unit (production)

`/etc/systemd/system/murat-ai-backend.service`:
```ini
[Unit]
Description=Murat AI Studio backend
After=network.target

[Service]
Type=simple
User=murat
WorkingDirectory=/opt/warehouse-ai-engine
Environment="MURAT_AI_OUT=/var/lib/murat-ai/out"
Environment="MURAT_AI_CORS_ORIGINS=*"
ExecStart=/opt/warehouse-ai-engine/.venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 2
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now murat-ai-backend
sudo systemctl status murat-ai-backend
```

## 5) Nginx + HTTPS (Cloudflare proxy off на момент Certbot)

```nginx
server {
    server_name ai.your-domain.com;
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 600;
        client_max_body_size 500M;
    }
}
```

```bash
sudo certbot --nginx -d ai.your-domain.com
```

## 6) Подключение к Streamlit Cloud

В кабинете Streamlit Cloud → app → `⋮` → **Settings** → **Secrets**:

```toml
BACKEND_URL = "https://ai.your-domain.com"
```

Reboot app. Сверху страницы появится зелёный pill «VPS backend подключён».

## 7) Как проверить (end-to-end)

1. Открой Streamlit Cloud app в браузере.
2. Сверху — зелёная плашка `BUILD: studio-backend-pipeline / ... / one-button`
3. Вставь YouTube URL → нажми **Показать по ссылке** → должны появиться title/duration.
4. Выбери качество (например 1080p Full HD), формат 9:16.
5. Нажми большую кнопку **✨ Создать готовое видео на туркменском**.
6. Появится блок `⏳ Прогресс обработки на VPS` со стадиями:
   `queued → downloading → extracting_audio → transcribing → detecting_speakers → analyzing_emotions → translating → quality_check → tts → syncing → rendering → done`
7. Когда `done` — появится ссылка **⬇ Скачать MP4**.

## 8) Логи

```bash
journalctl -u murat-ai-backend -f
ls -la /var/lib/murat-ai/out/  # каждый job — своя папка
```
