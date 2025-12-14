"""
Minimal TOML read/write utilities with no external dependencies.

Scope:
- Supports the subset of TOML needed for this project:
  - Top-level keys (string) and dotted keys (e.g., "ai.model_name")
  - Tables: [section] and nested tables [a.b]
  - Arrays: [1, 2], ["a", "b"], [true, false]
  - Scalars: string, int, float, bool
  - Inline comments (starting with #) outside of strings

Not supported (by design, to keep it dependency-free and simple):
- Multiline strings, literal strings, datetime types
- Arrays of tables ([[table]])
- Inline tables ({ key = "value" })
- Escapes beyond common ones in quoted strings

If you need full TOML compliance, use a TOML library (e.g. tomllib on Python 3.11+,
or 'tomli'/'tomlkit'), but this file intentionally avoids external deps.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union


class TomlError(ValueError):
    """Raised when TOML parsing/serialization fails."""


def loads(toml_text: str) -> Dict[str, Any]:
    """
    Parse TOML text into a nested dict.

    Args:
        toml_text: TOML content as a string.

    Returns:
        Nested dict representation.
    """
    parser = _TomlParser(toml_text)
    return parser.parse()


def load(path: str, encoding: str = "utf-8") -> Dict[str, Any]:
    """Read TOML from a file path and parse it."""
    with open(path, "r", encoding=encoding) as f:
        return loads(f.read())


def dumps(data: Dict[str, Any]) -> str:
    """
    Serialize a nested dict to TOML text.

    Notes:
    - Emits primitive keys at the root first, then tables.
    - Uses dotted-table headers for nesting.
    """
    if not isinstance(data, dict):
        raise TomlError("Top-level TOML document must be a dict")

    lines: List[str] = []
    _emit_table(lines, data, prefix=[])
    # Ensure trailing newline for POSIX friendliness
    return ("\n".join(lines)).rstrip() + "\n"


def dump(data: Dict[str, Any], path: str, encoding: str = "utf-8") -> None:
    """Serialize dict to TOML and write to a file path."""
    text = dumps(data)
    with open(path, "w", encoding=encoding, newline="\n") as f:
        f.write(text)


# -------------------------
# Serializer implementation
# -------------------------


def _emit_table(lines: List[str], table: Dict[str, Any], prefix: List[str]) -> None:
    """
    Emit a table:
      - first primitive key/values in this table
      - then child tables recursively
    """
    primitives: List[Tuple[str, Any]] = []
    subtables: List[Tuple[str, Dict[str, Any]]] = []

    for k, v in table.items():
        if isinstance(v, dict):
            subtables.append((k, v))
        else:
            primitives.append((k, v))

    # Emit header for non-root tables if they have any content
    if prefix:
        lines.append(f"[{'.'.join(prefix)}]")

    # Emit primitives
    for k, v in sorted(primitives, key=lambda kv: kv[0]):
        lines.append(f"{k} = {_format_value(v)}")

    # Separate tables with a blank line (if there will be child tables)
    if primitives and subtables:
        lines.append("")

    # Emit subtables
    for k, sub in sorted(subtables, key=lambda kv: kv[0]):
        _emit_table(lines, sub, prefix=prefix + [k])
        lines.append("")

    # Trim any excessive blank lines at the end
    while lines and lines[-1] == "":
        lines.pop()


def _format_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        # TOML allows floats; keep a stable representation
        return repr(value)
    if isinstance(value, str):
        return _quote_string(value)
    if isinstance(value, list):
        return _format_array(value)
    if value is None:
        # TOML has no null; raise to force caller to decide
        raise TomlError("TOML does not support null/None values")
    raise TomlError(f"Unsupported TOML value type: {type(value).__name__}")


def _format_array(items: List[Any]) -> str:
    parts = [_format_value(v) for v in items]
    return "[" + ", ".join(parts) + "]"


def _quote_string(s: str) -> str:
    # Basic TOML string quoting with common escapes
    s = s.replace("\\", "\\\\")
    s = s.replace('"', '\\"')
    s = s.replace("\n", "\\n")
    s = s.replace("\r", "\\r")
    s = s.replace("\t", "\\t")
    return f'"{s}"'


# ----------------------
# Parser implementation
# ----------------------


@dataclass
class _Token:
    kind: str
    value: Any
    pos: int


class _TomlParser:
    def __init__(self, text: str):
        self._text = text
        self._lines = text.splitlines()
        self._doc: Dict[str, Any] = {}
        self._current_path: List[str] = []

    def parse(self) -> Dict[str, Any]:
        for line_no, raw in enumerate(self._lines, start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue

            line_wo_comment = _strip_comment(line)
            if not line_wo_comment.strip():
                continue

            if line_wo_comment.lstrip().startswith("["):
                self._parse_header(line_wo_comment, line_no)
                continue

            self._parse_kv(line_wo_comment, line_no)

        return self._doc

    def _parse_header(self, line: str, line_no: int) -> None:
        s = line.strip()
        if not (s.startswith("[") and s.endswith("]")):
            raise TomlError(f"Invalid table header at line {line_no}: {line}")

        inner = s[1:-1].strip()
        if not inner:
            raise TomlError(f"Empty table header at line {line_no}")

        parts = [p.strip() for p in inner.split(".")]
        if any(not p for p in parts):
            raise TomlError(f"Invalid dotted table name at line {line_no}: {inner}")

        self._current_path = parts
        _ensure_table(self._doc, self._current_path)

    def _parse_kv(self, line: str, line_no: int) -> None:
        # Split at the first '=' that's not inside a string
        key, value_str = _split_kv(line)
        if key is None:
            raise TomlError(f"Invalid key/value line at line {line_no}: {line}")

        key = key.strip()
        if not key:
            raise TomlError(f"Empty key at line {line_no}")

        # Support dotted keys in assignments
        key_parts = [p.strip() for p in key.split(".")]
        if any(not p for p in key_parts):
            raise TomlError(f"Invalid dotted key at line {line_no}: {key}")

        value = _parse_value(value_str.strip(), line_no)

        target = _ensure_table(self._doc, self._current_path)
        _set_nested_key(target, key_parts, value, line_no)


def _strip_comment(line: str) -> str:
    """
    Remove inline comments starting with '#' unless inside a double-quoted string.
    """
    out = []
    in_str = False
    escape = False
    for ch in line:
        if in_str:
            out.append(ch)
            if escape:
                escape = False
                continue
            if ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
            continue

        if ch == '"':
            in_str = True
            out.append(ch)
            continue

        if ch == "#":
            break

        out.append(ch)
    return "".join(out)


def _split_kv(line: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Split a TOML key/value line into (key, value_str) on first '=' not in string.
    Returns (None, None) if no '=' found.
    """
    in_str = False
    escape = False
    for i, ch in enumerate(line):
        if in_str:
            if escape:
                escape = False
                continue
            if ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
            continue
        else:
            if ch == '"':
                in_str = True
                continue
            if ch == "=":
                return line[:i], line[i + 1 :]
    return None, None


