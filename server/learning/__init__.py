"""
Learning module for Hobbs Agent.

Provides adaptive learning, pattern detection, and rule refinement
capabilities based on historical data analysis.
"""

from server.learning.learning_engine import learning_engine
from server.learning.rule_refinement import rule_refinement
from server.learning.patterns import (
    rolling_avg,
    z_score,
    histogram,
    detect_peak_hours,
    correlation,
)

__all__ = [
    "learning_engine",
    "rule_refinement",
    "rolling_avg",
    "z_score",
    "histogram",
    "detect_peak_hours",
    "correlation",
]
