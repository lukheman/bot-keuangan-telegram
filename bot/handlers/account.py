import logging
import uuid
import jwt
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models import User
from app.core.config import settings

logger = logging.getLogger(__name__)

async def register_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = update.effective_user
    
    async with AsyncSessionLocal() as session:
        stmt = select(User).where(User.telegram_id == user_data.id)
        user = (await session.execute(stmt)).scalar_one_or_none()
        
        if user:
            await update.message.reply_text("✅ Anda sudah terdaftar di sistem kami. Ketik /akun untuk melihat info Anda.")
            return
            
        # Register baru
        user = User(
            telegram_id=user_data.id,
            username=user_data.username,
            full_name=user_data.full_name or "Unknown"
        )
        session.add(user)
        await session.commit()
        
        await update.message.reply_text(
            f"🎉 Selamat datang, {user.full_name}!\n\n"
            "Akun Anda berhasil didaftarkan.\n"
            "Mulai catat keuangan Anda dengan mengirim foto struk atau mengetik pengeluaran secara natural."
        )

async def account_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = update.effective_user
    
    if update.callback_query:
        await update.callback_query.answer()
        reply_func = update.callback_query.edit_message_text
    else:
        reply_func = update.message.reply_text
    
    async with AsyncSessionLocal() as session:
        stmt = select(User).where(User.telegram_id == user_data.id)
        user = (await session.execute(stmt)).scalar_one_or_none()
        
        keyboard = [[InlineKeyboardButton("🔙 Kembali", callback_data="menu_akun")]]
        reply_markup = InlineKeyboardMarkup(keyboard) if update.callback_query else None
        
        if not user:
            await reply_func("⚠️ Anda belum terdaftar. Silakan ketik /register terlebih dahulu.", reply_markup=reply_markup)
            return
            
        await reply_func(
            "👤 *Informasi Akun*\n\n"
            f"ID Telegram: `{user.telegram_id}`\n"
            f"Nama: {user.full_name}\n"
            f"Mata Uang: {user.currency}\n"
            f"Bergabung Sejak: {user.created_at.strftime('%d %b %Y')}",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )

async def delete_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = update.effective_user
    
    if update.callback_query:
        await update.callback_query.answer()
        reply_func = update.callback_query.edit_message_text
    else:
        reply_func = update.message.reply_text
    
    async with AsyncSessionLocal() as session:
        stmt = select(User).where(User.telegram_id == user_data.id)
        user = (await session.execute(stmt)).scalar_one_or_none()
        
        keyboard = [[InlineKeyboardButton("🔙 Kembali", callback_data="menu_akun")]]
        reply_markup = InlineKeyboardMarkup(keyboard) if update.callback_query else None
        
        if not user:
            await reply_func("⚠️ Anda belum terdaftar.", reply_markup=reply_markup)
            return
            
        await session.delete(user)
        await session.commit()
        
        await reply_func("🗑️ Akun Anda beserta seluruh data transaksi dan dompet telah berhasil dihapus permanen dari sistem kami.", reply_markup=reply_markup)

async def login_web(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = update.effective_user
    
    if update.callback_query:
        await update.callback_query.answer()
        reply_func = update.callback_query.edit_message_text
    else:
        reply_func = update.message.reply_text
    
    async with AsyncSessionLocal() as session:
        stmt = select(User).where(User.telegram_id == user_data.id)
        user = (await session.execute(stmt)).scalar_one_or_none()
        
        if not user:
            keyboard = [[InlineKeyboardButton("🔙 Kembali", callback_data="menu_akun")]]
            reply_markup = InlineKeyboardMarkup(keyboard) if update.callback_query else None
            await reply_func("⚠️ Anda belum terdaftar. Silakan ketik /register terlebih dahulu.", reply_markup=reply_markup)
            return
            
        # Generate JWT Token valid for 15 minutes
        payload = {
            "sub": str(user.id),
            "telegram_id": user.telegram_id,
            "name": user.full_name,
            "exp": datetime.utcnow() + timedelta(minutes=15)
        }
        
        # We use telegram token as the secret key for signing the JWT for simplicity
        token = jwt.encode(payload, settings.TELEGRAM_TOKEN, algorithm="HS256")
        
        login_url = f"https://bot-keuangan-telegram.vercel.app/api/auth/token?token={token}"
        
        keyboard = [
            [InlineKeyboardButton("🌐 Buka Dashboard Web", url=login_url)]
        ]
        if update.callback_query:
            keyboard.append([InlineKeyboardButton("🔙 Kembali", callback_data="menu_akun")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await reply_func(
            "🔐 *Link Login Web Auth*\n\n"
            "Klik tombol di bawah ini untuk masuk ke Dashboard Web secara otomatis. Link ini hanya berlaku selama 15 menit.",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
