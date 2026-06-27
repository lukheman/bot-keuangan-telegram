import decimal
from datetime import date
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.models import User, Category, Transaction, TransactionType, Wallet
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

async def get_or_create_wallet(session: AsyncSession, user_id, wallet_name: str = None) -> Wallet:
    if wallet_name:
        stmt = select(Wallet).where(
            Wallet.user_id == user_id,
            Wallet.name.ilike(wallet_name)
        )
        wallet = (await session.execute(stmt)).scalar_one_or_none()
        
        if not wallet:
            wallet = Wallet(
                user_id=user_id,
                name=wallet_name,
                balance=decimal.Decimal(0.0),
                is_primary=False
            )
            session.add(wallet)
            await session.flush()
        return wallet
    else:
        # Default to primary wallet
        stmt = select(Wallet).where(
            Wallet.user_id == user_id,
            Wallet.is_primary == True
        )
        wallet = (await session.execute(stmt)).scalar_one_or_none()
        
        if not wallet:
            # Fallback to the first wallet if no primary is set
            stmt = select(Wallet).where(Wallet.user_id == user_id).order_by(Wallet.created_at)
            wallet = (await session.execute(stmt)).scalar_one_or_none()
            
        if not wallet:
            # If completely empty, create "Utama" and make it primary
            wallet = Wallet(
                user_id=user_id,
                name="Utama",
                balance=decimal.Decimal(0.0),
                is_primary=True
            )
            session.add(wallet)
            await session.flush()
            
        return wallet

async def record_transaction(telegram_user, amount: decimal.Decimal, description: str, tx_type: TransactionType, category_name: str = None, wallet_name: str = None) -> Transaction:
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(
            session, 
            telegram_user.id, 
            telegram_user.username, 
            telegram_user.full_name
        )
        category = await get_or_create_category(session, user.id, tx_type, category_name)
        wallet = await get_or_create_wallet(session, user.id, wallet_name)
        
        # Update balance dompet
        if tx_type == TransactionType.INCOME:
            wallet.balance += amount
        else:
            wallet.balance -= amount

        new_tx = Transaction(
            user_id=user.id,
            category_id=category.id,
            wallet_id=wallet.id,
            amount=amount,
            type=tx_type,
            description=description,
            date=date.today()
        )
        session.add(new_tx)
        await session.commit()
        await session.refresh(new_tx)
        new_tx.category_name = category.name
        new_tx.wallet_name = wallet.name
        logger.debug(f"Transaksi tersimpan di database: id={new_tx.id}, wallet={wallet.name}")
        return new_tx
