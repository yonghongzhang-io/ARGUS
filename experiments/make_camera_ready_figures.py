"""Data figures for the ClimateNLP camera-ready, in one consistent style.

Drawn at their printed size (so type is never scaled below ~6.5 pt), thin marks, hairline
grid, surface-coloured gaps between touching fills, a neutral gray for baselines and a
single accent for the method. Colours were checked with a colour-vision-deficiency
validator: risk levels (low/medium/high) separate at dE 11.2 under protanopia and 19.5 in
normal vision; "unknown" is a deliberate neutral, not a hue; the outcome pair (exact /
over-severe) separates at dE 10.7 / 22.1.

Reads only committed result files and the frozen pilot. Writes ONLY to the directory given
(default paper_climatenlp/figures); it never touches paper/figures.

    PYTHONPATH=src python3 experiments/make_camera_ready_figures.py [out_dir]
"""
from __future__ import annotations

import csv
import json
import os
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments" / "annotation"))
os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "argus_mplconfig"))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from matplotlib.patches import Patch, PathPatch  # noqa: E402
from matplotlib.path import Path as MPath  # noqa: E402

from argus.config import load_flaws  # noqa: E402
from goldpath import gold_path  # noqa: E402  final gold once locked, else the frozen June gold
from argus.evaluation.injection import _INJECTIONS  # noqa: E402
from argus.evaluation.runner import evaluate_flaws  # noqa: E402

SURFACE = "#FFFFFF"
INK, MUTED, HAIR = "#1F2328", "#59636E", "#E3E6EA"
RISK = {"low": "#1E9E7A", "medium": "#E09A1F", "high": "#CB4B3C", "unknown": "#B4B9C0"}
BASE, ACCENT = "#B4B9C0", "#2A78D6"          # baseline (neutral) / method (accent)
EXACT, OVER = "#2A78D6", "#B5479A"            # outcome of an answered cell
DIM_LABEL = {"parallel_trends": "parallel trends", "no_anticipation": "no anticipation",
             "treatment_timing": "staggered timing", "treatment_definition_sutva": "SUTVA / spillovers",
             "control_group": "control group", "specification": "specification", "inference": "inference",
             "sample_period": "sample period", "concurrent_policies": "concurrent policies",
             "robustness_placebo": "placebo / robustness", "data_measurement": "data measurement"}
DIMS = list(DIM_LABEL)
RANK = {"low": 0, "medium": 1, "high": 2}


def style() -> None:
    plt.rcParams.update({
        "font.family": "sans-serif", "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "font.size": 7.5, "axes.titlesize": 8.2, "axes.labelsize": 7.5, "xtick.labelsize": 7, "ytick.labelsize": 7,
        "axes.edgecolor": HAIR, "axes.linewidth": 0.6, "axes.labelcolor": MUTED, "text.color": INK,
        "xtick.color": MUTED, "ytick.color": MUTED, "xtick.major.size": 0, "ytick.major.size": 0,
        "axes.spines.top": False, "axes.spines.right": False, "axes.facecolor": SURFACE, "figure.facecolor": SURFACE,
        "legend.frameon": False, "legend.fontsize": 7, "pdf.fonttype": 42, "ps.fonttype": 42})


def panel_title(ax, letter: str, text: str) -> None:
    ax.set_title(f"{letter}  {text}", loc="left", fontweight="bold", color=INK, pad=5)


def quantity_axis(ax, label: str, ticks: list[float], labels: list[str] | None = None, lim: tuple[float, float] | None = None) -> None:
    """One convention for every bar panel: categories on the y axis, the quantity on the x axis,
    hairline gridlines at the ticks with a darker line at zero, no spines, no tick marks."""
    ax.set_xlim(*(lim or (ticks[0], ticks[-1])))
    ax.set_xticks(ticks)
    ax.set_xticklabels(labels if labels is not None else [f"{t:g}" for t in ticks], color=MUTED)
    ax.set_xlabel(label, color=MUTED)
    ax.tick_params(axis="both", length=0)
    for sp in ax.spines.values():
        sp.set_visible(False)
    for t in ticks:
        ax.axvline(t, color="#C9CED4" if t == 0 else HAIR, lw=0.6, zorder=1)
    ax.set_axisbelow(True)


