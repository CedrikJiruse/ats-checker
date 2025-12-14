"""
Configuration management for ATS Checker.

This version switches configuration from JSON to TOML while remaining backward
compatible with existing `config.json` installs.

Key features:
- Primary config file: TOML (default: `config.toml`)
- Backward-compatible JSON loading:
  - If a JSON config is found/used, it will be migrated to TOML (best-effort)
    unless a TOML config already exists.
- New settings for:
  - multiple AI agents
  - scoring system + external weights TOML file
  - recursive/iterative resume improvement until a target score has been reached
- Restores OCR support configuration via `tesseract_cmd`

Design notes:
- Parsing TOML uses the Python standard library `tomllib` (Python 3.11+).
- Writing TOML uses a minimal internal serializer (dependency-free).
  It supports dicts/lists/scalars and nested tables, which is enough for this repo.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

try:
    import tomllib  # Python 3.11+
except Exception as e:  # pragma: no cover
    tomllib = None


# -----------------------
# Defaults (TOML schema)
# -----------------------

DEFAULTS: Dict[str, Any] = {
    "paths": {
        "output_folder": "workspace/output",
        "input_resumes_folder": "workspace/input_resumes",
        "job_descriptions_folder": "workspace/job_descriptions",
        "job_search_results_folder": "workspace/job_search_results",
        # State and saved searches are not part of the main config today,
        # but putting them here makes the system easier to relocate.
        "state_file": "data/processed_resumes_state.toml",
        "saved_searches_file": "data/saved_searches.toml",
        # OCR: optional explicit path to the Tesseract executable.
        # Use empty string to mean "unset" (TOML has no null).
        "tesseract_cmd": "",
        # Scoring weights are kept in a separate TOML file as requested.
        "scoring_weights_file": "config/scoring_weights.toml",
    },
    "ai": {
        # Default model settings (used by the "enhancer" agent unless overridden).
        "provider": "gemini",
        "model_name": "gemini-pro",
        "temperature": 0.7,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 8192,
        # Multi-agent configuration:
        # Represented as nested tables instead of array-of-tables to keep the writer simple.
        #
        # Example in TOML:
        # [ai.agents.enhancer]
        # role = "resume_enhancement"
        # provider = "gemini"
        # model_name = "gemini-1.5-flash-latest"
        "agents": {
            "enhancer": {
                "role": "resume_enhancement",
                "provider": "gemini",
                "model_name": "gemini-pro",
            },
            "job_summarizer": {
                "role": "job_summary",
                "provider": "gemini",
                "model_name": "gemini-pro",
            },
            "scorer": {
                "role": "scoring",
                "provider": "gemini",
                "model_name": "gemini-pro",
            },
            "reviser": {
                "role": "resume_revision",
                "provider": "gemini",
                "model_name": "gemini-pro",
            },
        },
    },
    "processing": {
        # Existing behavior: number of output versions to generate per job description.
        "num_versions_per_job": 3,
        # Iterative improvement options:
        "iterate_until_score_reached": False,
        "target_score": 80.0,
        "max_iterations": 3,
        # A safety guard: require at least this improvement to continue iterating.
        "min_score_delta": 0.1,
        # Iteration strategy (advanced)
        # - "best_of": keep best candidate seen so far; stop on target/no_progress/max_iterations
        # - "first_hit": stop immediately once target_score is reached
        # - "patience": stop if no improvement is seen for N iterations (more stable)
        "iteration_strategy": "patience",
        "iteration_patience": 2,
        "stop_on_regression": True,
        "max_regressions": 2,
        # Structured output format for enhanced resume data: "json" | "toml" | "both"
        "structured_output_format": "toml",
        # Schema validation (best-effort; if enabled, the app should validate AI output
        # against a schema and retry once or fail fast depending on config).
        "schema_validation_enabled": False,
        "resume_schema_path": "",
        "schema_validation_max_retries": 1,
        # Recommendations: allow generating actionable suggestions based on score breakdown.
        "recommendations_enabled": False,
        "recommendations_max_items": 5,
        # Output layout: controls how files are organized under the output folder.
        # Example pattern: "{resume_name}/{job_title}/{timestamp}"
        "output_subdir_pattern": "{resume_name}/{job_title}/{timestamp}",
        "write_score_summary_file": True,
    },
    "job_search": {
        "max_job_results_per_search": 50,
    },
}


# -----------------------
# Config data structure
# -----------------------


@dataclass
class Config:
    # Paths
    output_folder: str
    input_resumes_folder: str
    job_descriptions_folder: str
    job_search_results_folder: str
    tesseract_cmd: Optional[str]
    state_file: str
    saved_searches_file: str
    scoring_weights_file: str

    # AI settings
    ai_provider: str
    model_name: str
    temperature: float
    top_p: float
    top_k: int
    max_output_tokens: int
    ai_agents: Dict[str, Dict[str, Any]]

    # Processing
    num_versions_per_job: int
    iterate_until_score_reached: bool
    target_score: float
    max_iterations: int
    min_score_delta: float

    # Iteration strategy (advanced)
    iteration_strategy: str
    iteration_patience: int
    stop_on_regression: bool
    max_regressions: int

    # Output formats/layout
    structured_output_format: str
    output_subdir_pattern: str
    write_score_summary_file: bool

    # Schema validation
    schema_validation_enabled: bool
    resume_schema_path: str
    schema_validation_max_retries: int

    # Recommendations
    recommendations_enabled: bool
    recommendations_max_items: int

    # Job search
    max_job_results_per_search: int

    def to_dict(self) -> Dict[str, Any]:
        # Keep a stable, explicit representation for printing/debugging.
        return {
            "paths": {
                "output_folder": self.output_folder,
                "input_resumes_folder": self.input_resumes_folder,
                "job_descriptions_folder": self.job_descriptions_folder,
                "job_search_results_folder": self.job_search_results_folder,
                "tesseract_cmd": self.tesseract_cmd or "",
                "state_file": self.state_file,
                "saved_searches_file": self.saved_searches_file,
                "scoring_weights_file": self.scoring_weights_file,
            },
            "ai": {
                "provider": self.ai_provider,
                "model_name": self.model_name,
                "temperature": self.temperature,
                "top_p": self.top_p,
                "top_k": self.top_k,
                "max_output_tokens": self.max_output_tokens,
                "agents": self.ai_agents,
            },
            "processing": {
                "num_versions_per_job": self.num_versions_per_job,
                "iterate_until_score_reached": self.iterate_until_score_reached,
                "target_score": self.target_score,
                "max_iterations": self.max_iterations,
                "min_score_delta": self.min_score_delta,
                "iteration_strategy": self.iteration_strategy,
                "iteration_patience": self.iteration_patience,
                "stop_on_regression": self.stop_on_regression,
                "max_regressions": self.max_regressions,
                "structured_output_format": self.structured_output_format,
                "schema_validation_enabled": self.schema_validation_enabled,
                "resume_schema_path": self.resume_schema_path,
                "schema_validation_max_retries": self.schema_validation_max_retries,
                "recommendations_enabled": self.recommendations_enabled,
                "recommendations_max_items": self.recommendations_max_items,
                "output_subdir_pattern": self.output_subdir_pattern,
                "write_score_summary_file": self.write_score_summary_file,
            },
            "job_search": {
                "max_job_results_per_search": self.max_job_results_per_search,
            },
        }


# -----------------------
# Public API
# -----------------------


def load_config(
    config_file_path: str = "config/config.toml", cli_args: Any = None
) -> Config:
    """
    Load configuration from TOML, with backward-compatible JSON support.

    Behavior:
    - If `config_file_path` exists:
        - reads TOML if .toml
        - reads JSON if .json
        - attempts TOML first if extension is unknown
    - If it does not exist:
        - tries the "other" default (config.toml <-> config.json)
        - otherwise returns defaults
    - CLI args override file settings (only for known keys).

    Returns:
        Config object with normalized absolute paths.
    """
    resolved_path, file_kind = _resolve_config_path(config_file_path)

    raw: Dict[str, Any] = _deep_copy(DEFAULTS)

    loaded_from_json = False
    if resolved_path is not None and os.path.exists(resolved_path):
        if file_kind == "toml":
            file_data = _load_toml_file(resolved_path)
            _deep_merge(raw, file_data)
        elif file_kind == "json":
            file_data = _load_json_file(resolved_path)
            # JSON legacy configs are flat; map them into the new nested schema.
            file_data = _map_legacy_json_config_to_toml_shape(file_data)
            _deep_merge(raw, file_data)
            loaded_from_json = True
        else:
            # Unknown extension: attempt TOML then JSON.
            try:
                file_data = _load_toml_file(resolved_path)
                _deep_merge(raw, file_data)
                file_kind = "toml"
            except Exception:
                file_data = _load_json_file(resolved_path)
                file_data = _map_legacy_json_config_to_toml_shape(file_data)
                _deep_merge(raw, file_data)
                loaded_from_json = True
                file_kind = "json"

    # Apply CLI overrides
    if cli_args is not None:
        raw = _apply_cli_overrides(raw, cli_args)

    # Normalize + build Config
    cfg = _build_config(raw)

    # Best-effort migration if loaded from JSON and TOML doesn't already exist.
    if loaded_from_json:
        _maybe_migrate_json_to_toml(
            json_path=resolved_path,
            toml_path=_default_toml_path_for(resolved_path),
            merged_raw=cfg.to_dict(),
        )

    return cfg


def save_config_toml(config: Config, config_file_path: str = "config.toml") -> None:
    """
    Persist configuration to TOML.

    Note:
    - This writes only TOML.
    - It will omit any values that TOML cannot represent (e.g., None).
    """
    data = config.to_dict()
    _write_toml_file(config_file_path, data)


# -----------------------
# Path resolution
# -----------------------


def _resolve_config_path(config_file_path: str) -> Tuple[Optional[str], str]:
    """
    Resolve the config path to an existing file if possible.

    Returns:
        (resolved_path_or_none, kind)
        kind is one of: "toml", "json", "unknown"
    """
    path = config_file_path or "config.toml"
    _, ext = os.path.splitext(path.lower())

    def _kind_for_ext(e: str) -> str:
        if e == ".toml":
            return "toml"
        if e == ".json":
            return "json"
        return "unknown"

    kind = _kind_for_ext(ext)

    if os.path.exists(path):
        return path, kind

    # If user asked for TOML but it doesn't exist, try JSON.
    if path == "config/config.toml" and os.path.exists("config.json"):
        return "config.json", "json"

    # If user asked for JSON but it doesn't exist, try TOML.
    if path == "config.json" and os.path.exists("config/config.toml"):
        return "config/config.toml", "toml"

    # Otherwise, nothing found: stick with requested kind.
    return None, kind


def _default_toml_path_for(json_path: Optional[str]) -> str:
    if not json_path:
        return "config.toml"
    base, _ = os.path.splitext(json_path)
    return base + ".toml"


# -----------------------
# File I/O
# -----------------------


def _load_json_file(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_toml_file(path: str) -> Dict[str, Any]:
    if tomllib is None:
        raise RuntimeError(
            "TOML parsing requires Python 3.11+ (tomllib) or an external TOML library."
        )
    with open(path, "rb") as f:
        return tomllib.load(f)


def _write_toml_file(path: str, data: Dict[str, Any]) -> None:
    text = _toml_dumps_minimal(data)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def _maybe_migrate_json_to_toml(
    json_path: Optional[str], toml_path: str, merged_raw: Dict[str, Any]
) -> None:
    """
    Best-effort migration:
    - If TOML already exists, do nothing.
    - Otherwise, write a TOML config with the merged config (defaults + file + CLI).
    """
    try:
        if not json_path:
            return
        if os.path.exists(toml_path):
            return
        # Write TOML side-by-side to preserve the original JSON file.
        _write_toml_file(toml_path, merged_raw)
    except Exception:
        # Silent failure: config loading must remain reliable even if migration can't happen.
        return


# -----------------------
# Legacy JSON mapping
# -----------------------


def _map_legacy_json_config_to_toml_shape(flat: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map legacy `config.json` flat keys into the new TOML nested schema.

    Legacy keys observed in this repo:
    - output_folder
    - num_versions_per_job
    - model_name
    - temperature
    - top_p
    - top_k
    - max_output_tokens
    - input_resumes_folder
    - job_descriptions_folder
    - tesseract_cmd (nullable)
    - job_search_results_folder
    - max_job_results_per_search
    """
    out: Dict[str, Any] = {}
    paths: Dict[str, Any] = {}
    ai: Dict[str, Any] = {}
    processing: Dict[str, Any] = {}
    job_search: Dict[str, Any] = {}

    if "output_folder" in flat:
        paths["output_folder"] = flat["output_folder"]
    if "input_resumes_folder" in flat:
        paths["input_resumes_folder"] = flat["input_resumes_folder"]
    if "job_descriptions_folder" in flat:
        paths["job_descriptions_folder"] = flat["job_descriptions_folder"]
    if "job_search_results_folder" in flat:
        paths["job_search_results_folder"] = flat["job_search_results_folder"]

    # OCR tesseract_cmd: legacy JSON used null for "unset"; TOML uses "" for "unset".
    tesseract_cmd = flat.get("tesseract_cmd")
    if isinstance(tesseract_cmd, str) and tesseract_cmd.strip():
        paths["tesseract_cmd"] = tesseract_cmd

    if "num_versions_per_job" in flat:
        processing["num_versions_per_job"] = flat["num_versions_per_job"]

    if "model_name" in flat:
        ai["model_name"] = flat["model_name"]
    if "temperature" in flat:
        ai["temperature"] = flat["temperature"]
    if "top_p" in flat:
        ai["top_p"] = flat["top_p"]
    if "top_k" in flat:
        ai["top_k"] = flat["top_k"]
    if "max_output_tokens" in flat:
        ai["max_output_tokens"] = flat["max_output_tokens"]

    if "max_job_results_per_search" in flat:
        job_search["max_job_results_per_search"] = flat["max_job_results_per_search"]

    if paths:
        out["paths"] = paths
    if ai:
        out["ai"] = ai
    if processing:
        out["processing"] = processing
    if job_search:
        out["job_search"] = job_search

    return out


