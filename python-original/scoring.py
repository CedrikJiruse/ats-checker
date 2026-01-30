"""
Job and resume scoring module with category weights loaded from TOML.

This module is intentionally dependency-light:
- Uses stdlib `tomllib` on Python 3.11+ for reading TOML.
- Falls back to local `toml_io` module (if present) when `tomllib` is unavailable.

It provides:
- Resume quality scoring (structure/completeness/impact).
- Job posting quality scoring (clarity/completeness).
- Resume↔Job match scoring (keyword/skills overlap heuristics).
- Weight loading from a TOML file with sane defaults.

TOML weights format (recommended):

[resume.weights]
completeness = 0.30
skills_quality = 0.20
experience_quality = 0.30
impact = 0.20

[job.weights]
completeness = 0.35
clarity = 0.35
compensation_transparency = 0.15
link_quality = 0.15

[match.weights]
keyword_overlap = 0.45
skills_overlap = 0.35
role_alignment = 0.20

[overall.weights]
# Used for combining component reports into a single "iteration score"
# (e.g., when iterating on a resume until a target score is reached).
resume = 0.45
match = 0.55

Notes:
- Scores are 0..100 per category; totals are weighted averages 0..100.
- Weights are normalized per group (resume/job/match). Missing weights default to 0.
- Heuristics are deterministic and do not call any external services.
"""

from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
)

try:
    import tomllib  # Python 3.11+
except Exception:  # pragma: no cover
    tomllib = None


JsonLike = Union[Dict[str, Any], List[Any], str, int, float, bool, None]


# -------------------------
# Public data structures
# -------------------------


@dataclass(frozen=True)
class ScoreCategoryResult:
    name: str
    score: float  # 0..100
    weight: float  # normalized weight 0..1
    details: Dict[str, Any]


@dataclass(frozen=True)
class ScoreReport:
    kind: str  # "resume" | "job" | "match"
    total: float  # 0..100 weighted
    categories: List[ScoreCategoryResult]
    meta: Dict[str, Any]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind,
            "total": self.total,
            "categories": [
                {
                    "name": c.name,
                    "score": c.score,
                    "weight": c.weight,
                    "details": c.details,
                }
                for c in self.categories
            ],
            "meta": self.meta,
        }


# -------------------------
# Weight handling
# -------------------------

DEFAULT_WEIGHTS: Dict[str, Dict[str, float]] = {
    "resume": {
        "completeness": 0.30,
        "skills_quality": 0.20,
        "experience_quality": 0.30,
        "impact": 0.20,
    },
    "job": {
        "completeness": 0.35,
        "clarity": 0.35,
        "compensation_transparency": 0.15,
        "link_quality": 0.15,
    },
    "match": {
        "keyword_overlap": 0.45,
        "skills_overlap": 0.35,
        "role_alignment": 0.20,
    },
}


def load_scoring_weights(weights_toml_path: str) -> Dict[str, Dict[str, float]]:
    """
    Load scoring weights from a TOML file.

    The parser expects:
        [resume.weights], [job.weights], [match.weights]
    but is lenient: it will accept [resume] with 'weights' table, etc.

    Returns:
        dict with keys: "resume", "job", "match" -> {category: weight}
        If file is missing or malformed, returns DEFAULT_WEIGHTS (copy).
    """
    # Return a deep-ish copy so callers can safely mutate
    weights = {k: dict(v) for k, v in DEFAULT_WEIGHTS.items()}

    if not weights_toml_path:
        return weights

    if not os.path.exists(weights_toml_path):
        return weights

    try:
        doc = _toml_load_file(weights_toml_path)
    except Exception:
        return weights

    for group in ("resume", "job", "match"):
        group_tbl = doc.get(group, {})
        if not isinstance(group_tbl, dict):
            continue

        # prefer [group.weights]
        w_tbl = group_tbl.get("weights", group_tbl.get("weight", group_tbl))
        if not isinstance(w_tbl, dict):
            continue

        parsed = {}
        for k, v in w_tbl.items():
            if isinstance(k, str) and isinstance(v, (int, float)):
                parsed[k] = float(v)

        if parsed:
            weights[group].update(parsed)

    return weights


