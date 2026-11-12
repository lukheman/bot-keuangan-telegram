import os
import decimal
import time
import uuid
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from app.services.groq_service import analyze_transaction
from app.services.transaction_service import (
    adjust_wallet_balance,
    get_primary_wallet_name,
    record_transaction,
    record_transfer,
    undo_transaction,
)
from app.services.sheets_service import append_to_sheet, delete_from_sheet
from app.services.telemetry_service import track_ai_duration, track_transaction
from app.services.pending_service import (
    cancel_pending,
    consume_pending,
    create_pending,
)
from app.models import TransactionType
import logging
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models import Wallet, User
from app.services.transaction_service import get_or_create_user
from bot.utils.messages import (
    GENERIC_ERROR,
    SAVE_ERROR,
    SESSION_EXPIRED,
    build_wallet_callback_data,
    md,
    rupiah,
    transaksi_keyboard,
)

logger = logging.getLogger(__name__)

# Transaksi dengan keyakinan AI di bawah ambang ini ditampilkan sebagai
# pratinjau agar pengguna bisa memeriksa sebelum disimpan.
PREVIEW_CONFIDENCE_THRESHOLD = 0.75

# UX-054: foto struk boleh dikirim sebagai foto biasa atau dokumen gambar.
SUPPORTED_IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png"}
MAX_IMAGE_BYTES = 10 * 1024 * 1024


def _image_source(message) -> tuple[str | None, str | None, str | None]:
    """Ambil file_id + ekstensi dari foto/dokumen, atau pesan error yang ramah."""
    photos = getattr(message, "photo", None)
    if photos:
        return photos[-1].file_id, ".jpg", None

    document = getattr(message, "document", None)
    if document is None:
        return None, None, "Kirim foto struk atau gambar JPG/PNG, ya."

    mime_type = (getattr(document, "mime_type", "") or "").lower()
    extension = SUPPORTED_IMAGE_TYPES.get(mime_type)
    if extension is None:
        return None, None, "Format gambar harus JPG atau PNG."

    file_size = getattr(document, "file_size", None)
    if file_size and file_size > MAX_IMAGE_BYTES:
        return None, None, "Ukuran gambar terlalu besar (maksimal 10 MB)."

    return document.file_id, extension, None


async def _simpan_transfer(update_effective_user, amount, source_name, dest_name, fee, description):
    """Panggil record_transfer dan catat semua sisinya ke Google Sheets."""
    result = await record_transfer(
        update_effective_user,
        amount,
        source_name,
        dest_name,
        fee=fee,
        description=description,
    )
    await append_to_sheet(result["out_tx"])
    await append_to_sheet(result["in_tx"])
    if result["fee_tx"] is not None:
        await append_to_sheet(result["fee_tx"])
    return result


def _format_transfer_berhasil(result: dict) -> str:
    waktu = result["local_created_at"].strftime('%d %b %Y, %H:%M')
    fee_line = f"🧾 *Admin:* {rupiah(result['fee'])}\n" if result["fee"] > 0 else ""
    return (
        "🔁 *Transfer Berhasil Dicatat!*\n\n"
        f"💵 *Jumlah:* {rupiah(result['amount'])}\n"
        f"{fee_line}"
        f"📤 *Dari:* {md(result['source_wallet'].name)} ({rupiah(result['source_wallet'].balance)})\n"
        f"📥 *Ke:* {md(result['dest_wallet'].name)} ({rupiah(result['dest_wallet'].balance)})\n"
        f"🕒 *Waktu:* {waktu}\n"
        f"📝 *Deskripsi:* {md(result['description'])}"
    )


def _preview_keyboard(token: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Simpan", callback_data=f"prev_ok_{token}"),
                InlineKeyboardButton("❌ Batal", callback_data=f"prev_no_{token}"),
            ]
        ]
    )


