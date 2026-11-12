"""Penyimpanan sementara transaksi yang menunggu konfirmasi.

Sebelumnya state ini hanya ada di dict memori sehingga hilang saat bot
restart. Sekarang payload disimpan di tabel ``pending_transactions`` dengan
TTL, sehingga tombol pratinjau/pilih dompet tetap berfungsi setelah restart
dan tidak bisa dipakai dua kali (anti double-tap).
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import delete, select

from app.core.database import AsyncSessionLocal
from app.models import PendingTransaction, TransactionType, User
from app.services.transaction_service import get_or_create_user

logger = logging.getLogger(__name__)

# Sama dengan batas waktu pratinjau di UX-022.
PENDING_TTL = timedelta(minutes=10)

# Field payload yang aman disimpan sebagai JSON (tanpa objek Telegram).
_SIMPLE_FIELDS = (
    "kind",
    "description",
    "category",
    "wallet_name",
    "source",
    "dest",
    "needs_preview",
    "confidence",
)


@dataclass
class PendingUser:
    """Data minimal pengguna Telegram yang dibutuhkan service transaksi."""

    id: int
    username: str | None = None
    full_name: str | None = None


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def is_expired(expires_at: datetime, now: datetime | None = None) -> bool:
    """Cek kedaluwarsa dengan aman untuk datetime naive dari SQLite."""
    reference = now or now_utc()
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at <= reference


def serialize_pending(pending: dict) -> dict:
    """Ubah pending transaksi menjadi JSON yang bisa disimpan di database."""
    user = pending["user"]
    payload: dict = {
        "user": {
            "id": int(user.id),
            "username": getattr(user, "username", None),
            "full_name": getattr(user, "full_name", None),
        }
    }
    for field in _SIMPLE_FIELDS:
        if field in pending and pending[field] is not None:
            payload[field] = pending[field]

    if "amount" in pending:
        payload["amount"] = str(pending["amount"])
    if "fee" in pending:
        payload["fee"] = str(pending["fee"])
    if "type" in pending:
        payload["type"] = getattr(pending["type"], "value", pending["type"])
    return payload


def deserialize_pending(payload: dict) -> dict:
    """Kembalikan payload JSON menjadi dict siap dipakai handler."""
    raw = dict(payload or {})
    user_data = raw.pop("user", {}) or {}
    pending: dict = {
        "user": PendingUser(
            id=int(user_data.get("id")),
            username=user_data.get("username"),
            full_name=user_data.get("full_name"),
        )
    }
    pending.update({key: value for key, value in raw.items() if key not in ("amount", "fee", "type")})

    if "amount" in raw:
        pending["amount"] = Decimal(str(raw["amount"]))
    if "fee" in raw:
        pending["fee"] = Decimal(str(raw["fee"]))
    if "type" in raw:
        pending["type"] = TransactionType(raw["type"])
    return pending


async def _generate_token(session) -> str:
    while True:
        token = uuid.uuid4().hex[:12]
        exists = (
            await session.execute(
                select(PendingTransaction.id).where(PendingTransaction.token == token)
            )
        ).first()
        if not exists:
            return token


async def _cleanup_expired(session, now: datetime | None = None) -> None:
    reference = now or now_utc()
    await session.execute(
        delete(PendingTransaction).where(PendingTransaction.expires_at <= reference)
    )


async def create_pending(telegram_user, pending: dict, ttl: timedelta = PENDING_TTL) -> str:
    """Simpan pending transaksi baru dan kembalikan token pendeknya."""
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(
            session,
            telegram_user.id,
            getattr(telegram_user, "username", None),
            getattr(telegram_user, "full_name", None),
        )
        await _cleanup_expired(session)

        token = await _generate_token(session)
        session.add(
            PendingTransaction(
                token=token,
                user_id=user.id,
                payload=serialize_pending(pending),
                expires_at=now_utc() + ttl,
            )
        )
        await session.commit()

    return token


async def get_pending(telegram_id: int, token: str) -> dict | None:
    """Ambil pending milik pengguna; None bila tidak ada atau kedaluwarsa."""
    now = now_utc()
    async with AsyncSessionLocal() as session:
        row = (
            await session.execute(
                select(PendingTransaction)
                .join(User, User.id == PendingTransaction.user_id)
                .where(
                    PendingTransaction.token == token,
                    User.telegram_id == telegram_id,
                )
            )
        ).scalar_one_or_none()

        if row is None:
            return None
        if is_expired(row.expires_at, now):
            await session.delete(row)
            await session.commit()
            return None

        return deserialize_pending(row.payload)


async def update_pending(telegram_id: int, token: str, pending: dict) -> bool:
    """Perbarui payload pending (mis. setelah pengguna memilih dompet)."""
    async with AsyncSessionLocal() as session:
        row = (
            await session.execute(
                select(PendingTransaction)
                .join(User, User.id == PendingTransaction.user_id)
                .where(
                    PendingTransaction.token == token,
                    User.telegram_id == telegram_id,
                )
            )
        ).scalar_one_or_none()
        if row is None:
            return False

        row.payload = serialize_pending(pending)
        await session.commit()
        return True


async def consume_pending(telegram_id: int, token: str) -> dict | None:
    """Ambil sekaligus hapus pending agar tidak bisa dieksekusi dua kali."""
    now = now_utc()
    async with AsyncSessionLocal() as session:
        row = (
            await session.execute(
                select(PendingTransaction)
                .join(User, User.id == PendingTransaction.user_id)
                .where(
                    PendingTransaction.token == token,
                    User.telegram_id == telegram_id,
                )
                .with_for_update()
            )
        ).scalar_one_or_none()
        if row is None:
            return None
        if is_expired(row.expires_at, now):
            await session.delete(row)
            await session.commit()
            return None

        payload = dict(row.payload)
        await session.delete(row)
        await session.commit()

    return deserialize_pending(payload)


async def cancel_pending(telegram_id: int, token: str) -> None:
    """Hapus pending saat pengguna menekan Batal."""
    async with AsyncSessionLocal() as session:
        row = (
            await session.execute(
                select(PendingTransaction)
                .join(User, User.id == PendingTransaction.user_id)
                .where(
                    PendingTransaction.token == token,
                    User.telegram_id == telegram_id,
                )
            )
        ).scalar_one_or_none()
        if row is not None:
            await session.delete(row)
            await session.commit()
