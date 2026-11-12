"""Personalisasi: sapaan dan target tabungan (UX-053).

Target tabungan bersifat global dan progresnya dihitung dari total saldo
semua dompet. Ini pilihan sederhana yang mudah dipahami pengguna awam.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from sqlalchemy import func, select

from app.core.database import AsyncSessionLocal
from app.models import User, Wallet

MAX_NICKNAME_LENGTH = 30


class PersonalizationError(ValueError):
    """Kesalahan yang aman ditampilkan ke pengguna."""


async def _load_user(session, telegram_id: int) -> User | None:
    return (
        await session.execute(select(User).where(User.telegram_id == telegram_id))
    ).scalar_one_or_none()


async def _total_balance(session, user_id) -> Decimal:
    total = (
        await session.execute(
            select(func.coalesce(func.sum(Wallet.balance), 0)).where(
                Wallet.user_id == user_id
            )
        )
    ).scalar_one()
    return Decimal(str(total or 0))


async def get_personalization(telegram_id: int) -> dict:
    """Ambil sapaan, target tabungan, dan progresnya untuk satu pengguna."""
    async with AsyncSessionLocal() as session:
        user = await _load_user(session, telegram_id)
        if user is None:
            return {
                "nickname": None,
                "savings_target": None,
                "total_balance": Decimal("0"),
            }

        total = await _total_balance(session, user.id)
        target = user.savings_target
        return {
            "nickname": user.nickname,
            "savings_target": Decimal(str(target)) if target is not None else None,
            "total_balance": total,
        }


async def set_nickname(telegram_id: int, nickname: str) -> str:
    """Simpan sapaan; teks kosong menghapus sapaan dan kembali ke nama Telegram."""
    cleaned = " ".join((nickname or "").split())
    if len(cleaned) > MAX_NICKNAME_LENGTH:
        raise PersonalizationError(
            f"Sapaan maksimal {MAX_NICKNAME_LENGTH} karakter."
        )

    async with AsyncSessionLocal() as session:
        user = await _load_user(session, telegram_id)
        if user is None:
            raise PersonalizationError("Akunmu belum aktif. Kirim /start dulu, ya.")
        user.nickname = cleaned or None
        await session.commit()
    return cleaned


async def set_savings_target(telegram_id: int, amount) -> Decimal:
    """Simpan target tabungan. Nominal harus lebih besar dari nol."""
    try:
        target = Decimal(str(amount))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise PersonalizationError("Nominal target belum terbaca.") from exc

    if target <= 0:
        raise PersonalizationError("Target tabungan harus lebih besar dari nol.")

    async with AsyncSessionLocal() as session:
        user = await _load_user(session, telegram_id)
        if user is None:
            raise PersonalizationError("Akunmu belum aktif. Kirim /start dulu, ya.")
        user.savings_target = target
        await session.commit()
    return target


async def clear_savings_target(telegram_id: int) -> None:
    async with AsyncSessionLocal() as session:
        user = await _load_user(session, telegram_id)
        if user is None:
            raise PersonalizationError("Akunmu belum aktif. Kirim /start dulu, ya.")
        user.savings_target = None
        await session.commit()


def savings_progress(target, total_balance) -> dict:
    """Hitung progres target dalam persen dan sisa nominal."""
    target = Decimal(str(target or 0))
    total = Decimal(str(total_balance or 0))
    if target <= 0:
        pct = 0.0
    else:
        pct = float(total / target * 100)
    remaining = max(target - total, Decimal("0"))
    return {
        "target": target,
        "total": total,
        "pct": pct,
        "remaining": remaining,
        "achieved": total >= target,
    }