def _preview_text(pending: dict) -> str:
    kind = pending.get("kind", "simple")
    amount = rupiah(pending.get("amount", 0))

    if kind == "transfer":
        fee = pending.get("fee") or 0
        fee_line = f"🧾 *Admin:* {rupiah(fee)}\n" if fee > 0 else ""
        return (
            "🔁 *Konfirmasi Transfer*\n\n"
            f"📤 *Dari:* {md(pending.get('source'))}\n"
            f"📥 *Ke:* {md(pending.get('dest'))}\n"
            f"💵 *Jumlah:* {amount}\n"
            f"{fee_line}"
            f"📝 *Deskripsi:* {md(pending.get('description'))}\n\n"
            "Periksa lagi sebelum disimpan."
        )

    if kind == "correction":
        wallet = pending.get("wallet_name") or "dompet utama"
        return (
            "⚖️ *Konfirmasi Penyesuaian Saldo*\n\n"
            f"💼 Dompet: *{md(wallet)}*\n"
            f"🎯 Saldo baru: *{amount}*\n\n"
            "Aku akan mencatat selisihnya sebagai penyesuaian saldo. "
            "Periksa lagi sebelum disimpan."
        )

    jenis = "Pemasukan" if pending.get("type") == TransactionType.INCOME else "Pengeluaran"
    icon = "📈" if pending.get("type") == TransactionType.INCOME else "📉"
    wallet = pending.get("wallet_name") or "Dompet utama"
    confidence = pending.get("confidence")
    confidence_line = ""
    if confidence is not None:
        confidence_line = "\n🔎 Aku belum sepenuhnya yakin, jadi tolong periksa dulu."

    return (
        f"{icon} *Konfirmasi {jenis}*\n\n"
        f"💵 *Jumlah:* {amount}\n"
        f"📝 *Deskripsi:* {md(pending.get('description'))}\n"
        f"🏷️ *Kategori:* {md(pending.get('category'))}\n"
        f"💼 *Dompet:* {md(wallet)}"
        f"{confidence_line}\n\n"
        "Periksa lagi sebelum disimpan."
    )


def _wallet_missing(reason: str) -> bool:
    lowered = reason.lower()
    return "dompet" in lowered and "tidak ditemukan" in lowered


def _wallet_problem_keyboard() -> InlineKeyboardMarkup:
    """Jalan keluar saat dompet tidak ditemukan, bukan layar buntu."""
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("➕ Tambah dompet", callback_data="wallet_add_interactive")],
            [InlineKeyboardButton("💼 Lihat dompet", callback_data="menu_dompet")],
            [InlineKeyboardButton("🏠 Menu", callback_data="menu_utama")],
        ]
    )


def _wallet_picker_keyboard(wallets, token: str) -> InlineKeyboardMarkup:
    """Tombol pilih dompet + opsi buat dompet baru."""
    keyboard = [
        [
            InlineKeyboardButton(
                wallet.name,
                callback_data=build_wallet_callback_data(token, wallet.id),
            )
        ]
        for wallet in wallets
    ]
    keyboard.append(
        [InlineKeyboardButton("➕ Buat dompet baru", callback_data="wallet_add_interactive")]
    )
    keyboard.append([InlineKeyboardButton("🏠 Menu", callback_data="menu_utama")])
    return InlineKeyboardMarkup(keyboard)


async def _offer_wallet_choices(reply_func, pending: dict, reason: str) -> None:
    """Simpan ulang transaksi lalu minta pengguna memilih/membuat dompet."""
    telegram_id = pending["user"].id
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(
            session,
            telegram_id,
            getattr(pending["user"], "username", None),
            getattr(pending["user"], "full_name", None),
        )
        wallets = (
            await session.execute(select(Wallet).where(Wallet.user_id == user.id))
        ).scalars().all()

    retry = dict(pending)
    retry["wallet_name"] = None
    retry["needs_preview"] = True
    token = await create_pending(retry["user"], retry)

    await reply_func(
        f"⚠️ {md(reason)}\n\n"
        "Pilih dompet lain di bawah, atau buat dompet baru. "
        "Transaksinya tidak perlu diketik ulang.",
        parse_mode="Markdown",
        reply_markup=_wallet_picker_keyboard(wallets, token),
    )


