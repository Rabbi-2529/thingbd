#!/usr/bin/env bash
# Serve Thingbd on a domain with HTTPS (Let's Encrypt).
#
#   sudo bash enable_domain.sh thingbd.com [email-for-letsencrypt]
#
# - main site: https://<domain>;  www, plain http and the bare IP redirect there
# - reuses an existing certificate in /etc/letsencrypt/live/<domain>/, or requests one
# - other nginx sites for this domain are archived to /root/pre-domain-backup-<date>/ and disabled
# - updates /srv/thingbd/.env (ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS, USE_HTTPS=true)
set -euo pipefail

DOMAIN="${1:-}"
EMAIL="${2:-}"
BASE=/srv/thingbd
ENV_FILE="$BASE/.env"
STATIC="$BASE/static"
MEDIA="$BASE/media"
SITE=/etc/nginx/sites-available/thingbd
STAMP="$(date +%Y%m%d-%H%M%S)"

say()  { printf '\n\033[1;35m==> %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33m!!  %s\033[0m\n' "$*"; }
die()  { printf '\033[1;31mXX  %s\033[0m\n' "$*" >&2; exit 1; }

[[ $EUID -eq 0 ]] || die "Run as root."
[[ -n "$DOMAIN" ]] || die "Usage: sudo bash $0 thingbd.com [email]"
DOMAIN="${DOMAIN#https://}"; DOMAIN="${DOMAIN#http://}"; DOMAIN="${DOMAIN%%/*}"; DOMAIN="${DOMAIN#www.}"
WWW="www.$DOMAIN"
[[ -f "$ENV_FILE" ]] || die "$ENV_FILE not found. Run setup_server.sh first."
SERVER_IP="$(curl -4 -s --max-time 5 https://ifconfig.me || hostname -I | awk '{print $1}')"

# ---------------------------------------------------------------------------
say "1/6 Checking DNS"
for host in "$DOMAIN" "$WWW"; do
  resolved="$(getent ahostsv4 "$host" | awk 'NR==1{print $1}' || true)"
  if [[ "$resolved" == "$SERVER_IP" ]]; then echo "   $host -> $resolved ✓"
  else die "$host points to '${resolved:-nothing}', not this server ($SERVER_IP). Fix the DNS A record and try again."; fi
done

