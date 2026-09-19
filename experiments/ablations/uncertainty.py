"""Uncertainty quantification for the headline rates (camera-ready, reviewer point 3).

Reads only committed run files; no model access. Emits Wilson 95% intervals for
every proportion the paper reports, exact/paired tests between arms evaluated on
the same items, and cell-bootstrap intervals for the human-gold agreement
metrics (quadratic-weighted kappa, matching experiments/annotation/agreement.py).

    python3 experiments/ablations/uncertainty.py        # prints + writes uncertainty.json
"""
from __future__ import annotations

import csv
import json
import math
import random
from math import comb
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ABL = ROOT / "experiments" / "ablations"
VAR = ROOT / "experiments" / "variants" / "llm_runs"
XM = ROOT / "experiments" / "models" / "crossmodel"
ANN = ROOT / "experiments" / "annotation" / "pilot_frozen"  # frozen, committed copy of the pilot cells
ORDER = {"low": 0, "medium": 1, "high": 2}


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - h) / d, (c + h) / d)


def fisher_2x2(a: int, b: int, c: int, d: int) -> float:
    n, r1, c1 = a + b + c + d, a + b, a + c
    def p(x: int) -> float:
        return comb(r1, x) * comb(n - r1, c1 - x) / comb(n, c1)
    p0 = p(a)
    return sum(p(x) for x in range(max(0, c1 - (n - r1)), min(r1, c1) + 1) if p(x) <= p0 + 1e-12)


def mcnemar_exact(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    return min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n)


def weighted_kappa(pairs: list[tuple[int, int]], k: int = 3) -> float:
    n = len(pairs)
    if n == 0:
        return float("nan")
    obs = [[0] * k for _ in range(k)]
    for a, b in pairs:
        obs[a][b] += 1
    ra = [sum(obs[i]) for i in range(k)]
    rb = [sum(obs[i][j] for i in range(k)) for j in range(k)]
    num = den = 0.0
    for i in range(k):
        for j in range(k):
            w = ((i - j) / (k - 1)) ** 2
            num += w * obs[i][j]
            den += w * ra[i] * rb[j] / n
    return 1 - num / den if den else float("nan")


def rate(name: str, k: int, n: int) -> dict:
    lo, hi = wilson(k, n)
    return {"name": name, "k": k, "n": n, "rate": round(k / n, 3), "ci95": [round(lo, 3), round(hi, 3)]}


