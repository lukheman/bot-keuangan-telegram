# MESSAGE TEMPLATES — Copy Siap Pakai

> Draf teks pesan resmi bot. Gunakan variabel `{...}` dan HTML parse mode.
> Semua konten dinamis wajib di-escape sebelum dikirim.
> Jika memakai Markdown, escape karakter khusus terlebih dahulu.

---

## 1. First Run

### `/start` — pengguna baru

```
👋 Hai, {nama}! Aku asisten keuanganmu.

Catat transaksi cukup dengan chat biasa:
• `kopi 20rb`
• `gaji 5jt`
• `transfer bca ke tunai 100rb`

Atau kirim 📸 foto struk. Aku juga bisa bantu lihat saldo, budget,
dan laporan bulanan.

Mau mulai? Prosesnya cuma 4 langkah singkat.
```

Tombol:
```
[🚀 Mulai]  [📋 Buka Menu]
```

### `/start` — pengguna lama

```
👋 Hai lagi, {nama}!

📅 Hari ini: keluar {pengeluaran_hari_ini} ({jumlah} transaksi)
🗓️ Bulan ini: keluar {pengeluaran_bulan_ini}
💼 Total saldo: {total_saldo}

Mau ngapain?
[➕ Catat] [📊 Laporan] [💼 Dompet] [🎯 Budget]
```

---

## 2. Onboarding

### Langkah 1 — konfirmasi akun

```
👋 Senang kenalan, {nama}!

Aku akan pakai nama ini untuk sapaan. Kamu bisa mengubahnya nanti
lewat menu Akun.
```

Tombol: `[Lanjut]`

### Langkah 2 — zona waktu (1/4)

```
🌏 Langkah 1 dari 4 — Zona waktu

Supaya tanggal transaksi dan laporanmu akurat, pilih zona waktumu:
• WIB — Jakarta, Bandung, Surabaya
• WITA — Makassar, Bali, Balikpapan
• WIT — Jayapura, Ambon
```

Tombol: `[WIB] [WITA] [WIT]`

### Langkah 3 — dompet awal (2/4)

```
💼 Langkah 2 dari 4 — Dompet

Dompet dipakai untuk memisahkan uangmu, misalnya BCA, Tunai, atau Gopay.
Aku bisa buatkan dompet "Utama" dulu.
```

Tombol:
```
[Pakai "Utama"]  [Buat dompet sendiri]  [Lewati dulu]
```

Jika buat sendiri:
```
Siapa nama dompetnya? Contoh: BCA, Tunai, Gopay.
```

```
Berapa saldo awalnya? Ketik 0 kalau belum tahu.
Contoh: 500000 atau 500rb
```

### Langkah 4 — notifikasi (3/4)

```
🌙 Langkah 3 dari 4 — Notifikasi

Aku bisa kirim ringkasan transaksi setiap tengah malam (00:00).
Bermanfaat untuk evaluasi harian, tapi bisa dimatikan kapan saja.
```

Tombol: `[🔔 Aktifkan] [Nanti saja]`

### Langkah 5 — selesai (4/4)

```
🎉 Siap, {nama}!

Semua pengaturan bisa diubah lewat menu 👤 Akun.

Coba catat transaksi pertamamu sekarang:
`kopi 20rb`

Atau kirim foto struk. Aku langsung catat.
```

Tombol: `[➕ Catat sekarang] [📋 Menu]`

---

## 3. Bantuan

### `/help`

```
❓ Bantuan

✍️ Catat transaksi
Ketik natural, contoh:
• `beli kopi 20rb`
• `gaji 5jt`
• `transfer bca ke tunai 100rb`
Atau kirim 📸 foto struk.

💼 Dompet — lihat dan atur saldo
🎯 Budget — atur batas pengeluaran bulanan
📊 Laporan — rekap harian, mingguan, bulanan
🌙 Notifikasi — ringkasan otomatis tiap tengah malam
👤 Akun — zona waktu, dashboard, hapus akun

Butuh bantuan lain? Tekan tombol di bawah.
```

Tombol: `[📋 Menu] [💼 Dompet] [📊 Laporan]`

### Command / input tidak dikenal

