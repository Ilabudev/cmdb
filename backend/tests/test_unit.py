import pytest
from fastapi.testclient import TestClient

from app.core.security import Role, User
from app.main import create_app
from app.seed import CI_TYPES
from app.services.attributes import AttributeValidationError, check_schema, validate_attributes
from app.services.audit import diff


def test_healthz():
    assert TestClient(create_app()).get("/healthz").json() == {"status": "ok"}


def test_api_requires_token():
    assert TestClient(create_app()).get("/api/v1/ci-types").status_code == 401


def test_role_hierarchy():
    editor = User("u", {Role.EDITOR})
    assert editor.has(Role.VIEWER) and editor.has(Role.EDITOR) and not editor.has(Role.ADMIN)
    assert not User("u", {"unrelated"}).has(Role.VIEWER)


def test_diff_only_changed_fields():
    assert diff({"a": 1, "b": 2}, {"a": 1, "b": 3, "c": 4}) == {
        "b": {"old": 2, "new": 3},
        "c": {"old": None, "new": 4},
    }


def test_attribute_validation():
    schema = {"type": "object", "properties": {"cpu": {"type": "integer"}}, "required": ["cpu"]}
    validate_attributes(schema, {"cpu": 4})
    with pytest.raises(AttributeValidationError) as exc:
        validate_attributes(schema, {"cpu": "four"})
    assert "cpu" in exc.value.errors


@pytest.mark.parametrize("code,name,icon,schema", CI_TYPES)
def test_seed_schemas_are_valid(code, name, icon, schema):
    check_schema(schema)
