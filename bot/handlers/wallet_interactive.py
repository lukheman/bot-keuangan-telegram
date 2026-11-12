import decimal
import logging
import uuid

from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
)
from sqlalchemy import delete, func, select

from app.core.database import AsyncSessionLocal
from app.models import Transaction, User, Wallet
from bot.utils.messages import GENERIC_ERROR, md, rupiah
from bot.utils.parsing import parse_rupiah
from bot.utils.users import ensure_user

logger = logging.getLogger(__name__)

WALLET_NAME, WALLET_BALANCE = range(2)


async def _get_internal_user_id(session, telegram_id):
    stmt = select(User.id).where(User.telegram_id == telegram_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def get_wallet_menu_content(telegram_id):
    async with AsyncSessionLocal() as session:
        user_id = await _get_internal_user_id(session, telegram_id)
        if not user_id:
            text = (
                "💼 *Menu Dompet*\n\n"
                "Kamu belum punya akun. Tekan tombol Daftar di bawah—cukup satu klik."
            )
        else:
            stmt = select(Wallet).where(Wallet.user_id == user_id)
            wallets = (await session.execute(stmt)).scalars().all()

            if not wallets:
                text = (
                    "💼 *Menu Dompet*\n\n"
                    "Kamu belum punya dompet. Dompet membantu memisahkan uang, "
                    "misalnya BCA, Tunai, atau Gopay."
                )
            else:
                text = "💼 *Daftar Dompet Kamu*\n\n"
                total = 0
                for w in wallets:
                    text += f"• *{md(w.name)}*: {rupiah(w.balance)}\n"
                    total += w.balance
                text += f"\n*Total Saldo Dompet:* {rupiah(total)}\n\nApa yang ingin kamu lakukan?"

    if not user_id:
        reply_markup = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("🚀 Daftar", callback_data="start_ulang")],
                [InlineKeyboardButton("🏠 Menu", callback_data="menu_utama")],
            ]
        )
    else:
        reply_markup = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("➕ Tambah dompet", callback_data="wallet_add_interactive")],
                [InlineKeyboardButton("✏️ Ubah nama dompet", callback_data="wallet_rename_menu")],
                [InlineKeyboardButton("🗑️ Hapus dompet", callback_data="wallet_del_menu")],
                [InlineKeyboardButton("🔙 Kembali", callback_data="menu_utama")],
            ]
        )
    return text, reply_markup


async def cek_saldo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user is not None:
        await ensure_user(update.effective_user)
    text, reply_markup = await get_wallet_menu_content(update.effective_user.id)
    await update.effective_message.reply_text(
        text, reply_markup=reply_markup, parse_mode="Markdown"
    )


async def interactive_add_wallet_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if update.effective_user is not None:
        await ensure_user(update.effective_user)

    msg = (
        "💳 *Tambah Dompet Baru*\n\n"
        "Ketik *Nama Dompet* (contoh: BCA, Bank Mandiri, Tunai, Gopay):\n\n"
        "Ketik /batal untuk membatalkan."
    )

    if query:
        await query.answer()
        await query.edit_message_text(msg, parse_mode="Markdown")
    elif update.effective_message is not None:
        await update.effective_message.reply_text(msg, parse_mode="Markdown")
    return WALLET_NAME


async def interactive_add_wallet_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = (update.effective_message.text or "").strip()
    if not name:
        await update.effective_message.reply_text(
            "⚠️ Nama dompet belum diisi. Coba lagi (contoh: BCA):"
        )
        return WALLET_NAME
    if len(name) > 50:
        await update.effective_message.reply_text(
            "⚠️ Nama dompet terlalu panjang (maksimal 50 karakter). Coba nama yang lebih singkat:"
        )
        return WALLET_NAME

    context.user_data["new_wallet_name"] = name
    await update.effective_message.reply_text(
        f"Nama dompet *{md(name)}* dicatat!\n\n"
        "Sekarang ketik *Saldo Awalnya* (contoh: 500000, 500rb, atau Rp500.000). "
        "Ketik 0 jika kosong.\n\n"
        "Ketik /batal untuk membatalkan.",
        parse_mode="Markdown",
    )
    return WALLET_BALANCE


