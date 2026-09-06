import decimal
from app.core.timezone import local_now
from app.services.budget_service import get_budget_warning
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.models import User, Category, Transaction, TransactionType, Wallet
import logging

logger = logging.getLogger(__name__)

async def get_primary_wallet_name(telegram_id: int) -> str:
    async with AsyncSessionLocal() as session:
        stmt = select(User).where(User.telegram_id == telegram_id)
        user = (await session.execute(stmt)).scalar_one_or_none()
        if not user:
            return "Utama"
            
        stmt = select(Wallet).where(Wallet.user_id == user.id, Wallet.is_primary == True)
        wallet = (await session.execute(stmt)).scalars().first()
        
        if not wallet:
            stmt = select(Wallet).where(Wallet.user_id == user.id).order_by(Wallet.created_at)
            wallet = (await session.execute(stmt)).scalars().first()
            
        return wallet.name if wallet else "Utama"

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
    category = (await session.execute(stmt)).scalars().first()
    
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

async def get_wallet_or_default(session: AsyncSession, user_id, wallet_name: str = None) -> Wallet:
    if wallet_name:
        stmt = select(Wallet).where(
            Wallet.user_id == user_id,
            Wallet.name.ilike(wallet_name)
        )
        wallet = (await session.execute(stmt)).scalars().first()
        
        if not wallet:
            raise ValueError(f"Dompet '{wallet_name}' tidak ditemukan. Silakan buat dompet terlebih dahulu melalui menu dompet.")
            
        return wallet
    else:
        # Default to primary wallet
        stmt = select(Wallet).where(
            Wallet.user_id == user_id,
            Wallet.is_primary == True
        )
        wallet = (await session.execute(stmt)).scalars().first()
        
        if not wallet:
            # Fallback to the first wallet if no primary is set
            stmt = select(Wallet).where(Wallet.user_id == user_id).order_by(Wallet.created_at)
            wallet = (await session.execute(stmt)).scalars().first()
            
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

async def find_wallet_by_name(session: AsyncSession, user_id, candidate: str) -> Wallet | None:
    """Cari dompet milik user dengan pencocokan longgar (case-insensitive).

    Urutan: cocok persis -> mengandung -> terkandung. Mengembalikan None bila
    tidak ada yang cocok agar pemanggil bisa menampilkan daftar dompet.
    """
    if not candidate:
        return None
    candidate_clean = candidate.strip()
    if not candidate_clean:
        return None

    stmt = select(Wallet).where(Wallet.user_id == user_id)
    wallets = (await session.execute(stmt)).scalars().all()
    if not wallets:
        return None

    lowered = candidate_clean.lower()
    for wallet in wallets:
        if wallet.name.lower() == lowered:
            return wallet
    for wallet in wallets:
        if lowered in wallet.name.lower():
            return wallet
    for wallet in wallets:
        if wallet.name.lower() in lowered:
            return wallet
    return None


