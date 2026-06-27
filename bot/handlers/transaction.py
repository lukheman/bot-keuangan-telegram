import os
import decimal
import uuid
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from datetime import date
from app.services.groq_service import analyze_transaction
from app.services.transaction_service import record_transaction
from app.services.sheets_service import append_to_sheet
from app.models import TransactionType
import logging

logger = logging.getLogger(__name__)

async def proses_gambar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Sedang memproses gambar...")

    try:
        photo = update.message.photo[-1]
        caption = update.message.caption
        file = await context.bot.get_file(photo.file_id)
        file_path = f"/tmp/temp_{update.effective_user.id}.jpg"
        
        logger.info(f"User {update.effective_user.id} mengirim gambar untuk diproses AI Vision. Menyimpan di {file_path}")
        await file.download_to_drive(file_path)

        # Proses gambar secara langsung ke AI Vision (Tanpa Tesseract OCR)
        result = await analyze_transaction(file_path, caption=caption)
        os.remove(file_path)

        if not result.is_valid:
            await update.message.reply_text(f"❌ Gagal menganalisis gambar: {result.reason}")
            return

        # Simpan ke user_data
        tx_id = str(uuid.uuid4())
        context.user_data[tx_id] = {
            "type": result.type,
            "amount": result.amount,
            "description": result.description,
            "category": result.category,
            "wallet_name": result.wallet_name
        }

        jenis = "Pemasukan" if result.type == "INCOME" else "Pengeluaran"
        lawan_jenis = "Pengeluaran" if result.type == "INCOME" else "Pemasukan"
        icon = "📈" if result.type == "INCOME" else "📉"

        keyboard = [
            [InlineKeyboardButton("✅ Simpan", callback_data=f"simpan_{tx_id}")],
            [InlineKeyboardButton(f"🔄 Ubah ke {lawan_jenis}", callback_data=f"ubah_{tx_id}")],
            [InlineKeyboardButton("❌ Batal", callback_data=f"batal_{tx_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        msg = (
            f"🤖 *Hasil Analisis Otomatis*\n\n"
            f"{icon} *Jenis:* {jenis}\n"
            f"💵 *Jumlah:* Rp{result.amount:,.0f}\n"
            f"📝 *Deskripsi:* {result.description}\n"
            f"🏷️ *Kategori:* {result.category}\n"
            f"💼 *Dompet:* {result.wallet_name}\n"
            f"🎯 *Keyakinan:* {result.confidence * 100:.0f}%\n\n"
            f"Apakah data ini sudah benar?"
        )

        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=reply_markup)

    except Exception as e:
        logger.error(f"Error saat memproses gambar dari user {update.effective_user.id}: {str(e)}", exc_info=True)
        await update.message.reply_text(f"⚠️ Terjadi error: {str(e)}")
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)

