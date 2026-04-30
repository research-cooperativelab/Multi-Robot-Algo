#!/usr/bin/env bash
# update.sh — pull latest code and restart services (run as root on VPS).
# Usage: sudo bash deploy/update.sh
set -euo pipefail

APP_DIR="/var/www/searchfcr"
APP_USER="searchfcr"

echo "==> Pulling latest code"
git -C "$APP_DIR" pull --ff-only

echo "==> Updating Python deps"
sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install -q \
    -r "$APP_DIR/backend/requirements.txt"
sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install -q -e "$APP_DIR"

echo "==> Syncing slide assets (thesis/figures → /var/www/searchfcr/assets/)"
mkdir -p "$APP_DIR/assets"
cp -f "$APP_DIR"/thesis/figures/*.png "$APP_DIR/assets/" 2>/dev/null || true

echo "==> Rebuilding frontend"
cd "$APP_DIR/sar-sim"
rm -rf node_modules
npm ci
npm run build
chown -R "$APP_USER:$APP_USER" "$APP_DIR/sar-sim"

echo "==> Restarting backend"
systemctl restart searchfcr-backend
systemctl status searchfcr-backend --no-pager

echo "✓ Update complete"
