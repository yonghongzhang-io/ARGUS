"""Check every reported number in the ClimateNLP paper against the committed data.

No model access. Each claim is recomputed from a committed result file (or, where it can be,
from the cell-level CSVs), compared with the value the paper prints, and the printed form is
then asserted to occur in the LaTeX source. A claim fails if the data disagree with the
expected value or if the text no longer contains it.

    PYTHONPATH=src python3 experiments/verify_paper_numbers.py

Exit status 0 only if every claim passes. Bootstrap intervals are read from the JSON written
by `ablations/uncertainty.py` and `ablations/calibration_recheck.py` (seeded), not re-drawn.
"""
from __future__ import annotations

import csv
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments" / "annotation"))

from compare_argus_gold import cohen_kappa, weighted_kappa  # noqa: E402
from goldpath import gold_path  # noqa: E402

EXP = ROOT / "experiments"
ABL = EXP / "ablations"
TEX = ROOT / "paper_climatenlp"
FROZEN = EXP / "annotation" / "pilot_frozen"
ORDER = {"low": 0, "medium": 1, "high": 2}

_tex_cache: dict[str, str] = {}
results: list[tuple[bool, str, str]] = []


def tex(name: str) -> str:
    if name not in _tex_cache:
        path = TEX / name if name == "main.tex" else TEX / "sections" / name
        raw = re.sub(r"(?<!\\)%.*", "", path.read_text(encoding="utf-8"))
        _tex_cache[name] = re.sub(r"\s+", " ", raw)
    return _tex_cache[name]


def claim(label: str, computed, expected, where: list[tuple[str, str]]) -> None:
    """computed must equal expected; every (file, needle) must occur in the LaTeX."""
    ok = computed == expected
    msg = "" if ok else f"data give {computed!r}, paper value {expected!r}"
    for name, needle in where:
        if re.sub(r"\s+", " ", needle) not in tex(name):
            ok = False
            msg += f" | not in {name}: {needle!r}"
    results.append((ok, label, msg))


def jload(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def r2(x: float) -> str:
    return f"{x:.2f}"


def r3(x: float) -> str:
    return f"{x:.3f}"


def frac(pairs, field: str) -> tuple[int, int]:
    return sum(bool(p["score"][field]) for p in pairs), len(pairs)


def mcnemar(a: list[bool], b: list[bool]) -> tuple[tuple[int, int], float]:
    only_a = sum(x and not y for x, y in zip(a, b))
    only_b = sum(y and not x for x, y in zip(a, b))
    n, k = only_a + only_b, min(only_a, only_b)
    p = 1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)
    return (only_a, only_b), p


def wilson(k: int, n: int) -> str:
    z, p = 1.959964, k / n
    mid = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return f"{max(0.0, mid - half):.2f}--{min(1.0, mid + half):.2f}"


# ---------------------------------------------------------------- 11 clear flaws (Table 1)
def eleven_flaws() -> None:
    two = jload(ABL / "twostage_11flaw_fresh.json")
    det = [f["detected"] for f in two["per_flaw"]]
    loc = [f["localized"] for f in two["per_flaw"]]
    mat = jload(ABL / "ablation_matrix.json")
    sp, pd = mat["singlepass_11flaws_replication"]["pairs"], mat["perdim_11flaws"]["pairs"]
    shared = jload(ABL / "shared_evidence.json")["cells"]
    kw = shared["K-kw"]["11flaws"]
    claim("T1 keyword det/fa/loc",
          (kw["detection"]["k"], kw["false_alarm"]["k"], kw["localization"]["k"]), (2, 0, 2),
          [("results.tex", r"keyword baseline & 0 & 0.182 & 0.000 & 0.182 \\")])
    claim("T1 single-pass", (frac(sp, "detected"), frac(sp, "false_alarm"), frac(sp, "localized")),
          ((9, 11), (0, 11), (9, 11)),
          [("results.tex", r"single-pass & 1 & 0.818 & 0.000 & 0.818 \\")])
    claim("T1 per-dimension", (frac(pd, "detected"), frac(pd, "false_alarm"), frac(pd, "localized")),
          ((11, 11), (0, 11), (11, 11)),
          [("results.tex", r"per-dimension, no retrieval & 11 & 1.000 & 0.000 & 1.000 \\")])
    claim("T1 two-stage", (sum(det), len(det), two["false_alarm_rate"], sum(loc)), (8, 11, 0.0, 8),
          [("results.tex", r"\textbf{two-stage \sys{}} & 22 & \textbf{0.727} & \textbf{0.000} & \textbf{0.727} \\"),
           ("results.tex", r"from $0.182$ to $0.727$ with no false alarms"),
           ("results.tex", r"$0.182\,{\to}\,0.727$"),
           ("main.tex", r"detects $73\%$ of planted flaws, compared with $18\%$")])
    claim("rounding 8/11, 2/11, 9/11", (r3(8 / 11), r3(2 / 11), r3(9 / 11), round(800 / 11), round(200 / 11)),
          ("0.727", "0.182", "0.818", 73, 18), [])
    kw_items = {i["id"].split(":")[-1]: i["detected"] for i in kw["items"]}
    claim("keyword catches exactly the two named omission flaws",
          sorted(k for k, v in kw_items.items() if v), ["measurement_break", "spillover_contamination"],
          [("results.tex", r"(\texttt{measurement\_break}, \texttt{spillover\_contamination})")])
    misses = jload(ABL / "twostage_11flaw_misses.json")
    claim("two-stage: three misses, all omission, all abstentions",
          (len(misses["missed_flaws"]), {m["op"] for m in misses["missed_flaws"]},
           misses["all_three_misses_are_omission_abstentions"]), (3, {"remove"}, True),
          [("results.tex", r"its three misses are all \emph{omission} flaws")])
    # every commission flaw the keyword scorer misses is caught by the two-stage pipeline
    from argus.evaluation.injection import _INJECTIONS
    comm = [f for f, v in _INJECTIONS.items() if v["op"] != "remove"]
    two_det = {f["flaw"]: f["detected"] for f in two["per_flaw"]}
    claim("commission flaws: keyword 0 of 5, two-stage 5 of 5",
          (sum(kw_items[f] for f in comm), sum(two_det[f] for f in comm), len(comm)), (0, 5, 5),
          [("results.tex", r"catching \emph{every} commission flaw the keyword scorer is blind to")])
    fo = jload(ABL / "forensics_gpt-4o-2024-11-20.json")
    claim("dated snapshot replicates detection; localization range",
          (r3(fo["two_stage"]["detection_rate"]), r3(fo["single_pass"]["detection_rate"]),
           r3(fo["two_stage"]["localization_acc"]), r3(fo["two_stage"]["false_alarm_rate"])),
          ("0.727", "0.818", "0.455", "0.091"),
          [("appendix.tex", r"(localization varies between runs, $0.455$--$0.727$, and the snapshot run rates one clean dimension medium, a false alarm of $0.09$"),
           ("results.tex", r"detection replicated on the dated 2024-11-20 snapshot")])
    # Table 8 upper block
    for lab, k, n, ci in [("keyword detection", 2, 11, "0.05--0.48"), ("single-pass detection", 9, 11, "0.52--0.95"),
                          ("per-dimension detection", 11, 11, "0.74--1.00"), ("two-stage detection", 8, 11, "0.43--0.90")]:
        claim(f"T8 11-flaw {lab}", wilson(k, n), ci, [("appendix.tex", f"{lab} & {k}/{n} & {ci}")])
    (d, p) = mcnemar([kw_items[f["flaw"]] for f in two["per_flaw"]], det)
    claim("T8 McNemar keyword vs two-stage", (d, r3(p)), ((1, 7), "0.070"),
          [("appendix.tex", r"McNemar & keyword vs two-stage (11) & 1 / 7 & 0.070"),
           ("appendix.tex", r"(7 vs 1 discordant, $p{=}0.07$")])
    unc = {t["name"]: t for t in jload(ABL / "uncertainty.json")["tests"]}
    claim("T8 Fisher keyword vs two-stage", r3(unc["11-flaw keyword vs two-stage (Fisher exact)"]["p"]), "0.030",
          [("appendix.tex", r"Fisher & keyword vs two-stage (11) & -- & 0.030")])