def rounded_bar(ax, x: float, width: float, height: float, color: str, r_pt: float = 2.2) -> None:
    """Vertical bar, rounded at the data end and square at the baseline. Call after limits are set."""
    inv = ax.transData.inverted()
    (x0, y0), (x1, y1) = inv.transform((0, 0)), inv.transform((r_pt * ax.figure.dpi / 72, r_pt * ax.figure.dpi / 72))
    rx, ry = min(abs(x1 - x0), width / 2), min(abs(y1 - y0), height)
    l, rgt, top = x - width / 2, x + width / 2, height
    verts = [(l, 0), (l, top - ry), (l, top), (l + rx, top), (rgt - rx, top), (rgt, top), (rgt, top - ry), (rgt, 0), (l, 0)]
    codes = [MPath.MOVETO, MPath.LINETO, MPath.CURVE3, MPath.CURVE3, MPath.LINETO, MPath.CURVE3, MPath.CURVE3,
             MPath.LINETO, MPath.CLOSEPOLY]
    ax.add_patch(PathPatch(MPath(verts, codes), facecolor=color, edgecolor="none", zorder=3))


def save(fig, out: Path, name: str) -> None:
    fig.savefig(out / f"{name}.pdf", bbox_inches="tight", pad_inches=0.02, facecolor=SURFACE)
    plt.close(fig)
    print("wrote", out / f"{name}.pdf")


# ---------------------------------------------------------------- Figure 3
KEYWORD = RISK["medium"]   # the keyword pipeline wears the palette's amber; the LLM pipeline wears ACCENT


