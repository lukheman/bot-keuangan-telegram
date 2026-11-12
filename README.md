# Bot Keuangan Telegram

Bot pencatatan keuangan pribadi untuk Telegram. Catat transaksi dengan bahasa
natural (`kopi 20rb`), kirim foto struk (foto biasa atau file JPG/PNG), kelola
dompet & budget, lihat laporan harian/mingguan/bulanan, lalu edit atau hapus
transaksi kapan saja lewat menu Riwayat.

## Menjalankan

```bash
cp .env.example .env   # isi TELEGRAM_TOKEN dan GROQ_API_KEY
uv sync
uv run main.py
```

Tanpa `WEBHOOK_URL`, bot berjalan dengan long polling. Untuk produksi, isi
`WEBHOOK_URL` dan gunakan endpoint `/api/webhook`.

Variabel penting:

| Variabel | Fungsi |
|---|---|
| `TELEGRAM_TOKEN` | Token bot dari BotFather (wajib) |
| `GROQ_API_KEY` | Pembaca transaksi AI (wajib untuk catat otomatis) |
| `DATABASE_URL` | Koneksi database; default SQLite |
| `WEBHOOK_URL` | URL publik webhook (opsional) |
| `WEBAPP_BASE_URL` | Base URL dashboard web (opsional) |
| `CRON_SECRET` | Pengaman endpoint laporan harian |
| `HERMES_API_KEY` | API key integrasi eksternal & dashboard metrik `/metrics` |

## Metrik UX

Setelah `HERMES_API_KEY` diisi, buka:

```
/metrics?api_key=HERMES_API_KEY&weeks=8
```

Halaman ini menampilkan funnel onboarding → transaksi pertama/kelima, error,
dan durasi respons AI per minggu. Versi JSON tersedia di
`/api/metrics/ux?weeks=8&api_key=HERMES_API_KEY`.

## Dokumentasi UX

Rencana perbaikan pengalaman pengguna dan standar penulisan pesan:

- [Backlog & rencana bertahap](docs/ux/BACKLOG.md)
- [Roadmap](docs/ux/ROADMAP.md)
- [Panduan UX & copywriting](docs/ux/UX-GUIDELINES.md)
- [Template pesan](docs/ux/MESSAGE-TEMPLATES.md)
- [Checklist QA](docs/ux/QA-CHECKLIST.md)
- [Temuan audit](docs/ux/AUDIT-FINDINGS.md)

## Struktur Singkat

```
main.py                  # entry point polling/webhook
app/api/index.py         # webhook FastAPI, dashboard, API
app/services/            # transaksi, laporan, budget, AI, sheets
bot/handlers/            # handler Telegram
bot/utils/               # helper pesan, parsing, user
migrations/              # Alembic
tests/                   # pytest
```
