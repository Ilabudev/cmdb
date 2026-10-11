import uuid

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleted, Timestamped


class RelationType(Base, Timestamped):
    __tablename__ = "relation_types"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(255))  # «работает на»
    reverse_name: Mapped[str] = mapped_column(String(255))  # «хостит»
    # [{"source": "vm", "target": "hypervisor"}, ...]; пустой список — любые пары
    allowed_pairs: Mapped[list[dict]] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    propagates_impact: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    is_system: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))


class Relation(Base, Timestamped, SoftDeleted):
    """Направленная связь: source зависит от target."""

    __tablename__ = "relations"
    __table_args__ = (
        CheckConstraint("source_id <> target_id", name="no_self_link"),
        Index(
            "uq_relations_alive",
            "type_id",
            "source_id",
            "target_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type_id: Mapped[int] = mapped_column(ForeignKey("relation_types.id"))
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cis.id"), index=True)
    target_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cis.id"), index=True)
    description: Mapped[str | None] = mapped_column(Text)
