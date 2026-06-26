import calendar
from datetime import date, timedelta
from typing import Tuple, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.models import User, Transaction, TransactionType

async def _get_user_transactions(session: AsyncSession, telegram_id: int, start_date: date, end_date: date):
    stmt_user = select(User).where(User.telegram_id == telegram_id)
    user = (await session.execute(stmt_user)).scalar_one_or_none()
    if not user:
        return None
    
    stmt_tx = select(Transaction).where(
        Transaction.user_id == user.id,
        Transaction.date >= start_date,
        Transaction.date <= end_date
    ).order_by(Transaction.date.desc())
    
    transactions = (await session.execute(stmt_tx)).scalars().all()
    return transactions

async def get_summary_by_date_range(telegram_id: int, start_date: date, end_date: date) -> Tuple[Optional[List[Transaction]], float, float]:
    async with AsyncSessionLocal() as session:
        transactions = await _get_user_transactions(session, telegram_id, start_date, end_date)
        if transactions is None:
            return None, 0, 0
        
        total_income = sum(tx.amount for tx in transactions if tx.type == TransactionType.INCOME)
        total_expense = sum(tx.amount for tx in transactions if tx.type == TransactionType.EXPENSE)
        
        return list(transactions), float(total_income), float(total_expense)

async def get_daily_summary(telegram_id: int, target_date: date):
    return await get_summary_by_date_range(telegram_id, target_date, target_date)

async def get_weekly_summary(telegram_id: int, end_date: date):
    start_date = end_date - timedelta(days=7)
    return await get_summary_by_date_range(telegram_id, start_date, end_date)

async def get_monthly_summary(telegram_id: int, year: int, month: int):
    start_date = date(year, month, 1)
    _, last_day = calendar.monthrange(year, month)
    end_date = date(year, month, last_day)
    return await get_summary_by_date_range(telegram_id, start_date, end_date)
