"""Riwayat, edit, dan hapus transaksi dari bot (UX-056).

Transfer dan biaya admin sengaja tidak bisa diedit/dihapus dari sini karena
satu transfer terdiri dari beberapa baris transaksi yang saling terkait.
"""

from __future__ import annotations

import logging
import uuid
from decimal import Decimal, InvalidOperation

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.core.database import AsyncSessionLocal
from app.models import Category, Transaction, TransactionType, User
from app.services.transaction_service import get_or_create_category

logger = logging.getLogger(__name__)

TRANSFER_CATEGORIES = ("Transfer", "Biaya Admin")
MAX_DESCRIPTION_LENGTH = 255
DEFAULT_LIST_LIMIT = 8


def _parse_tx_id(tx_hex: str) -> uuid.UUID:
    try:
        return uuid.UUID(str(tx_hex))
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValueError(
            "Transaksi tidak ditemukan. Buka ulang daftar riwayat, ya."
        ) from exc


async def _load_user(session, telegram_id: int) -> User | None:
    return (
        await session.execute(select(User).where(User.telegram_id == telegram_id))
    ).scalar_one_or_none()


async def _load_transaction(session, user_id, tx_id: uuid.UUID) -> Transaction | None:
    return (
        await session.execute(
            select(Transaction)
            .options(
                joinedload(Transaction.wallet),
                joinedload(Transaction.category),
            )
            .where(Transaction.id == tx_id, Transaction.user_id == user_id)
        )
    ).scalar_one_or_none()


def _to_dict(tx: Transaction) -> dict:
    category_name = tx.category.name if tx.category else "Lainnya"
    wallet_name = tx.wallet.name if tx.wallet else "Utama"
    return {
        "id": tx.id.hex,
        "amount": Decimal(str(tx.amount)),
        "type": tx.type,
        "type_label": (
            "Pemasukan" if tx.type == TransactionType.INCOME else "Pengeluaran"
        ),
        "description": tx.description or "",
        "category": category_name,
        "wallet": wallet_name,
        "date": tx.date,
        "editable": category_name not in TRANSFER_CATEGORIES,
        "sheet": {
            "date": tx.date.isoformat(),
            "type": (
                "Pemasukan"
                if tx.type == TransactionType.INCOME
                else "Pengeluaran"
            ),
            "amount": float(tx.amount),
            "category": category_name,
            "description": tx.description or "",
            "wallet": wallet_name,
        },
    }


async def list_recent_transactions(
    telegram_id: int, limit: int = DEFAULT_LIST_LIMIT, offset: int = 0
) -> list[dict]:
    """Ambil transaksi terbaru milik user untuk ditampilkan sebagai tombol."""
    async with AsyncSessionLocal() as session:
        user = await _load_user(session, telegram_id)
        if user is None:
            return []

        rows = (
            await session.execute(
                select(Transaction)
                .options(
                    joinedload(Transaction.wallet),
                    joinedload(Transaction.category),
                )
                .where(Transaction.user_id == user.id)
                .order_by(Transaction.date.desc(), Transaction.created_at.desc())
                .offset(max(0, offset))
                .limit(limit)
            )
        ).scalars().all()
        return [_to_dict(tx) for tx in rows]


async def list_transaction_page(
    telegram_id: int, page: int = 0, page_size: int = DEFAULT_LIST_LIMIT
) -> dict:
    """Ambil satu halaman riwayat beserta penanda halaman sebelumnya/berikutnya."""
    page = max(0, int(page))
    # Ambil satu baris ekstra untuk mengetahui apakah masih ada halaman berikutnya.
    rows = await list_recent_transactions(
        telegram_id, limit=page_size + 1, offset=page * page_size
    )
    has_next = len(rows) > page_size
    return {
        "items": rows[:page_size],
        "page": page,
        "has_prev": page > 0,
        "has_next": has_next,
    }


async def get_transaction(telegram_id: int, tx_hex: str) -> dict | None:
    """Detail satu transaksi; None bila tidak ditemukan atau bukan milik user."""
    tx_id = _parse_tx_id(tx_hex)
    async with AsyncSessionLocal() as session:
        user = await _load_user(session, telegram_id)
        if user is None:
            return None
        tx = await _load_transaction(session, user.id, tx_id)
        return _to_dict(tx) if tx else None


