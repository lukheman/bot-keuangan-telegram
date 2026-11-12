"""Handler sistem: bantuan, fallback, dan error global."""

from __future__ import annotations

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import BadRequest, Forbidden
from telegram.ext import ContextTypes

from bot.utils.messages import (
    GENERIC_ERROR,
    bantuan_keyboard,
    md,
    menu_keyboard,
)
from app.services.telemetry_service import EVENT_ERROR, track

logger = logging.getLogger(__name__)

HELP_HOME = (
    "❓ *Pusat Bantuan*\n\n"
    "Pilih topik di bawah, atau langsung ketik transaksi seperti "
    "`kopi 20rb`.\n\n"
    "*Tips cepat*\n"
    "• Kirim foto struk atau file JPG/PNG\n"
    "• Transfer: `transfer bca ke tunai 100rb`\n"
    "• Sesuaikan saldo: `saldo gopay 50000`\n"
    "• Salah catat? Buka 🧾 Riwayat untuk edit atau hapus"
)

HELP_TOPICS = {
    "catat": (
        "✍️ Catat transaksi",
        "*Catat transaksi*\n\n"
        "Ketik bebas, contoh:\n"
        "• `kopi 20rb`\n"
        "• `gaji 5jt`\n"
        "• `transfer bca ke tunai 100rb`\n"
        "• `saldo gopay 50000` untuk menyesuaikan saldo\n\n"
        "Kirim foto struk atau file JPG/PNG. Kalau AI kurang yakin, bot "
        "menampilkan pratinjau sebelum menyimpan.",
    ),
    "dompet": (
        "💼 Dompet & saldo",
        "*Dompet & saldo*\n\n"
        "Buka menu 💼 Dompet untuk menambah, mengganti nama, atau menghapus "
        "dompet. Saldo awal bisa diisi saat membuat dompet.\n\n"
        "Kalau nama dompet tidak ditemukan saat transaksi, bot menawarkan "
        "tombol pilih dompet atau buat dompet baru.",
    ),
    "budget": (
        "🎯 Budget",
        "*Budget bulanan*\n\n"
        "Buka 🎯 Budget → `➕ Atur budget` → pilih kategori → ketik nominal "
        "(`1jt`, `500rb`, atau `500000`).\n\n"
        "Bot memberi peringatan saat pemakaian mencapai 80%, 100%, atau "
        "melebihi budget.",
    ),
    "laporan": (
        "📊 Laporan",
        "*Laporan*\n\n"
        "Menu 📊 Laporan berisi hari ini, 7 hari terakhir, bulan ini, pilih "
        "bulan, serta unduh data atau tabel.\n\n"
        "Total saldo dompet dan selisih periode ditampilkan terpisah agar "
        "mudah dibaca.",
    ),
    "notif": (
        "🌙 Notifikasi",
        "*Notifikasi harian*\n\n"
        "Aktifkan atau matikan lewat menu 🌙 Notifikasi, atau ketik "
        "`/laporan_harian on` dan `/laporan_harian off`.\n\n"
        "Laporan dikirim tiap 00:00 waktu lokal, hanya jika ada transaksi.",
    ),
    "akun": (
        "👤 Akun",
        "*Akun*\n\n"
        "Menu 👤 Akun menampilkan zona waktu, dompet utama, jumlah dompet, "
        "status notifikasi, dan tombol hapus akun.\n\n"
        "Zona waktu memengaruhi tanggal laporan dan pengiriman notifikasi.",
    ),
    "privasi": (
        "🔒 Privasi AI",
        "*Privasi AI*\n\n"
        "Teks dan foto struk diproses layanan AI (Groq) hanya untuk membaca "
        "transaksi. Catatan penggunaan bot hanya berisi jenis kejadian, bukan "
        "isi pesan atau nominal.\n\n"
        "Hapus akun akan menghapus transaksi, dompet, budget, dan kategori.",
    ),
    "error": (
        "🆘 Kendala & sesi",
        "*Kalau ada masalah*\n\n"
        "• Sesi kedaluwarsa: kirim ulang transaksi.\n"
        "• AI sibuk: tunggu sebentar atau catat manual.\n"
        "• Data salah: buka 🧾 Riwayat untuk edit atau hapus, atau tekan "
        "`↩️ Batalkan transaksi` di pesan sukses.\n"
        "• Masih bingung: buka menu utama lalu pilih Bantuan lagi.",
    ),
}


