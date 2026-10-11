from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (Index("ix_audit_entity", "entity", "entity_id", "at"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    entity: Mapped[str] = mapped_column(String(32))  # ci | relation | ci_type | relation_type
    entity_id: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(16))  # create | update | delete | restore
    # {"field": {"old": ..., "new": ...}}
    changes: Mapped[dict] = mapped_column(JSONB, default=dict)
    actor: Mapped[str] = mapped_column(String(255), index=True)
    source: Mapped[str] = mapped_column(String(16))  # ui | api | import
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
