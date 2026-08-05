"""The probes: one measured failure mode each, and the audit that runs them.

Band probes report a value with a 95% bootstrap CI and trigger only when the
whole CI leaves the innocent band. Exact procedures — conventional floors,
zero-tolerance counts, cross-rater comparisons — set ``flagged`` directly.
All thresholds live here, in one place, and are easy to disagree with.
"""

from __future__ import annotations

import numpy as np

from .dataset import Dataset
from .result import AuditResult, ProbeResult, SkippedProbe
from .schema import Config, Gold, Rating
from .stats import (
    bootstrap_ci,
    bootstrap_ci_grouped,
    krippendorff_alpha,
    percent_agreement,
    raters_needed,
)

ALPHA_FLOOR = 0.667  # Krippendorff's "unacceptable below" convention
INNOCENT_RELIABILITY = (ALPHA_FLOOR, 1.0)
INNOCENT_BIAS = (0.0, 0.1)  # total variation distance, rater vs the rest
INNOCENT_DRIFT = (-0.1, 0.1)  # early-minus-late alpha gap
INNOCENT_GOLD = (0.0, 0.02)  # share of gold contradicted by a unanimous crowd
MIN_RATER_PAIRS = 30  # rater-level probes need at least this many pairs
MIN_GOLD_ITEMS = 20  # gold probe needs at least this many double-rated golds


def _alpha_fn(ds: Dataset):
    values, level = ds.values, ds.config.level

    def fn(counts: np.ndarray) -> float:
        return krippendorff_alpha(counts, values, level)  # type: ignore[arg-type]

    return fn


def _pairable(counts: np.ndarray) -> int:
    m = counts.sum(axis=1)
    return int(m[m >= 2].sum())


def reliability(ds: Dataset) -> ProbeResult | SkippedProbe:
    """Chance-corrected agreement of the whole pool (Krippendorff's alpha)."""
    n = _pairable(ds.counts)
    if n == 0:
        return SkippedProbe(
            "reliability", "no item has two or more ratings; log overlapping assignments"
        )
    fn = _alpha_fn(ds)
    value = fn(ds.counts)
    ci = bootstrap_ci(ds.counts, fn)
    return ProbeResult(
        name="reliability",
        value=value,
        detail=(
            f"Krippendorff's alpha ({ds.config.level}) = {value:.3f} over {n} pairable "
            f"ratings; the conventional floor is {ALPHA_FLOOR}."
        ),
        n=n,
        unit="alpha",
        ci=ci,
        innocent=INNOCENT_RELIABILITY,
    )


def rater_agreements(ds: Dataset) -> list[tuple[str, float, tuple[float, float] | None, int]]:
    """Per-rater agreement with everyone else: (rater, alpha, ci, n_pairs).

    Only raters with MIN_RATER_PAIRS or more rating pairs are included; the
    bootstrap resamples items, not pairs, so several pairs from one item move
    together.
    """
    fn = _alpha_fn(ds)
    out = []
    for rater in ds.raters:
        rows, groups = ds.pair_table(rater)
        if rows.shape[0] < MIN_RATER_PAIRS:
            continue
        value = fn(rows)
        ci = bootstrap_ci_grouped(rows, groups, fn)
        out.append((rater, value, ci, rows.shape[0]))
    return out


def rogue_raters(ds: Dataset, pool: ProbeResult | SkippedProbe) -> ProbeResult | SkippedProbe:
    """Raters whose agreement with everyone else is credibly below the pool's."""
    if isinstance(pool, SkippedProbe) or pool.ci is None:
        return SkippedProbe("rogue raters", "needs a pool reliability estimate with a CI")
    pool_lo = pool.ci[0]
    tested, flagged_ids = 0, []
    worst_id, worst_alpha = "", float("inf")
    for rater, value, ci, _n_pairs in rater_agreements(ds):
        tested += 1
        if not np.isnan(value) and value < worst_alpha:
            worst_id, worst_alpha = rater, value
        if ci is not None and ci[1] < pool_lo:
            flagged_ids.append(rater)
    if tested == 0:
        return SkippedProbe(
            "rogue raters",
            f"no rater has {MIN_RATER_PAIRS}+ rating pairs with others; "
            "assign more overlapping items per rater",
        )
    untested = len(ds.raters) - tested
    detail = (
        f"{len(flagged_ids)} of {tested} raters agree with the rest credibly worse than "
        f"the pool agrees with itself"
        + (f": {', '.join(sorted(flagged_ids)[:5])}" if flagged_ids else "")
        + (f"; {untested} raters had too few pairs to test" if untested else "")
        + f". Lowest rater-vs-rest alpha: {worst_alpha:.3f} ({worst_id})."
    )
    return ProbeResult(
        name="rogue raters",
        value=float(len(flagged_ids)),
        detail=detail,
        n=tested,
        unit="raters",
        flagged=len(flagged_ids) > 0,
    )


