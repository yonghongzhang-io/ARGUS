"""Human annotation pilot: receive the two workbooks, measure agreement, build the locked gold.

    python3 experiments/annotation/human_pilot/pilot.py ingest  A.xlsx B.xlsx
    python3 experiments/annotation/human_pilot/pilot.py gold    reconcile.xlsx

`ingest` validates both workbooks (every row filled, sign-off complete), records their SHA-256 in
RECEIPT.json before anything is computed, writes the cell-level labels to the private
data/annotations/human_pilot/ (not tracked), writes aggregate agreement to agreement.json, and
produces reconcile.xlsx: the cells on which the annotators differ, with both labels and both
rationales and nothing else, for the two of them to resolve.

`gold` reads the filled reconcile.xlsx and writes experiments/annotation/gold_final/ with a lock
record. It refuses unresolved rows and refuses to run twice. Protocol: annotation/human_pilot/PROTOCOL.md.
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

import yaml
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "experiments" / "annotation"))
from compare_argus_gold import cohen_kappa, weighted_kappa  # noqa: E402
from goldpath import FINAL_GOLD  # noqa: E402

PRIVATE = ROOT / "data" / "annotations" / "human_pilot"
PAPERS = ["paper_01", "paper_03", "paper_07", "paper_08", "paper_10"]
APPLIC = {"conventional", "analogue", "not applicable"}
RISK = {"low": 0, "medium": 1, "high": 2}
FIELDS = ["paper_id", "dimension", "applicability", "reported", "evidence_location", "verbatim_quote", "risk",
          "confidence", "rationale"]


def dim_ids() -> list[str]:
    dims = yaml.safe_load((ROOT / "config" / "identification_dimensions.yaml").read_text(encoding="utf-8"))
    dims = dims["dimensions"] if isinstance(dims, dict) else dims
    return [d["id"] for d in dims]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def clean(v) -> str:
    return "" if v is None else str(v).strip()


def read_workbook(path: Path, who: str) -> tuple[list[dict], dict, list[str]]:
    wb = load_workbook(path, data_only=True)
    problems, rows = [], []
    ids = dim_ids()
    for pid in PAPERS:
        ws = wb[pid]
        for i, dim in enumerate(ids):
            r = 6 + i
            row = {"paper_id": pid, "dimension": dim, "applicability": clean(ws.cell(r, 5).value).lower(),
                   "reported": clean(ws.cell(r, 6).value).lower(), "evidence_location": clean(ws.cell(r, 7).value),
                   "verbatim_quote": clean(ws.cell(r, 8).value), "risk": clean(ws.cell(r, 9).value).lower(),
                   "confidence": clean(ws.cell(r, 10).value), "rationale": clean(ws.cell(r, 11).value)}
            where = f"{who} {pid} row {i + 1} ({dim})"
            if row["applicability"] not in APPLIC:
                problems.append(f"{where}: applicability is {row['applicability']!r}")
            elif row["applicability"] == "not applicable":
                if row["risk"]:
                    problems.append(f"{where}: not applicable but a risk is given")
            else:
                if row["risk"] not in RISK:
                    problems.append(f"{where}: risk is {row['risk']!r}")
                if row["reported"] not in {"yes", "no", "unclear"}:
                    problems.append(f"{where}: reported is {row['reported']!r}")
            if not row["rationale"]:
                problems.append(f"{where}: rationale is empty")
            rows.append(row)
    so = wb["Sign-off"]
    sign = {"name": clean(so["B3"].value), "dates": clean(so["B4"].value), "hours": clean(so["B5"].value),
            "read_pdfs_myself": clean(so["B6"].value).lower(), "no_ai_tool": clean(so["B7"].value).lower(),
            "no_system_output": clean(so["B8"].value).lower(), "no_discussion": clean(so["B9"].value).lower(),
            "note": clean(so["B10"].value)}
    for k in ("name", "dates", "hours"):
        if not sign[k]:
            problems.append(f"{who} sign-off: {k} is empty")
    for k in ("read_pdfs_myself", "no_ai_tool", "no_system_output", "no_discussion"):
        if sign[k] != "yes":
            problems.append(f"{who} sign-off: '{k}' is {sign[k]!r}, not 'yes' (keep the workbook; record this as a deviation)")
    return rows, sign, problems


def ingest(path_a: Path, path_b: Path) -> None:
    rp = HERE / "RECEIPT.json"
    receipt = json.loads(rp.read_text(encoding="utf-8")) if rp.exists() else {}
    now = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    for who, path in (("A", path_a), ("B", path_b)):  # keep the receipt recorded when each workbook arrived
        receipt.setdefault("received", {}).setdefault(who, {"file": path.name, "sha256": sha(path), "received_at": now})
        if receipt["received"][who]["sha256"] != sha(path):
            raise SystemExit(f"workbook {who} differs from the one whose receipt was recorded ({receipt['received'][who]['file']})")
    receipt["ingested_at"] = now
    receipt["sha256"] = {"A": sha(path_a), "B": sha(path_b)}
    rp.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    data, signs, problems = {}, {}, []
    for who, path in (("A", path_a), ("B", path_b)):
        data[who], signs[who], p = read_workbook(path, who)
        problems += p
    if problems:
        raise SystemExit("workbooks are not complete; nothing computed:\n  " + "\n  ".join(problems))
    PRIVATE.mkdir(parents=True, exist_ok=True)
    for who in "AB":
        with (PRIVATE / f"labels_{who}.csv").open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=FIELDS, lineterminator="\n")
            w.writeheader(); w.writerows(data[who])
    (PRIVATE / "signoff.json").write_text(json.dumps(signs, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    a = {(r["paper_id"], r["dimension"]): r for r in data["A"]}
    b = {(r["paper_id"], r["dimension"]): r for r in data["B"]}
    both = [k for k in a if a[k]["risk"] in RISK and b[k]["risk"] in RISK]
    pairs = [(a[k]["risk"], b[k]["risk"]) for k in both]
    dis = [(x, y) for x, y in pairs if x != y]
    na = lambda d: sum(r["applicability"] == "not applicable" for r in d.values())  # noqa: E731
    out = {"cells": len(a),
           "applicability": {"same": sum(a[k]["applicability"] == b[k]["applicability"] for k in a),
                             "not_applicable_A": na(a), "not_applicable_B": na(b),
                             "not_applicable_both": sum(a[k]["applicability"] == b[k]["applicability"] == "not applicable" for k in a)},
           "risk_both_rated": len(both), "risk_exact": sum(x == y for x, y in pairs),
           "cohen_kappa": round(cohen_kappa(pairs), 4), "weighted_kappa": round(weighted_kappa(pairs), 4),
           "disagreements": len(dis), "disagreements_one_step": sum(abs(RISK[x] - RISK[y]) == 1 for x, y in dis),
           "hours": {w: signs[w]["hours"] for w in "AB"}}
    (HERE / "agreement.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2))

    differ = [k for k in a if a[k]["applicability"] != b[k]["applicability"] or a[k]["risk"] != b[k]["risk"]]
    wb = Workbook(); ws = wb.active; ws.title = "reconcile"
    head = ["paper", "dimension", "A applicability", "A risk", "A location", "A rationale", "B applicability", "B risk",
            "B location", "B rationale", "FINAL applicability", "FINAL risk", "status", "decided by", "note"]
    ws.append(head)
    for c in range(1, len(head) + 1):
        ws.cell(1, c).font = Font(name="Arial", size=10, bold=True)
    for k in differ:
        ws.append([k[0], k[1], a[k]["applicability"], a[k]["risk"], a[k]["evidence_location"], a[k]["rationale"],
                   b[k]["applicability"], b[k]["risk"], b[k]["evidence_location"], b[k]["rationale"], "", "", "", "", ""])
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.font, c.alignment = Font(name="Arial", size=10), Alignment(wrap_text=True, vertical="top")
        for c in row[10:15]:
            c.fill = PatternFill("solid", fgColor="FFF9C4")
    for col, w_ in zip("ABCDEFGHIJKLMNO", (10, 24, 14, 8, 22, 46, 14, 8, 22, 46, 16, 10, 14, 16, 30)):
        ws.column_dimensions[col].width = w_
    n = len(differ) + 1
    for col, f in (("K", '"conventional,analogue,not applicable"'), ("L", '"low,medium,high"'), ("M", '"agreed,unresolved,tie-break"')):
        dv = DataValidation(type="list", formula1=f, allow_blank=True); ws.add_data_validation(dv); dv.add(f"{col}2:{col}{max(n, 2)}")
    ws.freeze_panes = "C2"
    wb.save(PRIVATE / "reconcile.xlsx")
    print(f"\n{len(differ)} cells to reconcile -> {PRIVATE / 'reconcile.xlsx'}")


def gold(reconcile: Path) -> None:
    lock = FINAL_GOLD.parent / "LOCK.json"
    if lock.exists():
        raise SystemExit("gold_final/LOCK.json exists: the gold is locked and is not rebuilt.")
    a = {(r["paper_id"], r["dimension"]): r for r in csv.DictReader((PRIVATE / "labels_A.csv").open(encoding="utf-8"))}
    b = {(r["paper_id"], r["dimension"]): r for r in csv.DictReader((PRIVATE / "labels_B.csv").open(encoding="utf-8"))}
    ws = load_workbook(reconcile, data_only=True)["reconcile"]
    final, problems = {}, []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row or not row[0]:
            continue
        key = (clean(row[0]), clean(row[1]))
        app, risk, status, by = (clean(row[i]).lower() for i in (10, 11, 12, 13))
        if app not in APPLIC or status not in {"agreed", "tie-break"} or not by or (app != "not applicable" and risk not in RISK) \
                or (app == "not applicable" and risk):
            problems.append(f"{key}: applicability {app!r}, risk {risk!r}, status {status!r}, decided by {by!r}")
        final[key] = (app, risk, status)
    expected = {k for k in a if a[k]["applicability"] != b[k]["applicability"] or a[k]["risk"] != b[k]["risk"]}
    if set(final) != expected:
        problems.append(f"reconcile sheet covers {len(final)} cells, expected {len(expected)}")
    if problems:
        raise SystemExit("reconcile.xlsx is not complete; nothing written:\n  " + "\n  ".join(problems))
    rows, dropped = [], []
    for k in a:
        app, risk, source = (a[k]["applicability"], a[k]["risk"], "agree") if k not in final else final[k]
        if app == "not applicable":
            dropped.append(k)
            continue
        rows.append({"paper_id": k[0], "dimension": k[1], "gold_risk": risk, "ambiguous": int(app == "analogue"), "source": source})
    FINAL_GOLD.parent.mkdir(parents=True, exist_ok=True)
    with FINAL_GOLD.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader(); w.writerows(rows)
    lock.write_text(json.dumps({
        "locked_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"), "cells": len(rows),
        "not_applicable": [list(k) for k in dropped], "agreed_independently": len(a) - len(final),
        "reconciled": sum(v[2] == "agreed" for v in final.values()), "tie_break": sum(v[2] == "tie-break" for v in final.values()),
        "sha256": {"gold_final/gold_labels.csv": sha(FINAL_GOLD), "reconcile.xlsx": sha(reconcile),
                   "workbooks": json.loads((HERE / "RECEIPT.json").read_text())["sha256"]},
        "note": "Built once from two independent human annotations; not adjusted afterwards."}, indent=2) + "\n", encoding="utf-8")
    print(f"locked {len(rows)} rated cells ({len(dropped)} not applicable) -> {FINAL_GOLD}")


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "ingest":
        ingest(Path(sys.argv[2]), Path(sys.argv[3]))
    elif len(sys.argv) == 3 and sys.argv[1] == "gold":
        gold(Path(sys.argv[2]))
    else:
        raise SystemExit(__doc__)