# -----------------------
# Build + normalization
# -----------------------


def _build_config(raw: Dict[str, Any]) -> Config:
    # Paths (normalize to absolute)
    output_folder = os.path.abspath(
        _deep_get(raw, ("paths", "output_folder"), DEFAULTS["paths"]["output_folder"])
    )
    input_resumes_folder = os.path.abspath(
        _deep_get(
            raw,
            ("paths", "input_resumes_folder"),
            DEFAULTS["paths"]["input_resumes_folder"],
        )
    )
    job_descriptions_folder = os.path.abspath(
        _deep_get(
            raw,
            ("paths", "job_descriptions_folder"),
            DEFAULTS["paths"]["job_descriptions_folder"],
        )
    )
    job_search_results_folder = os.path.abspath(
        _deep_get(
            raw,
            ("paths", "job_search_results_folder"),
            DEFAULTS["paths"]["job_search_results_folder"],
        )
    )

    state_file = os.path.abspath(
        _deep_get(raw, ("paths", "state_file"), DEFAULTS["paths"]["state_file"])
    )
    saved_searches_file = os.path.abspath(
        _deep_get(
            raw,
            ("paths", "saved_searches_file"),
            DEFAULTS["paths"]["saved_searches_file"],
        )
    )
    tesseract_cmd_raw = _deep_get(
        raw,
        ("paths", "tesseract_cmd"),
        DEFAULTS["paths"].get("tesseract_cmd", ""),
    )
    if isinstance(tesseract_cmd_raw, str) and tesseract_cmd_raw.strip():
        tesseract_cmd = tesseract_cmd_raw
    else:
        tesseract_cmd = None

    scoring_weights_file = os.path.abspath(
        _deep_get(
            raw,
            ("paths", "scoring_weights_file"),
            DEFAULTS["paths"]["scoring_weights_file"],
        )
    )

    # AI
    ai_provider = _deep_get(raw, ("ai", "provider"), DEFAULTS["ai"]["provider"])
    model_name = _deep_get(raw, ("ai", "model_name"), DEFAULTS["ai"]["model_name"])
    temperature = float(
        _deep_get(raw, ("ai", "temperature"), DEFAULTS["ai"]["temperature"])
    )
    top_p = float(_deep_get(raw, ("ai", "top_p"), DEFAULTS["ai"]["top_p"]))
    top_k = int(_deep_get(raw, ("ai", "top_k"), DEFAULTS["ai"]["top_k"]))
    max_output_tokens = int(
        _deep_get(raw, ("ai", "max_output_tokens"), DEFAULTS["ai"]["max_output_tokens"])
    )

    ai_agents = _deep_get(raw, ("ai", "agents"), DEFAULTS["ai"]["agents"])
    if not isinstance(ai_agents, dict):
        ai_agents = _deep_copy(DEFAULTS["ai"]["agents"])

    # Processing
    num_versions_per_job = int(
        _deep_get(
            raw,
            ("processing", "num_versions_per_job"),
            DEFAULTS["processing"]["num_versions_per_job"],
        )
    )
    iterate_until_score_reached = bool(
        _deep_get(
            raw,
            ("processing", "iterate_until_score_reached"),
            DEFAULTS["processing"]["iterate_until_score_reached"],
        )
    )
    target_score = float(
        _deep_get(
            raw, ("processing", "target_score"), DEFAULTS["processing"]["target_score"]
        )
    )
    max_iterations = int(
        _deep_get(
            raw,
            ("processing", "max_iterations"),
            DEFAULTS["processing"]["max_iterations"],
        )
    )
    min_score_delta = float(
        _deep_get(
            raw,
            ("processing", "min_score_delta"),
            DEFAULTS["processing"]["min_score_delta"],
        )
    )

    # Iteration strategy (advanced)
    iteration_strategy = (
        str(
            _deep_get(
                raw,
                ("processing", "iteration_strategy"),
                DEFAULTS["processing"]["iteration_strategy"],
            )
        )
        .strip()
        .lower()
    )
    iteration_patience = int(
        _deep_get(
            raw,
            ("processing", "iteration_patience"),
            DEFAULTS["processing"]["iteration_patience"],
        )
    )
    stop_on_regression = bool(
        _deep_get(
            raw,
            ("processing", "stop_on_regression"),
            DEFAULTS["processing"]["stop_on_regression"],
        )
    )
    max_regressions = int(
        _deep_get(
            raw,
            ("processing", "max_regressions"),
            DEFAULTS["processing"]["max_regressions"],
        )
    )

    structured_output_format = str(
        _deep_get(
            raw,
            ("processing", "structured_output_format"),
            DEFAULTS["processing"]["structured_output_format"],
        )
    ).lower()

    # Schema validation / recommendations / output layout (processing)
    schema_validation_enabled = bool(
        _deep_get(
            raw,
            ("processing", "schema_validation_enabled"),
            DEFAULTS["processing"]["schema_validation_enabled"],
        )
    )
    resume_schema_path = str(
        _deep_get(
            raw,
            ("processing", "resume_schema_path"),
            DEFAULTS["processing"]["resume_schema_path"],
        )
    )
    schema_validation_max_retries = int(
        _deep_get(
            raw,
            ("processing", "schema_validation_max_retries"),
            DEFAULTS["processing"]["schema_validation_max_retries"],
        )
    )
    recommendations_enabled = bool(
        _deep_get(
            raw,
            ("processing", "recommendations_enabled"),
            DEFAULTS["processing"]["recommendations_enabled"],
        )
    )
    recommendations_max_items = int(
        _deep_get(
            raw,
            ("processing", "recommendations_max_items"),
            DEFAULTS["processing"]["recommendations_max_items"],
        )
    )
    output_subdir_pattern = str(
        _deep_get(
            raw,
            ("processing", "output_subdir_pattern"),
            DEFAULTS["processing"]["output_subdir_pattern"],
        )
    )
    write_score_summary_file = bool(
        _deep_get(
            raw,
            ("processing", "write_score_summary_file"),
            DEFAULTS["processing"]["write_score_summary_file"],
        )
    )

    # Job search
    max_job_results_per_search = int(
        _deep_get(
            raw,
            ("job_search", "max_job_results_per_search"),
            DEFAULTS["job_search"]["max_job_results_per_search"],
        )
    )

    return Config(
        output_folder=output_folder,
        input_resumes_folder=input_resumes_folder,
        job_descriptions_folder=job_descriptions_folder,
        job_search_results_folder=job_search_results_folder,
        tesseract_cmd=tesseract_cmd,
        state_file=state_file,
        saved_searches_file=saved_searches_file,
        scoring_weights_file=scoring_weights_file,
        schema_validation_enabled=schema_validation_enabled,
        resume_schema_path=resume_schema_path,
        schema_validation_max_retries=schema_validation_max_retries,
        recommendations_enabled=recommendations_enabled,
        recommendations_max_items=recommendations_max_items,
        output_subdir_pattern=output_subdir_pattern,
        write_score_summary_file=write_score_summary_file,
        ai_provider=ai_provider,
        model_name=model_name,
        temperature=temperature,
        top_p=top_p,
        top_k=top_k,
        max_output_tokens=max_output_tokens,
        ai_agents=ai_agents,
        num_versions_per_job=num_versions_per_job,
        iterate_until_score_reached=iterate_until_score_reached,
        target_score=target_score,
        max_iterations=max_iterations,
        min_score_delta=min_score_delta,
        iteration_strategy=iteration_strategy,
        iteration_patience=iteration_patience,
        stop_on_regression=stop_on_regression,
        max_regressions=max_regressions,
        structured_output_format=structured_output_format,
        max_job_results_per_search=max_job_results_per_search,
    )