def main() -> None:
    out: dict = {"rates": [], "tests": [], "gold_bootstrap": []}

    # --- 11-flaw fixture -------------------------------------------------
    two = json.load(open(ABL / "twostage_11flaw_fresh.json"))
    am = json.load(open(ABL / "ablation_matrix.json"))
    two_det = {p["flaw"]: p["detected"] for p in two["per_flaw"]}
    kw_det = {f: f in {"measurement_break", "spillover_contamination"} for f in two_det}
    sp11 = {p["id"]: p["score"]["detected"] for p in am["singlepass_11flaws_replication"]["pairs"]}
    pd11 = {p["id"]: p["score"]["detected"] for p in am["perdim_11flaws"]["pairs"]}
    for name, d in (("11-flaw keyword detection", kw_det), ("11-flaw single-pass detection", sp11),
                    ("11-flaw per-dimension detection", pd11), ("11-flaw two-stage detection", two_det)):
        out["rates"].append(rate(name, sum(d.values()), len(d)))
    out["rates"].append(rate("11-flaw two-stage false alarm", 0, 11))
    kw_k, ts_k = sum(kw_det.values()), sum(two_det.values())
    out["tests"].append({"name": "11-flaw keyword vs two-stage (Fisher exact)", "p": round(fisher_2x2(kw_k, 11 - kw_k, ts_k, 11 - ts_k), 4)})
    out["tests"].append({"name": "11-flaw keyword vs per-dimension (Fisher exact)", "p": round(fisher_2x2(kw_k, 11 - kw_k, 11, 0), 4)})
    b = sum(1 for f in two_det if two_det[f] and not kw_det[f])
    c = sum(1 for f in two_det if kw_det[f] and not two_det[f])
    out["tests"].append({"name": "11-flaw keyword vs two-stage (paired McNemar exact)", "discordant": [b, c], "p": round(mcnemar_exact(b, c), 4)})

    # --- 33-variant benchmark ---------------------------------------------
    runs = [json.load(open(VAR / f"run_{i}.json")) for i in (1, 2, 3)]
    for i, r in enumerate(runs, 1):
        out["rates"].append(rate(f"33-variant two-stage detection run {i}", sum(p["score"]["detected"] for p in r["pairs"]), 33))
    r = runs[0]
    ts = {p["variant_id"]: p["score"]["detected"] for p in r["pairs"]}
    out["rates"].append(rate("33-variant commission detection (run 1)", sum(p["score"]["detected"] for p in r["pairs"] if p["flaw_type"] == "commission"), 22))
    out["rates"].append(rate("33-variant omission detection (run 1)", sum(p["score"]["detected"] for p in r["pairs"] if p["flaw_type"] == "omission"), 11))
    out["rates"].append(rate("33-variant false alarm", sum(p["score"]["false_alarm"] for p in r["pairs"]), 33))
    sp = {p["id"]: p["score"]["detected"] for p in am["singlepass_33variants"]["pairs"]}
    pdn = {p["variant_id"]: p["score"]["detected"] for p in json.load(open(ABL / "perdim_noretrieval.json"))["pairs"]}
    orc = {p["variant_id"]: p["detected"] for p in json.load(open(ABL / "oracle_retrieval.json"))["rows"]}
    out["rates"].append(rate("33-variant single-pass detection", sum(sp.values()), 33))
    out["rates"].append(rate("33-variant per-dimension detection", sum(pdn.values()), 33))
    out["rates"].append(rate("33-variant oracle-retrieval detection", sum(orc.values()), 33))
    for (a, an), (bb, bn) in (((sp, "single-pass"), (pdn, "per-dimension")), ((sp, "single-pass"), (ts, "two-stage")),
                               ((pdn, "per-dimension"), (ts, "two-stage")), ((ts, "two-stage"), (orc, "oracle-retrieval"))):
        ids = set(a) & set(bb)
        b1 = sum(1 for i in ids if a[i] and not bb[i])
        c1 = sum(1 for i in ids if bb[i] and not a[i])
        out["tests"].append({"name": f"33-variant {an} vs {bn} (paired McNemar exact)", "discordant": [b1, c1], "p": round(mcnemar_exact(b1, c1), 4)})

    # --- cross-model panel (single runs) ------------------------------------
    for mid, label in (("claude_opus", "Claude Opus 4.8"), ("gemini_flash", "Gemini 2.5 Flash"), ("llama_open", "Llama 3.1 8B")):
        pr = json.load(open(XM / f"{mid}.json"))["pairs"]
        for key, nm in (("detected", "detection"), ("false_alarm", "false alarm"), ("localized", "localization")):
            out["rates"].append(rate(f"cross-model {label} {nm}", sum(p["score"][key] for p in pr), 33))

    # --- human gold: cell bootstrap -----------------------------------------
    gold = {(r["paper_id"], r["dimension"]): r["gold_risk"] for r in csv.DictReader(open(ANN / "gold_labels.csv"))}
    def load(f: str) -> dict:
        return {(r["paper_id"], r["dimension"]): r["risk"] for r in csv.DictReader(open(ANN / f))}
    random.seed(0)
    for name, pred in (("before (rich run)", load("argus_rich_gold5.csv")),
                       ("demote to medium", load("argus_rich_gold5_calibrated_medium.csv")),
                       ("abstain to unknown", load("argus_rich_gold5_calibrated_unknown.csv"))):
        keys = [k for k in gold if pred.get(k) in ORDER]
        pairs = [(ORDER[pred[k]], ORDER[gold[k]]) for k in keys]
        exact = sum(1 for a, b in pairs if a == b) / len(pairs)
        exs, wks = [], []
        for _ in range(5000):
            s = [random.choice(keys) for _ in keys]
            pp = [(ORDER[pred[k]], ORDER[gold[k]]) for k in s]
            exs.append(sum(1 for a, b in pp if a == b) / len(pp))
            wk = weighted_kappa(pp)
            if wk == wk:
                wks.append(wk)
        exs.sort(); wks.sort()
        q = lambda v, f: v[int(len(v) * f)]
        out["gold_bootstrap"].append({"policy": name, "answered": len(keys), "exact": round(exact, 3),
                                      "exact_ci95": [round(q(exs, .025), 3), round(q(exs, .975), 3)],
                                      "weighted_kappa": round(weighted_kappa(pairs), 3),
                                      "weighted_kappa_ci95": [round(q(wks, .025), 3), round(q(wks, .975), 3)]})

    (ABL / "uncertainty.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    for r in out["rates"]:
        print(f"{r['name']:48s} {r['k']:>2}/{r['n']:<2} {r['rate']:.3f}  [{r['ci95'][0]:.2f}, {r['ci95'][1]:.2f}]")
    for t in out["tests"]:
        print(f"{t['name']:60s} {t.get('discordant', '')} p={t['p']}")
    for g in out["gold_bootstrap"]:
        print(g)


if __name__ == "__main__":
    main()
