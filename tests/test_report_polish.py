"""Test polish laporan: total saldo, pemilih bulan, dan ekspor CSV."""

from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace

from app.models import TransactionType
from app.services.report_service import build_csv_report
from bot.handlers.report import _format_transactions, month_options


def test_laporan_menampilkan_selisih_dan_total_saldo():
    transaksi = [
        SimpleNamespace(
            type=TransactionType.INCOME,
            amount=Decimal("50000"),
            description="gaji",
            date=date(2026, 11, 12),
            local_created_at=datetime(2026, 11, 12, 8, 0),
        )
    ]

    msg = _format_transactions(
        transaksi,
        50000,
        0,
        "Ringkasan Hari Ini",
        include_date=True,
        include_balance=True,
        total_balance=125000,
    )

    assert "Selisih periode" in msg
    assert "Total Saldo Dompet" in msg
    assert "Rp125.000" in msg


def test_pilihan_bulan_menyeberang_tahun():
    options = month_options(date(2026, 1, 15), count=3)

    assert options == [
        (2026, 1, "Jan 2026"),
        (2025, 12, "Des 2025"),
        (2025, 11, "Nov 2025"),
    ]


def test_csv_laporan_bisa_dibuka_excel():
    data = {
        "transactions": [
            {
                "date": "2026-11-12",
                "datetime": "2026-11-12T08:30:00+08:00",
                "type": "EXPENSE",
                "amount": 20000,
                "category": "Makanan",
                "wallet": "Tunai",
                "description": "kopi",
            }
        ]
    }

    payload = build_csv_report(data)

    assert payload.startswith(b"\xef\xbb\xbf")  # BOM untuk Excel
    text = payload.decode("utf-8-sig")
    assert "Tanggal,Waktu,Tipe,Nominal,Kategori,Dompet,Deskripsi" in text
    assert "2026-11-12,08:30,EXPENSE,20000,Makanan,Tunai,kopi" in text
