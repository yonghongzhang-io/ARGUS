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
os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "argus_mplconfig"))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from matplotlib.patches import Patch, PathPatch  # noqa: E402
from matplotlib.path import Path as MPath  # noqa: E402

from argus.config import load_flaws  # noqa: E402
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
def fig_phase1(out: Path) -> None:
    paper = json.loads((ROOT / "examples/papers/clean_supported.json").read_text())
    kw = evaluate_flaws(paper, sorted(load_flaws()), max_steps=1, assessor="keyword")
    llm = json.loads((ROOT / "experiments/phase1_pilot/llm_summary_current.json").read_text())
    kw_caught = {p["flaw_id"]: bool(p["score"]["detected"]) for p in kw["pairs"]}
    llm_caught = {k: bool(v) for k, v in llm["per_flaw_detected"].items()}

    fig, (a, b) = plt.subplots(1, 2, figsize=(4.62, 2.12), gridspec_kw={"width_ratios": [1.0, 1.05], "wspace": 0.95})
    rows = [("detection", kw["summary"]["detection_rate"], llm["detection_rate"]),
            ("localization", kw["summary"]["localization_acc"], llm["localization_acc"]),
            ("false alarm", kw["summary"]["false_alarm_rate"], llm["false_alarm_rate"])]
    for i, (name, k, m) in enumerate(rows):
        y = len(rows) - 1 - i
        a.plot([k, m], [y, y], color=HAIR, lw=2.2, solid_capstyle="round", zorder=1)
        a.scatter([k], [y], s=34, facecolor=SURFACE, edgecolor=BASE, linewidth=1.6, zorder=3)
        a.scatter([m], [y], s=40, facecolor=ACCENT, edgecolor=SURFACE, linewidth=1.2, zorder=4)
        if abs(m - k) > 0.05:
            a.text(k - 0.075, y, f"{k:.2f}", ha="right", va="center", color=MUTED, fontsize=7)
            a.text(m + 0.075, y, f"{m:.2f}", ha="left", va="center", color=INK, fontsize=7, fontweight="bold")
        else:
            a.text(m + 0.075, y, f"{m:.2f}", ha="left", va="center", color=INK, fontsize=7)
    a.set_yticks(range(len(rows)))
    a.set_yticklabels([r[0] for r in rows][::-1], color=INK)
    a.set_xlim(-0.30, 1.18); a.set_ylim(-0.6, len(rows) + 0.75)
    a.set_xticks([0, 0.5, 1.0]); a.set_xlabel("rate")
    a.grid(axis="x", color=HAIR, lw=0.6); a.set_axisbelow(True); a.spines["left"].set_visible(False)
    panel_title(a, "a", "End-to-end rates")
    a.legend(handles=[plt.Line2D([], [], marker="o", ls="", mfc=SURFACE, mec=BASE, mew=1.6, ms=5.5, label="keyword pipeline"),
                      plt.Line2D([], [], marker="o", ls="", mfc=ACCENT, mec=SURFACE, ms=6.5, label="LLM pipeline (gpt-4o)")],
             loc="upper left", bbox_to_anchor=(-0.02, 1.02), handletextpad=0.2, borderaxespad=0, labelspacing=0.3)

    flaws = sorted(kw_caught, key=lambda f: (_INJECTIONS[f]["op"] != "remove", f))
    n_om = sum(_INJECTIONS[f]["op"] == "remove" for f in flaws)
    b.set_xlim(-0.6, 2.35); b.set_ylim(-0.6, len(flaws) + 0.55); b.axis("off")
    for j, f in enumerate(flaws):
        y = len(flaws) - 1 - j
        b.text(-0.72, y, f.replace("_", " ").replace(" se", " SE"), ha="right", va="center", fontsize=6.8, color=INK)
        for c, caught in enumerate((kw_caught[f], llm_caught[f])):
            b.add_patch(plt.Rectangle((c - 0.40, y - 0.36), 0.80, 0.72, facecolor=ACCENT if caught else "#ECEEF1",
                                      edgecolor="none", zorder=2, joinstyle="round"))
            if not caught:
                b.text(c, y - 0.02, "×", ha="center", va="center", color="#8C939C", fontsize=7)
    for c, lab in enumerate(("keyword", "LLM")):
        b.text(c, len(flaws) - 0.42, lab, ha="center", va="bottom", fontsize=7, color=MUTED)
    for lo, hi, lab in ((len(flaws) - n_om, len(flaws) - 1, "omission"), (0, len(flaws) - n_om - 1, "commission")):
        b.plot([1.62, 1.62], [lo - 0.36, hi + 0.36], color=MUTED, lw=0.7)
        b.text(1.74, (lo + hi) / 2, lab, rotation=90, ha="left", va="center", fontsize=6.8, color=MUTED)
    b.set_title("b  Per-flaw outcome", loc="left", fontweight="bold", color=INK, pad=5, x=-0.55)
    b.legend(handles=[Patch(facecolor=ACCENT, label="caught"), Patch(facecolor="#ECEEF1", label="missed (×)")],
             loc="upper center", bbox_to_anchor=(0.30, 0.03), ncol=2, handlelength=1.0, columnspacing=1.0)
    save(fig, out, "figure_phase1")


