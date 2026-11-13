#!/usr/bin/env bash
set -Eeuo pipefail

URL="${URL:-http://127.0.0.1:8000/}"
curl --fail --silent --show-error --max-time 15 "$URL" >/dev/null
echo "OK: $URL"
