from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import Role, User, require
from app.models import AuditEvent
from app.schemas import AuditEventOut

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=list[AuditEventOut])
async def list_events(
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require(Role.VIEWER)),
    entity: str | None = None,
    entity_id: str | None = None,
    actor: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    stmt = select(AuditEvent)
    if entity:
        stmt = stmt.where(AuditEvent.entity == entity)
    if entity_id:
        stmt = stmt.where(AuditEvent.entity_id == entity_id)
    if actor:
        stmt = stmt.where(AuditEvent.actor == actor)
    if since:
        stmt = stmt.where(AuditEvent.at >= since)
    if until:
        stmt = stmt.where(AuditEvent.at < until)
    stmt = stmt.order_by(AuditEvent.at.desc(), AuditEvent.id.desc()).limit(limit).offset(offset)
    return (await session.scalars(stmt)).all()