# ---------------------------------------------------------------- Figure 4
def fig_vsgold(out: Path) -> None:
    frozen = ROOT / "experiments/annotation/pilot_frozen"
    gold = {(r["paper_id"], r["dimension"]): r["gold_risk"] for r in csv.DictReader((frozen / "gold_labels.csv").open())}
    argus = {(r["paper_id"], r["dimension"]): r["risk"]
             for r in csv.DictReader((ROOT / "experiments/real_papers/corpus_results/did_llm_risks.csv").open())}
    papers = sorted({p for p, _ in gold}, key=lambda s: int(s.split("_")[1]))
    fig, (a, b, c) = plt.subplots(1, 3, figsize=(6.3, 2.35), gridspec_kw={"width_ratios": [1.95, 1.2, 0.95], "wspace": 0.62})

    def outcome(k):
        if argus[k] == "unknown":
            return "abstained"
        return "exact" if argus[k] == gold[k] else ("over-severe" if RANK[argus[k]] > RANK[gold[k]] else "under-severe")
    col = {"abstained": RISK["unknown"], "exact": EXACT, "over-severe": OVER, "under-severe": "#1F2328"}
    counts = Counter(outcome(k) for k in gold)
    for i, p in enumerate(papers):
        for j, d in enumerate(DIMS):
            a.add_patch(plt.Rectangle((j + 0.07, len(papers) - 1 - i + 0.07), 0.86, 0.86, facecolor=col[outcome((p, d))], edgecolor="none"))
    a.set_xlim(0, len(DIMS)); a.set_ylim(0, len(papers)); a.set_aspect("equal"); a.set_anchor("N")
    a.set_xticks([j + 0.5 for j in range(len(DIMS))]); a.set_xticklabels([DIM_LABEL[d] for d in DIMS], rotation=55, ha="right", fontsize=6.3)
    a.set_yticks([i + 0.5 for i in range(len(papers))]); a.set_yticklabels([f"paper {n}" for n in range(len(papers), 0, -1)], fontsize=6.6)
    for s in a.spines.values():
        s.set_visible(False)
    a.legend(handles=[Patch(facecolor=col[k], label=f"{k} ({counts.get(k, 0)})") for k in ("over-severe", "exact", "abstained")],
             loc="lower left", bbox_to_anchor=(-0.01, 1.02), ncol=3, handlelength=0.8, columnspacing=0.6, handletextpad=0.3,
             borderaxespad=0, fontsize=6.6)
    a.set_title("a  Outcome of each of the 55 cells", loc="left", fontweight="bold", color=INK, pad=22)

    for y, (lab, src) in enumerate((("ARGUS", argus), ("expert gold", gold))):
        left = 0
        cnt = Counter(src[k] for k in gold)
        for lv in ("low", "medium", "high", "unknown"):
            n = cnt.get(lv, 0)
            if not n:
                continue
            b.barh(y, n, left=left, height=0.36, color=RISK[lv], edgecolor=SURFACE, linewidth=1.4, zorder=3)
            if n >= 5:
                b.text(left + n / 2, y, str(n), ha="center", va="center", fontsize=6.8,
                       color="#FFFFFF" if lv in ("low", "high") else INK, zorder=4)
            left += n
    b.set_yticks([0, 1]); b.set_yticklabels(["ARGUS", "expert\ngold"], color=INK); b.set_ylim(-0.55, 1.55)
    b.set_xlim(0, 55); b.set_xticks([0, 20, 40, 55]); b.set_xlabel("cells")
    b.grid(axis="x", color=HAIR, lw=0.6); b.set_axisbelow(True); b.spines["left"].set_visible(False)
    b.legend(handles=[Patch(facecolor=RISK[k], label=k) for k in ("low", "medium", "high", "unknown")], loc="lower left",
             bbox_to_anchor=(-0.02, 1.02), ncol=2, handlelength=0.8, columnspacing=0.7, handletextpad=0.3, borderaxespad=0,
             fontsize=6.6, labelspacing=0.25)
    b.set_title("b  Risk labels", loc="left", fontweight="bold", color=INK, pad=24)

    rows_, cols_ = ["low", "medium", "high", "unknown"], ["low", "medium", "high"]
    M = [[sum(1 for k in gold if argus[k] == r and gold[k] == cc) for cc in cols_] for r in rows_]
    cmap = LinearSegmentedColormap.from_list("seq", ["#F3F7FD", "#9EC5F4", "#2A78D6", "#184F95"])
    c.imshow(M, cmap=cmap, vmin=0, vmax=max(max(r) for r in M), aspect="auto")
    for i, r in enumerate(M):
        for j, v in enumerate(r):
            c.text(j, i, str(v), ha="center", va="center", fontsize=7.2, color="#FFFFFF" if v >= 9 else INK)
    c.set_xticks(range(3)); c.set_xticklabels(["low", "med.", "high"]); c.set_yticks(range(4)); c.set_yticklabels(rows_)
    c.set_xlabel("expert gold"); c.set_ylabel("ARGUS", labelpad=2)
    c.set_xticks([x - 0.5 for x in range(1, 3)], minor=True); c.set_yticks([y - 0.5 for y in range(1, 4)], minor=True)
    c.grid(which="minor", color=SURFACE, lw=1.6); c.tick_params(which="minor", length=0)
    for s in c.spines.values():
        s.set_visible(False)
    c.set_title("c  Confusion", loc="left", fontweight="bold", color=INK, pad=22)
    save(fig, out, "figure_vsgold")