def fig_phase1(out: Path) -> None:
    """Two pipelines on the 11 clear flaws: end-to-end rates (a) and a per-flaw dot matrix (b).

    Flat, like Figures 4-6. Drawn on one axes whose data units are points, so marks keep
    their geometry. Blue / amber / red validated with the dataviz palette checker.
    """
    paper = json.loads((ROOT / "examples/papers/clean_supported.json").read_text())
    kw = evaluate_flaws(paper, sorted(load_flaws()), max_steps=1, assessor="keyword")
    llm = json.loads((ROOT / "experiments/phase1_pilot/llm_summary_current.json").read_text())
    misses = json.loads((ROOT / "experiments/ablations/twostage_11flaw_misses.json").read_text())
    kw_caught = {p["flaw_id"]: bool(p["score"]["detected"]) for p in kw["pairs"]}
    llm_caught = {k: bool(v) for k, v in llm["per_flaw_detected"].items()}
    abstained = {m["flaw"] for m in misses["missed_flaws"]
                 if m["traces_in_run_window"] and all(t["risk"] == "unknown" for t in m["traces_in_run_window"])}
    assert abstained == {f for f, c in llm_caught.items() if not c}

    W, H = 333.0, 158.0
    fig = plt.figure(figsize=(W / 72, H / 72))
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis("off")

    def hbar(x0: float, y: float, length: float, h: float, color: str, r: float = 2.2) -> None:
        """Horizontal bar: square at the baseline, rounded at the data end."""
        r = min(r, length, h / 2)
        x1, lo, hi = x0 + length, y - h / 2, y + h / 2
        verts = [(x0, lo), (x1 - r, lo), (x1, lo), (x1, lo + r), (x1, hi - r), (x1, hi), (x1 - r, hi), (x0, hi), (x0, lo)]
        codes = [MPath.MOVETO, MPath.LINETO, MPath.CURVE3, MPath.CURVE3, MPath.LINETO, MPath.CURVE3, MPath.CURVE3,
                 MPath.LINETO, MPath.CLOSEPOLY]
        ax.add_patch(PathPatch(MPath(verts, codes), facecolor=color, edgecolor="none", zorder=3))

    def swatch(x: float, y: float, color: str) -> None:
        ax.add_patch(plt.Rectangle((x, y - 2.6), 5.2, 5.2, facecolor=color, edgecolor="none", zorder=3))

    # ---- a: end-to-end rates -------------------------------------------------
    ax.text(0, H - 8.5, "a  End-to-end rates", fontweight="bold", fontsize=8.2, color=INK, va="baseline")
    lx = 0.5
    for color, lab in ((KEYWORD, "keyword pipeline"), (ACCENT, "LLM pipeline (gpt-4o)")):
        swatch(lx, H - 22.5, color)
        ax.text(lx + 8, H - 22.7, lab, fontsize=7, color=INK, va="center")
        lx += 72
    x0, x1, hb = 58.0, 146.0, 6.2
    rows = [("detection", kw["summary"]["detection_rate"], llm["detection_rate"]),
            ("localization", kw["summary"]["localization_acc"], llm["localization_acc"]),
            ("false alarm", kw["summary"]["false_alarm_rate"], llm["false_alarm_rate"])]
    top_y, bot_y = H - 36, 26.0
    for v in (0, 0.5, 1):
        x = x0 + v * (x1 - x0)
        ax.plot([x, x], [bot_y, top_y], color=HAIR if v else "#C9CED4", lw=0.6, zorder=1)
        ax.text(x, bot_y - 7.5, f"{v:g}", ha="center", va="center", fontsize=7, color=MUTED)
    ax.text((x0 + x1) / 2, 6.5, "rate", ha="center", va="center", fontsize=7.5, color=MUTED)
    for i, (name, k, m) in enumerate(rows):
        yc = top_y - 17 - i * 33
        ax.text(x0 - 8, yc, name, ha="right", va="center", fontsize=7.5, color=INK)
        for y, v, color, bold in ((yc + 4.1, k, KEYWORD, False), (yc - 4.1, m, ACCENT, True)):
            if v > 0:
                hbar(x0, y, v * (x1 - x0), hb, color)
            ax.text(x0 + v * (x1 - x0) + 4.5, y - 0.2, f"{v:.2f}", ha="left", va="center", fontsize=7,
                    color=INK if bold else MUTED, fontweight="bold" if bold else "normal", zorder=4)

    # ---- b: per-flaw dot matrix ---------------------------------------------
    bx = 186.0
    ax.text(bx, H - 8.5, "b  Per-flaw outcome", fontweight="bold", fontsize=8.2, color=INK, va="baseline")

    def mark(kind: str, x: float, y: float) -> None:
        if kind in ("keyword", "llm"):
            ax.scatter([x], [y], s=28, facecolor=KEYWORD if kind == "keyword" else ACCENT, edgecolor="none", zorder=3)
        elif kind == "missed":
            ax.scatter([x], [y], s=18, facecolor=SURFACE, edgecolor=RISK["high"], linewidth=1.0, zorder=3)
        else:
            ax.plot([x - 2.9, x + 2.9], [y, y], color=RISK["unknown"], lw=1.9, solid_capstyle="round", zorder=3)

    lx, ly = bx + 3.5, H - 22.5
    mark("keyword", lx, ly); mark("llm", lx + 7, ly)
    ax.text(lx + 12.5, ly - 0.2, "caught", fontsize=7, color=INK, va="center")
    mark("missed", lx + 48, ly)
    ax.text(lx + 53.5, ly - 0.2, "missed", fontsize=7, color=INK, va="center")
    mark("abstained", lx + 90, ly)
    ax.text(lx + 96, ly - 0.2, "abstained", fontsize=7, color=INK, va="center")

    flaws = sorted(kw_caught, key=lambda f: (_INJECTIONS[f]["op"] != "remove", f))
    n_om = sum(_INJECTIONS[f]["op"] == "remove" for f in flaws)
    label_x, cols, pitch, top = bx + 82, (bx + 97, bx + 120), 9.9, H - 48.0
    for cx, lab in zip(cols, ("keyword", "LLM")):
        ax.text(cx, H - 36.5, lab, ha="center", va="center", fontsize=7, color=MUTED)
    ys = {}
    for j, f in enumerate(flaws):
        y = top - j * pitch - (3.2 if j >= n_om else 0)
        ys[f] = y
        ax.text(label_x, y, f.replace("_", " ").replace(" se", " std. errors").replace("cherrypicked", "cherry-picked"),
                ha="right", va="center", fontsize=7, color=INK)
        mark("keyword" if kw_caught[f] else "missed", cols[0], y)
        mark("llm" if llm_caught[f] else ("abstained" if f in abstained else "missed"), cols[1], y)
    for group, lab in ((flaws[:n_om], "omission"), (flaws[n_om:], "commission")):
        hi, lo = ys[group[0]] + 3.6, ys[group[-1]] - 3.6
        ax.plot([bx + 132.5] * 2, [lo, hi], color="#C3C8CF", lw=0.8, solid_capstyle="round")
        ax.text(bx + 136.5, (lo + hi) / 2, lab, rotation=90, ha="left", va="center", fontsize=7, color=MUTED)
    fig.savefig(out / "figure_phase1.pdf", facecolor=SURFACE)
    plt.close(fig)
    print("wrote", out / "figure_phase1.pdf")


