import pytest

from argus.agent.loop import _NEGATIVE_SIGNALS
from argus.config import load_flaws
from argus.evaluation.injection import inject_flaw
from argus.evaluation.metrics import evaluate_pair, summarize_results
from argus.evaluation.runner import evaluate_flaws, evaluate_injected_pair
from argus.pipeline.audit import run_audit


def _all_text(paper: dict) -> str:
    """Concatenate every searchable string in a parsed paper, lowercased."""
    parts: list[str] = []
    sections = paper.get("sections")
    if isinstance(sections, dict):
        parts.extend(str(v) for v in sections.values())
    elif isinstance(sections, list):
        for s in sections:
            parts.append(str(s.get("text") or s.get("content") or s) if isinstance(s, dict) else str(s))
    for key in ("figures", "tables"):
        items = paper.get(key) or []
        if isinstance(items, list):
            for it in items:
                if isinstance(it, dict):
                    parts.append(" ".join(str(it.get(f, "")) for f in ("caption", "title", "notes", "text")))
    return " ".join(parts).lower()


@pytest.mark.parametrize("flaw_id", sorted(load_flaws()))
def test_injection_does_not_embed_detector_keywords(flaw_id, supported_paper):
    """No circularity: the injected paper must not contain the detector's own
    negative-signal phrases for the target dimension. If it did, detection would
    be a tautology rather than a measurement."""
    injected = inject_flaw(supported_paper(f"clean_{flaw_id}"), flaw_id)
    target = injected["argus_ground_truth"]["target_dimension"]
    text = _all_text(injected)
    leaked = [p for p in _NEGATIVE_SIGNALS.get(target, []) if p in text]
    assert not leaked, f"{flaw_id} leaked detector keywords: {leaked}"


@pytest.mark.parametrize("flaw_id", sorted(load_flaws()))
def test_injection_never_false_alarms_on_clean(flaw_id, supported_paper):
    """Whatever the perturbation, the *clean* paper must stay quiet on the
    target dimension."""
    clean = supported_paper(f"clean_{flaw_id}")
    injected = inject_flaw(clean, flaw_id)
    target = injected["argus_ground_truth"]["target_dimension"]

    clean_audit = run_audit(clean, max_steps=1).risk_map
    injected_audit = run_audit(injected, max_steps=1).risk_map
    result = evaluate_pair(clean_audit, injected_audit, target)

    assert result["false_alarm"] is False


def test_baseline_is_neither_blind_nor_circular(supported_paper):
    """With sentinel leakage removed, the keyword baseline is honestly measured:
    it must catch *something* (not blind) but must not catch *everything* (which
    would mean circularity has crept back). It must never raise a false alarm on
    the clean paper."""
    from argus.evaluation.runner import evaluate_flaws

    res = evaluate_flaws(supported_paper("honesty_suite"), sorted(load_flaws()), max_steps=1)
    summary = res["summary"]

    assert summary["false_alarm_rate"] == 0.0
    assert 0.0 < summary["detection_rate"] < 1.0


def test_inject_flaw_does_not_mutate_original_paper(supported_paper):
    clean = supported_paper("clean_mutation_check")
    injected = inject_flaw(clean, "pretrend_divergence")

    assert "argus_ground_truth" not in clean
    assert injected["id"] == "clean_mutation_check__pretrend_divergence"
    assert injected["argus_ground_truth"]["target_dimension"] == "parallel_trends"
    # the original section text is untouched
    assert "drift upward" not in clean["sections"]["parallel trends"]


def test_summarize_results_and_invalid_threshold():
    results = [
        {"detected": True, "false_alarm": False, "localized": True},
        {"detected": False, "false_alarm": True, "localized": False},
    ]

    summary = summarize_results(results)
    assert summary == {
        "n": 2,
        "detection_rate": 0.5,
        "false_alarm_rate": 0.5,
        "localization_acc": 0.5,
    }

    with pytest.raises(ValueError, match="unknown threshold"):
        evaluate_pair({}, {}, "parallel_trends", threshold="severe")

    with pytest.raises(ValueError, match="empty"):
        summarize_results([])


def test_evaluation_runner_scores_single_and_batch_flaws(supported_paper):
    # measurement_break and spillover_contamination are omission-type flaws whose
    # vocabulary is not echoed elsewhere in the paper, so the baseline detects
    # them via absence; this keeps the test deterministic.
    single = evaluate_injected_pair(
        supported_paper("runner_single"),
        "measurement_break",
        max_steps=1,
    )
    assert single["score"]["detected"] is True
    assert single["ground_truth"]["target_dimension"] == "data_measurement"

    batch = evaluate_flaws(
        supported_paper("runner_batch"),
        ["measurement_break", "spillover_contamination"],
        max_steps=1,
    )
    assert batch["summary"]["n"] == 2
    assert batch["summary"]["false_alarm_rate"] == 0.0
    assert 0.0 <= batch["summary"]["detection_rate"] <= 1.0