# ---------------------------------------------------------------- Figure 5
def fig_realcorpus(out: Path) -> None:
    res = ROOT / "experiments/real_papers/corpus_results"
    fig, axes = plt.subplots(1, 2, figsize=(6.3, 2.55), sharey=True, gridspec_kw={"wspace": 0.06})
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
        ax.set_xlim(0, 1); ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0]); ax.set_xticklabels(["0", "", "0.5", "", "1"])
        ax.set_xlabel("share of the 26 papers"); ax.set_ylim(-0.6, len(DIMS) - 0.4)
        ax.spines["left"].set_visible(False); ax.spines["bottom"].set_visible(False)
        ax.set_title(title, loc="left", fontweight="bold", color=INK, pad=4)
    axes[0].set_yticks(range(len(DIMS))); axes[0].set_yticklabels([DIM_LABEL[d] for d in DIMS][::-1], color=INK)
    fig.legend(handles=[Patch(facecolor=RISK[k], label=k) for k in ("high", "medium", "low", "unknown")], loc="upper center",
               bbox_to_anchor=(0.56, 1.06), ncol=4, handlelength=0.9, columnspacing=1.2, handletextpad=0.4)
    save(fig, out, "figure_realcorpus")


# ---------------------------------------------------------------- Figure 6
def fig_calibration(out: Path) -> None:
    m = json.loads((ROOT / "experiments/ablations/calibration_recheck.json").read_text())["policies"]
    before, dem, ab = m["medium"]["before"], m["medium"]["dominant_rule_only"], m["unknown"]["dominant_rule_only"]
    panels = [("a", "Over-severe", "fewer is better", [x["over_severe"] for x in (before, dem, ab)], "{:.0f}"),
              ("b", "Answered", "more is better", [x["answered"] for x in (before, dem, ab)], "{:.0f}"),
              ("c", "Weighted \u03ba", "higher is better", [x["weighted_kappa"] for x in (before, dem, ab)], "{:.2f}")]
    fig, axes = plt.subplots(1, 3, figsize=(3.12, 1.62), gridspec_kw={"wspace": 0.2})
    for ax, (letter, title, hint, vals, fmt) in zip(axes, panels):
        top = max(vals) * 1.30
        ax.set_xlim(-0.5, 2.5); ax.set_ylim(0, top)
        fig.canvas.draw()
        for i, v in enumerate(vals):
            rounded_bar(ax, i, 0.56, v, BASE if i == 0 else ACCENT)
            ax.text(i, v + top * 0.035, fmt.format(v), ha="center", va="bottom", fontsize=6.8, color=INK,
                    fontweight="bold" if i else "normal")
        ax.set_xticks(range(3)); ax.set_xticklabels(["before", "med", "unk"], fontsize=6.0, color=INK)
        ax.set_yticks([]); ax.spines["left"].set_visible(False); ax.spines["bottom"].set_color(HAIR)
        ax.set_title(f"{letter}  {title}", loc="left", fontweight="bold", color=INK, pad=11, fontsize=7.2)
        ax.text(0, 1.035, hint, transform=ax.transAxes, fontsize=6.0, color=MUTED, ha="left", va="bottom")
    save(fig, out, "calibration_tradeoff")


if __name__ == "__main__":
    arg = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("paper_climatenlp/figures")
    out_dir = arg if arg.is_absolute() else ROOT / arg
    out_dir.mkdir(parents=True, exist_ok=True)
    assert out_dir.resolve() != (ROOT / "paper" / "figures").resolve(), "this script must not write to paper/figures"
    style()
    fig_phase1(out_dir); fig_vsgold(out_dir); fig_realcorpus(out_dir); fig_calibration(out_dir)
