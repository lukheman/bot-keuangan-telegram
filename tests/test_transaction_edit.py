"""Test riwayat, edit, dan hapus transaksi (UX-056)."""

import random
import uuid
from decimal import Decimal

import pytest
from sqlalchemy import delete, select

from app.core.database import AsyncSessionLocal
from app.models import Category, Transaction, TransactionType, User, Wallet
from app.services.transaction_edit_service import (
    delete_transaction,
    get_transaction,
    list_edit_categories,
    list_recent_transactions,
    list_transaction_page,
    update_transaction,
)
from bot.handlers.history import _detail_keyboard, _riwayat_keyboard


def _callback(prefix: str) -> str:
    return f"{prefix}{uuid.uuid4().hex}"


def test_callback_data_riwayat_tidak_melebihi_batas_telegram():
    for prefix in ("trx_view_", "trx_edit_", "trx_del_ask_", "trx_del_ok_"):
        data = _callback(prefix)
        assert len(data.encode("utf-8")) <= 64


def test_keyboard_riwayat_dan_detail_transfer():
    from datetime import date

    item = {
        "id": uuid.uuid4().hex,
        "amount": Decimal("20000"),
        "type_label": "Pengeluaran",
        "category": "Makanan",
        "date": date(2026, 11, 12),
        "editable": True,
    }
    list_buttons = [
        button
        for row in _riwayat_keyboard([item]).inline_keyboard
        for button in row
    ]
    assert any(button.callback_data == f"trx_view_{item['id']}" for button in list_buttons)
    assert all(
        len(button.callback_data.encode("utf-8")) <= 64 for button in list_buttons
    )

    detail_buttons = [
        button
        for row in _detail_keyboard(item).inline_keyboard
        for button in row
    ]
    callbacks = {button.callback_data for button in detail_buttons}
    assert f"trx_edit_{item['id']}" in callbacks
    assert f"trx_del_ask_{item['id']}" in callbacks

    transfer = dict(item, category="Transfer", editable=False)
    transfer_callbacks = {
        button.callback_data
        for row in _detail_keyboard(transfer).inline_keyboard
        for button in row
    }
    assert not any(cb.startswith(("trx_edit_", "trx_del_")) for cb in transfer_callbacks)


@pytest.mark.asyncio
async def test_riwayat_punya_halaman_berikutnya_dan_sebelumnya():
    seeded = await _seed()
    try:
        first = await list_transaction_page(
            seeded["telegram_id"], page=0, page_size=1
        )
        assert len(first["items"]) == 1
        assert first["has_prev"] is False
        assert first["has_next"] is True

        second = await list_transaction_page(
            seeded["telegram_id"], page=1, page_size=1
        )
        assert len(second["items"]) == 1
        assert second["has_prev"] is True
        assert second["has_next"] is False
    finally:
        await _cleanup(seeded)


async def _seed():
    telegram_id = random.randint(8_000_000_000, 8_999_999_999)
    async with AsyncSessionLocal() as session:
        user = User(
            telegram_id=telegram_id,
            username="ux056",
            full_name="Uji Riwayat",
        )
        session.add(user)
        await session.flush()

        wallet = Wallet(
            user_id=user.id,
            name="Utama",
            balance=Decimal("80000"),
            is_primary=True,
        )
        makanan = Category(
            user_id=user.id,
            name="Makanan",
            type=TransactionType.EXPENSE,
        )
        hiburan = Category(
            user_id=user.id,
            name="Hiburan",
            type=TransactionType.EXPENSE,
        )
        transfer = Category(
            user_id=user.id,
            name="Transfer",
            type=TransactionType.EXPENSE,
        )
        session.add_all([wallet, makanan, hiburan, transfer])
        await session.flush()

        tx = Transaction(
            user_id=user.id,
            category_id=makanan.id,
            wallet_id=wallet.id,
            amount=Decimal("20000"),
            type=TransactionType.EXPENSE,
            description="kopi",
            date=wallet.created_at.date(),
        )
        transfer_tx = Transaction(
            user_id=user.id,
            category_id=transfer.id,
            wallet_id=wallet.id,
            amount=Decimal("50000"),
            type=TransactionType.EXPENSE,
            description="transfer ke tunai",
            date=wallet.created_at.date(),
        )
        session.add_all([tx, transfer_tx])
        await session.commit()

        return {
            "telegram_id": telegram_id,
            "user_id": user.id,
            "wallet_id": wallet.id,
            "tx": tx.id.hex,
            "transfer": transfer_tx.id.hex,
        }