# ---------------------------------------------------------------------------
say "2/6 Disabling other nginx sites for $DOMAIN (archived, not deleted)"
OLD="/root/pre-domain-backup-$STAMP"
shopt -s nullglob
for f in /etc/nginx/sites-enabled/* /etc/nginx/conf.d/*.conf; do
  real="$(readlink -f "$f")"
  [[ "$real" == "$SITE" ]] && continue
  if grep -qE "server_name[^;]*\b($DOMAIN|$WWW)\b" "$real" 2>/dev/null || grep -q "default_server" "$real" 2>/dev/null; then
    mkdir -p "$OLD"
    cp -a "$real" "$OLD/"
    rm -f "$f"
    echo "   disabled $f (copy in $OLD)"
  fi
done
shopt -u nullglob

# ---------------------------------------------------------------------------
say "3/6 Certificate"
apt-get install -y -qq certbot python3-certbot-nginx >/dev/null
CERT_DIR="/etc/letsencrypt/live/$DOMAIN"
WEBROOT=/var/www/letsencrypt
mkdir -p "$WEBROOT/.well-known/acme-challenge"
covers_both() { openssl x509 -in "$CERT_DIR/fullchain.pem" -noout -ext subjectAltName 2>/dev/null | grep -q "DNS:$WWW"; }
if [[ -f "$CERT_DIR/fullchain.pem" ]] && covers_both; then
  echo "   using existing certificate: $(openssl x509 -in "$CERT_DIR/fullchain.pem" -noout -enddate)"
else
  echo "   requesting a certificate for $DOMAIN and $WWW"
  # temporary http-only config so Let's Encrypt can reach the challenge files
  cat > "$SITE" <<EOF
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name $DOMAIN $WWW _;
    location ^~ /.well-known/acme-challenge/ { root $WEBROOT; default_type text/plain; }
    location / { return 404; }
}
EOF
  ln -sf "$SITE" /etc/nginx/sites-enabled/thingbd
  nginx -t && systemctl reload nginx
  if [[ -n "$EMAIL" ]]; then ACCOUNT=(-m "$EMAIL"); else ACCOUNT=(--register-unsafely-without-email); fi
  certbot certonly --webroot -w "$WEBROOT" -d "$DOMAIN" -d "$WWW" --agree-tos --non-interactive "${ACCOUNT[@]}" \
    --cert-name "$DOMAIN"
fi
SSL_OPTS=""
[[ -f /etc/letsencrypt/options-ssl-nginx.conf ]] && SSL_OPTS="include /etc/letsencrypt/options-ssl-nginx.conf;"
DHPARAM=""
[[ -f /etc/letsencrypt/ssl-dhparams.pem ]] && DHPARAM="ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;"

# ---------------------------------------------------------------------------
say "4/6 Nginx: https://$DOMAIN"
cat > "$SITE" <<EOF
# Managed by deploy/enable_domain.sh — https://$DOMAIN
upstream thingbd_app { server unix:/run/thingbd/gunicorn.sock; }

# Plain HTTP (domain, www and bare IP): certificate renewals, then redirect to HTTPS.
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name $DOMAIN $WWW $SERVER_IP _;
    location ^~ /.well-known/acme-challenge/ { root $WEBROOT; default_type text/plain; }
    location / { return 301 https://$DOMAIN\$request_uri; }
}

# https://www -> https://domain
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name $WWW;
    ssl_certificate     $CERT_DIR/fullchain.pem;
    ssl_certificate_key $CERT_DIR/privkey.pem;
    $SSL_OPTS
    $DHPARAM
    return 301 https://$DOMAIN\$request_uri;
}

# The website
server {
    listen 443 ssl http2 default_server;
    listen [::]:443 ssl http2 default_server;
    server_name $DOMAIN;
    ssl_certificate     $CERT_DIR/fullchain.pem;
    ssl_certificate_key $CERT_DIR/privkey.pem;
    $SSL_OPTS
    $DHPARAM

    client_max_body_size 12M;
    add_header X-Content-Type-Options nosniff always;
    add_header Referrer-Policy strict-origin-when-cross-origin always;

    location /static/ { alias $STATIC/; expires 30d; access_log off; }
    location /media/  { alias $MEDIA/;  expires 7d; add_header X-Content-Type-Options nosniff; }

    location / {
        proxy_pass http://thingbd_app;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_read_timeout 60s;
    }
}
EOF
ln -sf "$SITE" /etc/nginx/sites-enabled/thingbd
nginx -t
systemctl reload nginx

# Renewals: use the webroot above and reload nginx afterwards.
RENEW="/etc/letsencrypt/renewal/$DOMAIN.conf"
if [[ -f "$RENEW" ]]; then
  cp -a "$RENEW" "$RENEW.bak-$STAMP"
  sed -i -E "s#^authenticator = .*#authenticator = webroot#; /^installer = /d; /^webroot_path = /d; /^\[\[webroot_map\]\]/,\$d" "$RENEW"
  sed -i "/^\[renewalparams\]/a webroot_path = $WEBROOT," "$RENEW"
  printf '[[webroot_map]]\n%s = %s\n%s = %s\n' "$DOMAIN" "$WEBROOT" "$WWW" "$WEBROOT" >> "$RENEW"
fi
mkdir -p /etc/letsencrypt/renewal-hooks/deploy
printf '#!/bin/sh\nsystemctl reload nginx\n' > /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh
chmod 755 /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh

# ---------------------------------------------------------------------------
say "5/6 Django settings (.env)"
cp -a "$ENV_FILE" "$ENV_FILE.bak-$STAMP"
set_env() {  # set_env KEY VALUE  — replace or append
  if grep -q "^$1=" "$ENV_FILE"; then sed -i "s#^$1=.*#$1=$2#" "$ENV_FILE"; else echo "$1=$2" >> "$ENV_FILE"; fi
}
set_env ALLOWED_HOSTS "$DOMAIN,$WWW,$SERVER_IP,localhost,127.0.0.1"
set_env CSRF_TRUSTED_ORIGINS "https://$DOMAIN,https://$WWW"
set_env USE_HTTPS true
echo "$DOMAIN" > "$BASE/.domain"
systemctl restart thingbd
sleep 3

# ---------------------------------------------------------------------------
say "6/6 Checking"
ok=true
check() {  # check URL EXPECTED_CODE [EXPECTED_LOCATION]
  local out code loc
  out="$(curl -s -o /dev/null -w '%{http_code} %{redirect_url}' --max-time 15 "$1")"; code="${out%% *}"; loc="${out#* }"
  if [[ "$code" == "$2" && ( -z "${3:-}" || "$loc" == "$3" ) ]]; then echo "   ✓ $1 -> $code ${loc}"
  else echo "   ✗ $1 -> $code ${loc} (expected $2 ${3:-})"; ok=false; fi
}
check "https://$DOMAIN/" 200
check "https://$DOMAIN/dashboard/login/" 200
check "https://$WWW/" 301 "https://$DOMAIN/"
check "http://$DOMAIN/" 301 "https://$DOMAIN/"
check "http://$SERVER_IP/" 301 "https://$DOMAIN/"
certbot renew --dry-run --cert-name "$DOMAIN" >/dev/null 2>&1 && echo "   ✓ automatic certificate renewal works" \
  || { echo "   ✗ certbot renew --dry-run failed (run it to see why)"; ok=false; }

if $ok; then
  say "Done! Your site is live at https://$DOMAIN"
  echo "   Dashboard: https://$DOMAIN/dashboard/"
else
  warn "Some checks failed (see above). Logs: journalctl -u thingbd -n 50   and   tail /var/log/nginx/error.log"
  exit 1
fi