# ---------------------------------------------------------------- 33 variants
def variants() -> None:
    runs = [jload(EXP / "variants" / "llm_runs" / f"run_{i}.json")["pairs"] for i in (1, 2, 3)]
    det = [frac(r, "detected")[0] for r in runs]
    loc = [frac(r, "localized")[0] for r in runs]
    fa = [frac(r, "false_alarm")[0] for r in runs]
    claim("runs: detection range", (det, r2(min(det) / 33), r2(max(det) / 33)), ([25, 25, 24], "0.73", "0.76"),
          [("results.tex", r"Detection is $0.73$--$0.76$")])
    claim("runs: localization range", (r2(min(loc) / 33), r2(max(loc) / 33)), ("0.64", "0.70"),
          [("results.tex", r"$0.64$--$0.70$")])
    claim("runs: false alarm 3/33 in every run", fa, [3, 3, 3],
          [("results.tex", r"($0.09$ in every run)"), ("appendix.tex", r"two-stage false alarm & 3/33 & --")])
    same_det = sum(len({r[i]["score"]["detected"] for r in runs}) == 1 for i in range(33))
    same_risk = sum(len({r[i]["score"]["injected_risk"] for r in runs}) == 1 for i in range(33))
    claim("runs: agreement across the three runs", (same_det, same_risk), (32, 31),
          [("results.tex", r"(detection identical on 32/33 variants, risk labels on 31/33"),
           ("appendix.tex", r"binary detection agreed on 32/33 variants across the three runs and target-dimension risk labels on 31/33")])
    fa_dims = [sorted({p["target_dimension"] for p in r if p["score"]["false_alarm"]}) for r in runs]
    claim("runs: which clean dimension is flagged", fa_dims, [["inference"], ["specification"], ["specification"]],
          [("results.tex", r"(\emph{inference} in run~1, \emph{specification} in runs~2 and~3)")])

    def mean(field: str, kind: str | None) -> float:
        vals = []
        for r in runs:
            sel = [p for p in r if kind is None or p["flaw_type"] == kind]
            vals.append(sum(bool(p["score"][field]) for p in sel) / len(sel))
        return sum(vals) / 3

    claim("T2 three-run means",
          (r2(mean("detected", "commission")), r2(mean("localized", "commission")), r2(mean("detected", "omission")),
           r2(mean("localized", "omission")), r2(mean("detected", None)), r2(mean("localized", None))),
          ("0.89", "0.82", "0.45", "0.33", "0.75", "0.66"),
          [("results.tex", r"commission & 22 & 0.89 & 0.82 \\"), ("results.tex", r"omission & 11 & 0.45 & 0.33 \\"),
           ("results.tex", r"\textbf{all} & 33 & \textbf{0.75} & \textbf{0.66} \\"),
           ("appendix.tex", r"gpt-4o & 0.75 & 0.09 & 0.66 & 0.89 & 0.45 \\")])
    claim("T5 two-stage row (three-run means, 3 d.p.)",
          (r3(mean("detected", None)), r3(sum(fa) / 99), r3(mean("localized", None))), ("0.747", "0.091", "0.657"),
          [("appendix.tex", r"two-stage (retrieval + gate) & 22 & 0.747 & 0.091 & 0.657 \\"),
           ("results.tex", r"the full two-stage pipeline (twenty-two calls) detects $0.747$")])
    comm = [sum(p["score"]["detected"] for p in r if p["flaw_type"] == "commission") / 22 for r in runs]
    claim("commission detection range over runs", (r2(min(comm)), r2(max(comm))), ("0.86", "0.91"),
          [("results.tex", r"catches $0.86$--$0.91$ of \emph{commission} flaws")])
    om1 = [p["score"] for p in runs[0] if p["flaw_type"] == "omission"]
    verdicts = Counter(s["injected_risk"] for s in om1)
    missed = [s["injected_risk"] for s in om1 if not s["detected"]]
    claim("run 1 omission verdicts; six misses all unknown",
          ((verdicts["unknown"], verdicts["high"], verdicts["medium"], verdicts["low"]), missed),
          ((6, 3, 2, 0), ["unknown"] * 6),
          [("results.tex", r"the six missed variants all abstain to \texttt{unknown}"),
           ("appendix.tex", r"gpt-4o & 6 / 3 / 2 / 0 & 2 / 22 & -- \\")])
    c1 = [p for p in runs[0] if p["flaw_type"] == "commission"]
    claim("run 1 clean >= medium on commission pairs",
          sum(ORDER.get(p["score"]["clean_risk"], -1) >= 1 for p in c1), 2, [])
    claim("T8 run-1 rows",
          (det[0], wilson(25, 33), sum(p["score"]["detected"] for p in c1), wilson(20, 22),
           sum(s["detected"] for s in om1), wilson(5, 11)),
          (25, "0.59--0.87", 20, "0.72--0.97", 5, "0.21--0.72"),
          [("appendix.tex", r"two-stage detection (run 1) & 25/33 & 0.59--0.87"),
           ("appendix.tex", r"\quad commission & 20/22 & 0.72--0.97"), ("appendix.tex", r"\quad omission & 5/11 & 0.21--0.72")])

    # ablation arms
    mat = jload(ABL / "ablation_matrix.json")["singlepass_33variants"]["pairs"]
    pdm = jload(ABL / "perdim_noretrieval.json")["pairs"]
    orc = jload(ABL / "oracle_retrieval.json")["rows"]
    claim("T5 single pass", (frac(mat, "detected"), frac(mat, "false_alarm"), frac(mat, "localized")),
          ((24, 33), (0, 33), (24, 33)),
          [("appendix.tex", r"full-paper single pass & 1 & 0.727 & 0.000 & 0.727 \\"),
           ("appendix.tex", r"single-pass detection & 24/33 & 0.56--0.85"), ("results.tex", r"detects $0.727$; per-dimension")])
    claim("T5 per-dimension", (frac(pdm, "detected"), frac(pdm, "false_alarm"), frac(pdm, "localized"), r3(29 / 33)),
          ((29, 33), (0, 33), (29, 33), "0.879"),
          [("appendix.tex", r"per-dimension, no retrieval & 11 & 0.879 & 0.000 & 0.879 \\"),
           ("appendix.tex", r"per-dimension detection & 29/33 & 0.73--0.95"), ("results.tex", r"detects $0.879$")])
    oc = [r for r in orc if r["flaw_type"] == "commission"]
    oo = [r for r in orc if r["flaw_type"] == "omission"]
    claim("oracle-retrieval arm",
          (sum(r["detected"] for r in orc), r2(sum(r["detected"] for r in oc) / 22),
           r2(sum(r["detected"] for r in oo) / 11), r2(sum(r["false_alarm"] for r in orc) / 33), wilson(30, 33)),
          (30, "0.86", "1.00", "0.21", "0.76--0.97"),
          [("results.tex", r"detects $0.86$ of commissions and $1.00$ of omissions"),
           ("results.tex", r"($0.21$ oracle arm vs $0.09$"),
           ("appendix.tex", r"oracle-retrieval detection & 30/33 & 0.76--0.97")])
    ids = [p["variant_id"] for p in runs[0]]
    by = lambda seq, key: {x[key]: x for x in seq}  # noqa: E731
    spd = [by(mat, "id")[i]["score"]["detected"] for i in ids]
    pdd = [by(pdm, "variant_id")[i]["score"]["detected"] for i in ids]
    twd = [p["score"]["detected"] for p in runs[0]]
    ord_ = [by(orc, "variant_id")[i]["detected"] for i in ids]
    for lab, a, b, disc, p3, p2, row in [
        ("single-pass vs per-dim", spd, pdd, (1, 6), "0.125", "0.13", r"McNemar & single-pass vs per-dim.\ (33) & 1 / 6 & 0.125"),
        ("per-dim vs two-stage", pdd, twd, (5, 1), "0.219", "0.22", r"McNemar & per-dim.\ vs two-stage (33) & 5 / 1 & 0.219"),
        ("single-pass vs two-stage", spd, twd, (5, 6), "1.000", "1.00", r"McNemar & single-pass vs two-stage (33) & 5 / 6 & 1.000"),
        ("two-stage vs oracle", twd, ord_, (1, 6), "0.125", "0.13", r"McNemar & two-stage vs oracle (33) & 1 / 6 & 0.125"),
    ]:
        d, p = mcnemar(a, b)
        claim(f"T8 McNemar {lab}", (d, r3(p), r2(p + 1e-9)), (disc, p3, p2), [("appendix.tex", row)])
    claim("main-text McNemar p-values", True, True,
          [("results.tex", r"$p{=}0.13$, per-dimension vs two-stage $p{=}0.22$, two-stage vs oracle $p{=}0.13$")])
    gained = [i for i, (x, y) in enumerate(zip(twd, ord_)) if y and not x]
    claim("every extra oracle catch is an omission the gate abstained on",
          all(runs[0][i]["flaw_type"] == "omission" and runs[0][i]["score"]["injected_risk"] == "unknown" for i in gained),
          True, [("results.tex", r"every extra omission the oracle arm catches is a case the gated pipeline had scored \texttt{unknown} at the gate")])

    # cross-model
    names = {"claude_opus": "Claude Opus 4.8", "gemini_flash": "Gemini 2.5 Flash", "llama_open": "Llama 3.1 8B (local)"}
    t6 = {"claude_opus": ("0.91", "0.82", "0.24", "1.00", "0.73", (3, 7, 1, 0), 18, 20),
          "gemini_flash": ("0.79", "0.18", "0.36", "0.91", "0.55", (4, 3, 3, 1), 4, 26),
          "llama_open": ("0.94", "0.27", "0.27", "0.95", "0.91", (1, 10, 0, 0), 6, 19)}
    t8 = {"claude_opus": ("Opus 4.8", 30, "0.76--0.97", 27), "gemini_flash": ("Gemini 2.5 Flash", 26, "0.62--0.89", 6),
          "llama_open": ("Llama 3.1 8B", 31, "0.80--0.98", 9)}
    g = by(runs[0], "variant_id")
    for key, exp in t6.items():
        pairs = jload(EXP / "models" / "crossmodel" / f"{key}.json")["pairs"]
        c = [p for p in pairs if p["flaw_type"] == "commission"]
        o = [p for p in pairs if p["flaw_type"] == "omission"]
        v = Counter(p["score"]["injected_risk"] for p in o)
        got = (r2(frac(pairs, "detected")[0] / 33), r2(frac(pairs, "false_alarm")[0] / 33),
               r2(frac(pairs, "localized")[0] / 33), r2(frac(c, "detected")[0] / 22), r2(frac(o, "detected")[0] / 11),
               (v["unknown"], v["high"], v["medium"], v["low"]),
               sum(ORDER.get(p["score"]["clean_risk"], -1) >= 1 for p in c),
               sum(p["score"]["injected_risk"] == g[p["variant_id"]]["score"]["injected_risk"] for p in pairs))
        om = " / ".join(str(x) for x in exp[5])
        claim(f"T6/T7 {names[key]}", got, exp,
              [("appendix.tex", f"{names[key]} & {exp[0]} & {exp[1]} & {exp[2]} & {exp[3]} & {exp[4]} \\\\"),
               ("appendix.tex", f"{names[key]} & {om} & {exp[6]} / 22 & {exp[7]} / 33 \\\\")])
        short, k, ci, fa_k = t8[key]
        claim(f"T8 {short}", (frac(pairs, "detected")[0], wilson(k, 33), frac(pairs, "false_alarm")[0]), (k, ci, fa_k),
              [("appendix.tex", f"{short} detection & {k}/33 & {ci}"), ("appendix.tex", f"{short} false alarm & {fa_k}/33 & --")])
    claim("main-text cross-model sentence", True, True,
          [("results.tex", r"(gpt-4o $0.89$, Claude Opus~4.8 $1.00$, Gemini~2.5 Flash $0.91$, Llama~3.1 8B $0.95$)"),
           ("results.tex", r"on 18 of 22 commission pairs (false alarm $0.82$)"),
           ("results.tex", r"(one \texttt{unknown} in eleven omissions)"), ("results.tex", r"(26/33 identical injected verdicts)")])


