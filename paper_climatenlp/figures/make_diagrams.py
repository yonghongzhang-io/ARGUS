"""Figures 1 and 2 (overview and architecture), laid out at print size.

The canvas is the printed size in points (455 pt = \\textwidth), so a font size written here is
the font size on the page: labels are 6-8 pt, in line with the result figures. Explanations that
the captions already give are not repeated inside the boxes.

    python3 paper_climatenlp/figures/make_diagrams.py            # writes figure{1,2}.svg + .pdf

Icons are read from the earlier drawings (paper/figures/figure{1,2}.svg); they are Flaticon
artwork used with attribution (see LICENSE-DATA.md) and are not stored as separate files.
PDF export uses Inkscape (text stays text).
"""
from __future__ import annotations

import base64
import hashlib
import io
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
INKSCAPE = "/Applications/Inkscape.app/Contents/MacOS/inkscape"
FONT = "'Helvetica Neue', Helvetica, Arial, sans-serif"
TTC = "/System/Library/Fonts/HelveticaNeue.ttc"
INK, MUTED, FAINT = "#1e2a3a", "#5a6472", "#8a9099"
BLUE, BLUE_FILL, BLUE_EDGE = "#2e6ad4", "#eef4fd", "#5c8ad8"
GREEN, GREEN_FILL, GREEN_EDGE = "#2f8a4c", "#e4f3e7", "#9fd9b3"
ORANGE, ORANGE_FILL, ORANGE_EDGE = "#d9741a", "#fdf6ee", "#e8943c"
PURPLE, RED, RED_FILL, RED_EDGE = "#6b3fb5", "#c2402c", "#fbe9e9", "#eab6b6"
CARD, CARD_EDGE, ARROW = "#f6f7f8", "#dfe3e8", "#4a4f57"
RISKS = ["#7fc08a", "#f2cb5c", "#de7b3e", "#ce4f36", "#a8a8a8"]
ICON = {"pdf": "4335db4b", "chart": "79036a90", "rubric": "76afb3a9", "retrieve": "127c363f", "brain": "edfea3c7",
        "report": "3374a9c3", "shield": "4bc80225", "experts": "3a09610a", "scales": "f80c62c3", "anchor": "d964cb97",
        "pie": "07a5f128", "docsearch": "0661cf09", "syringe": "3742b188"}


def load_icons() -> dict[str, str]:
    found: dict[str, str] = {}
    for name in ("figure1.svg", "figure2.svg"):
        svg = (ROOT / "paper" / "figures" / name).read_text(encoding="utf-8")
        for m in re.finditer(r'xlink:href="data:image/\w+;base64,([^"]*)"', svg, re.S):
            b64 = re.sub(r"\s+|&#10;|&#13;", "", m.group(1))
            raw = base64.b64decode(b64 + "=" * (-len(b64) % 4))
            key = hashlib.md5(raw).hexdigest()[:8]
            if key in found:
                continue
            im = Image.open(io.BytesIO(raw)).convert("RGBA")
            im.thumbnail((224, 224), Image.LANCZOS)
            buf = io.BytesIO()
            im.save(buf, "PNG", optimize=True)
            found[key] = base64.b64encode(buf.getvalue()).decode()
    return {k: found[v] for k, v in ICON.items()}


_fonts: dict[tuple[int, float], ImageFont.FreeTypeFont] = {}


def width(text: str, size: float, bold: bool = False, italic: bool = False) -> float:
    idx = {(False, False): 0, (True, False): 1, (False, True): 2, (True, True): 3}[(bold, italic)]
    font = _fonts.setdefault((idx, 100), ImageFont.truetype(TTC, 100, index=idx))
    return font.getlength(text) * size / 100


