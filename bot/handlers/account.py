import logging
from datetime import datetime, timedelta

import jwt
from sqlalchemy import delete, select
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models import Budget, PendingTransaction, User
from bot.handlers.personalization import account_keyboard
from app.services.personalization_service import get_personalization, savings_progress
from bot.utils.messages import md, rupiah, zona_waktu
from bot.utils.users import ensure_user

logger = logging.getLogger(__name__)


def _back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("🔙 Kembali", callback_data="menu_akun")]]
    )


def _dashboard_url(token: str) -> str | None:
    base = (settings.WEBAPP_BASE_URL or "").strip().rstrip("/")
    if not base:
        return None
    return f"{base}/api/auth/token?token={token}"


async def _get_user(telegram_id: int):
    async with AsyncSessionLocal() as session:
        return (
            await session.execute(select(User).where(User.telegram_id == telegram_id))
        ).scalar_one_or_none()


async def register_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_user = update.effective_user
    if tg_user is None or update.effective_message is None:
        return

    is_new = await ensure_user(tg_user)
    if is_new:
        nama = md(tg_user.first_name or tg_user.full_name or "Kawan")
        await update.effective_message.reply_text(
            f"🎉 Selamat datang, *{nama}*!\n\n"
            "Akunmu sudah siap. Langsung catat transaksi dengan chat biasa, "
            "misalnya `kopi 20rb`, atau kirim 📸 foto struk.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("🚀 Buka menu", callback_data="menu_utama")],
                    [InlineKeyboardButton("❓ Cara pakai", callback_data="menu_bantuan")],
                ]
            ),
        )
        return

    await update.effective_message.reply_text(
        "✅ Akunmu sudah terdaftar. Tidak perlu mendaftar lagi.",
        reply_markup=account_keyboard(),
    )


async def account_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_user = update.effective_user
    if tg_user is None:
        return

    if update.callback_query:
        await update.callback_query.answer()
        reply_func = update.callback_query.edit_message_text
        reply_markup = _back_keyboard()
    else:
        reply_func = update.effective_message.reply_text
        reply_markup = account_keyboard()

    user = await _get_user(tg_user.id)
    if not user:
        await reply_func(
            "⚠️ Akunmu belum aktif.\n\nKirim /start untuk membuat akun—cukup satu klik.",
            reply_markup=reply_markup,
        )
        return

    status_notif = "aktif ✅" if user.daily_report_enabled else "nonaktif ❌"
    username = f"@{md(user.username)}" if user.username else "—"
    mata_uang = "Rupiah" if (user.currency or "").upper() in ("IDR", "RP") else md(user.currency)
    bergabung = (
        user.created_at.strftime("%d %b %Y") if user.created_at else "—"
    )
    sapaan = md(user.nickname) if user.nickname else "—"

    try:
        personal = await get_personalization(tg_user.id)
        target = personal["savings_target"]
        if target:
            progress = savings_progress(target, personal["total_balance"])
            target_line = (
                f"{rupiah(progress['total'])} / {rupiah(target)} "
                f"({progress['pct']:.0f}%)"
            )
        else:
            target_line = "belum diatur"
    except Exception as exc:  # pragma: no cover - jalur DB bermasalah
        logger.warning("Gagal memuat personalisasi: %s", exc)
        target_line = "belum diatur"

    await reply_func(
        "👤 *Informasi Akun*\n\n"
        f"🆔 ID akun: `{user.telegram_id}`\n"
        f"🙋 Nama: {md(user.full_name)}\n"
        f"✨ Sapaan: {sapaan}\n"
        f"🔗 Nama pengguna: {username}\n"
        f"💱 Mata uang: {mata_uang}\n"
        f"🕒 Zona waktu: {zona_waktu(user.timezone)}\n"
        f"🌙 Notifikasi harian: {status_notif}\n"
        f"🎯 Target tabungan: {target_line}\n"
        f"📅 Bergabung: {bergabung}",
        parse_mode="Markdown",
        reply_markup=reply_markup,
    )


