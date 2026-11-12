"""Test UI budget berbasis tombol (UX-040/UX-044)."""

from decimal import Decimal

from app.services.budget_service import EXPENSE_CATEGORIES, parse_budget_nominal
from bot.handlers.budget import _category_keyboard


def test_pemilih_kategori_menampilkan_semua_kategori():
    keyboard = _category_keyboard()
    buttons = [button for row in keyboard.inline_keyboard for button in row]

    category_buttons = [
        button for button in buttons if button.callback_data.startswith("budget_cat_")
    ]
    assert len(category_buttons) == len(EXPENSE_CATEGORIES)
    assert any(button.text == "❌ Batal" for button in buttons)

    for button in buttons:
        assert len(button.callback_data.encode("utf-8")) <= 64


def test_parse_nominal_budget_format_indonesia():
    assert parse_budget_nominal("1jt") == Decimal("1000000")
    assert parse_budget_nominal("500rb") == Decimal("500000")
    assert parse_budget_nominal("1,5jt") == Decimal("1500000")
    assert parse_budget_nominal("500.000") == Decimal("500000")