# ---------------------------------------------------------------- Figure 4
def fig_vsgold(out: Path) -> None:
    gold = {(r["paper_id"], r["dimension"]): r["gold_risk"] for r in csv.DictReader(gold_path().open())}
    argus = {(r["paper_id"], r["dimension"]): r["risk"]
             for r in csv.DictReader((ROOT / "experiments/real_papers/corpus_results/did_llm_risks.csv").open())}
    papers = sorted({p for p, _ in gold}, key=lambda s: int(s.split("_")[1]))
    fig, (a, b, c) = plt.subplots(1, 3, figsize=(6.3, 2.55), gridspec_kw={"width_ratios": [1.15, 1.35, 0.95], "wspace": 0.55})

    def outcome(k):
        if k not in gold:  # cell excluded from the gold (dimension not applicable)
            return "excluded"
        if argus[k] == "unknown":
            return "abstained"
        return "exact" if argus[k] == gold[k] else ("over-severe" if RANK[argus[k]] > RANK[gold[k]] else "under-severe")
    col = {"abstained": RISK["unknown"], "exact": EXACT, "over-severe": OVER, "under-severe": "#1F2328", "excluded": SURFACE}
    counts = Counter(outcome(k) for k in gold)
    # dimensions on the y axis in the same order as Figure 5, papers on the x axis
    for j, d in enumerate(DIMS):
        y = len(DIMS) - 1 - j
        for i, p in enumerate(papers):
            o = outcome((p, d))
            a.add_patch(plt.Rectangle((i + 0.08, y + 0.08), 0.84, 0.84, facecolor=col[o],
                                      edgecolor=HAIR if o == "excluded" else "none", linewidth=0.6))
    a.set_xlim(0, len(papers)); a.set_ylim(0, len(DIMS)); a.set_aspect("equal"); a.set_anchor("W")
    a.set_yticks([len(DIMS) - 1 - j + 0.5 for j in range(len(DIMS))]); a.set_yticklabels([DIM_LABEL[d] for d in DIMS], color=INK)
    a.set_xticks([i + 0.5 for i in range(len(papers))]); a.set_xticklabels([str(i + 1) for i in range(len(papers))], color=MUTED)
    a.set_xlabel("paper", color=MUTED); a.tick_params(axis="both", length=0)
    for sp in a.spines.values():
        sp.set_visible(False)
    a.legend(handles=[Patch(facecolor=col[k], label=f"{k} ({counts.get(k, 0)})") for k in ("over-severe", "exact", "abstained")],
             loc="lower left", bbox_to_anchor=(-0.02, 1.01), ncol=2, handlelength=0.8, columnspacing=0.6, handletextpad=0.3,
             borderaxespad=0, fontsize=6.4, labelspacing=0.25)
    a.set_title(f"a  Outcome per cell (n={len(gold)})", loc="left", fontweight="bold", color=INK, pad=24)

    # three rows: the two label distributions, then the per-cell outcome (colours of panel a)
    outcome_cnt = Counter(outcome(k) for k in gold)
    rows_b = [("expert gold", [(lv, Counter(gold[k] for k in gold).get(lv, 0), RISK[lv]) for lv in ("low", "medium", "high", "unknown")]),
              ("ARGUS", [(lv, Counter(argus[k] for k in gold).get(lv, 0), RISK[lv]) for lv in ("low", "medium", "high", "unknown")]),
              ("outcome", [(o, outcome_cnt.get(o, 0), col[o]) for o in ("over-severe", "exact", "under-severe", "abstained")])]
    for y, (lab, segs) in zip((2, 1, 0), rows_b):
        left = 0
        for name, n, colr in segs:
            if not n:
                continue
            b.barh(y, n, left=left, height=0.5, color=colr, edgecolor=SURFACE, linewidth=1.4, zorder=3)
            if n >= 5:
                b.text(left + n / 2, y, str(n), ha="center", va="center", fontsize=6.8,
                       color="#FFFFFF" if colr in (RISK["low"], RISK["high"], OVER, EXACT) else INK, zorder=4)
            left += n
    b.set_yticks([2, 1, 0]); b.set_yticklabels(["expert gold", "ARGUS", "outcome"], color=INK); b.set_ylim(-0.7, 2.7)
    quantity_axis(b, f"cells (of {len(gold)})", [0, 11, 22, 33, 44, 55], lim=(0, 55))
    b.legend(handles=[Patch(facecolor=RISK[k], label=k) for k in ("low", "medium", "high", "unknown")], loc="lower left",
             bbox_to_anchor=(-0.02, 1.01), ncol=2, handlelength=0.8, columnspacing=0.7, handletextpad=0.3, borderaxespad=0,
             fontsize=6.4, labelspacing=0.25)
    b.set_title("b  Risk labels", loc="left", fontweight="bold", color=INK, pad=24)

    rows_, cols_ = ["low", "medium", "high", "unknown"], ["low", "medium", "high"]
    M = [[sum(1 for k in gold if argus[k] == r and gold[k] == cc) for cc in cols_] for r in rows_]
    cmap = LinearSegmentedColormap.from_list("seq", ["#F3F7FD", "#9EC5F4", "#2A78D6", "#184F95"])
    c.imshow(M, cmap=cmap, vmin=0, vmax=max(max(r) for r in M), aspect="auto")
    for i, r in enumerate(M):
        for j, v in enumerate(r):
            c.text(j, i, str(v), ha="center", va="center", fontsize=7.2, color="#FFFFFF" if v >= 9 else INK)
    c.set_xticks(range(3)); c.set_xticklabels(["low", "med.", "high"], color=MUTED); c.set_yticks(range(4)); c.set_yticklabels(rows_, color=INK)
    c.set_xlabel("expert gold", color=MUTED); c.set_ylabel("ARGUS", labelpad=2, color=MUTED)
    c.set_xticks([x - 0.5 for x in range(1, 3)], minor=True); c.set_yticks([y - 0.5 for y in range(1, 4)], minor=True)
    c.grid(which="minor", color=SURFACE, lw=1.6); c.tick_params(which="both", length=0)
    for sp in c.spines.values():
        sp.set_visible(False)
    c.set_title("c  Confusion", loc="left", fontweight="bold", color=INK, pad=24)
    save(fig, out, "figure_vsgold")