async def _finalize_simple(reply_func, pending: dict) -> None:
    """Simpan transaksi sederhana dan kirim pesan sukses."""
    try:
        tx = await record_transaction(
            pending["user"],
            pending["amount"],
            pending["description"],
            pending["type"],
            category_name=pending["category"],
            wallet_name=pending.get("wallet_name"),
        )
        await append_to_sheet(tx)
        await track_transaction(pending["user"].id, "simple")

        jenis = "Pemasukan" if tx.type == TransactionType.INCOME else "Pengeluaran"
        icon = "📈" if tx.type == TransactionType.INCOME else "📉"
        wallet_display = tx.wallet_name or await get_primary_wallet_name(
            pending["user"].id
        )

        msg = (
            f"{icon} *{jenis} Berhasil Dicatat!*\n\n"
            f"💵 *Jumlah:* {rupiah(tx.amount)}\n"
            f"🕒 *Waktu:* {tx.local_created_at.strftime('%d %b %Y, %H:%M')}\n"
            f"📝 *Deskripsi:* {md(tx.description)}\n"
            f"🏷️ *Kategori:* {md(tx.category_name)}\n"
            f"💼 *Dompet:* {md(wallet_display)}"
        )
        if getattr(tx, "budget_warning", None):
            msg += f"\n\n{tx.budget_warning}"

        await reply_func(
            msg,
            parse_mode="Markdown",
            reply_markup=transaksi_keyboard(tx.id.hex),
        )
    except ValueError as ve:
        reason = str(ve)
        if _wallet_missing(reason):
            await _offer_wallet_choices(reply_func, pending, reason)
            return
        await reply_func(
            f"⚠️ {md(reason)}",
            parse_mode="Markdown",
            reply_markup=transaksi_keyboard(),
        )
    except Exception as e:
        logger.error(f"Gagal mencatat transaksi: {e}", exc_info=True)
        await reply_func(SAVE_ERROR, reply_markup=transaksi_keyboard())


async def _finalize_transfer(reply_func, pending: dict) -> None:
    try:
        fee = decimal.Decimal(str(pending.get("fee") or 0))
        transfer_result = await _simpan_transfer(
            pending["user"],
            decimal.Decimal(str(pending["amount"])),
            pending["source"],
            pending["dest"],
            fee,
            pending.get("description")
            or f"Transfer {pending['source']} ke {pending['dest']}",
        )
        await reply_func(
            _format_transfer_berhasil(transfer_result),
            parse_mode="Markdown",
            reply_markup=transaksi_keyboard(),
        )
        await track_transaction(pending["user"].id, "transfer")
    except (decimal.InvalidOperation, ValueError) as ve:
        reason = str(ve)
        await reply_func(
            f"⚠️ {md(reason)}",
            parse_mode="Markdown",
            reply_markup=(
                _wallet_problem_keyboard()
                if _wallet_missing(reason)
                else transaksi_keyboard()
            ),
        )
    except Exception as e:
        logger.error(f"Gagal mencatat transfer: {e}", exc_info=True)
        await reply_func(SAVE_ERROR, reply_markup=transaksi_keyboard())


async def _finalize_correction(reply_func, pending: dict) -> None:
    try:
        tx = await adjust_wallet_balance(
            pending["user"],
            decimal.Decimal(str(pending["amount"])),
            wallet_name=pending.get("wallet_name"),
        )
        if tx is None:
            await reply_func(
                "✅ Saldo kamu sudah sesuai, tidak ada penyesuaian yang diperlukan.",
                reply_markup=transaksi_keyboard(),
            )
            return

        await append_to_sheet(tx)
        await track_transaction(pending["user"].id, "correction")
        jenis = (
            "Penyesuaian saldo (masuk)"
            if tx.type == TransactionType.INCOME
            else "Penyesuaian saldo (keluar)"
        )
        msg = (
            "⚖️ *Penyesuaian Saldo*\n\n"
            f"Saldo disesuaikan menjadi {rupiah(pending['amount'])}.\n"
            f"Dicatat sebagai *{jenis}* sebesar {rupiah(tx.amount)} agar sesuai.\n\n"
            f"🕒 *Waktu:* {tx.local_created_at.strftime('%d %b %Y, %H:%M')}\n"
            f"💼 *Dompet:* {md(tx.wallet_name)}"
        )
        await reply_func(
            msg, parse_mode="Markdown", reply_markup=transaksi_keyboard(tx.id.hex)
        )
    except ValueError as ve:
        reason = str(ve)
        await reply_func(
            f"⚠️ {md(reason)}",
            parse_mode="Markdown",
            reply_markup=(
                _wallet_problem_keyboard()
                if _wallet_missing(reason)
                else transaksi_keyboard()
            ),
        )
    except Exception as e:
        logger.error(f"Gagal melakukan koreksi saldo: {e}", exc_info=True)
        await reply_func(
            "⚠️ Gagal menyesuaikan saldo. Coba lagi sebentar.",
            reply_markup=transaksi_keyboard(),
        )


async def _store_preview(pending: dict) -> str:
    return await create_pending(pending["user"], pending)


async def _show_preview(reply_func, pending: dict) -> str:
    token = await _store_preview(pending)
    await reply_func(
        _preview_text(pending),
        parse_mode="Markdown",
        reply_markup=_preview_keyboard(token),
    )
    return token


