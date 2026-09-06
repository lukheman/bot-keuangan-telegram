import uuid
from decimal import Decimal
from sqlalchemy import ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel


class Budget(BaseModel):
    """Anggaran bulanan per kategori. Berlaku setiap bulan kalender."""

    __tablename__ = "budgets"
    __table_args__ = (
        UniqueConstraint("user_id", "category_id", name="uq_budgets_user_id_category_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    category_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("categories.id"), index=True)
    amount_limit: Mapped[Decimal] = mapped_column(Numeric(15, 2))

    # Relationships (satu arah agar tidak perlu mengubah model User/Category)
    user: Mapped["User"] = relationship("User")
    category: Mapped["Category"] = relationship("Category")

    def __repr__(self) -> str:
        return f"<Budget(user_id={self.user_id}, category_id={self.category_id}, limit={self.amount_limit})>"
