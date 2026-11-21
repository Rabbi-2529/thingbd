#!/usr/bin/env bash
# Install / update MediPOS (https://github.com/Rabbi-2529/medipos) next to Thingbd on the same server.
#
#   sudo bash install_medipos.sh [domain] [port]        defaults: pharmacy.thingbd.com 8001
#   SEED_DEMO=no sudo bash install_medipos.sh ...        skip the demo pharmacies (seed_demo)
#
# - app in /srv/medipos (code in app/, SQLite database in data/, backups in backups/)
# - Gunicorn listens on 127.0.0.1:<port> only; nginx serves https://<domain> and forwards to it
# - its own Let's Encrypt certificate; Thingbd's nginx config is not touched
# - safe to run again: updates the code, keeps the database, uploads and .env
set -euo pipefail

DOMAIN="${1:-pharmacy.thingbd.com}"
PORT="${2:-8001}"
REPO_URL="https://github.com/Rabbi-2529/medipos.git"
BRANCH="main"
NAME=medipos
BASE=/srv/medipos
APP="$BASE/app"
VENV="$BASE/venv"
DATA="$BASE/data"
BACKUPS="$BASE/backups"
ENV_FILE="$BASE/.env"
WEBROOT=/var/www/letsencrypt
SITE=/etc/nginx/sites-available/medipos

