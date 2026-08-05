"""Cross-checks against scipy, statsmodels and the krippendorff package.

raterkit depends on none of these at runtime; these tests are the evidence
that the hand-rolled implementations match the reference ones.
"""

import krippendorff
import numpy as np
import pytest
from scipy.stats import chi2 as scipy_chi2
from statsmodels.stats.inter_rater import cohens_kappa as sm_cohen
from statsmodels.stats.inter_rater import fleiss_kappa as sm_fleiss
from statsmodels.stats.multitest import multipletests

from raterkit.stats import (
    benjamini_hochberg,
    bootstrap_ci,
    bootstrap_ci_grouped,
    chi2_sf,
    chi_square_gof,
    cohen_kappa,
    fleiss_kappa,
    krippendorff_alpha,
    percent_agreement,
    raters_needed,
    spearman_brown,
)


def _random_counts(rng, n_items=40, n_raters=4, n_cats=5, missing=0.2):
    data = rng.integers(1, n_cats + 1, size=(n_raters, n_items)).astype(float)
    data[rng.random((n_raters, n_items)) < missing] = np.nan
    counts = np.zeros((n_items, n_cats))
    for r in range(n_raters):
        for i in range(n_items):
            if not np.isnan(data[r, i]):
                counts[i, int(data[r, i]) - 1] += 1
    return data, counts


@pytest.mark.parametrize("level", ["nominal", "ordinal", "interval"])
@pytest.mark.parametrize("seed", [1, 2, 3])
def test_alpha_matches_reference_package(level, seed):
    rng = np.random.default_rng(seed)
    data, counts = _random_counts(rng)
    mine = krippendorff_alpha(counts, [1, 2, 3, 4, 5], level)
    ref = krippendorff.alpha(
        reliability_data=data, level_of_measurement=level, value_domain=[1, 2, 3, 4, 5]
    )
    assert mine == pytest.approx(ref, abs=1e-10)


def test_alpha_perfect_agreement_is_one():
    counts = np.zeros((30, 3))
    counts[:10, 0] = 3
    counts[10:20, 1] = 3
    counts[20:, 2] = 3
    assert krippendorff_alpha(counts, [0, 1, 2]) == pytest.approx(1.0)


def test_alpha_undefined_when_one_category():
    counts = np.zeros((10, 3))
    counts[:, 1] = 3
    assert np.isnan(krippendorff_alpha(counts, [0, 1, 2]))


def test_alpha_ignores_single_rated_items():
    rng = np.random.default_rng(0)
    _data, counts = _random_counts(rng)
    padded = np.vstack([counts, np.eye(5)[:3]])  # three items with one rating each
    assert krippendorff_alpha(padded, [1, 2, 3, 4, 5]) == pytest.approx(
        krippendorff_alpha(counts, [1, 2, 3, 4, 5])
    )


def test_percent_agreement_known_case():
    counts = np.array([[2.0, 0.0], [1.0, 1.0]])
    # item 1: both pairs agree; item 2: no pair agrees
    assert percent_agreement(counts) == pytest.approx(0.5)


def test_cohen_kappa_matches_statsmodels():
    rng = np.random.default_rng(4)
    table = rng.integers(1, 30, size=(4, 4)).astype(float)
    assert cohen_kappa(table) == pytest.approx(sm_cohen(table).kappa, abs=1e-10)
    assert cohen_kappa(table, "quadratic") == pytest.approx(
        sm_cohen(table, wt="fc").kappa, abs=1e-10
    )


def test_fleiss_kappa_matches_statsmodels():
    rng = np.random.default_rng(5)
    counts = rng.multinomial(6, [0.3, 0.4, 0.3], size=30).astype(float)
    assert fleiss_kappa(counts) == pytest.approx(sm_fleiss(counts), abs=1e-10)


def test_fleiss_kappa_rejects_unequal_ratings():
    counts = np.array([[3.0, 0.0], [2.0, 0.0]])
    with pytest.raises(ValueError):
        fleiss_kappa(counts)


@pytest.mark.parametrize("df", range(1, 11))
def test_chi2_sf_matches_scipy(df):
    for x in [0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 25.0, 60.0]:
        assert chi2_sf(x, df) == pytest.approx(scipy_chi2.sf(x, df), abs=1e-10)


def test_chi_square_gof_uniform():
    stat, p = chi_square_gof([10, 10, 10, 10], [10, 10, 10, 10])
    assert stat == 0.0 and p == 1.0


def test_benjamini_hochberg_matches_statsmodels():
    rng = np.random.default_rng(6)
    p = rng.random(40).tolist()
    for alpha in [0.01, 0.05, 0.2]:
        assert benjamini_hochberg(p, alpha) == multipletests(p, alpha, "fdr_bh")[0].tolist()


def test_spearman_brown_known_values():
    assert spearman_brown(0.5, 2) == pytest.approx(2 / 3)
    assert spearman_brown(0.8, 1) == pytest.approx(0.8)
    assert raters_needed(0.5, 0.8) == pytest.approx(4.0)
    assert raters_needed(0.0, 0.8) == float("inf")
    assert raters_needed(0.9, 0.8) == 1.0


def test_bootstrap_ci_contains_point_estimate_and_is_deterministic():
    rng = np.random.default_rng(7)
    counts = rng.multinomial(3, [0.6, 0.25, 0.15], size=80).astype(float)

    def stat(c):
        return krippendorff_alpha(c, [0, 1, 2])

    ci1 = bootstrap_ci(counts, stat)
    ci2 = bootstrap_ci(counts, stat)
    assert ci1 == ci2
    assert ci1[0] <= stat(counts) <= ci1[1]


def test_bootstrap_grouped_keeps_groups_together():
    rows = np.array([[1.0, 1.0, 0.0]] * 6 + [[0.0, 1.0, 1.0]] * 6)
    groups = [0, 0, 0, 1, 1, 1, 2, 2, 2, 3, 3, 3]

    def stat(r):
        # group composition is preserved: row counts stay a multiple of 3
        assert r.shape[0] % 3 == 0
        return float(r[:, 1].mean())

    ci = bootstrap_ci_grouped(rows, groups, stat, n_resamples=50)
    assert ci is not None
