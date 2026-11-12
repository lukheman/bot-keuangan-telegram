"""Test regresi rentang laporan mingguan."""

from datetime import date

import pytest

from app.services import report_service


@pytest.mark.asyncio
async def test_weekly_summary_mencakup_tujuh_hari(monkeypatch):
    captured = {}

    async def fake_summary(telegram_id, start_date, end_date):
        captured["start"] = start_date
        captured["end"] = end_date
        return [], 0, 0, {}

    monkeypatch.setattr(report_service, "get_summary_with_category", fake_summary)

    await report_service.get_weekly_summary(123, date(2026, 11, 12))

    assert captured["end"] == date(2026, 11, 12)
    assert captured["start"] == date(2026, 11, 6)
    assert (captured["end"] - captured["start"]).days == 6  # inklusif = 7 hari
