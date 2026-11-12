"""Test metrik UX mingguan (Fase 3)."""

import random

import pytest
from sqlalchemy import delete

from app.core.database import AsyncSessionLocal
from app.models import UxEvent
from app.services.telemetry_service import (
    EVENT_AI_DURATION,
    EVENT_ERROR,
    EVENT_FIFTH_TRANSACTION,
    EVENT_FIRST_TRANSACTION,
    EVENT_ONBOARDING_COMPLETED,
    EVENT_ONBOARDING_STARTED,
)
from app.services.ux_metrics_service import _p95, weekly_ux_metrics


def test_p95_mengambil_nilai_percentile():
    assert _p95([]) is None
    assert _p95([1000]) == 1000
    assert _p95([1000, 2000, 3000, 4000, 5000]) == 5000


@pytest.mark.asyncio
async def test_metrik_mingguan_menghitung_funnel_error_dan_durasi_ai():
    first = random.randint(8_000_000_000, 8_499_999_999)
    second = random.randint(8_500_000_000, 8_999_999_999)
    ids = [first, second]

    before = await weekly_ux_metrics(weeks=2)

    async with AsyncSessionLocal() as session:
        session.add_all(
            [
                UxEvent(telegram_id=first, event=EVENT_ONBOARDING_STARTED),
                UxEvent(telegram_id=second, event=EVENT_ONBOARDING_STARTED),
                UxEvent(telegram_id=first, event=EVENT_ONBOARDING_COMPLETED),
                UxEvent(telegram_id=first, event=EVENT_FIRST_TRANSACTION),
                UxEvent(telegram_id=first, event=EVENT_FIFTH_TRANSACTION),
                UxEvent(
                    telegram_id=first,
                    event=EVENT_AI_DURATION,
                    data={"kind": "text", "duration_ms": 1200, "ok": True},
                ),
                UxEvent(
                    telegram_id=second,
                    event=EVENT_AI_DURATION,
                    data={"kind": "image", "duration_ms": 3400, "ok": False},
                ),
                UxEvent(
                    telegram_id=first,
                    event=EVENT_ERROR,
                    data={"type": "ValueError"},
                ),
            ]
        )
        await session.commit()

    try:
        after = await weekly_ux_metrics(weeks=2)

        assert after["funnel"]["onboarding_started"] == (
            before["funnel"]["onboarding_started"] + 2
        )
        assert after["funnel"]["onboarding_completed"] == (
            before["funnel"]["onboarding_completed"] + 1
        )
        assert after["funnel"]["first_transaction"] == (
            before["funnel"]["first_transaction"] + 1
        )
        assert after["funnel"]["fifth_transaction"] == (
            before["funnel"]["fifth_transaction"] + 1
        )
        assert after["totals"]["errors"] == before["totals"]["errors"] + 1
        assert after["ai"]["samples"] == before["ai"]["samples"] + 2
        assert after["ai"]["failures"] == before["ai"]["failures"] + 1
        assert after["ai"]["avg_ms"] is not None
        assert after["ai"]["p95_ms"] is not None
        assert len(after["weeks"]) == 2
    finally:
        async with AsyncSessionLocal() as session:
            await session.execute(
                delete(UxEvent).where(UxEvent.telegram_id.in_(ids))
            )
            await session.commit()
