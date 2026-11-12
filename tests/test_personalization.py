"""Test personalisasi sapaan & target tabungan (UX-053)."""

import random
from decimal import Decimal

import pytest
from sqlalchemy import delete

from app.core.database import AsyncSessionLocal
from app.models import User, Wallet
from app.services.personalization_service import (
    PersonalizationError,
    clear_savings_target,
    get_personalization,
    savings_progress,
    set_nickname,
    set_savings_target,
)
from bot.handlers.personalization import account_keyboard


def test_progres_target_dihitung_dari_total_saldo():
    progress = savings_progress(Decimal("5000000"), Decimal("2500000"))

    assert progress["pct"] == 50.0
    assert progress["remaining"] == Decimal("2500000")
    assert progress["achieved"] is False


def test_target_tercapai_tidak_memiliki_sisa():
    progress = savings_progress(Decimal("1000000"), Decimal("1500000"))

    assert progress["achieved"] is True
    assert progress["remaining"] == Decimal("0")


@pytest.mark.asyncio
async def test_target_nol_ditolak():
    with pytest.raises(PersonalizationError):
        await set_savings_target(123, 0)


def test_menu_akun_punya_jalan_masuk_personalisasi():
    buttons = [
        button
        for row in account_keyboard().inline_keyboard
        for button in row
    ]
    callbacks = {button.callback_data for button in buttons}

    assert "akun_nickname" in callbacks
    assert "akun_target" in callbacks
    assert "menu_utama" in callbacks


@pytest.mark.asyncio
async def test_personalisasi_tersimpan_di_database():
    telegram_id = random.randint(8_000_000_000, 8_999_999_999)

    async with AsyncSessionLocal() as session:
        user = User(
            telegram_id=telegram_id,
            username="ux053",
            full_name="Uji Personalisasi",
        )
        session.add(user)
        await session.flush()
        session.add(
            Wallet(
                user_id=user.id,
                name="Tabungan",
                balance=Decimal("2500000"),
                is_primary=True,
            )
        )
        await session.commit()
        user_id = user.id

    try:
        assert await set_nickname(telegram_id, "  Akmal  ") == "Akmal"
        await set_savings_target(telegram_id, Decimal("5000000"))

        data = await get_personalization(telegram_id)
        assert data["nickname"] == "Akmal"
        assert data["savings_target"] == Decimal("5000000")
        assert data["total_balance"] == Decimal("2500000")

        await clear_savings_target(telegram_id)
        data = await get_personalization(telegram_id)
        assert data["savings_target"] is None
    finally:
        async with AsyncSessionLocal() as session:
            await session.execute(delete(Wallet).where(Wallet.user_id == user_id))
            await session.execute(delete(User).where(User.id == user_id))
            await session.commit()
