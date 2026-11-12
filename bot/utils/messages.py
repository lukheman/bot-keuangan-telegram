"""Helper untuk pesan Telegram yang aman dan konsisten."""

from __future__ import annotations

import re
import uuid
from decimal import Decimal

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Legacy Markdown hanya membutuhkan escape untuk karakter ini.
_MD_SPECIAL = re.compile(r"([\\_*`\[])")


def md(value: object) -> str:
    """Escape konten dinamis agar tidak mematahkan parse_mode Markdown."""
    if value is None:
        return ""
    return _MD_SPECIAL.sub(r"\\\1", str(value))


def rupiah(value: object) -> str:
    """Format nominal gaya Indonesia: Rp20.000 (titik ribuan)."""
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return "Rp0"
    sign = "-" if amount < 0 else ""
    return f"{sign}Rp{abs(amount):,.0f}".replace(",", ".")


# Nama zona waktu yang dikenali pengguna awam.
TIMEZONE_LABELS = {
    "Asia/Jakarta": "WIB",
    "Asia/Makassar": "WITA",
    "Asia/Jayapura": "WIT",
}


def zona_waktu(value: object) -> str:
    """Ubah nama zona waktu teknis menjadi label ramah (WIB/WITA/WIT)."""
    key = str(value or "").strip()
    return TIMEZONE_LABELS.get(key, key or "WITA")


def build_wallet_callback_data(tx_id: str, wallet_id: object) -> str:
    """Bangun callback_data pemilihan dompet, dijamin <= 64 byte.

    Telegram membatasi callback_data 1-64 byte. UUID penuh (36 karakter)
    membuat data melewati batas saat digabung dengan tx_id panjang.
    """
    wallet_hex = wallet_id.hex if isinstance(wallet_id, uuid.UUID) else str(wallet_id).replace("-", "")
    tx_token = str(tx_id)[:12]
    data = f"sel_w_{tx_token}_{wallet_hex}"
    if len(data.encode("utf-8")) > 64:
        raise ValueError("callback_data melebihi batas Telegram")
    return data


def menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("🏠 Menu", callback_data="menu_utama")]]
    )


def bantuan_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("❓ Bantuan", callback_data="menu_bantuan")],
            [InlineKeyboardButton("🏠 Menu", callback_data="menu_utama")],
        ]
    )


def transaksi_keyboard(tx_id: str | None = None) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton("🧾 Riwayat", callback_data="trx_list"),
            InlineKeyboardButton("📊 Laporan", callback_data="menu_laporan"),
            InlineKeyboardButton("🏠 Menu", callback_data="menu_utama"),
        ]
    ]
    if tx_id:
        rows.insert(
            0,
            [InlineKeyboardButton("↩️ Batalkan transaksi", callback_data=f"undo_{tx_id}")],
        )
    return InlineKeyboardMarkup(rows)


GENERIC_ERROR = (
    "Maaf, ada gangguan saat memproses permintaanmu.\n\n"
    "Coba lagi sebentar. Kalau masih gagal, buka menu utama dan ulangi dari sana."
)

SAVE_ERROR = (
    "Maaf, transaksi belum berhasil disimpan karena ada gangguan.\n\n"
    "Coba lagi sebentar, ya."
)

SESSION_EXPIRED = "⌛ Sesi ini sudah kedaluwarsa.\n\nTransaksi belum tersimpan. Silakan kirim ulang."

AI_UNAVAILABLE = (
    "⚠️ Layanan pembaca transaksi sedang sibuk.\n\n"
    "Coba lagi dalam beberapa saat, atau catat manual seperti `kopi 20rb`."
)


def is_money(value: str) -> bool:
    try:
        Decimal(value)
        return True
    except Exception:
        return False
