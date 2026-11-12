"""Riwayat transaksi: lihat, edit, dan hapus dari bot (UX-056)."""

from __future__ import annotations

import logging
from types import SimpleNamespace

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from app.services.sheets_service import append_to_sheet, delete_from_sheet
from app.services.telemetry_service import (
    EVENT_TRANSACTION_DELETED,
    EVENT_TRANSACTION_EDITED,
    track,
)
from app.services.transaction_edit_service import (
    delete_transaction,
    get_transaction,
    list_edit_categories,
    list_transaction_page,
    update_transaction,
)
from bot.utils.messages import md, rupiah
from bot.utils.parsing import parse_rupiah
from bot.utils.users import ensure_user

logger = logging.getLogger(__name__)

EDIT_CHOICE, EDIT_AMOUNT, EDIT_DESC, EDIT_CATEGORY = range(4)

LIST_TEXT = (
    "🧾 *Riwayat Transaksi*\n\n"
    "Ketuk salah satu transaksi untuk melihat detail, lalu edit atau hapus."
)
EMPTY_TEXT = (
    "🧾 *Riwayat Transaksi*\n\n"
    "Belum ada transaksi. Catat yang pertama dengan `kopi 20rb` "
    "atau kirim 📸 foto struk."
)
TRANSFER_NOTE = (
    "\n\nℹ️ Transfer dan biaya admin tidak bisa diubah dari sini karena "
    "terdiri dari beberapa catatan sekaligus."
)

_field = "edit_tx"
_categories = "edit_categories"
_page_key = "riwayat_page"


def _icon(tx: dict) -> str:
    return "📈" if tx["type_label"] == "Pemasukan" else "📉"


def _short(text: str, limit: int = 28) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _riwayat_keyboard(
    items: list[dict],
    page: int = 0,
    has_prev: bool = False,
    has_next: bool = False,
) -> InlineKeyboardMarkup:
    rows = []
    for item in items:
        label = (
            f"{_icon(item)} {item['date'].strftime('%d/%m')} · "
            f"{_short(item['category'], 18)} · {rupiah(item['amount'])}"
        )
        rows.append(
            [InlineKeyboardButton(label, callback_data=f"trx_view_{item['id']}")]
        )
    navigation = []
    if has_prev:
        navigation.append(
            InlineKeyboardButton(
                "⬅️ Sebelumnya", callback_data=f"trx_page_{page - 1}"
            )
        )
    if has_next:
        navigation.append(
            InlineKeyboardButton(
                "Berikutnya ➡️", callback_data=f"trx_page_{page + 1}"
            )
        )
    if navigation:
        rows.append(navigation)
    rows.append([InlineKeyboardButton("🏠 Menu", callback_data="menu_utama")])
    return InlineKeyboardMarkup(rows)


def _detail_text(item: dict) -> str:
    description = md(item["description"]) or "—"
    text = (
        f"{_icon(item)} *Detail Transaksi*\n\n"
        f"📝 *Keterangan:* {description}\n"
        f"💵 *Jumlah:* {rupiah(item['amount'])}\n"
        f"🏷️ *Kategori:* {md(item['category'])}\n"
        f"💼 *Dompet:* {md(item['wallet'])}\n"
        f"📅 *Tanggal:* {item['date'].strftime('%d %b %Y')}\n"
        f"🔁 *Jenis:* {item['type_label']}"
    )
    if not item["editable"]:
        text += TRANSFER_NOTE
    return text


def _detail_keyboard(item: dict) -> InlineKeyboardMarkup:
    rows = []
    if item["editable"]:
        rows.append(
            [
                InlineKeyboardButton("✏️ Edit", callback_data=f"trx_edit_{item['id']}"),
                InlineKeyboardButton("🗑️ Hapus", callback_data=f"trx_del_ask_{item['id']}"),
            ]
        )
    rows.append(
        [
            InlineKeyboardButton("🔙 Riwayat", callback_data="trx_list"),
            InlineKeyboardButton("🏠 Menu", callback_data="menu_utama"),
        ]
    )
    return InlineKeyboardMarkup(rows)


def _done_keyboard(item: dict | None = None) -> InlineKeyboardMarkup:
    rows = []
    if item is not None:
        rows.append(
            [InlineKeyboardButton("🔎 Lihat transaksi", callback_data=f"trx_view_{item['id']}")]
        )
    rows.append(
        [
            InlineKeyboardButton("🧾 Riwayat", callback_data="trx_list"),
            InlineKeyboardButton("🏠 Menu", callback_data="menu_utama"),
        ]
    )
    return InlineKeyboardMarkup(rows)


