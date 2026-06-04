"""The bounded agent loop and its fixed tool set.

Agency in ARGUS lives only here, and only the `extraction` and `assessment`
stages call into it. Every loop has a hard step budget and writes a full trace.
"""

from .loop import run_bounded_loop
from .tools import DEFAULT_TOOLS

__all__ = ["run_bounded_loop", "DEFAULT_TOOLS"]
