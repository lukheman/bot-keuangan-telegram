"""Onboarding singkat untuk pengguna baru.

Empat langkah: zona waktu, notifikasi harian, dompet pertama, dan notice
privasi AI. Semua pilihan bisa diubah lagi lewat menu Akun / Notifikasi.
"""

from __future__ import annotations

import logging

from sqlalchemy import func, select
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from app.core.database import AsyncSessionLocal
from app.models import User, Wallet
from app.services.telemetry_service import (
    EVENT_ONBOARDING_COMPLETED,
    EVENT_ONBOARDING_STARTED,
    track,
)
from bot.utils.messages import md, rupiah
from bot.utils.parsing import parse_rupiah
from bot.utils.users import ensure_user

logger = logging.getLogger(__name__)

TIMEZONE, NOTIF, WALLET_NAME, WALLET_BALANCE, PRIVACY = range(5)

TIMEZONE_OPTIONS = {
    "wib": ("WIB", "Asia/Jakarta"),
    "wita": ("WITA", "Asia/Makassar"),
    "wit": ("WIT", "Asia/Jayapura"),
}


async def _load_user(telegram_id: int) -> User | None:
    async with AsyncSessionLocal() as session:
        return (
            await session.execute(select(User).where(User.telegram_id == telegram_id))
        ).scalar_one_or_none()


async def _update_user(telegram_id: int, **fields) -> None:
    async with AsyncSessionLocal() as session:
        user = (
            await session.execute(select(User).where(User.telegram_id == telegram_id))
        ).scalar_one_or_none()
        if user is None:
            return
        for key, value in fields.items():
            setattr(user, key, value)
        await session.commit()


async def _kirim(update: Update, text: str, keyboard: InlineKeyboardMarkup) -> None:
    if update.callback_query is not None:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text, parse_mode="Markdown", reply_markup=keyboard
        )
    elif update.effective_message is not None:
        await update.effective_message.reply_text(
            text, parse_mode="Markdown", reply_markup=keyboard
        )


def _timezone_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("WIB (Jakarta)", callback_data="onb_tz_wib"),
                InlineKeyboardButton("WITA (Makassar)", callback_data="onb_tz_wita"),
            ],
            [InlineKeyboardButton("WIT (Jayapura)", callback_data="onb_tz_wit")],
        ]
    )


def _notif_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🔔 Aktifkan", callback_data="onb_notif_on")],
            [InlineKeyboardButton("🔕 Nanti saja", callback_data="onb_notif_off")],
        ]
    )


def _wallet_name_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("💵 Pakai “Tunai”", callback_data="onb_wallet_tunai")],
            [InlineKeyboardButton("Lewati dulu", callback_data="onb_wallet_skip")],
        ]
    )


def _wallet_balance_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Saldo 0", callback_data="onb_balance_zero")],
            [InlineKeyboardButton("Lewati dulu", callback_data="onb_wallet_skip")],
        ]
    )


def _privacy_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("✅ Saya paham, mulai", callback_data="onb_done")]]
    )


def _finish_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🏠 Buka menu", callback_data="menu_utama")],
            [InlineKeyboardButton("❓ Cara pakai", callback_data="menu_bantuan")],
        ]
    )


async def _show_timezone(update: Update) -> int:
    nama = md(update.effective_user.first_name or "Kawan")
    await _kirim(
        update,
        f"👋 Selamat datang, *{nama}*!\n\n"
        "Aku asisten keuanganmu. Sebelum mulai, ada 4 langkah singkat "
        "(bisa diubah kapan saja).\n\n"
        "1/4 — *Zona waktu kamu di mana?*\n"
        "Ini dipakai agar tanggal transaksi dan laporan harian akurat.",
        _timezone_keyboard(),
    )
    return TIMEZONE


async def _show_notif(update: Update, timezone_label: str) -> int:
    await _kirim(
        update,
        f"✅ Zona waktu: *{timezone_label}*\n\n"
        "2/4 — *Mau ringkasan otomatis tiap tengah malam?*\n"
        "Isinya transaksi hari itu. Bisa dimatikan kapan saja.",
        _notif_keyboard(),
    )
    return NOTIF


