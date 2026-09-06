import os
import logging

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)
from telegram import BotCommand, Update
from datetime import timedelta

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

from app.core.config import settings
from bot.handlers.transaction import proses_gambar, proses_teks
from bot.handlers.report import (
    ringkasan_hari_ini,
    ringkasan_minggu,
    ringkasan_bulan,
    atur_laporan_harian,
    laporan_harian_job,
)
from bot.handlers.wallet_interactive import (
    interactive_wallet_conv, 
    interactive_del_wallet_menu, 
    interactive_del_wallet_action,
    interactive_rename_wallet_menu,
    interactive_rename_wallet_conv,
    cek_saldo
)
from bot.handlers.menu import tampilkan_menu, menu_callback
from bot.handlers.budget import kelola_budget

TOKEN = settings.TELEGRAM_TOKEN

# Daftar perintah untuk menu autocomplete "/" di Telegram.
BOT_COMMANDS = [
    BotCommand("start", "Mulai bot"),
    BotCommand("menu", "Tampilkan menu interaktif"),
    BotCommand("saldo", "Cek daftar dompet & saldo"),
    BotCommand("dompet", "Cek daftar dompet & saldo"),
    BotCommand("budget", "Atur budget bulanan"),
    BotCommand("laporan_harian", "Notifikasi laporan otomatis jam 8 malam"),
    BotCommand("register", "Daftarkan akun"),
    BotCommand("akun", "Info akun"),
    BotCommand("login_web", "Login dashboard web"),
    BotCommand("hapus_akun", "Hapus akun"),
]


async def set_bot_commands(application) -> None:
    """Daftarkan command list ke Telegram setiap bot initialize (polling/webhook/serverless)."""
    await application.bot.set_my_commands(BOT_COMMANDS)
    logger.info(f"✅ {len(BOT_COMMANDS)} bot commands terdaftar di Telegram.")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Halo! Aku bisa membaca teks dari gambar.\n\n"
        "📸 Kirim gambar ke aku, dan aku akan mengekstrak teksnya!\n\n"
        "Perintah:\n"
        "/start - Mulai bot\n"
        "/saldo - Cek daftar dompet & saldo\n"
        "/budget [kategori] [nominal] - Atur budget bulanan\n"
        "/laporan_harian [on|off] - Notifikasi laporan otomatis jam 8 malam\n"
        "/menu - Tampilkan menu interaktif"
    )

from bot.handlers.account import register_user, account_info, delete_account, login_web

def create_app():
    app = ApplicationBuilder().token(TOKEN).post_init(set_bot_commands).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("register", register_user))
    app.add_handler(CommandHandler("akun", account_info))
    app.add_handler(CommandHandler("hapus_akun", delete_account))
    app.add_handler(CommandHandler("login_web", login_web))
    
    app.add_handler(CommandHandler("budget", kelola_budget))
    app.add_handler(CommandHandler("laporan_harian", atur_laporan_harian))

    # Scheduler laporan otomatis jam 8 malam (aktif di proses long-running:
    # polling maupun webhook server biasa; di serverless tidak persist).
    if app.job_queue is not None:
        app.job_queue.run_repeating(
            laporan_harian_job,
            interval=timedelta(minutes=15),
            first=timedelta(seconds=60),
            name="laporan_harian_otomatis",
        )
    app.add_handler(CommandHandler("menu", tampilkan_menu))
    app.add_handler(CommandHandler("saldo", cek_saldo))
    app.add_handler(CommandHandler("dompet", cek_saldo))

    app.add_handler(interactive_wallet_conv)

    # Handler untuk gambar yang dikirim sebagai foto
    app.add_handler(MessageHandler(filters.PHOTO, proses_gambar))

    # Handler untuk menu laporan via inline keyboard
    app.add_handler(CallbackQueryHandler(ringkasan_hari_ini, pattern="^laporan_hari$"))
    app.add_handler(CallbackQueryHandler(ringkasan_minggu, pattern="^laporan_minggu$"))
    app.add_handler(CallbackQueryHandler(ringkasan_bulan, pattern="^laporan_bulan$"))
    
    app.add_handler(interactive_rename_wallet_conv)
    
    # Handler untuk Interactive Wallet Manager
    app.add_handler(CallbackQueryHandler(interactive_del_wallet_menu, pattern="^wallet_del_menu$"))
    app.add_handler(CallbackQueryHandler(interactive_del_wallet_action, pattern="^wallet_del_action_"))
    app.add_handler(CallbackQueryHandler(interactive_rename_wallet_menu, pattern="^wallet_rename_menu$"))

    # Handler untuk memilih dompet dari pending transaction
    from bot.handlers.transaction import select_wallet_callback
    app.add_handler(CallbackQueryHandler(select_wallet_callback, pattern="^sel_w_"))

    # Handler untuk teks biasa (NLP)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, proses_teks))

    # Handler untuk akun via inline keyboard
    app.add_handler(CallbackQueryHandler(account_info, pattern="^akun_info$"))
    app.add_handler(CallbackQueryHandler(delete_account, pattern="^akun_hapus$"))
    app.add_handler(CallbackQueryHandler(login_web, pattern="^akun_web$"))

    # Handler untuk menu interaktif
    app.add_handler(CallbackQueryHandler(menu_callback, pattern="^menu_"))

    return app

def main():
    app = create_app()
    logger.info("✅ Menyiapkan Bot...")
    if settings.WEBHOOK_URL:
        logger.info(f"🌐 Menggunakan metode WEBHOOK pada port {settings.PORT}")
        logger.info(f"🔗 Webhook URL: {settings.WEBHOOK_URL}")
        app.run_webhook(
            listen="0.0.0.0",
            port=settings.PORT,
            webhook_url=settings.WEBHOOK_URL
        )
    else:
        logger.info("🔄 Menggunakan metode LONG POLLING")
        app.run_polling()

if __name__ == "__main__":
    main()