```
Aku belum paham perintah itu.

Yang bisa aku lakukan:
• Catat transaksi: `kopi 20rb`
• Lihat saldo: menu 💼 Dompet
• Lihat laporan: menu 📊 Laporan

[❓ Bantuan] [📋 Menu]
```

### Voice note (sebelum fitur tersedia)

```
🎙️ Aku belum bisa mendengar voice note.

Sementara ini, ketik saja transaksinya:
`makan siang 25rb`
Atau kirim foto struk.
```

### Dokumen/gambar sebagai file

```
📎 Aku belum bisa membaca file itu.

Kirim sebagai foto biasa (bukan dokumen), atau ketik transaksinya:
`beli obat 35rb`
```

### Sticker / video / lokasi

```
🙂 Aku belum bisa memproses jenis pesan ini.

Coba ketik transaksi seperti `kopi 20rb`, kirim foto struk,
atau buka menu di bawah.
```

---

## 4. Pencatatan Transaksi

### Status saat memproses

```
⏳ Sebentar, aku baca dulu...
```

### Tidak dikenali

```
❌ Aku belum menemukan transaksi di pesan itu.

Coba tulis nominal dan kegiatannya:
• `makan siang 25rb`
• `gaji 5jt`

[❓ Bantuan] [📋 Menu]
```

### Pratinjau (confidence rendah / koreksi / transfer)

```
🔍 Cek dulu sebelum aku simpan

📉 Pengeluaran — Rp25.000
📝 Makan Siang
🏷️ Makanan
💼 Utama
🕒 12 Nov 2026, 12:30

Sudah benar?
[✅ Simpan] [✏️ Ubah] [❌ Batal]
```

Untuk koreksi saldo:
```
⚖️ Koreksi saldo

Kamu menyebut saldo Gopay sekarang Rp50.000.
Aku akan mencatat penyesuaian sebesar Rp15.000 (pemasukan)
supaya saldo sesuai.

[✅ Sesuai, simpan] [❌ Batal]
```

Untuk transfer:
```
🔁 Cek transfer

📤 Dari: BCA — Rp500.000
📥 Ke: Tunai — Rp500.000
🧾 Biaya admin: Rp5.000

Saldo BCA setelah ini: Rp1.250.000
Saldo Tunai setelah ini: Rp800.000

[✅ Simpan] [❌ Batal]
```

### Sukses — pengeluaran

```
✅ Tercatat: {deskripsi} — Rp{nominal}

🏷️ {kategori} · 💼 {dompet} · 🕒 {waktu}
Saldo {dompet}: Rp{saldo}

[↩️ Batalkan] [📊 Laporan] [🏠 Menu]
```

### Sukses — pemasukan

```
✅ Tercatat: {deskripsi} — Rp{nominal}

📈 Pemasukan · 🏷️ {kategori} · 💼 {dompet}
Saldo {dompet}: Rp{saldo}

[↩️ Batalkan] [📊 Laporan] [🏠 Menu]
```

### Sukses + peringatan budget

```
✅ Tercatat: {deskripsi} — Rp{nominal}

🏷️ Makanan · 💼 Utama · 🕒 {waktu}
Saldo Utama: Rp{saldo}

⚠️ Budget Makanan sudah 85% terpakai.
Rp425.000 dari Rp500.000 bulan ini.

[📊 Lihat budget] [🏠 Menu]
```

### Undo berhasil

```
↩️ Transaksi dibatalkan.

Saldo {dompet} kembali menjadi Rp{saldo}.
```

### Undo kedaluwarsa

```
⌛ Waktu pembatalan sudah lewat (5 menit).

Buka 🧾 Riwayat untuk mengedit atau menghapus transaksi kapan saja.
```

---

## 5. Dompet

### Daftar dompet

```
💼 Dompet kamu

• BCA: Rp1.750.000
• Tunai: Rp300.000
• Gopay: Rp125.000

Total saldo: Rp2.175.000

[➕ Tambah dompet] [✏️ Ubah nama] [🗑️ Hapus] [🏠 Menu]
```

### User baru / belum punya dompet

```
💼 Kamu belum punya dompet.

Dompet membantu memisahkan uang, misalnya BCA, Tunai, atau Gopay.
Aku bisa buatkan "Utama" sekarang.
```

Tombol: `[➕ Buat "Utama"] [Buat dompet sendiri] [🏠 Menu]`

