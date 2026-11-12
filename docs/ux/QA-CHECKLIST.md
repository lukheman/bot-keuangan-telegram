# QA CHECKLIST — UX Bot Keuangan

> Checklist manual + otomatis untuk memastikan perbaikan tidak merusak alur.
> Jalankan penuh sebelum setiap rilis; minimal "Smoke Test" sebelum merge.

---

## 0. Persiapan

- [ ] Siapkan 3 akun uji: **baru**, **lama dengan 1 dompet**, **lama dengan 3 dompet**.
- [ ] Siapkan data: 1 transaksi hari ini, 1 transaksi minggu ini, 1 transaksi bulan lalu, 1 budget aktif.
- [ ] Siapkan gambar: struk jelas, struk blur, foto bukan struk, screenshot tanpa nominal.
- [ ] Uji di dua mode: polling lokal dan webhook (staging).
- [ ] Catat versi commit dan waktu uji.

---

## 1. Smoke Test (wajib sebelum merge)

| # | Skenario | Langkah | Ekspektasi | Tiket |
|---|---|---|---|---|
| S1 | `/start` user baru | Kirim `/start` | Penjelasan fungsi + tombol Mulai/Menu; akun dibuat | UX-001, UX-002 |
| S2 | `/help` | Kirim `/help` | Kartu bantuan + tombol Menu | UX-003 |
| S3 | Command acak | Kirim `/xyz` | Balasan bantuan, bukan diam | UX-003 |
| S4 | Teks biasa | Kirim `kopi 20rb` | Tercatat + saldo + tombol aksi | UX-025 |
| S5 | Teks bukan transaksi | Kirim `halo apa kabar` | Pesan ramah + contoh + tombol | UX-022 |
| S6 | Foto struk, 1 dompet | Kirim foto | Tercatat tanpa error | UX-020 |
| S7 | Foto struk, 3 dompet | Kirim foto tanpa caption | Tombol dompet tampil dan bisa diklik | UX-020 |
| S8 | Hapus akun | Menu → Akun → Hapus | Butuh konfirmasi 2 langkah | UX-010 |
| S9 | Markdown | Set nama `A_B`, buka `/akun` | Pesan tampil normal | UX-008 |
| S10 | Error | Matikan `GROQ_API_KEY` sementara, kirim teks | Pesan ramah, bukan detail env | UX-005 |
| S11 | Bantuan in-chat | Menu → Bantuan → pilih `🎯 Budget` | Penjelasan topik muncul + tombol Kembali/Menu | UX-055 |
| S12 | Telemetri | Selesaikan onboarding lalu catat 1 transaksi | Ada event `onboarding_completed` dan `first_transaction` di `ux_events` | UX-050 |

---

## 2. Journey Test — Pengguna Baru

| # | Langkah | Ekspektasi |
|---|---|---|
| J1 | Kirim `/start` | Wizard onboarding langsung tampil |
| J2 | Pilih zona waktu WIB/WITA/WIT | Tersimpan; lanjut ke langkah notifikasi |
| J3 | Pilih `[🔔 Aktifkan]` atau `[🔕 Nanti saja]` | Status notifikasi tersimpan |
| J4 | Ketik `Tunai` atau tekan `[💵 Pakai “Tunai”]` | Lanjut ke pertanyaan saldo awal |
| J5 | Ketik `500rb` atau tekan `[Saldo 0]` | Dompet pertama dibuat, saldo sesuai |
| J6 | Baca notice privasi → tekan `[✅ Saya paham, mulai]` | Onboarding selesai, tombol menu tampil |
| J7 | Kirim `kopi 20rb` | Transaksi tercatat < 5 detik |
| J8 | Cek saldo | Saldo Tunai berkurang Rp20.000 |
| J9 | Buka laporan hari ini | Transaksi muncul, tanggal sesuai zona waktu |
| J10 | Kirim `/start` lagi | Ringkasan + menu, onboarding tidak diulang |

