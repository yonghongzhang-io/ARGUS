"""Phase-1 pilot: honest baseline under realistic flaw injection.

Runs the full flaw-injection evaluation loop for the deterministic keyword
baseline on the bundled example papers, and writes a reproducible results table
to `results.md` next to this script.

This is the experiment that replaced the earlier *circular* evaluation: when the
injector planted sentinel sentences containing the detector's own keywords,
detection was a trivial 1.000. With realistic structural perturbation
(`src/argus/evaluation/injection.py`) the number reported here is what the
baseline actually earns.

Run:
    PYTHONPATH=src python3 experiments/phase1_pilot/run_baseline_eval.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from argus.config import load_flaws  # noqa: E402
from argus.evaluation.runner import evaluate_flaws  # noqa: E402

PAPERS = [
    ROOT / "examples" / "papers" / "clean_supported.json",
    ROOT / "examples" / "papers" / "china_carbon_ets_pilot.json",
]
OUT = Path(__file__).resolve().parent / "results.md"
MAX_STEPS = 1


def run_one(paper_path: Path) -> dict:
    paper = json.loads(paper_path.read_text())
    return evaluate_flaws(paper, sorted(load_flaws()), max_steps=MAX_STEPS)


def fmt_per_flaw(result: dict) -> list[str]:
    rows = ["| flaw | op | target dimension | detected | localized | false alarm |",
            "|---|---|---|---|---|---|"]
    for pair in result["pairs"]:
        gt, s = pair["ground_truth"], pair["score"]
        rows.append(
            f"| `{pair['flaw_id']}` | {gt['injection_op']} | {gt['target_dimension']} | "
            f"{'✅' if s['detected'] else '—'} | {'✅' if s['localized'] else '—'} | "
            f"{'⚠️' if s['false_alarm'] else '—'} |"
        )
    return rows


def main() -> None:
    lines = [
        "# Phase-1 pilot — honest baseline under realistic flaw injection",
        "",
        "Deterministic keyword baseline, `max_steps=1`, all 11 flaws from "
        "`config/flaw_taxonomy.yaml`, one flaw injected per run.",
        "",
        "**Headline.** Removing the sentinel-sentence leakage that made the old "
        "evaluation circular drops detection from a trivial **1.000** to the "
        "numbers below. False-alarm stays at 0: the baseline never flags the "
        "clean paper. The baseline catches *omission* flaws only when the removed "
        "vocabulary is not echoed elsewhere, and is systematically blind to "
        "*commission* flaws where flawed-but-plausible evidence is present — which "
        "is the gap a reasoning-based auditor must close.",
        "",
    ]

    for paper_path in PAPERS:
        result = run_one(paper_path)
        s = result["summary"]
        lines += [
            f"## `{paper_path.name}`",
            "",
            *fmt_per_flaw(result),
            "",
            f"**Summary** (n={s['n']}): "
            f"detection_rate=**{s['detection_rate']:.3f}**, "
            f"false_alarm_rate=**{s['false_alarm_rate']:.3f}**, "
            f"localization_acc=**{s['localization_acc']:.3f}**",
            "",
        ]

    lines += [
        "---",
        "",
        "_Regenerate with_ `PYTHONPATH=src python3 experiments/phase1_pilot/run_baseline_eval.py`",
        "",
    ]

    OUT.write_text("\n".join(lines))
    print(f"wrote {OUT.relative_to(ROOT)}")
    for paper_path in PAPERS:
        s = run_one(paper_path)["summary"]
        print(f"  {paper_path.name:34} detection={s['detection_rate']:.3f}  "
              f"false_alarm={s['false_alarm_rate']:.3f}  localization={s['localization_acc']:.3f}")


if __name__ == "__main__":
    main()