async def list_edit_categories(telegram_id: int, tx_hex: str) -> list[str]:
    """Kategori yang sudah dipakai user dengan tipe transaksi yang sama."""
    tx_id = _parse_tx_id(tx_hex)
    async with AsyncSessionLocal() as session:
        user = await _load_user(session, telegram_id)
        if user is None:
            return []
        tx = await _load_transaction(session, user.id, tx_id)
        if tx is None:
            return []

        names = (
            await session.execute(
                select(Category.name)
                .where(
                    Category.user_id == user.id,
                    Category.type == tx.type,
                    Category.name.notin_(TRANSFER_CATEGORIES),
                )
                .order_by(Category.name)
            )
        ).scalars().all()
        return list(dict.fromkeys(name for name in names if name))


async def delete_transaction(telegram_id: int, tx_hex: str) -> dict:
    """Hapus transaksi dan kembalikan saldo dompet terkait."""
    tx_id = _parse_tx_id(tx_hex)
    async with AsyncSessionLocal() as session:
        user = await _load_user(session, telegram_id)
        if user is None:
            raise ValueError("Akunmu belum aktif. Kirim /start dulu, ya.")

        tx = await _load_transaction(session, user.id, tx_id)
        if tx is None:
            raise ValueError("Transaksi sudah tidak ada. Buka ulang riwayat, ya.")

        info = _to_dict(tx)
        if not info["editable"]:
            raise ValueError(
                "Transfer dan biaya admin tidak bisa dihapus dari sini "
                "karena terdiri dari beberapa catatan. "
                "Catat penyesuaian saldo bila perlu."
            )

        wallet = tx.wallet
        if wallet is not None:
            if tx.type == TransactionType.INCOME:
                wallet.balance -= tx.amount
            else:
                wallet.balance += tx.amount
            info["wallet_balance"] = Decimal(str(wallet.balance))

        await session.delete(tx)
        await session.commit()

    logger.info("Transaksi dihapus: user=%s, id=%s", telegram_id, tx_id)
    return info


async def update_transaction(
    telegram_id: int,
    tx_hex: str,
    *,
    amount=None,
    description: str | None = None,
    category_name: str | None = None,
) -> dict:
    """Ubah nominal, keterangan, atau kategori satu transaksi.

    Perubahan nominal ikut menyesuaikan saldo dompet sebesar selisihnya.
    """
    tx_id = _parse_tx_id(tx_hex)
    async with AsyncSessionLocal() as session:
        user = await _load_user(session, telegram_id)
        if user is None:
            raise ValueError("Akunmu belum aktif. Kirim /start dulu, ya.")

        tx = await _load_transaction(session, user.id, tx_id)
        if tx is None:
            raise ValueError("Transaksi sudah tidak ada. Buka ulang riwayat, ya.")

        old = _to_dict(tx)
        if not old["editable"]:
            raise ValueError(
                "Transfer dan biaya admin tidak bisa diubah dari sini "
                "karena terdiri dari beberapa catatan. "
                "Catat penyesuaian saldo bila perlu."
            )

        if amount is not None:
            try:
                new_amount = Decimal(str(amount))
            except (InvalidOperation, TypeError, ValueError) as exc:
                raise ValueError("Nominal baru belum terbaca.") from exc
            if new_amount <= 0:
                raise ValueError("Nominal harus lebih besar dari nol.")

            delta = new_amount - Decimal(str(tx.amount))
            if tx.wallet is not None and delta != 0:
                if tx.type == TransactionType.INCOME:
                    tx.wallet.balance += delta
                else:
                    tx.wallet.balance -= delta
                tx.wallet.balance = Decimal(str(tx.wallet.balance))
            tx.amount = new_amount

        if description is not None:
            cleaned = " ".join(str(description).split())
            if not cleaned:
                raise ValueError("Keterangan tidak boleh kosong.")
            if len(cleaned) > MAX_DESCRIPTION_LENGTH:
                raise ValueError(
                    f"Keterangan maksimal {MAX_DESCRIPTION_LENGTH} karakter."
                )
            tx.description = cleaned

        if category_name is not None:
            cleaned_category = " ".join(str(category_name).split())
            if not cleaned_category:
                raise ValueError("Kategori tidak boleh kosong.")
            if cleaned_category in TRANSFER_CATEGORIES:
                raise ValueError(
                    "Kategori Transfer hanya untuk transaksi transfer."
                )
            category = await get_or_create_category(
                session, user.id, tx.type, cleaned_category
            )
            tx.category_id = category.id
            tx.category = category

        await session.commit()
        new = _to_dict(tx)

    logger.info("Transaksi diubah: user=%s, id=%s", telegram_id, tx_id)
    return {"old": old, "new": new}
