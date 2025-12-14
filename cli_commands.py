"""
ats-checker/cli_commands.py

CLI subcommands for:
- dry-run scoring (resume-only and resume↔job match) without using the interactive menu
- ranking saved job result files by job_score (and optionally exporting top jobs)

This file is intentionally dependency-light:
- Uses stdlib argparse
- Uses stdlib tomllib on Python 3.11+ (falls back to project-local toml_io)
- Uses existing project modules: config.py, scoring.py, job_scraper_manager.py

Examples
--------
Score a structured resume TOML/JSON (no AI calls):
  python cli_commands.py score-resume --resume output/my_resume_generic_enhanced.toml

Score match between a structured resume and a job description text:
  python cli_commands.py score-match --resume output/my_resume_generic_enhanced.toml --job workspace/job_descriptions/foo.txt

Write scoring back into the structured resume file:
  python cli_commands.py score-match --resume output/my_resume_generic_enhanced.toml --job workspace/job_descriptions/foo.txt --write-back

Rank a job results file:
  python cli_commands.py rank-jobs --results workspace/job_search_results/linkedin_20250101_120000.toml --top 20

Export top-scored jobs to job descriptions:
  python cli_commands.py rank-jobs --results workspace/job_search_results/linkedin_20250101_120000.toml --export-top 10
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict
from typing import Any, Dict, List, Optional, Tuple

from config import load_config
from job_scraper_base import JobPosting
from job_scraper_manager import JobScraperManager
from scoring import compute_iteration_score, score_job, score_match, score_resume

try:
    import tomllib  # Python 3.11+
except Exception:  # pragma: no cover
    tomllib = None

try:
    import toml_io  # project-local TOML read/write
except Exception:  # pragma: no cover
    toml_io = None


# -----------------------------
# File loading / writing helpers
# -----------------------------


def _load_toml(path: str) -> Dict[str, Any]:
    if tomllib is not None:
        with open(path, "rb") as f:
            data = tomllib.load(f)
        return data if isinstance(data, dict) else {}
    if toml_io is None:
        raise RuntimeError("TOML parsing unavailable (missing tomllib and toml_io).")
    data = toml_io.load(path)
    return data if isinstance(data, dict) else {}


def _dump_toml(path: str, data: Dict[str, Any]) -> None:
    if toml_io is None:
        raise RuntimeError("TOML writing unavailable (missing toml_io).")
    toml_io.dump(data, path)


def _load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _dump_json(path: str, data: Any) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _read_text_file(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def _extract_job_description_text(path: str) -> str:
    """
    Minimal job description extractor.

    Supported:
    - .txt / .md / .tex: read as text
    - .pdf: extract via PyPDF2 if installed
    - fallback: read as text with errors ignored
    """
    ext = os.path.splitext(path)[1].lower()
    if ext in (".txt", ".md", ".tex"):
        return _read_text_file(path)

    if ext == ".pdf":
        try:
            import PyPDF2  # type: ignore
        except Exception as e:
            raise RuntimeError(
                "PDF extraction requires PyPDF2. Install it or convert PDF to text."
            ) from e
        with open(path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            parts = []
            for page in reader.pages:
                parts.append(page.extract_text() or "")
        return "\n".join(parts)

    # fallback
    return _read_text_file(path)


def _load_structured_resume(path: str) -> Dict[str, Any]:
    """
    Load a structured resume produced by the tool (JSON or TOML).
    The root must be a JSON object/dict.
    """
    ext = os.path.splitext(path)[1].lower()
    if ext == ".json":
        obj = _load_json(path)
        if not isinstance(obj, dict):
            raise ValueError("Structured resume JSON root must be an object/dict.")
        return obj
    if ext == ".toml":
        obj = _load_toml(path)
        if not isinstance(obj, dict):
            raise ValueError("Structured resume TOML root must be a table/object.")
        return obj

    raise ValueError("Unsupported resume file extension. Use .json or .toml.")


def _write_structured_resume(path: str, obj: Dict[str, Any]) -> None:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".json":
        _dump_json(path, obj)
        return
    if ext == ".toml":
        _dump_toml(path, obj)
        return
    raise ValueError("Unsupported output extension. Use .json or .toml.")


# -----------------------------
# Printing / formatting
# -----------------------------


def _fmt_float(x: Any) -> str:
    if isinstance(x, (int, float)):
        return f"{float(x):.2f}"
    return "N/A"


def _print_score_report(title: str, report: Dict[str, Any]) -> None:
    total = report.get("total")
    print(f"{title}: {_fmt_float(total)}")
    cats = report.get("categories")
    if isinstance(cats, list) and cats:
        for c in cats:
            if not isinstance(c, dict):
                continue
            name = c.get("name", "?")
            score = c.get("score")
            weight = c.get("weight")
            if weight is not None:
                print(f"  - {name}: {_fmt_float(score)} (weight {_fmt_float(weight)})")
            else:
                print(f"  - {name}: {_fmt_float(score)}")


def _print_iteration_score(payload: Dict[str, Any]) -> None:
    overall = payload.get("iteration_score")
    print(f"Overall iteration score: {_fmt_float(overall)}")

    rr = payload.get("resume_report") or payload.get("resume")
    mr = payload.get("match_report") or payload.get("match")
    jr = payload.get("job_report") or payload.get("job")

    if isinstance(rr, dict):
        _print_score_report("Resume score", rr)
    if isinstance(mr, dict):
        _print_score_report("Match score", mr)
    if isinstance(jr, dict):
        _print_score_report("Job score", jr)

    # Helpful keyword overlap details (if present)
    if isinstance(mr, dict):
        cats = mr.get("categories")
        if isinstance(cats, list):
            for c in cats:
                if not isinstance(c, dict):
                    continue
                if c.get("name") != "keyword_overlap":
                    continue
                details = c.get("details")
                if not isinstance(details, dict):
                    continue
                missing = details.get("sample_missing")
                overlap = details.get("sample_overlap")
                if isinstance(overlap, list) and overlap:
                    print(
                        f"Matched keywords (sample): {', '.join(str(x) for x in overlap[:20])}"
                    )
                if isinstance(missing, list) and missing:
                    print(
                        f"Missing keywords (sample): {', '.join(str(x) for x in missing[:20])}"
                    )
                break


# -----------------------------
# Subcommands
# -----------------------------


def cmd_score_resume(args: argparse.Namespace) -> int:
    cfg = load_config(args.config_file)

    resume_path = args.resume
    weights_path = args.weights or cfg.scoring_weights_file

    resume_obj = _load_structured_resume(resume_path)
    resume_report = score_resume(resume_obj, weights_toml_path=weights_path).as_dict()

    scoring_blob: Dict[str, Any] = {
        "iteration_score": float(resume_report.get("total", 0.0)),
        "mode": "resume_only",
        "resume_report": resume_report,
    }

    if args.write_back:
        resume_obj["_scoring"] = scoring_blob
        _write_structured_resume(resume_path, resume_obj)
        print(f"Wrote _scoring into: {resume_path}")

    if args.json:
        print(json.dumps(scoring_blob, indent=2, ensure_ascii=False))
    else:
        _print_iteration_score(scoring_blob)

    return 0


def cmd_score_match(args: argparse.Namespace) -> int:
    cfg = load_config(args.config_file)

    resume_path = args.resume
    job_path = args.job
    weights_path = args.weights or cfg.scoring_weights_file

    resume_obj = _load_structured_resume(resume_path)
    job_text = _extract_job_description_text(job_path)

    # Minimal job dict compatible with scoring functions
    job_title = os.path.splitext(os.path.basename(job_path))[0]
    job_obj: Dict[str, Any] = {
        "title": job_title,
        "company": "",
        "location": "",
        "description": job_text,
        "url": "",
        "source": "job_description",
    }

    resume_report = score_resume(resume_obj, weights_toml_path=weights_path)
    match_report = score_match(resume_obj, job_obj, weights_toml_path=weights_path)
    iteration_score, combine_details = compute_iteration_score(
        resume_report=resume_report,
        match_report=match_report,
        weights_toml_path=weights_path,
    )

    scoring_blob: Dict[str, Any] = {
        "iteration_score": float(iteration_score),
        "mode": "resume_plus_match",
        "resume_report": resume_report.as_dict(),
        "match_report": match_report.as_dict(),
        "combined": combine_details,
    }

    if args.write_back:
        resume_obj["_scoring"] = scoring_blob
        _write_structured_resume(resume_path, resume_obj)
        print(f"Wrote _scoring into: {resume_path}")

    if args.json:
        print(json.dumps(scoring_blob, indent=2, ensure_ascii=False))
    else:
        _print_iteration_score(scoring_blob)

    return 0


def cmd_rank_jobs(args: argparse.Namespace) -> int:
    cfg = load_config(args.config_file)
    manager = JobScraperManager(
        results_folder=cfg.job_search_results_folder,
        saved_searches_path=cfg.saved_searches_file,
    )

    results_path = args.results
    if not os.path.exists(results_path):
        # convenience: allow passing filename relative to results folder
        candidate = os.path.join(cfg.job_search_results_folder, results_path)
        if os.path.exists(candidate):
            results_path = candidate
        else:
            raise FileNotFoundError(results_path)

    ranked = manager.rank_jobs_in_results(
        results_path, top_n=args.top, recompute_missing_scores=not args.no_recompute
    )

    if args.json:
        # Keep it machine readable
        print(json.dumps(ranked, indent=2, ensure_ascii=False))
    else:
        if not ranked:
            print("No jobs found in results file.")
            return 0

        print(f"Results file: {results_path}")
        print(f"Showing top {len(ranked)} jobs by score:\n")

        for entry in ranked:
            job = entry.get("job", {}) if isinstance(entry, dict) else {}
            score = entry.get("job_score")
            rank = entry.get("rank")
            title = job.get("title", "")
            company = job.get("company", "")
            location = job.get("location", "")
            url = job.get("url", "")

            print(f"{rank}. {title}")
            print(f"   score: {_fmt_float(score)}")
            if company:
                print(f"   company: {company}")
            if location:
                print(f"   location: {location}")
            if url:
                print(f"   url: {url}")
            print("")

    # Optional: export top-scored jobs to job descriptions folder
    if args.export_top:
        n = int(args.export_top)
        if n <= 0:
            return 0

        to_export = ranked[:n]
        allowed = set(JobPosting.__dataclass_fields__.keys())
        postings: List[JobPosting] = []
        for entry in to_export:
            job = entry.get("job", {}) if isinstance(entry, dict) else {}
            if not isinstance(job, dict):
                continue
            filtered = {k: v for k, v in job.items() if k in allowed}
            try:
                postings.append(JobPosting(**filtered))
            except Exception:
                continue

        exported = manager.export_to_job_descriptions(
            postings, cfg.job_descriptions_folder
        )
        print(f"Exported {exported} job(s) to: {cfg.job_descriptions_folder}")

    return 0


# -----------------------------
# Argument parsing
# -----------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ats-checker",
        description="ATS Checker CLI utilities (non-interactive subcommands).",
    )
    parser.add_argument(
        "--config_file",
        type=str,
        default="config/config.toml",
        help="Path to config TOML file.",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # score-resume
    p_score_resume = sub.add_parser(
        "score-resume", help="Dry-run score a structured resume (JSON/TOML)."
    )
    p_score_resume.add_argument(
        "--resume", required=True, help="Path to structured resume (.json or .toml)."
    )
    p_score_resume.add_argument(
        "--weights",
        default=None,
        help="Path to scoring weights TOML (defaults to config paths.scoring_weights_file).",
    )
    p_score_resume.add_argument(
        "--write-back",
        action="store_true",
        help="Write the scoring payload into the resume file under `_scoring`.",
    )
    p_score_resume.add_argument(
        "--json",
        action="store_true",
        help="Print scoring payload as JSON (machine-readable).",
    )
    p_score_resume.set_defaults(func=cmd_score_resume)

    # score-match
    p_score_match = sub.add_parser(
        "score-match",
        help="Dry-run score a structured resume against a job description (resume+match).",
    )
    p_score_match.add_argument(
        "--resume", required=True, help="Path to structured resume (.json or .toml)."
    )
    p_score_match.add_argument(
        "--job",
        required=True,
        help="Path to job description (.txt/.md/.pdf supported).",
    )
    p_score_match.add_argument(
        "--weights",
        default=None,
        help="Path to scoring weights TOML (defaults to config paths.scoring_weights_file).",
    )
    p_score_match.add_argument(
        "--write-back",
        action="store_true",
        help="Write the scoring payload into the resume file under `_scoring`.",
    )
    p_score_match.add_argument(
        "--json",
        action="store_true",
        help="Print scoring payload as JSON (machine-readable).",
    )
    p_score_match.set_defaults(func=cmd_score_match)

    # rank-jobs
    p_rank = sub.add_parser(
        "rank-jobs", help="Rank jobs in a saved job results file by job_score."
    )
    p_rank.add_argument(
        "--results",
        required=True,
        help="Path to results file (.toml preferred; .json legacy supported). "
        "If a filename is provided, it is resolved relative to paths.job_search_results_folder.",
    )
    p_rank.add_argument(
        "--top",
        type=int,
        default=20,
        help="How many jobs to display (default: 20).",
    )
    p_rank.add_argument(
        "--no-recompute",
        action="store_true",
        help="Do not recompute job_score when missing.",
    )
    p_rank.add_argument(
        "--export-top",
        type=int,
        default=0,
        help="If set, export top N jobs (by score) into paths.job_descriptions_folder.",
    )
    p_rank.add_argument(
        "--json",
        action="store_true",
        help="Print ranked entries as JSON (machine-readable).",
    )
    p_rank.set_defaults(func=cmd_rank_jobs)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        return int(args.func(args))
    except KeyboardInterrupt:
        return 130
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
