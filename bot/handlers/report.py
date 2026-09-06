from collections import defaultdict
from functools import partial
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.core.timezone import local_now
from app.services.report_service import get_daily_summary, get_weekly_summary, get_monthly_summary, get_user_local_date
from app.models import TransactionType, User
import logging

logger = logging.getLogger(__name__)
TELEGRAM_MESSAGE_LIMIT = 4096
# Jam lokal user untuk pengiriman laporan harian otomatis (20:00).
AUTO_REPORT_HOUR_LOCAL = 20

async def _send_report(reply_func, message, reply_markup=None, overflow_func=None):
    lines = message.splitlines(keepends=True)
    chunks = []
    current = ""

    for line in lines:
        if len(current) + len(line) > TELEGRAM_MESSAGE_LIMIT:
            if current:
                chunks.append(current)
            current = line
        else:
            current += line

    if current:
        chunks.append(current)

    for index, chunk in enumerate(chunks):
        send_func = reply_func if index == 0 or overflow_func is None else overflow_func
        await send_func(
            chunk,
            parse_mode="Markdown",
            reply_markup=reply_markup if index == len(chunks) - 1 else None,
        )

def _format_transactions(transactions, total_income, total_expense, title, include_date=False, include_balance=False, expense_by_category=None, group_by_date=False):
    if transactions is None:
        return "Anda belum memiliki transaksi."
    if not transactions:
        return f"Tidak ada transaksi untuk {title.lower()}."

    msg = f"📊 *{title}*\n\n"
    if group_by_date:
        transactions_by_date = defaultdict(lambda: {TransactionType.INCOME: [], TransactionType.EXPENSE: []})
        for tx in transactions:
            transactions_by_date[tx.date][tx.type].append(tx)

        for transaction_date, daily_transactions in transactions_by_date.items():
            msg += f"*{transaction_date.strftime('%d %b')}*\n"
            for transaction_type, label in (
                (TransactionType.INCOME, "Pemasukan"),
                (TransactionType.EXPENSE, "Pengeluaran"),
            ):
                type_transactions = daily_transactions[transaction_type]
                if not type_transactions:
                    continue
                msg += f"  - *{label}*\n"
                for tx in type_transactions:
                    description = f" - {tx.description}" if tx.description else ""
                    transaction_time = tx.local_created_at.strftime('%H:%M')
                    msg += f"    - `{transaction_time}` Rp{tx.amount:,.0f}{description}\n"
    else:
        for tx in transactions:
            icon = "📈" if tx.type == TransactionType.INCOME else "📉"
            date_str = f"`{tx.date.strftime('%d %b')}` | " if include_date else ""
            transaction_time = tx.local_created_at.strftime('%H:%M')
            msg += f"{date_str}`{transaction_time}` | {icon} Rp{tx.amount:,.0f} - {tx.description}\n"
    
    msg += f"\n📈 Total Pemasukan: Rp{total_income:,.0f}"
    msg += f"\n📉 Total Pengeluaran: Rp{total_expense:,.0f}"
    if expense_by_category:
        msg += "\n\n📂 *Pengeluaran per Kategori:*"
        for category, total in expense_by_category.items():
            msg += f"\n• {category}: Rp{total:,.0f}"
    if include_balance:
        msg += f"\n💡 *Saldo:* Rp{(total_income - total_expense):,.0f}"

    return msg

async def ringkasan_hari_ini(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"User {update.effective_user.id} meminta ringkasan hari ini")
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("⏳ Sedang menyusun laporan hari ini...", parse_mode="Markdown")
        reply_func = update.callback_query.edit_message_text
        overflow_func = update.callback_query.message.reply_text
        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kembali", callback_data="menu_laporan")]])
    else:
        status_msg = await update.message.reply_text("⏳ Sedang menyusun laporan hari ini...", parse_mode="Markdown")
        reply_func = status_msg.edit_text
        overflow_func = update.message.reply_text
        reply_markup = None
        
    try:
        transactions, inc, exp, expense_by_category = await get_daily_summary(
            update.effective_user.id,
            await get_user_local_date(update.effective_user.id),
        )
        msg = _format_transactions(
            transactions,
            inc,
            exp,
            "Ringkasan Hari Ini",
            include_date=True,
            include_balance=True,
            expense_by_category=expense_by_category,
            group_by_date=True,
        )
        await _send_report(reply_func, msg, reply_markup, overflow_func)
    except Exception as e:
        logger.error(f"Error ringkasan_hari_ini: {str(e)}", exc_info=True)
        await reply_func(f"⚠️ Terjadi error: {str(e)}")

