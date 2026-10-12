#!/usr/bin/env bash
# Thingbd — one-step server setup for Ubuntu 22.04 / 24.04.
#
#   sudo bash setup_server.sh [domain-or-ip]
#
# Safe to run again: it updates the code and keeps the existing database, uploads and .env.
# Previous websites are NOT deleted: they are archived to /root/pre-thingbd-backup-<date>/ and disabled.
set -euo pipefail

REPO_URL="https://github.com/Rabbi-2529/thingbd.git"
BRANCH="main"
BASE=/srv/thingbd
APP="$BASE/app"
VENV="$BASE/venv"
DATA="$BASE/data"
MEDIA="$BASE/media"
STATIC="$BASE/static"
BACKUPS="$BASE/backups"
USER_NAME=thingbd
STAMP="$(date +%Y%m%d-%H%M%S)"

say()  { printf '\n\033[1;35m==> %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33m!!  %s\033[0m\n' "$*"; }
die()  { printf '\033[1;31mXX  %s\033[0m\n' "$*" >&2; exit 1; }

[[ $EUID -eq 0 ]] || die "Run as root (sudo bash $0)."
. /etc/os-release
[[ "${ID:-}" == "ubuntu" ]] || warn "This script is written for Ubuntu; continuing anyway on ${PRETTY_NAME:-unknown}."

HOST="${1:-$(curl -4 -s --max-time 5 https://ifconfig.me || hostname -I | awk '{print $1}')}"
[[ -n "$HOST" ]] || die "Could not detect the server IP. Pass it: sudo bash $0 147.93.152.43"
say "Setting up Thingbd for http://$HOST"

# ---------------------------------------------------------------------------
say "1/9 Installing system packages"
export DEBIAN_FRONTEND=noninteractive

# Ubuntu's automatic updates may be installing packages; wait until nobody holds the apt/dpkg locks.
# (Checks the lock files themselves: the always-running unattended-upgrades service does not count.)
APT_LOCKS=(/var/lib/dpkg/lock-frontend /var/lib/dpkg/lock /var/lib/apt/lists/lock /var/cache/apt/archives/lock)
apt_busy() { fuser "${APT_LOCKS[@]}" >/dev/null 2>&1; }
wait_for_apt() {
  local waited=0
  while apt_busy; do
    if (( waited % 60 == 0 )); then
      echo "   Ubuntu is installing updates in the background, waiting... ($((waited / 60)) min)"
    fi
    if (( waited >= 1800 )); then
      fuser -v "${APT_LOCKS[@]}" 2>&1 | sed 's/^/   /'
      die "apt is still busy after 30 minutes (process above). Check it with: ps -o pid,etime,cmd -p <PID>"
    fi
    sleep 10; waited=$((waited + 10))
  done
}
wait_for_apt
apt-get -o DPkg::Lock::Timeout=600 update -y
wait_for_apt
apt-get -o DPkg::Lock::Timeout=600 install -y psmisc python3 python3-venv python3-dev build-essential git nginx sqlite3 curl ufw \
  libjpeg-dev zlib1g-dev libwebp-dev

# ---------------------------------------------------------------------------
say "2/9 Retiring previous websites (archived, not deleted)"
OLD="/root/pre-thingbd-backup-$STAMP"
mkdir -p "$OLD"
if systemctl list-unit-files apache2.service >/dev/null 2>&1 && systemctl is-enabled apache2 >/dev/null 2>&1; then
  systemctl stop apache2 || true
  systemctl disable apache2 || true
  echo "apache2 was stopped and disabled (not uninstalled)." >> "$OLD/README.txt"
  warn "Apache was running — stopped and disabled."
fi
if [[ -d /var/www ]] && [[ -n "$(ls -A /var/www 2>/dev/null)" ]]; then
  tar -czf "$OLD/var-www.tar.gz" -C / var/www
  echo "Old /var/www archived to var-www.tar.gz" >> "$OLD/README.txt"
