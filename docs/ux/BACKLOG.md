# BACKLOG — Perbaikan UX Bot Keuangan Telegram

> Dokumen kerja untuk perbaikan bertahap. Disusun dari audit UX statis
> (`AUDIT-FINDINGS.md`).
>
> Status: `todo` · `in-progress` · `blocked` · `done`
> Prioritas: `P0` (blokir pengalaman inti) · `P1` (penting) · `P2` (peningkatan)
> Estimasi: `S` < 2 jam · `M` 0,5–1 hari · `L` 2–3 hari · `XL` > 3 hari

## Status Implementasi

**Fase 0 selesai (2026-11-12).** Item yang sudah dikerjakan:

| ID | Item | Status |
|---|---|---|
| UX-001 | `/start` baru + tombol menu | done |
| UX-002 | `/start` idempoten + auto-register di entry point | done |
| UX-003 | `/help`, `/bantuan`, fallback command | done |
| UX-004 | Fallback input non-teks (voice/dokumen/sticker) | done |
| UX-005 | Global error handler + pesan error generik | done |
| UX-006 | Teks "laporan hari ini" tidak lagi dibisukan | done |
| UX-007 | Standar tone "kamu", hapus jargon teknis | done |
| UX-008 | Escape Markdown pada konten dinamis | done |
| UX-009 | Command list ringkas; command destruktif lewat menu | done |
| UX-010 | Konfirmasi hapus akun 2 langkah | done |
| UX-011 | Konfirmasi hapus dompet 2 langkah | done (dipercepat dari Fase 1) |
| UX-012 | Konfirmasi hapus budget 2 langkah | done (dipercepat dari Fase 1) |
| UX-013 | Dead end menu dompet untuk user baru | done |
| UX-014 | Timeout, tombol batal, input dompet fleksibel | done |
| UX-020 | `callback_data` dompet ≤ 64 byte | done |
| UX-025 | Tombol aksi di pesan sukses transaksi | done |
| UX-041 | Rentang laporan mingguan tepat 7 hari | done |
| UX-042 | URL dashboard dari `WEBAPP_BASE_URL` | done |
| UX-043 | Info `/akun` lengkap | done |

Dokumentasi tambahan: `README.md`, `.env.example`, unit test di
`tests/test_ux_helpers.py`, `tests/test_report_service.py`,
`tests/test_transaction_preview.py`, `tests/test_pending_service.py`, dan
`tests/test_budget_ui.py`.

**Fase 1 — onboarding selesai (2026-11-12).** Item yang sudah dikerjakan:

| ID | Item | Status |
|---|---|---|
| UX-030 | Onboarding wizard (zona waktu → notifikasi → dompet → privasi) | done |
| UX-031 | Pilihan zona waktu WIB/WITA/WIT | done |
| UX-032 | Persetujuan notifikasi harian (opt-in saat onboarding) | done |
| UX-033 | Dompet awal + penjelasan saldo | done |
| UX-034 | Notice privasi pemrosesan AI | done |
| UX-022 | Pratinjau transaksi (confidence rendah, transfer, koreksi) | done |
| UX-023 | Undo transaksi dari pesan sukses | done |

**Fase 2 — keandalan transaksi (berjalan).** Item yang sudah dikerjakan:

| ID | Item | Status |
|---|---|---|
| UX-021 | Persistensi pending transaction di database + TTL 10 menit | done |
| UX-026 | Anti double-tap lewat konsumsi pending atomik | done |
| UX-040 | Pemilih kategori budget berbasis tombol | done |
| UX-044 | Tambah/ubah budget dari menu | done |
| UX-045 | Pencocokan nama dompet konsisten di semua alur | done |
| UX-024 | Nama file foto unik (UUID per unggahan) | done |
| UX-049 | Dompet tidak ditemukan → pilih/buat dompet tanpa mengetik ulang | done |
| UX-046 | Laporan menampilkan selisih periode + total saldo dompet | done |
| UX-047 | Pemilih bulan laporan berbasis tombol | done |
| UX-048 | Ekspor CSV di samping JSON (PDF menyusul) | done |

Sisa Fase 2: voice note (UX-027).

**Fase 3 — berjalan (2026-11-12).** Item yang sudah dikerjakan:

| ID | Item | Status |
|---|---|---|
| UX-054 | Foto struk bisa dikirim sebagai dokumen JPG/PNG | done (dipercepat) |
| UX-050 | Telemetri funnel onboarding → transaksi pertama/kelima + error | done |
| UX-055 | Pusat bantuan in-chat dengan tombol topik FAQ | done |
| UX-052 | Audit copywriting: istilah teknis, sapaan, dan label tombol | done |
| UX-053 | Personalisasi: sapaan + target tabungan dengan progres | done |
| UX-056 | Riwayat, edit, dan hapus transaksi dari bot | done |

Dashboard metrik mingguan dan durasi AI sudah tersedia. **UX-051** tinggal
eksekusi uji usability dengan 5 peserta nyata (paket sesi sudah siap). Voice
note (UX-027) tetap ditunda.

---

## 1. Ringkasan Epic

| Epic | Nama | Tujuan | Prioritas | Fase |
|---|---|---|---|---|
| E1 | First-run & onboarding | Pengguna baru paham, terdaftar, dan bisa transaksi pertama < 60 detik | P0 | 0–1 |
| E2 | Navigasi & discoverability | Semua fitur bisa ditemukan tanpa hafal command | P0 | 0–1 |
| E3 | Error handling & recovery | Tidak ada lagi layar buntu atau pesan teknis | P0 | 0–1 |
| E4 | Kepercayaan transaksi | Pengguna bisa memverifikasi, membatalkan, dan mengoreksi catatan | P0 | 1–2 |
| E5 | Dompet & budget | Alur dompet/budget selesai tanpa dead end | P1 | 1–2 |
| E6 | Laporan & notifikasi | Laporan akurat, mudah dipahami, dan tidak mengganggu | P1 | 2–3 |
| E7 | Copy, aksesibilitas & privasi | Bahasa konsisten, ramah awam, dan transparan | P1 | 0–3 |
| E8 | Pengukuran & pengujian | Perbaikan terukur, tidak regresi | P2 | 2–3 |

---

## 2. Papan Backlog

### Fase 0 — Quick Wins (target: 1–2 hari)

| ID | Item | Prioritas | Est | Depends | Lokasi utama |
|---|---|---|---|---|---|
| UX-001 | Tulis ulang `/start` + tombol menu | P0 | S | — | `main.py:68-79` |
| UX-002 | Jadikan `/start` idempoten (buat akun bila belum ada) | P0 | S | UX-001 | `main.py`, `account.py` |
| UX-003 | Tambah `/help` + fallback command tak dikenal | P0 | S | — | `main.py` |
| UX-004 | Fallback input non-teks (voice, dokumen, sticker) | P0 | S | UX-003 | `main.py` |
| UX-005 | Global error handler + hapus `str(e)` dari pesan user | P0 | M | — | semua handler |
| UX-006 | Hapus pembisuan teks "laporan hari ini" | P0 | S | — | `transaction.py:211-219` |
| UX-007 | Ganti jargon & standarkan tone "kamu" | P1 | S | — | semua handler |
| UX-008 | Escape konten dinamis Markdown | P0 | M | — | `account.py`, `menu.py`, `wallet_interactive.py` |
| UX-009 | Standarkan daftar command + sembunyikan command destruktif | P1 | S | UX-003 | `main.py:47-59` |
| UX-010 | Konfirmasi hapus akun 2 langkah | P0 | S | — | `account.py:70-93` |
| UX-020 | Perbaiki `callback_data` pemilihan dompet (batas 64 byte) | P0 | S | — | `transaction.py:146-162` |
| UX-041 | Perbaiki rentang laporan mingguan (8 hari → 7 hari) | P1 | S | — | `report_service.py:66-68` |
| UX-042 | Hapus URL dashboard hardcoded | P1 | S | — | `account.py:125` |

### Fase 1 — First-run, navigasi, dan kepercayaan (target: minggu 1–2)

