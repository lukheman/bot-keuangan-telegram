import logging
from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models import Wallet, User

logger = logging.getLogger(__name__)

async def list_wallets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    async with AsyncSessionLocal() as session:
        # Cari user internal ID
        stmt_user = select(User.id).where(User.telegram_id == user_id)
        internal_user_id = (await session.execute(stmt_user)).scalar_one_or_none()

        if not internal_user_id:
            await update.message.reply_text("Belum ada data dompet. Mulai catat transaksi pertamamu!")
            return

        stmt = select(Wallet).where(Wallet.user_id == internal_user_id)
        wallets = (await session.execute(stmt)).scalars().all()

        if not wallets:
            await update.message.reply_text("Kamu belum memiliki dompet yang tercatat.")
            return

        text = "💼 *Daftar Dompet Kamu*\n\n"
        total = 0
        for w in wallets:
            text += f"• *{w.name}*: Rp{w.balance:,.0f}\n"
            total += w.balance

        text += f"\n*Total Semua Saldo:* Rp{total:,.0f}"
        await update.message.reply_text(text, parse_mode="Markdown")

import decimal

async def _get_internal_user_id(session, telegram_id):
    stmt = select(User.id).where(User.telegram_id == telegram_id)
    return (await session.execute(stmt)).scalar_one_or_none()

async def tambah_dompet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or len(context.args) < 1:
        await update.message.reply_text("⚠️ Gunakan format: `/tambah_dompet [Nama_Dompet] [Saldo_Awal]`\nContoh: `/tambah_dompet BCA 500000`\n\n*(Catatan: Nama dompet tidak boleh mengandung spasi)*", parse_mode="Markdown")
        return

    nama = context.args[0]
    saldo_str = context.args[1].replace(".", "").replace(",", "") if len(context.args) > 1 else "0"

    try:
        saldo = decimal.Decimal(saldo_str)
    except Exception:
        await update.message.reply_text("⚠️ Saldo awal harus berupa angka.")
        return

    async with AsyncSessionLocal() as session:
        user_id = await _get_internal_user_id(session, update.effective_user.id)
        if not user_id:
            await update.message.reply_text("Silakan catat minimal satu transaksi dulu (atau /masuk) agar profilmu terdaftar.")
            return

        stmt = select(Wallet).where(Wallet.user_id == user_id, Wallet.name == nama)
        existing = (await session.execute(stmt)).scalar_one_or_none()
        if existing:
            await update.message.reply_text(f"⚠️ Dompet *{nama}* sudah ada!", parse_mode="Markdown")
            return

        wallet = Wallet(user_id=user_id, name=nama, balance=saldo)
        session.add(wallet)
        await session.commit()
        await update.message.reply_text(f"✅ Dompet *{nama}* berhasil ditambahkan dengan saldo awal Rp{saldo:,.0f}.", parse_mode="Markdown")

async def hapus_dompet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Gunakan format: `/hapus_dompet [Nama_Dompet]`\nContoh: `/hapus_dompet BCA`", parse_mode="Markdown")
        return

    nama = context.args[0]

    async with AsyncSessionLocal() as session:
        user_id = await _get_internal_user_id(session, update.effective_user.id)
        if not user_id:
            return

        stmt = select(Wallet).where(Wallet.user_id == user_id, Wallet.name == nama)
        wallet = (await session.execute(stmt)).scalar_one_or_none()

        if not wallet:
            await update.message.reply_text(f"⚠️ Dompet *{nama}* tidak ditemukan.", parse_mode="Markdown")
            return

        await session.delete(wallet)
        await session.commit()
        await update.message.reply_text(f"🗑️ Dompet *{nama}* telah dihapus beserta transaksinya.", parse_mode="Markdown")


