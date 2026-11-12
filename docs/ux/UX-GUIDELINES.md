# UX GUIDELINES — Bot Keuangan Telegram

> Standar desain percakapan yang wajib diikuti saat menulis pesan, tombol, dan
> alur baru. Tujuannya: pengguna awam bisa memakai bot tanpa panduan tambahan.

---

## 1. Sepuluh Prinsip

1. **Satu pesan, satu tujuan.** Jangan gabungkan instruksi, laporan, dan promosi
   dalam satu pesan panjang.
2. **Selalu ada jalan keluar.** Setiap layar harus punya minimal satu tombol
   navigasi (Menu/Kembali/Batal).
3. **Jangan pernah diam.** Semua input—termasuk yang salah—mendapat balasan.
4. **Konfirmasi sebelum merusak.** Tidak ada penghapusan permanen dalam satu klik.
5. **Tunjukkan, jangan jelaskan.** Beri contoh nyata, bukan dokumentasi panjang.
6. **Bahasa manusia, bukan istilah sistem.** "Unduh laporan", bukan "JSON".
7. **Umpan balik segera.** Kirim status dalam < 1 detik, hasil ideal < 5 detik.
8. **Bisa dibatalkan.** Setiap aksi penting punya undo atau langkah konfirmasi.
9. **Konsisten.** Satu istilah untuk satu konsep, di semua layar.
10. **Aman secara default.** Privasi dijelaskan, notifikasi opt-in, data sensitif
    tidak pernah ditampilkan di pesan error.

---

## 2. Voice & Tone

- **Sapaan:** "kamu", bukan "Anda". Konsisten di seluruh bot.
- **Nada:** ramah, tenang, tidak kekanak-kanakan. Emoji sebagai penanda, bukan
  pengganti kata.
- **Kalimat:** maksimal 2 baris per paragraf; hindari blok teks > 8 baris.
- **Angka:** selalu format rupiah `Rp20.000` (titik ribuan, tanpa desimal).
- **Tanggal:** `12 Nov 2026, 09:14` (bukan ISO di pesan user).
- **Kata terlarang di pesan user:** JSON, callback, API, token, auth, env,
  exception, parsing, NLP, dashboard (kecuali "buka dashboard" sebagai label
  tombol yang sudah dijelaskan), ID Telegram.

### Nada per konteks

| Konteks | Nada | Contoh |
|---|---|---|
| Sukses | Singkat, merayakan secukupnya | "✅ Tercatat: Kopi — Rp20.000" |
| Salah input | Membantu, tanpa menyalahkan | "Aku belum menemukan nominalnya. Coba: `kopi 20rb`." |
| Error sistem | Tenang, minta maaf singkat | "Maaf, ada gangguan. Coba lagi sebentar." |
| Konfirmasi hapus | Serius, jelas konsekuensinya | "Semua 128 transaksi akan hilang permanen." |
| Onboarding | Memandu, satu langkah per pesan | "Dulu, kamu di zona waktu mana?" |

---

## 3. Anatomi Pesan Standar

```
[Emoji status] [Judul singkat]

[Isi 1–3 baris]
[Detail penting: nominal, dompet, waktu]

[Aksi berikutnya]
[Tombol]
```

Contoh:
```
✅ Tercatat: Kopi — Rp20.000

🏷️ Makanan · 💼 Utama · 🕒 12 Nov, 09:14
Saldo Utama: Rp480.000

Mau lihat rekap hari ini?
[📊 Laporan] [🏠 Menu]
```

Aturan:
- Judul ≤ 1 baris, huruf kapital di awal, bukan ALL CAPS.
- Detail maksimal 4 baris.
- Tombol maksimal 3 per baris, total ≤ 6 per pesan.
- Tombol navigasi selalu di baris terakhir.

---

## 4. Pola Error

### Formula
1. **Apa yang terjadi** (tanpa detail teknis).
2. **Kenapa** (bila diketahui dan relevan).
3. **Apa yang bisa dilakukan** (contoh atau tombol).

### Contoh
```
❌ Aku belum bisa membaca pesan itu sebagai transaksi.

Coba tulis nominal dan kegiatannya, misalnya:
• `makan siang 25rb`
• `gaji 5jt`

[❓ Bantuan] [📋 Menu]
```

### Larangan
- `⚠️ Terjadi error: <str(e)>`
- Menampilkan nama environment variable.
- Menyalahkan pengguna ("Input Anda salah").
- Pesan kosong atau hanya emoji.

---

## 5. Pola Aksi Destruktif

Wajib 2 langkah:

**Langkah 1 — tombol aksi**
```
🗑️ Hapus akun?
```

**Langkah 2 — konfirmasi dengan konsekuensi**
```
⚠️ Hapus akun permanen?

Semua data ini akan hilang:
• 128 transaksi
• 3 dompet
• 2 budget

Tindakan ini tidak bisa dibatalkan.

[Ya, hapus permanen] [Batal]
```

Untuk hapus akun, tambahkan konfirmasi ketik `HAPUS` atau tombol kedua.
Setelah selesai, tampilkan `[🚀 Mulai lagi]`.