async def _cleanup(seeded: dict) -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(Transaction).where(Transaction.user_id == seeded["user_id"])
        )
        await session.execute(
            delete(Category).where(Category.user_id == seeded["user_id"])
        )
        await session.execute(
            delete(Wallet).where(Wallet.user_id == seeded["user_id"])
        )
        await session.execute(delete(User).where(User.id == seeded["user_id"]))
        await session.commit()


@pytest.mark.asyncio
async def test_hapus_transaksi_mengembalikan_saldo():
    seeded = await _seed()
    try:
        info = await delete_transaction(seeded["telegram_id"], seeded["tx"])

        assert info["amount"] == Decimal("20000")
        assert info["wallet_balance"] == Decimal("100000")

        async with AsyncSessionLocal() as session:
            wallet = await session.get(Wallet, seeded["wallet_id"])
            remaining = (
                await session.execute(
                    select(Transaction.id).where(
                        Transaction.user_id == seeded["user_id"],
                        Transaction.id == uuid.UUID(seeded["tx"]),
                    )
                )
            ).first()
        assert wallet.balance == Decimal("100000")
        assert remaining is None
    finally:
        await _cleanup(seeded)


@pytest.mark.asyncio
async def test_edit_nominal_menyesuaikan_saldo_dompet():
    seeded = await _seed()
    try:
        result = await update_transaction(
            seeded["telegram_id"], seeded["tx"], amount=Decimal("35000")
        )

        assert result["old"]["amount"] == Decimal("20000")
        assert result["new"]["amount"] == Decimal("35000")

        async with AsyncSessionLocal() as session:
            wallet = await session.get(Wallet, seeded["wallet_id"])
        # Saldo awal 100.000 - 35.000 = 65.000
        assert wallet.balance == Decimal("65000")
    finally:
        await _cleanup(seeded)


@pytest.mark.asyncio
async def test_edit_keterangan_dan_kategori():
    seeded = await _seed()
    try:
        categories = await list_edit_categories(seeded["telegram_id"], seeded["tx"])
        assert "Makanan" in categories
        assert "Hiburan" in categories
        assert "Transfer" not in categories

        result = await update_transaction(
            seeded["telegram_id"],
            seeded["tx"],
            description="  kopi   susu  ",
            category_name="Hiburan",
        )

        assert result["new"]["description"] == "kopi susu"
        assert result["new"]["category"] == "Hiburan"
        assert result["new"]["amount"] == Decimal("20000")
    finally:
        await _cleanup(seeded)


@pytest.mark.asyncio
async def test_transfer_tidak_bisa_diedit_atau_dihapus():
    seeded = await _seed()
    try:
        with pytest.raises(ValueError):
            await update_transaction(
                seeded["telegram_id"], seeded["transfer"], amount=Decimal("1000")
            )
        with pytest.raises(ValueError):
            await delete_transaction(seeded["telegram_id"], seeded["transfer"])
    finally:
        await _cleanup(seeded)


@pytest.mark.asyncio
async def test_riwayat_menampilkan_transaksi_terbaru():
    seeded = await _seed()
    try:
        items = await list_recent_transactions(seeded["telegram_id"])

        assert len(items) == 2
        assert all(len(item["id"]) == 32 for item in items)
        detail = await get_transaction(seeded["telegram_id"], seeded["tx"])
        assert detail["description"] == "kopi"
        assert detail["editable"] is True
        transfer = await get_transaction(seeded["telegram_id"], seeded["transfer"])
        assert transfer["editable"] is False
    finally:
        await _cleanup(seeded)


@pytest.mark.asyncio
async def test_nominal_nol_ditolak():
    seeded = await _seed()
    try:
        with pytest.raises(ValueError):
            await update_transaction(
                seeded["telegram_id"], seeded["tx"], amount=Decimal("0")
            )
    finally:
        await _cleanup(seeded)