def normalize_weights(group_weights: Mapping[str, float]) -> Dict[str, float]:
    """
    Normalize weights to sum to 1.0 (ignores non-positive weights).
    If all weights are <= 0, returns 0 weights for all categories.
    """
    positive = {k: float(v) for k, v in group_weights.items() if float(v) > 0.0}
    s = sum(positive.values())
    if s <= 0.0:
        return {k: 0.0 for k in group_weights.keys()}
    return {k: (positive.get(k, 0.0) / s) for k in group_weights.keys()}


DEFAULT_OVERALL_ITERATION_WEIGHTS: Dict[str, float] = {
    "resume": 0.45,
    "match": 0.55,
}


def load_overall_iteration_weights(
    weights_toml_path: Optional[str],
) -> Dict[str, float]:
    """
    Load overall weights used to combine ScoreReports into a single iteration score.

    Expected TOML:
        [overall.weights]
        resume = 0.45
        match = 0.55

    Returns:
        Dict with keys: "resume", "match" -> float weights (not normalized).
        Falls back to DEFAULT_OVERALL_ITERATION_WEIGHTS if unavailable.
    """
    weights = dict(DEFAULT_OVERALL_ITERATION_WEIGHTS)

    if not weights_toml_path:
        return weights
    if not os.path.exists(weights_toml_path):
        return weights

    try:
        doc = _toml_load_file(weights_toml_path)
    except Exception:
        return weights

    overall = doc.get("overall", {})
    if not isinstance(overall, dict):
        return weights

    w_tbl = overall.get("weights", overall.get("weight", {}))
    if not isinstance(w_tbl, dict):
        return weights

    for k in ("resume", "match"):
        v = w_tbl.get(k)
        if isinstance(v, (int, float)):
            weights[k] = float(v)

    return weights


def compute_iteration_score(
    resume_report: ScoreReport,
    match_report: ScoreReport,
    weights_toml_path: Optional[str] = None,
) -> Tuple[float, Dict[str, Any]]:
    """
    Compute a single iteration score (0..100) from:
      - a resume quality report (ScoreReport(kind="resume"))
      - a resume↔job match report (ScoreReport(kind="match"))

    This is intended to drive "iterate until target score reached" workflows.

    Returns:
        (score, details)
    """
    raw = load_overall_iteration_weights(weights_toml_path)
    w = normalize_weights(raw)

    # If weights are all zero (misconfiguration), fall back to a simple mean.
    if (w.get("resume", 0.0) + w.get("match", 0.0)) <= 0.0:
        score = (float(resume_report.total) + float(match_report.total)) / 2.0
        return _clamp(score), {
            "resume_total": float(resume_report.total),
            "match_total": float(match_report.total),
            "weights": {"resume": 0.5, "match": 0.5},
            "raw_weights": raw,
            "fallback": "mean",
        }

    score = (float(resume_report.total) * w.get("resume", 0.0)) + (
        float(match_report.total) * w.get("match", 0.0)
    )

    return _clamp(score), {
        "resume_total": float(resume_report.total),
        "match_total": float(match_report.total),
        "weights": w,
        "raw_weights": raw,
        "fallback": None,
    }


# -------------------------
# Scoring: resume
# -------------------------


def score_resume(
    resume: Mapping[str, Any],
    weights_toml_path: Optional[str] = None,
) -> ScoreReport:
    """
    Score a resume (structured dict) across multiple categories.

    Expected resume shape (best-effort; missing keys are handled):
      - personal_info (dict): name/email/phone/linkedin/github/portfolio
      - summary (str)
      - experience (list of dicts): title/company/location/start_date/end_date/description(list[str])
      - education (list of dicts)
      - skills (list[str])
      - projects (list of dicts)
    """
    weights_raw = (
        load_scoring_weights(weights_toml_path)
        if weights_toml_path
        else {k: dict(v) for k, v in DEFAULT_WEIGHTS.items()}
    )
    w = normalize_weights(weights_raw.get("resume", {}))

    completeness_score, completeness_details = _resume_completeness(resume)
    skills_score, skills_details = _resume_skills_quality(resume)
    exp_score, exp_details = _resume_experience_quality(resume)
    impact_score, impact_details = _resume_impact(resume)

    categories = [
        ScoreCategoryResult(
            "completeness",
            completeness_score,
            w.get("completeness", 0.0),
            completeness_details,
        ),
        ScoreCategoryResult(
            "skills_quality", skills_score, w.get("skills_quality", 0.0), skills_details
        ),
        ScoreCategoryResult(
            "experience_quality",
            exp_score,
            w.get("experience_quality", 0.0),
            exp_details,
        ),
        ScoreCategoryResult(
            "impact", impact_score, w.get("impact", 0.0), impact_details
        ),
    ]

    total = _weighted_total(categories)
    return ScoreReport(
        kind="resume",
        total=total,
        categories=categories,
        meta={
            "weights_source": os.path.abspath(weights_toml_path)
            if weights_toml_path
            else None,
        },
    )


