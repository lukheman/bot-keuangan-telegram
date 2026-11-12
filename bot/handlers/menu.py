import logging
import uuid
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from sqlalchemy import func, select
from app.core.database import AsyncSessionLocal
from app.core.timezone import local_now
from app.models import Transaction, TransactionType, User, Wallet
from app.services.budget_service import (
    delete_budget_by_id,
    get_budget_detail,
    list_budgets_with_usage,
)
from app.services.personalization_service import savings_progress
from bot.handlers.personalization import account_keyboard
from bot.utils.messages import md, rupiah, zona_waktu
from bot.utils.users import ensure_user

logger = logging.getLogger(__name__)

DEFAULT_TZ = "Asia/Makassar"
BAR_WIDTH = 10


def _salam(hour: int) -> str:
    if hour < 11:
        return "Selamat pagi"
    if hour < 15:
        return "Selamat siang"
    if hour < 19:
        return "Selamat sore"
    return "Selamat malam"


def _bar(pct: float, width: int = BAR_WIDTH) -> str:
    filled = max(0, min(width, int(pct / 100 * width)))
    return "▓" * filled + "░" * (width - filled)


def _ikon_budget(pct: float) -> str:
    if pct > 100:
        return "🚨"
    if pct >= 100:
        return "⛔"
    if pct >= 80:
        return "⚠️"
    return "✅"


def _rp(nominal) -> str:
    return rupiah(nominal)


async def _load_user(telegram_id: int):
    async with AsyncSessionLocal() as session:
        return (
            await session.execute(select(User).where(User.telegram_id == telegram_id))
        ).scalar_one_or_none()


async def _snapshot(user):
    """Ringkasan menu: pengeluaran hari ini, bulan ini, dan total saldo."""
    tz = user.timezone or DEFAULT_TZ
    today = local_now(tz).date()
    first_of_month = today.replace(day=1)
    async with AsyncSessionLocal() as session:
        today_row = (
            await session.execute(
                select(
                    func.coalesce(func.sum(Transaction.amount), 0),
                    func.count(Transaction.id),
                ).where(
                    Transaction.user_id == user.id,
                    Transaction.type == TransactionType.EXPENSE,
                    Transaction.date == today,
                )
            )
        ).one()
        month_total = (
            await session.execute(
                select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                    Transaction.user_id == user.id,
                    Transaction.type == TransactionType.EXPENSE,
                    Transaction.date >= first_of_month,
                    Transaction.date <= today,
                )
            )
        ).scalar_one()
        total_balance = (
            await session.execute(
                select(func.coalesce(func.sum(Wallet.balance), 0)).where(
                    Wallet.user_id == user.id
                )
            )
        ).scalar_one()
    return today_row[0], today_row[1], month_total, today, total_balance