async def delete_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tampilkan konfirmasi, lalu hapus akun hanya setelah dikonfirmasi."""
    tg_user = update.effective_user
    if tg_user is None:
        return

    is_confirmation = bool(
        update.callback_query
        and update.callback_query.data == "akun_hapus_confirm"
    )

    if update.callback_query:
        await update.callback_query.answer()
        reply_func = update.callback_query.edit_message_text
    else:
        reply_func = update.effective_message.reply_text

    user = await _get_user(tg_user.id)
    if not user:
        await reply_func(
            "⚠️ Akunmu belum terdaftar, jadi tidak ada data yang perlu dihapus.",
            reply_markup=account_keyboard(),
        )
        return

    if not is_confirmation:
        await reply_func(
            "⚠️ *Hapus akun?*\n\n"
            "Semua data berikut akan terhapus permanen:\n"
            "• transaksi\n"
            "• dompet dan saldonya\n"
            "• budget dan kategori\n\n"
            "Tindakan ini *tidak bisa dibatalkan*.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "Ya, hapus permanen", callback_data="akun_hapus_confirm"
                        )
                    ],
                    [InlineKeyboardButton("Batal", callback_data="menu_akun")],
                ]
            ),
        )
        return

    async with AsyncSessionLocal() as session:
        db_user = (
            await session.execute(select(User).where(User.telegram_id == tg_user.id))
        ).scalar_one_or_none()
        if not db_user:
            await reply_func(
                "Akun sudah tidak ada.",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("🏠 Menu", callback_data="menu_utama")]]
                ),
            )
            return

        # Budget tidak punya relasi cascade ke User, jadi hapus eksplisit.
        await session.execute(delete(Budget).where(Budget.user_id == db_user.id))
        await session.execute(
            delete(PendingTransaction).where(
                PendingTransaction.user_id == db_user.id
            )
        )
        await session.delete(db_user)
        await session.commit()

    logger.info("Akun dihapus oleh user telegram_id=%s", tg_user.id)

    await reply_func(
        "🗑️ Akunmu sudah dihapus permanen.\n\n"
        "Terima kasih sudah memakai bot ini. Kalau ingin mulai lagi, "
        "tekan tombol di bawah.",
        reply_markup=InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("🚀 Mulai lagi", callback_data="start_ulang")],
            ]
        ),
    )


async def login_web(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_user = update.effective_user
    if tg_user is None:
        return

    if update.callback_query:
        await update.callback_query.answer()
        reply_func = update.callback_query.edit_message_text
        reply_markup = _back_keyboard()
    else:
        reply_func = update.effective_message.reply_text
        reply_markup = account_keyboard()

    user = await _get_user(tg_user.id)
    if not user:
        await reply_func(
            "⚠️ Akunmu belum aktif. Kirim /start terlebih dahulu.",
            reply_markup=reply_markup,
        )
        return

    payload = {
        "sub": str(user.id),
        "telegram_id": user.telegram_id,
        "name": user.full_name,
        "exp": datetime.utcnow() + timedelta(minutes=15),
    }
    token = jwt.encode(payload, settings.TELEGRAM_TOKEN, algorithm="HS256")
    url = _dashboard_url(token)

    if url is None:
        await reply_func(
            "🌐 *Dashboard web belum tersedia*\n\n"
            "Fitur ini belum diaktifkan oleh admin. Kamu tetap bisa memakai "
            "semua fitur lewat chat dan menu bot.",
            parse_mode="Markdown",
            reply_markup=reply_markup,
        )
        return

    keyboard = [[InlineKeyboardButton("🌐 Buka dashboard", url=url)]]
    if update.callback_query:
        keyboard.append([InlineKeyboardButton("🔙 Kembali", callback_data="menu_akun")])
    else:
        keyboard.append([InlineKeyboardButton("🏠 Menu", callback_data="menu_utama")])

    await reply_func(
        "🔐 *Masuk ke Dashboard*\n\n"
        "Tekan tombol di bawah untuk masuk otomatis. "
        "Link ini berlaku selama 15 menit.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