def _resume_completeness(resume: Mapping[str, Any]) -> Tuple[float, Dict[str, Any]]:
    personal = (
        resume.get("personal_info")
        if isinstance(resume.get("personal_info"), dict)
        else {}
    )
    summary = resume.get("summary")
    exp = resume.get("experience") if isinstance(resume.get("experience"), list) else []
    edu = resume.get("education") if isinstance(resume.get("education"), list) else []
    skills = resume.get("skills") if isinstance(resume.get("skills"), list) else []
    projects = (
        resume.get("projects") if isinstance(resume.get("projects"), list) else []
    )

    checks = {
        "has_name": bool(_safe_str(personal.get("name")).strip()),
        "has_email": bool(_safe_str(personal.get("email")).strip()),
        "has_summary": bool(_safe_str(summary).strip()),
        "has_experience": len(exp) > 0,
        "has_education": len(edu) > 0,
        "has_skills": len(skills) > 0,
        "has_projects": len(projects) > 0,
    }
    # Weighted checklist -> 0..100
    weights = {
        "has_name": 0.10,
        "has_email": 0.10,
        "has_summary": 0.15,
        "has_experience": 0.25,
        "has_education": 0.15,
        "has_skills": 0.20,
        "has_projects": 0.05,
    }
    score = 100.0 * sum((1.0 if checks[k] else 0.0) * weights[k] for k in checks.keys())
    return _clamp(score), {
        "checks": checks,
        "counts": {
            "experience": len(exp),
            "education": len(edu),
            "skills": len(skills),
            "projects": len(projects),
        },
    }


def _resume_skills_quality(resume: Mapping[str, Any]) -> Tuple[float, Dict[str, Any]]:
    skills = resume.get("skills") if isinstance(resume.get("skills"), list) else []
    skills_norm = [s.strip() for s in (_safe_str(x) for x in skills) if s.strip()]
    unique = sorted(set(s.lower() for s in skills_norm))

    # heuristics:
    # - enough skills: saturates at 12
    # - penalize overly long skill strings (likely sentences)
    count = len(unique)
    count_score = 100.0 * min(count / 12.0, 1.0)

    too_long = sum(1 for s in skills_norm if len(s) > 32)
    long_penalty = min(too_long * 7.5, 30.0)  # cap
    score = count_score - long_penalty

    return _clamp(score), {"unique_skill_count": count, "too_long_skills": too_long}


def _resume_experience_quality(
    resume: Mapping[str, Any],
) -> Tuple[float, Dict[str, Any]]:
    exp = resume.get("experience") if isinstance(resume.get("experience"), list) else []
    if not exp:
        return 0.0, {"reason": "no_experience_entries"}

    total_bullets = 0
    action_bullets = 0
    quantified_bullets = 0

    for entry in exp:
        if not isinstance(entry, dict):
            continue
        desc = entry.get("description", [])
        if isinstance(desc, str):
            bullets = [d.strip() for d in desc.splitlines() if d.strip()]
        elif isinstance(desc, list):
            bullets = [(_safe_str(x)).strip() for x in desc if (_safe_str(x)).strip()]
        else:
            bullets = []

        for b in bullets:
            total_bullets += 1
            if _looks_like_action_bullet(b):
                action_bullets += 1
            if _contains_number(b):
                quantified_bullets += 1

    if total_bullets == 0:
        return 15.0, {"reason": "experience_without_bullets"}

    # scoring:
    # - bullet volume saturates at 10
    vol = min(total_bullets / 10.0, 1.0) * 35.0
    # - action verbs ratio
    action_ratio = action_bullets / max(total_bullets, 1)
    action = action_ratio * 35.0
    # - quantified ratio
    quant_ratio = quantified_bullets / max(total_bullets, 1)
    quant = quant_ratio * 30.0

    score = vol + action + quant
    return _clamp(score), {
        "total_bullets": total_bullets,
        "action_bullets": action_bullets,
        "quantified_bullets": quantified_bullets,
        "action_ratio": action_ratio,
        "quantified_ratio": quant_ratio,
    }


