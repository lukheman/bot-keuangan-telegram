from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes

async def tampilkan_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("💼 Cek Dompet", callback_data="menu_dompet"),
            InlineKeyboardButton("📊 Laporan", callback_data="menu_laporan")
        ],
        [
            InlineKeyboardButton("👤 Akun", callback_data="menu_akun"),
            InlineKeyboardButton("📈 Bantuan Pencatatan", callback_data="menu_bantuan")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    pesan = (
        "🤖 *Menu Utama Bot Keuangan*\n\n"
        "Pilih salah satu menu di bawah ini. "
        "Kamu juga bisa mengirimkan *gambar struk* kapan saja untuk mencatat otomatis!"
    )

    if update.callback_query:
        await update.callback_query.edit_message_text(pesan, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update.message.reply_text(pesan, reply_markup=reply_markup, parse_mode="Markdown")

async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "menu_utama":
        await tampilkan_menu(update, context)
        return

    if data == "menu_dompet":
        from bot.handlers.wallet_interactive import get_wallet_menu_content
        text, reply_markup = await get_wallet_menu_content(update.effective_user.id)
        await query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        return

    if data == "menu_laporan":
        keyboard = [
            [InlineKeyboardButton("📅 Hari Ini", callback_data="laporan_hari"), InlineKeyboardButton("📆 Minggu Ini", callback_data="laporan_minggu")],
            [InlineKeyboardButton("📊 Bulan Ini", callback_data="laporan_bulan")],
            [InlineKeyboardButton("🔙 Kembali", callback_data="menu_utama")]
        ]
        await query.edit_message_text(
            "📊 *Pilih Jenis Laporan*\n\nSilakan pilih rentang waktu laporan yang ingin Anda lihat:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if data == "menu_akun":
        keyboard = [
            [InlineKeyboardButton("ℹ️ Info Akun", callback_data="akun_info")],
            [InlineKeyboardButton("🌐 Login Dashboard Web", callback_data="akun_web")],
            [InlineKeyboardButton("🗑️ Hapus Akun", callback_data="akun_hapus")],
            [InlineKeyboardButton("🔙 Kembali", callback_data="menu_utama")]
        ]
        await query.edit_message_text(
            "👤 *Pengaturan Akun*\n\nPilih aksi yang ingin dilakukan:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if data == "menu_bantuan":
        await query.edit_message_text(
            "📈 *Bantuan Pencatatan*\n\n"
            "• *Otomatis:* Kirim foto struk belanja / bukti transfer ke bot ini.\n"
            "• *Manual:* Ketik `/masuk [nominal] [keterangan]` atau `/keluar [nominal] [keterangan]`.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kembali", callback_data="menu_utama")]])
        )
        return


