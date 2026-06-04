"""Command-line entry points for parsed-paper audit and evaluation."""

from __future__ import annotations

import argparse
import json
from typing import Any, Optional

from .evaluation.runner import evaluate_paper_file
from .paper import load_paper
from .pipeline.audit import run_audit


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="argus")
    subparsers = parser.add_subparsers(dest="command", required=True)

    audit_parser = subparsers.add_parser("audit", help="audit one parsed-paper JSON file")
    _add_audit_args(audit_parser)

    eval_parser = subparsers.add_parser("evaluate", help="run clean-vs-injected evaluation")
    _add_evaluate_args(eval_parser)

    args = parser.parse_args(argv)
    if args.command == "audit":
        return _audit(args)
    if args.command == "evaluate":
        return _evaluate(args)
    raise AssertionError(f"unhandled command: {args.command}")


def audit_main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="argus-audit")
    _add_audit_args(parser)
    return _audit(parser.parse_args(argv))


def evaluate_main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="argus-evaluate")
    _add_evaluate_args(parser)
    return _evaluate(parser.parse_args(argv))


def _add_audit_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("paper_json", help="path to parsed-paper JSON")
    parser.add_argument("--max-steps", type=int, default=1, help="bounded-loop step budget")


def _add_evaluate_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("paper_json", help="path to parsed-paper JSON")
    parser.add_argument("--flaw", action="append", dest="flaws", help="flaw id to inject; repeatable")
    parser.add_argument("--max-steps", type=int, default=1, help="bounded-loop step budget")
    parser.add_argument("--threshold", default="medium", help="risk threshold for scoring")


def _audit(args: argparse.Namespace) -> int:
    paper = load_paper(args.paper_json)
    result = run_audit(paper, max_steps=args.max_steps)
    flagged = [
        dim_id
        for dim_id in result.risk_map["ranked"]
        if result.risk_map["by_dimension"][dim_id]["risk"] != "low"
    ]
    print(
        json.dumps(
            {
                "paper_id": result.paper_id,
                "report_path": result.report_path,
                "trace_count": len(result.trace_paths),
                "flagged_risks": flagged[:5],
            },
            indent=2,
        )
    )
    return 0


def _evaluate(args: argparse.Namespace) -> int:
    result = evaluate_paper_file(
        args.paper_json,
        flaw_ids=args.flaws,
        max_steps=args.max_steps,
        threshold=args.threshold,
    )
    print(json.dumps(_evaluation_summary(result), indent=2))
    return 0


def _evaluation_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "summary": result["summary"],
        "pairs": [
            {
                "flaw_id": pair["flaw_id"],
                "target_dimension": pair["ground_truth"]["target_dimension"],
                "score": pair["score"],
                "clean_report": pair["clean_audit"].report_path,
                "injected_report": pair["injected_audit"].report_path,
            }
            for pair in result["pairs"]
        ],
    }


if __name__ == "__main__":
    raise SystemExit(main())
