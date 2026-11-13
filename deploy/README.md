# Deploy aaPanel

Target: FastAPI webhook lewat `uvicorn`, Neon/Postgres, Nginx aaPanel.

## Struktur VPS

```text
/www/wwwroot/bot-keuangan-telegram
├── .env
├── .venv
└── source code
```

Service memakai user/group `www`, port lokal `127.0.0.1:8000`, dan satu worker.
Sesuaikan path atau user di `systemd/bot-keuangan.service` jika aaPanel memakai
konfigurasi berbeda.

Pilih **salah satu** cara menjalankan: aaPanel Python Project (UI) atau systemd
manual. Jangan aktifkan keduanya karena akan berebut port `8000`.

## Opsi A: aaPanel Python Project (UI)

Isi form **Add Python Project** seperti ini:

| Field | Nilai |
|---|---|
| Project Name | `bot-keuangan-telegram` |
| Python Environment | environment **Python 3.12** (buat di Environment Management jika belum ada) |
| Startup Way | `Command Startup` |
| Project Path | `/www/wwwroot/bot-keuangan-telegram` |
| Startup Command | lihat perintah di bawah |
| Environment Variables | `Specify Variable` |
| Startup User | `www` |
| Install Dependencies | `/www/wwwroot/bot-keuangan-telegram/requirements.txt` |
| Port (More settings) | `8000` |

Startup Command:

```bash
python -m uvicorn app.api.index:app --host 127.0.0.1 --port 8000 --workers 1 --proxy-headers --forwarded-allow-ips=127.0.0.1
```

Environment Variables:

```env
ENV_FILE=/www/wwwroot/bot-keuangan-telegram/.env
PYTHONUNBUFFERED=1
```

Kosongkan **Project Init Command** dulu, karena `.env` belum ada saat project
baru dibuat. Migrasi dijalankan manual setelah `.env` terisi.

Setelah project dibuat, buat `.env` (file ini tidak ikut Git):

```bash
cd /www/wwwroot/bot-keuangan-telegram
cp .env.example .env
nano .env
chown www:www .env
chmod 600 .env
```

Lalu jalankan migrasi dari terminal aaPanel bila Init Command tadi kosong:

```bash
cd /www/wwwroot/bot-keuangan-telegram
ENV_FILE=/www/wwwroot/bot-keuangan-telegram/.env python -m alembic upgrade head
```

> Gunakan `python` milik virtualenv project aaPanel. Jika terminal belum
> mengaktifkan venv, buka **Terminal** pada halaman Python Project tersebut.

## Opsi B: systemd manual

```bash
cd /www/wwwroot/bot-keuangan-telegram
uv sync --frozen
cp .env.example .env
nano .env

# Setelah .env diisi, service user harus bisa membacanya.
chown www:www .env
chmod 600 .env
chown -R www:www .venv

ENV_FILE=.env uv run alembic upgrade head
sudo ./deploy/install-service.sh
./deploy/healthcheck.sh
```

Isi `.env` produksi:

```env
TELEGRAM_TOKEN=...
GROQ_API_KEY=...
DATABASE_URL=postgresql+asyncpg://.../...?sslmode=require
WEBHOOK_URL=https://bot.example.com/api/webhook
WEBAPP_BASE_URL=https://bot.example.com
PORT=8000
CRON_SECRET=...
HERMES_API_KEY=...
```

## aaPanel Nginx

Buat site `bot.example.com`, pasang Let's Encrypt, lalu masukkan isi
`nginx/reverse-proxy.conf` ke konfigurasi site. Jangan buka port 8000 ke publik.

Tes:

```bash
curl -fsS https://bot.example.com/
```

## Daftarkan Telegram webhook

Jalankan setelah DNS, SSL, Nginx, dan service aktif:

```bash
curl -fsS https://bot.example.com/api/set_webhook
curl -fsS "https://api.telegram.org/bot${TELEGRAM_TOKEN}/getWebhookInfo"
```

Jangan menjalankan `main.py` bersamaan dengan service ini. Satu token Telegram
hanya boleh punya satu webhook aktif.

## Cron laporan harian

Tambahkan cron aaPanel setiap 15 menit:

```bash
curl -fsS 'https://bot.example.com/api/cron/daily-report?secret=GANTI_CRON_SECRET' >/dev/null
```

## Deploy update

Commit dan push kode dari lokal, lalu di VPS:

```bash
sudo APP_DIR=/www/wwwroot/bot-keuangan-telegram ./deploy/deploy.sh
```

Script menghentikan deploy jika ada perubahan lokal atau `.env` hilang.

## Diagnostik

```bash
systemctl status bot-keuangan
journalctl -u bot-keuangan -n 100 --no-pager
./deploy/healthcheck.sh
```
