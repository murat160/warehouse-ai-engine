# Deploy guide

`warehouse-ai-engine` is built around **self-hosted deployment** on your own
VPS / server with your own domain. That's the supported, primary path. The
managed alternatives (Hugging Face Spaces, Streamlit Cloud) are documented
at the bottom for quick demos only — they reset their containers and are
not suitable for production.

---

## Primary: self-hosted on your VPS

End result: `https://ai.your-domain.com` → host nginx → Streamlit container
→ Postgres container.

* Pre-built Docker stack (`Dockerfile`, `docker-compose.yml`).
* Postgres 16 wired through `DATABASE_URL`.
* Persistent volumes for user data and model weights.
* nginx + Let's Encrypt SSL with WebSocket support and large-file uploads.

**Pointer:** the full step-by-step Ubuntu guide lives in
[`self-hosted-deploy.md`](self-hosted-deploy.md). Short version:

```bash
# on your VPS
cd /opt
sudo git clone https://github.com/murat160/warehouse-ai-engine.git
sudo chown -R $USER:$USER warehouse-ai-engine
cd warehouse-ai-engine
git checkout issue-2-ai-architecture

cp .env.production.example .env.production
chmod 600 .env.production
nano .env.production                       # set POSTGRES_PASSWORD, etc.

docker compose up -d --build

sudo cp deploy/nginx/translator.conf /etc/nginx/sites-available/translator.conf
sudo sed -i 's/ai\.example\.com/ai.your-domain.com/g' \
         /etc/nginx/sites-available/translator.conf
sudo ln -s /etc/nginx/sites-available/translator.conf /etc/nginx/sites-enabled/
sudo systemctl reload nginx

sudo certbot --nginx -d ai.your-domain.com --redirect \
             --agree-tos -m you@your-domain.com -n
```

Open `https://ai.your-domain.com` — you should see the Streamlit UI.

---

## Optional: Hugging Face Spaces (quick demo only)

Useful for a 5-minute share link. **Not** recommended for production:
Spaces wipe the container on every restart, so user-uploaded glossary,
Translation Memory, channels and Custom Voices vanish unless you point
`DATABASE_URL` at an external Postgres.

1. https://huggingface.co/spaces → **Create new Space**.
2. SDK = **Streamlit**, hardware = `CPU basic` (16 GB RAM).
3. Connect `murat160/warehouse-ai-engine`, branch `issue-2-ai-architecture`.
4. Add secrets in Settings → Variables: `OPENAI_API_KEY` (optional),
   `DATABASE_URL` (highly recommended — Supabase / Neon / Railway).
5. Final URL: `https://<your-username>-<space-name>.hf.space`.

---

## Optional: Streamlit Community Cloud (quick demo only)

Same caveat as Hugging Face: containers reset, RAM cap is ~1 GB which is
tight for NLLB-200 + Whisper-small.

1. https://share.streamlit.io → **New app**.
2. Repo = `murat160/warehouse-ai-engine`, branch = `issue-2-ai-architecture`,
   main file = `app.py`.
3. Secrets (TOML): `OPENAI_API_KEY`, `DATABASE_URL`.
4. Final URL: `https://<your-username>-warehouse-ai-engine-app-XXXX.streamlit.app/`.

---

## Why self-hosting is the recommended path

| Concern                       | Self-hosted VPS                        | HF Spaces / Streamlit Cloud |
|-------------------------------|----------------------------------------|------------------------------|
| Your own domain               | ✅ via host nginx + Certbot            | ❌ subdomain on theirs       |
| User data persists across restarts | ✅ Docker volumes + Postgres      | ❌ unless external Postgres  |
| Custom-voice audio samples kept | ✅ `./data/custom_voices/`           | ❌ wiped on rebuild          |
| Publishing inbox media        | ✅ `./data/publishing_inbox/`         | ❌ wiped on rebuild          |
| TLS                           | ✅ Let's Encrypt via Certbot          | ✅ managed                  |
| Resource limits               | only your VPS                          | platform-imposed             |
| Privacy of API keys           | only your VPS env                      | platform secrets store       |
