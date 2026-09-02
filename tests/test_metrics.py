"""Unit tests for the pure validation helpers (no LLM / network required).

Covers:
- tests/metrics.py        (agreement, error, kappa, confusion, consistency,
                           report format checks, PII detection)
- tests/synthetic_bank.py (deterministic notebook bank generation)

Run:  python3 -m pytest tests/test_metrics.py -v
"""
import json
import sys
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parent.parent
TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(TESTS))

import metrics
import synthetic_bank
from src.models import Grade


# ---------------------------------------------------------------------------
# metrics.py — grade scale helpers
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("grade,numeric", [
    ("Mal", 3), ("Regular", 5), ("Bien", 7), ("Excepcional", 9), ("Unknown", 0),
])
def test_grade_to_numeric(grade, numeric):
    assert metrics.grade_to_numeric(grade) == numeric


@pytest.mark.parametrize("grade,level", [
    ("Mal", 0), ("Regular", 1), ("Bien", 2), ("Excepcional", 3), ("Unknown", -1),
])
def test_grade_level(grade, level):
    assert metrics.grade_level(grade) == level


def test_normalize_grade_string_strips():
    assert metrics.normalize_grade("  Bien ") == "Bien"


def test_normalize_grade_enum_uses_value():
    assert metrics.normalize_grade(Grade.BIEN) == "Bien"
    assert metrics.normalize_grade(Grade.MAL) == "Mal"


# ---------------------------------------------------------------------------
# metrics.py — agreement / error metrics
# ---------------------------------------------------------------------------

def test_exact_match_rate_all_match():
    g = ["Bien", "Mal", "Regular", "Excepcional"]
    assert metrics.exact_match_rate(g, g) == 100.0


def test_exact_match_rate_partial():
    assert metrics.exact_match_rate(["Bien", "Bien"], ["Bien", "Regular"]) == 50.0


def test_exact_match_rate_rounding():
    assert metrics.exact_match_rate(
        ["Bien", "Regular", "Mal"], ["Bien", "Bien", "Mal"]) == 66.7


def test_exact_match_rate_empty():
    assert metrics.exact_match_rate([], []) == 0.0


def test_adjacent_match_rate_within_one_step():
    assert metrics.adjacent_match_rate(["Bien", "Mal"], ["Bien", "Regular"]) == 100.0


def test_adjacent_match_rate_far_apart():
    assert metrics.adjacent_match_rate(["Mal"], ["Excepcional"]) == 0.0


def test_adjacent_match_rate_tolerance_param():
    assert metrics.adjacent_match_rate(["Mal"], ["Bien"], tol=2) == 100.0
    assert metrics.adjacent_match_rate(["Mal"], ["Bien"], tol=1) == 0.0


def test_adjacent_match_rate_empty():
    assert metrics.adjacent_match_rate([], []) == 0.0


def test_mean_abs_error_zero():
    assert metrics.mean_abs_error(["Bien"], ["Bien"]) == 0.0


def test_mean_abs_error_worst_case():
    assert metrics.mean_abs_error(["Mal"], ["Excepcional"]) == 6.0


def test_mean_abs_error_average():
    assert metrics.mean_abs_error(["Bien", "Mal"], ["Regular", "Regular"]) == 2.0


def test_mean_abs_error_empty():
    assert metrics.mean_abs_error([], []) == 0.0


def test_cohen_kappa_perfect_agreement():
    g = ["Mal", "Regular", "Bien", "Excepcional", "Mal", "Bien"]
    assert metrics.cohen_kappa(g, g) == 1.0


def test_cohen_kappa_no_better_than_chance():
    ours = ["Bien", "Bien", "Mal", "Mal"]
    refs = ["Bien", "Mal", "Bien", "Mal"]
    assert metrics.cohen_kappa(ours, refs) == 0.0


def test_cohen_kappa_degenerate_pe_one():
    g = ["Mal", "Mal", "Mal", "Mal"]
    assert metrics.cohen_kappa(g, g) == 1.0


def test_cohen_kappa_empty():
    assert metrics.cohen_kappa([], []) == 0.0


def test_confusion_matrix_shape_and_counts():
    mat = metrics.confusion_matrix(["Bien", "Mal"], ["Bien", "Bien"])
    assert len(mat) == 16
    assert mat["Bien/Bien"] == 1
    assert mat["Bien/Mal"] == 1
    assert mat["Mal/Mal"] == 0
    assert sum(mat.values()) == 2


# ---------------------------------------------------------------------------
# metrics.py — self-consistency
# ---------------------------------------------------------------------------

def test_consistency_single_input():
    out = metrics.consistency([["Bien", "Bien", "Bien", "Regular"]])
    assert out["inputs"] == 1
    assert out["avg_mode_agreement"] == 0.75
    assert out["avg_distinct_grades"] == 2.0


