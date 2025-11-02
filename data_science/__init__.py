"""Minimal package marker for the Data Science agent.

This file enables the project to build/install as a Python package
(`module-name = "data_science"` in pyproject.toml).
"""

from .agent import root_agent as agent

__all__ = ['agent']