# ---------------------------------------------------------------- real-paper corpus
def corpus() -> None:
    res = EXP / "real_papers" / "corpus_results"
    drop = {"paper_164"}
    llm = [r for r in rows(res / "did_llm_risks.csv") if r["paper_id"] not in drop]
    kw = [r for r in rows(res / "did_keyword_risks.csv") if r["paper_id"] not in drop]
    sp = [r for r in rows(res / "did_single_pass_risks.csv") if r["paper_id"] not in drop]
    share = lambda rs, lv: sum(r["risk"] == lv for r in rs) / len(rs)  # noqa: E731
    claim("corpus size", (len({r["paper_id"] for r in llm}), len(llm), len(kw)), (26, 286, 286),
          [("appendix.tex", r"so every count reads 26 papers and 286 cells")])
    claim("keyword low share; LLM unknown and high shares",
          (round(100 * share(kw, "low")), round(100 * share(llm, "unknown")), round(100 * share(llm, "high"))),
          (91, 40, 44),
          [("results.tex", r"$91\%$ of its judgements are \emph{low}"), ("results.tex", r"${\sim}40\%$ of judgements are \texttt{unknown}"),
           ("results.tex", r"Roughly $44\%$ of judgements on these papers are \emph{high}"),
           ("main.tex", r"abstains on about $40\%$ of paper--dimension assessments")])
    dup = lambda f: [r["risk"] for r in rows(res / f) if r["paper_id"] == "paper_164"] == \
                    [r["risk"] for r in rows(res / f) if r["paper_id"] == "paper_120"]  # noqa: E731
    claim("duplicate entry audited identically by both assessors",
          (dup("did_llm_risks.csv"), dup("did_keyword_risks.csv")), (True, True),
          [("appendix.tex", r"both copies received identical audits on all eleven dimensions from both assessors")])
    common = {r["paper_id"] for r in sp} & {r["paper_id"] for r in llm}
    g = [r for r in llm if r["paper_id"] in common]
    s = [r for r in sp if r["paper_id"] in common]
    pct = lambda x: f"{100 * x:.1f}"  # noqa: E731
    claim("gated vs permissive single pass on the common papers",
          (len(common), len(s), sum(r["risk"] == "unknown" for r in s), pct(share(s, "unknown")), pct(share(g, "unknown")),
           pct(share(g, "low")), pct(share(s, "low")), pct(share(g, "medium")), pct(share(s, "medium")),
           pct(share(g, "high")), pct(share(s, "high"))),
          (25, 275, 1, "0.4", "38.9", "1.8", "14.9", "14.2", "43.6", "45.1", "41.1"),
          [("results.tex", r"abstained on one of 275 cells ($0.4\%$), against $38.9\%$ mechanical abstentions"),
           ("appendix.tex", r"Over the 25 papers common to both runs ($275$ cells) it chose \texttt{unknown} once ($0.4\%$"),
           ("appendix.tex", r"low ($1.8\%\!\to\!14.9\%$) or medium ($14.2\%\!\to\!43.6\%$)"),
           ("appendix.tex", r"(gated $45.1\%$, single pass $41.1\%$)")])
    man = [r for r in rows(EXP / "real_papers" / "corpus_manifest.csv") if r["counted"] == "yes"]
    venues = Counter(r["venue_in_table"] for r in man)
    single = sum(venues[v] for v in ("Journal of Finance", "Review of Economics and Statistics", "Review of Economic Studies",
                                     "Journal of Monetary Economics", "Journal of International Economics"))
    claim("T10 venues",
          (len(man), venues["American Economic Review"], venues["Quarterly Journal of Economics"],
           venues["Journal of Political Economy"], venues["Journal of Financial Economics"], venues["AEJ: Applied Economics"],
           single, venues["New England Journal of Medicine"], venues["NBER working-paper version"]),
          (26, 4, 3, 2, 2, 2, 5, 1, 7),
          [("appendix.tex", r"American Economic Review & 4 \\"), ("appendix.tex", r"Quarterly Journal of Economics & 3 \\"),
           ("appendix.tex", r"Journal of Political Economy & 2 \\"), ("appendix.tex", r"Journal of Financial Economics & 2 \\"),
           ("appendix.tex", r"AEJ: Applied Economics & 2 \\"), ("appendix.tex", r"(one each) & 5 \\"),
           ("appendix.tex", r"New England Journal of Medicine & 1 \\"), ("appendix.tex", r"NBER working-paper versions & 7 \\"),
           ("appendix.tex", r"Nineteen entries are journal articles, one of them in a medical journal, and seven")])
    topics = Counter(r["topic"] for r in man)
    claim("corpus topics",
          [topics[t] for t in ("finance and banking", "health", "education", "environment and energy",
                               "international trade", "labour", "crime and social policy", "industrial location")],
          [5, 4, 4, 4, 3, 3, 2, 1],
          [("appendix.tex", r"finance and banking (5), health (4), education (4), environment and energy (4), international trade (3), labour (3), crime and social policy (2), and industrial location (1)")])
    env = {r["paper_id"] for r in man if r["topic"] == "environment and energy"}
    e = [r for r in llm if r["paper_id"] in env]
    o = [r for r in llm if r["paper_id"] not in env]
    claim("environment-and-energy subset vs remainder",
          (len(e), r2(share(e, "high")), r2(share(e, "unknown")), len(o), r2(share(o, "high")), r2(share(o, "unknown"))),
          (44, "0.34", "0.43", 242, "0.46", "0.39"),
          [("appendix.tex", r"share of $0.43$ (44 cells), against $0.39$ in the remaining papers (242 cells); the corresponding high-risk shares are $0.34$ and $0.46$")])
    titles = [r["title_as_indexed"] for r in man]
    listed = tex("appendix.tex").split(r"\label{tab:corpuslist}")[1].split(r"\end{tabular}")[0].count(r"\\") - 0
    claim("T11 lists one title per counted paper", (len(titles), listed), (26, 26), [])


