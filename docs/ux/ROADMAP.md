# ROADMAP — Peningkatan UX Bot Keuangan

> Rencana bertahap 12 minggu (dapat dikompres menjadi 6–8 minggu bila fokus
> P0/P1). Mengacu ke ID tiket di `BACKLOG.md` dan temuan di `AUDIT-FINDINGS.md`.

---

## Prinsip Eksekusi

- **Utamakan alur, bukan fitur.** Setiap rilis harus membuat satu perjalanan
  pengguna selesai tanpa bantuan.
- **Perbaiki fondasi dulu.** Error handling, escaping, dan persistensi state
  dikerjakan sebelum menambah fitur baru.
- **Satu fase = satu tema.** Hindari mencampur onboarding dengan ekspor laporan.
- **Ukur sebelum-sesudah.** Tanpa telemetri, peningkatan hanya asumsi.

---

## Fase 0 — Stabilkan & Rapikan (Hari 1–2)

**Tema:** Hilangkan buntu dan pesan teknis.

**Scope:** UX-001, UX-002, UX-003, UX-004, UX-005, UX-006, UX-008, UX-010,
UX-020, UX-041, UX-042.

**Hasil yang diharapkan:**
- `/start` menjelaskan fungsi bot dan mengarahkan ke menu.
- `/help` tersedia; command/input aneh tidak lagi dibisukan.
- Tidak ada pesan `Terjadi error: <detail internal>`.
- Hapus akun tidak bisa dilakukan satu klik.
- Tombol pilih dompet dari foto berfungsi.

**Exit criteria:**
- [ ] Semua pemeriksaan "Smoke Test" di `QA-CHECKLIST.md` lulus.
- [ ] Tidak ada handler yang membalas dengan `str(e)`.
- [ ] Tidak ada `callback_data` > 64 byte.
- [ ] User baru bisa `/start` → menu → catat transaksi tanpa instruksi manual.

**Risiko:** Perubahan copy dan handler bisa memicu regresi pada callback lama.
Mitigasi: pertahankan alias callback lama selama satu rilis.

---

## Fase 1 — Onboarding & Kepercayaan (Minggu 1–2)

**Tema:** Pengguna baru paham dalam 60 detik; pengguna lama berani memperbaiki data.

**Scope:** UX-009, UX-011, UX-012, UX-013, UX-014, UX-022, UX-023, UX-025,
UX-030, UX-031, UX-032, UX-033, UX-034, UX-043.

**Milestone:**
1. Wizard onboarding 4 langkah dengan state persisten.
2. Zona waktu & notifikasi dapat diatur tanpa command.
3. Pratinjau transaksi + undo transaksi terakhir.
4. Konfirmasi semua aksi destruktif.

**Exit criteria:**
- [ ] 5 pengguna uji baru berhasil mencatat transaksi pertama < 60 detik.
- [ ] Tidak ada laporan tanggal salah akibat zona waktu default.
- [ ] Koreksi saldo dan transfer selalu melalui pratinjau.
- [ ] Undo mengembalikan saldo 100% akurat (test otomatis).
- [ ] Tidak ada dead end di menu Dompet.

**Metrik target:**
| Metrik | Baseline (asumsi) | Target |
|---|---|---|
| Waktu ke transaksi pertama | > 2 menit | < 60 detik |
| User baru yang membuka menu di sesi pertama | Tidak diketahui | > 70% |
| Transaksi dibatalkan karena salah parsing | Tidak diketahui | < 5% |
| Keluhan "bot tidak merespons" | Tidak diketahui | 0 |

---

## Fase 2 — Keandalan Alur Inti (Minggu 3–6)

**Tema:** Alur multi-dompet, budget, dan laporan selesai tanpa jebakan.

**Scope:** UX-021, UX-024, UX-026, UX-027, UX-040, UX-044, UX-045, UX-046,
UX-049.

**Milestone:**
1. Pending transaction persisten (DB/Redis) + TTL.
2. Pencegahan duplikasi transaksi.
3. Budget dapat diatur penuh dari tombol.
4. Dompet tidak ditemukan selalu punya jalan keluar.
5. Voice note didukung (opsional, jika kapasitas memungkinkan).

