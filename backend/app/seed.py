"""Встроенные типы CI и связей. Идемпотентно: `python -m app.seed`."""

import asyncio

from sqlalchemy import select

from app.core.db import SessionLocal
from app.models import CIType, RelationType


def _obj(required: list[str] | None = None, **props: dict) -> dict:
    return {"type": "object", "properties": props, "required": required or []}


_STR = {"type": "string"}
_INT = {"type": "integer", "minimum": 0}
_NUM = {"type": "number", "minimum": 0}
_IP = {"type": "string", "format": "ipv4"}

CI_TYPES = [
    ("server", "Физический сервер", "server", _obj(
        vendor=_STR, model=_STR, serial=_STR, cpu=_INT, ram_gb=_INT, location=_STR, rack=_STR)),
    ("hypervisor", "Гипервизор/кластер", "cluster", _obj(
        platform={"enum": ["vmware", "kvm", "hyper-v", "proxmox", "other"]}, version=_STR)),
    ("vm", "Виртуальная машина", "vm", _obj(cpu=_INT, ram_gb=_INT, disk_gb=_INT, os=_STR, ip=_IP)),
    ("network_device", "Сетевое устройство", "router", _obj(
        kind={"enum": ["switch", "router", "firewall", "load_balancer", "other"]},
        vendor=_STR, model=_STR, mgmt_ip=_IP)),
    ("network", "Сеть/подсеть", "network", _obj(
        ["cidr"], cidr=_STR, vlan={"type": "integer", "minimum": 1, "maximum": 4094},
        gateway=_IP)),
    ("os", "Операционная система", "os", _obj(family=_STR, version=_STR)),
    ("software", "ПО/приложение", "app", _obj(vendor=_STR, version=_STR)),
    ("database", "СУБД/база", "database", _obj(
        engine=_STR, version=_STR, port={"type": "integer", "minimum": 1, "maximum": 65535})),
    ("storage", "СХД", "storage", _obj(vendor=_STR, model=_STR, capacity_tb=_NUM)),
]

RELATION_TYPES = [
    ("runs_on", "работает на", "хостит"),
    ("installed_on", "установлено на", "содержит"),
    ("depends_on", "зависит от", "нужен для"),
    ("connected_to", "подключено к", "подключено"),
    ("member_of", "входит в", "включает"),
    ("uses_storage", "использует СХД", "предоставляет хранилище"),
]


async def seed() -> None:
    async with SessionLocal() as session:
        have_ci = set(await session.scalars(select(CIType.code)))
        for code, name, icon, schema in CI_TYPES:
            if code not in have_ci:
                session.add(CIType(code=code, name=name, icon=icon, attribute_schema=schema,
                                   is_system=True, created_by="system", updated_by="system"))
        have_rel = set(await session.scalars(select(RelationType.code)))
        for code, name, reverse in RELATION_TYPES:
            if code not in have_rel:
                session.add(RelationType(code=code, name=name, reverse_name=reverse,
                                         is_system=True, created_by="system", updated_by="system"))
        await session.commit()


if __name__ == "__main__":
    asyncio.run(seed())
