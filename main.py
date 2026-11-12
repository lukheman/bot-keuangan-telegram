import os
import logging

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)
from telegram import BotCommand
from datetime import timedelta

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from app.core.config import settings
from bot.handlers.transaction import (
    proses_gambar,
    proses_teks,
    preview_callback,
    undo_callback,
)
from bot.handlers.report import (
    ringkasan_hari_ini,
    ringkasan_minggu,
    ringkasan_bulan,
    pilih_bulan_laporan,
    unduh_bulan,
    atur_laporan_harian,
    laporan_harian_job,
)
from bot.handlers.wallet_interactive import (
    interactive_wallet_conv,
    interactive_del_wallet_menu,
    interactive_del_wallet_ask,
    interactive_del_wallet_confirm,
    interactive_rename_wallet_menu,
    interactive_rename_wallet_conv,
    cek_saldo,
)
from bot.handlers.menu import tampilkan_menu, tampilkan_menu_laporan, menu_callback
from bot.handlers.budget import budget_conv, kelola_budget
from bot.handlers.onboarding import onboarding_conv
from bot.handlers.system import (
    bantuan,
    bantuan_callback,
    perintah_tidak_dikenal,
    input_tidak_didukung,
    error_handler,
)
from bot.handlers.history import (
    delete_ask,
    delete_confirm,
    history_edit_conv,
    riwayat_callback,
    riwayat_command,
    show_detail,
)

TOKEN = settings.TELEGRAM_TOKEN

# Daftar perintah untuk menu autocomplete "/" di Telegram.
# Command destruktif/teknis sengaja tidak ditampilkan; aksesnya lewat menu.
BOT_COMMANDS = [
    BotCommand("start", "Mulai bot & buat akun"),
    BotCommand("menu", "Buka menu utama"),
    BotCommand("laporan", "Lihat laporan keuangan"),
    BotCommand("riwayat", "Lihat, edit, atau hapus transaksi"),
    BotCommand("saldo", "Cek dompet & saldo"),
    BotCommand("budget", "Atur budget bulanan"),
    BotCommand("help", "Bantuan & cara pakai"),
    BotCommand("akun", "Info & pengaturan akun"),
]


async def set_bot_commands(application) -> None:
    """Daftarkan command list ke Telegram setiap bot initialize (polling/webhook/serverless)."""
    await application.bot.set_my_commands(BOT_COMMANDS)
    logger.info(f"✅ {len(BOT_COMMANDS)} bot commands terdaftar di Telegram.")


from bot.handlers.account import (
    register_user,
    account_info,
    delete_account,
    login_web,
)
from bot.handlers.personalization import (
    personalization_conv,
    target_delete_ask,
    target_delete_confirm,
)