# ---------------------------------------------------------------- expert pilot
def pilot() -> None:
    gold = {(r["paper_id"], r["dimension"]): r for r in rows(gold_path())}  # final gold once locked
    g = {k: v["gold_risk"] for k, v in gold.items()}
    cnt = Counter(g.values())
    claim("gold distribution", (len(g), cnt["low"], cnt["medium"], cnt["high"]), (55, 29, 24, 2),
          [("results.tex", r"The adjudicated gold (55 cells) is low 29, medium 24, high 2")])
    nonagree = [v for v in gold.values() if v["source"] != "agree"]
    claim("round-1 disagreements: 27, of which 11 flagged ambiguous",
          (len(nonagree), sum(v["ambiguous"] == "1" for v in gold.values()),
           len(nonagree) - sum(v["ambiguous"] == "1" for v in nonagree)), (27, 11, 16),
          [("appendix.tex", r"Of the 27 round-1 disagreements, 16 resolved to a single label once the low/medium boundary was anchored, and 11 were flagged intrinsically ambiguous")])
    papers = sorted({k[0] for k in g})
    sheets = ROOT / "data" / "annotations"  # raw annotator sheets: private, present only locally
    where = [("appendix.tex", r"(Cohen's $\kappa=0.17$; quadratic-weighted $\kappa=0.31$), and $96\%$ of disagreements were a single severity step apart")]
    if all((sheets / f"{p}_{x}.csv").exists() for p in papers for x in "AB"):
        lab = {x: {(r["paper_id"], r["dimension"]): r["risk"].strip().lower()
                   for p in papers for r in rows(sheets / f"{p}_{x}.csv")} for x in "AB"}
        pr = [(lab["A"][k], lab["B"][k]) for k in g]
        dis = [(x, y) for x, y in pr if x != y]
        claim("round-1 agreement (from the private annotator sheets)",
              (len(pr), len(dis), r2(cohen_kappa(pr)), r2(weighted_kappa(pr)),
               round(100 * sum(abs(ORDER[x] - ORDER[y]) == 1 for x, y in dis) / len(dis))),
              (55, 27, "0.17", "0.31", 96), where)
    else:
        agg = (EXP / "annotation" / "RESULTS.md").read_text(encoding="utf-8")
        claim("round-1 agreement (committed aggregate; raw sheets not present)",
              all(t in agg for t in ("| **weighted kappa (quadratic)** | **0.31** |", "| **adjacent-disagreement share** | **0.96** |",
                                     "| (plain Cohen's kappa, 3-level) | 0.17 |")), True, where)
    corpus_run = {(r["paper_id"], r["dimension"]): r["risk"]
                  for r in rows(EXP / "real_papers" / "corpus_results" / "did_llm_risks.csv") if r["paper_id"] in papers}
    ans = [(corpus_run[k], g[k]) for k in g if corpus_run[k] != "unknown"]
    over = sum(ORDER[a] > ORDER[b] for a, b in ans)
    under = sum(ORDER[a] < ORDER[b] for a, b in ans)
    exact = sum(a == b for a, b in ans)
    high_gold = [k for k in g if g[k] == "high"]
    claim("corpus run vs gold",
          (len(papers), 55 - len(ans), len(ans), over, under, exact, sum(a == "high" for a, _ in ans),
           sorted(corpus_run[k] for k in high_gold)),
          (5, 22, 33, 28, 0, 5, 24, ["high", "unknown"]),
          [("results.tex", r"\sys{} abstains on 22/55 cells"),
           ("results.tex", r"28/33 answered cells are more severe than the adjudicated gold, none less severe; gold contains two high-risk cells, \sys{} assigns 24"),
           ("results.tex", r"of the two high gold cells \sys{} flags one and abstains on the other"),
           ("main.tex", r"on 28 of the 33 assessments it completes"),
           ("appendix.tex", r"\sys{} abstains on 22 and, of the 33 it answers, is more severe than the gold on 28, matches it on 5, and is less severe on none")])
    strict = [(corpus_run[k], g[k]) for k in g]
    claim("T13 agreement",
          (r3(exact / 33), r3(cohen_kappa(ans)), r3(weighted_kappa(ans)), r3(exact / 55), r3(cohen_kappa(strict))),
          ("0.152", "0.019", "0.044", "0.091", "0.002"),
          [("appendix.tex", r"exclude (coverage) & 33 & 0.152 & 0.019 & 0.044 \\"),
           ("appendix.tex", r"mismatch (strict) & 55 & 0.091 & 0.002 & -- \\")])

    rich = {(r["paper_id"], r["dimension"]): r for r in rows(FROZEN / "argus_rich_gold5.csv")}
    differs = [k for k in g if rich[k]["risk"] != corpus_run[k]]
    claim("rich re-run differs from the corpus run in one cell", len(differs), 1,
          [("results.tex", r"it differs from the corpus run of \S\ref{sec:vsgold} in one cell")])
    gate = Counter((r["retrieval_quality"], r["risk"]) for r in rich.values())
    table = [[gate[(q, lv)] for lv in ("unknown", "high", "medium", "low")] for q in ("failed", "weak", "good")]
    weak_high_missing = sum(r["retrieval_quality"] == "weak" and r["risk"] == "high" and r["evidence_status"] == "missing"
                            for r in rich.values())
    claim("T3 gate outcome by risk", (table, weak_high_missing), ([[22, 0, 0, 0], [0, 20, 2, 0], [0, 5, 5, 1]], 19),
          [("appendix.tex", r"failed (22) & 22 & 0 & 0 & 0 \\"), ("appendix.tex", r"weak (22) & 0 & 20 & 2 & 0 \\"),
           ("appendix.tex", r"good (11) & 0 & 5 & 5 & 1 \\"),
           ("results.tex", r"all 22 failed-retrieval cells are \texttt{unknown}, and 20 of the 22 weak-retrieval cells are \emph{high}, 19 of them with \texttt{evidence\_status=missing}"),
           ("discussion.tex", r"(20 of 22 weak-retrieval pilot cells)")])
    over_high = [k for k in g if rich[k]["risk"] == "high" and ORDER[g[k]] < 2]
    claim("over-severe highs: missing evidence, weak retrieval",
          (len(over_high), sum(rich[k]["evidence_status"] == "missing" for k in over_high),
           sum(rich[k]["retrieval_quality"] == "weak" for k in over_high)), (24, 23, 20),
          [("results.tex", r"$23/24$ have \texttt{evidence\_status=missing} and $20/24$ have \texttt{retrieval\_quality=weak}")])
    folds = {}
    for held in papers:
        ks = [k for k in over_high if k[0] != held]
        folds[held] = (round(100 * sum(rich[k]["retrieval_quality"] == "weak" for k in ks) / len(ks)),
                       round(100 * sum(rich[k]["evidence_status"] == "missing" for k in ks) / len(ks)))
    claim("leave-one-paper-out ranges",
          (min(v[0] for v in folds.values()), max(v[0] for v in folds.values()),
           min(v[1] for v in folds.values()), max(v[1] for v in folds.values())), (79, 86, 94, 100),
          [("appendix.tex", r"$79$--$86\%$ have weak retrieval and $94$--$100\%$ have missing evidence")])

    rec = jload(ABL / "calibration_recheck.json")["policies"]

    def metrics(pred: dict) -> tuple:
        a = [(pred[k], g[k]) for k in g if pred[k] != "unknown"]
        hi = [k for k in g if pred[k] == "high"]
        return (len(a), 55 - len(a), sum(ORDER[x] > ORDER[y] for x, y in a), sum(x == y for x, y in a),
                f"{sum(g[k] == 'high' for k in hi)}/{len(hi)}",
                f"{sum(pred[k] == 'high' for k in high_gold)}/{len(high_gold)}", r2(weighted_kappa(a)))

    before = {k: rich[k]["risk"] for k in g}

    def rule1(policy: str) -> dict:
        return {k: (policy if rich[k]["risk"] == "high" and rich[k]["retrieval_quality"] == "weak" else rich[k]["risk"]) for k in g}

    def four(policy: str) -> dict:
        return {(r["paper_id"], r["dimension"]): r["risk"] for r in rows(FROZEN / f"argus_rich_gold5_calibrated_{policy}.csv")}

    cols = [metrics(before), metrics(rule1("medium")), metrics(rule1("unknown")), metrics(four("medium")), metrics(four("unknown"))]
    claim("T14 calibration table", cols,
          [(33, 22, 29, 4, "1/25", "1/2", "0.06"), (33, 22, 21, 12, "1/5", "1/2", "0.21"), (13, 42, 9, 4, "1/5", "1/2", "0.32"),
           (33, 22, 18, 15, "1/2", "1/2", "0.13"), (13, 42, 6, 7, "1/2", "1/2", "0.25")],
          [("appendix.tex", r"over-severe (answ.) & 29 & 21 & 9 & 18 & 6 \\"),
           ("appendix.tex", r"high precision & 1/25 & 1/5 & 1/5 & 1/2 & 1/2 \\"),
           ("appendix.tex", r"high recall & 1/2 & 1/2 & 1/2 & 1/2 & 1/2 \\"),
           ("appendix.tex", r"exact agr.\ (answ.) & 0.12 & 0.36 & 0.31 & 0.45 & 0.54 \\"),
           ("appendix.tex", r"wt.\ $\kappa$ (answ.) & 0.06 & 0.21 & 0.32 & 0.13 & 0.25 \\"),
           ("appendix.tex", r"answered / \texttt{unk} & 33/22 & 33/22 & 13/42 & 33/22 & 13/42 \\")])
    claim("exact-agreement rounding", (r2(4 / 33), r2(12 / 33), r2(4 / 13), f"{15 / 33:.3f}"[:4], r2(7 / 13)),
          ("0.12", "0.36", "0.31", "0.45", "0.54"),
          [("results.tex", r"raises exact agreement from $0.12$ to $0.36$ ($4/33$ to $12/33$) and cuts over-severe cells from 29 to 21"),
           ("results.tex", r"Three further single-cell rules lift exact agreement to $0.45$"),
           ("results.tex", r"so its pre-calibration figures are 29/33 over-severe and exact agreement $0.12$")])
    fired = Counter(r["calibration_rule"] for r in rows(FROZEN / "argus_rich_gold5_calibrated_medium.csv"))
    claim("rules fired", sorted(fired.values()), [1, 1, 1, 20, 32],
          [("appendix.tex", r"Rule~1 (20 cells)"), ("results.tex", r"a weak-retrieval \emph{high} (20 cells)"),
           ("appendix.tex", r"Three further rules each fire on one cell")])
    r1 = rule1("medium")
    fixed = sum(before[k] != g[k] and r1[k] == g[k] for k in g if before[k] != "unknown")
    broke = sum(before[k] == g[k] and r1[k] != g[k] for k in g if before[k] != "unknown")
    f4 = four("medium")
    fixed4 = sum(before[k] != g[k] and f4[k] == g[k] for k in g if before[k] != "unknown")
    p1 = 2 * sum(math.comb(fixed, i) for i in range(0 + 1)) / 2 ** fixed
    p4 = 2 * sum(math.comb(fixed4, i) for i in range(0 + 1)) / 2 ** fixed4
    claim("paired tests for the calibration lift", (fixed, broke, r3(p1), fixed4, r3(p4)), (8, 0, "0.008", 11, "0.001"),
          [("results.tex", r"changes eight incorrect labels to the adjudicated label and no correct label to an incorrect one, and keeps the one high gold cell \sys{} had caught"),
           ("appendix.tex", r"turns eight wrong cells exact and none the other way (exact McNemar $p{=}0.008$); all four rules turn eleven ($p{=}0.001$)")])
    pv = rec["medium"]["paired_vs_before"]
    claim("per-paper sign tests",
          (pv["dominant_rule_only"]["papers_improved"], pv["dominant_rule_only"]["papers_tied"],
           pv["dominant_rule_only"]["sign_test_p_ties_dropped"], pv["four_rules"]["papers_improved"],
           pv["four_rules"]["sign_test_p_ties_dropped"]), (4, 1, 0.125, 5, 0.0625),
          [("appendix.tex", r"improves exact agreement in four papers and ties in one (sign test with the tie dropped, $p{=}0.125$); four rules improve all five ($p{=}0.0625$"),
           ("results.tex", r"the same way in four of five papers (one tie)")])
    claim("abstain policy fixes nothing", rec["unknown"]["paired_vs_before"]["dominant_rule_only"]["cells_fixed"], 0,
          [("results.tex", r"The abstention variant removes those 20 predictions (coverage $33/55 \to 13/55$) and leaves the remaining labels unchanged")])
    claim("released script reproduces the historical outputs",
          (rec["medium"]["reproduces_historical_output"], rec["unknown"]["reproduces_historical_output"]), ([55, 55], [55, 55]),
          [("appendix.tex", r"reproduces the historical outputs on all 55 cells")])

    ci = lambda v: f"{v[0]:.2f}--{v[1]:.2f}".replace("-0.", "$-0.").replace("$-0.", "$-0.", 1)  # noqa: E731

    def cell(block: dict) -> tuple[str, str]:
        e, k = block["exact_ci95"], block["weighted_kappa_ci95"]
        kk = f"{k[0]:.2f}--{k[1]:.2f}" if k[0] >= 0 else f"$-{abs(k[0]):.2f}$--{k[1]:.2f}"
        return f"{e[0]:.2f}--{e[1]:.2f}", kk

    expect = {("medium", "before"): r"before & 33 & 0.12 (0.03--0.24) & 0.06 ($-0.02$--0.15) \\",
              ("medium", "dominant_rule_only"): r"rule 1, demote$\to$med & 33 & 0.36 (0.21--0.55) & 0.21 (0.02--0.39) \\",
              ("unknown", "dominant_rule_only"): r"rule 1, abstain$\to$unk & 13 & 0.31 (0.08--0.54) & 0.32 (0.04--0.58) \\",
              ("medium", "four_rules"): r"rules 1--4, demote$\to$med & 33 & 0.45 (0.30--0.61) & 0.13 ($-0.07$--0.37) \\",
              ("unknown", "four_rules"): r"rules 1--4, abstain$\to$unk & 13 & 0.54 (0.31--0.77) & 0.25 ($-0.17$--0.69) \\"}
    for (pol, key), row in expect.items():
        e, k = cell(rec[pol][key])
        claim(f"T9 bootstrap interval {pol}/{key}", (f"({e})" in row, f"({k})" in row), (True, True), [("appendix.tex", row)])
    del ci