def _apply_cli_overrides(raw: Dict[str, Any], cli_args: Any) -> Dict[str, Any]:
    """
    Apply CLI overrides to the nested config.
    Only applies known keys.
    """
    data = _deep_copy(raw)
    args = vars(cli_args)

    # Path overrides
    _set_if_present(data, args, ("paths", "output_folder"), "output_folder")
    _set_if_present(
        data, args, ("paths", "input_resumes_folder"), "input_resumes_folder"
    )
    _set_if_present(
        data, args, ("paths", "job_descriptions_folder"), "job_descriptions_folder"
    )
    _set_if_present(
        data, args, ("paths", "job_search_results_folder"), "job_search_results_folder"
    )
    _set_if_present(data, args, ("paths", "tesseract_cmd"), "tesseract_cmd")
    _set_if_present(
        data, args, ("paths", "scoring_weights_file"), "scoring_weights_file"
    )

    # AI overrides
    _set_if_present(data, args, ("ai", "model_name"), "model_name")
    _set_if_present(data, args, ("ai", "temperature"), "temperature")
    _set_if_present(data, args, ("ai", "top_p"), "top_p")
    _set_if_present(data, args, ("ai", "top_k"), "top_k")
    _set_if_present(data, args, ("ai", "max_output_tokens"), "max_output_tokens")

    # Processing overrides
    _set_if_present(
        data, args, ("processing", "num_versions_per_job"), "num_versions_per_job"
    )
    _set_if_present(
        data,
        args,
        ("processing", "iterate_until_score_reached"),
        "iterate_until_score_reached",
    )
    _set_if_present(data, args, ("processing", "target_score"), "target_score")
    _set_if_present(data, args, ("processing", "max_iterations"), "max_iterations")
    _set_if_present(data, args, ("processing", "min_score_delta"), "min_score_delta")

    # Iteration strategy (advanced)
    _set_if_present(
        data, args, ("processing", "iteration_strategy"), "iteration_strategy"
    )
    _set_if_present(
        data, args, ("processing", "iteration_patience"), "iteration_patience"
    )
    _set_if_present(
        data, args, ("processing", "stop_on_regression"), "stop_on_regression"
    )
    _set_if_present(data, args, ("processing", "max_regressions"), "max_regressions")

    _set_if_present(
        data,
        args,
        ("processing", "schema_validation_enabled"),
        "schema_validation_enabled",
    )
    _set_if_present(
        data, args, ("processing", "resume_schema_path"), "resume_schema_path"
    )
    _set_if_present(
        data,
        args,
        ("processing", "schema_validation_max_retries"),
        "schema_validation_max_retries",
    )
    _set_if_present(
        data,
        args,
        ("processing", "recommendations_enabled"),
        "recommendations_enabled",
    )
    _set_if_present(
        data,
        args,
        ("processing", "recommendations_max_items"),
        "recommendations_max_items",
    )
    _set_if_present(
        data,
        args,
        ("processing", "output_subdir_pattern"),
        "output_subdir_pattern",
    )
    _set_if_present(
        data,
        args,
        ("processing", "write_score_summary_file"),
        "write_score_summary_file",
    )
    _set_if_present(
        data,
        args,
        ("processing", "structured_output_format"),
        "structured_output_format",
    )

    # Job search overrides
    _set_if_present(
        data,
        args,
        ("job_search", "max_job_results_per_search"),
        "max_job_results_per_search",
    )

    return data