async def ringkasan_minggu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"User {update.effective_user.id} meminta ringkasan minggu")
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("⏳ Sedang merangkum transaksi mingguan...", parse_mode="Markdown")
        reply_func = update.callback_query.edit_message_text
        overflow_func = update.callback_query.message.reply_text
        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kembali", callback_data="menu_laporan")]])
    else:
        status_msg = await update.message.reply_text("⏳ Sedang merangkum transaksi mingguan...", parse_mode="Markdown")
        reply_func = status_msg.edit_text
        overflow_func = update.message.reply_text
        reply_markup = None
        
    try:
        transactions, inc, exp, expense_by_category = await get_weekly_summary(
            update.effective_user.id,
            await get_user_local_date(update.effective_user.id),
        )
        msg = _format_transactions(
            transactions,
            inc,
            exp,
            "Ringkasan 7 Hari Terakhir",
            include_date=True,
            include_balance=True,
            expense_by_category=expense_by_category,
            group_by_date=True,
        )
        await _send_report(reply_func, msg, reply_markup, overflow_func)
    except Exception as e:
        logger.error(f"Error ringkasan_minggu: {str(e)}", exc_info=True)
        await reply_func(f"⚠️ Terjadi error: {str(e)}")

async def ringkasan_bulan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = await get_user_local_date(update.effective_user.id)
    target_month = today.month
    target_year = today.year

    if context.args:
        try:
            target_month = int(context.args[0])
            if len(context.args) > 1:
                target_year = int(context.args[1])
            if target_month < 1 or target_month > 12:
                raise ValueError()
        except ValueError:
            await update.message.reply_text("⚠️ Format bulan/tahun salah!\nContoh: `/bulan 11 2024`", parse_mode="Markdown")
            return

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("⏳ Sedang memuat laporan bulanan...", parse_mode="Markdown")
        reply_func = update.callback_query.edit_message_text
        overflow_func = update.callback_query.message.reply_text
        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kembali", callback_data="menu_laporan")]])
    else:
        status_msg = await update.message.reply_text("⏳ Sedang memuat laporan bulanan...", parse_mode="Markdown")
        reply_func = status_msg.edit_text
        overflow_func = update.message.reply_text
        reply_markup = None

    try:
        logger.info(f"User {update.effective_user.id} meminta ringkasan bulan {target_month}/{target_year}")
        transactions, inc, exp, expense_by_category = await get_monthly_summary(update.effective_user.id, target_year, target_month)
        msg = _format_transactions(
            transactions,
            inc,
            exp,
            f"Ringkasan Bulan {target_month}/{target_year}",
            include_date=True,
            include_balance=True,
            expense_by_category=expense_by_category,
            group_by_date=True,
        )
        await _send_report(reply_func, msg, reply_markup, overflow_func)
    except Exception as e:
        logger.error(f"Error ringkasan_bulan: {str(e)}", exc_info=True)
        await reply_func(f"⚠️ Terjadi error: {str(e)}")


def _is_auto_report_due(user) -> bool:
    """True bila user belum menerima laporan hari ini dan waktu lokalnya sudah lewat jam kirim."""
    if not user.daily_report_enabled:
        return False
    now_local = local_now(user.timezone)
    today = now_local.date()
    if user.last_daily_report_at is not None and user.last_daily_report_at >= today:
        return False
    return now_local.hour >= AUTO_REPORT_HOUR_LOCAL


