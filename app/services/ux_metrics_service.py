"""Agregasi metrik UX mingguan dari tabel `ux_events` (Fase 3).

Dipakai oleh dashboard metrik dan endpoint JSON. Tidak menyimpan isi pesan
pengguna; hanya menghitung event, konversi funnel, error, dan durasi AI.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.timezone import DEFAULT_TIMEZONE, get_zoneinfo, local_now, to_local_datetime
from app.models import UxEvent
from app.services.telemetry_service import (
    EVENT_AI_DURATION,
    EVENT_ERROR,
    EVENT_FIFTH_TRANSACTION,
    EVENT_FIRST_TRANSACTION,
    EVENT_ONBOARDING_COMPLETED,
    EVENT_ONBOARDING_STARTED,
    EVENT_TRANSACTION_CREATED,
)

MAX_WEEKS = 26


def _percent(part: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(part / total * 100, 1)


def _p95(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = int(round(0.95 * (len(ordered) - 1)))
    return ordered[index]


def _week_start(value: date) -> date:
    return value - timedelta(days=value.weekday())


async def weekly_ux_metrics(
    weeks: int = 8, now: datetime | None = None
) -> dict:
    """Hitung metrik per minggu (Senin–Minggu) untuk `weeks` minggu terakhir."""
    weeks = max(1, min(int(weeks), MAX_WEEKS))
    tz = get_zoneinfo(DEFAULT_TIMEZONE)

    current = now or local_now(DEFAULT_TIMEZONE)
    if current.tzinfo is None:
        current = current.replace(tzinfo=tz)
    else:
        current = current.astimezone(tz)

    current_week = _week_start(current.date())
    first_week = current_week - timedelta(weeks=weeks - 1)
    start_utc = datetime.combine(first_week, time.min, tzinfo=tz).astimezone(
        timezone.utc
    )

    async with AsyncSessionLocal() as session:
        rows = (
            await session.execute(
                select(UxEvent)
                .where(UxEvent.created_at >= start_utc)
                .order_by(UxEvent.created_at)
            )
        ).scalars().all()

    buckets: dict = {}
    for index in range(weeks):
        week = first_week + timedelta(weeks=index)
        buckets[week] = {
            "week_start": week.isoformat(),
            "week_end": (week + timedelta(days=6)).isoformat(),
            "events": {},
            "errors": 0,
            "ai_samples": 0,
            "ai_avg_ms": None,
            "ai_p95_ms": None,
            "_durations": [],
        }

    event_users: dict[str, set] = defaultdict(set)
    durations_all: list[float] = []
    ai_failures = 0
    errors_total = 0

    for row in rows:
        local_dt = to_local_datetime(row.created_at, DEFAULT_TIMEZONE)
        week = _week_start(local_dt.date())
        bucket = buckets.get(week)
        if bucket is None:
            continue

        event = row.event
        bucket["events"][event] = bucket["events"].get(event, 0) + 1
        if row.telegram_id:
            event_users[event].add(row.telegram_id)

        if event == EVENT_ERROR:
            bucket["errors"] += 1
            errors_total += 1

        if event == EVENT_AI_DURATION:
            data = row.data or {}
            value = data.get("duration_ms")
            if isinstance(value, (int, float)):
                duration = float(value)
                bucket["_durations"].append(duration)
                durations_all.append(duration)
            if data.get("ok") is False:
                ai_failures += 1

    weekly = []
    for week in sorted(buckets):
        bucket = buckets[week]
        durations = bucket.pop("_durations")
        bucket["ai_samples"] = len(durations)
        bucket["ai_avg_ms"] = (
            round(sum(durations) / len(durations), 1) if durations else None
        )
        bucket["ai_p95_ms"] = (
            round(_p95(durations), 1) if durations else None
        )
        weekly.append(bucket)

    started = len(event_users[EVENT_ONBOARDING_STARTED])
    completed = len(event_users[EVENT_ONBOARDING_COMPLETED])
    first_transaction = len(event_users[EVENT_FIRST_TRANSACTION])
    fifth_transaction = len(event_users[EVENT_FIFTH_TRANSACTION])

    return {
        "generated_at": current.isoformat(),
        "timezone": DEFAULT_TIMEZONE,
        "weeks": weekly,
        "funnel": {
            "onboarding_started": started,
            "onboarding_completed": completed,
            "first_transaction": first_transaction,
            "fifth_transaction": fifth_transaction,
            "completion_rate": _percent(completed, started),
            "first_transaction_rate": _percent(first_transaction, started),
            "fifth_transaction_rate": _percent(fifth_transaction, started),
        },
        "ai": {
            "samples": len(durations_all),
            "avg_ms": (
                round(sum(durations_all) / len(durations_all), 1)
                if durations_all
                else None
            ),
            "p95_ms": (
                round(_p95(durations_all), 1) if durations_all else None
            ),
            "failures": ai_failures,
        },
        "totals": {
            "events": len(rows),
            "transactions_created": len(event_users[EVENT_TRANSACTION_CREATED]),
            "errors": errors_total,
        },
    }
