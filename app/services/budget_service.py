"""Layanan anggaran (budget) bulanan per kategori.

Budget bersifat persisten: satu batas per kategori yang dievaluasi ulang
setiap bulan kalender. Setiap ada pengeluaran baru, pemakaian bulan berjalan
dibandingkan dengan batas dan peringatan dikirim saat melewati 80%, 100%,
atau melebihi budget.
"""

import calendar
import decimal
import logging
import re
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.timezone import local_now
from app.models import Budget, Category, Transaction, TransactionType, User

logger = logging.getLogger(__name__)

WARN_80_PCT = 80.0
WARN_100_PCT = 100.0

# Kategori pengeluaran kanonis (selaras dengan prompt ekstraksi AI).
EXPENSE_CATEGORIES = [
    "Makanan", "Transportasi", "Bensin", "Buku", "Kebersihan", "Kesehatan",
    "Hiburan", "Perawatan", "Freelance", "Kerja", "Pendidikan", "ATK",
    "Lainnya", "Transfer", "Biaya Admin",
]

_NOMINAL_RE = re.compile(
    r"^\s*(?P<num>\d[\d\.,]*)\s*(?P<unit>ribu|rb|juta|jt|k)?\s*$",
    re.IGNORECASE,
)


def parse_budget_nominal(text: str) -> decimal.Decimal:
    """Parse nominal budget: '1jt', '500rb', '500 ribu', '20k', '1,5jt', '500.000'."""
    if not text:
        raise ValueError("Nominal budget tidak boleh kosong.")
    match = _NOMINAL_RE.match(text.strip())
    if not match:
        raise ValueError(
            f"Nominal '{text}' tidak valid. Contoh: 1jt, 500rb, 20k, 500000."
        )
    num_str, unit = match.group("num"), (match.group("unit") or "").lower()
    if unit in ("rb", "ribu", "k"):
        value = float(num_str.replace(",", ".")) * 1_000
    elif unit in ("jt", "juta"):
        value = float(num_str.replace(",", ".")) * 1_000_000
    else:
        # Tanpa satuan, titik/koma dianggap pemisah ribuan.
        value = float(num_str.replace(".", "").replace(",", ""))
    if value <= 0:
        raise ValueError("Nominal budget harus lebih besar dari nol.")
    return decimal.Decimal(int(round(value)))


def _current_month_range(timezone_name: str | None) -> tuple[date, date]:
    today = local_now(timezone_name).date()
    _, last_day = calendar.monthrange(today.year, today.month)
    return date(today.year, today.month, 1), date(today.year, today.month, last_day)


async def _find_existing_category(
    session: AsyncSession, user_id, candidate: str
) -> Category | None:
    """Cari kategori EXPENSE milik user tanpa membuat baru."""
    candidate_clean = (candidate or "").strip()
    if not candidate_clean:
        return None
    lowered = candidate_clean.lower()
    categories = (
        await session.execute(
            select(Category).where(
                Category.user_id == user_id,
                Category.type == TransactionType.EXPENSE,
            )
        )
    ).scalars().all()
    for category in categories:
        if category.name.lower() == lowered:
            return category
    for category in categories:
        if lowered in category.name.lower():
            return category
    for category in categories:
        if category.name.lower() in lowered:
            return category
    return None


async def resolve_budget_category(
    session: AsyncSession, user_id, candidate: str
) -> Category:
    """Cari kategori budget; buat baru bila namanya kanonis, error bila tidak dikenal."""
    found = await _find_existing_category(session, user_id, candidate)
    if found:
        return found
    lowered = (candidate or "").strip().lower()
    for canonical in EXPENSE_CATEGORIES:
        if canonical.lower() == lowered:
            category = Category(
                user_id=user_id,
                name=canonical,
                type=TransactionType.EXPENSE,
                is_default=False,
            )
            session.add(category)
            await session.flush()
            return category
    available = ", ".join(EXPENSE_CATEGORIES)
    raise ValueError(
        f"Kategori '{candidate}' tidak ditemukan. Pilih: {available}."
    )


async def get_month_spending(
    session: AsyncSession, user_id, category_id, year: int, month: int
) -> decimal.Decimal:
    _, last_day = calendar.monthrange(year, month)
    total = (
        await session.execute(
            select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                Transaction.user_id == user_id,
                Transaction.category_id == category_id,
                Transaction.type == TransactionType.EXPENSE,
                Transaction.date >= date(year, month, 1),
                Transaction.date <= date(year, month, last_day),
            )
        )
    ).scalar_one()
    return decimal.Decimal(total)


