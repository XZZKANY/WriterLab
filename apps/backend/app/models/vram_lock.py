import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class VRAMLock(Base):
    __tablename__ = "vram_locks"
    __table_args__ = (UniqueConstraint("resource_key", name="uq_vram_locks_resource_key"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resource_key: Mapped[str] = mapped_column(String(100), nullable=False)
    lock_owner: Mapped[str] = mapped_column(String(100), nullable=False)
    lock_reason: Mapped[str] = mapped_column(String(200), nullable=False)
    acquired_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    ttl_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