**Kriteria lulus:** J1–J10 selesai < 60 detik tanpa membaca dokumentasi.

---

## 3. Journey Test — Pengguna Lama

| # | Langkah | Ekspektasi |
|---|---|---|
| L1 | Kirim `/start` | Ringkasan hari ini + menu |
| L2 | Buka Dompet | Daftar dompet + total saldo |
| L3 | Tambah dompet "BCA" saldo `500rb` | Dompet dibuat, saldo Rp500.000 |
| L4 | Transfer `transfer bca ke tunai 100rb` | Pratinjau transfer muncul: dompet asal/tujuan + biaya admin |
| L5 | Tekan `[✅ Simpan]` lalu cek saldo kedua dompet | Saldo berkurang/bertambah sesuai, biaya admin (jika ada) tercatat |
| L6 | Tekan `[↩️ Batalkan transaksi]` pada pesan sukses pengeluaran | Saldo kembali seperti sebelumnya, transaksi hilang dari laporan |
| L7 | Buka Budget → `[➕ Atur budget]` → pilih kategori → ketik `1jt` | Tersimpan dalam ≤ 3 langkah tanpa hafal nama kategori |
| L8 | Catat pengeluaran kategori tersebut | Peringatan muncul pada 80%/100% |
| L9 | Buka Laporan → `[📅 Pilih Bulan]` → pilih bulan lalu | Laporan bulan tersebut tampil tanpa mengetik command |
| L10 | Unduh JSON lalu CSV | Dua file terkirim; CSV terbuka rapi di spreadsheet |

---

## 4. Edge Case & Pemulihan

### Input & AI
- [ ] `beli kopi 20rb` → EXPENSE, Makanan, nominal 20.000.
- [ ] `gaji 5jt` → INCOME, nominal 5.000.000.
- [ ] `transfer dari bri ke tunai 500rb admin 5k` → TRANSFER + pratinjau.
- [ ] `ternyata saldo gopay saya 50000` → CORRECTION + pratinjau.
- [ ] `BCA ke Mandiri 200rb` (tanpa kata transfer) → EXPENSE + confidence rendah/pratinjau.
- [ ] `beli kopi 15rb terus transfer 50rb ke tunai` → hanya transaksi pertama, ada catatan/pratinjau.
- [ ] Teks tanpa nominal (`makan siang`) → pesan ramah, tidak menyimpan.
- [ ] Teks dengan nominal aneh (`makan 0`) → ditolak dengan penjelasan.
- [ ] Emoji dan huruf besar (`BELI KOPI 20RB`) → tetap dikenali.
- [ ] Teks sangat panjang (> 500 karakter) → diproses atau ditolak dengan jelas.
- [ ] Kirim struk sebagai dokumen JPG/PNG → diproses seperti foto biasa.
- [ ] Kirim dokumen PDF/non-gambar → pesan format yang jelas, bukan error.

### Dompet
- [ ] Nama dompet dengan spasi (`Bank Mandiri`) → diterima.
- [ ] Nama dompet dengan `_` atau `*` → tampil tanpa mematahkan pesan.
- [ ] Nama dompet duplikat (beda kapital) → ditolak dengan saran.
- [ ] Saldo `Rp500.000`, `500rb`, `500000`, `0` → terbaca benar.
- [ ] Saldo negatif → ditolak atau dikonfirmasi (tentukan kebijakan).
- [ ] Dompet tidak ditemukan saat transaksi → tombol buat/pilih, bukan dead end.
- [ ] Hapus dompet berisi transaksi → konfirmasi menyebut jumlah transaksi.
- [ ] Hapus dompet terakhir → dicegah atau dibuat dompet "Utama" otomatis.