async def _send_riwayat(
    target, telegram_id: int, edit: bool = False, page: int = 0
) -> None:
    result = await list_transaction_page(telegram_id, page=page)
    items = result["items"]
    if items:
        text = LIST_TEXT
    elif result["page"] > 0:
        text = "🧾 *Riwayat Transaksi*\n\nTidak ada transaksi di halaman ini."
    else:
        text = EMPTY_TEXT
    if items and (result["has_prev"] or result["has_next"]):
        text += f"\n\nHalaman {result['page'] + 1}."
    keyboard = _riwayat_keyboard(
        items,
        page=result["page"],
        has_prev=result["has_prev"],
        has_next=result["has_next"],
    )
    if edit:
        await target.edit_message_text(
            text, parse_mode="Markdown", reply_markup=keyboard
        )
    else:
        await target.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)


async def riwayat_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user is not None:
        await ensure_user(update.effective_user)
    await _send_riwayat(update.effective_message, update.effective_user.id)


async def riwayat_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if query.data.startswith("trx_page_"):
        page = int(query.data.removeprefix("trx_page_"))
    elif query.data == "trx_list":
        page = context.user_data.get(_page_key, 0)
    else:
        page = 0

    context.user_data[_page_key] = page
    await _send_riwayat(query, update.effective_user.id, edit=True, page=page)


async def show_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    tx_hex = query.data.removeprefix("trx_view_")

    try:
        item = await get_transaction(update.effective_user.id, tx_hex)
    except ValueError as exc:
        await query.edit_message_text(
            f"⚠️ {md(str(exc))}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 Riwayat", callback_data="trx_list")]]
            ),
        )
        return

    if item is None:
        await query.edit_message_text(
            "⚠️ Transaksi tidak ditemukan. Buka ulang daftar riwayat, ya.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 Riwayat", callback_data="trx_list")]]
            ),
        )
        return

    await query.edit_message_text(
        _detail_text(item),
        parse_mode="Markdown",
        reply_markup=_detail_keyboard(item),
    )


async def delete_ask(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    tx_hex = query.data.removeprefix("trx_del_ask_")

    try:
        item = await get_transaction(update.effective_user.id, tx_hex)
    except ValueError as exc:
        await query.edit_message_text(f"⚠️ {md(str(exc))}", parse_mode="Markdown")
        return

    if item is None:
        await query.edit_message_text(
            "⚠️ Transaksi sudah tidak ada.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 Riwayat", callback_data="trx_list")]]
            ),
        )
        return

    if not item["editable"]:
        await query.edit_message_text(
            f"⚠️ {md('Transfer dan biaya admin tidak bisa dihapus dari sini.')}"
            f"{TRANSFER_NOTE}",
            parse_mode="Markdown",
            reply_markup=_detail_keyboard(item),
        )
        return

    await query.edit_message_text(
        "⚠️ *Hapus transaksi ini?*\n\n"
        f"📝 {md(item['description']) or '—'}\n"
        f"💵 {rupiah(item['amount'])} · {md(item['category'])}\n"
        f"💼 {md(item['wallet'])}\n\n"
        "Saldo dompet akan dikembalikan seperti sebelum transaksi ini.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "Ya, hapus", callback_data=f"trx_del_ok_{item['id']}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "Batal", callback_data=f"trx_view_{item['id']}"
                    )
                ],
            ]
        ),
    )


async def delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    tx_hex = query.data.removeprefix("trx_del_ok_")

    try:
        info = await delete_transaction(update.effective_user.id, tx_hex)
    except ValueError as exc:
        await query.edit_message_text(
            f"⚠️ {md(str(exc))}",
            parse_mode="Markdown",
            reply_markup=_done_keyboard(),
        )
        return

    try:
        await delete_from_sheet(info["sheet"])
    except Exception as exc:  # pragma: no cover - sinkronisasi eksternal
        logger.warning("Gagal menyinkronkan hapus ke Sheets: %s", exc)

    await track(update.effective_user.id, EVENT_TRANSACTION_DELETED)

    saldo_line = ""
    if info.get("wallet_balance") is not None:
        saldo_line = (
            f"\n💼 *{md(info['wallet'])}* sekarang: "
            f"{rupiah(info['wallet_balance'])}"
        )

    await query.edit_message_text(
        "🗑️ *Transaksi dihapus*\n\n"
        f"📝 {md(info['description']) or '—'}\n"
        f"💵 {rupiah(info['amount'])} · {md(info['category'])}"
        f"{saldo_line}",
        parse_mode="Markdown",
        reply_markup=_done_keyboard(),
    )