| ID | Item | Prioritas | Est | Depends | Lokasi utama |
|---|---|---|---|---|---|
| UX-030 | Onboarding wizard 4 langkah | P0 | L | UX-001, UX-002 | handler baru `bot/handlers/onboarding.py` |
| UX-031 | Pilihan zona waktu (WIB/WITA/WIT) | P0 | M | UX-030 | `onboarding.py`, `models/user.py` |
| UX-032 | Persetujuan notifikasi harian (opt-in) | P1 | S | UX-030 | `onboarding.py`, `models/user.py` |
| UX-033 | Dompet awal + penjelasan saldo awal | P1 | M | UX-030 | `onboarding.py`, `wallet_interactive.py` |
| UX-034 | Notice privasi pemrosesan AI | P1 | S | UX-030 | `onboarding.py` |
| UX-011 | Konfirmasi hapus dompet 2 langkah | P0 | S | — | `wallet_interactive.py:143-161` |
| UX-012 | Konfirmasi hapus budget | P1 | S | — | `menu.py:247-258` |
| UX-013 | Perbaiki dead end menu dompet untuk user baru | P0 | M | UX-002 | `wallet_interactive.py:21-42,85-86` |
| UX-014 | Perbaiki conversation dompet: timeout, tombol Batal, input fleksibel | P1 | M | — | `wallet_interactive.py:48-116,163-242` |
| UX-022 | Pratinjau transaksi untuk confidence rendah/koreksi/transfer | P0 | L | — | `transaction.py` |
| UX-023 | Tombol "Batalkan transaksi terakhir" | P0 | M | UX-022 | `transaction.py`, service baru |
| UX-025 | Tombol aksi di pesan sukses (Laporan/Menu) | P1 | S | — | `transaction.py` |
| UX-043 | Lengkapi `/akun`: zona waktu, dompet utama, status notif | P1 | S | UX-031 | `account.py:60-68` |

### Fase 2 — Keandalan & alur lanjutan (target: minggu 3–6)

| ID | Item | Prioritas | Est | Depends | Lokasi utama |
|---|---|---|---|---|---|
| UX-021 | Persistensi pending transaction (DB/Redis + TTL) | P0 | L | UX-020 | `transaction.py`, model baru |
| UX-024 | Nama file foto unik | P1 | S | — | `transaction.py:124` |
| UX-026 | Cegah transaksi duplikat (double tap) | P1 | M | UX-021 | `transaction.py`, service |
| UX-027 | Dukung voice note (Whisper/Groq) | P1 | L | — | handler baru |
| UX-040 | Pemilih kategori budget berbasis tombol | P1 | M | — | `budget.py`, `menu.py` |
| UX-044 | Tambah/ubah budget dari menu | P1 | M | UX-040 | `menu.py` |
| UX-045 | Pencocokan nama dompet konsisten di semua alur | P1 | M | — | `transaction_service.py` |
| UX-046 | Laporan: label "Selisih" + tampilkan total saldo | P1 | S | — | `report.py:84` |
| UX-047 | Pilih bulan laporan dari UI | P2 | M | — | `menu.py`, `report.py` |
| UX-048 | Ekspor CSV/PDF di samping JSON | P2 | L | UX-047 | `report.py` |
| UX-049 | Fallback dompet tidak ditemukan → tombol buat/pilih | P0 | M | UX-014 | `transaction.py`, `wallet_interactive.py` |

### Fase 3 — Pengukuran, polish, dan pengembangan (target: minggu 7–12)

| ID | Item | Prioritas | Est | Depends | Lokasi utama | Status |
|---|---|---|---|---|---|---|
| UX-050 | Telemetri funnel & error | P1 | M | UX-005 | service baru | done |
| UX-051 | Uji usability 5 pengguna baru | P1 | M | Fase 1 | — | siap (butuh peserta) |
| UX-052 | Audit copywriting menyeluruh | P2 | M | UX-007 | semua handler | done |
| UX-053 | Personalisasi (sapaan, target tabungan) | P2 | L | UX-050 | — | done |
| UX-054 | Dukungan gambar sebagai dokumen | P2 | S | UX-004 | `main.py`, `transaction.py` | done |
| UX-055 | Halaman bantuan in-chat + FAQ | P2 | M | UX-003 | `menu.py` | done |
| UX-056 | Edit/hapus transaksi dari bot | P2 | XL | UX-023 | handler baru | done |

---

## 3. Detail Tiket Prioritas P0/P1

### UX-001 — Tulis ulang `/start`