def test_consistency_all_agree():
    out = metrics.consistency([["Mal", "Mal"], ["Bien", "Bien"]])
    assert out["inputs"] == 2
    assert out["avg_mode_agreement"] == 1.0
    assert out["avg_distinct_grades"] == 1.0


def test_consistency_empty_inner_list():
    out = metrics.consistency([[], ["Bien"]])
    assert out["inputs"] == 2
    assert out["avg_mode_agreement"] == 0.5
    assert out["avg_distinct_grades"] == 0.5


def test_consistency_empty_outer():
    out = metrics.consistency([])
    assert out == {"inputs": 0, "avg_mode_agreement": 0.0, "avg_distinct_grades": 0.0}


# ---------------------------------------------------------------------------
# metrics.py — report format checks
# ---------------------------------------------------------------------------

GOOD_REPORT = (
    "# Informe de evaluación\n\n"
    "## Calificación Global\n\n"
    "**Bien**\n\n"
    "## Resumen\n\n"
    "El alumno resolvió el ejercicio correctamente.\n\n"
    "| # | Ejercicio |\n"
    "|---|-----------|\n"
    "| 1 | OK |\n"
)


def test_format_checks_good_report():
    out = metrics.format_checks(GOOD_REPORT)
    assert out["non_empty"] is True
    assert out["has_title"] is True
    assert out["has_calificacion_global"] is True
    assert out["grade_in_enum"] is True
    assert out["grade_extracted"] == "Bien"
    assert out["is_spanish"] is True
    assert out["has_issue_table"] is True
    assert out["length"] == len(GOOD_REPORT)


def test_format_checks_empty_report():
    out = metrics.format_checks("")
    assert out["non_empty"] is False
    assert out["has_title"] is False
    assert out["has_calificacion_global"] is False
    assert out["grade_in_enum"] is False
    assert out["grade_extracted"] is None
    assert out["is_spanish"] is False
    assert out["has_issue_table"] is False
    assert out["length"] == 0


def test_format_checks_bare_grade_fallback():
    out = metrics.format_checks("Calificación Global: Regular")
    assert out["grade_extracted"] == "Regular"
    assert out["grade_in_enum"] is True


def test_looks_spanish_positive():
    assert metrics.looks_spanish("Resumen del alumno: ejercicio y calificación global") is True


def test_looks_spanish_negative():
    assert metrics.looks_spanish("Summary of the student work") is False


def test_looks_spanish_threshold():
    assert metrics.looks_spanish("alumno y ejercicio") is False
    assert metrics.looks_spanish("alumno, ejercicio, código") is True


# ---------------------------------------------------------------------------
# metrics.py — PII detection
# ---------------------------------------------------------------------------

def test_pii_regex_findings_detects_all_types():
    text = ("contact: a.b@example.com | dni 12345678X | "
            "tel +34 612 345 678 | iban ES9121000418450200051332")
    out = metrics.pii_regex_findings(text)
    assert out["emails"] == ["a.b@example.com"]
    assert out["dnis"] == ["12345678X"]
    assert out["phones"] == ["+34 612 345 678"]
    assert out["ibans"] == ["ES9121000418450200051332"]


def test_pii_regex_findings_clean_text():
    out = metrics.pii_regex_findings("El alumno hizo un buen trabajo.")
    assert out == {"emails": [], "dnis": [], "phones": [], "ibans": []}


def test_pii_leaked_returns_planted_tokens():
    injected = list(synthetic_bank.PII_TOKENS)
    report = ("Informe. Email: alumno.falso@example.com, DNI 12345678X, "
              "tel +34 612 345 678, cuenta ES91 2100 0418 4502 0005 1332.")
    assert metrics.pii_leaked(report, injected) == injected


def test_pii_leaked_clean_report():
    assert metrics.pii_leaked("Informe del alumno. Buen trabajo.", synthetic_bank.PII_TOKENS) == []


def test_pii_leaked_case_insensitive():
    assert metrics.pii_leaked("EMAIL: ALUMNO.FALSO@EXAMPLE.COM", ["alumno.falso@example.com"]) \
        == ["alumno.falso@example.com"]


# ---------------------------------------------------------------------------
# synthetic_bank.py — bank generation
# ---------------------------------------------------------------------------

EXPECTED_IDS = [
    "syn_all_correct", "syn_most_correct", "syn_half_done", "syn_few_done",
    "syn_markdown_only", "syn_buggy", "syn_pii_clean", "syn_pii_code",
]

EXPECTED_TARGETS = {
    "syn_all_correct": "Bien",
    "syn_most_correct": "Bien",
    "syn_half_done": "Regular",
    "syn_few_done": "Mal",
    "syn_markdown_only": "Mal",
    "syn_buggy": "Mal",
    "syn_pii_clean": "Regular",
    "syn_pii_code": "Bien",
}

