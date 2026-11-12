import uuid
from sqlalchemy import BigInteger, JSON, String
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import BaseModel


class UxEvent(BaseModel):
    """Event funnel/error untuk analisis UX.

    Sengaja tidak menyimpan isi pesan pengguna. Hanya telegram_id, nama event,
    dan metadata kecil (mis. jenis transaksi atau tipe error).
    """

    __tablename__ = "ux_events"

    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    event: Mapped[str] = mapped_column(String(50), index=True)
    data: Mapped[dict] = mapped_column(JSON, default=dict)

    def __repr__(self) -> str:
        return f"<UxEvent(telegram_id={self.telegram_id}, event='{self.event}')>"