**Masalah:** Teks lama menyebut bot "membaca teks dari gambar", tidak menyebut pencatatan keuangan, tanpa tombol.
**Dampak:** Pengguna baru tidak paham nilai bot dan tidak tahu langkah berikutnya.
**Scope:**
- Sapaan + 3 contoh pencatatan natural.
- Sebut foto struk, saldo, budget, laporan.
- Tombol inline: `[🚀 Mulai]` (`onboarding_start`) dan `[📋 Buka Menu]` (`menu_utama`).
- Untuk user lama: langsung tampilkan ringkasan + menu.
**Acceptance criteria:**
- [ ] User baru melihat penjelasan fungsi bot dalam < 10 detik membaca.
- [ ] Ada jalur satu klik ke menu.
- [ ] Tidak ada lagi kata "ekstrak teks".
- [ ] `/start` tidak mengirim dua pesan menu bertumpuk.

### UX-002 — `/start` idempoten

**Masalah:** `/start` tidak membuat akun; error lain menyuruh "kirim /start" sehingga terjadi loop.
**Scope:** `ensure_user()` dipanggil di `/start` dan seluruh entry point menu.
**Acceptance criteria:**
- [ ] `/start` pada user baru membuat baris `users`.
- [ ] `/start` berulang tidak membuat duplikat.
- [ ] Pesan error yang menyuruh `/start` benar-benar menyelesaikan masalah.
- [ ] Tidak ada akun "Unknown" tanpa nama yang wajar (fallback nama dari Telegram).

### UX-003 — `/help` + fallback command

**Scope:**
- Command `/help` dan alias `/bantuan`.
- Fallback `MessageHandler(filters.COMMAND)` → kartu bantuan.
- Isi bantuan: catat teks/foto, dompet, budget, laporan, notifikasi, batal, hapus data.
**Acceptance criteria:**
- [ ] `/help`, `/bantuan`, dan command acak mendapat balasan dalam < 2 detik.
- [ ] Kartu bantuan punya tombol `[📋 Menu]`.
- [ ] Semua command nyata tercantum; command yang tidak ada tidak dirujuk.

### UX-004 — Fallback input non-teks

**Scope:** voice, dokumen/gambar sebagai file, sticker, video, lokasi.
**Acceptance criteria:**
- [ ] Setiap jenis input mendapat penjelasan singkat + contoh yang didukung.
- [ ] Voice note menjanjikan dukungan (jika UX-027 belum selesai) tanpa menjanjikan fitur palsu.
- [ ] Tidak ada input yang dibiarkan tanpa balasan.

### UX-005 — Error handling terpusat

**Scope:**
- `app.add_error_handler(error_handler)` di `main.py`.
- Helper `safe_reply()` / `user_error_message()`.
- Hapus semua `f"...{str(e)}"` dari pesan user; log `logger.exception`.
**Acceptance criteria:**
- [ ] Error tak terduga menghasilkan pesan ramah + tombol Coba lagi/Menu.
- [ ] Tidak ada nama env, stack trace, atau pesan library di chat.
- [ ] Error tetap tercatat lengkap di log dengan `update_id`/`user_id`.
- [ ] Callback query selalu `answer()` agar spinner berhenti.

### UX-006 — Hapus pembisuan teks laporan

**Masalah:** Frasa "laporan hari ini" diabaikan padahal tidak ada reply keyboard.
**Acceptance criteria:**
- [ ] Mengetik "laporan hari ini/minggu ini/bulan ini" memunculkan laporan terkait.
- [ ] Jika ReplyKeyboard dipasang (UX-009), frasa yang sama tetap bekerja.
- [ ] Tidak ada teks pengguna yang dibisukan tanpa alasan jelas.

### UX-007 — Jargon & tone

**Peta penggantian:**
| Lama | Baru |
|---|---|
| Unduh Bulan Ini (JSON) | Unduh laporan bulan ini |
| Login Dashboard Web | Buka dashboard |
| Web Auth | Akses dashboard |
| ID Telegram | ID akun |
| Saldo (pada laporan periode) | Selisih bulan ini |
| callback/sesi | (tidak pernah muncul) |
| Anda | kamu |
**Acceptance criteria:**
- [ ] Tidak ada istilah teknis di pesan pengguna.
- [ ] Seluruh handler memakai "kamu" dan sapaan konsisten.
- [ ] Tidak ada campuran "Anda/kamu" dalam satu layar.

