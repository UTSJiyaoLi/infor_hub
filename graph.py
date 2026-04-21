"""Backward-compatible graph entrypoint.

Canonical location: orchestration.graph
"""

from orchestration.graph import graph, run_collector

__all__ = ["run_collector", "graph"]