async def preview_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    is_confirm = data.startswith("prev_ok_")
    token = data.removeprefix("prev_ok_" if is_confirm else "prev_no_")
    telegram_id = update.effective_user.id

    if not is_confirm:
        await cancel_pending(telegram_id, token)
        await query.edit_message_text(
            "❌ Pencatatan transaksi dibatalkan.",
            reply_markup=transaksi_keyboard(),
        )
        return

    # consume_pending menghapus baris sekaligus, sehingga tap kedua tidak
    # bisa menyimpan transaksi yang sama dua kali.
    pending = await consume_pending(telegram_id, token)

    if pending is None:
        await query.edit_message_text(
            SESSION_EXPIRED, reply_markup=transaksi_keyboard()
        )
        return

    await query.edit_message_text("⏳ Menyimpan transaksi...")
    kind = pending.get("kind", "simple")
    if kind == "transfer":
        await _finalize_transfer(query.edit_message_text, pending)
    elif kind == "correction":
        await _finalize_correction(query.edit_message_text, pending)
    else:
        await _finalize_simple(query.edit_message_text, pending)


async def undo_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    token = query.data.removeprefix("undo_")
    try:
        info = await undo_transaction(update.effective_user.id, token)
    except ValueError as e:
        await query.edit_message_text(
            f"⚠️ {md(str(e))}",
            parse_mode="Markdown",
            reply_markup=transaksi_keyboard(),
        )
        return
    except Exception as e:
        logger.error(f"Gagal membatalkan transaksi: {e}", exc_info=True)
        await query.edit_message_text(
            "Maaf, transaksi belum bisa dibatalkan. Coba lagi sebentar.",
            reply_markup=transaksi_keyboard(),
        )
        return

    await delete_from_sheet(info["sheet"])

    wallet_line = f"\n💼 *Dompet:* {md(info['wallet'])}" if info.get("wallet") else ""
    await query.edit_message_text(
        "↩️ *Transaksi dibatalkan*\n\n"
        f"📝 *Deskripsi:* {md(info['description'])}\n"
        f"💵 *Jumlah:* {rupiah(info['amount'])}"
        f"{wallet_line}\n\n"
        "Saldo dompet sudah dikembalikan.",
        parse_mode="Markdown",
        reply_markup=transaksi_keyboard(),
    )


async def select_wallet_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    telegram_id = update.effective_user.id

    if data.startswith("sel_w_cancel_"):
        tx_id = data.replace("sel_w_cancel_", "")
        await cancel_pending(telegram_id, tx_id)
        await query.edit_message_text(
            "❌ Pencatatan transaksi dibatalkan.",
            reply_markup=transaksi_keyboard(),
        )
        return

    parts = data.split("_")
    if len(parts) < 4:
        await query.edit_message_text(
            SESSION_EXPIRED, reply_markup=transaksi_keyboard()
        )
        return

    tx_id = parts[2]
    wallet_id_str = parts[3]

    async with AsyncSessionLocal() as session:
        try:
            wallet_uuid = uuid.UUID(wallet_id_str)
        except ValueError:
            await query.edit_message_text(
                "⚠️ Dompet yang dipilih tidak dikenali. Silakan kirim ulang transaksinya.",
                reply_markup=transaksi_keyboard(),
            )
            return

        stmt = select(Wallet).where(
            Wallet.id == wallet_uuid,
            Wallet.user_id
            == (
                await session.execute(
                    select(User.id).where(User.telegram_id == telegram_id)
                )
            ).scalar_one_or_none(),
        )
        wallet = (await session.execute(stmt)).scalars().first()
        if not wallet:
            await query.edit_message_text(
                "⚠️ Dompet tidak ditemukan. Silakan kirim ulang transaksinya.",
                reply_markup=transaksi_keyboard(),
            )
            return
        wallet_name = wallet.name

    # Ambil sekaligus hapus agar tap berulang tidak menyimpan dua kali.
    pending = await consume_pending(telegram_id, tx_id)
    if pending is None:
        await query.edit_message_text(
            SESSION_EXPIRED, reply_markup=transaksi_keyboard()
        )
        return

    await query.edit_message_text("⏳ Menyimpan transaksi...")
    pending["wallet_name"] = wallet_name

    if pending.get("needs_preview"):
        await _show_preview(query.edit_message_text, pending)
        return

    await _finalize_simple(query.edit_message_text, pending)

