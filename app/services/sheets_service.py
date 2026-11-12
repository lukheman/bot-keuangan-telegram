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
                worksheet.append_row(["Tanggal", "Tipe", "Nominal", "Kategori", "Deskripsi", "Dompet"])
        except Exception:
            worksheet.append_row(["Tanggal", "Tipe", "Nominal", "Kategori", "Deskripsi", "Dompet"])
            
        tipe_str = "Pemasukan" if tx.type == TransactionType.INCOME else "Pengeluaran"
        row = [
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


def _amount_matches(sheet_value: str, amount: float) -> bool:
    try:
        return abs(float(str(sheet_value).replace(",", ".")) - float(amount)) < 0.01
    except (TypeError, ValueError):
        return False


def _delete_from_sheet_sync(payload: dict) -> bool:
    """Hapus satu baris transaksi yang cocok dengan payload.

    Google Sheets belum punya ID transaksi, jadi pencocokan dilakukan pada
    kombinasi tanggal, tipe, nominal, kategori, deskripsi, dan dompet.
    """
    if not gc or not settings.GOOGLE_SHEET_ID:
        return False

    try:
        sh = gc.open_by_key(settings.GOOGLE_SHEET_ID)
        worksheet = sh.sheet1
        rows = worksheet.get_all_values()

        for index, row in enumerate(rows[1:], start=2):
            if len(row) < 6:
                continue
            row_date, row_type, row_amount, row_category, row_description, row_wallet = row[:6]
            if row_date != payload.get("date"):
                continue
            if row_type != payload.get("type"):
                continue
            if row_category != payload.get("category"):
                continue
            if row_description != payload.get("description"):
                continue
            if row_wallet != payload.get("wallet"):
                continue
            if not _amount_matches(row_amount, payload.get("amount", 0)):
                continue

            worksheet.delete_rows(index)
            logger.info("Baris transaksi dihapus dari Google Sheets: %s", payload)
            return True
    except Exception as e:
        logger.error(f"Gagal menghapus baris Google Sheets: {e}", exc_info=True)

    return False


async def delete_from_sheet(payload: dict) -> bool:
    """Hapus baris transaksi dari Google Sheets tanpa nge-block bot."""
    if not gc or not settings.GOOGLE_SHEET_ID:
        return False
    return await asyncio.to_thread(_delete_from_sheet_sync, payload)
