"""Dry-run planner for cross-model robustness runs. NO API CALLS.

Prints, for the models declared in ``config/models.yaml``, the projected number
of calls and an order-of-magnitude cost ESTIMATE for auditing a given number of
units (default: the flaw-variant catalog size), and whether each projection
stays under that model's cost ceiling.

It never runs a model. Cross-model numerical results are not produced here and
are not reported in the paper; this only lets you see what a run *would* cost
before authorizing one. Only providers with an implemented backend are marked
``runnable`` (today: openai); others are declarations of intent.

Usage:
    PYTHONPATH=src python3 experiments/models/plan_run.py
    PYTHONPATH=src python3 experiments/models/plan_run.py --units 33 --all
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from argus.agent.model_config import build_run_manifest, enabled_models, load_model_registry  # noqa: E402


def _default_units() -> int:
    try:
        from argus.config import load_flaw_variants
        return len(load_flaw_variants())
    except Exception:
        return 11  # fall back to the base flaw count


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--units", type=int, default=None,
                    help="number of audit units (default: flaw-variant catalog size)")
    ap.add_argument("--calls-per-unit", type=int, default=2,
                    help="LLM calls per unit (relevance gate + adequacy ~= 2)")
    ap.add_argument("--all", action="store_true",
                    help="plan for every model, not only enabled ones")
    args = ap.parse_args()

    registry = load_model_registry()
    units = args.units if args.units is not None else _default_units()
    ids = [m["id"] for m in registry["models"].values()] if args.all else [m["id"] for m in enabled_models(registry)]

    print(f"DRY RUN (no API calls). units={units}  calls/unit={args.calls_per_unit}\n")
    if not ids:
        print("No models enabled in config/models.yaml (this is the default). "
              "Nothing would run. Set enabled: true and re-plan with --all to preview costs.")
        # still show what --all would look like
        ids = [m["id"] for m in registry["models"].values()]
        print("\nPreview of ALL declared models:")

    manifest = build_run_manifest(units, calls_per_unit=args.calls_per_unit,
                                  model_ids=ids, registry=registry)
    print(f"{'id':16s} {'provider':10s} {'enabled':8s} {'runnable':9s} "
          f"{'calls':>7s} {'est.$':>8s} {'ceiling':>8s} ok")
    for m in manifest["models"]:
        print(f"{m['id']:16s} {m['provider']:10s} {str(m['enabled']):8s} {str(m['runnable']):9s} "
              f"{m['projected_calls']:7d} {m['estimated_cost_usd']:8.2f} "
              f"{('-' if m['cost_ceiling_usd'] is None else f'{m['cost_ceiling_usd']:.2f}'):>8s} "
              f"{'Y' if m['within_ceiling'] else 'N'}")

    unrunnable = [m["id"] for m in manifest["models"] if m["enabled"] and not m["runnable"]]
    if unrunnable:
        print(f"\nNote: {unrunnable} are enabled but have no implemented backend yet "
              "(implement a ProviderAdapter and branch it in pipeline/assessment.py).")
    print("\nCost figures are planning ESTIMATES only. Verify provider pricing before any real run.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
