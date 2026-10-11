from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditEvent


def diff(old: dict[str, Any], new: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Поле-за-полем: {"field": {"old": ..., "new": ...}} только для изменившихся полей."""
    keys = old.keys() | new.keys()
    return {
        k: {"old": old.get(k), "new": new.get(k)} for k in sorted(keys) if old.get(k) != new.get(k)
    }


def record(
    session: AsyncSession,
    *,
    entity: str,
    entity_id: object,
    action: str,
    actor: str,
    changes: dict | None = None,
    source: str = "api",
) -> None:
    """Добавляет событие в текущую транзакцию — коммитится вместе с изменением."""
    session.add(
        AuditEvent(
            entity=entity,
            entity_id=str(entity_id),
            action=action,
            changes=changes or {},
            actor=actor,
            source=source,
        )
    )
