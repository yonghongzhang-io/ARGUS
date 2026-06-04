"""Flaw-injection evaluation loop — the system that validates ARGUS.

    injection -> (clean audit, injected audit) -> evaluation

Local ground truth is the injected flaw, never the true causal effect.
"""

from .injection import inject_flaw
from .metrics import evaluate_pair, summarize_results
from .runner import evaluate_flaws, evaluate_injected_pair

__all__ = [
    "evaluate_flaws",
    "evaluate_injected_pair",
    "evaluate_pair",
    "inject_flaw",
    "summarize_results",
]