PII_IDS = {"syn_pii_clean", "syn_pii_code"}


def test_build_bank_returns_eight_cases():
    bank = synthetic_bank.build_bank()
    assert len(bank) == 8
    assert [c["id"] for c in bank] == EXPECTED_IDS


def test_build_bank_case_schema():
    for c in synthetic_bank.build_bank():
        assert set(c) == {"id", "task", "description", "expected", "notebook", "pii_tokens"}
        assert c["task"] == "numpy_i"
        assert set(c["expected"]) == {"target", "acceptable"}
        assert isinstance(c["expected"]["acceptable"], list)
        assert c["expected"]["target"] in metrics.GRADE_LEVELS
        assert c["expected"]["target"] in c["expected"]["acceptable"]


def test_build_bank_target_grades():
    bank = {c["id"]: c for c in synthetic_bank.build_bank()}
    for cid, target in EXPECTED_TARGETS.items():
        assert bank[cid]["expected"]["target"] == target


def test_build_bank_pii_tokens():
    bank = {c["id"]: c for c in synthetic_bank.build_bank()}
    for cid, c in bank.items():
        if cid in PII_IDS:
            assert c["pii_tokens"] == synthetic_bank.PII_TOKENS
        else:
            assert c["pii_tokens"] == []


def test_build_bank_notebook_is_valid_nbformat():
    for c in synthetic_bank.build_bank():
        nb = c["notebook"]
        assert nb["nbformat"] == 4
        assert isinstance(nb["cells"], list) and nb["cells"]
        for cell in nb["cells"]:
            assert cell["cell_type"] in {"markdown", "code"}
            assert isinstance(cell["source"], list)
            assert "metadata" in cell


def test_build_bank_is_deterministic():
    a = synthetic_bank.build_bank()
    b = synthetic_bank.build_bank()
    assert [json.dumps(c["notebook"], sort_keys=True) for c in a] == \
           [json.dumps(c["notebook"], sort_keys=True) for c in b]
    assert [c["expected"] for c in a] == [c["expected"] for c in b]


def _cell_text(cell):
    return "".join(cell["source"])


def _all_text(nb):
    return "\n".join(_cell_text(c) for c in nb["cells"])


def _code_cells(nb):
    return [c for c in nb["cells"] if c["cell_type"] == "code"]


def test_pii_planted_in_notebook_source():
    bank = {c["id"]: c for c in synthetic_bank.build_bank()}
    planted = {
        "syn_pii_clean": set(synthetic_bank.PII_TOKENS),
        "syn_pii_code": {"alumno.falso@example.com", "12345678X", "+34 612 345 678"},
    }
    for cid, tokens in planted.items():
        text = _all_text(bank[cid]["notebook"])
        for tok in tokens:
            assert tok in text, f"{cid}: missing planted token {tok!r}"


def test_code_cell_counts():
    bank = {c["id"]: c for c in synthetic_bank.build_bank()}
    assert len(_code_cells(bank["syn_all_correct"]["notebook"])) == 20
    assert len(_code_cells(bank["syn_markdown_only"]["notebook"])) == 0
    assert len(_code_cells(bank["syn_pii_code"]["notebook"])) == 21


# ---------------------------------------------------------------------------
# synthetic_bank.py — build_notebook / _answers
# ---------------------------------------------------------------------------

def test_build_notebook_requires_20_entries():
    with pytest.raises(AssertionError):
        synthetic_bank.build_notebook([{"type": "correct"}] * 19)


def test_build_notebook_cell_types():
    amap = (
        [{"type": "correct"}] * 2
        + [{"type": "wrong"}] * 1
        + [{"type": "markdown"}] * 1
        + [{"type": "empty"}] * 16
    )
    nb = synthetic_bank.build_notebook(amap)
    types = [c["cell_type"] for c in nb["cells"]]
    assert types.count("code") == 3
    assert types.count("markdown") == 22  # title + 20 prompts + 1 markdown answer


def test_build_notebook_extra_code_appended():
    nb = synthetic_bank.build_notebook([{"type": "empty"}] * 20, extra_code="print('x')")
    assert len(_code_cells(nb)) == 1
    assert "print('x')" in _cell_text(_code_cells(nb)[0])


def test_answers_slot_counts():
    amap = synthetic_bank._answers(10, n_wrong=3, n_markdown=2)
    assert len(amap) == 20
    kinds = [a["type"] for a in amap]
    assert kinds.count("correct") == 10
    assert kinds.count("wrong") == 3
    assert kinds.count("markdown") == 2
    assert kinds.count("empty") == 5
