#!/usr/bin/env bash
# Install the Murat AI nginx site config on the VPS.
#
# Usage:
#   sudo deploy/install-nginx.sh <DOMAIN>           # full HTTP + HTTPS config
#   sudo deploy/install-nginx.sh --bootstrap <DOMAIN>  # HTTP-only, before Certbot
#
# Examples:
#   sudo deploy/install-nginx.sh ai.murat-ai.com
#   sudo deploy/install-nginx.sh --bootstrap ai.ehlitrend.com
#
# The "--bootstrap" mode installs an HTTP-only site so Certbot can verify
# the domain. After Certbot succeeds, re-run the script WITHOUT
# --bootstrap to install the full HTTPS config.

set -euo pipefail

BOOTSTRAP=0
if [[ "${1:-}" == "--bootstrap" ]]; then
  BOOTSTRAP=1
  shift
fi

DOMAIN="${1:-}"
if [[ -z "$DOMAIN" ]]; then
  echo "Usage: $0 [--bootstrap] <DOMAIN>" >&2
  echo "  e.g. $0 ai.murat-ai.com" >&2
  exit 2
fi

if [[ "$EUID" -ne 0 ]]; then
  echo "This script must run as root (use sudo)." >&2
  exit 2
fi

# Resolve the directory containing this script so the relative path to
# the template works no matter where you run it from.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE="$SCRIPT_DIR/nginx/murat-ai.conf"
TARGET="/etc/nginx/sites-available/murat-ai.conf"
ENABLED="/etc/nginx/sites-enabled/murat-ai.conf"
ACME_ROOT="/var/www/certbot"

if [[ ! -f "$TEMPLATE" ]]; then
  echo "Template not found: $TEMPLATE" >&2
  exit 1
fi

mkdir -p "$ACME_ROOT"

if [[ "$BOOTSTRAP" -eq 1 ]]; then
  # Minimal HTTP-only config. Use this BEFORE Certbot has issued a cert.
  echo "Installing HTTP-only bootstrap config for $DOMAIN…"
  cat > "$TARGET" <<NGX
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN;

    location /.well-known/acme-challenge/ {
        root $ACME_ROOT;
    }

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 600s;
        client_max_body_size 500M;
    }
}
NGX
else
  # Full HTTPS config — assumes the certificate already exists at
  # /etc/letsencrypt/live/$DOMAIN/.
  echo "Installing full HTTPS config for $DOMAIN…"
  sed "s/__MURAT_AI_DOMAIN__/${DOMAIN//\//\\/}/g" "$TEMPLATE" > "$TARGET"
fi

ln -sf "$TARGET" "$ENABLED"

echo "Validating nginx config…"
nginx -t

echo "Reloading nginx…"
systemctl reload nginx

echo
echo "Done."
echo "Site config installed at: $TARGET"
echo "Enabled at:               $ENABLED"
echo
if [[ "$BOOTSTRAP" -eq 1 ]]; then
  cat <<NEXT
Next step — issue the SSL certificate:

  sudo certbot --nginx -d $DOMAIN --redirect \\
               --agree-tos -m you@your-domain.com -n

Then re-run this script WITHOUT --bootstrap to install the full HTTPS
config:

  sudo deploy/install-nginx.sh $DOMAIN
NEXT
else
  cat <<NEXT
Next step — verify it's reachable:

  curl -I https://$DOMAIN/_stcore/health     # should return 200 OK
  open https://$DOMAIN/                       # in your browser
NEXT
fi
