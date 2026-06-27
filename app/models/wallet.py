import uuid
from typing import List, Optional
from decimal import Decimal
from sqlalchemy import ForeignKey, String, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel

class Wallet(BaseModel):
    __tablename__ = "wallets"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(50))
    balance: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0.0)
    is_primary: Mapped[bool] = mapped_column(default=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="wallets")
    transactions: Mapped[List["Transaction"]] = relationship("Transaction", back_populates="wallet")

    def __repr__(self) -> str:
        return f"<Wallet(id={self.id}, name={self.name}, balance={self.balance})>"