def _set_if_present(
    dst: Dict[str, Any], args: Dict[str, Any], dst_path: Tuple[str, ...], arg_key: str
) -> None:
    if arg_key not in args:
        return
    value = args[arg_key]
    if value is None:
        return
    _deep_set(dst, dst_path, value)


# -----------------------
# Minimal TOML serializer
# -----------------------


def _toml_dumps_minimal(data: Dict[str, Any]) -> str:
    """
    Minimal TOML serializer for this project's config shape.
    - Supports nested dicts as tables
    - Supports lists, strings, bools, ints, floats
    - Omits None values (TOML has no null)
    """
    if not isinstance(data, dict):
        raise ValueError("TOML root must be a dict")

    lines = []
    _emit_toml_table(lines, data, path=())
    return ("\n".join(lines)).rstrip() + "\n"


def _emit_toml_table(lines: list, table: Dict[str, Any], path: Tuple[str, ...]) -> None:
    # Split primitives vs subtables
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
        lines.append(f"{k} = {_toml_format_value(primitives[k])}")

    if primitives and subtables:
        lines.append("")

    for k in sorted(subtables.keys()):
        _emit_toml_table(lines, subtables[k], path=path + (k,))
        lines.append("")

    while lines and lines[-1] == "":
        lines.pop()