async def proses_gambar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_message = await update.message.reply_text("⏳ Sedang memproses gambar...")

    try:
        file_id, extension, source_error = _image_source(update.message)
        if source_error:
            await status_message.edit_text(f"⚠️ {source_error}")
            return

        caption = update.message.caption
        file = await context.bot.get_file(file_id)
        file_path = (
            f"/tmp/temp_{update.effective_user.id}_{uuid.uuid4().hex}{extension}"
        )

        logger.info(f"User {update.effective_user.id} mengirim gambar untuk diproses AI Vision. Menyimpan di {file_path}")
        await file.download_to_drive(file_path)

        # Proses gambar secara langsung ke AI Vision (Tanpa Tesseract OCR)
        started = time.perf_counter()
        result = await analyze_transaction(file_path, caption=caption)
        await track_ai_duration(
            update.effective_user.id,
            "image",
            (time.perf_counter() - started) * 1000,
            result.is_valid,
        )
        os.remove(file_path)

        if not result.is_valid:
            detail = f"{md(result.reason)}\n\n" if result.reason else ""
            await status_message.edit_text(
                "❌ Gambar belum bisa dibaca.\n\n"
                f"{detail}"
                "Coba kirim foto yang lebih jelas, atau ketik transaksinya "
                "seperti `kopi 20rb`.",
                parse_mode="Markdown",
            )
            return

        tx_type = TransactionType.INCOME if result.type == "INCOME" else TransactionType.EXPENSE
        pending_payload = {
            "user": update.effective_user,
            "kind": "simple",
            "amount": decimal.Decimal(str(result.amount)),
            "description": result.description,
            "type": tx_type,
            "category": result.category,
            "confidence": result.confidence,
            "wallet_name": result.wallet_name,
        }

        if not result.wallet_name:
            async with AsyncSessionLocal() as session:
                user = await get_or_create_user(session, update.effective_user.id, update.effective_user.username, update.effective_user.full_name)
                stmt = select(Wallet).where(Wallet.user_id == user.id)
                wallets = (await session.execute(stmt)).scalars().all()
                
            if len(wallets) > 1:
                pending_payload["needs_preview"] = (
                    result.confidence < PREVIEW_CONFIDENCE_THRESHOLD
                )
                tx_id = await create_pending(
                    pending_payload["user"], pending_payload
                )
                
                keyboard = []
                for w in wallets:
                    keyboard.append([
                        InlineKeyboardButton(
                            w.name,
                            callback_data=build_wallet_callback_data(tx_id, w.id),
                        )
                    ])
                keyboard.append([InlineKeyboardButton("❌ Batal", callback_data=f"sel_w_cancel_{tx_id}")])
                
                msg = (
                    f"💳 *Pilih Dompet*\n\n"
                    f"Transaksi *{rupiah(result.amount)}* ({md(result.description)}) "
                    "belum jelas dompetnya. Pilih dompet di bawah:"
                )
                await status_message.edit_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
                return

        if result.confidence < PREVIEW_CONFIDENCE_THRESHOLD:
            await _show_preview(status_message.edit_text, pending_payload)
            return

        await _finalize_simple(status_message.edit_text, pending_payload)

    except Exception as e:
        logger.error(f"Error saat memproses gambar dari user {update.effective_user.id}: {str(e)}", exc_info=True)
        await status_message.edit_text(GENERIC_ERROR, reply_markup=transaksi_keyboard())
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)



from app.services.groq_service import analyze_text_transaction


async def _route_free_text(update: Update, context: ContextTypes.DEFAULT_TYPE, teks: str) -> bool:
    """Tangani frasa navigasi yang wajar diketik pengguna.

    Ini membuat bot tetap intuitif meski pengguna belum tahu command.
    """
    normalized = " ".join(teks.lower().split())

    if normalized in {"menu", "menu utama", "buka menu", "home"}:
        from bot.handlers.menu import tampilkan_menu

        await tampilkan_menu(update, context)
        return True

    if normalized in {"laporan", "laporan keuangan"}:
        from bot.handlers.menu import tampilkan_menu_laporan

        await tampilkan_menu_laporan(update, context)
        return True

    from bot.handlers.report import (
        ringkasan_bulan,
        ringkasan_hari_ini,
        ringkasan_minggu,
    )

    if "laporan hari ini" in normalized or "rekap hari ini" in normalized:
        await ringkasan_hari_ini(update, context)
        return True
    if "laporan minggu ini" in normalized or "laporan 7 hari" in normalized:
        await ringkasan_minggu(update, context)
        return True
    if "laporan bulan ini" in normalized or "rekap bulan ini" in normalized:
        await ringkasan_bulan(update, context)
        return True

    if normalized in {"saldo", "cek saldo", "dompet", "daftar dompet"}:
        from bot.handlers.wallet_interactive import cek_saldo

        await cek_saldo(update, context)
        return True

    if normalized in {"bantuan", "help", "cara pakai"}:
        from bot.handlers.system import bantuan

        await bantuan(update, context)
        return True

    return False


