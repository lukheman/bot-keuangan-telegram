import os
import logging

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

from app.core.config import settings
from bot.handlers.transaction import proses_gambar, catat_pemasukan, catat_pengeluaran, konfirmasi_transaksi
from bot.handlers.report import ringkasan_hari_ini, ringkasan_minggu, ringkasan_bulan

TOKEN = settings.TELEGRAM_TOKEN

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Halo! Aku bisa membaca teks dari gambar.\n\n"
        "📸 Kirim gambar ke aku, dan aku akan mengekstrak teksnya!\n\n"
        "Perintah:\n"
        "/start - Mulai bot\n"
        "/bahasa - Cek bahasa yang tersedia\n"
        "/masuk [jumlah] [deskripsi] - Catat pemasukan\n"
        "/keluar [jumlah] [deskripsi] - Catat pengeluaran\n"
        "/hari_ini - Ringkasan hari ini\n"
        "/minggu - Ringkasan 7 hari terakhir\n"
        "/bulan [bulan] [tahun] - Ringkasan bulan tertentu"
    )

async def cek_bahasa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌐 Bahasa yang didukung:\n"
        "• `eng` - Inggris (default)\n"
        "• `ind` - Indonesia\n"
        "• `eng+ind` - Inggris + Indonesia\n\n"
        "Contoh kirim gambar dengan caption: `ind`\n"
        "untuk menggunakan bahasa Indonesia.",
        parse_mode="Markdown"
    )

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("bahasa", cek_bahasa))
    app.add_handler(CommandHandler("masuk", catat_pemasukan))
    app.add_handler(CommandHandler("keluar", catat_pengeluaran))
    app.add_handler(CommandHandler("hari_ini", ringkasan_hari_ini))
    app.add_handler(CommandHandler("hariini", ringkasan_hari_ini))
    app.add_handler(CommandHandler("minggu", ringkasan_minggu))
    app.add_handler(CommandHandler("bulan", ringkasan_bulan))

    # Handler untuk gambar yang dikirim sebagai foto
    app.add_handler(MessageHandler(filters.PHOTO, proses_gambar))

    # Handler untuk tombol konfirmasi
    app.add_handler(CallbackQueryHandler(konfirmasi_transaksi, pattern="^(simpan|batal)_"))

    logger.info("✅ Bot berjalan...")
    app.run_polling()


if __name__ == "__main__":
    main()