### Pilih dompet saat transaksi

```
💳 Transaksi ini pakai dompet yang mana?

Rp25.000 — Makan Siang
```

Tombol:
```
[BCA] [Tunai] [Gopay]
[➕ Dompet baru] [❌ Batal]
```

### Dompet tidak ditemukan

```
Dompet "{nama}" belum ada.

Dompetmu saat ini: {daftar_dompet}.
```

Tombol:
```
[➕ Buat dompet "{nama}"] [Pilih dompet lain] [❌ Batal]
```

### Tambah dompet — nama

```
💳 Dompet baru

Siapa nama dompetnya?
Contoh: BCA, Tunai, Gopay, ShopeePay
```

Tombol: `[❌ Batal]`

### Tambah dompet — saldo

```
Berapa saldo awal {nama}?

Ketik angka, contoh: 500000 atau 500rb.
Ketik 0 kalau belum tahu.
```

Tombol: `[0 — Kosong] [❌ Batal]`

### Dompet sudah ada

```
Dompet "{nama}" sudah ada.

Mau pakai dompet itu, atau pakai nama lain?
[Pakai "{nama}"] [Ganti nama] [❌ Batal]
```

### Konfirmasi hapus dompet

```
⚠️ Hapus dompet {nama}?

Dompet ini punya {jumlah} transaksi. Semua transaksi tersebut
akan ikut terhapus permanen.

[Ya, hapus] [Batal]
```

---

## 6. Budget

### Menu budget — kosong

```
🎯 Budget bulanan

Belum ada budget. Budget membantumu menjaga pengeluaran per kategori.

Contoh: budget Makanan Rp1.000.000 per bulan.
Kamu akan dapat peringatan saat pemakaian mencapai 80%, 100%,
atau melebihi batas.
```

Tombol: `[➕ Atur budget] [🏠 Menu]`

### Pilih kategori

```
🎯 Atur budget — pilih kategori

[🍚 Makanan] [🚌 Transportasi] [⛽ Bensin]
[💊 Kesehatan] [🎬 Hiburan] [🧴 Perawatan]
[📚 Pendidikan] [📦 Lainnya]
```

### Input nominal

```
Berapa budget bulanan untuk {kategori}?

Contoh: 1jt, 500rb, atau 1000000.
```

Tombol: `[❌ Batal]`

### Budget berhasil

```
🎯 Budget {kategori} diatur: Rp{nominal}/bulan.

Aku akan ingatkan saat pemakaian mencapai 80%, 100%,
atau melebihi budget.
```

### Daftar budget

```
🎯 Budget bulan ini ({periode})

✅ Makanan — Rp425.000 / Rp500.000 (85%)
▓▓▓▓▓▓▓▓░░

⚠️ Transportasi — Rp240.000 / Rp250.000 (96%)
▓▓▓▓▓▓▓▓▓░

[➕ Tambah/ubah] [🗑️ Hapus] [🏠 Menu]
```

### Konfirmasi hapus budget

```
⚠️ Hapus budget {kategori}?

Batas Rp{nominal}/bulan akan dihapus. Transaksi yang sudah ada
tidak ikut terhapus.
```

Tombol: `[Ya, hapus] [Batal]`

---

## 7. Laporan

### Menu laporan

```
📊 Laporan keuangan

Mau lihat yang mana?
```

Tombol:
```
[📅 Hari ini] [📆 7 hari terakhir]
[🗓️ Bulan ini] [📂 Pilih bulan]
[⬇️ Unduh laporan] [🏠 Menu]
```

### Laporan kosong

```
📊 Laporan hari ini

Belum ada transaksi hari ini.

Coba catat yang pertama:
`kopi 20rb`
```

Tombol: `[➕ Catat] [🏠 Menu]`

### Ringkasan

```
📊 Laporan {periode}

📈 Pemasukan: Rp{masuk}
📉 Pengeluaran: Rp{keluar}
💡 Selisih: Rp{selisih}
💼 Total saldo dompet: Rp{total_saldo}

📂 Pengeluaran per kategori:
• Makanan: Rp425.000 (52%)
• Transportasi: Rp240.000 (29%)
• Lainnya: Rp155.000 (19%)

[📅 Hari ini] [🗓️ Bulan ini] [🏠 Menu]
```

