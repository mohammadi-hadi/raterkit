"""Statistical primitives.

Everything here is implemented from first principles on purpose: the library
runs with no scipy/statsmodels at runtime, and every function is cross-checked
against those packages in the test suite. Statistic paths avoid BLAS-backed
matrix products so results are byte-identical across platforms.
"""

from __future__ import annotations

import math
from statistics import NormalDist
from typing import Literal

import numpy as np

Level = Literal["nominal", "ordinal", "interval"]

_NORMAL = NormalDist()


def _gammq(a: float, x: float) -> float:
    """Regularized upper incomplete gamma Q(a, x) = Gamma(a, x) / Gamma(a).

    Series expansion for x < a + 1, Lentz continued fraction otherwise
    (Numerical Recipes 6.2). Accurate to ~1e-12 for the df range used here.
    """
    if x < 0 or a <= 0:
        raise ValueError("gammq requires x >= 0 and a > 0")
    if x == 0:
        return 1.0
    if x < a + 1.0:
        # P(a, x) by series, return 1 - P.
        term = 1.0 / a
        total = term
        for n in range(1, 500):
            term *= x / (a + n)
            total += term
            if abs(term) < abs(total) * 1e-15:
                break
        p = total * math.exp(-x + a * math.log(x) - math.lgamma(a))
        return max(0.0, min(1.0, 1.0 - p))
    # Q(a, x) by modified Lentz continued fraction.
    tiny = 1e-300
    b = x + 1.0 - a
    c = 1.0 / tiny
    d = 1.0 / b
    h = d
    for i in range(1, 500):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < tiny:
            d = tiny
        c = b + an / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-15:
            break
    q = h * math.exp(-x + a * math.log(x) - math.lgamma(a))
    return max(0.0, min(1.0, q))


def chi2_sf(x: float, df: int) -> float:
    """Survival function of the chi-square distribution."""
    if x <= 0:
        return 1.0
    return _gammq(df / 2.0, x / 2.0)


def chi_square_gof(observed: list[float], expected: list[float]) -> tuple[float, float]:
    """Goodness-of-fit chi-square. Returns (statistic, p). Zero-expected cells dropped."""
    stat = 0.0
    df = -1
    for o, e in zip(observed, expected, strict=True):
        if e <= 0:
            continue
        stat += (o - e) ** 2 / e
        df += 1
    if df < 1:
        return 0.0, 1.0
    return stat, chi2_sf(stat, df)


def benjamini_hochberg(pvalues: list[float], alpha: float) -> list[bool]:
    """BH step-up procedure. Returns per-hypothesis keep decisions."""
    m = len(pvalues)
    if m == 0:
        return []
    order = sorted(range(m), key=lambda i: pvalues[i])
    keep = [False] * m
    threshold_rank = 0
    for rank, idx in enumerate(order, start=1):
        if pvalues[idx] <= alpha * rank / m:
            threshold_rank = rank
    for rank, idx in enumerate(order, start=1):
        if rank <= threshold_rank:
            keep[idx] = True
    return keep


# ---------------------------------------------------------------------------
# Krippendorff's alpha
# ---------------------------------------------------------------------------