def _parse_value(s: str, line_no: int) -> Any:
    if not s:
        raise TomlError(f"Missing value at line {line_no}")

    # String
    if s.startswith('"'):
        return _parse_string(s, line_no)

    # Array
    if s.startswith("["):
        return _parse_array(s, line_no)

    # Bool
    if s == "true":
        return True
    if s == "false":
        return False

    # Int (no underscores support here; keep minimal)
    if _looks_like_int(s):
        try:
            return int(s, 10)
        except Exception:
            raise TomlError(f"Invalid int at line {line_no}: {s}")

    # Float
    if _looks_like_float(s):
        try:
            return float(s)
        except Exception:
            raise TomlError(f"Invalid float at line {line_no}: {s}")

    raise TomlError(f"Unsupported or invalid value at line {line_no}: {s}")


def _parse_string(s: str, line_no: int) -> str:
    # Must be a single-line basic string: "..."
    if len(s) < 2 or not s.endswith('"'):
        raise TomlError(f"Unterminated string at line {line_no}")

    inner = s[1:-1]
    return _unescape_string(inner, line_no)


def _unescape_string(s: str, line_no: int) -> str:
    out = []
    i = 0
    while i < len(s):
        ch = s[i]
        if ch != "\\":
            out.append(ch)
            i += 1
            continue

        i += 1
        if i >= len(s):
            raise TomlError(f"Invalid escape at line {line_no}")

        esc = s[i]
        if esc == "n":
            out.append("\n")
        elif esc == "r":
            out.append("\r")
        elif esc == "t":
            out.append("\t")
        elif esc == '"':
            out.append('"')
        elif esc == "\\":
            out.append("\\")
        else:
            # Keep minimal: unsupported escapes rejected
            raise TomlError(f"Unsupported escape '\\{esc}' at line {line_no}")
        i += 1
    return "".join(out)


