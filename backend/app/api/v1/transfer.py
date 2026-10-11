"""Импорт/экспорт CSV и XLSX (FR-12 … FR-15). Пока только контракт эндпоинтов."""

from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.core.security import Role, User, require

router = APIRouter(tags=["import-export"])

_NOT_YET = HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "Not implemented yet")


@router.post("/import/cis")
async def import_cis(
    type_id: int = Form(...),
    mode: Literal["create", "upsert"] = Form("upsert"),
    dry_run: bool = Form(True),
    file: UploadFile = File(...),
    _: User = Depends(require(Role.EDITOR)),
):
    """Колонки файла: name, status, owner, description, tags, <атрибуты типа>.

    dry_run=true возвращает отчёт без изменений; false — применяет атомарно.
    """
    raise _NOT_YET


@router.post("/import/relations")
async def import_relations(
    dry_run: bool = Form(True),
    file: UploadFile = File(...),
    _: User = Depends(require(Role.EDITOR)),
):
    """Колонки: source_type, source_name, relation_type, target_type, target_name."""
    raise _NOT_YET


@router.get("/export/cis")
async def export_cis(
    type_id: int,
    format: Literal["csv", "xlsx"] = "xlsx",
    _: User = Depends(require(Role.VIEWER)),
):
    raise _NOT_YET


@router.get("/import/template/{type_id}")
async def import_template(
    type_id: int,
    format: Literal["csv", "xlsx"] = "xlsx",
    _: User = Depends(require(Role.VIEWER)),
):
    raise _NOT_YET