async def _show_wallet_name(update: Update, notif_label: str) -> int:
    await _kirim(
        update,
        f"✅ Notifikasi harian: *{notif_label}*\n\n"
        "3/4 — *Dompet pertama kamu*\n"
        "Dompet memisahkan uang, misalnya BCA, Tunai, atau Gopay.\n\n"
        "Ketik nama dompet, atau pilih salah satu tombol di bawah.",
        _wallet_name_keyboard(),
    )
    return WALLET_NAME


async def _show_wallet_balance(update: Update, name: str) -> int:
    await _kirim(
        update,
        f"💼 Dompet *{md(name)}* siap.\n\n"
        "*Berapa saldo awalnya?*\n"
        "Ketik nominalnya (contoh: `500rb`, `Rp500.000`, atau `0`).",
        _wallet_balance_keyboard(),
    )
    return WALLET_BALANCE


async def _show_privacy(update: Update, wallet_note: str) -> int:
    await _kirim(
        update,
        f"{wallet_note}"
        "4/4 — 🔒 *Privasi & pemrosesan AI*\n\n"
        "Teks dan foto transaksi diproses oleh layanan AI (Groq) untuk "
        "membaca nominal dan kategori. Data tidak dipakai untuk iklan.\n\n"
        "Kalau tidak ingin memakai AI, kamu tetap bisa mengatur dompet dan "
        "budget secara manual lewat menu.",
        _privacy_keyboard(),
    )
    return PRIVACY


async def onboarding_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    tg_user = update.effective_user
    if tg_user is None:
        return ConversationHandler.END

    await ensure_user(tg_user)
    user = await _load_user(tg_user.id)

    if user is not None and user.onboarding_completed:
        # User lama: langsung ke menu, tanpa mengulang wizard.
        from bot.handlers.menu import tampilkan_menu

        await tampilkan_menu(update, context)
        return ConversationHandler.END

    context.user_data.pop("onb_wallet_name", None)
    await track(tg_user.id, EVENT_ONBOARDING_STARTED)
    return await _show_timezone(update)


async def pilih_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query is None:
        return TIMEZONE

    key = query.data.removeprefix("onb_tz_")
    label, tz_name = TIMEZONE_OPTIONS.get(key, ("WITA", "Asia/Makassar"))
    await _update_user(update.effective_user.id, timezone=tz_name)
    context.user_data["onb_timezone_label"] = label
    return await _show_notif(update, label)


