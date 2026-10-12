#!/usr/bin/env bash
# Pull the latest code from GitHub and restart Thingbd. Installed as /usr/local/bin/thingbd-update.
set -euo pipefail

BASE=/srv/thingbd
APP="$BASE/app"
VENV="$BASE/venv"

[[ $EUID -eq 0 ]] || { echo "Run as root: sudo thingbd-update" >&2; exit 1; }

echo "==> Backing up the database first"
/etc/cron.daily/thingbd-backup || true

echo "==> Updating code"
git -C "$APP" fetch --quiet origin main
git -C "$APP" reset --hard origin/main
git -C "$APP" log -1 --format='    now at %h — %s'
chown -R thingbd:thingbd "$APP"

echo "==> Installing requirements"
"$VENV/bin/pip" install --quiet -r "$APP/requirements.txt" gunicorn

echo "==> Migrating and collecting static files"
thingbd-manage migrate --noinput
thingbd-manage collectstatic --noinput --verbosity 0

# Keep this helper itself up to date.
cp "$APP/deploy/update.sh" /usr/local/bin/thingbd-update

systemctl restart thingbd
sleep 2
systemctl is-active --quiet thingbd && echo "==> Done. Thingbd restarted." \
  || { echo "!! Thingbd failed to start: journalctl -u thingbd -n 50" >&2; exit 1; }