### Budget
- [ ] `/budget` tanpa argumen → daftar + tombol tambah.
- [ ] Pilih kategori dari tombol → nominal → tersimpan.
- [ ] Nama kategori salah → saran kategori terdekat.
- [ ] Nominal `1jt`, `500rb`, `1,5jt`, `500.000` → benar.
- [ ] Hapus budget → konfirmasi, transaksi tidak terhapus.
- [ ] Budget 80%, 100%, >100% → ikon dan pesan sesuai.

### Laporan
- [ ] Hari ini, 7 hari, bulan ini, bulan lalu.
- [ ] Pilih bulan dari tombol → laporan bulan tersebut muncul.
- [ ] Tidak ada transaksi → pesan kosong yang ramah, total saldo tetap tampil.
- [ ] Laporan panjang > 4096 karakter → terpotong rapi, tombol di akhir.
- [ ] Label "Selisih periode" dan total saldo dompet tampil terpisah.
- [ ] Unduh JSON dan CSV → file valid dan bisa dibuka.
- [ ] Zona waktu WIB/WITA/WIT menghasilkan tanggal yang benar.
- [ ] Transaksi pukul 23:59 dan 00:01 masuk ke tanggal lokal yang benar.

### Notifikasi
- [ ] User opt-in menerima laporan 00:00 lokal.
- [ ] User opt-out tidak menerima.
- [ ] Tidak ada transaksi → tidak mengirim spam (atau kirim pesan singkat sesuai keputusan).
- [ ] Kirim ganda dicegah lewat `last_daily_report_at`.
- [ ] Cron webhook dengan secret salah → 403.

### Aksi destruktif
- [ ] Hapus akun: 1 klik tidak menghapus; konfirmasi kedua menghapus.
- [ ] Hapus akun: data transaksi/dompet/budget ikut terhapus.
- [ ] Hapus akun: setelah selesai ada tombol Mulai lagi.
- [ ] Hapus dompet: batal tidak mengubah apa pun.
- [ ] Hapus budget: batal tidak mengubah apa pun.
- [ ] Undo transaksi: saldo, transaksi, dan biaya admin konsisten.

### Error & state
- [ ] Matikan database sementara → pesan ramah, bukan stack trace.
- [ ] Matikan layanan AI → pesan ramah + tombol coba lagi.
- [ ] Restart server saat menunggu pilih dompet → pilihan tetap/beri pesan jelas.
- [ ] Klik tombol lama (> 10 menit) → pesan sesi kedaluwarsa.
- [ ] Klik tombol dua kali cepat → tidak membuat dua transaksi.
- [ ] Dua user berbeda menekan tombol dompet bersamaan → tidak saling tertukar.
- [ ] Callback tanpa handler → minimal ada feedback.
- [ ] Pesan sama diedit dua kali → tidak error "message is not modified".
- [ ] Timeout conversation 5 menit → keluar otomatis dengan pesan.

### Bantuan & telemetri
- [ ] `/help` dan `menu_bantuan` membuka pusat bantuan yang sama.
- [ ] Semua 8 topik FAQ bisa dibuka dan punya tombol Kembali + Menu.
- [ ] `help_home` kembali ke daftar topik, bukan pesan kedaluwarsa.
- [ ] Event onboarding/transaksi/error masuk ke `ux_events` tanpa isi pesan.
- [ ] Database telemetri gagal → alur transaksi tetap berhasil.
- [ ] Milestone `first_transaction`/`fifth_transaction` hanya tercatat sekali.
- [ ] Event `ai_duration` menyimpan `kind`, `duration_ms`, dan `ok` saja.
- [ ] `/api/metrics/ux` menolak tanpa `HERMES_API_KEY` (401).
- [ ] `/metrics?api_key=…` menampilkan tabel mingguan tanpa error.
- [ ] Angka funnel/durasi AI di dashboard berubah setelah transaksi baru.