def _resume_impact(resume: Mapping[str, Any]) -> Tuple[float, Dict[str, Any]]:
    """
    Impact focuses on quantification and outcome language (simple heuristic).
    """
    exp = resume.get("experience") if isinstance(resume.get("experience"), list) else []
    if not exp:
        return 0.0, {"reason": "no_experience_entries"}

    bullets: List[str] = []
    for entry in exp:
        if not isinstance(entry, dict):
            continue
        desc = entry.get("description", [])
        if isinstance(desc, list):
            bullets.extend(
                [(_safe_str(x)).strip() for x in desc if (_safe_str(x)).strip()]
            )
        elif isinstance(desc, str):
            bullets.extend([d.strip() for d in desc.splitlines() if d.strip()])

    if not bullets:
        return 10.0, {"reason": "no_bullets"}

    quantified = sum(1 for b in bullets if _contains_number(b))
    outcome = sum(1 for b in bullets if _contains_outcome_language(b))
    strong = sum(
        1
        for b in bullets
        if _looks_like_action_bullet(b)
        and (_contains_number(b) or _contains_outcome_language(b))
    )

    n = len(bullets)
    quantified_ratio = quantified / n
    outcome_ratio = outcome / n
    strong_ratio = strong / n

    # Weighted blend, all scaled to 0..100
    score = (quantified_ratio * 45.0) + (outcome_ratio * 35.0) + (strong_ratio * 20.0)
    return _clamp(score), {
        "bullets": n,
        "quantified": quantified,
        "outcome": outcome,
        "strong": strong,
        "quantified_ratio": quantified_ratio,
        "outcome_ratio": outcome_ratio,
        "strong_ratio": strong_ratio,
    }


# -------------------------
# Scoring: job posting
# -------------------------


def score_job(
    job: Mapping[str, Any],
    weights_toml_path: Optional[str] = None,
) -> ScoreReport:
    """
    Score a job posting (dict) across multiple categories.

    Expected job shape (best-effort):
      - title, company, location, description, url, salary, job_type, remote, posted_date
    """
    weights_raw = (
        load_scoring_weights(weights_toml_path)
        if weights_toml_path
        else {k: dict(v) for k, v in DEFAULT_WEIGHTS.items()}
    )
    w = normalize_weights(weights_raw.get("job", {}))

    completeness_score, completeness_details = _job_completeness(job)
    clarity_score, clarity_details = _job_clarity(job)
    comp_score, comp_details = _job_compensation(job)
    link_score, link_details = _job_link_quality(job)

    categories = [
        ScoreCategoryResult(
            "completeness",
            completeness_score,
            w.get("completeness", 0.0),
            completeness_details,
        ),
        ScoreCategoryResult(
            "clarity", clarity_score, w.get("clarity", 0.0), clarity_details
        ),
        ScoreCategoryResult(
            "compensation_transparency",
            comp_score,
            w.get("compensation_transparency", 0.0),
            comp_details,
        ),
        ScoreCategoryResult(
            "link_quality", link_score, w.get("link_quality", 0.0), link_details
        ),
    ]

    total = _weighted_total(categories)
    return ScoreReport(
        kind="job",
        total=total,
        categories=categories,
        meta={
            "weights_source": os.path.abspath(weights_toml_path)
            if weights_toml_path
            else None
        },
    )


def _job_completeness(job: Mapping[str, Any]) -> Tuple[float, Dict[str, Any]]:
    title = _safe_str(job.get("title")).strip()
    company = _safe_str(job.get("company")).strip()
    location = _safe_str(job.get("location")).strip()
    description = _safe_str(job.get("description")).strip()
    url = _safe_str(job.get("url")).strip()

    checks = {
        "has_title": bool(title and title.lower() != "unknown"),
        "has_company": bool(company and company.lower() != "unknown"),
        "has_location": bool(location and location.lower() != "unknown"),
        "has_description": len(description) >= 200,  # signal of a real posting
        "has_url": bool(url),
    }
    weights = {
        "has_title": 0.20,
        "has_company": 0.20,
        "has_location": 0.15,
        "has_description": 0.35,
        "has_url": 0.10,
    }
    score = 100.0 * sum((1.0 if checks[k] else 0.0) * weights[k] for k in checks.keys())
    return _clamp(score), {"checks": checks, "description_length": len(description)}