class Svg:
    def __init__(self, w: float, h: float, icons: dict[str, str]):
        self.w, self.h, self.icons, self.out = w, h, icons, []
        self.problems: list[str] = []

    def rect(self, x, y, w, h, r=0, fill="none", stroke="none", sw=0.6, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.out.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" rx="{r}" fill="{fill}" '
                        f'stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def header(self, x, y, w, h, r, fill):
        """Header band: rounded on top, square below."""
        self.out.append(f'<path d="M{x:.2f},{y + h:.2f} V{y + r:.2f} Q{x:.2f},{y:.2f} {x + r:.2f},{y:.2f} H{x + w - r:.2f} '
                        f'Q{x + w:.2f},{y:.2f} {x + w:.2f},{y + r:.2f} V{y + h:.2f} Z" fill="{fill}"/>')

    def text(self, x, y, s, size, fill=INK, bold=False, italic=False, anchor="start", fit=None):
        if fit is not None and width(s, size, bold, italic) > fit:
            self.problems.append(f"{s!r} is {width(s, size, bold, italic):.1f} pt wide, room {fit:.1f}")
        esc = s.replace("&", "&amp;").replace("<", "&lt;")
        style = (' font-weight="700"' if bold else "") + (' font-style="italic"' if italic else "")
        self.out.append(f'<text x="{x:.2f}" y="{y:.2f}" font-size="{size}" fill="{fill}" text-anchor="{anchor}"{style}>{esc}</text>')

    def icon(self, name, cx, cy, size):
        self.out.append(f'<image x="{cx - size / 2:.2f}" y="{cy - size / 2:.2f}" width="{size}" height="{size}" '
                        f'xlink:href="data:image/png;base64,{self.icons[name]}"/>')

    def line(self, pts, stroke=ARROW, sw=0.9, dash=None, head=None):
        d = "M" + " L".join(f"{x:.2f},{y:.2f}" for x, y in pts)
        da = f' stroke-dasharray="{dash}"' if dash else ""
        self.out.append(f'<path d="{d}" fill="none" stroke="{stroke}" stroke-width="{sw}" stroke-linejoin="round"{da}/>')
        if head:
            (x0, y0), (x1, y1) = pts[-2], pts[-1]
            n = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
            ux, uy = (x1 - x0) / n, (y1 - y0) / n
            bx, by = x1 - ux * head, y1 - uy * head
            px, py = -uy * head * 0.55, ux * head * 0.55
            self.out.append(f'<path d="M{x1 + ux * head * 0.35:.2f},{y1 + uy * head * 0.35:.2f} L{bx + px:.2f},{by + py:.2f} '
                            f'L{bx - px:.2f},{by - py:.2f} Z" fill="{stroke}"/>')

    def block_arrow(self, x0, x1, y, stroke=ARROW):
        self.out.append(f'<path d="M{x0:.2f},{y - 1.6:.2f} H{x1 - 5:.2f} V{y - 4.2:.2f} L{x1:.2f},{y:.2f} L{x1 - 5:.2f},{y + 4.2:.2f} '
                        f'V{y + 1.6:.2f} H{x0:.2f} Z" fill="{stroke}"/>')

    def save(self, path: Path) -> None:
        if self.problems:
            raise SystemExit("text does not fit:\n  " + "\n  ".join(self.problems))
        path.write_text(
            f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{self.w}pt" '
            f'height="{self.h}pt" viewBox="0 0 {self.w} {self.h}" font-family="{FONT}">\n'
            f'<rect width="{self.w}" height="{self.h}" fill="#ffffff"/>\n' + "\n".join(self.out) + "\n</svg>\n", encoding="utf-8")


# ------------------------------------------------------------------------------ Figure 1
def figure1(icons: dict[str, str]) -> Svg:
    W, H = 455.0, 157.0
    g = Svg(W, H, icons)

    # Step 1
    x, w = 1.0, 100.0
    g.rect(x, 1, w, 121, 6, "#ffffff", BLUE_EDGE, 0.7, "2.4,2")
    g.header(x + 0.4, 1.4, w - 0.8, 16, 5.6, BLUE_FILL)
    g.text(x + w / 2, 12.6, "Step 1: Paper & rubric", 8, BLUE, bold=True, anchor="middle", fit=w - 6)
    g.icon("pdf", x + 34, 35, 21); g.icon("chart", x + 66, 35.5, 22)
    g.text(x + w / 2, 56.5, "Empirical DID paper", 7, INK, bold=True, anchor="middle", fit=w - 6)
    g.line([(x + w / 2, 60.5), (x + w / 2, 68.5)], FAINT, 0.8, "2,1.6", head=3.6)
    g.rect(x + 6, 72, w - 12, 46, 4, "#ffffff", "#c7daf1", 0.6)
    g.icon("rubric", x + 22, 87, 22)
    for i, s in enumerate(("11 identification", "dimensions")):
        g.text(x + 36, 84.5 + i * 8.2, s, 7, INK, bold=True, fit=w - 44)
    cx = x + 12
    for lab, cw in (("d1", 17), ("d2", 17), ("…", 13), ("d11", 21)):
        g.rect(cx, 102, cw, 11.5, 2.6, "#dce8f8" if lab != "…" else "#edf2fa", "#9fbee8", 0.5)
        if lab == "…":
            g.text(cx + cw / 2, 109.6, lab, 6.5, "#7c93b5", anchor="middle")
        else:
            g.out.append(f'<text x="{cx + cw / 2:.2f}" y="110.3" font-size="6.6" fill="#2a4f8f" text-anchor="middle" '
                         f'font-style="italic">d<tspan font-size="4.8" dy="1.4">{lab[1:]}</tspan></text>')
        cx += cw + 3.2

    # Flag, not judge
    g.rect(x, 127, w, 29, 6, "#f8f8f8", "#d9dce1", 0.6)
    g.icon("shield", x + 15, 141.5, 17)
    g.text(x + 28, 137.2, "Flag, not judge", 7, INK, bold=True, fit=w - 31)
    g.text(x + 28, 145.2, "Audits evidence support,", 6, MUTED, fit=w - 30)
    g.text(x + 28, 152.2, "not causal truth.", 6, MUTED, fit=w - 30)

    # Step 2
    sx, sw_ = 115.0, 204.0
    g.block_arrow(x + w + 2.5, sx - 2.5, 62)
    g.rect(sx, 1, sw_, 155, 6, "#ffffff", GREEN_EDGE, 0.8)
    g.header(sx + 0.4, 1.4, sw_ - 0.8, 16, 5.6, GREEN_FILL)
    g.text(sx + sw_ / 2, 12.6, "Step 2: ARGUS audit", 8, GREEN, bold=True, anchor="middle")
    cw, gap, top, ch = 58.0, 10.0, 22.5, 88.0
    cards = [("Extract", "evidence", GREEN, GREEN_FILL, "retrieve", ["queries", "spans", "relevance gate"], "llm"),
             ("Assess", "evidence", GREEN, GREEN_FILL, "brain", ["reported?", "adequate?", "residual risk?", "uncertainty?"], "llm"),
             ("Localize", "risk", BLUE, BLUE_FILL, None, ["risk per", "dimension", "highest-risk", "dimensions"], "det")]
    x0 = sx + (sw_ - 3 * cw - 2 * gap) / 2
    centers = []
    for i, (t1, t2, col, band, icon, bullets, kind) in enumerate(cards):
        cx0 = x0 + i * (cw + gap)
        centers.append(cx0 + cw / 2)
        g.rect(cx0, top, cw, ch, 3.5, "#ffffff", GREEN_EDGE if kind == "llm" else BLUE_EDGE, 0.7,
               None if kind == "llm" else "2.4,2")
        g.header(cx0 + 0.3, top + 0.3, cw - 0.6, 19, 3.2, band)
        g.text(cx0 + cw / 2, top + 8.2, t1, 7, col, bold=True, anchor="middle")
        g.text(cx0 + cw / 2, top + 16, t2, 7, col, bold=True, anchor="middle")
        if icon:
            g.icon(icon, cx0 + cw / 2, top + 33.5, 20)
        else:
            for r in range(3):
                for c, (dx, colr) in enumerate(((0, RISKS[0]), (6.4, RISKS[1]), (15, [RISKS[2], "#e89a5a", RISKS[3]][r]),
                                                (21.4, [RISKS[3], RISKS[4], RISKS[4]][r]))):
                    g.rect(cx0 + cw / 2 - 13.2 + dx, top + 24.2 + r * 6.4, 5, 5, 0.9, colr)
        by = top + 53.5
        for j, b in enumerate(bullets):
            cont = i == 2 and j in (1, 3)
            if not cont:
                g.out.append(f'<circle cx="{cx0 + 6.2:.2f}" cy="{by + j * 8.1 - 2.1:.2f}" r="0.95" fill="{MUTED}"/>')
            g.text(cx0 + 10, by + j * 8.1, b, 6.4, "#27313f", fit=cw - 12)
        if i:
            g.line([(cx0 - gap + 2.4, top + 40), (cx0 - 3.6, top + 40)], ARROW, 1.6, head=4.2)
    ry, rh = 122.0, 29.0
    g.line([(centers[1], top + ch + 1.8), (centers[1], ry - 3.6)], ARROW, 1.8, head=4.4)
    g.rect(sx + 7, ry, sw_ - 14, rh, 5, BLUE_FILL, BLUE_EDGE, 0.7, "2.4,2")
    g.icon("report", sx + 28, ry + rh / 2, 22)
    g.text(sx + 48, ry + 12.6, "Audit report", 8, INK, bold=True)
    g.text(sx + 48, ry + 22, "risk map · evidence · rationale", 6.4, MUTED, fit=112)
    for k, (bh, colr) in enumerate(zip((6.5, 10, 13.5, 17.5, 8.5), RISKS)):
        g.rect(sx + sw_ - 42 + k * 6.2, ry + rh - 5 - bh, 4.8, bh, 0.7, colr)

    # Step 3
    tx, tw = 354.0, 100.0
    g.rect(tx, 1, tw, 133, 6, "#ffffff", ORANGE_EDGE, 0.8)
    g.header(tx + 0.4, 1.4, tw - 0.8, 24, 5.6, ORANGE_FILL)
    g.text(tx + tw / 2, 11.2, "Step 3: Human calibration", 7.6, ORANGE, bold=True, anchor="middle", fit=tw - 4)
    g.text(tx + tw / 2, 20.6, "& evaluation", 7.6, ORANGE, bold=True, anchor="middle")
    for k, (icon, a, b) in enumerate((("experts", "Expert", "annotation"), ("scales", "Adjudicated", "gold labels"),
                                      ("anchor", "Severity", "anchors"), ("pie", "ARGUS-vs-gold", "evaluation"))):
        cy = 41 + k * 26.2
        g.icon(icon, tx + 19, cy, 20)
        g.text(tx + 35, cy - 1.2, a, 7, INK, bold=True, fit=tw - 37)
        g.text(tx + 35, cy + 6.9, b, 7, INK, bold=True, fit=tw - 37)
    # calibrates severity: Step 3 -> Localize card
    lx1 = x0 + 3 * cw + 2 * gap
    g.line([(tx, 62), (tx - 12, 62), (tx - 12, 74), (lx1 + 3.6, 74)], FAINT, 0.9, "2.4,1.8", head=4)
    g.text((sx + sw_ + tx) / 2, 47.5, "calibrates", 6.2, ORANGE, bold=True, anchor="middle", fit=tx - sx - sw_ - 1)
    g.text((sx + sw_ + tx) / 2, 54.7, "severity", 6.2, ORANGE, bold=True, anchor="middle")
    # expert review: Step 3 -> report
    g.line([(tx + tw / 2, 134), (tx + tw / 2, ry + rh / 2), (sx + sw_ - 7 + 3.8, ry + rh / 2)], FAINT, 0.9, "2.4,1.8", head=4)
    g.text(tx + tw / 2 - 5, ry + rh / 2 + 9.5, "expert review", 6.2, FAINT, italic=True, anchor="end")
    return g


# ------------------------------------------------------------------------------ Figure 2
def figure2(icons: dict[str, str]) -> Svg:
    W, H = 455.0, 192.0
    g = Svg(W, H, icons)

    def doc(cx, cy, color, mark):
        g.out.append(f'<path d="M{cx - 5.5:.2f},{cy - 7:.2f} h7 l4,4 v10 h-11 Z" fill="#ffffff" stroke="{color}" stroke-width="0.9" '
                     f'stroke-linejoin="round"/>')
        g.line([(cx - 3, cy - 2.4), (cx + 2.6, cy - 2.4)], color, 0.7)
        g.line([(cx - 3, cy + 0.4), (cx + 2.6, cy + 0.4)], color, 0.7)
        g.out.append(f'<circle cx="{cx + 4.6:.2f}" cy="{cy + 5.4:.2f}" r="3.4" fill="{color}"/>')
        if mark == "check":
            g.line([(cx + 2.9, cy + 5.5), (cx + 4.2, cy + 6.9), (cx + 6.4, cy + 4.1)], "#ffffff", 0.9)
        else:
            g.line([(cx + 4.6, cy + 3.4), (cx + 4.6, cy + 5.9)], "#ffffff", 1.0)
            g.out.append(f'<circle cx="{cx + 4.6:.2f}" cy="{cy + 7.3:.2f}" r="0.55" fill="#ffffff"/>')

    # ---- A
    g.rect(0.6, 0.6, W - 1.2, 103.4, 5, "#fcfdfe", "#e2e5ea", 0.6)
    g.text(7, 12, "A.", 8.6, INK, bold=True)
    g.text(19.5, 12, "Bounded ARGUS audit pipeline", 8, INK, bold=True)
    g.text(19.5 + width("Bounded ARGUS audit pipeline", 8, True) + 4, 12, "(per paper)", 7, FAINT)
    bw, gap, top, bh = 64.5, 10.9, 19.0, 53.0
    x0 = (W - 6 * bw - 5 * gap) / 2
    stages = [("Decomposition", "pdf", BLUE, "det", ["Map paper to", "11 dimensions"]),
              ("Extraction", "docsearch", GREEN, "llm", ["Gather evidence", "per dimension"]),
              ("Assessment", "brain", GREEN, "llm", ["Judge evidence", "adequacy"]),
              ("Localization", None, BLUE, "det", ["Rank dimensions", "by risk"]),
              ("Report", "report", BLUE, "det", ["Risk map, spans,", "rationale"]),
              ("Expert review", "experts", ORANGE, "human", ["Expert reviews", "& adjudicates"])]
    style = {"det": (BLUE_FILL, BLUE_EDGE, "2.4,2"), "llm": (GREEN_FILL, GREEN_EDGE, None), "human": (ORANGE_FILL, ORANGE_EDGE, None)}
    for i, (name, icon, col, kind, lines) in enumerate(stages):
        bx = x0 + i * (bw + gap)
        fill, edge, dash = style[kind]
        g.rect(bx, top, bw, bh, 5, fill, edge, 0.7, dash)
        tw_ = width(name, 6.5, True)
        start = bx + (bw - (9.4 + tw_)) / 2
        g.out.append(f'<circle cx="{start + 3.6:.2f}" cy="{top + 9:.2f}" r="3.7" fill="{col}"/>')
        g.text(start + 3.6, top + 11.2, str(i + 1), 6, "#ffffff", bold=True, anchor="middle")
        g.text(start + 9.4, top + 11.4, name, 6.5, col, bold=True, fit=bw - 14)
        if icon:
            g.icon(icon, bx + bw / 2, top + 25.5, 17)
        else:
            for r in range(2):
                for c in range(3):
                    g.rect(bx + bw / 2 - 8.6 + c * 6, top + 20 + r * 6, 4.8, 4.8, 0.9, [[RISKS[0], RISKS[1], RISKS[2]], ["#e89a5a", RISKS[3], RISKS[4]]][r][c])
        for j, s in enumerate(lines):
            g.text(bx + bw / 2, top + 41.6 + j * 7.4, s, 6.2, "#27313f", anchor="middle", fit=bw - 3)
        if i < 5:
            g.line([(bx + bw + 1.8, top + bh / 2), (bx + bw + gap - 3.6, top + bh / 2)], ARROW, 1.5, head=4)
    # bounded model calls
    mx0, mx1 = x0 + bw + gap, x0 + 3 * bw + 2 * gap
    my = top + bh + 5.5
    g.line([((mx0 + mx1) / 2 - (bw + gap) / 2, top + bh), ((mx0 + mx1) / 2 - (bw + gap) / 2, my)], GREEN_EDGE, 0.8, "2,1.6")
    g.line([((mx0 + mx1) / 2 + (bw + gap) / 2, top + bh), ((mx0 + mx1) / 2 + (bw + gap) / 2, my)], GREEN_EDGE, 0.8, "2,1.6")
    g.rect(mx0 - 8, my, mx1 - mx0 + 16, 23, 4, GREEN_FILL, GREEN_EDGE, 0.6, "2.4,2")
    g.text((mx0 + mx1) / 2, my + 9.4, "Bounded model calls (per dimension)", 6.8, GREEN, bold=True, anchor="middle")
    g.text((mx0 + mx1) / 2, my + 18.4, "lexical retrieval · relevance gate · adequacy judge", 6.2, "#3f4650", anchor="middle",
           fit=mx1 - mx0 + 12)
    # legend, right of the model-call box
    lx, ly = mx1 + 22, my + 5
    for k, (lab, kind) in enumerate((("Deterministic", "det"), ("Model calls (bounded)", "llm"), ("Human / expert", "human"))):
        fill, edge, dash = style[kind]
        yy = ly + k * 8.2
        g.rect(lx, yy - 4.6, 9, 6, 1.4, fill, edge, 0.6, "1.6,1.2" if dash else None)
        g.text(lx + 12.5, yy + 0.6, lab, 6.2, "#3a3f45")
    g.line([(lx + 92, ly - 1.6), (lx + 106, ly - 1.6)], ARROW, 1.3, head=3.6)
    g.text(lx + 112, ly + 0.6, "Data / control flow", 6.2, "#3a3f45")
    g.line([(lx + 92, ly + 6.6), (lx + 108, ly + 6.6)], GREEN_EDGE, 0.9, "2,1.6")
    g.text(lx + 112, ly + 8.8, "Model-call scope", 6.2, "#3a3f45")
    g.rect(lx + 92, ly + 16.4 - 4.6, 9, 6, 1.4, RED_FILL, RED_EDGE, 0.6)
    g.text(lx + 104.5, ly + 17.0, "Injected / perturbed", 6.2, "#3a3f45")

    # ---- B
    by0 = 108.0
    g.rect(0.6, by0, W - 1.2, H - by0 - 0.6, 5, "#fcfdfe", "#e2e5ea", 0.6)
    g.text(7, by0 + 11.6, "B.", 8.6, INK, bold=True)
    g.text(19.5, by0 + 11.6, "Flaw-injection evaluation loop", 8, INK, bold=True)
    mid = by0 + 49.5
    # credible paper
    g.rect(7, mid - 15, 66, 30, 5, BLUE_FILL, BLUE_EDGE, 0.7, "2.4,2")
    g.icon("pdf", 20.5, mid, 17)
    g.text(32, mid - 1.2, "Synthetic", 6.8, INK, bold=True)
    g.text(32, mid + 6.8, "DID study", 6.8, INK, bold=True, fit=39)
    g.line([(74.8, mid), (84.4, mid)], ARROW, 1.5, head=4)
    # inject flaw
    ix, iw = 88.0, 96.0
    g.rect(ix, mid - 21, iw, 42, 5, BLUE_FILL, BLUE_EDGE, 0.7, "2.4,2")
    g.icon("syringe", ix + 15, mid + 1, 19)
    g.text(ix + 28, mid - 8.6, "Inject flaw", 7, INK, bold=True)
    for j, s in enumerate(("One known flaw on", "a target dimension")):
        g.text(ix + 28, mid + 0.4 + j * 7.6, s, 6.2, "#27313f", fit=iw - 30)
    # split
    vx, vw, up, dn = 204.0, 78.0, mid - 17, mid + 17
    g.line([(ix + iw + 1.5, mid), (ix + iw + 9, mid)], ARROW, 1.5)
    g.line([(ix + iw + 9, up), (ix + iw + 9, dn)], ARROW, 1.5)
    for yy, lab, col, fill, edge, markk in ((up, "Clean version", "#2f8a4c", BLUE_FILL, BLUE_EDGE, "check"),
                                            (dn, "Injected version", RED, RED_FILL, RED_EDGE, "bang")):
        g.line([(ix + iw + 9, yy), (vx - 3.6, yy)], ARROW, 1.5, head=4)
        g.rect(vx, yy - 12, vw, 24, 4.5, fill, edge, 0.7, "2.4,2" if markk == "check" else None)
        doc(vx + 12, yy - 1.5, col, markk)
        g.text(vx + 23, yy + 2.4, lab, 6.8, INK, bold=True, fit=vw - 25)
        ax_, aw = vx + vw + 13, 74.0
        g.line([(vx + vw + 1.8, yy), (ax_ - 3.6, yy)], ARROW, 1.5, head=4)
        g.rect(ax_, yy - 12, aw, 24, 4.5, GREEN_FILL, GREEN_EDGE, 0.7)
        g.icon("brain", ax_ + 13, yy, 15)
        g.text(ax_ + 24, yy - 0.6, "ARGUS audit", 6.8, GREEN, bold=True, fit=aw - 28)
        g.text(ax_ + 24, yy + 6.8, "(pipeline A)", 6, FAINT)
    ex = vx + vw + 13 + 74.0
    g.line([(ex + 1.5, up), (ex + 8, up)], ARROW, 1.5)
    g.line([(ex + 1.5, dn), (ex + 8, dn)], ARROW, 1.5)
    g.line([(ex + 8, up), (ex + 8, dn)], ARROW, 1.5)
    evx = ex + 16.5
    g.line([(ex + 8, mid), (evx - 3.6, mid)], ARROW, 1.5, head=4)
    evw = W - 7 - evx
    g.rect(evx, mid - 30, evw, 60, 5, BLUE_FILL, BLUE_EDGE, 0.7, "2.4,2")
    g.text(evx + evw / 2, mid - 20.4, "Evaluation", 7.4, INK, bold=True, anchor="middle")
    for j, (lab, colr) in enumerate((("Detection rate", MUTED), ("False-alarm rate", MUTED), ("Localization", MUTED))):
        yy = mid - 10.2 + j * 8
        g.out.append(f'<circle cx="{evx + 8:.2f}" cy="{yy - 2.1:.2f}" r="1.7" fill="{colr}"/>')
        g.text(evx + 13, yy, lab, 6.3, "#27313f", fit=evw - 15)
    g.rect(evx + 3, mid + 11.6, evw - 6, 16.2, 2.5, RED_FILL, RED_EDGE, 0.5)
    g.text(evx + evw / 2, mid + 18.2, "Truth: injected flaw,", 5.8, RED, bold=True, anchor="middle", fit=evw - 5)
    g.text(evx + evw / 2, mid + 25, "not the true effect", 5.8, RED, bold=True, anchor="middle", fit=evw - 5)
    return g


def main() -> None:
    icons = load_icons()
    for name, build in (("figure1", figure1), ("figure2", figure2)):
        svg = HERE / f"{name}.svg"
        build(icons).save(svg)
        subprocess.run([INKSCAPE, str(svg), "--export-type=pdf", f"--export-filename={HERE / (name + '.pdf')}"],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("wrote", svg.name, "and", name + ".pdf")


if __name__ == "__main__":
    sys.exit(main())
