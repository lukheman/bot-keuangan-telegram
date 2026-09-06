import logging

from telegram import Update
from telegram.ext import ContextTypes

from app.services.budget_service import (
    delete_budget,
    list_budgets_with_usage,
    parse_budget_nominal,
    set_budget,
)

logger = logging.getLogger(__name__)


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
    args = context.args or []

    if not args:
        try:
            budgets, period = await list_budgets_with_usage(update.effective_user.id)
        except Exception as e:
            logger.error(f"Gagal memuat budget: {e}", exc_info=True)
            await update.message.reply_text("⚠️ Terjadi error saat memuat budget.")
            return
        if not budgets:
            await update.message.reply_text(
                "🎯 *Budget Bulanan*\n\n"
                "Belum ada budget. Atur dengan:\n"
                "`/budget makanan 1jt`",
                parse_mode="Markdown",
            )
            return
        lines = [f"🎯 *Budget Bulan Ini ({period})*\n"]
        for item in budgets:
            lines.append(
                f"{_status_icon(item['pct'])} *{item['category_name']}*: "
                f"Rp{item['spent']:,.0f} / Rp{item['limit']:,.0f} "
                f"({item['pct']:.0f}%)"
            )
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        return

    if args[0].lower() == "hapus":
        if len(args) < 2:
            await update.message.reply_text(
                "⚠️ Format salah!\nGunakan: `/budget hapus [kategori]`\n"
                "Contoh: `/budget hapus makanan`",
                parse_mode="Markdown",
            )
            return
        category_name = " ".join(args[1:])
        try:
            resolved = await delete_budget(update.effective_user.id, category_name)
            await update.message.reply_text(
                f"🗑️ Budget *{resolved}* berhasil dihapus.", parse_mode="Markdown"
            )
        except ValueError as ve:
            await update.message.reply_text(f"⚠️ {ve}")
        except Exception as e:
            logger.error(f"Gagal menghapus budget: {e}", exc_info=True)
            await update.message.reply_text("⚠️ Terjadi error saat menghapus budget.")
        return

    if len(args) < 2:
        await update.message.reply_text(
            "⚠️ Format salah!\n\n"
            "Gunakan: `/budget [kategori] [nominal]`\n"
            "Contoh: `/budget makanan 1jt`\n\n"
            "Ketik `/budget` untuk melihat semua budget.",
            parse_mode="Markdown",
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
        await update.message.reply_text(
            "⚠️ Nominal tidak valid. Contoh: `/budget makanan 1jt`",
            parse_mode="Markdown",
        )
        return

    try:
        _, category, is_new = await set_budget(
            update.effective_user.id, category_name, amount
        )
        verb = "diatur" if is_new else "diperbarui"
        await update.message.reply_text(
            f"🎯 Budget *{category.name}* {verb}: Rp{amount:,.0f}/bulan.",
            parse_mode="Markdown",
        )
    except ValueError as ve:
        await update.message.reply_text(f"⚠️ {ve}")
    except Exception as e:
        logger.error(f"Gagal menyimpan budget: {e}", exc_info=True)
        await update.message.reply_text("⚠️ Terjadi error saat menyimpan budget.")
