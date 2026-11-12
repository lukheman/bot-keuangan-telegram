"""Helper user agar semua pintu masuk bot konsisten."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.database import AsyncSessionLocal
from app.models import User

logger = logging.getLogger(__name__)


async def ensure_user(tg_user) -> bool:
    """Pastikan user terdaftar. Kembalikan True bila baru dibuat.

    Semua entry point (start, menu, dompet, budget) memakai helper ini agar
    instruksi "kirim /start" tidak pernah menjadi jalan buntu.
    """
    if tg_user is None:
        return False

    async with AsyncSessionLocal() as session:
        existing = (
            await session.execute(select(User).where(User.telegram_id == tg_user.id))
        ).scalar_one_or_none()
        if existing:
            return False

        user = User(
            telegram_id=tg_user.id,
            username=tg_user.username,
            full_name=tg_user.full_name or tg_user.first_name or "Kawan",
        )
        session.add(user)
        try:
            await session.commit()
        except IntegrityError:
            # Bisa terjadi bila dua update datang bersamaan.
            await session.rollback()
            return False
        logger.info("User baru terdaftar lewat entry point: %s", tg_user.id)
        return True