**Exit criteria:**
- [x] Pilih dompet tetap berhasil setelah restart server.
- [x] Budget bisa dibuat/diubah/dihapus tanpa mengetik nama kategori.
- [x] Tidak ada pesan "Dompet X tidak ditemukan" tanpa tombol aksi.
- [x] Double tap tidak menghasilkan dua transaksi.
- [x] Laporan mingguan benar-benar 7 hari.
- [x] Bulan laporan bisa dipilih dari tombol dan diunduh sebagai CSV/JSON.

**Risiko:** Migrasi tabel pending transaction dan perubahan callback dapat
mematahkan tombol lama. Mitigasi: feature flag + fallback handler.

---

## Fase 3 — Polish, Laporan, & Pengukuran (Minggu 7–12)

**Tema:** Produk terasa selesai dan perbaikan berikutnya berbasis data.

**Scope:** UX-047, UX-048, UX-050, UX-051, UX-052, UX-053, UX-054, UX-055,
UX-056.

**Milestone:**
1. ✅ Telemetri funnel: start → onboarding → transaksi pertama → transaksi ke-5.
2. 🟡 Uji usability formal: panduan & template siap, eksekusi menunggu peserta.
3. ✅ Ekspor laporan CSV dan pemilih bulan (PDF menyusul).
4. ✅ Pusat bantuan in-chat + FAQ dan edit/hapus transaksi lewat riwayat.
5. ✅ Audit copywriting menyeluruh (istilah teknis, sapaan, label tombol).
6. ✅ Personalisasi sapaan dan target tabungan dengan progres.
7. ✅ Dashboard metrik mingguan di `/metrics` + endpoint JSON.
8. ✅ Durasi respons AI (`text`/`image`) tercatat di `ux_events`.

**Exit criteria:**
- [x] Dashboard metrik mingguan tersedia (data mentah sudah ada di `ux_events`).
- [x] Error rate dan waktu respons AI terpantau (error + durasi AI tercatat).
- [x] Pengguna dapat mengunduh laporan tanpa memahami JSON.
- [ ] Ada laporan hasil uji usability dan action item (template siap, isi setelah sesi).

---

## Urutan Rilis yang Disarankan

| Rilis | Isi | Sasaran |
|---|---|---|
| v0.2.0 | Fase 0 | Tidak ada layar buntu |
| v0.3.0 | Fase 1 | Onboarding + trust |
| v0.4.0 | Fase 2 | Keandalan multi-dompet/budget |
| v0.5.0 | Fase 3 | Laporan + telemetri |

Setiap rilis:
1. Jalankan `QA-CHECKLIST.md`.
2. Uji dengan 1 akun baru dan 1 akun lama.
3. Deploy ke staging/webhook preview.
4. Pantau log 24 jam.
5. Update `BACKLOG.md` (status + temuan baru).

---

## Dependensi & Keputusan Teknis

| Keputusan | Opsi | Rekomendasi | Alasan |
|---|---|---|---|
| State percakapan | `PicklePersistence` vs tabel DB | Tabel DB (production) | Aman untuk serverless & multi-instance |
| Pending transaction | Memori vs DB vs Redis | DB + TTL | Sederhana, sudah ada SQLAlchemy |
| Format pesan | Markdown vs HTML | HTML + escape | Lebih toleran terhadap konten user |
| Navigasi utama | Command vs inline vs reply keyboard | Reply keyboard + inline | Awam tidak perlu hafal command |
| Telemetri | Log file vs tabel event | Tabel `ux_events` + log | Bisa dianalisis tanpa tools baru |
| Voice note | Groq Whisper | Groq Whisper | Satu vendor, sudah ada API key |

---

## Hal yang TIDAK Dilakukan Dulu

- Redesign web dashboard (kecuali perbaikan link login).
- Multi-bahasa.
- Integrasi API bank.
- Fitur sosial/sharing.
- Model AI kustom.

---

## Ritme Kerja

- **Harian:** 15 menit cek log error & feedback user.
- **Mingguan:** review backlog, update status, satu perbaikan copy.
- **Akhir fase:** demo alur ke 1 pengguna awam, catat friksi, prioritaskan ulang.