### UX-008 — Escape Markdown

**Masalah:** Nama user/dompet/kategori bisa mengandung `_`, `*`, `` ` `` dan mematahkan pesan.
**Scope:** helper `md_escape()`; terapkan ke semua konten dinamis; pertimbangkan migrasi ke HTML.
**Acceptance criteria:**
- [ ] User bernama `A_B` bisa membuka `/akun`.
- [ ] Dompet bernama `my_wallet*` tetap tampil di menu.
- [ ] Kategori budget `biaya_admin` tidak membuat pesan gagal.
- [ ] Ada unit test untuk karakter `_ * [ ] ` `.

### UX-010/011/012 — Konfirmasi aksi destruktif

**Pola wajib:**
1. Tombol aksi → pesan konsekuensi + jumlah data.
2. Tombol `[Ya, hapus permanen]` dan `[Batal]`.
3. Untuk hapus akun: konfirmasi tambahan (ketik `HAPUS` atau tekan tombol kedua).
**Acceptance criteria:**
- [ ] Satu klik tidak pernah menghapus data permanen.
- [ ] Pesan menyebut apa saja yang hilang (jumlah transaksi/dompet/budget).
- [ ] Batal mengembalikan ke layar sebelumnya tanpa perubahan.
- [ ] Setelah hapus, user mendapat tombol `[Mulai lagi]`.

### UX-020 — Callback dompet ≤ 64 byte

**Masalah:** Foto memakai UUID penuh: ±75 byte → `BUTTON_DATA_INVALID`.
**Rencana teknis:**
- Buat token pendek (mis. `w:{pending_id}:{index}`) dengan `pending_id` ≤ 12 karakter.
- Simpan mapping index → wallet ID di state/DB, bukan di callback.
**Acceptance criteria:**
- [ ] Foto dengan 3 dompet menampilkan tombol yang bisa diklik.
- [ ] Tidak ada `callback_data` > 64 byte (unit test).
- [ ] Callback lama/stale menghasilkan pesan jelas, bukan error mentah.

### UX-021 — Persistensi pending transaction

**Masalah:** `pending_transactions` global dict hilang saat restart/serverless.
**Rencana teknis:**
- Tabel `pending_transactions`: `id`, `user_id`, `payload JSON`, `expires_at`, `created_at`.
- TTL 10 menit; cleanup saat akses.
- Alternatif: `ConversationHandler(persistent=True)` + `PicklePersistence`/DB storage.
**Acceptance criteria:**
- [ ] Pilih dompet tetap berhasil setelah proses restart.
- [ ] Pending kedaluwarsa menghasilkan pesan "sesi habis, ulangi" + tombol.
- [ ] Tidak ada kebocoran data antar-user.

### UX-022 — Pratinjau transaksi

**Trigger pratinjau:** `confidence < 0.8`, tipe `CORRECTION`, atau `TRANSFER`.
**Isi pratinjau:** jenis, nominal, deskripsi, kategori, dompet, tanggal.
**Tombol:** `[✅ Simpan] [✏️ Ubah] [❌ Batal]`.
**Acceptance criteria:**
- [ ] Koreksi saldo tidak pernah mengubah data tanpa persetujuan.
- [ ] Transfer menampilkan dompet asal/tujuan + biaya admin sebelum simpan.
- [ ] `[✏️ Ubah]` membuka form singkat (nominal/jenis/kategori/dompet).
- [ ] Timeout 5 menit → batal otomatis dengan pesan.

### UX-023 — Batalkan transaksi terakhir

**Scope:**
- Tombol `[↩️ Batalkan]` di pesan sukses, valid 5 menit.
- Service `undo_last_transaction(user_id)` mengembalikan saldo & menghapus transaksi.
- Konfirmasi ringan sebelum undo.
**Acceptance criteria:**
- [ ] Undo mengembalikan saldo dompet persis seperti sebelum transaksi.
- [ ] Undo hanya untuk transaksi terakhir milik user tersebut.
- [ ] Setelah 5 menit tombol memberi pesan kedaluwarsa.
- [ ] Ada test saldo sebelum/sesudah.

### UX-030/031/032/033 — Onboarding wizard

