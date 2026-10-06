import calendar
from datetime import date, timedelta
from typing import Tuple, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from app.core.database import AsyncSessionLocal
from app.models import Category, User, Transaction, TransactionType, Wallet
from app.core.timezone import local_now, to_local_datetime

async def get_user_local_date(telegram_id: int) -> date:
    async with AsyncSessionLocal() as session:
        user = (await session.execute(select(User).where(User.telegram_id == telegram_id))).scalar_one_or_none()
        return local_now(user.timezone if user else None).date()

async def _get_user_transactions(session: AsyncSession, telegram_id: int, start_date: date, end_date: date):
    stmt_user = select(User).where(User.telegram_id == telegram_id)
    user = (await session.execute(stmt_user)).scalar_one_or_none()
    if not user:
        return None

    stmt_tx = select(Transaction).options(
        joinedload(Transaction.category),
        joinedload(Transaction.wallet),
    ).where(
        Transaction.user_id == user.id
    ).order_by(Transaction.created_at.desc())
    
    transactions = (await session.execute(stmt_tx)).scalars().all()
    local_transactions = []
    for transaction in transactions:
        transaction.local_created_at = to_local_datetime(transaction.created_at, user.timezone)
        if start_date <= transaction.local_created_at.date() <= end_date:
            transaction.date = transaction.local_created_at.date()
            local_transactions.append(transaction)
    return local_transactions

async def get_summary_by_date_range(telegram_id: int, start_date: date, end_date: date) -> Tuple[Optional[List[Transaction]], float, float]:
    async with AsyncSessionLocal() as session:
        transactions = await _get_user_transactions(session, telegram_id, start_date, end_date)
        if transactions is None:
            return None, 0, 0
        
        total_income = sum(tx.amount for tx in transactions if tx.type == TransactionType.INCOME)
        total_expense = sum(tx.amount for tx in transactions if tx.type == TransactionType.EXPENSE)
        
        return list(transactions), float(total_income), float(total_expense)

async def get_summary_with_category(telegram_id: int, start_date: date, end_date: date):
    """Ringkasan transaksi + total + rekap pengeluaran per kategori (format laporan bulanan)."""
    summary = await get_summary_by_date_range(telegram_id, start_date, end_date)
    if summary[0] is None:
        return (*summary, {})

    expense_by_category = {}
    for transaction in summary[0]:
        if transaction.type == TransactionType.EXPENSE:
            category_name = transaction.category.name if transaction.category else "Lainnya"
            expense_by_category[category_name] = expense_by_category.get(category_name, 0) + float(transaction.amount)
    expense_by_category = dict(sorted(expense_by_category.items(), key=lambda item: item[1], reverse=True))
    return (*summary, expense_by_category)

async def get_daily_summary(telegram_id: int, target_date: date):
    return await get_summary_with_category(telegram_id, target_date, target_date)

async def get_weekly_summary(telegram_id: int, end_date: date):
    start_date = end_date - timedelta(days=7)
    return await get_summary_with_category(telegram_id, start_date, end_date)

async def get_monthly_summary(telegram_id: int, year: int, month: int):
    start_date = date(year, month, 1)
    _, last_day = calendar.monthrange(year, month)
    end_date = date(year, month, last_day)
    return await get_summary_with_category(telegram_id, start_date, end_date)


def _totals_by_category(transactions, tx_type: TransactionType) -> dict:
    totals: dict = {}
    for tx in transactions:
        if tx.type != tx_type:
            continue
        name = tx.category.name if tx.category else "Lainnya"
        totals[name] = totals.get(name, 0) + float(tx.amount)
    return dict(sorted(totals.items(), key=lambda item: item[1], reverse=True))


async def get_monthly_export(telegram_id: int, year: int, month: int) -> dict | None:
    """Bangun dict laporan bulanan siap-serialisasi JSON.

    Mengembalikan None bila user tidak ditemukan.
    """
    start_date = date(year, month, 1)
    _, last_day = calendar.monthrange(year, month)
    end_date = date(year, month, last_day)

    async with AsyncSessionLocal() as session:
        stmt_user = select(User).where(User.telegram_id == telegram_id)
        user = (await session.execute(stmt_user)).scalar_one_or_none()
        if not user:
            return None
        timezone_name = user.timezone

        stmt_tx = select(Transaction).options(
            joinedload(Transaction.category),
            joinedload(Transaction.wallet),
        ).where(
            Transaction.user_id == user.id
        ).order_by(Transaction.created_at.desc())
        rows = (await session.execute(stmt_tx)).scalars().all()

    transactions = []
    for tx in rows:
        local_created = to_local_datetime(tx.created_at, timezone_name)
        if not (start_date <= local_created.date() <= end_date):
            continue
        transactions.append({
            "id": str(tx.id),
            "date": local_created.date().isoformat(),
            "datetime": local_created.isoformat(),
            "type": tx.type.value if hasattr(tx.type, "value") else str(tx.type),
            "amount": float(tx.amount),
            "description": tx.description,
            "category": tx.category.name if tx.category else "Lainnya",
            "wallet": tx.wallet.name if tx.wallet else None,
        })

    # transactions sudah terurut terbaru-dulu mengikuti created_at desc.
    total_income = sum(t["amount"] for t in transactions if t["type"] == "INCOME")
    total_expense = sum(t["amount"] for t in transactions if t["type"] == "EXPENSE")

    def _by_category(tx_type: str) -> dict:
        totals: dict = {}
        for t in transactions:
            if t["type"] != tx_type:
                continue
            totals[t["category"]] = totals.get(t["category"], 0) + t["amount"]
        return dict(sorted(totals.items(), key=lambda item: item[1], reverse=True))

    generated_at = local_now(timezone_name)
    return {
        "meta": {
            "year": year,
            "month": month,
            "period": f"{year}-{month:02d}",
            "timezone": timezone_name,
            "generated_at": generated_at.isoformat(),
            "transaction_count": len(transactions),
        },
        "summary": {
            "total_income": total_income,
            "total_expense": total_expense,
            "balance": total_income - total_expense,
        },
        "expense_by_category": _by_category("EXPENSE"),
        "income_by_category": _by_category("INCOME"),
        "transactions": transactions,
    }
