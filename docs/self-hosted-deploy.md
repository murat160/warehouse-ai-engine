# Self-hosted deployment on your own VPS

This is the **primary** deployment path for `warehouse-ai-engine`: your VPS,
your domain, your data. Everything is delivered as Docker containers, with
host-side nginx as the TLS reverse proxy. End result:

> `https://ai.your-domain.com` → nginx → Streamlit container → Postgres container.

## What you get

* Streamlit app on Python 3.11, GPU-less torch (CPU wheel) — fits a 4 GB VPS.
* Postgres 16 (Alpine) for glossary / TM / channels / Custom Voices /
  publishing packages — already wired through `DATABASE_URL`.
* Persistent named volumes:
  * `./data` — user-uploaded audio samples, publishing inbox, ffmpeg
    artefacts. **Safe to back up.**
  * `hf_cache` — NLLB-200 / Whisper / MMS-TTS weights (~2 GB on first run).
* nginx config with proper Streamlit WebSocket support, large-file uploads
  (500 MB), long ASR/TTS timeouts (10 min) and Let's Encrypt SSL.

## Server requirements

| Resource | Minimum | Comfortable |
|----------|---------|-------------|
| RAM      | 4 GB    | 8 GB        |
| CPU      | 2 vCPU  | 4 vCPU      |
| Disk     | 20 GB   | 40 GB       |
| OS       | Ubuntu 22.04 / 24.04 LTS | same |
| Network  | public IPv4, ports 80 + 443 open | same |

You also need a registered domain pointing to the VPS (an `A` record like
`ai → <VPS_IP>`).

---

## 1. Install Docker on Ubuntu

```bash
sudo apt update
sudo apt install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
        -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

echo "deb [arch=$(dpkg --print-architecture) \
signed-by=/etc/apt/keyrings/docker.asc] \
https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io \
                    docker-buildx-plugin docker-compose-plugin

# Run docker without sudo (re-login afterwards):
sudo usermod -aG docker $USER
```

Verify: `docker compose version` and `docker run --rm hello-world`.

## 2. Clone the repository

```bash
sudo apt install -y git
cd /opt
sudo git clone https://github.com/murat160/warehouse-ai-engine.git
sudo chown -R $USER:$USER warehouse-ai-engine
cd warehouse-ai-engine
git checkout issue-2-ai-architecture
```

## 3. Create `.env.production`

```bash
cp .env.production.example .env.production
chmod 600 .env.production
nano .env.production
```

What you must set:

* `POSTGRES_PASSWORD` — long random string (`openssl rand -base64 32`).
* `OPENAI_API_KEY` — only if you want cloud TTS for ru/tr/en or want the
  FastAPI provider chain. Turkmen voice and offline NLLB translation work
  without it.

> ⚠️ `.env.production` is in `.gitignore`. Never commit it.

## 4. Start the stack

```bash
docker compose up -d --build
docker compose ps      # both services should be "healthy"
docker compose logs -f app
```

The first build takes ~5 minutes. The first request hits Whisper + NLLB-200
+ MMS-TTS, which are downloaded into the `hf_cache` volume (~2 GB) — give
it a couple of minutes for the cold start.

Quick smoke-test the app from the VPS itself:

```bash
curl -fsS http://127.0.0.1:8501/_stcore/health
# expected: ok
```

## 5. Install nginx + Certbot on the host

```bash
sudo apt install -y nginx
sudo apt install -y snapd
sudo snap install --classic certbot
sudo ln -s /snap/bin/certbot /usr/bin/certbot
```

Drop the bundled site config:

```bash
sudo cp deploy/nginx/translator.conf /etc/nginx/sites-available/translator.conf
sudo ln -s /etc/nginx/sites-available/translator.conf \
           /etc/nginx/sites-enabled/translator.conf

# Replace the placeholder domain.
sudo sed -i 's/ai\.example\.com/ai.your-domain.com/g' \
        /etc/nginx/sites-available/translator.conf
```

Before Certbot has issued a certificate, comment out the `listen 443` block
**or** skip the `nginx -t` for now. Easier path: bootstrap with HTTP only
(see step 6), then switch on TLS automatically.

```bash
# Temporary HTTP-only setup before Certbot
sudo tee /etc/nginx/sites-available/translator.conf > /dev/null <<'NGX'
server {
    listen 80;
    server_name ai.your-domain.com;
    location /.well-known/acme-challenge/ { root /var/www/certbot; }
    location / { proxy_pass http://127.0.0.1:8501; }
}
NGX
sudo mkdir -p /var/www/certbot
sudo nginx -t && sudo systemctl reload nginx
```

## 6. Point the domain at the VPS

In your DNS provider create:

```
Type  Host  Value           TTL
A     ai    <VPS public IP> 300
```

Wait until `dig +short ai.your-domain.com` returns the right IP. With a 300
TTL this is usually under 5 minutes.

