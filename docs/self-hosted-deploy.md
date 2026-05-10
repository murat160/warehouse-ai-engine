# Self-hosted deployment on your own VPS — Murat AI

This is the **primary** deployment path for **Murat AI** (the source code
ships in the `warehouse-ai-engine` repository). Your VPS, your domain,
your data. Everything is delivered as Docker containers, with host-side
nginx as the TLS reverse proxy.

End result:

> `https://<your-domain>` → nginx → Streamlit container → Postgres container.

The whole flow is **domain-agnostic** — the nginx config uses a placeholder
`__MURAT_AI_DOMAIN__` that the installer swaps for whatever domain you
own. Throughout this guide we use the shell variable `MURAT_AI_DOMAIN` so
you can copy-paste the commands once and they'll work for any choice.

## Choose your domain

Pick whichever DNS zone you control. The nginx config and SSL flow are
identical for all of them:

```bash
# Pick ONE and export it for the rest of the session.
export MURAT_AI_DOMAIN=ai.murat-ai.com        # — option 1
# export MURAT_AI_DOMAIN=ai.ehlitrend.com     # — option 2
# export MURAT_AI_DOMAIN=translator.your-domain.com  # — anything you own
```

> ⚠️ At the time of writing `ai.murat-ai.com` is not yet active — its
> DNS A record has not been created. **The site will only work after you
> create the A record (next section)** — see
> [`deploy/dns-records.md`](../deploy/dns-records.md) for the table.

## Server requirements

| Resource | Minimum | Comfortable |
|----------|---------|-------------|
| RAM      | 4 GB    | 8 GB        |
| CPU      | 2 vCPU  | 4 vCPU      |
| Disk     | 20 GB   | 40 GB       |
| OS       | Ubuntu 22.04 / 24.04 LTS | same |
| Network  | public IPv4, ports 80 + 443 open | same |

VPS used in this project: **`46.202.189.230`** (Ubuntu).

---

## 1. Create the DNS record

In your DNS provider (Cloudflare or Hostinger DNS) add a single **A**
record on the zone you chose:

| Type | Name (host) | Content (value)   | Proxy / Cloud                | TTL  |
|------|-------------|-------------------|------------------------------|------|
| A    | `ai`        | `46.202.189.230`  | DNS only (initial), then Proxied | 300  |

* **Name** is the subdomain part only — `ai`, not the full FQDN.
* **Content** is your VPS public IPv4 — `46.202.189.230`.
* **Proxy** (Cloudflare only): **DNS only / grey cloud** for the first
  Certbot run, then switch to **Proxied / orange cloud** afterwards.

Verify before continuing:

```bash
nslookup "$MURAT_AI_DOMAIN" 1.1.1.1
# Address must include 46.202.189.230 (or a Cloudflare anycast IP if Proxied).
```

Full DNS reference: [`deploy/dns-records.md`](../deploy/dns-records.md).

## 2. Install Docker on Ubuntu

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

sudo usermod -aG docker $USER          # log out + log back in afterwards
```

Verify: `docker compose version` and `docker run --rm hello-world`.

## 3. Clone the repository

```bash
sudo apt install -y git
cd /opt
sudo git clone https://github.com/murat160/warehouse-ai-engine.git
sudo chown -R $USER:$USER warehouse-ai-engine
cd warehouse-ai-engine
git checkout issue-2-ai-architecture
```

## 4. Create `.env.production`

```bash
cp .env.production.example .env.production
chmod 600 .env.production
nano .env.production
```

What you must set:

* `POSTGRES_PASSWORD` — long random string (`openssl rand -base64 32`).
* `OPENAI_API_KEY` — only if you want cloud TTS for ru/tr/en.

> ⚠️ `.env.production` is in `.gitignore`. Never commit it.

## 5. Start the Docker stack

```bash
docker compose up -d --build
docker compose ps                   # both services should be "healthy"
docker compose logs -f app
```

The first build takes ~5 minutes. The first request hits Whisper + NLLB-200
+ MMS-TTS, which are downloaded into the `hf_cache` volume (~2 GB) — give
it a couple of minutes for the cold start.

Smoke-test on the VPS itself:

```bash
curl -fsS http://127.0.0.1:8501/_stcore/health
# expected: ok
```

## 6. Install nginx + Certbot

```bash
sudo apt install -y nginx snapd
sudo snap install --classic certbot
sudo ln -sf /snap/bin/certbot /usr/bin/certbot
```

## 7. Bootstrap the nginx site (HTTP-only, before SSL)

The repo ships a domain-agnostic nginx template at
`deploy/nginx/murat-ai.conf` and a one-liner installer:

```bash
sudo deploy/install-nginx.sh --bootstrap "$MURAT_AI_DOMAIN"
```

This drops an HTTP-only site at
`/etc/nginx/sites-available/murat-ai.conf`, enables it, validates and
reloads nginx. Certbot needs this minimal HTTP block to verify your
domain via the `/.well-known/acme-challenge/` path.

Smoke-test:

```bash
curl -I "http://$MURAT_AI_DOMAIN/_stcore/health"
# expected: HTTP/1.1 200 OK   (proxied through nginx → Streamlit)
```

## 8. Issue the SSL certificate

```bash
sudo certbot --nginx -d "$MURAT_AI_DOMAIN" --redirect \
             --agree-tos -m you@your-domain.com -n
