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
        reply_keyboard = [
            ["📅 Laporan Hari Ini", "📆 Laporan Minggu Ini"],
            ["📊 Laporan Bulan Ini"],
            ["🔙 Tutup Menu Laporan"]
        ]
        await query.message.reply_text(
            "📊 *Menu Laporan Aktif*\n\nSilakan gunakan menu di bawah layar untuk melihat laporan.",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=False)
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

async def tutup_menu_laporan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("🔄", reply_markup=ReplyKeyboardRemove())
    await msg.delete()
    await tampilkan_menu(update, context)
