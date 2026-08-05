"""Audit result types."""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ProbeResult:
    """One measured failure mode.

    Band probes carry an ``innocent`` interval and trigger when the 95% CI is
    disjoint from it. Exact procedures (conventional thresholds, zero-tolerance
    counts, cross-rater comparisons) set ``flagged`` directly and it overrides
    the band logic.
    """

    name: str
    value: float
    detail: str
    n: int
    unit: str = ""
    ci: tuple[float, float] | None = None
    innocent: tuple[float, float] | None = None
    flagged: bool | None = None

    @property
    def triggered(self) -> bool:
        if self.flagged is not None:
            return self.flagged
        if self.innocent is None or self.ci is None:
            return False
        lo, hi = self.ci
        band_lo, band_hi = self.innocent
        return hi < band_lo or lo > band_hi


@dataclass(frozen=True)
class SkippedProbe:
    """A check that could not run, and exactly what to log to enable it."""

    name: str
    reason: str


@dataclass
class AuditResult:
    """All probe results for one labeled dataset."""

    probes: list[ProbeResult] = field(default_factory=list)
    skipped: list[SkippedProbe] = field(default_factory=list)

    @property
    def flags(self) -> list[ProbeResult]:
        return [p for p in self.probes if p.triggered]

    def probe(self, name: str) -> ProbeResult | None:
        for p in self.probes:
            if p.name == name:
                return p
        return None

    def to_dict(self) -> dict:
        def _num(x: float) -> float | None:
            return None if isinstance(x, float) and math.isnan(x) else x

        return {
            "probes": [
                {
                    "name": p.name,
                    "value": _num(p.value),
                    "detail": p.detail,
                    "n": p.n,
                    "unit": p.unit,
                    "ci": list(p.ci) if p.ci else None,
                    "innocent": list(p.innocent) if p.innocent else None,
                    "triggered": p.triggered,
                }
                for p in self.probes
            ],
            "skipped": [{"name": s.name, "reason": s.reason} for s in self.skipped],
            "flags": [p.name for p in self.flags],
        }