## 7. Issue the SSL certificate

```bash
sudo certbot --nginx -d ai.your-domain.com \
             --redirect --agree-tos --email you@your-domain.com -n
```

Certbot edits the nginx config in place to add the HTTPS server block and
sets up a renewal timer (`systemctl status snap.certbot.renew.timer`).

Now replace the temporary nginx config with the full one bundled in the
repo (it has WebSocket + long timeouts + large uploads tuned for Streamlit):

```bash
sudo cp deploy/nginx/translator.conf /etc/nginx/sites-available/translator.conf
sudo sed -i 's/ai\.example\.com/ai.your-domain.com/g' \
        /etc/nginx/sites-available/translator.conf
sudo nginx -t && sudo systemctl reload nginx
```

## 8. Verify it works

* `https://ai.your-domain.com` opens the Streamlit UI in the browser.
* Switch the UI language in the sidebar (🇷🇺 / 🇹🇲 / 🇹🇷 / 🇬🇧) — the page
  re-renders on the chosen language.
* Translate a short Russian phrase to Turkmen — first call takes ~30 s
  (model download), subsequent calls are fast.
* Upload a short video to the **🎬 Аудио / Видео / URL** tab and run it.
* Health endpoint: `curl https://ai.your-domain.com/_stcore/health` → `ok`.

## 9. Operations

| Action                | Command                                              |
|-----------------------|------------------------------------------------------|
| Pull updates          | `git pull origin issue-2-ai-architecture && docker compose up -d --build app` |
| Restart only the app  | `docker compose restart app`                         |
| Stop the stack        | `docker compose down`                                |
| Logs (live)           | `docker compose logs -f app`                         |
| Database shell        | `docker compose exec db psql -U $POSTGRES_USER $POSTGRES_DB` |
| Backup the data dir   | `tar czf data-$(date +%F).tar.gz data/`              |
| Backup Postgres       | `docker compose exec db pg_dump -U $POSTGRES_USER $POSTGRES_DB > db-$(date +%F).sql` |
| Renew SSL manually    | `sudo certbot renew && sudo systemctl reload nginx`  |

## 10. Troubleshooting

> **`docker compose up` fails with `port is already allocated`**
> Something else listens on `8501`. Find it: `sudo ss -tlnp | grep 8501`.

> **`502 Bad Gateway` from nginx**
> The Streamlit container is down or still booting.
> ```bash
> docker compose ps
> docker compose logs -f app
> curl http://127.0.0.1:8501/_stcore/health
> ```

> **Streamlit UI loads but never updates / reconnects loop**
> WebSocket proxying is broken. Make sure
> `/etc/nginx/sites-available/translator.conf` has the `Upgrade` and
> `Connection "upgrade"` headers AND a high `proxy_read_timeout` for
> `/_stcore/stream`.

> **First model download fails / OOM**
> NLLB-200 + Whisper + MMS-TTS together need ~3 GB RAM at load time.
> Pre-download Whisper-tiny instead by setting `Whisper size` to `tiny`
> in the sidebar — far cheaper than `small`.

> **Postgres won't accept connections**
> The DB container starts last. Look for `pg_isready` in
> `docker compose logs db`. A wrong `POSTGRES_PASSWORD` between
> `.env.production` and an existing `postgres_data` volume will block
> startup — wipe with `docker compose down -v` (⚠️ deletes data) and
> re-create.

> **Need to move to a bigger box**
> Stop the stack, copy `./data/` and the named volumes
> (`docker volume ls` → `warehouse-ai-engine_postgres_data`,
> `…_hf_cache`) to the new host, restart. No code changes.

## Where data lives

```
/opt/warehouse-ai-engine/
├── .env.production              # secrets — chmod 600, DO NOT commit
├── data/                        # user glossary samples, publishing inbox,
│                                # ffmpeg artefacts (host-mounted)
└── docker volumes:
    ├── postgres_data            # Postgres tables (channels, glossary, TM,
    │                            # custom voices, publishing packages)
    └── hf_cache                 # NLLB-200, Whisper, MMS-TTS weights
```

`./data` lives on the host so backups are trivial. The two named docker
volumes are managed by docker but easy to inspect:

```bash
docker volume inspect warehouse-ai-engine_postgres_data
docker volume inspect warehouse-ai-engine_hf_cache
```

## Hardening checklist

* [ ] `chmod 600 .env.production` (already done in step 3).
* [ ] UFW: allow only 22 / 80 / 443 from the public network.
* [ ] Streamlit container exposes `127.0.0.1:8501` only — never bind to
      `0.0.0.0` on the public interface.
* [ ] Postgres is `expose:`d only on the docker network — never publish
      `5432` to the host.
* [ ] Set unique strong values for `POSTGRES_PASSWORD` and any provider
      API keys; rotate them periodically.
* [ ] Schedule a daily `cron` job that runs `pg_dump` and rotates `data/`.