def _toml_format_value(v: Any) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int) and not isinstance(v, bool):
        return str(v)
    if isinstance(v, float):
        return repr(v)
    if isinstance(v, str):
        return _toml_quote(v)
    if isinstance(v, list):
        return "[" + ", ".join(_toml_format_value(x) for x in v) + "]"
    raise ValueError(f"Unsupported TOML value type: {type(v).__name__}")


def _toml_quote(s: str) -> str:
    s = s.replace("\\", "\\\\")
    s = s.replace('"', '\\"')
    s = s.replace("\n", "\\n")
    s = s.replace("\r", "\\r")
    s = s.replace("\t", "\\t")
    return f'"{s}"'


# -----------------------
# Small dict helpers
# -----------------------


def _deep_get(d: Dict[str, Any], path: Tuple[str, ...], default: Any) -> Any:
    cur: Any = d
    for p in path:
        if not isinstance(cur, dict) or p not in cur:
            return default
        cur = cur[p]
    return cur


def _deep_set(d: Dict[str, Any], path: Tuple[str, ...], value: Any) -> None:
    cur = d
    for p in path[:-1]:
        if p not in cur or not isinstance(cur[p], dict):
            cur[p] = {}
        cur = cur[p]
    cur[path[-1]] = value


def _deep_merge(dst: Dict[str, Any], src: Dict[str, Any]) -> None:
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            _deep_merge(dst[k], v)
        else:
            dst[k] = v