say()  { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33m!!  %s\033[0m\n' "$*"; }
die()  { printf '\033[1;31mXX  %s\033[0m\n' "$*" >&2; exit 1; }

[[ $EUID -eq 0 ]] || die "Run as root."
[[ "$PORT" =~ ^[0-9]+$ ]] || die "Port must be a number."
SERVER_IP="$(curl -4 -s --max-time 5 https://ifconfig.me || hostname -I | awk '{print $1}')"

# ---------------------------------------------------------------------------
say "1/8 Checks"
resolved="$(getent ahostsv4 "$DOMAIN" | awk 'NR==1{print $1}' || true)"
[[ "$resolved" == "$SERVER_IP" ]] || die "$DOMAIN points to '${resolved:-nothing}', not this server ($SERVER_IP). Add a DNS A record first."
echo "   $DOMAIN -> $resolved ✓"
if ss -ltnH "sport = :$PORT" | grep -q . && ! systemctl is-active --quiet "$NAME"; then
  ss -ltnp "sport = :$PORT"
  die "Port $PORT is already used by another program (above). Run again with another port: sudo bash $0 $DOMAIN 8002"
fi
echo "   port $PORT is free for MediPOS ✓"

# ---------------------------------------------------------------------------
say "2/8 System packages"
APT_LOCKS=(/var/lib/dpkg/lock-frontend /var/lib/dpkg/lock /var/lib/apt/lists/lock)
waited=0
while fuser "${APT_LOCKS[@]}" >/dev/null 2>&1; do
  (( waited % 60 == 0 )) && echo "   Ubuntu is installing updates in the background, waiting... ($((waited / 60)) min)"
  (( waited >= 1800 )) && die "apt is still busy after 30 minutes."
  sleep 10; waited=$((waited + 10))
done
export DEBIAN_FRONTEND=noninteractive
apt-get -o DPkg::Lock::Timeout=600 install -y -qq python3 python3-venv python3-dev build-essential git nginx \
  sqlite3 gettext certbot libjpeg-dev zlib1g-dev >/dev/null
echo "   done"

# ---------------------------------------------------------------------------
say "3/8 User, folders and code"
id "$NAME" >/dev/null 2>&1 || useradd --system --home "$BASE" --shell /usr/sbin/nologin "$NAME"
mkdir -p "$BASE" "$DATA" "$BACKUPS"
git config --global --add safe.directory "$APP" 2>/dev/null || true
FIRST_INSTALL=false
if [[ -d "$APP/.git" ]]; then
  git -C "$APP" fetch --quiet origin "$BRANCH"
  git -C "$APP" reset --hard --quiet "origin/$BRANCH"     # keeps untracked media/ and staticfiles/
else
  FIRST_INSTALL=true
  git clone --quiet --branch "$BRANCH" "$REPO_URL" "$APP"
fi
git -C "$APP" log -1 --format='   code at %h — %s'
mkdir -p "$APP/media"

# ---------------------------------------------------------------------------
say "4/8 Python environment"
[[ -x "$VENV/bin/python" ]] || python3 -m venv "$VENV"
"$VENV/bin/pip" install --quiet --upgrade pip wheel
"$VENV/bin/pip" install --quiet -r "$APP/requirements.txt" gunicorn
echo "   done"

# ---------------------------------------------------------------------------
say "5/8 Settings (.env)"
if [[ ! -f "$ENV_FILE" ]]; then
  SECRET="$("$VENV/bin/python" -c 'import secrets; print(secrets.token_urlsafe(50))')"
  cat > "$ENV_FILE" <<EOF
# MediPOS production settings — keep this file private.
DJANGO_SETTINGS_MODULE=config.settings.prod
SECRET_KEY=$SECRET
DEBUG=False
ALLOWED_HOSTS=$DOMAIN,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://$DOMAIN
DATABASE_URL=sqlite:///$DATA/db.sqlite3
SITE_URL=https://$DOMAIN
# nginx passes the visitor's address in X-Forwarded-For (used by staff self check-in)
BEHIND_PROXY=True
# nginx serves /media/
SERVE_MEDIA=False

TRIAL_DAYS=14
SUBSCRIPTION_GRACE_DAYS=3
SUBSCRIPTION_PAYMENT_INSTRUCTIONS=Contact ThingBD support to renew or upgrade your subscription.

# Messages are queued and sent every minute by cron (send_messages).
MESSAGES_SEND_NOW=False
DEFAULT_FROM_EMAIL=MediPOS <no-reply@thingbd.com>
# Mail server for emails (empty = emails are only logged)
EMAIL_HOST=
EMAIL_PORT=587
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
EMAIL_USE_TLS=True
# SMS gateway (empty URL = SMS are only logged)
SMS_GATEWAY_URL=
SMS_GATEWAY_METHOD=GET
SMS_GATEWAY_API_KEY=
SMS_GATEWAY_SENDER=
SMS_GATEWAY_SUCCESS_TEXT=
SUPPORT_AI_API_KEY=
EOF
  echo "   created $ENV_FILE"
else
  echo "   keeping existing $ENV_FILE"
fi
ln -sf "$ENV_FILE" "$APP/.env"
chown -R "$NAME:$NAME" "$BASE"
chown root:"$NAME" "$ENV_FILE"
chmod 640 "$ENV_FILE"
chmod 750 "$BASE"
usermod -aG "$NAME" www-data   # nginx reads static and media files

cat > /usr/local/bin/medipos-manage <<EOF
#!/usr/bin/env bash
# Run a MediPOS manage.py command as the app user, e.g.  medipos-manage createsuperuser
cd "$APP" && exec sudo -u $NAME "$VENV/bin/python" manage.py "\$@"
EOF
chmod 755 /usr/local/bin/medipos-manage

# ---------------------------------------------------------------------------
say "6/8 Database and static files"
medipos-manage migrate --noinput
medipos-manage collectstatic --noinput --verbosity 0
medipos-manage check --deploy --fail-level ERROR >/dev/null && echo "   deploy checks passed"

# Demo data: platform admin + 3 demo pharmacies, ONCE, and BEFORE the DGDA catalog.
# seed_demo gives the demo pharmacy every medicine in the catalog: with the 28-row sample that
# takes seconds, with the full DGDA list (~41,000 rows) it takes hours. So: demo first, catalog after.
# The example password in the MediPOS repo is public, so a random one is stored in .env.
if ! grep -q '^DEMO_PASSWORD=.\+' "$ENV_FILE"; then
  sed -i '/^DEMO_PASSWORD=/d' "$ENV_FILE"
  DEMO_PW="Demo-$("$VENV/bin/python" -c 'import secrets; print(secrets.token_urlsafe(9))')"
  printf '\n# Password for the demo logins created by seed_demo\nDEMO_PASSWORD=%s\n' "$DEMO_PW" >> "$ENV_FILE"
fi
if [[ "${SEED_DEMO:-yes}" == "yes" && ! -f "$DATA/.demo-seeded" ]]; then
  if [[ -f "$DATA/.catalog-loaded" ]]; then
    warn "Skipping demo data: the full DGDA catalog is already loaded (seed_demo would take hours)."
    warn "For demo data on a fresh database, see the README (Deploy MediPOS)."
  else
    echo "   loading demo data (seed_demo, sample catalog)..."
    medipos-manage seed_demo | tail -1 | sed 's/^/   /'
    sudo -u "$NAME" touch "$DATA/.demo-seeded"
  fi
fi

if [[ ! -f "$DATA/.catalog-loaded" ]]; then
  echo "   loading the DGDA medicine catalog (about 41,000 medicines, takes a few minutes)..."
  medipos-manage import_catalog --dgda && sudo -u "$NAME" touch "$DATA/.catalog-loaded" \
    || warn "Catalog import failed; run later: medipos-manage import_catalog --dgda"
fi

# ---------------------------------------------------------------------------
say "7/8 Service, scheduled jobs and backups"
cat > /etc/systemd/system/medipos.service <<EOF
[Unit]
Description=MediPOS (Gunicorn on 127.0.0.1:$PORT)
After=network.target

[Service]
User=$NAME
Group=$NAME
WorkingDirectory=$APP
EnvironmentFile=$ENV_FILE
ExecStart=$VENV/bin/gunicorn config.wsgi:application --bind 127.0.0.1:$PORT --workers 3 --timeout 120 --access-logfile -
Restart=always
RestartSec=3
NoNewPrivileges=true
ProtectSystem=full
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --quiet medipos
systemctl restart medipos

# send queued emails/SMS every minute (also daily stock alerts and due reminders)
cat > /etc/cron.d/medipos <<EOF
# MediPOS scheduled jobs
* * * * * $NAME cd $APP && $VENV/bin/python manage.py send_messages 2>&1 | logger -t medipos-messages
EOF
chmod 644 /etc/cron.d/medipos

cat > /etc/cron.daily/medipos-backup <<EOF
#!/usr/bin/env bash
set -e
STAMP=\$(date +%Y%m%d)
sqlite3 "$DATA/db.sqlite3" ".backup '$BACKUPS/db-\$STAMP.sqlite3'"
tar -czf "$BACKUPS/media-\$STAMP.tar.gz" -C "$APP" media
chown $NAME:$NAME "$BACKUPS"/*-\$STAMP.*
find "$BACKUPS" -type f -mtime +14 -delete
EOF
chmod 755 /etc/cron.daily/medipos-backup

# helper: medipos-update = backup + run this installer again with the same domain/port
cat > /usr/local/bin/medipos-update <<EOF
#!/usr/bin/env bash
set -e
/etc/cron.daily/medipos-backup || true
export SEED_DEMO=no   # demo data only on first install
curl -fsSL https://raw.githubusercontent.com/Rabbi-2529/thingbd/main/deploy/install_medipos.sh -o /tmp/install_medipos.sh
bash /tmp/install_medipos.sh $DOMAIN $PORT
EOF
chmod 755 /usr/local/bin/medipos-update

# ---------------------------------------------------------------------------
say "8/8 HTTPS for $DOMAIN"
mkdir -p "$WEBROOT/.well-known/acme-challenge"
CERT_DIR="/etc/letsencrypt/live/$DOMAIN"
NGINX_COMMON="    client_max_body_size 25M;
    add_header X-Content-Type-Options nosniff always;
    add_header Referrer-Policy strict-origin-when-cross-origin always;

    location /static/ { alias $APP/staticfiles/; expires 30d; access_log off; }
    location /media/  { alias $APP/media/;  expires 7d; add_header X-Content-Type-Options nosniff; }

    location / {
        proxy_pass http://127.0.0.1:$PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$remote_addr;
        proxy_set_header X-Forwarded-Proto https;
        proxy_read_timeout 120s;
    }"

HTTP_BLOCK="server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN;
    location ^~ /.well-known/acme-challenge/ { root $WEBROOT; default_type text/plain; }
    location / { return 301 https://$DOMAIN\$request_uri; }
}"

if [[ ! -f "$CERT_DIR/fullchain.pem" ]]; then
  echo "$HTTP_BLOCK" > "$SITE"
  ln -sf "$SITE" /etc/nginx/sites-enabled/medipos
  nginx -t -q && systemctl reload nginx
  certbot certonly --webroot -w "$WEBROOT" -d "$DOMAIN" --cert-name "$DOMAIN" \
    --agree-tos --non-interactive --register-unsafely-without-email
fi
SSL_OPTS=""; [[ -f /etc/letsencrypt/options-ssl-nginx.conf ]] && SSL_OPTS="    include /etc/letsencrypt/options-ssl-nginx.conf;"
DHPARAM="";  [[ -f /etc/letsencrypt/ssl-dhparams.pem ]] && DHPARAM="    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;"

cat > "$SITE" <<EOF
# Managed by thingbd/deploy/install_medipos.sh — https://$DOMAIN -> 127.0.0.1:$PORT
$HTTP_BLOCK

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name $DOMAIN;
    ssl_certificate     $CERT_DIR/fullchain.pem;
    ssl_certificate_key $CERT_DIR/privkey.pem;
$SSL_OPTS
$DHPARAM

$NGINX_COMMON
}
EOF
ln -sf "$SITE" /etc/nginx/sites-enabled/medipos
nginx -t -q
systemctl reload nginx
mkdir -p /etc/letsencrypt/renewal-hooks/deploy
printf '#!/bin/sh\nsystemctl reload nginx\n' > /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh
chmod 755 /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh

# ---------------------------------------------------------------------------
sleep 3
CODE="$(curl -s -o /dev/null -w '%{http_code}' --max-time 20 "https://$DOMAIN/")"
if [[ "$CODE" =~ ^(200|301|302)$ ]]; then
  say "Done! MediPOS is live at https://$DOMAIN (app on 127.0.0.1:$PORT)"
  DEMO_PW="$(grep '^DEMO_PASSWORD=' "$ENV_FILE" | cut -d= -f2-)"
  cat <<EOF

Demo logins (password for all: $DEMO_PW — also in $ENV_FILE)
  admin@medipos.local        platform admin   https://$DOMAIN/platform/
  owner@lazzpharma.local     Lazz Pharma (paid, 2 outlets)
  manager@lazzpharma.local   Lazz manager
  cashier@lazzpharma.local   Lazz cashier     POS: https://$DOMAIN/sales/pos/
  owner@greenlife.local      Green Life (trial ending)
  owner@sunrise.local        Sunrise (trial expired)
EOF
  if $FIRST_INSTALL; then cat <<EOF

Next steps
  1. Your own platform admin:     medipos-manage createsuperuser
  2. Update later:                medipos-update
  3. Logs:                        journalctl -u medipos -f
  4. Email / SMS settings:        nano $ENV_FILE   then  systemctl restart medipos
EOF
  fi
else
  warn "https://$DOMAIN answered HTTP $CODE. Logs: journalctl -u medipos -n 50  and  tail /var/log/nginx/error.log"
  exit 1
fi