def _parse_array(s: str, line_no: int) -> List[Any]:
    s = s.strip()
    if not s.endswith("]"):
        raise TomlError(f"Unterminated array at line {line_no}")

    inner = s[1:-1].strip()
    if not inner:
        return []

    items: List[str] = _split_array_items(inner, line_no)
    return [_parse_value(item.strip(), line_no) for item in items]


def _split_array_items(inner: str, line_no: int) -> List[str]:
    items: List[str] = []
    buf: List[str] = []
    in_str = False
    escape = False
    depth = 0  # nested arrays

    for ch in inner:
        if in_str:
            buf.append(ch)
            if escape:
                escape = False
                continue
            if ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
            continue

        if ch == '"':
            in_str = True
            buf.append(ch)
            continue

        if ch == "[":
            depth += 1
            buf.append(ch)
            continue
        if ch == "]":
            depth -= 1
            if depth < 0:
                raise TomlError(f"Invalid array nesting at line {line_no}")
            buf.append(ch)
            continue

        if ch == "," and depth == 0:
            items.append("".join(buf).strip())
            buf = []
            continue

        buf.append(ch)

    if in_str or depth != 0:
        raise TomlError(f"Invalid array syntax at line {line_no}")

    if buf:
        items.append("".join(buf).strip())

    # Reject trailing commas that produce empty items
    if any(item == "" for item in items):
        raise TomlError(f"Invalid array item at line {line_no}")

    return items


def _looks_like_int(s: str) -> bool:
    if s.startswith(("+", "-")):
        s = s[1:]
    return s.isdigit()


def _looks_like_float(s: str) -> bool:
    # minimal float detection: digits '.' digits (with optional sign)
    raw = s
    if raw.startswith(("+", "-")):
        raw = raw[1:]
    if raw.count(".") != 1:
        return False
    a, b = raw.split(".", 1)
    return (
        (a.isdigit() and b.isdigit())
        or (a == "" and b.isdigit())
        or (a.isdigit() and b == "")
    )


def _ensure_table(doc: Dict[str, Any], path: List[str]) -> Dict[str, Any]:
    cur: Dict[str, Any] = doc
    for part in path:
        existing = cur.get(part)
        if existing is None:
            nxt: Dict[str, Any] = {}
            cur[part] = nxt
            cur = nxt
            continue
        if not isinstance(existing, dict):
            raise TomlError(f"Cannot redefine non-table key as table: {'.'.join(path)}")
        cur = existing
    return cur


def _set_nested_key(
    target: Dict[str, Any], parts: List[str], value: Any, line_no: int
) -> None:
    cur = target
    for p in parts[:-1]:
        if p not in cur:
            cur[p] = {}
        if not isinstance(cur[p], dict):
            raise TomlError(
                f"Cannot set nested key under non-table at line {line_no}: {p}"
            )
        cur = cur[p]
    last = parts[-1]
    if last in cur and isinstance(cur[last], dict):
        raise TomlError(
            f"Cannot overwrite table with value at line {line_no}: {'.'.join(parts)}"
        )
    cur[last] = value