async def record_transfer(
    telegram_user,
    amount: decimal.Decimal,
    source_wallet_name: str,
    dest_wallet_name: str,
    fee: decimal.Decimal = decimal.Decimal(0),
    description: str | None = None,
) -> dict:
    """Catat transfer antar dompet milik user yang sama.

    - Dompet asal berkurang sebesar amount + fee.
    - Dompet tujuan bertambah sebesar amount.
    - Dicatat sebagai 2 transaksi (keluar + masuk) dan 1 transaksi biaya
      admin bila fee > 0, dalam satu commit database.
    """
    amount = decimal.Decimal(amount)
    fee = decimal.Decimal(fee or 0)
    if amount <= 0:
        raise ValueError("Jumlah transfer harus lebih besar dari nol.")
    if fee < 0:
        raise ValueError("Biaya admin tidak boleh negatif.")
    if not source_wallet_name or not dest_wallet_name:
        raise ValueError("Dompet asal dan tujuan harus disebutkan.")
    if source_wallet_name.strip().lower() == dest_wallet_name.strip().lower():
        raise ValueError("Dompet asal dan tujuan tidak boleh sama.")

    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(
            session,
            telegram_user.id,
            telegram_user.username,
            telegram_user.full_name,
        )
        source_wallet = await find_wallet_by_name(session, user.id, source_wallet_name)
        dest_wallet = await find_wallet_by_name(session, user.id, dest_wallet_name)
        if not source_wallet or not dest_wallet:
            available = ", ".join(
                w.name for w in (await session.execute(
                    select(Wallet).where(Wallet.user_id == user.id)
                )).scalars().all()
            ) or "-"
            missing = source_wallet_name if not source_wallet else dest_wallet_name
            raise ValueError(
                f"Dompet '{missing}' tidak ditemukan. Dompet tersedia: {available}."
            )

        if source_wallet.id == dest_wallet.id:
            raise ValueError("Dompet asal dan tujuan tidak boleh sama.")

        local_time = local_now(user.timezone)
        desc = (description or f"Transfer {source_wallet.name} ke {dest_wallet.name}").strip()

        transfer_out_cat = await get_or_create_category(session, user.id, TransactionType.EXPENSE, "Transfer")
        transfer_in_cat = await get_or_create_category(session, user.id, TransactionType.INCOME, "Transfer")

        source_wallet.balance -= amount + fee
        dest_wallet.balance += amount

        out_tx = Transaction(
            user_id=user.id,
            category_id=transfer_out_cat.id,
            wallet_id=source_wallet.id,
            amount=amount,
            type=TransactionType.EXPENSE,
            description=desc,
            date=local_time.date(),
        )
        in_tx = Transaction(
            user_id=user.id,
            category_id=transfer_in_cat.id,
            wallet_id=dest_wallet.id,
            amount=amount,
            type=TransactionType.INCOME,
            description=desc,
            date=local_time.date(),
        )
        session.add(out_tx)
        session.add(in_tx)

        fee_tx = None
        if fee > 0:
            fee_cat = await get_or_create_category(session, user.id, TransactionType.EXPENSE, "Biaya Admin")
            fee_tx = Transaction(
                user_id=user.id,
                category_id=fee_cat.id,
                wallet_id=source_wallet.id,
                amount=fee,
                type=TransactionType.EXPENSE,
                description=f"Biaya admin transfer ke {dest_wallet.name}",
                date=local_time.date(),
            )
            session.add(fee_tx)

        await session.commit()
        for tx, cat, wallet in (
            (out_tx, transfer_out_cat, source_wallet),
            (in_tx, transfer_in_cat, dest_wallet),
        ):
            await session.refresh(tx)
            tx.category_name = cat.name
            tx.wallet_name = wallet.name
            tx.local_created_at = local_time
        if fee_tx is not None:
            await session.refresh(fee_tx)
            await session.refresh(source_wallet)
            await session.refresh(dest_wallet)
            fee_tx.category_name = "Biaya Admin"
            fee_tx.wallet_name = source_wallet.name
            fee_tx.local_created_at = local_time
        else:
            await session.refresh(source_wallet)
            await session.refresh(dest_wallet)

        logger.debug(
            f"Transfer tersimpan: {source_wallet.name} -> {dest_wallet.name} "
            f"Rp{amount} (admin Rp{fee})"
        )
        return {
            "amount": amount,
            "fee": fee,
            "description": desc,
            "source_wallet": source_wallet,
            "dest_wallet": dest_wallet,
            "out_tx": out_tx,
            "in_tx": in_tx,
            "fee_tx": fee_tx,
            "local_created_at": local_time,
        }


async def record_transaction(telegram_user, amount: decimal.Decimal, description: str, tx_type: TransactionType, category_name: str = None, wallet_name: str = None) -> Transaction:
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(
            session, 
            telegram_user.id, 
            telegram_user.username, 
            telegram_user.full_name
        )
        category = await get_or_create_category(session, user.id, tx_type, category_name)
        wallet = await get_wallet_or_default(session, user.id, wallet_name)
        
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
            date=local_now(user.timezone).date()
        )
        session.add(new_tx)
        await session.commit()
        await session.refresh(new_tx)
        new_tx.category_name = category.name
        new_tx.wallet_name = wallet.name
        new_tx.local_created_at = local_now(user.timezone)
        new_tx.budget_warning = await get_budget_warning(
            session, user, category, new_tx.amount
        )
        logger.debug(f"Transaksi tersimpan di database: id={new_tx.id}, wallet={wallet.name}")
        return new_tx

async def adjust_wallet_balance(telegram_user, target_balance: decimal.Decimal, wallet_name: str = None) -> Transaction | None:
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, telegram_user.id, telegram_user.username, telegram_user.full_name)
        
        if wallet_name:
            stmt = select(Wallet).where(Wallet.user_id == user.id, Wallet.name.ilike(wallet_name))
            wallet = (await session.execute(stmt)).scalars().first()
            if not wallet:
                raise ValueError(f"Dompet '{wallet_name}' tidak ditemukan. Silakan buat dompet terlebih dahulu atau cek ejaannya.")
        else:
            stmt = select(Wallet).where(Wallet.user_id == user.id, Wallet.is_primary == True)
            wallet = (await session.execute(stmt)).scalars().first()
            if not wallet:
                stmt = select(Wallet).where(Wallet.user_id == user.id).order_by(Wallet.created_at)
                wallet = (await session.execute(stmt)).scalars().first()
            if not wallet:
                raise ValueError("Anda belum memiliki dompet sama sekali.")
        
        diff = target_balance - wallet.balance
        if diff == 0:
            return None
            
        tx_type = TransactionType.INCOME if diff > 0 else TransactionType.EXPENSE
        amount = abs(diff)
        
        # We only need the wallet name to pass to record_transaction
        resolved_wallet_name = wallet.name

    # Use existing function to record and apply the difference
    return await record_transaction(
        telegram_user=telegram_user,
        amount=amount,
        description="Penyesuaian Saldo Otomatis",
        tx_type=tx_type,
        category_name="Penyesuaian Saldo",
        wallet_name=resolved_wallet_name
    )