async def konfirmasi_transaksi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    action, tx_id = data.split("_", 1)

    if action == "batal":
        logger.info(f"User {update.effective_user.id} membatalkan transaksi {tx_id}")
        await query.edit_message_text("❌ Pencatatan dibatalkan.")
        if tx_id in context.user_data:
            del context.user_data[tx_id]
        return

    if action == "ubah":
        tx_data = context.user_data.get(tx_id)
        if not tx_data:
            await query.edit_message_text("⚠️ Sesi kedaluwarsa atau data tidak ditemukan.")
            return
            
        # Balik tipe
        tx_data["type"] = "EXPENSE" if tx_data["type"] == "INCOME" else "INCOME"
        
        # Buat keyboard baru
        lawan_jenis = "Pengeluaran" if tx_data["type"] == "INCOME" else "Pemasukan"
        keyboard = [
            [InlineKeyboardButton("✅ Simpan", callback_data=f"simpan_{tx_id}")],
            [InlineKeyboardButton(f"🔄 Ubah ke {lawan_jenis}", callback_data=f"ubah_{tx_id}")],
            [InlineKeyboardButton("❌ Batal", callback_data=f"batal_{tx_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        jenis = "Pemasukan" if tx_data["type"] == "INCOME" else "Pengeluaran"
        icon = "📈" if tx_data["type"] == "INCOME" else "📉"
        msg = (
            f"🤖 *Hasil Analisis Otomatis (Diedit)*\n\n"
            f"{icon} *Jenis:* {jenis}\n"
            f"💵 *Jumlah:* Rp{tx_data['amount']:,.0f}\n"
            f"📝 *Deskripsi:* {tx_data['description']}\n"
            f"🏷️ *Kategori:* {tx_data['category']}\n"
            f"💼 *Dompet:* {tx_data.get('wallet_name', 'Utama')}\n\n"
            f"Apakah data ini sudah benar?"
        )
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=reply_markup)
        return

    if action == "simpan":
        tx_data = context.user_data.get(tx_id)
        if not tx_data:
            await query.edit_message_text("⚠️ Sesi kedaluwarsa atau data tidak ditemukan.")
            return

        tx_type = TransactionType.INCOME if tx_data["type"] == "INCOME" else TransactionType.EXPENSE
        amount = tx_data["amount"]
        description = tx_data["description"]
        category = tx_data["category"]
        wallet_name = tx_data.get("wallet_name", "Utama")

        try:
            logger.info(f"User {update.effective_user.id} mengkonfirmasi transaksi {tx_id} ({tx_type.value} {amount})")
            tx = await record_transaction(update.effective_user, decimal.Decimal(amount), description, tx_type, category_name=category, wallet_name=wallet_name)
            
            # Catat ke Google Sheets
            await append_to_sheet(tx)
            
            jenis = "Pemasukan" if tx_data["type"] == "INCOME" else "Pengeluaran"
            icon = "📈" if tx_data["type"] == "INCOME" else "📉"
            await query.edit_message_text(
                f"{icon} *{jenis} Berhasil Dicatat!*\n\n"
                f"💵 *Jumlah:* Rp{amount:,.0f}\n"
                f"📝 *Deskripsi:* {description}\n"
                f"🏷️ *Kategori:* {category}\n"
                f"💼 *Dompet:* {wallet_name}",
                parse_mode="Markdown"
            )
            del context.user_data[tx_id]
        except Exception as e:
            logger.error(f"Gagal mencatat transaksi dari konfirmasi: {str(e)}", exc_info=True)
            await query.edit_message_text(f"⚠️ Terjadi error saat menyimpan: {str(e)}")

async def _catat_transaksi(update: Update, context: ContextTypes.DEFAULT_TYPE, tx_type: TransactionType, command_name: str, verb: str, icon: str):
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            f"⚠️ *Format salah!*\n\n"
            f"Gunakan: `/{command_name} [jumlah] [deskripsi]`\n"
            f"Contoh: `/{command_name} 50000 {verb}`",
            parse_mode="Markdown"
        )
        return

    try:
        amount_str = context.args[0].replace(".", "").replace(",", "")
        amount = decimal.Decimal(amount_str)
        description = " ".join(context.args[1:])
    except decimal.InvalidOperation:
        await update.message.reply_text("⚠️ Jumlah transaksi harus berupa angka yang valid.")
        return

    try:
        logger.info(f"Mencatat manual ({command_name}): User {update.effective_user.id}, Rp{amount}, {description}")
        tx = await record_transaction(update.effective_user, amount, description, tx_type)
        
        # Catat ke Google Sheets
        await append_to_sheet(tx)
        
        jenis = "Pemasukan" if tx_type == TransactionType.INCOME else "Pengeluaran"
        await update.message.reply_text(
            f"{icon} *{jenis} Berhasil Dicatat!*\n\n"
            f"💵 *Jumlah:* Rp{amount:,.0f}\n"
            f"📝 *Deskripsi:* {description}\n"
            f"📅 *Tanggal:* {date.today().strftime('%d %b %Y')}",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Gagal mencatat transaksi manual: {str(e)}", exc_info=True)
        await update.message.reply_text(f"⚠️ Terjadi error saat menyimpan ke database: {str(e)}")

async def catat_pemasukan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _catat_transaksi(update, context, TransactionType.INCOME, "masuk", "gaji bulan ini", "📈")

async def catat_pengeluaran(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _catat_transaksi(update, context, TransactionType.EXPENSE, "keluar", "makan siang", "📉")

from app.services.groq_service import analyze_text_transaction

async def proses_teks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    teks = update.message.text
    if not teks or teks.startswith("/"):
        return
        
    await update.message.reply_text("⏳ Membaca pesanmu...")
    
    try:
        result = await analyze_text_transaction(teks)
        
        if not result.is_valid:
            await update.message.reply_text(f"❌ Pesan tidak dikenali sebagai transaksi.\n({result.reason})")
            return
            
        # Simpan ke user_data (sama seperti gambar)
        tx_id = str(uuid.uuid4())
        context.user_data[tx_id] = {
            "type": result.type,
            "amount": result.amount,
            "description": result.description,
            "category": result.category,
            "wallet_name": result.wallet_name
        }

        jenis = "Pemasukan" if result.type == "INCOME" else "Pengeluaran"
        lawan_jenis = "Pengeluaran" if result.type == "INCOME" else "Pemasukan"
        icon = "📈" if result.type == "INCOME" else "📉"

        keyboard = [
            [InlineKeyboardButton("✅ Simpan", callback_data=f"simpan_{tx_id}")],
            [InlineKeyboardButton(f"🔄 Ubah ke {lawan_jenis}", callback_data=f"ubah_{tx_id}")],
            [InlineKeyboardButton("❌ Batal", callback_data=f"batal_{tx_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        msg = (
            f"🤖 *Hasil Analisis AI (Teks)*\n\n"
            f"{icon} *Jenis:* {jenis}\n"
            f"💵 *Jumlah:* Rp{result.amount:,.0f}\n"
            f"📝 *Deskripsi:* {result.description}\n"
            f"🏷️ *Kategori:* {result.category}\n"
            f"💼 *Dompet:* {result.wallet_name}\n\n"
            f"Apakah data ini sudah benar?"
        )

        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error saat memproses teks dari user {update.effective_user.id}: {str(e)}", exc_info=True)
        await update.message.reply_text(f"⚠️ Terjadi error: {str(e)}")
