import json
from pathlib import Path

import pytest

from argus.agent.loop import run_bounded_loop
from argus.agent.tools import DEFAULT_TOOLS, evidence_search, figure_parse, policy_lookup
from argus.pipeline import report
from argus.pipeline.audit import run_audit
from argus.pipeline.localization import localize


def test_run_audit_supported_fixture_generates_low_risk_report_and_traces(supported_paper):
    result = run_audit(supported_paper(), max_steps=1)

    risks = {dim_id: data["risk"] for dim_id, data in result.risk_map["by_dimension"].items()}
    assert set(risks.values()) == {"low"}
    assert len(result.trace_paths) == len(risks) * 2
    assert Path(result.report_path).exists()

    trace = json.loads(Path(result.trace_paths[0]).read_text(encoding="utf-8"))
    assert trace
    assert trace[0]["action"] == "evidence_search"
    assert "paper" not in trace[0]["args"]


def test_report_sanitizes_paper_id_before_writing_filename():
    out = report.render({"id": "../bad/id"}, {"ranked": [], "by_dimension": {}}, {})
    path = Path(out["report_path"])

    assert path.parent == report.RESULTS_DIR
    assert ".." not in path.name
    assert "/" not in path.name


def test_localize_handles_missing_judgement_as_unknown():
    risk_map = localize({"judgements": {"parallel_trends": None}})

    assert risk_map["by_dimension"]["parallel_trends"]["risk"] == "unknown"
    assert risk_map["ranked"] == ["parallel_trends"]


def test_tools_search_figures_and_static_policy_metadata(supported_paper):
    paper = supported_paper()

    matches = evidence_search(paper, "event study pre-trend", k=2)
    assert matches
    assert matches[0]["source"] in {"section:parallel trends", "figures:fig_event_study"}

    figure = figure_parse(paper, "fig_event_study")
    assert figure["found"] is True

    policy = policy_lookup("China carbon ETS")
    assert policy["implementation_years"] == [2013, 2014]


def test_bounded_loop_requires_positive_step_budget(supported_paper):
    with pytest.raises(ValueError, match="max_steps"):
        run_bounded_loop(
            task="extract_evidence:parallel_trends",
            context={"paper": supported_paper(), "dimension": {"id": "parallel_trends"}},
            tools=DEFAULT_TOOLS,
            max_steps=0,
        )
