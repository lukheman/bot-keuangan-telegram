"""Test audit copywriting UX-052.

Fokus: istilah teknis tidak bocor ke pengguna, sapaan konsisten "kamu",
dan label tombol memakai bahasa manusia.
"""

from types import SimpleNamespace

import pytest

from bot.handlers.menu import laporan_keyboard
from bot.handlers.system import HELP_HOME, HELP_TOPICS, help_keyboard
from bot.utils.messages import TIMEZONE_LABELS, zona_waktu

TERLARANG = ("JSON", "CSV", "ID Telegram", "Anda", "Telemetri", "Error")


def test_zona_waktu_memakai_label_ramah():
    assert TIMEZONE_LABELS["Asia/Jakarta"] == "WIB"
    assert zona_waktu("Asia/Makassar") == "WITA"
    assert zona_waktu("Asia/Jayapura") == "WIT"
    assert zona_waktu(None) == "WITA"


def test_bantuan_tidak_memakai_istilah_teknis():
    teks = [HELP_HOME]
    teks.extend(body for _, body in HELP_TOPICS.values())

    for pesan in teks:
        for kata in TERLARANG:
            assert kata not in pesan, f"istilah {kata!r} bocor ke bantuan"


def test_tombol_bantuan_tidak_memakai_kata_error():
    buttons = [
        button
        for row in help_keyboard().inline_keyboard
        for button in row
    ]
    assert not any("Error" in button.text for button in buttons)
    assert any(button.callback_data == "help_error" for button in buttons)


def test_tombol_unduh_memakai_bahasa_manusia():
    buttons = [
        button
        for row in laporan_keyboard().inline_keyboard
        for button in row
    ]
    texts = [button.text for button in buttons]

    assert "⬇️ Unduh data" in texts
    assert "📄 Unduh tabel" in texts
    assert not any("JSON" in text or "CSV" in text for text in texts)


@pytest.mark.asyncio
async def test_fallback_dokumen_tidak_menyuruh_ubah_ke_foto_biasa():
    """UX-054 sudah mendukung dokumen JPG/PNG, jadi pesannya harus selaras."""
    terkirim = {}

    async def reply_text(text, **kwargs):
        terkirim["text"] = text
        terkirim["kwargs"] = kwargs

    message = SimpleNamespace(
        voice=None,
        audio=None,
        document=SimpleNamespace(file_id="doc-1"),
        sticker=None,
        animation=None,
        video=None,
        reply_text=reply_text,
    )
    update = SimpleNamespace(effective_message=message)

    from bot.handlers.system import input_tidak_didukung

    await input_tidak_didukung(update, SimpleNamespace())

    assert "JPG/PNG" in terkirim["text"]
    assert "bukan dokumen" not in terkirim["text"]
