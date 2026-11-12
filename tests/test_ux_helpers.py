"""Test helper UX yang dipakai lintas handler."""

import uuid
from decimal import Decimal

import pytest

from bot.utils.messages import (
    build_wallet_callback_data,
    md,
    rupiah,
    transaksi_keyboard,
)
from bot.utils.parsing import parse_rupiah


def test_md_escapes_legacy_markdown_characters():
    assert md("Harga *promo* [50%]_cash") == r"Harga \*promo\* \[50%]\_cash"
    assert md(None) == ""


def test_rupiah_formats_tanpa_desimal():
    assert rupiah(20000) == "Rp20.000"
    assert rupiah("1500000") == "Rp1.500.000"
    assert rupiah(-20000) == "-Rp20.000"
    assert rupiah(None) == "Rp0"


def test_build_wallet_callback_data_di_bawah_batas_telegram():
    tx_id = "abcdef12"
    wallet_id = uuid.uuid4()
    data = build_wallet_callback_data(tx_id, wallet_id)
    assert len(data.encode("utf-8")) <= 64
    assert data.startswith("sel_w_abcdef12_")
    # Hex tanpa dash agar UUID tetap bisa direkonstruksi.
    assert uuid.UUID(data.split("_")[3]).int == wallet_id.int


def test_tombol_undo_di_bawah_batas_telegram():
    tx_id = uuid.uuid4().hex
    keyboard = transaksi_keyboard(tx_id)
    undo_button = keyboard.inline_keyboard[0][0]
    assert undo_button.callback_data == f"undo_{tx_id}"
    assert len(undo_button.callback_data.encode("utf-8")) <= 64


@pytest.mark.parametrize(
    "text,expected",
    [
        ("500000", Decimal("500000")),
        ("Rp500.000", Decimal("500000")),
        ("500rb", Decimal("500000")),
        ("20k", Decimal("20000")),
        ("1,5jt", Decimal("1500000")),
        ("1.5jt", Decimal("1500000")),
        ("2 juta", Decimal("2000000")),
    ],
)
def test_parse_rupiah_variasi_wajar(text, expected):
    assert parse_rupiah(text) == expected


@pytest.mark.parametrize("text", ["", "abc", "-5000", "Rp"])
def test_parse_rupiah_menolak_input_tidak_valid(text):
    with pytest.raises(ValueError):
        parse_rupiah(text)
