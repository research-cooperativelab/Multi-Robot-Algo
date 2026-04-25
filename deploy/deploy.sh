#!/usr/bin/env bash
# deploy.sh — run this on the VPS as root (or with sudo) after first clone.
# Usage: sudo bash deploy/deploy.sh
set -euo pipefail

DOMAIN="searchfcr.fozhan.dev"
APP_DIR="/var/www/searchfcr"
APP_USER="searchfcr"
REPO="https://github.com/research-cooperativelab/Multi-Robot-Algo.git"

echo "==> [1/8] System packages"
apt-get update -q
apt-get install -y -q \
    git nginx python3 python3-venv python3-pip \
    nodejs npm certbot python3-certbot-nginx curl

# Install a recent Node via NodeSource if system node is too old
node_ver=$(node --version 2>/dev/null | cut -c2- | cut -d. -f1)
if [ "${node_ver:-0}" -lt 20 ]; then
    echo "  Node too old ($node_ver), installing v20 via NodeSource..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y nodejs
fi

echo "==> [2/8] Create app user + directory"
id -u "$APP_USER" &>/dev/null || useradd --system --no-create-home --shell /usr/sbin/nologin "$APP_USER"
mkdir -p "$APP_DIR"

echo "==> [3/8] Clone / pull repo"
git config --global --add safe.directory "$APP_DIR"
if [ -d "$APP_DIR/.git" ]; then
    git -C "$APP_DIR" pull --ff-only
else
    git clone "$REPO" "$APP_DIR"
fi
chown -R "$APP_USER:$APP_USER" "$APP_DIR"

echo "==> [4/8] Python virtual environment + backend deps"
sudo -u "$APP_USER" python3 -m venv "$APP_DIR/venv"
sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install -q --upgrade pip
sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install -q \
    -r "$APP_DIR/backend/requirements.txt"
# Install the searchfcr package itself (provides main.py shim)
sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install -q -e "$APP_DIR"

echo "==> [5/8] Build React frontend"
cd "$APP_DIR/sar-sim"
HOME="$APP_DIR" sudo -u "$APP_USER" npm ci
HOME="$APP_DIR" sudo -u "$APP_USER" npm run build
echo "  Built to $APP_DIR/sar-sim/dist/"

echo "==> [6/8] Nginx config"
cp "$APP_DIR/deploy/searchfcr.fozhan.dev.nginx" \
   "/etc/nginx/sites-available/$DOMAIN"
ln -sf "/etc/nginx/sites-available/$DOMAIN" \
       "/etc/nginx/sites-enabled/$DOMAIN"
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

echo "==> [7/8] Systemd service"
cp "$APP_DIR/deploy/searchfcr-backend.service" \
   /etc/systemd/system/searchfcr-backend.service
systemctl daemon-reload
systemctl enable --now searchfcr-backend
systemctl status searchfcr-backend --no-pager

echo "==> [8/8] TLS certificate (Let's Encrypt)"
certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos \
    --email "foojanbabaeeian@gmail.com" --redirect
systemctl reload nginx

echo ""
echo "✓ Deployed!  https://$DOMAIN"
echo "  Simulator : https://$DOMAIN/"
echo "  Slides    : https://$DOMAIN/slides"
echo "  API health: https://$DOMAIN/api/health"
