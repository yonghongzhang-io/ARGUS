"""Build the arXiv source bundle from this directory (run after `tectonic main.tex`).

    tectonic -X compile main.tex --keep-intermediates && python3 make_arxiv_bundle.py

Comments are stripped, the bibliography is inlined from main.bbl (arXiv does not run BibTeX
reliably under every engine), `\\pdfoutput=1` is put first, and only files the paper includes
are packed. Output: submissions/ARGUS_arxiv_source.tar.gz (not tracked).
"""
from __future__ import annotations

import re
import tarfile
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "submissions" / "ARGUS_arxiv_source.tar.gz"


def strip(text: str) -> str:
    lines = []
    for line in text.splitlines():
        cut = re.sub(r"(?<!\\)%.*", "%" if re.search(r"(?<!\\)%", line) and not line.lstrip().startswith("%") else "", line)
        if line.lstrip().startswith("%"):
            continue
        lines.append(cut.rstrip())
    return "\n".join(lines) + "\n"


def main() -> None:
    bbl = HERE / "main.bbl"
    if not bbl.exists():
        raise SystemExit("main.bbl not found: compile with --keep-intermediates first")
    tex = strip((HERE / "main.tex").read_text(encoding="utf-8"))
    tex = re.sub(r"\\bibliography\{references\}", r"\\input{main.bbl}", tex)
    assert r"\input{main.bbl}" in tex
    tex = "\\pdfoutput=1\n" + tex
    figures = sorted(set(re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{figures/([^}]+)\}",
                                    tex + "".join(p.read_text(encoding="utf-8") for p in (HERE / "sections").glob("*.tex")))))
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "sections").mkdir()
        (root / "figures").mkdir()
        (root / "main.tex").write_text(tex, encoding="utf-8")
        (root / "main.bbl").write_bytes(bbl.read_bytes())
        for name in ("acl.sty", "acl_natbib.bst"):
            (root / name).write_bytes((HERE / name).read_bytes())
        for p in sorted((HERE / "sections").glob("*.tex")):
            (root / "sections" / p.name).write_text(strip(p.read_text(encoding="utf-8")), encoding="utf-8")
        for fig in figures:
            src = HERE / "figures" / (fig if "." in fig else fig + ".pdf")
            (root / "figures" / src.name).write_bytes(src.read_bytes())
        OUT.parent.mkdir(exist_ok=True)
        with tarfile.open(OUT, "w:gz") as tar:
            for p in sorted(root.rglob("*")):
                if p.is_file():
                    tar.add(p, arcname=str(p.relative_to(root)))
    print("wrote", OUT.relative_to(HERE), "with", len(figures), "figures")


if __name__ == "__main__":
    main()