```

Certbot creates `/etc/letsencrypt/live/$MURAT_AI_DOMAIN/` with the cert,
edits the nginx config to add the HTTPS block and sets up automatic
renewal (`systemctl status snap.certbot.renew.timer`).

## 9. Switch nginx to the full HTTPS config

The bootstrap config from step 7 was minimal. Re-run the installer
**without** `--bootstrap` to drop in the production-grade config
(WebSocket support for Streamlit, 600 s timeouts, 500 MB upload cap):

```bash
sudo deploy/install-nginx.sh "$MURAT_AI_DOMAIN"
```

The script substitutes `__MURAT_AI_DOMAIN__` → your real domain, validates
the result and reloads nginx.

> 💡 **If you use Cloudflare** — switch the A record back to **Proxied**
> (orange cloud) now. Cloudflare will sit in front of nginx. Traffic
> path: client → Cloudflare → nginx (TLS) → Streamlit.

## 10. Verify it works

```bash
curl -I "https://$MURAT_AI_DOMAIN/_stcore/health"
# expected: HTTP/1.1 200 OK     (200 = healthy, 502 = container down)

# from your laptop:
open "https://$MURAT_AI_DOMAIN/"     # macOS
# or just open it in any browser
```

In the browser you should see the Murat AI Streamlit UI with a sidebar
language switcher (🇷🇺 / 🇹🇲 / 🇹🇷 / 🇬🇧).

A short functional test:

* Sidebar → switch language to **🇹🇲 Türkmençe** — the page re-renders.
* Tab **✨ Перевод** → переведи короткую русскую фразу на туркменский.
  Первый вызов ~30 с (загрузка моделей), потом быстро.
* Tab **🎬 Аудио / Видео / URL** → загрузи короткий ролик. Whisper сам
  определит язык, NLLB-200 переведёт, MMS-TTS озвучит на туркменском.

## 11. Operations

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
| Switch domain         | `export MURAT_AI_DOMAIN=new-domain.com && sudo deploy/install-nginx.sh "$MURAT_AI_DOMAIN" && sudo certbot --nginx -d "$MURAT_AI_DOMAIN" --redirect --agree-tos -m you@your-domain.com -n` |

## 12. Troubleshooting

> **`docker compose up` fails with `port is already allocated`**
> Something else listens on `8501`. Find it: `sudo ss -tlnp | grep 8501`.

> **`502 Bad Gateway` from nginx**
> The Streamlit container is down or still booting.
> ```bash
> docker compose ps
> docker compose logs -f app
> curl http://127.0.0.1:8501/_stcore/health
> ```

> **`curl: (35) … unable to get local issuer certificate` after Certbot**
> Certbot didn't manage to write the certificate. Inspect:
> `sudo certbot certificates` and `sudo journalctl -u nginx -n 50`.
> Typical cause: A record points to the wrong IP, or Cloudflare is
> Proxied during the first cert issuance — toggle to **DNS only** and
> re-run `certbot --nginx -d $MURAT_AI_DOMAIN`.

> **Streamlit UI loads but never updates / reconnects loop**
> WebSocket proxying is broken. Check that the installed
> `/etc/nginx/sites-available/murat-ai.conf` contains the `Upgrade` /
> `Connection "upgrade"` headers in the `/_stcore/stream` location.

> **First model download fails / OOM**
> NLLB-200 + Whisper + MMS-TTS together need ~3 GB RAM at load time.
> In the sidebar set **Whisper size** to `tiny` — far cheaper than `small`.

> **Postgres won't accept connections**
> Look for `pg_isready` in `docker compose logs db`. A wrong
> `POSTGRES_PASSWORD` between `.env.production` and an existing
> `postgres_data` volume blocks startup — wipe with
> `docker compose down -v` (⚠️ deletes data) and re-create.

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

* [ ] `chmod 600 .env.production` (already done in step 4).
* [ ] UFW: allow only 22 / 80 / 443 from the public network.
* [ ] Streamlit container exposes `127.0.0.1:8501` only — never bind to
      `0.0.0.0` on the public interface.
* [ ] Postgres is `expose:`d only on the docker network — never publish
      `5432` to the host.
* [ ] Set unique strong values for `POSTGRES_PASSWORD` and any provider
      API keys; rotate them periodically.
* [ ] Schedule a daily `cron` job that runs `pg_dump` and rotates `data/`.
