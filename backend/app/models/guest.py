from datetime import date

from sqlalchemy import Date, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class GuestUsage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "guest_usage"
    __table_args__ = (UniqueConstraint("guest_id", "usage_date", name="uq_guest_usage_date"),)

    guest_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    ip_address: Mapped[str | None] = mapped_column(String(80), index=True)
    usage_date: Mapped[date] = mapped_column(Date, nullable=False)
    question_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