def _job_clarity(job: Mapping[str, Any]) -> Tuple[float, Dict[str, Any]]:
    desc = _safe_str(job.get("description")).strip()
    if not desc:
        return 0.0, {"reason": "missing_description"}

    # Heuristics:
    # - length-based (saturates around 1200 chars)
    # - presence of common sections/keywords (requirements/responsibilities/benefits)
    length_score = 100.0 * min(len(desc) / 1200.0, 1.0)

    section_hits = 0
    section_markers = (
        "requirements",
        "responsibilities",
        "qualifications",
        "what you will",
        "benefits",
        "nice to have",
        "about you",
        "about the role",
    )
    desc_l = desc.lower()
    for m in section_markers:
        if m in desc_l:
            section_hits += 1

    section_score = min(section_hits / 4.0, 1.0) * 100.0  # cap at 4 hits
    # Blend: more weight on length, but sections help
    score = (length_score * 0.65) + (section_score * 0.35)
    return _clamp(score), {
        "description_length": len(desc),
        "section_hits": section_hits,
    }


def _job_compensation(job: Mapping[str, Any]) -> Tuple[float, Dict[str, Any]]:
    salary = job.get("salary")
    if isinstance(salary, str) and salary.strip():
        return 100.0, {"has_salary": True}
    # If min/max amounts exist from raw JobSpy rows, they might not be in JobPosting;
    # keep this minimal.
    return 0.0, {"has_salary": False}


def _job_link_quality(job: Mapping[str, Any]) -> Tuple[float, Dict[str, Any]]:
    url = _safe_str(job.get("url")).strip()
    if not url:
        return 0.0, {"reason": "missing_url"}
    ok = bool(re.match(r"^https?://", url))
    return (100.0 if ok else 30.0), {"url": url, "looks_http": ok}


# -------------------------
# Scoring: resume-job match
# -------------------------


def score_match(
    resume: Mapping[str, Any],
    job: Mapping[str, Any],
    weights_toml_path: Optional[str] = None,
) -> ScoreReport:
    """
    Score the match between a resume and a job posting.

    This is not the same as resume quality or job quality; it measures alignment.
    """
    weights_raw = (
        load_scoring_weights(weights_toml_path)
        if weights_toml_path
        else {k: dict(v) for k, v in DEFAULT_WEIGHTS.items()}
    )
    w = normalize_weights(weights_raw.get("match", {}))

    keyword_score, keyword_details = _match_keyword_overlap(resume, job)
    skills_score, skills_details = _match_skills_overlap(resume, job)
    role_score, role_details = _match_role_alignment(resume, job)

    categories = [
        ScoreCategoryResult(
            "keyword_overlap",
            keyword_score,
            w.get("keyword_overlap", 0.0),
            keyword_details,
        ),
        ScoreCategoryResult(
            "skills_overlap", skills_score, w.get("skills_overlap", 0.0), skills_details
        ),
        ScoreCategoryResult(
            "role_alignment", role_score, w.get("role_alignment", 0.0), role_details
        ),
    ]
    total = _weighted_total(categories)
    return ScoreReport(
        kind="match",
        total=total,
        categories=categories,
        meta={
            "weights_source": os.path.abspath(weights_toml_path)
            if weights_toml_path
            else None
        },
    )


def _match_keyword_overlap(
    resume: Mapping[str, Any], job: Mapping[str, Any]
) -> Tuple[float, Dict[str, Any]]:
    job_text = " ".join(
        s
        for s in [
            _safe_str(job.get("title")),
            _safe_str(job.get("description")),
            _safe_str(job.get("company")),
            _safe_str(job.get("location")),
        ]
        if s
    )
    resume_text = _resume_as_text(resume)

    job_tokens = _keywords(job_text)
    resume_tokens = _keywords(resume_text)

    if not job_tokens:
        return 0.0, {"reason": "job_has_no_tokens"}

    overlap = job_tokens.intersection(resume_tokens)
    missing = job_tokens.difference(resume_tokens)
    ratio = len(overlap) / len(job_tokens)

    # Convert overlap ratio into a score; cap and shape slightly to avoid punishing long JDs too much.
    # sqrt makes it easier to get decent scores on large job token sets.
    score = 100.0 * math.sqrt(_clamp01(ratio))
    return _clamp(score), {
        "job_token_count": len(job_tokens),
        "resume_token_count": len(resume_tokens),
        "overlap_count": len(overlap),
        "missing_count": len(missing),
        "overlap_ratio": ratio,
        "sample_overlap": sorted(list(overlap))[:20],
        "sample_missing": sorted(list(missing))[:20],
    }