async def interactive_add_wallet_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw = (update.effective_message.text or "").strip()
    try:
        balance = parse_rupiah(raw)
    except ValueError:
        await update.effective_message.reply_text(
            "⚠️ Saldo awal harus berupa angka.\n"
            "Contoh: 500000, 500rb, atau Rp500.000. Silakan ketik ulang:"
        )
        return WALLET_BALANCE

    if balance < 0:
        await update.effective_message.reply_text(
            "⚠️ Saldo tidak boleh negatif. Silakan ketik ulang:"
        )
        return WALLET_BALANCE

    name = context.user_data.get("new_wallet_name")
    if not name:
        await update.effective_message.reply_text(
            "⚠️ Sesi pembuatan dompet sudah berakhir. Silakan mulai lagi dari menu Dompet."
        )
        return ConversationHandler.END

    async with AsyncSessionLocal() as session:
        user_id = await _get_internal_user_id(session, update.effective_user.id)
        if not user_id:
            await ensure_user(update.effective_user)
            user_id = await _get_internal_user_id(session, update.effective_user.id)
        if not user_id:
            await update.effective_message.reply_text(GENERIC_ERROR)
            return ConversationHandler.END

        stmt = select(Wallet).where(
            Wallet.user_id == user_id, func.lower(Wallet.name) == name.lower()
        )
        existing = (await session.execute(stmt)).scalar_one_or_none()
        if existing:
            await update.effective_message.reply_text(
                f"⚠️ Dompet *{md(name)}* sudah ada. Pakai nama lain, ya.",
                parse_mode="Markdown",
            )
            return ConversationHandler.END

        has_wallet = (
            await session.execute(select(Wallet.id).where(Wallet.user_id == user_id))
        ).first()
        wallet = Wallet(
            user_id=user_id,
            name=name,
            balance=balance,
            is_primary=not bool(has_wallet),
        )
        session.add(wallet)
        await session.commit()

    text, reply_markup = await get_wallet_menu_content(update.effective_user.id)
    await update.effective_message.reply_text(
        f"✅ Dompet *{md(name)}* berhasil ditambahkan dengan saldo awal {rupiah(balance)}!\n\n{text}",
        parse_mode="Markdown",
        reply_markup=reply_markup,
    )
    return ConversationHandler.END


async def interactive_add_wallet_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "❌ Penambahan dompet dibatalkan. Ketik /menu untuk kembali."
    )
    return ConversationHandler.END


interactive_wallet_conv = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(interactive_add_wallet_start, pattern="^wallet_add_interactive$")
    ],
    states={
        WALLET_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, interactive_add_wallet_name)],
        WALLET_BALANCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, interactive_add_wallet_balance)],
    },
    fallbacks=[CommandHandler("batal", interactive_add_wallet_cancel)],
    conversation_timeout=300,
    per_message=False,
)