async def edit_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    tx_hex = query.data.removeprefix("trx_edit_")

    try:
        item = await get_transaction(update.effective_user.id, tx_hex)
    except ValueError as exc:
        await query.edit_message_text(f"⚠️ {md(str(exc))}", parse_mode="Markdown")
        return ConversationHandler.END

    if item is None:
        await query.edit_message_text(
            "⚠️ Transaksi sudah tidak ada.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 Riwayat", callback_data="trx_list")]]
            ),
        )
        return ConversationHandler.END

    if not item["editable"]:
        await query.edit_message_text(
            f"⚠️ {md('Transfer dan biaya admin tidak bisa diubah dari sini.')}"
            f"{TRANSFER_NOTE}",
            parse_mode="Markdown",
            reply_markup=_detail_keyboard(item),
        )
        return ConversationHandler.END

    context.user_data[_field] = item["id"]
    await query.edit_message_text(
        "✏️ *Edit Transaksi*\n\n"
        f"📝 {md(item['description']) or '—'}\n"
        f"💵 {rupiah(item['amount'])} · {md(item['category'])}\n\n"
        "Mau ubah bagian yang mana?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("💵 Nominal", callback_data="trx_edit_amount"),
                    InlineKeyboardButton("📝 Keterangan", callback_data="trx_edit_desc"),
                ],
                [InlineKeyboardButton("🏷️ Kategori", callback_data="trx_edit_cat")],
                [InlineKeyboardButton("❌ Batal", callback_data="trx_edit_batal")],
            ]
        ),
    )
    return EDIT_CHOICE


async def edit_amount_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "💵 *Ubah Nominal*\n\n"
        "Ketik nominal baru, contoh `25000`, `25rb`, atau `25.000`.\n"
        "Ketik /batal untuk membatalkan.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("❌ Batal", callback_data="trx_edit_batal")]]
        ),
    )
    return EDIT_AMOUNT


async def edit_amount_save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    raw = (update.effective_message.text or "").strip()
    tx_id = context.user_data.get(_field)
    try:
        amount = parse_rupiah(raw)
        result = await update_transaction(
            update.effective_user.id, tx_id, amount=amount
        )
    except ValueError as exc:
        await update.effective_message.reply_text(
            f"⚠️ {md(str(exc))}\n\nCoba ketik nominal lain, contoh `25rb`.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("❌ Batal", callback_data="trx_edit_batal")]]
            ),
        )
        return EDIT_AMOUNT

    await _sync_sheet(result)
    await track(update.effective_user.id, EVENT_TRANSACTION_EDITED, field="amount")
    await update.effective_message.reply_text(
        _updated_text(result),
        parse_mode="Markdown",
        reply_markup=_done_keyboard(result["new"]),
    )
    return ConversationHandler.END


async def edit_desc_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "📝 *Ubah Keterangan*\n\n"
        "Ketik keterangan baru, contoh `kopi susu`.\n"
        "Ketik /batal untuk membatalkan.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("❌ Batal", callback_data="trx_edit_batal")]]
        ),
    )
    return EDIT_DESC


async def edit_desc_save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    raw = (update.effective_message.text or "").strip()
    tx_id = context.user_data.get(_field)
    try:
        result = await update_transaction(
            update.effective_user.id, tx_id, description=raw
        )
    except ValueError as exc:
        await update.effective_message.reply_text(
            f"⚠️ {md(str(exc))}\n\nCoba ketik keterangan lain.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("❌ Batal", callback_data="trx_edit_batal")]]
            ),
        )
        return EDIT_DESC

    await _sync_sheet(result)
    await track(update.effective_user.id, EVENT_TRANSACTION_EDITED, field="description")
    await update.effective_message.reply_text(
        _updated_text(result),
        parse_mode="Markdown",
        reply_markup=_done_keyboard(result["new"]),
    )
    return ConversationHandler.END


async def edit_category_prompt(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query = update.callback_query
    await query.answer()
    tx_id = context.user_data.get(_field)

    try:
        categories = await list_edit_categories(update.effective_user.id, tx_id)
    except ValueError as exc:
        await query.edit_message_text(f"⚠️ {md(str(exc))}", parse_mode="Markdown")
        return ConversationHandler.END

    if not categories:
        await query.edit_message_text(
            "Belum ada kategori lain untuk jenis transaksi ini.",
            reply_markup=_done_keyboard(),
        )
        return ConversationHandler.END

    context.user_data[_categories] = categories
    rows = []
    row = []
    for index, name in enumerate(categories):
        row.append(
            InlineKeyboardButton(name, callback_data=f"trx_cat_{index}")
        )
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("❌ Batal", callback_data="trx_edit_batal")])

    await query.edit_message_text(
        "🏷️ *Ubah Kategori*\n\nPilih kategori baru:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(rows),
    )
    return EDIT_CATEGORY