**Langkah:**
1. Konfirmasi akun (pakai nama Telegram, tanpa form).
2. Zona waktu: `[WIB] [WITA] [WIT]` + penjelasan singkat.
3. Dompet awal: `[Pakai "Utama"] [Buat dompet] [Lewati]`; jika buat, minta nama + saldo opsional.
4. Notifikasi: `[Aktifkan] [Nanti saja]`.
5. Selesai: contoh transaksi + menu keyboard.

**Acceptance criteria:**
- [ ] User baru bisa menyelesaikan onboarding ≤ 4 tap tanpa mengetik (kecuali nama dompet).
- [ ] Zona waktu tersimpan dan dipakai di laporan.
- [ ] Notifikasi hanya aktif jika user setuju.
- [ ] Onboarding bisa dilewati dan diulang dari `/akun`.
- [ ] Data onboarding tidak hilang di tengah jalan (state persisten).

### UX-040 — Budget berbasis tombol

**Scope:**
- `/budget` tanpa argumen menampilkan daftar + tombol `[➕ Atur budget]`.
- Pilih kategori dari daftar kanonis (tombol), lalu masukkan nominal.
- Tetap dukung `/budget makanan 1jt` untuk pengguna lama.
**Acceptance criteria:**
- [ ] Pengguna tidak perlu hafal nama kategori.
- [ ] Salah ketik kategori mendapat saran kategori terdekat.
- [ ] Tambah/ubah budget selesai ≤ 3 langkah.

### UX-043 — Informasi akun lengkap

**Isi `/akun`:** nama, ID akun, zona waktu, dompet utama, jumlah dompet, status notifikasi, tombol ubah zona waktu/notifikasi, hapus akun.
**Acceptance criteria:**
- [ ] Semua info yang memengaruhi laporan terlihat.
- [ ] Ada tombol kembali ke menu.
- [ ] Tidak ada istilah "ID Telegram".

### UX-050 — Telemetri funnel & error

**Scope:**
- Tabel `ux_events` (telegram_id, event, data JSON) + migrasi Alembic.
- Event: `onboarding_started`, `onboarding_completed`, `transaction_created`,
  `first_transaction`, `fifth_transaction`, `error`, `ai_duration`.
- Penulisan best-effort: kegagalan telemetri tidak menggagalkan alur bot.
- Dashboard metrik mingguan di `/metrics` + endpoint `/api/metrics/ux`.
**Acceptance criteria:**
- [x] Funnel onboarding → transaksi pertama → transaksi kelima tercatat.
- [x] Error global tercatat tanpa menyimpan isi pesan/nominal.
- [x] Milestone pertama/kelima tidak tercatat ganda.
- [x] Durasi AI (`text`/`image`) tercatat dalam milidetik.
- [x] Dashboard metrik mingguan menampilkan funnel, error, dan durasi AI.

### UX-051 — Uji usability 5 pengguna baru

**Scope:**
- Panduan sesi, script moderator, 9 skenario tugas, dan lembar catatan.
- Metrik: waktu ke transaksi pertama, success rate, SEQ, temuan severity.
- Laporan hasil + action item di `USABILITY-REPORT.md`.
**Acceptance criteria:**
- [x] Panduan dan template laporan tersedia.
- [ ] 5 peserta baru menjalankan sesi.
- [ ] Median transaksi pertama < 60 detik.
- [ ] Semua temuan Critical/High punya action item.
- [ ] Laporan diisi dan UX-051 ditandai selesai.

> **Status:** paket uji siap; eksekusi menunggu 5 peserta nyata.

### UX-052 — Audit copywriting menyeluruh

**Scope:**
- Istilah teknis (JSON, CSV, token, error) diganti bahasa manusia.
- Sapaan "kamu" konsisten di bot dan halaman web.
- Label tombol memakai kata kerja dan menjelaskan hasilnya.
- Zona waktu ditampilkan sebagai WIB/WITA/WIT, bukan nama teknis.
- Pesan fallback dokumen diselaraskan dengan dukungan JPG/PNG (UX-054).
**Acceptance criteria:**
- [x] Tidak ada "JSON", "CSV", "ID Telegram", atau "Anda" di pesan pengguna.
- [x] Label unduh menjadi "Unduh data" dan "Unduh tabel".
- [x] Onboarding menyebut kemajuan 1/4 sampai 4/4.
- [x] Preview transaksi tidak menampilkan persentase keyakinan AI.
- [x] Ada test otomatis yang menjaga istilah terlarang tidak kembali.

