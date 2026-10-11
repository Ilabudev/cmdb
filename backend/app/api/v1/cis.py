import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import Role, User, require
from app.models import CI, CIStatus, CIType, Relation
from app.schemas import CIIn, CIOut, CIUpdate, Direction, Graph, Page
from app.services import audit, graph
from app.services.attributes import AttributeValidationError, validate_attributes

router = APIRouter(prefix="/cis", tags=["cis"])

_AUDITED = ("name", "status", "owner", "description", "tags", "attributes")


def _snapshot(ci: CI) -> dict:
    return {k: getattr(ci, k) for k in _AUDITED}


async def _get_alive(session: AsyncSession, ci_id: uuid.UUID) -> CI:
    ci = await session.get(CI, ci_id)
    if ci is None or ci.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    return ci


def _validate(ci_type: CIType, attributes: dict) -> None:
    try:
        validate_attributes(ci_type.attribute_schema, attributes)
    except AttributeValidationError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, {"attributes": exc.errors}) from exc


@router.get("", response_model=Page[CIOut])
async def list_cis(
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require(Role.VIEWER)),
    type_id: int | None = None,
    status_: Annotated[list[CIStatus] | None, Query(alias="status")] = None,
    owner: str | None = None,
    tag: Annotated[list[str] | None, Query()] = None,
    q: str | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    # TODO(FR-2): фильтр по значениям атрибутов, сортировка, полнотекстовый поиск
    stmt = select(CI).where(CI.deleted_at.is_(None))
    if type_id is not None:
        stmt = stmt.where(CI.type_id == type_id)
    if status_:
        stmt = stmt.where(CI.status.in_(status_))
    if owner:
        stmt = stmt.where(CI.owner == owner)
    if tag:
        stmt = stmt.where(CI.tags.contains(tag))
    if q:
        stmt = stmt.where(or_(CI.name.ilike(f"%{q}%"), CI.description.ilike(f"%{q}%")))
    total = await session.scalar(select(func.count()).select_from(stmt.subquery()))
    items = (await session.scalars(stmt.order_by(CI.name).limit(limit).offset(offset))).all()
    return Page(items=items, total=total or 0, limit=limit, offset=offset)


@router.get("/{ci_id}", response_model=CIOut)
async def get_ci(
    ci_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require(Role.VIEWER)),
):
    return await _get_alive(session, ci_id)


@router.post("", response_model=CIOut, status_code=status.HTTP_201_CREATED)
async def create_ci(
    data: CIIn,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require(Role.EDITOR)),
):
    if (ci_type := await session.get(CIType, data.type_id)) is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, {"type_id": "Unknown type"})
    _validate(ci_type, data.attributes)
    ci = CI(**data.model_dump(), created_by=user.username, updated_by=user.username)
    session.add(ci)
    await session.flush()
    audit.record(
        session, entity="ci", entity_id=ci.id, action="create", actor=user.username,
        changes=audit.diff({}, _snapshot(ci)),
    )
    await session.commit()
    return ci


@router.patch("/{ci_id}", response_model=CIOut)
async def update_ci(
    ci_id: uuid.UUID,
    data: CIUpdate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require(Role.EDITOR)),
):
    ci = await _get_alive(session, ci_id)
    patch = data.model_dump(exclude_unset=True)
    if "attributes" in patch:
        _validate(ci.type, patch["attributes"])
    old = _snapshot(ci)
    for k, v in patch.items():
        setattr(ci, k, v)
    ci.updated_by = user.username
    audit.record(
        session, entity="ci", entity_id=ci.id, action="update", actor=user.username,
        changes=audit.diff(old, _snapshot(ci)),
    )
    await session.commit()
    await session.refresh(ci)
    return ci


@router.delete("/{ci_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ci(
    ci_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require(Role.EDITOR)),
):
    ci = await _get_alive(session, ci_id)
    now = datetime.now(UTC)
    ci.deleted_at = now
    ci.updated_by = user.username
    # FR-4: связи удалённого CI тоже помечаются удалёнными
    await session.execute(
        update(Relation)
        .where(Relation.deleted_at.is_(None))
        .where(or_(Relation.source_id == ci_id, Relation.target_id == ci_id))
        .values(deleted_at=now, updated_by=user.username)
    )
    audit.record(session, entity="ci", entity_id=ci.id, action="delete", actor=user.username)
    await session.commit()


@router.get("/{ci_id}/graph", response_model=Graph)
async def ci_graph(
    ci_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require(Role.VIEWER)),
    depth: Annotated[int, Query(ge=1, le=5)] = 2,
    direction: Direction = "both",
):
    await _get_alive(session, ci_id)
    return await graph.neighbourhood(session, ci_id, depth=depth, direction=direction)


@router.get("/{ci_id}/impact", response_model=Graph)
async def ci_impact(
    ci_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require(Role.VIEWER)),
    depth: Annotated[int, Query(ge=1, le=10)] = 10,
):
    """FR-10: всё, что транзитивно зависит от CI."""
    # TODO: вернуть путь до каждого затронутого CI
    await _get_alive(session, ci_id)
    return await graph.neighbourhood(
        session, ci_id, depth=depth, direction="upstream", impact_only=True
    )
