"""The fixed, deterministic audit pipeline.

Stage order is written in code and never decided by a model:

    decomposition -> extraction -> assessment -> localization -> report
                     (agentic)     (agentic)

Only `extraction` and `assessment` invoke the bounded agent loop.
"""

from .audit import run_audit

__all__ = ["run_audit"]