def help_keyboard() -> InlineKeyboardMarkup:
    callbacks = [
        ("✍️ Catat transaksi", "help_catat"),
        ("💼 Dompet", "help_dompet"),
        ("🎯 Budget", "help_budget"),
        ("📊 Laporan", "help_laporan"),
        ("🌙 Notifikasi", "help_notif"),
        ("👤 Akun", "help_akun"),
        ("🔒 Privasi AI", "help_privasi"),
        ("🆘 Kendala & sesi", "help_error"),
    ]
    rows = [
        [
            InlineKeyboardButton(text, callback_data=data)
            for text, data in callbacks[index:index + 2]
        ]
        for index in range(0, len(callbacks), 2)
    ]
    rows.append([InlineKeyboardButton("🏠 Menu", callback_data="menu_utama")])
    return InlineKeyboardMarkup(rows)


def _topic_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🔙 Kembali", callback_data="help_home")],
            [InlineKeyboardButton("🏠 Menu", callback_data="menu_utama")],
        ]
    )


async def bantuan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Command /help dan /bantuan."""
    if update.effective_message is None:
        return
    await update.effective_message.reply_text(
        HELP_HOME,
        parse_mode="Markdown",
        reply_markup=help_keyboard(),
    )


async def bantuan_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menu Bantuan dan topik FAQ in-chat (UX-055)."""
    query = update.callback_query
    if query is None:
        return
    await query.answer()

    data = query.data or ""
    if data in ("menu_bantuan", "help_home"):
        await query.edit_message_text(
            HELP_HOME,
            parse_mode="Markdown",
            reply_markup=help_keyboard(),
        )
        return

    topic = data.removeprefix("help_")
    if topic in HELP_TOPICS:
        _, body = HELP_TOPICS[topic]
        await query.edit_message_text(
            body,
            parse_mode="Markdown",
            reply_markup=_topic_keyboard(),
        )
        return

    await query.edit_message_text(
        HELP_HOME,
        parse_mode="Markdown",
        reply_markup=help_keyboard(),
    )


async def perintah_tidak_dikenal(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Fallback untuk command yang tidak terdaftar."""
    if update.effective_message is None or not update.effective_message.text:
        return

    command = update.effective_message.text.split()[0]
    await update.effective_message.reply_text(
        f"Aku belum paham perintah `{md(command)}`.\n\n{HELP_HOME}",
        parse_mode="Markdown",
        reply_markup=bantuan_keyboard(),
    )


async def input_tidak_didukung(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Fallback untuk voice, dokumen, sticker, dan input non-teks lain."""
    message = update.effective_message
    if message is None:
        return

    if message.voice or message.audio:
        text = (
            "🎙️ Aku belum bisa mendengar voice note.\n\n"
            "Sementara ini, ketik saja transaksinya:\n"
            "`makan siang 25rb`\n"
            "Atau kirim foto struk."
        )
    elif message.document:
        text = (
            "📎 File itu belum bisa kubaca.\n\n"
            "Kirim foto biasa atau file JPG/PNG, atau ketik transaksinya:\n"
            "`beli obat 35rb`"
        )
    elif message.sticker or message.animation or message.video:
        text = (
            "🙂 Aku belum bisa memproses jenis pesan ini.\n\n"
            "Coba ketik transaksi seperti `kopi 20rb`, kirim foto struk, "
            "atau buka menu di bawah."
        )
    else:
        text = (
            "🙂 Aku belum bisa memproses pesan ini.\n\n"
            "Coba ketik transaksi seperti `kopi 20rb` atau kirim foto struk."
        )

    await message.reply_text(
        text, parse_mode="Markdown", reply_markup=bantuan_keyboard()
    )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Tangkap semua exception agar pengguna selalu mendapat balasan ramah."""
    error = context.error

    if isinstance(error, BadRequest) and "Message is not modified" in str(error):
        return
    if isinstance(error, Forbidden):
        logger.warning("Bot tidak bisa mengirim pesan ke user: %s", error)
        return

    logger.error(
        "Unhandled error pada update %s",
        getattr(update, "update_id", "-"),
        exc_info=error,
    )
    await track(
        getattr(getattr(update, "effective_user", None), "id", None),
        EVENT_ERROR,
        error_type=type(error).__name__,
        update_id=str(getattr(update, "update_id", "-")),
    )

    if not isinstance(update, Update):
        return

    try:
        if update.callback_query is not None:
            try:
                await update.callback_query.answer(
                    "Terjadi gangguan. Coba lagi sebentar.", show_alert=True
                )
            except BadRequest:
                pass
            if update.effective_chat is not None:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=GENERIC_ERROR,
                    reply_markup=bantuan_keyboard(),
                )
        elif update.effective_message is not None:
            await update.effective_message.reply_text(
                GENERIC_ERROR, reply_markup=bantuan_keyboard()
            )
    except Exception:
        logger.exception("Gagal mengirim pesan error ke pengguna")