---

## 6. Pola Navigasi

### Struktur
- **Reply Keyboard permanen** (bawah):
  `➕ Catat` · `📊 Laporan` · `💼 Dompet` · `🎯 Budget` · `❓ Bantuan`
- **Inline keyboard** untuk drill-down: periode, kategori, konfirmasi.
- **Command** hanya alias untuk pengguna lama; semua fitur harus bisa diakses
  lewat tombol.

### Aturan tombol
- Label diawali emoji fungsional, bukan dekoratif: `📊 Laporan`, `➕ Tambah`.
- Gunakan kata kerja: "Atur budget", bukan "Budget".
- Tombol destruktif diberi warna/kata jelas: "Hapus akun".
- Tombol `Batal` selalu ada pada alur multi-langkah.
- `Kembali` kembali ke layar sebelumnya, `Menu` ke menu utama.

### Peta command

| Command | Alias | Fungsi | Muncul di autocomplete |
|---|---|---|---|
| `/start` | — | Landing + onboarding | Ya |
| `/menu` | `/home` | Menu utama | Ya |
| `/catat` | — | Panduan mencatat | Ya |
| `/laporan` | `/bulan` | Laporan periode | Ya |
| `/saldo` | `/dompet` | Daftar dompet | Ya |
| `/budget` | — | Budget bulanan | Ya |
| `/help` | `/bantuan` | Bantuan | Ya |
| `/akun` | — | Info & pengaturan | Ya |
| `/register` | — | Daftar (alias `/start`) | Tidak |
| `/hapus_akun` | — | Hapus akun | Tidak (via menu) |
| `/login_web` | — | Buka dashboard | Tidak (via menu) |
| `/laporan_harian` | — | Notifikasi harian | Tidak (via menu) |

---

## 7. Onboarding

- Maksimal **4 langkah**, satu pertanyaan per pesan.
- Semua langkah bisa dijawab dengan tombol; ketik hanya untuk nama dompet.
- Setiap langkah menyebut kemajuan: "Langkah 2 dari 4".
- Selalu ada `[Lewati]` dan `[Batal]`.
- Jangan meminta data yang tidak dipakai.
- Setelah selesai: satu contoh transaksi konkret + menu.

---

## 8. Konfirmasi & Undo

- Transaksi dengan `confidence < 0.8`, `CORRECTION`, atau `TRANSFER` wajib
  pratinjau.
- Transaksi normal langsung disimpan, tetapi pesan sukses punya `[↩️ Batalkan]`
  selama 5 menit.
- Undo harus mengembalikan saldo dan menghapus transaksi terkait (termasuk biaya
  admin pada transfer).
- Jika tombol kedaluwarsa: "Sudah lewat 5 menit. Kamu bisa hapus lewat
  [daftar transaksi]."

---

## 9. Format & Teknis

- Gunakan **HTML parse mode** untuk pesan baru; escape semua konten dinamis.
- Jika tetap Markdown: escape `_ * [ ] ( ) ~ ` > # + - = | { } . !`.
- Jangan memotong pesan di tengah baris; gunakan pemecahan per baris.
- `callback_data` maksimal 64 byte; gunakan token pendek, bukan UUID/nama.
- Jangan menyimpan state penting hanya di memori proses.
- Semua handler wajib memanggil `callback_query.answer()`.
- Semua handler wajib menangani `BadRequest: message is not modified`.

---

## 10. Standar Respons

| Kejadian | Target |
|---|---|
| Balasan pertama setelah input | < 1 detik |
| Hasil parsing AI | < 5 detik (95 persentil) |
| Membuka menu | < 1 detik |
| Laporan bulanan | < 3 detik |
| Timeout conversation | 5 menit |
| Masa berlaku undo | 5 menit |
| Masa berlaku pilih dompet | 10 menit |

Jika proses > 2 detik, kirim pesan status yang bisa diedit, bukan pesan baru
berulang.

---

## 11. Aksesibilitas untuk Pengguna Awam

- Tidak ada singkatan yang tidak dijelaskan (JSON, OCR, NLP).
- Contoh selalu menyertakan nominal ("kopi 20rb"), bukan hanya "ketik transaksi".
- Hindari istilah bank yang ambigu tanpa contoh.
- Jangan andalkan warna/emoji saja; sertakan teks status ("Aktif", "Nonaktif").
- Semua tombol harus bisa dipahami tanpa membaca pesan sebelumnya.
- Sediakan bantuan yang bisa dibuka kapan saja, termasuk dari pesan error.

---

## 12. Checklist Copywriting per Pesan

- [ ] Siapa pembacanya? (baru/lama)
- [ ] Apa satu tindakan utama yang diminta?
- [ ] Apakah ada contoh konkret?
- [ ] Apakah ada jalan keluar (Menu/Batal/Kembali)?
- [ ] Apakah ada istilah teknis yang bisa diganti?
- [ ] Apakah panjangnya ≤ 8 baris?
- [ ] Apakah nada konsisten dengan konteks?
- [ ] Apakah semua konten dinamis sudah di-escape?
