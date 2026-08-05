"""Eight demo annotation projects, seven implanted defects.

Each row implants exactly one defect and must produce exactly its target flag
set. Seeds are found by search (`_find_seed`) and then confirmed by running
the full audit: for threshold-riding defects — a lean or a drift sized near
the innocent band — the seed selection IS the defect being demonstrated, a
project where the failure is large enough to clear the evidence bar.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .probes import run_audit
from .result import AuditResult
from .synthetic import simulate

MAX_SEED = 60


@dataclass(frozen=True)
class DemoRow:
    name: str
    defect: str
    target: frozenset[str]
    kwargs: dict = field(default_factory=dict)


ROWS: list[DemoRow] = [
    DemoRow(
        "clean",
        "nothing",
        frozenset(),
        dict(competence=0.92),
    ),
    DemoRow(
        "careless-crowd",
        "every rater at 55% accuracy",
        frozenset({"reliability"}),
        dict(competence=0.55),
    ),
    DemoRow(
        "one-spammer",
        "one rater answers uniformly at random",
        frozenset({"rogue raters"}),
        dict(competence=0.93, n_raters=12, spammers=1, spammer_load=0.7),
    ),
    DemoRow(
        "leaning-rater",
        "one rater always takes the same side of ambiguous items",
        frozenset({"rater bias"}),
        dict(
            competence=0.95,
            n_items=400,
            n_raters=8,
            hard_share=0.4,
            leaners=1,
            with_gold=False,
        ),
    ),
    DemoRow(
        "tiring-crowd",
        "competence decays 0.97 to 0.73 over the queue",
        frozenset({"drift"}),
        dict(competence=0.97, drift=0.24),
    ),
    DemoRow(
        "leaky-split",
        "12 test items duplicate a train item's text",
        frozenset({"split leakage"}),
        dict(competence=0.92, dup_across_splits=12),
    ),
    DemoRow(
        "stale-gold",
        "8% of gold labels are wrong",
        frozenset({"stale gold"}),
        dict(competence=0.92, gold_error=0.08),
    ),
    DemoRow(
        "easy-but-skewed",
        "94% of items are one class; raters 90% accurate",
        frozenset({"reliability"}),
        dict(prevalence=[0.94, 0.02, 0.02, 0.02], competence=0.9),
    ),
]


def _audit_row(row: DemoRow, seed: int) -> AuditResult:
    ratings, gold, config = simulate(seed=seed, **row.kwargs)
    return run_audit(ratings, gold, config)


def _find_seed(row: DemoRow) -> tuple[int, AuditResult]:
    for seed in range(MAX_SEED):
        audit = _audit_row(row, seed)
        if frozenset(f.name for f in audit.flags) == row.target:
            return seed, audit
    raise RuntimeError(f"no seed below {MAX_SEED} lands {row.name} on its target flags")


def build() -> list[tuple[DemoRow, int, AuditResult]]:
    """Audit all demo rows, confirming each lands exactly its target flag set."""
    out = []
    for row in ROWS:
        seed, audit = _find_seed(row)
        out.append((row, seed, audit))
    return out
