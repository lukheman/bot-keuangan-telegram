"""Test pusat bantuan & FAQ in-chat (UX-055)."""

from bot.handlers.system import (
    HELP_HOME,
    HELP_TOPICS,
    _topic_keyboard,
    help_keyboard,
)


def test_semua_topik_punya_tombol_dan_isi():
    keyboard = help_keyboard()
    buttons = [button for row in keyboard.inline_keyboard for button in row]

    for topic in HELP_TOPICS:
        assert any(
            button.callback_data == f"help_{topic}" for button in buttons
        ), f"topik {topic} tidak punya tombol"

    assert any(button.callback_data == "menu_utama" for button in buttons)
    for button in buttons:
        assert len(button.callback_data.encode("utf-8")) <= 64


def test_bantuan_utama_punya_contoh_transaksi():
    assert "kopi 20rb" in HELP_HOME
    assert "transfer bca ke tunai" in HELP_HOME


def test_tombol_kembali_dari_topik():
    keyboard = _topic_keyboard()
    callbacks = [
        button.callback_data
        for row in keyboard.inline_keyboard
        for button in row
    ]
    assert "help_home" in callbacks
    assert "menu_utama" in callbacks