async def edit_category_save(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query = update.callback_query
    await query.answer()
    index = int(query.data.removeprefix("trx_cat_"))
    categories = context.user_data.get(_categories) or []
    if index < 0 or index >= len(categories):
        await query.edit_message_text(
            "⚠️ Kategori tidak dikenali. Coba lagi dari daftar riwayat.",
            reply_markup=_done_keyboard(),
        )
        return ConversationHandler.END

    tx_id = context.user_data.get(_field)
    try:
        result = await update_transaction(
            update.effective_user.id, tx_id, category_name=categories[index]
        )
    except ValueError as exc:
        await query.edit_message_text(
            f"⚠️ {md(str(exc))}",
            parse_mode="Markdown",
            reply_markup=_done_keyboard(),
        )
        return ConversationHandler.END

    await _sync_sheet(result)
    await track(update.effective_user.id, EVENT_TRANSACTION_EDITED, field="category")
    await query.edit_message_text(
        _updated_text(result),
        parse_mode="Markdown",
        reply_markup=_done_keyboard(result["new"]),
    )
    return ConversationHandler.END


async def edit_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop(_field, None)
    context.user_data.pop(_categories, None)
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            "❌ Edit dibatalkan.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("🧾 Riwayat", callback_data="trx_list"),
                        InlineKeyboardButton("🏠 Menu", callback_data="menu_utama"),
                    ]
                ]
            ),
        )
    elif update.effective_message is not None:
        await update.effective_message.reply_text(
            "❌ Edit dibatalkan.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("🧾 Riwayat", callback_data="trx_list"),
                        InlineKeyboardButton("🏠 Menu", callback_data="menu_utama"),
                    ]
                ]
            ),
        )
    return ConversationHandler.END


def _updated_text(result: dict) -> str:
    old, new = result["old"], result["new"]
    saldo_line = ""
    if old["amount"] != new["amount"]:
        saldo_line = "\n💼 Saldo dompet ikut disesuaikan."
    return (
        "✅ *Transaksi diperbarui*\n\n"
        f"📝 {md(new['description']) or '—'}\n"
        f"💵 {rupiah(new['amount'])} · {md(new['category'])}\n"
        f"💼 {md(new['wallet'])}"
        f"{saldo_line}"
    )


async def _sync_sheet(result: dict) -> None:
    """Sinkronkan perubahan ke Google Sheets, best-effort."""
    try:
        await delete_from_sheet(result["old"]["sheet"])
        new = result["new"]
        proxy = SimpleNamespace(
            id=new["id"],
            date=new["date"],
            type=new["type"],
            amount=new["amount"],
            description=new["description"],
            category_name=new["category"],
            wallet_name=new["wallet"],
        )
        await append_to_sheet(proxy)
    except Exception as exc:  # pragma: no cover - sinkronisasi eksternal
        logger.warning("Gagal menyinkronkan edit ke Sheets: %s", exc)


history_edit_conv = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(edit_entry, pattern=r"^trx_edit_[0-9a-f]{32}$"),
    ],
    states={
        EDIT_CHOICE: [
            CallbackQueryHandler(edit_amount_prompt, pattern="^trx_edit_amount$"),
            CallbackQueryHandler(edit_desc_prompt, pattern="^trx_edit_desc$"),
            CallbackQueryHandler(edit_category_prompt, pattern="^trx_edit_cat$"),
            CallbackQueryHandler(edit_cancel, pattern="^trx_edit_batal$"),
        ],
        EDIT_AMOUNT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, edit_amount_save),
            CallbackQueryHandler(edit_cancel, pattern="^trx_edit_batal$"),
        ],
        EDIT_DESC: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, edit_desc_save),
            CallbackQueryHandler(edit_cancel, pattern="^trx_edit_batal$"),
        ],
        EDIT_CATEGORY: [
            CallbackQueryHandler(edit_category_save, pattern=r"^trx_cat_\d+$"),
            CallbackQueryHandler(edit_cancel, pattern="^trx_edit_batal$"),
        ],
    },
    fallbacks=[CommandHandler("batal", edit_cancel)],
    conversation_timeout=300,
    per_message=False,
)