# ---------------------------------------------------------------- shared-evidence control
def shared() -> None:
    d = jload(ABL / "shared_evidence.json")
    cells = d["cells"]
    exp = {"K-kw": ("2/11", "0/11", "2/11", "8/33", "0/33", "8/33", "0.00"),
           "K-llm": ("10/11", "1/11", "8/11", "31/33", "3/33", "22/33", "0.15"),
           "S-kw": ("1/11", "0/11", "1/11", "2/33", "0/33", "2/33", "0.00"),
           "S-llm": ("11/11", "0/11", "11/11", "31/33", "0/33", "22/33", "0.16")}
    kn = lambda x: f"{x['k']}/{x['n']}"  # noqa: E731
    for name, e in exp.items():
        a, b = cells[name]["11flaws"], cells[name]["33variants"]
        got = (kn(a["detection"]), kn(a["false_alarm"]), kn(a["localization"]), kn(b["detection"]), kn(b["false_alarm"]),
               kn(b["localization"]), r2(b["offtarget_alarm_injected"]["rate"]))
        claim(f"T15 {name}", got, e, [("appendix.tex", f"{name} & " + " & ".join(e) + r" \\")])
    con = {(c["a"], c["b"], c["set"], c["outcome"]): c for c in d["contrasts"]}
    k11 = con[("K-kw", "K-llm", "11flaws", "detected")]
    k33 = con[("K-kw", "K-llm", "33variants", "detected")]
    claim("policy contrast on the keyword chunks",
          (k11["discordant_a_only_b_only"], r3(k11["mcnemar_exact_p"]), k33["mcnemar_exact_p"] < 0.001), ([0, 8], "0.008", True),
          [("appendix.tex", r"(eight gained, none lost; exact McNemar $p{=}0.008$) and from 8 to 31 of 33 variants ($p{<}0.001$); on S, from 1 to 11 and from 2 to 31"),
           ("results.tex", r"detects 10 of 11 flaws against the keyword scorer's 2 (exact McNemar $p{=}0.008$), and 31 against 8 of the 33 variants")])
    off = (cells["K-llm"]["11flaws"]["offtarget_alarm_injected"]["rate"], cells["S-llm"]["11flaws"]["offtarget_alarm_injected"]["rate"],
           cells["K-llm"]["33variants"]["offtarget_alarm_injected"]["rate"], cells["S-llm"]["33variants"]["offtarget_alarm_injected"]["rate"])
    claim("off-target range on injected papers", (round(100 * min(off)), round(100 * max(off))), (11, 16),
          [("results.tex", r"$11$--$16\%$ of non-target dimensions"), ("appendix.tex", r"The judge rates $11$--$16\%$ of non-target dimensions")])
    claim("clean off-target rate and the single clean false alarm",
          (r2(cells["K-llm"]["33variants"]["offtarget_alarm_clean"]["rate"]), cells["K-llm"]["clean_dimensions_flagged"],
           cells["S-llm"]["clean_dimensions_flagged"]), ("0.09", ["treatment_definition_sutva"], []),
          [("appendix.tex", r"All three hold, the last narrowly ($0.09$)"), ("appendix.tex", r"the judge also rates one clean dimension (SUTVA) medium")])
    claim("run bookkeeping",
          (d["n_papers"], d["n_papers"] * 11 * 2, sum(len(cells[c]["errors"]) for c in cells), d["model"],
           kn(cells["S-llm"]["33variants"]["detection_omission"])), (45, 990, 0, "gpt-4o-2024-11-20", "11/11"),
          [("appendix.tex", r"All 45 papers (one clean fixture, 11 flaws, 33 variants)"), ("appendix.tex", r"990 adequacy calls, none failed"),
           ("appendix.tex", r"(omission variants 11/11 vs 5/11)")])
    claim("T15 reference row", True, True, [("appendix.tex", r"\textit{gated two-stage} & 8/11 & 0/11 & 8/11 & 25/33 & 3/33 & 0.66 & -- \\")])


