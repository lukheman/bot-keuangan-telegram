"""Test telemetri UX (UX-050)."""

import random

import pytest
from sqlalchemy import delete, select

from app.core.database import AsyncSessionLocal
from app.models import UxEvent
from app.services import telemetry_service


@pytest.mark.asyncio
async def test_track_tidak_melempar_saat_database_gagal(monkeypatch):
    class BrokenSession:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("database mati")

    monkeypatch.setattr(telemetry_service, "AsyncSessionLocal", BrokenSession)

    # Telemetri best-effort: alur utama tidak boleh ikut gagal.
    await telemetry_service.track(123, "test_event", foo="bar")
    await telemetry_service.track_transaction(123, "simple")
    await telemetry_service.track(None, "test_event")


def test_nama_event_funnel_stabil():
    assert telemetry_service.EVENT_ONBOARDING_STARTED == "onboarding_started"
    assert telemetry_service.EVENT_ONBOARDING_COMPLETED == "onboarding_completed"
    assert telemetry_service.EVENT_FIRST_TRANSACTION == "first_transaction"
    assert telemetry_service.EVENT_FIFTH_TRANSACTION == "fifth_transaction"
    assert telemetry_service.EVENT_ERROR == "error"
    assert telemetry_service.EVENT_AI_DURATION == "ai_duration"


@pytest.mark.asyncio
async def test_durasi_ai_hanya_menyimpan_metadata_teknis():
    telegram_id = random.randint(8_000_000_000, 8_999_999_999)
    try:
        await telemetry_service.track_ai_duration(
            telegram_id, "text", 1234.56, True
        )

        async with AsyncSessionLocal() as session:
            event = (
                await session.execute(
                    select(UxEvent).where(
                        UxEvent.telegram_id == telegram_id,
                        UxEvent.event == telemetry_service.EVENT_AI_DURATION,
                    )
                )
            ).scalar_one()

        assert event.data == {"kind": "text", "duration_ms": 1235, "ok": True}
    finally:
        async with AsyncSessionLocal() as session:
            await session.execute(
                delete(UxEvent).where(UxEvent.telegram_id == telegram_id)
            )
            await session.commit()
