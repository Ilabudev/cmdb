"""Проверка OIDC Bearer-токенов и ролей."""

from dataclasses import dataclass, field
from enum import StrEnum

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Settings, get_settings


class Role(StrEnum):
    VIEWER = "cmdb-viewer"
    EDITOR = "cmdb-editor"
    ADMIN = "cmdb-admin"


# Каждая роль включает права нижестоящих
_ROLE_RANK = {Role.VIEWER: 1, Role.EDITOR: 2, Role.ADMIN: 3}


@dataclass
class User:
    username: str
    roles: set[str] = field(default_factory=set)

    def has(self, role: Role) -> bool:
        rank = max((_ROLE_RANK.get(Role(r), 0) for r in self.roles if r in Role), default=0)
        return rank >= _ROLE_RANK[role]


_bearer = HTTPBearer(auto_error=False)
_jwks_clients: dict[str, jwt.PyJWKClient] = {}


def _jwks(settings: Settings) -> jwt.PyJWKClient:
    url = settings.oidc_jwks_url or f"{settings.oidc_issuer}/protocol/openid-connect/certs"
    if url not in _jwks_clients:
        _jwks_clients[url] = jwt.PyJWKClient(url)
    return _jwks_clients[url]


def _extract_roles(claims: dict, claim: str) -> set[str]:
    # Поддерживает как плоский claim, так и вложенный через точку (realm_access.roles)
    value: object = claims
    for part in claim.split("."):
        value = value.get(part, {}) if isinstance(value, dict) else {}
    return set(value) if isinstance(value, list) else set()


async def current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    settings: Settings = Depends(get_settings),
) -> User:
    if settings.auth_disabled:
        return User(username="dev", roles={Role.ADMIN})
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    try:
        key = _jwks(settings).get_signing_key_from_jwt(creds.credentials).key
        claims = jwt.decode(
            creds.credentials,
            key,
            algorithms=["RS256"],
            audience=settings.oidc_audience,
            issuer=settings.oidc_issuer,
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Invalid token: {exc}") from exc
    return User(
        username=claims.get("preferred_username") or claims["sub"],
        roles=_extract_roles(claims, settings.oidc_roles_claim),
    )


def require(role: Role):
    async def dependency(user: User = Depends(current_user)) -> User:
        if not user.has(role):
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Role {role} required")
        return user

    return dependency
