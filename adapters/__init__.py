"""
Explorer adapters package.

This package contains adapters that convert external LLM-based explorer
outputs into the unified trajectory format.

ARCHITECTURAL RULES:
1. Explorers are BLACK BOXES - never modify their source code
2. Adapters are the ONLY bridge: explorer output → unified trajectory
3. Core runtime must NOT depend on adapters (offline only)

DEPENDENCY RULES:
Adapters MAY import:
- schema.py (unified trajectory format)
- standard library (json, pathlib, typing)
- explorer output files (logs, json, pickle)

Adapters MUST NOT import:
- envs/ (runtime environments)
- agents/ (runtime agents)
- browser/ (browser automation)
- training/ (training code)

This maintains a clean separation between offline exploration
and online production runtime.
"""
