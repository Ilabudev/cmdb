import uuid
from enum import StrEnum

from sqlalchemy import Boolean, Enum, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleted, Timestamped


class CIStatus(StrEnum):
    PLANNED = "planned"
    ACTIVE = "active"
    MAINTENANCE = "maintenance"
    DECOMMISSIONED = "decommissioned"


class CIType(Base, Timestamped):
    __tablename__ = "ci_types"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    icon: Mapped[str | None] = mapped_column(String(64))
    # JSON Schema атрибутов CI этого типа
    attribute_schema: Mapped[dict] = mapped_column(
        JSONB, server_default=text("""'{"type": "object", "properties": {}}'::jsonb""")
    )
    is_system: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))


class CI(Base, Timestamped, SoftDeleted):
    __tablename__ = "cis"
    __table_args__ = (
        # Имя уникально в рамках типа среди неудалённых CI
        Index(
            "uq_cis_type_name_alive",
            "type_id",
            "name",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_cis_attributes", "attributes", postgresql_using="gin"),
        Index("ix_cis_tags", "tags", postgresql_using="gin"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type_id: Mapped[int] = mapped_column(ForeignKey("ci_types.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    status: Mapped[CIStatus] = mapped_column(
        Enum(CIStatus, name="ci_status", values_callable=lambda e: [m.value for m in e]),
        default=CIStatus.ACTIVE,
        index=True,
    )
    owner: Mapped[str | None] = mapped_column(String(255), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String(64)), server_default=text("'{}'"))
    attributes: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))

    type: Mapped[CIType] = relationship(lazy="joined")
