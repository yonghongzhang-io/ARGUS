"""Flaw-injection evaluation loop — the system that validates ARGUS.

    injection -> (clean audit, injected audit) -> evaluation

Local ground truth is the injected flaw, never the true causal effect.
"""

from .injection import inject_flaw
from .metrics import evaluate_pair

__all__ = ["inject_flaw", "evaluate_pair"]
