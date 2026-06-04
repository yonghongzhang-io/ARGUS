import json
from pathlib import Path

import pytest

from argus.cli import main
from argus.evaluation.runner import evaluate_paper_file
from argus.paper import load_paper, validate_paper
from argus.pipeline.audit import run_audit

EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "papers"


@pytest.mark.parametrize(
    "filename",
    [
        "clean_supported.json",
        "pretrend_issue.json",
        "china_carbon_ets_pilot.json",
    ],
)
def test_example_papers_load_and_audit(filename):
    paper = load_paper(EXAMPLES / filename)
    result = run_audit(paper, max_steps=1)

    assert result.paper_id == paper["id"]
    assert Path(result.report_path).exists()
    assert len(result.trace_paths) == len(result.risk_map["by_dimension"]) * 2


def test_clean_and_china_ets_examples_are_low_risk():
    for filename in ("clean_supported.json", "china_carbon_ets_pilot.json"):
        result = run_audit(load_paper(EXAMPLES / filename), max_steps=1)
        risks = {d["risk"] for d in result.risk_map["by_dimension"].values()}
        assert risks == {"low"}


def test_pretrend_issue_example_flags_parallel_trends():
    result = run_audit(load_paper(EXAMPLES / "pretrend_issue.json"), max_steps=1)

    assert result.risk_map["by_dimension"]["parallel_trends"]["risk"] == "high"
    assert "parallel_trends" in result.risk_map["ranked"][:3]


def test_schema_validation_rejects_missing_title(supported_paper):
    paper = supported_paper()
    del paper["title"]

    with pytest.raises(ValueError, match="title"):
        validate_paper(paper)


def test_evaluate_paper_file_runs_selected_flaws():
    result = evaluate_paper_file(
        EXAMPLES / "clean_supported.json",
        ["measurement_break", "spillover_contamination"],
        max_steps=1,
    )

    assert result["summary"] == {
        "n": 2,
        "detection_rate": 1.0,
        "false_alarm_rate": 0.0,
        "localization_acc": 1.0,
    }


def test_cli_audit_and_evaluate_emit_json(capsys):
    assert main(["audit", str(EXAMPLES / "clean_supported.json"), "--max-steps", "1"]) == 0
    audit_out = json.loads(capsys.readouterr().out)
    assert audit_out["paper_id"] == "clean_supported"
    assert audit_out["trace_count"] == 22
    assert audit_out["flagged_risks"] == []

    assert (
        main(
            [
                "evaluate",
                str(EXAMPLES / "clean_supported.json"),
                "--flaw",
                "measurement_break",
                "--max-steps",
                "1",
            ]
        )
        == 0
    )
    eval_out = json.loads(capsys.readouterr().out)
    assert eval_out["summary"]["detection_rate"] == 1.0
    assert eval_out["pairs"][0]["target_dimension"] == "data_measurement"
