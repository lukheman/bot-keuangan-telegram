import gspread
import logging
import asyncio
import json
import base64
from datetime import datetime
from app.core.config import settings
from app.models import Transaction, TransactionType

logger = logging.getLogger(__name__)

gc = None
try:
    if settings.GOOGLE_SHEETS_CREDENTIALS_B64:
        creds_json = base64.b64decode(settings.GOOGLE_SHEETS_CREDENTIALS_B64).decode('utf-8')
        creds_dict = json.loads(creds_json)
        gc = gspread.service_account_from_dict(creds_dict)
        logger.info("Service Account Google Sheets berhasil diinisialisasi dari base64.")
    else:
        # Memerlukan 'account.json' di direktori akar proyek
        gc = gspread.service_account(filename="account.json")
        logger.info("Service Account Google Sheets berhasil diinisialisasi dari account.json.")
except Exception as e:
    logger.warning(f"Gagal menginisialisasi Google Sheets (kredensial tidak valid atau tidak ditemukan): {e}")

def _append_to_sheet_sync(tx: Transaction):
    if not gc or not settings.GOOGLE_SHEET_ID:
        return
        
    try:
        sh = gc.open_by_key(settings.GOOGLE_SHEET_ID)
        worksheet = sh.sheet1
        
        # Jika baris pertama kosong, tambahkan header
        try:
            first_row = worksheet.row_values(1)
            if not first_row:
                worksheet.append_row(["ID", "Tanggal", "Tipe", "Nominal", "Kategori", "Deskripsi", "Dompet"])
        except Exception:
            worksheet.append_row(["ID", "Tanggal", "Tipe", "Nominal", "Kategori", "Deskripsi", "Dompet"])
            
        tipe_str = "Pemasukan" if tx.type == TransactionType.INCOME else "Pengeluaran"
        row = [
            str(tx.id),
            tx.date.strftime("%Y-%m-%d"),
            tipe_str,
            float(tx.amount),
            getattr(tx, "category_name", "Lainnya"),
            tx.description,
            getattr(tx, "wallet_name", "Utama")
        ]
        
        worksheet.append_row(row)
        logger.info(f"Berhasil mencatat transaksi ID {tx.id} ke Google Sheets.")
    except Exception as e:
        logger.error(f"Gagal mencatat ke Google Sheets: {e}", exc_info=True)

async def append_to_sheet(tx: Transaction):
    """Fungsi asynchronous untuk menulis ke Google Sheets tanpa nge-block bot."""
    if not gc or not settings.GOOGLE_SHEET_ID:
        return
    await asyncio.to_thread(_append_to_sheet_sync, tx)
