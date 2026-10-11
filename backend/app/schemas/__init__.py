import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.ci import CIStatus


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page[T](BaseModel):
    items: list[T]
    total: int
    limit: int
    offset: int


# --- CI types ---


class CITypeIn(BaseModel):
    code: str = Field(pattern=r"^[a-z][a-z0-9_]{1,63}$")
    name: str
    description: str | None = None
    icon: str | None = None
    attribute_schema: dict = Field(default_factory=lambda: {"type": "object", "properties": {}})


class CITypeUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    icon: str | None = None
    attribute_schema: dict | None = None


class CITypeOut(ORM):
    id: int
    code: str
    name: str
    description: str | None
    icon: str | None
    attribute_schema: dict
    is_system: bool


# --- CI ---


class CIIn(BaseModel):
    type_id: int
    name: str = Field(min_length=1, max_length=255)
    status: CIStatus = CIStatus.ACTIVE
    owner: str | None = None
    description: str | None = None
    tags: list[str] = []
    attributes: dict = {}


class CIUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    status: CIStatus | None = None
    owner: str | None = None
    description: str | None = None
    tags: list[str] | None = None
    attributes: dict | None = None


class CIOut(ORM):
    id: uuid.UUID
    type_id: int
    name: str
    status: CIStatus
    owner: str | None
    description: str | None
    tags: list[str]
    attributes: dict
    created_at: datetime
    created_by: str
    updated_at: datetime
    updated_by: str


# --- Relations ---


class RelationTypeIn(BaseModel):
    code: str = Field(pattern=r"^[a-z][a-z0-9_]{1,63}$")
    name: str
    reverse_name: str
    allowed_pairs: list[dict[str, str]] = []
    propagates_impact: bool = True


class RelationTypeOut(ORM):
    id: int
    code: str
    name: str
    reverse_name: str
    allowed_pairs: list[dict[str, str]]
    propagates_impact: bool
    is_system: bool


class RelationIn(BaseModel):
    type_id: int
    source_id: uuid.UUID
    target_id: uuid.UUID
    description: str | None = None


class RelationOut(ORM):
    id: uuid.UUID
    type_id: int
    source_id: uuid.UUID
    target_id: uuid.UUID
    description: str | None


# --- Graph ---

Direction = Literal["upstream", "downstream", "both"]


class GraphNode(BaseModel):
    id: uuid.UUID
    name: str
    type_code: str
    status: CIStatus
    depth: int


class GraphEdge(BaseModel):
    id: uuid.UUID
    type_code: str
    source_id: uuid.UUID
    target_id: uuid.UUID


class Graph(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


# --- Audit ---


class AuditEventOut(ORM):
    id: int
    entity: str
    entity_id: str
    action: str
    changes: dict
    actor: str
    source: str
    at: datetime
