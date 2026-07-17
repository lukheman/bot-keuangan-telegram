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
    status_message = await update.message.reply_text("⏳ Sedang memproses gambar...")

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
            await status_message.edit_text(f"❌ Gagal menganalisis gambar: {result.reason}")
            return

        tx_type = TransactionType.INCOME if result.type == "INCOME" else TransactionType.EXPENSE
        try:
            tx = await record_transaction(update.effective_user, decimal.Decimal(result.amount), result.description, tx_type, category_name=result.category, wallet_name=result.wallet_name)
            await append_to_sheet(tx)

            jenis = "Pemasukan" if result.type == "INCOME" else "Pengeluaran"
            icon = "📈" if result.type == "INCOME" else "📉"

            wallet_display = tx.wallet_name
            if not wallet_display:
                from app.services.transaction_service import get_primary_wallet_name
                wallet_display = await get_primary_wallet_name(update.effective_user.id)

            msg = (
                f"{icon} *{jenis} Berhasil Dicatat!*\n\n"
                f"💵 *Jumlah:* Rp{result.amount:,.0f}\n"
                f"📝 *Deskripsi:* {result.description}\n"
                f"🏷️ *Kategori:* {result.category}\n"
                f"💼 *Dompet:* {wallet_display}\n"
                f"🎯 *Keyakinan AI:* {result.confidence * 100:.0f}%"
            )
            await status_message.edit_text(msg, parse_mode="Markdown")
        except ValueError as ve:
            await status_message.edit_text(f"⚠️ {str(ve)}")
        except Exception as e:
            logger.error(f"Gagal mencatat transaksi gambar: {str(e)}", exc_info=True)
            await status_message.edit_text(f"⚠️ Terjadi error saat menyimpan: {str(e)}")

    except Exception as e:
        logger.error(f"Error saat memproses gambar dari user {update.effective_user.id}: {str(e)}", exc_info=True)
        await status_message.edit_text(f"⚠️ Terjadi error: {str(e)}")
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)



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
            f"💼 *Dompet:* {tx.wallet_name}\n"
            f"📅 *Tanggal:* {date.today().strftime('%d %b %Y')}",
            parse_mode="Markdown"
        )
    except ValueError as ve:
        await update.message.reply_text(f"⚠️ {str(ve)}")
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

    teks_lower = teks.strip().lower()

    # Daftar pesan pasti dari Reply Keyboard (termasuk variasi tanpa emoji jika diketik manual)
    REPLY_KEYBOARD_MESSAGES = {
        "📅 laporan hari ini", "laporan hari ini",
        "📆 laporan minggu ini", "laporan minggu ini",
        "📊 laporan bulan ini", "laporan bulan ini",
        "🔙 tutup menu laporan", "tutup menu laporan"
    }
    if teks_lower in REPLY_KEYBOARD_MESSAGES:
        return

    status_message = await update.message.reply_text("⏳ Membaca transaksimu...")

    try:
        result = await analyze_text_transaction(teks)

        if not result.is_valid:
            await status_message.edit_text(f"❌ Pesan tidak dikenali sebagai transaksi.\n({result.reason})")
            return

        if result.type == "CORRECTION":
            from app.services.transaction_service import adjust_wallet_balance
            try:
                tx = await adjust_wallet_balance(update.effective_user, decimal.Decimal(result.amount), wallet_name=result.wallet_name)
                
                if tx is None:
                    await status_message.edit_text("✅ Saldo Anda sudah sesuai, tidak ada penyesuaian yang diperlukan.")
                    return
                
                await append_to_sheet(tx)
                
                jenis = "Pemasukan (Koreksi)" if tx.type == TransactionType.INCOME else "Pengeluaran (Koreksi)"
                
                msg = (
                    f"⚖️ *Penyesuaian Saldo Otomatis!*\n\n"
                    f"Saldo disesuaikan menjadi Rp{result.amount:,.0f}.\n"
                    f"Dicatat sebagai *{jenis}* sebesar Rp{tx.amount:,.0f} agar sesuai.\n\n"
                    f"💼 *Dompet:* {tx.wallet_name}\n"
                    f"🎯 *Keyakinan AI:* {result.confidence * 100:.0f}%"
                )
                await status_message.edit_text(msg, parse_mode="Markdown")
                return
            except ValueError as ve:
                await status_message.edit_text(f"⚠️ {str(ve)}")
                return
            except Exception as e:
                logger.error(f"Gagal melakukan koreksi saldo: {str(e)}", exc_info=True)
                await status_message.edit_text(f"⚠️ Terjadi error saat koreksi saldo: {str(e)}")
                return

        tx_type = TransactionType.INCOME if result.type == "INCOME" else TransactionType.EXPENSE
        try:
            tx = await record_transaction(update.effective_user, decimal.Decimal(result.amount), result.description, tx_type, category_name=result.category, wallet_name=result.wallet_name)
            await append_to_sheet(tx)

            jenis = "Pemasukan" if result.type == "INCOME" else "Pengeluaran"
            icon = "📈" if result.type == "INCOME" else "📉"

            wallet_display = tx.wallet_name
            if not wallet_display:
                from app.services.transaction_service import get_primary_wallet_name
                wallet_display = await get_primary_wallet_name(update.effective_user.id)

            msg = (
                f"{icon} *{jenis} Otomatis Dicatat!*\n\n"
                f"💵 *Jumlah:* Rp{result.amount:,.0f}\n"
                f"📝 *Deskripsi:* {result.description}\n"
                f"🏷️ *Kategori:* {result.category}\n"
                f"💼 *Dompet:* {wallet_display}\n"
                f"🎯 *Keyakinan AI:* {result.confidence * 100:.0f}%"
            )
            await status_message.edit_text(msg, parse_mode="Markdown")
        except ValueError as ve:
            await status_message.edit_text(f"⚠️ {str(ve)}")
        except Exception as e:
            logger.error(f"Gagal mencatat transaksi teks: {str(e)}", exc_info=True)
            await status_message.edit_text(f"⚠️ Terjadi error saat menyimpan: {str(e)}")

    except Exception as e:
        logger.error(f"Error saat memproses teks dari user {update.effective_user.id}: {str(e)}", exc_info=True)
        await status_message.edit_text(f"⚠️ Terjadi error: {str(e)}")
