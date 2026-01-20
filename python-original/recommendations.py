"""
Heuristic recommendations generator based on score breakdowns and missing keywords.

This module is intentionally deterministic and dependency-light. It consumes the score
breakdown dictionaries produced by `scoring.py` (or embedded into a resume JSON under
`_scoring`) and returns actionable, human-readable recommendations.

Expected inputs (best-effort; this module is tolerant of missing keys):
- A "score_details" dict like the one returned by ResumeProcessor._score_for_iteration:
    {
      "mode": "resume_only" | "resume_plus_match",
      "resume_report": {"total": ..., "categories": [...]},
      "match_report": {"total": ..., "categories": [...]},
      "combined": {"resume_total": ..., "match_total": ..., ...}
    }

- Or a resume JSON object containing:
    {"_scoring": { ...same structure... }}

Additionally, if match_report category details include "sample_missing" from keyword_overlap,
those will be used to suggest missing keywords.

Usage:
    from recommendations import generate_recommendations

    recs = generate_recommendations(
        scoring_payload=score_details_or_resume_obj,
        max_items=5
    )

Notes:
- This does NOT call any external services.
- It does NOT modify resumes; it only suggests what to change.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union

JsonObj = Dict[str, Any]


@dataclass(frozen=True)
class Recommendation:
    """A single recommendation with optional rationale and metadata."""

    message: str
    reason: Optional[str] = None
    severity: str = "info"  # "info" | "warn" | "high"
    meta: Optional[Dict[str, Any]] = None

    def as_dict(self) -> Dict[str, Any]:
        out = {"message": self.message, "severity": self.severity}
        if self.reason:
            out["reason"] = self.reason
        if self.meta:
            out["meta"] = self.meta
        return out


def generate_recommendations(
    scoring_payload: Union[JsonObj, None],
    max_items: int = 5,
    *,
    low_score_threshold: float = 60.0,
) -> List[str]:
    """
    Generate heuristic recommendations as a list of strings.

    Args:
        scoring_payload:
            - score_details dict (from ResumeProcessor._score_for_iteration), OR
            - resume object containing `_scoring`, OR
            - `_scoring` object itself.
        max_items: Maximum number of recommendations to return.
        low_score_threshold: Categories below this score are considered "needs work".

    Returns:
        List of recommendation strings (ordered by estimated impact).
    """
    recs = generate_recommendations_detailed(
        scoring_payload=scoring_payload,
        max_items=max_items,
        low_score_threshold=low_score_threshold,
    )
    return [r.message for r in recs]


def generate_recommendations_detailed(
    scoring_payload: Union[JsonObj, None],
    max_items: int = 5,
    *,
    low_score_threshold: float = 60.0,
) -> List[Recommendation]:
    """
    Generate heuristic recommendations as structured objects.

    Same behavior as `generate_recommendations`, but returns Recommendation objects.
    """
    max_items = int(max_items) if max_items is not None else 5
    if max_items <= 0:
        return []

    scoring = _extract_scoring(scoring_payload)
    if not scoring:
        return [
            Recommendation(
                message="No scoring data found. Enable scoring or ensure `_scoring` is embedded in structured outputs.",
                severity="warn",
            )
        ][:max_items]

    resume_report = scoring.get("resume_report") or scoring.get("resume")
    match_report = scoring.get("match_report") or scoring.get("match")
    mode = scoring.get("mode")

    rec_list: List[Recommendation] = []

    # 1) High-level guidance based on mode
    if mode == "resume_plus_match":
        rec_list.append(
            Recommendation(
                message="Prioritize changes that improve match to the job description (keywords, requirements coverage) without inventing experience.",
                severity="info",
                reason="match_mode",
            )
        )
    else:
        rec_list.append(
            Recommendation(
                message="Prioritize resume clarity and impact (strong bullets, quantified outcomes, complete sections).",
                severity="info",
                reason="resume_only_mode",
            )
        )

    # 2) Category-driven recommendations
    rec_list.extend(
        _recommend_from_resume_report(
            resume_report, low_score_threshold=low_score_threshold
        )
    )
    rec_list.extend(
        _recommend_from_match_report(
            match_report, low_score_threshold=low_score_threshold
        )
    )

    # 3) Missing keyword suggestions (from match_report.keyword_overlap details)
    missing_keywords = _extract_missing_keywords(match_report)
    if missing_keywords:
        chunks = _chunk(missing_keywords, 8)
        # Only add up to 2 "missing keyword" recs to avoid spam.
        for chunk in chunks[:2]:
            rec_list.append(
                Recommendation(
                    message=(
                        "Consider adding these job-relevant keywords *only if they are truthful for you*: "
                        + ", ".join(chunk)
                        + "."
                    ),
                    severity="warn",
                    reason="missing_keywords",
                    meta={"keywords": chunk},
                )
            )

    # 4) De-duplicate and prioritize
    rec_list = _dedupe(recs=rec_list)

    # Sort by severity then by whether it targets low-score categories
    rec_list = _prioritize(rec_list)

    return rec_list[:max_items]


# -----------------------------
# Extractors / Normalizers
# -----------------------------


def _extract_scoring(payload: Union[JsonObj, None]) -> JsonObj:
    """
    Accepts:
    - full resume object -> use resume["_scoring"]
    - score details object -> use as-is
    - _scoring object -> use as-is
    """
    if not isinstance(payload, dict):
        return {}

    if "_scoring" in payload and isinstance(payload.get("_scoring"), dict):
        return payload["_scoring"]  # type: ignore[return-value]

    # If it "looks like" score_details, accept it.
    if any(k in payload for k in ("resume_report", "match_report", "combined", "mode")):
        return payload

    # If it "looks like" the scoring object itself (iteration_score + reports)
    if any(k in payload for k in ("iteration_score", "resume", "match", "job")):
        return payload

    return {}


def _extract_categories(report: Any) -> List[Dict[str, Any]]:
    if not isinstance(report, dict):
        return []
    cats = report.get("categories")
    if isinstance(cats, list):
        return [c for c in cats if isinstance(c, dict)]
    return []


def _extract_total(report: Any) -> Optional[float]:
    if not isinstance(report, dict):
        return None
    t = report.get("total")
    if isinstance(t, (int, float)):
        return float(t)
    # sometimes stored as "score"
    s = report.get("score")
    if isinstance(s, (int, float)):
        return float(s)
    return None


def _extract_missing_keywords(match_report: Any) -> List[str]:
    """
    Pull `sample_missing` from the `keyword_overlap` category details if present.
    """
    cats = _extract_categories(match_report)
    for c in cats:
        if c.get("name") != "keyword_overlap":
            continue
        details = c.get("details")
        if isinstance(details, dict):
            missing = details.get("sample_missing")
            if isinstance(missing, list):
                out = []
                for x in missing:
                    if isinstance(x, str) and x.strip():
                        out.append(x.strip())
                return out
    return []


# -----------------------------
# Recommendation logic
# -----------------------------


def _recommend_from_resume_report(
    resume_report: Any, *, low_score_threshold: float
) -> List[Recommendation]:
    recs: List[Recommendation] = []
    if not isinstance(resume_report, dict):
        return recs

    total = _extract_total(resume_report)
    if total is not None and total < low_score_threshold:
        recs.append(
            Recommendation(
                message="Your resume quality score is low. Focus on completeness, strong experience bullets, and measurable impact.",
                severity="high",
                reason="resume_total_low",
                meta={"resume_total": total},
            )
        )

    for cat in _extract_categories(resume_report):
        name = cat.get("name")
        score = cat.get("score")
        if not isinstance(name, str) or not isinstance(score, (int, float)):
            continue

        s = float(score)
        if s >= low_score_threshold:
            continue

        if name == "completeness":
            recs.append(
                Recommendation(
                    message="Fill in missing core sections: name, email, summary, experience, education, skills. Ensure each experience entry has bullet points.",
                    severity="high",
                    reason="resume_completeness_low",
                )
            )

        elif name == "skills_quality":
            recs.append(
                Recommendation(
                    message="Refine your skills section: keep skills as short keywords (not sentences), remove duplicates, and aim for ~10–15 relevant skills.",
                    severity="warn",
                    reason="resume_skills_quality_low",
                )
            )

        elif name == "experience_quality":
            recs.append(
                Recommendation(
                    message="Improve experience bullets: start with action verbs, include tools/tech, and add outcomes. Aim for 3–6 bullets per role.",
                    severity="high",
                    reason="resume_experience_quality_low",
                )
            )

        elif name == "impact":
            recs.append(
                Recommendation(
                    message="Increase impact: add quantified results (%, $, time saved, scale) and outcome language (performance, reliability, cost, latency).",
                    severity="high",
                    reason="resume_impact_low",
                )
            )

        else:
            recs.append(
                Recommendation(
                    message=f"Improve '{name}' (score {s:.1f}). Focus on clarity, accuracy, and concision.",
                    severity="warn",
                    reason="resume_category_low",
                    meta={"category": name, "score": s},
                )
            )

    return recs


def _recommend_from_match_report(
    match_report: Any, *, low_score_threshold: float
) -> List[Recommendation]:
    recs: List[Recommendation] = []
    if not isinstance(match_report, dict):
        return recs

    total = _extract_total(match_report)
    if total is not None and total < low_score_threshold:
        recs.append(
            Recommendation(
                message="Your resume-to-job match score is low. Tailor your summary, skills, and top bullets to mirror the job’s wording and requirements.",
                severity="high",
                reason="match_total_low",
                meta={"match_total": total},
            )
        )

    for cat in _extract_categories(match_report):
        name = cat.get("name")
        score = cat.get("score")
        if not isinstance(name, str) or not isinstance(score, (int, float)):
            continue

        s = float(score)
        if s >= low_score_threshold:
            continue

        if name == "keyword_overlap":
            recs.append(
                Recommendation(
                    message="Improve keyword alignment: incorporate key terms from the job description into your skills and experience bullets (truthfully).",
                    severity="high",
                    reason="match_keyword_overlap_low",
                )
            )

        elif name == "skills_overlap":
            recs.append(
                Recommendation(
                    message="Improve skills match: ensure your skills section includes the job’s required tools/technologies you actually know, using the exact names.",
                    severity="warn",
                    reason="match_skills_overlap_low",
                )
            )

        elif name == "role_alignment":
            recs.append(
                Recommendation(
                    message="Improve role alignment: adjust your headline/summary and the first 1–2 experience entries to clearly match the target role title.",
                    severity="warn",
                    reason="match_role_alignment_low",
                )
            )

        else:
            recs.append(
                Recommendation(
                    message=f"Improve match category '{name}' (score {s:.1f}). Tailor content to the job’s responsibilities and requirements.",
                    severity="warn",
                    reason="match_category_low",
                    meta={"category": name, "score": s},
                )
            )

    return recs


# -----------------------------
# Helpers
# -----------------------------


def _dedupe(recs: Sequence[Recommendation]) -> List[Recommendation]:
    seen = set()
    out: List[Recommendation] = []
    for r in recs:
        key = (r.message.strip().lower(), (r.reason or "").strip().lower())
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def _prioritize(recs: Sequence[Recommendation]) -> List[Recommendation]:
    severity_rank = {"high": 0, "warn": 1, "info": 2}
    return sorted(
        list(recs),
        key=lambda r: (
            severity_rank.get(r.severity, 9),
            0 if (r.reason or "").endswith("_low") else 1,
            len(r.message),
        ),
    )


def _chunk(items: List[str], n: int) -> List[List[str]]:
    if n <= 0:
        return [items]
    out: List[List[str]] = []
    cur: List[str] = []
    for x in items:
        cur.append(x)
        if len(cur) >= n:
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out