async def tampilkan_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_user = update.effective_user
    if tg_user is None:
        return

    await ensure_user(tg_user)
    user = await _load_user(tg_user.id)
    nama = md(
        (
            (user.nickname if user and user.nickname else None)
            or tg_user.first_name
            or "Kawan"
        ).strip()
    )

    if user:
        now = local_now(user.timezone or DEFAULT_TZ)
        try:
            hari_ini, jumlah, bulan_ini, today, total_saldo = await _snapshot(user)
            ringkasan = (
                f"📅 *Hari ini ({today.strftime('%d %b')}):* "
                f"keluar {_rp(hari_ini)} ({jumlah} transaksi)\n"
                f"🗓️ *Bulan ini:* keluar {_rp(bulan_ini)}\n"
            )
            if user.savings_target:
                progress = savings_progress(user.savings_target, total_saldo)
                ringkasan += (
                    f"🎯 *Target tabungan:* {_rp(progress['total'])} / "
                    f"{_rp(progress['target'])} ({progress['pct']:.0f}%)\n"
                )
        except Exception as e:
            logger.error(f"Gagal memuat ringkasan menu: {e}", exc_info=True)
            now = local_now(DEFAULT_TZ)
            ringkasan = ""
        notif_label = "🌙 Notifikasi ✅" if user.daily_report_enabled else "🌙 Notifikasi ❌"
    else:
        now = local_now(DEFAULT_TZ)
        ringkasan = (
            "👋 Akunmu belum aktif. Ketuk tombol Daftar di bawah—cukup satu klik.\n"
        )
        notif_label = "🌙 Notifikasi ✅"

    pesan = (
        f"{_salam(now.hour)}, *{nama}*! 🤖\n\n"
        f"{ringkasan}\n"
        "💡 *Catat cepat:* ketik saja `beli kopi 20rb` atau kirim 📸 foto struk.\n\n"
        "Mau mulai dari mana? 👇"
    )

    keyboard = [
        [
            InlineKeyboardButton("💼 Dompet & Saldo", callback_data="menu_dompet"),
            InlineKeyboardButton("📊 Laporan", callback_data="menu_laporan"),
        ],
        [
            InlineKeyboardButton("🧾 Riwayat", callback_data="menu_riwayat"),
            InlineKeyboardButton("🎯 Budget", callback_data="menu_budget"),
        ],
        [
            InlineKeyboardButton(notif_label, callback_data="menu_notif"),
            InlineKeyboardButton("👤 Akun", callback_data="menu_akun"),
        ],
        [InlineKeyboardButton("❓ Bantuan", callback_data="menu_bantuan")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text(pesan, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update.message.reply_text(pesan, reply_markup=reply_markup, parse_mode="Markdown")


def laporan_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("📅 Hari Ini", callback_data="laporan_hari"),
                InlineKeyboardButton("📆 7 Hari Terakhir", callback_data="laporan_minggu"),
            ],
            [
                InlineKeyboardButton("📊 Bulan Ini", callback_data="laporan_bulan"),
                InlineKeyboardButton("📅 Pilih Bulan", callback_data="laporan_pilih_bulan"),
            ],
            [InlineKeyboardButton("🎯 Budget Bulan Ini", callback_data="menu_budget")],
            [InlineKeyboardButton("🧾 Riwayat Transaksi", callback_data="menu_riwayat")],
            [
                InlineKeyboardButton("⬇️ Unduh data", callback_data="laporan_unduh"),
                InlineKeyboardButton("📄 Unduh tabel", callback_data="laporan_unduh_csv"),
            ],
            [InlineKeyboardButton("🔙 Kembali", callback_data="menu_utama")],
        ]
    )