async def kirim_laporan_harian_otomatis(bot) -> dict:
    """Kirim laporan hari ini ke semua user yang waktunya tiba. Mengembalikan rekap hasil.

    Aman dipanggil berulang (cron tiap 15 menit / job polling): user yang sudah
    menerima laporan hari ini dilewati lewat `last_daily_report_at`.
    """
    hasil = {"terkirim": 0, "dilewati": 0, "gagal": 0}
    async with AsyncSessionLocal() as session:
        users = (
            await session.execute(
                select(User).where(User.daily_report_enabled == True)  # noqa: E712
            )
        ).scalars().all()
        for user in users:
            if not _is_auto_report_due(user):
                hasil["dilewati"] += 1
                continue
            try:
                today = local_now(user.timezone).date()
                transactions, inc, exp, expense_by_category = await get_daily_summary(
                    user.telegram_id, today
                )
                if not transactions:
                    logger.info(f"Laporan otomatis dilewati (tanpa transaksi): {user.telegram_id}")
                    user.last_daily_report_at = today
                    await session.commit()
                    hasil["dilewati"] += 1
                    continue
                msg = (
                    "🌙 *Laporan Pengeluaran Hari Ini (Otomatis)*\n\n"
                    + _format_transactions(
                        transactions,
                        inc,
                        exp,
                        "Ringkasan Hari Ini",
                        include_date=True,
                        include_balance=True,
                        expense_by_category=expense_by_category,
                        group_by_date=True,
                    )
                )
                await _send_report(partial(bot.send_message, user.telegram_id), msg)
                user.last_daily_report_at = today
                await session.commit()
                hasil["terkirim"] += 1
                logger.info(f"Laporan otomatis terkirim ke {user.telegram_id}")
            except Exception as e:
                await session.rollback()
                hasil["gagal"] += 1
                logger.error(f"Gagal mengirim laporan otomatis ke {user.telegram_id}: {e}", exc_info=True)
    return hasil


async def laporan_harian_job(context: ContextTypes.DEFAULT_TYPE):
    """Wrapper JobQueue (mode polling) untuk pengiriman laporan otomatis."""
    hasil = await kirim_laporan_harian_otomatis(context.bot)
    logger.info(f"Job laporan harian selesai: {hasil}")


async def atur_laporan_harian(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command /laporan_harian: lihat status atau aktif/nonaktifkan notifikasi jam 8 malam.

    - /laporan_harian → tampilkan status
    - /laporan_harian on → aktifkan
    - /laporan_harian off → matikan
    """
    args = [a.lower() for a in (context.args or [])]
    async with AsyncSessionLocal() as session:
        user = (
            await session.execute(
                select(User).where(User.telegram_id == update.effective_user.id)
            )
        ).scalar_one_or_none()
        if not user:
            await update.message.reply_text(
                "⚠️ Akun belum terdaftar. Kirim /start terlebih dahulu."
            )
            return
        if not args:
            status = "aktif ✅" if user.daily_report_enabled else "nonaktif ❌"
            await update.message.reply_text(
                "🌙 *Laporan Harian Otomatis*\n\n"
                f"Status: {status}\n"
                f"Dikirim setiap jam 8 malam waktu lokal ({user.timezone}).\n\n"
                "Ketik `/laporan_harian on` untuk mengaktifkan atau "
                "`/laporan_harian off` untuk mematikan.",
                parse_mode="Markdown",
            )
            return
        if args[0] in ("on", "aktif", "ya", "1"):
            user.daily_report_enabled = True
            await session.commit()
            await update.message.reply_text(
                "✅ Laporan harian otomatis *diaktifkan*. "
                "Bot akan mengirim ringkasan setiap jam 8 malam.",
                parse_mode="Markdown",
            )
        elif args[0] in ("off", "mati", "nonaktif", "tidak", "0"):
            user.daily_report_enabled = False
            await session.commit()
            await update.message.reply_text(
                "❌ Laporan harian otomatis *dimatikan*.",
                parse_mode="Markdown",
            )
        else:
            await update.message.reply_text(
                "⚠️ Format salah! Gunakan `/laporan_harian on` atau `/laporan_harian off`.",
                parse_mode="Markdown",
            )