async def interactive_del_wallet_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    async with AsyncSessionLocal() as session:
        user_id = await _get_internal_user_id(session, update.effective_user.id)
        if not user_id:
            await query.edit_message_text(
                "Kamu belum punya akun. Tekan tombol Daftar di bawah.",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("🚀 Daftar", callback_data="start_ulang")]]
                ),
            )
            return

        stmt = select(Wallet).where(Wallet.user_id == user_id)
        wallets = (await session.execute(stmt)).scalars().all()

        if not wallets:
            await query.edit_message_text(
                "Kamu belum punya dompet. Tambahkan dompet dulu, ya.",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "➕ Tambah dompet",
                                callback_data="wallet_add_interactive",
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                "🔙 Kembali", callback_data="menu_dompet"
                            )
                        ],
                    ]
                ),
            )
            return

        keyboard = []
        for w in wallets:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"🗑️ Hapus {w.name}",
                        callback_data=f"wallet_del_ask_{w.id.hex}",
                    )
                ]
            )
        keyboard.append([InlineKeyboardButton("🔙 Kembali", callback_data="menu_dompet")])

        await query.edit_message_text(
            "Pilih dompet yang ingin dihapus:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )


async def interactive_del_wallet_ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    token = query.data.removeprefix("wallet_del_ask_")
    try:
        wallet_id = uuid.UUID(token)
    except ValueError:
        await query.answer("Dompet yang dipilih tidak dikenali.", show_alert=True)
        return

    async with AsyncSessionLocal() as session:
        user_id = await _get_internal_user_id(session, update.effective_user.id)
        wallet = (
            await session.execute(
                select(Wallet).where(Wallet.id == wallet_id, Wallet.user_id == user_id)
            )
        ).scalar_one_or_none()
        if not wallet:
            await query.answer("Dompet tidak ditemukan atau sudah dihapus.", show_alert=True)
            return

        jumlah = (
            await session.execute(
                select(func.count(Transaction.id)).where(Transaction.wallet_id == wallet.id)
            )
        ).scalar_one()
        nama = wallet.name

    keyboard = [
        [InlineKeyboardButton("Ya, hapus", callback_data=f"wallet_del_confirm_{wallet_id.hex}")],
        [InlineKeyboardButton("Batal", callback_data="menu_dompet")],
    ]
    await query.edit_message_text(
        f"⚠️ *Hapus dompet {md(nama)}?*\n\n"
        f"Dompet ini punya {jumlah} transaksi. Semua transaksi tersebut "
        "akan ikut terhapus permanen.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def interactive_del_wallet_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    token = query.data.removeprefix("wallet_del_confirm_")
    try:
        wallet_id = uuid.UUID(token)
    except ValueError:
        await query.answer("Dompet yang dipilih tidak dikenali.", show_alert=True)
        return

    async with AsyncSessionLocal() as session:
        user_id = await _get_internal_user_id(session, update.effective_user.id)
        wallet = (
            await session.execute(
                select(Wallet).where(Wallet.id == wallet_id, Wallet.user_id == user_id)
            )
        ).scalar_one_or_none()
        if not wallet:
            await query.answer("Dompet tidak ditemukan atau sudah dihapus.", show_alert=True)
            return

        nama = wallet.name
        was_primary = wallet.is_primary
        await session.execute(delete(Transaction).where(Transaction.wallet_id == wallet.id))
        await session.delete(wallet)
        await session.flush()

        if was_primary:
            next_wallet = (
                await session.execute(
                    select(Wallet).where(Wallet.user_id == user_id).order_by(Wallet.created_at)
                )
            ).scalars().first()
            if next_wallet:
                next_wallet.is_primary = True

        await session.commit()

    text, reply_markup = await get_wallet_menu_content(update.effective_user.id)
    await query.edit_message_text(
        f"✅ Dompet *{md(nama)}* berhasil dihapus.\n\n{text}",
        parse_mode="Markdown",
        reply_markup=reply_markup,
    )


RENAME_WALLET_NEW_NAME = 10


async def interactive_rename_wallet_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    async with AsyncSessionLocal() as session:
        user_id = await _get_internal_user_id(session, update.effective_user.id)
        if not user_id:
            await query.edit_message_text(
                "Kamu belum punya akun. Tekan tombol Daftar di bawah.",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("🚀 Daftar", callback_data="start_ulang")]]
                ),
            )
            return

        stmt = select(Wallet).where(Wallet.user_id == user_id)
        wallets = (await session.execute(stmt)).scalars().all()

        if not wallets:
            await query.edit_message_text(
                "Kamu belum punya dompet. Tambahkan dompet dulu, ya.",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "➕ Tambah dompet",
                                callback_data="wallet_add_interactive",
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                "🔙 Kembali", callback_data="menu_dompet"
                            )
                        ],
                    ]
                ),
            )
            return

        keyboard = []
        for w in wallets:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"✏️ Ubah nama {w.name}",
                        callback_data=f"wallet_rename_action_{w.id.hex}",
                    )
                ]
            )
        keyboard.append([InlineKeyboardButton("🔙 Kembali", callback_data="menu_dompet")])

        await query.edit_message_text(
            "Pilih dompet yang ingin diubah namanya:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )


async def interactive_rename_wallet_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    wallet_id_hex = query.data.replace("wallet_rename_action_", "")

    context.user_data["rename_wallet_id"] = wallet_id_hex

    msg = (
        "✏️ *Ubah Nama Dompet*\n\n"
        "Ketik *Nama Baru* untuk dompet ini (contoh: Bank Mandiri).\n\n"
        "Ketik /batal untuk membatalkan."
    )
    await query.edit_message_text(msg, parse_mode="Markdown")
    return RENAME_WALLET_NEW_NAME


async def interactive_rename_wallet_new_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_name = (update.effective_message.text or "").strip()
    if not new_name:
        await update.effective_message.reply_text(
            "⚠️ Nama dompet belum diisi. Coba lagi:"
        )
        return RENAME_WALLET_NEW_NAME
    if len(new_name) > 50:
        await update.effective_message.reply_text(
            "⚠️ Nama dompet terlalu panjang (maksimal 50 karakter). Coba lagi:"
        )
        return RENAME_WALLET_NEW_NAME

    wallet_id_hex = context.user_data.get("rename_wallet_id")

    async with AsyncSessionLocal() as session:
        try:
            wallet_id = uuid.UUID(wallet_id_hex)
        except (ValueError, TypeError):
            await update.effective_message.reply_text(
                "⚠️ Sesi ubah nama sudah berakhir. Silakan mulai lagi dari menu Dompet."
            )
            return ConversationHandler.END

        user_id = await _get_internal_user_id(session, update.effective_user.id)
        wallet = (
            await session.execute(
                select(Wallet).where(Wallet.id == wallet_id, Wallet.user_id == user_id)
            )
        ).scalar_one_or_none()

        if not wallet:
            await update.effective_message.reply_text("⚠️ Dompet tidak ditemukan.")
            return ConversationHandler.END

        duplicate = (
            await session.execute(
                select(Wallet).where(
                    Wallet.user_id == user_id,
                    func.lower(Wallet.name) == new_name.lower(),
                    Wallet.id != wallet.id,
                )
            )
        ).scalar_one_or_none()
        if duplicate:
            await update.effective_message.reply_text(
                f"⚠️ Nama *{md(new_name)}* sudah dipakai dompet lain. Coba nama lain:",
                parse_mode="Markdown",
            )
            return RENAME_WALLET_NEW_NAME

        old_name = wallet.name
        wallet.name = new_name
        await session.commit()

    text, reply_markup = await get_wallet_menu_content(update.effective_user.id)
    await update.effective_message.reply_text(
        f"✅ Nama dompet *{md(old_name)}* berhasil diubah menjadi *{md(new_name)}*!\n\n{text}",
        parse_mode="Markdown",
        reply_markup=reply_markup,
    )
    return ConversationHandler.END


async def interactive_rename_wallet_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "❌ Ubah nama dompet dibatalkan. Ketik /menu untuk kembali."
    )
    return ConversationHandler.END


interactive_rename_wallet_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(interactive_rename_wallet_start, pattern="^wallet_rename_action_")],
    states={
        RENAME_WALLET_NEW_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, interactive_rename_wallet_new_name)]
    },
    fallbacks=[CommandHandler("batal", interactive_rename_wallet_cancel)],
    conversation_timeout=300,
    per_message=False,
)