def rater_bias(ds: Dataset) -> ProbeResult | SkippedProbe:
    """Raters whose label distribution credibly diverges from everyone else's."""
    rng_seed = 0
    tested, flagged_ids = 0, []
    worst_id, worst_tvd = "", 0.0
    for rater in ds.raters:
        own = ds.ratings_of(rater)
        if len(own) < MIN_RATER_PAIRS:
            continue
        rest = ds.marginal(exclude=rater)
        if rest.sum() == 0:
            continue
        tested += 1
        rest_p = rest / rest.sum()
        cats = np.array([ds.cat_of(r.label) for r in own])

        def tvd_of(sample: np.ndarray, rest_p: np.ndarray = rest_p) -> float:
            p = np.bincount(sample, minlength=len(ds.cats)) / len(sample)
            return 0.5 * float(np.abs(p - rest_p).sum())

        value = tvd_of(cats)
        if value > worst_tvd:
            worst_id, worst_tvd = rater, value
        rng = np.random.Generator(np.random.PCG64(rng_seed))
        draws = [tvd_of(cats[rng.integers(0, len(cats), size=len(cats))]) for _ in range(1000)]
        lo = float(np.quantile(np.array(draws), 0.025))
        if lo > INNOCENT_BIAS[1]:
            flagged_ids.append(rater)
    if tested == 0:
        return SkippedProbe(
            "rater bias",
            f"no rater has {MIN_RATER_PAIRS}+ ratings; assign more items per rater",
        )
    detail = (
        f"{len(flagged_ids)} of {tested} raters use the labels credibly differently from "
        f"the rest (total variation distance beyond {INNOCENT_BIAS[1]})"
        + (f": {', '.join(sorted(flagged_ids)[:5])}" if flagged_ids else "")
        + f". Largest divergence: {worst_tvd:.2f} ({worst_id})."
    )
    return ProbeResult(
        name="rater bias",
        value=float(len(flagged_ids)),
        detail=detail,
        n=tested,
        unit="raters",
        flagged=len(flagged_ids) > 0,
    )


def drift(ds: Dataset) -> ProbeResult | SkippedProbe:
    """Did agreement change between the early and the late half of the work?"""
    times = ds.item_times()
    if times is None:
        return SkippedProbe("drift", "needs t on every rating; log a timestamp per rating")
    order = sorted(ds.items, key=lambda it: (times[it], it))
    half = len(order) // 2
    if half < 5:
        return SkippedProbe("drift", "fewer than 10 items; too few to split by time")
    item_index = {it: i for i, it in enumerate(ds.items)}
    early_idx = [item_index[it] for it in order[:half]]
    late_idx = [item_index[it] for it in order[half:]]
    fn = _alpha_fn(ds)
    early, late = ds.counts[early_idx], ds.counts[late_idx]
    gap = fn(early) - fn(late)
    rng = np.random.Generator(np.random.PCG64(0))
    draws = []
    for _ in range(1000):
        e = early[rng.integers(0, len(early_idx), size=len(early_idx))]
        la = late[rng.integers(0, len(late_idx), size=len(late_idx))]
        g = fn(e) - fn(la)
        if not np.isnan(g):
            draws.append(g)
    ci = None
    if len(draws) >= 900:
        ci = (float(np.quantile(draws, 0.025)), float(np.quantile(draws, 0.975)))
    return ProbeResult(
        name="drift",
        value=gap,
        detail=(
            f"alpha on the earlier half of items minus the later half = {gap:+.3f}; "
            "a credible gap means the guidelines meant something different over time."
        ),
        n=len(order),
        unit="alpha gap",
        ci=ci,
        innocent=INNOCENT_DRIFT,
    )


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def split_leakage(ds: Dataset) -> ProbeResult | SkippedProbe:
    """The same text appearing in more than one split under different item ids."""
    texts: dict[str, str] = {}
    splits: dict[str, set[str]] = {}
    for r in ds.ratings:
        if r.text is not None:
            texts[r.item_id] = _normalize(r.text)
        if r.split is not None:
            splits.setdefault(r.item_id, set()).add(r.split)
    if not texts:
        return SkippedProbe("split leakage", "needs text per item; log the item text")
    if not splits:
        return SkippedProbe("split leakage", "needs split per item; log train/test membership")
    groups: dict[str, set[str]] = {}
    for item, norm in texts.items():
        groups.setdefault(norm, set()).add(item)
    leaks = 0
    dup_items = 0
    for members in groups.values():
        if len(members) < 2:
            continue
        dup_items += len(members)
        spanned = set()
        for item in members:
            spanned |= splits.get(item, set())
        if len(spanned) > 1:
            leaks += 1
    return ProbeResult(
        name="split leakage",
        value=float(leaks),
        detail=(
            f"{leaks} duplicated texts span more than one split "
            f"({dup_items} items are duplicates of another item). Any leak means the "
            "test split is partly memorized."
        ),
        n=len(texts),
        unit="texts",
        flagged=leaks > 0,
    )


