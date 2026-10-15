"""Static tests for the red-team (adversarial) notebook bank (no LLM / network).

Covers:
- tests/redteam_bank.py  (deterministic adversarial notebook generation)
- reuse of tests/metrics.py helpers (pii_regex_findings, format_checks)
- the app's task-classifier on the malformed notebooks

Run:  ./.venv/bin/pytest tests/test_redteam.py -v
"""
import json
import sys
from pathlib import Path

import nbformat
import pytest

BASE = Path(__file__).resolve().parent.parent
TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(TESTS))

import metrics
import redteam_bank
from src.utils.notebook import clean_notebook
from src.utils.task_classifier import classify_task


EXPECTED_IDS = [
    "inj_markdown", "inj_code", "self_grade", "pii_heavy",
    "malformed_empty", "malformed_outputs_only", "non_numpy", "oversized",
]
VALID_CATEGORIES = {"injection", "pii", "malformed"}


def _cell_text(cell):
    return "".join(cell["source"])


def _all_text(nb):
    return "\n".join(_cell_text(c) for c in nb["cells"])


def _code_cells(nb):
    return [c for c in nb["cells"] if c["cell_type"] == "code"]


# ---------------------------------------------------------------------------
# bank generation — ids / schema / categories
# ---------------------------------------------------------------------------

def test_build_redteam_bank_returns_expected_ids():
    bank = redteam_bank.build_redteam_bank()
    assert [c["id"] for c in bank] == EXPECTED_IDS
    assert {c["id"] for c in bank} == set(EXPECTED_IDS)


def test_build_redteam_bank_case_schema():
    for c in redteam_bank.build_redteam_bank():
        assert set(c) == {"id", "task", "description", "category", "notebook", "planted_tokens"}
        assert c["task"] == "numpy_i"
        assert c["category"] in VALID_CATEGORIES
        assert isinstance(c["planted_tokens"], list)


def test_build_redteam_bank_categories():
    bank = {c["id"]: c for c in redteam_bank.build_redteam_bank()}
    expected_cat = {
        "inj_markdown": "injection", "inj_code": "injection", "self_grade": "injection",
        "pii_heavy": "pii",
        "malformed_empty": "malformed", "malformed_outputs_only": "malformed",
        "non_numpy": "malformed", "oversized": "malformed",
    }
    for cid, cat in expected_cat.items():
        assert bank[cid]["category"] == cat


# ---------------------------------------------------------------------------
# nbformat validity + determinism
# ---------------------------------------------------------------------------

def test_every_notebook_passes_nbformat_validate():
    for c in redteam_bank.build_redteam_bank():
        nbformat.validate(c["notebook"])


def test_build_redteam_bank_is_deterministic():
    a = redteam_bank.build_redteam_bank()
    b = redteam_bank.build_redteam_bank()
    assert [json.dumps(c["notebook"], sort_keys=True) for c in a] == \
           [json.dumps(c["notebook"], sort_keys=True) for c in b]
    assert [c["planted_tokens"] for c in a] == [c["planted_tokens"] for c in b]


# ---------------------------------------------------------------------------
# PII — regex detection + credit-card gap
# ---------------------------------------------------------------------------

def test_pii_heavy_regex_detects_email_dni_phone_iban():
    bank = {c["id"]: c for c in redteam_bank.build_redteam_bank()}
    text = _all_text(bank["pii_heavy"]["notebook"])
    findings = metrics.pii_regex_findings(text)
    assert "alumno.falso@example.com" in findings["emails"]
    assert "12345678X" in findings["dnis"]
    assert any("612 345 678" in p for p in findings["phones"])
    assert "ES9121000418450200051332" in findings["ibans"]


def test_pii_heavy_credit_card_present_but_no_regex():
    # metrics.py has NO credit-card regex — document the gap by asserting the
    # raw CC string is present in the notebook (and NOT caught by any finding).
    bank = {c["id"]: c for c in redteam_bank.build_redteam_bank()}
    text = _all_text(bank["pii_heavy"]["notebook"])
    assert "4111 1111 1111 1111" in text
    findings = metrics.pii_regex_findings(text)
    assert not any("4111 1111 1111 1111" in v for vals in findings.values() for v in vals)


def test_pii_heavy_planted_tokens_recorded():
    bank = {c["id"]: c for c in redteam_bank.build_redteam_bank()}
    tokens = bank["pii_heavy"]["planted_tokens"]
    assert set(tokens) == set(redteam_bank.PII_HEAVY_TOKENS)
    text = _all_text(bank["pii_heavy"]["notebook"])
    for tok in tokens:
        assert tok in text, f"missing planted token {tok!r}"


# ---------------------------------------------------------------------------
# injection sanity — payloads actually present in the notebook text
# ---------------------------------------------------------------------------

def test_inj_markdown_payload_present():
    bank = {c["id"]: c for c in redteam_bank.build_redteam_bank()}
    text = _all_text(bank["inj_markdown"]["notebook"])
    assert redteam_bank.INJ_MARKDOWN_ES in text
    assert redteam_bank.INJ_MARKDOWN_DAN in text


def test_inj_code_payload_present():
    bank = {c["id"]: c for c in redteam_bank.build_redteam_bank()}
    text = _all_text(bank["inj_code"]["notebook"])
    assert redteam_bank.INJ_CODE_COMMENT in text


def test_self_grade_payload_present():
    bank = {c["id"]: c for c in redteam_bank.build_redteam_bank()}
    text = _all_text(bank["self_grade"]["notebook"])
    assert redteam_bank.SELF_GRADE_TEXT in text


# ---------------------------------------------------------------------------
# malformed handling — classifier must not raise, oversized must build
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("cid", [
    "malformed_empty", "malformed_outputs_only", "non_numpy", "oversized",
])
def test_classify_task_returns_key_without_raising(cid):
    bank = {c["id"]: c for c in redteam_bank.build_redteam_bank()}
    nb = bank[cid]["notebook"]
    cleaned = clean_notebook(nb)
    key = classify_task(cleaned, f"{cid}.ipynb")
    assert isinstance(key, str) and key


def test_oversized_builds_with_large_code_cell():
    bank = {c["id"]: c for c in redteam_bank.build_redteam_bank()}
    code_cells = _code_cells(bank["oversized"]["notebook"])
    assert len(code_cells) == 1
    n_lines = len(_cell_text(code_cells[0]).splitlines())
    assert n_lines >= 1500


def test_malformed_empty_has_no_code_cells():
    bank = {c["id"]: c for c in redteam_bank.build_redteam_bank()}
    assert len(_code_cells(bank["malformed_empty"]["notebook"])) == 0


def test_malformed_outputs_only_empty_source_with_outputs():
    bank = {c["id"]: c for c in redteam_bank.build_redteam_bank()}
    code_cells = _code_cells(bank["malformed_outputs_only"]["notebook"])
    assert code_cells
    for cell in code_cells:
        assert cell["source"] == []
        assert cell["outputs"]


# ---------------------------------------------------------------------------
# format guard — empty report is flagged non-empty == False
# ---------------------------------------------------------------------------

def test_format_checks_empty_report_guard():
    assert metrics.format_checks("")["non_empty"] is False
