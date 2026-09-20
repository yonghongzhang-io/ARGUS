"""README banner: title plus ARGUS's own risk map of the real-paper corpus.

The matrix is real output, not decoration: 26 published DID papers (columns) by the
11 identification dimensions (rows), coloured by the two-stage pipeline's risk
(experiments/real_papers/corpus_results/did_llm_risks.csv, duplicate paper_164 excluded
as in the paper). No third-party artwork is used.

    python3 docs/make_banner.py        # writes docs/banner-{light,dark}.svg
    rsvg-convert -w 2560 docs/banner-light.svg -o docs/banner-light.png   (same for dark)
"""
from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "experiments" / "real_papers" / "corpus_results" / "did_llm_risks.csv"
EXCLUDE = {"paper_164"}
DIMS = ["parallel_trends", "no_anticipation", "treatment_timing", "treatment_definition_sutva",
        "control_group", "specification", "inference", "sample_period", "concurrent_policies",
        "robustness_placebo", "data_measurement"]
# Validated for colour-vision deficiency per surface (same hues, separate steps for dark):
# light dE 11.2 protan / 19.5 normal; dark dE 7.9 deutan / 15.9 normal, backed by the labelled legend.
RISK_BY_THEME = {"light": {"low": "#1E9E7A", "medium": "#E09A1F", "high": "#CB4B3C", "unknown": "#B4B9C0"},
                 "dark": {"low": "#1E9E7A", "medium": "#AE8B0E", "high": "#D2404A", "unknown": "#8B949E"}}
THEMES = {
    "light": {"bg": "#F6F8FA", "frame": "#D9DEE5", "ink": "#1F2328", "muted": "#59636E",
              "accent": "#3E6598", "unknown_opacity": "0.55"},
    "dark": {"bg": "#0D1117", "frame": "#30363D", "ink": "#F0F6FC", "muted": "#9198A1",
             "accent": "#7FA7DB", "unknown_opacity": "0.45"},
}
W, H = 1280, 320
CELL, GAP = 15, 4
FONT = "'Helvetica Neue', Helvetica, Arial, sans-serif"


def load() -> tuple[list[str], dict[tuple[str, str], str]]:
    rows = [r for r in csv.DictReader(CSV.open(encoding="utf-8")) if r["paper_id"] not in EXCLUDE]
    papers = sorted({r["paper_id"] for r in rows}, key=lambda p: int(p.split("_")[1]))
    return papers, {(r["paper_id"], r["dimension"]): r["risk"] for r in rows}


def render(theme: str) -> str:
    t = THEMES[theme]
    RISK = RISK_BY_THEME[theme]
    papers, risk = load()
    grid_w = len(papers) * (CELL + GAP) - GAP
    grid_h = len(DIMS) * (CELL + GAP) - GAP
    gx, gy = W - 72 - grid_w, (H - grid_h) // 2 + 6
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
           f'role="img" aria-label="ARGUS: evidence-grounded auditing of identification assumptions">',
           f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="18" fill="{t["bg"]}" stroke="{t["frame"]}" stroke-width="2"/>',
           f'<rect x="64" y="70" width="6" height="180" rx="3" fill="{t["accent"]}"/>',
           f'<text x="94" y="136" font-family="{FONT}" font-size="76" font-weight="700" letter-spacing="2" fill="{t["ink"]}">ARGUS</text>',
           f'<text x="96" y="178" font-family="{FONT}" font-size="23" fill="{t["ink"]}">Evidence-grounded auditing of identification</text>',
           f'<text x="96" y="208" font-family="{FONT}" font-size="23" fill="{t["ink"]}">assumptions in difference-in-differences studies</text>',
           f'<text x="96" y="246" font-family="{FONT}" font-size="16" letter-spacing="1.2" fill="{t["muted"]}">'
           f'FLAG, NOT JUDGE  ·  CLIMATENLP WORKSHOP @ EMNLP 2026</text>']
    for j, dim in enumerate(DIMS):
        for i, paper in enumerate(papers):
            level = risk.get((paper, dim), "unknown")
            opacity = f' fill-opacity="{t["unknown_opacity"]}"' if level == "unknown" else ""
            out.append(f'<rect x="{gx + i * (CELL + GAP)}" y="{gy + j * (CELL + GAP)}" width="{CELL}" '
                       f'height="{CELL}" rx="3.5" fill="{RISK[level]}"{opacity}/>')
    out.append(f'<text x="{gx}" y="{gy - 14}" font-family="{FONT}" font-size="13.5" fill="{t["muted"]}">'
               f'ARGUS risk map: 26 published papers × 11 identification dimensions</text>')
    ly = gy + grid_h + 26
    lx = gx + grid_w
    for level in ("unknown", "high", "medium", "low"):
        label_w = {"low": 26, "medium": 52, "high": 30, "unknown": 58}[level]
        lx -= label_w
        out.append(f'<text x="{lx}" y="{ly}" font-family="{FONT}" font-size="13.5" fill="{t["muted"]}">{level}</text>')
        lx -= 16
        opacity = f' fill-opacity="{t["unknown_opacity"]}"' if level == "unknown" else ""
        out.append(f'<rect x="{lx}" y="{ly - 10.5}" width="11" height="11" rx="2.5" fill="{RISK[level]}"{opacity}/>')
        lx -= 14
    out.append("</svg>")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    for name in THEMES:
        path = ROOT / "docs" / f"banner-{name}.svg"
        path.write_text(render(name), encoding="utf-8")
        print("wrote", path.relative_to(ROOT))
