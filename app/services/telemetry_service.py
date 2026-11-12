"""Telemetri UX: funnel onboarding → transaksi pertama → transaksi kelima.

Semua penulisan bersifat best-effort: kegagalan telemetri tidak boleh
menggagalkan alur utama bot.
"""

from __future__ import annotations

import logging

from sqlalchemy import func, select

from app.core.database import AsyncSessionLocal
from app.models import Transaction, User, UxEvent

logger = logging.getLogger(__name__)

EVENT_ONBOARDING_STARTED = "onboarding_started"
EVENT_ONBOARDING_COMPLETED = "onboarding_completed"
EVENT_TRANSACTION_CREATED = "transaction_created"
EVENT_FIRST_TRANSACTION = "first_transaction"
EVENT_FIFTH_TRANSACTION = "fifth_transaction"
EVENT_ERROR = "error"
EVENT_AI_DURATION = "ai_duration"
EVENT_TRANSACTION_EDITED = "transaction_edited"
EVENT_TRANSACTION_DELETED = "transaction_deleted"


async def track(telegram_id: int | None, event: str, **data) -> None:
    """Catat satu event UX. Tidak pernah melempar exception ke pemanggil."""
    if telegram_id is None:
        return
    try:
        async with AsyncSessionLocal() as session:
            session.add(
                UxEvent(
                    telegram_id=int(telegram_id),
                    event=event[:50],
                    data=data or {},
                )
            )
            await session.commit()
    except Exception as exc:  # pragma: no cover - jalur kegagalan DB
        logger.warning("Telemetri gagal (%s): %s", event, exc)


async def _has_event(session, telegram_id: int, event: str) -> bool:
    found = (
        await session.execute(
            select(UxEvent.id).where(
                UxEvent.telegram_id == telegram_id,
                UxEvent.event == event,
            ).limit(1)
        )
    ).first()
    return found is not None


async def track_transaction(telegram_id: int, kind: str = "simple") -> None:
    """Catat transaksi dan tandai milestone pertama/kelima bila tercapai."""
    try:
        async with AsyncSessionLocal() as session:
            user = (
                await session.execute(
                    select(User).where(User.telegram_id == telegram_id)
                )
            ).scalar_one_or_none()
            if user is None:
                return

            session.add(
                UxEvent(
                    telegram_id=int(telegram_id),
                    event=EVENT_TRANSACTION_CREATED,
                    data={"kind": kind},
                )
            )

            total = (
                await session.execute(
                    select(func.count(Transaction.id)).where(
                        Transaction.user_id == user.id
                    )
                )
            ).scalar_one()

            if total >= 1 and not await _has_event(
                session, telegram_id, EVENT_FIRST_TRANSACTION
            ):
                session.add(
                    UxEvent(
                        telegram_id=int(telegram_id),
                        event=EVENT_FIRST_TRANSACTION,
                        data={"kind": kind},
                    )
                )

            if total >= 5 and not await _has_event(
                session, telegram_id, EVENT_FIFTH_TRANSACTION
            ):
                session.add(
                    UxEvent(
                        telegram_id=int(telegram_id),
                        event=EVENT_FIFTH_TRANSACTION,
                        data={},
                    )
                )

            await session.commit()
    except Exception as exc:  # pragma: no cover - jalur kegagalan DB
        logger.warning("Telemetri transaksi gagal: %s", exc)


async def track_ai_duration(
    telegram_id: int | None, kind: str, duration_ms: float, ok: bool
) -> None:
    """Catat durasi panggilan AI tanpa menyimpan isi pesan pengguna."""
    await track(
        telegram_id,
        EVENT_AI_DURATION,
        kind=kind,
        duration_ms=round(max(0.0, float(duration_ms))),
        ok=bool(ok),
    )