def _match_skills_overlap(
    resume: Mapping[str, Any], job: Mapping[str, Any]
) -> Tuple[float, Dict[str, Any]]:
    skills = resume.get("skills") if isinstance(resume.get("skills"), list) else []
    resume_skills = set(s.lower() for s in (_safe_str(x).strip() for x in skills) if s)

    job_text = " ".join(
        [_safe_str(job.get("title")), _safe_str(job.get("description"))]
    ).strip()
    job_tokens = _keywords(job_text)

    if not resume_skills:
        return 0.0, {"reason": "resume_has_no_skills"}

    # Skill match is a bit stricter: count skill phrases that appear in job tokens.
    matched = set()
    for sk in resume_skills:
        sk_tokens = set(_keywords(sk))
        # If skill is multi-token, require most tokens present in job tokens
        if not sk_tokens:
            continue
        if len(sk_tokens) == 1 and next(iter(sk_tokens)) in job_tokens:
            matched.add(sk)
        elif len(sk_tokens) > 1:
            hits = sum(1 for t in sk_tokens if t in job_tokens)
            if hits / len(sk_tokens) >= 0.6:
                matched.add(sk)

    ratio = len(matched) / len(resume_skills)
    score = 100.0 * _clamp01(ratio)
    return _clamp(score), {
        "resume_skill_count": len(resume_skills),
        "matched_skill_count": len(matched),
        "match_ratio": ratio,
        "sample_matched_skills": sorted(list(matched))[:20],
    }


def _match_role_alignment(
    resume: Mapping[str, Any], job: Mapping[str, Any]
) -> Tuple[float, Dict[str, Any]]:
    """
    Simple role alignment heuristic:
    - Compare job title tokens vs resume recent titles tokens.
    """
    job_title = _safe_str(job.get("title")).strip()
    if not job_title:
        return 0.0, {"reason": "missing_job_title"}

    exp = resume.get("experience") if isinstance(resume.get("experience"), list) else []
    titles: List[str] = []
    for entry in exp[:3]:  # recent-ish roles
        if isinstance(entry, dict):
            t = _safe_str(entry.get("title")).strip()
            if t:
                titles.append(t)

    if not titles:
        # Can't infer alignment without past titles; don't hard-zero it.
        return 25.0, {"reason": "missing_resume_titles"}

    job_toks = _keywords(job_title)
    if not job_toks:
        return 0.0, {"reason": "job_title_no_tokens"}

    best = 0.0
    best_title = None
    for t in titles:
        rt = _keywords(t)
        if not rt:
            continue
        overlap = len(job_toks.intersection(rt)) / len(job_toks)
        best = max(best, overlap)
        if best == overlap:
            best_title = t

    score = 100.0 * math.sqrt(_clamp01(best))
    return _clamp(score), {
        "job_title": job_title,
        "best_resume_title": best_title,
        "best_overlap_ratio": best,
    }


# -------------------------
# Utilities
# -------------------------

_STOPWORDS: Set[str] = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "but",
    "by",
    "for",
    "from",
    "has",
    "have",
    "he",
    "in",
    "is",
    "it",
    "its",
    "of",
    "on",
    "or",
    "that",
    "the",
    "their",
    "they",
    "this",
    "to",
    "was",
    "were",
    "will",
    "with",
    "you",
    "your",
    "we",
    "our",
    "us",
}

_ACTION_VERBS: Tuple[str, ...] = (
    "built",
    "created",
    "designed",
    "developed",
    "delivered",
    "implemented",
    "improved",
    "increased",
    "reduced",
    "optimized",
    "automated",
    "led",
    "managed",
    "owned",
    "shipped",
    "launched",
    "migrated",
    "refactored",
    "collaborated",
    "analyzed",
    "architected",
    "tested",
    "deployed",
)

_OUTCOME_MARKERS: Tuple[str, ...] = (
    "improved",
    "increased",
    "reduced",
    "decreased",
    "accelerated",
    "saved",
    "cut",
    "boosted",
    "grew",
    "optimized",
    "revenue",
    "cost",
    "latency",
    "throughput",
    "uptime",
    "performance",
    "efficiency",
    "scalability",
)


