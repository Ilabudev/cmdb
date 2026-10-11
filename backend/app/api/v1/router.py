from fastapi import APIRouter

from app.api.v1 import audit, ci_types, cis, relations, transfer

api_router = APIRouter(prefix="/api/v1")
for module in (ci_types, cis, relations, audit, transfer):
    api_router.include_router(module.router)