async def proses_teks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    teks = update.message.text
    if not teks or teks.startswith("/"):
        return

    if await _route_free_text(update, context, teks):
        return

    status_message = await update.message.reply_text("⏳ Membaca transaksimu...")

    try:
        started = time.perf_counter()
        result = await analyze_text_transaction(teks)
        await track_ai_duration(
            update.effective_user.id,
            "text",
            (time.perf_counter() - started) * 1000,
            result.is_valid,
        )

        if not result.is_valid:
            detail = f"\n\nAlasannya: {md(result.reason)}" if result.reason else ""
            await status_message.edit_text(
                "❌ Aku belum menemukan transaksi di pesan itu.\n\n"
                "Coba tulis nominal dan kegiatannya:\n"
                "• `makan siang 25rb`\n"
                "• `gaji 5jt`"
                f"{detail}",
                parse_mode="Markdown",
                reply_markup=transaksi_keyboard(),
            )
            return

        if result.type == "TRANSFER":
            source_name = result.source_wallet
            dest_name = result.destination_wallet
            if not source_name or not dest_name:
                await status_message.edit_text(
                    "⚠️ Dompet asal atau tujuan tidak terbaca.\n"
                    "Contoh: `transfer dari bri ke tunai sebesar 500 ribu dengan admin 5k`",
                    parse_mode="Markdown",
                )
                return
            try:
                fee = decimal.Decimal(str(result.fee or 0))
            except decimal.InvalidOperation:
                fee = decimal.Decimal(0)

            pending = {
                "user": update.effective_user,
                "kind": "transfer",
                "amount": decimal.Decimal(str(result.amount)),
                "source": source_name,
                "dest": dest_name,
                "fee": fee,
                "description": result.description
                or f"Transfer {source_name} ke {dest_name}",
            }
            await _show_preview(status_message.edit_text, pending)
            return

        if result.type == "CORRECTION":
            pending = {
                "user": update.effective_user,
                "kind": "correction",
                "amount": decimal.Decimal(str(result.amount)),
                "wallet_name": result.wallet_name,
                "description": "Penyesuaian Saldo Otomatis",
            }
            await _show_preview(status_message.edit_text, pending)
            return

        tx_type = TransactionType.INCOME if result.type == "INCOME" else TransactionType.EXPENSE
        pending_payload = {
            "user": update.effective_user,
            "kind": "simple",
            "amount": decimal.Decimal(str(result.amount)),
            "description": result.description,
            "type": tx_type,
            "category": result.category,
            "confidence": result.confidence,
            "wallet_name": result.wallet_name,
        }

        if not result.wallet_name:
            async with AsyncSessionLocal() as session:
                user = await get_or_create_user(session, update.effective_user.id, update.effective_user.username, update.effective_user.full_name)
                stmt = select(Wallet).where(Wallet.user_id == user.id)
                wallets = (await session.execute(stmt)).scalars().all()
                
            if len(wallets) > 1:
                pending_payload["needs_preview"] = (
                    result.confidence < PREVIEW_CONFIDENCE_THRESHOLD
                )
                tx_id = await create_pending(
                    pending_payload["user"], pending_payload
                )
                
                keyboard = []
                for w in wallets:
                    keyboard.append([
                        InlineKeyboardButton(
                            w.name,
                            callback_data=build_wallet_callback_data(tx_id, w.id),
                        )
                    ])
                keyboard.append([InlineKeyboardButton("❌ Batal", callback_data=f"sel_w_cancel_{tx_id}")])
                
                msg = (
                    f"💳 *Pilih Dompet*\n\n"
                    f"Transaksi *{rupiah(result.amount)}* ({md(result.description)}) "
                    "belum jelas dompetnya. Pilih dompet di bawah:"
                )
                await status_message.edit_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
                return

        if result.confidence < PREVIEW_CONFIDENCE_THRESHOLD:
            await _show_preview(status_message.edit_text, pending_payload)
            return

        await _finalize_simple(status_message.edit_text, pending_payload)

    except Exception as e:
        logger.error(f"Error saat memproses teks dari user {update.effective_user.id}: {str(e)}", exc_info=True)
        await status_message.edit_text(GENERIC_ERROR, reply_markup=transaksi_keyboard())