### Unduh laporan

```
⬇️ Unduh laporan

Pilih format:
[📄 PDF] [📊 Excel/CSV] [🧾 JSON]
```

### File siap

```
📥 Laporan {periode}

{jumlah} transaksi · masuk Rp{masuk} · keluar Rp{keluar}
```

---

## 8. Akun

### Info akun

```
👤 Akun kamu

Nama: {nama}
ID akun: {id}
Zona waktu: {zona}
Dompet utama: {dompet}
Notifikasi harian: {Aktif/Nonaktif}
Bergabung: {tanggal}

[✏️ Ubah zona waktu] [🔔 Notifikasi] [🌐 Buka dashboard]
[🗑️ Hapus akun] [🏠 Menu]
```

### Konfirmasi hapus akun

```
⚠️ Hapus akun permanen?

Semua data ini akan hilang:
• {jumlah_transaksi} transaksi
• {jumlah_dompet} dompet
• {jumlah_budget} budget

Tindakan ini tidak bisa dibatalkan.

[Ya, hapus permanen] [Batal]
```

### Konfirmasi terakhir

```
Ini konfirmasi terakhir.

Ketik HAPUS untuk menghapus akun {nama} secara permanen.
```

Tombol: `[Batal]`

### Akun dihapus

```
🗑️ Akun kamu sudah dihapus.

Terima kasih sudah memakai bot ini. Kalau mau mulai lagi,
tekan tombol di bawah.
```

Tombol: `[🚀 Mulai lagi]`

### Link dashboard

```
🌐 Buka dashboard

Klik tombol di bawah untuk masuk otomatis. Link berlaku 15 menit.
Jika sudah kedaluwarsa, buka menu ini lagi.
```

Tombol: `[Buka dashboard] [🏠 Menu]`

---

## 9. Notifikasi

### Pengaturan notifikasi

```
🌙 Notifikasi harian

Status: {Aktif/Nonaktif}
Dikirim setiap 00:00 waktu {zona}.
Isinya ringkasan transaksi hari yang baru selesai.

[🔔 Aktifkan / 🔕 Matikan] [🏠 Menu]
```

### Laporan harian otomatis

```
🌙 Laporan harian — {tanggal}

📈 Pemasukan: Rp{masuk}
📉 Pengeluaran: Rp{keluar}
💡 Selisih: Rp{selisih}

📂 Pengeluaran terbesar:
• Makanan: Rp125.000
• Transportasi: Rp50.000

[📊 Laporan lengkap] [🏠 Menu]
```

---

## 10. Error

### Error umum

```
Maaf, ada gangguan saat memproses permintaanmu.

Coba lagi sebentar. Kalau masih gagal, buka menu utama
dan ulangi dari sana.
```

Tombol: `[🔄 Coba lagi] [🏠 Menu]`

### Sesi kedaluwarsa

```
⌛ Sesi ini sudah kedaluwarsa.

Transaksi belum tersimpan. Silakan kirim ulang, ya.
Contoh: `kopi 20rb`
```

Tombol: `[➕ Catat ulang] [🏠 Menu]`

### Service AI tidak tersedia

```
⚠️ Layanan pembaca transaksi sedang sibuk.

Coba lagi dalam beberapa saat, atau catat manual:
`kopi 20rb`
```

Tombol: `[🔄 Coba lagi] [🏠 Menu]`

### User belum terdaftar

```
Kamu belum punya akun di bot ini.

Tekan tombol di bawah untuk mendaftar—cukup satu klik.
```

Tombol: `[🚀 Daftar sekarang] [❓ Bantuan]`

---

## 11. Konvensi Tombol

| Aksi | Label |
|---|---|
| Menu utama | `🏠 Menu` |
| Kembali | `🔙 Kembali` |
| Batal | `❌ Batal` |
| Simpan | `✅ Simpan` |
| Ubah | `✏️ Ubah` |
| Undo | `↩️ Batalkan` |
| Tambah | `➕ Tambah ...` |
| Hapus | `🗑️ Hapus ...` |
| Coba lagi | `🔄 Coba lagi` |
| Dashboard | `🌐 Buka dashboard` |

Aturan: satu emoji per tombol, kata kerja di depan, maksimal 3 tombol per baris.
