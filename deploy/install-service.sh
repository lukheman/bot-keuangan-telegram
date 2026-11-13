#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${APP_DIR:-/www/wwwroot/bot-keuangan-telegram}"
SERVICE_FILE="$APP_DIR/deploy/systemd/bot-keuangan.service"

if [[ "$(id -u)" -ne 0 ]]; then
    echo "Jalankan sebagai root: sudo APP_DIR=$APP_DIR $0" >&2
    exit 1
fi

if [[ ! -f "$SERVICE_FILE" ]]; then
    echo "File service tidak ditemukan: $SERVICE_FILE" >&2
    exit 1
fi

if [[ ! -x "$APP_DIR/.venv/bin/python" ]]; then
    echo "Python virtualenv tidak ditemukan: $APP_DIR/.venv/bin/python" >&2
    echo "Jalankan uv sync --frozen terlebih dahulu." >&2
    exit 1
fi

install -m 0644 "$SERVICE_FILE" /etc/systemd/system/bot-keuangan.service
systemctl daemon-reload
systemctl enable bot-keuangan.service
systemctl restart bot-keuangan.service
systemctl --no-pager --full status bot-keuangan.service
