"""raterkit: audit a labeled dataset before you trust it."""

from .probes import run_audit
from .result import AuditResult, ProbeResult, SkippedProbe
from .schema import Config, Gold, Rating, load_config, load_gold, load_ratings

__version__ = "0.1.0"

__all__ = [
    "AuditResult",
    "Config",
    "Gold",
    "ProbeResult",
    "Rating",
    "SkippedProbe",
    "load_config",
    "load_gold",
    "load_ratings",
    "run_audit",
    "__version__",
]
