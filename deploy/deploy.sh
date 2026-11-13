#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${APP_DIR:-/www/wwwroot/bot-keuangan-telegram}"
BRANCH="${BRANCH:-main}"

if [[ "$(id -u)" -eq 0 ]]; then
    RUN_AS="${RUN_AS:-www}"
else
    RUN_AS="${RUN_AS:-$(id -un)}"
fi

if [[ ! -d "$APP_DIR/.git" ]]; then
    echo "Repo Git tidak ditemukan: $APP_DIR" >&2
    exit 1
fi

if [[ ! -f "$APP_DIR/.env" ]]; then
    echo "File environment tidak ditemukan: $APP_DIR/.env" >&2
    echo "Buat .env dari .env.example dan isi secret produksi." >&2
    exit 1
fi

cd "$APP_DIR"

if [[ -n "$(git status --porcelain)" ]]; then
    echo "Working tree memiliki perubahan lokal. Deploy dihentikan agar perubahan tidak tertimpa." >&2
    git status --short >&2
    exit 1
fi

git fetch origin "$BRANCH"
git checkout "$BRANCH"
git pull --ff-only origin "$BRANCH"

if [[ "$(id -u)" -eq 0 && "$RUN_AS" != "$(id -un)" ]]; then
    runuser -u "$RUN_AS" -- uv sync --frozen
    runuser -u "$RUN_AS" -- env ENV_FILE=.env uv run alembic upgrade head
else
    uv sync --frozen
    ENV_FILE=.env uv run alembic upgrade head
fi

if systemctl is-active --quiet bot-keuangan.service; then
    systemctl restart bot-keuangan.service
    systemctl --no-pager --full status bot-keuangan.service
else
    echo "Service bot-keuangan belum aktif. Jalankan deploy/install-service.sh." >&2
    exit 1
fi

echo "Deploy selesai. Cek: $APP_DIR/deploy/healthcheck.sh"
