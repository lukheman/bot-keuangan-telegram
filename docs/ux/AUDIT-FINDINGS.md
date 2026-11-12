# AUDIT FINDINGS — Ringkasan Temuan UX

> Audit statis terhadap kode dan teks pesan bot (tanpa runtime test).
> Tanggal audit: 12 November 2026. Skor kemudahan penggunaan: **5/10**.
>
> Asumsi yang ditandai: produksi memakai webhook Vercel/serverless
> (berdasarkan `app/api/index.py`, `vercel.json`, `.vercel/`).

---

## Metodologi

- Membaca seluruh handler Telegram (`main.py`, `bot/handlers/*`), service
  (`app/services/*`), model, prompt AI, dan konfigurasi.
- Menelusuri alur: `/start` → pendaftaran → menu → transaksi teks/foto →
  laporan → pengaturan akun → aksi destruktif.
- Memeriksa batas teknis Telegram (panjang `callback_data` 64 byte), penanganan
  error, persistensi state, dan konsistensi copy.
- Tidak menguji di perangkat/akun nyata; temuan perilaku bersifat pembacaan kode.

---

## Skor per Dimensi

| Dimensi | Skor | Catatan |
|---|---|---|
| Kejelasan | 5/10 | Menu bagus, `/start` menyesatkan, banyak jargon |
| Jumlah langkah minimum | 7/10 | Pencatatan teks sangat cepat; budget/dompet bertele-tele |
| Konsistensi | 4/10 | Campur command/menu, "Anda/kamu", label tidak seragam |
| Pencegahan & pemulihan error | 3/10 | Dead end, pesan teknis, tanpa undo, tanpa `/help` |
| Aksesibilitas pengguna awam | 4/10 | Butuh hafal command dan nama kategori |
| Kecepatan respons | 7/10 | Ada pesan progres; bergantung latensi AI |

---

## Temuan (pemetaan ke backlog)

| ID | Prioritas | Temuan | Lokasi | Tiket |
|---|---|---|---|---|
| T1 | Tinggi | `/start` masih menjelaskan OCR gambar, bukan pencatatan keuangan; tanpa tombol menu | `main.py:68-79` | UX-001 |
| T2 | Tinggi | Instruksi "kirim /start" salah karena `/start` tidak mendaftarkan user | `report.py:369-372`, `budget_service.py:150` | UX-002 |
| T3 | Tinggi | Hapus akun/dompet/budget tanpa konfirmasi | `account.py:70-93`, `wallet_interactive.py:143-161`, `menu.py:247-258` | UX-010/011/012 |
| T4 | Tinggi | `callback_data` pemilihan dompet dari foto ±75 byte (> 64) | `transaction.py:146,158-162` | UX-020 |
| T5 | Tinggi | Pending transaction hanya di memori; hilang saat restart/serverless | `transaction.py:18,57-73` | UX-021 |
| T6 | Tinggi | Hasil AI & koreksi saldo disimpan otomatis tanpa pratinjau/undo | `transaction.py:226-340`, `transaction_service.py:298-334` | UX-022/023 |
| T7 | Tinggi | Tidak ada `/help`; command tak dikenal & input non-teks dibisukan | `main.py:81-141`, `transaction.py:204-207` | UX-003/004 |
| T8 | Tinggi | Error teknis ditampilkan mentah; tidak ada global error handler | banyak handler | UX-005 |
| T9 | Tinggi | Teks "laporan hari ini" dibisukan padahal reply keyboard tidak ada | `transaction.py:211-219` | UX-006 |
| T10 | Sedang | Onboarding tidak ada: zona waktu, dompet awal, consent notifikasi | `models/user.py:15-16`, `account.py:14-38` | UX-030–034 |
| T11 | Sedang | Menu dompet user baru dead end (gagal setelah 2 langkah) | `wallet_interactive.py:21-42,85-86` | UX-013 |
| T12 | Sedang | Budget harus mengetik nama kategori persis; menu hanya hapus | `budget.py`, `budget_service.py:96-118`, `menu.py:144-170` | UX-040/044 |
| T13 | Sedang | Jargon & label menyesatkan (JSON, Auth, "Saldo" laporan) | `menu.py:233`, `account.py:135`, `report.py:84` | UX-007/046 |
| T14 | Sedang | Laporan "7 hari" sebenarnya 8 hari | `report_service.py:66-68` | UX-041 |
| T15 | Sedang | Konten dinamis tidak di-escape untuk Markdown | `account.py:60-68`, `wallet_interactive.py:29-34` | UX-008 |
| T16 | Sedang | Command tidak konsisten (`/bulan` dirujuk tapi tidak ada, `/laporan` tidak ada) | `main.py:47-59`, `report.py:169` | UX-009 |
| T17 | Sedang | Conversation dompet menjebak: tanpa timeout, larangan spasi, parsing saldo kaku | `wallet_interactive.py:48-116,163-242` | UX-014 |
| T18 | Sedang | URL dashboard hardcoded | `account.py:125` | UX-042 |
| T19 | Rendah | Notifikasi harian aktif default tanpa persetujuan | `models/user.py:16` | UX-032 |
| T20 | Rendah | `/akun` tidak menampilkan zona waktu/status notifikasi | `account.py:60-68` | UX-043 |
| T21 | Rendah | Nama file foto sementara bisa bentrok | `transaction.py:124` | UX-024 |
| T22 | Rendah | Tidak ada pemberitahuan privasi pemrosesan AI | `groq_service.py` | UX-034 |

> **Tindak lanjut 2026-11-12:** T13 sudah dituntaskan lewat UX-007, UX-046,
> dan UX-052. Istilah JSON/CSV, "ID Telegram", sapaan "Anda", dan persentase
> keyakinan AI tidak lagi tampil di pesan pengguna.

---

## Kekuatan yang Harus Dipertahankan

- Pencatatan teks natural yang cepat dan langsung memberi umpan balik.
- Menu inline berkelompok dengan emoji dan tombol kembali.
- Visual budget (bar, ikon status) informatif.
- Laporan per kategori dan peringatan budget otomatis.
- Pemisahan handler/service yang cukup rapi untuk dikembangkan.
- Dukungan web dashboard sebagai jalur lanjutan.

---

## Catatan Asumsi & Batasan

- Tidak ada pengujian runtime; beberapa temuan (mis. hilangnya state di
  serverless) bergantung pada konfigurasi deployment.
- Skor bersifat judgement kualitatif, bukan hasil pengukuran pengguna.
- Temuan keamanan web (verifikasi hash Telegram) tidak diaudit mendalam karena
  fokus pada UX bot; tetap disarankan ditinjau terpisah.
