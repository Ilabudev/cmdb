import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import Role, User, require
from app.models import CI, Relation, RelationType
from app.schemas import RelationIn, RelationOut, RelationTypeIn, RelationTypeOut
from app.services import audit

router = APIRouter(tags=["relations"])


@router.get("/relation-types", response_model=list[RelationTypeOut])
async def list_relation_types(
    session: AsyncSession = Depends(get_session), _: User = Depends(require(Role.VIEWER))
):
    return (await session.scalars(select(RelationType).order_by(RelationType.name))).all()


@router.post("/relation-types", response_model=RelationTypeOut, status_code=201)
async def create_relation_type(
    data: RelationTypeIn,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require(Role.ADMIN)),
):
    obj = RelationType(**data.model_dump(), created_by=user.username, updated_by=user.username)
    session.add(obj)
    await session.flush()
    audit.record(
        session, entity="relation_type", entity_id=obj.id, action="create", actor=user.username,
        changes=audit.diff({}, data.model_dump()),
    )
    await session.commit()
    return obj


@router.get("/relations", response_model=list[RelationOut])
async def list_relations(
    ci_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require(Role.VIEWER)),
):
    """Все входящие и исходящие связи CI."""
    stmt = select(Relation).where(
        Relation.deleted_at.is_(None),
        or_(Relation.source_id == ci_id, Relation.target_id == ci_id),
    )
    return (await session.scalars(stmt)).all()


@router.post("/relations", response_model=RelationOut, status_code=201)
async def create_relation(
    data: RelationIn,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require(Role.EDITOR)),
):
    rtype = await session.get(RelationType, data.type_id)
    source = await session.get(CI, data.source_id)
    target = await session.get(CI, data.target_id)
    if rtype is None or source is None or target is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Unknown relation type or CI")
    if source.deleted_at or target.deleted_at:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "CI is deleted")
    if data.source_id == data.target_id:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Self-link is not allowed")
    pair = {"source": source.type.code, "target": target.type.code}
    if rtype.allowed_pairs and pair not in rtype.allowed_pairs:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"{rtype.code} is not allowed between {pair['source']} and {pair['target']}",
        )
    rel = Relation(**data.model_dump(), created_by=user.username, updated_by=user.username)
    session.add(rel)
    try:
        await session.flush()
    except IntegrityError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, "Relation already exists") from exc
    audit.record(
        session, entity="relation", entity_id=rel.id, action="create", actor=user.username,
        changes=audit.diff({}, {k: str(v) for k, v in data.model_dump().items()}),
    )
    await session.commit()
    return rel


@router.delete("/relations/{relation_id}", status_code=204)
async def delete_relation(
    relation_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require(Role.EDITOR)),
):
    rel = await session.get(Relation, relation_id)
    if rel is None or rel.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    rel.deleted_at = datetime.now(UTC)
    rel.updated_by = user.username
    audit.record(session, entity="relation", entity_id=rel.id, action="delete", actor=user.username)
    await session.commit()
