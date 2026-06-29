import decimal
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models import Wallet, User

logger = logging.getLogger(__name__)

WALLET_NAME, WALLET_BALANCE = range(2)

async def _get_internal_user_id(session, telegram_id):
    stmt = select(User.id).where(User.telegram_id == telegram_id)
    return (await session.execute(stmt)).scalar_one_or_none()

async def get_wallet_menu_content(telegram_id):
    async with AsyncSessionLocal() as session:
        user_id = await _get_internal_user_id(session, telegram_id)
        if not user_id:
            text = "💼 *Menu Dompet*\n\nBelum ada dompet. Mulai catat transaksi pertamamu!"
        else:
            stmt = select(Wallet).where(Wallet.user_id == user_id)
            wallets = (await session.execute(stmt)).scalars().all()
            
            if not wallets:
                text = "💼 *Menu Dompet*\n\nKamu belum memiliki dompet."
            else:
                text = "💼 *Daftar Dompet Kamu*\n\n"
                total = 0
                for w in wallets:
                    text += f"• *{w.name}*: Rp{w.balance:,.0f}\n"
                    total += w.balance
                text += f"\n*Total Semua Saldo:* Rp{total:,.0f}\n\nApa yang ingin Anda lakukan?"
                
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Tambah Dompet", callback_data="wallet_add_interactive")],
        [InlineKeyboardButton("🗑️ Hapus Dompet", callback_data="wallet_del_menu")],
        [InlineKeyboardButton("🔙 Kembali", callback_data="menu_utama")]
    ])
    return text, reply_markup

async def interactive_add_wallet_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    msg = "💳 *Tambah Dompet Baru*\n\nSilakan balas (reply) pesan ini dengan *Nama Dompet* (contoh: BCA, Mandiri, Cash):"
    
    if query:
        await query.answer()
        await query.edit_message_text(msg, parse_mode="Markdown")
    else:
        await update.message.reply_text(msg, parse_mode="Markdown")
    return WALLET_NAME

async def interactive_add_wallet_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    if " " in name:
        await update.message.reply_text("⚠️ Nama dompet sebaiknya tidak mengandung spasi. Silakan ketik ulang namanya (contoh: BCA):")
        return WALLET_NAME
    
    context.user_data['new_wallet_name'] = name
    await update.message.reply_text(
        f"Nama dompet *{name}* dicatat!\n\nSekarang ketik jumlah *Saldo Awalnya* (contoh: 500000) atau ketik 0 jika kosong:", 
        parse_mode="Markdown"
    )
    return WALLET_BALANCE

async def interactive_add_wallet_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    balance_str = update.message.text.replace(".", "").replace(",", "")
    try:
        balance = decimal.Decimal(balance_str)
    except Exception:
        await update.message.reply_text("⚠️ Saldo awal harus berupa angka. Silakan ketik ulang saldonya:")
        return WALLET_BALANCE
    
    name = context.user_data.get('new_wallet_name')
    
    async with AsyncSessionLocal() as session:
        user_id = await _get_internal_user_id(session, update.effective_user.id)
        if not user_id:
            await update.message.reply_text("Kamu belum memiliki akun. Catat transaksi pertamamu dulu!")
            return ConversationHandler.END
            
        stmt = select(Wallet).where(Wallet.user_id == user_id, Wallet.name == name)
        existing = (await session.execute(stmt)).scalar_one_or_none()
        if existing:
            await update.message.reply_text(f"⚠️ Dompet *{name}* sudah ada!", parse_mode="Markdown")
            return ConversationHandler.END
            
        wallet = Wallet(user_id=user_id, name=name, balance=balance)
        session.add(wallet)
        await session.commit()
    
    text, reply_markup = await get_wallet_menu_content(update.effective_user.id)
    await update.message.reply_text(f"✅ Dompet *{name}* berhasil ditambahkan dengan saldo awal Rp{balance:,.0f}!\n\n" + text, parse_mode="Markdown", reply_markup=reply_markup)
    return ConversationHandler.END

async def interactive_add_wallet_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Penambahan dompet dibatalkan.")
    return ConversationHandler.END

interactive_wallet_conv = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(interactive_add_wallet_start, pattern="^wallet_add_interactive$")
    ],
    states={
        WALLET_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, interactive_add_wallet_name)],
        WALLET_BALANCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, interactive_add_wallet_balance)]
    },
    fallbacks=[CommandHandler("batal", interactive_add_wallet_cancel)],
    per_message=False
)

async def interactive_del_wallet_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    async with AsyncSessionLocal() as session:
        user_id = await _get_internal_user_id(session, update.effective_user.id)
        if not user_id:
            await query.edit_message_text("Kamu belum memiliki akun.")
            return
            
        stmt = select(Wallet).where(Wallet.user_id == user_id)
        wallets = (await session.execute(stmt)).scalars().all()
        
        if not wallets:
            await query.edit_message_text("Kamu belum memiliki dompet.")
            return
            
        keyboard = []
        for w in wallets:
            keyboard.append([InlineKeyboardButton(f"🗑️ Hapus {w.name}", callback_data=f"wallet_del_action_{w.name}")])
        keyboard.append([InlineKeyboardButton("🔙 Kembali", callback_data="menu_dompet")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Pilih dompet yang ingin dihapus:\n*(Peringatan: Semua transaksi di dompet ini akan ikut terhapus!)*", parse_mode="Markdown", reply_markup=reply_markup)

async def interactive_del_wallet_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    nama_dompet = query.data.replace("wallet_del_action_", "")
    
    async with AsyncSessionLocal() as session:
        user_id = await _get_internal_user_id(session, update.effective_user.id)
        stmt = select(Wallet).where(Wallet.user_id == user_id, Wallet.name == nama_dompet)
        wallet = (await session.execute(stmt)).scalar_one_or_none()
        
        if wallet:
            await session.delete(wallet)
            await session.commit()
            text, reply_markup = await get_wallet_menu_content(update.effective_user.id)
            await query.edit_message_text(f"✅ Dompet *{nama_dompet}* berhasil dihapus.\n\n" + text, parse_mode="Markdown", reply_markup=reply_markup)
        else:
            text, reply_markup = await get_wallet_menu_content(update.effective_user.id)
            await query.edit_message_text("⚠️ Dompet tidak ditemukan atau sudah dihapus.\n\n" + text, parse_mode="Markdown", reply_markup=reply_markup)