def hygiene() -> None:
    pat = re.compile(r"\b(TODO|FIXME|TBD|XXX|PENDING|placeholder)\b|\?\?", re.I)
    hits = []
    for path in [TEX / "main.tex", *sorted((TEX / "sections").glob("*.tex"))]:
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if pat.search(re.sub(r"(?<!\\)%.*", "", line)):
                hits.append(f"{path.name}:{n}")
    claim("no TODO / PENDING / placeholder markers in the LaTeX source", hits, [], [])
    out = []
    for path in sorted(ABL.glob("*.json")) + sorted((EXP / "annotation").glob("*.csv")):
        if re.search(r"\bpending\b|\bTODO\b", path.read_text(encoding="utf-8"), re.I):
            out.append(path.name)
    claim("no pending markers in committed result files", out, [], [])
    import hashlib
    bad = []
    for line in (FROZEN / "MANIFEST.sha256").read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        digest, name = line.split()[:2]
        target = FROZEN / Path(name).name
        if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
            bad.append(name)
    claim("frozen pilot inputs match their checksums", bad, [], [])


def main() -> int:
    for part in (eleven_flaws, variants, corpus, pilot, shared, hygiene):
        try:
            part()
        except Exception as exc:  # a crash is a failure, not a skip
            results.append((False, f"{part.__name__} crashed", repr(exc)))
    failed = [r for r in results if not r[0]]
    for ok, label, msg in results:
        print(("PASS  " if ok else "FAIL  ") + label + (f"\n        {msg}" if msg else ""))
    print(f"\n{len(results) - len(failed)} of {len(results)} claims verified")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