# ---------------------------------------------------------------- Figure 5
def fig_realcorpus(out: Path) -> None:
    res = ROOT / "experiments/real_papers/corpus_results"
    fig, axes = plt.subplots(1, 2, figsize=(6.3, 2.55), sharey=True, gridspec_kw={"wspace": 0.08})
    for ax, (fname, title) in zip(axes, (("did_keyword_risks.csv", "keyword pipeline"), ("did_llm_risks.csv", "two-stage LLM pipeline"))):
        rows = [r for r in csv.DictReader((res / fname).open()) if r["paper_id"] != "paper_164"]
        n = len({r["paper_id"] for r in rows})
        for i, d in enumerate(DIMS):
            y = len(DIMS) - 1 - i
            cnt = Counter(r["risk"] for r in rows if r["dimension"] == d)
            left = 0.0
            for lv in ("high", "medium", "low", "unknown"):
                w = cnt.get(lv, 0) / n
                if w:
                    ax.barh(y, w, left=left, height=0.62, color=RISK[lv], edgecolor=SURFACE, linewidth=1.2, zorder=3)
                left += w
        ax.set_ylim(-0.6, len(DIMS) - 0.4)
        quantity_axis(ax, f"share of the {n} papers", [0, 0.5, 1])
        ax.set_title(title, loc="left", fontweight="bold", color=INK, pad=4)
    axes[0].set_yticks(range(len(DIMS))); axes[0].set_yticklabels([DIM_LABEL[d] for d in DIMS][::-1], color=INK)
    fig.legend(handles=[Patch(facecolor=RISK[k], label=k) for k in ("high", "medium", "low", "unknown")], loc="upper center",
               bbox_to_anchor=(0.56, 1.06), ncol=4, handlelength=0.9, columnspacing=1.2, handletextpad=0.4)
    save(fig, out, "figure_realcorpus")