def _keywords(text: str) -> Set[str]:
    toks = [t for t in re.split(r"[^a-zA-Z0-9\+#]+", (text or "").lower()) if t]
    # keep short technical tokens like "c", "c++", "c#"? The split keeps +/#; filter lightly.
    cleaned = set()
    for t in toks:
        if t in _STOPWORDS:
            continue
        if len(t) <= 2 and t not in (
            "c",
            "go",
            "ai",
            "ml",
            "ui",
            "ux",
            "qa",
            "c#",
            "c++",
        ):
            continue
        cleaned.add(t)
    return cleaned


def _resume_as_text(resume: Mapping[str, Any]) -> str:
    parts: List[str] = []
    personal = resume.get("personal_info")
    if isinstance(personal, dict):
        parts.extend(
            [
                _safe_str(personal.get("name")),
                _safe_str(personal.get("headline")),
                _safe_str(personal.get("location")),
            ]
        )

    parts.append(_safe_str(resume.get("summary")))

    skills = resume.get("skills")
    if isinstance(skills, list):
        parts.extend([_safe_str(s) for s in skills])

    exp = resume.get("experience")
    if isinstance(exp, list):
        for e in exp:
            if not isinstance(e, dict):
                continue
            parts.extend(
                [
                    _safe_str(e.get("title")),
                    _safe_str(e.get("company")),
                    _safe_str(e.get("location")),
                ]
            )
            desc = e.get("description")
            if isinstance(desc, list):
                parts.extend([_safe_str(x) for x in desc])
            elif isinstance(desc, str):
                parts.append(desc)

    edu = resume.get("education")
    if isinstance(edu, list):
        for e in edu:
            if not isinstance(e, dict):
                continue
            parts.extend([_safe_str(e.get("degree")), _safe_str(e.get("institution"))])

    proj = resume.get("projects")
    if isinstance(proj, list):
        for p in proj:
            if not isinstance(p, dict):
                continue
            parts.extend(
                [
                    _safe_str(p.get("name")),
                    _safe_str(p.get("description")),
                    _safe_str(p.get("link")),
                ]
            )

    return "\n".join([p for p in parts if p and p.strip()])


def _looks_like_action_bullet(bullet: str) -> bool:
    b = (bullet or "").strip().lower()
    if not b:
        return False
    # crude: starts with action verb or includes verb early
    first = re.split(r"\s+", b, maxsplit=1)[0]
    if first in _ACTION_VERBS:
        return True
    for v in _ACTION_VERBS:
        if b.startswith(v + " "):
            return True
    return False


def _contains_number(s: str) -> bool:
    return bool(re.search(r"\b\d+(\.\d+)?%?\b", s or ""))


def _contains_outcome_language(s: str) -> bool:
    t = (s or "").lower()
    return any(m in t for m in _OUTCOME_MARKERS)


def _safe_str(x: Any) -> str:
    if x is None:
        return ""
    if isinstance(x, str):
        return x
    try:
        return str(x)
    except Exception:
        return ""


def _clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    if math.isnan(x) or math.isinf(x):
        return lo
    return max(lo, min(hi, float(x)))


def _clamp01(x: float) -> float:
    if math.isnan(x) or math.isinf(x):
        return 0.0
    return max(0.0, min(1.0, float(x)))


def _weighted_total(categories: Sequence[ScoreCategoryResult]) -> float:
    total_weight = sum(c.weight for c in categories)
    if total_weight <= 0.0:
        # No weights configured => treat as unweighted mean if any categories exist.
        if not categories:
            return 0.0
        return _clamp(sum(c.score for c in categories) / len(categories))
    acc = 0.0
    for c in categories:
        acc += c.score * c.weight
    # weights already normalized in caller, but be defensive:
    return _clamp(acc / max(total_weight, 1e-12))


def _toml_load_file(path: str) -> Dict[str, Any]:
    """
    Load TOML using stdlib `tomllib` when available.
    Falls back to local `toml_io` (if present).
    """
    if tomllib is not None:
        with open(path, "rb") as f:
            data = tomllib.load(f)
        if isinstance(data, dict):
            return data
        return {}

    # fallback
    try:
        import toml_io  # type: ignore

        data = toml_io.load(path)
        return data if isinstance(data, dict) else {}
    except Exception as e:
        raise RuntimeError(
            "TOML parsing unavailable (missing tomllib and toml_io)"
        ) from e
