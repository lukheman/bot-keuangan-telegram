import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from sqlalchemy import func, select
from app.core.database import AsyncSessionLocal
from app.core.timezone import local_now
from app.models import Transaction, TransactionType, User
from app.services.budget_service import delete_budget, list_budgets_with_usage

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
    return f"Rp{nominal:,.0f}"


async def _load_user(telegram_id: int):
    async with AsyncSessionLocal() as session:
        return (
            await session.execute(select(User).where(User.telegram_id == telegram_id))
        ).scalar_one_or_none()


async def _snapshot(user):
    """(pengeluaran_hari_ini, jumlah_transaksi_hari_ini, pengeluaran_bulan_ini)."""
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
    return today_row[0], today_row[1], month_total, today


async def tampilkan_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_user = update.effective_user
    nama = (tg_user.first_name or "Kawan").strip()
    user = await _load_user(tg_user.id)

    if user:
        now = local_now(user.timezone or DEFAULT_TZ)
        try:
            hari_ini, jumlah, bulan_ini, today = await _snapshot(user)
            ringkasan = (
                f"📅 *Hari ini ({today.strftime('%d %b')}):* "
                f"keluar {_rp(hari_ini)} ({jumlah} transaksi)\n"
                f"🗓️ *Bulan ini:* keluar {_rp(bulan_ini)}\n"
            )
        except Exception as e:
            logger.error(f"Gagal memuat ringkasan menu: {e}", exc_info=True)
            now = local_now(DEFAULT_TZ)
            ringkasan = ""
        notif_label = "🌙 Notif ✅" if user.daily_report_enabled else "🌙 Notif ❌"
    else:
        now = local_now(DEFAULT_TZ)
        ringkasan = "👋 Kamu belum terdaftar. Ketik /register dulu, atau langsung catat aja!\n"
        notif_label = "🌙 Notif ✅"

    pesan = (
        f"{_salam(now.hour)}, *{nama}*! 🤖\n\n"
        f"{ringkasan}\n"
        "💡 *Catat cepat:* ketik aja `beli kopi 20rb` atau kirim 📸 foto struk.\n\n"
        "Mau ngapain? 👇"
    )

    keyboard = [
        [
            InlineKeyboardButton("💼 Dompet & Saldo", callback_data="menu_dompet"),
            InlineKeyboardButton("📊 Laporan", callback_data="menu_laporan"),
        ],
        [
            InlineKeyboardButton("🎯 Budget", callback_data="menu_budget"),
            InlineKeyboardButton(notif_label, callback_data="menu_notif"),
        ],
        [
            InlineKeyboardButton("👤 Akun", callback_data="menu_akun"),
            InlineKeyboardButton("❓ Bantuan", callback_data="menu_bantuan"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text(pesan, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update.message.reply_text(pesan, reply_markup=reply_markup, parse_mode="Markdown")


async def _tampilkan_budget(query, telegram_id: int):
    try:
        budgets, period = await list_budgets_with_usage(telegram_id)
    except Exception as e:
        logger.error(f"Gagal memuat budget: {e}", exc_info=True)
        await query.edit_message_text("⚠️ Gagal memuat budget. Coba lagi nanti.")
        return

    if not budgets:
        text = (
            "🎯 *Budget Bulanan*\n\n"
            "Belum ada budget. Contoh:\n"
            "`/budget makanan 1jt`\n\n"
            "Bot bakal ingetin kamu pas pemakaian nyentuh 80%, 100%, atau jebol. 🚨"
        )
        keyboard = [[InlineKeyboardButton("🔙 Kembali", callback_data="menu_utama")]]
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    lines = [f"🎯 *Budget Bulan Ini ({period})*\n"]
    keyboard = []
    for item in budgets:
        lines.append(
            f"{_ikon_budget(item['pct'])} *{item['category_name']}* — {item['pct']:.0f}%\n"
            f"`{_bar(item['pct'])}`\n"
            f"{_rp(item['spent'])} / {_rp(item['limit'])}"
        )
        keyboard.append(
            [InlineKeyboardButton(f"🗑️ Hapus {item['category_name']}", callback_data=f"menu_budget_del_{item['category_name']}")]
        )
    lines.append("\n💡 Ubah: `/budget makanan 1jt`")
    keyboard.append([InlineKeyboardButton("🔙 Kembali", callback_data="menu_utama")])
    await query.edit_message_text(
        "\n\n".join(lines), parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def _tampilkan_notif(query, telegram_id: int):
    user = await _load_user(telegram_id)
    if not user:
        await query.edit_message_text("⚠️ Kamu belum terdaftar. Ketik /register dulu ya!")
        return
    status = "Aktif ✅" if user.daily_report_enabled else "Mati ❌"
    toggle = (
        InlineKeyboardButton("🔕 Matikan", callback_data="menu_notif_off")
        if user.daily_report_enabled
        else InlineKeyboardButton("🔔 Aktifkan", callback_data="menu_notif_on")
    )
    text = (
        "🌙 *Notifikasi Harian*\n\n"
        f"Status: {status}\n"
        f"Dikirim tiap jam 8 malam waktu lokal ({user.timezone or DEFAULT_TZ}).\n"
        "Isinya ringkasan pengeluaran hari itu. 🌙"
    )
    keyboard = [[toggle], [InlineKeyboardButton("🔙 Kembali", callback_data="menu_utama")]]
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


async def _set_notif(query, telegram_id: int, enabled: bool):
    async with AsyncSessionLocal() as session:
        user = (
            await session.execute(select(User).where(User.telegram_id == telegram_id))
        ).scalar_one_or_none()
        if not user:
            await query.answer("Kamu belum terdaftar. Ketik /register dulu ya!", show_alert=True)
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
        keyboard = [
            [InlineKeyboardButton("📅 Hari Ini", callback_data="laporan_hari"), InlineKeyboardButton("📆 Minggu Ini", callback_data="laporan_minggu")],
            [InlineKeyboardButton("📊 Bulan Ini", callback_data="laporan_bulan")],
            [InlineKeyboardButton("🎯 Budget Bulan Ini", callback_data="menu_budget")],
            [InlineKeyboardButton("⬇️ Unduh Bulan Ini (JSON)", callback_data="laporan_unduh")],
            [InlineKeyboardButton("🔙 Kembali", callback_data="menu_utama")]
        ]
        await query.edit_message_text(
            "📊 *Laporan Keuangan*\n\nMau lihat ringkasan yang mana? 👇",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if data == "menu_budget":
        await _tampilkan_budget(query, update.effective_user.id)
        return

    if data.startswith("menu_budget_del_"):
        nama = data.removeprefix("menu_budget_del_")
        try:
            await delete_budget(update.effective_user.id, nama)
            await query.answer(f"Budget {nama} dihapus 🗑️")
        except ValueError as e:
            await query.answer(str(e), show_alert=True)
        except Exception as e:
            logger.error(f"Gagal hapus budget via menu: {e}", exc_info=True)
            await query.answer("Gagal menghapus. Coba lagi nanti.", show_alert=True)
        await _tampilkan_budget(query, update.effective_user.id)
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
        keyboard = [
            [InlineKeyboardButton("ℹ️ Info Akun", callback_data="akun_info")],
            [InlineKeyboardButton("🌐 Login Dashboard Web", callback_data="akun_web")],
            [InlineKeyboardButton("🗑️ Hapus Akun", callback_data="akun_hapus")],
            [InlineKeyboardButton("🔙 Kembali", callback_data="menu_utama")]
        ]
        await query.edit_message_text(
            "👤 *Pengaturan Akun*\n\nPilih aksi yang ingin dilakukan: 👇",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if data == "menu_bantuan":
        await query.edit_message_text(
            "❓ *Bantuan*\n\n"
            "*✍️ Catat transaksi*\n"
            "Ketik natural aja, contoh:\n"
            "• `beli kopi 20rb`\n"
            "• `gaji 5jt`\n"
            "• `transfer bri ke tunai 500rb`\n"
            "Atau kirim 📸 foto struk.\n\n"
            "*💼 Dompet* — `/saldo`\n"
            "*🎯 Budget* — `/budget makanan 1jt`\n"
            "*⬇️ Unduh laporan* — `/unduh 10 2026` (JSON) atau tombol di menu 📊 Laporan\n"
            "*🌙 Notif harian* — otomatis jam 8 malam, atur di menu 🌙 Notif\n"
            "*🌐 Dashboard web* — via menu 👤 Akun",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kembali", callback_data="menu_utama")]])
        )
        return
