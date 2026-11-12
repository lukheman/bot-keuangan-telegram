import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel


class PendingTransaction(BaseModel):
    """Transaksi yang menunggu konfirmasi/pilihan dompet.

    Disimpan di database agar tombol tetap berfungsi setelah bot restart
    atau berpindah instance (serverless). Payload berisi data mentah yang
    sudah diserialisasi, bukan objek Telegram.
    """

    __tablename__ = "pending_transactions"

    token: Mapped[str] = mapped_column(String(12), unique=True, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True
    )

    user: Mapped["User"] = relationship("User", back_populates="pending_transactions")

    def __repr__(self) -> str:
        return f"<PendingTransaction(token={self.token}, expires_at={self.expires_at})>"