async def set_budget(
    telegram_id: int, category_name: str, amount: decimal.Decimal
) -> tuple[Budget, Category, bool]:
    """Buat/ubah budget kategori. Mengembalikan (budget, category, is_baru)."""
    if amount <= 0:
        raise ValueError("Nominal budget harus lebih besar dari nol.")
    async with AsyncSessionLocal() as session:
        user = (
            await session.execute(select(User).where(User.telegram_id == telegram_id))
        ).scalar_one_or_none()
        if not user:
            raise ValueError("Akun tidak ditemukan. Kirim /start terlebih dahulu.")
        category = await resolve_budget_category(session, user.id, category_name)
        budget = (
            await session.execute(
                select(Budget).where(
                    Budget.user_id == user.id,
                    Budget.category_id == category.id,
                )
            )
        ).scalar_one_or_none()
        is_new = budget is None
        if is_new:
            budget = Budget(
                user_id=user.id, category_id=category.id, amount_limit=amount
            )
            session.add(budget)
        else:
            budget.amount_limit = amount
        await session.commit()
        await session.refresh(budget)
        logger.info(
            f"Budget diset: user={telegram_id}, kategori={category.name}, limit=Rp{amount}"
        )
        return budget, category, is_new


async def delete_budget(telegram_id: int, category_name: str) -> str:
    """Hapus budget kategori. Mengembalikan nama kategori yang dihapus."""
    async with AsyncSessionLocal() as session:
        user = (
            await session.execute(select(User).where(User.telegram_id == telegram_id))
        ).scalar_one_or_none()
        if not user:
            raise ValueError("Akun tidak ditemukan. Kirim /start terlebih dahulu.")
        category = await _find_existing_category(session, user.id, category_name)
        budget = None
        if category:
            budget = (
                await session.execute(
                    select(Budget).where(
                        Budget.user_id == user.id,
                        Budget.category_id == category.id,
                    )
                )
            ).scalar_one_or_none()
        if not budget:
            raise ValueError(
                f"Tidak ada budget untuk kategori '{category_name}'."
            )
        category_name_resolved = category.name
        await session.delete(budget)
        await session.commit()
        logger.info(f"Budget dihapus: user={telegram_id}, kategori={category_name_resolved}")
        return category_name_resolved


async def list_budgets_with_usage(telegram_id: int) -> tuple[list[dict], str]:
    """Daftar semua budget user beserta pemakaian bulan berjalan."""
    async with AsyncSessionLocal() as session:
        user = (
            await session.execute(select(User).where(User.telegram_id == telegram_id))
        ).scalar_one_or_none()
        if not user:
            return [], ""
        today = local_now(user.timezone).date()
        budgets = (
            await session.execute(
                select(Budget, Category)
                .join(Category, Budget.category_id == Category.id)
                .where(Budget.user_id == user.id)
                .order_by(Category.name)
            )
        ).all()
        result = []
        for budget, category in budgets:
            spent = await get_month_spending(
                session, user.id, category.id, today.year, today.month
            )
            limit = decimal.Decimal(budget.amount_limit)
            pct = float(spent / limit * 100) if limit > 0 else 0.0
            result.append(
                {
                    "category_name": category.name,
                    "limit": limit,
                    "spent": spent,
                    "pct": pct,
                }
            )
        return result, today.strftime("%b %Y")


async def get_budget_warning(
    session: AsyncSession,
    user: User,
    category: Category,
    tx_amount: decimal.Decimal,
) -> str | None:
    """Hitung status budget sesudah transaksi dicatat. Kembalikan teks peringatan atau None.

    Harus dipanggil setelah transaksi ter-commit dalam session yang sama agar
    total pemakaian sudah mencakup transaksi terbaru.
    """
    if category.type != TransactionType.EXPENSE:
        return None
    budget = (
        await session.execute(
            select(Budget).where(
                Budget.user_id == user.id,
                Budget.category_id == category.id,
            )
        )
    ).scalar_one_or_none()
    if not budget:
        return None

    today = local_now(user.timezone).date()
    spent = await get_month_spending(
        session, user.id, category.id, today.year, today.month
    )
    limit = decimal.Decimal(budget.amount_limit)
    if limit <= 0:
        return None
    before = spent - decimal.Decimal(tx_amount)
    pct_after = float(spent / limit * 100)
    pct_before = float(before / limit * 100)

    spent_fmt = f"Rp{spent:,.0f}"
    limit_fmt = f"Rp{limit:,.0f}"
    if pct_after > WARN_100_PCT:
        over = spent - limit
        return (
            f"🚨 *Budget {category.name} terlampaui!*\n"
            f"Terpakai {spent_fmt} dari {limit_fmt} "
            f"(+Rp{over:,.0f} melebihi budget)."
        )
    if pct_after >= WARN_100_PCT and pct_before < WARN_100_PCT:
        return (
            f"⛔ *Budget {category.name} habis (100% terpakai)!*\n"
            f"Terpakai {spent_fmt} dari {limit_fmt} bulan ini."
        )
    if pct_after >= WARN_80_PCT and pct_before < WARN_80_PCT:
        return (
            f"⚠️ *Budget {category.name} {pct_after:.0f}% terpakai.*\n"
            f"Terpakai {spent_fmt} dari {limit_fmt} bulan ini."
        )
    return None
