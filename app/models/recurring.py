import uuid
import enum
from datetime import date
from typing import Optional
from decimal import Decimal
from sqlalchemy import ForeignKey, String, Numeric, Enum, Date, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel
from app.models.category import TransactionType

class Period(str, enum.Enum):
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    YEARLY = "YEARLY"

class RecurringTransaction(BaseModel):
    __tablename__ = "recurring_transactions"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    category_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("categories.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    type: Mapped[TransactionType] = mapped_column(Enum(TransactionType))
    frequency: Mapped[Period] = mapped_column(Enum(Period))  # Memakai enum Period yang sama
    next_run_date: Mapped[date] = mapped_column(Date, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="recurring_transactions")
    category: Mapped["Category"] = relationship("Category", back_populates="recurring_transactions")

    def __repr__(self) -> str:
        return f"<RecurringTransaction(id={self.id}, amount={self.amount}, frequency={self.frequency})>"
