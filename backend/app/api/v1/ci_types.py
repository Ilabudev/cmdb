from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import Role, User, require
from app.models import CIType
from app.schemas import CITypeIn, CITypeOut, CITypeUpdate
from app.services import audit
from app.services.attributes import AttributeValidationError, check_schema

router = APIRouter(prefix="/ci-types", tags=["ci-types"])


@router.get("", response_model=list[CITypeOut])
async def list_types(
    session: AsyncSession = Depends(get_session), _: User = Depends(require(Role.VIEWER))
):
    return (await session.scalars(select(CIType).order_by(CIType.name))).all()


@router.get("/{type_id}", response_model=CITypeOut)
async def get_type(
    type_id: int,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require(Role.VIEWER)),
):
    if (obj := await session.get(CIType, type_id)) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    return obj


@router.post("", response_model=CITypeOut, status_code=status.HTTP_201_CREATED)
async def create_type(
    data: CITypeIn,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require(Role.ADMIN)),
):
    try:
        check_schema(data.attribute_schema)
    except AttributeValidationError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, exc.errors) from exc
    obj = CIType(**data.model_dump(), created_by=user.username, updated_by=user.username)
    session.add(obj)
    await session.flush()
    audit.record(
        session, entity="ci_type", entity_id=obj.id, action="create", actor=user.username,
        changes=audit.diff({}, data.model_dump()),
    )
    await session.commit()
    return obj


@router.patch("/{type_id}", response_model=CITypeOut)
async def update_type(
    type_id: int,
    data: CITypeUpdate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require(Role.ADMIN)),
):
    if (obj := await session.get(CIType, type_id)) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    patch = data.model_dump(exclude_unset=True)
    if "attribute_schema" in patch:
        try:
            check_schema(patch["attribute_schema"])
        except AttributeValidationError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, exc.errors) from exc
        # TODO(FR-6): отчёт о CI, не соответствующих новой схеме
    old = {k: getattr(obj, k) for k in patch}
    for k, v in patch.items():
        setattr(obj, k, v)
    obj.updated_by = user.username
    audit.record(
        session, entity="ci_type", entity_id=obj.id, action="update", actor=user.username,
        changes=audit.diff(old, patch),
    )
    await session.commit()
    return obj
