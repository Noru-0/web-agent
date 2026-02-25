"""
Trajectory recorders for online agent runs.

This package contains recorders that observe agent-environment
interactions and save them in the unified trajectory format.

ARCHITECTURAL RULES:
- Recorders depend ONLY on: schema.py, standard library
- Recorders must NOT import: explorers/, adapters/, training/
- Recording is optional and non-intrusive
"""