# ---------------------------------------------------------------- Figure 6
def fig_calibration(out: Path) -> None:
    m = json.loads((ROOT / "experiments/ablations/calibration_recheck.json").read_text())["policies"]
    before, dem, ab = m["medium"]["before"], m["medium"]["dominant_rule_only"], m["unknown"]["dominant_rule_only"]
    n_cells = before["answered"] + before["unknown"]
    panels = [("a", "Over-severe", "fewer is better", [x["over_severe"] for x in (before, dem, ab)], "{:.0f}",
               f"cells (of {before['answered']} answered)", [0, before["answered"]]),
              ("b", "Answered", "more is better", [x["answered"] for x in (before, dem, ab)], "{:.0f}", f"cells (of {n_cells})", [0, n_cells]),
              ("c", "Weighted \u03ba", "higher is better", [x["weighted_kappa"] for x in (before, dem, ab)], "{:.2f}", "\u03ba", [0, 0.5])]
    fig, axes = plt.subplots(1, 3, figsize=(3.12, 1.5), sharey=True, gridspec_kw={"wspace": 0.28})
    rows = ["before", "rule 1 \u2192 med", "rule 1 \u2192 unk"]
    for ax, (letter, title, hint, vals, fmt, xlabel, ticks) in zip(axes, panels):
        for i, v in enumerate(vals):
            y = len(vals) - 1 - i
            ax.barh(y, v, height=0.56, color=BASE if i == 0 else ACCENT, zorder=3)
            ax.text(v + ticks[-1] * 0.03, y, fmt.format(v), ha="left", va="center", fontsize=6.6, color=INK,
                    fontweight="bold" if i else "normal", zorder=4)
        ax.set_ylim(-0.6, len(vals) - 0.4)
        quantity_axis(ax, xlabel, ticks, lim=(0, ticks[-1] * 1.32))
        ax.set_title(f"{letter}  {title}", loc="left", fontweight="bold", color=INK, pad=11, fontsize=7.2)
        ax.text(0, 1.04, hint, transform=ax.transAxes, fontsize=6.0, color=MUTED, ha="left", va="bottom")
    axes[0].set_yticks(range(len(rows))); axes[0].set_yticklabels(rows[::-1], color=INK, fontsize=6.6)
    save(fig, out, "calibration_tradeoff")


if __name__ == "__main__":
    arg = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("paper_climatenlp/figures")
    out_dir = arg if arg.is_absolute() else ROOT / arg
    out_dir.mkdir(parents=True, exist_ok=True)
    assert out_dir.resolve() != (ROOT / "paper" / "figures").resolve(), "this script must not write to paper/figures"
    style()
    fig_phase1(out_dir); fig_vsgold(out_dir); fig_realcorpus(out_dir); fig_calibration(out_dir)
