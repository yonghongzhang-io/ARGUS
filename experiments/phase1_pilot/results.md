# Phase-1 pilot — honest baseline under realistic flaw injection

Deterministic keyword baseline, `max_steps=1`, all 11 flaws from `config/flaw_taxonomy.yaml`, one flaw injected per run.

**Headline.** Removing the sentinel-sentence leakage that made the old evaluation circular drops detection from a trivial **1.000** to the numbers below. False-alarm stays at 0: the baseline never flags the clean paper. The baseline catches *omission* flaws only when the removed vocabulary is not echoed elsewhere, and is systematically blind to *commission* flaws where flawed-but-plausible evidence is present — which is the gap a reasoning-based auditor must close.

## `clean_supported.json`

| flaw | op | target dimension | detected | localized | false alarm |
|---|---|---|---|---|---|
| `anticipation_effect` | replace | no_anticipation | — | — | — |
| `bad_control` | replace | specification | — | — | — |
| `cherrypicked_window` | remove | sample_period | — | — | — |
| `confounding_policy` | remove | concurrent_policies | — | — | — |
| `forbidden_comparison` | replace | treatment_timing | — | — | — |
| `measurement_break` | remove | data_measurement | ✅ | ✅ | — |
| `missing_placebo` | remove | robustness_placebo | — | — | — |
| `noncomparable_controls` | remove | control_group | — | — | — |
| `pretrend_divergence` | replace | parallel_trends | — | — | — |
| `spillover_contamination` | remove | treatment_definition_sutva | ✅ | ✅ | — |
| `understated_se` | replace | inference | — | — | — |

**Summary** (n=11): detection_rate=**0.182**, false_alarm_rate=**0.000**, localization_acc=**0.182**

## `china_carbon_ets_pilot.json`

| flaw | op | target dimension | detected | localized | false alarm |
|---|---|---|---|---|---|
| `anticipation_effect` | replace | no_anticipation | — | — | — |
| `bad_control` | replace | specification | — | — | — |
| `cherrypicked_window` | remove | sample_period | — | — | — |
| `confounding_policy` | remove | concurrent_policies | — | — | — |
| `forbidden_comparison` | replace | treatment_timing | — | — | — |
| `measurement_break` | remove | data_measurement | ✅ | ✅ | — |
| `missing_placebo` | remove | robustness_placebo | — | — | — |
| `noncomparable_controls` | remove | control_group | — | — | — |
| `pretrend_divergence` | replace | parallel_trends | — | — | — |
| `spillover_contamination` | remove | treatment_definition_sutva | — | — | — |
| `understated_se` | replace | inference | — | — | — |

**Summary** (n=11): detection_rate=**0.091**, false_alarm_rate=**0.000**, localization_acc=**0.091**

---

_Regenerate with_ `PYTHONPATH=src python3 experiments/phase1_pilot/run_baseline_eval.py`
