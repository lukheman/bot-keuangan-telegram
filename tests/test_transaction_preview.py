"""Test pratinjau transaksi sebelum disimpan."""

import uuid
from decimal import Decimal
from types import SimpleNamespace

from app.models import TransactionType
from bot.handlers.transaction import (
    _preview_keyboard,
    _preview_text,
    _wallet_missing,
    _wallet_picker_keyboard,
)


def test_preview_transaksi_sederhana():
    text = _preview_text(
        {
            "kind": "simple",
            "amount": Decimal("20000"),
            "description": "kopi *promo*",
            "type": TransactionType.EXPENSE,
            "category": "Makanan",
            "wallet_name": "Tunai",
            "confidence": 0.62,
        }
    )
    assert "Konfirmasi Pengeluaran" in text
    assert "Rp20.000" in text
    assert "belum sepenuhnya yakin" in text
    assert "Keyakinan AI" not in text
    assert r"kopi \*promo\*" in text


def test_preview_transfer_menampilkan_biaya_admin():
    text = _preview_text(
        {
            "kind": "transfer",
            "amount": Decimal("100000"),
            "source": "BCA",
            "dest": "Tunai",
            "fee": Decimal("5000"),
            "description": "Transfer BCA ke Tunai",
        }
    )
    assert "Konfirmasi Transfer" in text
    assert "Rp100.000" in text
    assert "Rp5.000" in text


def test_callback_preview_di_bawah_batas_telegram():
    keyboard = _preview_keyboard("abcdef12")
    for row in keyboard.inline_keyboard:
        for button in row:
            assert len(button.callback_data.encode("utf-8")) <= 64


def test_pemilih_dompet_menyediakan_jalan_keluar():
    wallets = [
        SimpleNamespace(id=uuid.uuid4(), name="Bank Mandiri"),
        SimpleNamespace(id=uuid.uuid4(), name="Tunai"),
    ]
    keyboard = _wallet_picker_keyboard(wallets, "abcdef123456")
    buttons = [button for row in keyboard.inline_keyboard for button in row]

    assert any(button.text == "Bank Mandiri" for button in buttons)
    assert any(button.callback_data == "wallet_add_interactive" for button in buttons)
    for button in buttons:
        assert len(button.callback_data.encode("utf-8")) <= 64


def test_deteksi_pesan_dompet_tidak_ditemukan():
    assert _wallet_missing("Dompet 'BCA' tidak ditemukan. Dompet tersedia: Tunai.")
    assert not _wallet_missing("Jumlah transfer harus lebih besar dari nol.")