fi
shopt -s nullglob
for site in /etc/nginx/sites-enabled/* /etc/nginx/conf.d/*.conf; do
  [[ "$(basename "$site")" == "thingbd" || "$(basename "$site")" == "thingbd.conf" ]] && continue
  mkdir -p "$OLD/nginx"
  cp -a "$(readlink -f "$site")" "$OLD/nginx/" 2>/dev/null || true
  rm -f "$site"
  echo "Disabled nginx site: $site" >> "$OLD/README.txt"
done
shopt -u nullglob
[[ -s "$OLD/README.txt" ]] && warn "Old sites archived in $OLD" || rmdir "$OLD"

# Anything other than nginx still holding port 80?
if ss -ltnp 'sport = :80' | grep -v nginx | grep -q LISTEN; then
  ss -ltnp 'sport = :80'
  die "Another program is using port 80 (shown above). Stop it, then run this script again."
fi

# ---------------------------------------------------------------------------
say "3/9 Creating the app user and folders"
id "$USER_NAME" >/dev/null 2>&1 || useradd --system --home "$BASE" --shell /usr/sbin/nologin "$USER_NAME"
mkdir -p "$BASE" "$DATA" "$MEDIA" "$STATIC" "$BACKUPS"

# ---------------------------------------------------------------------------
say "4/9 Downloading the code from GitHub"
git config --global --add safe.directory "$APP" 2>/dev/null || true
if [[ -d "$APP/.git" ]]; then
  git -C "$APP" fetch --quiet origin "$BRANCH"
  git -C "$APP" reset --hard "origin/$BRANCH"
else
  rm -rf "$APP"
  git clone --quiet --branch "$BRANCH" "$REPO_URL" "$APP"
fi
git -C "$APP" log -1 --format='   deployed commit %h — %s'

# ---------------------------------------------------------------------------
say "5/9 Python environment"
[[ -x "$VENV/bin/python" ]] || python3 -m venv "$VENV"
"$VENV/bin/pip" install --quiet --upgrade pip wheel
"$VENV/bin/pip" install --quiet -r "$APP/requirements.txt" gunicorn

# ---------------------------------------------------------------------------
say "6/9 Configuration (.env)"
ENV_FILE="$BASE/.env"
if [[ ! -f "$ENV_FILE" ]]; then
  SECRET="$("$VENV/bin/python" -c 'import secrets; print(secrets.token_urlsafe(50))')"
  cat > "$ENV_FILE" <<EOF
# Thingbd production settings — keep this file private.
SECRET_KEY=$SECRET
DEBUG=false
ALLOWED_HOSTS=$HOST,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://$HOST
# Switch to true (and update the two lines above to https://yourdomain) once HTTPS is set up.
USE_HTTPS=false
TIME_ZONE=Asia/Dhaka

DATABASE_PATH=$DATA/db.sqlite3
MEDIA_ROOT=$MEDIA
STATIC_ROOT=$STATIC

# Email for new-lead alerts. Until this is filled in, emails are only written to the log.
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
#EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
#EMAIL_HOST=smtp.example.com
#EMAIL_PORT=587
#EMAIL_HOST_USER=
#EMAIL_HOST_PASSWORD=
#EMAIL_USE_TLS=true
#DEFAULT_FROM_EMAIL=Thingbd <no-reply@thingbd.com>
EOF
  echo "   created $ENV_FILE"
else
  echo "   keeping existing $ENV_FILE"
fi
ln -sf "$ENV_FILE" "$APP/.env"
chmod 640 "$ENV_FILE"

chown -R "$USER_NAME:$USER_NAME" "$BASE"
chown root:"$USER_NAME" "$ENV_FILE"

# Helper: run any manage.py command as the app user, e.g. `thingbd-manage createsuperuser`
cat > /usr/local/bin/thingbd-manage <<EOF
#!/usr/bin/env bash
cd "$APP" && exec sudo -u $USER_NAME "$VENV/bin/python" manage.py "\$@"
EOF
chmod 755 /usr/local/bin/thingbd-manage

# ---------------------------------------------------------------------------
say "7/9 Database, static files and starter content"
thingbd-manage migrate --noinput
thingbd-manage collectstatic --noinput --verbosity 0
thingbd-manage seed_content
thingbd-manage check --deploy --fail-level ERROR >/dev/null && echo "   deploy checks passed"

# ---------------------------------------------------------------------------
say "8/9 Gunicorn service and Nginx"
cat > /etc/systemd/system/thingbd.service <<EOF
[Unit]
Description=Thingbd website (Gunicorn)
After=network.target

[Service]
User=$USER_NAME
Group=$USER_NAME
WorkingDirectory=$APP
EnvironmentFile=$ENV_FILE
RuntimeDirectory=thingbd
ExecStart=$VENV/bin/gunicorn config.wsgi:application --bind unix:/run/thingbd/gunicorn.sock --workers 3 --timeout 60 --access-logfile - --umask 007
Restart=always
RestartSec=3
NoNewPrivileges=true
ProtectSystem=full
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/nginx/sites-available/thingbd <<EOF
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name $HOST _;

    client_max_body_size 12M;

    location /static/ {
        alias $STATIC/;
        expires 30d;
        access_log off;
    }

    location /media/ {
        alias $MEDIA/;
        expires 7d;
        add_header X-Content-Type-Options nosniff;
    }

    location / {
        proxy_pass http://unix:/run/thingbd/gunicorn.sock;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 60s;
    }
}
EOF
ln -sf /etc/nginx/sites-available/thingbd /etc/nginx/sites-enabled/thingbd
usermod -aG "$USER_NAME" www-data   # lets nginx read static and media files
chmod 750 "$BASE"
nginx -t
systemctl daemon-reload
systemctl enable --now thingbd
systemctl restart thingbd
systemctl enable nginx
systemctl restart nginx

# Firewall: keep SSH open, allow web traffic.
# Collect SSH ports from sshd's config AND from what is actually listening (Ubuntu 24.04 uses
# systemd socket activation, where `sshd -T` can fail). Port 22 is always kept open.
SSH_PORTS="$( { sshd -T 2>/dev/null | awk '/^port /{print $2}' || true
                ss -ltnpH 2>/dev/null | awk '/sshd|"systemd"/ {n=split($4,a,":"); print a[n]}' || true
                echo 22; } | grep -E '^[0-9]+$' | sort -un | tr '\n' ' ')"
for port in $SSH_PORTS; do ufw allow "$port"/tcp >/dev/null; done
ufw allow 'Nginx Full' >/dev/null
ufw --force enable >/dev/null
echo "   firewall on: SSH (port ${SSH_PORTS% }), HTTP and HTTPS allowed"

# ---------------------------------------------------------------------------
say "9/9 Daily backups (kept 14 days in $BACKUPS)"
cat > /etc/cron.daily/thingbd-backup <<EOF
#!/usr/bin/env bash
set -e
STAMP=\$(date +%Y%m%d)
sqlite3 "$DATA/db.sqlite3" ".backup '$BACKUPS/db-\$STAMP.sqlite3'"
tar -czf "$BACKUPS/media-\$STAMP.tar.gz" -C "$BASE" media
find "$BACKUPS" -type f -mtime +14 -delete
EOF
chmod 755 /etc/cron.daily/thingbd-backup
/etc/cron.daily/thingbd-backup && echo "   first backup written"

# Helper: `thingbd-update` pulls the latest code from GitHub and restarts.
cp "$APP/deploy/update.sh" /usr/local/bin/thingbd-update
chmod 755 /usr/local/bin/thingbd-update

sleep 2
CODE="$(curl -s -o /dev/null -w '%{http_code}' -H "Host: $HOST" http://127.0.0.1/)"
[[ "$CODE" == "200" ]] && say "Done! Website: http://$HOST   Dashboard: http://$HOST/dashboard/" \
  || { warn "The site answered HTTP $CODE. Check logs with: journalctl -u thingbd -n 50"; exit 1; }

cat <<EOF

Next steps
  1. Create your dashboard login:     thingbd-manage createsuperuser
  2. Deploy future updates:           thingbd-update
  3. Logs:                            journalctl -u thingbd -f
  4. Settings (email, domain):        nano $ENV_FILE   then  systemctl restart thingbd
EOF
