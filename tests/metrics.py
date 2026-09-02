"""
Metric utilities for MVP validation (Modulo 3.2).

Pure, dependency-free functions. No LLM / network access.

Grade scale (see AGENTS.md):
    Mal -> 3, Regular -> 5, Bien -> 7, Excepcional -> 9
"""
import re
from collections import Counter

# Ordered levels (low -> high). Used for agreement/adjacency metrics.
GRADE_ORDER = {"Mal": 0, "Regular": 1, "Bien": 2, "Excepcional": 3}
GRADE_NUMERIC = {"Mal": 3, "Regular": 5, "Bien": 7, "Excepcional": 9}
GRADE_LEVELS = list(GRADE_ORDER.keys())


def grade_to_numeric(grade: str) -> int:
    return GRADE_NUMERIC.get(grade, 0)


def grade_level(grade: str) -> int:
    return GRADE_ORDER.get(grade, -1)


def normalize_grade(raw) -> str:
    """Coerce a Grade enum or string to one of the canonical labels."""
    val = getattr(raw, "value", raw)
    return str(val).strip()


def exact_match_rate(ours, refs) -> float:
    """% of cases where our grade == reference grade (exact)."""
    if not ours:
        return 0.0
    n = len(ours)
    m = sum(1 for o, r in zip(ours, refs) if normalize_grade(o) == normalize_grade(r))
    return round(m / n * 100, 1)


def adjacent_match_rate(ours, refs, tol: int = 1) -> float:
    """% of cases within `tol` level steps of the reference (1 step = adjacent grade)."""
    if not ours:
        return 0.0
    n = len(ours)
    m = sum(1 for o, r in zip(ours, refs)
            if abs(grade_level(normalize_grade(o)) - grade_level(normalize_grade(r))) <= tol)
    return round(m / n * 100, 1)


def mean_abs_error(ours, refs) -> float:
    """Mean absolute error on the 3/5/7/9 numeric scale (0 = perfect, 6 = worst)."""
    if not ours:
        return 0.0
    errs = [abs(grade_to_numeric(normalize_grade(o)) - grade_to_numeric(normalize_grade(r)))
            for o, r in zip(ours, refs)]
    return round(sum(errs) / len(errs), 3)


def cohen_kappa(ours, refs) -> float:
    """Cohen's kappa (inter-rater agreement) for 4 unordered categories."""
    pairs = [(normalize_grade(o), normalize_grade(r)) for o, r in zip(ours, refs)]
    n = len(pairs)
    if n == 0:
        return 0.0
    obs = Counter(pairs)
    po = sum(c for (a, b), c in obs.items() if a == b) / n

    our_counts = Counter(a for a, _ in pairs)
    ref_counts = Counter(b for _, b in pairs)
    pe = sum((our_counts[g] / n) * (ref_counts[g] / n) for g in GRADE_LEVELS)

    if pe == 1.0:
        return 1.0
    return round((po - pe) / (1 - pe), 3)


def confusion_matrix(ours, refs) -> dict:
    """rows = reference, cols = ours. keys 'reference->ours'."""
    mat = {f"{r}/{o}": 0 for r in GRADE_LEVELS for o in GRADE_LEVELS}
    for o, r in zip(ours, refs):
        mat[f"{normalize_grade(r)}/{normalize_grade(o)}"] += 1
    return mat


def consistency(grade_lists) -> dict:
    """Self-consistency: for a set of repeated grades on the SAME input,
    report the fraction of runs matching the most frequent (mode) grade,
    and the number of distinct grades observed."""
    modes = []
    for gl in grade_lists:
        if not gl:
            modes.append(None)
            continue
        cnt = Counter(normalize_grade(g) for g in gl)
        mode, cnt_max = cnt.most_common(1)[0]
        modes.append(cnt_max / len(gl))
    n = len(grade_lists)
    return {
        "inputs": n,
        "avg_mode_agreement": round(sum(m for m in modes if m is not None) / n, 3) if n else 0.0,
        "avg_distinct_grades": round(
            sum(len(set(normalize_grade(g) for g in gl)) for gl in grade_lists if gl) / n, 3) if n else 0.0,
    }


# --------------------------------------------------------------------------- #
# Report format checks (category B — deterministic, no LLM)
# --------------------------------------------------------------------------- #
REQUIRED_SECTIONS = [
    "calificaci",            # "Calificación Global"
    "resumen",              # "Resumen de ..."
]
TITLE_RE = re.compile(r"^#\s+\S", re.M)
CALIF_RE = re.compile(r"calificación\s+global", re.I)
GRADE_RE = re.compile(r"\b(Mal|Regular|Bien|Excepcional)\b")


def looks_spanish(text: str) -> bool:
    """Cheap heuristic: a student-facing report must be Spanish (Spain)."""
    spanish_markers = [
        "resumen", "alumno", "ejercicio", "calificación", "global",
        "completitud", "código", "problema", "recomendación", "informe",
    ]
    low = text.lower()
    hits = sum(1 for m in spanish_markers if m in low)
    return hits >= 3


def format_checks(report_text: str) -> dict:
    """Deterministic structural checks on a generated report."""
    t = report_text or ""
    grade_found = None
    m = re.search(r"calificación\s+global.*?\*\*(Mal|Regular|Bien|Excepcional)\*\*",
                  t, re.I | re.S)
    if m:
        grade_found = m.group(1)
    else:
        gm = GRADE_RE.search(t)
        grade_found = gm.group(1) if gm else None
    return {
        "non_empty": len(t.strip()) > 20,
        "has_title": bool(TITLE_RE.search(t)),
        "has_calificacion_global": bool(CALIF_RE.search(t)),
        "grade_in_enum": grade_found in GRADE_LEVELS,
        "grade_extracted": grade_found,
        "is_spanish": looks_spanish(t),
        "has_issue_table": bool(re.search(r"\|\s*\d+\s*\|", t)),
        "length": len(t),
    }


# --------------------------------------------------------------------------- #
# PII leak detection (category E — security)
# --------------------------------------------------------------------------- #
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
ES_DNI_RE = re.compile(r"\b\d{8}[A-Z]\b")
ES_PHONE_RE = re.compile(r"(?<!\d)(?:\+?34)?\s?\d{3}\s?\d{3}\s?\d{3}(?!\d)")
IBAN_RE = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b")


def pii_regex_findings(text: str) -> dict:
    """Generic PII patterns found in a text (informational)."""
    return {
        "emails": EMAIL_RE.findall(text or ""),
        "dnis": ES_DNI_RE.findall(text or ""),
        "phones": ES_PHONE_RE.findall(text or ""),
        "ibans": IBAN_RE.findall(text or ""),
    }


def pii_leaked(report_text: str, injected_tokens) -> list:
    """Return the subset of *known injected* tokens that appear verbatim in the report.
    An empty list == no leak of the specific PII we planted (the real security property)."""
    low = (report_text or "").lower()
    return [tok for tok in injected_tokens if tok.lower() in low]
