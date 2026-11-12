import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from app.services.budget_service import (
    EXPENSE_CATEGORIES,
    delete_budget,
    list_budgets_with_usage,
    parse_budget_nominal,
    set_budget,
)
from bot.utils.messages import GENERIC_ERROR, md, menu_keyboard, rupiah
from bot.utils.users import ensure_user

logger = logging.getLogger(__name__)

HELP_EXAMPLE = "`/budget makanan 1jt`"

# State percakapan "Atur budget".
BUDGET_AMOUNT = 1


def _budget_add_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton("➕ Atur budget", callback_data="menu_budget_add")],
        [InlineKeyboardButton("🏠 Menu", callback_data="menu_utama")],
    ]
    return InlineKeyboardMarkup(rows)


def _category_keyboard() -> InlineKeyboardMarkup:
    rows = []
    row = []
    for index, name in enumerate(EXPENSE_CATEGORIES):
        row.append(
            InlineKeyboardButton(name, callback_data=f"budget_cat_{index}")
        )
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("❌ Batal", callback_data="budget_cancel")])
    return InlineKeyboardMarkup(rows)


async def budget_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tampilkan pemilih kategori budget dari menu atau /budget."""
    query = update.callback_query
    await query.answer()
    context.user_data.pop("budget_category", None)
    await query.edit_message_text(
        "🎯 *Atur Budget*\n\n"
        "Pilih kategori dulu, lalu ketik batas budget bulanannya. 👇",
        parse_mode="Markdown",
        reply_markup=_category_keyboard(),
    )
    return BUDGET_AMOUNT


async def budget_category_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "budget_cancel":
        context.user_data.pop("budget_category", None)
        await query.edit_message_text(
            "❌ Pengaturan budget dibatalkan.",
            reply_markup=_budget_add_keyboard(),
        )
        return ConversationHandler.END

    try:
        index = int(query.data.rsplit("_", 1)[1])
        category = EXPENSE_CATEGORIES[index]
    except (ValueError, IndexError):
        await query.edit_message_text(
            "⚠️ Kategori belum dikenali. Buka ulang menu Budget, ya.",
            reply_markup=_budget_add_keyboard(),
        )
        return ConversationHandler.END

    context.user_data["budget_category"] = category
    await query.edit_message_text(
        f"🎯 *Budget {md(category)}*\n\n"
        "Ketik batas budget bulanan. Contoh: `1jt`, `500rb`, atau `500000`.\n\n"
        "Ketik /batal untuk membatalkan.",
        parse_mode="Markdown",
    )
    return BUDGET_AMOUNT


async def budget_amount_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    category = context.user_data.get("budget_category")
    if not category:
        await update.effective_message.reply_text(
            "⚠️ Kategori belum dipilih. Buka menu Budget lalu tekan "
            "`➕ Atur budget`.",
            parse_mode="Markdown",
            reply_markup=_budget_add_keyboard(),
        )
        return ConversationHandler.END

    raw = (update.effective_message.text or "").strip()
    try:
        amount = parse_budget_nominal(raw)
    except ValueError as ve:
        await update.effective_message.reply_text(
            f"⚠️ {md(ve)}\n\nCoba lagi, contoh: `1jt` atau `500rb`.",
            parse_mode="Markdown",
        )
        return BUDGET_AMOUNT

    try:
        _, saved_category, is_new = await set_budget(
            update.effective_user.id, category, amount
        )
    except ValueError as ve:
        await update.effective_message.reply_text(
            f"⚠️ {md(ve)}", parse_mode="Markdown", reply_markup=_budget_add_keyboard()
        )
        context.user_data.pop("budget_category", None)
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Gagal menyimpan budget dari menu: {e}", exc_info=True)
        await update.effective_message.reply_text(
            GENERIC_ERROR, reply_markup=_budget_add_keyboard()
        )
        context.user_data.pop("budget_category", None)
        return ConversationHandler.END

    context.user_data.pop("budget_category", None)
    verb = "diatur" if is_new else "diperbarui"
    await update.effective_message.reply_text(
        f"🎯 Budget *{md(saved_category.name)}* {verb}: "
        f"{rupiah(amount)}/bulan.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🎯 Lihat budget", callback_data="menu_budget"
                    )
                ],
                [InlineKeyboardButton("🏠 Menu", callback_data="menu_utama")],
            ]
        ),
    )
    return ConversationHandler.END


async def budget_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("budget_category", None)
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            "❌ Pengaturan budget dibatalkan.",
            reply_markup=_budget_add_keyboard(),
        )
    else:
        await update.effective_message.reply_text(
            "❌ Pengaturan budget dibatalkan.",
            reply_markup=_budget_add_keyboard(),
        )
    return ConversationHandler.END


budget_conv = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(budget_add_start, pattern="^menu_budget_add$")
    ],
    states={
        BUDGET_AMOUNT: [
            CallbackQueryHandler(
                budget_category_selected, pattern="^(budget_cat_|budget_cancel)"
            ),
            MessageHandler(
                filters.TEXT & ~filters.COMMAND, budget_amount_received
            ),
        ],
    },
    fallbacks=[CommandHandler("batal", budget_cancel)],
    conversation_timeout=300,
    per_message=False,
)


def _status_icon(pct: float) -> str:
    if pct > 100:
        return "🚨"
    if pct >= 100:
        return "⛔"
    if pct >= 80:
        return "⚠️"
    return "✅"


async def kelola_budget(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command /budget: lihat, atur, atau hapus anggaran bulanan per kategori.

    - /budget → daftar budget + pemakaian bulan ini
    - /budget <kategori> <nominal> → atur budget (contoh: /budget makanan 1jt)
    - /budget hapus <kategori> → hapus budget
    """
    if update.effective_user is not None:
        await ensure_user(update.effective_user)

    message = update.effective_message
    if message is None:
        return

    args = context.args or []

    if not args:
        try:
            budgets, period = await list_budgets_with_usage(update.effective_user.id)
        except Exception as e:
            logger.error(f"Gagal memuat budget: {e}", exc_info=True)
            await message.reply_text(GENERIC_ERROR, reply_markup=menu_keyboard())
            return

        if not budgets:
            await message.reply_text(
                "🎯 *Budget Bulanan*\n\n"
                "Belum ada budget. Budget membantumu mengatur batas pengeluaran "
                "per kategori setiap bulan.\n\n"
                "Tekan tombol di bawah untuk memilih kategori tanpa hafal nama.\n\n"
                f"Atau lewat perintah: {HELP_EXAMPLE}",
                parse_mode="Markdown",
                reply_markup=_budget_add_keyboard(),
            )
            return

        lines = [f"🎯 *Budget Bulan Ini ({period})*\n"]
        for item in budgets:
            lines.append(
                f"{_status_icon(item['pct'])} *{md(item['category_name'])}*: "
                f"{rupiah(item['spent'])} / {rupiah(item['limit'])} "
                f"({item['pct']:.0f}%)"
            )
        lines.append("\nUbah budget lewat tombol di bawah atau `/budget makanan 1jt`.")
        await message.reply_text(
            "\n".join(lines),
            parse_mode="Markdown",
            reply_markup=_budget_add_keyboard(),
        )
        return

    if args[0].lower() == "hapus":
        if len(args) < 2:
            await message.reply_text(
                "⚠️ Sebutkan kategori yang ingin dihapus.\n\n"
                "Contoh: `/budget hapus makanan`",
                parse_mode="Markdown",
                reply_markup=menu_keyboard(),
            )
            return
        category_name = " ".join(args[1:])
        try:
            resolved = await delete_budget(update.effective_user.id, category_name)
            await message.reply_text(
                f"🗑️ Budget *{md(resolved)}* berhasil dihapus.",
                parse_mode="Markdown",
                reply_markup=menu_keyboard(),
            )
        except ValueError as ve:
            await message.reply_text(
                f"⚠️ {md(ve)}", parse_mode="Markdown", reply_markup=menu_keyboard()
            )
        except Exception as e:
            logger.error(f"Gagal menghapus budget: {e}", exc_info=True)
            await message.reply_text(GENERIC_ERROR, reply_markup=menu_keyboard())
        return

    if len(args) < 2:
        await message.reply_text(
            "⚠️ Format belum lengkap.\n\n"
            "Gunakan: `/budget [kategori] [nominal]`\n"
            f"Contoh: {HELP_EXAMPLE}\n\n"
            "Ketik `/budget` untuk melihat semua budget.",
            parse_mode="Markdown",
            reply_markup=menu_keyboard(),
        )
        return

    # Dukung kategori multi-kata ("biaya admin") dan nominal terpisah ("1 jt"):
    # coba kategori terpanjang dulu, pakai yang nominalnya valid.
    category_name, amount = None, None
    for i in range(len(args) - 1, 0, -1):
        try:
            amount = parse_budget_nominal(" ".join(args[i:]))
            category_name = " ".join(args[:i])
            break
        except ValueError:
            continue
    if category_name is None:
        await message.reply_text(
            "⚠️ Nominal belum terbaca.\n\n"
            "Tulis angka setelah kategori. Contoh: `/budget makanan 1jt`",
            parse_mode="Markdown",
            reply_markup=menu_keyboard(),
        )
        return

    try:
        _, category, is_new = await set_budget(
            update.effective_user.id, category_name, amount
        )
        verb = "diatur" if is_new else "diperbarui"
        await message.reply_text(
            f"🎯 Budget *{md(category.name)}* {verb}: {rupiah(amount)}/bulan.",
            parse_mode="Markdown",
            reply_markup=menu_keyboard(),
        )
    except ValueError as ve:
        await message.reply_text(
            f"⚠️ {md(ve)}", parse_mode="Markdown", reply_markup=menu_keyboard()
        )
    except Exception as e:
        logger.error(f"Gagal menyimpan budget: {e}", exc_info=True)
        await message.reply_text(GENERIC_ERROR, reply_markup=menu_keyboard())
