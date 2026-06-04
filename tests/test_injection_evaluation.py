import pytest

from argus.config import load_flaws
from argus.evaluation.injection import inject_flaw
from argus.evaluation.metrics import evaluate_pair, summarize_results
from argus.evaluation.runner import evaluate_flaws, evaluate_injected_pair
from argus.pipeline.audit import run_audit


@pytest.mark.parametrize("flaw_id", sorted(load_flaws()))
def test_injected_flaw_is_detected_without_clean_false_alarm(flaw_id, supported_paper):
    clean = supported_paper(f"clean_{flaw_id}")
    injected = inject_flaw(clean, flaw_id)
    target_dimension = injected["argus_ground_truth"]["target_dimension"]

    clean_audit = run_audit(clean, max_steps=1).risk_map
    injected_audit = run_audit(injected, max_steps=1).risk_map
    result = evaluate_pair(clean_audit, injected_audit, target_dimension)

    assert result["detected"] is True
    assert result["false_alarm"] is False
    assert result["localized"] is True


def test_inject_flaw_does_not_mutate_original_paper(supported_paper):
    clean = supported_paper("clean_mutation_check")
    injected = inject_flaw(clean, "pretrend_divergence")

    assert "argus_ground_truth" not in clean
    assert injected["id"] == "clean_mutation_check__pretrend_divergence"
    assert injected["argus_ground_truth"]["target_dimension"] == "parallel_trends"


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
    single = evaluate_injected_pair(
        supported_paper("runner_single"),
        "pretrend_divergence",
        max_steps=1,
    )
    assert single["score"]["detected"] is True
    assert single["ground_truth"]["target_dimension"] == "parallel_trends"

    batch = evaluate_flaws(
        supported_paper("runner_batch"),
        ["pretrend_divergence", "missing_placebo"],
        max_steps=1,
    )
    assert batch["summary"] == {
        "n": 2,
        "detection_rate": 1.0,
        "false_alarm_rate": 0.0,
        "localization_acc": 1.0,
    }
