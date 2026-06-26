import decimal
from datetime import date
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.models import User, Category, Transaction, TransactionType
import logging

logger = logging.getLogger(__name__)

async def get_or_create_user(session: AsyncSession, telegram_id: int, username: str, full_name: str) -> User:
    stmt = select(User).where(User.telegram_id == telegram_id)
    user = (await session.execute(stmt)).scalar_one_or_none()
    
    if not user:
        user = User(
            telegram_id=telegram_id,
            username=username,
            full_name=full_name or "Unknown"
        )
        session.add(user)
        await session.flush()
    return user

async def get_or_create_category(session: AsyncSession, user_id, type_: TransactionType, category_name: str = None) -> Category:
    name = category_name or ("Pemasukan Umum" if type_ == TransactionType.INCOME else "Pengeluaran Umum")
    stmt = select(Category).where(
        Category.user_id == user_id, 
        Category.name == name,
        Category.type == type_
    )
    category = (await session.execute(stmt)).scalar_one_or_none()
    
    if not category:
        category = Category(
            user_id=user_id,
            name=name,
            type=type_,
            is_default=(category_name is None)
        )
        session.add(category)
        await session.flush()
    return category

async def record_transaction(telegram_user, amount: decimal.Decimal, description: str, tx_type: TransactionType, category_name: str = None) -> Transaction:
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(
            session, 
            telegram_user.id, 
            telegram_user.username, 
            telegram_user.full_name
        )
        category = await get_or_create_category(session, user.id, tx_type, category_name)
        
        new_tx = Transaction(
            user_id=user.id,
            category_id=category.id,
            amount=amount,
            type=tx_type,
            description=description,
            date=date.today()
        )
        session.add(new_tx)
        await session.commit()
        await session.refresh(new_tx)
        new_tx.category_name = category.name
        logger.debug(f"Transaksi tersimpan di database: id={new_tx.id}")
        return new_tx