def create_app():
    app = ApplicationBuilder().token(TOKEN).post_init(set_bot_commands).build()

    # Onboarding harus lebih dulu agar /start dan tombol Daftar masuk ke wizard.
    app.add_handler(onboarding_conv)

    app.add_handler(CommandHandler("register", register_user))
    app.add_handler(CommandHandler("akun", account_info))
    app.add_handler(CommandHandler("hapus_akun", delete_account))
    app.add_handler(CommandHandler("login_web", login_web))
    
    app.add_handler(CommandHandler("budget", kelola_budget))
    app.add_handler(CommandHandler("unduh", unduh_bulan))
    app.add_handler(CommandHandler("laporan_harian", atur_laporan_harian))
    app.add_handler(CommandHandler("laporan", tampilkan_menu_laporan))
    app.add_handler(CommandHandler("bulan", ringkasan_bulan))
    app.add_handler(CommandHandler("riwayat", riwayat_command))
    app.add_handler(CommandHandler("help", bantuan))
    app.add_handler(CommandHandler("bantuan", bantuan))

    # Scheduler laporan otomatis tengah malam (aktif di proses long-running:
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
    app.add_handler(budget_conv)
    # Conversation personalisasi harus sebelum handler teks biasa.
    app.add_handler(personalization_conv)
    # Conversation edit transaksi juga harus sebelum handler teks biasa.
    app.add_handler(history_edit_conv)

    # Handler untuk gambar yang dikirim sebagai foto atau dokumen gambar.
    app.add_handler(MessageHandler(filters.PHOTO, proses_gambar))
    app.add_handler(MessageHandler(filters.Document.IMAGE, proses_gambar))

    # Handler untuk menu laporan via inline keyboard
    app.add_handler(CallbackQueryHandler(ringkasan_hari_ini, pattern="^laporan_hari$"))
    app.add_handler(CallbackQueryHandler(ringkasan_minggu, pattern="^laporan_minggu$"))
    app.add_handler(CallbackQueryHandler(ringkasan_bulan, pattern="^laporan_bulan$"))
    app.add_handler(CallbackQueryHandler(ringkasan_bulan, pattern="^laporan_bulan_"))
    app.add_handler(CallbackQueryHandler(pilih_bulan_laporan, pattern="^laporan_pilih_bulan$"))
    app.add_handler(CallbackQueryHandler(unduh_bulan, pattern="^laporan_unduh(_csv)?$"))
    
    app.add_handler(interactive_rename_wallet_conv)
    
    # Handler untuk Interactive Wallet Manager
    app.add_handler(CallbackQueryHandler(interactive_del_wallet_menu, pattern="^wallet_del_menu$"))
    app.add_handler(CallbackQueryHandler(interactive_del_wallet_ask, pattern="^wallet_del_ask_"))
    app.add_handler(CallbackQueryHandler(interactive_del_wallet_confirm, pattern="^wallet_del_confirm_"))
    app.add_handler(CallbackQueryHandler(interactive_rename_wallet_menu, pattern="^wallet_rename_menu$"))

    # Handler untuk memilih dompet dari pending transaction
    from bot.handlers.transaction import select_wallet_callback
    app.add_handler(CallbackQueryHandler(select_wallet_callback, pattern="^sel_w_"))
    app.add_handler(CallbackQueryHandler(preview_callback, pattern="^prev_"))
    app.add_handler(CallbackQueryHandler(undo_callback, pattern="^undo_"))

    # Handler untuk teks biasa (NLP)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, proses_teks))

    # Handler untuk akun via inline keyboard
    app.add_handler(CallbackQueryHandler(account_info, pattern="^akun_info$"))
    app.add_handler(CallbackQueryHandler(delete_account, pattern="^akun_hapus$"))
    app.add_handler(CallbackQueryHandler(delete_account, pattern="^akun_hapus_confirm$"))
    app.add_handler(CallbackQueryHandler(login_web, pattern="^akun_web$"))
    app.add_handler(
        CallbackQueryHandler(target_delete_ask, pattern="^akun_target_hapus_ask$")
    )
    app.add_handler(
        CallbackQueryHandler(
            target_delete_confirm, pattern="^akun_target_hapus_confirm$"
        )
    )

    # Pusat bantuan & FAQ in-chat (UX-055).
    app.add_handler(
        CallbackQueryHandler(
            bantuan_callback, pattern="^(menu_bantuan|help_)"
        )
    )

    # Riwayat & edit/hapus transaksi (UX-056).
    app.add_handler(
        CallbackQueryHandler(
            riwayat_callback, pattern=r"^(menu_riwayat|trx_list|trx_page_\d+)$"
        )
    )
    app.add_handler(CallbackQueryHandler(show_detail, pattern=r"^trx_view_"))
    app.add_handler(CallbackQueryHandler(delete_ask, pattern=r"^trx_del_ask_"))
    app.add_handler(CallbackQueryHandler(delete_confirm, pattern=r"^trx_del_ok_"))

    # Handler untuk menu interaktif
    app.add_handler(CallbackQueryHandler(menu_callback, pattern="^menu_"))

    # Fallback: jangan biarkan command/input apa pun tanpa balasan.
    app.add_handler(MessageHandler(filters.COMMAND, perintah_tidak_dikenal))
    app.add_handler(MessageHandler(filters.ALL, input_tidak_didukung))

    app.add_error_handler(error_handler)

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
