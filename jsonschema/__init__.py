"""Minimal JSON Schema validator for repository contract tests."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ValidationError(Exception):
    message: str

    def __str__(self) -> str:
        return self.message


def validate(instance: object, schema: dict, resolver: object | None = None) -> None:
    _validate(instance, schema, path="$")


def _validate(instance: object, schema: dict, path: str) -> None:
    schema_type = schema.get("type")
    if schema_type is not None:
        _check_type(instance, schema_type, path)

    if "enum" in schema:
        if instance not in schema["enum"]:
            raise ValidationError(f"{path}: value {instance!r} not in enum {schema['enum']}")

    if isinstance(instance, str) and "minLength" in schema:
        if len(instance) < schema["minLength"]:
            raise ValidationError(f"{path}: string shorter than {schema['minLength']}")

    if isinstance(instance, (int, float)) and "minimum" in schema:
        if instance < schema["minimum"]:
            raise ValidationError(f"{path}: number below minimum {schema['minimum']}")
    if isinstance(instance, (int, float)) and "maximum" in schema:
        if instance > schema["maximum"]:
            raise ValidationError(f"{path}: number above maximum {schema['maximum']}")

    if isinstance(instance, dict):
        if schema.get("additionalProperties") is False:
            allowed = set(schema.get("properties", {}).keys())
            extra = set(instance.keys()) - allowed
            if extra:
                raise ValidationError(f"{path}: unexpected keys {sorted(extra)}")

        required = schema.get("required", [])
        for key in required:
            if key not in instance:
                raise ValidationError(f"{path}: missing required key '{key}'")

        properties = schema.get("properties", {})
        for key, value in instance.items():
            if key in properties:
                _validate(value, properties[key], f"{path}.{key}")

    if isinstance(instance, list):
        items_schema = schema.get("items")
        if items_schema:
            for index, item in enumerate(instance):
                _validate(item, items_schema, f"{path}[{index}]")


def _check_type(instance: object, schema_type: str | list[str], path: str) -> None:
    if isinstance(schema_type, list):
        if any(_is_type(instance, t) for t in schema_type):
            return
        raise ValidationError(f"{path}: expected types {schema_type}, got {type(instance).__name__}")
    if not _is_type(instance, schema_type):
        raise ValidationError(f"{path}: expected type {schema_type}, got {type(instance).__name__}")


def _is_type(instance: object, schema_type: str) -> bool:
    if schema_type == "object":
        return isinstance(instance, dict)
    if schema_type == "array":
        return isinstance(instance, list)
    if schema_type == "string":
        return isinstance(instance, str)
    if schema_type == "integer":
        return isinstance(instance, int) and not isinstance(instance, bool)
    if schema_type == "number":
        return isinstance(instance, (int, float)) and not isinstance(instance, bool)
    if schema_type == "null":
        return instance is None
    return False