### UX-053 — Personalisasi sapaan & target tabungan

**Scope:**
- Sapaan dapat diatur dari menu Akun dan dipakai di menu utama.
- Target tabungan global; progres dihitung dari total saldo semua dompet.
- Nominal cepat (Rp1 juta/Rp5 juta/Rp10 juta) atau input manual.
- Hapus target memakai konfirmasi dua langkah.
**Acceptance criteria:**
- [x] Sapaan tersimpan dan muncul di menu utama serta info akun.
- [x] Target tabungan dan progresnya terlihat di menu utama dan info akun.
- [x] Target bisa diubah/dihapus tanpa menyentuh saldo dompet.
- [x] Ada test otomatis untuk progres dan persistensi.

### UX-056 — Riwayat, edit, dan hapus transaksi

**Scope:**
- `/riwayat` dan tombol Menu → Riwayat menampilkan 8 transaksi terbaru
  dengan navigasi halaman.
- Detail transaksi bisa dibuka, lalu diedit atau dihapus.
- Edit mendukung nominal, keterangan, dan kategori dengan tipe yang sama.
- Hapus memakai konfirmasi dua langkah dan mengembalikan saldo dompet.
- Transfer/biaya admin tidak bisa diedit/dihapus karena terdiri dari
  beberapa baris yang saling terkait.
**Acceptance criteria:**
- [x] Riwayat bisa dibuka tanpa menghafal command.
- [x] Semua `callback_data` riwayat/edit/hapus ≤ 64 byte.
- [x] Edit nominal menyesuaikan saldo dompet sebesar selisihnya.
- [x] Hapus transaksi mengembalikan saldo dan menghapus baris di Sheets.
- [x] Transfer dan biaya admin mendapat penjelasan, bukan layar buntu.
- [x] Ada test otomatis untuk hapus, edit nominal, kategori, dan transfer.

### UX-055 — Pusat bantuan in-chat

**Scope:**
- `/help` dan `menu_bantuan` membuka pusat bantuan dengan tombol topik.
- Topik: catat transaksi, dompet, budget, laporan, notifikasi, akun,
  privasi AI, dan error/sesi.
- Setiap topik punya tombol kembali ke pusat bantuan dan menu utama.
**Acceptance criteria:**
- [x] Semua topik bisa dibuka tanpa mengetik command.
- [x] `callback_data` semua tombol ≤ 64 byte.
- [x] Tidak ada layar buntu: selalu ada tombol kembali/menu.

---

## 4. Definition of Done (berlaku semua tiket)

- [ ] Kode mengikuti pola handler/service yang ada.
- [ ] Tidak ada pesan error teknis ke pengguna.
- [ ] Ada test otomatis untuk logika baru (unit/integration).
- [ ] Test manual alur terkait di `QA-CHECKLIST.md` lulus.
- [ ] Copywriting sesuai `UX-GUIDELINES.md` dan `MESSAGE-TEMPLATES.md`.
- [ ] `callback_data` ≤ 64 byte dan aman untuk nama/kategori panjang.
- [ ] Tidak ada state kritis hanya di memori proses.
- [ ] Logging cukup untuk debugging tanpa membocorkan data sensitif.
- [ ] Dokumentasi singkat diperbarui (README/TODO bila perlu).

---

## 5. Di Luar Scope (fase ini)

- Rebranding visual besar atau web dashboard redesign.
- Multi-bahasa (i18n) — fokus Bahasa Indonesia dulu.
- Integrasi bank/e-wallet otomatis.
- Sistem langganan/pembayaran.
- Machine learning model sendiri; tetap gunakan Groq.

---

## 6. Catatan Eksekusi

1. Kerjakan Fase 0 berurutan; UX-005 dan UX-008 sebaiknya lebih dulu agar perubahan berikutnya tidak menambah error baru.
2. UX-020 + UX-021 harus satu paket: memperbaiki callback tanpa persistensi hanya memindahkan masalah.
3. UX-022 + UX-023 harus satu paket: pratinjau tanpa undo masih menyisakan risiko data salah.
4. Setiap fase diakhiri uji usability singkat dan update `ROADMAP.md`.
