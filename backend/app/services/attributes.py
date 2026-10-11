"""Валидация атрибутов CI по JSON Schema типа."""

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError


class AttributeValidationError(ValueError):
    def __init__(self, errors: dict[str, str]):
        super().__init__("Invalid attributes")
        self.errors = errors


def check_schema(schema: dict) -> None:
    """Проверяет, что схема типа сама по себе корректна."""
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        raise AttributeValidationError({"attribute_schema": exc.message}) from exc


def validate_attributes(schema: dict, attributes: dict) -> None:
    errors = {
        ".".join(map(str, e.absolute_path)) or "$": e.message
        for e in Draft202012Validator(schema).iter_errors(attributes)
    }
    if errors:
        raise AttributeValidationError(errors)