async def pilih_notif(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query is None:
        return NOTIF

    enabled = query.data == "onb_notif_on"
    await _update_user(update.effective_user.id, daily_report_enabled=enabled)
    label = "Aktif ✅" if enabled else "Nonaktif ❌"
    return await _show_wallet_name(update, label)


async def wallet_nama_tunai(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # query.answer() dilakukan oleh _show_wallet_balance.
    context.user_data["onb_wallet_name"] = "Tunai"
    return await _show_wallet_balance(update, "Tunai")


async def wallet_nama_teks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = (update.effective_message.text or "").strip()
    if not name:
        await update.effective_message.reply_text(
            "⚠️ Nama dompet belum diisi. Ketik nama dompet (contoh: BCA):"
        )
        return WALLET_NAME
    if len(name) > 50:
        await update.effective_message.reply_text(
            "⚠️ Nama dompet maksimal 50 karakter. Coba nama yang lebih singkat:"
        )
        return WALLET_NAME

    context.user_data["onb_wallet_name"] = name
    return await _show_wallet_balance(update, name)


async def wallet_skip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop("onb_wallet_name", None)
    return await _show_privacy(
        update,
        "💼 Dompet bisa ditambahkan nanti lewat menu Dompet.\n\n",
    )


async def _create_wallet(telegram_id: int, name: str, balance) -> None:
    async with AsyncSessionLocal() as session:
        user = (
            await session.execute(select(User).where(User.telegram_id == telegram_id))
        ).scalar_one_or_none()
        if user is None:
            return

        existing = (
            await session.execute(
                select(Wallet.id).where(
                    Wallet.user_id == user.id,
                    func.lower(Wallet.name) == name.lower(),
                )
            )
        ).first()
        if existing:
            return

        has_wallet = (
            await session.execute(select(Wallet.id).where(Wallet.user_id == user.id))
        ).first()
        session.add(
            Wallet(
                user_id=user.id,
                name=name,
                balance=balance,
                is_primary=not bool(has_wallet),
            )
        )
        await session.commit()


async def wallet_saldo_teks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    raw = (update.effective_message.text or "").strip()
    try:
        balance = parse_rupiah(raw)
    except ValueError:
        await update.effective_message.reply_text(
            "⚠️ Nominal belum terbaca.\n"
            "Contoh: `500rb`, `Rp500.000`, atau `0`.",
            parse_mode="Markdown",
        )
        return WALLET_BALANCE

    name = context.user_data.get("onb_wallet_name")
    if not name:
        return WALLET_NAME

    await _create_wallet(update.effective_user.id, name, balance)
    note = (
        f"✅ Dompet *{md(name)}* dibuat dengan saldo awal "
        f"{rupiah(balance)}.\n\n"
    )
    return await _show_privacy(update, note)


async def wallet_saldo_nol(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = context.user_data.get("onb_wallet_name") or "Tunai"
    await _create_wallet(update.effective_user.id, name, 0)
    return await _show_privacy(
        update,
        f"✅ Dompet *{md(name)}* dibuat dengan saldo awal Rp0.\n\n",
    )


async def selesai(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await _update_user(update.effective_user.id, onboarding_completed=True)
    context.user_data.pop("onb_wallet_name", None)
    await track(
        update.effective_user.id,
        EVENT_ONBOARDING_COMPLETED,
        skipped=False,
    )

    await _kirim(
        update,
        "🎉 *Semua siap!*\n\n"
        "Sekarang kamu bisa langsung catat transaksi dengan chat biasa:\n"
        "• `kopi 20rb`\n"
        "• `gaji 5jt`\n\n"
        "Atau kirim 📸 foto struk. Selamat mencatat!",
        _finish_keyboard(),
    )
    return ConversationHandler.END


async def lewati_onboarding(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await _update_user(update.effective_user.id, onboarding_completed=True)
    context.user_data.pop("onb_wallet_name", None)
    await track(
        update.effective_user.id,
        EVENT_ONBOARDING_COMPLETED,
        skipped=True,
    )
    if update.effective_message is not None:
        await update.effective_message.reply_text(
            "Oke, pengaturan dilewati.\n\n"
            "Kamu masih bisa mengubah zona waktu dan notifikasi lewat menu Akun.",
            reply_markup=_finish_keyboard(),
        )
    return ConversationHandler.END


onboarding_conv = ConversationHandler(
    entry_points=[
        CommandHandler("start", onboarding_start),
        CallbackQueryHandler(
            onboarding_start, pattern="^(onboarding_start|start_ulang)$"
        ),
    ],
    states={
        TIMEZONE: [CallbackQueryHandler(pilih_timezone, pattern="^onb_tz_")],
        NOTIF: [CallbackQueryHandler(pilih_notif, pattern="^onb_notif_")],
        WALLET_NAME: [
            CallbackQueryHandler(wallet_nama_tunai, pattern="^onb_wallet_tunai$"),
            CallbackQueryHandler(wallet_skip, pattern="^onb_wallet_skip$"),
            MessageHandler(
                filters.TEXT & ~filters.COMMAND, wallet_nama_teks
            ),
        ],
        WALLET_BALANCE: [
            CallbackQueryHandler(wallet_saldo_nol, pattern="^onb_balance_zero$"),
            CallbackQueryHandler(wallet_skip, pattern="^onb_wallet_skip$"),
            MessageHandler(
                filters.TEXT & ~filters.COMMAND, wallet_saldo_teks
            ),
        ],
        PRIVACY: [CallbackQueryHandler(selesai, pattern="^onb_done$")],
    },
    fallbacks=[CommandHandler("batal", lewati_onboarding)],
    conversation_timeout=900,
    per_message=False,
)