async def tampilkan_menu_laporan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tampilkan menu laporan, baik dari command /laporan maupun callback."""
    text = "📊 *Laporan Keuangan*\n\nMau lihat ringkasan yang mana? 👇"
    keyboard = laporan_keyboard()
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text, parse_mode="Markdown", reply_markup=keyboard
        )
    elif update.effective_message is not None:
        await update.effective_message.reply_text(
            text, parse_mode="Markdown", reply_markup=keyboard
        )


async def _tampilkan_budget(query, telegram_id: int):
    try:
        budgets, period = await list_budgets_with_usage(telegram_id)
    except Exception as e:
        logger.error(f"Gagal memuat budget: {e}", exc_info=True)
        await query.edit_message_text(
            "Maaf, budget belum bisa dimuat. Coba lagi sebentar.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 Kembali", callback_data="menu_utama")]]
            ),
        )
        return

    if not budgets:
        text = (
            "🎯 *Budget Bulanan*\n\n"
            "Belum ada budget. Tekan tombol di bawah untuk memilih kategori "
            "tanpa perlu hafal nama.\n\n"
            "Bot akan mengingatkanmu saat pemakaian mencapai 80%, 100%, atau "
            "melebihi budget. 🚨"
        )
        keyboard = [
            [InlineKeyboardButton("➕ Atur budget", callback_data="menu_budget_add")],
            [InlineKeyboardButton("🔙 Kembali", callback_data="menu_utama")],
        ]
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    lines = [f"🎯 *Budget Bulan Ini ({period})*\n"]
    keyboard = [
        [InlineKeyboardButton("➕ Atur budget", callback_data="menu_budget_add")]
    ]
    for item in budgets:
        nama_kategori = md(item["category_name"])
        category_token = str(item["category_id"]).replace("-", "")
        lines.append(
            f"{_ikon_budget(item['pct'])} *{nama_kategori}* — {item['pct']:.0f}%\n"
            f"`{_bar(item['pct'])}`\n"
            f"{_rp(item['spent'])} / {_rp(item['limit'])}"
        )
        keyboard.append(
            [InlineKeyboardButton(f"🗑️ Hapus {item['category_name']}", callback_data=f"menu_budget_del_ask_{category_token}")]
        )
    lines.append("\n💡 Atur atau ubah budget lewat tombol di bawah.")
    keyboard.append([InlineKeyboardButton("🔙 Kembali", callback_data="menu_utama")])
    await query.edit_message_text(
        "\n\n".join(lines), parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def _tampilkan_notif(query, telegram_id: int):
    user = await _load_user(telegram_id)
    if not user:
        await query.edit_message_text(
            "⚠️ Akunmu belum aktif. Tekan tombol di bawah untuk mulai.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🚀 Daftar", callback_data="start_ulang")]]
            ),
        )
        return
    status = "Aktif ✅" if user.daily_report_enabled else "Nonaktif ❌"
    toggle = (
        InlineKeyboardButton("🔕 Matikan", callback_data="menu_notif_off")
        if user.daily_report_enabled
        else InlineKeyboardButton("🔔 Aktifkan", callback_data="menu_notif_on")
    )
    text = (
        "🌙 *Notifikasi Harian*\n\n"
        f"Status: {status}\n"
        f"Dikirim tiap jam 12 malam (00:00) waktu lokal "
        f"({zona_waktu(user.timezone or DEFAULT_TZ)}).\n"
        "Isinya ringkasan transaksi hari yang baru selesai. 🌙"
    )
    keyboard = [[toggle], [InlineKeyboardButton("🔙 Kembali", callback_data="menu_utama")]]
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


async def _set_notif(query, telegram_id: int, enabled: bool):
    async with AsyncSessionLocal() as session:
        user = (
            await session.execute(select(User).where(User.telegram_id == telegram_id))
        ).scalar_one_or_none()
        if not user:
            await query.answer(
                "Akunmu belum aktif. Kirim /start dulu, ya.", show_alert=True
            )
            return
        user.daily_report_enabled = enabled
        await session.commit()
    await query.answer("Notifikasi harian diaktifkan ✅" if enabled else "Notifikasi harian dimatikan ❌")
    await _tampilkan_notif(query, telegram_id)


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
        await tampilkan_menu_laporan(update, context)
        return

    if data == "menu_budget":
        await _tampilkan_budget(query, update.effective_user.id)
        return

    if data.startswith("menu_budget_del_ask_"):
        token = data.removeprefix("menu_budget_del_ask_")
        try:
            detail = await get_budget_detail(update.effective_user.id, token)
        except Exception as e:
            logger.error(f"Gagal memuat detail budget: {e}", exc_info=True)
            await query.answer("Gagal memuat budget. Coba lagi nanti.", show_alert=True)
            return
        if detail is None:
            await query.answer("Budget tidak ditemukan atau sudah dihapus.", show_alert=True)
            await _tampilkan_budget(query, update.effective_user.id)
            return
        nama, limit = detail
        keyboard = [
            [InlineKeyboardButton("Ya, hapus", callback_data=f"menu_budget_del_confirm_{token}")],
            [InlineKeyboardButton("Batal", callback_data="menu_budget")],
        ]
        await query.edit_message_text(
            f"⚠️ *Hapus budget {md(nama)}?*\n\n"
            f"Batas {_rp(limit)}/bulan akan dihapus. "
            "Transaksi yang sudah ada tidak ikut terhapus.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    if data.startswith("menu_budget_del_confirm_"):
        token = data.removeprefix("menu_budget_del_confirm_")
        try:
            nama = await delete_budget_by_id(update.effective_user.id, token)
            await query.answer(f"Budget {nama} dihapus 🗑️")
        except ValueError as e:
            await query.answer(str(e), show_alert=True)
        except Exception as e:
            logger.error(f"Gagal hapus budget via menu: {e}", exc_info=True)
            await query.answer("Gagal menghapus. Coba lagi nanti.", show_alert=True)
        await _tampilkan_budget(query, update.effective_user.id)
        return

    if data.startswith("menu_budget_del_"):
        # Tombol dari versi menu lama.
        await query.answer(
            "Menu ini sudah kedaluwarsa. Buka ulang menu Budget ya.",
            show_alert=True,
        )
        return

    if data == "menu_notif":
        await _tampilkan_notif(query, update.effective_user.id)
        return

    if data == "menu_notif_on":
        await _set_notif(query, update.effective_user.id, True)
        return

    if data == "menu_notif_off":
        await _set_notif(query, update.effective_user.id, False)
        return

    if data == "menu_akun":
        await query.edit_message_text(
            "👤 *Pengaturan Akun*\n\nPilih aksi yang ingin dilakukan: 👇",
            parse_mode="Markdown",
            reply_markup=account_keyboard(),
        )
        return

    if data == "menu_bantuan":
        from bot.handlers.system import bantuan_callback

        await bantuan_callback(update, context)
        return

    # Menu lama / callback tak dikenal.
    await query.edit_message_text(
        "Menu ini sudah kedaluwarsa. Silakan buka menu utama lagi.",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("🏠 Menu", callback_data="menu_utama")]]
        ),
    )
