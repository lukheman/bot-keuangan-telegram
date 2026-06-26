import enum
import uuid
from datetime import date
from typing import Optional
from decimal import Decimal
from sqlalchemy import ForeignKey, String, Numeric, Enum, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel

class Period(str, enum.Enum):
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    YEARLY = "YEARLY"

class Budget(BaseModel):
    __tablename__ = "budgets"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("categories.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    amount_limit: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    period: Mapped[Period] = mapped_column(Enum(Period))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="budgets")
    category: Mapped[Optional["Category"]] = relationship("Category", back_populates="budgets")

    def __repr__(self) -> str:
        return f"<Budget(id={self.id}, name='{self.name}', amount_limit={self.amount_limit})>"
