"""
JSON schema validation helpers for resume outputs.

Purpose
-------
This module provides lightweight, dependency-optional JSON Schema validation with
readable error formatting. It is designed to validate the structured resume JSON
produced by the application (and optionally enriched with `_meta` / `_scoring`).

It supports:
- Loading JSON schemas from disk.
- Validating JSON objects against a schema (using `jsonschema` if installed).
- Producing human-friendly, stable error messages suitable for logs/UI.

Dependencies
------------
- Optional: `jsonschema` (recommended). If not installed, validation is disabled and
  helpers will raise or return a "not available" result depending on the call.

Notes
-----
- This module does not attempt to be a full JSON Schema implementation.
- Draft version is whatever `jsonschema` supports; the bundled schema uses draft 2020-12.

Public API
----------
- schema_validation_available() -> bool
- load_schema(schema_path: str) -> dict
- validate_json(instance: Any, schema: dict, *, instance_name: str = "instance") -> ValidationResult
- format_validation_errors(errors: list[ValidationErrorLike], *, max_errors: int = 20) -> str
- validate_json_str(json_str: str, schema: dict, *, instance_name: str = "instance") -> ValidationResult
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

try:
    import jsonschema  # type: ignore
except Exception:  # pragma: no cover
    jsonschema = None


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    errors: List[str]
    summary: str
    detail: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "summary": self.summary,
            "errors": list(self.errors),
            "detail": self.detail,
        }


def schema_validation_available() -> bool:
    """Return True if JSON Schema validation is available in this environment."""
    return jsonschema is not None


def load_schema(schema_path: str) -> Dict[str, Any]:
    """
    Load a JSON schema from disk.

    Args:
        schema_path: Path to a JSON schema file.

    Returns:
        Parsed schema dict.

    Raises:
        FileNotFoundError: if schema_path does not exist.
        ValueError: if schema file is not valid JSON or not a JSON object.
    """
    if not schema_path:
        raise ValueError("schema_path is empty")
    if not os.path.exists(schema_path):
        raise FileNotFoundError(schema_path)

    with open(schema_path, "r", encoding="utf-8") as f:
        try:
            schema = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON schema file: {schema_path} ({e})") from e

    if not isinstance(schema, dict):
        raise ValueError(f"Schema must be a JSON object at top-level: {schema_path}")
    return schema


def validate_json(
    instance: Any,
    schema: Dict[str, Any],
    *,
    instance_name: str = "instance",
    max_errors: int = 20,
) -> ValidationResult:
    """
    Validate an in-memory JSON-like instance against a JSON schema.

    Args:
        instance: JSON-like object (typically dict) to validate.
        schema: JSON schema dict.
        instance_name: Friendly label for error messages.
        max_errors: Maximum errors to report.

    Returns:
        ValidationResult (ok/errors/summary/detail).

    Behavior:
        - If `jsonschema` is not installed, returns ok=False with a helpful message.
        - Uses `Draft202012Validator` when available, otherwise falls back to `validate`.
        - Collects errors and formats them for readability.
    """
    if jsonschema is None:
        return ValidationResult(
            ok=False,
            errors=[
                "JSON Schema validation is not available (missing 'jsonschema' dependency)."
            ],
            summary="schema_validation_unavailable",
            detail=(
                "Install 'jsonschema' to enable validation. "
                "Example: pip install jsonschema"
            ),
        )

    if not isinstance(schema, dict):
        return ValidationResult(
            ok=False,
            errors=[f"{instance_name}: schema must be a dict (JSON object)"],
            summary="invalid_schema_type",
        )

    # Prefer an explicit validator class if present.
    ValidatorClass = getattr(jsonschema, "Draft202012Validator", None)
    errors_raw = []

    try:
        if ValidatorClass is not None:
            validator = ValidatorClass(schema)
            errors_raw = sorted(
                validator.iter_errors(instance),
                key=lambda e: list(e.absolute_path),
            )
        else:
            # Fallback: raises first error only; convert to list for uniform formatting.
            try:
                jsonschema.validate(instance=instance, schema=schema)
                errors_raw = []
            except Exception as e:
                errors_raw = [e]
    except Exception as e:
        # Malformed schema or validator issues
        return ValidationResult(
            ok=False,
            errors=[f"{instance_name}: schema validation failed to run: {e}"],
            summary="validation_runtime_error",
        )

    if not errors_raw:
        return ValidationResult(ok=True, errors=[], summary="ok")

    formatted = format_validation_errors(
        errors_raw, instance_name=instance_name, max_errors=max_errors
    )
    # Keep a short list and a full detail text
    short_errors = _first_lines(formatted, max_lines=min(max_errors, 20))
    return ValidationResult(
        ok=False,
        errors=short_errors,
        summary="schema_validation_failed",
        detail=formatted,
    )


def validate_json_str(
    json_str: str,
    schema: Dict[str, Any],
    *,
    instance_name: str = "instance",
    max_errors: int = 20,
) -> ValidationResult:
    """
    Validate a JSON string against a schema.

    This is useful when the AI returns JSON text and you want schema checking
    before persisting.

    Args:
        json_str: JSON string to parse and validate.
        schema: JSON schema dict.
        instance_name: Friendly label for error messages.
        max_errors: Maximum errors to report.

    Returns:
        ValidationResult
    """
    if not isinstance(json_str, str) or not json_str.strip():
        return ValidationResult(
            ok=False,
            errors=[f"{instance_name}: JSON string is empty"],
            summary="empty_json",
        )

    try:
        instance = json.loads(json_str)
    except json.JSONDecodeError as e:
        return ValidationResult(
            ok=False,
            errors=[f"{instance_name}: invalid JSON ({e})"],
            summary="invalid_json",
        )

    return validate_json(
        instance, schema, instance_name=instance_name, max_errors=max_errors
    )


def format_validation_errors(
    errors: Sequence[Any],
    *,
    instance_name: str = "instance",
    max_errors: int = 20,
) -> str:
    """
    Format jsonschema validation errors into a readable multi-line string.

    We attempt to extract:
    - JSON pointer-ish path where the error occurred
    - Message
    - Validator keyword (if available)
    - Expected schema fragment (compact)
    - Actual instance value (compact)

    Args:
        errors: A sequence of jsonschema ValidationError objects (or exceptions).
        instance_name: Label for the instance.
        max_errors: Max number of errors to include.

    Returns:
        Multi-line string suitable for logs.
    """
    lines: List[str] = []
    count = 0

    for err in errors:
        if count >= max_errors:
            break
        count += 1

        # ValidationError from jsonschema has many attributes; keep best-effort.
        path = _format_error_path(err)
        message = getattr(err, "message", None) or str(err)
        validator = getattr(err, "validator", None)
        schema_fragment = getattr(err, "schema", None)
        instance_value = getattr(err, "instance", None)

        header = f"{count}. {instance_name}{path}: {message}"
        lines.append(header)

        if validator:
            lines.append(f"   validator: {validator}")

        if schema_fragment is not None:
            lines.append(f"   expected: {_compact(schema_fragment)}")

        if instance_value is not None:
            lines.append(f"   actual:   {_compact(instance_value)}")

        # Add context about which schema path failed (helps debugging schemas).
        schema_path = _format_schema_path(err)
        if schema_path:
            lines.append(f"   schema_path: {schema_path}")

        lines.append("")

    # Trim trailing blank line
    while lines and lines[-1] == "":
        lines.pop()

    return "\n".join(lines)


# -----------------------
# Internal helpers
# -----------------------


def _format_error_path(err: Any) -> str:
    """
    Convert jsonschema error absolute_path into something stable and readable.
    Example: ['experience', 0, 'title'] -> ".experience[0].title"
    """
    abs_path = getattr(err, "absolute_path", None)
    if abs_path is None:
        return ""

    parts = []
    try:
        for p in list(abs_path):
            if isinstance(p, int):
                parts.append(f"[{p}]")
            else:
                # dot segment
                s = str(p)
                # if it contains weird chars, fallback to bracket notation
                if s.isidentifier():
                    parts.append("." + s)
                else:
                    parts.append(f"[{json.dumps(s)}]")
    except Exception:
        return ""

    return "".join(parts)


def _format_schema_path(err: Any) -> str:
    """
    Convert jsonschema error absolute_schema_path into a dotted/bracket path.
    """
    abs_path = getattr(err, "absolute_schema_path", None)
    if abs_path is None:
        return ""
    try:
        items = list(abs_path)
    except Exception:
        return ""
    if not items:
        return ""

    parts = []
    for p in items:
        if isinstance(p, int):
            parts.append(f"[{p}]")
        else:
            s = str(p)
            if s.isidentifier():
                parts.append("." + s)
            else:
                parts.append(f"[{json.dumps(s)}]")
    return "".join(parts).lstrip(".")


def _compact(value: Any, *, max_len: int = 240) -> str:
    """
    Compact a value to a short JSON-ish representation.
    """
    try:
        if isinstance(value, (dict, list)):
            s = json.dumps(value, ensure_ascii=False, sort_keys=True)
        else:
            s = json.dumps(value, ensure_ascii=False)
    except Exception:
        s = repr(value)

    if len(s) > max_len:
        return s[: max_len - 3] + "..."
    return s


def _first_lines(text: str, *, max_lines: int = 20) -> List[str]:
    """
    Return the first non-empty-ish lines as a list, capped.
    """
    out = []
    for line in text.splitlines():
        if line.strip() == "":
            continue
        out.append(line)
        if len(out) >= max_lines:
            break
    return out
