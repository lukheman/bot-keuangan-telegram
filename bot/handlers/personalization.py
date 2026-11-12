"""Handler personalisasi: sapaan dan target tabungan (UX-053)."""

from __future__ import annotations

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

from app.services.personalization_service import (
    MAX_NICKNAME_LENGTH,
    PersonalizationError,
    clear_savings_target,
    get_personalization,
    savings_progress,
    set_nickname,
    set_savings_target,
)
from bot.utils.messages import md, rupiah
from bot.utils.parsing import parse_rupiah

logger = logging.getLogger(__name__)

NICKNAME, TARGET = range(2)

ACCOUNT_MENU_TEXT = "👤 *Pengaturan Akun*\n\nPilih aksi yang ingin dilakukan: 👇"


def account_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("ℹ️ Info akun", callback_data="akun_info")],
            [InlineKeyboardButton("✏️ Atur sapaan", callback_data="akun_nickname")],
            [InlineKeyboardButton("🎯 Target tabungan", callback_data="akun_target")],
            [InlineKeyboardButton("🌐 Buka dashboard", callback_data="akun_web")],
            [InlineKeyboardButton("🗑️ Hapus akun", callback_data="akun_hapus")],
            [InlineKeyboardButton("🔙 Kembali", callback_data="menu_utama")],
        ]
    )


def _cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("❌ Batal", callback_data="akun_batal")]]
    )


def _target_quick_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Rp1 juta", callback_data="akun_target_quick_1000000"),
                InlineKeyboardButton("Rp5 juta", callback_data="akun_target_quick_5000000"),
            ],
            [
                InlineKeyboardButton("Rp10 juta", callback_data="akun_target_quick_10000000"),
                InlineKeyboardButton("❌ Batal", callback_data="akun_batal"),
            ],
        ]
    )


def _done_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("ℹ️ Info akun", callback_data="akun_info")],
            [InlineKeyboardButton("🎯 Target tabungan", callback_data="akun_target")],
            [InlineKeyboardButton("🏠 Menu", callback_data="menu_utama")],
        ]
    )


def _progress_text(nickname: str, target, total) -> str:
    progress = savings_progress(target, total)
    pct = max(0.0, progress["pct"])
    bar_width = 10
    filled = min(bar_width, int(progress["pct"] / 100 * bar_width))
    bar = "▓" * filled + "░" * (bar_width - filled)
    status = "🎉 Target tercapai!" if progress["achieved"] else (
        f"Sisa {rupiah(progress['remaining'])} lagi."
    )
    sapaan = f"Halo *{md(nickname)}*! 👋\n\n" if nickname else ""
    return (
        f"{sapaan}"
        "🎯 *Target Tabungan*\n\n"
        f"Terkumpul: *{rupiah(progress['total'])}* dari *{rupiah(progress['target'])}*\n"
        f"`{bar}` {pct:.0f}%\n"
        f"{status}"
    )


async def _back_to_account(query) -> None:
    await query.edit_message_text(
        ACCOUNT_MENU_TEXT,
        parse_mode="Markdown",
        reply_markup=account_keyboard(),
    )


async def start_nickname(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = await get_personalization(update.effective_user.id)
    current = data.get("nickname")
    hint = f"Saat ini: *{md(current)}*.\n\n" if current else ""
    await query.edit_message_text(
        "✏️ *Atur Sapaan*\n\n"
        f"{hint}"
        "Ketik nama yang ingin kupakai untuk menyapamu "
        f"(maksimal {MAX_NICKNAME_LENGTH} karakter).\n\n"
        "Ketik /batal untuk membatalkan.",
        parse_mode="Markdown",
        reply_markup=_cancel_keyboard(),
    )
    return NICKNAME


async def save_nickname(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    raw = (update.effective_message.text or "").strip()
    try:
        nickname = await set_nickname(update.effective_user.id, raw)
    except PersonalizationError as exc:
        await update.effective_message.reply_text(
            f"⚠️ {md(str(exc))}\n\nCoba ketik sapaan lain:",
            parse_mode="Markdown",
            reply_markup=_cancel_keyboard(),
        )
        return NICKNAME

    sapaan = f"*{md(nickname)}*" if nickname else "nama Telegram-mu"
    await update.effective_message.reply_text(
        f"✅ Sapaan disimpan. Aku akan memanggilmu {sapaan}.",
        parse_mode="Markdown",
        reply_markup=_done_keyboard(),
    )
    return ConversationHandler.END


async def start_target(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = await get_personalization(update.effective_user.id)
    target = data.get("savings_target")
    total = data.get("total_balance")

    if target:
        text = _progress_text(data.get("nickname") or "", target, total)
        text += (
            "\n\nMau ubah targetnya? Ketik nominal baru, atau pilih nominal "
            "cepat di bawah."
        )
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "Rp1 juta", callback_data="akun_target_quick_1000000"
                    ),
                    InlineKeyboardButton(
                        "Rp5 juta", callback_data="akun_target_quick_5000000"
                    ),
                ],
                [
                    InlineKeyboardButton(
                        "Rp10 juta", callback_data="akun_target_quick_10000000"
                    ),
                    InlineKeyboardButton("❌ Batal", callback_data="akun_batal"),
                ],
                [
                    InlineKeyboardButton(
                        "🗑️ Hapus target", callback_data="akun_target_hapus_ask"
                    )
                ],
            ]
        )
    else:
        text = (
            "🎯 *Target Tabungan*\n\n"
            "Target ini dihitung dari total saldo semua dompetmu.\n\n"
            "Ketik nominal target (contoh: `10jt`, `5.000.000`, atau `500rb`) "
            "atau pilih nominal cepat di bawah.\n\n"
            "Ketik /batal untuk membatalkan."
        )
        keyboard = _target_quick_keyboard()

    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)
    return TARGET