def _deep_copy(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _deep_copy(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_deep_copy(v) for v in obj]
    return obj


# -----------------------
# CLI example (optional)
# -----------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ATS Checker Configuration (TOML)")
    parser.add_argument(
        "--config_file",
        type=str,
        default="config/config.toml",
        help="Path to the configuration file (TOML preferred; JSON supported for migration).",
    )

    # Common overrides (subset)
    parser.add_argument(
        "--output_folder", type=str, help="Folder to save generated output."
    )
    parser.add_argument(
        "--input_resumes_folder", type=str, help="Folder containing input resumes."
    )
    parser.add_argument(
        "--job_descriptions_folder",
        type=str,
        help="Folder containing job descriptions.",
    )
    parser.add_argument(
        "--job_search_results_folder",
        type=str,
        help="Folder to store job search results.",
    )
    parser.add_argument(
        "--scoring_weights_file", type=str, help="Path to scoring weights TOML file."
    )
    parser.add_argument(
        "--tesseract_cmd",
        type=str,
        help="Optional explicit path to the Tesseract executable for OCR (empty/unset uses system default).",
    )

    parser.add_argument(
        "--num_versions_per_job",
        type=int,
        help="Number of resume versions per job description.",
    )
    parser.add_argument(
        "--iterate_until_score_reached",
        action="store_true",
        help="Iterate until target score is reached.",
    )
    parser.add_argument(
        "--target_score", type=float, help="Target score for iterative improvement."
    )
    parser.add_argument(
        "--max_iterations",
        type=int,
        help="Maximum iterations for iterative improvement.",
    )
    parser.add_argument(
        "--min_score_delta",
        type=float,
        help="Minimum score delta required to keep iterating.",
    )

    # Iteration strategy (advanced)
    parser.add_argument(
        "--iteration_strategy",
        type=str,
        help='Iteration strategy: "best_of", "first_hit", or "patience".',
    )
    parser.add_argument(
        "--iteration_patience",
        type=int,
        help="Stop after this many consecutive non-improving iterations (patience strategy).",
    )
    parser.add_argument(
        "--stop_on_regression",
        action="store_true",
        help="Stop iteration if regressions exceed the configured threshold.",
    )
    parser.add_argument(
        "--max_regressions",
        type=int,
        help="Maximum allowed regression count before stopping (when stop_on_regression is enabled).",
    )

    parser.add_argument(
        "--structured_output_format",
        type=str,
        help='Structured output format: "json", "toml", or "both".',
    )

    # Schema validation (best-effort)
    parser.add_argument(
        "--schema_validation_enabled",
        action="store_true",
        help="Enable schema validation for AI-produced structured resume output.",
    )
    parser.add_argument(
        "--resume_schema_path",
        type=str,
        help="Path to a resume schema file used for validation (leave empty to disable).",
    )
    parser.add_argument(
        "--schema_validation_max_retries",
        type=int,
        help="Max retries to attempt schema-fixing when validation fails.",
    )

    # Recommendations
    parser.add_argument(
        "--recommendations_enabled",
        action="store_true",
        help="Enable generating actionable recommendations from score breakdowns.",
    )
    parser.add_argument(
        "--recommendations_max_items",
        type=int,
        help="Maximum number of recommendation items to generate.",
    )

    # Output layout
    parser.add_argument(
        "--output_subdir_pattern",
        type=str,
        help='Output subdirectory pattern under output_folder (e.g., "{resume_name}/{job_title}/{timestamp}").',
    )
    parser.add_argument(
        "--write_score_summary_file",
        action="store_true",
        help="Write a separate score summary file alongside outputs.",
    )

    parser.add_argument(
        "--model_name", type=str, help="Name of the generative AI model to use."
    )
    parser.add_argument(
        "--temperature", type=float, help="Controls randomness of the output."
    )
    parser.add_argument(
        "--top_p", type=float, help="Max cumulative probability of tokens to consider."
    )
    parser.add_argument("--top_k", type=int, help="Max number of tokens to consider.")
    parser.add_argument("--max_output_tokens", type=int, help="Max tokens to generate.")
    parser.add_argument(
        "--max_job_results_per_search", type=int, help="Maximum results per job search."
    )

    args = parser.parse_args()
    cfg = load_config(config_file_path=args.config_file, cli_args=args)

    print("Loaded Configuration (normalized):")
    # Print nested dict for readability
    for section, values in cfg.to_dict().items():
        print(f"\n[{section}]")
        if isinstance(values, dict):
            for k, v in values.items():
                print(f"{k} = {v}")
        else:
            print(values)
