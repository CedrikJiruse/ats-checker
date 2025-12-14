import json
import logging
import os
from typing import Any, Dict, Optional

try:
    import tomllib  # Python 3.11+
except Exception:  # pragma: no cover
    tomllib = None

logger = logging.getLogger(__name__)


class StateManager:
    """
    Stores resume processing state (hash -> output metadata) in TOML.

    Current state schema (in-memory):
        {
            "<sha256>": {"output_path": "<path>"},
            ...
        }

    TOML on-disk schema:
        [resumes.<sha256>]
        output_path = "..."

    Backward compatibility:
    - If the configured TOML state file does not exist, but a legacy JSON state file
      exists (same basename or default `processed_resumes_state.json`), it will be
      loaded and migrated to TOML automatically (best-effort).
    """

    def __init__(self, state_filepath: str = "data/processed_resumes_state.toml"):
        self.state_filepath = state_filepath
        self.state: Dict[str, Any] = self._load_state()

    # -----------------------------
    # Public API (unchanged shape)
    # -----------------------------

    def get_resume_state(self, file_hash: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves the state for a given resume hash.

        Args:
            file_hash: The SHA256 hash of the resume file.

        Returns:
            A dictionary containing the resume's state (e.g., {"output_path": ...})
            or None if not found.
        """
        return self.state.get(file_hash)

    def update_resume_state(self, file_hash: str, output_path: str) -> None:
        """
        Updates the state for a processed resume.

        Args:
            file_hash: The SHA256 hash of the resume file.
            output_path: The path where the generated output is saved.
        """
        self.state[file_hash] = {"output_path": output_path}
        self._save_state()
        logger.info(
            "Updated state for hash %s with output path %s", file_hash, output_path
        )

    def is_processed(self, file_hash: str) -> bool:
        """
        Checks if a resume with the given hash has already been processed.

        Args:
            file_hash: The SHA256 hash of the resume file.

        Returns:
            True if the resume has been processed, False otherwise.
        """
        return file_hash in self.state

    # -----------------------------
    # Load / Save
    # -----------------------------

    def _load_state(self) -> Dict[str, Any]:
        """
        Loads state from TOML, migrating from legacy JSON if present.
        """
        # 1) Load TOML if it exists
        if os.path.exists(self.state_filepath):
            try:
                state = self._read_toml_state(self.state_filepath)
                logger.info("Loaded state from %s", self.state_filepath)
                return state
            except Exception as e:
                logger.error(
                    "Error loading TOML state file %s: %s",
                    self.state_filepath,
                    e,
                    exc_info=True,
                )
                return {}

        # 2) TOML does not exist -> try migration from JSON
        legacy_json_path = self._infer_legacy_json_path()
        if legacy_json_path and os.path.exists(legacy_json_path):
            try:
                legacy_state = self._read_legacy_json_state(legacy_json_path)
                # Persist to TOML (best-effort)
                self.state = legacy_state
                self._save_state()
                logger.info(
                    "Migrated legacy JSON state from %s to %s",
                    legacy_json_path,
                    self.state_filepath,
                )
                return legacy_state
            except Exception as e:
                logger.error(
                    "Error migrating legacy JSON state file %s: %s",
                    legacy_json_path,
                    e,
                    exc_info=True,
                )
                return {}

        logger.info(
            "No existing state file found at %s. Starting with empty state.",
            self.state_filepath,
        )
        return {}

    def _save_state(self) -> None:
        """
        Saves the current state to TOML.
        """
        try:
            os.makedirs(
                os.path.dirname(os.path.abspath(self.state_filepath)), exist_ok=True
            )
        except Exception:
            # dirname may be empty (relative file in cwd)
            pass

        try:
            self._write_toml_state(self.state_filepath, self.state)
            logger.debug("State saved to %s", self.state_filepath)
        except Exception as e:
            logger.error(
                "Error writing state to TOML file %s: %s",
                self.state_filepath,
                e,
                exc_info=True,
            )

    # -----------------------------
    # Legacy JSON helpers
    # -----------------------------

    def _infer_legacy_json_path(self) -> Optional[str]:
        """
        Infer which legacy JSON file to migrate from.

        Rules:
        - If current state file ends with .toml, use same basename + .json
        - Else fall back to 'processed_resumes_state.json' in cwd
        """
        base, ext = os.path.splitext(self.state_filepath)
        if ext.lower() == ".toml":
            return base + ".json"
        # If the user passes a non-.toml file name, still try the common legacy name.
        return "processed_resumes_state.json"

    def _read_legacy_json_state(self, path: str) -> Dict[str, Any]:
        """
        Load the legacy JSON schema:
            { "<hash>": {"output_path": "..."} , ... }
        """
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            raise ValueError("Legacy JSON state must be an object/dict")

        # Validate/normalize
        out: Dict[str, Any] = {}
        for file_hash, meta in data.items():
            if not isinstance(file_hash, str):
                continue
            if isinstance(meta, dict):
                output_path = meta.get("output_path")
                if isinstance(output_path, str):
                    out[file_hash] = {"output_path": output_path}
                else:
                    # Keep structure but avoid crashing
                    out[file_hash] = dict(meta)
            else:
                # Unexpected schema; keep as-is to avoid data loss
                out[file_hash] = meta
        return out

    # -----------------------------
    # TOML helpers
    # -----------------------------

    def _read_toml_state(self, path: str) -> Dict[str, Any]:
        """
        Read TOML state and return the in-memory schema:
            { "<hash>": {"output_path": "..."} }
        """
        raw = self._toml_load_file(path)
        if not isinstance(raw, dict):
            return {}

        resumes = raw.get("resumes", {})
        if not isinstance(resumes, dict):
            return {}

        out: Dict[str, Any] = {}
        for file_hash, meta in resumes.items():
            if not isinstance(file_hash, str) or not isinstance(meta, dict):
                continue
            output_path = meta.get("output_path")
            if isinstance(output_path, str):
                out[file_hash] = {"output_path": output_path}
            else:
                out[file_hash] = dict(meta)
        return out

    def _write_toml_state(self, path: str, state: Dict[str, Any]) -> None:
        """
        Write the in-memory state schema to TOML:
            [resumes.<hash>]
            output_path = "..."
        """
        doc: Dict[str, Any] = {"resumes": {}}
        for file_hash, meta in state.items():
            if not isinstance(file_hash, str):
                continue
            if isinstance(meta, dict):
                # Only store fields we understand; keep it extensible.
                entry: Dict[str, Any] = {}
                output_path = meta.get("output_path")
                if isinstance(output_path, str):
                    entry["output_path"] = output_path
                else:
                    # Preserve unknown dict-ish meta as strings where possible
                    # (TOML doesn't support null; non-string values are dropped).
                    for k, v in meta.items():
                        if isinstance(k, str) and isinstance(
                            v, (str, int, float, bool, list)
                        ):
                            entry[k] = v
                doc["resumes"][file_hash] = entry
            else:
                # If schema is unexpected, keep minimal placeholder
                doc["resumes"][file_hash] = {}

        self._toml_dump_file(path, doc)

    # -----------------------------
    # Minimal TOML loader/dumper
    # -----------------------------

    def _toml_load_file(self, path: str) -> Dict[str, Any]:
        """
        Prefer stdlib `tomllib` for parsing. Fallback to local `toml_io` if available.
        """
        if tomllib is not None:
            with open(path, "rb") as f:
                return tomllib.load(f)

        # Fallback (should be rare on modern Python)
        try:
            import toml_io  # type: ignore

            return toml_io.load(path)
        except Exception as e:
            raise RuntimeError(
                "TOML parsing requires Python 3.11+ (tomllib) or a local toml_io module"
            ) from e

    def _toml_dump_file(self, path: str, data: Dict[str, Any]) -> None:
        """
        Use local `toml_io` if available (it writes nested tables cleanly),
        otherwise use a small serializer for dict/list/scalars.
        """
        try:
            import toml_io  # type: ignore

            toml_io.dump(data, path)
            return
        except Exception:
            # Fall back to internal minimal serializer
            text = self._toml_dumps_minimal(data)
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(text)

    def _toml_dumps_minimal(self, data: Dict[str, Any]) -> str:
        """
        Minimal TOML serializer for nested dicts, lists, and scalar values.
        Enough for writing state + simple project configs.
        """
        if not isinstance(data, dict):
            raise ValueError("TOML root must be a dict")

        lines = []
        self._emit_toml_table(lines, data, path=())
        return ("\n".join(lines)).rstrip() + "\n"

    def _emit_toml_table(self, lines: list, table: Dict[str, Any], path: tuple) -> None:
        primitives = {}
        subtables = {}

        for k, v in table.items():
            if v is None:
                continue
            if isinstance(v, dict):
                subtables[k] = v
            else:
                primitives[k] = v

        if path:
            lines.append(f"[{'.'.join(path)}]")

        for k in sorted(primitives.keys()):
            lines.append(f"{k} = {self._toml_format_value(primitives[k])}")

        if primitives and subtables:
            lines.append("")

        for k in sorted(subtables.keys()):
            self._emit_toml_table(lines, subtables[k], path=path + (k,))
            lines.append("")

        while lines and lines[-1] == "":
            lines.pop()

    def _toml_format_value(self, v: Any) -> str:
        if isinstance(v, bool):
            return "true" if v else "false"
        if isinstance(v, int) and not isinstance(v, bool):
            return str(v)
        if isinstance(v, float):
            return repr(v)
        if isinstance(v, str):
            return self._toml_quote(v)
        if isinstance(v, list):
            return "[" + ", ".join(self._toml_format_value(x) for x in v) + "]"
        raise ValueError(f"Unsupported TOML value type: {type(v).__name__}")

    def _toml_quote(self, s: str) -> str:
        s = s.replace("\\", "\\\\")
        s = s.replace('"', '\\"')
        s = s.replace("\n", "\\n")
        s = s.replace("\r", "\\r")
        s = s.replace("\t", "\\t")
        return f'"{s}"'


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    # Quick sanity check:
    sm = StateManager("test_processed_resumes_state.toml")
    h = "a1b2c3"
    if not sm.is_processed(h):
        sm.update_resume_state(h, "output/example.txt")
    print("Loaded:", sm.get_resume_state(h))
