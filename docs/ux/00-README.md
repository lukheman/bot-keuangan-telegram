# Paket Dokumen Perbaikan UX

Folder ini berisi draft plan perbaikan bot keuangan. Dibuat saat sesi masih
**Plan mode**, sehingga belum ada file yang diubah di repo
`/home/akmal/Code/40_Playground/bot-keuangan`.

## Isi

| File | Fungsi |
|---|---|
| `AUDIT-FINDINGS.md` | Ringkasan temuan T1–T22, skor, dan pemetaan ke tiket |
| `BACKLOG.md` | Epic, papan backlog per fase, detail tiket P0/P1, acceptance criteria |
| `ROADMAP.md` | Rencana 12 minggu, milestone, exit criteria, metrik, keputusan teknis |
| `UX-GUIDELINES.md` | Prinsip UX, voice & tone, pola error/konfirmasi/navigasi, standar respons |
| `MESSAGE-TEMPLATES.md` | Copy pesan siap pakai untuk semua alur utama |
| `QA-CHECKLIST.md` | Smoke test, journey test, edge case, non-fungsional, otomatisasi |
| `USABILITY-TEST.md` | Panduan sesi uji usability UX-051 (5 peserta) |
| `USABILITY-REPORT.md` | Template laporan hasil uji + action item |
| `00-README.md` | Indeks dan cara memakai paket ini |

## Cara Memakai

1. Baca `AUDIT-FINDINGS.md` untuk konteks masalah.
2. Mulai dari `BACKLOG.md` Fase 0; kerjakan tiket sesuai urutan.
3. Saat menulis pesan, ikuti `UX-GUIDELINES.md` dan ambil teks dari
   `MESSAGE-TEMPLATES.md`.
4. Sebelum merge, jalankan `QA-CHECKLIST.md`.
5. Update status tiket dan `ROADMAP.md` di akhir setiap fase.

## Cara Menyalin ke Repo

Saat siap implementasi, pindah ke agent build lalu salin:

```bash
cp /home/akmal/.opencode/plan/BACKLOG.md \
   /home/akmal/.opencode/plan/ROADMAP.md \
   /home/akmal/.opencode/plan/UX-GUIDELINES.md \
   /home/akmal/.opencode/plan/MESSAGE-TEMPLATES.md \
   /home/akmal/.opencode/plan/QA-CHECKLIST.md \
   /home/akmal/.opencode/plan/AUDIT-FINDINGS.md \
   /home/akmal/Code/40_Playground/bot-keuangan/docs/ux/
```

Lalu tambahkan tautan dari `README.md` repo ke `docs/ux/BACKLOG.md`.

## Urutan Eksekusi yang Disarankan

```
Fase 0 (1–2 hari)
  UX-005 error handler
  UX-008 escaping
  UX-001/002 /start + akun
  UX-003/004 help + fallback
  UX-010/020/041/042 quick fixes

Fase 1 (minggu 1–2)
  UX-030–034 onboarding
  UX-011–014 dompet
  UX-022/023 pratinjau + undo

Fase 2 (minggu 3–6)
  UX-021/026 persistensi + dedupe
  UX-040/044 budget
  UX-045/049 pemulihan dompet

Fase 3 (minggu 7–12)
  UX-050 telemetri
  UX-047/048 laporan
  UX-051 uji usability
```

## Prinsip Utama

> Pengguna baru harus bisa menyelesaikan transaksi pertama dalam < 60 detik
> tanpa membaca dokumentasi, dan tidak pernah menemui layar buntu.
