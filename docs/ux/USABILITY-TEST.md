# PANDUAN UJI USABILITY (UX-051)

> Tujuan: memastikan pengguna baru bisa menyelesaikan transaksi pertama
> < 60 detik tanpa dibantu, serta menemukan fitur utama lain tanpa menghafal
> command. Panduan ini dipakai bersama `USABILITY-REPORT.md`.

---

## 1. Target & Metrik

| Metrik | Target |
|---|---|
| Waktu ke transaksi pertama | median < 60 detik |
| Berhasil catat transaksi tanpa bantuan | 5/5 peserta |
| Berhasil edit/hapus lewat Riwayat | ≥ 4/5 peserta |
| Berhasil atur budget | ≥ 4/5 peserta |
| Berhasil unduh laporan | ≥ 4/5 peserta |
| Rata-rata SEQ (1–7) | ≥ 5,5 |
| Temuan severity Critical/High | 0 yang lolos ke rilis |

**SEQ (Single Ease Question):** setelah setiap tugas, tanyakan
"Seberapa mudah tugas ini? 1 = sangat sulit, 7 = sangat mudah."

---

## 2. Peserta

- 5 orang yang **belum pernah** memakai bot ini.
- Kriteria: punya Telegram aktif, terbiasa chat, usia/pekerjaan bervariasi.
- Minimal 2 peserta yang mengaku "tidak paham istilah keuangan digital".
- Tidak merekrut developer/tester yang sudah tahu alur bot.

---

## 3. Persiapan Moderator (15 menit sebelum sesi)

1. Siapkan akun Telegram baru untuk peserta (atau minta peserta memakai akun
   pribadinya dengan izin).
2. Pastikan bot online dan `TELEGRAM_TOKEN`, `GROQ_API_KEY`, serta database
   produksi/staging aktif.
3. Siapkan tautan bot dan kertas catatan.
4. Minta izin rekam layar/suara. Jelaskan data hanya untuk perbaikan produk.
5. Jangan menjelaskan fitur sebelum tugas dimulai.

---

## 4. Script Pembuka

> "Terima kasih sudah membantu. Saya sedang menguji sebuah bot pencatatan
> keuangan, bukan menguji kamu. Tidak ada jawaban salah. Saya akan memberi
> beberapa tugas, dan kamu bisa bicara sambil mencoba. Kalau bingung, itu
> justru informasi berharga. Boleh saya rekam layar dan suara untuk catatan?"

Setelah peserta setuju, kirim tautan bot dan mulai tugas 1.

**Aturan moderator:**
- Diam dulu saat peserta mencoba. Catat friksi, jangan langsung menolong.
- Bantuan hanya diberikan setelah 90 detik atau jika peserta menyerah.
- Catat setiap bantuan sebagai "dibantu", bukan "berhasil mandiri".
- Jangan menyebut nama tombol/command sebelum peserta menemukannya.

---

## 5. Skenario Tugas

| # | Tugas | Kriteria berhasil | Batas waktu |
|---|---|---|---|
| 1 | Daftar dan catat pengeluaran `kopi 20rb` | Transaksi tersimpan, saldo berubah | 60 detik |
| 2 | Kirim foto struk belanja | Bot membaca/menampilkan pratinjau, transaksi tersimpan | 90 detik |
| 3 | Lihat laporan bulan ini | Ringkasan bulan berjalan tampil | 45 detik |
| 4 | Unduh laporan sebagai tabel | File terunduh | 60 detik |
| 5 | Atur budget kategori Makanan `500rb` | Budget tersimpan dan tampil | 90 detik |
| 6 | Ubah nominal transaksi pertama lewat Riwayat | Nominal berubah, saldo menyesuaikan | 90 detik |
| 7 | Hapus transaksi uji dan konfirmasi | Transaksi hilang, saldo kembali | 60 detik |
| 8 | Atur sapaan dan target tabungan `10jt` | Sapaan/target tampil di menu | 90 detik |
| 9 | Temukan bantuan cara transfer | Pusat bantuan/topik transfer terbuka | 45 detik |

**Setelah setiap tugas:** ajukan SEQ dan catat momen kebingungan.

---

## 6. Pertanyaan Debrief

1. Menurutmu bot ini untuk apa?
2. Bagian mana yang paling membingungkan? Kenapa?
3. Apakah ada kata/tombol yang tidak kamu pahami?
4. Kalau lupa cara mencatat, apa yang akan kamu lakukan?
5. Apakah kamu percaya saldo dan laporannya? Apa yang membuat ragu?
6. Fitur apa yang paling berguna? Fitur apa yang tidak kamu temukan?
7. Skor keseluruhan 1–10, dan alasannya?

---

## 7. Lembar Catatan

Isi satu baris per peserta/tugas. Salin ke `USABILITY-REPORT.md` setelah sesi.

| Peserta | Tugas | Berhasil? | Dibantu? | Waktu | SEQ | Catatan friksi |
|---|---|---|---|---|---|---|
| P1 | 1 |  |  |  |  |  |
| P1 | 2 |  |  |  |  |  |
| … | … |  |  |  |  |  |

**Temuan baru:** tulis kalimat observasi, bukan opini. Contoh:
"P1 mengetuk 'Laporan' lalu berhenti 12 detik karena mencari tombol unduh."

---

## 8. Etika & Privasi

- Jangan menyimpan isi pesan/nominal asli peserta di dokumen publik.
- Ganti nama peserta dengan kode P1–P5.
- Hapus rekaman setelah temuan dicatat, kecuali peserta mengizinkan.
- Data telemetri (`ux_events`) tidak berisi isi pesan; aman untuk analisis.

---

## 9. Setelah Sesi

1. Isi `USABILITY-REPORT.md` maksimal 24 jam setelah sesi.
2. Kelompokkan temuan: Critical / High / Medium / Low.
3. Buat action item dengan pemilik dan tiket backlog baru.
4. Update `BACKLOG.md`, `ROADMAP.md`, dan `QA-CHECKLIST.md`.