def _coincidence_matrix(counts: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
    """Coincidence matrix from an items x categories value-count table.

    Items with fewer than two ratings contribute nothing (pairable values only).
    Returns (o, n_c, n) where o[c, k] is the coincidence count, n_c the
    marginals and n the total number of pairable values.
    """
    n_cat = counts.shape[1]
    o = np.zeros((n_cat, n_cat), dtype=float)
    for row in counts:
        m_u = float(row.sum())
        if m_u < 2:
            continue
        for c in range(n_cat):
            if row[c] == 0:
                continue
            for k in range(n_cat):
                if row[k] == 0:
                    continue
                pairs = row[c] * (row[k] - (1 if c == k else 0))
                if pairs:
                    o[c, k] += pairs / (m_u - 1.0)
    n_c = o.sum(axis=1)
    return o, n_c, float(n_c.sum())


def _distance_matrix(values: list[float], n_c: np.ndarray, level: Level) -> np.ndarray:
    n_cat = len(values)
    delta = np.zeros((n_cat, n_cat), dtype=float)
    for c in range(n_cat):
        for k in range(n_cat):
            if c == k:
                continue
            if level == "nominal":
                delta[c, k] = 1.0
            elif level == "interval":
                delta[c, k] = (values[c] - values[k]) ** 2
            else:  # ordinal
                lo, hi = min(c, k), max(c, k)
                cum = float(n_c[lo : hi + 1].sum())
                delta[c, k] = (cum - (n_c[lo] + n_c[hi]) / 2.0) ** 2
    return delta


def krippendorff_alpha(counts: np.ndarray, values: list[float], level: Level = "nominal") -> float:
    """Krippendorff's alpha from an items x categories value-count table.

    ``values`` gives the numeric value of each category column (used by the
    interval metric; the ordinal metric uses column order). Returns nan when
    expected disagreement is zero (fewer than two distinct pairable values).
    """
    o, n_c, n = _coincidence_matrix(counts)
    if n <= 1:
        return float("nan")
    delta = _distance_matrix(values, n_c, level)
    d_o = float((o * delta).sum()) / n
    d_e = float((np.outer(n_c, n_c) * delta).sum()) / (n * (n - 1.0))
    if d_e == 0.0:
        return float("nan")
    return 1.0 - d_o / d_e


def percent_agreement(counts: np.ndarray) -> float:
    """Average pairwise raw agreement over pairable values."""
    o, _, n = _coincidence_matrix(counts)
    if n <= 0:
        return float("nan")
    return float(np.trace(o)) / n


# ---------------------------------------------------------------------------
# Kappa family
# ---------------------------------------------------------------------------


def cohen_kappa(table: np.ndarray, weights: Literal[None, "quadratic"] = None) -> float:
    """Cohen's kappa from a square contingency table of two raters' labels."""
    n = float(table.sum())
    if n == 0:
        return float("nan")
    p = table / n
    k = table.shape[0]
    if weights is None:
        w = 1.0 - np.eye(k)
    else:
        idx = np.arange(k, dtype=float)
        w = (idx[:, None] - idx[None, :]) ** 2
        if k > 1:
            w = w / float((k - 1) ** 2)
    row = p.sum(axis=1)
    col = p.sum(axis=0)
    expected = np.outer(row, col)
    d_o = float((w * p).sum())
    d_e = float((w * expected).sum())
    if d_e == 0.0:
        return float("nan")
    return 1.0 - d_o / d_e


def fleiss_kappa(counts: np.ndarray) -> float:
    """Fleiss' kappa from an items x categories count table with equal ratings per item."""
    m = counts.sum(axis=1)
    if len(set(m.tolist())) != 1 or m[0] < 2:
        raise ValueError("fleiss_kappa requires the same number of ratings on every item")
    n_items = counts.shape[0]
    n_raters = float(m[0])
    p_j = counts.sum(axis=0) / (n_items * n_raters)
    p_i = ((counts * counts).sum(axis=1) - n_raters) / (n_raters * (n_raters - 1.0))
    p_bar = float(p_i.mean())
    p_e = float((p_j * p_j).sum())
    if p_e == 1.0:
        return float("nan")
    return (p_bar - p_e) / (1.0 - p_e)


# ---------------------------------------------------------------------------
# Reliability projections (Spearman-Brown)
# ---------------------------------------------------------------------------


def spearman_brown(r1: float, k: float) -> float:
    """Projected reliability of the mean of k parallel ratings, from single-rating r1."""
    if r1 <= 0.0:
        return 0.0
    return k * r1 / (1.0 + (k - 1.0) * r1)


def raters_needed(r1: float, target: float) -> float:
    """Raters per item needed to reach target reliability (inf if unreachable)."""
    if r1 <= 0.0:
        return float("inf")
    if r1 >= target:
        return 1.0
    return target * (1.0 - r1) / (r1 * (1.0 - target))


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

N_RESAMPLES = 1000
MAX_UNDEFINED_SHARE = 0.1


def bootstrap_ci(
    counts: np.ndarray,
    statistic,
    seed: int = 0,
    n_resamples: int = N_RESAMPLES,
    level: float = 0.95,
) -> tuple[float, float] | None:
    """Percentile bootstrap CI, resampling items (rows of the count table).

    ``statistic`` maps a count table to a float. Returns None when more than
    MAX_UNDEFINED_SHARE of resamples are undefined (nan).
    """
    rng = np.random.Generator(np.random.PCG64(seed))
    n_items = counts.shape[0]
    if n_items == 0:
        return None
    stats: list[float] = []
    undefined = 0
    for _ in range(n_resamples):
        idx = rng.integers(0, n_items, size=n_items)
        value = statistic(counts[idx])
        if math.isnan(value):
            undefined += 1
        else:
            stats.append(value)
    if undefined > MAX_UNDEFINED_SHARE * n_resamples or not stats:
        return None
    lo = (1.0 - level) / 2.0
    lower = float(np.quantile(np.array(stats), lo))
    upper = float(np.quantile(np.array(stats), 1.0 - lo))
    return lower, upper


def bootstrap_ci_grouped(
    rows: np.ndarray,
    groups: list[int],
    statistic,
    seed: int = 0,
    n_resamples: int = N_RESAMPLES,
    level: float = 0.95,
) -> tuple[float, float] | None:
    """Percentile bootstrap CI resampling groups of rows together.

    ``groups[i]`` names the group of ``rows[i]``; resampling draws whole
    groups so within-group dependence (e.g. several rating pairs from one
    item) is respected. Returns None when more than MAX_UNDEFINED_SHARE of
    resamples are undefined.
    """
    if rows.shape[0] == 0:
        return None
    unique = sorted(set(groups))
    members: dict[int, list[int]] = {g: [] for g in unique}
    for i, g in enumerate(groups):
        members[g].append(i)
    rng = np.random.Generator(np.random.PCG64(seed))
    n_groups = len(unique)
    stats: list[float] = []
    undefined = 0
    for _ in range(n_resamples):
        picks = rng.integers(0, n_groups, size=n_groups)
        idx = [i for p in picks for i in members[unique[p]]]
        value = statistic(rows[idx])
        if math.isnan(value):
            undefined += 1
        else:
            stats.append(value)
    if undefined > MAX_UNDEFINED_SHARE * n_resamples or not stats:
        return None
    lo = (1.0 - level) / 2.0
    lower = float(np.quantile(np.array(stats), lo))
    upper = float(np.quantile(np.array(stats), 1.0 - lo))
    return lower, upper


def normal_sf(z: float) -> float:
    """Standard normal survival function."""
    return 1.0 - _NORMAL.cdf(z)
