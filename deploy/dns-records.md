# DNS records for Murat AI

Murat AI is **domain-agnostic** — point any subdomain you own at the VPS
and the same code, same nginx config and same SSL flow work. The two
domains discussed in the project history are:

* `ai.murat-ai.com`
* `ai.ehlitrend.com`

Either one works. Pick whichever DNS zone you actually own; the
`__MURAT_AI_DOMAIN__` placeholder in `deploy/nginx/murat-ai.conf` is
substituted at install time by `deploy/install-nginx.sh`.

## Required record (one DNS provider, one record, that's it)

Add a single **A** record on the DNS provider that hosts the chosen zone:

| Type | Name (host)              | Content (value)   | Proxy / Cloud   | TTL  |
|------|--------------------------|-------------------|-----------------|------|
| A    | `ai`                     | `46.202.189.230`  | see note below  | 300  |

* **Name** is the *subdomain part only*. In Cloudflare's zone `murat-ai.com`
  put `ai` (NOT the full FQDN). Cloudflare/Hostinger usually shorten this
  in the UI; saving `ai` produces `ai.murat-ai.com`.
* **Content** is the public IPv4 of your VPS — `46.202.189.230`.
* **Proxy** column:
  * **Cloudflare**: orange cloud (Proxied) is fine for the production UI
    and gives you their free WAF + DDoS shielding. SSL termination by
    Cloudflare + nginx Full / Full Strict on origin.
    For the **first-time Certbot HTTP-01 verification** you must temporarily
    set this record to **DNS only** (grey cloud) — Certbot needs to reach
    your origin directly on port 80. Switch back to Proxied after the
    certificate is issued.
  * **Hostinger / other registrars**: not applicable — no proxy mode,
    just save the A record.
* **TTL**: 300 s (5 min) so changes propagate quickly while you set
  things up. Bump to 3600 once stable.

## Concrete examples

### Option 1 — `ai.murat-ai.com`

Cloudflare zone `murat-ai.com` → DNS → **Add record**:

| Type | Name | Content          | Proxy             | TTL |
|------|------|------------------|-------------------|-----|
| A    | `ai` | `46.202.189.230` | DNS only (initial), then Proxied | 300 |

→ Resolves to `ai.murat-ai.com`.

### Option 2 — `ai.ehlitrend.com`

Cloudflare zone `ehlitrend.com` → DNS → **Add record**:

| Type | Name | Content          | Proxy             | TTL |
|------|------|------------------|-------------------|-----|
| A    | `ai` | `46.202.189.230` | DNS only (initial), then Proxied | 300 |

→ Resolves to `ai.ehlitrend.com`.

### Other valid subdomains

Same pattern — just change the `Name`:

* `translator` → `translator.murat-ai.com`
* `voice` → `voice.murat-ai.com`
* `app` → `app.ehlitrend.com`

## Verifying the record from anywhere

```bash
# from your laptop / VPS
nslookup ai.murat-ai.com 1.1.1.1
# Address(es) should include 46.202.189.230
# (or one of Cloudflare's 188.114.x.x anycast IPs if Proxied is on)

# alternative
dig +short ai.murat-ai.com @1.1.1.1
```

If the answer is empty → record not saved or the zone uses different
nameservers. If the answer is a Hostinger parking IP → A record was
overwritten by a default parking record, edit / delete it.

## After DNS is up

DNS is the only step that involves your registrar. Everything else
happens on the VPS — see `docs/self-hosted-deploy.md` for the full
sequence:

1. `docker compose up -d --build`
2. `sudo deploy/install-nginx.sh --bootstrap ai.your-domain.com`
3. `sudo certbot --nginx -d ai.your-domain.com --redirect …`
4. `sudo deploy/install-nginx.sh ai.your-domain.com`
5. open `https://ai.your-domain.com/` in a browser

## What about the apex (root) domain?

You don't need it for Murat AI — the app lives on a subdomain. Leave
`murat-ai.com` / `ehlitrend.com` apex records pointing wherever they
already point (parking page, marketing site, etc.).
