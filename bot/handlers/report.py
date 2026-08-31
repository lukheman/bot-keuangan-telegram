from collections import defaultdict
from datetime import date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from app.services.report_service import get_daily_summary, get_weekly_summary, get_monthly_summary
from app.models import TransactionType
import logging

logger = logging.getLogger(__name__)

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
                    transaction_time = tx.created_at.strftime('%H:%M')
                    msg += f"    - `{transaction_time}` Rp{tx.amount:,.0f}{description}\n"
    else:
        for tx in transactions:
            icon = "📈" if tx.type == TransactionType.INCOME else "📉"
            date_str = f"`{tx.date.strftime('%d %b')}` | " if include_date else ""
            transaction_time = tx.created_at.strftime('%H:%M')
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
        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kembali", callback_data="menu_laporan")]])
    else:
        status_msg = await update.message.reply_text("⏳ Sedang menyusun laporan hari ini...", parse_mode="Markdown")
        reply_func = status_msg.edit_text
        reply_markup = None
        
    try:
        transactions, inc, exp = await get_daily_summary(update.effective_user.id, date.today())
        msg = _format_transactions(transactions, inc, exp, "Ringkasan Hari Ini")
        await reply_func(msg, parse_mode="Markdown", reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Error ringkasan_hari_ini: {str(e)}", exc_info=True)
        await reply_func(f"⚠️ Terjadi error: {str(e)}")

async def ringkasan_minggu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"User {update.effective_user.id} meminta ringkasan minggu")
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("⏳ Sedang merangkum transaksi mingguan...", parse_mode="Markdown")
        reply_func = update.callback_query.edit_message_text
        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kembali", callback_data="menu_laporan")]])
    else:
        status_msg = await update.message.reply_text("⏳ Sedang merangkum transaksi mingguan...", parse_mode="Markdown")
        reply_func = status_msg.edit_text
        reply_markup = None
        
    try:
        transactions, inc, exp = await get_weekly_summary(update.effective_user.id, date.today())
        msg = _format_transactions(transactions, inc, exp, "Ringkasan 7 Hari Terakhir", include_date=True)
        await reply_func(msg, parse_mode="Markdown", reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Error ringkasan_minggu: {str(e)}", exc_info=True)
        await reply_func(f"⚠️ Terjadi error: {str(e)}")

async def ringkasan_bulan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = date.today()
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
        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kembali", callback_data="menu_laporan")]])
    else:
        status_msg = await update.message.reply_text("⏳ Sedang memuat laporan bulanan...", parse_mode="Markdown")
        reply_func = status_msg.edit_text
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
        await reply_func(msg, parse_mode="Markdown", reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Error ringkasan_bulan: {str(e)}", exc_info=True)
        await reply_func(f"⚠️ Terjadi error: {str(e)}")