async def save_target(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    raw = (update.effective_message.text or "").strip()
    try:
        amount = parse_rupiah(raw)
        target = await set_savings_target(update.effective_user.id, amount)
    except (PersonalizationError, ValueError) as exc:
        await update.effective_message.reply_text(
            f"⚠️ {md(str(exc))}\n\nCoba ketik nominal lain, contoh: `10jt`.",
            parse_mode="Markdown",
            reply_markup=_cancel_keyboard(),
        )
        return TARGET

    data = await get_personalization(update.effective_user.id)
    await update.effective_message.reply_text(
        _progress_text(data.get("nickname") or "", target, data["total_balance"]),
        parse_mode="Markdown",
        reply_markup=_done_keyboard(),
    )
    return ConversationHandler.END


async def quick_target(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    amount = int(query.data.rsplit("_", 1)[1])
    try:
        await set_savings_target(update.effective_user.id, amount)
    except PersonalizationError as exc:
        await query.edit_message_text(
            f"⚠️ {md(str(exc))}",
            parse_mode="Markdown",
            reply_markup=_done_keyboard(),
        )
        return ConversationHandler.END
    data = await get_personalization(update.effective_user.id)
    await query.edit_message_text(
        _progress_text(data.get("nickname") or "", amount, data["total_balance"]),
        parse_mode="Markdown",
        reply_markup=_done_keyboard(),
    )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query:
        await update.callback_query.answer()
        await _back_to_account(update.callback_query)
    elif update.effective_message:
        await update.effective_message.reply_text(
            "Oke, pengaturan dibatalkan.",
            reply_markup=_done_keyboard(),
        )
    return ConversationHandler.END


async def target_delete_ask(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "⚠️ *Hapus target tabungan?*\n\n"
        "Progres target akan dihapus. Saldo dompetmu tidak berubah.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "Ya, hapus target", callback_data="akun_target_hapus_confirm"
                    )
                ],
                [InlineKeyboardButton("Batal", callback_data="menu_akun")],
            ]
        ),
    )


async def target_delete_confirm(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query = update.callback_query
    await query.answer()
    await clear_savings_target(update.effective_user.id)
    await query.edit_message_text(
        "🗑️ Target tabungan dihapus. Saldo dompetmu tetap aman.\n\n"
        "Kamu bisa membuat target baru kapan saja.",
        reply_markup=InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("🎯 Atur target", callback_data="akun_target")],
                [InlineKeyboardButton("🏠 Menu", callback_data="menu_utama")],
            ]
        ),
    )
    return ConversationHandler.END


personalization_conv = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(start_nickname, pattern="^akun_nickname$"),
        CallbackQueryHandler(start_target, pattern="^akun_target$"),
    ],
    states={
        NICKNAME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, save_nickname),
            CallbackQueryHandler(cancel, pattern="^(akun_batal|menu_akun)$"),
        ],
        TARGET: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, save_target),
            CallbackQueryHandler(
                quick_target, pattern="^akun_target_quick_"
            ),
            CallbackQueryHandler(cancel, pattern="^(akun_batal|menu_akun)$"),
            CallbackQueryHandler(
                target_delete_ask, pattern="^akun_target_hapus_ask$"
            ),
            CallbackQueryHandler(
                target_delete_confirm, pattern="^akun_target_hapus_confirm$"
            ),
        ],
    },
    fallbacks=[CommandHandler("batal", cancel)],
    conversation_timeout=300,
    per_message=False,
)
