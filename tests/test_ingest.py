"""Tests for the real-paper Markdown ingestion."""

from argus.ingest import ingest_markdown
from argus.pipeline.audit import run_audit

SAMPLE = """# A DID Study of Some Policy
This is the abstract paragraph describing the study.

## a r t i c l e i n f o

## parallel trends
The event-study shows pre-trend coefficients near zero.

## inference
Standard errors are clustered by province.

@figure fig_event_study | Event-study plot with null pre-trend coefficients.
@table table_balance | Balance table for treated vs control.
"""


def test_ingest_markdown_shape():
    paper = ingest_markdown(SAMPLE, paper_id="demo_real")
    assert paper["id"] == "demo_real"
    assert paper["title"] == "A DID Study of Some Policy"
    assert "abstract" in paper and "abstract paragraph" in paper["abstract"]
    # empty bare-header sections are dropped; real ones kept
    assert "a r t i c l e i n f o" not in paper["sections"]
    assert "parallel trends" in paper["sections"]
    assert "inference" in paper["sections"]
    assert {f["id"] for f in paper["figures"]} == {"fig_event_study"}
    assert {t["id"] for t in paper["tables"]} == {"table_balance"}


def test_ingested_paper_audits_end_to_end():
    paper = ingest_markdown(SAMPLE, paper_id="demo_real")
    result = run_audit(paper, max_steps=1)  # keyword assessor, no network
    assert result.paper_id == "demo_real"
    # every rubric dimension gets a risk
    assert len(result.risk_map["by_dimension"]) >= 10