### Copywriting (UX-052)
- [ ] Semua pesan memakai "kamu", bukan "Anda".
- [ ] Tidak ada JSON/CSV/ID Telegram/token di pesan pengguna.
- [ ] Tombol unduh berbunyi "Unduh data" dan "Unduh tabel".
- [ ] Zona waktu tampil sebagai WIB/WITA/WIT, bukan nama teknis.
- [ ] Onboarding menunjukkan kemajuan 1/4 sampai 4/4.
- [ ] Dokumen JPG/PNG tidak disuruh dikirim ulang sebagai foto biasa.
- [ ] Pratinjau transaksi tidak menampilkan persentase keyakinan AI.

### Personalisasi (UX-053)
- [ ] Menu Akun → `Atur sapaan` → ketik nama → menu utama memakai sapaan itu.
- [ ] Target tabungan `10jt` → progres muncul di menu utama dan info akun.
- [ ] Tambah saldo dompet → progres target ikut naik.
- [ ] Ganti target lewat nominal cepat → progres dihitung ulang.
- [ ] Hapus target → butuh konfirmasi; saldo dompet tidak berubah.
- [ ] Target tercapai → pesan "Target tercapai!", bukan sisa negatif.

### Riwayat & edit/hapus (UX-056)
- [ ] Menu → `🧾 Riwayat` dan `/riwayat` menampilkan transaksi terbaru.
- [ ] Tombol `Berikutnya`/`Sebelumnya` membuka halaman riwayat lain.
- [ ] Ketuk transaksi → detail menampilkan nominal, kategori, dompet, tanggal.
- [ ] Edit nominal `25rb` → nominal berubah dan saldo dompet menyesuaikan.
- [ ] Edit keterangan dan kategori → detail langsung diperbarui.
- [ ] Hapus → minta konfirmasi; saldo kembali seperti sebelum transaksi.
- [ ] Transaksi transfer/biaya admin menampilkan penjelasan, bukan error.
- [ ] Setelah edit/hapus, tombol Riwayat dan Menu tetap tersedia.

---

## 5. Non-Fungsional

| Aspek | Cara uji | Target |
|---|---|---|
| Waktu balas awal | Stopwatch/Log | < 1 detik |
| Waktu parsing AI | Log durasi | < 5 detik P95 |
| Waktu buka menu | Log durasi | < 1 detik |
| `callback_data` | Unit test | ≤ 64 byte |
| Kebocoran data | Cek pesan error | Tidak ada detail internal |
| Isolasi user | Dua akun paralel | Tidak ada data tertukar |
| Logging | Cek log | Ada `user_id`, `update_id`, error lengkap |
| Aksesibilitas copy | Baca tanpa konteks | Bisa dipahami awam |

---

## 6. Otomatisasi yang Perlu Dibuat

- [ ] Unit test: parser nominal (`1jt`, `500rb`, `1,5jt`, `Rp500.000`).
- [ ] Unit test: `callback_data` ≤ 64 byte untuk semua tombol.
- [ ] Unit test: escape Markdown/HTML untuk nama dengan karakter khusus.
- [ ] Unit test: `undo_transaction` mengembalikan saldo.
- [ ] Unit test: pending transaksi tersimpan di DB dan tidak bisa dipakai dua kali.
- [ ] Unit test: duplikasi transaksi ditolak.
- [ ] Integration test: onboarding → transaksi → laporan (DB sementara).
- [ ] Integration test: multi-dompet via callback.
- [ ] Contract test: semua command terdaftar punya handler.
- [ ] Snapshot test: teks pesan utama sesuai `MESSAGE-TEMPLATES.md`.

---

## 7. Kriteria Rilis

Rilis dinyatakan siap jika:
- [ ] Semua Smoke Test lulus.
- [ ] Tidak ada bug P0 terbuka.
- [ ] Journey pengguna baru lulus < 60 detik.
- [ ] Tidak ada error rate baru di log 24 jam staging.
- [ ] `BACKLOG.md` diperbarui.
- [ ] Catatan rilis ditulis (apa yang berubah untuk pengguna).