def stale_gold(ds: Dataset, gold: list[Gold]) -> ProbeResult | SkippedProbe:
    """Gold labels a unanimous crowd contradicts."""
    gold_map = {g.item_id: g.label for g in gold}
    by_item = ds.by_item()
    eligible: list[bool] = []
    for item_id, label in gold_map.items():
        group = by_item.get(item_id, [])
        if len(group) < 2:
            continue
        crowd = {r.label for r in group}
        eligible.append(len(crowd) == 1 and next(iter(crowd)) != label)
    if len(eligible) < MIN_GOLD_ITEMS:
        return SkippedProbe(
            "stale gold",
            f"needs {MIN_GOLD_ITEMS}+ gold items with two or more crowd ratings each",
        )
    arr = np.array(eligible, dtype=float)
    share = float(arr.mean())
    rng = np.random.Generator(np.random.PCG64(0))
    draws = [float(arr[rng.integers(0, len(arr), size=len(arr))].mean()) for _ in range(1000)]
    ci = (float(np.quantile(draws, 0.025)), float(np.quantile(draws, 0.975)))
    return ProbeResult(
        name="stale gold",
        value=share,
        detail=(
            f"{share:.1%} of {len(arr)} double-rated gold items are contradicted by a "
            "unanimous crowd; those golds are likely wrong or outdated."
        ),
        n=len(arr),
        unit="share",
        ci=ci,
        innocent=INNOCENT_GOLD,
    )


def ambiguity(ds: Dataset) -> ProbeResult | SkippedProbe:
    """Share of multi-rated items that are contested (not unanimous). Descriptive."""
    m = ds.counts.sum(axis=1)
    multi = ds.counts[m >= 2]
    if multi.shape[0] == 0:
        return SkippedProbe("ambiguity", "no item has two or more ratings")
    contested = (multi.max(axis=1) < multi.sum(axis=1)).astype(float)
    share = float(contested.mean())
    rng = np.random.Generator(np.random.PCG64(0))
    draws = [
        float(contested[rng.integers(0, len(contested), size=len(contested))].mean())
        for _ in range(1000)
    ]
    ci = (float(np.quantile(draws, 0.025)), float(np.quantile(draws, 0.975)))
    return ProbeResult(
        name="ambiguity",
        value=share,
        detail=(
            f"{share:.1%} of {multi.shape[0]} multi-rated items are contested (at least one "
            "dissenting rating) — where disagreement lives, and where a single 'true' label "
            "may not exist. Descriptive; never flags."
        ),
        n=int(multi.shape[0]),
        unit="share",
        ci=ci,
    )


def prevalence(ds: Dataset) -> ProbeResult:
    """Raw agreement vs chance-corrected agreement under skewed labels. Descriptive."""
    marg = ds.counts.sum(axis=0)
    top = float(marg.max() / marg.sum()) if marg.sum() else float("nan")
    raw = percent_agreement(ds.counts)
    fn = _alpha_fn(ds)
    alpha = fn(ds.counts)
    return ProbeResult(
        name="prevalence",
        value=top,
        detail=(
            f"most common label covers {top:.1%} of ratings; raw agreement {raw:.1%} vs "
            f"alpha {alpha:.3f}. When these disagree, the skew — not the raters — is "
            "doing the agreeing. Descriptive; never flags."
        ),
        n=int(marg.sum()),
        unit="share",
    )


def rating_depth(ds: Dataset, pool: ProbeResult | SkippedProbe) -> ProbeResult | SkippedProbe:
    """How many raters per item this reliability level implies you need. Descriptive."""
    if isinstance(pool, SkippedProbe) or np.isnan(pool.value):
        return SkippedProbe("rating depth", "needs a pool reliability estimate")
    m = ds.counts.sum(axis=1)
    mean_depth = float(m.mean())
    single = float((m == 1).mean())
    target = ds.config.target_reliability
    needed = raters_needed(pool.value, target)
    needed_text = "unreachable by adding raters" if needed == float("inf") else f"{needed:.1f}"
    return ProbeResult(
        name="rating depth",
        value=mean_depth,
        detail=(
            f"mean {mean_depth:.1f} ratings per item, {single:.0%} single-rated. "
            f"Spearman-Brown: majority-of-k labels need ~{needed_text} raters per item "
            f"for {target:.0%} reliability at this alpha. Descriptive; never flags."
        ),
        n=len(ds.items),
        unit="ratings/item",
    )


def run_audit(
    ratings: list[Rating],
    gold: list[Gold] | None = None,
    config: Config | None = None,
) -> AuditResult:
    """Run every probe that the logged fields allow."""
    config = config or Config()
    ds = Dataset.build(ratings, config)
    result = AuditResult()

    def add(outcome: ProbeResult | SkippedProbe) -> ProbeResult | SkippedProbe:
        if isinstance(outcome, SkippedProbe):
            result.skipped.append(outcome)
        else:
            result.probes.append(outcome)
        return outcome

    pool = add(reliability(ds))
    add(rogue_raters(ds, pool))
    add(rater_bias(ds))
    add(drift(ds))
    add(split_leakage(ds))
    if gold:
        add(stale_gold(ds, gold))
    else:
        result.skipped.append(
            SkippedProbe("stale gold", "needs a gold file; pass --gold gold.jsonl")
        )
    add(ambiguity(ds))
    add(prevalence(ds))
    add(rating_depth(ds, pool))
    return result
